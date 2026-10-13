# 1·2·3단계를 거치며 발견한 문제 목록

작성: 2026-10-11, Claude Code
범위: 1단계 구현 + 2단계·3단계 사양 작성 과정에서 **코드와 파일을 직접 열어 확인한** 것만.
한국어로 쓴 이유: 읽는 사람이 사람입니다. `CONVENTIONS.md` §5의 "`handoff/` 는 영어" 규칙과 어긋나는
점을 밝혀 둡니다(2·3단계 `_KO.md` 와 같은 선례).

분류 원칙 — **오류와 중복을 섞지 않습니다.**
A 오류(틀린 값·조용한 누락을 실제로 만드는 것) / B 미연결(있어야 할 연결이 없는 것) /
C 중복(같은 것이 두 번 있는 것, 오늘 피해는 없음) / D 미정의·미측정(코드가 아니라 결정·측정이 막는 것) /
E 테스트 공백·절차.

근거 표기가 없는 항목은 없습니다. 추측은 넣지 않았습니다.

---

## A. 오류

### A-1. 수정 완료 (1단계)

| # | 위치 | 무엇이 틀렸나 | 상태 |
|---|---|---|---|
| A1 | 전 이미지 IO | 한글 경로에서 `cv2.imread` 는 `None`, `cv2.imwrite` 는 `False` 반환. **입력을 한 장도 못 읽고**, 마스크는 어디에도 안 써졌는데 품질은 "학습 가능"으로 발행 | 수정 (`io/images.py`) |
| A2 | `mask/silhouette.py` | 투영된 보드 사각형이 **T0 실루엣 전체**를 지움(식물 화소 60,077개 중 **0개** 생존)인데 세션은 사용 가능 표시 | **보수적 임시 조치** — 설계 결정 대기(D-2) |
| A3 | `cli/run_stage1.py` | 800×600으로 줄인 사진이 1600×1200 보정값으로 풀려 카메라 거리 **713 mm → 1413 mm**. 잔차는 1 px 게이트를 통과할 만큼 작아 어떤 품질 지표도 못 잡음 | 수정 (검출 전 크기 검사) |
| A4 | `cli/run_stage1.py` | 재실행이 이전 마스크를 새 `quality.json` 옆에 남김 | 수정 (스테이징 후 일괄 교체) |
| A5 | `config/board_spec.json` ↔ `io/schemas.py` | 설정이 스키마 검증을 통과하지 못해 **아무것도 돌지 않던** 상태(금지 키 17개, `null` vs `Field(gt=0)`) | 수정 (스키마 확장, 설정 불변) |

A1–A4는 각 회귀 테스트가 **변이 검증**을 통과했습니다 — 수정을 되돌리면 그 테스트가 실패합니다
(`build/mutation_check_stage1.py`).

### A-2. 미수정 — 보고만 (2·3단계 감사에서 확인, 반증 통과 6건)

| # | 위치 | 무엇이 틀리는가 |
|---|---|---|
| A6 | `tomato3d/synth/contours.py:57` | 깨진 소엽 마스크를 `continue` 로 조용히 버림. 감사 행도 남지 않고, **이웃 접촉도를 그 마스크 없이 계산**해 `contact_fraction` 이 낮아지고 `geometric` 판정이 뒤집힘 → 가려진 소엽이 윤곽 라이브러리에 정상으로 등록 |
| A7 | `tomato3d/synth/render_remote.py:89` | 재내보낸 작업이 **파일명만 보고** 이전 캔버스를 재사용(`seed`·`scene_params`·`parts.npz` 비교 없음) → finalize가 새 마스크·라벨을 옛 이미지와 짝지음. 학습쌍 어긋남 |
| A8 | `tomato3d/synth/sideview.py` 474·520·628–637·691–715 | 평면 `labels/`·`yolo/` 가 누적되고 manifest와 대조되지 않음(유일한 삭제는 `work/`) → 디렉터리를 glob 하는 학습기가 **현재 manifest에 없는 파일**을 읽음 |
| A9 | `tomato3d/synth/cli.py:442,449` | `scene_params.csv` 헤더는 첫 생성 때만 쓰는데 `fieldnames` 를 매 행에서 뽑음 → 설정이 바뀌어 키가 하나 늘면 **그 뒤 모든 열이 조용히 밀림**. fieldnames가 행에서 오므로 `extrasaction='raise'` 가 못 잡음 |
| A10 | `tomato3d/synth/cli.py:401,439,517-520` | manifest·rejected 를 run id 없이 append. `cmd_realism` 은 scene은 set으로 중복 제거하면서 행은 전부 합산 → **재생성한 scene 통계 이중 계산** |
| A11 | `tools/plant_traits.py:120` | 레거시 S8 경로가 마스크 0개인 top 사진을 건너뛰고 **남은 것들의 평균**을 `top_leaf_area_cm2` 로 발표. 그 값에 DLI를 곱해 `intercepted_mmol_d` 가 나옴. v2 경로는 같은 상황을 거부하고 주석까지 달려 있는데 **실제 설정은 레거시 경로를 탐** |

A6–A10은 `tomato3d/` (제 영역, 지시하면 수정), A11은 `tools/` (Codex 영역, 인계 필요).

### A-3. 3단계 검토에서 드러난 모델 쪽 오류

| # | 위치 | 무엇이 틀리는가 |
|---|---|---|
| A12 | ψ = 42.4 °Cd | 원 변수명이 `delay_between_fruit_appearance` — **과실 출현 지연**입니다. 엽 출현 간격(phyllochron)으로 쓰면 안 됩니다. 요청서 지적이 사실로 확인됨 |
| A13 | 생장 엔진 예측 상태 | `surface_role = 'compound_envelope'` 로 태깅 — 광 계산에 **금지된 형태**가 이미 코드에 있음(광 쪽은 소엽별 삼각형을 올바르게 씀) |
| A14 | `tools/compound_growth.py` | `train_plant_ids` 를 **분리 확인용으로만 읽고** 그 뒤 적합을 제약하지 않음 → 동결 분할이 사실상 아무 일도 안 함(누설 방지 장치가 작동하지 않음) |
| A15 | `forecast()` | 입력 스냅샷 필드가 비어 있음 → 어느 입력으로 만든 예측인지 추적 불가 |

---

## B. 미연결

| # | 끊긴 지점 | 확인 내용 |
|---|---|---|
| B1 | 탄소 → 기관 sink 배분 | **배분 엔진이 아예 없음** |
| B2 | 배분 → 기관 생장량 | 생장 엔진이 **탄소를 모름**: 2,309행에 `carbon`/`assimilate` **0회** |
| B3 | 생장 → 다음 구조 | 되먹임 없음. 자란 구조를 다음 광 계산 입력으로 넣는 경로가 없음 |
| B4 | 광 ① → 광합성 ② | 두 표현을 잇는 **운영 어댑터가 없음** |
| B5 | ①·②의 실측 적용 | 구현·실행됐지만 **합성 입력에서만**. 실제 개체 `dwt_01` 은 광 단계 전체가 모든 값을 `unavailable` 로 반환 |
| B6 | 2단계 출력 → 기존 계산기 | 계산기 둘 다 `coordinate_frame == 'board_mm'` 를 **강제 검사**, 2단계 기본은 `plant_local_mm`, 둘 사이 변환은 **복원 불가로 금지**. 즉 보드 없는 촬영은 기존 계산기에 들어갈 수 없음 → **가장 어려운 장벽** |
| B7 | `tomato3d/graph`·`track`·`organ`·`pheno` | **전부 빈 스텁**(각 `NotImplementedError` 3개). 2단계가 기댈 구조·추적 구현이 없음 |
| B8 | `phynotype2/` | **README만 존재**. `SCHEMA.md`·`PROTOCOL.md`·`tracking_config_template.json` 없음 → 추적 단계 미구현, 계약은 handoff 문서로만 |
| B9 | `removal_confirmed` 와 사람 라벨 | `data/records/manual_events.csv`·`organ_label_map.csv` **부재** → 두 기능이 구조적으로 도달 불가 |
| B10 | `environment_log_ref` | 값이 `data/records/<plant_id>/environment.csv` 를 가리키는데 **아무 코드도 해석·검증하지 않음**. `Settings` 에 `records_dir` 속성 없음 |
| B11 | 대응 신뢰도 | 요청서가 전제한 "기관 대응 신뢰도"가 phynotype2 §7에 **없음** — 366행 전체에 `confidence` 문자열 0회, §7.6에 옛 스켈레톤의 `confidence` 열을 **뺐다**고 기록. 최적–차선 마진은 요구되는데 **열 이름도 파일도 미지정** |

---

## C. 중복 (오늘 피해 없음 — A와 섞지 않음)

| # | 중복 | 내용 |
|---|---|---|
| C1 | `tomato3d/synth/images.py` ↔ `tomato3d/io/images.py` | 같은 기능 두 번 구현, synth 24개 호출지점. 둘 다 한글 경로 안전하고 쓰기 실패 시 예외를 던져 **오늘 데이터 손실은 없음**. 다만 세 군데 갈림: 없는 파일(`FileNotFoundError` vs `None`), 기본 플래그(`UNCHANGED` vs `COLOR`), 빈 확장자 처리. **import만 바꿔선 합칠 수 없고** 호출지점마다 flags를 명시해야 함. A6의 "조용히 버림"이 가능해진 것도 이 갈림 때문 |
| C2 | `tools/make_square_board.py` | `DICT_4X4_50` 과 자체 인라인 사양을 하드코딩 — `config/board_spec.json` 을 읽지 않음. 보드 사양의 두 번째 출처 |
| C3 | `tools/plant_structure.py` (739행) | 2단계 구조 조립과 범위가 겹침. 새로 쓰기 전에 Codex가 중복 여부를 판정해야 함 |
| C4 | 광 계산 백엔드 | 네이티브 GroIMP 백엔드는 스칼라 전용(공간 샘플·방향 채널 없음)이고 `tomato3d/light/` 와 병행 구현 관계 |
| C5 | `test_schema_roundtrip` | 브리프는 한 개를 요구, 구현은 4개로 분리(`_json`/`_intrinsics`/`_manifest`/`_poses_csv`). 내용은 더 강하고 **이름이 계약과 다름** |
| C6 | 감사 보고 자체 | `contours.py` 한 지점을 두 감사(R1·R2)가 각각 보고 → A6으로 1건 병합 |

---

## D. 미정의·미측정 (코드가 아니라 결정·측정이 막는 것)

| # | 막힌 것 | 결과 |
|---|---|---|
| D1 | `scale_block_nominal_height_mm` = `null` | **모든 실루엣이 생성되지 않음**. 대체 높이를 넣지 않음 |
| D2 | 상면 실루엣 설계 결정 | T0가 필수라 **모든 세션이 `usable_for_training=false`** |
| D3 | `pot_rim_inner_diameter_mm` 미실측 | 전 개체 `scale_status = unavailable` → **mm 값 0건**, 가림 보완 후보 생성도 금지 |
| D4 | 점등 시각 = null | 경과시간 산출 불가 → **생장과 일주운동을 분리할 수 없음**. 과거 촬영분 **소급 불가** |
| D5 | 소엽 표면 기울기·잎자루 삽입각·소엽 굴곡 | **정의 자체가 없음**(복엽 문서에 기준면·부호·값 전무) → 적합할 대상이 없음 |
| D6 | θ 평/휨 경계 | 정적 측정 **7건 이상** 필요, 현재 **0건** |
| D7 | 18개 슬롯의 `plant_id` 가 전부 빈칸 | **식별된 개체 0개** → 날짜 간 추적이 성립하지 않음 |
| D8 | `capture_id` 문법 미정의 | 8개 표의 열인데 문법이 없음 |
| D9 | `area_basis` 미정의 | 면적 재현성의 전제(초록만 vs 외곽 전체) |
| D10 | 절대 PPFD 없음 | 비율뿐이고 유효 n은 18이 아니라 **9**, 같은 줄 두 개체 완전 교락 → 광반응 계수 불가 |
| D11 | 문헌 파일 디스크 부재 | diaf024·Butturini·Carvalho·Martí 전부 없음 → 수치는 요청서 본문 인용이며 **원논문 대조 못 함** |
| D12 | `physical_print_verified` = false | 인쇄된 종이를 실제로 재지 않음 |
| D13 | `board_center_mm` 의 의미 미명시 | 보드 중심인지 회전판 축인지 불명 → 교차검증 불가 |

**측정 기록 실태 한 줄 요약**: 같은 개체·기관의 반복 관측 **0건**, 캘리퍼 실측 **1건**(50.71 mm,
개체 미식별), 화방 관측 **0건**, θ **0건**. 그래서 어떤 생장 속도·발생 간격도 오늘은 추정 불가입니다.

---

## E. 테스트 공백·절차

| # | 문제 | 내용 |
|---|---|---|
| E1 | synth 테스트 12개 전부 ASCII 경로 | `pyproject.toml` 의 `testpaths = ["tests"]` 가 `tools/tests` 103개를 아예 수집하지 않음 → **A1이 되살아나도 전체 통과**합니다 |
| E2 | 기계적 방지 장치 없음 | `cv2.imread`/`imwrite` 금지를 강제하는 린터 규칙이 없고, `CONVENTIONS.md`·`CLAUDE.md`·`AGENTS.md` 어디에도 이 제약이 적혀 있지 않음 — 규칙이 모듈 docstring 두 줄에만 존재 |
| E3 | `.gitignore` 부재 | `CONVENTIONS.md` §7이 요구하는데 파일이 없음 → `build/`·`data/`·`__pycache__/`·`.env` 가 전부 추적 대상 |
| E4 | `handoff/LOG.md` 덮어쓰기 | 2026-09-16에 **두 번**(18:48, 18:55) 이전 사본으로 통째로 다시 쓰여 Claude Code 항목 2건이 사라짐. append-only(§5) 위반. 그래서 기록을 별도 파일로 보존했습니다 |
| E5 | 기준선에 예측구간 없음 | `compound_growth` 가 구간을 만들지 않아 **적중률을 채점할 대상이 없음** |
| E6 | 지평·범위가 한 `if` 에 묶임 | `probabilistic_compound_growth.py:796-797` 이 30일과 `provided_axes` 를 함께 강제 → 지평 **길이** 목록은 코드 변경 필요 |
| E7 | 평가 대상 시각 정합 | 대상 시각이 `observed_at` 과 **정확히** 일치해야 함. 세션 날짜로 계획을 세우면 조용히 `unavailable` 행이 됨 |

---

## 우선순위 제안

**즉시 (오늘 산출물이 틀리게 나오는 것)**: A6 → A9 → A7 → A8 → A10 (제 영역) / A11 (Codex 인계).
**측정 한 번으로 많이 풀리는 것**: D1(블록) → D3(테두리 내경) → D4(점등 시각) → D7(`plant_id` 부여).
**결정이 필요한 것**: D2(상면 설계), B6(좌표계 게이트), D5(각도 정의).
**되살아남 방지**: E1·E2(테스트와 린터), C1(중복 통합), E4(LOG append 준수).

---

## 추가 (2026-10-11 저녁) — Amendment L1 검증 결과 반영

다른 세션이 2·3단계 사양서에 덧붙인 Amendment L1을 파일로 검증했습니다. 설계 내용은 수용, 코드
참조는 전부 일치. 다만 "이미 있다/해결됐다"고 쓴 세 가지가 **아직 계획 단계**라 아래를 정정합니다.

| 항목 | 정정 |
|---|---|
| **D5** 각도 정의 3종 | L1은 "MTG A1/A2로 2/3 해결"이라 했으나 **A2는 존재하지 않습니다.** `MTG_CONVENTION_2026-10-10.md` 는 `## 10` 에서 끝나고 `## 11 Amendment` 가 없음. A2 필드명 4개는 **A2를 쓰라는 지시문**(`CLI_PROMPT_LITERATURE_P1P4_2026-10-11.md` P1-1, Claude Code 담당)에만 있음. A1도 별도 파일로만 있고 규약 본문에 병합되지 않음 → **D5 는 미해결 유지.** 고도각 부호(+ = 위)만 A1.4로 이미 확정 |
| **A13 / CR-3** 복엽 포락면 | vtc 포크 표현은 소엽 단위(`modules_organs.rgg:385, :399, :406`)라 **포크 쪽은 만족**. 그러나 `tools/` 생장 엔진의 `surface_role='compound_envelope'` 는 그대로 → **CR-3 는 트랙 (a)에서 미해결 유지** |
| **E8 (신규)** 선행 산출물을 현재형으로 기술 | L1이 세 가지를 존재하는 것처럼 참조: `tools/phyllotaxis_fit.py`(없음, 문헌 프롬프트 P1-2), `build/vtc_microtom_20261011/`(없음, 포크 프롬프트), `light_input.csv`·`light_ratio_latest.txt`(없음, 포크 Task 3). 사양서에 소유자 조정 메모를 덧붙여 **선행 계약**으로 표시했습니다 |

**확인된 것**: vtc-main 코드맵 전부 일치 — `rewrites.rgg:65-66`(4번째 phytomer마다 화방, 무한생장),
`modules_organs.rgg:355 calcAngle` / `:362-364 LEAF_CURVE/segments` "hardcoded for 3 leaflet pairs" /
`:374 calcNrLeaflets` / `:774 Apex`, `parametersMerlice.rgg:7 PHYLLOCHRON 37.9` / `:8 FINAL_VEG_PHYT_NUM 8` /
`:26 MAX_LEN_INT 0.072` / `:5 DELAY 206.3`. 두 사양서 모두 제 원문이 그대로이고(append-only 준수),
LOG 기록(642행)도 있음.

**다음 선행 작업(이 순서로 풀립니다)**: ① A2를 MTG 규약에 실제로 덧붙임(문헌 프롬프트가 Claude Code
에 배정) → D5 가 "소엽 잎몸 말림"만 남음 ② `tools/phyllotaxis_fit.py` ③ vtc 포크 생성 + light 파일.

### D5 갱신 (2026-10-11, A2 덧붙임 후)

A2를 MTG 규약 §12에 실제로 덧붙였습니다(A1은 §11에 참조 편입). 이제 정의가 있는 것: 잎자루 삽입각
(줄기축↔잎자루, 측면·3D 전용, 상면만으로는 `unavailable`), 엽축 마디별 휨 α_i(아래쪽 양수, 생성기
`rachis_droop_deg` 부호와 일치)와 부호 합 `rachis_curvature_deg`, 방위 2칸(`petiole_base_azimuth_deg` /
`blade_azimuth_deg`)과 방위 기준(§12.1 — 그전엔 규약에 기준 자체가 없었음). **남은 미정의는 소엽 잎몸
말림뿐**(§8.3). θ와 Σα의 관계를 명시: θ는 마지막 마디의 휨 α_m을 구조적으로 제외하므로 둘은 다른 양이고
둘 다 유지. 임계값·기본값은 하나도 넣지 않았습니다.

**새 주의 항목 C7 (동음이의)**: `insertion_angle_deg` 가 두 스케일에서 다른 뜻 — CompoundLeaf(줄기↔잎자루,
A2) vs Leaflet(엽축 접선↔소엽, `leafarea.py:339`·Addendum C). `mtg_vertices.csv` 는 행마다 `class` 가 있어
충돌하지 않지만 **평면 내보내기는 반드시 class 접두어**를 붙여야 함. 이름은 바꾸지 않음(지시문 고정).
