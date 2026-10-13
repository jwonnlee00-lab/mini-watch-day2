# SKT ALEPH Day 1 Docker 통합 미니프로젝트

시작 소스: zeroskill2400/mini-watch의 day06-start 브랜치. 작업 폴더는 C:\work\mini-watch-day06이다.
C:\work\m5d1-sample의 기존 문장 조회 샘플과 컨테이너·데이터는 수정하지 않았다.
기존 로그인·CSRF·게시글·감시 이벤트·메모 CRUD를 사용하고 day1-materials/project-starter를 적용했다.
시작본 README는 docs/README-start.md에 보존했다. 이미 적용된 제출물에 시작 자료를 다시 복사하지 않는다.

Docker 구현 및 실제 실행 증거 커밋: `4cc50d1d6c1d1b70d7c9e27b9264efaa36f6cf26`
브랜치: `codex/day1-docker-integration`. GitHub push는 사용자 확인 전 수행하지 않았다.
전체 제출본의 최종 커밋은 `git rev-parse HEAD`로 확인한다. ZIP에도 위 구현 커밋과 검증 결과가 포함된다.

## 최초 실행 (Windows PowerShell)

Docker Desktop이 Linux 컨테이너 모드로 실행되어 있어야 한다. 8081·8082 포트가 비어 있어야 한다.
공유망이 이미 있으면 재사용한다. Compose는 각 파일을 별도로 실행한다.

```powershell
cd C:\work\mini-watch-day06
docker network inspect m5d1-events *> $null
if ($LASTEXITCODE -ne 0) { docker network create m5d1-events }
docker compose -f compose-general.yaml config --quiet
docker compose -f compose-monitor.yaml config --quiet
docker compose -f compose-monitor.yaml up -d --build --wait
(Invoke-WebRequest http://localhost:8082/api/auth/me).StatusCode
# 위 응답이 200인 것을 확인한 뒤 일반을 실행한다.
docker compose -f compose-general.yaml up -d --build --wait
docker compose -f compose-monitor.yaml exec -T monitor-api python create_user.py
docker compose -f compose-general.yaml exec -T general-api python create_user.py
```

계정 생성은 기존 username과 비밀번호를 덮어쓰지 않는다. 기존 계정은 기존 비밀번호를 사용한다.
새 DB의 수업 계정은 일반 `student / Learn123!`, 감시 `operator / Learn123!`이다.
일반 화면·API는 http://localhost:8081, 감시 화면·API는 http://localhost:8082이다.
Compose의 DB 비밀번호와 세션 키는 공개 로컬 수업용 예시이며 실제 운영 비밀값이 아니다.
.env 없이 실행되므로 별도 .env 복사가 필요 없다. 실서비스 배포용 구성이 아니다.

## 화면 검증 절차

1. 감시 API 준비(위 200 응답)를 확인한다. 일반 화면에서 로그인 링크를 열고 student에 틀린 비밀번호를 입력한다.
2. 오류 문구를 확인한 뒤 Learn123!로 로그인한다. 게시글 목록에 student 로그인 문구와 Docker 실행 확인 게시글이 보인다.
3. 감시 화면에서 operator로 로그인하고 기록 불러오기를 누른다. `/auth/login`의 login_failure·401, login_success·200을 확인한다.
4. 목록 불러오기를 누른 뒤 제목 `Docker 점검`, 내용 `로그인 실패와 성공을 확인했다`로 메모를 등록한다.
5. 새로고침 후 현재 로그인 확인 → 기록 불러오기 → 목록 불러오기를 누른다. 같은 메모와 기록을 확인한다.
6. 아래 종료·재실행을 수행한 뒤 두 서비스에서 다시 로그인하고 기존 기록과 메모를 확인한다.

현재 로그인 확인은 기존 화면의 명시적 세션 조회 버튼이다. 새로고침 직후에는 이를 눌러 화면 상태를 복원한다.
기존 기록 전송은 실패한 이벤트를 재전송하지 않는다. 감시 API가 준비된 후 새로운 실패·성공 로그인을 수행한다.

## 종료와 데이터 보존 재실행

```powershell
docker compose -f compose-general.yaml down
docker compose -f compose-monitor.yaml down
docker compose -f compose-monitor.yaml up -d --wait
(Invoke-WebRequest http://localhost:8082/api/auth/me).StatusCode
# 200 확인 후 실행
docker compose -f compose-general.yaml up -d --wait
```

두 프로젝트를 각각 독립적으로 종료할 수 있다. `down`은 컨테이너와 프로젝트 망을 제거하지만 named volume과 외부망은 보존한다.
`down -v` 또는 volume prune을 사용하지 않는다. 초기 SQL은 빈 DB 볼륨의 최초 초기화에만 적용된다.
기존 볼륨이 있다면 초기 SQL은 자동 재실행되지 않으므로 기존 스키마를 별도로 확인한다.
새 소스나 Dockerfile 변경은 `up -d --build`로 반영한다. 로컬 개발 서버를 켤 필요가 없다.

## 서비스·네트워크·공개 포트

| 서비스 | 참여 망 | PC 공개 포트 |
|---|---|---|
| general-gateway | general-front-net | 127.0.0.1:8081 → 80 |
| general-api | general-front-net, general-data-net, m5d1-events | 없음 (내부 5000) |
| general-db | general-data-net (internal) | 없음 (내부 5432) |
| monitor-gateway | monitor-front-net | 127.0.0.1:8082 → 80 |
| monitor-web | monitor-front-net | 없음 (내부 3000) |
| monitor-api | monitor-front-net, monitor-data-net, m5d1-events | 없음 (내부 5000) |
| monitor-db | monitor-data-net (internal) | 없음 (내부 5432) |

Compose 프로젝트 이름은 m5d1-general/m5d1-monitor이다. 프로젝트 내부망 실제 이름에는 프로젝트 접두사가 붙는다.
같은 YAML 별칭 events만 선언하면 프로젝트별 다른 망이 생성된다. 두 Compose에서 `external: true`,
`name: m5d1-events`를 지정하고 API 서비스의 networks에 참여시켜야 같은 실제 외부망을 공유한다.
DB_HOST는 general-db/monitor-db, DB_PORT는 5432이다. 일반 MONITOR_URL은 http://monitor-api:5000/api/events이다.
공유망은 사전 생성하며 다른 Compose 서비스에 depends_on을 걸지 않는다. 각 API는 자기 DB service_healthy를 기다린다.
monitor-web/gateway의 실행 중 상태는 DB healthy와 다르며 HTTP 응답으로 별도 검증했다.

## 실제 확인 명령과 결과 (2026-10-12, 한국 시간)

```powershell
docker compose -f compose-general.yaml config --quiet
docker compose -f compose-monitor.yaml config --quiet
docker compose -f compose-general.yaml ps
docker compose -f compose-monitor.yaml ps
docker network inspect m5d1-events
docker compose -f compose-general.yaml exec -T general-api getent hosts monitor-api
docker compose -f compose-general.yaml logs --no-color
docker compose -f compose-monitor.yaml logs --no-color
```

두 config 종료코드 0. 7개 서비스 Up, DB 두 개 healthy. 공유망에는 두 API만 참여했다.
DNS 조회 출력: `172.21.0.2 monitor-api` (IP는 재실행 환경에 따라 달라진다).
DNS 조회는 이름 해석만 증명한다. 실제 이벤트 수신 201, 로그인 401/200, 감시 조회 200을 API/gateway 로그와 화면으로 별도 확인했다.
두 화면과 `/api/auth/me` 모두 HTTP 200이었다. 컨테이너 내부 SQL로 general_db/sample 및 monitor_db/sample 연결을 확인했다.
Next.js 빌드 로그에는 optimized production build 성공과 세 경로가 기록되며 실행 로그는 `next start`이다.
Flask 두 앱의 로그에서 0.0.0.0:5000을 확인했다.

재생성 전후: 이벤트 ID 7 login_failure/401, ID 8 login_success/200 및 메모 ID 1의 제목·내용 동일.
API 컨테이너 ID는 변경됐고 DB named volume은 동일하게 유지됐다. 새 계정도 유지되어 재로그인이 성공했다.
초기 생성·계정 준비 결과는 operator/student 계정을 만들었습니다였으며, 기존 계정 덮어쓰기는 수행하지 않았다.

증거 파일은 [검증 보고서](verification/REPORT.md)에서 연결한다.
`verification/monitor-build.txt`, `general-build.txt`는 실제 빌드·기동 출력이다.
`infrastructure.txt`, `final-checks.txt`는 설정·상태·망·DNS·DB 연결·HTTP 검사 결과다.
`logs-before.txt`, `logs-after.txt`는 각 7개 서비스의 실제 로그다.
`recreate.txt`는 DB 조회 전후·컨테이너 ID·down/up·볼륨 보존 결과다.
`monitor-before.png`, `monitor-after.png`, `general-success.png`는 직접 확인한 화면이다.
ui.txt 파일은 해당 화면의 접근성 텍스트 기록이다. 세션 쿠키나 CSRF 값은 증거에 저장하지 않았다.

## 변경 목록과 이유

| 파일 | 변경 이유 |
|---|---|
| compose-general.yaml, compose-monitor.yaml | DB 시작틀을 3/4개 서비스로 완성, 내부망·외부망·DB 준비 대기·gateway 포트 구성 |
| general/app.py, monitor/backend/app.py | 제공된 설정으로 컨테이너 외부 요청을 받는 0.0.0.0:5000 실행 |
| general/request_logging.py | 기존 전송 로직을 유지하고 MONITOR_URL 환경변수 지원 |
| general/Dockerfile, monitor/backend/Dockerfile | 제공된 Python 이미지·requirements 기반 실행 재사용 |
| monitor/next-frontend/Dockerfile | npm ci, npm run build, production next start 재사용 |
| 세 빌드 폴더의 .dockerignore | 로컬 가상환경·캐시·node_modules·.next·.env 제외 |
| general/sql/docker-init.sql, monitor/backend/sql/docker-init.sql | 제공 SQL의 테이블과 실제 repository 쿼리 호환 확인, 빈 볼륨 초기화 |
| gateways/general.conf, gateways/monitor.conf | 일반 Flask 및 감시 API/Next.js로 내부 이름 프록시, 이벤트 POST는 내부 API로 수신 |
| monitor/next-frontend/next.config.mjs | 컨테이너의 localhost:5200 개발 rewrite 제거, gateway가 /api 처리 |
| .gitignore | .next·로그·제출 ZIP 생성물 제외 |
| README.md, docs/README-start.md, verification/* | 원본 문서 보존, 재현 절차와 실제 검증 증거·20개 판정 기록 |

게시글·로그인·메모·이벤트의 route/repository 및 UI는 변경하지 않았다. 패키지 목록·Next.js 잠금 파일은 기존 소스를 사용한다.
기존 npm ci는 high 취약점 5개를 보고했다. 강제 버전 업데이트는 이번 컨테이너화 범위에서 하지 않았으며 보안 점검 통과를 주장하지 않는다.
공유망 분리/복구, restart/rebuild 비교, 다른 DB DNS 격리 실험, PR 병합은 선택 심화이며 수행하지 않았다.

## 제출 구성

앱 소스 general/, monitor/ (기존 React도 보존), Compose 2개, Dockerfile·.dockerignore,
requirements.txt·package.json·package-lock.json, SQL, gateways/, README, docs/, verification/를 포함한다.
Git 추적 파일의 ZIP을 생성해 node_modules·.next·가상환경·캐시·DB 데이터·실제 .env가 포함되지 않게 한다.
GitHub 제출은 본인 저장소와 push 확인 후 별도로 수행한다. 현재는 로컬 커밋과 ZIP 제출본이다.
