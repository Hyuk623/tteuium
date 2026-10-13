# 깃 푸시 준비 — 점검 결과와 실행 순서 (2026-10-13)

저장소 폴더는 **아직 git 저장소가 아닙니다**(`git rev-parse` 확인). `.gitignore`와 `.gitattributes`는 제가 방금 저장소 루트에 넣어 두었습니다. 아래 순서대로 하면 푸시까지 갑니다.

## 0. 먼저 알아야 할 것 두 가지

**① 이 폴더는 OneDrive 안에 있습니다.** OneDrive가 `.git` 폴더를 동기화하면서 git이 쓰는 잠금 파일과 충돌할 수 있습니다. git 작업 중에는 동기화를 잠시 멈추거나, OneDrive 설정에서 `.git`을 동기화 제외로 두세요. 치명적이진 않지만 드물게 인덱스가 깨져 `git status`가 이상해집니다.

**② git 명령은 직접 터미널에서 돌리는 게 낫습니다.** 제가 브리지로 돌릴 수도 있지만, 측정해 보니 이 경로에서 파일 단위 작업이 분당 수 개 수준까지 떨어집니다(`du`가 20초 안에 끝나지 않는 폴더가 여럿). git init/add/commit은 수만 개 파일을 만지므로 Windows 쪽에서 직접 하는 편이 비교할 수 없이 빠릅니다.

## 1. 용량 점검 결과 (측정값)

| 폴더 | 크기 | git 추적 |
|---|---|---|
| `build/` | 수 GB (항목 3,811개 → 정리 후 1,221개) | **제외** |
| `data/raw/` | 103 M | **제외** |
| `tomato_photos_organized_/` | 103 M | **제외** |
| `토마토/` | 53 M (스크린샷) | **제외** |
| `tomato_photos_by_view_/` | 50 M | **제외** |
| `date_data/` | 16 M (HEIC 9장) | **제외** |
| `tools/` | 16 M | 추적 |
| `tomato3d/` | 3.6 M | 추적 |
| `data/records/` | 2.9 M | **추적** (사람이 만든 관측 기록) |
| `tests/` | 2.5 M | 추적 |
| `handoff/` | 5.3 M | 추적 |
| `docs/` 136 K, `flow/` 104 K, `config/` 8 K, `measurements/` 4 K | | 추적 |

추적 대상 안의 파일 구성: `.py` 458, `.md` 416, `.json` 33, `.csv` 28, `.html` 20, `.cjs` 10, `.js` 9, `.png` 3, `.xlsx` 2, `.rgg` 2, `.txt` 2, `.svg` 1, `.lpy` 1, 그리고 `__pycache__`의 `.pyc` 508개(제외됨).

**100 MB를 넘는 파일은 없습니다.** 가장 큰 추적 대상은 `data/records/compound_bend_types_20261010/compound_bend_examples_contact_sheet_20261010.png` 2.4 M입니다. GitHub 거부 한도에 걸릴 파일이 없습니다.

`measurements/`는 템플릿 CSV 2개와 README뿐(4 K)이라 추적합니다 — 이전 안내에서 "내용을 못 봤다"고 적었던 항목은 확인 완료입니다.

## 2. 비밀값 점검 결과

코드·문서·기록 전체를 훑었고 **하드코딩된 키나 비밀번호는 없습니다.**
- `tomato3d/topview/measure2d.py`는 Roboflow 키를 `os.environ.get("ROBOFLOW_API_KEY")`로 읽습니다 — 올바른 방식입니다.
- `tools/leaf_preprocess_lab.py`의 토큰은 실행할 때 `secrets.token_urlsafe(32)`로 새로 만드는 세션 토큰이라 저장되지 않습니다.
- 나머지 `token` 일치 항목은 전부 변수명·식별자(`token()`, `tokenizer`, `X-Local-Token` 헤더 이름)입니다.

`.gitignore`에 `.env`, `*.pem`, `*.key`, `kaggle.json`, `credentials*.json`, `service_account*.json`을 넣어 두었습니다. 다만 **문자열 리터럴 전수 검사는 시간 초과로 끝까지 돌리지 못했으니**, 커밋 전에 3단계의 `git grep`을 한 번 돌려 확인하세요. 루트의 메모 파일(`3D도움.txt`, `자동라벨링.txt`, `중첩잎 판정.txt`)은 각 4~8 K이고 추적 대상이니 눈으로 한 번 보시는 게 좋습니다.

## 3. 실행 순서

```
cd "C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis"

git init
git add -A
git status --short | more
```

`git status`에 **사진·`build/`·`runs/`·`.pyc`가 보이면 안 됩니다.** 보이면 `.gitignore`가 안 먹은 것이니 멈추세요.

커밋 **전에** 비밀값 확인:

```
git grep -nEI "(api[_-]?key|secret|token|password)[\"']?[ ]*[:=][ ]*[\"'][A-Za-z0-9_-]{16,}[\"']"
```

아무것도 안 나와야 합니다. 뭔가 나오면 그 파일을 `.gitignore`에 넣고 `git rm --cached <파일>`로 인덱스에서 빼세요. **한 번 커밋된 비밀값은 되돌려도 히스토리에 남습니다.**

그다음:

```
git commit -m "Initial import: P1-P4 pipeline, contracts, records, flow map"
git branch -M main
git remote add origin <원격 주소>
git push -u origin main
```

## 4. 무엇이 올라가고 무엇이 빠지는가

**올라감** — `tomato3d/`, `tools/`, `tests/`, `flow/`, `handoff/`, `docs/`, `config/`, `measurements/`, `data/records/`(CSV·JSON·엑셀 + 관측 근거 PNG), 루트의 `*.md`·`*.txt`·`pyproject.toml`

**빠짐** — `build/`, `runs/`, `date_data/`, `data/raw/`, 사진 폴더 3개, `__pycache__`, 모든 `.HEIC`·`.jpg`·`.npy`·`.zip`·`.pdf`, PNG(단 `data/records/`·`docs/`·`flow/` 안은 예외로 추적)

## 5. 빠지는 것에 대한 주의 — 의식적으로 고르셔야 하는 지점

`build/`를 제외하면 **발행된 예측 패키지와 네이티브 실행 증거가 git 히스토리에 남지 않습니다.** 이 프로젝트는 "산출물은 불변, 해시로 고정"을 지켜 왔는데, 그 산출물 자체가 저장소 밖에 있게 됩니다. 영향을 받는 것들:

`build/forecast_20261012_07`, `build/p1_state_20261013_03`, `build/topview_20261012_02`, `build/stress_20261013_01`, `build/p2_empirical_light_field_20261013_01`, `build/rim_click_side_20261013_01`

선택지는 둘입니다.
1. **그대로 둔다** — 보고서가 경로로 가리키고 실물은 로컬/OneDrive에만 있음. 재현은 코드와 `data/records/`로 다시 돌려서 한다.
2. **핵심 패키지만 따로 올린다** — manifest와 해시 파일처럼 작은 것만 git에 넣고(수십 KB), 큰 렌더·점군은 릴리스 첨부나 별도 보관으로 돌린다.

2번이 "근거는 추적 가능하게, 용량은 밖에" 라는 지금까지의 원칙과 맞습니다. 원하시면 각 패키지의 manifest·checks·해시만 골라 `evidence/` 같은 폴더로 복사하는 규칙을 만들어 드리겠습니다.

## 6. 정리 중인 폴더 하나

`build/_purge_20261013/` 에 삭제 예정 임시 산출물 1,675개를 모아 두었습니다. `build/`는 어차피 git에서 제외되니 **푸시에는 영향이 없습니다.** 용량 확보용이니 Windows에서 통째로 지우세요:

```
rmdir /s /q "build\_purge_20261013"
```
