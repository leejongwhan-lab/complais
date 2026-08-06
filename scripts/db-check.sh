#!/usr/bin/env bash
# ComplAIs Backend — DB / Alembic / DATABASE_URL 안전 점검
# Secrets(비밀번호)는 절대 출력하지 않습니다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mask_url() {
  # postgresql://user:pass@host:5432/db?sslmode=require  →  postgresql://user:***@host:5432/db?...
  python3 - <<'PY' "$1"
import re, sys
url = sys.argv[1]
print(re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:***@", url))
PY
}

parse_endpoint() {
  python3 - <<'PY' "$1"
import re, sys, urllib.parse
url = sys.argv[1]
raw = url
u = urllib.parse.urlparse(raw if "://" in raw else "postgresql://" + raw)
host = u.hostname or "?"
port = u.port or ("5432" if "postgres" in (u.scheme or "") else "3306")
db = (u.path or "/").lstrip("/") or "?"
scheme = (u.scheme or "?").split("+")[0]
print(f"scheme={scheme} host={host} port={port} database={db}")
PY
}

echo "=============================================="
echo " ComplAIs Backend — DB / Migration Check"
echo "=============================================="

# shellcheck source=scripts/_load_env.sh
source "$ROOT/scripts/_load_env.sh"
if [[ -f .env ]]; then
  load_dotenv .env
  echo "Loaded: .env"
else
  echo "WARNING: .env not found — using process env / defaults"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[FAIL] DATABASE_URL is not set"
  exit 1
fi

echo
echo "1) DATABASE_URL (masked)"
echo "  $(mask_url "$DATABASE_URL")"
echo "  $(parse_endpoint "$DATABASE_URL")"

if echo "$DATABASE_URL" | grep -qiE 'render\.com|dpg-|\.oregon-postgres\.|\.singapore-postgres\.|\.frankfurt-postgres\.'; then
  echo "  [OK] looks like Render PostgreSQL host"
elif echo "$DATABASE_URL" | grep -qi 'localhost\|127\.0\.0\.1'; then
  echo "  [WARN] localhost DB — production migrate needs Render External URL"
else
  echo "  [INFO] non-local host (verify this is the intended target)"
fi

echo
echo "2) Alembic files"
if [[ ! -f alembic.ini ]]; then
  echo "  [FAIL] alembic.ini missing"
  exit 1
fi
COUNT=$(find alembic/versions -name '*.py' ! -name '__*' 2>/dev/null | wc -l | tr -d ' ')
echo "  migration scripts: $COUNT"
echo "  (authoritative head comes from 'alembic heads' below)"

echo
echo "3) Alembic revision status (live DB)"
ALEMBIC_BIN="alembic"
[[ -x .venv/bin/alembic ]] && ALEMBIC_BIN=".venv/bin/alembic"
[[ -x venv/bin/alembic ]] && ALEMBIC_BIN="venv/bin/alembic"

if ! command -v "$ALEMBIC_BIN" >/dev/null 2>&1 && [[ ! -x "$ALEMBIC_BIN" ]]; then
  echo "  [WARN] alembic CLI not found — try: pip install -r requirements.txt"
else
  echo "  using: $ALEMBIC_BIN"
  set +e
  CURRENT=$($ALEMBIC_BIN current 2>&1)
  HEADS=$($ALEMBIC_BIN heads 2>&1)
  RC_CUR=$?
  set -e
  echo "  --- current ---"
  echo "$CURRENT" | sed 's/^/  /'
  echo "  --- heads ---"
  echo "$HEADS" | sed 's/^/  /'
  if [[ $RC_CUR -ne 0 ]]; then
    echo "  [WARN] could not query DB (check SSL / External URL / firewall)"
  else
    echo "  [OK] alembic reachable"
  fi
fi

echo
echo "4) Safe commands"
echo "  Status:   ./scripts/db-check.sh"
echo "  Migrate:  ./scripts/db-migrate.sh          # alembic upgrade head"
echo "  Generate: alembic revision --autogenerate -m \"desc\""
echo "  DBeaver:  ./scripts/dbeaver-connection.sh"
echo
echo "NOTE: This project uses Alembic (SQLAlchemy), not Prisma/TypeORM."
echo "      Do NOT run npx prisma db push against this schema."
