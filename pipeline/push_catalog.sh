#!/usr/bin/env bash
# push_catalog.sh <run-id> <batch> "<one-line summary>" "<manifest path>"
# RULES §1c: publish the batch to GitHub (CSV + CHANGELOG + manifest + pipeline toolchain).
# PAT source order: GH_TOKEN/GITHUB_TOKEN env -> .env GITHUB_PAT=
set -u
RUN_ID="${1:?run-id}"; BATCH="${2:?batch}"; SUMMARY="${3:?summary}"; MANIFEST="${4:?manifest}"
PROJ=/home/z/my-project
REPO="$PROJ/work/repo_asleep"
CSV="$PROJ/download/art_d_final/syllabus_extreme_rich.csv"

PAT="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [ -z "$PAT" ]; then
  PAT=$(grep -E '^GITHUB_PAT=' "$PROJ/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
fi
if [ -z "$PAT" ]; then echo "PUSH_FAIL|no PAT (env/.env)"; exit 1; fi

[ -f "$CSV" ] || { echo "PUSH_FAIL|missing CSV $CSV"; exit 1; }
[ -f "$MANIFEST" ] || { echo "PUSH_FAIL|missing manifest $MANIFEST"; exit 1; }

TS=$(date -u +%Y%m%dT%H%M%SZ)
SLUG=$(printf '%s' "$SUMMARY" | tr -c 'A-Za-z0-9' '-' | tr -s '-' | cut -c2-61 | sed 's/-*$//')
MF_NAME="${TS}_${RUN_ID}_${SLUG}.md"

# stage catalog artifacts
cp "$CSV" "$REPO/syllabus_catalog/syllabus_extreme_rich.csv"
cp "$MANIFEST" "$REPO/syllabus_catalog/runs/$MF_NAME"

# sync toolchain (RULES §1c item 4: the versioned pipeline actually used by the run)
cp "$PROJ"/scripts/pipeline_v2/*.py "$REPO/pipeline/" 2>/dev/null
cp "$PROJ/scripts/pipeline_v2/RULES.md" "$PROJ/scripts/pipeline_v2/draft_prompt.md" "$REPO/pipeline/" 2>/dev/null
cp "$0" "$REPO/pipeline/push_catalog.sh" 2>/dev/null
chmod +x "$REPO/pipeline/push_catalog.sh" 2>/dev/null

# CHANGELOG prepend (run-id dedup)
CH="$REPO/syllabus_catalog/CHANGELOG.md"
if [ -f "$CH" ] && ! grep -q -- "$RUN_ID" "$CH"; then
  TMP=$(mktemp)
  { echo "# $RUN_ID — $BATCH — $(date -u +%Y-%m-%d)"
    echo
    echo "$SUMMARY"
    echo
    cat "$CH"; } > "$TMP"
  cp "$TMP" "$CH"; rm -f "$TMP"
fi

cd "$REPO" || { echo "PUSH_FAIL|no repo clone"; exit 1; }
git config user.name  >/dev/null 2>&1 || git config user.name "Z Catalog Pipeline"
git config user.email >/dev/null 2>&1 || git config user.email "catalog-pipeline@users.noreply.github.com"
git add syllabus_catalog pipeline
git commit -m "catalog($BATCH) run=$RUN_ID: $SUMMARY" >/dev/null || { echo "PUSH_FAIL|commit"; exit 1; }

# fail fast: the CSV MUST be in the commit (B06 incident: CHANGELOG+manifest only)
if ! git show --stat HEAD | grep -q "syllabus_extreme_rich.csv"; then
  echo "PUSH_FAIL|CSV not in commit (B06 incident guard)"; exit 1
fi

URL="https://x-access-token:${PAT}@github.com/harshvardhan9084/asleep.git"
if ! git push "$URL" main:main 2>/dev/null; then
  sleep 3
  if ! git push "$URL" main:main 2>/dev/null; then
    echo "PUSH_FAIL|push (after 1 retry)"; exit 1
  fi
fi
SHA=$(git ls-remote "$URL" main 2>/dev/null | cut -f1)
echo "PUSH_OK|sha=$SHA|manifest=$MF_NAME"
