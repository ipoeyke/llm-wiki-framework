---
title: "{{title}}"
flavor: {{flavor}}
audience: "{{audience}}"
purpose: "{{purpose}}"
digest_cadence: {{digest_cadence}}
created: {{created}}
lifecycle:
  # half_life_days: {paper: 180}      # page type -> days until review_by; omit to use the flavor default
  topic_half_life_days: {}             # topic -> days; overrides the type rule for fast-moving topics
  hub_token_cap: 5000                  # body tokens (chars/4) above which a page is a split candidate
  demote_max_inbound: 2
  consolidate_every_articles: 100
  consolidate_every_days: 90
---

# {{title}}

{{purpose}}

## Custom rules

<!-- Anything specific to THIS wiki that overrides the flavor defaults below. Examples:
  - domain jargon to preserve verbatim
  - terms to avoid or always disambiguate
  - per-source citation conventions
  - extra page types beyond what the flavor defines
The rules in this section take precedence over the flavor preset's defaults. -->

---

<!-- ---------------------------------------------------------------------- -->
<!-- Flavor defaults injected from references/flavor-presets/{{flavor}}.md  -->
<!-- The flavor preset's Page types, Style rules, Topic taxonomy, and       -->
<!-- Custom rules sections appear below. Edit freely.                       -->
<!-- ---------------------------------------------------------------------- -->

{{flavor_preset_body}}
