---
title: {{title}}
collected: {{YYYY-MM-DD}}
published: {{YYYY-MM-DD or "Unknown"}}
topics: [{{topic}}]
content_type: {{article | paper | lecture | assignment | reading | discussion | announcement | syllabus | transcript | personal-note}}
source_url: {{https://... or omit if no canonical URL}}
source_ref: {{notion://page/abc123 or slack://team/T0/channel/C1/ts/172800000.001 or omit if source_url is set}}
# Optional extension fields (source-type specific; lint ignores these):
# canvas_course_id: 12345
# canvas_module_id: 678
# due_date: 2026-10-15
# assignment_type: homework
# notion_database_id: ...
# Revision pointers (added by Ingest when a source has multiple revisions):
# supersedes: [[raw/<topic>/<previous-file>.md]]
# superseded_by: [[raw/<topic>/<next-file>.md]]
# Binary sidecar pointer (for PDFs, images, audio):
# binary: [[raw/<topic>/<base-name>.<ext>]]
---

{{Source content verbatim. Do not rewrite, clean, or normalize beyond formatting noise.

For threaded content (Canvas discussions, Slack threads, email chains), structure as a single file:

## Original post

<author, date, body>

### Reply by <author> [<date>]

<reply body>

### Reply by <author> [<date>]

<reply body>
}}
