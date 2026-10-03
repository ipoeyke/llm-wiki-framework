# Sync

Batch-process new `raw/` files into the wiki. The "I dumped a week of Web Clipper clippings, catch up" operation.

## Triggers

- `/wiki:sync`
- "sync the wiki", "process my inbox", "catch up"
- Scheduled run (default: daily or on-demand)

## Inputs

None. Sync operates on the delta since the last sync.

## Behavior

1. **Determine the delta.** Find every `raw/<topic>/*.md` file with `collected` (or filesystem mtime as fallback) newer than the last sync timestamp. The last-sync timestamp is recorded in `wiki/log.md` (the most recent `## [YYYY-MM-DD] sync` or `## [YYYY-MM-DD] init` entry).
2. **Relocate Web-Clipper drops** out of `raw/inbox/` or `raw/<numeric-course-id>/` into subject-matter topic directories (`raw/cryptography/`, etc.) per the **topics-are-subject-matter** rule. Ask the user when the right topic isn't obvious. Update each file's `topics` frontmatter to match its new location.
3. **For each new `raw/` file, run the Ingest compile step** for the current flavor (read from `wiki.config.md`):
   - Load `prompts/ingest/<flavor>.md` and execute Step 2 (Compile) onward — Step 1 (Fetch) is already done; these files exist.
   - Apply the same `> [!conflict]` discipline, page-type vocabulary, voice, and personal-note handling.
   - **Write-time admission first** (Step 2.0 of the ingest prompt): decide new page, update existing page, or merge-only before writing anything.
   - Every new article gets `catalog:` (one double-quoted sentence, at most 25 words) and `status: active`. Do not write `review_by`; step 5 computes it.
   - **Successor (no retirement):** when a new page describes the direct successor of an existing page's subject (a new version of the same product, model, spec or standard that replaces it), leave the predecessor `status: active` and write no `supersedes` or `superseded_by`. Cascade a dated successor subsection and link onto the predecessor, and add `Supersession candidate: [[Old]] by [[New]]` to the log entry. Retirement happens only in the consolidation pass.
4. **Batch the cascade updates.** This is why Sync exists separately from Ingest: instead of touching a popular concept page once per source, **consolidate**. Compute the union of cascade-touched articles across all new sources, then write each touched article once with the combined updates. One consolidated walk beats N small ones. Pages with `status: superseded` or `status: merged` are never cascade-updated, same as archived pages; add new evidence to their `superseded_by` target instead. When a touched article's gist changes, rewrite its `catalog:` line too.
4a. **Backlink new pages in older articles.** After the cascade, link the **first plain-text mention** of each newly created page in every *other* article that does not already link it. Match the page's title or any `aliases` entry that is at least 4 characters, case-sensitive, as a whole term: not preceded by a letter, digit or hyphen, and not followed by one or by `.digit` (so `Claude Opus 5` never matches inside `Claude Opus 5.5`). Skip frontmatter, headings, fenced code, inline code, existing wikilinks, markdown links, URLs, and `> [!source]` lines. Write `[[Title]]` when the matched text equals the title, else `[[Title|matched text]]`, with the pipe escaped as `\|` inside table rows. One link per new page per article; never rewrite surrounding prose. Refresh `updated` on each touched article (step 5 regenerates its index row), and list every link added in the log entry. Merge these edits into the consolidated cascade write when the article is already being touched.
5. **Regenerate lifecycle dates and indexes with the script, never by hand.** From the vault root run:
   ```
   python3 prompts/tools/wiki_maint.py lifecycle
   python3 prompts/tools/wiki_maint.py index
   python3 prompts/tools/wiki_maint.py check
   ```
   `lifecycle` fills `status` defaults and recomputes `review_by` from `updated`. `index` rewrites `wiki/index.md` (topics, hubs, recent updates, preserved Digests section) and every `wiki/<topic>/_index.md` (one catalog row per active article). `check` must report zero problems except "split candidate" lines, which are report-only; fix any missing `catalog` it lists by writing the line into that article's frontmatter, then rerun `index`.
6. **Update `wiki/index.base`** (delegate to `obsidian-bases`) only if the article frontmatter schema drifted.
7. **Log a single consolidated entry** to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] sync | N sources processed, M articles updated
   - <primary-article-1>
   - <primary-article-2>
   Supersession candidate: [[Old]] by [[New]]
   ```
   Include one `Supersession candidate:` line per successor pair from step 3.

8. **Consolidation.** Run `python3 prompts/tools/wiki_maint.py due`. If it prints `DUE`, after the sync log entry is written, run the consolidation pass (`prompts/consolidate.md`) as a separate subagent, without asking. End the sync report with one line naming its report file. Also mention any page that `check` newly lists over the hub size cap.

## Idempotency

Sync is safe to run multiple times. The second run finds zero delta (the first run's log entry advances the timestamp) and exits with a "nothing to sync" message — no log entry written.

## File-write contract

- **Writes:** moves to `raw/` files (only when relocating from `raw/inbox/` or `raw/<course-id>/`); zero-to-many new `wiki/` articles; updates to cascade-touched articles; lifecycle frontmatter on new pages (`catalog`, `status: active`, `review_by`); `wiki/index.md` and `wiki/<topic>/_index.md` (script-generated only); `wiki/index.base` (if schema changed); `wiki/log.md`.
- **Never touches:** raw file *content*; archived, superseded or merged articles' bodies; lifecycle `status`, `supersedes` and `superseded_by` on existing pages; `wiki.config.md`; per-vault `prompts/`; `.query-log.jsonl`.
