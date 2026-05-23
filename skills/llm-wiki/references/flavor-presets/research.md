# Flavor preset: research

For personal research wikis — typically NLP, ML, systems papers, blog posts, repo READMEs. The wiki is the durable side of a researcher's reading practice: concept pages compound, papers get cited from multiple angles, open questions are first-class.

## Page types

- **concept** — a recurring idea (attention, mixture-of-experts, RLHF). Built up over many sources, never owned by one. The default page type.
- **paper** — a specific publication. Frontmatter includes `authors`, `venue`, `year`. Body covers contribution, method, results, where it sits relative to neighboring concepts. One paper, one page.
- **open-question** — an unresolved research question (your own or one a paper raised). `> [!question]` callouts in other articles can link here.
- **hypothesis** — a stronger claim you'd defend or want to test. Cite the evidence pulling for and against.

## Style rules

- **Voice:** rigorous and hedged. Use "the paper claims" / "the authors argue" — not "X is true". Conclusions get qualified by evidence quality.
- **Length:** concepts grow as evidence accumulates; no fixed cap. Papers are typically 200–500 words plus a method box.
- **Citation:** every nontrivial claim has a `> [!source]` callout or an inline wikilink to the raw source. Untraceable claims are a smell.
- **What to expand:** mechanisms, ablations, failure modes, surprising results, contrary evidence.
- **What to summarize:** background you already have elsewhere in the wiki — link out instead of repeating.
- **Personal notes** (`content_type: personal-note`): always render as `> [!question]` callouts. Never blend into the body as if they were external evidence.

## Topic taxonomy (seed)

Topics are subject-matter — research areas or technical themes, never authors, venues, or years.

Examples:
- `attention/`
- `tokenization/`
- `pretraining-objectives/`
- `rlhf/`
- `evaluation/`
- `retrieval/`

The LLM adds new topics as ingestion warrants. Reuse aggressively; fragmenting `attention/` into `flash-attention/`, `sparse-attention/`, etc. is wrong — those go inside `attention/` as articles, not as topics.

## Custom rules

- Prefer the paper's own terminology over your synthesized renames. If the paper says "expert" and not "module", use "expert".
- When two papers disagree, surface it via `> [!conflict]` immediately. Resolution can come later from a third source.
- arXiv versions: if a paper has v2/v3, ingest the latest by default. Use the revision protocol (`-revN.md`) if you ingest a later version of an already-vaulted paper.
