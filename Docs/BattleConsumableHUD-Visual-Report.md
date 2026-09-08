# BattleConsumableHUD 외형 변경 결과

## Before
좌측 상단 큰 배경 패널 안에 제목, 가로 88px 슬롯, 빈 칸 라벨, 상시 설명을 표시했다.

## After
큰 배경과 제목을 제거하고 왼쪽 가장자리에 독립적인 세로 슬롯을 배치했다. 기존 슬라이스 스킨, 어두운 반투명 배경, 1px 밝은 테두리, 중앙 50px 아이콘을 사용한다. 슬롯 전체 64px 버튼으로 클릭하며 hover 때 밝아진다. 빈 칸에는 텍스트가 없다. 설명/사용 불가 이유는 hover 동안 슬롯 오른쪽에만 나타난다. 시간의 모래 선택창도 선택 슬롯 오른쪽에 작게 열린다.

## Position
- 기준 화면: 1920 × 1080.
- Slot1 좌상단: 화면 (24, 360). 왼쪽 중앙 앵커, pivot (0, 1), anchoredPosition (24, 180).
- 슬롯: 64 × 64px, 아이콘 50 × 50px, 슬롯 사이 여백 8px, 배치 간격 72px.
- Slot2–5 화면 Y: 432 / 504 / 576 / 648.
- Tooltip: 슬롯 오른쪽 12px 여백, 화면 X=100, 너비 300px, 높이 76–144px.
- 시간의 모래: 선택 슬롯 오른쪽 X=100, 너비 304px, 높이 84 + 표시 행 수 × 48px. 최대 4행 276px.
- 기존 상단 정보/하단 스킬 바의 정적 영역과 겹치지 않는 좌표를 확인했다. 전투 캐릭터/몬스터와의 실제 겹침, 엔진 스케일, 리소스 렌더링은 Maker 검증이 남아 있다.

## Capacity
3칸 높이 208px / 4칸 280px / 5칸 352px. 고정된 첫 슬롯에서 아래로 추가한다. 잠긴 4/5칸은 숨기며, 5→3 감소도 숨김 처리한다. 1 Slot = 1 Item 및 중복 아이콘은 유지한다.

## Preserved Logic
이번 변경 전 스냅샷과 비교하여 RootDesk/ui/map/Global 보호 파일 479개의 SHA-256이 동일하다. Inventory, Drop, Union, 서버 Item Use, Time Sand 효과/검증, All Cure 검증, 포션 수치, 아이템 ID 및 ConsumableDefinitions는 변경하지 않았다. HP HUD, Skill Bar, Enemy Intent도 변경하지 않았다. HUD의 기존 InventoryRevision/RPC/클릭 검증 흐름은 유지하고 표시와 배치만 조정했다. 새 단축키는 없다.

## UI Test
아래 PASS는 실제 mLua 메서드를 실행하고 엔진/이벤트/RPC를 mock한 오프라인 결과다.

| 상태 | 오프라인 결과 | Maker 화면/입력 |
|---|---|---|
| Empty | PASS | 미실행 |
| Potion | PASS | 미실행 |
| Duplicate | PASS | 미실행 |
| Hover | PASS | 미실행 |
| Disabled | PASS | 미실행 |
| Union +1 | PASS | 미실행 |
| Union +2 | PASS | 미실행 |
| Click Use | PASS | 미실행 |
| Time Sand | PASS | 미실행 |

기존 회귀 33개 + 세로 HUD A–I 9개 = 42/42 PASS. UIBuilder 구조/8개 UUID 바인딩/경계/보호 파일 비교 PASS. git diff --check PASS.

Maker MCP 도구가 제공되지 않아 refresh/build/play/logs/실제 hover 테스트는 실행하지 못했다. 따라서 최종 네이티브 UI 판정은 FAIL(검증 근거 미확보)이며 실제 기능 실패를 관찰한 것은 아니다.

UIBuilder 오류는 0개. 모바일 88px 권장 크기 경고 5개는 요청한 소형 슬롯/선택창 규격에 따른 것이다. 툴팁의 부모 영역 초과는 오른쪽 표시를 위한 의도된 배치다.

## Files Modified
게임 파일:
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/RootDesk/MyDesk/02_UI/BattleConsumableHudComponent.mlua
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/ui/BattleConsumableHUD.ui

빌더 및 검증 파일:
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/.builder-work/build-consumable-hud.cjs
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/.builder-work/upgrade-consumable-hud.cjs
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumables_test.py
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumables_shogun_test.py
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumable-ui-check.cjs
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumable-vertical-ui-test.py

이번 작업의 비교 기준 및 보고서:
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumable-visual-protected-hashes.json
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/fixtures/BattleConsumableHud-before-vertical.mlua
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Docs/BattleConsumableHUD-Visual-Report.md

기존 working tree에 있던 다른 수정/추가 파일은 이번 외형 변경에 포함하지 않았다.

## Git
Commit: NO
Push: NO
