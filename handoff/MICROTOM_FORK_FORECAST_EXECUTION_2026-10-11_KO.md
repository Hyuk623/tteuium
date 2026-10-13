# Micro-Tom 포크 잔여분 + 3단계 예측 계층 — 실행 보고 (2026-10-11, 한국어 설명)

작성: Claude Code. 영어 원본: `handoff/MICROTOM_FORK_FORECAST_EXECUTION_2026-10-11.md` (숫자·명령은 그쪽이 기준).
커버리지 맵(코드보다 먼저 작성): `handoff/MICROTOM_FORK_FORECAST_COVERAGE_2026-10-11.md`. 사용 안내: `tools/MICROTOM_FORECAST.md`.

**한 줄 요약.** 소프트웨어 구현과 테스트는 끝났고, V3 엔진을 실제로 돌려 조건부 예측 두 건을 발행했습니다.
생물학적 검증은 **없음**, 생장 정확도는 같은 개체의 촬영일이 3회 이상 쌓이기 전까지 **평가 불가(not testable)** 입니다.
어떤 결과도 "검증된 Micro-Tom 생장"이 아닙니다.

## 1. V3가 이미 한 것 / 여기서 만든 것

- **V3가 이미 구현(다시 만들지 않음):** 두 화방 연속 뒤 정지, 첫 화방 전 9잎, 화방 간격 매개변수, 잎 순서별 소엽쌍 표, 가운데 쌍 크기 램프,
  평면 full_outline 소엽, 기부→끝 소엽각 기울기, 파종 후 30일 스핀업과 65일 지속, 램프 장면, 광비율 포인터 동결, 16셀 가상 센서,
  출처가 찍힌 매개변수 파일, 소엽별 면(복엽 봉투 없음).
- **여기서 만든 것:** Micro-Tom 매개변수 레지스트리(`tools/microtom_parameters.csv`, 모든 행에 source_kind, measured 없음)와 V3 요청 JSON 매핑,
  기후 설정값 CSV(`user_stated`), DLI 유도(PPFD × 3600 × 광주기 / 1e6, 14 h이면 0.0504배), 포인터 해석과 해시 기록, 16셀 RMSE·피어슨 r 검증,
  그리고 3단계 전체 — 앙상블, 예측 전용 ID 이름공간(`F:<run>:<organ>`), 1회 기록 폴더 `build/forecast_<날짜>_<nn>`,
  가정표·미해결표, 추가 전용 대응표(`forecast_map.csv`), 롤링 오리진 평가, 기준선 전제조건 6개, 후보 모형 등록.
- **V3 파일 수정으로 막힌 것(훅 요청만):** `CURVE_RATIO`(Chen 1:2:2; V3는 3쌍일 때 1:2:2를 코드에 고정), `BENT_FRACTION`(측정값 없음 → unavailable),
  `AREA_CORRECTION`(1.0 표시만). 세 항목은 모든 예측 manifest에 `inactive_in_engine`으로 기록됩니다.
- **사람 입력이 없어 막힌 것:** 마디 길이 상한(캘리퍼 없음 → V3의 12 mm 가정 유지, 72 mm는 절대 안 씀), 화방 간격 값, 파종일, 점등 시각,
  굽은형 비율, 절대 PPFD.

편집한 파일은 `flow/flow_map.csv`(2행 갱신, 6행 추가)와 `handoff/LOG.md`(추가)뿐입니다. `vtc_development*`, `vtc_growth_bridge.py`, `tomato_fsp_*`,
`config/`, `data/records/`, `docs/`, 원본 `Downloads/vtc-main`은 손대지 않았습니다.

## 2. 실행한 명령과 종료 코드

| 명령 | 종료 | 결과 |
|---|---|---|
| `python -X utf8 -m tools.microtom_parameters validate` | 0 | 22행: active 9, inactive_in_engine 3, engine_default_retained 1, layer_only 1, environment 5, candidate 3 |
| `python -X utf8 -m tools.microtom_environment climate …` | 0 | 열량 18.633 °Cd/일(T_base 5.7), DLI 계수 0.0504 |
| `python -X utf8 -m tools.microtom_environment validate-light --sim build/vtc_dev_v3_delivery_sufficient/results/sensors.csv --measured data/records/env_light_20261010/light_ratio_map_20261010.csv …` | 0 | 비율 RMSE 0.1175, r 0.402 — 가정한 점광원과 폰 비율맵의 모양 비교일 뿐 보정 아님 |
| `… microtom_forecast issue --scenario scenario_stage2_fixture.json` | 0 | **`build/forecast_20261011_01`**, 네이티브 4멤버, 3분 09초 |
| `… microtom_forecast issue --scenario scenario_seed_route.json` | 0 | **`build/forecast_20261011_02`**, 네이티브 4멤버, 1분 54초 |
| 첫 네이티브 시험(`--rays 1000`) | 1 | V3가 모든 멤버를 `unfunded obligations; carbon deficit`로 거부(광선이 너무 적어 굶음). 300k rays로 재실행 성공. 실패 폴더는 `FAILED.json`만 남고 manifest가 없음 |
| `pytest tools/tests/test_microtom_*.py` | 0 | **33 통과**(86.7 s, 네이티브 픽스처 경로 1회 포함) |
| `pytest tools/tests` (작업 전 기준선) | 0 | **1675 통과, 1 건너뜀**(624.8 s; 건너뜀은 선택 의존성 openalea.lpy) |
| `pytest tests` (tomato3d, 손대지 않음) | 0 | **331 통과, 1 건너뜀** |
| `python -X utf8 flow/check_flow.py --md` | 0 | 경로 없음 0건 |

새 테스트를 포함한 `tools/tests` 전체 재실행: **1736 통과, 1 건너뜀**(731.6 s). 기준선 + 33보다 많은 것은 같은 시간대에 Codex의 `test_tomato_fsp_pipeline.py`와 다른 세션의 P1 테스트가 추가됐기 때문이며, 기존 테스트의 상태 변화는 없습니다.

## 3. 발행한 예측 두 건 (조건부; `run_status = assumption_conditioned`, `evaluation_status = evaluated_unaccepted`)

공통: GroIMP 2.2.1 / Java 21, 멤버당 300,000 rays(정량 광 주장에는 4.8M 필요 → `quantitative_light_sampling = false`), 기후 26/22 °C 14 h(`user_stated`),
CO₂ 400 ppm(`user_assumed`, V3 생리에 비활성), 기준 PPFD 300(`user_assumed`) → DLI 15.12(조건부), 광비율 포인터는
`data/records/env_light_20261010/plant_slot_light_ratio_20261010.csv`로 동결(비교 전용), 램프는 0.6 m 점광원 가정(`declared_guess`),
지평 1/3/7/14일, 앙상블 4멤버는 레지스트리의 후보 집합에서 추첨(seed 11) — **시나리오 집합이지 보정된 확률이 아님**.
기준선(persistence/recent_change): 전제조건 P1(보드 좌표계)·P2(mm 척도)·P3(동일성 확정)·P4(광주기 위상)·P6(정확한 시각) 미충족으로 차단, P5(구간 없음)는 구조적 한계로 보고.
`topology_scope = provided_axes`, `completeness = unavailable`, 굴광성 `not_modelled`.

| | `forecast_20261011_01` (Stage-2 **픽스처** 경로) | `forecast_20261011_02` (**종자** 경로) |
|---|---|---|
| 입력 스냅샷 | 검증된 V3 65일 실행의 30일차 상태로 만든 Stage-2 형식 픽스처(실제 P1 산출 아님) | 동결된 종자 입력; 파종 2026-09-11 06:00으로 선언해 30일차 = 발행일 |
| 멤버(FIRST_LEAVES / PAIRS / RAMP) | 8/—/0.35, 9/—/0.35, 9/—/0, 9/—/0 (PAIRS는 가져온 식물 구조에 맞춰 [1,1,2] 고정) | 8/[1,1,3]/0.35, 9/[1,1,3]/0, 9/[1,1,2]/0, 9/[1,1,2]/0.35 |
| 앙상블 퍼짐 | **퇴화: 2,474행 중 0행만 멤버 간 차이.** 9잎이 이미 있으면 FIRST_LEAVES가 작용하지 않고, 2쌍 복엽에서는 가운데 램프가 무효(pairWeight=1). 숨기지 않고 보고; 이후 발행의 manifest에는 `ensemble_spread` 필드가 들어감 | 3,006행 중 2,298행이 멤버 간 차이(소엽 면적·길이·폭, 엽축 마디, 마디, 개체 합계) |
| p1, +14일(44일차) | 복엽 12, 화방 4, 줄기 118.9 mm, 구조 건물 1.214 gDM (모든 멤버 동일) | 복엽 12 [11, 12], 화방 4, 줄기 113.6 [106.9, 115.5] mm, 건물 1.078 [1.033, 1.122] gDM |
| p1 사건 | +3일 내 새 화방 p=1.0(첫 발생 +2일); +14일 내 정단 정지 p=1.0(+14일) | +3일 내 새 화방 p=0.75; +3일 내 새 복엽 p=0.25; +14일 내 정단 정지 p=1.0(12–14일) |
| 광주기 위상 | 점등 시각이 기록에 없어 `unavailable` → 실측과의 비교는 모두 `unavailable_diurnal_confound` | 같음 |

멤버별 네이티브 실행: 픽스처 84.4/27.2/24.6/33.2 s(14구간), 종자 42.9/18.0/15.6/18.2 s(44구간); 모두 V3 자체 검증(`validate_outputs`) 통과.

## 4. V3에 요청한 훅 (Codex 소유 파일; LOG에 요청, 구현 안 함)

| 훅 | 정확한 필드/함수 |
|---|---|
| H1 | `vtc_development_io.PARAMS` + `vtc_development_native.rgg::updateGeometry`: 엽축 마디별 `CURVE_RATIO double[]`(정규화), 고정식 `(pair==1?1:2)/(2m-1)` 대체 |
| H2 | `BENT_FRACTION double` + `native.rgg::compound`에서 복엽별 굽은형 추첨 |
| H3 | `vtc_development_observation.derived_tables`에 회계 전용 `AREA_CORRECTION`(광학 형상에는 절대 적용 안 함) |
| 참고 | 16셀 가상 센서·포인터 동결·정지 규칙·소엽표·램프·스핀업·`days_after_sowing`은 V3에 이미 있어 훅 불필요. Codex가 LOG에 올린 `tomato_fsp_pipeline` 훅(P1 경로)은 이 계층이 호출하지 않으며, `advance_interval`로 상태를 두 번 전진시키는 일은 없음 |

## 5. 비활성·유지·unavailable 매개변수

`inactive_in_engine`: CURVE_RATIO, BENT_FRACTION, AREA_CORRECTION. `engine_default_retained`: INTERNODE_CAP(레지스트리는 unavailable, V3는 0.012 m 가정 유지).
레지스트리 밖 V3 매개변수 27개(AMAX/ALPHA/THETA 등 Merlice NRH, SLA, 기관 싱크 곡선)는 V3 출처 그대로 `forecast_assumptions.csv`에 복사.
후보(비활성): CAND_INTERNODE_LOGISTIC(maxlen은 반드시 우리 자료로 적합), CAND_INSERTION_ANGLE_CHEN7, CAND_AZIMUTH_SUCCESSION(Kanahama 범위는 폭으로만, 야생종).
`TRUSS_INTERVAL`은 활성이지만 화방 기록이 없어 퍼짐을 선언하지 않았으므로 추첨 대상이 아님.

## 6. 소프트웨어 통과 기준(사양 §12) — 전부 테스트

재현성(같은 입력 → `issued_at`만 다른 동일 파일; 네이티브는 유효숫자 10자리까지), ID 비충돌(`F:` 접두, 엔진 ID와 분리), 이전 예측 보존(변조 감지·재발행 거부),
미래 정보 누출 0(발행 이후 관측이 입력이면 평가 중단; 이전 입력은 결과를 바꾸지 않음), 출처 없는 기본값 0(모든 엔진 매개변수가 가정표 행에 연결, measured 없음),
범위 정직(`provided_axes`, `completeness = unavailable`), 전제조건 표면화(6개 + file::function), 상태 라벨(`accepted_for_domain` 어디에도 없음),
복엽 봉투 없음, 포인터 재지정 시 동결 비율 파일과 해시만 변경, 광검증 수식 손계산 검증, 기후 CSV 18.63 °Cd/일.

## 7. 생장 정확도

**평가 불가(not testable).** 같은 개체의 반복 기관 관측 0건, 화방 관측 0건, 점등 시각 없음, 절대 PPFD 없음. 평가 도구는 합성 진실로만 시험됨
(`software_check_only_synthetic_truth`). 같은 개체의 촬영일이 3회 이상 쌓이고 `time_since_lights_on_min`이 기록되면,
Stage-2/phynotype2 검토가 만드는 `forecast_map.csv` 연결(ID 개명 금지)을 통해 의미 있는 평가가 됩니다.

## 8. 내가 둔 가정과 사양의 빈틈

- 종자 경로 기본 파종 시각 = 발행일 − 30일 06:00(+09:00). 실제 파종일은 미기록(파종일 열 요청 유지). 사양에 이 경로의 `start_time` 정의가 없었음.
- 설정값에는 MTG A1.2의 `user_stated`를 씀(작업 지시의 5개 어휘에 "선언된 설정값"이 없음).
- 픽스처 경로에서는 PAIRS를 추첨에서 제외: V3 `validate_outputs`가 모든 복엽을 멤버의 PAIRS로 검사하므로 2쌍 식물에 3쌍 멤버를 넣으면 거부됨.
- 시뮬레이션 값의 `source_kind`는 `user_assumed`(가정 매개변수에 조건부). 사양에 "모형 출력" 라벨이 없음.
- 독립 관측 평가는 발행 기준 시각이 과거여야 함; 합성 진실은 시나리오 시계로 평가 가능(`leakage`에 `synthetic_clock` 기록).
- 픽스처 앙상블이 퇴화함(3절). 가운데 램프 후보는 3쌍 이상 복엽에서만 의미가 있고, 퍼짐을 만드는 것은 해부 후보 `[1,1,3]`임.
- 센서 높이(`GRID_Z`)는 V3 매개변수로 남아 있고 미기록 표시.

## 9. 아직 필요한 사람 입력 (변경 없음, 대체하지 않음)

개체별 파종일; 점등 시각(CR-6); `light_input.csv`용 PPFD 계측값; 마디 캘리퍼(상한); 화방 시트 행(간격, FINAL_VEG_PHYT_NUM); C3/소엽 시트(순서별 쌍 수, 쌍 크기);
굽은형 비율; 18슬롯의 `plant_id`; 좌표계 게이트 결정(CR-2); `manual_events.csv`/`organ_label_map.csv` 또는 탈리 범위 제외 선언(CR-5); VTC 라이선스(그때까지 로컬 전용).
