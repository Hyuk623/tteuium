# 예측 계층 수정 B1–B6 — 실행 보고 (2026-10-12, 한국어 설명)

작성: Claude Code(예측 세션). 영어 원본: `handoff/FORECAST_FIXES_EXECUTION_2026-10-11.md`(숫자·명령은 그쪽이 기준).
안내서 갱신: `tools/MICROTOM_FORECAST.md`의 "Fixes of 2026-10-11/12".
편집 범위: `tools/microtom_*`, `tools/tests/test_microtom_*`, 이 보고, `flow/flow_map.csv`, LOG만. Codex 소유 `vtc_development*`·`vtc_growth_bridge.py`·
`tomato_fsp_*`·`fsp_extensions*`, 다른 세션의 `tomato3d/state`·`tomato3d/cli/run_p1.py`·`tests/`, 그리고 `config/`·`data/records/`·`docs/`·원본 vtc-main은 손대지 않았습니다.
이전 `build/forecast_20261011_01/_02`는 해시 검증으로 변경 없음 확인.

## 항목별 결과

| 항목 | 상태 | 내용 |
|---|---|---|
| **B1** 파이프라인 경유 | **완료** | `--engine pipeline`(경로 `p1_pipeline`): 멤버마다 Codex 공개 함수 `tomato_fsp_acceptance.scenario_fixture`로 시나리오를 만들고 멤버 매개변수를 `parameters`에 기록(파이프라인 시나리오가 이미 `parameters` 블록을 받으므로 새 훅 요청 불필요) → `tomato_fsp_pipeline.prepare_run` → `run`(체크포인트 커밋). 결과는 `native_inputs/initial_state.csv`와 `committed/step_NNNN/{state.csv, development_events.csv, checkpoint.json}`에서만 읽고, 커밋 파일 해시와 `native_advance_count == 1`을 확인하며 `advance_interval`은 절대 호출하지 않음(테스트가 호출 시 실패하도록 패치). manifest에 `instance_ids`, 멤버별 `checkpoints`(checkpoint.json sha256), `state_advance_authority`, `engine_scope = multi_instance_canopy_placement` 기록. `--engine v3_direct`(종자·픽스처 경로)는 유지하고 `single_plant_no_canopy`로 표시, `canopy_shading` 미해결 행 추가. |
| **B2** 4.8M 기본값 | **완료** | 기본 rays 4,800,000, `issue_class = quantitative`; 더 적으면 `--rays N --diagnostic` 필수 → manifest에 `issue_class = diagnostic`, `quantitative_light_sampling = false`. 종자 경로를 4.8M으로 재발행: `build/forecast_20261012_02`. |
| **B3** 실제로 퍼지는 앙상블 | **완료** | `microtom_parameters.thermal_schedule`가 V3의 열적 발생 규칙을 재현하고, `eligibility()`가 실제 입력 상태(종자 카운터 / 원본 실행의 정단 카운터 / P1 `plant_initialization`)에서 후보별로 돌려 "지평 안에서 일정이나 새 복엽의 쌍 수를 바꾸는" 후보만 추첨. 무효 행은 이유와 함께 `eligibility.json`·`manifest.ensemble.excluded_parameters`에 명시. 불확실성이 선언되지 않은 행(`TRUSS_INTERVAL`, `PHYLLOCHRON` 등)은 `no_declared_uncertainty`로 보고하고 절대 추첨하지 않음(범위 발명 없음). 적격 행이 없으면 멤버 1개, `ensemble_spread = none`. |
| **B4** 규칙 출력과 시나리오 퍼짐 분리 | **완료** | `forecast_events.csv`에 `probability_basis` 열 추가: `rule_deterministic`(모든 멤버가 지배 매개변수 SP_STOP_RULE·CADENCE·FIRST_LEAVES·PHYLLOCHRON_DD·GERMINATION_DD·BASE_C·EMERGENCE_DAYS(+소엽·엽축 발생은 PAIRS)를 공유), `scenario_fraction`(다름), `unavailable`. 그 외 이름 변경 없음. |
| **B5** 파종일 입력 | **완료** | `--sowing-datetime`(aware ISO) → `sowing_source = user_stated`; 개체 레지스트리의 `파종일`/`sowing_datetime` 열(읽기 전용) → `plant_registry_user_record`(오늘은 열이 없어 미사용, 개체목록에는 이식일만 있음); 종자 경로 기본값은 그대로 두되 `assumed_issue_minus_days_at_start`로 표시; 그 밖에는 `unavailable`. `days_after_sowing`도 같이 따라감. |
| **B6** H1–H3 자동 활성화 | **완료(의도적으로 게이트)** | `resolve_engine_capabilities`가 실행 시 `vtc_development_io.PARAMS`(현재 36개, 훅 3개 키 광고됨)와 엔진 파일 해시를 읽음. Codex의 LOG 공지(2026-10-11: "PARAMS 포함만으로 자동 활성화 금지… 소유자 RESULT까지 보류")에 따라, 활성화 조건은 키 존재 + 값이 unavailable 아님 + Codex의 `fsp_extensions.hook_settings` 계약 통과 + 명시적 `--enable-hooks`. 오늘: CURVE_RATIO → `contract_unmet`(정확한 마디 수 벡터 또는 PAIRS 수마다 `by_segment_count` 필요; Chen 1:2:2는 3마디용이고 절단 가정 금지 → 사람이 매핑 선언 필요), BENT_FRACTION → `value_unavailable`, AREA_CORRECTION → `activation_deferred`(`--enable-hooks`면 활성, 회계 전용, `area_basis = summed_one_sided_full_outline_lamina_m2`, 광학 형상에는 적용 안 함). 결정·이유·엔진 해시는 `manifest.engine_capabilities`에 기록. |

LOG 훅 요청: 새로 없음. H1–H3는 이제 존재하며, CURVE_RATIO에는 사람이 선언한 `by_segment_count` 매핑이, 셋 모두에는 소유자의 최종 RESULT가 `--enable-hooks` 사용 전에 필요합니다.

## 명령과 종료 코드

| 명령 | 종료 | 결과 |
|---|---|---|
| `python -X utf8 -m tools.microtom_parameters capabilities` / `--enable-hooks` | 0 / 0 | 위 결정; `--enable-hooks`면 AREA_CORRECTION만 `activated_by_capability_check` |
| `… microtom_forecast issue --scenario scenario_p1_pipeline.json --date 20261012`(1차) | 1 | `build/forecast_20261012_01`: 멤버 m01에서 V3 `unresolved native token`으로 **실패** — Codex가 `vtc_development*`를 저장하던 시각(15:46–15:49)과 겹침. `FAILED.json`만 있고 manifest 없음 → 예측이 아님. fail-closed 증거로 남김 |
| `… issue --scenario scenario_seed_route_4p8M.json --date 20261012` | 0 | **`build/forecast_20261012_02`**(종자, 4.8M, quantitative), 3분 27초 |
| `… issue --scenario scenario_p1_pipeline.json --date 20261012`(재시도) | 0 | **`build/forecast_20261012_03`**(P1 파이프라인, 4.8M, quantitative), 14분 49초(P1 동결·prepare가 대부분; 네이티브 71.0/26.8/41.3/49.7 s) |
| `pytest tools/tests/test_microtom_*.py -q`(5개 파일) | 0 | **43 통과**(42개 142 s + 파이프라인 경로 테스트는 같은 일시적 토큰 오류로 1회 실패 뒤 재실행 통과 167 s) |
| `pytest tools/tests -q`(전체) | 0 | **1746 통과, 1 건너뜀**(950.8 s; Codex가 동시에 추가한 확장 테스트 포함, 기존 테스트 상태 변화 없음) |
| `python -X utf8 flow/check_flow.py --md` | 0 | 경로 없음 0건 |

## 발행한 예측(둘 다 `assumption_conditioned` / `evaluated_unaccepted`, 4.8M rays, `quantitative_light_sampling = true`)

| | `forecast_20261012_02` — 종자 경로, v3_direct | `forecast_20261012_03` — P1 파이프라인 경로 |
|---|---|---|
| 입력 | 동결 종자 입력; `start_time` 2026-09-12 06:00(+09:00) = 발행일 − 30일; `sowing_source = assumed_issue_minus_days_at_start` | `build/p1_state_20261011_01`, `state_source = fixture_truth`(배치된 4개체 fx_om0, fx_om0#2, fx_om1, fx_sp0; 합성 픽스처, 사진 복원 아님); `start_time`은 패키지 촬영 시각; `sowing_source = unavailable` |
| 적격성 | FINAL_VEG_PHYT_NUM·NR_LEAFLET_PAIRS_BY_RANK·MIDDLE_PAIR_RAMP 적격; 활성 6행은 `no_declared_uncertainty`로 제외 | NR_LEAFLET_PAIRS_BY_RANK·MIDDLE_PAIR_RAMP 적격; FINAL_VEG_PHYT_NUM은 `inert`(7잎 + 3일: 어느 후보여도 8번째 잎이 발생) |
| 멤버 | 4: (8,[1,1,3],0.35) (9,[1,1,3],0) (9,[1,1,2],0) (9,[1,1,2],0.35); 네이티브 31.7/35.0/53.5/50.5 s(44구간) | 4: ([1,1,2],0.35) ([1,1,3],0.35) ([1,1,3],0) ([1,1,3],0); 멤버마다 커밋 체크포인트 3개 |
| 퍼짐 | `present`: 3,006행 중 2,298행 차이 | `present`: 2,385행 중 110행 차이 — 새로 발생한 복엽의 소엽·엽축만(쌍 수·램프); 개체 합계는 멤버 간 동일 |
| probability_basis | 모두 `scenario_fraction` — 지배 매개변수 FIRST_LEAVES가 멤버 간 다르므로 이 집합에서는 규칙 결정적 사건이 없음 | `apex_stop`·`new_truss`·`new_compound`·`new_internode` → `rule_deterministic`; `organ_initiation:Leaflet/RachisSegment` → `scenario_fraction`(PAIRS 다름) |
| 마지막 지평의 개체 합계 | 44일차: 복엽 12 [11, 12], 화방 4, 줄기 121.0 [113.2, 123.1] mm, 건물 1.272 [1.206, 1.329] gDM | fx_om0 +3일: 복엽 7(가져온 6 + +2일에 발생 1, p = 1.0), 화방 0, 줄기 78.6 mm, 건물 0.895 gDM, 멤버 간 동일; `days_after_sowing = unavailable` |
| 체크포인트 | —(v3_direct) | 멤버마다 checkpoint.json sha256 3개, `native_advance_count = 1`; `manifest.checkpoints`·`members.csv`에 기록 |

B4 열은 B3의 정직한 결과를 보여줍니다: FIRST_LEAVES를 변동시키면 정단 정지 시각은 공유 규칙이 아니라 시나리오 비율이 됩니다.

## 생장 정확도

변경 없음: **평가 불가(not testable)**. 같은 개체의 반복 관측·점등 시각·PPFD 계측·파종 기록이 없습니다. 어느 결과도 검증된 Micro-Tom 예측이 아니며,
파이프라인 경로의 입력은 진실표를 통해 읽은 합성 P1 픽스처입니다.

## 소유자에게 전하는 관찰

- 훅 키 3개는 광고되지만 `vtc_development.parameters()`에는 없음; 이 계층은 `--enable-hooks`와 계약 통과 시에만 활성 선택 키를 요청에 추가합니다. 훅을 켜고 발행한 예측은 없습니다.
- Codex의 `vtc_development*` 동시 편집(15:46–15:49)으로 두 실행에서 일시적 `unresolved native token`이 발생했고, 둘 다 실패로 기록(`FAILED.json`, 테스트 재실행)했으며 재라벨링하지 않았습니다.
- P1 픽스처 개체(7잎, 490.55 °Cd)는 3일 지평에서 어느 FIRST_LEAVES 후보로도 복엽 1개를 발생시키므로 그 사전값은 무효이고, 해부 기반 3쌍 후보와 램프가 변동을 만듭니다.
