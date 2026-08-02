# Battle Turn 개발 가이드

## 1. 책임

`BattleTurnComponent`는 전투 맵 수명 동안 아래 상태의 단일 소유자다.

- `BattlePhase`, `TurnNumber`
- 즉시 행동 슬롯(`QueuedActionType`, `QueuedActionDirection`)
- Skill 등록 큐와 실행 큐
- `IsActionProcessing`
- 큐 용량(`BaseQueueCapacity`, `QueueCapacityBonus`, `TileQueueCapacity`)
- 큐 용량 Modifier Snapshot과 상태 Revision

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

일반 Skill 등록은 큐에 보관된 뒤 즉시 적 턴으로 넘어간다. 적 라운드가 끝나도 등록
큐는 유지되므로 다음 플레이어 턴에 이동·회전하거나 Skill을 더 등록할 수 있다.
`FreePlay=true`인 Skill 등록만 턴을 소비하지 않는다.

Skill 실행은 별도 실행 명령에서 다음 순서를 고정한다.

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
| `ConfigureQueueCapacity(integer base, integer min, integer max, string reason)` | void | Session | 기본값·상하한 적용 |
| `UpsertQueueCapacityModifier(string modifierId, string sourceType, string sourceId, integer addValue)` | table | Job/Augment/Relic Adapter | 큐 용량 보너스 추가·갱신 |
| `RemoveQueueCapacityModifier(string modifierId)` | table | Job/Augment/Relic Adapter | 큐 용량 보너스 제거 |
| `GetQueueCapacityState()` | table | Session | Base/Bonus/Effective와 슬롯 상태 조회 |
| `OpenPlayerTurn(integer turn, string reason)` | void | Session | 첫 턴·다음 턴·다음 Wave 개방 |
| `TryReserveImmediateAction(string type, integer direction)` | table | Session | MOVE/TURN 등 즉시 행동 예약 |
| `CompleteImmediateAction(string reason)` | void | Session | 즉시 행동 슬롯 해제 |
| `TryAppendSkill(string skillId)` | table | Session | 검증이 끝난 Skill을 큐에 추가 |
| `TryFreezeSkillQueue()` | table | Session | 등록 큐를 실행 큐로 고정 |
| `SetExecutingAction(string type, integer direction)` | void | Session | 현재 실행 표시 갱신 |
| `AdvanceExecutingSkill()` | void | Session | 다음 실행 인덱스로 이동 |
| `CompleteSkillQueue(string reason)` | void | Session | 실행 상태 해제 |
| `TryClearQueuedSkills()` | table | Session | 실행 전 등록 큐 전체 비우기 |
| `TryRemoveQueuedSkillAt(integer queueIndex)` | table | Session | 1-based 위치의 타일을 무료 제거 |
| `TryMoveQueuedSkill(integer fromIndex, integer toIndex)` | table | Session | 타일을 무료 순서 변경 |
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
- 신규 HUD와 외부 UI는 `BattleSessionComponent.GetBattleUiState()`만 호출한다.
- DTO는 Phase/Turn, 명령 가능 여부, PlayerQueue의 Base/Bonus/Effective/Count,
  실행 상태, 마지막 명령 결과, Cooldown, Wave, 현재 호환 Intent를 함께 반환한다.
- `LastCommand`는 `Type`, `Success`, `Reason`, `Revision`을 제공한다. RPC는 반환값이 없는
  구조이므로 UI는 Revision 변경을 감지해 거절 사유를 토스트·버튼 상태 등에 표시한다.
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

위 직접 조회는 레거시 HUD를 해석할 때만 참고한다. 신규 UI에서 상태 Entity 경로를
복제하지 않는다. `GetBattleUiState()`의 `RevisionKey`가 바뀔 때 화면을 갱신한다.

## 5. 확장 규칙

- Queue 정책을 추가할 때 Session 조건문을 늘리지 말고 Turn의 `Try...` API에 둔다.
- 실행 큐 동결과 `IsActionProcessing=true` 설정은 하나의 `TryFreezeSkillQueue()` 호출에서
  처리한다. 실행 중 `EXECUTE_QUEUE`, 등록, 이동, 전체 비우기, 제거, 정렬은 모두
  `ACTION_PROCESSING`을 우선 반환한다.
- 턴 소비 여부와 큐 변경 횟수를 동일시하지 않는다. 일반 등록·실행은 턴을 소비하지만
  FreePlay 등록·제거·정렬은 같은 PlayerTurn에서 여러 번 수행할 수 있다.
- 피해, 타깃, Cooldown, 모션 규칙은 Turn에 넣지 않는다.
- Wave Timer와 Spawn 예약은 구현된 `BattleWaveComponent`가 단일 소유한다.
- 적 행동 선택은 Intent 영역이 소유하고 Turn은 현재 Phase와 표시용 행동만 보관한다.

### 전투 경계의 큐 정책

| 경계 | 등록 큐 | 실행 상태 | 이유 |
|---|---|---|---|
| 다음 Wave 진입 | 보존 | 초기화 | 같은 Stage에서 구성한 플레이어 계획을 이어 간다. |
| Victory | 초기화 | 초기화 | 종료된 전투의 명령이 다음 콘텐츠로 유출되지 않게 한다. |
| Defeat | 초기화 | 초기화 | 재도전은 깨끗한 전투 상태에서 시작한다. |
| 수동 Reset | 초기화 | 초기화 | Stage를 처음부터 재구축한다. |

Wave 전환은 `ClearActionState()`, Victory·Defeat·Reset은 `ClearTransientState()` 또는
`ResetTurnState()`를 사용한다. 신규 경계 로직에서 등록 큐 필드를 직접 비우지 않는다.
- 상태를 바꾼 뒤 Session 호환 소비자가 남아 있으면 같은 경계에서
  `PublishTurnStateSnapshot()`을 호출한다.

## 6. 검증 체크리스트

1. 시작 시 `PlayerTurn`, Turn 1인지 확인한다.
2. 기본 용량 3과 Modifier 적용/제거 시 Effective 용량이 상하한 안에서 변하는지 확인한다.
3. 일반 Skill 등록 직후 적 라운드가 한 번 실행되고 등록 큐가 유지되는지 확인한다.
4. 큐가 남은 다음 플레이어 턴에도 이동·회전·추가 등록이 가능한지 확인한다.
5. 별도 실행 명령이 큐 전체를 순서대로 실행한 뒤 큐를 비우고 적 라운드를 한 번 실행하는지 확인한다.
6. 실행 중 추가 입력이 `ACTION_PROCESSING`인지 확인한다.
7. Wave 전환에서는 등록 큐가 보존되고 실행 잠금만 해제되는지 확인한다.
8. Victory·Defeat·Reset에서는 등록 큐와 실행 잠금이 모두 초기화되는지 확인한다.
9. `GetBattleUiState()`와 HUD가 같은 Phase/Turn/Queue/명령 가능 상태를 표시하는지 확인한다.
10. 제거·정렬 전후 TurnNumber와 PlayerTurn이 유지되고 실행 중에는 `ACTION_PROCESSING`인지 확인한다.
11. 같은 프레임에 `RequestExecuteQueuedTile()`을 두 번 호출했을 때 첫 요청만 승인되고,
    두 번째 요청과 실행 중 다른 입력의 `LastCommand.Reason`이 `ACTION_PROCESSING`인지 확인한다.
