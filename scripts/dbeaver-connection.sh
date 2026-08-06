#!/usr/bin/env bash
# ComplAIs Backend — DBeaver / GUI 클라이언트용 연결 정보 (비밀번호 마스킹)
#
# Render Dashboard → PostgreSQL → Connections:
#   - Internal Database URL  : Web Service 전용 (같은 private network)
#   - External Database URL  : DBeaver / 로컬 alembic 용 (+ SSL)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/_load_env.sh
source "$ROOT/scripts/_load_env.sh"
load_dotenv .env

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL not set. Copy from Render → PostgreSQL → External Database URL into .env" >&2
  exit 1
fi

python3 - <<'PY'
import os, re, urllib.parse

url = os.environ["DATABASE_URL"]
masked = re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:***@", url)
u = urllib.parse.urlparse(url)

host = u.hostname or ""
port = u.port or 5432
db = (u.path or "/").lstrip("/")
user = urllib.parse.unquote(u.username or "")
qs = urllib.parse.parse_qs(u.query)
ssl = (qs.get("sslmode") or ["(not set)"])[0]
scheme = (u.scheme or "").split("+")[0]

print("==============================================")
print(" DBeaver connection (password hidden)")
print("==============================================")
print(f"Masked URL : {masked}")
print()
print("DBeaver → New Connection → PostgreSQL (or MySQL if scheme is mysql):")
print(f"  Host     : {host}")
print(f"  Port     : {port}")
print(f"  Database : {db}")
print(f"  Username : {user}")
print(f"  Password : (from Render dashboard — do not paste into git)")
print(f"  SSL      : sslmode={ssl}")
print()
if "postgres" in scheme:
    print("DBeaver SSL tip (Render External):")
    print("  SSL → SSL mode = require  (or verify-full if you install CA)")
    print("  JDBC URL append: ?sslmode=require")
elif "mysql" in scheme:
    print("Local MySQL/XAMPP tip: leave SSL off for localhost.")
print()
print("App env key: DATABASE_URL  (never commit .env)")
print("SQLAlchemy  : postgresql://...  or  mysql+pymysql://...")
print("Alembic     : reads DATABASE_URL via app.core.config.settings")
PY
