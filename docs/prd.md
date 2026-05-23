# LLM Wiki Framework — Product Requirements Document

**Version:** 0.1 (draft for Claude Code to implement)
**Date:** 2026-05-23
**Status:** Feature spec — implementation details deferred to Claude Code

---

## 1. Overview

The LLM Wiki Framework is a generalizable, Obsidian-native implementation of Karpathy's LLM Wiki pattern. The human collects raw sources in an Obsidian vault; an LLM agent maintains a compounding, cross-referenced wiki on top of them. The framework adapts to different domains (personal NLP research, MS CS coursework, an internal project, etc.) via a per-vault configuration file rather than code changes.

### Goals

- Be the cleanest **Obsidian-native** LLM Wiki available. Wikilinks, callouts, frontmatter, Bases, and Obsidian Canvas (the `.canvas` visual-map format, not Instructure Canvas LMS) should feel first-class, not bolted on.
- **Generalize across domains via configuration**, not code. One install. Each vault picks a flavor and customizes its own `wiki.config.md` and prompts.
- Ship as a **portable skill** (agentskills.io standard) plus an **optional Claude Code plugin wrapper** that adds slash commands and scheduling. Skill core works in CC, Cursor, Codex, OpenCode, etc.
- **Maintenance is the LLM's job, not the human's.** The human reads, captures, and asks. The LLM compiles, links, lints, syncs, and digests.

### Non-goals (v1)

- Multi-wiki / `WIKI_ROOT` support. **One vault = one wiki.**
- Journal or CRM extensions (designed-around, but not shipped).
- Bundling Obsidian Web Clipper. We recommend it; we don't ship it.
- Knowledge-graph extraction layer (Vivian/mnemon pattern). Possible v2 module.
- Hosted / MCP variant (Hjarni-style). Local-first only.
- Embeddings or vector retrieval. The wiki itself is the index.

---

## 2. Personas & example domains

- **Researcher** — personal NLP research wiki. Ingests arXiv papers, blog posts, repo READMEs. Wants concept pages, paper pages, open-question tracking.
- **Student** — MS CS coursework second brain. Ingests lecture notes, problem sets, textbook chapters. Wants topic pages, definitions, worked-example links.
- **Builder** — agent/internal project wiki. Ingests Slack threads, design docs, customer calls. Wants entity pages, decision logs, contradiction flags.

Same framework, three `wiki.config.md` files, three flavors.

---

## 3. Architecture

Three layers, all inside a single Obsidian vault.

**Layer 1: `raw/`** — immutable source material. The LLM reads, never modifies. Organized by topic subdirectories. Once a file lands here, it is not edited, not even for typos. This is the audit trail for every claim in the wiki.

**Layer 2: `wiki/`** — LLM-owned compiled knowledge. Obsidian-flavored Markdown. One level of topic subdirectories (`wiki/<topic>/<article>.md`). Special files:
- `wiki/index.md` — single-page TOC, grouped by topic, with summary + last-updated per article.
- `wiki/index.base` — Obsidian Base providing queryable table views.
- `wiki/log.md` — append-only operation log.

**Layer 3: schema** — the skill (this framework) plus per-vault `wiki.config.md`. The skill defines universal workflow rules. The config captures the specific wiki's purpose, audience, page types, style, flavor-specific overrides.

### Folder shape

```
<obsidian-vault>/
├── wiki.config.md
├── raw/
│   └── <topic>/
│       └── YYYY-MM-DD-source-slug.md
├── wiki/
│   ├── index.md
│   ├── index.base
│   ├── log.md
│   ├── <topic>/
│   │   ├── <article>.md
│   │   └── <topic>.base                (optional, per-topic view)
│   ├── digests/
│   │   └── YYYY-Www-recap.html
│   └── canvas/                          (Obsidian Canvas / .canvas files)
│       └── <topic>-map.canvas          (on demand only)
└── prompts/
    ├── ingest.md
    ├── sync.md
    ├── query.md
    ├── lint.md
    └── digest.md
```

The skill itself lives outside the vault, in the agent's skill directory (e.g., `~/.claude/skills/llm-wiki/`). Per-vault prompt customization lives inside the vault at `prompts/`.

---

## 4. Configuration

### `wiki.config.md`

A single markdown file at the vault root. The LLM reads it before every operation.

```yaml
---
title: <human-readable wiki name>
flavor: research | course | domain
audience: <who reads this — informs voice, depth, jargon>
purpose: <one-paragraph statement of what this wiki is for>
digest_cadence: weekly | biweekly | monthly | off
created: <ISO date>
---

## Page types
<which page types this wiki maintains>

## Style rules
<voice, length norms, citation style, what to expand vs. summarize>

## Topic taxonomy (optional, seed only)
<initial topic directories; LLM adds more as it ingests>

## Custom rules
<anything else for this specific wiki>
```

### Flavors

Flavors are presets — sensible defaults for page types, style, and prompts. v1 ships **three**, kept deliberately tight:

| Flavor | Primary page types | Voice | Example use case |
|---|---|---|---|
| `research` | concept, paper, open-question, hypothesis | rigorous, hedged where evidence is thin | personal NLP research wiki |
| `course` | topic, definition, worked-example, problem-set | pedagogical, builds from primitives | MS CS coursework second brain |
| `domain` | concept, overview, comparison | encyclopedic, generalist | catch-all for subject areas not covered by the two above |

`domain` is intentionally the generalist bucket. Anything that isn't clearly a research wiki or a course wiki goes here, with the specifics encoded in `wiki.config.md`. We are **not** shipping `paper`, `product`, `person`, `organization`, `project`, or `custom` flavors in v1 — `domain` plus a customized `wiki.config.md` covers those cases. Adding new flavors later is non-breaking.

Flavors set defaults; `wiki.config.md` always wins.

**Topic-naming convention (universal across all three flavors):** topic directories under `raw/` and `wiki/` are **subject-matter**, never weeks, lecture numbers, content types, or course phases. For a `course` wiki on information security, topics look like `cryptography/`, `network-security/`, `web-security/` — not `week-2/` or `lectures/`. This rule is enforced by each flavor preset and by the Ingest operation's topic-selection step (§5.2). The rationale: subject-matter topics let cross-references survive when a course re-sequences material between semesters and let one wiki concept page absorb information from multiple weeks or content types.

---

## 5. Operations

Five operations. Each has clear triggers, behavior, and file-write effects.

### 5.1 Init

**Triggers:** `/wiki:init`, "initialize this vault as an LLM wiki", "start a new wiki"
**Inputs:**
- **Required (asked if not provided):** `flavor`, `title`.
- **Optional (default to flavor-template values; user can edit `wiki.config.md` later):** `audience`, `purpose`.
- **Implicit:** vault path (current working directory or vault root inferred from `.obsidian/` presence).

**Interaction shape:** if any required field is missing, the agent asks for all of them **in a single batched prompt** (not sequentially — one question, multiple answers). Before writing any files, the agent echoes the final config and asks for confirmation. After confirmation, write proceeds. This avoids a half-initialized vault from a mid-flow abort.

**Behavior:**
1. Check for existing structure. Never overwrite.
2. Create `raw/`, `wiki/`, `prompts/`, `wiki/digests/` directories (with `.gitkeep`).
3. Write `wiki.config.md` from the flavor template.
4. Write `wiki/index.md` (empty heading), `wiki/index.base` (default views), `wiki/log.md`.
5. Copy the flavor's prompt set into `prompts/` so the user can edit per-vault.
6. Append init entry to `wiki/log.md`.

**Idempotent.** Re-running Init only creates missing pieces; existing files are untouched.

### 5.2 Ingest

**Triggers:** "ingest this", "add to wiki", "ingest <url>", a URL or file mentioned with intent to add
**Inputs:** URL, file path, pasted text, content surfaced via Obsidian Web Clipper, **or** content surfaced by a connected MCP server (see "Sourcing content" below)

**Sourcing content:**

Ingest is source-agnostic. The framework cares about what lands in `raw/`, not where it came from. Five supported paths:

1. **URL** — the LLM fetches it. Best for public articles, arXiv papers, blog posts. `defuddle` (kepano/obsidian-skills) cleans web pages.
2. **File path** — the LLM reads it from disk. PDFs, local markdown, exported notes.
3. **Pasted text** — the LLM treats the pasted content as a source.
4. **Obsidian Web Clipper** — the official Obsidian browser extension writes content directly into `raw/` from the user's authenticated browser session. This is the primary path for any web content behind authentication (LMS pages, internal wikis, paywalled journals while logged in). See "Web Clipper integration" below.
5. **MCP-sourced** — the LLM pulls content via a connected MCP server. Useful when an authenticated MCP server is already available for the source platform (e.g., Notion MCP, Slack MCP, Linear MCP).

**Recommended path per flavour:**

| Flavour | Primary path | Notes |
|---|---|---|
| `course` | **Obsidian Web Clipper** for pages; manual download + drop for files | Course content lives behind LMS auth; Web Clipper uses the existing browser session and requires no special access |
| `research` | URL for public papers/blogs; Web Clipper for paywalled content while logged in; MCP server if one is already connected | URL ingestion suffices for most arXiv and blog material |
| `domain` | Whichever fits the source | URL for public; Web Clipper for auth'd portals; MCP for connected platforms (Slack, Notion, Linear, Gmail) |

**Notes on MCP-sourced ingestion:**
- Authentication is handled by the MCP server; the framework never sees credentials.
- The framework does not validate MCP-server output beyond its standard schema checks. Garbage in, garbage out applies.
- The framework **does not bundle or vendor any MCP server.** Users install whichever they need separately and configure it in their agent client.

### Web Clipper integration

For browser-accessible sources behind authentication — which covers virtually all coursework content — the framework integrates with **Obsidian Web Clipper**, the official Obsidian browser extension by Steph Ango that saves web pages as Markdown directly into the vault. Web Clipper operates inside the user's authenticated browser session, so no special access is required: if you can read the page in your browser, you can clip it.

The framework ships a reusable Web Clipper template, `canvas-web-clipper.json` (in `references/`), which:

- **Auto-triggers** on Instructure Canvas URL patterns (`*.instructure.com/courses/*`).
- **Routes** clips to `raw/<topic>/` (topic inferred from page metadata; falls back to `raw/inbox/` for the user to relocate during the next sync).
- **Populates** the framework's required frontmatter: `title`, `collected`, `published` (or `Unknown`), `topics`, `content_type`. `content_type` is defaulted from the URL pattern — `lecture` for `/pages/`, `assignment` for `/assignments/`, `discussion` for `/discussion_topics/`, `announcement` for `/announcements/`, `syllabus` for `/assignments/syllabus`.
- **Captures** the page body via DOM selectors targeting Canvas's main content area, dropping navigation and chrome.
- **Uses** `source_url` for the canonical page URL.

After clipping any number of pages, the user runs `/wiki:sync` to compile the new sources into the wiki in one batched pass.

**The same pattern works for any browser-accessible source:** Notion pages without API access, Google Docs read-only links, internal company portals, paywalled academic publishers while logged in. Communities maintain templates for many sites at `github.com/obsidian-community/web-clipper-templates`. The framework ships the Canvas LMS template directly; users author or import others as needed for their other flavours.

For PDFs and file attachments: download manually from the source and drop into `raw/<topic>/`. The binary-source policy below handles them on the next `/wiki:sync`.

**Behavior:**

**Step 1 — Fetch into `raw/`:**
- Resolve source content. Use `defuddle` (from kepano/obsidian-skills) for web pages to strip nav/ads/boilerplate before saving.
- **Pick or reuse a topic subdirectory.** Reuse if a close topic already exists; never create gratuitous new topics. **Topic semantics are subject-matter, not weeks or content-types** (e.g., `raw/cryptography/`, not `raw/week-2/` or `raw/lectures/`). This rule is enforced across all three flavors and codified in each flavor preset.
- **Save as `raw/<topic>/YYYY-MM-DD-<slug>.md` (or `.md` sidecar for binary sources, see below).** Slug from title, kebab-case, max 60 chars.
- **Binary source policy (PDFs, images, audio, video, etc.):** store the original binary in `raw/<topic>/YYYY-MM-DD-<slug>.<ext>` AND write a `.md` sidecar at `raw/<topic>/YYYY-MM-DD-<slug>.md` containing extracted text (OCR if needed for scanned PDFs), the standard frontmatter, and a wikilink to the binary (e.g., `binary: [[raw/cryptography/2026-09-15-lecture-2.pdf]]`). **The `.md` sidecar is the source of truth for wiki articles.** Articles cite the `.md`; the `.md` references the binary for visual lookback.
- **Threaded content (Canvas discussions, Slack threads, email chains):** store the whole thread as a **single** `.md` file, structured as `## Original post` followed by `### Reply by <author> [<date>]` sections. Splitting destroys conversational context.
- **Required frontmatter (core schema):** `collected`, `published` (set `Unknown` if absent), `title`, `topics`, `content_type`. **At least one of:** `source_url` (for content with a stable canonical URL — covers URL fetches, Web Clipper, and many MCP-sourced items) **or** `source_ref` (a structured identifier when a URL isn't available, e.g., `notion://page/abc123` or `slack://team/T0/channel/C1/ts/172800000.001`) — used for deduplication.
- **Optional extension fields (namespaced, source-type-specific):** ingestion paths may add fields tailored to the source (e.g., `canvas_course_id`, `canvas_module_id`, `due_date`, `assignment_type`, `discussion_replies_count`, `announcement_priority` from a Canvas Web Clipper template; `notion_database_id`, `notion_block_id` from a Notion MCP). Lint validates only the required core fields; extensions are pass-through.
- **`content_type` values** (controlled vocabulary, extendable per flavor): `article`, `paper`, `lecture`, `assignment`, `reading`, `discussion`, `announcement`, `syllabus`, `transcript`, `personal-note`. `personal-note` flags user-authored notes (reflections, questions, hypotheses) — see §5.2 compile rules for how these are treated differently from external sources.
- If `published` is unknown, omit the date prefix from the filename.
- Numeric suffix on filename collision.
- **Never** rewrite or clean source content beyond formatting noise. Preserve opinions verbatim.

**Step 2 — Compile into `wiki/`:**
- Decide: merge into an existing article, create a new article, or both (a source can spawn an update AND a new concept page — these are not mutually exclusive).
- Write using **Obsidian-flavored Markdown** via kepano/obsidian-skills: wikilinks (`[[Article]]`), callouts (`> [!summary]`, `> [!conflict]`), frontmatter properties.
- Cross-link aggressively. A single new source typically touches 5–15 pages.
- On factual conflict with existing wiki content: add a `> [!conflict]` callout, attribute both claims to their sources, **do not silently rewrite**. The conflict stays visible until resolved by a future ingest or explicit user direction.

**Step 3 — Cascade updates:**
- Scan same-topic articles for ripple effects.
- Scan `wiki/index.md` for related cross-topic articles.
- Refresh `updated` on every materially-changed article.
- Archive pages are never cascade-updated (they are point-in-time snapshots).

**Step 4 — Post-ingest:**
- Update `wiki/index.md` and `wiki/index.base`.
- Append to `wiki/log.md`:
  ```
  ## [YYYY-MM-DD] ingest | <primary article>
  - Updated: <cascade-updated article>
  - Updated: <another cascade-updated article>
  ```

**Idempotency (handles mutable sources):** when an ingest matches an existing `raw/` entry by `source_url` or `source_ref`, branch on content hash:

- **Hash matches (true duplicate):** refuse. Log: `## [YYYY-MM-DD] ingest | skipped duplicate <source_ref>`.
- **Hash differs (source has been updated upstream — Canvas page edited, discussion got new replies, assignment description clarified):** write as a **revision**. New file at `raw/<topic>/YYYY-MM-DD-<slug>-revN.md` with frontmatter `supersedes: [[raw/<topic>/<previous-file>.md]]`, plus a reverse pointer `superseded_by:` added to the previous file's frontmatter. Cascade-update any wiki articles that cite the previous revision so they reflect current content. Log: `## [YYYY-MM-DD] ingest | revision rev<N> of <slug>`.
- **No prior match (genuinely new source):** standard new-source flow.

Older revisions remain in `raw/` — never deleted, never silently overwritten. This preserves the audit trail for any claim sourced from the older revision.

### 5.3 Sync

**Triggers:** "sync the wiki", "process my inbox", "catch up", scheduled run
**Inputs:** none (operates on the delta since last sync)
**Behavior:**

1. Find every `raw/` file newer than the last sync timestamp (tracked in `wiki/log.md` or `.wiki-state`).
2. For each, run the Ingest **compile** step (Fetch is already done — these files were dropped in manually or via Web Clipper).
3. **Batch the cascade updates.** Instead of touching a popular concept page once per source, consolidate into a single update. This is the whole reason Sync exists as separate from Ingest — one consolidated walk is better than N small ones.
4. Single combined log entry:
   ```
   ## [YYYY-MM-DD] sync | N sources processed, M articles updated
   ```

Sync is the "I dumped a week of clippings via Obsidian Web Clipper, please catch up" operation.

### 5.4 Query

**Triggers:** "what do I know about X?", "summarize my notes on Y", "compare A and B from my wiki", any question in a vault initialized as an LLM wiki
**Inputs:** the question
**Behavior:**

1. Read `wiki/index.md` (or query `wiki/index.base`) to locate relevant articles.
2. Read those articles. **Prefer wiki content over training knowledge.** If the wiki has nothing relevant, say so explicitly rather than answering from priors.
3. Answer in conversation with markdown links to cited articles. Inside Obsidian, the user can click these.
4. Do **not** write files unless asked.

**Archive sub-operation (opt-in):**
- Triggered by: "archive this", "save this answer to the wiki", "file this".
- Write a new article in the most relevant topic directory. **Never merge into an existing article** — archives are point-in-time syntheses, not raw material.
- Frontmatter: `archived: true`, `sources` field points to the wiki articles cited (not raw).
- File name reflects the query, e.g., `transformer-architectures-overview.md`.
- Update `wiki/index.md` with the new entry; prefix summary with `[Archived]`.
- Log: `## [YYYY-MM-DD] query | Archived: <title>`.

**Question→page growth (proactive suggestion, never auto):**
If a query produces a synthesis the framework judges genuinely new and reusable, suggest archiving at the end of the answer. Wait for the user to confirm. Never archive silently.

### 5.5 Lint

**Triggers:** "lint the wiki", "health check", "wiki quality pass", scheduled run
**Behavior:** two categories with strictly different authority levels.

**Deterministic checks — auto-fix:**
- **Index consistency:** every `wiki/*.md` (excluding `index.md`, `log.md`) appears in `wiki/index.md`. Files missing from the index get added with `(no summary)` placeholder. Index entries pointing to nonexistent files are marked `[MISSING]` — never deleted; the user decides.
- **Internal links (wikilinks):** every wikilink in article bodies and frontmatter resolves. Dead links are searched for in the vault: exactly-one-match → auto-relinked; zero/multi-match → reported.
- **Raw references:** every `sources` entry in frontmatter resolves to an existing `raw/` file. Same exactly-one-match auto-fix rule.
- **See-also pruning:** within each topic directory, links to deleted files are removed.
- **Frontmatter validation:** required properties (`title`, `summary`, `updated`) present; defaults filled if obvious.
- **`wiki/index.base` regeneration:** if its schema has drifted from the article frontmatter.

**Heuristic checks — report only, never auto-fix:**
- Factual contradictions across articles.
- Outdated claims superseded by newer ingests (date-based heuristic).
- Missing conflict annotations where sources clearly disagree.
- Orphan pages (no inbound wikilinks).
- Missing cross-topic references.
- Concepts frequently mentioned but lacking a dedicated page.
- Archive pages whose cited source articles have changed substantially since archival.
- Thin pages (below configurable word count or single-source).

**The framework never silently rewrites content based on a heuristic.** Heuristic findings go in a report. The user decides whether to ingest a clarifying source, accept a suggestion, or ignore it.

Log entry: `## [YYYY-MM-DD] lint | N issues found, M auto-fixed, K reported`.

### 5.6 Digest

**Triggers:** "weekly digest", "what's new in my wiki", scheduled (cadence from `wiki.config.md`; default weekly)
**Inputs:** time window (default = since last digest, bounded by the cadence)
**Output:** a self-contained HTML artifact, **not** a Markdown file. This is the one place the framework breaks from pure Markdown.

**Time window definition:** when cadence is `weekly`, the window is an **ISO week (Monday 00:00 to Sunday 23:59 in the user's local timezone)**, and the filename slug uses ISO week numbering (`YYYY-Www`, e.g., `2026-W21-recap.html`). `biweekly` is two consecutive ISO weeks; `monthly` is the calendar month.

**Empty-period behavior:** if the window contains no `wiki/log.md` activity (no ingests, no syncs, no archives, no lints with findings), the digest **does not write a file by default**. The agent reports to the user: *"No wiki activity for <window>. Skipping digest. Run with `--force` to produce an empty recap."* This prevents the `wiki/digests/` directory from accumulating boilerplate files during midterm weeks or vacation periods.

**Behavior:**

1. Read `wiki/log.md` entries within the window.
2. Identify themes:
   - Which topics gained the most coverage?
   - Which articles got cascade-updated the most?
   - Which contradictions arose?
   - Which open questions were resolved or raised?
   - Which new concepts emerged?
   - Where are the coverage gaps?
3. Write `wiki/digests/YYYY-Www-recap.html` (e.g., `2026-W21-recap.html`). Required sections:
   - **Header** — week number, date range, wiki title, source count for the period.
   - **At a glance** — counter cards/badges for: sources ingested, articles touched, articles created, contradictions surfaced, open questions raised/resolved.
   - **Top articles by activity** — ranked, with one-line summaries; each link uses the `obsidian://open?vault=<vault>&file=<path>` URI scheme so clicking opens the article in Obsidian.
   - **Newly created articles** — with summaries pulled from frontmatter.
   - **Contradictions surfaced** — pulled from `> [!conflict]` callouts created or modified this period; show the two sources side by side.
   - **Open questions** — pulled from `> [!question]` callouts, split into "raised this period" and "resolved this period".
   - **Coverage gaps / suggested next reads** — concepts mentioned across multiple articles but lacking a dedicated page; topics with thin coverage.
4. Style requirements for the HTML:
   - **Self-contained.** No external dependencies. No CDN scripts, no remote fonts, no Google Analytics, nothing the browser has to fetch. Vanilla CSS is fine; if Tailwind is used it must be inlined.
   - Clean, readable, print-friendly. Light mode is sufficient.
   - Section cards or clear vertical sections with anchor links.
   - System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`) is fine.
   - Mobile-responsive (the user may open the digest on a phone).
   - Works opened directly in a browser **and** from Obsidian's file explorer (which delegates `.html` opens to the system browser by default).
5. Append a "Digests" section to `wiki/index.md` if not present; add the new digest as an entry. Use a standard Markdown link to the `.html` file rather than a wikilink, since Obsidian routes `.html` files to the browser via standard links.
6. Log: `## [YYYY-MM-DD] digest | week N | <filename>`.

Digest is the "Sunday 6pm, what did I learn this week" operation. The HTML format is the deliberate exception to "everything is markdown" — a digest is a presentation artifact (read once, browsed, sometimes shared), not part of the editable wiki corpus.

---

## 6. Obsidian-native conventions

### Hard dependency: kepano/obsidian-skills

The framework declares **kepano/obsidian-skills** as a hard dependency. Setup docs require installing it in the agent's skill directory alongside this framework. The framework's SKILL.md explicitly delegates to it for:
- `obsidian-markdown` — wikilinks, callouts, frontmatter, embeds, block references
- `obsidian-bases` — Base file authoring with views, filters, formulas
- `json-canvas` — `.canvas` file authoring
- `defuddle` — clean web extraction during Ingest

**Rationale:** kepano/obsidian-skills is the official Obsidian-team-authored skill set, 13k+ stars, maintained as Obsidian's syntax evolves. Re-implementing OFM, Bases, or JSON Canvas authoring here would mean duplicating work and breaking when syntax changes.

### Link style rules

- **Inside `wiki/`:** always wikilinks (`[[Article Name]]`, `[[Article Name|display]]`, `[[Article#Heading]]`).
- **From wiki to raw:** wikilinks (`[[raw/<topic>/<file>]]`) since the raw files are in the vault.
- **External URLs:** standard Markdown `[text](url)`.
- **In conversation output (query answers):** wikilinks where possible so they're clickable in Obsidian.

### Article frontmatter schema

```yaml
---
title: <title>
summary: <one-line summary; also used in index>
topics: [<topic>, ...]
sources: [[[raw/...]], [[raw/...]]]      # wikilinks to raw files in this vault
external_sources: <author/org; date; ...>  # for non-vaulted sources, semicolon-separated
created: <ISO date>
updated: <ISO date — knowledge change, not filesystem mtime>
archived: false
---
```

### Callouts

The framework standardizes on these callout types (all native Obsidian, no plugins required):
- `> [!summary]` — top-of-article summary block
- `> [!conflict]` — sources disagree on a claim
- `> [!source]` — inline attribution for a specific claim
- `> [!question]` — open questions flagged for future ingestion
- `> [!warning]` — stale or outdated content flagged by lint
- `> [!quote]` — direct quotes from sources

### Bases (`wiki/index.base`)

Default views in the global index Base:
- **All articles** (table) — title, summary, topics, updated
- **By topic** (grouped table)
- **Orphans** (filter: no inbound wikilinks; auto-flagged by lint)
- **Recently updated** (sort by `updated` desc)
- **Archived only** (filter: `archived == true`)
- **Open questions** (filter: articles containing `> [!question]`)

Per-topic Bases (`wiki/<topic>/<topic>.base`) are generated on demand when a topic exceeds a configurable threshold (default 5 articles).

### Obsidian Canvas (supported but de-emphasized)

> **Note on naming:** "Obsidian Canvas" throughout this PRD refers to Obsidian's `.canvas` (JSON Canvas) visual-map files — **not** Instructure Canvas LMS. The two are unrelated. Canvas LMS as a content source is covered in §5.2 under "Sourcing content".

Obsidian Canvas authoring is supported via kepano/obsidian-skills (`json-canvas`), but the framework does **not** generate `.canvas` files automatically.

- **Generated only on explicit user request** (e.g., "draw a concept map of <topic>", "make an Obsidian canvas of how these articles relate").
- **Not generated during digest** — the digest is the HTML artifact described in §5.6.
- **Not generated during ingest or sync.**
- **Stored in:** `wiki/canvas/` when produced.
- **Nodes** link back to wiki articles via wikilinks. The Obsidian Canvas is a view, not a source of truth.

Rationale for de-emphasis: in practice, auto-generated `.canvas` files tend to go stale, bloat the vault, and rarely get revisited. We keep the capability available for the moments it genuinely helps (visualizing a complex topic on demand) without pushing it into routine operations.

---

## 7. Distribution

### Skill core (portable, primary deliverable)

Lives at `skills/llm-wiki/SKILL.md` plus `references/` (templates) and `prompts/` (default flavor prompts). Conforms to the agentskills.io standard.

**Install paths:**
- Claude Code: `~/.claude/skills/llm-wiki/`
- Cursor: `.cursor/skills/llm-wiki/`
- Codex CLI: `~/.codex/skills/llm-wiki/`
- OpenCode: `~/.opencode/skills/llm-wiki/`
- Portable: `.skills/llm-wiki/` in any project

**Install methods:**
- `npx add-skill <owner>/llm-wiki-framework`
- Manual `git clone` + copy

The skill is self-contained: no bash dependency, no external scripts.

### Claude Code plugin wrapper (optional, secondary deliverable)

A thin wrapper around the skill that adds:
- **Slash commands:** `/wiki:init`, `/wiki:ingest`, `/wiki:sync`, `/wiki:query`, `/wiki:lint`, `/wiki:digest`
- **Plugin marketplace install:** `/plugin marketplace add <owner>/llm-wiki-framework` then `/plugin install llm-wiki@llm-wiki-framework`
- **Routines integration** for scheduled `digest` (default weekly) and `sync` (default daily or on-demand)
- **`init_wiki.sh`** scaffolding script — same behavior as the skill's Init operation but executable for power users who want one-shot setup from a shell

The plugin **imports** the skill, not forks it. Updates to the skill propagate without re-publishing the plugin.

### Repository layout

The framework is shipped as a **single monorepo**. The skill core and the CC plugin wrapper live in one repo so they version-lock and release together. Recommended structure:

```
llm-wiki-framework/                       # the repo
├── README.md
├── LICENSE                               # MIT
├── skills/
│   └── llm-wiki/
│       ├── SKILL.md
│       ├── references/
│       │   ├── raw-template.md
│       │   ├── article-template.md
│       │   ├── archive-template.md
│       │   ├── index-template.md
│       │   ├── index-base-template.base
│       │   ├── wiki-config-template.md
│       │   ├── digest-template.html       # HTML template for §5.6
│       │   ├── canvas-web-clipper.json    # Web Clipper template for Canvas LMS, see §5.2
│       │   └── flavor-presets/
│       │       ├── research.md
│       │       ├── course.md
│       │       └── domain.md
│       └── prompts/
│           ├── ingest.md
│           ├── sync.md
│           ├── query.md
│           ├── lint.md
│           └── digest.md
├── cc-plugin/
│   ├── .claude-plugin/
│   │   └── plugin.json                   # plugin metadata
│   ├── commands/                         # slash command definitions
│   │   ├── wiki-init.md
│   │   ├── wiki-ingest.md
│   │   ├── wiki-sync.md
│   │   ├── wiki-query.md
│   │   ├── wiki-lint.md
│   │   └── wiki-digest.md
│   ├── scripts/
│   │   └── init_wiki.sh
│   └── README.md
└── .claude-plugin/
    └── marketplace.json                  # turns the repo into a single-plugin marketplace
```

**Install paths:**

The repo doubles as a Claude Code plugin marketplace (single-plugin), so users install the CC plugin via:

```
/plugin marketplace add ipoeyke/llm-wiki-framework
/plugin install llm-wiki@llm-wiki-framework
```

Skill-only users install via `npx add-skill ipoeyke/llm-wiki-framework` — the agentskills.io tooling discovers the `skills/llm-wiki/` subdirectory automatically.

**Where this lives concretely:** `ipoeyke/llm-wiki-framework` on GitHub. We are **not** recommending contributing this as a plugin to `dair-ai/dair-academy-plugins` for two reasons: (a) this framework is Obsidian-specialized while dair-ai's `wiki-builder` is Obsidian-agnostic, so they coexist rather than compete; (b) self-owned versioning makes release cadence independent of dair-ai's marketplace gating. Open to cross-listing later if there's appetite.

---

## 8. Templates & reference files

All colocated with the skill in `references/`:

| File | Purpose |
|---|---|
| `raw-template.md` | Frontmatter + body shape for files in `raw/` |
| `article-template.md` | Frontmatter + body shape for `wiki/` articles, with callout slots |
| `archive-template.md` | Variant for query-archived pages |
| `index-template.md` | Structure for `wiki/index.md` |
| `index-base-template.base` | Default Bases views for `wiki/index.base` |
| `digest-template.html` | Weekly recap HTML template (self-contained, see §5.6) |
| `wiki-config-template.md` | `wiki.config.md` skeleton |
| `canvas-web-clipper.json` | Obsidian Web Clipper template for Instructure Canvas LMS — see §5.2 "Web Clipper integration" |
| `flavor-presets/<flavor>.md` | Per-flavor defaults (page types, style rules, prompts) |
| `prompts/<operation>.md` | Default prompt for each of the 5 operations, per flavor |

---

## 9. Acceptance criteria

A successful v1 implementation must satisfy:

1. **Init creates a valid Obsidian vault** that opens cleanly in Obsidian with no warnings.
2. **Ingesting a single URL** produces: one `raw/` file with valid frontmatter, 1–5 wiki articles using wikilinks (not standard Markdown links), an updated `wiki/index.md`, an updated `wiki/index.base`, and a log entry.
3. **Ingesting the same URL twice** does not create duplicates — the framework recognizes the source via `source_url` and refuses.
4. **A second ingest on a related topic** triggers cascade updates to the first ingest's articles, reflected in `wiki/log.md`.
5. **Query without archive** returns answers grounded in wiki content with clickable wikilinks; no files written.
6. **Query with archive** writes one new article; never merges into existing articles.
7. **Lint auto-fixes** index drift and dead wikilinks where exactly one rename target exists. Lint **reports without fixing** contradictions, orphans, thin pages.
8. **Digest** produces a self-contained HTML artifact at `wiki/digests/YYYY-Www-recap.html` referencing only activity from the requested window; never invents activity not in the log. Opens cleanly in a browser with **zero external network requests** (verify via DevTools Network tab). Article links use the `obsidian://` URI scheme to open the corresponding wiki page in Obsidian.
9. **Same skill + different flavor** produces materially different `wiki.config.md`, prompt sets, and default page types — verifiable by diffing two fresh inits.
10. **Vault opens correctly in Obsidian:** wikilinks resolve, callouts render, `wiki/index.base` views populate, Obsidian Canvas (`.canvas`) files open.
11. **The skill runs on at least Claude Code and one other agent** (Cursor or Codex) without modification.
12. **kepano/obsidian-skills is invoked** for all OFM, Bases, JSON Canvas (`.canvas`), and Defuddle operations — verifiable from agent traces.

---

## 10. Open questions / future work

- **Knowledge-graph layer** (Vivian/mnemon pattern): possibly worth adding once a wiki has 100+ articles. Out of v1.
- **MCP variant** for cross-device access (Hjarni pattern): out of v1; local-first is the v1 promise.
- **Multi-wiki support** (`WIKI_ROOT`): explicitly deferred per the v1 scope decision. If wanted later, a thin wrapper is straightforward — the per-vault config already supports the use case at small N.
- **Auto-scheduling:** the framework relies on Claude Code Routines (CC plugin) or the user's own cron. We document recommended schedules but don't enforce them.
- **Style transfer:** should ingestion adapt voice based on `audience` in the config (academic vs. casual)? Probably v2.
- **Journal / CRM modules:** out of v1 but the folder layout is designed not to preclude adding `journal/` and `crm/` later.
- **Git integration:** documenting a `.gitignore` and recommended commit pattern (e.g., commit after sync, after digest) is part of setup docs but not enforced behavior.
- **Browser-automation agent for batch capture (Playwright MCP, chrome-devtools-mcp):** considered as an alternative to Obsidian Web Clipper for batch ingestion of authenticated web sources. Deferred — for the realistic v1 cadence (a few sources per day, semester-paced), the per-page click cost of Web Clipper is negligible, and browser-automation adds setup overhead, session-refresh brittleness, and a layer of agent supervision that doesn't repay itself at this scale. Revisit if a user reports specific batch-ingestion pain.

---

## Appendix A — How this differs from the closest existing implementations

| Concern | dair-ai wiki-builder (baseline) | Astro-Han karpathy-llm-wiki | **This framework** |
|---|---|---|---|
| Per-vault config | Yes (`wiki.config.md`) | No | **Yes (`wiki.config.md`)** |
| Flavors | 7 | 1 | **3 — `research`, `course`, `domain` (deliberately tight; `domain` is the generalist bucket)** |
| Form factor | CC plugin only | Portable skill only | **Both — skill core + CC plugin wrapper** |
| Multi-wiki | Yes (`WIKI_ROOT`) | No | **No (v1)** |
| Obsidian-native | No | No | **Yes — kepano/obsidian-skills dependency, OFM, Bases, Obsidian Canvas (`.canvas`)** |
| Operations | start, ingest, compile, query, lint, restructure, export | Ingest, Query, Lint | **Init, Ingest, Sync, Query, Lint, Digest** |
| Lint discipline | Mixed | Strict deterministic/heuristic split | **Strict split (Astro-Han pattern)** |
| Digest / weekly synthesis | No | No | **Yes** |
| Sync (batch reconcile) | Partial | No | **Yes (first-class)** |
| Question→page growth | No | Archive on request | **Archive on request + proactive suggestion** |
| Provenance | `sources.md` | Frontmatter `Sources` field | **Frontmatter wikilinks to raw + `source_url` deduplication** |
