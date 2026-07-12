---
description: Produce a self-contained HTML digest for the current window (default: this ISO week).
---

Invoke the `llm-wiki` skill's Digest operation. Optional `$ARGUMENTS`: a window override such as `--week 2026-W20`, or `--force` to produce a digest for an empty period.

Follow `prompts/digest.md` (vault override takes precedence). Render `references/digest-template.html` into `digests/YYYY-Www-recap.html` at the vault root. Verify the output is self-contained (zero external network requests) and article links use the `obsidian://open?vault=...&file=...` URI scheme.
