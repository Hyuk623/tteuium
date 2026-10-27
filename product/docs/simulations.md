# 시뮬레이션 결과 연결

## 저장소에서 확인된 범위

- `tools/microtom_forecast.py`: 조건부 생육 시나리오/ensemble 실행과 결과 표. 원격 main 확인 당시 `real_p1_package` 설명에 실제 형상 기반 실행이 아직 이루어지지 않았다고 명시되어 있습니다. 코드의 입력 경로 지원과 실제 관측 식물의 검증된 실행은 다릅니다.
- `tools/vtc_development.py::collect`: 검증된 native 실행을 수집하고 `results/viewer.html`을 만듭니다. 뷰어는 시간 슬라이더와 회전 기능을 가진 자체 포함 canvas HTML입니다. 반드시 PNG를 생성하는 것은 아닙니다.
- 현재 로컬 build에는 연결할 실제 엔진 결과가 없습니다. 홈의 SVG 그림은 시뮬레이션 결과가 아닙니다.

## 새 탭

시뮬레이션 탭은 선택 식물에 등록된 결과 전체를 생성 시각 순으로 표시합니다. 7/14/30일 관측 필터와 독립적입니다. 결과 이미지(PNG/JPEG)와 생성된 HTML 뷰어를 지원합니다. 실행 ID, 시나리오 ID, 생성 시각, 입력 종류, 파일 해시를 보존합니다. 결과가 없으면 없는 상태를 표시하며 샘플 이미지를 실제 모델 결과로 대신하지 않습니다.

## 이미 생성된 결과 등록

실제 파일이 준비된 뒤, 저장소 루트에서 아래 예시의 파일/식물/실행/시나리오/생성시각을 실제 결과로 바꾸어 실행합니다. `--db`는 실행 중인 서버와 동일해야 합니다. 현재 8018 서버는 `build/product/dashboard-verified.sqlite3`를 사용합니다.

```powershell
build/product-venv/Scripts/python -m product.backend.simulations --db build/product/dashboard-verified.sqlite3 --file build/YOUR_RUN/results/viewer.html --plant-id YOUR_PLANT_ID --title "생육 시뮬레이션" --run-id YOUR_RUN_ID --scenario-id YOUR_SCENARIO_ID --generated-at 2026-10-19T09:00:00+09:00 --input-kind synthetic_fixture
```

- 입력 종류: `observed_geometry`(관측 형상 기반), `synthetic_fixture`(합성 입력), `assumed`(가정 입력). 실제 출처대로 지정합니다. 이 정보는 등록자의 명시이며 자동으로 과학적 검증을 증명하지 않습니다.
- `--file`은 생성된 viewer.html 또는 PNG/JPEG입니다. 아직 `__DATA__`가 들어 있는 뷰어 템플릿은 거절합니다.
- 식물은 사전 등록되어 있어야 합니다. 파일명만으로 실제 식물과 자동 매칭하지 않습니다.
- 파일은 원본을 변경하지 않고 DB 옆 `simulation-assets/`로 복사합니다. 최대 20 MiB, SHA-256 보존, 동일 식물/실행/시나리오/파일 재등록은 중복 생성하지 않습니다.
- HTML은 sandbox로 격리하고 같은 출처 권한·네트워크·폼 전송을 허용하지 않습니다. 외부 리소스가 필요한 HTML은 지원하지 않습니다. 기존 자체 포함 VTC 뷰어를 대상으로 합니다.

## API 및 미구현

`GET /api/simulations?plant_id=...`, `GET /api/simulations/{id}/asset`.

자동 엔진 실행, 관측 이미지에서 자동 3D 생성, 모든 작물에 대한 생육 모델, 실행 결과 자동 수집/검증은 아직 연결하지 않았습니다. 틔움의 제품명 변경은 연구 엔진이 다른 작물을 지원한다는 의미가 아닙니다. 프런트의 현재 탭은 **기존 실행 결과를 확인하는 화면**입니다.
