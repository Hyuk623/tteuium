# tomato3d 코드 점검 — 환경변수·입출력·버그·유령코드 (2026-09-29)

- 대상: `tomato3d/` 패키지, 커밋 `26280b1` (브랜치 `claude/tomato-pipeline-20260929`)
- 범위 밖: `tools/`, `tools/tests/`, `config/`, `docs/` (Codex 담당, CLAUDE.md)
- 검증: `pytest` 182 passed / 1 skipped, `ruff check tomato3d tests` 통과, `vulture tomato3d --min-confidence 60`
- 이 문서는 점검 결과만 정리합니다. 코드 수정은 하지 않았습니다.

---

## 1. 환경변수

`tomato3d/config.py`에서만 읽습니다(다른 모듈은 `os.environ`을 쓰지 않음). 실행 시 `.env`를 자동으로 읽고(`load_dotenv()`), 예시는 `.env.example`입니다.

| 변수 | 기본값 | 용도 |
|---|---|---|
| `TOMATO3D_DATA_ROOT` | `./data` | 데이터 최상위 경로 |
| `TOMATO3D_CONFIG_DIR` | `./config` | 설정 JSON 폴더 |
| `TOMATO3D_CAMERA_ID` | `cam_a` | 캘리브레이션 기본 카메라 ID |
| `TOMATO3D_LOG_LEVEL` | `INFO` | 세 CLI의 로그 수준 |
| `TOMATO3D_MAX_WORKERS` | `4` | `run_stage1` 병렬 스레드 수. 1 이상 정수가 아니면 `ConfigError` |

### `TOMATO3D_DATA_ROOT` 아래 경로

| 경로 | 내용 |
|---|---|
| `raw/<plant_id>/<session_id>/` | 촬영 원본 |
| `calib/intrinsics_<camera_id>.json` | 카메라 내부 파라미터 |
| `derived/<plant_id>/<session_id>/` | Stage 1 결과 |
| `outputs/light/<run_id>/` | 광 계산 결과 |
| `outputs/` | 진단·조치 등 후속 산출물 |
| `knowledge/` | Crop Pack 등 지식 JSON |
| `tracks/` | 날짜 간 기관 추적 결과 |

### `TOMATO3D_CONFIG_DIR` 아래 파일

| 파일 | 비고 |
|---|---|
| `board_spec.json` | 보드 규격 |
| `capture_config.json` | 촬영 설정 |
| `quality_thresholds.json` | 품질 판정 기준 |
| `light_scene.json` | 조명 정보. 조명 측정 후 사람이 만드는 파일이라 없을 수 있음 |

### 참고: 패키지 밖에서 쓰는 변수

- `tools/sam_trial_bundle.py`: `SAM_TRIAL_ARCHIVE`, `SAM_TRIAL_WORKDIR`, `SAM_TRIAL_RUNTIME`, `SAM_TRIAL_REPOSITORY`, `SAM_TRIAL_CHECKPOINT`
- `build/*/train.py`, `tools/offload_job.py`: `PYTORCH_CUDA_ALLOC_CONF`를 직접 설정
- `tools/offload_job.py`: 하위 프로세스에 `PYTHONUTF8=1` 전달

---

## 2. CLI 입력·출력

종료 코드는 세 CLI 공통으로 `0` 성공, `2` 필수 입력 오류(설정·스키마·경로)입니다. `calibrate_intrinsics`만 캘리브레이션 계산 실패 시 `1`을 반환합니다.

### 2.1 `python -m tomato3d.cli.calibrate_intrinsics`

ChArUco 보드 사진으로 카메라 내부 파라미터를 계산합니다.

| 인자 | 필수 | 기본값 |
|---|---|---|
| `--images` | ✅ | 보드 사진 폴더 (jpg, jpeg, png, tif, tiff) |
| `--board` | | `<CONFIG_DIR>/board_spec.json` |
| `--camera-id` | | `TOMATO3D_CAMERA_ID` |
| `--out` | | `<DATA_ROOT>/calib/intrinsics_<camera_id>.json` |

**출력:** `intrinsics_<camera_id>.json` 한 개. 주요 필드는 `camera_id`, `image_width_px`, `image_height_px`, `camera_matrix`, `dist_coeffs`, `rms_reprojection_error_px`, `n_calibration_images`.

### 2.2 `python -m tomato3d.cli.run_stage1`

촬영 세션 하나에 대해 사진별 보드 포즈와 식물 실루엣 마스크를 구합니다.

| 인자 | 필수 | 기본값 |
|---|---|---|
| `--session` | ✅ | `<DATA_ROOT>/raw/<plant_id>/<session_id>` |
| `--board` | | `<CONFIG_DIR>/board_spec.json` |
| `--thresholds` | | `<CONFIG_DIR>/quality_thresholds.json` |
| `--intrinsics` | | manifest의 `camera_id`로 찾은 `<DATA_ROOT>/calib/intrinsics_<id>.json` |

**입력**
- 세션 폴더의 `session_manifest.json`과 `images/` 사진
- 세션 ID 형식 `<plant_id>_<YYYYMMDD>_<HHMM>`
- 보드 variant 또는 카메라 ID가 manifest와 다르면 중단

**출력** — `<DATA_ROOT>/derived/<plant_id>/<session_id>/`

| 파일 | 내용 |
|---|---|
| `poses.csv` | `session_id`, `image_file`, `view_type`, `top_position`, `pose_status`, `n_corners_detected`, `reprojection_error_px`, `rvec_x/y/z`, `tvec_x/y/z_mm`, `measured_angle_deg`. 포즈 실패 행도 남고 `pose_status=failed`, 숫자 칸은 `unavailable` |
| `masks/<이미지 파일명>.png` | 실루엣 마스크 |
| `quality.json` | `session_id`, `pose_solved_ratio`, `mean_reprojection_error_px`, `silhouette_area_cv`, `n_images_total`, `n_images_solved`, `usable_for_training`, `failure_reasons` |

세 가지는 임시 폴더에 먼저 쓴 뒤 한꺼번에 제자리로 옮깁니다.

### 2.3 `python -m tomato3d.cli.run_light`

조명, 잎 형상, 선택적으로 PPFD 측정값을 받아 잎별 광량·에너지와 예측 오차를 계산합니다.

| 인자 | 기본값 / 설명 |
|---|---|
| `--scene` | `<CONFIG_DIR>/light_scene.json` |
| `--geometry` | `leaf_surfaces.csv` / `leaf_patches.csv` (여러 개 가능, 보드 좌표계). 식물 없는 빈 공간 variant는 항상 포함 |
| `--readings` | `ppfd_readings.csv` (재배대 좌표계, 선택) |
| `--reference-variant` | 비교 기준 형상 variant (예: `multiview_41`) |
| `--calibration-variant` | 조명 보정 계수를 맞출 variant. 기본은 식물 없는 variant |
| `--run-id` | 결과 폴더 이름. 기본은 실행 시각 |
| `--out` | `<DATA_ROOT>/outputs/light/<run_id>` |

**입력 CSV 주요 컬럼**
- `leaf_surfaces.csv`: `plant_id`, `session_id`, `geometry_variant_id`, `geometry_source`, `organ_class`, `organ_id`, `leaflet_id`, `triangle_id`, `v0/v1/v2_{x,y,z}_mm`, `normal_convention`
- `leaf_patches.csv`: `plant_id`, `session_id`, `geometry_variant_id`, `geometry_source`, `organ_id`, `centroid_{x,y,z}_mm`, `area_mm2`, `normal_tilt_deg`, `normal_azimuth_deg`, `length_to_width_ratio`
- `ppfd_readings.csv`: `reading_id`, `setup_id`, `scenario_id`, `measured_at`, `sensor_model`, `x/y/z_mm`, `normal_x/y/z`, `all_fixtures_full_output`, `ppfd_umol_m2_s`, `split_role`, `region_label`, `observer`, `note`

**출력** — 결과 폴더가 이미 있으면 덮어쓰지 않고 종료 코드 2

| 파일 | 내용 |
|---|---|
| `run_summary.json` | 입력 파일과 출처, 한계, 경고 |
| `leaf_triangle_light.csv` | 삼각형별 광량 지도 |
| `leaf_light.csv` | 잎별 광량 |
| `plant_light.csv` | 식물별 광량 |
| `scenario_summary.csv` | 배치 × 형상 variant별 핵심 수치 |
| `sensor_predictions.csv` | 측정 지점별 예측 PPFD와 실측값 |
| `validation.csv` | 보정용·평가용 MAE / RMSE / bias |
| `geometry_variant_comparison.csv` | 형상 variant별 기준 대비 비교 |

### 2.4 데이터 흐름

```
calibrate_intrinsics ──> calib/intrinsics_<cam>.json ─┐
raw/<plant>/<session>/ (manifest + images) ───────────┴─> run_stage1
                                                          └─> derived/<plant>/<session>/{poses.csv, masks/, quality.json}

light_scene.json + leaf_surfaces/patches.csv (+ ppfd_readings.csv) ──> run_light ──> outputs/light/<run_id>/
```

`recon`, `organ`, `fuse3d`, `graph`, `pheno`, `track`, `rules`, `twoview`는 아직 `NotImplementedError` 스텁이라 입출력이 없습니다.

---

## 3. 버그

모두 심각도 낮음. 기존 테스트는 이 경우들을 다루지 않아 통과합니다.

### B1. 깨진 CSV를 넣으면 `run_light`가 traceback으로 멈춤 — 재현됨
- 위치: `tomato3d/io/tables.py:63` (`read_table`)
- `OSError`만 `SchemaError`로 바꿈. 빈 CSV는 `pandas.errors.EmptyDataError`, 형식이 틀린 CSV는 `ParserError`가 그대로 올라감
- 결과: 문서상 종료 코드 2가 아니라 traceback
- 같은 파일 `read_table_columns`(line 88)는 `EmptyDataError`를 이미 잡고 있어 두 함수가 일관되지 않음
- 제안: `except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError)`

### B2. `origin_corner`를 검증만 하고 실제로는 무시
- 위치: `tomato3d/io/schemas.py:161`, `schemas.py:256` (`first_inner_corner_sheet_mm`)
- 스키마는 `top_left`, `top_right`, `bottom_left`, `bottom_right`를 모두 받지만, `first_inner_corner_sheet_mm`은 항상 `(square_size_mm, square_size_mm)`을 반환 → 코드 전체가 `top_left`로 동작
- 결과: `"bottom_left"` 등도 검증을 통과하고 스케일 블록 제외 영역이 조용히 틀어짐
- 현재 `config/board_spec.json`은 `top_left`라 당장 영향 없음
- **결정 필요:** `Literal["top_left"]`로 제한할지, 네 방향을 모두 처리할지

### B3. 파일명이 같은 이미지의 마스크가 서로 덮어씀
- 위치: `tomato3d/io/manifest.py:35` (`mask_filename`), `tomato3d/cli/run_stage1.py:302`
- 마스크 이름이 이미지 stem만으로 정해짐(`<stem>.png`). `SessionManifest._check_counts`는 개수만 세고 중복 stem은 검사하지 않음
- 예: `side/000.jpg`와 `top/000.jpg` → 마스크 하나가 경고 없이 사라짐
- 제안: manifest 검증에서 중복 stem 거부

### B4. 환경변수 값이 틀리면 traceback — 재현됨
- 위치: 세 CLI의 `main()` (`run_light.py:229`, `run_stage1.py:432`, `calibrate_intrinsics.py`)
- `get_settings()`가 `try` 밖에서 호출됨. `TOMATO3D_MAX_WORKERS=abc`이면 `ConfigError` traceback, 종료 코드 1
- 제안: `get_settings()`를 `try` 안으로 옮기고 `ConfigError`도 잡아 종료 코드 2

### 확인 필요 (의도 여부)
- top view에는 실루엣이 만들어지지 않아 모든 세션에 `operational_top_view_silhouette_unavailable`가 붙음 → 어떤 세션도 `usable_for_training=true`가 될 수 없음

---

## 4. 유령 코드

### 4.1 어디서도 쓰이지 않음 (패키지·테스트·`tools/` 참조 0건) — 삭제 후보

| 위치 | 이름 |
|---|---|
| `tomato3d/calib/board.py:158` | `sheet_xy_to_board_mm` |
| `tomato3d/light/frames.py:47` | `board_to_grow_direction` |
| `tomato3d/io/schemas.py:445` | `SessionManifest.side_images` |
| `tomato3d/io/schemas.py:448` | `SessionManifest.top_images` |

### 4.2 문서와 실제가 다름
- `tomato3d/io/schemas.py:635` `parse_maybe_float`: 호출하는 곳이 없음
- 그런데 `tomato3d/io/tables.py` docstring은 "호출자가 이 함수로 `unavailable`을 변환한다"고 적고 있음
- `tomato3d/light/validate.py` 등은 같은 처리를 각자 구현함
- 제안: 실제 호출부를 이 함수로 모으거나 docstring을 고칠 것

### 4.3 테스트에서만 쓰임 — 유지 권장
`write_manifest`, `read_poses_csv`, `board_to_sheet_mm`, `SessionPaths.mask_path`, `json_schema`, `active_thresholds`, `board_center_sheet_mm`, `DATA_DIR_PROPERTIES`, `CONFIG_FILE_PROPERTIES`

### 4.4 의도된 것 — 정리 대상 아님
- 후속 단계 스텁 21개 (`recon`, `organ`, `fuse3d`, `graph`, `pheno`, `track`, `rules`, `twoview`): CLAUDE.md 지시대로 `NotImplementedError` 유지
- `knowledge_dir`, `tracks_dir`: Stage 1 명세가 요구하는 경로
- `capture_config_path`: 패키지에서는 안 쓰지만 `tools/light_study.py`, `tools/multiview_plant.py`에서 사용
- vulture가 "미사용"으로 표시한 pydantic 필드·validator 수십 개: 오탐
- `build/` (65 파일, 748K): Kaggle 커널 소스, 의도적으로 커밋됨

---

## 5. 작업 환경 메모
- `pip install -e .` 실행 시 `tomato3d.egg-info/`가 생김. `.gitignore`에 `*.egg-info/`가 없어 추적 안 된 파일로 남음 → 추가 권장

## 6. 후속 작업 제안 순서
1. B1, B4 수정 + 회귀 테스트 (종료 코드 2 확인)
2. B3 manifest 중복 stem 검증 + 테스트
3. B2 방향 결정 후 수정
4. 4.1 삭제, 4.2 정리
5. `.gitignore`에 `*.egg-info/` 추가

---

## 7. 반영 결과 (2026-09-29, Claude Code 로컬 세션)

| 항목 | 조치 | 위치 |
|---|---|---|
| B1 | `read_table`·`read_table_columns`가 `EmptyDataError`·`ParserError`도 `SchemaError`로 변환 → CLI 종료 코드 2 | `tomato3d/io/tables.py` |
| B2 | 결정: `origin_corner`를 `Literal["top_left"]`로 제한(실제 보드가 top_left이고 나머지 방향은 구현·검증 없음) | `tomato3d/io/schemas.py` |
| B3 | manifest 검증에서 파일 stem 중복을 거부("share the stem") | `tomato3d/io/schemas.py` |
| B4 | 세 CLI 모두 `get_settings()`를 `try` 안에서 호출, `ConfigError` → 종료 코드 2 | `tomato3d/cli/*.py` |
| 4.1 | `sheet_xy_to_board_mm`, `board_to_grow_direction`, `SessionManifest.side_images/top_images` 삭제 | `calib/board.py`, `light/frames.py`, `io/schemas.py` |
| 4.2 | `tables.py` docstring을 실제에 맞게 수정(호출부 통합은 보류) | `tomato3d/io/tables.py` |
| 5 | `.gitignore`에 `*.egg-info/` 추가 | `.gitignore` |

- 회귀 테스트: `tests/test_review_fixes_20260929.py` 8개. 전체 `pytest tests` **191 passed**.
- 변이 확인: B1·B3·B4 수정을 하나씩 되돌리면 해당 테스트가 실패함(3/3).
- 로컬 PC에 ruff가 없어 `ruff check`는 이 세션에서 다시 돌리지 않았음.
- 남은 "확인 필요": top view 실루엣이 없어 `usable_for_training`이 항상 false인 문제는 코드 변경 없이 유지(촬영 규격 결정 필요).
