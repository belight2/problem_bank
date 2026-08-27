# Problem Bank

React·TypeScript 프론트엔드와 FastAPI 백엔드로 구성한 개인용 문제 은행입니다. PostgreSQL만 Docker Compose로 실행하고 애플리케이션은 로컬 환경에서 실행합니다.

```text
React (localhost:5571) → FastAPI (localhost:8899) → PostgreSQL (localhost:25431)
```

처음 실행할 때 로그인 없이 사용할 단일 프로필을 등록하며, 카드와 학습 기록은 모두 이 프로필에 저장됩니다. 홈 대시보드에서는 하루 학습 목표, 전체 정답률, 미해결 오답, 완료한 학습 수와 취약 주제를 확인할 수 있습니다.

카드를 만들고 그 안에 주제를 별도로 관리한 뒤 문제와 Markdown 공부 노트를 연결할 수 있습니다. 문제 생성 시 등록된 주제를 선택하므로 문제마다 주제 이름을 다시 입력하면서 생기는 오타를 방지합니다. 노트에서 바로 문제를 만들면 해당 노트가 선택적으로 문제의 참고 자료로 연결됩니다. 문제는 단답형, 주관식, 객관식, O/X, 빈칸 추론 형식으로 만들 수 있으며, 프론트엔드에서는 카드·주제·문제·노트 CRUD와 설정한 개수만큼 문제를 무작위로 제공하는 기능을 사용할 수 있습니다. 객관식과 O/X는 자동 채점하고 나머지 유형은 사용자가 직접 판정합니다.

## 기술 스택

- Python 3.12+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL 17
- RDF/OWL 온톨로지 및 SHACL 검증 규칙
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
| `GET` | `/profile` | 단일 로컬 프로필 조회 및 최초 기본 프로필 생성 |
| `PUT` | `/profile` | 프로필 이름·시간대·하루 목표 등록 또는 수정 |
| `GET` | `/dashboard` | 현재 프로필의 전체 학습 현황과 취약 주제 조회 |
| `POST` | `/cards` | 카드 생성 |
| `GET` | `/cards` | 카드 목록 조회 |
| `GET` | `/cards/{card_id}` | 카드 단건 조회 |
| `PATCH` | `/cards/{card_id}` | 카드 수정 |
| `DELETE` | `/cards/{card_id}` | 카드와 소속 주제·문제·노트 삭제 |
| `POST` | `/cards/{card_id}/topics` | 주제 생성 |
| `GET` | `/cards/{card_id}/topics` | 주제 목록 조회 |
| `GET` | `/cards/{card_id}/topics/{topic_id}` | 주제 단건 조회 |
| `PATCH` | `/cards/{card_id}/topics/{topic_id}` | 주제 이름 수정 |
| `DELETE` | `/cards/{card_id}/topics/{topic_id}` | 사용하지 않는 주제 삭제 |
| `POST` | `/cards/{card_id}/notes` | Markdown 노트 생성 |
| `GET` | `/cards/{card_id}/notes` | 노트 목록 조회 |
| `GET` | `/cards/{card_id}/notes/{note_id}` | 노트 단건 조회 |
| `PATCH` | `/cards/{card_id}/notes/{note_id}` | 노트 수정 |
| `DELETE` | `/cards/{card_id}/notes/{note_id}` | 노트 삭제 및 문제의 참고 연결 해제 |
| `POST` | `/cards/{card_id}/problems` | 문제 생성 |
| `GET` | `/cards/{card_id}/problems` | 문제 목록 조회 |
| `GET` | `/cards/{card_id}/problems?topic_id={topic_id}` | 주제별 문제 조회 |
| `GET` | `/cards/{card_id}/problems/{problem_id}` | 문제 단건 조회 |
| `PATCH` | `/cards/{card_id}/problems/{problem_id}` | 문제 수정 |
| `DELETE` | `/cards/{card_id}/problems/{problem_id}` | 문제 삭제 |
| `POST` | `/cards/{card_id}/workbooks` | 설정한 출제 기준으로 문제집 생성 및 첫 풀이 회차 시작 |
| `GET` | `/cards/{card_id}/workbooks` | 문제집과 풀이 회차 이력 조회 |
| `GET` | `/cards/{card_id}/workbooks/{workbook_id}` | 문제집 단건 조회 |
| `PATCH` | `/cards/{card_id}/workbooks/{workbook_id}` | 문제집 이름 수정 |
| `DELETE` | `/cards/{card_id}/workbooks/{workbook_id}` | 문제집과 풀이 이력 삭제 |
| `POST` | `/cards/{card_id}/workbooks/{workbook_id}/attempts` | 동일한 문제와 순서로 새 풀이 회차 시작 |
| `POST` | `/cards/{card_id}/workbooks/{workbook_id}/regenerate` | 같은 설정으로 문제를 다시 추출한 새 문제집 생성 |
| `POST` | `/cards/{card_id}/workbooks/{workbook_id}/attempts/{session_id}/results` | 문제집 풀이 회차의 답안과 채점 결과 기록 |

카드는 `title`, 선택적인 `description`을 갖습니다. 주제는 카드 안에서 별도로 생성하며 같은 카드에는 동일한 이름의 주제를 중복 생성할 수 없습니다. 사용 중인 주제는 삭제할 수 없으므로 먼저 소속 문제의 주제를 변경하거나 문제를 삭제해야 합니다.

문제는 `topic_id`, `question`, 유형에 따라 필수 또는 선택인 `answer`를 가지며 응답에는 표시용 `topic_name`이 함께 포함됩니다. 다른 카드의 주제를 연결하거나 문제를 다른 카드로 이동하는 기능은 제공하지 않습니다.

노트는 `title`, `content_markdown`, 선택적인 `topic_id`를 가집니다. 노트 화면에서 문제를 만들면 `source_note_id`로 출처를 연결하며, 연결은 문제 생성 화면에서 해제할 수 있습니다. 출처 노트를 삭제해도 문제는 유지됩니다. 문제집을 푸는 동안에는 답안을 모두 제출하기 전까지 노트를 노출하지 않고, 일괄 채점 화면에서 필요한 노트만 펼쳐 볼 수 있습니다.

### 문제 유형

| 화면 표시 | `problem_type` | 유형별 데이터 |
| --- | --- | --- |
| 단답형 | `short_answer` | 선택적인 짧은 정답 |
| 주관식 | `essay` | 선택적인 서술형 정답·해설 |
| 객관식 | `multiple_choice` | 2~10개의 `choices`, 필수 정답 선택지 |
| O/X | `true_false` | 필수 `O` 또는 `X` 정답 |
| 빈칸 추론 | `fill_blank` | 문장 안에 지정한 빈칸 한 곳, 선택적인 기준 답안·해설 |

객관식 정답은 `choices` 중 하나와 일치해야 하며 O/X 정답은 `O` 또는 `X`만 사용할 수 있습니다. 빈칸 추론 문제는 프론트엔드에서 문장을 작성한 뒤 핵심 부분을 선택해 빈칸으로 지정합니다. 선택한 내용은 기준 답안으로 자동 입력됩니다.

문제집에서는 모든 답안을 제출한 뒤 한 화면에서 일괄 채점합니다. 객관식과 O/X는 선택한 답과 등록된 정답을 자동으로 비교하고, 단답형·주관식·빈칸 추론은 전체 채점 화면에서 사용자가 기준 답안·해설을 확인한 뒤 직접 정답 또는 오답으로 판정합니다. 문제별 제출 답안과 판정 결과는 풀이 회차에 저장되며 출제·정답·오답 횟수도 DB에 누적합니다.

문제집을 만들 때는 설정한 개수만큼 최대 100개까지 가중치 기반으로 문제를 선택합니다. 가중치는 아래 식으로 계산하며, 오답 비율이 높거나 출제 횟수가 적은 문제일수록 선택 확률이 높아집니다.

```text
가중치 = 1 + 6 × ((오답 횟수 + 1) / (정답 횟수 + 오답 횟수 + 2)) + 2 / (출제 횟수 + 1)
```

한 문제집 안에서는 가중치 추출 후 선택된 문제를 후보에서 제거하므로 중복되지 않습니다. 문제집의 풀이 회차를 시작할 때 출제 횟수를 올리고, 전체 채점 완료 시 정답·오답 횟수를 반영합니다. 동일 풀이 회차의 결과가 다시 전송돼도 횟수는 중복 집계되지 않습니다.

출제 기준은 전체 문제, 오답률, 오답 횟수 중에서 선택합니다. 오답률 기준은 `오답 횟수 / (정답 횟수 + 오답 횟수)`로 계산하고 최소 풀이 횟수를 함께 적용합니다. 오답 횟수 기준은 누적 오답 횟수가 설정값 이상인 문제만 후보로 사용합니다. 조건을 통과한 후보 안에서는 기존 가중치 추출을 그대로 적용합니다.

프론트엔드에서는 카드 전체 또는 등록된 특정 주제를 범위로 정하고, 1~100 사이의 문제 개수와 출제 기준을 설정합니다. 이 값은 기본 설정과 문제집 템플릿에 저장됩니다. 문제집은 선택된 문제와 순서를 유지하므로 동일 문제집을 다시 풀 수 있고, 같은 설정으로 문제를 다시 추출해 별도의 새 문제집도 만들 수 있습니다. 요청한 개수보다 조건을 만족하는 문제가 적으면 존재하는 문제만 포함합니다. 문제 제공 기준은 [문제 제공 및 랜덤 로직 기획서](docs/problem-delivery-random-plan.md)에 정리되어 있습니다.

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
├── api/routes/       # 카드·주제·문제·노트 API
├── core/config.py    # 환경변수 설정
├── db/               # SQLAlchemy Base와 세션
├── models/           # Card·Topic·Problem·Note DB 모델
├── schemas/          # 요청·응답 검증 모델
└── main.py           # FastAPI 애플리케이션
alembic/              # PostgreSQL 스키마 마이그레이션
tests/                # SQLite 기반 API 테스트
frontend/             # React·TypeScript 프론트엔드
docs/                 # 구현 전 검토할 기획 문서
ontology/             # OWL 온톨로지·SHACL 규칙·예제 RDF 데이터
```

온톨로지의 클래스와 관계, TTL 시각화 방법은 [온톨로지 문서](ontology/README.md)에 정리되어 있습니다.
