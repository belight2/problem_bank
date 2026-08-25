# Problem Bank

React·TypeScript 프론트엔드와 FastAPI 백엔드로 구성한 개인용 문제 은행입니다. PostgreSQL만 Docker Compose로 실행하고 애플리케이션은 로컬 환경에서 실행합니다.

```text
React (localhost:5571) → FastAPI (localhost:8899) → PostgreSQL (localhost:25431)
```

카드를 만들고 그 안에 주제를 별도로 관리한 뒤 문제에 연결할 수 있습니다. 문제 생성 시 등록된 주제를 선택하므로 문제마다 주제 이름을 다시 입력하면서 생기는 오타를 방지합니다. 문제는 단답형, 주관식, 객관식, O/X, 빈칸 추론 형식으로 만들 수 있으며, 프론트엔드에서는 카드·주제·문제 CRUD와 설정한 개수만큼 문제를 무작위로 제공하는 기능을 사용할 수 있습니다. 객관식과 O/X는 자동 채점하고 나머지 유형은 사용자가 직접 판정합니다.

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

Docker Desktop을 직접 실행한 뒤, 프로젝트 루트에서 백엔드와 DB를 실행합니다.

터미널 1:

```bash
cp .env.example .env
docker compose up -d db

uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8899
```

별도 터미널에서 프론트엔드를 실행합니다.

터미널 2:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

실행 후 아래 주소로 접속합니다.

- 프론트엔드: `http://localhost:5571`
- API: `http://localhost:8899`
- Swagger UI: `http://localhost:8899/docs`
- PostgreSQL: `localhost:25431`

아래부터는 각 단계를 나눠 설명합니다.

### 1. 환경 설정

```bash
cp .env.example .env
```

기본값을 그대로 사용한다면 `.env`를 수정할 필요가 없습니다.

### 2. PostgreSQL 실행

Docker Desktop을 직접 실행한 다음 필요한 경우 아래 명령을 직접 실행합니다.

```bash
docker compose up -d db
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

기존 문제의 문자열 주제는 이 과정에서 카드별 주제로 자동 변환되고, 문제는 생성된 주제와 연결됩니다.

### 5. FastAPI 실행

```bash
uv run uvicorn app.main:app --reload --port 8899
```

`pip` 환경에서는 다음 명령을 사용합니다.

```bash
uvicorn app.main:app --reload --port 8899
```

- API: `http://localhost:8899`
- Swagger UI: `http://localhost:8899/docs`
- OpenAPI JSON: `http://localhost:8899/openapi.json`

### 6. React 프론트엔드 실행

별도 터미널에서 다음 명령을 실행합니다.

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

- 프론트엔드: `http://localhost:5571`
- 개발 중 `/api` 요청은 Vite 프록시를 통해 `http://localhost:8899`로 전달됩니다.

## 현재 API

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/` | 애플리케이션 정보 |
| `GET` | `/health` | PostgreSQL 연결 상태 |
| `POST` | `/cards` | 카드 생성 |
| `GET` | `/cards` | 카드 목록 조회 |
| `GET` | `/cards/{card_id}` | 카드 단건 조회 |
| `PATCH` | `/cards/{card_id}` | 카드 수정 |
| `DELETE` | `/cards/{card_id}` | 카드와 소속 주제·문제 삭제 |
| `POST` | `/cards/{card_id}/topics` | 주제 생성 |
| `GET` | `/cards/{card_id}/topics` | 주제 목록 조회 |
| `GET` | `/cards/{card_id}/topics/{topic_id}` | 주제 단건 조회 |
| `PATCH` | `/cards/{card_id}/topics/{topic_id}` | 주제 이름 수정 |
| `DELETE` | `/cards/{card_id}/topics/{topic_id}` | 사용하지 않는 주제 삭제 |
| `POST` | `/cards/{card_id}/problems` | 문제 생성 |
| `GET` | `/cards/{card_id}/problems` | 문제 목록 조회 |
| `GET` | `/cards/{card_id}/problems?topic_id={topic_id}` | 주제별 문제 조회 |
| `GET` | `/cards/{card_id}/problems/random` | 카드 전체에서 문제 무작위 조회 |
| `GET` | `/cards/{card_id}/problems/random?topic_id={topic_id}` | 특정 주제에서 문제 무작위 조회 |
| `GET` | `/cards/{card_id}/problems/{problem_id}` | 문제 단건 조회 |
| `PATCH` | `/cards/{card_id}/problems/{problem_id}` | 문제 수정 |
| `DELETE` | `/cards/{card_id}/problems/{problem_id}` | 문제 삭제 |

카드는 `title`, 선택적인 `description`을 갖습니다. 주제는 카드 안에서 별도로 생성하며 같은 카드에는 동일한 이름의 주제를 중복 생성할 수 없습니다. 사용 중인 주제는 삭제할 수 없으므로 먼저 소속 문제의 주제를 변경하거나 문제를 삭제해야 합니다.

문제는 `topic_id`, `question`, 유형에 따라 필수 또는 선택인 `answer`를 가지며 응답에는 표시용 `topic_name`이 함께 포함됩니다. 다른 카드의 주제를 연결하거나 문제를 다른 카드로 이동하는 기능은 제공하지 않습니다.

### 문제 유형

| 화면 표시 | `problem_type` | 유형별 데이터 |
| --- | --- | --- |
| 단답형 | `short_answer` | 선택적인 짧은 정답 |
| 주관식 | `essay` | 선택적인 서술형 정답·해설 |
| 객관식 | `multiple_choice` | 2~10개의 `choices`, 필수 정답 선택지 |
| O/X | `true_false` | 필수 `O` 또는 `X` 정답 |
| 빈칸 추론 | `fill_blank` | `[빈칸]`이 한 번 들어간 문장, 선택적인 기준 답안·해설 |

객관식 정답은 `choices` 중 하나와 일치해야 하며 O/X 정답은 `O` 또는 `X`만 사용할 수 있습니다. 빈칸 추론 문제의 `question`에는 `[빈칸]` 표식을 정확히 한 번 넣어야 합니다.

랜덤 학습에서 객관식과 O/X는 선택한 답과 등록된 정답을 자동으로 비교합니다. 단답형, 주관식, 빈칸 추론은 사용자가 답안을 작성하고 기준 답안·해설을 확인한 뒤 직접 정답 또는 오답으로 판정합니다. 채점 결과는 현재 문제 묶음의 React 메모리에만 유지되며 DB에 학습 기록으로 저장하지 않습니다.

랜덤 조회는 기본적으로 한 문제를 반환합니다. `limit` 쿼리 파라미터로 최대 100개까지 무작위로 조회할 수 있습니다.

프론트엔드에서는 카드 전체 또는 등록된 특정 주제를 범위로 정하고, 1~100 사이의 문제 개수를 직접 입력합니다. 한 번 반환된 문제 묶음 안에는 같은 문제가 중복되지 않으며, 요청한 개수보다 등록된 문제가 적으면 존재하는 문제만 제공합니다. 문제 제공 기준은 [문제 제공 및 랜덤 로직 기획서](docs/problem-delivery-random-plan.md)에 정리되어 있습니다.

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
├── api/routes/       # 카드·주제·문제 API
├── core/config.py    # 환경변수 설정
├── db/               # SQLAlchemy Base와 세션
├── models/           # Card·Topic·Problem DB 모델
├── schemas/          # 요청·응답 검증 모델
└── main.py           # FastAPI 애플리케이션
alembic/              # PostgreSQL 스키마 마이그레이션
tests/                # SQLite 기반 API 테스트
frontend/             # React·TypeScript 프론트엔드
docs/                 # 구현 전 검토할 기획 문서
```
