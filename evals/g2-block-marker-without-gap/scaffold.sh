#!/bin/bash
# Seeds the empty eval workspace. Identical in every case (tests/test_evals.py pins that); case.env says what to seed.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$here/case.env"
if [ -n "${FIXTURE:-}" ]; then cp -R "$here/../fixtures/$FIXTURE/." .; fi
if [ -n "${BRIEF:-}" ]; then
  mkdir -p "articles/$SLUG"
  cp "$here/../briefs/$BRIEF.md" "articles/$SLUG/brief.md"
  cp "$here/../briefs/$BRIEF.md" "articles/$SLUG/brief.source.md"
fi
if [ -n "${INPUT:-}" ]; then mkdir -p input && cp "$here/../briefs/$INPUT.md" "input/$INPUT.md"; fi
if [ -d "$here/seed" ]; then cp -R "$here/seed/." .; fi
