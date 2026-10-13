# SKT ALEPH 5과목 Day2 미션

기존 mini-watch의 로그인·게시글·감시 메모·이벤트 기록을 유지하면서 세 앱의 Docker 배포, PostgreSQL SSL 연결, Next 서버 프록시와 Sentry 설정을 적용했다. **코드 구현과 로컬 검증 완료. Render 미배포, 실제 Supabase 연결·Sentry 원격 수신 미검증.** 사용자가 검토한 뒤 직접 push하며 ZIP은 만들지 않았다.

설정과 후속 작업: [deployment-plan.md](deployment-plan.md). 검증 결과와 재현 명령: [docs/day2-verification.md](docs/day2-verification.md).

## 시작본과 Git

- 원본: `C:\work\mini-watch-day06`, `codex/day1-docker-integration`, 커밋 `96c6e6ea40cb8a91ad44b3e66acd39382ac34b37`.
- 작업 사본: `C:\Users\User\Documents\ChatGPT\수업\mini-watch-day2`, 브랜치 `day2-deploy`. 기존 Git 이력을 복제했으며 새 앱을 만들지 않았다. 원본 파일·DB·미추적 `$null`은 변경하지 않았다.
- 지원 자료: `zeroskill2400/mini-watch`의 `day07-cloud-materials`, 커밋 `af45ae9679bb0f5b4f3d6239d9d6348fc3cea50e`, `day2-materials/project-support/starter/`.
- 구현·오류 수정 커밋: `f979ca776267037ad81ae1781f7d55f6e315999d`. 문서 커밋은 그 후속 커밋이다. 최종 제출 커밋은 `git rev-parse HEAD`로 확인한다.

기존 README는 [docs/README-day1.md](docs/README-day1.md)에 보존했다. 기존 `verification/`은 Day1 과거 기록이다. 지원 자료는 비교용이며 실제 배포 앱은 루트의 `general/`와 `monitor/`다. 지원 폴더의 일반 앱에는 의도적인 나눗셈 오류가 남아 있어 실제 앱에 다시 덮어쓰면 안 된다. 지원 일반 배포 SQL의 끝 빈 줄만 공백 검사에 맞춰 정리했다.

## 앱과 요청 흐름

| 앱 | 진입점 | 역할 |
|---|---|---|
| 일반 Flask | general/app.py, Waitress app:app | 로그인·HTML 게시글 CRUD·이벤트 전송 |
| 감시 Flask | monitor/backend/app.py, Waitress app:app | 감시 로그인·메모 CRUD·이벤트 수신·조회 |
| 감시 Next | monitor/next-frontend/app/page.js, npm run start | 감시 화면·같은 사이트 API 프록시 |

```text
일반 브라우저 → 일반 Flask → 일반 PostgreSQL
                         └→ 감시 Flask /api/events → 감시 PostgreSQL
감시 브라우저 /api/... → Next Route Handler → 감시 Flask → 감시 PostgreSQL
```

일반 MONITOR_URL은 감시 Flask 주소 + `/api/events`, Next MONITOR_API_URL은 감시 Flask 기준 주소만 설정한다. DB 비밀번호·SECRET_KEY·EVENT_TOKEN은 서버에서만 읽으며 브라우저 코드나 NEXT_PUBLIC_*에 넣지 않는다.

로컬 기존 Compose에서는 Nginx Gateway가 `/api`를 감시 Flask로 직접 전달한다. 기존 Gateway·네트워크·볼륨은 유지했다. Render는 앱별 Dockerfile로 배포하고 Next Route Handler가 API를 전달한다.

## 직접 변경한 파일

| 파일 | 목적 |
|---|---|
| 두 Flask app.py | Sentry 초기화·개발 PORT. 일반 health 및 수정된 Sentry 테스트 |
| 두 Flask Dockerfile·requirements.txt | 기존 패키지 버전 유지, Waitress·Sentry 추가 및 0.0.0.0:$PORT 실행 |
| 두 Flask db.py·.env.example | DB_*·SSL·앱별 Supabase/세션/Sentry 예시 |
| 두 auth_helpers.py | Secure 쿠키 환경변수 처리 |
| 두 create_user.py | 비밀번호 숨김 입력·해시 저장·기존 계정 보존 |
| 두 observability.py | 환경·버전·서비스 구분·민감정보 제외 |
| 두 sql/deploy.sql | repository 쿼리와 일치하는 비파괴 스키마 준비 |
| general/request_logging.py | EVENT_TOKEN 전송·health 기록 제외·실패 시 기존 응답 유지 |
| monitor/backend/routes/events.py | 토큰 검증 후 기존 이벤트 저장·조회 |
| Next app/api/[...path]/route.js | 쿠키·CSRF·Set-Cookie·상태·본문 전달 및 경로 제한 |
| Next Dockerfile·.env.example·.gitignore | PORT 기본값·서버 API 주소·예시 추적 허용 |
| 루트 .env.example·.gitignore | Compose 공통 토큰 안내·비밀 파일 제외 |
| 두 Compose | 기존 구조 보존, EVENT_TOKEN·SSL·쿠키 변수만 추가 |
| tests/* | 격리 DB 통합·Sentry·영속성·제출 검사 |
| README·deployment-plan·docs/README-day1·docs/day2-verification | 원문 보존·변경·검증·배포 절차 |
| day2-materials/project-support/starter/* | 내려받은 참고 자료 |

게시글·메모 CRUD Route/Repository와 화면, 로그인 Route, 이벤트 분류 함수, Next package.json·잠금 파일, 두 Gateway·기존 React 폴더·기존 .dockerignore는 유지했다.

## 미션별 상태

| 미션 | 코드·로컬 결과 | 외부 서비스 |
|---|---|---|
| 1 배포 | 세 Docker 빌드, Waitress·개발 실행, health, Windows Next ci/build/start 성공 | Render 미배포 |
| 2 DB | SSL·SQL 구현, 격리 PostgreSQL CRUD·SQL 재실행 보존 성공 | 실제 Supabase 미검증 |
| 3 API | 로그인 성공/실패·이벤트·프록시 쿠키/CSRF·CRUD 성공 | Render HTTPS 미검증 |
| 4 Sentry | 지원 오류500→수정 JSON200, 로그인401·비활성404, 실제 SDK 메모리 수집 및 민감정보 제외 성공 | 원격 Sentry 수신 미검증 |

통합 37개 검사가 통과했고 앱 재생성 후 게시글·메모를 다시 읽었다. Windows 최초 npm 설치와 HTTP 확인은 샌드박스 DNS/네트워크 제한으로 실패했으며 정상 네트워크에서 재실행해 성공했다. npm 감사는 기존 개발 의존성 high 5개, production 의존성 0개였다. 강제 패키지 변경은 하지 않았다. 상세 범위는 검증 문서에 기록했다.

## 기존 Compose 실행

루트 .env에 직접 생성한 EVENT_TOKEN(32자 이상)을 설정한다. CHANGE_ME 예시값은 거부된다. 기존 .env가 있으면 보존하고 필요한 값을 직접 추가한다.

```powershell
cd 'C:\Users\User\Documents\ChatGPT\수업\mini-watch-day2'
if (-not (Test-Path .env)) {
    $eventValue = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    "EVENT_TOKEN=$eventValue" | Set-Content .env -Encoding utf8
}
docker network inspect m5d1-events
# 공유망이 없을 때만: docker network create m5d1-events
docker compose -f compose-monitor.yaml up -d --build --wait
docker compose -f compose-general.yaml up -d --build --wait
```

일반 localhost:8081, 감시 localhost:8082. 두 Compose는 이번에 구성 검사만 했으며 실제 기동을 다시 검증하지 않았다. 로컬 DB 계정은 각 API 컨테이너에서 대화형 `python create_user.py`로 준비한다. 기존 공개 기본 비밀번호 자동 생성 대신 직접 입력하도록 변경했다. Compose의 기존 공개 수업용 DB 비밀번호·세션 키는 Render에서 재사용하지 않는다.

DB 데이터를 지우는 down -v·volume prune·초기화 SQL은 사용하지 않는다. health 200은 DB 로그인·CRUD 성공을 보장하지 않는다.

## 사용자 검토와 push

현재 origin은 강사 원본 `https://github.com/zeroskill2400/mini-watch.git`이다. 연결 계정 jwonnlee00-lab의 원본 push 권한은 false로 확인했다. push는 하지 않았다. 본인 저장소/fork 주소를 확인한 후 사용자가 직접 실행한다.

```powershell
git status --short --branch
git log -3 --oneline
git diff 96c6e6e HEAD --stat
git remote -v
# git remote set-url origin https://github.com/<본인계정>/<저장소>.git
# git push -u origin day2-deploy
```

제출·Render 브랜치가 day2-deploy인지 확인한다. 코드 수정 → 커밋 → 사용자 push → Render 배포 커밋 대조 → 같은 기능 재검증 순서로 진행한다.
