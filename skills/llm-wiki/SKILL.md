---
name: llm-wiki
description: Maintains a compounding, cross-referenced Obsidian wiki on top of a raw/ source archive. Use when the user wants to initialize a wiki vault, ingest sources, sync clippings, query their wiki, lint it, or produce a weekly digest. Triggers on phrases like "initialize this vault as a wiki", "ingest this URL", "what do I know about X from my wiki", "lint the wiki", "weekly digest".
license: MIT
disable-model-invocation: true
metadata:
  version: 0.1.0
---

# LLM Wiki

An Obsidian-native LLM Wiki: the human collects raw sources in an Obsidian vault, you (the agent) maintain a compounding, cross-referenced wiki on top of them.

Three layers inside one vault:

1. **`raw/`** — immutable source material. Never edited, never normalized, never typo-fixed. This is the audit trail.
2. **`wiki/`** — your compiled knowledge: Obsidian-flavored Markdown with wikilinks, callouts, frontmatter, and a Bases index.
3. **schema** — this skill plus per-vault `wiki.config.md` (purpose, audience, flavor, style rules).

## Hard dependency: kepano/obsidian-skills

This skill **requires** [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) to be installed in the same skills directory. Without it, Obsidian-flavored output will be malformed.

Delegate to its sub-skills explicitly when the relevant artifact is being authored:

| Sub-skill | Use it for |
|---|---|
| `obsidian-markdown` | wikilinks, callouts, frontmatter, embeds, block references — every `wiki/*.md` write |
| `obsidian-bases` | `wiki/index.base` and any `wiki/<topic>/<topic>.base` authoring |
| `json-canvas` | `wiki/canvas/*.canvas` authoring (on explicit user request only) |
| `defuddle` | cleaning web pages during Ingest (Step 1: Fetch) |

There is no programmatic dependency mechanism. Installation is the user's responsibility — document it in setup, don't try to enforce it.

Install via the Claude Code plugin marketplace (recommended):

```
/plugin marketplace add kepano/obsidian-skills
/plugin install obsidian@obsidian-skills
```

Or install manually at `~/.claude/skills/` (or wherever your Claude Code skills live) before using this framework.

## Vault layout

```
<obsidian-vault>/
├── wiki.config.md
├── raw/
│   └── <topic>/
│       └── YYYY-MM-DD-source-slug.md
├── wiki/
│   ├── index.md                        (topic level, script-generated)
│   ├── index.base
│   ├── log.md
│   ├── <topic>/
│   │   ├── _index.md                   (article level, script-generated)
│   │   ├── <article>.md
│   │   └── <topic>.base               (optional, per-topic view)
│   └── canvas/                         (Obsidian Canvas / .canvas files)
│       └── <topic>-map.canvas         (on explicit request only)
├── digests/
│   └── YYYY-Www-recap.html
├── reports/
│   └── consolidation-YYYY-MM-DD.md     (record of each consolidation pass)
├── .query-log.jsonl                    (pages cited per query)
└── prompts/
    ├── ingest.md
    ├── sync.md
    ├── query.md
    ├── lint.md
    ├── digest.md
    ├── consolidate.md
    └── tools/
        └── wiki_maint.py               (copied from scripts/ at init)
```

Per-vault prompts under `prompts/` override the skill's defaults at `prompts/`. Read both; the vault wins on conflict.

## Operations

Seven operations. Each has a dedicated prompt file. Read the relevant prompt **before** acting on a trigger.

### Execution: delegate the heavy operations to a subagent

**Ingest, Sync, Lint, Digest, and Consolidate are compile-heavy** — they read many sources (often large PDFs and web pages), write and cascade-update many `wiki/` files, and produce large tool outputs. Running them inline burns the main agent's context on material the user never needs to see. **Do not perform these operations inline. Spawn a subagent (Agent tool, `general-purpose`) to do the work, and relay its compact report.** Run several in parallel (one Agent call per source) when ingesting a batch of independent sources.

- **Delegate:** Ingest, Sync, Lint, Digest, Consolidate.
- **Keep on the main thread:** Init (interactive — batched question + confirmation before writing) and Query (the answer is the deliverable the user reads now).

When you delegate, give the subagent everything it needs to run autonomously and match the vault, and require it to self-verify and report compactly. The subagent prompt MUST include:

1. **Vault path** and today's date (for `collected`); the source(s) to process.
2. **Read-first instructions:** `wiki.config.md` (flavor + Custom rules — especially the YAML colon-quoting rule and the flavor's page types), the relevant operation prompt (per-vault `prompts/<op>.md` override wins over the skill default at the same path), and 1-2 existing articles to match voice/structure.
3. The **binary-source policy** for PDFs/images/audio (store the original + a text sidecar as source of truth, with a `binary:` frontmatter pointer), and the operation's **file-write contract** (what it may and may not touch — never `wiki.config.md`, `index.base`, other `raw/` files, or archived, superseded or merged articles).
4. **Cross-linking + cascade** expectations: link aggressively to existing articles, add reciprocal See-also links and bump `updated:` on cascade-touched pages, link the first plain-text mention of each new page in older articles (Sync step 4a, Lint check 9), write `catalog` and `status` on new articles, regenerate indexes with `prompts/tools/wiki_maint.py lifecycle`, `index` and `check` (never hand-edit index rows), and append one consolidated `wiki/log.md` entry.
5. A **self-verification** step before it reports: every `[[wikilink]]` resolves to an existing article title or `raw/` path (0 broken), every new article's frontmatter parses, and each binary source has both its original and sidecar. Fix issues before returning.
6. A request for a **compact report** (per source: title, topic, article path, one-line thesis, strongest cross-links; plus counts and any failures) — not a file dump.

The main agent stays responsible for the outcome: after the subagent returns, independently spot-check link/YAML integrity before telling the user it is done.

### Init

Triggers: `/wiki:init`, "initialize this vault as a wiki", "start a new wiki".

Init is a one-time bootstrap, not a recurring operation, so its full agentic flow lives here in SKILL.md rather than a per-flavor prompt.

**Inputs:**
- Required: `flavor` (`research` | `course` | `domain`), `title`.
- Optional (default to flavor-template values): `audience`, `purpose`.
- Implicit: vault path = current working directory (or vault root if `.obsidian/` is found nearby).

**Interaction:**
1. Check for existing structure. If `wiki.config.md` already exists, treat as idempotent: only create missing pieces; never overwrite.
2. If any required field is missing, ask **all of them in a single batched prompt**. Do not ask sequentially.
3. Echo the final config (flavor, title, audience, purpose, digest cadence) and ask for confirmation before writing.
4. After confirmation:
   - Create directories: `raw/`, `wiki/`, `digests/`, `prompts/`. Touch `.gitkeep` in empty leaves.
   - Write `wiki.config.md` from `references/wiki-config-template.md`, substituting placeholders. Inject defaults from `references/flavor-presets/<flavor>.md`.
   - Write `wiki/index.md` from `references/index-template.md` (empty heading shape). From the first compile on, `wiki_maint.py index` regenerates it.
   - Write `wiki/index.base` from `references/index-base-template.base` (nine default views — delegate Bases syntax to `obsidian-bases`).
   - Touch `wiki/log.md`.
   - Copy the chosen flavor's ingest prompt to vault: `prompts/ingest/<flavor>.md` → `prompts/ingest.md`. Copy flat `prompts/{sync,query,lint,digest,consolidate}.md` as-is.
   - Copy `scripts/wiki_maint.py` to `prompts/tools/wiki_maint.py`. It needs Python 3 with PyYAML.
   - Write `.obsidian/app.json` with `userIgnoreFilters: ["raw/", "prompts/", "digests/", "reports/", "wiki.config.md", "wiki/index.md", "wiki/log.md", "/\\.base$/", "/_index\\.md$/"]` so that only compiled wiki articles appear in Obsidian's graph view and link suggestions — everything else (sources, operation prompts, digests, consolidation reports, config, indexes, log, and Bases files) is plumbing. If `.obsidian/app.json` already exists, merge these entries into any existing `userIgnoreFilters` array instead of overwriting the file — it holds other user settings.
   - Append init entry to `wiki/log.md`:
     ```
     ## [YYYY-MM-DD] init | <flavor> | <title>
     ```

### Ingest

Triggers: "ingest this", "add to wiki", "ingest <url>", a URL or file mentioned with intent to add.

Read `prompts/ingest/<flavor>.md` (where flavor comes from `wiki.config.md`).

### Sync

Triggers: "sync the wiki", "process my inbox", "catch up", scheduled run.

Read `prompts/sync.md`.

### Query

Triggers: "what do I know about X?", "summarize my notes on Y", "compare A and B from my wiki", any question in a vault initialized as an LLM wiki.

Read `prompts/query.md`.

### Lint

Triggers: "lint the wiki", "health check", "wiki quality pass", scheduled run.

Read `prompts/lint.md`.

### Digest

Triggers: "weekly digest", "what's new in my wiki", scheduled run (cadence from `wiki.config.md`; default weekly).

Read `prompts/digest.md`.

### Consolidate

Triggers: `/wiki:consolidate`, "consolidate the wiki", "prune the wiki"; Sync starts it when `wiki_maint.py due` says it is due.

Read `prompts/consolidate.md`. The pass runs without user approval: back up, apply the changes the evidence supports, verify, and write a report that records what changed.

## Universal rules

These apply to every operation. Do not relax them per-flavor.

- **Wikilinks inside `wiki/`, always.** `[[Article]]`, `[[Article|display]]`, `[[Article#Heading]]`. Markdown links only for external URLs.
- **From `wiki/` to `raw/`:** wikilinks too — the raw files are in the vault: `[[raw/<topic>/<file>]]`.
- **`raw/` is immutable.** No rewrites, no typo fixes, no normalization beyond the framework's stated frontmatter writes. When an upstream source changes, write a `-revN.md` revision and add `supersedes:` / `superseded_by:` frontmatter pointers. Never edit in place.
- **`personal-note` content_type** (user-authored reflections, questions, hypotheses) surfaces as `> [!question]` callouts in article bodies. **Never cite a personal-note as if it were external evidence.**
- **Topic directories are subject-matter, never weeks, lecture numbers, content types, or course phases.** `raw/cryptography/`, not `raw/week-2/` or `raw/lectures/`. Enforce in every flavor's Ingest topic-selection step.
- **Lint never silently rewrites article content based on a heuristic.** Deterministic checks (index drift, dead wikilinks with exactly-one-match resolution, missing frontmatter defaults) auto-fix. Heuristic checks (contradictions, orphans, thin pages, missing cross-refs) report only.
- **Digest HTML is self-contained.** No CDN scripts, no remote fonts, no analytics, no tracking pixels. Vanilla CSS only.
- **Obsidian Canvas (`.canvas`) files are never auto-generated.** Only on explicit user request.
- **`raw/` topics ≡ `wiki/` topics.** Reuse rather than fragment. Never create a new topic when an existing one fits.
- **Secondary characterizations are claims to verify, not facts to transcribe.** When a `raw/` source carries both primary material and a secondary characterization of it — a quoted blurb, a third-party summary, someone's framing of what a paper or announcement said — treat the secondary as a claim. If it diverges from the primary on a fact or number, prefer the primary and cite the primary's value; render a two-sourced numeric disagreement as `> [!conflict]` and an overstatement, omission, or misframing as `> [!warning]`, attributing each side. Never promote the secondary's number into the article's asserted fact. (A `## Compile hints` discrepancy note in the raw source is a signal to do this, not a substitute for checking.)
- **`open_questions` frontmatter tracks `> [!question]` callouts.** Whenever you write or update an article, set `open_questions: true` if the body contains at least one `> [!question]` callout, and remove the flag (or set `false`) when the last question is resolved. Bases cannot filter on body content, so this flag is what powers the index's "Open questions" view — an article with a question callout but no flag is invisible to it.
- **Lifecycle and growth: retire pages, never delete them.** `raw/` is the retention layer and is never pruned; `wiki/` is the consolidation layer. Policy (half-lives, size cap, cadence) lives in the `lifecycle:` block of `wiki.config.md` frontmatter, with per-flavor defaults in `scripts/wiki_maint.py`.
  - Every article carries `catalog:` (one double-quoted sentence, at most 25 words; its row text in the topic index), `status:` (`active`, `superseded` or `merged`), and, for types or topics with a half-life, `review_by:` (computed by `wiki_maint.py lifecycle` from `updated`; never hand-computed, and the script never shortens a later hand-set date). Non-active pages carry `superseded_by:`; the newer page carries `supersedes:`.
  - Superseded and merged pages keep their full body plus one `> [!warning]` line naming the replacement. They are hidden from topic indexes and default queries and are never cascade-updated.
  - **Write-time admission:** before creating a page, decide new page, update-only or merge-only. No standalone substance means merge into the parent, not a new page.
  - **Indexes are generated.** `wiki/index.md` (topics, hubs, recent updates) and `wiki/<topic>/_index.md` (one catalog row per active article) come from `wiki_maint.py index`. Only the Digests section of `wiki/index.md` is hand-edited.
  - **Only Consolidate retires or restructures pages.** Merges, splits of pages over the size cap, demotions and supersessions of existing pages happen only in the Consolidate pass, which runs without user approval, backs up `wiki/` first, and writes a report recording what it changed. Sync and Ingest never retire a page: for a direct successor they leave the predecessor active, link it to the new page, and log a `Supersession candidate:` line for the next pass.

## Callouts (standardized vocabulary)

Use only these native Obsidian callout types — no plugins required:

| Callout | Use |
|---|---|
| `> [!summary]` | Top-of-article one-paragraph summary block |
| `> [!conflict]` | Sources disagree on a claim — attribute both, do not silently pick |
| `> [!source]` | Inline attribution for a specific claim |
| `> [!question]` | Open question flagged for future ingestion; also wraps personal-note content |
| `> [!warning]` | Stale or outdated content flagged by lint |
| `> [!quote]` | Direct quotes from sources |

## References & templates

All under `references/`:

| File | Purpose |
|---|---|
| `raw-template.md` | Frontmatter + body shape for files in `raw/` |
| `article-template.md` | Frontmatter + body shape for `wiki/` articles, with callout slots |
| `archive-template.md` | Variant for query-archived pages (`archived: true`) |
| `index-template.md` | Structure for `wiki/index.md` |
| `index-base-template.base` | Default Bases views for `wiki/index.base` |
| `digest-template.html` | Self-contained HTML template for weekly recaps |
| `wiki-config-template.md` | `wiki.config.md` skeleton with `{{placeholder}}` slots and the `lifecycle:` policy block |
| `canvas-web-clipper.json` | Obsidian Web Clipper template for Instructure Canvas LMS (best-effort, validate in Web Clipper UI on first install) |
| `flavor-presets/research.md` | Page types + style for personal research wikis |
| `flavor-presets/course.md` | Page types + style for coursework wikis |
| `flavor-presets/domain.md` | Page types + style for generalist/encyclopedic wikis |

And operation prompts under `prompts/`:

```
prompts/
├── ingest/
│   ├── research.md
│   ├── course.md
│   └── domain.md
├── sync.md
├── query.md
├── lint.md
├── digest.md
└── consolidate.md
```

And the maintenance script at `scripts/wiki_maint.py` (copied into each vault at `prompts/tools/`): `lifecycle`, `index [--check]`, `check`, `candidates [--json]`, `due`, `log-query`, `set-catalog`.

No `init.md` prompt — Init's flow is above, in this file.
