# Problem Bank

React·TypeScript 프론트엔드와 FastAPI 백엔드로 구성한 개인용 문제 은행입니다. PostgreSQL만 Docker Compose로 실행하고 애플리케이션은 로컬 환경에서 실행합니다.

```text
React (localhost:5173) → FastAPI (localhost:8000) → PostgreSQL (localhost:25431)
```

카드를 만들고 그 안에 주제별 문제를 직접 저장할 수 있습니다. 프론트엔드에서는 카드·문제 CRUD와 설정한 개수만큼 문제를 무작위로 제공하는 기능을 사용할 수 있습니다. 문제 채점이나 점수 계산 기능은 포함하지 않습니다.

## 기술 스택

- Python 3.12+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL 17
- Pydantic Settings
- pytest, Ruff
- React
- TypeScript
- Vite
- ESLint

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

### 4. DB 마이그레이션

```bash
uv run alembic upgrade head
```

### 5. FastAPI 실행

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

### 6. React 프론트엔드 실행

별도 터미널에서 다음 명령을 실행합니다.

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

- 프론트엔드: `http://localhost:5173`
- 개발 중 `/api` 요청은 Vite 프록시를 통해 `http://localhost:8000`으로 전달됩니다.

## 현재 API

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/` | 애플리케이션 정보 |
| `GET` | `/health` | PostgreSQL 연결 상태 |
| `POST` | `/cards` | 카드 생성 |
| `GET` | `/cards` | 카드 목록 조회 |
| `GET` | `/cards/{card_id}` | 카드 단건 조회 |
| `PATCH` | `/cards/{card_id}` | 카드 수정 |
| `DELETE` | `/cards/{card_id}` | 카드와 소속 문제 삭제 |
| `POST` | `/cards/{card_id}/problems` | 문제 생성 |
| `GET` | `/cards/{card_id}/problems` | 문제 목록 조회 |
| `GET` | `/cards/{card_id}/problems?topic=주제` | 주제별 문제 조회 |
| `GET` | `/cards/{card_id}/problems/random` | 카드 전체에서 문제 무작위 조회 |
| `GET` | `/cards/{card_id}/problems/random?topic=주제` | 특정 주제에서 문제 무작위 조회 |
| `GET` | `/cards/{card_id}/problems/{problem_id}` | 문제 단건 조회 |
| `PATCH` | `/cards/{card_id}/problems/{problem_id}` | 문제 수정 |
| `DELETE` | `/cards/{card_id}/problems/{problem_id}` | 문제 삭제 |

카드는 `title`, 선택적인 `description`을 갖습니다. 문제는 `topic`, `question`, 선택적인 `answer`를 가지며 다른 카드로 이동하는 기능은 제공하지 않습니다.

랜덤 조회는 기본적으로 한 문제를 반환합니다. `limit` 쿼리 파라미터로 최대 100개까지 무작위로 조회할 수 있습니다.

프론트엔드에서는 카드 전체 또는 특정 주제를 범위로 정하고, 1~100 사이의 문제 개수를 직접 입력합니다. 한 번 반환된 문제 묶음 안에는 같은 문제가 중복되지 않으며, 요청한 개수보다 등록된 문제가 적으면 존재하는 문제만 제공합니다. 문제 제공 기준은 [문제 제공 및 랜덤 로직 기획서](docs/problem-delivery-random-plan.md)에 정리되어 있습니다.

## 테스트와 코드 검사

테스트는 격리된 SQLite DB를 사용하며 Docker나 PostgreSQL을 자동으로 실행하지 않습니다.

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

프론트엔드 검사:

```bash
cd frontend
npm run lint
npm run build
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
├── api/routes/       # 카드·문제 API
├── core/config.py    # 환경변수 설정
├── db/               # SQLAlchemy Base와 세션
├── models/           # Card·Problem DB 모델
├── schemas/          # 요청·응답 검증 모델
└── main.py           # FastAPI 애플리케이션
alembic/              # PostgreSQL 스키마 마이그레이션
tests/                # SQLite 기반 API 테스트
frontend/             # React·TypeScript 프론트엔드
docs/                 # 구현 전 검토할 기획 문서
```
