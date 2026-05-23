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
4. **Batch the cascade updates.** This is why Sync exists separately from Ingest: instead of touching a popular concept page once per source, **consolidate**. Compute the union of cascade-touched articles across all new sources, then write each touched article once with the combined updates. One consolidated walk beats N small ones.
5. **Update `wiki/index.md`** in one pass: add all new articles, refresh summaries and `updated` dates for every cascade-touched article.
6. **Update `wiki/index.base`** (delegate to `obsidian-bases`) only if the article frontmatter schema drifted.
7. **Log a single consolidated entry** to `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] sync | N sources processed, M articles updated
   - <primary-article-1>
   - <primary-article-2>
   ```

## Idempotency

Sync is safe to run multiple times. The second run finds zero delta (the first run's log entry advances the timestamp) and exits with a "nothing to sync" message — no log entry written.

## File-write contract

- **Writes:** moves to `raw/` files (only when relocating from `raw/inbox/` or `raw/<course-id>/`); zero-to-many new `wiki/` articles; updates to cascade-touched articles; `wiki/index.md`; `wiki/index.base` (if schema changed); `wiki/log.md`.
- **Never touches:** raw file *content*; archived articles; `wiki.config.md`; per-vault `prompts/`.
