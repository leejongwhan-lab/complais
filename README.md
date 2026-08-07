# ComplAIs Backend

실사용 포탈(기업 / CB / 심사원) HTML + API.

## 기동

```bash
../scripts/start-complais.sh   # :8000 healthy면 재기동하지 않음
# or (stable — recommended on OneDrive paths)
uvicorn app.main:app --host 127.0.0.1 --port 8000

# optional hot-reload (app/ only; avoid watching static/OneDrive thrash)
COMPLAIS_RELOAD=1 ../scripts/start-complais.sh
```

> OneDrive 경로에서 `uvicorn --reload` 전체 트리 watch 는 파일 동기화로 재시작 루프가
> 나며 브라우저에 "사이트 연결할 수 없음" 이 반복됩니다. 기본은 reload 없이 기동하세요.

## 시드

```bash
python seed_companies_full.py --file data/companies_full.csv
python scripts/seed_cb_korea.py
```

DB: MySQL `complais` (`DATABASE_URL` in `.env`)

통일 기준: `../docs/UNIFIED_PORTAL.md`
