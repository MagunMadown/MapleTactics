# MapleTactics 후속 작업 및 튜토리얼 오류 수정 계획

작성일: 2026-10-11\
기준 브랜치: `codex/battle-session-responsibility-split`\
기준 커밋: `2cec83a` (develop `f85c18d` 이후 작업별 9개 커밋)

이 문서는 현재 변경의 실행 결과와 남은 검증 기준을 정리한다. 2026-10-11에 튜토리얼 수정과 BS-01~07의 코드 분리를 반영했다. 상세 증거는 [통합 검증 기록](Artifacts/tutorial-session-refactor/verification.md)을 따른다. 게임 전체 범위와 단계 상태는 [M1 GDD](Docs/MapleTactics-M1-GDD.md), [Phase 1](Docs/MapleTactics-M1-Phase1.md), [Roadmap](Docs/MapleTactics-Roadmap.md)을 따른다.

## 1. 현재 상태와 우선순위

- 로비·전투 일반 이동의 착지 검사를 공통화했다. 완료 후 0.5초 유예, X·Y 오차 0.05 월드 단위 초과 시 한 번 보정하며 전투 턴 완료는 이 검사를 기다리지 않는다.
- 전투 UI 상태, 적 계획·스냅샷·전조·턴 실행, 스킬·투사체 실행, 피해·회복·버프, 유틸리티 실행을 책임별 로직으로 분리했다.
- `BattleSessionComponent`는 7,320줄에서 2,732줄로 줄였다(주요 분리 후 2,745줄, 보조 함수 6개 정리 후 2,732줄). 공개 메서드 288개의 인자·실행 공간을 유지하고 사망/승패·제어/이동·상태 효과·큐·모션/표시·진입/결과·즉시 행동/보스 구현을 담당 로직으로 분리했다. 세션에는 호출 연결, RPC 검증, 상태 동기화와 생명주기 처리를 남겼다.
- 기존 전투 회귀 194개 그룹과 새 분리 회귀 91개 그룹, 튜토리얼 2개 모음을 포함한 18개 모음을 최종 코드로 실행해 모두 통과했다. 새 모음은 실제 Lua 본문과 상태 불변식을 검사한다.
- 튜토리얼 테스트의 이전 함수 위치·4단계 fixture를 현재 진입/규칙/표시 구조와 10단계 계약에 맞춰 복구했다. 실제로 확인한 3~6번 슬롯 강조 누락과 안내 키 축약 문제도 수정했다.
- Maker에서 신규 격리 키의 최초 완료 저장, 완료 계정 자동 진입 제외, 최종 코드 재플레이 10단계·총 4마리 처치·완료 저장·로비 복귀, 로비 이동과 연습 전투 순간이동 후 이동 복귀를 확인했다. 슬롯 재정렬·결과 확인·재플레이 시작은 실제 클라이언트 RPC로 검증했으며 실제 포인터 조작으로 취급하지 않는다.
- 2026-10-12 추가 검증: 로비와 전투 20개 맵의 기본 이동·착지 검사에서 전투 이동/검사 48회가 모두 일치하고 보정 0회였다. 대표 맵의 경계·점유 거절, 순간이동 후 복귀, 이동 중 맵 전환 정리를 확인했다. 홉 애니메이션은 로비 1배/전투 3배 차이가 남아 있으며 코드 수정 없이 [맵별 이동 검증 기록](Artifacts/tutorial-session-refactor/map-pointer-verification/verification.md)에 기록했다. 실제 PC 포인터는 사용자 요청으로 유예했다.
- 2026-10-12 후속 검증: 홉 애니메이션을 공통 로비 기준 1배로 통일했다. 실제 기본값 프로필 비교와 이동 37개·제어/이동 20개 회귀, 전투 20개 맵 기본 이동·착지 41/41(보정 0), 양끝·대표 점유 거절, 정밀 이벤트 검사 40개를 통과했다. 로비 반전·연속 입력/양끝, 실제 S키 순간이동 후 A/D 복귀, 이동 중 맵 전환 정리를 재검증했다. 최종 추종 좌표 오차 0은 사람의 렌더 체감 판단과 구분하며, 실제 포인터·물리 정밀 입력은 유예한다. [후속 이동 검증 기록](Artifacts/tutorial-session-refactor/movement-feel-verification/verification.md)을 따른다.
- 2026-10-12 보조 로직 정리: 턴·타일 행동 판정, 방향 변환, 스킬 속도 보정, 피해 숫자 묶음 소비와 홉 시간 보정을 기존 담당 로직으로 위임했다. 공통 이동의 같은 홉 보정 계산도 한 곳으로 모았다. 공개 계약 288개와 이전 본문 6개 동일성, 보조 검사 7개를 포함한 회귀 18개 모음, Maker 전투/로비 이동·장전·실행·피해 숫자 표시를 확인했다. [보조 로직 검증 기록](Artifacts/tutorial-session-refactor/auxiliary-logic-cleanup/verification.md)을 따른다.
- 기존 GDD는 Phase 1 진행 상태다. 구조 분리 검증을 근거로 게임 기능·출시 검증의 완료 상태를 올리지 않는다. 실제 포인터, 모바일/다중 계정, 전투맵별 화면·체감 검토는 남아 있다.

- 2026-10-12 정상 진행 후속 검증: 상·하단 각각 20전투, 상점 구매/무구매·다음 지역·반대 경로 잠금·새 런 초기화와 v3 시작 조건/4·4·4·8 집계·실제 기록 UI를 확인했다. 전투는 실제 ApplyDamage 처리로 가속했으므로 일반 전술 조작만의 완주와 구분한다. 공통 이동의 nil 재탐색 시간과 다른 경로의 거절 응답이 지도를 바꾸는 오류 두 곳을 수정했다. 최종 회귀 20모음(전투/코어 16개 296그룹), schema 74개·vocabulary·재시작 저장 키 기본값 및 build/runtime 오류 0을 확인했다. [상세 검증 기록](Artifacts/normal-run-validation-20261012/verification.md).

수행한 순서: **튜토리얼 테스트 복구 → Maker 재현·수정 → BS-01~07 구현 → 통합 검증 → 정상 상점/양쪽 경로·기록 후속 검증**. 남은 작업에는 P0-05 Column/Value 기본 진단 구현, 일반 전술 전체 완주, 실제 포인터·실기기·화면/체감 검사가 포함된다.

## 2. 반드시 유지할 구조

[AGENTS.md](AGENTS.md)의 전투 세션 책임 분리와 일반 이동 일관성 규칙을 따른다.

- 세션은 책임별 로직 호출, 인자·결과 전달, 상태 동기화, RPC 검증과 생명주기 연결을 담당한다. 계산·판정·실행·표시 데이터 생성 본문은 각 책임의 `.mlua`에 둔다.
- 기존 담당 로직·실행기를 먼저 재사용한다. 모든 구현을 하나의 새 세션 로직으로 옮기거나 같은 책임의 복사 구현을 남기지 않는다.
- 플레이어·맵·진입·요청·타이머·피해 컨텍스트는 수명이 맞는 세션/컴포넌트가 소유한다. 공통 `@Logic`은 전달받은 상태를 처리하고 전투별 값을 전역 필드에 저장하지 않는다.
- 기존 RPC 인자와 서버의 소유권·현재 맵·셀·턴 검증을 유지한다. 중복 완료·오래된 응답·이전 진입의 타이머는 새 행동에 영향을 주지 않아야 한다.
- 일반 이동은 `PlayerGridMovementLogic`을 계속 공유한다. 서버가 일반 이동 중 클라이언트 루트 위치를 매 프레임 덮어쓰지 않으며, 시각적 홉과 실제 바닥 Y를 분리한다.
- 분리와 밸런스/조작 변경은 별도 작업으로 진행한다. 새 닫힌 값이 필요한 변경은 같은 변경에서 Balance Studio vocabulary catalog도 갱신한다.
- 새 `.mlua`는 `RootDesk/MyDesk/`의 해당 도메인에 둔다. `.codeblock`은 Maker Refresh로 생성하고, `.model/.map/.ui`는 해당 builder로 변경한다.

## 3. 튜토리얼 오류 수정 계획 — 먼저 진행

### 3.1 착수 시 확인한 실패와 수정 결과

| 구분 | 현재 근거 | 수정 방향 |
|---|---|---|
| 확인된 로딩 실패 | `new-player-tutorial-test.py:16`, `tutorial-dodge-highlight-test.py:23`이 `NewPlayerTutorialLogic.GetGuideMessage`를 로드한다. 함수는 현재 `TutorialPresentationLogic`에 있다 | 테스트에서 실제 담당 로직을 로드하고 위임 경로를 연결 |
| 확인된 계약 불일치 | 기존 fixture는 4단계 완료, 단일 웨이브/적, 시작 포션 미지급, 3·4단계 몬스터 강조를 기대한다 | 현재 10단계·3웨이브·총 4마리·주황 포션 1개·회피/가드 강조 계약에 맞춤 |
| 후속 fixture 의존성 | `RequestStart → BeginEntry`, `Finish → TutorialRulesLogic.IsCompletionValid`, 피해/적 턴/HUD도 분리 로직으로 위임한다 | 함수 위치뿐 아니라 실제 호출부와 필요한 mock을 함께 정리 |
| 실제 플레이 오류 | 안내는 슬롯 1·2만 강조했고 키 안내는 1~6을 축약했다. 9단계에서 스킬을 슬롯 3·6으로 옮기면 새 슬롯의 강조가 빠졌다 | 표시 로직이 실제 슬롯을 따라가게 하고 안내 중 여섯 키를 각각 표시. 회귀 및 Maker 새 슬롯 키 입력·완주로 확인 |

위 테스트 실패만으로 실제 게임의 안내 함수가 없어졌거나 튜토리얼이 실행되지 않는다고 단정하지 않는다. 런타임 안내 호출은 이미 `TutorialPresentationLogic:GetGuideMessage`를 사용한다. 테스트를 통과시키기 위해 이전 위치에 표시 구현을 복원하지 않는다.

### 3.2 현재 구현의 단계 계약

`TutorialRulesLogic`이 입력 허용과 단계 전이를, `TutorialPresentationLogic`이 안내·강조·복원을 소유한다.

| 단계 | 수행할 조작 | 전이/검증 시점 |
|---:|---|---|
| 1 | 오른쪽 한 칸 이동 | 플레이어 `OnUnitMoved` 후 2단계 |
| 2 | 브랜디쉬 1개 장전 | 적 라운드 완료 후 3단계; 추가 장전·다른 스킬 차단 |
| 3 | 왼쪽으로 회피하고 예고 공격 관찰 | 적 라운드 완료 후 4단계; 적 공격 재선택 없이 빗나감 확인 |
| 4 | 오른쪽으로 재접근 | 플레이어 이동 이벤트 후 5단계 |
| 5 | 등록한 브랜디쉬 실행 | 큐가 비고 적 라운드가 끝나면 6단계 |
| 6 | 디바인 스윙 장전·실행으로 첫 적 처치 | Wave 2 시작 시 7단계 및 스킬 런타임 초기화 |
| 7 | 주황 포션 사용 | 실제 회복량·소비량 모두 양수일 때 8단계; 턴 미소비 |
| 8 | 브랜디쉬 장전 후 전사 가드 사용 | 가드 성공 표시 후 적 라운드 완료 시 9단계; 장전 큐 유지 |
| 9 | 예약 취소·슬롯 드래그 연습, 두 스킬 장전·실행 | 큐 2개일 때 실행 허용; 두 번째 적 처치 후 Wave 3 진입 |
| 10 | 주황버섯 2마리와 자유전투 | 일반 조작 허용; 전체 처치 후 결과 확인·저장·로비 복귀 |

완료 저장 조건은 `TutorialStep >= 10`, Wave 3, 대기 스폰 0, 생존 적 0, 실제 처치 수 4 이상이다. 결과 문자열 `Victory`만 바꾸거나 이전 4단계 상태를 만드는 것은 완료가 아니다. 안내 중 피해 보정은 학습자와 필요한 적을 HP 1 이상 유지하고, 자유전투에서는 정상 사망을 허용한다.

### 3.3 작업 체크리스트

| ID | 상태 | 작업 | 완료 기준 |
|---|---|---|---|
| TUT-01 | ✅ | 두 테스트의 로더를 진입/규칙/표시 로직 및 전투 위임 구조에 맞춤 | 누락 함수 로딩 실패가 사라지고 튜토리얼 자체 assertion이 실제 실행됨 |
| TUT-02 | ✅ | 10단계, 3웨이브(1+1+2), 포션 지급, 피해 제한·해제, 완료 저장 fixture 갱신 | 각 단계의 허용/거절 조작, 중복 콜백, 저장 실패 후 재시도, 이전 요청 차단 검사 통과 |
| TUT-03 | ✅ | 몬스터·셀·키·스킬·포션 강조 테스트 갱신 | 몬스터 강조는 3단계 또는 장전 큐가 있는 8단계, 결과/비튜토리얼에서는 해제. 확대/축소와 템플릿 누락 안전성 유지 |
| TUT-04 | 🟡 | Maker에서 신규 진입부터 10단계 완주·복귀까지 실제 입력 재현 | 단계/셀/HP/큐/턴/저장 결과가 로그와 화면에서 일치 |
| TUT-05 | 🟡 | 재현된 런타임 오류만 담당 로직에서 수정하고 정상 런 회귀 확인 | 재현 → 원인 → 수정 → 재검증 기록과 관련 회귀 통과; 일반 전투에 튜토리얼 제약이 남지 않음 |

TUT-01~03에서는 문구 전체 일치보다 단계별 행동 안내가 맞는지 확인한다. 현재 문구에 없는 “회피 성공”, “반격” 같은 이전 문자열 assertion을 유지하지 않는다. 완료·보상·저장 검증은 약화하거나 삭제하지 않는다.

### 3.4 수정 시 함께 확인할 파일

- [NewPlayerTutorialLogic](RootDesk/MyDesk/00_Core/Lobby/NewPlayerTutorialLogic.mlua): 최초 진입/다시 하기, 플레이어·요청 소유권, 저장 후 복귀, 진입 실패 해제.
- [TutorialRulesLogic](RootDesk/MyDesk/00_Core/Lobby/Tutorial/TutorialRulesLogic.mlua): 입력 허용, 단계 전이, HP 제한, 웨이브·시작 포션·완료 판정.
- [TutorialPresentationLogic](RootDesk/MyDesk/00_Core/Lobby/Tutorial/TutorialPresentationLogic.mlua): 안내, 강조, dimmer, 렌더 순서·색상·크기 복원, Retry 이벤트 연결/해제.
- [BattleSessionComponent](RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua), [EnemyTurnExecutionLogic](RootDesk/MyDesk/01_Combat/Resolvers/EnemyTurnExecutionLogic.mlua), [BattleDamageLogic](RootDesk/MyDesk/01_Combat/Resolvers/BattleDamageLogic.mlua): 실제 이벤트 호출 시점과 중복 완료 방지.
- [BattleWaveComponent](RootDesk/MyDesk/01_Combat/Components/Shared/BattleWaveComponent.mlua), [RunManagerLogic](RootDesk/MyDesk/04_Roguelike/RunManager/RunManagerLogic.mlua), [UnionProfileRepositoryLogic](RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.mlua): 스폰·런 초기화·포션·영구 완료 저장, 일반 보상/기록 제외.
- [EnemyIntentHudComponent](RootDesk/MyDesk/02_UI/EnemyIntentHudComponent.mlua)와 큐/키/포션 HUD: 표시 위임 및 맵 이탈 정리.
- [튜토리얼 회귀](Artifacts/tests/new-player-tutorial-test.py), [강조 회귀](Artifacts/tests/tutorial-dodge-highlight-test.py): 현재 본문을 실행하도록 fixture 정리.

## 4. 전투 세션 책임 분리 후속 작업

각 항목은 호출부·회귀·Maker 검증을 포함한 별도 커밋 단위로 진행한다. 새 로직의 이름과 개수는 착수 시 기존 담당 파일을 확인한 뒤 결정하며, 줄 수 감소만으로 완료를 판정하지 않는다.

| 순서 / ID | 상태 | 분리 대상과 방향 | 핵심 완료 기준 |
|---|---|---|---|
| 1 / BS-01 | ✅ | 사망·승패·웨이브 정산: `HandleUnitDiedFromSource`, `FinishEmptyBattlefield`, 지연 클리어와 적 정리. `Resolvers`의 책임별 로직으로 이동하고 Unit/Board/Wave/Drop 소유 API 재사용 | 중복 사망·보스 소환수 제거·드롭 yield 중 진입 변경·큐/유틸리티 완료 후 정산이 한 번만 처리됨 |
| 2 / BS-02 | ✅ | 밀치기·당기기·대상 회전·스킬 이동: `ResolvePushImpact*`, `ResolvePullImpactOnTarget`, `ResolveTurnImpactOnTarget`, `ResolveSkillMoveImpact`. 기존 Push/MoveSelf 실행기 책임을 우선 활용 | 셀 경계/점유/HEAVY/충돌 피해/방향/강제 재배치 검증 유지. 강제 이동이 이전 일반 이동을 취소하고 출발점으로 되돌리지 않음 |
| 3 / BS-03 | ✅ | 적 특수 효과·독 안개·Modifier: `ExecuteEnemySpecialEffect`, `AdvancePoisonMists`, `ExecuteCombatModifier`, 생성/제거/사망 정리 호출부 | 지속 효과의 턴 순서, 시전자 사망·맵 이탈 시 정리, 중복 타이머·전투 간 상태 공유 없음 |
| 4 / BS-04 | 🟡 | 큐 등록·순차 실행·재정렬·퀵바: `TryQueueTile`, `ExecuteNextQueuedTile`, `CompleteTileQueueExecution`, `TryReorderQueuedTile`, `TryReorderBattleSkillSlot`, `RefreshSkillSlots`. 실제 실행은 SkillExecutionLogic, 큐 원본은 BattleTurnComponent 유지 | FreePlay/쿨다운 예약/큐 유지/매 타일 현재 상태 재타깃/예약 취소/슬롯 이동의 의미가 동일하고 튜토리얼 9단계도 통과 |
| 5 / BS-05 | 🟡 | 모션 완료 영수증·게이트와 이동·효과 표시: `BeginMotionCompletionWait`, `AwaitClientMotionCompletion`, 플레이어/적 이동 표시, `BeginSkillEffectPresentation`, 셀 효과·카메라·추종 표시. 공통 이동 및 기존 Presentation Component 재사용 | epoch/receipt/sequence 중복·누락·재전송·새 진입 취소 유지. 서버/클라이언트 루트 경합과 착지 후 반복 위치 쓰기 없음 |
| 6 / BS-06 | ✅ | 진입·유닛 초기화·재구성·결과·진행 DTO·소모품 어댑터: `InitializeFromEntry`, `RegisterPlayer`, `RebuildBattleState`, `RefreshHudProgressSnapshot`, `RequestContinueResult` 주변 구현 | 책임별 파일에서 기존 Gateway/Run/소모품/HUD 로직 재사용. RPC 검증·동기화·생명주기 연결은 세션에 유지하며 오래된 결과가 새 전투를 진행시키지 않음 |
| 7 / BS-07 | 🟡 | 전체 세션 경계와 로비·전투 통합 재점검 | 세션에 기능 구현이 남지 않고 각 호출 경로·상태 소유자가 추적 가능. 회귀와 실제 입력 검증을 구분해 기록 |

BS-01의 정산/지연 클리어 계약을 먼저 고정한 뒤 큐·유틸리티·이동을 추가 분리한다. 이동의 셀 규칙을 분리할 때는 `TryMoveInternal`, `TryMoveAwayInternal`, `TryChargeForward`도 함께 검토하되, 일반 이동 재생을 로비/전투별로 복제하지 않는다.

BS-07 보조 로직 후속 정리(2026-10-12): ✅ `IsTeamTurn`, `GetFacingDirection`, `GetTileActionType`, `GetSkillSpeedMultiplier`, `FlushDamageNumberBatch`, `GetPlayerHopDuration`의 구현을 기존 Action/Movement/Queue/Presentation/공통 이동 로직으로 위임했다. 공개 계약 288개·본문 6개 동일성과 회귀 18개 모음(새 보조 검사 7개 포함), Maker의 보조 반환값·전투 D/A·W 전환·1 장전/Space 실행·피해 숫자·로비 A/D 복귀를 확인했다. 이 하위 작업의 완료는 BS-07 전체나 실제 포인터·실기기·화면 검증의 완료를 뜻하지 않는다.

## 5. 검증 계획과 완료 판정

### 오프라인 회귀

Python 회귀에는 Lupa가 필요하다. 현재 머신의 임시 설치 경로는 `/private/tmp/mapletactics-landing-lupa`이며 다른 환경에서는 설치된 경로로 바꾼다. 임시 경로가 존재한다고 가정하지 않고 먼저 환경을 확인한다.

```bash
LUPA_PATH=/private/tmp/mapletactics-landing-lupa python3 Artifacts/tests/new-player-tutorial-test.py
LUPA_PATH=/private/tmp/mapletactics-landing-lupa python3 Artifacts/tests/tutorial-dodge-highlight-test.py
```

튜토리얼 검사 복구 후 변경 책임에 맞는 회귀를 실행한다. 최신 코드에서는 아래 10개 기존 모음과 분리 회귀 6개(합계 296그룹), 튜토리얼 2개, 상점 hover/scroll 2개를 포함한 20개 모음이 모두 통과했다. 새 모음은 `battle-outcome`, `battle-control-movement`, `battle-status-effects`, `battle-queue`, `battle-entry-result`, `battle-session-boundary`이며 전체 파일명·그룹 수·결과는 [통합 검증 기록](Artifacts/tutorial-session-refactor/verification.md)에 있다. 파일은 `Artifacts/tests/`에 있다.

| 기존 모음 | 직전 통과 그룹 | 보존할 계약 |
|---|---:|---|
| `utility-skill-execution-test.py` | 18 | 유틸리티 거절·비용·큐 유지·강제 이동·턴 복귀 |
| `battle-damage-test.py` | 19 | 피해·지원·사망·충돌·시전 방해 |
| `skill-execution-test.py` | 21 | 스킬/투사체/지연 타격·타이머 정리 |
| `grid-movement-latency-test.py` | 38 | 공통 착지·정상 완료 위치 쓰기 0·오래된 응답 |
| `battle-motion-gate-test.py` | 33 | 영수증·완료 게이트·대체 경로·중복 완료 |
| `battle-ui-state-test.py` | 11 | 표시 DTO·현재 셀·스킬 상태 |
| `enemy-plan-snapshot-test.py` | 12 | 계획 스냅샷·전조 |
| `enemy-planning-test.py` | 14 | 준비된 행동 유지·추적/공격 구분 |
| `enemy-turn-execution-test.py` | 21 | 적 순서·턴 전환·안전한 완료 |
| `hud-map-lifecycle-test.py` | 11 | 같은 Stage/Unit 재진입·HUD 캐시 정리 |

새 분리 책임에 부족한 사망/정산·제어 효과·큐 경계 검사는 실제 본문과 의미 있는 상태 불변식으로 보강한다. 위임되었다는 문자열만 검사하거나 모든 의존성을 빈 stub으로 바꾸어 통과시키지 않는다. 수정한 mLua LSP, `node tools/check-balance-vocab.cjs`, `git diff --check`도 확인한다.

### Maker 실제 입력

구현 검증 순서: **stop → refresh → build 로그 → play → 입력/상태·normal 로그 → stop**. 테스트용 저장은 격리된 계정/키를 사용하고 실제 완료 기록을 임의로 초기화하지 않는다.

| 시나리오 | 확인할 결과 |
|---|---|
| 신규/기존 계정, 메뉴에서 다시 하기 | 신규 미완료만 자동 진입, 완료 계정 자동 진입 제외, 명시적 재플레이 허용, 중복 진입 차단 |
| 튜토리얼 1~6단계 | 오른쪽 이동 → 브랜디쉬 장전 → 왼쪽 회피 → 재접근 → 실행 → 디바인 스윙으로 처치. 안내와 서버 단계·큐·셀·HP 일치 |
| 튜토리얼 7~9단계 | 포션 1개 실제 소비/회복·턴 유지, 가드 피해 0·큐 유지, 예약 취소·슬롯 드래그 후 올바른 새 슬롯 키·실행 순서 |
| 자유전투·완료·재도전 | Wave 3 적 2명, 총 처치 4명, 정상 사망 허용, 완료 저장 성공 후 로비 복귀. 패배/전송 실패/저장 실패의 재시도 경로 확인 |
| 일반 런 복귀 | 튜토리얼 입력·HP·웨이브 제한과 dimmer/강조가 남지 않음. 튜토리얼이 일반 보상·도감·개인 기록·랭킹에 기여하지 않음 |
| 로비/전투 일반 이동 비교 | 좌우 단발·연속·빠른 반전·점유/경계·착지 직후 입력·맵 전환. 0.5초 전 무보정, 오차 이하 무보정, 초과 한 번 보정, 다음 행동에 오래된 검사 무효 |
| 스킬/강제 이동 후 일반 이동 | 기존 이동 요청 취소와 타이머 정리, 최종 서버 셀/위치 일치, 일반 이동 정상 복귀, 카메라·이름표·HP 표시 떨림 확인 |
| 사망/웨이브/결과 중 재구성·맵 이탈 | 이전 콜백·드롭 정산·완료 응답이 새 진입에 영향을 주지 않음. 중복 턴 증가·승패·보상 지급 없음 |

Maker 로그 기반 판정과 실제 시각적 체감 판정을 따로 기록한다. 모바일·실제 다중 계정/인스턴스·발행 환경 검증은 별도이며, 프레임 간격 로그를 GPU FPS 측정으로 표현하지 않는다.

### 완료 기준

- 튜토리얼 두 테스트의 본문이 실행되고 현재 10단계 계약의 정상/거절/중복/실패 경로가 통과한다.
- Maker에서 최초 진입부터 완료 저장·로비 복귀, 재플레이·패배 재도전 및 일반 전투 복귀를 실제 입력으로 확인한다.
- 세션 분리 단계마다 원래 실행 순서와 상태 소유권을 유지하고 관련 회귀·Maker 경로를 통과한다.
- 빌드/런타임 오류 0과 각 시나리오 성공 로그를 보존한다. 기존 `IsPCPlatform` 폐기 예정 경고 등은 새 문제와 구분해 기록한다.
- 변경 파일·검사 명령·결과·미검증 범위를 `Artifacts/` 기록에 남기고 이 문서의 작업 상태를 갱신한다. 모든 실제 완료 기준을 만족한 항목만 ✅로 올린다.

## 6. 그다음 프로젝트 작업

아래는 기존 문서의 후속 범위다. 현재 책임 분리와 튜토리얼 수정이 안정화된 뒤 기존 계획을 재확인하며 진행한다.

- ✅ 2026-10-12 GDD/Phase 0/Phase 1·Roadmap의 맵 타입·운영·실제 Region/MapId·상태 기록을 대조했다. 맵 26개 모두 MapleTile(0)·Static Map, 최대 1명 운영과 클라이언트 일반 이동을 반영했다. Phase 0/1 현재 상태를 GDD에 한 번씩 미러하고 미착수/미구현·도구 부재 오해를 정리했다. 전체 Phase 완료는 아니며 Body/잘못된 RPC 거절/데이터 오류 근거·포인터/실기기/상점 통합 대기를 유지한다. [문서 정리 기록](Artifacts/plan-reconciliation-20261012/verification.md)을 따른다.
- 🟡 Phase 1 사용자 화면/체감·실제 포인터 검토. 통합 상점의 양쪽 경로·구매·무구매·다음 전투·새 런 기능 회귀는 완료했으며 사람의 표시/입력 기준은 남는다.
- 🟡 P0-05/06 기본 오류 진단의 Column/Value 보완. 현재 정상 Dataset·Range=0/중복 복제본 거절과 원본 보존은 확인했으나 AddError DTO/SerializeErrors에는 열·값이 없다. 관련 호출부·회귀·Maker 재검증이 필요하다.
- 🟡 개인 기록 v3의 제어된 NORMAL 상·하단 각 20전투/지역 집계·실제 기록 UI 검증은 완료했다. 일반 전술 입력만의 전체 완주와 공개 랭킹의 실제 계정/인스턴스·모바일·포인터·발행 운영은 남는다.
- 🟡 엘리니아 전투 무대의 사용자 화면 검토와 후속 지역 전체 콘텐츠/공통 UI 확장 감사를 Roadmap 순서대로 진행한다. 상점 이후 Stage/Map 승인·해금·양쪽 합류 기능은 실제 진행으로 확인했다.

새 지역·시즌·랭킹 확장·공개 payload 장기 정리 등은 기존 Roadmap의 범위와 우선순위를 유지한다. 이 문서는 새 게임 기능이나 새 마일스톤을 추가하지 않는다.

## 7. 재개할 때 읽을 근거

- [정상 상점·양쪽 경로·v3 기록 및 데이터 오류 검증](Artifacts/normal-run-validation-20261012/verification.md)
- [계획 문서 정합성 정리](Artifacts/plan-reconciliation-20261012/verification.md)
- [보조 로직 정리 검증 기록](Artifacts/tutorial-session-refactor/auxiliary-logic-cleanup/verification.md)
- [홉 배율·정밀 이동 후속 검증 기록](Artifacts/tutorial-session-refactor/movement-feel-verification/verification.md)

- [맵별 이동 검증 기록](Artifacts/tutorial-session-refactor/map-pointer-verification/verification.md)
- [이번 튜토리얼·세션 통합 검증 기록](Artifacts/tutorial-session-refactor/verification.md)
- [피해·지원 분리 검증 기록](Artifacts/battle-session-damage-separation-verification.md)
- [유틸리티 분리 검증 기록 및 194개 회귀 내역](Artifacts/battle-session-utility-separation-verification.md)
- [전투 세션 책임 분리/일반 이동 규칙](AGENTS.md)
- [Phase 1 기존 작업 상태](Docs/MapleTactics-M1-Phase1.md), [상위 Roadmap](Docs/MapleTactics-Roadmap.md)

현재 상태는 **튜토리얼·BS-01~07 분리와 정상 상점/양쪽 경로/기록 기능 검증 후, P0-05 오류 위치 진단 보완 및 실제 포인터/실기기/화면·체감·일반 전술 전체 완주 대기**다. TUT-04/05, BS-04/05/07의 🟡는 아래 미검증 범위를 뜻한다. 이전 또는 이번 `skill_test` 검증을 모든 전투맵 체감 검증의 근거로 사용하지 않는다.

| 남은 항목 | 필요한 확인 |
|---|---|
| P0-05/06 | 기본 오류 DTO·직렬화·검증 호출부에 Column/Value를 연결하고 정상/고의 오류를 다시 검증. 검사 스크립트의 보충 로그만으로 완료 처리하지 않음 |
| P1-S16/SHOP·기록 후속 | 기능 경로는 완료. 일반 전술 조작만으로 전체 런 완주, 실제 상점/기록 포인터·화면·실기기 검토는 남음 |
| TUT-04/05, BS-04 | 실제 PC 포인터로 1→3·2→6 슬롯 드래그, 큐 예약 취소·재정렬, 결과 확인 및 메뉴 다시 하기·패배 재도전. 새 슬롯의 프레임/키 강조와 복귀 후 해제 확인 |
| BS-05/07 | 홉 1배 통일, 20개 맵 기본 이동/착지 41/41, 양끝·대표 점유 거절, 정밀 이벤트 40개와 로비 연속 입력·순간이동 후 복귀·이동 중 맵 전환을 도구로 확인. 사람의 화면 체감·실제 정밀 키 입력·모든 직업/점유 조합 검토는 남음 |
| TUT-04/05, BS-06/07 확장 검증 | 실제 저장/전송 실패, 다중 계정·인스턴스, 모바일·발행 환경. 실패/오래된 결과 계약의 오프라인 검사는 통과했으나 실제 서비스 장애 주입은 하지 않음 |

정지·로그·Refresh 등 Maker MCP 호출로 실행을 확인했다. 관찰 스크립트의 잘못된 필드/맵 가정에서 난 오류는 원인과 보정 후 결과를 별도 기록했고 제품 런타임 오류와 구분한다. 최종 로비 경계 및 연습 전투 검증 라운드는 오류 0건이다.
