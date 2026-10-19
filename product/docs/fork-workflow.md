# 개인 Fork에서 개발하고 팀 코드와 병합하기

- 개인 Fork: https://github.com/Hyuk623/tteuium
- 원본: https://github.com/fish-444/tomato
- 개발 브랜치: `feature/tteuium-dashboard`
- 로컬 remote: `origin`은 원본, `fork`는 개인 Fork입니다. 원본 main에 직접 push하지 않습니다.

## 팀원에게 공유

Actions의 `Deploy Tteuium demo`가 성공하면 Pages 주소가 표시됩니다. 배포물은 새로 생성한 모의 데이터와 정적 화면만 포함합니다. 실제 DB, 수동 관리 기록, 실제 관측/시뮬레이션 파일은 자동 업로드하지 않습니다. 데모에서 입력한 기록은 해당 브라우저에만 저장됩니다. 실제 관측 입력/공용 기록 저장은 로컬 서버 기능입니다.

## 이후 업데이트

```powershell
git switch feature/tteuium-dashboard
git add product
git commit -m "Update Tteuium dashboard"
git push fork feature/tteuium-dashboard
```

## 원본의 최신 작업 가져오기

작업 파일을 먼저 커밋한 다음 실행합니다. 다른 팀원의 변경을 확인하며 충돌이 있는 파일만 조정합니다.

```powershell
git fetch origin
git merge origin/main
# 충돌이 있으면 수정 후 git add / git commit
git push fork feature/tteuium-dashboard
```

## 원본으로 병합

원본 저장소에서 base=`fish-444/tomato:main`, head=`Hyuk623/tteuium:feature/tteuium-dashboard`로 Pull Request를 만듭니다. Product Layer와 연구 엔진 경계, 테스트 결과, DB 변경을 함께 검토한 뒤 원본 관리자가 병합합니다. 이 작업에서 원본으로 자동 병합하지 않습니다.

## Pages 직접 빌드

```powershell
build/product-venv/Scripts/python -m product.export_pages
python -m http.server 8020 --directory build/pages
```

출력은 build/pages입니다. 새 임시 DB에서 모의값만 생성하므로 실행 중인 서버 DB를 읽지 않습니다. HTML, JS, CSS, SVG 및 공개용 JSON 스냅샷만 배포합니다. `.github/workflows/pages.yml`은 개인 Fork에만 배포되도록 제한되어 있습니다.
