# ComplAIs Backend — 배포 / DB 체크리스트

상세 통합 가이드는 프론트 저장소 `complais-frontend/docs/DEPLOY_CHECKLIST.md` 를 참고하세요.

## 빠른 명령

```bash
./scripts/git-status.sh
./scripts/db-check.sh
./scripts/dbeaver-connection.sh
./scripts/db-migrate.sh          # alembic upgrade head
./scripts/deploy.sh              # git push + migrate
```

## Render env

| Key | Required | Notes |
|-----|----------|--------|
| `DATABASE_URL` | Yes | Blueprint `fromDatabase` 또는 Dashboard 연결 |
| `SECRET_KEY` | Yes | JWT 서명 (앱은 `JWT_SECRET` 이 아니라 `SECRET_KEY` 사용) |
| `PORT` | Auto | `uvicorn ... --port $PORT` |
| `API_V1_STR` | `/api/v1` | |
| `DEBUG` | `false` | production |

## Migration

이 프로젝트는 **Alembic** 입니다. Prisma/TypeORM 명령을 사용하지 마세요.

```bash
alembic current
alembic heads
alembic upgrade head
alembic revision --autogenerate -m "describe"
```
