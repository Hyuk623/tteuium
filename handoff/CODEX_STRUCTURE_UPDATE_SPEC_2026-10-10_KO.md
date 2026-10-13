# 2단계 "현재 식물 구조 갱신" 설계 설명서

작성: 2026-10-10, Claude Code
요청: `handoff/PROMPT_STRUCTURE_UPDATE_SPEC_2026-10-10.md`
영어 구현 계약: `handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md` ← **Codex가 실제로 따를 문서**
이 문서는 사람이 읽는 설명입니다. `docs/` 는 사람 소유이므로 `handoff/` 에 두었습니다 — 옮기실 위치는 정해주세요.

**구현하지 않았습니다.** 사양만 작성했습니다.

---

## 0. 읽은 파일과 없던 파일

읽은 파일(요청 순서대로): `../공통규약.md`(7,511 B — 요청서가 "경로 확인 필요"로 단 파일이지만 실제로
있었습니다) · `CONVENTIONS.md` · `handoff/CLAUDE_CODE_PROMPT_STAGE1_2026-09-15.md`(397행) ·
`handoff/CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md`(366행) ·
`handoff/MTG_CONVENTION_2026-10-10.md` · `handoff/CLAUDE_CODE_CLI_PROMPT_MTG_AMEND_2026-10-10.md` ·
`docs/복엽구조_형태_2026-10-10.md` · `docs/phynotype2_복엽_터미널리프_추적설계_2026-10-10.md` ·
`phynotype2/README.md` · `tomato3d/` 의 graph·track·organ·pheno·synth·io·calib·mask ·
`tools/` 관련 20여 개 · `data/records/` 5개 폴더(헤더와 행수만, 쓰지 않음) · `handoff/LOG.md`.

**요청서에 있었지만 디스크에 없던 것** — 아무것도 비슷한 파일로 대체하지 않았습니다.

| 없는 것 | 결과 |
|---|---|
| `phynotype2/SCHEMA.md`, `PROTOCOL.md` | `phynotype2/` 에는 README뿐 — **추적 단계가 아직 미구현**. 계약은 handoff 문서로만 존재 |
| `phynotype2/tracking_config_template.json` | 추적 문서 §9가 "모든 임계값의 유일한 집" 으로 요구하는데 없음 |
| phynotype2 `captures.csv` 실제 파일 | 디스크의 유일한 `captures.csv` 는 `build/observation_records_20261001/` 의 다른 옛 파일(`capture_id` 열 없음, 0행). 쓰지 않았습니다 |
| `handoff/NOTE_TO_CODEX_GENERATOR_FIXED_API_2026-10-10.md` | 실재하는 `..._S_GENERATOR_FIXED_TERMINAL_2026-10-10.md` 를 대신 읽고 그 사실을 기록 |
| `data/records/manual_events.csv`, `organ_label_map.csv` | **두 기능이 막힙니다** — `removal_confirmed`(추적 §5.4가 다른 증거를 인정하지 않음)와 모든 사람 라벨 연결 |
| `claude/MTG_기준_...`, `claude/복엽구조_형태_...` | `claude/` 폴더 자체가 없음. MTG 규약이 두 파일을 인용합니다. 뒤쪽은 `docs/` 의 같은 이름 파일로 보이지만 **경로가 다르므로 동일 문서로 가정하지 않고 표시만** 했습니다 |
| `compound_bend_types_20261010` 의 원본 사진 9장 | 저해상도 콘택트시트 PNG만 있음 (`docs/복엽구조_형태_2026-10-10.md:4` "사진은 채팅에만 있음") |

---

## 1. 먼저 바로잡아야 할 전제 — "대응 신뢰도"는 존재하지 않습니다

요청서 §1·§3은 입력을 "기관 ID와 **대응 신뢰도**(phynotype2 §7 출력)" 로 적었습니다. 확인 결과:

- 366행 추적 문서 전체에 **`confidence` 라는 문자열이 없습니다.**
- 옛 설계 스켈레톤(`TOMATO_3D_PHENOTYPING_ALGORITHM_SKELETON_2026-09-15.md`)의 `tracks.csv` 에는
  `confidence` 열이 있었지만 **phynotype2가 그것을 의도적으로 뺐습니다**(§7.6).
- 하류로 실제로 넘어오는 대응 품질 신호는 두 가지뿐입니다: `link_status` 가 `proposed|confirmed`
  두 값, 그리고 "최적–차선 비용 마진을 관측마다 보고하라"는 요구 — 그런데 **그 마진의 열 이름도,
  들어갈 파일도 정해져 있지 않습니다**(설정 키 `association.ambiguity_margin` 만 null로 존재).

그래서 영어 계약에서는 §7을 "**트랙 신원과 상태**의 유일한 출처" 로만 묶고, 마진 열을
`match_candidates.csv` 의 `match_margin` 으로 **신설 제안**했습니다(계약문제 a). 순위는 확률이
아니라는 문서의 선언도 그대로 지켰습니다.

---

## 2. 갱신 절차 (요약)

1. **입력 적재** — phynotype2 실행 폴더(`build/phynotype2_<날짜>_<번호>/<식물ID>/`)의
   `tracks.csv`·`track_states.csv`·`observed_geometry.csv`·`captures.csv`·`frame_transforms.csv`.
   열이 없으면 그 열 이름을 말하며 멈춥니다(추측 금지).
2. **좌표계 결정** — 촬영마다 `frame` 토큰을 하나 정합니다. 보드가 찍히고 포즈가 풀린 촬영은
   `board_mm`, 보드 없는 촬영은 화분 테두리 기준 `plant_local_mm`, 둘 다 아니면 `image_px`.
   **전역 상수가 아니라 행마다 기록되는 값**입니다.
3. **스케일 교차검증** — 근거가 둘 이상이면 비교해서 **5 % 넘게 다르면 중단·보고**. 평균 금지.
4. **MTG 스냅샷 작성** — 기존 ID 그대로 사용(ID를 만들지 않습니다). `track_id` 가 곧 MTG의
   `CompoundLeaf vertex_id` 라서 대응표가 필요 없습니다.
5. **면적 3종 산출** — 보이는 투영(px²) / 같은 것의 mm² / 가림 보완 추정(구간) / 실제 표면적.
   뒤 세 개는 지금 전부 `unavailable` 입니다(§4 참조).
6. **부착 관계** — 모르면 `unassigned`, 경합 부모는 `attachment_candidates.csv` 로. 간선을 만들지
   않습니다.
7. **변경 기록** — 이전 스냅샷과 무엇이 왜 달라졌는지 `change_log.csv` 에, 비어 있는 값은 전부
   `unresolved.csv` 에 "막힌 이유" 와 함께.

원 관측은 **복사하지도 덮어쓰지도 않습니다.** 추적 실행 폴더의 행을
`(capture_id, track_id, part, obs_id)` 로 참조만 하고, 날짜별 추정층은 별도 실행 폴더에 둡니다.

---

## 3. 식별 가능성 검토 — 상면 1장으로 어디까지 되는가

판단 담당에게 **근거가 얇으면 약한 쪽으로 판정하라**고 지시했습니다. 결과: 12개 중 **1개만 지금
산출 가능**합니다.

| 항목 | 판정 | 막는 이유 |
|---|---|---|
| 보이는 투영면적 (px²) | **산출 가능** | 단, `area_basis`(초록만/외곽 전체)를 사람이 정해야 재현 가능 |
| 같은 면적 (mm²) | 불가 | **화분 테두리 지름을 한 번도 안 쟀습니다** → 스케일 자체가 없음 |
| 가림 보완 투영면적 | 복수 후보 | 스케일이 없으면 후보 생성 자체가 금지(추적 §6.3) |
| 실제 잎 표면적 | 불가 | 소엽별 3D 면이 필요. 평탄화 기준 사진이 없음 |
| 소엽 표면 기울기 | 불가 | **복엽 문서에 정의가 없습니다**. 수직 근처 1장에서는 위/아래 부호가 물리적으로 구분 불가 |
| 잎자루 삽입각 | 불가 | **정의 없음** — 기준면·부호·값 어디에도 없음 |
| 엽축 휨 θ | 불가 | 두 문서가 독립적으로 "상면만으로는 `unknown`" 이라고 명시 |
| 소엽 굴곡 | 불가 | **정의 없음**, 열린 항목으로만 적혀 있음 |
| 테두리면 위 높이 | 불가 | 1장은 광선 방향 깊이가 무한 — 이미 프로젝트가 규칙으로 정해둠 |
| 잎자루·줄기가 안 보이는 잎의 부착 | 복수 후보 | 계약이 이미 `unassigned` 를 규정. 사람 라벨 경로는 `organ_label_map.csv` 가 없어 막힘 |
| 새 잎의 마디 랭크 | 불가 | MTG 규약: 줄기 위치가 확립되지 않으면 `rank = unavailable`, "상면만으로는 항상 그러함" |
| 변화가 생장인가 일주운동인가 | 불가 | **점등 시각이 기록돼 있지 않아** 경과시간이 `unavailable` |

기울기·삽입각·굴곡 세 항목은 **데이터가 아니라 정의가 없어서** 막혀 있습니다. 사양서에서 임의
정의를 만들지 않았습니다.

덧붙여, `tomato3d/synth/leafarea.py::fit_correction` 은 모델 **형태**
(`평탄종횡비/투영종횡비 = a + b·sin(카메라 고도)`, leafarea.py:420)만 갖고 있고 **적합된 계수가
디스크에 없습니다**. 보정에 쓸 수 없고, 나중에 적합할 대상일 뿐입니다.

---

## 4. 지금 돌리면 어떻게 되는가 (중요)

규약을 지킨 구현을 오늘 그대로 돌리면 **물리 단위 값이 하나도 나오지 않습니다**:
화분 테두리 지름이 없어 `scale_status = unavailable` → mm 값 금지, 후보 생성 금지.
나오는 것은 px² 면적, 트랙 상태, 연결 가능한 부분의 구조, 그리고 "왜 비었는지" 목록입니다.

이건 결함이 아니라 **요청서 §4의 "스케일 없으면 물리 단위 보고 금지" 를 지킨 결과**입니다.
바꾸려면 §6의 블로킹 결정 1번(테두리 지름 실측)이 먼저입니다.

---

## 5. 기존 코드 재사용

| 대상 | 실제 내용 | 판정 |
|---|---|---|
| `tomato3d/graph/{nodes,connectivity,skeleton,keypoints}.py` | 빈 스텁, 각 `NotImplementedError` 3개 | **재사용 불가** — 구현이 없음 |
| `tomato3d/track/link.py`, `organ/*`, `pheno/measure.py` | 빈 스텁 | **재사용 불가** |
| `tomato3d/io/schemas.py`, `io/tables.py` | 프로젝트의 스키마·CSV 계약(`UNAVAILABLE` 센티넬, 엄격 모델) | **그대로 재사용** — 모든 표에 쓸 것 |
| `tomato3d/io/images.py` | 한글 경로에서 동작하는 이미지 IO | **그대로 재사용, 필수** (통과기준 12) |
| `tomato3d/synth/leafarea.py` | `rectify`(인쇄 격자에서 실측 스케일), `fit_correction`(형태만) | **부분 재사용** — `rectify` 만. 보정은 계수가 없어 적용 금지 |
| `tomato3d/synth/structure.py`, `compound_leaf.py`, `leaflet_surface.py` | 생성기 구조·표면 매개화. 모든 범위가 `user_assumed`, 사실성 관문 C6 미통과 | **후보 생성 전용** — 측정값으로 쓰면 안 됨 |
| `tomato3d/calib/{board,pose}.py` | 보드 프레임·PnP. `sheet_to_board_mm` 이 유일한 변환기 | 보드 촬영에 **그대로 재사용**. 두 번째 변환기 작성 금지 |
| `tools/plant_structure.py` (739행) | 기존 식물 구조 조립 코드 | **새로 쓰기 전에 Codex가 중복 여부 판정** (tools/ 는 Codex 소유) |
| `tools/leaf_area_geometry.py::view_geometry` 등 | 뷰별 기하, 소엽 연쇄 매칭, 교차뷰 후보 | 재사용 가능, Codex 소유 |

핵심: **구조·추적용으로 만들어 둔 `tomato3d` 패키지는 전부 빈 스텁**이라 2단계가 기댈 구현이
없습니다. 실제 재사용은 `io`·`calib`·`synth`(생성 전용) 쪽에서만 나옵니다. Codex는 `tomato3d` 를
import만 할 수 있으니, 수정이 필요하면 `handoff/LOG.md` 에 요청으로 남겨야 합니다.

---

## 6. 사람 결정이 필요한 항목

**블로킹** — 해결되기 전에는 물리 단위 값이 나오지 않습니다.

| # | 결정할 것 | 왜 |
|---|---|---|
| 1 | 화분 종류별 **테두리 내경 실측값**(캘리퍼) → `config/` 에 기재 | 유일한 스케일 근거. 지금 전 개체 스케일 없음 |
| 2 | **하루 점등 시각** — 지금부터 기록 | 경과시간 없이는 생장과 일주운동을 분리 못 함. **과거 촬영분은 소급 불가** |
| 3 | 잎자루 삽입각 · 소엽 표면 기울기 · 소엽 굴곡의 **정의**(기준면·기준축·부호) | 세 값은 측정 실패가 아니라 정의 부재로 비어 있음 |
| 4 | `area_basis` — 초록 화소만인가 외곽 전체인가 | 면적 재현성의 전제 |

**비블로킹** — 해당 산출물을 신뢰하기 전에 필요합니다.

5. `capture_id` 문법과 `plant_id` 허용 문자(현재 `capture_id` 는 8개 표의 열인데 문법이 없음)
6. `manual_events.csv` / `organ_label_map.csv` 를 만들 것인지와 열 구성
7. 개체별 `rank_reference_capture_id`
8. `frame` 토큰 어휘, 그리고 `config/capture_config.json` 좌표가 어느 프레임인지 선언

---

## 7. 추가 촬영 — 필수 / 선택

| 관측 | 무엇이 풀리는가 | 구분 |
|---|---|---|
| 화분 테두리 내경 캘리퍼 실측 (1회/화분종류) | mm² 전부, 후보 생성 전부 | **필수** |
| 점등 시각 기록 (매일) | 생장 vs 일주운동 분리 | **필수**(지금부터) |
| 측면 사진 + 상대 포즈 해 (복엽별) | θ, 삽입각, 기울기, 높이 | 정의가 생긴 뒤 **필수** |
| 소엽 평탄화 기준 사진(인쇄 격자 위) | 실제 표면적 | 실제 면적이 필요하면 **필수** |
| 파괴 측정 / 캘리퍼 (해체 복엽) | 길이·폭·면적·부착 실체 검증 | 선택(검증용). 프로토콜·스키마는 있고 **측정 행은 아직 없음** |
| 보드 없는 3D (Q2) | 높이·면적·부착 | 선택(검증용). 결과 파일 디스크에 없음 |
| 가림이 걷힌 뒤의 재촬영 | 가림 보완 후보 축소 | 선택 — `candidate_reassessment.csv` 로 이미 설계돼 있음 |

---

## 8. 계약 문제 판정 (a–e + 신규 f·g)

영어 계약 §11에 "제안 + 이유 + 영향 필드 + 결정 주체" 표로 있습니다. 요약:

- **a** — §7은 *트랙 신원·상태*의 유일 출처. **대응 신뢰도는 존재하지 않음** → 마진 열 신설 제안.
- **b** — 보드 없는 촬영에서 "정합 불필요" 전제가 깨짐 → 그 금지를 **삭제가 아니라 보드 촬영으로
  범위 축소**, `frame` 토큰 행마다 필수, 촬영별 등록은 `frame_transforms.csv` 에 그대로 둠.
  두 프레임 사이 변환은 **디스크 자료로 복원 불가** → 만들지 않음.
- **c** — `top_position` 은 `Literal["T0".."T4"]` 하드 열거이고 상면에 값이 없으면 **예외를 던집니다**
  → 보드 없는 촬영은 `session_manifest.json` 을 요구하지 않고 `captures.csv` 를 키로. 기존 검증기
  건드리지 않음.
- **d** — ID 세 체계, 문법은 `session_id` 만 있고 `_` 분해가 모호(`plant_id` 에 `-` 가능).
  **통합하지 말고 대응표**. `session_id` 는 오른쪽부터 파싱.
- **e** — `time_since_lights_on_min` 은 열은 있지만 **값의 출처가 없음** → 열은 필수,
  `unavailable` 허용, `captured_at` 이나 `session_id` 꼬리에서 유도 금지.
- **f (신규)** — `manual_events.csv`·`organ_label_map.csv` 부재로 `removal_confirmed` 와 사람 라벨이
  **구조적으로 도달 불가**. 대체 경로를 만들지 않음.
- **g (신규)** — 각도 3종의 정의 부재(§3 참조).

---

## 9. 금지 사항 준수 확인

- 근거 없는 형상·각도 기본값으로 빈칸 채우기: **하지 않았습니다.** 비는 값은 전부 `unavailable` +
  막힌 이유로 남겼습니다. 생성기 범위는 모두 `user_assumed` 이므로 후보 전용임을 명시했습니다.
- 코드 구현: **하지 않았습니다.**
- `config/`·`data/records/`·`docs/`·`tools/`·`phynotype2/` 수정: **하지 않았습니다.** 산출물은
  `handoff/` 두 파일뿐입니다.
- 상면 중심 목표: 측면·깊이는 검증·보조 근거로만 적었습니다.
