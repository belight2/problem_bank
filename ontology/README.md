# Problem Bank Ontology

문제은행의 학습 지식을 RDF/OWL로 표현하는 온톨로지입니다. 운영 데이터는 PostgreSQL에 유지하고, 이 디렉터리는 개념과 의미 관계 및 검증 규칙을 관리합니다.

## 파일

- `problem-bank.ttl`: 클래스, 관계, 문제 유형과 추론 가능한 속성을 정의한 OWL 온톨로지
- `shapes.ttl`: 데이터 구조와 카드 경계를 검증하는 SHACL 규칙
- `examples/information-processing-engineer.ttl`: 정보처리기사 데이터베이스 영역 예제 그래프

## 핵심 모델

```text
학습 카드 ──주제를 포함함──> 주제 ──개념을 분류함──> 개념
    │                                              │
    ├──문제──평가함────────────────────────────────┤
    └──노트──설명함────────────────────────────────┘

개념 ──선수 개념임──> 개념
개념 ──상위 개념──> 개념
개념 ──혼동하기 쉬움──> 개념
문제 ──노트에서 파생됨──> 노트
오개념 ──개념에 대한 오개념임──> 개념
```

`Concept`는 특정 카드에 종속시키지 않았습니다. 동일한 개념을 여러 자격증 카드나 학습 영역에서 재사용할 수 있고, `StudyCard usesConcept Concept` 관계로 카드별 지식 범위를 정합니다.

## TTL과 시각화

TTL은 Turtle 문법으로 직렬화한 RDF 텍스트 파일입니다. 파일 자체가 이미지인 것은 아니지만 다음 도구에 불러오면 클래스와 인스턴스 및 관계를 그래프로 볼 수 있습니다.

- Apache Jena Fuseki: 데이터를 적재하고 SPARQL로 그래프를 조회
- Protégé: `problem-bank.ttl`의 클래스와 객체 속성을 온톨로지 그래프로 탐색
- RDF 시각화 도구: 예제 TTL을 불러와 노드와 간선을 바로 탐색

Fuseki의 기본 화면은 관리와 SPARQL 조회 용도입니다. 실제 사용자가 보는 지식 지도는 React에서 별도로 구현하고, Fuseki의 조회 결과만 사용합니다.

프로젝트 루트에서 다음 명령을 직접 실행하면 Fuseki를 시작할 수 있습니다.

```bash
docker compose up -d fuseki
```

- Fuseki UI: `http://localhost:3030/#/dataset/problem-bank/query`
- SPARQL endpoint: `http://localhost:3030/problem-bank/sparql`

`problem-bank.ttl`과 `shapes.ttl`은 시작할 때마다 읽으며, 예제 데이터는 `fuseki-data` 볼륨에 최초 한 번만 적재합니다. dataset에는 OWL Micro 추론기가 적용됩니다. SHACL 규칙은 Fuseki가 쓰기 요청마다 자동 검증하는 구조가 아니며, 현재는 `tests/test_ontology.py`에서 검증합니다.

## 애플리케이션 데이터 동기화

FastAPI는 PostgreSQL의 `graph_outbox`를 읽는 백그라운드 작업자를 실행합니다. 카드·주제·개념·문제·노트, 개념 관계, 문제별 출제·정답·오답 횟수를 안정적인 리소스 IRI로 변환한 뒤 Fuseki의 SPARQL Update endpoint에 반영합니다.

```text
card-{id}
topic-{id}
problem-{id}
note-{id}
concept-{id}
```

동일한 리소스의 갱신은 PostgreSQL이 관리하는 속성과 관계만 지우고 현재 상태를 다시 넣는 멱등 방식입니다. 카드의 `usesConcept`, 문제의 `primaryConcept`·`supportingConcept`, 노트의 `explains`, 개념 간 관계를 CRUD 변경과 함께 동기화합니다. 전송 성공 뒤 DB 상태 기록 전에 프로세스가 종료되어 같은 이벤트가 다시 처리되더라도 결과가 중복되지 않습니다. 문제의 정답·선택지와 노트의 Markdown 본문은 RDF payload에 포함하지 않습니다.

예제 데이터에서 주요 개념 관계를 조회하는 SPARQL은 다음과 같습니다.

```sparql
PREFIX pb: <https://belight2.github.io/problem_bank/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?fromLabel ?relation ?toLabel
WHERE {
  VALUES ?relation {
    pb:prerequisiteOf
    pb:broaderConcept
    pb:relatedConcept
    pb:contrastsWith
    pb:commonlyConfusedWith
  }

  ?from ?relation ?to ;
        skos:prefLabel ?fromLabel .
  ?to skos:prefLabel ?toLabel .
}
ORDER BY ?fromLabel ?relation ?toLabel
```

## 관계 방향

`prerequisiteOf`는 먼저 알아야 하는 개념에서 이후에 학습할 개념을 향합니다.

```text
함수 종속성 prerequisiteOf 제2정규형
제2정규형 prerequisiteOf 제3정규형
```

이 속성은 `owl:TransitiveProperty`로 선언했습니다. 추론을 활성화하면 함수 종속성이 제3정규형의 간접 선수 개념이라는 사실을 얻을 수 있습니다.

`broaderConcept`는 세부 개념에서 상위 개념을 향합니다.

```text
제3정규형 broaderConcept 정규화
```

Fuseki dataset은 Jena OWL Micro Rule Reasoner를 사용하므로 `owl:TransitiveProperty`, 역속성, 대칭 속성 등 기본 OWL 추론 결과를 SPARQL에서 조회할 수 있습니다.

## 식별자 규칙

- 온톨로지 namespace: `https://belight2.github.io/problem_bank/ontology#`
- 데이터 resource namespace: `https://belight2.github.io/problem_bank/resource/`
- PostgreSQL 엔티티: `pb:externalId`로 기존 정수 ID 연결
- PostgreSQL에서 생성한 개념: `concept-{id}` IRI와 `pb:externalId` 사용
- 정적 예제의 개념과 오개념: 영문 소문자와 하이픈으로 된 `dcterms:identifier` 사용

아직 실제 GraphDB 데이터가 없는 단계이므로 namespace는 `0.1.0` 동안 변경할 수 있습니다. 실제 데이터를 생성하기 시작한 뒤에는 기존 URI가 깨지지 않도록 유지합니다.
