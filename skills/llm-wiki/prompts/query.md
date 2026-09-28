# Query

Answer a question using the wiki's compiled knowledge. Default behavior writes nothing — the answer lands in conversation, with optional archiving.

## Triggers

- `/wiki:query <question>`
- "what do I know about X?", "summarize my notes on Y", "compare A and B from my wiki"
- Any substantive question in a vault initialized as an LLM wiki

## Inputs

The question (and an optional explicit "archive this" follow-up).

## Behavior

1. **Locate relevant articles, grep first.** Do not read the whole index up front.
   - Grep the question's key terms (names, methods, and synonyms) across article frontmatter in `wiki/**/*.md`: the `title:`, `aliases:`, `catalog:` and `summary:` lines. Then grep bodies for any term that returned too few hits.
   - Read `wiki/index.md` (topics, hubs, recent updates; small) to scope the question, then read the one or two most relevant `wiki/<topic>/_index.md` files when you need a topic's full list.
   - Query `wiki/index.base` if the question is structural (e.g., "what are my open questions in cryptography?"). Delegate Base reads to the `obsidian-bases` sub-skill.
   - **Active pages by default.** Skip pages whose frontmatter has `status: superseded` or `status: merged`, and follow their `superseded_by` link to the current page instead. Read a superseded page only when the question is historical, names that page's subject explicitly, or asks how something changed; then say in the answer that it is superseded and by what.
2. **Read those articles** in full before composing the answer. Don't synthesize from titles + summaries alone. Past `review_by` means the page may be stale: say so when its claims carry the answer.
3. **Prefer wiki content over training knowledge.** This is the central rule. If the wiki has nothing relevant, **say so explicitly** rather than answering from priors. The user invoked the wiki because they want a wiki-grounded answer. Filling gaps with general knowledge defeats the purpose and hides the gap from the user.
4. **Answer in conversation, using wikilinks** (`[[Article]]`) so the user can click through inside Obsidian. Inline `> [!source]` style attribution is fine where it helps.
5. **Log citations, write nothing else.** After answering, record the pages you cited, from the vault root:
   ```
   python3 prompts/tools/wiki_maint.py log-query --question "<the question>" --cited "<Title 1>" "<Title 2>"
   ```
   This appends one line to `.query-log.jsonl`, which the consolidation pass uses to rank demotion candidates. Skip it when you cited nothing. Query writes no other file by default.

## Sub-operation: Archive (opt-in only)

Triggered by an explicit follow-up: "archive this", "save this answer to the wiki", "file this".

When archiving:

1. **Write a new article**, never merge into an existing one. Archives are point-in-time syntheses, not raw material.
2. **Pick the most relevant topic directory** for the new article's location. Reuse, never fragment.
3. **Use `references/archive-template.md`** as the structural template. Set frontmatter:
   - `archived: true`
   - `sources:` — wikilinks to the **wiki articles** cited, never raw sources directly (archives compose at the wiki level)
   - `title:` — derived from the query (e.g., `Transformer Architectures Overview`)
4. **Give the archive a `catalog:` line and `status: active`**, then regenerate indexes: `python3 prompts/tools/wiki_maint.py index`. The script prefixes archived rows with `[Archived]`. Never hand-edit index rows.
5. **Log:** `## [YYYY-MM-DD] query | Archived: <title>`.

## Sub-operation: Suggest archiving (proactive, never auto)

If a query produces a synthesis you judge **genuinely new and reusable** (not a one-off answer, not trivially answerable by reading one article), suggest archiving at the end of the answer. One sentence: "This synthesis seems worth archiving as `<proposed-title>` — say so if you'd like me to save it."

**Wait for explicit confirmation.** Never archive silently.

## File-write contract

- **Default (no archive):** appends one line to `.query-log.jsonl`; nothing else.
- **With archive:** one new `wiki/<topic>/<slug>.md` (never modifies existing articles), `wiki/index.md` and `wiki/<topic>/_index.md` (script only), `wiki/log.md`, `.query-log.jsonl`.
- **Never touches:** raw files; existing articles (archives never merge); `wiki.config.md`; per-vault `prompts/`.
