# BattleConsumableHUD 메이플풍 외형 보정

## Visual Direction
기존 둥근 슬라이스 리소스를 재사용하여 회청색 외곽, 남색 내부, 밝은 은청색 가장자리와 작은 그림자를 겹쳤다. 큰 배경 패널 없이 독립적인 퀵슬롯을 유지한다. 실제 리소스 렌더링의 시각적 완성도는 Maker 확인이 남아 있다.

## Position
Anchor bottom-left / Panel pivot (0,0) / 왼쪽 32px, 아래 184px.
1920×1080 첫 슬롯 좌상단 (32,824). 기존 하단 스킬 바 시작 Y=906과 슬롯 하단 Y=896 사이 10px 간격 유지.
HUD 크기: 3칸 232×72 / 4칸 312×72 / 5칸 392×72px.
툴팁과 선택창은 선택 슬롯 오른쪽 위에 표시하고, 하단은 Y=812로 하단 스킬 바 위에 둔다.
채팅창의 실제 위치는 Maker MCP 미연결로 확인하지 못했으므로 채팅창 바로 위 정렬 완료를 주장하지 않는다.

## Slot Style
72px 외곽 SlotRim(#788CA5) + 64px 내부 SlotBackground(#303E55)로 사방 4px 프레임을 구성한다. SlotFrame은 기존 슬라이스 가장자리에 은청색(#B3CAE0), 1px 밝은 outline을 사용한다. 외곽에는 2px 그림자를 준다. Hover는 밝은 청백색, Disabled는 아이콘 RGB 0.45에서 0.70으로 올리고 불투명도는 1로 유지했다. 프레임 위치/표시는 사용 가능 여부와 무관하게 유지한다. 툴팁/선택창은 #29374C와 같은 회청색 테두리로 통일했다.

## Icon Alignment
아이콘 56×56px. SlotTemplate 자식이며 anchor/pivot=(0.5,0.5), anchoredPosition=(0,0).
외곽 대비 사방 8px 여백, 내부 대비 사방 4px 여백. 렌더 순서는 외곽→내부→프레임→아이콘. 자식 raycast를 끄고 슬롯 전체 Button 클릭을 유지한다.

## Removed
현재 구조에 Count/수량 라벨은 이미 없었다. 빈 슬롯 문자열도 공백이다. 신규 숫자 표시는 추가하지 않았으며, 동일 아이템은 개별 슬롯에 반복 표시한다. 숫자를 제거하기 위한 데이터 변경은 없다.

## Capacity
3 / 4 / 5칸 오프라인 PASS. 슬롯 간격 8px, 배치 간격 80px. 기존 슬롯 위치 고정, 오른쪽 확장, 잠긴 슬롯 숨김 유지.

## Preserved Logic
Inventory / Drop / Union / Use / Time Sand / All Cure 변경 없음. ConsumableDefinitions, Item ID, 수치, 서버/Turn 처리 변경 없음. HP HUD / Skill Bar / Enemy Intent 변경 없음.
보호 파일 479개 SHA-256 동일 확인. 변경한 mLua는 hover/disabled 색상뿐이다.

## UI Test
| 항목 | 오프라인 |
|---|---|
| Empty | PASS |
| Filled | PASS |
| Duplicate | PASS |
| Disabled | PASS |
| Hover / exit | PASS |
| Click | PASS |
| Union +1 | PASS |
| Union +2 | PASS |
| Time Sand | PASS |
| 정적 배치 / 스킬 바 분리 / 아이콘 정렬 | PASS |

기존 회귀 33개 + HUD 9개 = 42/42 PASS. UIBuilder 구조/8개 UUID 바인딩/프레임 레이어/보호 파일 검사 PASS. 빌더 오류 0개. 소형 버튼에 따른 모바일 88px 권장 경고 5개 유지.
Maker MCP 도구가 없어 build/play/실제 입력/스크린샷 미실행. 네이티브 최종 판정 FAIL(검증 근거 미확보); 실제 기능 실패를 관찰한 것은 아니다.

## Files Modified
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/RootDesk/MyDesk/02_UI/BattleConsumableHudComponent.mlua
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/ui/BattleConsumableHUD.ui
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/.builder-work/build-consumable-hud.cjs
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumable-ui-check.cjs
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Artifacts/tests/consumable-vertical-ui-test.py
- C:/Users/user/Documents/Workspace/MapleTactics-all-integration/Docs/BattleConsumableHUD-MapleStyle-Report.md

## Git
Commit: NO
Push: NO
