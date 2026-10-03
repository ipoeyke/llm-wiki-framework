# Consolidate

Keep the wiki bounded. `raw/` is never pruned; this pass moves `wiki/` pages through their lifecycle (`active` → `superseded` or `merged`) and splits oversized hubs. Policy lives in the `lifecycle:` block of `wiki.config.md` frontmatter and the "Lifecycle and growth" universal rules in the skill. Deterministic parts run through `prompts/tools/wiki_maint.py`.

The pass runs end to end without user input: it judges each candidate, applies the actions it is confident in, and writes a report that records what it did. The report is a record, not a request. It has no action items and nothing waits on approval. Pages are never deleted and retired pages keep their full body, so every change can be reversed by hand.

## Triggers

- `/wiki:consolidate`, "consolidate the wiki", "run the consolidation pass", "prune the wiki".
- Sync step 8, when `wiki_maint.py due` prints `DUE`.

Run as a subagent (see "Execution: delegate the heavy operations to a subagent" in the skill).

## 1. Refresh state and back up

From the vault root:
```
python3 prompts/tools/wiki_maint.py lifecycle
python3 prompts/tools/wiki_maint.py index
python3 prompts/tools/wiki_maint.py candidates --json > "$TMPDIR/wiki-candidates.json"
```
Copy `wiki/` to `.backups/YYYY-MM-DD-consolidate/` before the first edit.

## 2. Judge each candidate group

Read each page in full before acting on it. Decide one action per page, with a reason and evidence. Apply an action only when the evidence is clear; when unsure, leave the page as it is and record why in the report.
- **`demotion`** (paper page past `review_by`, single-source, ≤2 inbound links, no conflict or open question). Find the parent concept page by grepping `title:`, `aliases:` and `catalog:`. Action: **merge into [[Parent]] under `### <Title> (YYYY-MM-DD)`**, moving the one to three Insights worth keeping. If no parent fits, **keep** with a new `review_by` 180 days out. Work in order of `cited_180d` ascending, then inbound links.
- **`overdue_review`** (past `review_by` but multi-source, linked, or carrying a conflict or question). Check whether newer wiki pages extend or contradict it. Action: **keep** (new `review_by`), **supersede by [[Newer]]**, or **add an outdated warning** naming the newer evidence.
- **`fast_decay_topics`** (all active pages in topics listed under `lifecycle.topic_half_life_days`), plus every `Supersession candidate:` line in `wiki/log.md` since the last consolidate entry. Group pages that describe versions of the same thing (a product, model, spec or standard). Action: **supersede [[Old]] by [[New]]** only for direct successors in the same line. Coexisting versions (different sizes, tiers, or open and closed variants) and different product lines are not successors. A predecessor that a newer page says is still in service (a fallback, a cheaper tier still offered) stays active.
- **`hubs_over_cap`** (body over ~5,000 tokens). Action: **split**, choosing which `##` sections move to which new child page titles and writing the 2 to 4 sentence summary the parent keeps for each. Moved text is carried verbatim; the split never rewrites prose. Prefer sections that already read as standalone topics. Leave the page whole when it is long because it is one tightly argued piece.
- **`orphans`** (no inbound links). Action: **link** from the pages that mention the topic, or merge if the page is thin.
- **`review_due_30d`**. Note only; no action.

## 3. Apply

Never delete a file. Never touch `raw/`.
- **Merge into parent.** Add a dated subsection to the parent carrying the moved Insights, citing the same `[[raw/...]]` sources and linking back to the merged page. Add those raw files to the parent's `sources`. Bump the parent's `updated`, and rewrite its `catalog` if its gist changed. On the merged page set `status: merged` and `superseded_by: "[[Parent#Subsection]]"`, and add one line at the top of the body: `> [!warning] Merged into [[Parent#Subsection]] on YYYY-MM-DD.` Keep the rest of the body.
- **Supersede.** On the old page set `status: superseded`, `superseded_by: "[[New]]"`, and add `> [!warning] Superseded by [[New]] (YYYY-MM-DD).` at the top of the body. On the new page add `supersedes: "[[Old]]"`.
- **Keep.** Set `review_by` to the new date by hand. The script never shortens it.
- **Outdated warning.** Add one `> [!warning]` line naming the newer evidence and bump `updated`.
- **Split.** Create each child page with full frontmatter (`title`, `summary`, `catalog`, `topics`, `sources` limited to the raw files its sections cite, `type`, `created`, `updated`, `archived: false`, `status: active`). Move the sections verbatim. In the parent, replace each moved section with its summary and a link to the child, and trim `sources` to what the parent still cites. Repoint inbound `[[Parent#Moved Section]]` links to the child.
- **Link orphans.** Add links in the named pages, first mention only, same matching rules as the sync backlink step.

## 4. Regenerate and verify

Run `lifecycle`, `index` and `check`. Confirm zero dead wikilinks (alias-aware, case-insensitive, NFC-normalized), every frontmatter block parses, and every non-active page's `superseded_by` resolves. If a change fails verification and cannot be fixed, restore that page from the backup and record it in the report.

## 5. Report and log

Write `reports/consolidation-YYYY-MM-DD.md` as a record: a short header with counts per group, whether `.query-log.jsonl` had data, and the backup path; then each change made (page link, action, one or two sentences of reason, evidence); then the pages judged and left alone, with why; then the `review_due_30d` list. No proposals, action items or approval prompts.

Log: `## [YYYY-MM-DD] consolidate | N changes applied (reports/consolidation-YYYY-MM-DD.md)`, listing each page changed and its action. This entry resets the cadence that `wiki_maint.py due` checks.

## File-write contract

- **Writes:** articles it judged and changed; new child pages from splits; `.backups/`; `reports/consolidation-YYYY-MM-DD.md`; index files and lifecycle defaults through the script; `wiki/log.md`.
- **Never:** deletes files; touches `raw/`; edits `wiki.config.md` or per-vault `prompts/`.
