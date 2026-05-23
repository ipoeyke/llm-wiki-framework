---
description: Run a health check on the wiki: auto-fix deterministic issues, report heuristic findings.
---

Invoke the `llm-wiki` skill's Lint operation. No arguments expected.

Follow `prompts/lint.md` (vault override takes precedence). Auto-fix deterministic checks (index drift, dead wikilinks with exactly one match, missing frontmatter defaults, see-also pruning, Bases regeneration). Report heuristic findings (contradictions, orphans, thin pages, missing cross-refs) — never silently rewrite article bodies based on heuristics.
