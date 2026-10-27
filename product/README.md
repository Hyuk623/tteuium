# Tomato 관찰 대시보드 MVP

기존 tomato3d Analysis Engine을 유지하고 독립 Product Layer를 확장했습니다. Python 3.11+, FastAPI, SQLite, 빌드 없는 HTML/CSS/JS를 사용합니다. 연구 모델 설치나 실행은 필요 없습니다.

## 실행 — 저장소 루트에서 PowerShell

```powershell
python -m venv build/product-venv
build/product-venv/Scripts/python -m pip install -r product/requirements-dev.txt
build/product-venv/Scripts/python -m product.backend.api
```

서버를 유지한 채 두 번째 터미널에서 14일 모의 데이터를 생성합니다.

```powershell
build/product-venv/Scripts/python -m product.device_contract.seed_demo
```

[대시보드](http://127.0.0.1:8000) · [API 문서](http://127.0.0.1:8000/docs)

- 기본 DB: `build/product/product.sqlite3`; 재시작해도 보존됩니다.
- 종료: 서버 터미널 Ctrl+C. Linux/macOS는 `Scripts/python` 대신 `bin/python`.
- 별도 포트 사용: API에 `--port 8019`, 생성기에 `--url http://127.0.0.1:8019`.
- 별도 DB 사용: API에 `--db build/product/my-demo.sqlite3`.
- 데이터 생성 재실행은 일별 센서/성장 기록을 중복 생성하지 않습니다. 마지막 현재 시각 센서 샘플 1건은 새로 추가합니다.
- 5분 이상 지나면 모의 센서도 오래된 데이터로 표시합니다. 생성기를 다시 실행하면 최신 샘플이 추가됩니다.
- Windows venv 설치가 실패하면 `python -m pip --python build/product-venv/Scripts/python.exe install -r product/requirements-dev.txt`로 설치할 수 있습니다.

## 실제 구현 화면

| 화면 | 기능 |
|---|---|
| 홈 | 식물명·최근 이미지, 온도/습도, 선택 기간 성장 변화, 근거를 펼쳐보는 확인 필요 항목, 향후 카메라 관찰 안내 |
| 성장 | 초장/잎 면적/캐노피 면적의 출처별 그래프, 정확한 값 표, 첫/최근 이미지 비교, 직접 잰 키 입력 |
| 환경 | 선택 장치의 온도/습도 시간 그래프, 모의/센서 출처 분리, 7/14/30일 선택, 누락값 보존 |
| 기록 | 월간 캘린더·날짜별 기록, 종류/내용 필터, 최신/오래된/종류순 목록, 관리 활동 및 메모 저장/조회 |

관측과 수동 기록을 돕는 화면이며 정상·질병·영양결핍을 판단하지 않습니다. 데이터 조회 실패·빈 데이터·오래된 관측을 별도로 표시합니다. 30초마다 갱신합니다.

## Mock / 사람 / 모델 / 실제 장치 구분

- `seed_demo`의 환경/생육은 모의값, 이미지는 SVG 예시 그림입니다. 실제 촬영/생육 분석이 아닙니다.
- 직접 입력한 키는 human, 기기 수신값은 device, 연구 CSV 값은 model_estimated, 미지원 값은 unavailable입니다. 모의 연구 fixture는 synthetic_fixture로 남습니다.
- 성장 그래프는 출처·시나리오·형상 variant·상태별로 분리합니다. 모의값과 실제값을 한 성장 추세로 연결하지 않습니다.
- `plant_light.csv`의 잎 면적은 모델 형상의 면적입니다. 초장/캐노피 투영면적은 해당 CSV에 없으므로 어댑터에서 unavailable입니다. 수동/모의 입력과 구분합니다.
- 실제 센서의 단위·보정·통신·시각 정책은 아직 검증하지 않았습니다. lux를 PPFD/DLI로 환산하지 않습니다.

## tomato3d 어댑터

기존 `plant_light.csv` 어댑터를 재사용합니다. 먼저 실제 CSV의 plant_id와 동일한 식물을 API에서 등록해야 합니다. 아래 fixture는 기존 mock_sensor로 demo-plant를 등록한 뒤 실행합니다.

```powershell
build/product-venv/Scripts/python -m product.device_contract.mock_sensor --count 1 --interval 0
build/product-venv/Scripts/python -m product.backend.adapters.tomato3d --csv product/tests/fixtures/plant_light.csv --plant-id demo-plant --scenario-id as_built --geometry-variant-id fixture --observed-at 2026-10-18T09:00:00+09:00 --evidence synthetic_fixture --import-id demo-light-1
```

실제 CSV는 `--evidence research_model`을 사용하고 관측 시각/시나리오/variant를 해당 결과와 일치시킵니다. SHA-256과 원본 출처가 저장됩니다. 현재 날짜가 위 예시 날짜보다 30일 이상 지나면 기간 필터에 나타나지 않습니다. 실제 관측 시각으로 실행하세요.

## 안전한 확인 안내

기본 재배 임계값은 null(비활성)입니다. 대시보드는 오래된/누락된 데이터 확인과 같은 출처의 최근 5일 이상 비교에서 지표 증가가 관찰되지 않는 경우에만 근거→측정 방법·조명·온도·급수 확인→기록/재관찰을 안내합니다. 낮은 성장률의 농업적 기준, 질병 진단, 자동 처방은 없습니다. 새 안내는 조회 때 계산되며 별도 알림이나 해결 상태는 없습니다. 기존 이벤트별 임계값 기록 API는 유지합니다. `rules.demo.json`의 기준은 데모용일 뿐이며 기본 실행에서는 사용하지 않습니다.

## 검증

```powershell
build/product-venv/Scripts/python -m pytest product/tests -q --basetemp=build/product-test-run
```

테스트 전용 폴더를 사용하세요. pytest가 basetemp를 정리합니다. 테스트는 ingestion, 재전송/충돌, 단위/시간대 검증, 어댑터, 출처 분리, 기간 필터, 저장 유지, 실제 HTTP 서버에서 mock/adapter/14일 생성기 재실행을 검증합니다. `requirements-tested.txt`는 기존 환경 버전 기록입니다.

## 미구현 / 보류

열매/상태/질병 진단, 영양결핍 확진, 농학적으로 검증된 추천, 자동 제어, 실제 기기 연결, PPFD/DLI/잎별 분포 상세 연결, 이미지 업로드, 인증/다중 사용자, 원격 배포, PostgreSQL 런타임 및 정식 DB 마이그레이션은 미구현입니다. 이미지 URL/참조만 등록합니다. 서버는 로컬 단일 사용자용으로 loopback에만 바인딩합니다.

[6주 로드맵과 전문가 결정 3가지](docs/roadmap.md) · [아키텍처/Plant State/DB/확장 계약](docs/observation-mvp.md) · [변경 파일과 검증 결과](docs/delivery.md) · [기존 CSV 매핑](docs/adapter.md)

## 모의 환경 v2 (2026-10-18)

`seed_demo --live`는 14일 이력 생성 후 60초마다 새 모의 센서값을 전송합니다. Ctrl+C로 종료합니다. 한국 시간 기준 조명 07–21시, 창가 빛 07–18시, 온습도 일주기와 작은 센서 흔들림, 4일 간격 물 보충을 가정합니다. 온도 약 20–26°C, 습도 약 50–68%, 밝기 야간 약 3–5 lux/주간 최대 약 9,800 lux, 수위 약 36–88%로 구성한 가상 시나리오입니다. 작물별 적정 범위·실측·보정된 생육 예측이 아닙니다. 성장값도 별도 가상 곡선입니다. 기존 v1 데이터와 같은 이벤트 ID를 사용하므로 v1 DB에는 충돌 방지가 작동합니다. 새 DB 경로로 실행하거나, 기존 데이터 백업 후 생성기 소유의 모의값만 명시적으로 교체해야 합니다. 이번 활성 데모 DB는 백업 후 모의 센서/생육값만 교체했으며 수동 기록은 보존했습니다.

## 시뮬레이션 탭

선택 식물에 명시적으로 등록한 모델 이미지/3D 뷰어를 별도 탭에서 확인할 수 있습니다. 현재 실제 결과 파일이 연결되지 않았다면 빈 상태로 표시합니다. 자동으로 현재 식물을 시뮬레이션하는 기능은 아닙니다. [등록 방법과 검증 범위](docs/simulations.md).

## 개인 Fork / 팀 데모

개인 Fork의 개발·자동 배포·원본 PR 통합 절차: [Fork 작업 방법](docs/fork-workflow.md).
Pages 공개 데모의 기록은 브라우저에만 저장되고 팀원과 공유되지 않습니다. 로컬 API/SQLite 버전은 그대로 유지합니다.

## 2026-10-27 도메인 회의 변경 (이전 범위보다 우선)

현재 환경 센서는 온도·습도만 표시/생성합니다. 기록은 월간 캘린더와 필터·정렬 가능한 목록을 지원합니다. 시뮬레이션 탭 및 홈 빛 분석은 제거했습니다. 카메라 기반 잎 분할/관리 제안은 준비 중이며, 이번에 진단이나 제거 추천을 구현한 것은 아닙니다. [변경 내용과 후속 완료 기준](docs/domain-review-2026-10-27.md).

기록 캘린더에서 날짜를 누르면 해당 날짜의 기록 조회/입력 팝업이 열립니다. 선택 날짜(action_date)와 실제 저장 시각(created_at)을 구분합니다. 기존 기록은 저장 시각의 현지 날짜를 사용합니다. 닫은 팝업의 임시 입력은 같은 페이지 안에서 날짜별로 유지되며 새로고침하면 사라집니다.
