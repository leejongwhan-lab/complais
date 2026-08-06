# ComplAIs Backend

실사용 포탈(기업 / CB / 심사원) HTML + API.

## 기동

```bash
../scripts/start-complais.sh
# or
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 시드

```bash
python seed_companies_full.py --file data/companies_full.csv
python scripts/seed_cb_korea.py
```

DB: MySQL `complais` (`DATABASE_URL` in `.env`)

통일 기준: `../docs/UNIFIED_PORTAL.md`
