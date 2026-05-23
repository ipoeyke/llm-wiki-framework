---
description: Initialize the current directory as an Obsidian LLM Wiki vault.
---

Invoke the `llm-wiki` skill's Init operation in the current working directory.

Arguments (optional, parsed from `$ARGUMENTS`):
- First positional token, if it's one of `research` / `course` / `domain`: use as the flavor.
- Remaining tokens: treat as the wiki `title`.

If any required field (flavor, title) is missing, ask for all missing fields in a single batched prompt per the skill's Init flow. Echo the final config and request confirmation before writing.
