# Day2 배포 계획

2026-10-13 한국 시간 기준. 세 앱 모두 **미배포**이며 실제 서비스 URL은 없다. 로컬 검증과 코드 준비만 완료했다. 과제의 Render Hobby/Free·Supabase Free·Sentry Developer 범위로 진행하며 유료 전환은 하지 않는다. 사용자가 확인한 후 직접 push하고 ZIP은 만들지 않는다.

## 저장소·커밋

현재 origin은 강사 원본 `https://github.com/zeroskill2400/mini-watch.git`. 본인 저장소/fork로 변경할 필요가 있다. 연결 계정의 원본 push 권한은 false이며 push하지 않았다. 배포 브랜치 `day2-deploy`.

시작 커밋 `96c6e6ea40cb8a91ad44b3e66acd39382ac34b37`, 지원 커밋 `af45ae9679bb0f5b4f3d6239d9d6348fc3cea50e`, 구현·오류 수정 커밋 `f979ca776267037ad81ae1781f7d55f6e315999d`. 문서 커밋은 구현 커밋의 후속이며 최종 식별자는 git rev-parse HEAD로 확인한다.

## Render 서비스

| 앱 | Root Directory | Dockerfile Path | Build Context | Health Check | 상태 |
|---|---|---|---|---|---|
| 감시 API | monitor/backend | ./Dockerfile | . | /health | 미배포 |
| 일반 앱 | general | ./Dockerfile | . | /health | 미배포 |
| 감시 화면 | monitor/next-frontend | ./Dockerfile | . | / | 미배포 |

각 서비스에서 본인 저장소·day2-deploy·Docker 런타임을 선택한다. Docker Command 빈칸, Auto-Deploy On Commit. 두 Compose와 Gateway는 로컬 용도이며 Render는 앱별 Dockerfile을 사용한다.

Flask는 Waitress로 `app:app`을 0.0.0.0:$PORT에서 실행한다. 기본 5000이며 Render PORT가 우선한다. python app.py 개발 실행도 같은 PORT를 읽는다. Next는 잠금 파일로 npm ci → build → start를 수행하며 0.0.0.0:$PORT, 기본 3000이다. API는 요청 때 읽고 클라이언트 화면에서 불러오므로 외부 API·DB 설정 없이 Docker 및 Windows build가 성공했다.

## Supabase DB와 SQL

| 앱 | 프로젝트 | SQL | 테이블 |
|---|---|---|---|
| 일반 Flask | 일반용 프로젝트; 본인 Day2 샘플 프로젝트 재사용 가능 | general/sql/deploy.sql | users, posts |
| 감시 Flask | 일반과 별도 감시용 프로젝트 | monitor/backend/sql/deploy.sql | users, http_events, notes |

프로젝트별 Connect의 Session pooler Host·User를 대응시킨다. DB_PORT=5432, DB_NAME=postgres, DB_SSLMODE=require. 두 이름이 postgres여도 다른 프로젝트다. 실제 연결값은 사용자 프로젝트에서 확인한다. 현재 실제 Supabase 생성·연결은 하지 않았다.

수업용 프로젝트 Data API는 과제대로 끄고 Flask가 PostgreSQL로 직접 접속한다. 별도 RLS 정책은 추가하지 않았다. 각 SQL Editor에서 대응하는 deploy.sql을 적용한다. 연습 초기화 SQL·docker-init.sql은 외부 DB 준비에 사용하지 않는다.

SQL에는 DROP·TRUNCATE·DELETE가 없다. CREATE TABLE IF NOT EXISTS로 테이블을 보존하고 일반 posts ID 시퀀스는 기존 MAX(id)·시퀀스 값보다 뒤로 가지 않게 설정한다. 격리 PostgreSQL에서 빈 DB 적용·자료가 있는 상태의 재실행·ID 발급을 검증했다. 기존 스키마가 다른 경우 IF NOT EXISTS가 열을 자동 변환하지 않으므로 먼저 비교한다. 데이터 삭제로 맞추지 않는다.

## 환경변수와 비밀값

| 변수 | 앱 | 역할 |
|---|---|---|
| DB_HOST·DB_PORT·DB_NAME·DB_USER·DB_PASSWORD | 두 Flask | 앱별 PostgreSQL 연결 |
| DB_SSLMODE | 두 Flask | Supabase require, 로컬 prefer, 격리 테스트 disable |
| SECRET_KEY | 두 Flask | 서로 다른 32자 이상 랜덤 세션 키 |
| SESSION_COOKIE_SECURE | 두 Flask | 로컬 HTTP false, Render HTTPS true |
| EVENT_TOKEN | 두 Flask | 동일한 32자 이상 랜덤 이벤트 인증 토큰 |
| MONITOR_URL | 일반 | https://<감시-API>.onrender.com/api/events |
| MONITOR_API_URL | Next 서버 | https://<감시-API>.onrender.com; /api 없음 |
| SENTRY_DSN | 두 Flask | 본인 Sentry 프로젝트 DSN; 예시에서는 빈 값 |
| SENTRY_ENVIRONMENT | 두 Flask | mini-general / mini-monitor |
| APP_VERSION | 두 Flask | release; 배포 코드 커밋으로 설정 권장 |
| ENABLE_SENTRY_TEST | 일반 | 기본 false, 실습 확인 중에만 true |
| PORT | 세 앱 | 실행 포트; Render 제공값 사용 |

앱별 .env.example은 자리표시자다. 감시 예시의 ENABLE_SENTRY_TEST=false는 지원 형식을 보존했지만 실제 감시 앱에는 실습 경로를 추가하지 않았다. 일반 앱만 해당 경로가 있다. SECRET_KEY·EVENT_TOKEN의 CHANGE_ME는 시작 시 거부한다. 일반 MONITOR_URL과 두 EVENT_TOKEN은 필수다.

Render 환경 설정에 실제 값을 입력한다. DB 비밀번호·세션 키·이벤트 토큰은 서버에서만 읽으며 브라우저 코드·NEXT_PUBLIC_*에 넣지 않는다. 실제 .env는 Git·Docker에서 제외한다. 세션 HTTPOnly·SameSite=Lax는 유지하며 HTTPS 배포에서 Secure=true로 설정한다.

## 계정 준비: 각 앱의 로컬 가상환경

python 실행이 가능해야 한다. 없으면 Python을 설치하거나 사용할 로컬 Python 경로를 지정한다. 일반과 감시는 각각 별도로 실행하며 해당 앱 DB 연결값을 로컬 .env에 넣는다.

```powershell
cd general
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# .env.example을 참고해 본인 일반 DB 값을 로컬 .env에 설정
.\.venv\Scripts\python.exe create_user.py
```

감시는 monitor/backend에서 같은 절차를 수행한다. 아이디·12자 이상 비밀번호를 입력하고 비밀번호는 숨겨진다. Werkzeug 해시를 users에 저장하며 동일 username이면 기존 비밀번호를 보존한다. 문서·로그에 비밀번호를 적지 않는다. 개발 실행은 필요한 SECRET_KEY·EVENT_TOKEN·MONITOR_URL도 채운 뒤 가상환경 Python으로 app.py를 실행한다. PC에서 동시에 실행할 때 PORT를 구분한다.

## 실제 배포·검증 순서

1. 본인 저장소에 day2-deploy를 push하고 두 Supabase 프로젝트에 대응 SQL·계정을 준비한다.
2. 감시 API에 감시 DB·EVENT_TOKEN·별도 SECRET_KEY·Secure=true·Sentry를 설정해 배포하고 /health를 확인한다.
3. 일반에 일반 DB·다른 SECRET_KEY·같은 EVENT_TOKEN·감시 HTTPS 주소 + /api/events를 설정해 배포한다.
4. Next에 감시 HTTPS 기준 주소만 MONITOR_API_URL로 설정해 배포한다.
5. 감시 현재 로그인 확인 → 로그인 → 메모 CRUD. 일반 실패·성공 로그인 → 감시 login_failure/401·login_success/200 조회를 비교한다.
6. 게시글·메모 새로고침과 각 DB의 행을 확인한다. 사용자의 기존 자료는 테스트 목적으로 임의 삭제하지 않는다.
7. 일반 ENABLE_SENTRY_TEST를 잠시 true로 설정하고 로그인 세션에서 /api/sentry-test의 정상 JSON을 확인한다. false로 돌린 뒤 404를 확인한다.
8. 코드 수정 → 커밋 → 사용자 push → Render 배포 커밋 대조 → 동일 기능 재확인. 재배포 후 기존 게시글·메모도 다시 읽는다.

health는 DB를 조회하지 않아 DB 실패 중에도 200일 수 있다. 실제 Supabase SSL·Render HTTPS 로그인·재배포·Sentry 원격 수신은 아직 미검증이다.

## Sentry 오류와 수정

원본 Day1에는 /api/sentry-test가 없었다. 지원 커밋 af45ae9679bb0f5b4f3d6239d9d6348fc3cea50e의 general/app.py, sentry_test()에 있던 `result = 1 / 0`을 적용 과정에서 정상 JSON으로 바꿨다. 오류 수정 커밋 f979ca776267037ad81ae1781f7d55f6e315999d. 지원 원본을 격리 test client에서 실행해 ZeroDivisionError·500을 재현했고 실제 앱에서는 status=ok·service=general·message=Sentry test fixed의 200을 확인했다. 로그인 검사와 ENABLE_SENTRY_TEST 조건을 유지했다.

두 observability.configure_errors는 개발·Waitress 모듈 로딩에서 실행된다. send_default_pii=false, include_local_variables=false, max_request_body_size=never, enable_logs=false 및 before_send로 요청 본문·쿠키·헤더·검색 조건·사용자 필드를 제외한다. 실제 SDK/Flask 예외 수집은 메모리 전송으로 테스트했으며 환경·release·service 태그와 생성한 테스트 비밀값 제외를 확인했다. 원격 DSN은 사용하지 않았다.

Sentry Resolve는 코드 수정·재배포를 대신하지 않는다. 최종 예시는 false이며 실행 중인 테스트 서비스도 실습 후 false로 복귀했다. 지원 app.py와 실제 general/app.py, Git 구현 diff로 수정 전후를 비교할 수 있다.

## 오류 진단과 재시도

- 감시 주소: Next 설정 누락은 503, 연결 실패는 502 JSON. MONITOR_API_URL·감시 health·서비스 로그부터 확인한다. 일반 이벤트 전송 실패는 일반 로그에 경고를 남기고 기존 응답은 유지한다. 재전송 큐는 없으므로 복구 후 새 로그인 요청을 만든다.
- DB: 기존 psycopg 오류 처리의 503을 확인한다. 해당 앱 DB_*·프로젝트·테이블을 점검한다. health 성공과 별개다.
- 입력: 기존 검증 400, 인증·이벤트 토큰 401, CSRF 403을 구분한다. 감시 화면은 error 메시지를 표시하며 현재 로그인 확인·기록/목록 불러오기 버튼으로 재시도할 수 있다.

## 남은 사용자 작업

본인 저장소 결정·push, 두 Supabase 설정·SQL·계정 준비, Render 세 서비스 배포와 HTTPS 재검증, 본인 Sentry DSN·원격 수신 확인. 기존 개발 의존성 high 5개는 별도 유지보수 항목이며 production 감사는 0개였다. 자동 채점 대상 코드와 실제 서비스 검증을 혼동하지 않는다.
