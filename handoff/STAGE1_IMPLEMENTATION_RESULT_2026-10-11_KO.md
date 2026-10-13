# 1단계 "촬영·보정" — 실행 결과와 적합성 보고서

작성: 2026-10-11, Claude Code
구현 대상: `handoff/CLAUDE_CODE_PROMPT_STAGE1_2026-09-15.md`
영어판: `handoff/STAGE1_IMPLEMENTATION_RESULT_2026-10-11.md`
하류: `handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md`(2단계) →
`handoff/CODEX_FORECAST_SPEC_2026-10-10.md`(3단계)

---

## 1. 결론부터

1단계는 구현돼 돌아가고, 브리프 §13 완료조건 다섯 개는 **직접 측정해** 전부 충족입니다. 오늘 판본
기준으로 조항별 채점은 **96개 중 충족 77 · 부분 11 · 미달 3 · (기록된 결정으로) 대체 5** 입니다.

**다만 지금 1단계는 식물 실루엣도, 물리 단위 값도 하나도 내지 않습니다.** 이것은 결함이 아니라
규약을 지킨 결과입니다.

| 막힌 산출 | 원인 | 무엇이 풀어주는가 |
|---|---|---|
| 모든 식물 실루엣 | `scale_block_nominal_height_mm` 가 `null` → 스케일 블록을 제외할 수 없음 | 블록을 캘리퍼로 실측 |
| `silhouette_area_cv` | 위의 결과 | 동일 |
| 전 세션의 `usable_for_training` | `silhouette_area_cv_unavailable` + `operational_top_view_silhouette_unavailable` 로 차단 | 위 + 상면 설계 결정(§6) |
| 하류의 모든 mm 값 | 화분 테두리 내경 미실측(보드 없는 촬영) | 실측. 2단계 §3 참조 |

프레임별 포즈 계산 자체는 정상입니다 — 41장 합성 세션에서 **41/41 포즈 해, 평균 재투영 0.22 px**.

---

## 2. 무엇을 만들었나

1단계 모듈 16개: `config.py`(동결 `Settings`, `lru_cache` 된 `get_settings()`, 파생 경로는 속성) ·
`logging_setup.py` · `io/schemas.py`(모든 스키마·`poses.csv` 열 순서·`unavailable` 센티넬) ·
`io/manifest.py` · `io/tables.py`(pandas/csv 를 쓰는 유일한 모듈) · `io/quality.py` ·
`io/images.py`(리뷰 R1 이후 추가, 한글 경로 안전) · `calib/board.py`(ChArUco·코너 검출·시트↔보드
프레임 변환) · `calib/intrinsics.py` · `calib/pose.py` · `mask/silhouette.py` ·
`cli/{calibrate_intrinsics,run_stage1}.py`. 후속 단계 스텁 29개 파일. 1단계 테스트 7개 파일
(전체 262개 테스트 중).

세션 산출물은 **한 묶음으로 발행**됩니다(스테이징 후 교체):
`data/derived/<plant_id>/<session_id>/{poses.csv, masks/, quality.json}`.

현재 운영 보드: **`charuco_7x5_266x190mm`** (7×5칸, 266×190 mm, A4 가로),
`physical_print_verified: false`, `scale_block_nominal_height_mm: null`.

---

## 3. 브리프 적합성

"충족" 주장마다 반증 담당이 인용된 `file:line` 을 직접 열어 검증했고, 그 과정에서 네 건이
강등됐습니다.

### 미달 3건

| 조항 | 요구 | 상태 |
|---|---|---|
| §6 | `.gitignore` (`build/`·`data/` 포함) | 파일 없음. `CONVENTIONS.md` §7도 미충족. **제가 구현한 뒤 브리프에 추가된 조항** |
| §7 | `data/records/<plant_id>/` 의 4개 CSV | 없음. 사람이 쓰는 정답 자료이고 브리프도 파이프라인이 쓰지 않는다고 명시 |
| §9 | `solve_pose` 가 `cv2.aruco.estimatePoseCharucoBoard` 사용 | **OpenCV 4.13에 그 심볼이 없음** — §7 |

### 부분충족 11건

타입힌트(`tomato3d/` 는 0건 누락, 브리프가 트리에 넣은 `tests/` 는 87곳) · 단위 없는 변수
(`pose.py:137 radius`, `board.py:148,154 points`) · 매직넘버(상수로 명명했지만 **config JSON에서
오지 않음**, PnP 최소 `4` 2곳) · `Settings` 6번째 필드 `synth_path_map`(다른 세션 추가, LOG 기록) ·
`_note_board` 키 부재 · `intrinsics_shots/`(docstring뿐) · `environment_log_ref` 미검증 ·
컬러차트 미제외 · `segment_plant_silhouette` 무조건 raise · `test_schema_roundtrip` 이름 분리 ·
§13.1(감사에 실행 금지 → §4에서 별도 측정).

### 대체됨 5건

보드 7×7/190 mm → **`charuco_7x5_266x190mm`**(9/17 사람 지시) · "특징점 기반 포즈 전면 금지" →
S4 진단 뷰로만 허용(9/24 사람 선택) · 렌더러를 `tools` 에서 import → `tests/conftest.py` 가 정본 ·
`build/` 단독 소유 → 공용 · 합성 세션 문법 `<plant_id>_gen_<YYYYMMDD>` 추가.

---

## 4. 완료조건 — 직접 측정값

| # | 조건 | 결과 |
|---|---|---|
| 1 | `pytest` 통과 | **261 passed, 1 skipped** (스킵은 선택 의존성 `openalea.lpy` 미설치) |
| 2 | `run_stage1 --help` | exit 0 (`calibrate_intrinsics --help` 도 exit 0) |
| 3 | README에 설치·`.env`·보정·세션 실행 | 네 항목 모두 |
| 4 | 후속 패키지 import + `NotImplementedError` | 진입점 **21개 전부**, 잘못된 예외 0 |
| 5 | `pyproject.toml` 에 SfM 의존성 없음 | 없음(유일한 일치는 설명 주석) |

---

## 5. 리뷰 지적과 수정

### Codex 리뷰 R1–R4

네 건 모두 고치기 전에 재현했고, 각 회귀 테스트는 **변이 검증**을 통과했습니다 — 수정을
되돌리면 그 테스트가 실패합니다(`build/mutation_check_stage1.py`).

- **R1** 한글 경로에서 `cv2.imread`/`imwrite` 가 조용히 실패 → 입력을 한 장도 못 읽고, 마스크는
  어디에도 안 써졌는데 품질은 "사용 가능"이라고 보고. → 모든 이미지 IO를 `io/images.py` 로,
  쓰기 실패는 예외·하드 실패, **CLI 테스트 전체를 한글 데이터 루트에서** 실행.
- **R2** 투영된 보드 사각형이 **T0 실루엣 전체**를 지움(식물 화소 60,077개 중 0개 생존)인데 세션은
  여전히 사용 가능 표시. → 상면은 마스크하지 않음, 빈 마스크는 발행하지 않음, 새 유효성 코드가
  `usable_for_training` 을 차단. **보수적 임시 조치**이고 설계 질문은 열려 있음(§6).
- **R3** 800×600으로 줄인 사진이 1600×1200 보정값으로 풀려 **카메라 거리 713 mm 대신 1413 mm**,
  잔차는 1 px 게이트를 통과할 만큼 작음. → 검출 전에 크기를 `Intrinsics.image_shape` 와 비교,
  불일치는 기록된 실패 + 유효성 코드.
- **R4** 재실행이 이전 마스크를 새 `quality.json` 옆에 남김. → 산출물을 스테이징 후 한 묶음으로
  교체, `quality.json` 이 가장 먼저 나가고 가장 마지막에 들어옴, 1단계 산출물 3개만 교체.

응답 문서: `handoff/CLAUDE_CODE_STAGE1_REVIEW_RESPONSE_2026-09-16.md`.

### BoardSpec 수정

`config/board_spec.json` 이 다시 쓰이면서 검증을 통과하지 못해 **아무것도 돌지 않던** 상태였습니다
(엄격 모델이 금지하는 키 17개, `scale_block_nominal_height_mm: null` vs `Field(gt=0)`). 설정이 아니라
**스키마를 확장**해 해결했습니다: 새 필드를 타입과 함께 추가하되 `extra="forbid"` 유지,
`_` 접두 사람 메모는 그대로 보존하고 **코드가 절대 읽지 않음**, 마커·코너 수 교차검증, 블록 높이
nullable, `scale_block_footprint_mm` 선택 추가. `build_charuco_board` 가 legacy 플래그와
`marker_ids` 를 **명시적으로** 설정하고, `board_variant_id` 는 모든 매니페스트 필수이며 불일치 시
**산출물을 쓰기 전에** exit 2.

**스펙 정정(OpenCV 4.13에서 확인)**: `legacy_pattern` 은 **행 수가 짝수일 때만** 레이아웃을 바꿉니다.
7×7·5×5·6×7은 양쪽이 동일하므로, 이 프로젝트가 쓴 어떤 보드에도 "조용한 ID 오매칭 위험"은 애초에
없었습니다. 명시 호출 자체는 여전히 옳고(나중에 짝수행 보드가 추가될 때를 위해) 두 사실 모두
테스트로 고정했습니다.

---

## 6. 알려진 한계 — 오늘 1단계가 낼 수 없는 것

1. **실루엣이 전혀 없음.** 블록이 미측정이라 제외할 수 없고, 대체 높이를 넣지 않습니다. 포즈는
   계산되고, 이유는 실행당 한 번 기록되고, 마스크는 쓰지 않고, 세션은 학습에서 제외됩니다.
2. **상면 실루엣은 설계상 없음.** 위에서 보면 식물 전체가 보드 사각형 안에 투영되어 기하적 보드
   제거가 식물을 지웁니다. 빈/부분 상면 마스크는 시각적 외피에서 식물을 **깎아내므로** 아예 만들지
   않습니다. **운영 상면 T0가 필수라 모든 세션이 차단됩니다.** 해결에는 설계 결정이 필요합니다 —
   렌더한 보드 패턴과 비교 / 사각형 안에서 녹색 분류 허용(하드 제약 3과 충돌 소지) / 상면 실루엣을
   2단계 다중뷰 일관성으로 미루기.
3. **컬러차트 미제외.** `color_chart_on_board: false` — 보드 옆에 있고 위치가 사양에 없어, 고도 있는
   측면 뷰에서 식물 후보 영역에 들어올 수 있습니다.
4. **측면 실루엣은 화분과 줄기 하부를 잃습니다**(보드 사각형에 겹쳐 투영되므로).
5. **블록 바닥 크기**는 `scale_block_footprint_mm` 가 null이면 보드 한 칸으로 대체됩니다.
6. **`physical_print_verified: false`** — 인쇄된 종이를 실제로 재지 않았습니다.

---

## 7. 계약 정정

1. **`cv2.aruco.estimatePoseCharucoBoard` 는 OpenCV 4.13에 없습니다.** `solve_pose` 는 새 ArUco API의
   공식 대체 경로인 `CharucoBoard.matchImagePoints` + `cv2.solvePnP` 를 쓰고, 정확도는 재투영
   0.5 px 이내로 테스트에 고정돼 있습니다. **이 대체는 2026-09-16에 `handoff/LOG.md` 에 기록했지만
   그 파일이 이전 사본으로 두 번 덮어써지면서 사라졌고, 이 문서가 기록을 복원합니다.**
2. `legacy_pattern` 은 홀수 행에서 무효(§5).
3. 실패한 `poses.csv` 행은 **관측된 코너 수까지 포함해** 모든 숫자 열에 `unavailable` 을 씁니다 —
   브리프 문구를 문자 그대로 따랐습니다.
4. 측면 행의 `top_position` 도 `unavailable` — 구조적으로 없는 값이지만 센티넬을 하나로 유지해
   읽는 쪽이 빈 칸과 누락을 구분하지 않아도 되게 했습니다.
5. `scale_reference_block_mm` 를 nullable로 바꿨습니다 — 필수 float이면 블록 측정 전에 촬영한 모든
   매니페스트가 숫자를 **지어내야** 했습니다.

### 변경 요청 (적용하지 않음 — 제 영역 밖)

| CR | 요청 | 담당 |
|---|---|---|
| S1-CR-1 | `.gitignore` 생성(`__pycache__/`·`*.pyc`·`.pytest_cache/`·`build/`·`data/`·`.env` 이상) | 사람(루트 파일) |
| S1-CR-2 | `data/records/<plant_id>/` 와 4개 CSV를 만들지 여부·열 구성 | 사람 |
| S1-CR-3 | 세그멘테이션 상수를 config JSON으로 옮기거나 브리프 §12.5 수정 | 사람(`config/` 소유) |
| S1-CR-4 | `board_center_mm` 의 의미 확정(보드 중심 vs 회전판 축) | 사람 |
| S1-CR-5 | 블록 높이·바닥 크기 실측, `physical_print_verified` 는 실측 후에만 true | 사람 |

---

## 8. 사람 결정 대기

1. 스케일 블록 실측 → 모든 실루엣이 열립니다.
2. 상면 실루엣 설계 결정(§6-2) → `usable_for_training` 이 열립니다.
3. 컬러차트 위치, 또는 오염 위험을 감수한다는 명시적 결정.
4. 화분 테두리 내경 → 2·3단계의 모든 mm 값이 열립니다.
5. `.gitignore`(S1-CR-1), `data/records/` 배치(S1-CR-2).

---

## 9. 2단계 인계

2단계는 `poses.csv`·`masks/`·`quality.json` 을 받고 다음을 지켜야 합니다: 두 좌표계(시트/보드)와
유일한 변환기 `calib/board.py::sheet_to_board_mm`, `unavailable` 은 절대 0이 아님, 표는 CSV·설정은
JSON, `board_variant_id` 는 신뢰가 아니라 검사, 그리고 **오늘 마스크도 mm 값도 존재하지 않는다는
사실**. 2단계 계약이 이미 이 모두를 담고 있습니다 — `CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md`
§2–§4.

1단계 범위 밖: 재구성·기관 분할·표현형·2뷰 제품 — 모두 `NotImplementedError` 를 던지는 스텁
패키지로 존재합니다.
