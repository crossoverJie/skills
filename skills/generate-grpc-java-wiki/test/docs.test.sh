#!/usr/bin/env bash
set -euo pipefail

test -f SKILL.md
test -f README.md
test -f docs/workflow.md
test -f docs/quality-checklist.md
test -f templates/page-service.md
test -f templates/page-architecture.md
test -f templates/page-features.md
test -f templates/page-er.md
test -f templates/page-powerjob.md
test -f templates/page-pulsar.md

grep -q "Agent" SKILL.md
grep -q "gRPC" README.md
grep -q "PowerJob" SKILL.md
grep -q "Pulsar" SKILL.md
grep -q "Do not invent" docs/workflow.md

# Summary pages must be generated from finalized component content, not memory.
grep -q "re-read the completed component pages" SKILL.md || (echo "ERROR: SKILL.md must require re-reading completed component pages before Phase 3" && exit 1)
grep -q "component inventory manifest" SKILL.md || (echo "ERROR: SKILL.md must require using the component inventory manifest before Phase 3" && exit 1)
grep -q "Re-read Generated Component Pages" docs/workflow.md || (echo "ERROR: workflow.md missing Phase 3 re-read step" && exit 1)
grep -q "Do not generate summary pages from memory" docs/workflow.md || (echo "ERROR: workflow.md must forbid memory-based summary generation" && exit 1)
grep -q "Summary pages were generated from completed component pages" docs/quality-checklist.md || (echo "ERROR: quality checklist must verify summary pages used completed component pages" && exit 1)

echo "Prompt-only documentation contract passed."
