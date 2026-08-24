# Problem Bank

문제 은행 백엔드 프로젝트입니다. PostgreSQL과 Redis는 Docker Compose로 실행하고, Spring Boot 애플리케이션은 로컬 Java 환경에서 실행합니다.

```text
로컬 Spring Boot 애플리케이션 → localhost:25431 → Docker PostgreSQL
                           └→ localhost:6379 → Docker Redis
```

## 요구 사항

- Java 21
- Docker Desktop 또는 Docker Engine

프로젝트에는 Gradle Wrapper가 포함되어 있으므로 Gradle을 별도로 설치할 필요는 없습니다.

## 빠른 시작

### 1. PostgreSQL과 Redis 실행

```bash
docker compose up -d
```

실행 상태를 확인합니다.

```bash
docker compose ps
```

`db`와 `redis` 서비스가 모두 `healthy` 상태가 되면 사용할 수 있습니다.

### 2. Spring Boot 실행

```bash
./gradlew bootRun
```

애플리케이션은 기본적으로 `http://localhost:8080`에서 실행됩니다.

## 빌드

```bash
./gradlew clean build
```

생성된 JAR 파일을 직접 실행할 수도 있습니다.

```bash
java -jar build/libs/product-0.0.1-SNAPSHOT.jar
```

현재 기본 테스트는 Spring Context를 생성하므로 빌드와 테스트를 실행할 때 PostgreSQL이 먼저 실행되어 있어야 합니다.

## 기본 데이터베이스 설정

| 항목 | 기본값 |
| --- | --- |
| Host | `localhost` |
| Port | `25431` |
| Database | `problem_bank` |
| Username | `problem_bank` |
| Password | `problem_bank_local` |

Redis는 `localhost:6379`의 0번 데이터베이스를 사용하며 로컬 개발 환경에서는 별도 비밀번호를 설정하지 않습니다.

기본값은 로컬 개발 전용입니다. 설정을 변경하려면 `.env.example`을 복사해 Compose용 `.env` 파일을 만듭니다.

```bash
cp .env.example .env
```

DB 또는 Redis 설정을 변경했다면 애플리케이션 실행 환경에도 동일한 `POSTGRES_*`, `REDIS_*` 값을 지정해야 합니다. 기본값을 그대로 사용한다면 별도 환경변수 설정은 필요 없습니다.

## PostgreSQL 접속

실행 중인 PostgreSQL에 `psql`로 접속합니다.

```bash
docker compose exec db psql -U problem_bank -d problem_bank
```

Redis 연결 상태는 다음 명령으로 확인합니다.

```bash
docker compose exec redis redis-cli ping
```

정상이라면 `PONG`이 출력됩니다.

## 종료 및 데이터 초기화

DB와 Redis 컨테이너를 종료합니다. 데이터는 Docker 볼륨에 유지됩니다.

```bash
docker compose down
```

PostgreSQL과 Redis 데이터까지 완전히 삭제하려면 다음 명령을 사용합니다.

```bash
docker compose down -v
```

`-v` 옵션을 사용하면 저장된 PostgreSQL 데이터가 삭제되므로 주의하세요.

## 개발 설정 참고

- `spring.jpa.hibernate.ddl-auto=update`가 기본값이라 엔티티 변경이 로컬 DB 스키마에 반영됩니다.
- 현재 Spring Security는 모든 요청을 허용하도록 설정되어 있습니다.
- `ddl-auto=update`와 전체 요청 허용 설정은 운영 환경에 그대로 사용하면 안 됩니다.
