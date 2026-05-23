---
description: Answer a question from the wiki's compiled knowledge.
---

Invoke the `llm-wiki` skill's Query operation. Treat `$ARGUMENTS` as the question.

Follow `prompts/query.md` (vault override takes precedence). Default behavior writes no files. If the user follows up with "archive this" or similar, run the archive sub-operation.
