#!/usr/bin/env bash
# ComplAIs Backend — Git 상태 / main 기준 추적 점검
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MAIN_BRANCH="main"
if git show-ref --verify --quiet refs/heads/master && ! git show-ref --verify --quiet refs/heads/main; then
  MAIN_BRANCH="master"
fi

echo "=============================================="
echo " ComplAIs Backend — Git Status"
echo "=============================================="
echo "Repo:   $(basename "$ROOT")  ($(git remote get-url origin 2>/dev/null || echo 'no remote'))"
echo "Branch: $(git branch --show-current 2>/dev/null || echo '(detached)')"
echo "Base:   $MAIN_BRANCH"
echo

git status -sb
echo

STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')
UNSTAGED=$(git diff --name-only | wc -l | tr -d ' ')
UNTRACKED=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')
echo "Staged: $STAGED | Unstaged: $UNSTAGED | Untracked: $UNTRACKED"
echo

if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  git fetch --quiet origin "$MAIN_BRANCH" 2>/dev/null || true
  AHEAD=$(git rev-list --count "origin/${MAIN_BRANCH}..HEAD" 2>/dev/null || echo "?")
  BEHIND=$(git rev-list --count "HEAD..origin/${MAIN_BRANCH}" 2>/dev/null || echo "?")
  echo "vs origin/${MAIN_BRANCH}: ahead=$AHEAD behind=$BEHIND"
  if [[ "$AHEAD" != "0" && "$AHEAD" != "?" ]]; then
    echo
    echo "--- commits to push ---"
    git log --oneline "origin/${MAIN_BRANCH}..HEAD"
  fi
  if [[ "$BEHIND" != "0" && "$BEHIND" != "?" ]]; then
    echo
    echo "WARNING: local is behind origin/${MAIN_BRANCH}. Pull/rebase before push."
  fi
else
  echo "WARNING: no upstream. Run: git push -u origin HEAD"
fi

echo
if [[ "$STAGED$UNSTAGED$UNTRACKED" != "000" ]]; then
  echo "RESULT: uncommitted changes present — commit before deploy."
  exit 1
fi

echo "RESULT: clean working tree — ready to push."
exit 0
