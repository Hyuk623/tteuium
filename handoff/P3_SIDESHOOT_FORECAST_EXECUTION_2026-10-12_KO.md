# P3 — 축·화방·세그먼트 인식 예측: 실행 보고 (V3 프롬프트, 2026-10-12, 한국어 설명)

작성: Claude Code. 영어 원본: `handoff/P3_SIDESHOOT_FORECAST_EXECUTION_2026-10-12.md`(숫자·명령은 그쪽이 기준). 커버리지 맵(코드보다 먼저):
`handoff/P3_SIDESHOOT_COVERAGE_2026-10-12.md`. 안내서: `tools/MICROTOM_FORECAST.md`의 "P3 V3". V2 프롬프트는 실행하지 않았습니다.

**한 줄 요약.** 예측 계층(`tools/microtom_*`)만 고쳐 구현·테스트했고, 현재 화방 픽스처 패키지에서 축 인식 예측 1건을 4.8M rays로 발행했습니다.
엔진·`tomato3d/`·`config/`·`data/records/`·`docs/`는 손대지 않았습니다. 결과는 **형식 검증일 뿐 실제 식물 검증이 아닙니다**: 엔진은 실제 P1 패키지로 돌아간 적이 없고
(Codex의 본 경로 시도는 잎 기하 결손으로 중단, 성공 실행은 픽스처의 `fixture_truth` 경로), 실사진 척도도 아직 닫히지 않아(117건 중 0건) 실제 예측에 mm 값을 담을 수 없습니다.

## 1. 적용한 범위 결정
- **선언된 축만.** 곁순 축은 절대 새로 만들지 않음(엔진이 미선언 축을 거부; 계층은 `topology_scope = provided_axes`, `completeness = unavailable`을 기록; 테스트: 곁순 없는 패키지 → S 행 0개, 표시).
- **선언된 축 위에서 엔진의 조건부 프로그램이 만든 화방은 허용**(사용자 관찰 `user_stated`), 항상 `generated_truss`로 표시. P1 레지스트리 화방은 `registry_truss`. 둘은 어떤 산출에서도 섞이지 않음(테스트).
- 적용 가능성 관찰(`SUBSTEM_TRUSS_APPLICABILITY`, user_stated)과 프로그램 플래그(`APPLY_DETERMINATE_STOP`, user_assumed)는 별도 레지스트리 행으로 출처를 분리.
- 축별 화방 간격은 **차단**(엔진이 CADENCE 하나를 공유; 계약 확장 필요, 소유자 Codex) — 레지스트리 행 `AXIS_CADENCE_PER_AXIS = blocked_engine_extension`, LOG 훅 요청 **H4**; 멤버 추첨으로 꾸며내지 않음.

## 2. 조용히 결과를 망칠 수 있는 두 이름 충돌의 처리
| 충돌 | 처리 | 테스트 |
|---|---|---|
| `parent_rank`: 축 행에서는 주경 부착 잎 랭크, 화방 행에서는 그 화방이 달린 축에서 바로 아래 잎 랭크 | `microtom_axes.read_axis_tables`가 모호한 키를 제거하고 `axil_parent_rank`(축) / `truss_above_rank`(화방)로 분리; `axis_attachment_rank()`는 화방 행을, `truss_above_rank()`는 축 행을 거부; 예측 표에는 `axil_parent_rank`만 | S1 부착 2, S2 부착 5; F0001은 M 위 랭크 4, F0002는 S1 위 랭크 3; 교차 읽기는 예외 |
| 기관의 불변 `segment_index` vs 축의 현재 카운터 | `organ_segment_index`(state/organ_inventory)와 `axis_segment_index`(커밋된 axis_inventory.csv) 두 열을 모든 MTG 행에 기록; `manifest.axis_columns`에 정의 | side_stop: S1 기관은 1–4, 축 카운터는 생성 화방 뒤 5 |

## 3. 작업 항목별
| 항목 | 상태 | 내용 |
|---|---|---|
| F1 레지스트리 | 완료(+차단 1) | `SUBSTEM_SINK_SCALE` 1.0 user_assumed, `APPLY_DETERMINATE_STOP` true user_assumed(프로그램), `SUBSTEM_TRUSS_APPLICABILITY` user_stated(관찰, 계층 전용), `TRUSS_INTERVAL`에 "축 간 공유" 표기, `AXIS_CADENCE_PER_AXIS` 차단(H4). 새 engine_status `axis`, `blocked_engine_extension`; 축 행은 엔진 소유자의 `fsp_axes.validate_records`로 검사 |
| F2 입력 상태 | 완료 | `microtom_axes.build_axis_records`: 생산자 값 그대로(축 정점 id, order, stage, 부착 노드, `segment_index`, `truss_count`), 등록 잎 = 그 축의 가장 낮은 랭크 2장, 숨은 카운터는 `user_assumed`(시계 식 명시; `apex_stopped=false`는 공급된 가정); 엔진 소유자의 공개 `select_axes`가 검증하고 `truss_history`·`truss_rule_status`를 채움. `segment_index`는 절대 유도하지 않음: 생산자 값 `unavailable`이면 그대로 두고 그 축은 `truss_rule_status = unavailable`(테스트). 화방 기하 보조: 영점 부기점(`zero_extent_bookkeeping_point_casts_no_shadow; not an observed truss location`) |
| F3 앙상블 | 완료(추첨 대상 없음) | 축마다 자체 카운터로 적격성 판정; `SUBSTEM_SINK_SCALE`은 substem ≥ 1일 때, `APPLY_DETERMINATE_STOP`은 아직 화방을 만들 수 있는 축이 있을 때 구조적으로 적격 — 둘 다 보고하되 선언된 후보 집합이 없어 추첨 제외(`no_declared_uncertainty`; 범위 발명 없음). 패키지 09에서는 `FINAL_VEG_PHYT_NUM` 무효, `NR_LEAFLET_PAIRS_BY_RANK`·`MIDDLE_PAIR_RAMP` 적격 |
| F4 산출 | 완료 | MTG 행에 `axis_id, axil_parent_rank, organ_segment_index, axis_segment_index, developmental_axis_id, truss_provenance`; 축별 구간(`axis_leaf_count, axis_leaf_area_mm2, axis_stem_length_mm, axis_truss_count_generated, axis_truss_count_registry`)과 축별 사건(`new_leaf, new_truss_generated, apex_stop`)에 `probability_basis`(축의 정지 플래그가 지배 집합에 포함)와 `truss_provenance`; `manifest.headline`(조건부: 주경 정지가 살아 있는 곁순을 멈추지 않음); `manifest.axis_sums_check`(축 플럭스 합 = 개체 탄소 장부) |
| F5 평가 | 완료 | `forecast_map.csv`에 `axis`; 관측에 `axis`, `truss_source`; 지표 `substem_leaf_count_error`, `truss_timing_error_days`(`truss_source = registry`일 때만; 생성 화방을 기준으로 삼으면 `unavailable`); 광주기 위상 게이트·누출 검사 유지; 생장 정확도 `not testable` |
| F6 경로 | 완료 | 파이프라인 엔진; `v3_direct`는 단일 개체로 표시 |
| F7 예측 | 완료 | `build/forecast_20261012_04`(`build/p1_state_20261012_09`, `p1_manifest.schema_revision` 5 확인, `fixture_truth`, 4.8M rays) — 5절 |

검증된 기존 파이프라인 실행을 Java 없이 멤버로 소비할 수 있습니다(`--from-results`, 파이프라인 엔진; 커밋 체크포인트만 읽음). 결정론적 테스트는 Codex의 `side_stop`과 레거시 `producer_run_02`를 이렇게 사용합니다.

## 4. 명령과 종료 코드
| 명령 | 종료 | 결과 |
|---|---|---|
| `python -X utf8 -m tools.microtom_parameters validate` | 0 | 26행: axis 2, blocked_engine_extension 1, layer_only 2 |
| `… microtom_forecast issue … --from-results build/fsp_truss_20261012_acceptance_04/side_stop`(시험) | 0 | 축 모드, S1 +1일 정지, 생성 `Truss4` vs 레지스트리 HT1–3, 축 합계 = 장부(3.5e-18 gC) |
| `… microtom_forecast issue <패키지 09, 100k, diagnostic, 1멤버, 지평 1·2>`(네이티브 시험) | 0 | 1분 12초; M이 +2일에 `Truss2` 생성(`generated_truss`), F0001/F0002 `registry_truss`, S1 +2일 새 잎 |
| `… microtom_forecast issue --scenario build/forecast_scenarios_20261012/scenario_p3_axes_pipeline.json --date 20261012` | 0 | **`build/forecast_20261012_04`**, 8분 45초(멤버별 P1 동결·prepare가 대부분; 네이티브 20.7/58.1/43.7/33.8 s, 각 3구간) |
| `pytest tools/tests/test_microtom_axes.py -q` | 0 | 12 통과(결정론 11 + 네이티브 1) |
| `pytest tools/tests/test_microtom_*.py -q`(6개 파일) | 0 | **55 통과**(323.9 s, 네이티브 2개 포함) |
| `pytest tools/tests -q`(전체) | 0 | **1832 통과, 1 건너뜀**(1014.1 s); 다른 소유자가 같은 시간대에 추가한 P1/P4 테스트 포함, 기존 테스트 상태 변화 없음 |
| `python -X utf8 flow/check_flow.py --md` | 0 | 경로 없음 0건(P4 행 12개 경로 기준 upsert: 삽입 6, 갱신 6) |

## 5. 발행한 예측 `build/forecast_20261012_04`(조건부; `assumption_conditioned` / `evaluated_unaccepted`)
입력: `build/p1_state_20261012_09`, `state_source = fixture_truth`, 촬영 c2(2026-10-13 08:00 +09:00), 개체 `fx_ss0`, 축 M(세그먼트 2, 레지스트리 화방 F0001 랭크 4 위),
S1(substem, 부착 랭크 2, 세그먼트 2, 레지스트리 화방 F0002 자기 랭크 3 위), S2(substem, 부착 랭크 5, 세그먼트 1, 화방 없음). 지평 1/2/3일, 4.8M rays, 앙상블 seed 11.

| | 결과(멤버 4, 모두 `verified`, 멤버마다 커밋 체크포인트 3개, `native_advance_count = 1`) |
|---|---|
| 적격성 | `NR_LEAFLET_PAIRS_BY_RANK`·`MIDDLE_PAIR_RAMP` 적격(지평 안에 새 복엽 발생); `FINAL_VEG_PHYT_NUM` 무효; `SUBSTEM_SINK_SCALE`/`APPLY_DETERMINATE_STOP`은 구조적 적격이나 `no_declared_uncertainty` |
| 멤버 | ([1,1,2], 0.35) ([1,1,3], 0.35) ([1,1,3], 0) ([1,1,3], 0) |
| 퍼짐 | `present`: 965행 중 55행(새 소엽 면적·길이·폭, 엽축 마디, 높이); 축 합계는 멤버 간 동일 |
| 축별 사건 | M: `new_truss_generated` p = 1.0, +2일(`generated_truss`, 세그먼트 2를 닫고 카운터 3), 새 잎 없음, 정지 없음; S1·S2: `new_leaf` p = 1.0, +2일, 화방·정지 없음. 모두 `rule_deterministic`(열적·축별 정지 매개변수를 모든 멤버가 공유; PAIRS·램프만 변동) |
| +3일 축 합계 | M: 잎 6, 잎면적 5377 mm², 줄기 60.2 mm, 레지스트리 1 + 생성 1 화방; S1: 잎 4, 1997 mm², 19.0 mm, 레지스트리 화방 1; S2: 잎 3, 1086 mm², 11.2 mm |
| 화방 출처 | F0001·F0002는 매 경계에서 `registry_truss`; `fx_ss0/Truss2`는 `generated_truss`(기관 세그먼트 2, 이후 축 카운터 3) |
| 검사 | 축 플럭스 합 = 개체 탄소 장부(멤버마다 최대 1.39e-17 gC); 체크포인트 해시 기록; `provided_axes`/`completeness = unavailable`; `sowing_source = unavailable` |

정직하게 덧붙일 것: P1 패키지는 진실표로 읽은 합성 픽스처(사진 복원 아님); 축 시계·질량·`apex_stopped=false`는 선언한 가정; 화방 2개는 영점 부기점(그림자·위치 없음);
모든 축이 같은 공유 `CADENCE`를 따름.

## 6. 차단 항목(소유자)
| 항목 | 이유 | 소유자 |
|---|---|---|
| 축별 cadence(`AXIS_CADENCE_PER_AXIS`) | 엔진이 CADENCE 하나를 공유; fsp-axes-1 계약 확장 필요(훅 H4) | Codex |
| `SUBSTEM_SINK_SCALE`/`APPLY_DETERMINATE_STOP` 추첨 | 선언된 후보 집합 없음; 적격성 기계는 준비됨 | 사람(후보 선언) |
| 실제 식물 예측 | 엔진이 실제 P1 패키지로 돈 적 없음; 본 경로는 잎 기하 결손으로 중단; 실사진 척도 0/117 | P1 소유자 + 사람(화분 테두리 점, Q2) |
| 생장 정확도 | 같은 개체의 반복 관측 없음; 점등 시각은 손으로 조작('내외') | 사람 |

## 7. 테스트(소프트웨어 기준)
축 id와 두 카운터의 입력→요청→산출 왕복; 두 `parent_rank` 의미의 교차 금지(명시적 실패 테스트); 레거시 패키지에서 축 발명 없음; 생성 화방을 레지스트리/관측으로 표시하지 않음;
축별 합계 = 개체 장부(side_stop 최대 3.5e-18 gC); 정지한 축은 `new_leaf`를 내지 않으면서 잎면적은 계속 증가; 재현성(같은 커밋 체크포인트에서 바이트 동일), 불변성, 누출, 출처 없는 기본값 0(기존 B 계층 테스트, 새 열에서도 통과).

## 8. F8(2026-10-12 추가) — `SUBSTEM_SINK_SCALE`를 선언된 시나리오 집합으로: 실행 완료
구현: 레지스트리 행 `uncertainty_kind = scenario_set`, 후보 0.5 / 1.0 / 2.0(low / base / high, base가 기준, `user_assumed`, 사용자 결정 2026-10-12; 품종 우세 계수 없음).
축 인식 파이프라인 경로에서 `issue`는 값마다 예측 1건을 따로 돌리고(각 시나리오 안에서 **같은** 멤버 추첨), 시나리오별로 따로 집계(절대 합치지 않음; 행의 `n_members`는 시나리오 내 멤버 수),
모든 MTG/구간/사건/멤버 행에 `scenario_id`·`scenario_value`를 기록하며, ID는 `F:<run>:<label>:<organ>`으로 시나리오 간 겹치지 않음. `manifest.scenario_set`에 시나리오가 바꾸는 것(S축의 스케일; M·뿌리 1.0)과
멤버가 바꾸는 것을 명시하고 `comparison.low_high_distance`를 담음. `APPLY_DETERMINATE_STOP`는 시나리오 집합 **없음**, true 유지. 레거시 경로·`--from-results`는 base만 발행하고 그렇게 표시.
테스트: `test_f8_*` 3개 — microtom 58 통과; 전체 `tools/tests` **1835 통과, 1 건너뜀**(3806 s, 동시 네이티브 실행으로 느려짐).

같은 패키지(`build/p1_state_20261012_09`, fixture_truth, 4.8M rays, 3 시나리오 x 4 멤버 x 3 구간) 재발행: **`build/forecast_20261012_07`**(75분 48초; 멤버 재시도 0).
`_05`·`_06`은 FAILED 폴더(manifest 없음): 전체 테스트가 `build/`에 쓰는 동안 Windows/OneDrive가 엔진의 원자적 폴더 이름 바꾸기(`.step_0003_partial`->`step_0003`, `publication_partial`->`results`)를 거부함;
네이티브 실행 자체는 검증됨. 세 번째 시도 전에 멤버 단위 재시도(새 폴더에서 재구축, 최대 2회, `manifest.transient_retries`에 기록)를 넣었고 성공 실행에서는 필요하지 않았음. `_04`는 그대로.

**결과 — 세 시나리오가 완전히 같음.** +3일 축별 잎 수/잎면적/줄기(low = base = high): M 6 / 5377 mm2 / 60.2 mm; S1 4 / 1997 mm2 / 19.0 mm; S2 3 / 1086 mm2 / 11.2 mm; 어느 시나리오에도 정단 정지 없음;
모든 양에서 `low_high_distance = 0`. 원인(모든 단계·시나리오의 커밋 `axis_flux.csv`로 확인): 모든 축에서 `allocated_gC == demand_gC` — 엔진의 상한 있는 싱크 가중 배분은 개체 탄소 예산이 모자랄 때만 작동하는데,
이 픽스처에서는 선언된 종자 저장 0.2 gC + 일일 총동화(~0.017 gC)가 3일 지평 내내 일일 수요(1일차 0.154 gC, 이후 < 0.005 gC)보다 큼. **한 문장:** 이 픽스처·지평에서 미측정 싱크 스케일의 가치는 정확히 0(0 mm2, 잎 0장)이며,
탄소 제한 상태(더 작은 선언 저장, 더 큰 수요, 더 긴 지평)를 모사하기 전까지 실측은 아무것도 사 주지 않음 — 이는 픽스처의 선언된 숨은 상태가 만든 한계이고 Micro-Tom에 대한 증거가 아님.
