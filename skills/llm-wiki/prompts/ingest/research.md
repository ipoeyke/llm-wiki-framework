# Ingest — research flavor

Ingest a single source (URL, file, pasted text, Web Clipper output, or MCP-sourced content) into a `research`-flavored wiki.

## Triggers

- `/wiki:ingest <input>`
- "ingest this", "add to wiki", "ingest <url>"
- A URL or file mentioned with intent to add to the wiki

## Inputs

A single source. Resolve before proceeding:

- **URL** — fetch directly. Use the `defuddle` sub-skill from `kepano/obsidian-skills` to strip nav/ads/boilerplate before saving.
- **File path** — read from disk. PDFs and other binaries follow the binary-source policy below.
- **Pasted text** — treat as source content; ask the user for `title` and `source_url`/`source_ref` if not obvious.
- **Web Clipper output** — already in `raw/`; routed to Step 2 via `/wiki:sync` (this prompt handles single-source ingest).
- **MCP-sourced content** — pull via the connected MCP server; the framework never sees credentials.

## Step 1 — Fetch into `raw/`

1. **Pick or reuse a topic subdirectory.** Reuse if a close topic already exists. Never create gratuitous new topics.
   - **Topics are subject-matter, never authors, venues, years, or content types.** Reject candidates like `raw/arxiv/`, `raw/2024/`, `raw/karpathy/`. Use `raw/attention/`, `raw/tokenization/`, etc.
   - If unsure between two existing topics, ask the user.
2. **Save as `raw/<topic>/YYYY-MM-DD-<slug>.md`.** Slug from title, kebab-case, max 60 chars. If `published` is unknown, omit the date prefix.
3. **Numeric suffix on filename collision** (`...-slug-2.md`).
4. **Binary source policy** (PDFs, images, audio): store the original at `raw/<topic>/YYYY-MM-DD-<slug>.<ext>` AND write a `.md` sidecar at the same path with extracted text (OCR if scanned). Sidecar frontmatter includes `binary: [[raw/<topic>/<file>.<ext>]]`. **The `.md` sidecar is the source of truth.** Articles cite the sidecar, never the binary directly.
5. **Threaded content** (Slack threads, email chains): one `.md` per thread, structured `## Original post` followed by `### Reply by <author> [<date>]` sections.
6. **Required frontmatter:** `title`, `collected`, `published` (or `Unknown`), `topics`, `content_type`, and at least one of `source_url` / `source_ref`. See `references/raw-template.md`.
7. **Preserve content verbatim.** No rewriting, no typo fixing, no normalization beyond formatting noise. Opinions are evidence; preserve them.
8. **Idempotency:** if an existing `raw/` entry has the same `source_url` or `source_ref`, branch on content hash:
   - Hash matches: refuse. Log `## [YYYY-MM-DD] ingest | skipped duplicate <source_ref>`. Stop.
   - Hash differs (upstream updated): write a revision file `raw/<topic>/YYYY-MM-DD-<slug>-rev<N>.md` with `supersedes: [[<previous>]]`. Add `superseded_by:` to the previous file. Continue to Step 2 with the new revision; cascade-update wiki articles that cite the previous revision.
   - No prior match: standard new-source flow.

## Step 2 — Compile into `wiki/` (research-specific)

This step has the flavor-specific behavior. Delegate to the `obsidian-markdown` sub-skill for wikilink, callout, frontmatter, and embed syntax.

0. **Write-time admission.** Before writing, classify the source against the wiki:
   - **Update-only:** an existing page already covers this subject (same paper, same release, same event). Add the source to that page's `sources` and fold in what is new. No new page.
   - **Merge-only:** a single-source item with no substance of its own beyond a data point for an existing page. Add a dated subsection to that parent page. No new page.
   - **New page:** the source is a paper with its own method and results, or introduces an idea no existing page covers.
   Grep `title:`, `aliases:` and `catalog:` across `wiki/**` and read the one or two relevant `wiki/<topic>/_index.md` files to find the existing page. State the admission decision and its reason in the log entry.
1. **Decide:** merge into existing article(s), create new article(s), or both. These are not mutually exclusive — one paper often updates a `concept` page AND warrants its own `paper` page.
2. **Page-type vocabulary** (`research` flavor):
   - `concept` — recurring idea (attention, tokenization, RLHF). Default; built up over many sources.
   - `paper` — a specific publication. Frontmatter adds `authors`, `venue`, `year`. One paper, one page. Body covers contribution, method, results, position relative to neighboring concepts.
   - `open-question` — an unresolved research question. Linked from `> [!question]` callouts in other articles.
   - `hypothesis` — a stronger claim worth defending; cite evidence pulling for and against.
3. **Voice:** rigorous and hedged. "The paper claims X" / "The authors argue Y", never "X is true." Qualify conclusions by evidence quality.
4. **Citation discipline:** every nontrivial claim has a `> [!source]` callout or an inline wikilink to the raw source. Untraceable claims are a smell — flag them as `> [!question]` for follow-up.
5. **Personal-note handling:** if `content_type: personal-note`, the content surfaces only as `> [!question]` callouts in the relevant articles. **Never cite a personal-note as if it were external evidence.**
6. **Cross-link aggressively.** A single new source typically touches 5–15 pages. Use `[[Article]]`, `[[Article|display text]]`, `[[Article#Heading]]` (delegate to `obsidian-markdown`).
7. **Conflicts:** if a new claim conflicts with existing wiki content, add a `> [!conflict]` callout attributing both claims to their sources. **Do not silently rewrite.** The conflict stays visible until resolved by a future ingest or explicit user direction.
8. **Use `references/article-template.md` as the structural template** for new articles, plus the lifecycle fields: `catalog:` (one double-quoted sentence, at most 25 words: what it is and its one distinguishing claim; no title repeat) directly after `summary`, and `status: active`. Leave `review_by` to the script.
9. **Successor (no retirement).** If the new page describes the direct successor of an existing page's subject (a new version of the same product, model, spec or standard that replaces it), leave the predecessor `status: active` and write no `supersedes` or `superseded_by`. Cascade a dated successor subsection and link onto the predecessor, and add `Supersession candidate: [[Old]] by [[New]]` to the log entry. Retirement happens only in the consolidation pass. Versions that coexist (different sizes, tiers or product lines) are not successors.

## Step 3 — Cascade updates

1. Scan same-topic articles for ripple effects: this source might add evidence to, refine, or contradict claims in them.
2. Grep article frontmatter (`title:`, `aliases:`, `catalog:`) across `wiki/**` for related cross-topic articles; open a topic's `_index.md` when you need its full list. A new paper on attention often updates `tokenization/` or `efficiency/` articles too.
3. **Refresh `updated` on every materially-changed article.** Filesystem mtime is not the same — `updated` tracks knowledge change.
4. **Archive pages (`archived: true`) are NEVER cascade-updated.** They are point-in-time syntheses. The same holds for `status: superseded` and `status: merged` pages: put new evidence on their `superseded_by` target.
5. If a touched article's gist changed, rewrite its `catalog:` line.

## Step 4 — Post-ingest

1. Regenerate lifecycle dates and indexes from the vault root: `python3 prompts/tools/wiki_maint.py lifecycle`, then `index`, then `check`. Never hand-edit `wiki/index.md` rows or any `_index.md`. `check` must be clean apart from report-only split candidates.
2. Update `wiki/index.base` (delegate to the `obsidian-bases` sub-skill). Usually no change unless the schema drifted.
3. Append to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] ingest | <primary article>
   - Updated: <cascade-updated article>
   - Updated: <another cascade-updated article>
   ```

## File-write contract

- **Writes:** one new `raw/` file (or a `-revN.md`), zero-to-many new `wiki/` articles, updates to existing articles cascade-touched, lifecycle frontmatter on new pages, `wiki/index.md` and `wiki/<topic>/_index.md` (script only), `wiki/index.base` (if schema changed), `wiki/log.md`.
- **Never touches:** `raw/` files other than the one being added; archived, superseded or merged articles' bodies; `wiki.config.md`; per-vault `prompts/`.
