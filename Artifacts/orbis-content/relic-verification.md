# 오르비스 기념 유물 구현 검증 (2026-10-24)

구현·기능 검사 PASS. 자연 전술 1→16 완주의 회복 총량/구매 선택 평가는 대기다.

- 정적/편집기: node --test tools/balance-schema.test.cjs Artifacts/orbis-content/verify-content.test.cjs — 115 PASS.
- 실제 Lua: ORBIS_LUA_PATH를 lupa 설치 경로로 지정하고 python Artifacts/orbis-content/verify-relics.py — 기존 3,900개·상점 경로·기존 상품 384개·신규 기념 상품 384개·5직업·6효과 경계 PASS.
- 기존 전투: LUPA_PATH를 같은 설치 경로로 지정하고 python tools/combat-issue-test.py — 1,152개 및 기존 아이콘/명령/큐 검사 PASS.
- 어휘: node tools/check-balance-vocab.cjs — 37개 특수 효과·3개 획득 종류 포함 PASS.
- 공백: git diff --check — PASS. 기존 줄바꿈 정규화 안내만 있다.
- Maker: Refresh 빌드 오류 0, 기존 IsPCPlatform 사용 중단 경고 1. 최종 깨끗한 재실행 오류 0, 57개 정의(프리미엄 포함)와 16단계 시작 확인.

기능 실행은 relic-maker-verification.json, 실제 Lua는 relic-lua-verification.json, 원본 아이콘은 relic-resources.json을 따른다. 앞선 Maker QA의 준비 오류도 기록에 남겼으며 제품 실행 오류와 구분했다. 보스/웨이브 전멸 가속·임시 구매 골드·아이스 시전자 배치·회복 보유 fixture를 사용한 검사는 자연 플레이로 분류하지 않는다.

새 게임 데이터에 치트 수치·영구 QA 런타임을 추가하지 않았다. 새 발동 로직의 codeblock은 Maker Refresh가 생성했다. 기존 오르비스 맵/모델·세션과 공통 이동 원본은 이번 유물 구현에서 수정하지 않았다.
