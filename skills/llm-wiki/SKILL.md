---
name: llm-wiki
description: Maintains a compounding, cross-referenced Obsidian wiki on top of a raw/ source archive. Use when the user wants to initialize a wiki vault, ingest sources, sync clippings, query their wiki, lint it, or produce a weekly digest. Triggers on phrases like "initialize this vault as a wiki", "ingest this URL", "what do I know about X from my wiki", "lint the wiki", "weekly digest".
license: MIT
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

**Install paths per agent** (kepano/obsidian-skills colocates with this skill):

| Agent | Path |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` (per-project) |
| Codex CLI | `~/.codex/skills/` |
| OpenCode | `~/.opencode/skills/` |
| Portable | `.skills/` in any project root |

## Vault layout

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
│   │   └── <topic>.base               (optional, per-topic view)
│   ├── digests/
│   │   └── YYYY-Www-recap.html
│   └── canvas/                         (Obsidian Canvas / .canvas files)
│       └── <topic>-map.canvas         (on explicit request only)
└── prompts/
    ├── ingest.md
    ├── sync.md
    ├── query.md
    ├── lint.md
    └── digest.md
```

Per-vault prompts under `prompts/` override the skill's defaults at `prompts/`. Read both; the vault wins on conflict.

## Operations

Six operations. Each has a dedicated prompt file. Read the relevant prompt **before** acting on a trigger.

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
   - Create directories: `raw/`, `wiki/`, `wiki/digests/`, `prompts/`. Touch `.gitkeep` in empty leaves.
   - Write `wiki.config.md` from `references/wiki-config-template.md`, substituting placeholders. Inject defaults from `references/flavor-presets/<flavor>.md`.
   - Write `wiki/index.md` from `references/index-template.md` (empty heading shape).
   - Write `wiki/index.base` from `references/index-base-template.base` (six default views — delegate Bases syntax to `obsidian-bases`).
   - Touch `wiki/log.md`.
   - Copy the chosen flavor's ingest prompt to vault: `prompts/ingest/<flavor>.md` → `prompts/ingest.md`. Copy flat `prompts/{sync,query,lint,digest}.md` as-is.
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

## Cross-agent compatibility

This skill and its prompts use no Claude Code-specific syntax. Specifically:
- No `$ARGUMENTS` (that's a CC slash-command convention; it appears only in the CC plugin wrapper, not here).
- No assumptions about a particular slash-command surface.
- File paths are POSIX; the bash init script in the CC plugin is the only POSIX-shell-specific artifact and is optional.

Tested under: Claude Code. Smoke-tested under: Cursor, Codex CLI (skill discoverable at the documented install paths).

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
| `wiki-config-template.md` | `wiki.config.md` skeleton with `{{placeholder}}` slots |
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
└── digest.md
```

No `init.md` prompt — Init's flow is above, in this file.
