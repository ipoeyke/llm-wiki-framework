# Flavor preset: domain

The generalist bucket. Use `domain` whenever a wiki isn't clearly a research wiki (`research`) or a coursework wiki (`course`) — internal project wikis, knowledge-management for a hobby or trade, encyclopedic notes on a subject area, capture for a focused investigation.

The voice is encyclopedic and the page types are deliberately spare so the per-vault `wiki.config.md` can encode the specifics.

## Page types

- **concept** — the default. A topic, idea, entity, decision, term, anything that earns a page. One concept per page; cross-link aggressively.
- **overview** — a higher-altitude page that orients the reader across many concepts within a topic. Useful as a landing page per topic.
- **comparison** — sustained side-by-side analysis of two or more concepts that are commonly confused or commonly traded off. Single page; not a duplicate of either concept's page.

If your wiki needs more specific page types (e.g., `entity`, `decision`, `incident`, `vendor`), add them in `wiki.config.md` under "Page types" — the flavor preset is just a starting point.

## Style rules

- **Voice:** encyclopedic and generalist. Plain. Define jargon on first use, then link to a definition page if the term recurs.
- **Length:** as long as the concept requires. Most concepts are 100–400 words. Overviews are longer; comparisons are structured.
- **Citation:** every nontrivial claim is sourced — wikilink to the raw entry, or a `> [!source]` callout for emphasis. External non-vaulted citations go in the `external_sources` frontmatter field.
- **What to expand:** anything contested, anything subtle, anything where this wiki is the only place the user has consolidated the answer.
- **What to summarize:** widely-known background — link out to a definition page or external reference rather than restating.
- **Personal notes** (`content_type: personal-note`): always render as `> [!question]` callouts. Never blend into the body as cited claims.

## Topic taxonomy (seed)

Topics are subject-matter. Whatever the wiki is *about* — the natural categories a reader would expect. Examples vary entirely by domain:

- A coffee wiki: `extraction/`, `roasting/`, `green-coffee/`, `equipment/`, `cafes/`.
- An internal project wiki: `architecture/`, `decisions/`, `incidents/`, `runbooks/`, `vendors/`.
- A hobby wiki on a board game: `openings/`, `endgames/`, `tournaments/`, `players/`.

The LLM adds new topics as ingestion warrants. Reuse before fragmenting. Topics are never dates, never content-types, never sources.

## Custom rules

- Because `domain` is the catch-all, lean harder on `wiki.config.md` — encode specific terminology, citation preferences, and any domain-specific page types there.
- Comparisons earn their own page only when the comparison itself is the thing being captured. Otherwise a See-also link suffices.
- For project/business wikis, "decisions" often deserve their own page type — add it explicitly in `wiki.config.md` if so.
