#!/usr/bin/env bash
# init_wiki.sh — deterministic scaffold of an LLM Wiki vault.
#
# This script is a power-user shortcut. It does the deterministic file
# creation that /wiki:init does, without the agentic confirmation flow.
# If you want the agent to ask for audience/purpose interactively, run
# /wiki:init from Claude Code instead.
#
# Usage:
#   init_wiki.sh [--flavor research|course|domain] [--title "Wiki Name"]
#
# Defaults:
#   --flavor domain
#   --title  basename of the current directory

set -euo pipefail

# ---------- arg parsing ----------
flavor="domain"
title=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --flavor)
      flavor="${2:-}"
      shift 2
      ;;
    --title)
      title="${2:-}"
      shift 2
      ;;
    -h|--help)
      sed -n '2,15p' "$0"
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      sed -n '2,15p' "$0" >&2
      exit 1
      ;;
  esac
done

case "$flavor" in
  research|course|domain) ;;
  *)
    echo "error: --flavor must be one of: research, course, domain (got: $flavor)" >&2
    exit 1
    ;;
esac

if [[ -z "$title" ]]; then
  title="$(basename "$PWD")"
fi

# ---------- locate the skill's references directory ----------
script_dir="$(cd "$(dirname "$0")" && pwd)"
references_dir="$script_dir/../skills/llm-wiki/references"
prompts_dir="$script_dir/../skills/llm-wiki/prompts"

if [[ ! -d "$references_dir" ]]; then
  echo "error: cannot find skill references at $references_dir" >&2
  echo "expected layout: <repo>/scripts/init_wiki.sh and <repo>/skills/llm-wiki/references/" >&2
  exit 1
fi

# ---------- idempotency check ----------
if [[ -f "$PWD/wiki.config.md" ]]; then
  echo "wiki.config.md already exists in $PWD — already initialized. Nothing to do."
  exit 0
fi

# ---------- create directory tree ----------
mkdir -p raw wiki digests prompts
touch raw/.gitkeep digests/.gitkeep

# ---------- write wiki.config.md ----------
today="$(date +%Y-%m-%d)"

flavor_preset="$references_dir/flavor-presets/$flavor.md"
if [[ ! -f "$flavor_preset" ]]; then
  echo "error: flavor preset not found at $flavor_preset" >&2
  exit 1
fi

# Substitute top-level placeholders in the config template, then append the
# flavor preset content (skipping its H1) so the user has the flavor's
# page-types / style-rules / topic-seed inline and can edit in place.

config_template="$references_dir/wiki-config-template.md"

# Render the flavor preset body (without its H1) to a temp file, then read it
# back inline. Two-pass keeps sed substitutions clean.
preset_body="$(mktemp)"
trap 'rm -f "$preset_body"' EXIT
tail -n +2 "$flavor_preset" > "$preset_body"

awk -v t="$title" \
    -v f="$flavor" \
    -v aud="<edit: who reads this wiki>" \
    -v pur="<edit: one-paragraph statement of what this wiki is for>" \
    -v cad="weekly" \
    -v cre="$today" \
    -v body_file="$preset_body" '
  {
    gsub(/\{\{title\}\}/,           t)
    gsub(/\{\{flavor\}\}/,          f)
    gsub(/\{\{audience\}\}/,        aud)
    gsub(/\{\{purpose\}\}/,         pur)
    gsub(/\{\{digest_cadence\}\}/,  cad)
    gsub(/\{\{created\}\}/,         cre)
  }
  /\{\{flavor_preset_body\}\}/ {
    while ((getline line < body_file) > 0) print line
    close(body_file)
    next
  }
  { print }
' "$config_template" > wiki.config.md

# ---------- write wiki/index.md, wiki/index.base, wiki/log.md ----------
sed "s|{{Wiki title}}|${title}|g" "$references_dir/index-template.md" > wiki/index.md
cp "$references_dir/index-base-template.base" wiki/index.base
touch wiki/log.md

# ---------- Obsidian defaults: only compiled wiki articles in the graph ----------
# Everything except the compiled articles is plumbing — raw/ sources, operation
# prompts, the vault config, the index, and the log. Exclude it all from graph
# view / link suggestions via Obsidian's "Excluded files".
# Only written when app.json doesn't exist yet — never clobber user settings.
if [[ ! -f ".obsidian/app.json" ]]; then
  mkdir -p .obsidian
  cat > .obsidian/app.json <<'JSON'
{
  "userIgnoreFilters": [
    "raw/",
    "prompts/",
    "digests/",
    "reports/",
    "wiki.config.md",
    "wiki/index.md",
    "wiki/log.md",
    "/\\.base$/",
    "/_index\\.md$/"
  ]
}
JSON
else
  echo "note: .obsidian/app.json already exists — add raw/, prompts/, digests/, reports/, wiki.config.md, wiki/index.md, wiki/log.md, and the regexes /\\.base$/ and /_index\\.md$/ to Settings > Files and links > Excluded files yourself."
fi

# ---------- copy the chosen flavor's prompts into the vault ----------
cp "$prompts_dir/ingest/${flavor}.md" prompts/ingest.md
cp "$prompts_dir/sync.md"             prompts/sync.md
cp "$prompts_dir/query.md"            prompts/query.md
cp "$prompts_dir/lint.md"             prompts/lint.md
cp "$prompts_dir/digest.md"           prompts/digest.md
cp "$prompts_dir/consolidate.md"      prompts/consolidate.md

# ---------- install the maintenance script ----------
mkdir -p prompts/tools
cp "$script_dir/../skills/llm-wiki/scripts/wiki_maint.py" prompts/tools/wiki_maint.py

# ---------- append init entry to wiki/log.md ----------
{
  echo "## [${today}] init | ${flavor} | ${title}"
  echo "- scaffolded via init_wiki.sh"
  echo
} >> wiki/log.md

# ---------- report ----------
cat <<EOF
Initialized LLM Wiki vault at $PWD
  flavor: $flavor
  title:  $title

Next steps:
  1. Open wiki.config.md and fill in <audience> and <purpose>.
  2. Install kepano/obsidian-skills (required): /plugin marketplace add kepano/obsidian-skills && /plugin install obsidian@obsidian-skills
  3. /wiki:ingest <url>  — add your first source.
EOF
