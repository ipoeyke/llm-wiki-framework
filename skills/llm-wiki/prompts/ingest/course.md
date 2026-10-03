# Ingest — course flavor

Ingest a single source (URL, file, pasted text, Web Clipper output, or MCP-sourced content) into a `course`-flavored wiki.

## Triggers

- `/wiki:ingest <input>`
- "ingest this", "add to wiki", "ingest <url>"
- A URL or file mentioned with intent to add to the wiki

For a batch of clippings (typical in coursework), the user usually invokes `/wiki:sync` instead — that's Sync's job, and this prompt's Step 2 logic is what Sync calls.

## Inputs

A single source. Resolve before proceeding:

- **URL** — fetch directly. Use `defuddle` from `kepano/obsidian-skills` for web pages.
- **File path** — PDFs (typical for lecture slides, papers) follow the binary-source policy.
- **Pasted text** — ask for `title` and a `source_url`/`source_ref` if not obvious.
- **Web Clipper output** — primary path for coursework. Already in `raw/` after the user clips; this prompt's Step 2 onward applies.
- **MCP-sourced content** — pull via the connected MCP server.

## Step 1 — Fetch into `raw/`

1. **Pick or reuse a topic subdirectory.**
   - **Critical (course flavor):** topics are subject-matter, **never** weeks, lecture numbers, content types, or course phases.
   - **Reject:** `raw/week-2/`, `raw/lectures/`, `raw/problem-sets/`, `raw/midterm-review/`, `raw/announcements/`. If the user asks for one of these, push back: ask for a subject-matter alternative.
   - **Use:** `raw/cryptography/`, `raw/network-security/`, `raw/access-control/`, `raw/replication/`, etc.
   - If Web Clipper has placed the file under `raw/<course-id>/` or `raw/inbox/`, relocate to a subject-matter topic during this step.
2. **Save as `raw/<topic>/YYYY-MM-DD-<slug>.md`.** Slug from title, kebab-case, max 60 chars.
3. **Numeric suffix on filename collision.**
4. **Binary source policy** (PDFs, scanned slides, lecture-recording audio): store binary at `raw/<topic>/YYYY-MM-DD-<slug>.<ext>` AND write a `.md` sidecar with extracted text (OCR if needed) and `binary: [[raw/<topic>/<file>.<ext>]]` frontmatter. Sidecar is the source of truth.
5. **Threaded content** (Canvas discussion boards, email chains): one `.md` per thread — `## Original post` then `### Reply by <author> [<date>]` sections. Splitting destroys conversational context.
6. **Required frontmatter:** `title`, `collected`, `published` (or `Unknown`), `topics`, `content_type`, plus one of `source_url`/`source_ref`. Course-specific `content_type` values: `lecture`, `assignment`, `reading`, `discussion`, `announcement`, `syllabus`, `transcript`, plus `personal-note` for user reflections.
7. **Optional course-specific frontmatter** (pass-through; not validated): `canvas_course_id`, `canvas_module_id`, `due_date`, `assignment_type`.
8. **Preserve content verbatim.** Lectures, problem sets, professor's announcements — verbatim. Even confusing prose stays as written.
9. **Idempotency:** same source_url/source_ref + same hash → refuse with `skipped duplicate` log. Different hash → revision file (`-revN.md`) with `supersedes:` / `superseded_by:` pointers. This is critical for coursework: Canvas pages get edited, assignment descriptions get clarified, discussions get new replies. Revisions preserve the audit trail.

## Step 2 — Compile into `wiki/` (course-specific)

Delegate to the `obsidian-markdown` sub-skill for OFM syntax.

0. **Write-time admission.** Before writing, classify the source against the wiki:
   - **Update-only:** an existing page already covers this subject (same paper, same release, same event). Add the source to that page's `sources` and fold in what is new. No new page.
   - **Merge-only:** a single-source item with no substance of its own beyond a data point for an existing page. Add a dated subsection to that parent page. No new page.
   - **New page:** the source introduces a topic, definition, worked example or problem set no existing page covers.
   Grep `title:`, `aliases:` and `catalog:` across `wiki/**` and read the one or two relevant `wiki/<topic>/_index.md` files to find the existing page. State the admission decision and its reason in the log entry.
1. **Decide:** merge into existing topic article(s), create new article(s), or both. A lecture on RSA both updates a `topic` page for RSA AND may spawn `definition` and `worked-example` pages.
2. **Page-type vocabulary** (`course` flavor):
   - `topic` — default. A subject-matter area within the course (e.g., "RSA", "BGP", "Paxos"). Builds up from lectures + readings + your notes.
   - `definition` — single term, sharp definition. Short. Linked from many topic pages.
   - `worked-example` — a problem solved start-to-finish. Frontmatter includes `difficulty` and `source` (e.g., "ps3-q2").
   - `problem-set` — meta-page linking worked-examples for a set or exam, plus topic pages it covers.
3. **Voice:** pedagogical. Build from primitives. If a topic page assumes a concept, **link** to its definition rather than gloss-explaining inline.
4. **Citation discipline:** lectures and readings are wikilinked; cite the lecture date or slide where available via `> [!source]` callouts. When professor and textbook disagree, surface with `> [!conflict]`.
5. **Personal-note handling:** if `content_type: personal-note`, surface only as `> [!question]` callouts in the relevant topic page. **Never cite a personal-note as if it were the professor or textbook saying it.** This rule is doubly important in `course` flavor — confusion about who-said-what is a study-time bug.
6. **Cross-link aggressively.** A lecture typically touches 3–10 wiki pages: the topic page, prerequisite definitions, prior worked examples that exercise the same concept, related topic pages.
7. **Worked-example back-links:** each worked-example links to the topic page(s) it exercises. Each topic page maintains a "Worked examples" section linking back.
8. **Conflicts:** if a new source conflicts with existing wiki content (common when re-watching a lecture clarifies an earlier confusion), add a `> [!conflict]` callout. Do not silently rewrite.
9. **Use `references/article-template.md` as the structural template** for new articles, plus the lifecycle fields: `catalog:` (one double-quoted sentence, at most 25 words: what it is and its one distinguishing claim; no title repeat) directly after `summary`, and `status: active`. Leave `review_by` to the script.
10. **Successor (no retirement).** If the new page describes the direct successor of an existing page's subject (a new version of the same product, model, spec or standard that replaces it), leave the predecessor `status: active` and write no `supersedes` or `superseded_by`. Cascade a dated successor subsection and link onto the predecessor, and add `Supersession candidate: [[Old]] by [[New]]` to the log entry. Retirement happens only in the consolidation pass. Versions that coexist (different sizes, tiers or product lines) are not successors.

## Step 3 — Cascade updates

1. Scan same-topic articles for ripple effects.
2. Grep article frontmatter (`title:`, `aliases:`, `catalog:`) across `wiki/**` for related cross-topic articles; open a topic's `_index.md` when you need its full list. A `network-security/` reading often updates `cryptography/` articles too.
3. **Refresh `updated` on every materially-changed article.** Knowledge change, not mtime.
4. **Archive pages (`archived: true`) are never cascade-updated.** The same holds for `status: superseded` and `status: merged` pages: put new evidence on their `superseded_by` target.
5. If a touched article's gist changed, rewrite its `catalog:` line.

## Step 4 — Post-ingest

1. Regenerate lifecycle dates and indexes from the vault root: `python3 prompts/tools/wiki_maint.py lifecycle`, then `index`, then `check`. Never hand-edit `wiki/index.md` rows or any `_index.md`. `check` must be clean apart from report-only split candidates.
2. Update `wiki/index.base` (delegate to `obsidian-bases`) if frontmatter schema drifted.
3. Append to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] ingest | <primary article>
   - Updated: <cascade-updated article>
   ```

## File-write contract

- **Writes:** one new `raw/` file (or `-revN.md`), zero-to-many new `wiki/` articles, updates to cascade-touched articles, lifecycle frontmatter on new pages, `wiki/index.md` and `wiki/<topic>/_index.md` (script only), `wiki/index.base` (if schema changed), `wiki/log.md`.
- **Never touches:** other `raw/` files; archived, superseded or merged articles' bodies; `wiki.config.md`; per-vault `prompts/`.
