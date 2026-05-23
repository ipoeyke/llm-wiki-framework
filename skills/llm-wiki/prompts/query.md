# Query

Answer a question using the wiki's compiled knowledge. Default behavior writes nothing — the answer lands in conversation, with optional archiving.

## Triggers

- `/wiki:query <question>`
- "what do I know about X?", "summarize my notes on Y", "compare A and B from my wiki"
- Any substantive question in a vault initialized as an LLM wiki

## Inputs

The question (and an optional explicit "archive this" follow-up).

## Behavior

1. **Locate relevant articles.** Read `wiki/index.md` to find candidates, or query `wiki/index.base` if the question is structural (e.g., "what are my open questions in cryptography?"). Delegate Base reads to the `obsidian-bases` sub-skill.
2. **Read those articles** in full before composing the answer. Don't synthesize from titles + summaries alone.
3. **Prefer wiki content over training knowledge.** This is the central rule. If the wiki has nothing relevant, **say so explicitly** rather than answering from priors. The user invoked the wiki because they want a wiki-grounded answer. Filling gaps with general knowledge defeats the purpose and hides the gap from the user.
4. **Answer in conversation, using wikilinks** (`[[Article]]`) so the user can click through inside Obsidian. Inline `> [!source]` style attribution is fine where it helps.
5. **Do not write files.** Query is read-only by default.

## Sub-operation: Archive (opt-in only)

Triggered by an explicit follow-up: "archive this", "save this answer to the wiki", "file this".

When archiving:

1. **Write a new article**, never merge into an existing one. Archives are point-in-time syntheses, not raw material.
2. **Pick the most relevant topic directory** for the new article's location. Reuse, never fragment.
3. **Use `references/archive-template.md`** as the structural template. Set frontmatter:
   - `archived: true`
   - `sources:` — wikilinks to the **wiki articles** cited, never raw sources directly (archives compose at the wiki level)
   - `title:` — derived from the query (e.g., `Transformer Architectures Overview`)
4. **Update `wiki/index.md`** with the new entry. Prefix its summary with `[Archived]` so it's distinguishable from compiled articles.
5. **Log:** `## [YYYY-MM-DD] query | Archived: <title>`.

## Sub-operation: Suggest archiving (proactive, never auto)

If a query produces a synthesis you judge **genuinely new and reusable** (not a one-off answer, not trivially answerable by reading one article), suggest archiving at the end of the answer. One sentence: "This synthesis seems worth archiving as `<proposed-title>` — say so if you'd like me to save it."

**Wait for explicit confirmation.** Never archive silently.

## File-write contract

- **Default (no archive):** writes nothing.
- **With archive:** one new `wiki/<topic>/<slug>.md` (never modifies existing articles), `wiki/index.md`, `wiki/log.md`.
- **Never touches:** raw files; existing articles (archives never merge); `wiki.config.md`; per-vault `prompts/`.
