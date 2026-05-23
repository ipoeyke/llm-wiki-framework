---
description: Process all new raw/ sources since the last sync.
---

Invoke the `llm-wiki` skill's Sync operation. No arguments expected; Sync operates on the delta since the last `## [YYYY-MM-DD] sync` or `## [YYYY-MM-DD] init` entry in `wiki/log.md`.

Follow `prompts/sync.md` (vault override takes precedence over the skill's default).
