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

0. **Write-time admission.** Before writing, classify the source against the wiki:
   - **Update-only:** an existing page already covers this subject (same paper, same release, same event). Add the source to that page's `sources` and fold in what is new. No new page.
   - **Merge-only:** a single-source item with no substance of its own beyond a data point for an existing page. Add a dated subsection to that parent page. No new page.
   - **New page:** the source introduces a concept, entity or decision no existing page covers, or warrants an overview or comparison page that does not yet exist.
   Grep `title:`, `aliases:` and `catalog:` across `wiki/**` and read the one or two relevant `wiki/<topic>/_index.md` files to find the existing page. State the admission decision and its reason in the log entry.
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
8. **Use `references/article-template.md` as the structural template** for new articles, plus the lifecycle fields: `catalog:` (one double-quoted sentence, at most 25 words: what it is and its one distinguishing claim; no title repeat) directly after `summary`, and `status: active`. Leave `review_by` to the script.
9. **Successor (no retirement).** If the new page describes the direct successor of an existing page's subject (a new version of the same product, model, spec or standard that replaces it), leave the predecessor `status: active` and write no `supersedes` or `superseded_by`. Cascade a dated successor subsection and link onto the predecessor, and add `Supersession candidate: [[Old]] by [[New]]` to the log entry. Retirement happens only in the consolidation pass. Versions that coexist (different sizes, tiers or product lines) are not successors.

## Step 3 — Cascade updates

1. Scan same-topic articles for ripple effects.
2. Grep article frontmatter (`title:`, `aliases:`, `catalog:`) across `wiki/**` for related cross-topic articles; open a topic's `_index.md` when you need its full list.
3. **Refresh `updated` on every materially-changed article.**
4. **Archive pages (`archived: true`) are never cascade-updated.** The same holds for `status: superseded` and `status: merged` pages: put new evidence on their `superseded_by` target.
5. If a touched article's gist changed, rewrite its `catalog:` line.

## Step 4 — Post-ingest

1. Regenerate lifecycle dates and indexes from the vault root: `python3 prompts/tools/wiki_maint.py lifecycle`, then `index`, then `check`. Never hand-edit `wiki/index.md` rows or any `_index.md`. `check` must be clean apart from report-only split candidates.
2. Update `wiki/index.base` (delegate to `obsidian-bases`) if schema drifted.
3. Append to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] ingest | <primary article>
   - Updated: <cascade-updated article>
   ```

## File-write contract

- **Writes:** one new `raw/` file (or `-revN.md`), zero-to-many new `wiki/` articles, updates to cascade-touched articles, lifecycle frontmatter on new pages, `wiki/index.md` and `wiki/<topic>/_index.md` (script only), `wiki/index.base` (if schema changed), `wiki/log.md`.
- **Never touches:** other `raw/` files; archived, superseded or merged articles' bodies; `wiki.config.md`; per-vault `prompts/`.
