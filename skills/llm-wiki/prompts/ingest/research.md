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
8. **Use `references/article-template.md` as the structural template** for new articles.

## Step 3 — Cascade updates

1. Scan same-topic articles for ripple effects: this source might add evidence to, refine, or contradict claims in them.
2. Scan `wiki/index.md` for related cross-topic articles. A new paper on attention often updates `tokenization/` or `efficiency/` articles too.
3. **Refresh `updated` on every materially-changed article.** Filesystem mtime is not the same — `updated` tracks knowledge change.
4. **Archive pages (`archived: true`) are NEVER cascade-updated.** They are point-in-time syntheses.

## Step 4 — Post-ingest

1. Update `wiki/index.md`: add new articles, refresh summary/updated dates for cascade-updated ones.
2. Update `wiki/index.base` (delegate to the `obsidian-bases` sub-skill). Usually no change unless the schema drifted.
3. Append to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] ingest | <primary article>
   - Updated: <cascade-updated article>
   - Updated: <another cascade-updated article>
   ```

## File-write contract

- **Writes:** one new `raw/` file (or a `-revN.md`), zero-to-many new `wiki/` articles, updates to existing articles cascade-touched, `wiki/index.md`, `wiki/index.base` (if schema changed), `wiki/log.md`.
- **Never touches:** `raw/` files other than the one being added; archived articles; `wiki.config.md`; per-vault `prompts/`.
