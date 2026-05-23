# Ingest — domain flavor

Ingest a single source (URL, file, pasted text, Web Clipper output, or MCP-sourced content) into a `domain`-flavored wiki. `domain` is the generalist bucket — anything not clearly a research or coursework wiki.

## Triggers

- `/wiki:ingest <input>`
- "ingest this", "add to wiki", "ingest <url>"
- A URL or file mentioned with intent to add to the wiki

## Inputs

A single source. Resolve before proceeding:

- **URL** — fetch directly. Use `defuddle` from `kepano/obsidian-skills` for web pages.
- **File path** — read from disk. Binaries follow the binary-source policy below.
- **Pasted text** — ask for `title` and a `source_url`/`source_ref` if not obvious.
- **Web Clipper output** — already in `raw/`; routed to Step 2 via `/wiki:sync` for batches.
- **MCP-sourced content** — pull via the connected MCP server (Notion, Slack, Linear, Gmail, etc.).

## Step 1 — Fetch into `raw/`

1. **Pick or reuse a topic subdirectory.** Topics are subject-matter — the natural categories a reader of *this specific wiki* would expect.
   - For a coffee wiki: `raw/extraction/`, `raw/roasting/`, not `raw/articles/` or `raw/2024/`.
   - For an internal project wiki: `raw/architecture/`, `raw/incidents/`, not `raw/slack/` or `raw/q3-2025/`.
   - Reuse before fragmenting. If unsure between two existing topics, ask the user.
2. **Save as `raw/<topic>/YYYY-MM-DD-<slug>.md`.** Slug from title, kebab-case, max 60 chars. Omit date prefix if `published` is `Unknown`.
3. **Numeric suffix on filename collision.**
4. **Binary source policy:** binary at `raw/<topic>/YYYY-MM-DD-<slug>.<ext>` AND `.md` sidecar with extracted text and `binary: [[<binary-file>]]` frontmatter. Sidecar is the source of truth.
5. **Threaded content** (Slack threads, email chains, forum discussions): one `.md` per thread, structured `## Original post` then `### Reply by <author> [<date>]` sections.
6. **Required frontmatter:** `title`, `collected`, `published` (or `Unknown`), `topics`, `content_type`, plus one of `source_url`/`source_ref`.
7. **Optional extension fields** (pass-through; not validated): source-type-specific fields from your MCP server or Web Clipper template (e.g., `notion_database_id`, `slack_channel_id`, `linear_issue_id`).
8. **Preserve content verbatim.** No rewriting, no normalization beyond formatting noise.
9. **Idempotency:** matching `source_url`/`source_ref` + same hash → refuse with `skipped duplicate` log. Different hash → revision file (`-revN.md`) with `supersedes:` / `superseded_by:` pointers.

## Step 2 — Compile into `wiki/` (domain-specific)

Delegate to the `obsidian-markdown` sub-skill.

1. **Decide:** merge into existing article(s), create new article(s), or both.
2. **Page-type vocabulary** (`domain` flavor — deliberately spare; extend in `wiki.config.md`):
   - `concept` — default. A topic, idea, entity, decision, term — anything that earns a page. One concept per page.
   - `overview` — higher-altitude page orienting the reader across many concepts within a topic. Often a topic's landing page.
   - `comparison` — sustained side-by-side analysis of two or more concepts commonly confused or commonly traded off. Earns its own page when the comparison itself is the captured thing.
   - **Per-vault extensions:** if `wiki.config.md` lists additional page types (e.g., `entity`, `decision`, `incident`, `runbook`, `vendor`), honor them.
3. **Voice:** encyclopedic and generalist. Plain. Define jargon on first use, then link to a definition page if the term recurs.
4. **Citation discipline:** every nontrivial claim sourced — wikilink to raw, or a `> [!source]` callout for emphasis. External non-vaulted citations go in `external_sources`.
5. **Personal-note handling:** if `content_type: personal-note`, surface only as `> [!question]` callouts. Never cite a personal-note as if it were external evidence.
6. **Cross-link aggressively.** Even a single source typically updates 3–10 pages.
7. **Conflicts:** add a `> [!conflict]` callout attributing both claims. Do not silently rewrite.
8. **Use `references/article-template.md` as the structural template** for new articles.

## Step 3 — Cascade updates

1. Scan same-topic articles for ripple effects.
2. Scan `wiki/index.md` for related cross-topic articles.
3. **Refresh `updated` on every materially-changed article.**
4. **Archive pages (`archived: true`) are never cascade-updated.**

## Step 4 — Post-ingest

1. Update `wiki/index.md`.
2. Update `wiki/index.base` (delegate to `obsidian-bases`) if schema drifted.
3. Append to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] ingest | <primary article>
   - Updated: <cascade-updated article>
   ```

## File-write contract

- **Writes:** one new `raw/` file (or `-revN.md`), zero-to-many new `wiki/` articles, updates to cascade-touched articles, `wiki/index.md`, `wiki/index.base` (if schema changed), `wiki/log.md`.
- **Never touches:** other `raw/` files; archived articles; `wiki.config.md`; per-vault `prompts/`.
