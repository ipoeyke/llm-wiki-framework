# LLM Wiki — Claude Code plugin

Thin Claude Code wrapper around the `llm-wiki` skill at [`../skills/llm-wiki/`](../skills/llm-wiki/). The plugin adds six slash commands and a deterministic bash-init shortcut. All operational logic lives in the skill — this plugin is the CC surface.

## Install

The repository root doubles as a single-plugin marketplace, so:

```
/plugin marketplace add ipoeyke/llm-wiki-framework
/plugin install wiki@llm-wiki-framework
```

## Hard dependency: kepano/obsidian-skills

The skill delegates to [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) for Obsidian-Flavored Markdown, Bases authoring, JSON Canvas authoring, and clean web extraction. **Install it alongside this plugin's skill** at the same skills directory:

| Agent | Skills directory |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` |
| Codex CLI | `~/.codex/skills/` |
| OpenCode | `~/.opencode/skills/` |

Without `kepano/obsidian-skills`, Obsidian-flavored output (wikilinks, callouts, frontmatter, Bases) will be malformed.

## Slash commands

| Command | What it does |
|---|---|
| `/wiki:init [flavor] [title…]` | Initialize the current directory as an LLM Wiki vault. Prompts for any missing required fields, echoes the final config, asks for confirmation before writing. |
| `/wiki:ingest <url-or-file-or-text>` | Ingest a single source. Fetches (using `defuddle` for web pages), normalizes into `raw/<topic>/YYYY-MM-DD-<slug>.md`, then compiles into the wiki with cascade-updates. |
| `/wiki:sync` | Batch-process every new `raw/` source since the last sync, consolidating cascade updates. The "I dumped a week of Web Clipper clippings, catch up" operation. |
| `/wiki:query <question>` | Answer from the wiki. Read-only by default. Follow up with "archive this" to save the answer as a new article. |
| `/wiki:lint` | Auto-fix deterministic issues (index drift, dead wikilinks with exactly one match, missing frontmatter defaults). Report heuristic findings (contradictions, orphans, thin pages) — never silently rewrite article bodies based on heuristics. |
| `/wiki:digest [--week YYYY-Www \| --force]` | Render the current period's activity (default: this ISO week) as a self-contained HTML file at `wiki/digests/YYYY-Www-recap.html`. Article links use `obsidian://` URIs. Empty periods skip the write unless `--force` is passed. |

The full per-operation spec lives in `../skills/llm-wiki/prompts/` (and `prompts/ingest/<flavor>.md` for the per-flavor compile step). Per-vault `prompts/` files override the skill's defaults on a per-operation basis.

## init_wiki.sh — power-user scaffolding shortcut

A bash script at `scripts/init_wiki.sh` that does the deterministic file-creation half of `/wiki:init` without the agentic confirmation flow. Useful when you want a vault scaffolded immediately from a terminal.

```sh
# from inside the directory you want to initialize as a vault
init_wiki.sh --flavor course --title "Information Security Wiki"
```

Defaults: `--flavor domain`, `--title <basename of cwd>`. The script:

- Refuses if `wiki.config.md` already exists (safe to re-run; prints "already initialized").
- Creates `raw/`, `wiki/`, `wiki/digests/`, `prompts/`.
- Writes `wiki.config.md` from `references/wiki-config-template.md`, substituting top-level placeholders and appending the chosen flavor's preset (`references/flavor-presets/<flavor>.md`).
- Writes `wiki/index.md`, `wiki/index.base`, touches `wiki/log.md`.
- Copies the chosen flavor's `prompts/ingest/<flavor>.md` → vault's `prompts/ingest.md`, plus the four flat prompts.
- Leaves `<edit: …>` placeholders in the config for `audience` and `purpose` — fill those in before your first ingest.

The script is pure bash; no Node, no Python, no argument-parsing libraries.

## Canvas LMS Web Clipper template

`../skills/llm-wiki/references/canvas-web-clipper.json` is a best-effort [Obsidian Web Clipper](https://obsidian.md/clipper) template targeting Instructure Canvas URL patterns (`*.instructure.com/courses/*`). It routes clips into `raw/<course-id>/` with the framework's required frontmatter pre-populated.

**Validate this template in the Web Clipper UI on first install.** Obsidian Web Clipper's full template JSON schema is not publicly documented as of this writing, so field syntax (e.g., `{{url|split:'/'|index:5}}`) may need adjustment for your Web Clipper version. Once you've validated it, relocate clipped sources from `raw/<course-id>/` (or `raw/inbox/`) into subject-matter topic directories (`raw/cryptography/`, etc.) during the next `/wiki:sync` — the framework's topic-naming convention is subject-matter, never course IDs or weeks.

The Canvas template is the only Canvas-LMS-specific artifact shipped. The same Web Clipper pattern works for any browser-accessible source behind authentication — Notion pages, Google Docs, internal portals, paywalled academic publishers. Community templates for many sites live at [github.com/obsidian-community/web-clipper-templates](https://github.com/obsidian-community/web-clipper-templates).

## Layout

```
cc-plugin/
├── .claude-plugin/
│   └── plugin.json          # plugin metadata; "skills": "../skills/" imports the skill
├── commands/
│   ├── init.md
│   ├── ingest.md
│   ├── sync.md
│   ├── query.md
│   ├── lint.md
│   └── digest.md
├── scripts/
│   └── init_wiki.sh
└── README.md
```

The plugin **imports** the skill via `plugin.json`'s `"skills": "../skills/"`. Updates to the skill propagate without re-publishing the plugin.

## See also

- [Project README](../README.md) — what the framework is, both install paths (skill-only or CC plugin), quickstart.
- [PRD](../docs/prd.md) — full v1 spec.
- [Skill](../skills/llm-wiki/SKILL.md) — the portable skill the plugin wraps.
