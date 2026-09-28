#!/usr/bin/env python3
"""Deterministic maintenance for an llm-wiki vault.

Installed into each vault at prompts/tools/wiki_maint.py by /wiki:init. Run it
from the vault root, or pass --vault PATH.

Subcommands:

  lifecycle            Fill lifecycle frontmatter defaults: `status: active` when
                       missing, and `review_by` from `updated` + the page type's
                       half-life (never shortens an existing later date).
  set-catalog FILE     Write `catalog:` lines from a JSON map {relpath: text}.
  index [--check]      Regenerate wiki/index.md (topic level) and every
                       wiki/<topic>/_index.md (article level) from frontmatter.
                       --check exits 1 if regeneration would change anything.
  check                Report lifecycle/catalog/index problems (exit 1 if any).
  candidates [--json]  List consolidation candidates (demotion, overdue review,
                       hubs over the size cap, orphans, pages in fast-decay
                       topics for successor review).
  due                  Say whether a consolidation pass is due.
  log-query            Append one query's cited pages to .query-log.jsonl:
                       --question TEXT --cited TITLE [TITLE ...]

Policy comes from the `lifecycle:` block in wiki.config.md frontmatter, with
per-flavor defaults below. Keys:
  half_life_days          {page type: days}; types not listed never expire
  topic_half_life_days    {topic: days}; overrides the type rule for a topic
  hub_token_cap           body tokens (chars/4) above which a page is a split candidate
  demote_max_inbound      max inbound links for a demotion candidate
  consolidate_every_articles, consolidate_every_days   consolidation cadence
"""
import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
import unicodedata

import yaml

def find_vault(argv):
    """--vault PATH, else the vault two levels above this script, else cwd."""
    if "--vault" in argv:
        i = argv.index("--vault")
        path = argv[i + 1]
        del argv[i:i + 2]
        return os.path.abspath(path)
    installed = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if os.path.exists(os.path.join(installed, "wiki.config.md")):
        return installed
    return os.getcwd()


VAULT = find_vault(sys.argv)
WIKI = os.path.join(VAULT, "wiki")
LOG = os.path.join(WIKI, "log.md")
TOP_INDEX = os.path.join(WIKI, "index.md")
QUERY_LOG = os.path.join(VAULT, ".query-log.jsonl")
CONFIG = os.path.join(VAULT, "wiki.config.md")

# ---- policy -----------------------------------------------------------------
FLAVOR_HALF_LIFE = {"research": {"paper": 180}, "domain": {}, "course": {}}
DEFAULTS = {
    "topic_half_life_days": {},
    "hub_token_cap": 5000,
    "demote_max_inbound": 2,
    "consolidate_every_articles": 100,
    "consolidate_every_days": 90,
}


def load_policy():
    cfg = {}
    if os.path.exists(CONFIG):
        m = re.match(r"\A---\n(.*?)\n---\n", open(CONFIG, encoding="utf-8").read(), re.S)
        if m:
            try:
                cfg = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError as e:
                # Keep working on a malformed config: read flavor/title line by line.
                print(f"warning: wiki.config.md frontmatter does not parse ({e.problem}); "
                      "using defaults for lifecycle policy", file=sys.stderr)
                for key in ("flavor", "title"):
                    km = re.search(rf"^{key}:\s*(.+)$", m.group(1), re.M)
                    if km:
                        cfg[key] = km.group(1).strip().strip('"')
    pol = dict(DEFAULTS)
    pol["half_life_days"] = FLAVOR_HALF_LIFE.get(cfg.get("flavor"), {})
    pol.update({k: v for k, v in (cfg.get("lifecycle") or {}).items() if v is not None})
    pol["title"] = cfg.get("title") or "Wiki"
    return pol


POLICY = load_policy()
HALF_LIFE_DAYS = POLICY["half_life_days"] or {}
TOPIC_HALF_LIFE_DAYS = POLICY["topic_half_life_days"] or {}
HUB_TOKEN_CAP = int(POLICY["hub_token_cap"])
DEMOTE_MAX_INBOUND = int(POLICY["demote_max_inbound"])
CONSOLIDATE_EVERY_ARTICLES = int(POLICY["consolidate_every_articles"])
CONSOLIDATE_EVERY_DAYS = int(POLICY["consolidate_every_days"])
CATALOG_MAX_WORDS = 30          # hard ceiling checked by `check`; target is ~25
RECENT_ROWS = 15
HUBS_PER_TOPIC = 3
STATUSES = ("active", "superseded", "merged")
NON_ARTICLES = {"index.md", "log.md", "_index.md"}

FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LINK_RE = re.compile(r"\[\[([^\]|#\\]+)(?:#[^\]|]*)?(?:\\?\|[^\]]*)?\]\]")


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def today():
    return dt.date.today()


def to_date(v):
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v).strip().strip('"'))
    except Exception:
        return None


# ---- article model ----------------------------------------------------------
class Article:
    def __init__(self, path):
        self.path = path
        self.rel = os.path.relpath(path, WIKI)
        self.topic = self.rel.split(os.sep)[0] if os.sep in self.rel else ""
        self.basename = nfc(os.path.splitext(os.path.basename(path))[0])
        with open(path, encoding="utf-8") as fh:
            self.text = fh.read()
        m = FM_RE.match(self.text)
        self.fm_raw = m.group(1) if m else ""
        self.body = self.text[m.end():] if m else self.text
        try:
            self.fm = yaml.safe_load(self.fm_raw) or {} if m else {}
            self.fm_ok = bool(m)
        except yaml.YAMLError:
            self.fm, self.fm_ok = {}, False
        fm = self.fm
        self.title = nfc(str(fm.get("title") or self.basename))
        self.aliases = [nfc(str(a)) for a in (fm.get("aliases") or [])]
        self.summary = str(fm.get("summary") or "")
        self.catalog = str(fm.get("catalog") or "")
        self.type = fm.get("type") or ("paper" if fm.get("authors") else "concept")
        self.status = fm.get("status") or "active"
        self.archived = fm.get("archived") is True
        self.updated = to_date(fm.get("updated"))
        self.created = to_date(fm.get("created"))
        self.review_by = to_date(fm.get("review_by"))
        self.superseded_by = fm.get("superseded_by")
        self.sources = [s for s in (fm.get("sources") or []) if "raw/" in str(s)]
        self.open_questions = fm.get("open_questions") is True
        self.has_conflict = "> [!conflict]" in self.body
        self.body_tokens = len(self.body) // 4
        self.links = {nfc(l.strip()) for l in LINK_RE.findall(self.body)}

    @property
    def link(self):
        if nfc(self.title) == self.basename:
            return f"[[{self.basename}]]"
        return f"[[{self.basename}|{self.title}]]"

    def half_life(self):
        if self.archived or self.status != "active":
            return None
        if self.topic in TOPIC_HALF_LIFE_DAYS:
            return int(TOPIC_HALF_LIFE_DAYS[self.topic])
        days = HALF_LIFE_DAYS.get(self.type)
        return int(days) if days else None


def load_articles():
    out = []
    for root, dirs, files in os.walk(WIKI):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".md") and f not in NON_ARTICLES and not (root == WIKI and f in NON_ARTICLES):
                out.append(Article(os.path.join(root, f)))
    out.sort(key=lambda a: (a.topic, a.basename.lower()))
    return out


def resolver(articles):
    """Map lowercase NFC title/basename/alias -> Article."""
    idx = {}
    for a in articles:
        for k in [a.basename, a.title, *a.aliases]:
            idx.setdefault(k.lower(), a)
    return idx


def inbound_counts(articles):
    res = resolver(articles)
    counts = collections.Counter()
    for a in articles:
        seen = set()
        for l in a.links:
            if l.startswith("raw/"):
                continue
            tgt = res.get(l.split("/")[-1].lower()) or res.get(l.lower())
            if tgt is not None and tgt is not a and tgt.rel not in seen:
                seen.add(tgt.rel)
                counts[tgt.rel] += 1
    return counts


# ---- frontmatter line editing (never round-trips YAML) ----------------------
def yaml_quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def set_fm_key(text, key, value_literal):
    """Set a top-level single-line key. Inserts before closing --- if absent."""
    m = FM_RE.match(text)
    if not m:
        raise ValueError("no frontmatter")
    lines = m.group(1).split("\n")
    pat = re.compile(rf"^{re.escape(key)}:(\s|$)")
    for i, ln in enumerate(lines):
        if pat.match(ln):
            # refuse to clobber a block value
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if ln.rstrip().endswith(":") and nxt.startswith((" ", "-")):
                raise ValueError(f"{key} is a block value")
            lines[i] = f"{key}: {value_literal}"
            break
    else:
        # keep catalog next to summary; lifecycle keys after `updated`
        anchor = "summary" if key == "catalog" else "updated"
        pos = len(lines)
        for i, ln in enumerate(lines):
            if ln.startswith(anchor + ":"):
                pos = i + 1
                while pos < len(lines) and lines[pos].startswith((" ", "-")):
                    pos += 1
                break
        lines.insert(pos, f"{key}: {value_literal}")
    new_fm = "\n".join(lines)
    yaml.safe_load(new_fm)  # verify before writing
    return "---\n" + new_fm + "\n---\n" + text[m.end():]


def write_if_changed(a, new_text):
    if new_text != a.text:
        with open(a.path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        a.text = new_text
        return True
    return False


# ---- subcommands ------------------------------------------------------------
def cmd_lifecycle(_):
    changed = 0
    for a in load_articles():
        t = a.text
        if "status" not in a.fm:
            t = set_fm_key(t, "status", "active")
        hl = a.half_life()
        if hl and a.updated:
            want = a.updated + dt.timedelta(days=hl)
            if a.review_by is None or a.review_by < want:
                t = set_fm_key(t, "review_by", want.isoformat())
        changed += write_if_changed(a, t)
    print(f"lifecycle: {changed} files updated")


def cmd_set_catalog(args):
    with open(args.file, encoding="utf-8") as fh:
        data = json.load(fh)
    by_rel = {nfc(a.rel): a for a in load_articles()}
    n, missing = 0, []
    for rel, text in data.items():
        a = by_rel.get(nfc(rel))
        if a is None:
            missing.append(rel)
            continue
        text = " ".join(str(text).split())
        n += write_if_changed(a, set_fm_key(a.text, "catalog", yaml_quote(text)))
    print(f"set-catalog: {n} files updated, {len(missing)} paths not found")
    for m in missing:
        print("  missing:", m)


def fallback_catalog(a):
    s = " ".join(a.summary.split())
    first = re.split(r"(?<=[.!?])\s+", s, maxsplit=1)[0]
    words = first.split()
    return " ".join(words[:25]) + ("…" if len(words) > 25 else "")


def catalog_of(a):
    return " ".join(a.catalog.split()) or fallback_catalog(a)


def read_top_parts():
    """Return (intro paragraph, digests section) preserved from the current index."""
    intro, digests = "", "## Digests\n"
    if os.path.exists(TOP_INDEX):
        t = open(TOP_INDEX, encoding="utf-8").read()
        m = re.search(r"^# .*?\n\n(.*?)\n\n", t, re.S)
        if m and not m.group(1).startswith(("##", ">")):
            intro = m.group(1).strip()
        d = re.search(r"^## Digests\n.*", t, re.S | re.M)
        if d:
            digests = d.group(0).rstrip() + "\n"
    return intro, digests


def render_indexes(articles):
    inbound = inbound_counts(articles)
    by_topic = collections.defaultdict(list)
    for a in articles:
        by_topic[a.topic].append(a)
    files = {}
    rows_total = 0
    for topic, arts in sorted(by_topic.items()):
        active = [a for a in arts if a.status == "active"]
        retired = [a for a in arts if a.status != "active"]
        lines = [
            f"# {topic}",
            "",
            f"{len(active)} active articles. Generated from frontmatter by `prompts/tools/wiki_maint.py index`; "
            "do not hand-edit. Row text is each article's `catalog` field.",
            "",
        ]
        for a in active:
            prefix = "[Archived] " if a.archived else ""
            upd = a.updated.isoformat() if a.updated else "?"
            lines.append(f"- {a.link} - {prefix}{catalog_of(a)} <small>(updated: {upd})</small>")
        rows_total += len(active)
        if retired:
            lines += ["", "## Superseded and merged", "",
                      "Hidden from default queries. Follow the arrow for the current page.", ""]
            for a in retired:
                tgt = str(a.superseded_by or "").strip('"') or "(no target recorded)"
                lines.append(f"- {a.link} ({a.status}) → {tgt}")
        files[os.path.join(WIKI, topic, "_index.md")] = "\n".join(lines) + "\n"

    intro, digests = read_top_parts()
    n_active = sum(1 for a in articles if a.status == "active")
    n_retired = len(articles) - n_active
    top = [
        f"# {POLICY['title']}",
        "",
        intro or "Compounding AI/agents research knowledge base.",
        "",
        "> [!info] How to read this index",
        "> Two-level catalog. This page lists topics. Each topic's `_index` page lists its active articles "
        "with a one-line catalog entry. To find candidates, grep article frontmatter (`title:`, `aliases:`, "
        "`catalog:`, `summary:`) first, then open one or two topic indexes. Generated by "
        "`prompts/tools/wiki_maint.py index`; do not hand-edit above the Digests section.",
        "",
        f"{n_active} active articles across {len(by_topic)} topics; {n_retired} superseded or merged.",
        "",
        "## Topics",
        "",
    ]
    for topic, arts in sorted(by_topic.items()):
        active = [a for a in arts if a.status == "active"]
        hubs = sorted(active, key=lambda a: (-inbound[a.rel], a.basename.lower()))[:HUBS_PER_TOPIC]
        hub_txt = ", ".join(h.link for h in hubs if inbound[h.rel] > 0)
        top.append(f"- [[{topic}/_index|{topic}]] - {len(active)} articles"
                   + (f". Hubs: {hub_txt}" if hub_txt else ""))
    recent = sorted((a for a in articles if a.status == "active" and a.updated),
                    key=lambda a: (a.updated, a.basename), reverse=True)[:RECENT_ROWS]
    top += ["", "## Recently updated", ""]
    for a in recent:
        top.append(f"- {a.link} ({a.topic}, {a.updated.isoformat()}) - {catalog_of(a)}")
    top += ["", digests.rstrip(), ""]
    files[TOP_INDEX] = "\n".join(top)
    return files, rows_total


def cmd_index(args):
    articles = load_articles()
    files, rows = render_indexes(articles)
    stale = []
    for path, content in files.items():
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != content:
            stale.append(os.path.relpath(path, VAULT))
            if not args.check:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)
    # remove per-topic indexes for topics that no longer exist
    live = {os.path.dirname(p) for p in files if p != TOP_INDEX}
    for d in os.listdir(WIKI):
        p = os.path.join(WIKI, d, "_index.md")
        if os.path.isfile(p) and os.path.join(WIKI, d) not in live:
            stale.append(os.path.relpath(p, VAULT))
            if not args.check:
                os.remove(p)
    verb = "would change" if args.check else "rewrote"
    print(f"index: {rows} active rows; {verb} {len(stale)} files")
    for s in stale[:50]:
        print("  ", s)
    if args.check and stale:
        sys.exit(1)


def cmd_check(_):
    articles = load_articles()
    res = resolver(articles)
    problems = []
    for a in articles:
        if not a.fm_ok:
            problems.append(f"{a.rel}: frontmatter does not parse")
            continue
        if a.status not in STATUSES:
            problems.append(f"{a.rel}: status '{a.status}' not in {STATUSES}")
        if "status" not in a.fm:
            problems.append(f"{a.rel}: missing status (run lifecycle)")
        if a.half_life() and a.review_by is None:
            problems.append(f"{a.rel}: missing review_by (run lifecycle)")
        if not a.catalog:
            problems.append(f"{a.rel}: missing catalog (index uses summary fallback)")
        elif len(a.catalog.split()) > CATALOG_MAX_WORDS:
            problems.append(f"{a.rel}: catalog is {len(a.catalog.split())} words (> {CATALOG_MAX_WORDS})")
        if a.status != "active":
            tgt = str(a.superseded_by or "").strip('"')
            name = tgt[2:-2].split("|")[0].split("#")[0] if tgt.startswith("[[") else ""
            if not name or name.lower() not in res:
                problems.append(f"{a.rel}: status {a.status} but superseded_by '{tgt}' does not resolve")
        if a.status == "active" and a.body_tokens > HUB_TOKEN_CAP:
            problems.append(f"{a.rel}: {a.body_tokens} body tokens > cap {HUB_TOKEN_CAP} (split candidate, report only)")
    files, _ = render_indexes(articles)
    for path, content in files.items():
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != content:
            problems.append(f"{os.path.relpath(path, VAULT)}: stale (run index)")
    for p in problems:
        print(p)
    print(f"check: {len(problems)} problems")
    sys.exit(1 if problems else 0)


def query_citations(days=180):
    counts = collections.Counter()
    if not os.path.exists(QUERY_LOG):
        return counts, False
    cutoff = today() - dt.timedelta(days=days)
    for line in open(QUERY_LOG, encoding="utf-8"):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        d = to_date(rec.get("date"))
        if d and d >= cutoff:
            for c in rec.get("cited", []):
                counts[nfc(c).lower()] += 1
    return counts, True


def cmd_candidates(args):
    articles = load_articles()
    inbound = inbound_counts(articles)
    cites, have_log = query_citations()
    t = today()

    def cited(a):
        return sum(cites.get(k.lower(), 0) for k in {a.basename, a.title})

    active = [a for a in articles if a.status == "active" and not a.archived]
    demote, overdue, soon = [], [], []
    for a in active:
        if not a.review_by:
            continue
        if a.review_by < t:
            if (len(a.sources) <= 1 and inbound[a.rel] <= DEMOTE_MAX_INBOUND
                    and not a.has_conflict and not a.open_questions):
                demote.append(a)
            else:
                overdue.append(a)
        elif a.review_by <= t + dt.timedelta(days=30):
            soon.append(a)
    demote.sort(key=lambda a: (cited(a), inbound[a.rel], a.review_by))
    hubs = sorted((a for a in active if a.body_tokens > HUB_TOKEN_CAP), key=lambda a: -a.body_tokens)
    orphans = [a for a in active if inbound[a.rel] == 0]
    fast = sorted((a for a in active if a.topic in TOPIC_HALF_LIFE_DAYS), key=lambda a: (a.topic, a.basename.lower()))

    def row(a, extra=""):
        return {"path": a.rel, "title": a.title, "type": a.type, "updated": str(a.updated),
                "review_by": str(a.review_by), "sources": len(a.sources), "inbound": inbound[a.rel],
                "cited_180d": cited(a), "body_tokens": a.body_tokens, "catalog": catalog_of(a), "note": extra}

    out = {
        "date": t.isoformat(),
        "query_log_present": have_log,
        "demotion": [row(a) for a in demote],
        "overdue_review": [row(a, "overdue but fails demotion criteria (multi-source, linked, or has conflict/question)") for a in overdue],
        "review_due_30d": [row(a) for a in soon],
        "hubs_over_cap": [row(a) for a in hubs],
        "orphans": [row(a) for a in orphans],
        "fast_decay_topics": [row(a) for a in fast],
    }
    if args.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return
    for k, v in out.items():
        if isinstance(v, list):
            print(f"\n## {k} ({len(v)})")
            for r in v:
                print(f"- {r['title']} | {r['path']} | upd {r['updated']} | review {r['review_by']} | "
                      f"src {r['sources']} | in {r['inbound']} | cited {r['cited_180d']} | tok {r['body_tokens']}")
        else:
            print(f"{k}: {v}")


def cmd_due(_):
    log = open(LOG, encoding="utf-8").read() if os.path.exists(LOG) else ""
    dates = re.findall(r"^## \[(\d{4}-\d{2}-\d{2})\] consolidate", log, re.M)
    last = to_date(dates[-1]) if dates else None
    arts = load_articles()
    if last is None:
        print("consolidation: due (never run)")
        return
    new = sum(1 for a in arts if a.created and a.created > last)
    days = (today() - last).days
    due = new >= CONSOLIDATE_EVERY_ARTICLES or days >= CONSOLIDATE_EVERY_DAYS
    print(f"consolidation: {'DUE' if due else 'not due'} - last {last}, {days} days ago, "
          f"{new} articles created since (thresholds {CONSOLIDATE_EVERY_ARTICLES} articles / {CONSOLIDATE_EVERY_DAYS} days)")


def cmd_log_query(args):
    rec = {"date": today().isoformat(), "question": args.question, "cited": args.cited}
    with open(QUERY_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"logged {len(args.cited)} citations")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lifecycle").set_defaults(fn=cmd_lifecycle)
    s = sub.add_parser("set-catalog"); s.add_argument("file"); s.set_defaults(fn=cmd_set_catalog)
    s = sub.add_parser("index"); s.add_argument("--check", action="store_true"); s.set_defaults(fn=cmd_index)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    s = sub.add_parser("candidates"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_candidates)
    sub.add_parser("due").set_defaults(fn=cmd_due)
    s = sub.add_parser("log-query"); s.add_argument("--question", required=True)
    s.add_argument("--cited", nargs="+", required=True); s.set_defaults(fn=cmd_log_query)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
