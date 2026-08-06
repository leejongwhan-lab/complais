#!/usr/bin/env bash
# ComplAIs Backend — Alembic migration (safe upgrade to head)
#
# Usage:
#   ./scripts/db-migrate.sh              # upgrade head (uses .env DATABASE_URL)
#   ./scripts/db-migrate.sh --dry-run    # show SQL only
#   ./scripts/db-migrate.sh --check      # current/heads only
#
# Production (Render External URL):
#   export DATABASE_URL="postgresql://USER:PASS@HOST:5432/DB?sslmode=require"
#   ./scripts/db-migrate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="upgrade"
for arg in "$@"; do
  case "$arg" in
    --dry-run) MODE="dry-run" ;;
    --check) MODE="check" ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

# shellcheck source=scripts/_load_env.sh
source "$ROOT/scripts/_load_env.sh"
load_dotenv .env

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[FAIL] DATABASE_URL is not set (.env or export)" >&2
  exit 1
fi

# Render Internal URL is only reachable from Render services.
# Local/DBeaver/this script should use the External Database URL + sslmode=require.
if echo "$DATABASE_URL" | grep -qE '@[^/]*-a$|internal\.render\.com|dpg-[^.]+\.render\.com:5432' \
  && ! echo "$DATABASE_URL" | grep -qi 'sslmode'; then
  echo "[WARN] Render DB often requires ?sslmode=require for external clients."
fi

ALEMBIC_BIN="alembic"
[[ -x .venv/bin/alembic ]] && ALEMBIC_BIN=".venv/bin/alembic"
[[ -x venv/bin/alembic ]] && ALEMBIC_BIN="venv/bin/alembic"

echo "=============================================="
echo " ComplAIs — Alembic migrate ($MODE)"
echo "=============================================="
bash "$ROOT/scripts/db-check.sh" || true
echo

case "$MODE" in
  check)
    exit 0
    ;;
  dry-run)
    echo ">>> alembic upgrade head --sql"
    $ALEMBIC_BIN upgrade head --sql
    ;;
  upgrade)
    echo ">>> alembic upgrade head"
    $ALEMBIC_BIN upgrade head
    echo
    echo ">>> post-migrate current"
    $ALEMBIC_BIN current
    echo
    echo "Done."
    ;;
esac
