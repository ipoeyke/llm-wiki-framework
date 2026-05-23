---
description: Ingest a URL, file, or pasted text into the wiki.
---

Invoke the `llm-wiki` skill's Ingest operation. Treat `$ARGUMENTS` as the source — a URL, file path, or pasted text.

Read the current vault's `wiki.config.md` to determine the flavor, then follow `prompts/ingest/<flavor>.md` (vault override takes precedence over the skill's default at the same path).
