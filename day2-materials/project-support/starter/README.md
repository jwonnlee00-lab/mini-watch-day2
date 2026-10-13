# Day2 미니프로젝트 배포 지원 코드

이 자료는 Day1에서 완성한 일반 게시판·감시 화면·관찰 메모를 유지하며 외부 배포 설정을 적용한 비교본이다. `starter`는 오류 수집 실습용 오류가 남아 있고, `solution`은 같은 요청이 정상 응답하도록 수정되어 있다. 실제 연결값은 두 자료 모두 비워 두었다.

## 시작 상태

본인의 Day1 완성 폴더에서 작업 브랜치를 만든다. 기존 변경 내용을 먼저 `git status`로 확인한다. Git 복구가 필요한 경우에만 새 폴더에 다음을 실행한다.

```cmd
cd /d C:\work
git clone --branch day06-start https://github.com/zeroskill2400/mini-watch.git mini-watch-day2
cd mini-watch-day2
xcopy /E /I /Y day1-materials\project-docker .
git switch -c day2-deploy
```

복구용 기준 커밋은 `7ac02c0b968caf0a35d09e235389d77e7c8eafc7`이다. 원격 브랜치가 바뀌면 제공 자료의 기준 커밋과 비교한다. `main`이나 `project-starter`는 이 시작 상태가 아니다. 지원 파일은 기존 앱 폴더에 대응시켜 적용한다. 실제 비밀값이 있는 .env는 자료에 포함되어 있지 않다. 이 자료의 Git 경로는 `day07-cloud-materials` 브랜치의 `day2-materials/project-support`이다.

## 직접 설정할 부분

`general/.env.example`, `monitor/backend/.env.example`, `monitor/next-frontend/.env.example`가 학생 설정 영역이다. 로컬에서 사용할 폴더에서 `copy .env.example .env`로 복사한 뒤 값을 채운다. Render에서는 파일을 올리지 않고 같은 이름의 Environment 항목을 입력한다. 로컬 HTTP에서 SESSION_COOKIE_SECURE는 false, Render HTTPS에서는 true다.

기존 general/monitor의 DB_* 필드가 2~3교시 샘플의 PG*와 다른 경우, 의미가 같은 항목을 대응시킨다. DB_NAME은 Supabase 기본값 postgres이며 로컬 Compose의 general_db/monitor_db를 넣지 않는다. DB_USER는 Session pooler에 표시된 프로젝트 참조가 붙은 사용자 값이다. Supabase 로그인 비밀번호와 프로젝트 DB 비밀번호는 서로 다른 값이다.

SECRET_KEY는 앱별로 별도 생성한다. EVENT_TOKEN은 일반·감시 두 API에 같은 새 값을 넣는다. 가상환경이 활성화된 터미널에서 다음 명령으로 필요할 때마다 하나씩 생성하고, 자기 .env/Render Environment에만 넣는다. 출력이나 실제 .env를 Git에 올리지 않는다.

```cmd
python -c "import secrets; print(secrets.token_hex(32))"
```

## DB 준비와 계정 생성

2교시 Supabase 프로젝트를 일반 DB로 재사용하고 감시 프로젝트 하나를 추가한다. 기존 다른 무료 프로젝트가 있으면 활성 2개 한도를 먼저 확인한다. 무료 한도를 늘리기 위해 결제하지 않는다. 두 프로젝트 모두 Data API를 사용하지 않으므로 왼쪽 Project Settings → Data API → Overview에서 Enable Data API를 끄고 Save를 누른다. [Data API 화면으로 이동](https://supabase.com/dashboard/project/_/integrations/data_api/overview)할 수도 있으며, 위쪽에서 대상 프로젝트를 확인한다. 기존 샘플 messages는 지우지 않는다.

새 감시 DB 비밀번호는 2교시와 같이 영문 대소문자·숫자·- _ . ! @ # %를 조합해 16자 이상으로 만들고, 따옴표와 역슬래시는 넣지 않는다.

일반 DB의 SQL Editor에는 `general/sql/deploy.sql`, 감시 DB에는 `monitor/backend/sql/deploy.sql`을 실행한다. 프로젝트 이름을 먼저 확인한다. CREATE DATABASE 명령은 사용하지 않는다. 같은 SQL을 다시 실행해도 기존 테이블·데이터를 지우지 않는다.

각 Flask 폴더에서 앞 교안처럼 가상환경 생성·활성화·의존성 설치를 한다. 이미 해당 가상환경이 있으면 생성은 생략한다. 한 폴더 작업을 마치면 deactivate 후 다른 폴더에서 진행한다.

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python create_user.py
```

일반은 student, 감시는 operator를 기본 아이디로 사용한다. 직접 정한 새 비밀번호를 두 번 입력한다. 입력 글자는 표시되지 않는다. 기존 계정이 있으면 비밀번호를 덮어쓰지 않는다. 공개 예시 Learn123!를 외부 배포용 계정에 사용하지 않는다. 이 명령은 로컬에서 실행하지만 .env에 지정한 Supabase DB에 계정을 만든다. Render Free에는 Shell/SSH가 없어 그곳에서 실행하는 절차가 아니다.

## 앱별 Render 설정

GitHub의 본인 저장소에 push한 뒤 Git Provider로 연결한다. 각 앱은 Docker Web Service, 작업 공간 Hobby, Compute Free로 설정한다. Root Directory를 먼저 정하고 Dockerfile Path는 ./Dockerfile, Docker Command는 빈칸을 사용한다.

| 앱 | Root Directory | 환경 변수 |
|---|---|---|
| 감시 API | monitor/backend | DB_* 6개, SECRET_KEY, SESSION_COOKIE_SECURE=true, EVENT_TOKEN, SENTRY_DSN, SENTRY_ENVIRONMENT=mini-monitor, APP_VERSION, ENABLE_SENTRY_TEST=false |
| 일반 앱 | general | 위 항목과 MONITOR_URL=https://자신의-감시-api.onrender.com/api/events, SENTRY_ENVIRONMENT=mini-general |
| 감시 화면 | monitor/next-frontend | MONITOR_API_URL=https://자신의-감시-api.onrender.com |

PORT는 Render가 정한 값을 시작 명령에서 읽는다. Flask와 Next에 로컬 PC 주소나 Docker 서비스 이름을 클라우드 연결 주소로 입력하지 않는다. Render는 이 두 Compose 파일을 실행하지 않는다. Compose 두 파일은 로컬 Docker 실습용으로 남아 있다.

먼저 감시 API를 배포하고 외부 /health 응답을 확인한 뒤 일반과 감시 화면의 연결 주소를 넣는다. 감시 화면에서 현재 로그인 확인을 누르고 operator로 로그인한다. 일반 앱에서 틀린 비밀번호를 한 번 입력하고 올바른 비밀번호로 로그인한 다음, 감시 화면의 기록 불러오기를 누른다. login_failure의 401과 login_success의 200을 확인한다.

무료 앱은 사용하지 않으면 잠들고 첫 요청 준비가 오래 걸릴 수 있다. 감시 /health와 로그인 상태 확인이 응답한 뒤 일반 앱 요청을 다시 보낸다. 전송 실패 시 일반 앱은 계속 응답하고 Render 로그에 경고를 남긴다. 기존 best-effort 기록 전송은 모든 기록의 저장을 보장하지 않는다. 시간 한도를 넘은 첫 요청의 기록이 나중에 중복 도착할 가능성도 있다.

## Sentry 오류 확인과 수정

Sentry DSN과 환경값을 적용한 일반 또는 감시 API에서 ENABLE_SENTRY_TEST를 잠시 true로 바꾼다. 해당 앱에 로그인한 뒤 `/api/sentry-test`로 접속한다. 감시는 감시 Next의 같은 경로에서도 확인할 수 있다. starter의 `app.py` 마지막 실습 함수는 ZeroDivisionError를 발생시키며 Sentry에서 파일·줄을 확인한다. solution은 같은 함수가 JSON을 반환하는 비교본이다. 수정 commit→push→재배포 후 동일 주소가 200인지 확인하고 ENABLE_SENTRY_TEST=false로 마무리한다. 기존 Sentry 이슈는 자동으로 없어지지 않는다.

지원된 오류 수집은 요청 본문·비밀번호·쿠키·사용자 정보를 제외한다. 기존 DB 오류는 처리되어 503으로 반환하므로 이것이 자동으로 Sentry 예외가 된다고 가정하지 않는다.

## 기존 기능 확인

- 일반 게시글의 목록·상세·등록·수정·삭제가 동작한다.
- 일반 로그인 실패·성공이 감시 기록에 들어온다.
- 감시 로그인 후 메모를 등록·수정·삭제할 수 있고 새로고침 후 다시 로그인 상태를 확인할 수 있다.
- 재배포 후 일반 게시글과 감시 메모가 각 Supabase DB에 남는다.
- 토큰 없이 감시 API의 POST /api/events를 호출하면 저장되지 않는다.
- 오류 수정 후 같은 요청은 200이며 실습 오류 경로는 다시 비활성화했다.

## Git에 남길 파일과 남기지 않을 값

Dockerfile, requirements, 지원 코드, SQL, 빈 예시 .env.example, 본인 배포 설정 설명과 오류 수정 commit을 남긴다. 실제 .env, DB 비밀번호, SECRET_KEY, EVENT_TOKEN은 남기지 않는다. .gitignore는 이미 추적된 비밀 파일을 지우지 않는다. 실수로 commit한 비밀값이 있으면 새 값으로 바꾸고 기존 값을 폐기해야 한다.

지원 코드의 프록시·쿠키/CSRF 전달·이벤트 토큰 확인·원격 DB SSL·오류 수집 내부를 이번 교시에 새로 구현하는 문제로 내지 않는다. 학생은 설정을 적용하고 기존 기능이 이어지는지 검증한다. 앱 기능을 지우고 새 hello 앱으로 대체하지 않는다.
