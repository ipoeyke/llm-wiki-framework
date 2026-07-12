# LLM Wiki Framework

An Obsidian-native implementation of Karpathy's LLM Wiki pattern: you collect raw sources in an Obsidian vault, an LLM agent compiles and maintains a cross-referenced wiki on top of them. Generalizes across domains (personal research, coursework, internal project knowledge) via a per-vault config file rather than code changes.

Packaged as a Claude Code plugin: a skill plus `/wiki:*` slash commands and a deterministic init shortcut for power users.

## What you get

Six operations, all running locally:

| Operation | What it does |
|---|---|
| **Init** | Scaffold a vault: `raw/`, `wiki/`, `wiki/digests/`, `prompts/`, plus `wiki.config.md`, a Bases-backed index, and Obsidian defaults that keep `raw/` and the index/log plumbing out of the graph view. |
| **Ingest** | Add a single source (URL, file, pasted text, Web Clipper output, MCP-sourced content) — fetches, normalizes into `raw/<topic>/YYYY-MM-DD-<slug>.md`, then compiles into wiki articles with cascade updates. |
| **Sync** | Batch-process all new `raw/` sources since the last sync, consolidating cascade updates. |
| **Query** | Answer from the wiki, grounded in wiki articles (never silently from training priors). Optionally archive the answer as a new article. |
| **Lint** | Auto-fix deterministic issues (index drift, dead wikilinks with one match, missing frontmatter defaults, `open_questions` flag drift). Report heuristic findings (contradictions, orphans, thin pages) — never silently rewrite. |
| **Digest** | Render the period's activity as a self-contained HTML recap with `obsidian://` deep-links back to articles. |

Three flavors, kept deliberately tight:

- **`research`** — personal research wikis (NLP papers, blog posts, etc.). Page types: `concept`, `paper`, `open-question`, `hypothesis`.
- **`course`** — coursework second brains. Page types: `topic`, `definition`, `worked-example`, `problem-set`. Topics are subject-matter, never weeks or lecture numbers.
- **`domain`** — generalist bucket for anything else (internal project wikis, hobby knowledge bases, encyclopedic notes). Page types: `concept`, `overview`, `comparison`. Extend in `wiki.config.md`.

## Install

### Hard dependency: kepano/obsidian-skills

Install [`kepano/obsidian-skills`](https://github.com/kepano/obsidian-skills) **first** — it provides the four sub-skills this framework delegates to:

- `obsidian-markdown` — wikilinks, callouts, frontmatter, embeds, block references
- `obsidian-bases` — Bases authoring
- `json-canvas` — `.canvas` authoring (on explicit user request only)
- `defuddle` — clean web extraction during Ingest

Without it, Obsidian-flavored output will be malformed.

Recommended (Claude Code plugin):

```
/plugin marketplace add kepano/obsidian-skills
/plugin install obsidian@obsidian-skills
```

Or install manually into `~/.claude/skills/` (or wherever your Claude Code skills live).

### Plugin

```
/plugin marketplace add ipoeyke/llm-wiki-framework
/plugin install wiki@llm-wiki-framework
```

You get `/wiki:init`, `/wiki:ingest`, `/wiki:sync`, `/wiki:query`, `/wiki:lint`, `/wiki:digest`, and the `init_wiki.sh` scaffolding script.

## Quickstart

```sh
# 1. cd into the directory you want as your Obsidian vault root
cd ~/Obsidian/my-wiki

# 2. initialize — either via the agent (asks for audience/purpose interactively)…
#    /wiki:init course "Information Security"
#
#    …or via the bash shortcut (fills audience/purpose with placeholders):
init_wiki.sh --flavor course --title "Information Security"

# 3. edit wiki.config.md to fill in audience and purpose

# 4. open the directory in Obsidian.app

# 5. ingest your first source
#    /wiki:ingest https://en.wikipedia.org/wiki/RSA_(cryptosystem)
#    or use Obsidian Web Clipper to clip LMS pages, then:
#    /wiki:sync
```

## Layout

```
llm-wiki-framework/
├── README.md                  (this file)
├── LICENSE                    (MIT)
├── .claude-plugin/
│   ├── plugin.json            (plugin manifest)
│   └── marketplace.json       (single-plugin marketplace)
├── commands/                  (6 slash command registrations)
├── scripts/
│   └── init_wiki.sh           (bash scaffolding shortcut)
└── skills/
    └── llm-wiki/
        ├── SKILL.md
        ├── references/        (templates: raw, article, archive, index, digest HTML, flavor presets, Canvas Web Clipper)
        └── prompts/           (per-operation prompts; ingest has per-flavor variants)
```

A note on the Canvas LMS Web Clipper template at `skills/llm-wiki/references/canvas-web-clipper.json`: it's a best-effort [Obsidian Web Clipper](https://obsidian.md/clipper) template targeting `*.instructure.com/courses/*` URLs. Validate it in the Web Clipper UI on first install — Obsidian Web Clipper's JSON schema isn't publicly documented, so field syntax may need adjustment for your version. The same Web Clipper pattern works for any browser-accessible source behind authentication.

## Design principles

- **Local-first.** No telemetry, no cloud sync, no hosted variant. Only URL ingestion touches the network.
- **`raw/` is immutable.** Source material is never edited in place. Mutable upstream sources (e.g., a Canvas page that gets updated) are handled via a revision protocol (`-revN.md` + `supersedes:`/`superseded_by:` frontmatter pointers), never silent overwrites.
- **Wikilinks inside `wiki/`, always.** Markdown links only for external URLs.
- **Subject-matter topics.** `raw/cryptography/`, never `raw/week-2/`. Survives course re-sequencing; lets one wiki article absorb information from many weeks and content types.
- **Lint discipline.** Deterministic checks auto-fix; heuristic checks report only. The auto-fix list is closed.
- **Personal notes** (`content_type: personal-note`) surface as `> [!question]` callouts, never as cited claims in article bodies.
- **Open questions are queryable.** Any article containing a `> [!question]` callout carries `open_questions: true` frontmatter (Bases can't filter on body content), powering the index's "Open questions" view. Lint keeps flag and callouts in sync deterministically.
- **Digest HTML is self-contained.** No CDN, no remote fonts, no analytics, no tracking pixels. Article links use the `obsidian://` URI scheme.
- **Obsidian Canvas (`.canvas`) is supported but de-emphasized.** Generated only on explicit user request — auto-generated canvases tend to go stale.

## Roadmap and non-goals

Out of v1, explicitly: multi-wiki (`WIKI_ROOT`), embedded vector retrieval, journal/CRM modules, a hosted/MCP variant, bundled Canvas LMS API clients, additional flavors beyond the three above.

## License

MIT. See [`LICENSE`](LICENSE).
