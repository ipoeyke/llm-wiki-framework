# Digest

Produce a self-contained HTML recap of wiki activity for a time window. The one place the framework breaks from pure Markdown — a digest is a presentation artifact (read once, browsed, sometimes shared), not editable wiki corpus.

## Triggers

- `/wiki:digest [window]`
- "weekly digest", "what's new in my wiki"
- Scheduled run (cadence from `wiki.config.md` — `weekly` | `biweekly` | `monthly`; default `weekly`)

## Inputs

A time window. Defaults from cadence:

- **`weekly`** — the current ISO week (Monday 00:00 to Sunday 23:59 in the user's local timezone). Filename slug: `YYYY-Www` (e.g., `2026-W21-recap.html`).
- **`biweekly`** — two consecutive ISO weeks.
- **`monthly`** — the current calendar month.
- **Explicit window** — `--week 2026-W20` or a date range.

## Empty-period behavior

If the window contains **no** `wiki/log.md` activity (no ingests, no syncs, no archives, no lints with auto-fixes or reported findings), **do not write a file**. Report to the user:

> No wiki activity for {{window}}. Skipping digest. Run with `--force` to produce an empty recap.

This prevents `digests/` from accumulating boilerplate during midterm weeks or vacation periods.

## Behavior

1. **Read `wiki/log.md`** and select entries within the window. Use those entries as the ground truth — **never invent activity not in the log.**
2. **Pull frontmatter from the touched articles** (titles, summaries, `topics`, `updated`).
3. **Scan touched articles for callouts** created or modified in this window: `> [!conflict]` (contradictions), `> [!question]` (open questions, split into raised vs. resolved).
4. **Identify themes:**
   - Which topics gained the most coverage?
   - Which articles got cascade-updated the most? (count log entries referencing each article)
   - Which contradictions arose?
   - Which open questions were resolved? raised?
   - Which new concepts emerged?
   - Where are the coverage gaps? (concepts mentioned across multiple articles but lacking a dedicated page — same heuristic Lint uses)
5. **Render `references/digest-template.html`** into `digests/<filename>.html` (at the vault root — digests are presentation artifacts, not wiki corpus), substituting:
   - `{{wiki_title}}` — from `wiki.config.md`
   - `{{period_label}}` — e.g., "Week 21, 2026"
   - `{{date_range}}` — e.g., "May 18 – May 24, 2026"
   - `{{source_count}}`, `{{sources_ingested}}`, `{{articles_touched}}`, `{{articles_created}}`, `{{contradictions_surfaced}}`, `{{questions_raised}}`, `{{questions_resolved}}` — counts from the log + frontmatter scan.
   - `{{top_articles_list}}`, `{{new_articles_list}}`, `{{conflicts_list}}`, `{{questions_raised_list}}`, `{{questions_resolved_list}}`, `{{gaps_list}}` — rendered HTML fragments matching the commented-out shape in the template.
   - `{{vault}}` — vault name (URL-encoded) for the `obsidian://open?vault={{vault}}&file={{path}}` URI.
6. **Article links use the `obsidian://` URI scheme** so clicking opens the article in Obsidian:
   ```html
   <a href="obsidian://open?vault=MyVault&file=wiki/cryptography/rsa.md">RSA</a>
   ```
   The `file` path is relative to the vault root, URL-encoded.
7. **Verify the output is self-contained.** No `<script src="https://...">`, no `<link href="https://fonts...">`, no analytics tags, no tracking pixels. All CSS is inlined in `<style>`. The template already enforces this — confirm before writing.
8. **Append a "Digests" section to `wiki/index.md`** if not present, and add an entry:
   ```markdown
   - [2026-W21 recap](../digests/2026-W21-recap.html) — 4 sources, 11 articles touched
   ```
   Use a standard Markdown link (not a wikilink) so Obsidian routes the `.html` to the system browser. The `../` is because `index.md` lives in `wiki/` while digests live at the vault root.
9. **Log:** `## [YYYY-MM-DD] digest | week N | <filename>`.

## Verification before reporting done

Open the produced HTML in a browser and confirm:
- DevTools → Network shows **zero external requests** when the page loads.
- An article link's `href` is an `obsidian://open?vault=...&file=...` URI.
- The layout is readable at both desktop and mobile widths.

## File-write contract

- **Writes:** one new `digests/YYYY-Www-recap.html`; `wiki/index.md` (digest entry); `wiki/log.md`.
- **Never writes:** any `wiki/*.md` article; raw files; `wiki/index.base`; `wiki.config.md`; per-vault `prompts/`.
- **Never invents:** activity not present in `wiki/log.md` within the window.
