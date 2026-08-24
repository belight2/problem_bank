# Problem Bank API

FastAPI 기반 문제 은행 백엔드의 시작 프로젝트입니다. PostgreSQL만 Docker Compose로 실행하고 애플리케이션은 로컬 Python 환경에서 실행합니다.

```text
로컬 FastAPI 애플리케이션 → localhost:25431 → Docker PostgreSQL
```

아직 도메인 모델이나 CRUD API는 구현하지 않았습니다.

## 기술 스택

- Python 3.12+
- FastAPI
- SQLAlchemy 2
- PostgreSQL 17
- Pydantic Settings
- pytest, Ruff

## 빠른 시작

### 1. 환경 설정

```bash
cp .env.example .env
```

기본값을 그대로 사용한다면 `.env`를 수정할 필요가 없습니다.

### 2. PostgreSQL 실행

Docker Desktop을 직접 실행한 다음 필요한 경우 아래 명령을 직접 실행합니다.

```bash
docker compose up -d
docker compose ps
```

### 3. Python 패키지 설치

`uv` 사용:

```bash
uv sync --extra dev
```

일반 `venv`와 `pip` 사용:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. FastAPI 실행

```bash
uv run uvicorn app.main:app --reload
```

`pip` 환경에서는 다음 명령을 사용합니다.

```bash
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 현재 API

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/` | 애플리케이션 정보 |
| `GET` | `/health` | PostgreSQL 연결 상태 |

## 테스트와 코드 검사

아래 명령은 Docker나 PostgreSQL을 자동으로 실행하지 않습니다.

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## PostgreSQL 기본 설정

| 항목 | 기본값 |
| --- | --- |
| Host | `localhost` |
| Port | `25431` |
| Database | `problem_bank` |
| Username | `problem_bank` |
| Password | `problem_bank_local` |

PostgreSQL에 직접 접속하려면 다음 명령을 사용합니다.

```bash
docker compose exec db psql -U problem_bank -d problem_bank
```

## 종료와 데이터 초기화

```bash
docker compose down
```

위 명령은 컨테이너만 제거하며 데이터는 Docker 볼륨에 유지합니다. 데이터까지 삭제하려면 다음 명령을 직접 실행해야 합니다.

```bash
docker compose down -v
```

`-v` 옵션은 저장된 PostgreSQL 데이터를 삭제하므로 주의하세요.

## 프로젝트 구조

```text
app/
├── core/config.py    # 환경변수 설정
├── db/session.py     # SQLAlchemy 연결과 세션
└── main.py           # FastAPI 애플리케이션
tests/                # DB 없이 실행하는 기본 테스트
```
