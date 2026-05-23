# Flavor preset: course

For coursework second brains — MS CS courses, bootcamps, structured study. The wiki compiles a course's worth of lecture notes, problem sets, readings, and your own working notes into a cross-referenced second brain that outlives the semester.

## Page types

- **topic** — a subject-matter area within the course (e.g., "RSA", "BGP", "MapReduce"). The default page type. Builds up from lectures + readings + your own notes over the term.
- **definition** — a single term with a sharp definition. Short. Linked from many topic pages.
- **worked-example** — a problem solved start-to-finish. Frontmatter includes `difficulty` and `source` (e.g., problem set 3 question 2).
- **problem-set** — meta-page for a problem set or exam, linking to the worked-example pages for individual questions plus topic pages it covers.

## Style rules

- **Voice:** pedagogical. Build from primitives. If a topic page assumes a concept, link to its definition or topic page rather than gloss-explaining inline.
- **Length:** topic pages grow; definitions stay one paragraph. Worked examples are as long as the problem requires.
- **Citation:** lecture clips and readings are wikilinked; cite the lecture date or slide where possible.
- **What to expand:** intuitions, why-this-not-that motivations, common pitfalls, the bridges between formal and informal explanations.
- **What to summarize:** material covered elsewhere in the course wiki — link out.
- **Personal notes** (`content_type: personal-note`): user-authored reflections, "wait, why does X?" questions, study notes. Always surface as `> [!question]` callouts in the relevant topic page. **Never cite a personal-note as if it were the professor or textbook saying it.**

## Topic taxonomy (seed)

**Critical rule — topics are subject-matter, NEVER weeks, lectures, content-types, or course phases.**

Wrong: `raw/week-2/`, `raw/lectures/`, `raw/problem-sets/`, `raw/midterm-review/`.

Right: `raw/cryptography/`, `raw/network-security/`, `raw/web-security/`, `raw/access-control/`.

Why this matters: courses re-sequence material between semesters; lectures and readings on the same subject cluster naturally when topics are subject-matter; a single wiki concept page can absorb information from multiple weeks and content types.

Examples (information security course):
- `cryptography/`
- `network-security/`
- `web-security/`
- `access-control/`
- `software-security/`
- `privacy/`

Examples (distributed systems course):
- `consistency/`
- `consensus/`
- `replication/`
- `storage-systems/`
- `scheduling/`

The LLM adds new topics as ingestion warrants. The Ingest topic-selection step **must** reject week/lecture/content-type topic names and ask the user for a subject-matter alternative.

## Custom rules

- Preserve professor's terminology over the textbook's where they diverge — note both with a `> [!source]` callout.
- Worked examples link back to the topic page(s) the problem exercises, and the topic page maintains a "Worked examples" section linking back to them.
- Discussion-board threads ingest as a single `.md` per thread (`## Original post` then `### Reply by <author>`), per the framework's threaded-content policy.
- Assignment due dates land in frontmatter `due_date` for queryability; the framework doesn't render due dates anywhere — that's the user's calendar's job.
