---
title: {{Article title}}
summary: {{One-line summary. Also surfaces in wiki/index.md.}}
topics: [{{topic}}]
sources:
  - "[[raw/<topic>/<source-file>.md]]"
external_sources: "{{Author/org; date; — semicolon-separated, for non-vaulted sources}}"
created: {{YYYY-MM-DD}}
updated: {{YYYY-MM-DD — knowledge change, not filesystem mtime}}
archived: false
open_questions: {{true if body contains any "> [!question]" callout — powers the index's Open questions view; omit otherwise}}
---

> [!summary]
> {{One-paragraph summary of the article. What it covers, why it matters in this wiki.}}

## {{First body section}}

{{Body text. Cross-link aggressively to other articles: [[Related Article]], [[Other Article#Specific section]]. Cite raw sources with the [[raw/<topic>/<file>]] wikilink form, or inline with `> [!source]` callouts for specific claims.}}

> [!source]
> {{Attribution for a specific claim drawn from a particular source. Optional but recommended when one paragraph leans heavily on a single source.}}

## {{Next body section}}

{{...}}

> [!conflict]
> **{{Topic of disagreement}}**
>
> - [[raw/<topic>/<source-A>.md]] argues: {{paraphrase of position A}}
> - [[raw/<topic>/<source-B>.md]] argues: {{paraphrase of position B}}
>
> {{Use this callout when two sources cited in this article disagree on a factual claim. Do not silently pick a side.}}

> [!question]
> {{Open question raised by this article — either an explicit user-authored question (content_type: personal-note) or a gap in coverage that future ingestion should fill.}}

## See also

- [[{{Related article 1}}]]
- [[{{Related article 2}}]]
