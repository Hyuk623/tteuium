# P3 F9 — F8 시나리오가 왜 같았는지, 무엇을 했는지: 실행 보고 (2026-10-13)

작성: Claude Code. 작업 지시: `handoff/CLAUDE_CODE_CLI_PROMPT_P3_F9_CARBON_LIMIT_2026-10-13.md`. 영문 원본: `P3_F9_CARBON_LIMIT_EXECUTION_2026-10-13.md`(수치·표의 기준).

**한 줄 상태.** F8 결과는 그대로 두고 그 원인을 레지스트리의 가정으로 기록했다. 별도 스트레스 픽스처(`stress_20261013_01`, 네이티브 12건, 4,800,000 광선,
소프트웨어 검증 전용, 모든 산출에 `reuse_as_prediction = forbidden`)로 배분 상한이 처음으로 작동했고 계약 검사를 전부 통과했다. 예비 탄소 스윕으로 모델의 임계값을
찾았다(**약 0.1420 gC 아래에서 상한이 물린다; 선언값 0.2 gC에서는 8일 지평에서도 물리지 않는다**). 본 픽스처와 `build/forecast_20261012_04`·`_07`은 그대로다.
여기의 어떤 수치도 예측이나 실측이 아니다.

## 0. 출발점(유지)
F8의 세 시나리오가 완전히 같았던 원인: 모든 단계에서 `allocated_gC == demand_gC`. 1일차 예산 `reserve_start + gross - maintenance` = 0.2 + 0.0118 - 0.0002 = 0.2115 gC가
수요 0.1536 gC를 넘어 상한 가중 배분의 '물리는' 분기가 한 번도 실행되지 않았다(F8 base 멤버로 재확인, 테스트 포함). 이 픽스처에서는 "SUBSTEM_SINK_SCALE이 중요한가"를 **물을 수 없다**.

## 1. 사용자 결정 적용(2026-10-13)
1. 본 픽스처는 **조정하지 않음**. 엔진 소유 픽스처의 `reserve_gC = 0.2`는 그대로(매 스트레스 편집 전에 확인: `checks.main_fixture_unchanged`), `_04`·`_07`의 멤버 `scenario.json`도 0.2이고 스트레스 표식이 없음(테스트).
2. 소프트웨어 검증 전용 스트레스 픽스처는 별도(§2).
3. 진짜 판정은 실측 광을 기다림(§4).
4. 양분 피드백은 범위 밖: `ENABLE_NUTRIENT_FEEDBACK` false, 두 번째 시나리오 집합 없음.

## 2. G1 — 배분 상한을 작동시키는 스트레스 픽스처
`tools/microtom_stress.py`가 같은 엔진·같은 P1 패키지(`build/p1_state_20261012_09`, `fixture_truth`)·같은 공개 파이프라인 함수(`prepare_run` → `run`, 커밋 체크포인트만, `advance_interval` 미호출)를 쓰되,
**이 모듈의 자체 엔진 시나리오 JSON**에서 `plant_initialization.reserve_gC`만 **0.1 gC(`source_kind = fixture_declared`)**로 바꾼다(픽스처의 0.2 대체). 나머지는 모두 고정(기관 숨은 상태, 기후 설정값,
램프, 가정 PPFD 300, 4.8M 광선, 광 시드 11, 레지스트리 선언값, `APPLY_DETERMINATE_STOP = true`). 멤버 추첨 없음. 세 실행: low 0.5 / base 1.0 / high 2.0.
예비 탄소는 엔진 쪽(acceptance 픽스처)에서 선언되지만 엔진 **입력 필드**이므로 엔진 코드를 고치지 않았고 훅이 꼭 필요하진 않았다. 편의용 훅(`scenario_fixture(..., plant_reserve_gC=)`)만 LOG에 H5(낮은 우선순위)로 적어 둠.

**검사**(모두 커밋된 `carbon_ledger.csv`·`organ_allocations.csv`·`axis_flux.csv`·`state.csv`에서 계산; manifest `checks`):

| check (P4 resource contract §2) | result | evidence |
|---|---|---|
| the cap binds | pass | first binding step 1, funded fraction 0.7263 |
| demand-proportional under the cap (base) | pass | max cross-organ allocation/demand spread 1.1e-16 |
| native allocation = independent oracle (organ level, per-axis scale) | pass | max abs diff 1.6e-17 gC over every case/step |
| budget law funded = min(max(0, reserve+gross-maint), demand) | pass | max abs diff 4.2e-17 gC |
| SUBSTEM_SINK_SCALE shifts the split in the declared direction | pass | S: low < base < high; M: low > base > high at step 1 (table below) |
| carbon closure | pass | max abs residual 4.9e-17 gC, max deficit 0.0 |
| per-axis sums = plant ledger | pass | max abs diff 9.7e-17 gC; axis_flux vs organ sums 0.0e+00 |
| main fixture unchanged | pass | engine fixture reserve before edit {'fx_ss0': 0.2} = registry 0.2 |
| no-reuse mark in every frozen engine scenario | pass | `initialization_provenance` → native `plants.csv` |

**첫 물림 단계의 배분 분할**(개체 `fx_ss0`; 상한이 총량을 고정하고 스케일이 분할만 움직임):

| scenario (SUBSTEM_SINK_SCALE) | step | M allocated gC | S allocated gC (S1+S2) | funded total gC |
|---|---|---|---|---|
| low (0.5) | 1 | 0.08764 | 0.02389 | 0.11153 |
| base (1.0) | 1 | 0.07218 | 0.03935 | 0.11153 |
| high (2.0) | 1 | 0.05736 | 0.05417 | 0.11153 |

**마지막 단계의 축별 잎 수/면적, 세 시나리오 나란히**(분할 이동이 기관까지 닿는다는 소프트웨어 증거):

| axis | low: leaves / area mm2 | base: leaves / area mm2 | high: leaves / area mm2 |
|---|---|---|---|
| M | 6 / 5324.8 | 6 / 5160.1 | 6 / 5031.5 |
| S1 | 4 / 1780.8 | 4 / 1897.8 | 4 / 1984.7 |
| S2 | 3 / 959.2 | 3 / 1023.1 | 3 / 1074.8 |

**이 수치는 어떤 것의 예측도 아니다.** 예비 탄소를 상한이 물리도록 골랐으므로 예측으로 인용할 수 없고, 헤드라인·구간·시나리오 범위를 여기서 끌어내지 않는다. 강제 장치: 폴더는 `build/stress_*`(절대 `forecast_*` 아님);
모든 행과 manifest에 `reuse_as_prediction = forbidden`; 표식이 엔진 시나리오의 `initialization_provenance`→네이티브 `plants.csv`까지 기록; `microtom_forecast`는 표식이 있는 실행을 `--from-results` 멤버로 거부(테스트);
`verify_forecast`/`evaluate`는 폴더를 거부(테스트); `finalize_stress`는 `headline`이 있는 manifest를 거부(테스트).

## 3. G2 — 지배 가정 기록, 임계값은 찾되 채택하지 않음
**레지스트리.** `PLANT_RESERVE_GC` = 0.2 gC, `user_assumed`, `engine_status = hidden_state`, 출처 `tools/tomato_fsp_acceptance.py::scenario_fixture`: 종자/개체 탄소 예비는 한 번도 측정된 적 없고, 이 숫자 하나가 상한이 물릴지를 결정한다.
모든 예측 manifest가 `hidden_state_passed_through`에 이를 기록. `RESERVE_CAP_THRESHOLD_GC` = 0.14203 gC, `source_kind = model_property`, `layer_only`, "채택하지 않음" 명시.

**스윕**(base 시나리오, 나머지 고정, 4,800,000 광선, 3구간, `fixture_declared` 예비값; `sweep_summary.json`):

| reserve_gC (fixture_declared) | cap binds? | first binding step | funded fraction at step 1 |
|---|---|---|---|
| 0.0500 | yes | 1 | 0.4007 |
| 0.1000 | yes | 1 | 0.7263 |
| 0.1200 | yes | 1 | 0.8566 |
| 0.1400 | yes | 1 | 0.9868 |
| 0.1415 | yes | 1 | 0.9966 |
| 0.1425 | no | None | 1.0000 |
| 0.1500 | no | None | 1.0000 |
| 0.1700 | no | None | 1.0000 |
| 0.2000 | no | None | 1.0000 |

1일차 해석식(`vtc_development_native.rgg`): `reserve_start < demand_1 - gross_1 + maintenance_1` = **0.14203 gC**일 때 물림(모든 스윕 실행에서 동일, 편차 0.0e+00 gC).
스윕이 이를 괄호로 잡음: 0.1415에서 물리고 0.1425에서 안 물림; 예비값에 단조: True.
**문장:** 상한은 약 0.1420 gC 아래에서 물린다; 선언값 0.2 gC에서는 물리지 않는다. 이는 픽스처의 수입 수요·가정 PPFD·램프에 조건부인 모델 성질이며(실측 광이 오면 움직임), 예비값으로 채택하지 않는다.

**지평(별도)**(`horizon.json`; base, **선언값** 0.2 gC, 8구간): the cap never binds through day 8 at the declared reserve. 예비 궤적:

| day | reserve start gC | demand gC | gross gC | reserve end gC |
|---|---|---|---|---|
| 1 | 0.2000 | 0.1536 | 0.0118 | 0.0580 |
| 2 | 0.0580 | 0.0049 | 0.0169 | 0.0695 |
| 3 | 0.0695 | 0.0073 | 0.0169 | 0.0788 |
| 4 | 0.0788 | 0.0083 | 0.0169 | 0.0870 |
| 5 | 0.0870 | 0.0146 | 0.0169 | 0.0888 |
| 6 | 0.0888 | 0.0197 | 0.0173 | 0.0859 |
| 7 | 0.0859 | 0.0287 | 0.0183 | 0.0751 |
| 8 | 0.0751 | 0.0379 | 0.0201 | 0.0569 |

궤적은 단조가 아니다: 예비는 5일 뒤 0.0888 gC로 최고점을 찍고 6일부터 줄어든다(새 잎의 수요가 총동화보다 빨리 늘어남; 8일 수요 0.0379 vs 총동화 0.0201 gC). 따라서 "물리지 않음"은 8일까지만 확인된 것이고, 더 긴 지평에서 선언값이 물리는지는 열려 있으며 실행하지 않았다(물리도록 지평을 고르지 않음).

## 4. G3 — 재실행 조건(기록만; 기다리지 않음)
`tools/microtom_forecast.RERUN_TRIGGERS` + 모든 예측 manifest의 `rerun_trigger`(주장한 트리거 + 세 조건; CLI `--rerun-trigger`). 하나라도 참이 되면 본 픽스처에서 재발행하고 manifest에 어느 것인지 적는다:
1. **measured_light_landed** — `tools/reference_dli.py`가 보정된 광장(`handoff/CODEX_CLI_PROMPT_P2_LAMP_CALIBRATION_2026-10-13.md`, `data/records/env_20261013/`)을 받으면 탄소 제한은 **결과로** 나타나거나 나타나지 않음(그늘 점이 노출의 ~21 %라 그럴듯하지만 그럴듯함은 결과가 아님).
2. **real_p1_package** — 엔진은 아직 실제 식물 기하로 돈 적이 없음.
3. **nutrient_feedback_enabled** — `f_nut`가 총동화에 곱해지면 스스로 제한 상태를 만들 수 있음(오늘은 범위 밖).
재실행마다 `base`가 기준이고 `low_high_distance`를 헤드라인 옆에 보고(F8과 같음).

## 5. 수용 기준(§5)
- 스트레스 픽스처가 상한을 물리고 세 시나리오가 선언 방향으로 갈라짐 — **예**(§2 표; `all_checks_passed = True`).
- 폐쇄·축별 합 유지 — 예(잔차 ≤ 4.9e-17 gC; 모든 케이스에서 축 합 = 개체 원장).
- 재사용 금지 표식 테스트 — 예(멤버 거부, 예측 검증기/평가기의 폴더 거부, 동결 엔진 시나리오·네이티브 `plants.csv`의 표식).
- 임계값 스윕 재현 가능 — 예(§5 영문의 명령; `verify stress_20261013_01`).
- 본 픽스처 선언값 불변 — 예(diff: 매 편집 전 엔진 픽스처 예비 = 0.2; `_04`/`_07` 멤버 시나리오 0.2; 레지스트리 0.2).
- 테스트: microtom set 71 passed (1100 s, native included); full tools/tests 1879 passed / 1 skipped (1582 s).

## 6. 파일
작성/변경: `tools/microtom_stress.py`(신규), `tools/microtom_parameters.py`(+`.csv`: `PLANT_RESERVE_GC`, `RESERVE_CAP_THRESHOLD_GC`; 어휘 `hidden_state`·`fixture_declared`·`model_property`), `tools/microtom_forecast.py`(스트레스용 `scenario_edit` 훅, 표식 실행 거부, `RERUN_TRIGGERS`/`rerun_trigger`),
`tools/microtom_forecast_io.py`(`NO_REUSE_MARK`), `tools/tests/test_microtom_stress.py`(신규), `tools/MICROTOM_FORECAST.md`, 이 보고(+EN), `flow/flow_map.csv`, `handoff/LOG.md`. 건드리지 않음: Codex 소유 파일 전부, `tomato3d/`, `config/`, `data/records/`, `docs/`, `build/forecast_20261012_04`, `_07`.
네이티브 12건, 네이티브 총 499 s, 일시 재시도 0회, GroIMP ['2.2.1'], Java ['openjdk version "21.0.12.1" 2026-08-18 LTS'].

## 7. 이 보고가 말하지 않는 것
식물에 대한 결과는 없다: 스트레스 예비값은 선언된 숫자이고, 임계값은 가정 광과 픽스처의 수입 기관 상태에 조건부이며, 엔진은 아직 실제 기하로 돈 적이 없다(`real_plant_verified = false`). 시나리오 집합은 본 픽스처에서 G3 트리거가 켜질 때까지 선언된 채 비활성이다.
