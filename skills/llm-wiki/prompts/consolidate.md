# Consolidate

Keep the wiki bounded. `raw/` is never pruned; this pass moves `wiki/` pages through their lifecycle (`active` → `superseded` or `merged`) and splits oversized hubs. Policy lives in the `lifecycle:` block of `wiki.config.md` frontmatter and the "Lifecycle and growth" universal rules in the skill. Deterministic parts run through `prompts/tools/wiki_maint.py`.

The pass has two phases. **Report** is the default and changes no article. **Apply** runs only on the user's explicit approval of items in a named report. This follows the framework rule that heuristic judgments are never applied silently.

## Triggers

- `/wiki:consolidate`, "consolidate the wiki", "run the consolidation pass", "prune the wiki".
- A sync or lint report saying "Consolidation pass due".
- Apply phase only: "apply consolidation <date> items 1, 3, 5", "apply all from the <date> consolidation report".

Run as a subagent (see "Execution: delegate the heavy operations to a subagent" in the skill).

## Phase 1: Report

1. **Refresh state.** From the vault root:
   ```
   python3 prompts/tools/wiki_maint.py lifecycle
   python3 prompts/tools/wiki_maint.py index
   python3 prompts/tools/wiki_maint.py candidates --json > "$TMPDIR/wiki-candidates.json"
   ```
2. **Judge each candidate group.** Read each page in full before proposing anything for it. Every proposal names one action, the reason, and the evidence.
   - **`demotion`** (paper page past `review_by`, single-source, ≤2 inbound links, no conflict or open question). Find the parent concept page by grepping `title:`, `aliases:` and `catalog:`. Propose **merge into [[Parent]] under `### <Title> (YYYY-MM-DD)`**, quoting the one to three Insights that would move. If no parent fits, propose **keep** with a new `review_by` 180 days out and say why. Rank by `cited_180d` ascending, then inbound links.
   - **`overdue_review`** (past `review_by` but multi-source, linked, or carrying a conflict or question). Check whether newer wiki pages extend or contradict it. Propose one of: **keep** (new `review_by`), **supersede by [[Newer]]**, or **add an outdated warning** naming the newer evidence.
   - **`fast_decay_topics`** (all active pages in topics listed under `lifecycle.topic_half_life_days`). Group pages that describe versions of the same thing (a product, model, spec or standard). Propose **supersede [[Old]] by [[New]]** only for direct successors in the same line. Coexisting versions (different sizes, tiers, or open and closed variants) and different product lines are not successors. When unsure, leave it out and say so.
   - **`hubs_over_cap`** (body over ~5,000 tokens). Propose a split plan: which `##` sections move to which new child page titles, and the 2 to 4 sentence summary the parent keeps for each. Moved text is carried verbatim; the split never rewrites prose. Prefer splitting along sections that already read as standalone topics. Propose **no split** when the page is long because it is one tightly argued piece.
   - **`orphans`** (no inbound links). Propose where to link them from, or a merge if the page is thin.
   - **`review_due_30d`**. List only; no action yet.
3. **Write the report** to `reports/consolidation-YYYY-MM-DD.md`: a short header with counts per group and whether `.query-log.jsonl` had data, then numbered proposals grouped by action, each with the page link, the action, one or two sentences of reason, and the evidence. Close with "Approve by number, for example: apply consolidation YYYY-MM-DD items 1-4, 7."
4. **Log:** `## [YYYY-MM-DD] consolidate | report | N proposals (reports/consolidation-YYYY-MM-DD.md)`. This entry resets the cadence that `wiki_maint.py due` checks.
5. **Stop.** Change no article in this phase.

## Phase 2: Apply (approved items only)

1. **Back up first.** Copy `wiki/` to `.backups/YYYY-MM-DD-consolidate/` before the first edit.
2. **Apply each approved item.** Never delete a file. Never touch `raw/`.
   - **Merge into parent.** Add a dated subsection to the parent carrying the moved Insights, citing the same `[[raw/...]]` sources and linking back to the merged page. Add those raw files to the parent's `sources`. Bump the parent's `updated`, and rewrite its `catalog` if its gist changed. On the merged page set `status: merged` and `superseded_by: "[[Parent#Subsection]]"`, and add one line at the top of the body: `> [!warning] Merged into [[Parent#Subsection]] on YYYY-MM-DD.` Keep the rest of the body.
   - **Supersede.** On the old page set `status: superseded`, `superseded_by: "[[New]]"`, and add `> [!warning] Superseded by [[New]] (YYYY-MM-DD).` at the top of the body. On the new page add `supersedes: "[[Old]]"`.
   - **Keep.** Set `review_by` to the approved date by hand. The script never shortens it.
   - **Outdated warning.** Add one `> [!warning]` line naming the newer evidence and bump `updated`.
   - **Split.** Create each child page with full frontmatter (`title`, `summary`, `catalog`, `topics`, `sources` limited to the raw files its sections cite, `type`, `created`, `updated`, `archived: false`, `status: active`). Move the approved sections verbatim. In the parent, replace each moved section with its approved summary and a link to the child, and trim `sources` to what the parent still cites. Repoint inbound `[[Parent#Moved Section]]` links to the child.
   - **Link orphans.** Add the approved links in the named pages, first mention only, same matching rules as the sync backlink step.
3. **Regenerate and verify.** Run `lifecycle`, `index` and `check`. Confirm zero dead wikilinks (alias-aware, case-insensitive, NFC-normalized), every frontmatter block parses, and every non-active page's `superseded_by` resolves.
4. **Log:** `## [YYYY-MM-DD] consolidate | applied N of M from reports/consolidation-YYYY-MM-DD.md`, listing each page changed and its action.

## File-write contract

- **Report phase writes:** `reports/consolidation-YYYY-MM-DD.md`; `wiki/log.md`; index files and lifecycle defaults through the script.
- **Apply phase writes:** approved articles only; new child pages from approved splits; `.backups/`; index files through the script; `wiki/log.md`.
- **Never:** deletes files; touches `raw/`; edits `wiki.config.md` or per-vault `prompts/`; applies an item the user did not approve.
