# Problem Bank

React·TypeScript 프론트엔드와 FastAPI 백엔드로 구성한 개인용 문제 은행입니다. PostgreSQL과 Apache Jena Fuseki는 Docker Compose로 실행하고 애플리케이션은 로컬 환경에서 실행합니다.

```text
React (localhost:5571) → FastAPI (localhost:8899) → PostgreSQL (localhost:25431)
브라우저 ───────────────────────────────────────→ Fuseki (localhost:3030)
```

처음 실행할 때 로그인 없이 사용할 단일 프로필을 등록하며, 카드와 학습 기록은 모두 이 프로필에 저장됩니다. 홈 대시보드에서는 하루 학습 목표, 전체 정답률, 미해결 오답, 완료한 학습 수와 취약 주제를 확인할 수 있습니다.

카드를 만들고 그 안에 주제와 개념을 관리한 뒤 문제와 Markdown 공부 노트를 연결할 수 있습니다. 개념은 여러 카드에서 재사용할 수 있고, 상위·선수·관련·비교·혼동 관계를 연결할 수 있습니다. 문제에는 핵심 개념 하나와 보조 개념을, 노트에는 해당 노트가 설명하는 개념을 선택적으로 연결합니다. 문제는 단답형, 주관식, 객관식, O/X, 빈칸 추론 형식으로 만들 수 있습니다.

카드의 주제·개념·개념 관계·노트·문제를 `.pbcard.json` 파일로 내보내거나 새 카드로 불러올 수 있습니다. 풀이 통계·오답노트·문제집·프로필은 카드 파일에 포함하지 않습니다.

## 기술 스택

- Python 3.12+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL 17
- Apache Jena Fuseki 6.2
- RDF/OWL 온톨로지 및 SHACL 검증 규칙
- Pydantic Settings
- pytest, Ruff
- React
- TypeScript
- Vite
- ESLint

## 빠른 시작

Docker Desktop을 직접 실행한 뒤, 프로젝트 루트에서 백엔드와 데이터 서비스를 실행합니다.

터미널 1:

```bash
cp .env.example .env
docker compose up -d db fuseki

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
- Fuseki UI: `http://localhost:3030/#/dataset/problem-bank/query`
- SPARQL endpoint: `http://localhost:3030/problem-bank/sparql`

아래부터는 각 단계를 나눠 설명합니다.

### 1. 환경 설정

```bash
cp .env.example .env
```

기본값을 그대로 사용한다면 `.env`를 수정할 필요가 없습니다.

### 2. PostgreSQL과 Fuseki 실행

Docker Desktop을 직접 실행한 다음 필요한 경우 아래 명령을 직접 실행합니다.

```bash
docker compose up -d db fuseki
docker compose ps
```

처음 실행할 때는 Apache Jena Fuseki 6.2.0 공식 배포본을 사용하는 로컬 이미지를 빌드합니다. Fuseki는 `127.0.0.1`에만 공개되며 다음 주소에서 온톨로지를 조회할 수 있습니다.

- 관리·SPARQL UI: `http://localhost:3030/#/dataset/problem-bank/query`
- SPARQL Query: `http://localhost:3030/problem-bank/sparql`
- SPARQL Update: `http://localhost:3030/problem-bank/update`
- Graph Store: `http://localhost:3030/problem-bank/data`

`ontology/problem-bank.ttl`과 `ontology/shapes.ttl`은 컨테이너 시작 시 직접 읽습니다. 정보처리기사 예제 그래프는 `fuseki-data` 볼륨에 최초 한 번만 적재하며, 저장된 RDF 데이터는 컨테이너를 다시 만들어도 유지됩니다. 온톨로지 또는 SHACL 파일을 수정했다면 아래 명령으로 Fuseki만 다시 시작합니다.

```bash
docker compose restart fuseki
```

Fuseki에서는 OWL Micro 추론을 적용합니다. SHACL 파일은 조회할 수 있도록 함께 불러오지만 요청 데이터에 대한 SHACL 검증을 자동으로 강제하지는 않습니다. 저장소의 온톨로지 테스트가 SHACL 규칙을 검증합니다.

카드·주제·개념·문제·노트 CRUD, 개념 관계, 문제 풀이 통계 변경은 PostgreSQL의 `graph_outbox`에 Fuseki 동기화 이벤트를 같은 트랜잭션으로 기록합니다. FastAPI가 실행되면 백그라운드 작업자가 이벤트 순서대로 SPARQL Update를 전송하고, 성공한 이벤트를 `completed`로 변경합니다. Fuseki 연결이나 전송에 실패하면 지수 백오프로 재시도하며, 설정한 최대 횟수를 넘긴 이벤트는 `failed`로 남겨 뒤 이벤트 처리를 막지 않습니다.

동기화 설정은 `.env`의 `FUSEKI_*`와 `GRAPH_SYNC_*` 항목에서 바꿀 수 있습니다. 작업자를 잠시 끄려면 `GRAPH_SYNC_ENABLED=false`로 설정합니다. 문제의 정답·선택지와 노트 본문은 그래프에 보내지 않고, 관계 탐색에 필요한 제목·주제·개념·개념 관계·문제 유형·출제 통계·출처 노트 관계만 저장합니다.

Outbox 도입 전에 이미 PostgreSQL에 있던 데이터는 아래 명령으로 소급 적재 이벤트를 만들 수 있습니다.

```bash
uv run python -m app.commands.backfill_graph
```

명령은 개념 → 카드 → 주제 → 노트 → 문제 순서로 현재 상태를 Outbox에 넣습니다. FastAPI가 실행 중이면 백그라운드 작업자가 이어서 처리하고, 실행 중이 아니라면 다음 FastAPI 시작 때 처리합니다. 같은 명령을 다시 실행해도 RDF 결과가 중복되지 않습니다.

동기화 상태와 실패 이벤트는 API에서 확인할 수 있습니다.

- `GET /graph-sync/status`: 상태별 이벤트 수와 최근 처리 시각
- `GET /graph-sync/events/failed`: 실패 이벤트 목록
- `POST /graph-sync/events/{event_id}/retry`: 최신 PostgreSQL 상태로 재처리 이벤트 생성

재처리할 때 실패했던 payload를 그대로 다시 사용하지 않습니다. 현재 엔티티가 있으면 최신 상태의 `upsert`, 이미 삭제되었다면 `delete` 이벤트를 새로 만들고 기존 실패 이벤트는 `superseded` 상태로 보존합니다.

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
| `GET` | `/cards/{card_id}/package` | 카드 학습 콘텐츠 내보내기 |
| `POST` | `/card-packages/preview` | 카드 파일 검증 및 가져오기 미리보기 |
| `POST` | `/card-packages/import` | 카드 파일을 새 카드로 가져오기 |
| `GET` | `/cards/{card_id}/knowledge-graph` | 카드의 지식 그래프를 노드·간선 형태로 조회 |
| `PATCH` | `/cards/{card_id}` | 카드 수정 |
| `DELETE` | `/cards/{card_id}` | 카드와 소속 주제·문제·노트 삭제 |
| `POST` | `/cards/{card_id}/topics` | 주제 생성 |
| `GET` | `/cards/{card_id}/topics` | 주제 목록 조회 |
| `GET` | `/cards/{card_id}/topics/{topic_id}` | 주제 단건 조회 |
| `PATCH` | `/cards/{card_id}/topics/{topic_id}` | 주제 이름 수정 |
| `DELETE` | `/cards/{card_id}/topics/{topic_id}` | 사용하지 않는 주제 삭제 |
| `POST` | `/concepts` | 재사용 가능한 개념 생성 |
| `GET` | `/concepts` | 프로필의 개념 목록 조회 |
| `PATCH` | `/concepts/{concept_id}` | 개념 수정 |
| `DELETE` | `/concepts/{concept_id}` | 개념과 모든 연결 삭제 |
| `GET` | `/cards/{card_id}/concepts` | 카드에 연결된 개념 조회 |
| `PUT` | `/cards/{card_id}/concepts/{concept_id}` | 기존 개념을 카드에 연결 |
| `DELETE` | `/cards/{card_id}/concepts/{concept_id}` | 사용 중이 아닌 개념을 카드에서 해제 |
| `GET` | `/concept-relations` | 개념 관계 목록 조회 |
| `POST` | `/concept-relations` | 개념 관계 생성 |
| `DELETE` | `/concept-relations/{relation_id}` | 개념 관계 삭제 |
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

카드 파일에는 `format_version`이 포함됩니다. 가져오기는 항상 새 카드를 만들며 파일 안의 참조를 새 DB ID로 다시 연결합니다. 현재 프로필에 같은 이름의 개념이 있으면 새로 만들지 않고 기존 개념을 연결하며, 전체 내용을 저장할 수 없으면 카드 생성을 포함한 변경을 모두 취소합니다. 가져온 카드도 일반 CRUD와 동일하게 Outbox 동기화 이벤트를 생성합니다.

개념은 프로필 단위에서 이름이 중복되지 않으며 여러 카드에 연결할 수 있습니다. 문제나 노트가 사용 중인 개념은 해당 카드에서 바로 해제할 수 없습니다. 문제의 `primary_concept_id`는 하나의 핵심 개념, `supporting_concept_ids`는 보조 개념, 노트의 `concept_ids`는 설명하는 개념입니다. 이 개념들은 먼저 해당 카드에 연결되어 있어야 합니다.

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

카드 지식 그래프 API는 Fuseki에서 카드와 소속 주제·문제·노트 및 연결된 개념·오개념을 조회해 `nodes`, `edges`로 반환합니다. `limit` 쿼리 파라미터는 최대 500개 관계까지 허용하며, 조회 결과가 잘렸는지는 응답의 `truncated`로 확인할 수 있습니다. Fuseki에 연결할 수 없으면 API는 `503 Service Unavailable`을 반환합니다.

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

## Fuseki 기본 설정

| 항목 | 기본값 |
| --- | --- |
| Host | `localhost` |
| Port | `3030` |
| Dataset | `problem-bank` |
| 저장소 | Docker volume `fuseki-data` |
| 추론기 | Jena OWL Micro Rule Reasoner |

Fuseki 로그는 다음 명령으로 확인합니다.

```bash
docker compose logs -f fuseki
```

## 종료와 데이터 초기화

```bash
docker compose down
```

위 명령은 컨테이너만 제거하며 PostgreSQL과 Fuseki 데이터는 Docker 볼륨에 유지합니다. 데이터까지 삭제하려면 다음 명령을 직접 실행해야 합니다.

```bash
docker compose down -v
```

`-v` 옵션은 저장된 PostgreSQL 데이터와 Fuseki RDF 데이터를 모두 삭제하므로 주의하세요.

## 프로젝트 구조

```text
app/
├── api/routes/       # 카드·주제·개념·문제·노트 API
├── core/config.py    # 환경변수 설정
├── db/               # SQLAlchemy Base와 세션
├── models/           # Card·Topic·Concept·Problem·Note DB 모델
├── schemas/          # 요청·응답 검증 모델
└── main.py           # FastAPI 애플리케이션
alembic/              # PostgreSQL 스키마 마이그레이션
tests/                # SQLite 기반 API 테스트
frontend/             # React·TypeScript 프론트엔드
docs/                 # 구현 전 검토할 기획 문서
docker/fuseki/        # Fuseki 이미지·dataset·자동 적재 설정
ontology/             # OWL 온톨로지·SHACL 규칙·예제 RDF 데이터
```

온톨로지의 클래스와 관계, TTL 시각화 방법은 [온톨로지 문서](ontology/README.md)에 정리되어 있습니다.
