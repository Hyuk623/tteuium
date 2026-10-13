# 흐름 상태 (자동 생성: flow/check_flow.py)

## P1 사진·형상

| 프로그램 | 경로 | 주체 | 상태 | 파일 | 수정일 | 메모 |
|---|---|---|---|---|---|---|
| 1단계 마스크 | `tomato3d/mask` | Claude Code | 구현됨 | OK | 2026-09-16 | scale_block_nominal_height_mm 필요 |
| 1단계 입출력·스키마 | `tomato3d/io` | Claude Code | 구현됨 | OK | 2026-10-02 | unavailable 규칙, poses.csv, quality.json |
| 1단계 촬영·보정 | `tomato3d/calib` | Claude Code | 구현됨 | OK | 2026-09-29 | 스케일 블록 높이 미측정이라 실루엣·mm 미출력 (전체 tests 443 통과, 2026-10-12) |
| 2단계 구조 갱신(MTG 스냅샷) | `tomato3d/state/update.py` | Claude Code | 구현됨 | OK | 2026-10-12 | 사양: handoff/CODEX_STRUCTURE_UPDATE_SPEC_2026-10-10.md; 합성 경로 실행, 실사진 unavailable |
| Declared axis producer adapter | `tools/fsp_axes.py` | Codex | 실행됨 | OK | 2026-10-12 | A4/A5 multiscale parent and exact axil binding; actual P1 fixture consumed; explicit aliases reject disagreement |
| Explicit observation intake | `tools/fsp_observation_intake.py` | Codex | 일부 | OK | 2026-10-13 | Observed/conditional/observation-only routes; current real audit has 117 scale gaps and 13 optical-surface gaps; no truth substitution |
| Frozen P1 native initialization | `tools/tomato_fsp_io.py` | Codex | 실행됨 | OK | 2026-10-13 | Freeze trusses.csv; explicit geometry supplement for unlocated Truss; actual P1 fixture_truth route |
| MTG 기준(A1·A2·§13) | `handoff/MTG_CONVENTION_2026-10-10.md` | Claude(채팅) + Claude Code | 사양만 | OK | 2026-10-12 | 구조 형식 계약; §14 A3(옆 뷰 규칙), §15 A4(곁가지), §16 A5(화방 Truss 정점·segment_index·번호/동시 출현 규칙 확정·2차 곁순 S1.1 표기 예약) 2026-10-12 |
| P1 CLI(inventory·prepare·run·collect·compare·replay) | `tomato3d/cli/run_p1.py` | Claude Code | 실행됨 | OK | 2026-10-12 | 부분 실행은 종료코드 3; side-validate, prepare --capture-tz 추가 |
| P1 곁가지 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_P1_SIDESHOOT_2026-10-12.md` | Claude(채팅) | 실행됨 | OK | 2026-10-12 | 결과: handoff/P1_SIDESHOOT_EXECUTION_2026-10-12.md(+_KO) |
| P1 곁가지 합성 패키지 | `build/p1_state_20261012_03` | Claude Code | 실행됨 | OK | 2026-10-12 | S1 substem(3잎)·S2 axis_shoot→substem(2잎); 등록 쌍 C0010·C0011, 출현 (c0,c1]; 오연결 0; Codex fixture_ready=true |
| P1 구현 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_P1_PHOTO_GEOMETRY_2026-10-11.md` | Claude(채팅) | 실행됨 | OK | 2026-10-11 | 결과: handoff/P1_EXECUTION_2026-10-11.md(+_KO), P1_INVENTORY_2026-10-11.md |
| P1 생성기 단서(생성기 기준 수치 목록) | `handoff/P1_GENERATOR_CAVEAT_2026-10-12.md` | Claude Code | 실행됨 | OK | 2026-10-12 | 소엽 L/W 1.19 vs 실측 1.4–1.7, 복엽 6–8 vs 4–5; 합성 광학면·가림 보완·추적 지표는 생성기 기준, A3 옆 각도는 미검증 |
| P1 수정 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_P1_FIXES_2026-10-11.md` | Claude(채팅) | 실행됨 | OK | 2026-10-11 | 결과: handoff/P1_FIXES_EXECUTION_2026-10-11.md(+_KO) |
| P1 스키마·검증기 | `tomato3d/state/schema.py` | Claude Code | 구현됨 | OK | 2026-10-13 | p1_state_v1 revision 6: segment_index·Truss·trusses.csv(4), 스케일 규칙명·sd·교차확인·평면(5), camera_poses.csv·세로축 스케일(6); 실사진 mm는 화분별 테두리·불확도 필수; 이전 헤더도 통과 |
| P1 실사진 점검 패키지 | `build/p1_state_20261011_02` | Claude Code | 일부 | OK | 2026-10-11 | 117장 등록; 시간대 미진술 상태의 기록 (현행은 _03, 2026-10-12) |
| P1 실사진 점검 패키지(A5 코드) | `build/p1_state_20261012_06` | Claude Code | 일부 | OK | 2026-10-12 | 화방 등록부 없음 → segment_index unavailable — T6 코드로 stale, 현행은 _10 |
| P1 실사진 점검 패키지(시간대 반영) | `build/p1_state_20261011_03` | Claude Code | 일부 | OK | 2026-10-12 | capture_tz=Asia/Seoul(사용자 진술 2026-10-12); Codex 결손 247→130(시간 결손 0); 스케일·마스크·plant_id·점등시각 여전히 없음 |
| P1 실사진 점검 패키지(현행 코드) | `build/p1_state_20261012_04` | Claude Code | 일부 | OK | 2026-10-12 | 시간대 Asia/Seoul; 곁가지 등록부 없음 → 축은 M만 (현행 코드 기준은 _06) |
| P1 실사진 점검 패키지(현행) | `build/p1_state_20261012_10` | Claude Code | 일부 | OK | 2026-10-12 | 스케일 결손 117 중 0 해소(화분 기록 전) — 현행은 _11 |
| P1 실사진 점검 패키지(화분 스케일, revision 6) | `build/p1_state_20261012_14` | Claude Code | 일부 | OK | 2026-10-12 | _20261013_01이 대체(같은 값 + 기준 평면 명시). 위 13장 스케일·camera_poses 65행; 결손 104(옆 52·수평 52) |
| P1 옆 사진 테두리·자세 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_P1_SIDE_RIM_POSE_2026-10-12.md` | Claude(채팅) | 사양만 | OK | 2026-10-12 | Y1 점 찍기 도구 옆 사진 52장 확장, Y2 초점거리 기준으로 12% 자체점검 해결, Y3 옆 사진 스케일·자세(결손 104 중 최대 52), Y4 자세표만(Q2 미구현), Y5 생성기 감사 단서 P1 보고서 명시, Y6 재감사 — 미실행 |
| P1 합성 패키지 | `build/p1_state_20261011_01` | Claude Code | 실행됨 | OK | 2026-10-11 | 인스턴스 5·시점 3; 재실행 61파일 동일 (이후 코드 변경으로 stale — 현행은 build/p1_state_20261012_02) |
| P1 합성 패키지(현행) | `build/p1_state_20261012_02` | Claude Code | 실행됨 | OK | 2026-10-12 | A3 측면 뷰 선택·생성기 후보 반영; 재실행 동일; Codex fixture_ready=true |
| P1 화방 합성 패키지 | `build/p1_state_20261012_05` | Claude Code | 실행됨 | OK | 2026-10-12 | M 화방(4번 잎 위)·S1 화방(c2); M 5·6번 잎 segment 2; 재실행 54파일 동일 — T6 코드로 stale, 현행은 _09 |
| P1 화방 합성 패키지(revision 6) | `build/p1_state_20261012_15` | Claude Code | 실행됨 | OK | 2026-10-12 | _20261013_02가 대체(revision 7 코드). 화방 합성: M 5·6번 잎 segment 2 |
| P1 화방·segment 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_P1_SEGMENT_TRUSS_2026-10-12.md` | Claude(채팅) | 실행됨 | OK | 2026-10-12 | 결과: handoff/P1_SEGMENT_TRUSS_EXECUTION_2026-10-12.md(+_KO); T1-T5 + T6(화분 테두리 스케일, 사용자 지시로 실행) |
| SAM 마스크 조정 | `tools/sam_mask_tuner.py` | Codex | 구현됨 | OK | 2026-09-19 |  |
| Truss and segment history contract | `tools/fsp_axes_segments.py` | Codex | 실행됨 | OK | 2026-10-12 | No missing index imputation; same-axis node binding; immutable organ segment and current axis counter |
| 개체 작업 흐름 | `tools/instance_workflow.py` | Codex | 구현됨 | OK | 2026-09-29 |  |
| 검출 잎 면적 | `tools/detected_leaf_area.py` | Codex | 구현됨 | OK | 2026-10-04 | 보드 시절 데이터 기준 |
| 곁가지 등록부 템플릿 | `build/side_shoot_registry_template` | Claude Code | 구현됨 | OK | 2026-10-12 | 사람이 data/records/side_shoots/로 복사해 작성; 상면에서 parent_rank의 유일한 출처 |
| 곁가지 등록부(사람 작성) | `(data/records/side_shoots)` | 사람 | 없음 | - |  | 상면에서 parent_rank의 유일한 출처 — 미작성; 템플릿 build/side_shoot_registry_template |
| 곁가지 축 등록·구분(axes.csv·분류) | `tomato3d/state/axes.py` | Claude Code | 실행됨 | OK | 2026-10-12 | 사람 등록부 읽기·검증, 등록일→촬영 매핑, 출현 구간, axis_shoot/substem, shoot/truss 구분; 번호 규칙·동시 출현 규칙은 사용자 확정(2026-10-12, user_stated) |
| 관측 기록 | `tools/observation_records.py` | Codex | 구현됨 | OK | 2026-10-01 |  |
| 관측 수집(사진·사람 라벨·검출 제안) | `tomato3d/state/ingest.py` | Claude Code | 구현됨 | OK | 2026-10-13 | C6 상자는 제안으로만; --capture-tz(사용자 진술 시에만 시간대 부여, DST 모호·없는 시각은 오류) |
| 구조 그래프 | `tomato3d/graph` | Claude Code | 일부 | OK | 2026-09-15 | 일부 스텁 (P1은 tomato3d/state로 구현, graph 미사용) |
| 다중 시점 보완 | `tools/multiview_completion.py` | Codex | 구현됨 | OK | 2026-10-04 | 보드 시절 데이터 기준 |
| 라벨 JSON 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_LABEL_SCHEMA_JSON_2026-10-12.md` | Claude(채팅) | 실행됨 | OK | 2026-10-12 | 결과: handoff/LABEL_CLASS_SCHEMA_2026-10-12.md, tomato3d/synth/labels_json.py, build/labels_json_20261012/top_labels_v1.json |
| 라벨 클래스 결정 기록 | `handoff/LABEL_CLASS_SCHEMA_2026-10-12.md` | Claude Code | 실행됨 | OK | 2026-10-12 | 클래스 6개 확정(compond_leaf/leaf/leaf2/shoot/terminal_leaf/truss), 방향 4종은 속성(direction)으로, 측면은 복엽만 |
| 라벨 클래스 스키마·JSON 내보내기(합성 상면/측면 검증) | `tomato3d/synth/labels_json.py` | Claude Code | 실행됨 | OK | 2026-10-12 | 2026-10-12: 클래스 6개(compond_leaf/leaf/leaf2/shoot/terminal_leaf/truss). 상면 O-mature 15장면 top 30뷰 → build/labels_json_20261012/top_labels_v1.json 986개(leaf2는 I1 3개뿐, truss 0 = 생성기에 화방 없음), 소엽 마스크 재현 0px 차이. 측면 side_labels_compound_v1.json 검증 pass(헤더 classes_absent·counts_as_real_annotation 누락만 보고). 실사진 라벨 없음, 탐지기 미학습 |
| 모바일 기록 폼 제작 프롬프트 | `handoff/CLAUDE_ARTIFACT_PROMPT_MOBILE_RECORD_FORM_2026-10-12.md` | Claude(채팅) | 사양만 | OK | 2026-10-12 | 클라우드 호스팅 폼(아티팩트 + 공유 DB) 사양: 빈칸=unavailable·0 구분, 추가 전용(수정은 supersedes), 고정 어휘(tray_id·axis·event_kind), 오프라인 큐, 내보내기 열 순서 = 저장소 템플릿. CLI로는 실행 불가(아티팩트 발행 필요) — 미실행 |
| 보드 없는 3D(Q2) | `(없음)` | 없음 | 없음 | - |  | 실사진 supported 광학면의 전제; 미구현 |
| 복엽 생성기 numpy 백엔드·fixed= 화이트리스트 | `tomato3d/synth/compound_leaf.py` | Claude Code | 실행됨 | OK | 2026-10-12 | L-Py 없이 동일 결과(저장된 105복엽과 6e-11 mm, L-Py 대비 4e-11 mm); fixed=None 비트 동일 34/34 |
| 상면 검출기 tomato_top_nonboard | `(Roboflow -ndul9/tomato_top_nonboard)` | 사람(라벨링) + Roboflow | 구현됨 | - |  | 2026-10-12 확인: 존재함. 이미지 49, 클래스 compond_leaf 66 / leaf 293 / leaf2 81 / terminal_leaf 67 / truss 13 / shoot 8 (+빈 클래스 tomato-top-nonboard 0). 모델 5개, 최신 v4 rfdetr-2xlarge mAP 68.4%(valid). 실제 사진 held-out 평가는 없음 |
| 상면3D T0 휨 보정 입력(+생성기 감사) | `tomato3d/topview/calibration.py` | Claude Code | 구현됨 | OK | 2026-10-12 | 2026-10-12: data/records/leaf_bend 없음 → BENT_FRACTION unavailable, T2 게이트 닫힘. 생성기 감사: 소엽 장폭비 1.19 vs 실측 1.4–1.7 충돌, 복엽 6–8 vs 4–5 |
| 상면3D T1 실사진 상면 → 복엽·소엽 2-D(v4 박스+SAM, mm) | `tomato3d/topview/measure2d.py` | Claude Code | 실행됨 | OK | 2026-10-12 | 2026-10-12 실사진 연결: 13장 모두 원본 해시·dwt_id 연결, 소엽 444·복엽 67 전부 테두리 평면 mm(과대평가 주석·불확도); SAM은 Kaggle T4(prepare-remote / --masks-from); 화분 귀속 애매 2(dwt_113 이웃) |
| 상면3D T2 상면·측면 마스크 짝 데이터셋 | `tomato3d/synth/pairs.py` | Claude Code | 구현됨 | OK | 2026-10-12 | 위 카메라 = 실측 포즈 13개(193–278 mm, 1–31°, approximate); T0 게이트로 여전히 차단(종료코드 1), 스모크만 not_for_training |
| 상면3D T3 기울기·실면적(장폭비 사전값 기준선) | `tomato3d/topview/geometry.py` | Claude Code | 일부 | OK | 2026-10-12 | 학습 모델 차단(T2 필요). 기준선 합성 753개: 비가림 면적 −1~−4%(개별 16%), 가림 시 보이는 마스크 −38/−85%; 생성기 장폭비 상쇄로 실물 근거 아님. T4·T5 차단 |
| 상면3D 사람 확인 대기 페이지 | `build/topview_confirm_20261012_01` | Claude Code | 일부 | OK | 2026-10-12 | 511개 제안 전부 proposed — 사람 확인 대기 |
| 상면3D 사람 확인 페이지(수락·거부·수정) | `tomato3d/topview/confirm_tool.py` | Claude Code | 구현됨 | OK | 2026-10-12 | build/ 아래 사람 소유 CSV만; data/records/ 쓰기 거부; check로 검증 |
| 상면3D 산출 패키지 | `build/topview_20261012_01` | Claude Code | 일부 | OK | 2026-10-12 | T1 실사진 1장 px 측정 + T2 쌍 마스크 1장면 스모크(not_for_training) + T3 기준선; mm는 테두리 기록 전 unavailable |
| 상면3D 실사진 연결 산출(13장 mm·포즈·마스크) | `build/topview_20261012_02` | Claude Code | 실행됨 | OK | 2026-10-12 | real_top/ 13장(Kaggle T4 마스크, CPU 3장과 IoU 1.0), v4_split.json(dwt_104·105 train 누수), t2_geometry_measured.json, t2 스모크 |
| 상면3D 실사진 연결 실행 보고(+_KO) | `handoff/TOPVIEW_REAL_LINK_EXECUTION_2026-10-12.md` | Claude Code | 실행됨 | OK | 2026-10-12 | X0–X5; 차단: 사람 확인, leaf_bend 기록, R.5 |
| 상면3D 실사진 연결·부호 정정 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_TOPVIEW_REAL_LINK_2026-10-12.md` | Claude(채팅) | 사양만 | OK | 2026-10-12 | X0 과대 부호 정정, X1 dwt_113·원본 해시 재연결, X2 위 13장 mm, X3 이웃 개체 구분, X4 복엽 단위 마스크 저장+사람 확인, X5 합성 위 카메라를 실측 분포로 — 미실행(T2는 굽힘 기록 없어 계속 차단) |
| 상면3D 실사진↔화분 기록 연결·카메라 거리 | `tomato3d/topview/reallink.py` | Claude Code | 구현됨 | OK | 2026-10-12 | 원본 HEIC 해시·ispe·회전 확인 못 하면 거부(mm 없음); 테두리 호모그래피+EXIF 초점 → 거리 d·기울기(approximate, P1 Y2/Y4 표가 나오면 대체) |
| 상면3D 인스턴스 마스크 저장·복엽 소속·화분 귀속 | `tomato3d/topview/instances.py` | Claude Code | 구현됨 | OK | 2026-10-12 | PNG+해시 manifest; 소속 = 상자 과반→마스크 과반→애매; 귀속 inside/outside/ambiguous(outside는 이웃 테두리 기록 필요) |
| 상면3D 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_TOP_TO_3D_2026-10-12.md` | Claude(채팅) | 일부 | OK | 2026-10-12 | T0~T3 실행(handoff/TOP_TO_3D_EXECUTION_2026-10-12.md +_KO); T4 측면 렌더 검증·T5 P1 패키지 차단 — 학습 3D 모델 없음, R.5 실사진 측면 라벨 없음 |
| 상면3D↔P1 상호 해소 검토 | `handoff/TOPVIEW_P1_CROSS_BENEFIT_2026-10-12_KO.md` | Claude Code | 실행됨 | OK | 2026-10-12 | 두 세션이 서로 푸는 항목 정리 + 정정 2건: 테두리 스케일 편향은 과대(과소 아님), 실사진 IMG_8419가 원본 해시·개체번호와 미연결. 카메라 19~28 cm·수직에서 중앙 8°(자체점검 최대 12% 오차) |
| 소엽 광학면 내보내기 | `tomato3d/state/optical.py` | Claude Code | 실행됨 | OK | 2026-10-12 | 가림 보완 후보: 생성기(numpy 백엔드+말단 소엽 고정+국소 맞춤) 추가 → 같은 합성 14복엽 중 통과 5→10 (기준 0.98 유지); 실사진은 Q2 없어 unavailable |
| 소엽 분할 | `tools/leaflet_segmenter.py` | Codex + Claude Code | 일부 | OK | 2026-09-30 | 실제 사진 검증 일부 |
| 스케일 기준 평면 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_P1_RIM_INNER_PLANE_2026-10-13.md` | Claude(채팅) | 사양만 | OK | 2026-10-13 | 안쪽 윗변 59 mm·배지 10 mm 아래·테이퍼 없음 기록, 안쪽 선을 1차 기준으로 채택하되 평면이 테두리−10 mm임을 필수 명시(미기재 시 mm 거부), 위 13장 재유도 전후 비교, side_000 13장 유효화·_03 무효, plane_bias 재계산(보정 계수 금지) — 미실행 |
| 식물 계층 | `tools/plant_hierarchy.py` | Claude Code | 구현됨 | OK | 2026-09-24 |  |
| 식물 구조 | `tools/plant_structure.py` | Claude Code | 구현됨 | OK | 2026-10-04 | 보드 시절 데이터 기준 |
| 옆 사진 테두리 점 찍기 도구(방향별 4개) | `build/rim_click_side_20261012_03` | Claude Code | 일부 | OK | 2026-10-13 | 무효(VOID.md·페이지 상단 빨간 띠, 2026-10-13): 자동 점이 계산 착시였고 선 구분(edge)도 없음 — 아무 코드도 읽지 않음. 대체 build/rim_click_side_20261013_01 |
| 잎 면적 기하 | `tools/leaf_area_geometry.py` | Codex | 구현됨 | OK | 2026-10-03 |  |
| 잎 추적(복엽 ID 연결) | `tomato3d/track/link.py` | Claude Code | 구현됨 | OK | 2026-10-12 | phynotype2 §7 계약; 복엽은 평생 한 축(M/S1…), 서로 다른 축 사이 연결 금지(합성 126쌍 차단), 오연결 0; 모든 연결 proposed; 실사진은 상면 마스크 없어 unavailable |
| 잎 휨 기록(사람 작성) | `(data/records/leaf_bend)` | 사람 | 없음 | - |  | 상면3D T0 게이트 입력 — 없어서 BENT_FRACTION unavailable·T2 차단; 템플릿 build/leaf_bend_template |
| 정의집(용어·결정 사본) | `docs/정의집_토마토_2026-10-11.md` | Claude(채팅) | 사양만 | OK | 2026-10-13 | claude.ai 원본의 저장소 사본 — CLI 세션이 읽을 수 있도록; 구속력은 handoff/MTG_CONVENTION_2026-10-10.md |
| 측면 기하(삽입각·α·θ) | `tomato3d/state/sidegeom.py` | Claude Code | 실행됨 | OK | 2026-10-12 | MTG A3 규칙(select_views 단일 구현); R.1 150장면 재검증: A3 중앙 5.9°/p90 13.7° vs 첫 뷰 14.5°/52.9°, 사분면 3118/3118 → build/p1_side_validation_20261012_01 |
| 카메라 위치(테두리 → 자세·초점 검증·세로 스케일) | `tomato3d/state/camera.py` | Claude Code | 구현됨 | OK | 2026-10-13 | EXIF 초점(폭 5824/대각 6057 px) + 테두리 호모그래피 → 자세·거리·자체 점검(2σ). 2026-10-13: 기준 평면이 흙 표면이어도 자세는 테두리 기준으로 환산; 세 변 + 가려진 변 → 초점 고정 근사 자세(검증 불가). 세로 자 확인은 기준점 결정 대기 |
| 테두리 바깥선 자동 제안(반자동) | `tomato3d/state/rim_auto.py` | Claude Code | 일부 | OK | 2026-10-13 | 2026-10-13 개정: 제안마다 선 이름(앞 = 안쪽 윗선, 좌우 = 바깥 윗선), 뒤쪽 = side_occluded 기본값. 옆 39장: 앞 29·좌 20·우 25 제안, 세 변 근사 자세 14. 위 사진은 미지원 |
| 합성 생성기·렌더(상면 N/O·측면 R.1) | `tomato3d/synth` | Claude Code | 실행됨 | OK | 2026-10-12 | R.1/R.2 완료 2026-10-12: 150장면 x 4뷰 = 600장 렌더·라벨(64spp 400 + 16spp 200), 복엽 박스 4,017, 사분면 검사 3,247개 불일치 0, unclear 22.4%; 상면 N/O 완료 |
| 합성 정답 내보내기 | `tomato3d/state/fixture_truth.py` | Claude Code | 실행됨 | OK | 2026-10-12 | 정답 MTG·면적 4종·광학면; counts_as_photo_reconstruction=false |
| 화방 등록·segment_index(trusses.csv·Truss 정점) | `tomato3d/state/trusses.py` | Claude Code | 실행됨 | OK | 2026-10-12 | 사람 화방 등록부 읽기·검증; segment_index = 1 + 그 축에서 아래 화방 수(등록부+랭크에서 유도, 손 입력·사진 추정 없음); 등록부 없으면 unavailable; 촬영 시점까지 기록된 화방만 사용 |
| 화방 등록부 템플릿 | `build/truss_registry_template` | Claude Code | 구현됨 | OK | 2026-10-12 | 사람이 data/records/trusses/로 복사해 작성(plant_id, axis, above_rank, first_observed, note) |
| 화방 등록부(사람 작성) | `(data/records/trusses)` | 사람 | 없음 | - |  | 관측 화방의 유일한 출처 — 미작성이면 예측 화방은 generated_truss만; 템플릿 build/truss_registry_template |
| 화분 기록 템플릿(pot_spec·rim_points) | `build/pot_records_template` | Claude Code | 실행됨 | OK | 2026-10-13 | 2026-10-13 새 열 + edge 열 + side_occluded; 사용자 지시로 pot_spec 행과 rim_points_side_000.csv를 data/records/pots/에 복사함(2026-10-13, 이전 pot_spec은 build/rim_inner_plane_20261013/records_before_copy/) |
| 화분 기록(사람 작성) | `data/records/pots` | 사람 | 일부 | OK | 2026-10-13 | rim_points.csv 105점·위 사진 13장(kind=rim_edge만 → 자 눈금 없어 교차확인 불가); pot_spec.csv는 EXAMPLE 행 확인 대기 |
| 화분 테두리 스케일(호모그래피·불확도·자 교차확인) | `tomato3d/state/potscale.py` | Claude Code | 실행됨 | OK | 2026-10-13 | 네모 셀 바깥 60·안쪽 59 mm, 흙 표면 10 mm 아래(사용자 캘리퍼). 점마다 선(outer_top/inner_top/medium_junction) → 그 선의 평면으로 호모그래피; 모든 mm 값에 기준 평면(pot_rim/medium_surface)과 높이 차 필수(없으면 거부). 위 13장: 바깥 윗선·테두리 평면 그대로(변화 0) |
| 화분 테두리 점 찍기 도구(브라우저) | `build/rim_click_20261012_03` | Claude Code | 구현됨 | OK | 2026-10-12 | 자체 포함 HTML(사진·코드 내장, 17 MB) — 탐색기 더블클릭으로 Chrome/Edge에서 열기; tomato3d/cli/rim_points_tool.py로 생성; 위 사진 13장 → rim_points.csv; 미리보기 = potscale.py; _01·_02 대체 |
| P1 실사진 점검 패키지(기준 평면 명시) | `build/p1_state_20261013_01` | Claude Code | 일부 | OK | 2026-10-13 | revision 7, 사람 기록 복사 전: 위 13장 = _14와 같은 값(pot_rim, 0); 결손 104. _20261013_03이 대체 |
| P1 화방 합성 패키지(현행) | `build/p1_state_20261013_02` | Claude Code | 실행됨 | OK | 2026-10-13 | revision 7 코드 재실행(합성 카메라 = synthetic_camera 평면); 검증 문제 0; _15 대체 |
| 안쪽 선·평면 점검(R3·R4 근거) | `build/rim_inner_plane_20261013` | Claude Code | 실행됨 | OK | 2026-10-13 | 위 사진 전후표(13장 변화 0), 흙 경계 자동 점검(네 변 1/13, 거리 불일치), 클릭 확대 사진, side_000 미리보기(7 validated·6 approximate) |
| 옆 사진 선별 자동 제안(090·180·270) | `build/rim_auto_20261013_01` | Claude Code | 일부 | OK | 2026-10-13 | 39장: 앞(안쪽 윗선) 29·좌 20·우 25, 뒤 = 가려짐 기본값; 사람 확인 전에는 기록 아님 |
| 옆 사진 테두리 점 찍기 도구(선 구분) | `build/rim_click_side_20261013_01` | Claude Code | 구현됨 | OK | 2026-10-13 | side_090·180·270 페이지(자동 제안 미리 채움, 변별 선 선택·가려짐 체크); 저장 → rim_points_side_XXX.csv(edge 열) |
| P1 실사진 점검 패키지(현행, 옆 side_000 반영) | `build/p1_state_20261013_03` | Claude Code | 일부 | OK | 2026-10-13 | D1 = 테두리 평면 유지(사용자 2026-10-13). 위 13장 그대로; 옆 side_000: 자세 8 validated → 세로 스케일 8장(52~85 µm/px, 상대 sd 2.8~13%), 5 approximate; 스케일 결손 96(옆 44·수평 52); 검증 문제 0; _01 대체 |

## 캐노피 구성

| 프로그램 | 경로 | 주체 | 상태 | 파일 | 수정일 | 메모 |
|---|---|---|---|---|---|---|
| 개체→캐노피 좌표 변환·합치기/나누기 | `tomato3d/state/canopy.py` | Claude Code | 실행됨 | OK | 2026-10-11 | P1 쪽 배치 행렬; 왕복 오차 0.0001 mm; 선반 간격 300/110/110 mm·흙 높이는 가정값(assumed_unmeasured) |
| 캐노피 합치기/나누기(엔진 쪽) | `tools/tomato_fsp_canopy.py` | Codex | 실행됨 | OK | 2026-10-11 | P1 행렬 1회 적용, 복제 인스턴스 분리, 외부 소엽 ID 유지 |
| 화분별 광 비율·배치 기록 | `data/records/env_light_20261010` | Claude(채팅) | 실행됨 | OK | 2026-10-11 | 규칙 v3; 사람 소유 기록. 2026-10-13 실측 PPFD(data/records/env_20261013)로 비율의 절대 기준이 생김 |
| 환경 실측 기록(PPFD·분광·양액) | `data/records/env_20261013` | 사람 + Claude(정리) | 실행됨 | OK | 2026-10-13 | 2026-10-13 실측: 광 46점(테두리면 7 cm 30점·캐노피면 15 cm 16점), 분광 2점, 램프·판·트레이 기하, 양액 5건. 미기재 항목은 unavailable로 표기 |

## P2 광

| 프로그램 | 경로 | 주체 | 상태 | 파일 | 수정일 | 메모 |
|---|---|---|---|---|---|---|
| GroIMP 광 장면 | `tools/groimp_light_scene.py` | Claude Code | 구현됨 | OK | 2026-09-29 | 2026-10-13 확인: lamps_from_scene이 방향성 광원을 등방성 PointLight로 환원(절대값 주장 차단). 방향성 LED 보정에는 ppfd_validation.arealight_node/lamp_adapter 경로 재사용 필요 |
| GroIMP 연결 | `tools/groimp_bridge.py` | Codex | 구현됨 | OK | 2026-09-27 |  |
| Native optical materials and objects | `tools/fsp_extensions.py` | Codex | 일부 | OK | 2026-10-12 | Actual reflection/transmission and static objects; independent first-hit received tally; terminal photon closure unavailable; conditional 550 nm conversion |
| PPFD 검증 | `tools/ppfd_validation.py` | Codex | 구현됨 | OK | 2026-10-02 | 기존 직달 fit_empty_rig는 반사 리그 거부. 사용자 결정으로 벽 반사율 적합 목표 폐기; 현재 주 경로는 46점 실측 보간. 네이티브 반사율 적합을 후속 필수 작업으로 해석하지 않음 |
| Python 캐노피 광 | `tools/canopy_light.py` | Codex | 구현됨 | OK | 2026-09-19 | 진단·비교용 |
| 계층 광 | `tools/hierarchical_light.py` | Codex | 구현됨 | OK | 2026-10-03 | 진단·비교용 |
| 광 모듈 | `tomato3d/light` | Codex + Claude Code | 구현됨 | OK | 2026-09-29 |  |
| 기준 DLI | `tools/reference_dli.py` | Codex | 구현됨 | OK | 2026-10-13 | 실측 logged/spot_schedule 및 새 empirical 명령 제공; 46점 보간의 위치별 DLI와 독립 소비자 검증. 실제 잎 광량·생장 검증과 별개. 기존 simulated 의미/역사 보존; 근거 P2_EMPIRICAL_LIGHT_FIELD_EXECUTION_2026-10-13.md |
| 램프 모델 적합(확산광 분리) | `data/records/env_20261013/derived_summary_20261013.json` | Claude(채팅) | 실행됨 | OK | 2026-10-13 | 바 3개 선광원 적합 RMS 16.5% → 확산광 항 추가 시 5.7%, 확산 112 µmol(평균의 60%). 캐비닛 내벽 반사면 필요, 램프 위치는 미결정 |
| 램프·캐비닛 보정 프롬프트 | `handoff/CODEX_CLI_PROMPT_P2_LAMP_CALIBRATION_2026-10-13.md` | Claude(채팅) | 사양만 | OK | 2026-10-13 | 실측 46점 기준 보정: 흰 내벽 반사면 추가, 램프 3바 실측 기하, 자유 파라미터 3개 이하, 테두리면으로 적합 후 캐노피면 예측(홀드아웃 오차가 결과), 반사 기여율 vs 해석 추정 60% 대조 — 미실행 | 2026-10-13: 적합 목표는 EMPIRICAL_LIGHT_FIELD 프롬프트로 대체(반사율 식별 불가). 전달된 코드(네이티브 장면 물체·쌍시드 반사 추정기·동결 내보내기·reference_dli 소비자)는 계속 사용 |
| 실측 광장 보간 프롬프트 | `handoff/CODEX_CLI_PROMPT_P2_EMPIRICAL_LIGHT_FIELD_2026-10-13.md` | Claude(채팅) | 실행됨 | OK | 2026-10-13 | Codex E1–E6 구현·조건부 실행: 46점 제한 보간, 0.5/0.6/0.7 방향 시나리오, empirical DLI, 254 회귀 테스트. 실물 정확도·광학면·조명 위치·공간 등록은 미검증; P2_EMPIRICAL_LIGHT_FIELD_EXECUTION_2026-10-13.md |
| Empirical measured field | `tools/empirical_light_field.py` | Codex | 구현됨 | OK | 2026-10-13 | 46 measured points; bounded interpolation; configuration binding; physical accuracy unvalidated |
| Empirical canopy direction scenarios | `tools/empirical_canopy.py` | Codex | 일부 | OK | 2026-10-13 | 50/60/70 percent diffuse scenarios implemented and fixture tested; real optical surfaces and lamp pose unavailable |
| Empirical reference DLI | `tools/reference_dli_empirical.py` | Codex | 구현됨 | OK | 2026-10-13 | Versioned derived per-position duration dose; independent consumer; no whole-plant promotion |
| Empirical field tests | `tools/tests/test_empirical_light_field.py` | Codex | 실행됨 | OK | 2026-10-13 | 29 focused tests passed |
| Empirical field execution | `handoff/P2_EMPIRICAL_LIGHT_FIELD_EXECUTION_2026-10-13.md` | Codex | 실행됨 | OK | 2026-10-13 | Four declared coordinate variants and independent consumer outputs; no real leaf forecast |
| 실측 광장 → 잎별·시간별 광 출력 | `tools/empirical_growth_boundary.py` | Codex | 실행됨 | OK | 2026-10-13 | 입사/흡수 분리, 면적 우선 집계, 형상·등록·설정·시간 해시 결합, 외삽/이중 차폐 거부. 합성 기하 조건부 실행; 실제 생장 미검증 |
| 실측 잎 광량 독립 소비자 | `tools/empirical_growth_consumer.py` | Codex | 실행됨 | OK | 2026-10-13 | 독립 면적·광량·시간 적분, 불일치·변조 거부. 경계+기존 광장/소비자 합계 86 테스트 통과(중복 합산 금지) |
| 실측 광량 네이티브 응답 어댑터 | `tools/empirical_native_response.py` | Codex | 실행됨 | OK | 2026-10-13 | 실제 네이티브 light-only 3회, 45 공학용 삼각형 잎/회, 135 잎-구간 비교 오차 0; external_once. 탄소 0·질량/나이/면적 불변; 생장 모드 검증 아님 |
| 실측 광량 경계 테스트 | `tools/tests/test_empirical_growth_boundary.py` | Codex | 실행됨 | OK | 2026-10-13 | 신규 32 사례; 경계·기존 실측 광장·소비자 회귀 합계 86 통과. 전체 저장소 재시험 아님 |
| 실측 광량 경계 실행 보고 | `handoff/P2_EMPIRICAL_GROWTH_BOUNDARY_EXECUTION_2026-10-13.md` | Codex | 실행됨 | OK | 2026-10-13 | 최종 native 증거가 초기 no-hook 설명을 대체. 실제 작물/NRH 생장/변화하는 복잡 형상 검증은 남음; 실패 시도 보존 |
| 실측 광량 네이티브 전달 검증 | `build/p2_empirical_growth_boundary_20261013_01/delivery_verification.json` | Codex | 실행됨 | OK | 2026-10-13 | 소스·산출물 해시/3개 방향 시나리오 네이티브 전달 독립 검증. 원래 13062삼각형 형상은 500M 연산 한도로 미실행; 축소 공학 형상임을 명시 |
| 광자 반복 입사·종료 집계 인계 | `handoff/P2_EMPIRICAL_NATIVE_HOOK_2026-10-13.md` | Codex | 일부 | OK | 2026-10-13 | 외부 흡수 광 입력 훅 연동은 검증됨. 반복 입사·탈출·절단 이벤트 계측은 계약만; 집계 getter로 재구성 불가, 광자 전체 수지 미완료 |

## P4 생리·배분

| 프로그램 | 경로 | 주체 | 상태 | 파일 | 수정일 | 메모 |
|---|---|---|---|---|---|---|
| Native contract IO | `tools/vtc_development_io.py` | Codex | 실행됨 | OK | 2026-10-13 | Segment strings preserved through native reads and validation |
| Native organ segment initialization | `tools/vtc_development_observation.py` | Codex | 실행됨 | OK | 2026-10-12 | Imported segments retained; unavailable remains unavailable |
| Native per-axis truss and stop program | `tools/vtc_development_native.rgg` | Codex | 실행됨 | OK | 2026-10-13 | User-authorized conditional truss generation on declared axes; independent stop; shared plant pool |
| Native source binding | `tools/vtc_development.py` | Codex | 실행됨 | OK | 2026-10-13 | Includes segment helper in source hashes |
| Native truss and segment controls | `tools/fsp_axes_truss_acceptance.py` | Codex | 실행됨 | OK | 2026-10-12 | Four core synthetic controls plus three exchange runs; 15 intervals at 4.8M rays; max carbon residual 2.34e-17 gC |
| Nutrient transaction protocol fixture | `tools/fsp_nutrient_transaction.py` | Codex | 틀·데모만 | OK | 2026-10-12 | Identity/timeout/retry/unused-resource checks only; no native causal handshake or nutrient-growth law |
| P4 substem truss execution | `handoff/P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12.md` | Codex | 실행됨 | OK | 2026-10-12 | Conditional software acceptance and actual P1 fixture interoperability; biological accuracy not established |
| P4 곁순 자원 프롬프트 | `handoff/CODEX_CLI_PROMPT_P4_SIDESHOOT_RESOURCES_2026-10-12.md` | Claude(채팅) | 실행됨 | OK | 2026-10-12 | 결과: handoff/P4_SIDESHOOT_EXECUTION_2026-10-12.md + P4_SIDESHOOT_SCIENCE_AND_IO_CONTRACT_2026-10-12.md |
| P4 곁순·화방 프롬프트 | `handoff/CODEX_CLI_PROMPT_P4_SUBSTEM_TRUSS_2026-10-12.md` | Claude(채팅) | 실행됨 | OK | 2026-10-12 | 결과: handoff/P4_SUBSTEM_TRUSS_EXECUTION_2026-10-12.md |
| Resource contract addendum | `handoff/P4_SIDESHOOT_RESOURCE_CONTRACT_2026-10-12.md` | Codex | 실행됨 | OK | 2026-10-12 | Section 7 selects substem applicability from user observation; timing and hidden state remain pending |
| Segment and history regression | `tools/tests/test_fsp_axes_segments.py` | Codex | 실행됨 | OK | 2026-10-12 | 24 new cases; focused union 219 unique passed; overlaps excluded |
| VTC 1단계 연결 | `tools/vtc_growth_bridge.py` | Codex | 실행됨 | OK | 2026-10-13 | 탄소 보존·차폐 피드백 확인; 축소판(소엽 일부) |
| VTC 입출력 | `tools/vtc_growth_io.py` | Codex | 실행됨 | OK | 2026-10-11 |  |
| VTC 포크 | `tools/vtc_growth_fork.py` | Codex | 실행됨 | OK | 2026-10-11 | 원본 vtc-main은 수정 안 함 |
| 광→생장 소비자 | `tools/light_growth_consumer.py` | Codex | 틀·데모만 | OK | 2026-10-05 |  |
| 광→생장 연결 | `tools/light_growth_bridge.py` | Codex | 틀·데모만 | OK | 2026-10-05 | 틀·데모 |
| 양분 균형 | `tools/nutrient_balance.py` | Codex | 구현됨 | OK | 2026-10-06 |  |
| 양분 기록 양식(사람 작성용 템플릿) | `build/nutrient_records_template` | Claude(채팅) | 구현됨 | OK | 2026-10-12 | tray_spec.csv + nutrient_log.csv + README_KO; 사람이 data/records/nutrient/로 복사. 급액량·고인 깊이·대조 트레이가 수지의 전제 |
| 양분 기록(사람 작성) | `(data/records/nutrient)` | 사람 | 없음 | - |  | 미작성 — 급액 7회 이상(대조 트레이 포함)이 쌓이면 흡수 파라미터를 처음으로 실측 적합 가능 |
| 양분 수지 | `tools/fsp_nutrients.py` | Codex | 구현됨 | OK | 2026-10-06 | 생장에 연결 안 됨 |
| 양분 저수조 계약·구현 프롬프트 | `handoff/CODEX_CLI_PROMPT_P4_NUTRIENT_RESERVOIR_2026-10-12.md` | Claude(채팅) | 일부 | OK | 2026-10-13 | 기록·EC 당량 수지·양방향 저장 이동·대조 트레이 보정·모형 개체 분배 구현. 최종 84 테스트/24 검사/6 CLI 통과. 반응식·계수 삽입 대기, 네이티브 생장 제약 비활성; 전체 사양 완료 아님. P4_NUTRIENT_RESERVOIR_EXECUTION_2026-10-12.md |
| 양분-FSP 연결 | `tools/nutrient_fsp_bridge.py` | Codex | 구현됨 | OK | 2026-10-06 | 진단용 장부 |
| 탄소 진단 | `tools/fsp_carbon_diagnostic.py` | Codex | 구현됨 | OK | 2026-10-05 | 진단 전용 |
| 트레이 저수조 EC 당량 수지 | `tools/nutrient_reservoir.py` | Codex | 실행됨 | OK | 2026-10-13 | 용액·배지수·저장 당량 분리, 처방 흡착/방출, 대조 보정·불확도·모형 분배. 원소별 흡수/동역학 아님; 생장 피드백 false |
| 트레이 기록 수신·계산 결합 | `tools/nutrient_reservoir_records.py` | Codex | 실행됨 | OK | 2026-10-13 | 사람 기록 읽기 전용, 상태·단위·원본 해시·시각/소속 검증. 실제 기록은 체적·정확한 시간·대조군 등이 부족해 흡수 unavailable; 약400mL는 참고값만 |
| 저수조 공동 확정 거래 픽스처 | `tools/nutrient_reservoir_transaction.py` | Codex | 틀·데모만 | OK | 2026-10-13 | 식별자/선행상태/구간/설정 결합, 만료·재시도·충돌 검사 및 원자적 픽스처 저장 검증. 실제 네이티브 자원 차감·되돌리기·인과적 성장 제약 없음 |
| 저수조 수지 테스트 | `tools/tests/test_nutrient_reservoir.py` | Codex | 실행됨 | OK | 2026-10-13 | 최종 84 통과; 기존 모델 회귀 178 통과/1 실패 별도 보존, B1 재검사 중단으로 통과 주장 없음 |
| 저수조 계약·미확정 과학 항목 | `handoff/P4_NUTRIENT_RESERVOIR_CONTRACT_2026-10-12.md` | Codex | 일부 | OK | 2026-10-13 | 결손 초기 상태/과학값을 0으로 채우지 않음; 반응식·breakpoint·교환법칙·대조 비교 가능성 필요. 방출 누락 시 흡수 편향 부호 이의 기록 |
| 저수조 구현 실행 보고 | `handoff/P4_NUTRIENT_RESERVOIR_EXECUTION_2026-10-12.md` | Codex | 실행됨 | OK | 2026-10-13 | 실제 실행일 2026-10-13; 최종 addendum 84 테스트/24 검사/6 CLI. 수지 구현과 생장 결합 미완료 구분; delivery_02가 최종 |
| 저수조 최종 전달 검증 | `build/reservoir_continuation_20261013_delivery_02/verification.json` | Codex | 실행됨 | OK | 2026-10-13 | 24 독립 검사/6 실제 CLI; 처방·대조 보정·대조군 누락 거부·실제 관측 감사·CSV 결합. native 인과성 검증 아님 |

## P3 생장·방향

| 프로그램 | 경로 | 주체 | 상태 | 파일 | 수정일 | 메모 |
|---|---|---|---|---|---|---|
| 3단계 예측 계층(앙상블·불변 산출) | `tools/microtom_forecast.py` | Claude Code | 실행됨 | OK | 2026-10-13 | P3 V3(2026-10-12): 축·화방·세그먼트 인식 — fsp-axes-1 레코드를 P1 axes.csv/trusses.csv에서 그대로 구성(segment_index 유도 금지), 두 parent_rank 의미·두 세그먼트 카운터 분리 열, 축별 사건(new_leaf·new_truss_generated·apex_stop)+probability_basis+truss_provenance; 산출 build/forecast_20261012_04(P1 _09 픽스처, 4.8M). 이전: B1-B6, build/forecast_20261012_02·_03. F8(2026-10-12, 미실행): SUBSTEM_SINK_SCALE을 시나리오 집합 0.5/1.0/2.0으로 선언 — 현재 발행본은 1.0 단일 가정, 3시나리오 × N멤버 재발행 대기; F8: SUBSTEM_SINK_SCALE 시나리오 집합 0.5/1.0/2.0 나란히(합치지 않음), build/forecast_20261012_07 (세 시나리오 동일: 이 픽스처는 탄소 비제한); _05·_06은 OneDrive 이름바꾸기 거부로 FAILED 표식; F9: 스트레스 실행(reuse_as_prediction=forbidden 표식) 멤버 거부, RERUN_TRIGGERS·manifest.rerun_trigger(G3), hidden_state_passed_through |
| 3단계 예측 사양 | `handoff/CODEX_FORECAST_SPEC_2026-10-10.md` | Claude Code | 실행됨 | OK | 2026-10-11 | 구현: tools/microtom_forecast.py·_io·_eval; 산출 build/forecast_20261011_01·_02(300k, 진단급), build/forecast_20261012_02(종자 4.8M)·_03(P1 파이프라인 4.8M); 수정 보고 handoff/FORECAST_FIXES_EXECUTION_2026-10-11.md; 조건부; 생물학 정확도 not testable |
| 3단계 예측 평가(롤링 오리진) | `tools/microtom_forecast_eval.py` | Claude Code | 구현됨 | OK | 2026-10-12 | P3 V3: forecast_map.csv에 axis; 관측에 axis·truss_source; substem_leaf_count_error, truss_timing_error_days(레지스트리 화방만); 실측 시계열 없음 → not testable |
| Axis-aware immutable pipeline checkpoints | `tools/tomato_fsp_pipeline.py` | Codex | 실행됨 | OK | 2026-10-13 | Committed axis and organ inventories include segment; native checkpoint published once |
| F10 지평 연장 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_P3_F10_HORIZON_2026-10-13.md` | Claude(채팅) | 사양만 | OK | 2026-10-13 | 선언값 0.2 gC 그대로 두고 지평만 30일로 — 상한이 언제 물리는지, 예비탄소 궤적의 전환점 포함. 물리면 F8 시나리오 집합을 그 구간에서 재발행해 low_high_distance를 처음으로 산출. 결과는 model_property, 지평이 길수록 가정 오차 누적 명시 — 미실행 |
| F9 배분 상한 스트레스·예비 탄소 임계 스윕 | `tools/microtom_stress.py` | Claude Code | 실행됨 | OK | 2026-10-13 | 소프트웨어 검증 전용(예측 아님, 모든 행 reuse_as_prediction=forbidden, 폴더 build/stress_*). 자체 시나리오 JSON에서만 plant_initialization.reserve_gC 교체(fixture_declared); 상한 물림·수요비례(fsp_axes.allocation_reference 오라클)·방향·폐쇄·축합 검사; 스윕 임계 약 0.1420 gC(선언 0.2에서는 8일에도 안 물림) |
| F9 스트레스 픽스처·스윕 산출 | `build/stress_20261013_01` | Claude Code | 실행됨 | OK | 2026-10-13 | 12 네이티브 케이스, 4800000 광선: 스트레스 예비 0.1 gC에서 low/base/high 분할 선언 방향으로 갈라짐(all_checks_passed=True); 스윕 괄호 0.1415(물림)/0.1425(안 물림); 지평 8일 선언값 비물림. 예측으로 인용 금지 |
| F9 실행 보고 | `handoff/P3_F9_CARBON_LIMIT_EXECUTION_2026-10-13.md` | Claude Code | 실행됨 | OK | 2026-10-13 | G1 스트레스 검사표, G2 지배 가정(PLANT_RESERVE_GC user_assumed)·임계 스윕·지평, G3 재실행 조건 3개, 수용 기준 대조; _KO 동반 |
| F9 탄소 제한 프롬프트 | `handoff/CLAUDE_CODE_CLI_PROMPT_P3_F9_CARBON_LIMIT_2026-10-13.md` | Claude(채팅) | 실행됨 | OK | 2026-10-13 | 실행됨(Claude Code 2026-10-13): tools/microtom_stress.py + build/stress_20261013_01; 본 픽스처 미조정; 임계 약 0.1420 gC는 model_property로 기록(채택 금지); 재실행 조건은 RERUN_TRIGGERS/manifest.rerun_trigger |
| F9 테스트 | `tools/tests/test_microtom_stress.py` | Claude Code | 실행됨 | OK | 2026-10-13 | 레지스트리 어휘·행, 본 픽스처 불변, 재사용 금지 표식(멤버 거부·폴더 거부), 합성 표에서 물림·오라클·방향·임계, F8 멤버 비물림, 네이티브 1구간 3시나리오 |
| Micro-Tom 기후·광 입력 흐름 | `tools/microtom_environment.py` | Claude Code | 구현됨 | OK | 2026-10-11 | 설정값 CSV(user_stated)·DLI 유도·광비율 포인터(해시 기록)·16셀 광검증(RMSE·r); 기준 PPFD는 user_assumed(계측기 전) |
| Micro-Tom 매개변수 레지스트리 | `tools/microtom_parameters.py` | Claude Code | 구현됨 | OK | 2026-10-13 | tools/microtom_parameters.csv: 모든 행 source_kind 보유, measured 없음; V3 request parameters로 매핑(build_request_overrides); F9: PLANT_RESERVE_GC(0.2 user_assumed, hidden_state, 지배 가정)·RESERVE_CAP_THRESHOLD_GC(0.1420 model_property, 채택 금지); 어휘 hidden_state/fixture_declared/model_property |
| Micro-Tom 포크 사양 | `handoff/CLAUDE_CODE_CLI_PROMPT_VTC_MICROTOM_FORK_2026-10-11.md` | Claude(채팅) | 실행됨 | OK | 2026-10-11 | V3가 결정론적 정지·9잎·랭크 소엽표·램프를 이미 구현; 나머지는 tools/microtom_parameters.py(레지스트리)·tools/microtom_environment.py(기후 CSV·DLI·포인터·16셀 광검증); CURVE_RATIO·BENT_FRACTION·AREA_CORRECTION는 엔진 비활성(훅 H1-H3 요청); 커버리지: handoff/MICROTOM_FORK_FORECAST_COVERAGE_2026-10-11.md |
| P3 시나리오 예측 산출(F8) | `build/forecast_20261012_07` | Claude Code | 실행됨 | OK | 2026-10-12 | 3시나리오(0.5/1.0/2.0) × 4멤버 × 3구간, 4.8M, 75분. 모든 행에 scenario_id·scenario_value. 세 시나리오 수치 동일 — 픽스처 탄소 비제한 상태의 성질(품종 성질이 아님). _05·_06은 OneDrive 폴더 이름변경 거부로 실패 폴더 F8 결론: 픽스처가 탄소 비제한이라 시나리오 차이 0 — 판정은 실측 광 반영 후로 미룸(F9) |
| P3 축·화방 예측 산출(첫 발행) | `build/forecast_20261012_04` | Claude Code | 실행됨 | OK | 2026-10-12 | P1 _09 픽스처·4.8M 광선·4멤버·체크포인트 3: M이 Truss2 생성(generated_truss), S1·S2 신엽 +2 d, 정지 없음, 축 합계=개체 장부 1.4e-17 gC. 실사진 미경유, SUBSTEM_SINK_SCALE 1.0 단일 |
| P3 축·화방 예측 커버리지/실행 보고 | `handoff/P3_SIDESHOOT_FORECAST_EXECUTION_2026-10-12.md` | Claude Code | 실행됨 | OK | 2026-10-12 | 항목별 done/remainder/blocked, 명령·종료코드, 훅 H4(축별 CADENCE) 요청; 커버리지 handoff/P3_SIDESHOOT_COVERAGE_2026-10-12.md; _KO.md 동반 |
| P3 축·화방 예측 프롬프트 V3 | `handoff/CLAUDE_CODE_CLI_PROMPT_P3_SIDESHOOT_FORECAST_V3_2026-10-12.md` | Claude(채팅) | 실행됨 | OK | 2026-10-12 | F1~F7(build/forecast_20261012_04) + F8 시나리오 집합 0.5/1.0/2.0 실행(build/forecast_20261012_07, 3시나리오 × 4멤버 × 3구간). F8 결과: 세 시나리오 동일(low_high_distance=0) — 픽스처가 탄소 제한이 아니어서 싱크 가중이 작동하지 않음. V1·V2는 미실행 |
| Piecewise schedules and H1-H3 | `tools/fsp_extensions_native.rgg` | Codex | 실행됨 | OK | 2026-10-11 | Midnight and staggered lamps; elapsed-time maintenance/development; stable posture hooks; area correction reporting-only; no imported deformation law |
| VTC 전체 식물 발달 V3 | `tools/vtc_development.py` | Codex | 실행됨 | OK | 2026-10-13 | V3 조건부 전달: 65일 스핀업·새 기관·44일차 유한생장 정지; 생물학 검증 없음 |
| 복엽 생장 | `tools/compound_growth.py` | Codex | 구현됨 | OK | 2026-10-05 | 조건부; Claude Code 검토 |
| 생장 보정 | `tools/growth_calibration.py` | Codex | 구현됨 | OK | 2026-10-05 | 실측 시계열 없음 |
| 생장 시뮬레이터 | `tools/growth_simulator.py` | Codex | 구현됨 | OK | 2026-10-02 |  |
| 예측 계층 수정 보고(B1-B6) | `handoff/FORECAST_FIXES_EXECUTION_2026-10-11.md` | Claude Code | 실행됨 | OK | 2026-10-12 | 항목별 done/blocked, 명령·종료코드, 훅 결정; _KO.md 동반 |
| 월간 생장 | `tools/monthly_growth.py` | Codex | 구현됨 | OK | 2026-10-03 |  |
| 축·화방 입력 어댑터(P3) | `tools/microtom_axes.py` | Claude Code | 구현됨 | OK | 2026-10-12 | axes.csv/trusses.csv → fsp-axes-1 레코드; axil_parent_rank vs truss_above_rank; 화방 기하 보조(영점 부기점, 그림자 없음); 축 합계=개체 장부 검사 |
| 포크·예측 실행 보고 | `handoff/MICROTOM_FORK_FORECAST_EXECUTION_2026-10-11.md` | Claude Code | 실행됨 | OK | 2026-10-11 | 명령·종료코드·V3 훅 요청·비활성 매개변수·정확도 상태(not testable); _KO.md 동반 |
| 포크·예측 커버리지 맵 | `handoff/MICROTOM_FORK_FORECAST_COVERAGE_2026-10-11.md` | Claude Code | 실행됨 | OK | 2026-10-11 | 항목별 done_in_V3 / remainder / blocked 판정과 V3 file:function 근거 |
| 확률 복엽 생장 | `tools/probabilistic_compound_growth.py` | Codex | 구현됨 | OK | 2026-10-05 | provided_axes; 곁가지 생성 없음 |

## 광 재계산

| 프로그램 | 경로 | 주체 | 상태 | 파일 | 수정일 | 메모 |
|---|---|---|---|---|---|---|
| Declared-axis native acceptance | `tools/fsp_axes_acceptance.py` | Codex | 실행됨 | OK | 2026-10-12 | 4.8M two-seed main-leaf shading effect 0.08025 vs seed variation 0.009 umol/s; shared carbon residual 4.16e-17 gC |
| Optional extension native acceptance | `tools/fsp_extensions_acceptance.py` | Codex | 실행됨 | OK | 2026-10-12 | Optical limits/reflector/planes; midnight schedules; three 30-day hook runs; explicit unavailability for E2 closure/E6/E7 |
| P1~P4 통합 프롬프트 | `handoff/CLAUDE_P1_P2_P3_P4_END_TO_END_INTEGRATION_PROMPT_2026-10-11.md` | Codex | 실행됨 | OK | 2026-10-11 | 결과: handoff/CODEX_STAGED_FSP_INTEGRATION_EXECUTION_2026-10-11.md; 설정 목록 VTC_V3_PENDING_DECISIONS_2026-10-11.md |
| 구조 내보내기 | `tools/groimp_structure_export.py` | Codex | 구현됨 | OK | 2026-09-28 |  |
| 통합 검수·대조군 | `tools/tomato_fsp_acceptance.py` | Codex | 실행됨 | OK | 2026-10-13 | 동적/고정/시드/반일/실패 대조; 물 장부 실패 시 2단계 미확정 |
| 포크 엔진 훅 H1–H3 (네이티브 구현됨) | `tools/fsp_extensions_native.rgg` | Codex | 구현됨 | OK | 2026-10-11 | E8로 네이티브 구현 완료(CODEX_FSP_EIGHT_CAPABILITIES_EXECUTION_2026-10-11.md): H1 정확한 세그먼트 수 정규화, H2 기관별 안정 추출, H3 보고 전용. 한계 - H1/H2는 생성 기관 기하에만, 래퍼는 H1 매핑 미충족·H2 unavailable. H4(축별 CADENCE)는 여전히 차단 |

경로 없음: 0건
