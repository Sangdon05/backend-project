# Backend Project API

FastAPI + SQLAlchemy(async) 기반의 회원·인증·게시판 REST API 서버입니다.
기능은 `feature/<도메인>/{domain,application,infrastructure,presentation}` 레이어로 나뉘며,
구현체 주입은 `wiring/` 에서 `app.dependency_overrides` 로 바인딩합니다.

---

## 1. 프로젝트 개발 환경

### 기술 스택

| 구분 | 사용 기술 |
|---|---|
| 언어 | Python 3.13 (`.python-version`) |
| 웹 프레임워크 | FastAPI, Uvicorn |
| ORM / DB 드라이버 | SQLAlchemy 2.x (async), asyncpg |
| 데이터베이스 | PostgreSQL |
| 인증 | JWT (PyJWT, HS512), bcrypt 비밀번호 해시 |
| 검증 | Pydantic v2 (`pydantic[email]`) |
| 패키지 관리 | uv (`pyproject.toml`, `uv.lock`) |
| 린트 | ruff (별도 설치) |

### 디렉터리 구조

```text
.
├── main.py                 # 앱 생성, 라우터 등록, lifespan(테이블 생성/DB 종료)
├── feature/
│   ├── auth/               # 로그인·로그아웃, JWT 발급/검증, 토큰 블랙리스트
│   ├── user/               # 회원가입, 내 정보, 비밀번호 변경
│   └── board/              # 게시판 설정, 게시글, 댓글
│       ├── domain/         # 엔티티·도메인 규칙·리포지토리 인터페이스
│       ├── application/    # 유스케이스 서비스
│       ├── infrastructure/ # SQLAlchemy 모델·리포지토리 구현
│       └── presentation/   # 라우터·요청/응답 스키마·의존성 placeholder
├── shared/core/            # DB 세션, 공통 응답, 예외/핸들러, 보안 스킴, 로거
└── wiring/                 # placeholder 의존성 → 실제 구현 바인딩
```

### 환경 변수 (`.env`)

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://postgres:postgres@localhost:5432/postgres` | async 드라이버(`postgresql+asyncpg`) URL |
| `JWT_SECRET_KEY` | ✅ | (없음) | JWT 서명 키. 미설정 시 기동 실패 |
| `JWT_EXPIRE_MINUTES` | | `60` | 액세스 토큰 유효 시간(분) |
| `SQL_ECHO` | | `False` | `true` 면 실행 SQL 로그 출력 |
| `CONNECTION_POOL_SIZE` | | `10` | 커넥션 풀 크기 |
| `CONNECTION_POOL_MAX_SIZE` | | `20` | 풀 초과 허용 커넥션 수(max_overflow) |

```dotenv
DATABASE_URL="postgresql+asyncpg://postgres:<password>@localhost:5432/postgres"
JWT_SECRET_KEY="<충분히 긴 임의 문자열>"
SQL_ECHO=False
```

### 실행

```bash
uv sync                              # 의존성 설치 (.venv 생성)
uv run python main.py                # 개발 서버 (reload) — http://127.0.0.1:8000
# 또는
uv run uvicorn main:app --reload
```

- Swagger UI: <http://127.0.0.1:8000/docs> / ReDoc: <http://127.0.0.1:8000/redoc>
- 인증이 필요한 API는 `POST /v1/auth/login` 으로 받은 `access_token` 을
  Swagger의 **Authorize** 에 입력하면 `Authorization: Bearer <token>` 헤더로 전송됩니다.
- 린트: `ruff check .`

### 테이블 생성 방식

마이그레이션 도구(Alembic 등)는 사용하지 않습니다. 서버 기동 시 `create_tables()` 가
`Base.metadata.create_all` 로 **없는 테이블만** 생성하며, 기존 테이블의 컬럼 변경은 반영하지 않습니다.
모델을 바꿨다면 해당 테이블을 직접 정리한 뒤 재기동해야 합니다.

### 관리자 계정

관리자 지정 API는 없습니다. 회원가입 후 DB에서 직접 권한을 변경합니다.

```sql
UPDATE users SET role = 'ADMIN' WHERE email = 'user01@example.com';
```

---

## 2. 스키마 설명

### ER 다이어그램

```mermaid
erDiagram
    users ||--o{ posts : "author_id (SET NULL)"
    users ||--o{ comments : "author_id (SET NULL)"
    boards ||--o{ posts : "board_id"
    posts ||--o{ comments : "post_id"

    users {
        uuid id PK
        varchar email UK
        varchar name
        varchar password_hash
        varchar role
        boolean resign
    }
    token_blacklist {
        varchar jti PK
        timestamptz expired_at
    }
    boards {
        varchar id PK
        varchar board_name
        int page_size
        varchar edit_role
        varchar view_role
        varchar list_role
        varchar comment_list_role
        varchar comment_edit_role
    }
    posts {
        bigint id PK
        varchar board_id FK
        varchar title
        text content
        varchar author_name
        uuid author_id FK
        varchar guest_password
    }
    comments {
        bigint id PK
        bigint post_id FK
        text content
        varchar author_name
        uuid author_id FK
        varchar guest_password
    }
```

### 공통 컬럼 (`DateTimeBase`)

`users`, `boards`, `posts`, `comments` 에 포함됩니다. 모두 `timestamptz`(UTC)입니다.

| 컬럼 | Null | 설명 |
|---|---|---|
| `created_at` | N | 생성 일시 |
| `modified_at` | Y | 수정 시 자동 갱신 |
| `deleted_at` | Y | 소프트 삭제 일시 (값이 있으면 삭제된 것으로 간주) |

### `users` — 회원

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | UUID | PK | 회원 ID (uuid4) |
| `email` | VARCHAR(255) | UNIQUE, INDEX | 로그인 이메일 |
| `name` | VARCHAR(50) | NOT NULL | 이름 (입력 2~20자) |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt 해시 |
| `role` | VARCHAR(20) | 기본 `USER` | `USER` / `ADMIN` |
| `resign` | BOOLEAN | 기본 `false` | 탈퇴 여부 (탈퇴 회원 토큰은 401) |

### `token_blacklist` — 로그아웃된 토큰

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `jti` | VARCHAR(36) | PK | JWT 고유 식별자 |
| `expired_at` | TIMESTAMPTZ | INDEX | 토큰 만료 시각 (만료분 정리 기준) |

### `boards` — 게시판 설정

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | VARCHAR(30) | PK | 게시판 ID. `^[a-z][a-z0-9_-]{1,29}$` (예: `freetalk`) |
| `board_name` | VARCHAR(100) | NOT NULL | 표시 이름 (입력 1~50자) |
| `page_size` | INTEGER | 기본 20 | 페이지당 게시글 수 (1~100) |
| `list_role` | VARCHAR(20) | 기본 `ALL` | 게시글 목록 열람 권한 |
| `view_role` | VARCHAR(20) | 기본 `ALL` | 게시글 상세 열람 권한 |
| `edit_role` | VARCHAR(20) | 기본 `ALL` | 게시글 작성/수정/삭제 권한 |
| `comment_list_role` | VARCHAR(20) | 기본 `ALL` | 댓글 목록 열람 권한 |
| `comment_edit_role` | VARCHAR(20) | 기본 `ALL` | 댓글 작성/수정/삭제 권한 |

**권한 등급 (`Role`)**: `ALL`(0, 비회원 포함) < `USER`(1, 회원) < `ADMIN`(2).
요청자의 등급이 게시판에 설정된 등급 이상이면 허용됩니다. 비로그인 요청자는 `ALL` 입니다.

### `posts` — 게시글

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | BIGINT | PK, 자동 증가 | 게시글 ID |
| `board_id` | VARCHAR(30) | FK → `boards.id` | 소속 게시판 |
| `title` | VARCHAR(255) | NOT NULL | 제목 (입력 1~200자) |
| `content` | TEXT | NOT NULL | 본문 |
| `author_name` | VARCHAR(50) | NOT NULL | 작성자 표시 이름 (회원 이름 또는 비회원 닉네임) |
| `author_id` | UUID | FK → `users.id` (ON DELETE SET NULL), INDEX | 회원 작성자 ID. 비회원이면 NULL |
| `guest_password` | VARCHAR(65) | NULL | 비회원 비밀번호 해시 |

인덱스: `ix_posts_id_deleted_at(id, deleted_at)`, `ix_posts_author_id(author_id)`

### `comments` — 댓글

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | BIGINT | PK, 자동 증가 | 댓글 ID |
| `post_id` | BIGINT | FK → `posts.id` | 대상 게시글 |
| `content` | TEXT | NOT NULL | 내용 |
| `author_name` | VARCHAR(50) | NOT NULL | 작성자 표시 이름 |
| `author_id` | UUID | FK → `users.id` (ON DELETE SET NULL) | 회원 작성자 ID. 비회원이면 NULL |
| `guest_password` | VARCHAR(65) | NULL | 비회원 비밀번호 해시 |

인덱스: `ix_comments_post_id_deleted_at(post_id, deleted_at)`

---

## 3. API 명세

### 공통 사항

- Base URL: `http://127.0.0.1:8000`
- 인증: `Authorization: Bearer <access_token>`
- 모든 응답은 아래 공통 포맷(`APIResponse`)으로 감쌉니다. (로그아웃 `204` 제외)

```json
{
  "success": true,
  "code": "OK",
  "message": "요청이 성공적으로 처리되었습니다.",
  "errors": null,
  "data": { },
  "responded_at": "2026-11-17T04:54:05.002822Z"
}
```

| 필드 | 설명 |
|---|---|
| `success` | 처리 성공 여부 |
| `code` | 성공 시 `OK`, 실패 시 에러 코드 |
| `message` | 결과 설명 |
| `errors` | 실패 시 필드별 오류 (`{"필드명": ["오류 메시지"]}`) |
| `data` | 성공 시 응답 데이터 |
| `responded_at` | 응답 시각 (UTC) |

#### 에러 코드

| HTTP | `code` | 발생 상황 |
|---|---|---|
| 400 | `BAD_REQUEST` | 잘못된 요청 |
| 401 | `UNAUTHORIZED` | 토큰 없음·만료·위조·로그아웃된 토큰, 로그인 실패, 탈퇴 회원 |
| 403 | `FORBIDDEN` | 관리자 권한 필요, 게시판 권한 등급 미달, 작성자/비밀번호 불일치 |
| 404 | `NOT_FOUND` | 대상 없음 또는 삭제됨 |
| 409 | `CONFLICT` | 중복 (이메일, 게시판 ID 등) |
| 422 | `REQUEST_VALIDATION_ERROR` | 요청 형식 검증 실패 (JSON 문법 오류, 필수값 누락, 길이 등) |
| 422 | `VALIDATION_ERROR` | 도메인 규칙 위반 (비밀번호 규칙, 게시판 ID 형식 등) |
| 500 | `INTERNAL_SERVER_ERROR` | 서버 내부 오류 |

#### 인증 구분

| 표기 | 의미 |
|---|---|
| — | 인증 불필요 |
| 회원 | 로그인 필수 |
| 관리자 | `role = ADMIN` 필수 |
| 선택 | 토큰을 생략하면 비회원(`ALL`), 전달하면 검증 후 회원 등급 적용 (잘못된 토큰은 401) |

### 엔드포인트 요약

| Method | Path | 설명 | 인증 | 성공 |
|---|---|---|---|---|
| POST | `/v1/auth/login` | 로그인 (JWT 발급) | — | 200 |
| POST | `/v1/auth/logout` | 로그아웃 (토큰 블랙리스트 등록) | 회원 | 204 |
| POST | `/v1/users` | 회원가입 | — | 201 |
| GET | `/v1/users/me` | 내 정보 조회 | 회원 | 200 |
| PATCH | `/v1/users/{user_id}/password` | 비밀번호 변경 (본인만) | 회원 | 200 |
| GET | `/v1/boards` | 게시판 목록 | — | 200 |
| POST | `/v1/boards` | 게시판 생성 | 관리자 | 201 |
| GET | `/v1/boards/{board_id}` | 게시판 설정 조회 | — | 200 |
| PUT | `/v1/boards/{board_id}` | 게시판 설정 수정 | 관리자 | 200 |
| DELETE | `/v1/boards/{board_id}` | 게시판 삭제 (소프트 삭제) | 관리자 | 200 |
| POST | `/v1/boards/{board_id}/posts` | 게시글 작성 (회원/비회원) | 선택 | 201 |
| GET | `/v1/boards/{board_id}/posts` | 게시글 목록 (페이징/검색) | 선택 | 200 |
| GET | `/v1/posts/{post_id}` | 게시글 상세 | 선택 | 200 |
| PUT | `/v1/posts/{post_id}` | 게시글 수정 | 선택 | 200 |
| DELETE | `/v1/posts/{post_id}` | 게시글 삭제 | 선택 | 200 |
| POST | `/v1/posts/{post_id}/comments` | 댓글 작성 (회원/비회원) | 선택 | 201 |
| GET | `/v1/posts/{post_id}/comments` | 댓글 목록 (등록순) | 선택 | 200 |
| PUT | `/v1/comments/{comment_id}` | 댓글 수정 | 선택 | 200 |
| DELETE | `/v1/comments/{comment_id}` | 댓글 삭제 | 선택 | 200 |

"선택" 인증 API의 실제 허용 여부는 해당 게시판의 권한 설정(`boards.*_role`)에 따릅니다.
수정·삭제는 **작성자 본인(회원) / 비회원 비밀번호 일치 / 관리자** 중 하나를 만족해야 합니다.

---

### Auth

#### `POST /v1/auth/login` — 로그인

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `email` | string | ✅ | 이메일 형식 |
| `password` | string | ✅ | 1자 이상 |

```bash
curl -X POST http://127.0.0.1:8000/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "user01@example.com", "password": "Test123456@"}'
```

응답 `data`:

```json
{ "access_token": "eyJhbGciOiJIUzUxMiIs...", "token_type": "bearer", "expires_in": 3600 }
```

#### `POST /v1/auth/logout` — 로그아웃

요청 본문 없음. 전달한 토큰의 `jti` 를 블랙리스트에 등록하며, 이후 같은 토큰은 401 입니다. 응답은 `204 No Content` (본문 없음).

---

### Users

#### `POST /v1/users` — 회원가입

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `email` | string | ✅ | 이메일 형식, 중복 불가(409) |
| `name` | string | ✅ | 2~20자 |
| `password` | string | ✅ | 8자 이상, 영문·숫자·특수문자 포함 |

```bash
curl -X POST http://127.0.0.1:8000/v1/users \
  -H 'Content-Type: application/json' \
  -d '{"email": "user01@example.com", "name": "테스트", "password": "Test123456@"}'
```

응답 `data` (`UserResponse`):

```json
{ "id": "b2893de5-7771-4f33-a1b3-539b43e88fc3", "email": "user01@example.com", "name": "테스트", "role": "USER" }
```

#### `GET /v1/users/me` — 내 정보 조회

응답 `data`: `UserResponse` (위와 동일)

#### `PATCH /v1/users/{user_id}/password` — 비밀번호 변경

`user_id` 가 로그인 사용자와 다르면 403.

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `old_password` | string | ✅ | 현재 비밀번호 |
| `new_password` | string | ✅ | 8자 이상, 영문·숫자·특수문자 포함 |

응답 `data`: `null`

---

### Boards

#### 게시판 응답 (`BoardResponse`)

```json
{
  "board_id": "freetalk",
  "board_name": "자유게시판",
  "authority": {
    "edit_role": "USER",
    "view_role": "ALL",
    "list_role": "ALL",
    "comment_list_role": "ALL",
    "comment_edit_role": "USER"
  },
  "page_size": 20,
  "created_at": "2026-11-17T05:00:00Z",
  "modified_at": null
}
```

#### `GET /v1/boards` — 게시판 목록

응답 `data`: `BoardResponse[]` (삭제된 게시판 제외)

#### `POST /v1/boards` — 게시판 생성 (관리자)

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `board_id` | string | ✅ | 2~30자, `^[a-z][a-z0-9_-]{1,29}$`, 중복 불가(409) |
| `board_name` | string | ✅ | 1~50자 |
| `authority` | object | | 5개 권한 필드, 각 `ALL`/`USER`/`ADMIN` (기본 `ALL`) |
| `page_size` | integer | | 1~100 (기본 20) |

```bash
curl -X POST http://127.0.0.1:8000/v1/boards \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"board_id": "freetalk", "board_name": "자유게시판", "authority": {"edit_role": "USER"}}'
```

#### `GET /v1/boards/{board_id}` — 게시판 설정 조회

응답 `data`: `BoardResponse`

#### `PUT /v1/boards/{board_id}` — 게시판 설정 수정 (관리자)

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `board_name` | string | ✅ | 1~50자 |
| `page_size` | integer | | 1~100 (기본 20) |
| `authority` | object | | 생략 시 기존 권한 유지 |

#### `DELETE /v1/boards/{board_id}` — 게시판 삭제 (관리자)

`deleted_at` 을 기록하는 소프트 삭제. 응답 `data`: `null`

---

### Posts

#### 작성자 정보 (`AuthorResponse`)

```json
{ "author_id": "b2893de5-...", "author_name": "테스트", "is_guest": false }
```

비회원 작성물은 `author_id: null`, `is_guest: true` 입니다.

#### `POST /v1/boards/{board_id}/posts` — 게시글 작성

게시판의 `edit_role` 이상이어야 합니다.

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `title` | string | ✅ | 1~200자 |
| `content` | string | ✅ | 1자 이상 |
| `guest_name` | string | 비회원 필수 | 비회원 닉네임 |
| `guest_password` | string | 비회원 필수 | 6자 이상 (수정·삭제 시 사용) |

로그인 회원은 `guest_*` 를 생략하며, 작성자 이름은 회원 이름이 사용됩니다.
응답 `data`: `PostDetailResponse`

#### `GET /v1/boards/{board_id}/posts` — 게시글 목록

게시판의 `list_role` 이상이어야 합니다.

| Query | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `page` | integer | 1 | 페이지 번호 |
| `page_size` | integer | 게시판 설정값 | 1~100 |
| `search_type` | enum | `ALL` | `ALL` / `TITLE` / `CONTENT` / `TITLE_CONTENT` / `AUTHOR_NAME` / `AUTHOR_EMAIL` |
| `keyword` | string | — | 1~50자 |

응답 `data` (`PostPaginationResponse`):

```json
{
  "items": [
    {
      "post_id": 1, "board_id": "freetalk", "board_name": "자유게시판", "title": "첫 글",
      "author": { "author_id": null, "author_name": "손님", "is_guest": true },
      "created_at": "2026-11-17T05:00:00Z", "modified_at": null
    }
  ],
  "total_count": 1, "page": 1, "page_size": 20, "total_pages": 1,
  "search_type": "ALL", "keyword": null
}
```

#### `GET /v1/posts/{post_id}` — 게시글 상세

게시판의 `view_role` 이상이어야 합니다. 응답 `data` (`PostDetailResponse`): 목록 항목 필드 + `content`.

#### `PUT /v1/posts/{post_id}` — 게시글 수정

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `title` | string | ✅ | 1~200자 |
| `content` | string | ✅ | 1자 이상 |
| `guest_password` | string | 비회원 글 필수 | 작성 시 비밀번호 |

응답 `data`: `PostDetailResponse`

#### `DELETE /v1/posts/{post_id}` — 게시글 삭제

| Header | 필수 | 설명 |
|---|---|---|
| `X-Guest-Password` | 비회원 글 필수 | 작성 시 비밀번호 (DELETE 본문 대신 헤더로 전달) |

소프트 삭제. 응답 `data`: `null`

---

### Comments

#### 댓글 응답 (`CommentResponse`)

```json
{
  "comment_id": 1, "post_id": 1, "content": "댓글입니다.",
  "author": { "author_id": "b2893de5-...", "author_name": "테스트", "is_guest": false },
  "created_at": "2026-11-17T05:10:00Z", "modified_at": null
}
```

#### `POST /v1/posts/{post_id}/comments` — 댓글 작성

게시판의 `comment_edit_role` 이상이어야 합니다.

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `content` | string | ✅ | 1자 이상 |
| `guest_name` | string | 비회원 필수 | 비회원 닉네임 |
| `guest_password` | string | 비회원 필수 | 6자 이상 |

응답 `data`: `CommentResponse`

#### `GET /v1/posts/{post_id}/comments` — 댓글 목록

게시판의 `comment_list_role` 이상이어야 합니다. 등록순 정렬. 응답 `data`: `CommentResponse[]`

#### `PUT /v1/comments/{comment_id}` — 댓글 수정

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `content` | string | ✅ | 1자 이상 |
| `guest_password` | string | 비회원 댓글 필수 | 작성 시 비밀번호 |

응답 `data`: `CommentResponse`

#### `DELETE /v1/comments/{comment_id}` — 댓글 삭제

| Header | 필수 | 설명 |
|---|---|---|
| `X-Guest-Password` | 비회원 댓글 필수 | 작성 시 비밀번호 |

소프트 삭제. 응답 `data`: `null`
