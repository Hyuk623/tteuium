# 변경 및 검증 기록 — 2026-10-18

원격 `fish-444/tomato` HEAD와 로컬 HEAD는 `d1f89a4cca56994c0abe2b97f4f6f37603a8391a`로 일치함을 확인했습니다. 기존 미커밋 product/ 작업 위에 확장했으며 기존 연구 코드는 수정하지 않았습니다. GitHub push/PR은 만들지 않았습니다.

## 이번 작업에서 수정한 파일

- `product/backend/api.py`: Plant State/관측 입력 API, 이미지 출처 저장.
- `product/backend/schemas.py`: 관리 유형, 출처/status, 수동/모의 생육 계약.
- `product/backend/db/schema.sql`: 호환 가능한 image_sources 테이블 추가.
- `product/backend/services/ingestion.py`: 수동/모의 관측 타입 지원 명시.
- `product/frontend/dashboard/index.html`: 홈/성장/환경/기록 4개 화면.
- `product/frontend/dashboard/app.js`: API 연결, 기간/장치/출처 분리 그래프, 이미지 비교, 관측/관리 저장, 실패/빈 데이터 처리.
- `product/frontend/dashboard/style.css`: 가정 사용자용 큰 카드, 반응형 메뉴/레이아웃.
- `product/tests/test_http_e2e.py`: 14일 mock 생성/재실행 HTTP 검증 추가.
- `product/README.md`: 실행 및 실제 구현 범위 설명 갱신.
- `product/docs/roadmap.md`: 6주 산출물/완료 기준/전문가 결정 재구성.
- `handoff/LOG.md`: 기존 내용을 보존하고 작업 결과 추가.

## 이번 작업에서 추가한 파일

- `product/backend/services/dashboard.py`: Plant State와 근거 기반 안전한 확인 안내.
- `product/device_contract/seed_demo.py`: HTTP를 통한 14일 모의 환경/성장/이미지 생성기.
- `product/frontend/dashboard/demo-before.svg`, `demo-now.svg`: 실제 사진이 아닌 예시 그림.
- `product/tests/test_dashboard.py`: 출처/식물 격리, 기간, 안전 안내, 입력 검증, 영속성.
- `product/docs/observation-mvp.md`: 아키텍처, 데이터 모델, API, provenance, PostgreSQL 이전 범위.
- `product/docs/delivery.md`: 이 문서.
- `handoff/OBSERVATION_DASHBOARD_2026-10-18.md`: 구현 전 영문 브리프 및 결과.

기존 CSV adapter는 검토/재사용했으며 변경하지 않았습니다. DB 및 화면 캡처 등 생성 결과는 build/product/에 있습니다.

## 검증 결과

- API/계약/규칙/어댑터/영속성/실제 HTTP 테스트 **21개 통과**.
- Starlette의 httpx 테스트 클라이언트 폐기 예정 경고 1건; 기능 테스트 실패 아님.
- JavaScript 문법 확인 통과.
- 실제 브라우저: 홈, 성장 3종 그래프와 이미지 비교, 7일 기간 전환, 환경 4종 그래프, 관리 기록 저장 후 목록 반영 확인.
- 390px 모바일 홈 레이아웃 확인, 브라우저 오류 로그 없음.
- 검증 화면: `build/product/dashboard-home.jpg`, `dashboard-mobile.jpg`, `record-verified.jpg`.
- 제한 환경에서는 로컬 테스트가 정지하여 허용된 로컬 실행 환경에서 다시 검증했습니다.
- 실제 하드웨어, PostgreSQL, 농학적 정확도, 외부 배포는 검증하지 않았습니다.

## 인수

[실행 방법](../README.md), [6주 로드맵](roadmap.md), [설계 계약](observation-mvp.md)을 순서대로 확인하세요. 기본 서버 실행 후 seed_demo를 한 번 실행하면 별도 하드웨어 없이 4개 화면을 사용할 수 있습니다. 수동 기록은 실제 저장되지만 샘플 식물의 센서/생육/그림은 모의입니다.
