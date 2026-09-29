# 사람이 해야 할 작업

우선순위 순서입니다. 끝나면 `python -X utf8 -m tools.plant_pipeline --all` 을 다시 실행하면 결과가 반영됩니다.

1. [dwt_02] dwt_02 짝짓기 충돌 3건 해결 (모순된 결정 때문에 해당 소엽 묶음 전체가 빠져 있음). 틀린 결정을 바꾸고 '결정 파일 저장'
   - 위치: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis\build\pipeline_20260929_015111\CONFLICTS_REVIEW.html`
2. [dwt_03] dwt_03 짝짓기 충돌 2건 해결 (모순된 결정 때문에 해당 소엽 묶음 전체가 빠져 있음). 틀린 결정을 바꾸고 '결정 파일 저장'
   - 위치: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis\build\pipeline_20260929_015111\CONFLICTS_REVIEW.html`
3. [dwt_02] dwt_02 소엽 대응 검토 18개 (같은 소엽 후보 1, 보임 정도 17). 페이지를 열고 고른 뒤 '결정 파일 저장' → 다운로드 폴더에 그대로 두면 다음 실행이 읽습니다.
   - 위치: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis\build\pipeline_20260929_015111\dwt_02\candidates\review.html`
4. [dwt_03] dwt_03 소엽 대응 검토 14개 (같은 소엽 후보 0, 보임 정도 14). 페이지를 열고 고른 뒤 '결정 파일 저장' → 다운로드 폴더에 그대로 두면 다음 실행이 읽습니다.
   - 위치: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis\build\pipeline_20260929_015111\dwt_03\candidates\review.html`
5. [dwt_04] dwt_04 소엽 대응 검토 14개 (같은 소엽 후보 3, 보임 정도 11). 페이지를 열고 고른 뒤 '결정 파일 저장' → 다운로드 폴더에 그대로 두면 다음 실행이 읽습니다.
   - 위치: `C:\Users\sho36\OneDrive\작업물저장소\홈팜\Tomato 3D phenotyping analysis\build\pipeline_20260929_015111\dwt_04\candidates\review.html`
6. [dwt_01] dwt_01 모델 2 라벨: 모델 1 소엽 박스를 복사해 잎끝 방향 클래스(side_left/side_right/front/back)로 바꾼 export. 정면/후면 기준 한 줄을 먼저 정해 주세요.
7. [dwt_02] dwt_02 모델 2 라벨: 모델 1 소엽 박스를 복사해 잎끝 방향 클래스(side_left/side_right/front/back)로 바꾼 export. 정면/후면 기준 한 줄을 먼저 정해 주세요.
8. [dwt_03] dwt_03 모델 2 라벨: 모델 1 소엽 박스를 복사해 잎끝 방향 클래스(side_left/side_right/front/back)로 바꾼 export. 정면/후면 기준 한 줄을 먼저 정해 주세요.
9. [dwt_04] dwt_04 모델 2 라벨: 모델 1 소엽 박스를 복사해 잎끝 방향 클래스(side_left/side_right/front/back)로 바꾼 export. 정면/후면 기준 한 줄을 먼저 정해 주세요.

## 받은 결정 (코드 변경이 필요한 것은 Claude 가 반영)

- pose_candidates: "use_as_diagnostic"
- s6_guard: "wait_for_codex"
- direction_rule: "잎끝이 카메라면 front, 뒤면 back"
