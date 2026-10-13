# FSP 흐름 지도 — 단계별 프로그램과 만든 주체 (2026-10-11)

전체 흐름:

```
P1 사진·형상 → 캐노피 구성 → P2 광 → P4 생리·배분 → P3 생장·방향 → 새 형상으로 광 재계산 → (다음 시점)
```

번호는 프로젝트 이름이고 실행 순서는 아닙니다. 생리(P4)가 생장·형상 갱신(P3)보다 먼저 옵니다.

## 이 폴더의 파일
| 파일 | 내용 |
|---|---|
| `README.md` | 이 설명 |
| `flow_map.csv` | 단계 · 프로그램 · 경로 · 주체 · 상태 · 메모 (한 줄 = 프로그램 하나). **지도의 원본** |
| `check_flow.py` | `flow_map.csv`의 경로가 실제로 있는지 확인하고 단계별 표를 출력. 프로젝트 코드는 import하거나 실행하지 않음 |
| `FLOW_STATUS.md` | `check_flow.py --md`로 만든 최신 상태표 (자동 생성, 손으로 고치지 않음) |

코드는 이 폴더로 **복사하지 않았습니다.** 실제 코드는 원래 위치(`tomato3d/`, `tools/`)에서 계속 고쳐지기 때문에, 복사본은 바로 낡은 사본이 됩니다. 이 폴더는 경로로 원본을 가리키는 지도입니다.

```bash
cd "C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis"
python -X utf8 flow/check_flow.py --md
```
경로가 하나라도 없으면 끝에 "경로 없음"으로 나오고 종료 코드 1을 냅니다.

## 주체
- **Claude Code**: `tomato3d/`, `tests/` 담당
- **Codex**: `tools/` 담당 (2026-10-11부터 Claude Code도 함께 수정 가능)
- **Claude(채팅)**: 사양서·기록·프롬프트 (코드 없음)

주체는 `handoff/LOG.md` 작성자와 폴더 담당 기준입니다. 여러 번 다뤄진 파일은 주로 만든 쪽을 적었습니다.

## 상태 표기
| 값 | 뜻 |
|---|---|
| executed | 실제로 돌려서 결과가 있음 |
| implemented | 코드는 있음, 실제 데이터 검증은 부족하거나 진단용 |
| partial | 일부만 되거나 일부 스텁 |
| demo_only | 연결 틀과 데모만 |
| in_progress | 다른 주체가 지금 작업 중 (건드리지 않음) |
| spec_only | 사양·프롬프트만, 코드 없음 |
| absent | 없음 |

## 단계별 요약 (P1·P3 원문 유지, Codex P2·P4는 2026-10-13 갱신)
### P1 사진·형상
- 촬영·보정·마스크·스키마(`tomato3d/calib`, `mask`, `io`, `state/schema.py`) — Claude Code, 구현됨. 스키마는 **revision 6**(camera_poses.csv 추가; revision 5의 segment_index·Truss·스케일 규칙명·불확도 포함).
- 화분 테두리 스케일(`tomato3d/state/potscale.py`) — 실행됨. 사용자 캘리퍼 60 mm + 테두리 점 기록으로 **위 사진 13장 mm 확정**(33.2~49.3 µm/px, 1σ 0.2% 안). 남은 스케일 결손 104장(옆·수평) + 광학면 13.
- 합성 생성기·렌더(`tomato3d/synth`) — 실행됨. 상면 N/O + 측면 R.1·R.2 완료(150장면 × 4뷰 = 600장). **화방 생성 코드는 없음** → `truss` 합성 인스턴스 0, 실사진 라벨 13개뿐.
- 라벨 클래스 6개 확정(`handoff/LABEL_CLASS_SCHEMA_2026-10-12.md`): compond_leaf / leaf / leaf2 / shoot / terminal_leaf / truss. 방향 4종은 클래스가 아니라 속성(`direction`). 측면은 복엽만.
- 상면 검출기 `tomato_top_nonboard`(Roboflow -ndul9) — 존재함, 이미지 49, v4 rfdetr-2xlarge valid mAP 0.684(valid·test 각 2장이라 노이즈 큼). **객체검출=박스**이므로 면적은 SAM 필수.
- 잎 추적(`tomato3d/track/link.py`)·구조 갱신(`state/update.py`)·축(`state/axes.py`)·화방(`state/trusses.py`) — 구현·실행됨(합성 경로). 실사진은 상면 마스크·사람 등록부가 없어 `unavailable`.
- 상면→3D(`tomato3d/topview/`) — T0~T3만. 잎 휨 기록이 없어 T2 학습 데이터 게이트가 닫혀 있고 T4(측면 렌더 검증)·T5(P1 패키지)는 차단. 생성기 감사 충돌: 소엽 장폭비 1.19 vs 실측 1.4~1.7.

### 캐노피 구성
- 개체 → 캐노피 좌표 변환·합치기/나누기(`tomato3d/state/canopy.py`, `tools/tomato_fsp_canopy.py`) — 실행됨(왕복 오차 0.0001 mm). 선반 간격·흙 높이는 가정값.
- 화분별 광 비율·배치 기록(`data/records/env_light_20261010/`) — 확정, 비율로만 적용.

### P2 광 — Codex 갱신 2026-10-13
- 실측 PPFD 46점의 제한 보간·설정 해시·위치별 DLI와 독립 소비자 구현. 벽 반사율 적합은 사용자 결정으로 종료하고 실측 광장 경로로 전환했습니다. 조명 배치 변경은 재측정 대상입니다.
- `empirical_growth_boundary` / `empirical_growth_consumer` / `empirical_native_response`: 실제 네이티브 **광 계산 전용 3회**, 방향 시나리오 0.5/0.6/0.7, 공학용 삼각형 잎 45개씩 총 135 잎-구간 전달 오차 0. `external_once`로 한 번만 적용합니다.
- 위 실행은 질량·나이·면적 불변, 총광합성 탄소 0인 진단입니다. 실제 작물 형상, 광학 성질, 공간 등록, NRH 광 기준과 생장 모드는 미검증입니다. 원래 복잡 형상은 연산 한도로 실행하지 않았고, 별도 공학 형상을 사용했습니다.
- 반복 입사와 광자의 탈출·절단 계측은 미완료입니다. 광량 전달 검증을 장면 전체 광자 수지 검증으로 해석하지 않습니다. 경계 및 관련 회귀 86개 통과; 근거 `handoff/P2_EMPIRICAL_GROWTH_BOUNDARY_EXECUTION_2026-10-13.md`.

### P4 생리·배분 — Codex 갱신 2026-10-13
- 기존 V3 탄소·축별 배분은 조건부 실행 상태를 유지합니다. 새 트레이 모듈은 기존 개체별 양분 장부와 별도 경로입니다.
- `nutrient_reservoir` / `nutrient_reservoir_records`: 기록 수신, 용액·배지수·저장 EC 당량, 처방 흡착/방출, 대조 트레이 보정·불확도, 모형 기반 개체 분배를 구현했습니다. EC 당량은 N/P/K 원소 흡수량이 아닙니다.
- `nutrient_reservoir_transaction`: 식별자·시간·재시도·원자적 확정은 **픽스처 검증**입니다. 네이티브 성장 전 자원 제약과 공동 확정은 미구현이며, 생장 피드백은 false입니다. 반응식·계수·초기 상태는 미확정 항목을 그대로 남겼습니다.
- 최종 84개 집중 테스트, 24개 전달 검사·6개 CLI 통과. 기존 모델 회귀는 178 통과/1 실패이며, 해당 B1 재검사가 중단돼 전체 통과로 표시하지 않습니다. 근거 `handoff/P4_NUTRIENT_RESERVOIR_EXECUTION_2026-10-12.md`의 최종 addendum(실행일 10월 13일).

### P3 생장·방향
- 축·화방·세그먼트 인식 예측(`tools/microtom_forecast.py`, `microtom_axes.py`) — 실행됨. 첫 발행본 `build/forecast_20261012_04`(픽스처, 4.8M 광선, 4멤버): M이 Truss2 생성, S1·S2 신엽 +2 d, 축 합계 = 개체 장부(1.4e-17 gC).
- **대기:** F8 — `SUBSTEM_SINK_SCALE`을 시나리오 집합 0.5 / 1.0 / 2.0으로 선언했고, 3시나리오 × N멤버 재발행이 아직 안 됨. 현재 발행본은 1.0 단일 가정.
- 생물학 정확도는 같은 개체의 반복 관측이 없어 `not testable`.

### 새 형상으로 광 재계산
- 구조 내보내기·검수 대조군(`tools/groimp_structure_export.py`, `tomato_fsp_acceptance.py`, `fsp_axes_acceptance.py`) — 구현·실행됨. 축·화방을 포함한 루프는 **픽스처에서만** 확인.
- Codex 훅 H1–H3는 네이티브에 구현·검증됐습니다. H1/H2는 생성 기관에 적용하고 H3는 보고 전용입니다. 가져온 잎의 발달 변형과 H4의 상태는 별도 계약·검증 대상으로 남습니다.

## 끊긴 곳 (1–5는 기존 P1 기록, Codex 항목 6만 2026-10-13 갱신)
1. **엔진이 실제 P1 패키지로 돌아간 적이 없다.** 모든 발행본은 합성 픽스처 경로다.
2. 실사진 스케일: 위 13장만 해소. 옆·수평 104장 남음. `data/records/pots/pot_spec.csv`가 아직 EXAMPLE 행이라 확인 필요.
3. 사람 기록 3종 미작성 — `data/records/leaf_bend`(휨 보정·T2 게이트), `data/records/side_shoots`(상면에서 parent_rank의 유일한 출처), `data/records/trusses`(관측 화방). 전부 템플릿만 있다.
4. 상면→3D 학습 모델 없음. 게다가 생성기 소엽 장폭비가 실측과 충돌해 합성 3D 진실을 그대로 믿을 수 없다.
5. 화방 합성 데이터 0건 → `truss`는 실사진 라벨 13개로만 학습 가능.
6. Codex 갱신(2026-10-13): 실측 광장·위치별 DLI와 네이티브 광 계산 전용 전달은 구현됐지만 실제 형상/공간 등록·광학 성질·생장 광 기준은 미확정입니다. 트레이 수지는 구현됐지만 생장 반응식과 실제 네이티브 양분 제약은 비활성입니다. 전체 실물 생육 예측 완료를 뜻하지 않습니다.

## 갱신 방법
프로그램이 새로 생기거나 상태가 바뀌면 `flow_map.csv` 한 줄만 고치고 `check_flow.py --md`를 다시 돌립니다.
