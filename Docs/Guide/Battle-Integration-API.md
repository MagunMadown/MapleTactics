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

## 4. Client UI 공개 API

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
RUN_STATE_UNAVAILABLE
```

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
