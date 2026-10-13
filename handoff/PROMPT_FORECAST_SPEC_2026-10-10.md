# 설계 요청 — 3단계 "미래 구조와 생장 예측" 과학 검토 + Codex 사양 (2026-10-10, 검토 반영본)

현재 관측된 왜성토마토(**Micro-Tom**) 구조에서 출발해 기존 잎의 생장과 새 잎·화방·곁가지 발생을 예측하는 모델을 검토·설계해줘.
**지금은 구현하지 말고**, 설계·과학적 검토와 Codex 구현 사양까지만.

전체 흐름: ① 잎 개체별 추적 → ② 현재 구조 갱신 → **③ 미래 구조와 생장 예측(이번 범위)**.

## 0. 먼저 읽을 것 (읽은 파일 목록을 산출물 첫머리에)
프로젝트: `C:/Users/sho36/OneDrive/작업물저장소/홈팜/Tomato 3D phenotyping analysis`
1. 부모 공통규약(`홈팜/` 아래, 프로젝트 폴더 밖 — 실제 경로 확인, 못 읽으면 그렇다고 적기), `CONVENTIONS.md`(소유권: `tools/`·`phynotype2/` = Codex, `tomato3d/`·`tests/` = Claude Code, `config/`·`data/records/`·`docs/` = 사람), `handoff/LOG.md` 최근 30줄.
2. **입력 계약**
   - 1단계: `handoff/CLAUDE_CODE_PROMPT_STAGE1_2026-09-15.md`(좌표계·단위·`unavailable`), `handoff/CODEX_PROMPT_PHYNOTYPE2_COMPOUND_TERMINAL_TRACKING_2026-10-10.md` §7(기관 ID·신뢰도·트랙 상태·출현/소실 이벤트).
   - 2단계: **아직 사양이 없음.** 요청서 `handoff/PROMPT_STRUCTURE_UPDATE_SPEC_2026-10-10.md`와 구조 형식 `handoff/MTG_CONVENTION_2026-10-10.md` + 수정안 `handoff/CLAUDE_CODE_CLI_PROMPT_MTG_AMEND_2026-10-10.md`를 기준으로 **가정한 입력 계약**을 명시하고, 2단계 사양이 나오면 대조할 항목을 표로 남길 것.
3. **기존 계산기 (소스 확인 필수, 파일:함수 근거와 함께)**
   - `tools/compound_growth.py` + `tools/COMPOUND_MODEL.md`: `forecast_persistence`, `forecast_recent_change`(→ 기준선으로 재사용 후보), `forecast`, `evaluate_compound_forecasts`, `validate_history`.
   - `tools/probabilistic_compound_growth.py` + `tools/PROBABILISTIC_COMPOUND_GROWTH.md`: `determinate_beta`, residual-to-next-event 대기시간, `stop_logit`, `truss_rule`(`first_truss_rank_pmf`, `interval_leaves`), `topology_scope = provided_axes`.
   - `handoff/CODEX_PROBABILISTIC_COMPOUND_GROWTH_SPEC_2026-10-03.md` 116행: "첫 버전은 관측되지 않은 곁가지 축의 발생을 예측하지 않음" → **현재 코드에서도 그런지 확인**(grep 결과 인용).
   - 광·탄소 연결: `tools/light_growth_bridge.py`, `light_growth_consumer.py`, `LIGHT_GROWTH_BRIDGE.md`, `canopy_light.py`, `HIERARCHICAL_LIGHT.md`, `tools/fsp_carbon_diagnostic.py`, `FSP_CARBON_DIAGNOSTIC.md`, `GROWTH_CALIBRATION.md`, `growth_calibration.py`, `groimp_structure_export.py`, `tomato3d/light/`. **어느 연결이 실제 구현·실행됐고 어느 것이 스키마/데모뿐인지** 표로.
4. 근거·기록 (프로젝트 docs는 claude.ai 프로젝트에도 있음)
   - diaf024 상세(`논문상세_Butturini_diaf024`), Micro-Tom 문헌 확인(`논문확인_MicroTom_2026-10-10`), 재배환경·광분포(`data/records/env_light_20261010/`), 개체·기관 기록 엑셀(`data/records/plant_registry/`), 복엽 휨 타입(`docs/복엽구조_형태_2026-10-10.md`, `data/records/compound_bend_types_20261010/`).

## 1. 반드시 반영할 사실 (근거 있음)
- **diaf024의 품종은 Micro-Tom이 아님**('Heartbreakers F1 Twiggy Red', 22/19 °C, 16 h, CO₂ 800 ppm, 고밀도). 그래서 diaf024 계수는 전부 **"다른 품종·다른 조건의 사전값"**이다. 특히 다음은 보편 법칙으로 쓰지 말 것:
  - 측지 발생 랭크 1·2·7, 분지각 30°, 엽서각 137°, 잎 경사 70° 고정, 주경 마디 상한 10, 측지 마디 상한 4, 화방 랭크 6–10, 화방당 8과.
  - 재사용 후보(검증 필요)로만: 기관 beta 생장(T_base 5.7 °C), 광합성·호흡·버퍼·sink 배분의 **식 구조**.
  - ψ 42.4 °Cd는 **과실 출현 지연**이지 엽 출현 간격(phyllochron)이 아님.
- **Micro-Tom 품종 정보(Carvalho 2011, 다른 조건: 온실 평균 28 °C, 11.5–13 h)**: 유한생장(sp) — 화방 두 개가 연속으로 나오면 주경 생장이 끝남, 첫 화방은 9번 잎 위가 가장 흔함, 잎은 보통 소엽 5장(1·2번 잎은 3장). 우리 10/10 해체 복엽은 1차 소엽 7장 → 랭크별 실측으로 판단할 것. **주경 끝이 멈추는 사건(stop)과 화방 발생을 모델에 넣을 것.** 절간 길이는 d/mnt 유전 상한이 있어 자원의 단순 증가 함수로 두지 말 것(Martí 2006).
- **환경·빛**: 26/22 °C, RH 60 %, 14/10 h(설정값, 로그 아님) → 열시간 18.6 °Cd/일(T_base 5.7 가정). **절대 PPFD 없음** — 화분별 광 비율(0.92–1.24, 앱 측정·비율 전용)만 있음. 그래서 탄소 기반 생장은 기준 PPFD를 가정한 **조건부 시뮬레이션**으로만 표시하고, 측정기 값이 들어오면 교체.
- **잎은 하루 주기로 움직임** — 점등 후 경과 시간이 다른 촬영 사이의 각도·투영면적 변화를 생장이나 굴성으로 외삽하지 말 것(같은 위상끼리 비교).
- 다른 품종 6개체: 예측 대상 아님, 광 계산의 그늘 이웃(식물 단위 MTG)으로만.
- 광 계산에는 **소엽 단위 면**만 — 복엽 외곽 포락면을 불투명 면으로 쓰지 말 것.

## 2. 설계할 내용
1. 2단계 현재 상태를 출발점으로. 발아일부터 재생성 금지, 확정 기관 ID·부착 관계 변경 금지.
2. 구분: 기존 기관의 연속 변화(면적·길이 증가, 펼쳐짐, 방향·굴곡 변화) / 이산 사건(새 마디·복엽·화방 발생, 주경 정지, 곁가지 발생, 낙엽).
3. 각 예측에 필요한 관측·환경·품종 정보와 **식별 가능한 매개변수**. 한 시점 사진으로 생장 속도·발생 간격을 안다고 가정하지 말 것 — 최소 몇 시점·몇 개체가 필요한지 명시.
4. 새 기관의 발생 시점·부착 위치·방향을 분포로 예측. **예측 기관 ID는 관측 ID와 다른 이름공간**(예: `forecast_id` 아래 별도 하위 MTG, MTG §7의 생성 후보 규칙과 같은 방식). 관측이 들어와도 예측 ID를 관측 ID로 바꾸지 말고 대응표로 연결.
5. diaf024 규칙(적산온도·기관 발생·탄소 배분)과 Micro-Tom/우리 조건에서 따로 보정해야 하는 계수를 분리한 표: 식, 변수, 단위, 출처, 적용 한계, 현재 값의 `source_kind`(measured / literature_other_cultivar / user_assumed / unavailable).
6. 방향: ① 고정 각도 생성 ② 관측된 방향 변화의 외삽 ③ 빛·중력 반응(굴광성·굴중성) — 셋을 구분. ③은 근거·데이터가 없으면 별도 연구 과제로 남기고 기본값으로 채우지 말 것.
7. 미래 구조 → 광 흡수 → 탄소 배분 → 생장 → 다음 구조 연결 계약 검토. 현재 계산기에 없는 연결을 구현된 것으로 취급하지 말 것(§0-3 표 근거).
8. 후속 사진이 들어오면 예측–관측 비교 후 갱신. **이전 예측은 덮어쓰지 않고 보존**(예측 발행 시각·입력 스냅샷 해시 기록), 평가에 미래 관측이 새지 않도록 rolling-origin 방식.
9. 곁가지: 현재 코드 범위(`provided_axes`) 확인 결과를 근거로, 관측되지 않은 곁가지 축의 발생을 이번 범위에 넣을지 판단 — 넣는다면 발생 확률만(위치·방향은 분포/모름), 넣지 않는다면 `topology_scope` 표시와 완전성 `unavailable`.

## 3. 산출물
- (한국어) 설명·과학 검토: 기존 계산기 유지·수정·추가 항목, 최소 실행 가능 모델(MVP), 필요한 시계열 데이터와 보정 절차, 근거가 부족한 항목 목록.
- (영어) 구현 계약 `handoff/CODEX_FORECAST_SPEC_2026-10-10.md` (+ 한국어판 `..._KO.md`, `docs/`는 사람 소유라 handoff에 둠):
  - 입력: 2단계 상태 스냅샷, 환경 시나리오, **예측 기간(horizon) 목록**.
  - 출력: 날짜별 구조(별도 forecast MTG), 발생 이벤트·확률·예측구간, 각 값의 근거·`source_kind`, 조건부 시뮬레이션 여부 플래그.
  - 기준선 비교: 현 상태 유지(persistence)·최근 변화율 외삽(recent change) — 기존 함수 재사용 여부 포함.
  - 독립 검증: 발생 시점·개수·부착 위치·방향·면적 및 예측구간 적중률(coverage). 근거: 이후 촬영(같은 광주기 위상), 개체·기관 기록 엑셀, 파괴 측정, 측면 사진. 예측에 쓰인 개체/기간과 검증용을 분리.
  - Codex 지시: 우선순위별, 파일 경로(`tools/` 또는 `phynotype2/`), 함수, 입출력, 단위, 통과 기준.
- **소프트웨어 테스트 통과**(재현성, ID 비충돌, 이전 예측 보존, 미래 정보 누설 0건, 근거 없는 기본값 0건)와 **실제 생장 예측 정확도**(관측 시계열이 쌓여야만 판정 가능)를 분리해서 적을 것. 자료가 없으면 "검증되지 않은 조건부 시뮬레이션"으로 표시.

## 4. 금지
- 코드 구현, `config/`·`data/records/` 수정, 다른 담당 파일 직접 수정(필요하면 `handoff/LOG.md`에 요청).
- 근거 없는 형상·각도·속도 기본값으로 빈칸 채우기, 생성기 범위(`user_assumed`)를 측정값처럼 쓰기.
- diaf024 수치를 Micro-Tom 측정값처럼 쓰기.
