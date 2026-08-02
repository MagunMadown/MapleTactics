# 전투 외부 연동 API 가이드

## 1. 목적

이 문서는 메인 UI, 대기 화면, 캐릭터 선택, 맵 이동 시스템이 전투 내부 구현을 직접
참조하지 않고 전투를 준비·시작·취소·조회하기 위한 호출 규격이다.

공동 아키텍처 원칙은
[`Architecture-Standard-v0.1.md`](./Architecture-Standard-v0.1.md)를 따른다.

## 2. MSW에서 생성자를 사용하지 않는 이유

MSW `@Component`와 `@Logic`은 엔진이 생성하고 `OnInitialize`, `OnBeginPlay` 생명주기를
호출한다. 일반 클래스처럼 외부 코드에서 생성자를 호출해 BattleSession을 만들지 않는다.

대신 다음 두 단계 API를 사용한다.

```text
외부 시스템
→ BattleGatewayLogic에 전투 입장 정보 준비
→ 전투 맵의 BattleSessionComponent가 준비 정보를 소비해 초기화
```

## 3. 구성 요소

### BattleGatewayLogic

전역 무상태 전투 진입 Facade다. 다른 시스템이 전투를 시작할 때 사용하는 첫 진입점이다.
특정 플레이어의 입장 정보는 Logic 내부가 아니라 플레이어 컴포넌트에 저장한다.

파일:
`RootDesk/MyDesk/01_Combat/Resolvers/BattleGatewayLogic.mlua`

### BattleEntryStateComponent

플레이어별 Pending 전투 입장 정보다. 로비에서 준비한 정보가 전투 맵 진입까지 유지된다.

파일:
`RootDesk/MyDesk/01_Combat/Components/Shared/BattleEntryStateComponent.mlua`

| 속성 | 의미 |
|---|---|
| `EntryState` | `IDLE`, `PREPARED`, `STARTED`, `CANCELLED` |
| `RequestId` | 플레이어별 증가하는 요청 번호 |
| `StageId` | 시작할 Stage |
| `CharacterId` | 캐릭터 선택 시스템의 안정된 ID |
| `JobId` | 선택 직업 ID |
| `LoadoutId` | 덱·장비·스킬 구성 ID |
| `RunSeed` | Run 재현 Seed |
| `EntryMode` | `NEW_RUN` 또는 `CONTINUE_RUN` |
| `LastReason` | 최근 준비·시작·실패 사유 |

### BattleSessionComponent

전투 맵의 실제 Session이다. 외부 시스템은 이 컴포넌트를 직접 생성하거나 내부
`StartStage`, `SpawnWave` 메서드를 호출하지 않는다.

`BattleGatewayLogic`이 `InitializeFromEntry(...)`를 호출해 Session을 초기화한다.

적 Intent의 mutable state는 `EnemyIntentComponent`가 소유하며, 무상태 선택 규칙은
`EnemyIntentResolverLogic`에 있다. 외부 UI는 이 둘을 직접 호출하지 않고
`BattleSessionComponent.GetBattleUiState()`의 `EnemyIntents` DTO만 읽는다. DTO의 현재
`EnemyIntentMode`는 `COMPONENT_SINGLE_COMPAT`이고 각 Intent는 `Revision`을 제공한다.

## 4. Client UI 공개 API

전투 화면은 시작 가능 여부를 먼저 `GetBattleUiState().ContentValidation`에서 확인한다.
`State=BLOCKED`이면 전투 명령 버튼을 모두 비활성화하고 `ErrorSnapshot`을 개발용 오류 화면에
표시한다. `State`, `IsReady`, `Reason`, `ErrorCount`, `ErrorSnapshot`, `Revision`이 공개
계약이며 UI가 Dataset이나 Validator를 직접 호출해서는 안 된다. Validation Revision은
`RevisionKey`에도 포함된다.

### 전투 입장 준비

```lua
_BattleGatewayLogic:RequestPrepareBattleEntry(
    "stage01",
    "character_warrior_01",
    "warrior",
    "starter_loadout",
    1000,
    "NEW_RUN"
)
```

캐릭터 선택 완료 또는 전투 시작 버튼에서 호출한다. 서버는 `senderUserId`로 실제
플레이어 Entity를 찾으므로 Client가 다른 플레이어 Entity를 전달하지 않는다.

### 현재 전투 맵에서 즉시 시작

```lua
_BattleGatewayLogic:RequestBeginBattle(
    "stage01",
    "character_warrior_01",
    "warrior",
    "starter_loadout",
    1000,
    "NEW_RUN"
)
```

준비와 시작을 한 번의 Server 요청으로 처리한다. 플레이어의 현재 맵 Root에
`BattleSessionComponent`가 있을 때 사용하며, 현재 map01 프로토타입에 적합하다.

이미 `RequestPrepareBattleEntry(...)`를 호출했고 맵 이동까지 끝났다면 다음 메서드로
준비된 요청만 시작할 수도 있다.

```lua
_BattleGatewayLogic:RequestStartPreparedBattle()
```

### 준비 취소

```lua
_BattleGatewayLogic:RequestCancelBattleEntry()
```

캐릭터 선택으로 돌아가거나 대기 상태를 취소할 때 사용한다.

Client 요청 메서드는 비동기 Server 요청이므로 반환값으로 성공을 판단하지 않는다.
동기화된 `BattleEntryStateComponent.EntryState`와 `LastReason` 또는 이후 UI Event를
사용한다.

## 5. Server 시스템 공개 API

### 준비만 수행

```lua
local result = _BattleGatewayLogic:PrepareBattleEntry(
    playerEntity,
    "stage01",
    "character_warrior_01",
    "warrior",
    "starter_loadout",
    1000,
    "NEW_RUN"
)
```

대기열이나 맵 이동이 별도 시스템에 있을 때 사용한다.

### 준비된 전투 시작

```lua
local result = _BattleGatewayLogic:StartPreparedBattle(playerEntity)
```

현재 맵에서 `BattleSessionComponent`를 찾아 준비 정보를 소비한다.

### 준비와 즉시 시작

```lua
local result = _BattleGatewayLogic:BeginBattle(
    playerEntity,
    "stage01",
    "character_warrior_01",
    "warrior",
    "starter_loadout",
    1000,
    "NEW_RUN"
)
```

현재 플레이어가 이미 전투 맵에 있을 때 사용하는 편의 API다.

### 준비 상태 조회

```lua
local snapshot = _BattleGatewayLogic:GetBattleEntrySnapshot(playerEntity)
```

대기 화면이나 서버 Flow Controller가 Pending 상태를 확인할 때 사용한다.

### 준비 취소

```lua
local result = _BattleGatewayLogic:CancelBattleEntry(
    playerEntity,
    "MATCH_CANCELLED"
)
```

## 6. 권장 호출 흐름

### 메인 UI에서 같은 map01 전투 시작

```text
캐릭터 선택 완료
→ RequestBeginBattle(...)
→ 내부에서 EntryState=PREPARED
→ BattleSession.InitializeFromEntry(...)
→ EntryState=STARTED
→ BattlePhase=PlayerTurn
```

### 로비·대기 화면과 전투 맵이 분리된 경우

```text
캐릭터 선택 완료
→ PrepareBattleEntry(player, ...)
→ 대기/매칭 시스템 처리
→ 맵 이동 시스템이 플레이어를 전투 맵으로 이동
→ BattleSession.OnMapEnter
→ BattleGateway.ConsumePreparedBattle
→ BattleSession.InitializeFromEntry
→ EntryState=STARTED
```

맵 이동 자체는 BattleGateway의 책임이 아니다. StageId와 실제 Map의 연결은 향후
`StageDefinitions` 또는 전용 Map Flow 시스템이 담당한다.

## 7. EntryMode

### NEW_RUN

- `RunManagerLogic.StartNewRun` 호출
- 전달한 RunSeed로 Run 순번 증가
- 완료 Stage와 마지막 전투 결과 초기화
- 선택한 Stage를 새 전투로 구성

### CONTINUE_RUN

- 기존 `PlayerRunStateComponent` 재사용
- 기존 RunSeed 유지
- 다음 Stage 입장에 사용
- Run이 없으면 전달한 Seed로 최초 Run 상태 생성

## 8. BattleSession 외부 API

다른 시스템이 직접 사용할 수 있는 읽기 API:

```lua
local snapshot = battleSession:GetBattleSnapshot()
```

Snapshot 주요 값:

```text
EntryRequestId
EntryMode
StageId
StageNumber
RunSeed
CharacterId
JobId
LoadoutId
BattlePhase
BattleResult
TurnNumber
CurrentWave
TotalWaves
```

`InitializeFromEntry(...)`는 공개된 형태이지만 Gateway 전용이다. UI나 Stage 스크립트가
직접 호출하지 않는다.

전투가 끝난 뒤 다음 화면은 Battle Snapshot의 `NextStageId`를 해석하지 않는다.
서버 Flow Controller는 다음 API로 플레이어별 Run Flow Snapshot을 읽는다.

```lua
local flow = _RunManagerLogic:GetRunFlowSnapshot(playerEntity)
```

주요 값은 `RunFlowState`, `CurrentNodeGraphId`, `CurrentNodeId`,
`LastCompletedStageId`, `AvailableNodeIds`, `AvailableContentTypes`,
`AvailableContentIds`, `Revision`이다. `Available*` 세 문자열은 `|`로 구분하며 같은
인덱스가 하나의 다음 콘텐츠 옵션이다. `BATTLE/BOSS`의 ContentId는 StageId,
`SHOP/EVENT/REST`의 ContentId는 NodeId다.

현재 HUD는 이 계약과 전투 명령을 검증하는 디버그 도구다. 최종 UI 개발자는 HUD의
배치·문구·버튼 구조를 호환 대상으로 보지 않고, 공개 Snapshot/Request 계약만 사용한다.

## 8.1 드롭·런 인벤토리·소모품 UI 계약

최종 UI는 내부 Component 경로를 조합하지 않고 `GetBattleUiState()`의 다음 DTO를 읽는다.

```text
Drops.PendingSnapshot
Drops.PendingCount
Drops.Revision
RunInventory.CurrencySnapshot
RunInventory.ConsumableSnapshot
RunInventory.SkillSnapshot
RunInventory.ConsumableCapacity
RunInventory.SkillRevision
RunInventory.Revision
RunAugments.OwnedSnapshot
RunAugments.LastTriggerType
RunAugments.LastTriggerReason
RunAugments.LastExecutedCount
RunAugments.RuntimeRevision
RunAugments.Revision
```

마지막 스킬의 실제 타격 대상은 같은 DTO의 다음 값을 읽는다.

```text
LastSkillTarget.SkillId
LastSkillTarget.TargetingType
LastSkillTarget.TargetUnitIds
LastSkillTarget.TargetCellIndices
LastSkillTarget.Reason
LastSkillTarget.Revision
```

`TargetUnitIds`와 `TargetCellIndices`는 `|` 구분 문자열이다. 이 값은 타격 시점에 서버
`SkillTargetResolverLogic`이 확정한 디버그·표시용 Snapshot이다. UI는 사거리나 대상을 다시
계산하지 않으며 `RevisionKey` 또는 `LastSkillTarget.Revision` 변경에 맞춰 표시만 갱신한다.

`SkillSnapshot`은 `SkillId~Count|SkillId~Count` 형식이다. UI는 이 값으로 보유 버튼을
숨기거나 비활성화할 수 있지만 최종 권한 검사는 서버 `TryQueueTile`이 수행한다.
외부 상점·보상 시스템의 공개 스킬 API는 다음과 같다.

```lua
local owned = _RunManagerLogic:CanUseRunSkill(playerEntity, "basic_slash")
local grant = _RunManagerLogic:GrantRunSkill(playerEntity, "heavy_slash", 1, rewardKey)
local snapshot = _RunManagerLogic:GetRunSkillSnapshot(playerEntity)
```

`rewardKey`는 구매/노드 보상 단위의 고유 키여야 한다. 같은 키를 재전송하면 수량은 다시
증가하지 않는다.

외부 직업·상점·보상 시스템의 증강 API는 다음과 같다.

```lua
local grant = _RunManagerLogic:GrantRunAugment(playerEntity, "prototype_warrior_recovery", "JOB", rewardKey)
local snapshot = _RunManagerLogic:GetRunAugmentSnapshot(playerEntity)
```

`OwnedSnapshot` 형식은 `AugmentId~Stacks~AcquiredOrder~SourceType`을 `|`로 구분한다.
최종 UI는 이를 표시만 하고 Trigger/Condition을 다시 계산하지 않는다. `LastTrigger*` 값은 현재
디버깅·기능 검증용이며 연출 타이밍의 영구 이벤트 스트림 계약은 아니다.

소모품 사용 요청은 다음 메서드만 호출한다.

```lua
session:RequestUseConsumable("potion_hp_small", clientRequestId)
```

`clientRequestId`는 한 전투 UI 세션에서 증가시킨다. 서버는 RunSequence와 StageId를
결합해 UseKey를 만들므로 같은 요청 재전송은 효과·소비 모두 무시한다. UI는 HP 회복량,
턴 소비 여부, 보유 수량을 직접 계산하지 않는다. 현재 `H` 키와 HUD 문구는 기능 검증용
어댑터이며 최종 UI 호환 대상이 아니다.

## 9. 공통 결과

Server API는 다음 형태를 반환한다.

```lua
{
    Success = true,
    Reason = "BATTLE_ENTRY",
    RequestId = 1,
    StageId = "stage01"
}
```

주요 실패 Reason:

```text
INVALID_PLAYER
INVALID_STAGE_ID
INVALID_ENTRY_MODE
ENTRY_STATE_UNAVAILABLE
ENTRY_NOT_PREPARED
CURRENT_MAP_UNAVAILABLE
BATTLE_SESSION_NOT_FOUND
STAGE_DEFINITION_NOT_FOUND
CONTENT_VALIDATION_FAILED
RUN_STATE_UNAVAILABLE
NODE_DEFINITION_NOT_FOUND
AMBIGUOUS_STAGE_NODE
NEXT_NODE_REFERENCE_MISSING
```

Stage 시작 전 `StageDefinitionRepositoryLogic`과 `ContentValidatorLogic`이
Stage Definition, 보드 범위, 큐 용량, Wave 참조를 검증한다.

- Stage가 없으면 `STAGE_DEFINITION_NOT_FOUND`
- Stage 행은 있으나 값 또는 참조가 잘못되면 `CONTENT_VALIDATION_FAILED`
- 세부 원인은 Server 결과의 `DetailReason`과 `[ContentValidation]` 로그에서 확인

Stage 제작 규칙은
[`Stage-Authoring-Guide.md`](./Stage-Authoring-Guide.md)를 따른다.

전투 승리 확정 시 호출 경계는
`RecordBattleResult(player, stageId, stageNumber, result, entryRequestId)`다. 이 메서드는
`NodeDefinitions` 전환을 먼저 검증한 뒤 전투 결과와 다음 콘텐츠 옵션을 같은 플레이어
컴포넌트에 기록한다. 상점이나 다음 맵 시스템이 전투 Session을 직접
참조하지 않는다.

승리인 경우 `StageRewardDefinitions`를 먼저 해석해 런 인벤토리에 멱등 지급한다. UI는
보상표를 읽지 않고 `RunInventory.CurrencySnapshot`, `ConsumableSnapshot`, `Revision`을
표시한다. 상세 제작 규칙은
[`Stage-Reward-Authoring-Guide.md`](./Stage-Reward-Authoring-Guide.md)를 따른다.

현재 `prototype_run`은 실제 Dataset의 `stage01_battle → shop_after_stage01` 두 행으로 구성되며,
전투 종료 전 `_ContentValidatorLogic:ValidateNodeGraph("prototype_run")`이 시작점·참조·도달
가능성을 검증한다. Repository compatibility fallback은 비활성이다.

`RunSequence:StageId:EntryRequestId`를 전투 결과의 멱등 키로 사용한다. 같은 전투 결과가
중복 전달되면 진행·보상 소비자가 두 번 처리하지 않도록 `[RunManager] duplicate result ignored`
로그와 함께 성공으로 무시한다. 이후 `StageRewardDefinitions`도 이 키를 그대로 사용한다.

다음 노드 선택과 화면 전환 준비는 전투 Session이 아니라 RunManager가 담당한다.

```lua
_RunManagerLogic:RequestSelectNextContent(nodeId, requestId)
local ui = _RunManagerLogic:GetLocalRunFlowUiState()
```

UI는 `Transition.RouteAction`, `UiRouteId`, `DestinationId`를 표시 계층에 전달한다. 상세 계약은
[`Run-Content-Flow-Guide.md`](./Run-Content-Flow-Guide.md)를 따른다.

`RouteAction=OPEN_SHOP` 뒤에는 `_RunShopLogic:RequestOpenShop(shopId)`를 호출하고,
구매는 `_RunShopLogic:RequestPurchaseOffer(shopEntryId, requestId)`만 사용한다. 상점 UI DTO는
`GetLocalShopUiState()`이며 상세 형식은
[`Run-Shop-Authoring-Guide.md`](./Run-Shop-Authoring-Guide.md)를 따른다.

구매하거나 건너뛴 뒤에는 `_RunShopLogic:RequestCloseShop(requestId)`를 호출한다. 서버가 현재
SHOP 전환과 요청 중복을 검증한 뒤 공통 `RunManagerLogic.CompleteCurrentContent()` 경계에서
다음 노드 또는 `RUN_COMPLETED`를 결정한다. UI가 `NodeDefinitions.NextNodeIds`를 직접 해석하지
않는다.

## 10. Prototype 자동 시작

`BattleSessionComponent.AutoStartPrototypeBattle`로 시작 방식을 선택한다.

- `true`: 현재 map01처럼 Play 즉시 Stage 1 시작
- `false`: Gateway의 Prepared Entry가 올 때까지 `Setup` 상태로 대기

메인 UI·대기·캐릭터 선택 흐름이 연결된 실제 전투 맵은 `false`를 권장한다.
현재 map01의 기존 Play 검증을 유지하기 위해 기본값은 `true`다.

## 11. 다른 개발 시스템이 지켜야 할 경계

- 캐릭터 선택 시스템은 `CharacterId`, `JobId`, `LoadoutId`만 전달한다.
- 캐릭터 선택 시스템이 `BattleSessionComponent`를 직접 찾지 않는다.
- 대기 시스템은 Pending 상태와 맵 이동만 담당한다.
- Stage 개발자는 `StageId`를 제공하고 Session 내부 메서드를 호출하지 않는다.
- 전투 결과 화면은 `BattleResult` Snapshot을 읽고 Run 상태를 직접 변경하지 않는다.
- Server 호출은 반환된 `Success`, `Reason`을 확인한다.
- Client 호출은 동기화된 Entry 상태로 결과를 확인한다.

## 12. 아직 연결되지 않은 영역

- StageId에서 실제 전투 Map/Instance Room을 찾는 Flow
- CharacterId와 JobId를 실제 모델·능력치·스킬 세트에 적용하는 Repository
- LoadoutId를 Skill Runtime 상태로 변환하는 로더
- 전투 종료 후 로비·보상 화면으로 이동하는 Gateway
- Client용 전투 진입 완료/실패 Event

이 항목은 각 기능 Slice에서 Gateway 공개 API를 확장하고 본 문서에 추가한다.
