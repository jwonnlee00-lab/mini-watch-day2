# Day2 로컬 검증 보고서

2026-10-13 한국 시간. 대상 브랜치 day2-deploy, 구현 커밋 `f979ca776267037ad81ae1781f7d55f6e315999d`. 실제 Render·Supabase·Sentry 원격에는 연결하지 않았다. 원본 C:\work와 기존 DB 볼륨·기동 중인 m5d2-sample 서비스는 변경하지 않았다. ZIP·push도 수행하지 않았다.

## 실행 결과

| 검사 | 실제 결과 | 범위 |
|---|---|---|
| 일반/감시 Docker build | 둘 다 종료 0 | Python 3.13·기존 의존성·Waitress·Sentry 설치 |
| Next Docker build | 종료 0, /·/notes 정적, /api/[...path] 동적 | 외부 API·DB 설정 없이 성공; npm ci 단계는 기존 Docker 캐시 재사용 |
| Windows npm ci/build | 재실행 종료 0 | Node v24.21.0, 339 패키지 설치, Next 16.4.0 |
| Windows npm start | ready 및 /·/api/auth/me HTTP 200 | 정상 네트워크 localhost:3903 |
| Flask Waitress | 두 health HTTP 200 | 기본과 다른 PORT 5101/5102, 0.0.0.0 로그 확인 |
| Flask python app.py | 두 health HTTP 200 | 별도 일시 컨테이너에서 개발 실행, 해당 컨테이너만 정리 |
| Next Docker start | / HTTP 200 | npm start, PORT=3100 |
| tests/integration.py | ALL 37 CHECKS PASSED | 실제 격리 PostgreSQL 두 DB 및 세 앱 네트워크 요청 |
| tests/app_checks.py | 6개 PASS | 지원 오류500 재현·수정200·비활성404·쿠키·SDK설정·기존 계정 보존 |
| tests/sentry_capture.py | 두 서비스 PASS | 실제 SDK/Flask 예외 수집, 메모리 전송·태그·민감정보 제외 |
| tests/proxy-check.mjs | 3개 PASS | 설정누락503·연결실패502·다중 Set-Cookie/상태/본문/쿼리 전달 |
| tests/persistence.py | prepare/verify 둘 다 DB별 PASS | API/Next 컨테이너 force-recreate 후 게시글·메모 재조회 |
| 최종 실습 경로 비활성화 | HTTP 404 | 실행 테스트 일반 앱도 ENABLE_SENTRY_TEST=false로 복귀 |
| 기존 Compose config --quiet | 두 파일 종료 0 | 구성만 검사, 실제 기존 Compose 기동은 재검증 안 함 |
| 제출 파일 검사·Git diff --check | 성공 | 환경파일·생성물·테스트 비밀값·브라우저 비밀 변수 제외, 비파괴 SQL |
| npm audit | 개발 high 5개, production 0개 | 기존 개발 의존성 유지, 강제 수정 없음 |

통합 37개 검사는 두 Flask/Next health, 일반·감시 로그인 실패401/성공200, 프록시 Set-Cookie·Cookie·CSRF, 게시글·메모 생성/조회/수정/삭제, CSRF403·잘못된입력400, 이벤트 토큰 누락/오류401·잘못된본문400, 브라우저 이벤트 수신 차단404, 이벤트 성공/실패 DB 기록·조회, Sentry 로그인401·수정JSON200, 두 SQL 재실행 데이터 보존·시퀀스 발급, 로그아웃·삭제후404를 포함한다.

SQL과 HTTP 테스트가 사용하는 삭제는 tests/compose.yaml의 테스트 DB에서 이번 테스트가 만든 게시글·메모 ID에만 적용됐다. 기존 DB 데이터는 삭제·초기화하지 않았다. 영속성 확인용 테스트 행은 테스트 볼륨에 남겨 두었다.

## 초기 실패와 재확인

- Windows 최초 npm ci는 샌드박스 DNS의 registry.npmjs.org ENOTFOUND와 정리 EPERM을 보고했다. 설치 전 build도 next 명령 미설치로 실패했다. 정상 네트워크에서 npm ci·build를 다시 실행해 성공했다.
- 샌드박스에서 시작한 Windows Next를 호스트에서 요청했을 때 HTTP timeout이 났다. 정상 네트워크에서 start를 다시 실행하고 두 URL의 200을 확인했다.
- 첫 Sentry 메모리 테스트에서 소스에 직접 적은 검사 문자열이 이벤트에 없다는 assertion이 실패했다. 검사 비밀값을 로컬 환경에서 생성한 값으로 읽도록 테스트를 수정했고, 두 SDK에서 실제 비밀번호/헤더 값이 이벤트에 없는 것을 재검증해 통과했다. 원격 수신 성공으로 해석하지 않는다.
- Git 공백 검사는 지원/적용 일반 deploy.sql의 끝 빈 줄을 보고했다. 해당 공백만 정리한 후 통과했다.

## 재현 명령

작업 루트에서 실행한다. Docker Desktop Linux 컨테이너 모드가 필요하다. 테스트 Compose는 `mini-watch-day2-check`라는 독립 프로젝트, 별도 general-test-data/monitor-test-data 볼륨, localhost:5801/5802/3802를 사용한다. 기존 일반·감시 Compose와 데이터를 공유하지 않는다.

```powershell
New-Item -ItemType Directory .local-test -Force | Out-Null
# 기존 테스트 .env가 있으면 덮어쓰지 않는다.
if (-not (Test-Path .local-test/.env)) {
    $lines = foreach ($name in @('EVENT_TOKEN','GENERAL_SECRET','MONITOR_SECRET','TEST_DB_PASSWORD','TEST_ACCOUNT_PASSWORD')) {
        $value = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
        "$name=$value"
    }
    $lines | Set-Content .local-test/.env -Encoding utf8
}
docker build -t mini-watch-day2-general:local general
docker build -t mini-watch-day2-monitor:local monitor/backend
docker build -t mini-watch-day2-next:local monitor/next-frontend
$env:TEST_ENABLE_SENTRY_TEST='true'
docker compose --env-file .local-test/.env -f tests/compose.yaml up -d --wait
docker compose --env-file .local-test/.env -f tests/compose.yaml run --rm --no-deps checks
docker compose --env-file .local-test/.env -f tests/compose.yaml run --rm --no-deps --entrypoint python checks app_checks.py
docker compose --env-file .local-test/.env -f tests/compose.yaml run --rm --no-deps --entrypoint python checks sentry_capture.py
node tests/proxy-check.mjs
docker compose --env-file .local-test/.env -f tests/compose.yaml run --rm --no-deps --entrypoint python checks persistence.py prepare
docker compose --env-file .local-test/.env -f tests/compose.yaml up -d --wait --force-recreate general-api monitor-api monitor-web
docker compose --env-file .local-test/.env -f tests/compose.yaml run --rm --no-deps --entrypoint python checks persistence.py verify
$env:TEST_ENABLE_SENTRY_TEST='false'
docker compose --env-file .local-test/.env -f tests/compose.yaml up -d --wait --force-recreate general-api
python tests/submission_check.py
git diff --check
```

Windows Python 실행 별칭을 사용할 수 없어 제출 검사는 bundled Python 3.12.14, Flask 실행은 Docker Python 3.13을 사용했다. 재현할 때는 동작하는 Python 경로를 지정한다.

Windows Next 확인:

```powershell
cd monitor/next-frontend
npm.cmd ci
npm.cmd run build
$env:MONITOR_API_URL='http://127.0.0.1:5802'
$env:PORT='3903'
npm.cmd run start -- --hostname 127.0.0.1
# 다른 터미널에서 / 및 /api/auth/me를 확인하고 종료할 때 Ctrl+C
```

테스트 서비스는 사용자 확인용으로 유지한다. 중지할 때는 `docker compose --env-file .local-test/.env -f tests/compose.yaml stop`을 사용한다. 볼륨을 삭제할 필요는 없다.

## 未検証

실제 Render URL·HTTPS 세션, Supabase SSL 연결·저장, Render 재배포, Sentry 원격 수신, 브라우저 화면 수동 조작은 미검증이다. API/DB 검증이나 메모리 SDK 검증과 구분한다. 제출 검사는 생성한 테스트 비밀값과 설정을 검사한 범위이며 모든 형식의 비밀정보 부재를 보장하는 검사는 아니다.
