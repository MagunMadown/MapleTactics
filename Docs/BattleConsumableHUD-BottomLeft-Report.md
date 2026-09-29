# BattleConsumableHUD 왼쪽 아래 배치 보정

## Layout Choice
가로 배치. 요청 우선순위에 맞춰 왼쪽 아래에서 3개 슬롯을 한 묶음으로 읽고, 4/5칸은 오른쪽에 추가한다. 기존 아이콘의 parent는 슬롯이며 anchor/pivot도 중앙이었다. 따라서 부모 불일치가 원인이라는 증거는 없으며, 실제 화면의 떠 보이는 원인은 Maker 확인 전 확정하지 않는다.

## Position
Anchor: bottom-left. Panel pivot: (0,0). 시작 좌표: 화면 왼쪽에서 32px, 아래에서 184px. 1920×1080에서 첫 슬롯 좌상단은 (32,824), 전체 하단은 Y=896이다.

기존 하단 스킬 바는 정적 기준 Y=906부터 시작하므로 10px 간격을 확보하려고 권장 아래 여백 110–160px보다 조금 높게 배치했다. 툴팁과 시간의 모래 선택창은 해당 슬롯 오른쪽 위에 열리며 하단이 화면 Y=812이므로 슬롯/하단 스킬 바를 가리지 않는다.

전체 HUD 크기: 3칸 232×72 / 4칸 312×72 / 5칸 392×72px.

## Slot
슬롯 72×72px / 아이콘 56×56px / 슬롯 사이 여백 8px / 배치 간격 80px.
아이콘 내부 여백은 사방 8px. 빈 슬롯 텍스트와 큰 외곽 패널은 없다.

## Alignment
SlotTemplate(전체 영역 Button) 아래 SlotBackground, SlotFrame, Icon을 둔다. 배경→프레임→아이콘 순서로 표시한다. 각 자식의 anchor/pivot은 center, anchoredPosition은 (0,0)이다. 자식은 RaycastTarget=false로 슬롯 전체 클릭을 유지한다. 프레임은 기존 슬라이스 리소스의 테두리만 표시하며 hover 때 밝아진다. Disabled는 기존처럼 아이콘 색상만 어둡게 한다.

## Capacity
3 / 4 / 5칸 모두 PASS(오프라인). 슬롯 X는 0 / 80 / 160 / 240 / 320으로 고정되며 추가 슬롯은 오른쪽에 표시된다. 잠긴 슬롯 숨김과 기존 슬롯 위치 유지.

## Preserved Logic
Inventory / Drop / Union / Use / Time Sand / All Cure 변경 없음.
ConsumableDefinitions, 포션 수치, Item ID, HP HUD, Skill Bar, Enemy Intent 변경 없음.
보호 파일 479개 SHA-256 동일. HUD 수정은 배치/크기/정렬/프레임 강조에 한정했다.

## UI Test
아래 PASS는 엔진/RPC를 mock한 실제 mLua 메서드 실행 결과이며 네이티브 렌더링 결과가 아니다.

| 항목 | 오프라인 |
|---|---|
| Empty | PASS |
| Filled / Duplicate | PASS |
| Disabled | PASS |
| Hover / exit | PASS |
| Click | PASS |
| Union +1 | PASS |
| Union +2 | PASS |
| Time Sand / Cancel | PASS |
| 1920×1080 정적 경계 / 중앙 정렬 | PASS |

기존 회귀 33개 + HUD 시나리오 9개 = 42/42 PASS. UIBuilder 구조/8개 UUID 바인딩/보호 파일 검사 PASS. 빌더 오류 0개, 요청한 소형 버튼에 따른 모바일 88px 권장 경고 5개.
Maker MCP 미연결: build/play/실제 hover/스크린샷 미실행. 네이티브 UI 최종 판정 FAIL(검증 근거 미확보). 실제 채팅/시스템 버튼, 캐릭터 발밑, 프레임 리소스와 아이콘의 시각적 결합은 Maker 확인이 남아 있다.

## Files Modified
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/RootDesk/MyDesk/02_UI/BattleConsumableHudComponent.mlua
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/ui/BattleConsumableHUD.ui
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/.builder-work/build-consumable-hud.cjs
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumables_test.py
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumables_shogun_test.py
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumable-ui-check.cjs
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumable-vertical-ui-test.py
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Docs/BattleConsumableHUD-BottomLeft-Report.md

consumable-vertical-ui-test.py는 기존 파일명을 유지하되 현재 가로 배치 기대값으로 갱신했다. 이전 Visual-Report는 당시 세로 배치 작업 기록이며 최신 배치는 이 문서를 따른다.

## Git
Commit: NO
Push: NO
