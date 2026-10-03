# LLM Wiki Framework

An Obsidian-native implementation of Karpathy's LLM Wiki pattern: you collect raw sources in an Obsidian vault, an LLM agent compiles and maintains a cross-referenced wiki on top of them. Generalizes across domains (personal research, coursework, internal project knowledge) via a per-vault config file rather than code changes.

Packaged as a Claude Code plugin: a skill plus `/wiki:*` slash commands and a deterministic init shortcut for power users.

## What you get

Seven operations, all running locally:

| Operation | What it does |
|---|---|
| **Init** | Scaffold a vault: `raw/`, `wiki/`, `digests/`, `prompts/`, plus `wiki.config.md`, a Bases-backed index, and Obsidian defaults so only compiled wiki articles appear in the graph view (sources, prompts, digests, config, index, log, and `.base` files are all excluded). |
| **Ingest** | Add a single source (URL, file, pasted text, Web Clipper output, MCP-sourced content) — fetches, normalizes into `raw/<topic>/YYYY-MM-DD-<slug>.md`, then compiles into wiki articles with cascade updates. |
| **Sync** | Batch-process all new `raw/` sources since the last sync, consolidating cascade updates. |
| **Query** | Answer from the wiki, grounded in wiki articles (never silently from training priors). Optionally archive the answer as a new article. |
| **Lint** | Auto-fix deterministic issues (index drift, dead wikilinks with one match, missing frontmatter defaults, `open_questions` flag drift, unquoted YAML colons, unlinked first mentions of new pages). Report heuristic findings (contradictions, orphans, thin pages) — never silently rewrite. |
| **Digest** | Render the period's activity as a self-contained HTML recap with `obsidian://` deep-links back to articles. |
| **Consolidate** | Keep the wiki bounded: merge, split oversized pages, supersede and link orphans on its own, backing up first and writing a report that records each change. Sync starts it when it is due. |

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

You get `/wiki:init`, `/wiki:ingest`, `/wiki:sync`, `/wiki:query`, `/wiki:lint`, `/wiki:digest`, `/wiki:consolidate`, the `init_wiki.sh` scaffolding script, and the `wiki_maint.py` maintenance script (Python 3 with PyYAML).

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
├── commands/                  (7 slash command registrations)
├── scripts/
│   └── init_wiki.sh           (bash scaffolding shortcut)
└── skills/
    └── llm-wiki/
        ├── SKILL.md
        ├── scripts/           (wiki_maint.py: lifecycle dates, generated indexes, checks, consolidation candidates)
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
- **Bounded growth without deletion.** Articles carry `catalog`, `status` and `review_by` frontmatter. Pages retire as `superseded` or `merged` instead of being deleted, and default queries read active pages only. Half-lives, the size cap and the consolidation cadence live in the `lifecycle:` block of `wiki.config.md`.
- **Generated two-level index.** `wiki/index.md` lists topics; `wiki/<topic>/_index.md` lists articles, one catalog line each. Both are regenerated from frontmatter, so queries read a small index and grep frontmatter instead of one ever-growing file.
- **Digest HTML is self-contained.** No CDN, no remote fonts, no analytics, no tracking pixels. Article links use the `obsidian://` URI scheme.
- **Obsidian Canvas (`.canvas`) is supported but de-emphasized.** Generated only on explicit user request — auto-generated canvases tend to go stale.

## Design notes: lifecycle, two-level index and consolidate

The lifecycle fields, the generated two-level index, grep-first query and the Consolidate operation were added on 2026-09-28. They were first built in a personal AI-research vault, then moved into the framework with the vault-specific wording removed.

### How the decisions were made

1. **Problem.** The research vault had grown to 711 articles and 1.2M words with no way to retire pages. Measurements from that vault:
   - Query read the whole flat `wiki/index.md` (711 rows, 357 KB, about 89k tokens) on every call.
   - 338 of 413 paper pages had a single source, and 192 had never been touched after creation.
   - The three largest hubs had 112 to 121 inbound links, and the largest page was 7,111 words.
   - Stale model-release facts sat next to current ones with equal weight.
2. **Research.** A survey of agent-memory papers, agent-memory products, LLM-wiki guides and Wikipedia's editorial policy (see [References](#references)). The one point every source agreed on: do not prune, change lifecycle state, and retrieve only active items.
3. **Index check.** The first set of recommendations was tested against the index cost. Only two of them shrank `index.md`, and slowly. Row length and the flat structure caused the cost, not page count. That led to the separate index fixes: catalog lines, two levels and grep first.
4. **Ranking.** Index fixes and lifecycle recommendations were merged into one list, ranked by payoff: index cost first, then staleness, then growth. All ten items were approved and applied together.
5. **First pass.** Consolidate ran once on the vault. The report had 49 numbered items, and the user approved them by number. Split proposals were revised after the pages were condensed.
6. **Generalization.** The prompts, skill and script were moved into this repo. Vault-specific rules became config: the vault's model-release rule became `topic_half_life_days` and the `fast_decay_topics` candidate group.

### Decisions and their sources

| Decision | Rationale | Source |
|---|---|---|
| **One-sentence `catalog` line (at most 25 words)** as the index row, separate from the longer `summary` | Rows had become 60 to 100 word summaries, which made the index a retrieval document instead of a catalog. Catalog lines cut the index about 4x at the same row count. | Infini Memory routes on one-line per-document summaries and reads content only for candidates |
| **Generated two-level index**: `wiki/index.md` lists topics and hubs, and `wiki/<topic>/_index.md` lists articles | Query reads a small top file plus one or two topic files instead of the whole catalog. The per-query read dropped from about 89k to about 2k tokens plus the topic files. The script generates both levels from frontmatter, so they cannot drift. | Infini Memory (hierarchical routing) |
| **Grep before read** in Query: grep `title`, `aliases`, `catalog`, `summary` across `wiki/**`, then use the index only to scope topics | Summary-only routing is weak. Pairing a catalog with lexical search over content is much stronger, so the catalog stays short and grep does the work. | Infini Memory ablation: summary-only routing 41.7% vs summary plus lexical search 76.0%; its agentic reader (`list_docs`, `grep`, `read_lines`). Letta's memory filesystem uses the same pattern. |
| **Lifecycle frontmatter, never delete**: `status: active \| superseded \| merged`, `superseded_by`, `review_by` | Retrieval runs over active pages, and history stays reachable through `superseded_by` links. The existing `archived: true` already means "query-archive page", so retirement needed its own field. | MemoryLACE (active/inactive plus merge, supersession and contradiction links; linked merge beat compact merge by 1.43pp); MemStrata (`valid_from`/`valid_to`/`superseded_by`, stale-fact error near 0% vs 15-40% for naive RAG) |
| **`raw/` is never pruned; only `wiki/` consolidates** | Compress state, not evidence. `raw/` is the retention layer with a loose budget, and `wiki/` is the consolidation layer with a tight budget. | MemStrata lossy ablation (static recall fell 0.82 to 0.62); Retain or Consolidate? (consolidation wins by up to 48pp under tight budgets, retention wins under loose ones) |
| **Type- and topic-conditioned half-lives** written to `review_by` (research flavor: paper 180 days; concepts never expire; `topic_half_life_days` for fast-moving topics) | Content types go stale at different rates, so one decay rate fails. Expiry triggers a review, not a silent drop. | Scrub Jay paper (removing type-conditioned decay cut the gain 5.7x); Mem0 2026 review (decay handles low-relevance items, not stale high-confidence facts, so supersession must be explicit) |
| **Write-time admission** in Sync and Ingest: decide new page, update or merge-only before creating a page | Stop low-value pages at write time instead of filtering them at read time. A source without standalone notability folds into its parent. | Dual-Layer Agentic Memory (routes each write to skip, new or update; pruned up to 68% of redundant writes and kept 98.3% of accuracy); Wikipedia: Notability |
| **Demotion rule**: a paper page past `review_by`, single-source, with 2 or fewer inbound links and no open conflict or question, is merged into its parent as a dated subsection. The page is kept as `status: merged`. | Merge verifiable content into the parent instead of deleting it. Old wikilinks keep resolving. | Wikipedia: Delete or merge; MemStrata; Retain or Consolidate? |
| **Hub cap of about 5,000 tokens** (`hub_token_cap`). Split by `##` section into child pages, and the parent keeps a short summary and links. Moved text is carried verbatim. | Oversized pages absorb unrelated subtopics and routing degrades. | Infini Memory (split over 5,000 tokens, merge under 1,000; disabling this maintenance cost 6.7pp, and raising the split threshold to 9,000 cost 6.3pp) |
| **Scheduled pass that applies its own changes**: back up, apply what the evidence supports, verify, and write a report recording each change. Due every 90 days or 100 new articles; Sync starts it when due. Sync and Ingest only log successor pairs as candidates, so one pass owns every status change. | Retirement keeps the full body and backups are taken first, so every change is reversible without a review step. An unattended Sync cannot judge whether a predecessor is still in service; the pass reads both pages before retiring one. | Letta dreaming and sleep-time compute (background subagents split and merge, back up before restructuring, optional review before commit); Falconer enterprise LLM-wiki guide (scheduled drift review routed to an owner) |
| **Query citation log** (`.query-log.jsonl`). Pages never cited rank first for demotion. | Usage is a signal of value. Pages that answer questions stay; pages nobody cites are the first to fold. | REALM (reinforce links that supported answers and weaken ones that misled, using local edits only; +7.17pp on LoCoMo) |
| **Deterministic script** (`wiki_maint.py`: `lifecycle`, `index`, `check`, `candidates`, `due`, `log-query`) | Date math, index generation, drift checks and candidate lists are mechanical. The script does them so the LLM only does judgment. | Framework lint rule: deterministic fixes are automatic, heuristic ones are report-only |

Figures are as reported by each source.

### Observed on the first pass

- The pass on the research vault proposed 9 model-release supersessions, 4 orphan fixes, 27 splits and 9 fixes.
- Condensing the split candidates before splitting them brought 17 of 26 pages under the cap. Splits were then proposed only for the rest.
- A few hubs stayed over the cap after their approved splits. The pass stopped there instead of cutting text the report had not proposed.
- Supersession proposals needed a strict successor test: coexisting sizes, tiers and product lines are not successors. That test became part of the `fast_decay_topics` rule.

### References

- Karpathy, [LLM Wiki gist](https://gist.github.com/karpathy/442a6bf6c6ba1a8d7a2d6b8f0c4a5f02), the pattern this framework implements
- [Infini Memory](https://www.alphaxiv.org/abs/2606.10677): one-line routing summaries, grep-based agentic reading, split and merge thresholds
- [MemoryLACE](https://www.alphaxiv.org/abs/2609.03201): active/inactive memories with merge, supersession and contradiction links
- [Temporal Validity in Retrieval Memory (MemStrata)](https://www.alphaxiv.org/abs/2606.26511): bi-temporal ledger and deterministic supersession
- [Retain or Consolidate?](https://www.alphaxiv.org/abs/2607.17545): when consolidation beats retention
- [Dual-Layer Agentic Memory](https://www.alphaxiv.org/abs/2608.22215): write-time admission
- [Scrub Jay Episodic Memory Principles](https://www.alphaxiv.org/abs/2608.04746): type-conditioned decay
- [Retrieval-Driven Memory Reconsolidation (REALM)](https://arxiv.org/abs/2609.16053): usage feedback
- [Letta memory and dreaming docs](https://docs.letta.com/letta-agent/memory) and [Letta sleep-time compute](https://www.letta.com/blog/sleep-time-compute/): background consolidation passes
- [Mem0: State of AI agent memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026): limits of decay for stale facts
- [Falconer: Enterprise LLM wiki guide](https://falconer.com/guides/enterprise-llm-wiki-karpathy/): scheduled drift review
- [Wikipedia: Notability](https://en.wikipedia.org/wiki/Wikipedia:Notability) and [Wikipedia: Delete or merge](https://en.wikipedia.org/wiki/Wikipedia:Delete_or_merge): merge into a parent instead of deleting

## Roadmap and non-goals

Out of v1, explicitly: multi-wiki (`WIKI_ROOT`), embedded vector retrieval, journal/CRM modules, a hosted/MCP variant, bundled Canvas LMS API clients, additional flavors beyond the three above.

## License

MIT. See [`LICENSE`](LICENSE).
