# 사람이 재는 값 (형질 파이프라인 입력)

파이프라인(`tools.plant_batch`, `tools.plant_pipeline`)은 이 폴더의 두 파일만 사람에게 받습니다. 없으면 대리값까지만 냅니다.

## leaf_area.csv — 잎 면적 보정 (4~6개체)

`leaf_area.template.csv` 를 `leaf_area.csv` 로 복사해서 적습니다.

- `plant_id`: 사진 폴더 이름과 같게 (예: dwt_05)
- `leaf_area_cm2`: 잎을 떼지 않고 잰 개체 전체 잎 면적. 소엽마다 길이×폭(cm)을 재고, 합계에 계수 k 를 곱합니다.
  k 는 소엽 몇 장을 보드 위에 펴서 사진으로 잰 면적 ÷ (길이×폭) 의 평균입니다 (토마토 소엽은 보통 0.6~0.7 근처).
- `method`, `date`: 메모

3개체 이상이면 한 개체씩 빼고 맞춘 오차가 같이 나옵니다. 크기가 다른 개체(작은 것·중간·큰 것)를 고르면 보정이 안정적입니다.

## light.csv — PPFD 와 일장

`light.template.csv` 를 `light.csv` 로 복사합니다.

- `plant_id`: 개체별로 다르면 개체마다 한 줄, 모두 같으면 `*` 한 줄
- `ppfd_umol_m2_s`: 식물 꼭대기 높이에서 광량계로 잰 PPFD
- `photoperiod_h`: 하루 조명 시간

DLI = PPFD × 일장 × 3600 / 1,000,000 (mol m⁻² d⁻¹). 개체가 받는 빛 = DLI × 위에서 본 잎 면적.

적은 뒤 `python -X utf8 -m tools.plant_batch --out <실행 폴더> --summary-only` 로 표만 다시 만듭니다.
