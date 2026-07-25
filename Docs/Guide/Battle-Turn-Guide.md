# Battle Turn 개발 가이드

## 1. 책임

`BattleTurnComponent`는 전투 맵 수명 동안 아래 상태의 단일 소유자다.

- `BattlePhase`, `TurnNumber`
- 즉시 행동 슬롯(`QueuedActionType`, `QueuedActionDirection`)
- Skill 등록 큐와 실행 큐
- `IsActionProcessing`
- `TileQueueCapacity`

`BattleSessionComponent`는 명령 검증, 실제 행동 실행, 적 Intent, Wave와 승패를
조정한다. HUD는 Turn 상태를 `BattleTurnComponent`에서 읽고 명령은 Session에 보낸다.
`map01`에서는 같은 Entity에 여러 상태 컴포넌트를 겹쳐 붙이지 않고
`BattleTurnState` 자식 Entity가 Turn 컴포넌트를 소유한다. 새 전투 맵도
`BattleBoardState`, `BattleTurnState` 자식 이름을 유지한다.

## 2. 호출 흐름

```text
UI/입력
→ BattleSession Request/Try
→ BattleTurn 상태 예약
→ Session 행동 실행
→ BattleTurn 완료/Phase 전환
→ @Sync 상태를 HUD가 표시
```

즉시 행동은 `TryReserveImmediateAction`으로 슬롯과 입력 잠금을 함께 확보한다. 실행이
끝나면 `CompleteImmediateAction`을 호출하고, 성공했으면 `BeginEnemyTurn`으로 넘긴다.

Skill 큐는 다음 순서를 고정한다.

```text
TryAppendSkill
→ TryFreezeSkillQueue
→ SetExecutingAction
→ AdvanceExecutingSkill
→ CompleteSkillQueue
→ BeginEnemyTurn
```

## 3. 공개 API

아래 상태 변경 API는 모두 `ServerOnly`이며 Session 또는 서버 전투 조정자만 호출한다.
Client UI는 직접 호출하지 않고 `BattleSessionComponent.Request...` 메서드로 요청한다.

| 메서드 서명 | 반환 | 주 호출자 | 용도 |
|---|---|---|---|
| `ResetTurnState(integer capacity, string reason)` | void | Session | 전투 또는 Stage 재구축 |
| `SetQueueCapacity(integer capacity, string reason)` | void | Session | Stage Definition 적용 |
| `OpenPlayerTurn(integer turn, string reason)` | void | Session | 첫 턴·다음 턴·다음 Wave 개방 |
| `TryReserveImmediateAction(string type, integer direction)` | table | Session | MOVE/TURN 등 즉시 행동 예약 |
| `CompleteImmediateAction(string reason)` | void | Session | 즉시 행동 슬롯 해제 |
| `TryAppendSkill(string skillId)` | table | Session | 검증이 끝난 Skill을 큐에 추가 |
| `TryFreezeSkillQueue()` | table | Session | 등록 큐를 실행 큐로 고정 |
| `SetExecutingAction(string type, integer direction)` | void | Session | 현재 실행 표시 갱신 |
| `AdvanceExecutingSkill()` | void | Session | 다음 실행 인덱스로 이동 |
| `CompleteSkillQueue(string reason)` | void | Session | 실행 상태 해제 |
| `TryClearQueuedSkills()` | table | Session | 실행 전 등록 큐 전체 비우기 |
| `BeginEnemyTurn(string type, integer direction, string reason)` | void | Session | 적 턴 진입 |
| `UpdateEnemyAction(string type, integer direction)` | void | Session | 다중 적 라운드의 현재 행동 표시 |
| `CompleteEnemyTurn(string reason)` | void | Session | Turn 증가 후 플레이어 턴 개방 |
| `SetPhase(string phase, string reason)` | void | Session | Wave 전환·종료·데이터 오류 반영 |

`Try...` 실패는 `Success=false`, `Reason=UPPER_SNAKE_CASE`로 반환한다.
직렬화 Helper인 `AppendTileId`, `QueueContainsSkill`, `GetTileIdCount`, `GetTileIdAt`과
`ClearTransientState`는 Turn 내부 또는 Session 호환 처리용이며 일반 기능의 진입 API로
사용하지 않는다.

## 4. 호환 Snapshot

기존 외부 코드 보호를 위해 Session에도 같은 이름의 `@Sync` 필드가 잠시 남아 있다.
이 필드는 원본이 아니며 `PublishTurnStateSnapshot(reason)`만 값을 쓸 수 있다.

- 신규 코드에서 Session의 Turn/Queue 필드에 직접 대입하지 않는다.
- `GetBattleTurnState()`는 `BattleQueueHudComponent` 내부 Helper이며 전투 공용 API가 아니다.
- 신규 HUD는 아래 표준 조회 방식으로 `BattleTurnComponent` 원본을 읽거나 같은 Helper를
  자체 구현한다.
- 외부 연동은 당분간 `GetBattleSnapshot()`을 사용할 수 있다.
- 모든 소비자가 원본 또는 DTO로 전환된 뒤 호환 필드를 제거한다.

```lua
local player = _UserService.LocalPlayer
local currentMap = player ~= nil and player.CurrentMap or nil
local stateEntity = currentMap ~= nil and currentMap:GetChildByName("BattleTurnState") or nil
local turnState = stateEntity ~= nil
    and stateEntity:GetComponent("script.BattleTurnComponent")
    or nil
```

이 조회는 `ClientOnly` UI 코드에서 사용한다. 공용 Client accessor가 아직 없으므로 여러
HUD에서 같은 코드가 반복되는 것이 현재 부족 항목이다.

## 5. 확장 규칙

- Queue 정책을 추가할 때 Session 조건문을 늘리지 말고 Turn의 `Try...` API에 둔다.
- 피해, 타깃, Cooldown, 모션 규칙은 Turn에 넣지 않는다.
- Wave Timer와 Spawn 예약은 구현된 `BattleWaveComponent`가 단일 소유한다.
- 적 행동 선택은 Intent 영역이 소유하고 Turn은 현재 Phase와 표시용 행동만 보관한다.
- 상태를 바꾼 뒤 Session 호환 소비자가 남아 있으면 같은 경계에서
  `PublishTurnStateSnapshot()`을 호출한다.

## 6. 검증 체크리스트

1. 시작 시 `PlayerTurn`, Turn 1인지 확인한다.
2. QueueCapacity만큼 등록되고 다음 등록이 `QUEUE_FULL`인지 확인한다.
3. 실행 중 추가 입력이 `ACTION_PROCESSING`인지 확인한다.
4. 전체 Skill 큐가 끝난 뒤 적 라운드가 한 번 실행되는지 확인한다.
5. 적 라운드 뒤 Turn이 정확히 1 증가하는지 확인한다.
6. Wave 전환과 승패에서 큐와 입력 잠금이 해제되는지 확인한다.
7. HUD와 Session 호환 Snapshot이 같은 Phase/Turn/Queue를 표시하는지 확인한다.
