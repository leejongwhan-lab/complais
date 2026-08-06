#!/usr/bin/env bash
# ComplAIs Backend — push + Alembic migrate (Render Auto Deploy trigger)
#
# Usage:
#   ./scripts/deploy.sh
#   ./scripts/deploy.sh --dry-run
#   ./scripts/deploy.sh --migrate-only
#   ./scripts/deploy.sh --skip-check
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DRY_RUN=0
MIGRATE_ONLY=0
SKIP_CHECK=0
MAIN_BRANCH="${MAIN_BRANCH:-main}"

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --migrate-only) MIGRATE_ONLY=1 ;;
    --skip-check) SKIP_CHECK=1 ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

echo "=============================================="
echo " ComplAIs Backend Deploy"
echo "=============================================="

if [[ "$SKIP_CHECK" -eq 0 ]]; then
  bash "$ROOT/scripts/db-check.sh" || true
  echo
fi

if [[ "$MIGRATE_ONLY" -eq 0 ]]; then
  echo ">>> Git"
  bash "$ROOT/scripts/git-status.sh" || {
    echo "Uncommitted changes — commit first, or use --migrate-only / --skip-check carefully." >&2
    if [[ "$SKIP_CHECK" -eq 0 ]]; then
      exit 1
    fi
  }
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] would: git push origin HEAD"
  else
    if ! git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
      git push -u origin HEAD
    else
      git push origin HEAD
    fi
    echo "Pushed backend → origin (Render Auto Deploy if linked to main)"
  fi
  echo
fi

echo ">>> Migrate"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] would: ./scripts/db-migrate.sh"
else
  bash "$ROOT/scripts/db-migrate.sh"
fi

echo
echo "Done. Verify Render → Logs and GET /health"
echo "Checklist: docs/DEPLOY_CHECKLIST.md"
