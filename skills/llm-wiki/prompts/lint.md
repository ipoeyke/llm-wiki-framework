# Lint

Health check on the wiki. Two strictly-separated categories: deterministic checks **auto-fix**, heuristic checks **report only**.

## Triggers

- `/wiki:lint`
- "lint the wiki", "health check", "wiki quality pass"
- Scheduled run (default: weekly, alongside or before digest)

## Inputs

None.

## Deterministic checks — AUTO-FIX

These checks have a single objectively correct fix. Apply directly. Each fix is logged.

1. **Index consistency and lifecycle defaults (scripted).** The index is two-level and generated from frontmatter: `wiki/index.md` lists topics, and `wiki/<topic>/_index.md` lists each topic's active articles. From the vault root run:
   ```
   python3 prompts/tools/wiki_maint.py lifecycle
   python3 prompts/tools/wiki_maint.py index
   python3 prompts/tools/wiki_maint.py check
   ```
   `lifecycle` fills missing `status` defaults and recomputes `review_by` from `updated`; `index` regenerates every index file from current frontmatter, so missing and stale rows cannot persist; `check` lists what remains. Log the number of files each command changed. Never hand-edit index rows. Articles are every `wiki/**/*.md` except `index.md`, `log.md` and `_index.md`.
2. **Internal links (wikilinks).** Every wikilink in article bodies and frontmatter resolves to an existing file.
   - Dead wikilinks: search the vault for a matching basename (case-insensitive, allowing for known synonyms in `wiki.config.md` if present).
     - **Exactly one match:** auto-relink.
     - **Zero or multiple matches:** report only — don't guess.
3. **Raw references.** Every `sources` frontmatter entry resolves to an existing `raw/` file. Same exactly-one-match auto-fix rule.
4. **See-also pruning.** Within each topic's articles, links in `## See also` sections that point to deleted files are removed.
5. **Frontmatter validation.** Required properties (`title`, `summary`, `updated`) are present.
   - `title` missing: fill from the article's H1 heading if present.
   - `summary` missing: leave as `""` and report — don't invent summaries.
   - `updated` missing: fill from the most recent `## [YYYY-MM-DD]` entry in `wiki/log.md` that mentions this article, falling back to filesystem mtime as last resort.
6. **`wiki/index.base` regeneration.** If the Base file's schema has drifted from current article frontmatter (e.g., a new property is widely adopted), regenerate from `references/index-base-template.base`. Delegate to the `obsidian-bases` sub-skill.
7. **`open_questions` flag sync.** The `open_questions` frontmatter flag must mirror whether the article body contains at least one `> [!question]` callout (see the universal rule in SKILL.md — Bases cannot filter on body content, so the flag powers the index's "Open questions" view). Both drift directions are deterministic:
   - Body has a `> [!question]` callout but frontmatter lacks `open_questions: true`: **set it**.
   - Frontmatter has `open_questions: true` but the body has no `> [!question]` callout: **remove the flag**.
   - This check reads callouts only — it never adds, removes, or rewrites the `> [!question]` callouts themselves.
8. **Frontmatter YAML colon quoting.** A top-level scalar line `key: value` whose `value` is unquoted (first non-space char is not `"` `'` `[` `{` `|` `>`) and contains a colon-followed-by-whitespace, or ends in a colon, is invalid YAML — the parser reads the inner colon as a nested mapping key and the whole frontmatter block silently fails to load (breaking index summaries, Bases views, and every other flag). The fix is unambiguous: **wrap the value in double quotes**, escaping any literal `"` as `\"` and any `\` as `\\`. Applies to `summary`, `title`, `external_sources`, and any other string scalar. Does not touch block/flow values (lists, `|`/`>` blocks, already-quoted strings) or a colon with no trailing space (e.g. `L2:Law`, which is valid unquoted). Verify each fixed block re-parses.
9. **Unlinked mentions of new pages.** For every article whose `created` date falls on or after the date of the previous `lint` entry in `wiki/log.md`, link the **first plain-text mention** of each newly created page in every *other* article that does not already link it. Match the page's title or any `aliases` entry that is at least 4 characters, case-sensitive, as a whole term: not preceded by a letter, digit or hyphen, and not followed by one or by `.digit` (so `Claude Opus 5` never matches inside `Claude Opus 5.5`). Skip frontmatter, headings, fenced code, inline code, existing wikilinks, markdown links, URLs, and `> [!source]` lines. Write `[[Title]]` when the matched text equals the title, else `[[Title|matched text]]`, with the pipe escaped as `\|` inside table rows. One link per new page per article; never rewrite surrounding prose. Refresh `updated` on each touched article (then rerun `wiki_maint.py lifecycle` and `index`), and list every link added in the log entry.

**The auto-fix list above is closed.** Do not invent new auto-fixes. Anything not on this list goes in the report-only category below.

## Heuristic checks — REPORT ONLY, never auto-fix

These checks are judgment calls. Surface findings in a Markdown report so the user can decide. **Never silently rewrite article content based on a heuristic.**

- **Factual contradictions across articles** — two articles assert claims that disagree, but no `> [!conflict]` callout exists. Report both sources and locations.
- **Outdated claims** — an article cites a source from year X, and a later-ingested source (year Y > X) contradicts or extends it without a corresponding update. Date-based heuristic — surface, don't act.
- **Missing conflict annotations** — sources cited in the same article clearly disagree (heuristic match) but no `> [!conflict]` callout is present.
- **Orphan pages** — articles with zero inbound wikilinks. List them; the user might want to cross-link or delete.
- **Missing cross-topic references** — a concept that's a wiki article in another topic is mentioned (as plain text) in this article but not wikilinked.
- **Concepts frequently mentioned but lacking a dedicated page** — a candidate "should-be-a-page" list. Threshold heuristic.
- **Archive pages whose cited articles have changed substantially since archival** — the archive may have drifted from current wiki state. Surface; let the user decide whether to re-archive.
- **Thin pages** — articles below a word-count floor (default 80 words) or single-source. Often a sign of premature page creation.
- **Missing or overlong `catalog`**: listed by `wiki_maint.py check`. Report; don't invent catalog lines in lint (sync and ingest author them).
- **Hub pages over the size cap**: `check` lines ending "split candidate". Report; splits happen only in the consolidation pass.
- **Past `review_by`**: run `python3 prompts/tools/wiki_maint.py candidates` and report the counts of demotion candidates and overdue pages. Never demote, merge or supersede from lint.
- **Consolidation due**: run `python3 prompts/tools/wiki_maint.py due` and report its line when it says `DUE`.

## Output

A `## Lint report — YYYY-MM-DD` block in conversation:

```markdown
## Lint report — 2026-05-24

### Auto-fixed (N)
- Added missing index entry: [[Article A]]
- Re-linked dead wikilink in [[Article B]]: `[[Old Name]]` → `[[New Name]]`
- Filled missing `updated` on [[Article C]] from log
- Set `open_questions: true` on [[Article H]] (body has a `> [!question]` callout, flag was missing)

### Reported — needs your call (M)
- **Possible contradiction**: [[Article D]] and [[Article E]] disagree on <claim>. Sources: [[raw/...]], [[raw/...]]. Suggested: add `> [!conflict]` in [[Article D]].
- **Orphan**: [[Article F]] has no inbound wikilinks.
- **Thin page**: [[Article G]] (42 words, single source). Consider merging into [[Parent Article]] or expanding.
```

## Log entry

```
## [YYYY-MM-DD] lint | N issues found, M auto-fixed, K reported
```

## File-write contract

- **Writes:** existing `wiki/*.md` articles that needed deterministic fixes (frontmatter fills including `status` and `review_by` defaults, YAML colon quoting, dead-link relinking, see-also pruning, first-mention links to new pages); `wiki/index.md` and `wiki/<topic>/_index.md` (script only); `wiki/index.base` (if regenerated); `wiki/log.md`.
- **Never writes:** new articles; raw files; article body content based on heuristic findings; `catalog` lines; lifecycle status changes (`superseded`, `merged`); `wiki.config.md`; per-vault `prompts/`.
