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
9. **Use `references/article-template.md` as the structural template** for new articles.

## Step 3 — Cascade updates

1. Scan same-topic articles for ripple effects.
2. Scan `wiki/index.md` for related cross-topic articles. A `network-security/` reading often updates `cryptography/` articles too.
3. **Refresh `updated` on every materially-changed article.** Knowledge change, not mtime.
4. **Archive pages (`archived: true`) are never cascade-updated.**

## Step 4 — Post-ingest

1. Update `wiki/index.md`: new articles added, summaries/updated refreshed.
2. Update `wiki/index.base` (delegate to `obsidian-bases`) if frontmatter schema drifted.
3. Append to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] ingest | <primary article>
   - Updated: <cascade-updated article>
   ```

## File-write contract

- **Writes:** one new `raw/` file (or `-revN.md`), zero-to-many new `wiki/` articles, updates to cascade-touched articles, `wiki/index.md`, `wiki/index.base` (if schema changed), `wiki/log.md`.
- **Never touches:** other `raw/` files; archived articles; `wiki.config.md`; per-vault `prompts/`.
