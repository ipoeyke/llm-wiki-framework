---
description: Find pages to merge, split, supersede or link, write a numbered report, and apply only approved items.
---

Invoke the `llm-wiki` skill's Consolidate operation. With no arguments, run Phase 1 (Report): write `reports/consolidation-YYYY-MM-DD.md` and change no article. With arguments naming a report and item numbers (for example `2026-09-28 items 1-4, 7`), run Phase 2 (Apply) for exactly those items.

Follow `prompts/consolidate.md` (vault override takes precedence).
