# 전투 조작감 개선 STEP 1 — 현재 입력 및 턴 흐름 분석

## 범위와 결론

- 기준 브랜치: `develop` (`d24c307`)
- 분석 브랜치: `codex/combat-feel-step-1-analysis`
- 작업 분류: 기존 전투 입력·턴·스킬 실행 구조의 정적 분석
- 변경 사항: 이 문서 1개만 추가. 전투 코드, 턴 규칙, 스킬 데이터, UI 구조는 변경하지 않았다.
- 결론: 현재 구조는 이미 `플레이어 행동 1회 → 적 전체 라운드 → 다음 플레이어 턴`을 서버 권위 상태로 유지한다. 조작감 개선은 `BattleTurnComponent`의 규칙을 바꾸기보다 `BattleSessionComponent`의 입력 피드백, 고정 타이머, 이동 표현, 적 행동 간 대기 구간을 다루는 편이 안전하다.

## 분석 진행표

| 항목 | 상태 | 근거 |
|---|---|---|
| 좌·우 입력부터 이동 확정까지 | 확인 완료 | `HandleMoveKeyDown` → `RequestMove` → `TryQueuePlayerAction` → `ExecuteQueuedAction` → `TryMove` |
| 이동 후 적 턴과 입력 복구 | 확인 완료 | `CompleteQueuedAction` → `BeginEnemyTurn` → 적 계획 실행 → `CompleteEnemyTurn` → `OpenPlayerTurn` |
| 스킬 선택과 Queue 등록 | 확인 완료 | HUD → Presenter → `RequestQueueTile` → `TryQueueTile` → `TryAppendSkill` |
| Execute와 Queue 순차 실행 | 확인 완료 | `TryFreezeSkillQueue` → `ExecuteNextQueuedTile` → `TryExecuteSkill` → `CompleteTileQueueExecution` |
| 명중·넉백·사망 처리 | 확인 완료 | `ExecuteEffectSteps` → Effect Router → Damage/Push Executor → BattleSession/BattleUnit |
| 런타임 Play Test | 미실행 | STEP 1은 코드 수정 전 정적 분석 단계이며 사용자가 아직 Play Test를 요청하지 않았다. 런타임 정상 동작을 주장하지 않는다. |

## 관련 파일

### 입력·턴·전투 조정

- `RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua`
  - 클라이언트 키 입력, 서버 RPC, 이동, Queue 등록·실행, 적 라운드, 명중·넉백·사망을 연결하는 중앙 조정자다.
- `RootDesk/MyDesk/01_Combat/Components/Shared/BattleTurnComponent.mlua`
  - `BattlePhase`, `IsActionProcessing`, 즉시 행동 슬롯, 편집 Queue, 실행 Queue를 소유하는 서버 권위 상태 머신이다.
- `RootDesk/MyDesk/01_Combat/Components/Shared/BattleUnitComponent.mlua`
  - 유닛의 Cell, 방향, HP, 사망 상태를 실제로 변경한다.

### 공격 실행

- `RootDesk/MyDesk/01_Combat/Skills/SkillExecutionLogic.mlua`
  - 스킬 실행 Context를 만들고 Target Resolver 결과를 고정한 후 Effect Step을 순서대로 실행한다.
- `RootDesk/MyDesk/01_Combat/Resolvers/EffectRouterLogic.mlua`
  - `DAMAGE`, `PUSH`, `HEAL` Effect를 전용 Executor로 분배한다.
- `RootDesk/MyDesk/01_Combat/Skills/EffectExecutors/DamageEffectExecutorLogic.mlua`
  - 선택된 대상별로 `ResolveSkillDamageImpact`를 호출한다.
- `RootDesk/MyDesk/01_Combat/Skills/EffectExecutors/PushEffectExecutorLogic.mlua`
  - 선택된 대상별로 `ResolvePushImpactOnTarget`을 호출한다.
- `RootDesk/MyDesk/01_Combat/Resolvers/SkillTargetResolverLogic.mlua`
  - 명중 시점의 대상과 Cell을 해석한다.
- `RootDesk/MyDesk/01_Combat/Components/Shared/EnemyActionPlanComponent.mlua`
- `RootDesk/MyDesk/01_Combat/Components/Shared/EnemyPatternRunnerComponent.mlua`
  - 적이 플레이어 행동 뒤 실행할 동작 Queue와 패턴 Step 진행을 소유한다.

### UI 입력과 상태 반영

- `RootDesk/MyDesk/02_UI/BattleQueueHudComponent.mlua`
  - 스킬 슬롯 및 Execute 버튼 입력을 Presenter로 전달하고, 서버 동기화 상태에 따라 버튼을 활성화한다.
- `RootDesk/MyDesk/02_UI/BattleHudPresenterLogic.mlua`
  - 0.05초 간격으로 전투 UI 상태를 읽고 변경 이벤트를 발행한다.

## 이동 흐름

### 1. 플레이어 좌·우 입력

`BattleSessionComponent.HandleMoveKeyDown` (`165-193`)

- Left/A는 `direction = -1`, Right/D는 `direction = 1`로 변환한다.
- 클라이언트에서 `RequestMove(direction)` 서버 RPC를 바로 호출한다.
- 이 지점에는 로컬 `CanMove` 검사나 선행 이동 피드백이 없다. 눌림 자체는 서버 응답 전까지 시각적으로 확정되지 않는다.

### 2. 입력 허용 여부 판단

1. `BattleSessionComponent.RequestMove` (`4667-4690`)
   - PlayerEntity 존재, `senderUserId`, `BattlePhase == "PlayerTurn"`을 검사한다.
2. `BattleSessionComponent.TryQueuePlayerAction` (`1275-1296`)
   - MOVE와 방향 값의 형식을 검사한다.
3. `BattleTurnComponent.TryReserveImmediateAction` (`185-205`)
   - `PlayerTurn`인지 확인한다.
   - `IsActionProcessing == false`인지 확인한다.
   - 다른 `QueuedActionType`이 없는지 확인한다.
   - 성공 시 `QueuedActionType = "MOVE"`, 방향 저장, `IsActionProcessing = true`로 입력을 잠근다.

### 3. 이동 시작

`BattleSessionComponent.ExecuteQueuedAction` (`1300-1332`)에서 `TryMove("player_01", direction)`을 호출하는 지점이 이동 시작점이다.

`BattleSessionComponent.TryMove` (`4821-4925`)는 다음을 검사하고 즉시 상태를 바꾼다.

- 유닛 존재 및 생존
- 해당 팀의 턴인지 여부
- 보드 경계
- 목적 Cell 점유
- 직업 Mechanic 개입 가능성
- `BattleUnitComponent.ApplyCellChange(toCell)`로 논리 Cell 변경
- `PlaceEntity`로 월드 위치 변경
- 이동 Cell의 Drop 수집
- `UnitMovedEvent` 발행

### 4. 이동 완료

이 구조에는 이동 Tween이나 애니메이션의 실제 완료 Callback이 없다.

- 논리 이동 완료: `TryMove` 안의 `ApplyCellChange`와 `PlaceEntity`가 끝나는 순간
- 월드 배치: `BattleSessionComponent.PlaceEntity` (`5041-5056`)
  - MovementComponent가 있으면 `SetPosition(position)`
  - 없으면 `TransformComponent.Position`을 직접 변경
- 턴 흐름상의 이동 완료: `ExecuteQueuedAction`이 `MoveActionDuration = 0.12`초 타이머를 예약하고, 타이머가 `CompleteQueuedAction`을 호출하는 순간

따라서 현재의 “이동 종료”는 실제 화면 이동 종료가 아니라 고정 0.12초 Presentation Lock 종료다.

### 5. 턴 소비

`BattleSessionComponent.CompleteQueuedAction` (`1348-1363`)

- 먼저 `TurnState.CompleteImmediateAction`으로 즉시 행동 슬롯을 비운다.
- 이동 성공이면 곧바로 `BeginEnemyTurn()`을 호출한다.
- 별도의 `ConsumeTurn()` 함수가 있는 방식이 아니라, PlayerTurn에서 EnemyTurn으로 Phase를 넘기는 것이 턴 소비의 실체다.

### 6~7. 적 턴 시작과 적 행동

`BattleSessionComponent.BeginEnemyTurn` (`1366-1410`)

- 미리 준비된 적 Intent/ActionPlan을 가져온다.
- `BattleTurnComponent.BeginEnemyTurn` (`393-400`)이 `BattlePhase = "EnemyTurn"`, `IsActionProcessing = true`를 설정한다.
- 기본 `EnemyThinkDuration = 0.25`초 후 `ExecutePreparedEnemyIntent`를 호출한다.

`BattleSessionComponent.ExecutePreparedEnemyIntent` (`1831-1917`)

- MOVE, TURN, TELEGRAPH, 보스 점프, `EXECUTE_TILE`을 기존 권위 함수로 분기한다.
- 적 스킬도 플레이어와 같은 `TryExecuteSkill` 파이프라인을 사용한다.
- `GetEnemyActionDuration`의 고정/스킬별 시간만큼 기다린 뒤 `CompletePreparedEnemyIntent`를 호출한다.
- 한 적의 Plan에 다음 Action이 있거나 다음 적이 있으면 다시 `BeginEnemyTurn`을 호출한다.

### 8. 다시 플레이어 입력 가능

마지막 적 행동이 끝나면 `BattleSessionComponent.CompleteEnemyTurn` (`2233-2253`)이 호출된다.

1. `BattleTurnComponent.CompleteEnemyTurn` (`410-411`)
2. `BattleTurnComponent.OpenPlayerTurn(TurnNumber + 1, reason)` (`176-181`)
3. `ClearActionState`가 `IsActionProcessing = false`와 실행 상태를 정리
4. `BattlePhase = "PlayerTurn"`
5. `PublishTurnStateSnapshot("PLAYER_TURN_REOPENED")`
6. 클라이언트 동기화
7. `BattleHudPresenterLogic.OnUpdate`의 최대 0.05초 Poll 뒤 HUD 버튼 재활성화

서버 기준 Unlock은 `OpenPlayerTurn`이며, 사용자가 실제로 버튼이 풀렸다고 보는 시점은 네트워크 동기화와 Presenter Poll 이후다.

## 공격 흐름

### 1. 스킬 선택

`BattleQueueHudComponent.RequestSlotSkill` (`617-627`)

- 선택 Slot의 skillId를 읽는다.
- `_BattleHudPresenterLogic:RequestQueueTile(skillId)`를 호출한다.
- Presenter의 `RequestQueueTile` (`180-186`)이 Session의 `RequestQueueTile` 서버 RPC로 전달한다.

### 2. 공격 Queue 등록

`BattleSessionComponent.RequestQueueTile` (`2412-2424`) → `TryQueueTile` (`2535-2592`)

- 스킬 데이터 유효성, Run 소유권, RuntimeState, Cooldown, 동일 스킬의 Cooldown 예약을 검증한다.
- `BattleTurnComponent.TryAppendSkill` (`218-240`)이 편집 Queue에 skillId를 추가한다.
- `FreePlay ~= true`이면 정상적인 준비 행동으로 취급한다.

### 3. Queue 등록 턴 소비

`TryQueueTile`의 `definition.FreePlay ~= true` 분기에서 `BeginEnemyTurn()`을 호출한다.

- 즉 Queue에 스킬 1개를 넣는 행위가 한 턴을 소비한다.
- 적 라운드가 끝나도 편집 Queue는 유지된다. `ClearActionState`가 실행 Queue만 지우고 `QueuedTileIds`는 보존하기 때문이다.
- 이것은 현재 설계된 Shogun Showdown식 규칙이며 STEP 1에서 변경 대상이 아니다.

### 4. Execute 입력

`BattleQueueHudComponent.OnExecuteClicked` (`660-662`)

- Presenter `RequestExecuteQueue` (`190-196`)
- Session `RequestExecuteQueuedTile` (`2427-2439`)
- `BattleSessionComponent.TryExecuteQueuedTile` (`2595-2605`)

`BattleTurnComponent.TryFreezeSkillQueue` (`244-268`)가 다음을 수행한다.

- PlayerTurn 및 미처리 상태 검사
- Queue 비어 있음 검사
- `QueuedTileIds`를 `ExecutingTileIds`로 이동
- 실행 Index를 1로 설정
- 편집 Queue를 비움
- `IsActionProcessing = true`로 전체 Queue 실행 동안 입력 Lock

### 5. Queue 순차 실행

`BattleSessionComponent.ExecuteNextQueuedTile` (`2609-2656`)

1. 현재 Index의 skillId 조회
2. `SetExecutingAction("EXECUTE_SKILL", 0)`
3. `TryExecuteSkill("player_01", skillId)`
4. `GetSkillActionDuration(skillId)`만큼 `ActionTimerId` 대기
5. `AdvanceExecutingSkill()`
6. 재귀적으로 다음 Tile 실행
7. 마지막 Tile 뒤 `CompleteTileQueueExecution`

`GetSkillActionDuration` (`2727-2750`)은 일반 스킬은 authored ActionDuration을 사용한다. 투사체는 최대 Range의 비행 시간과 Volley 전체 간격까지 포함한 최악 조건을 최소 실행 시간으로 잡는다.

### 6. 적 피격

`BattleSessionComponent.TryExecuteSkill` (`3851-3954`)

- 스킬과 Cooldown을 검증하고 Cooldown을 시작한다.
- 무기/모션/캐스트 Effect를 시작한다.
- 일반 스킬은 ImpactDelay, 투사체는 LaunchDelay + 실제 비행 시간 뒤 `ExecuteEffectSteps`를 호출한다.

`SkillExecutionLogic.ExecuteEffectSteps` (`55-117`)

- Impact 시점에 Target Resolver를 실행해 대상을 고정한다.
- 데이터의 Effect Step 순서대로 `EffectRouterLogic.ExecuteEffectStep`을 호출한다.
- DAMAGE는 `DamageEffectExecutorLogic.Execute` → `BattleSession.ResolveSkillDamageImpact` (`4362-4420`) → `ApplyDamage` (`4423-4488`)로 이어진다.
- 실제 HP 변경 지점은 `BattleUnitComponent.ApplyDamage` (`122-150`)의 `self.CurrentHp = result.HpAfter`다.

### 7. 넉백과 사망 처리

- PUSH Step: `PushEffectExecutorLogic.Execute` → `BattleSession.ResolvePushImpactOnTarget` (`3776-3848`)
  - 대상 생존·팀·Cell을 검사한다.
  - Heavy Trait, 보드 경계, 점유 상태에 따라 밀림을 막을 수 있다.
  - 성공 시 `ApplyCellChange`, `PlaceEntity`, `UnitMovedEvent` 순으로 즉시 처리한다.
- 사망: DAMAGE가 HP를 0으로 만들면 `ApplyDamage`가 `HandleUnitDiedFromSource` (`4497-4613`)를 즉시 호출한다.
  - `BattleUnitComponent.MarkDead`
  - Drop, 생존 적, Wave/Stage 종료 판정
  - 전투가 계속되면 남은 Effect/Queue 흐름으로 복귀
  - 전투 종료면 Timer와 Transient State를 정리하고 BattleEnded로 전환

Effect Step은 데이터 순서대로 실행된다. 앞선 DAMAGE Step에서 전투가 종료되면 `ExecuteEffectSteps`는 뒤 Step을 더 실행하지 않는다. 대상이 사망한 뒤 PUSH Step이 이어지는 경우도 `ResolvePushImpactOnTarget`의 `UNIT_DEAD` 검사에 의해 이동되지 않는다.

### 8~9. 적 턴과 플레이어 입력 복구

전체 Queue가 성공적으로 끝나면 `CompleteTileQueueExecution` (`2659-2674`)이 실행 상태를 정리한 뒤 정확히 한 번 `BeginEnemyTurn()`을 호출한다.

- Queue 내부 스킬마다 적 턴이 끼어들지 않는다.
- Execute 명령 전체가 한 플레이어 행동이며 Queue 전체 실행 뒤 적 라운드가 시작된다.
- 마지막 적 행동 뒤 이동 흐름과 같은 `CompleteEnemyTurn` → `OpenPlayerTurn` 경로로 입력이 복구된다.

## 시작·종료·Lock 지점 요약

| 구분 | 실제 지점 |
|---|---|
| 이동 입력 시작 | `BattleSessionComponent.HandleMoveKeyDown` |
| 이동 실행 시작 | `BattleSessionComponent.ExecuteQueuedAction`의 `TryMove` 호출 |
| 논리 이동 종료 | `TryMove`의 `ApplyCellChange` + `PlaceEntity` 완료 |
| 턴 흐름상 이동 종료 | 0.12초 후 `CompleteQueuedAction` |
| 이동 턴 소비 | `CompleteQueuedAction`의 `BeginEnemyTurn` |
| 스킬 선택 시작 | `BattleQueueHudComponent.RequestSlotSkill` |
| Queue 등록 | `BattleTurnComponent.TryAppendSkill` |
| Queue 등록 턴 소비 | `BattleSessionComponent.TryQueueTile`의 `BeginEnemyTurn` |
| 공격 실행 시작 | `TryExecuteQueuedTile` → `ExecuteNextQueuedTile` → `TryExecuteSkill` |
| 공격 명중 | `TryExecuteSkill`의 Impact Timer → `ExecuteEffectSteps` → Damage/Push Executor |
| HP 변경 | `BattleUnitComponent.ApplyDamage` |
| 넉백 위치 변경 | `BattleSessionComponent.ResolvePushImpactOnTarget` |
| 사망 시작 | `BattleSessionComponent.ApplyDamage`의 `HandleUnitDiedFromSource` 호출 |
| 입력 Lock | 즉시 행동: `TryReserveImmediateAction`; Execute: `TryFreezeSkillQueue`; 적 턴: `BeginEnemyTurn` |
| 행동 종료 직후 임시 Release | 이동: `CompleteImmediateAction`; Execute: `CompleteSkillQueue`가 `IsActionProcessing = false`를 Publish한 직후 같은 서버 흐름에서 `BeginEnemyTurn`으로 다시 Lock |
| 서버 입력 Unlock | `BattleTurnComponent.OpenPlayerTurn` |
| HUD 입력 Unlock | 동기화 후 `BattleHudPresenterLogic` Poll 및 `BattleQueueHudComponent.RefreshHud` |

## 조작감이 끊기거나 느려질 가능성이 있는 지점

### 우선순위 높음

1. 이동이 보간되지 않고 즉시 배치된다.
   - `PlaceEntity`는 SetPosition/Transform 직접 변경이다.
   - 화면상 순간이동 뒤 0.12초 동안 입력만 잠긴 느낌이 날 수 있다.
   - 후속 개선은 논리 Cell 확정과 턴 규칙을 유지하고, 클라이언트 Presentation만 짧게 보간하는 경계가 안전하다.

2. 적 Think Delay가 적의 각 Action 전마다 다시 붙는다.
   - 기본 0.25초 Think Delay + ActionDuration이 누적된다.
   - 한 적의 Plan에 여러 Action이 있거나 적 수가 많을수록 대기 체감이 선형으로 커진다.
   - 규칙을 건드리지 않고 Telegraph 가독성, Action 간 Delay, 연속 재생 타이밍을 조정할 수 있는 핵심 지점이다.

3. 서버 승인 전 로컬 입력 피드백이 없다.
   - 키 입력과 HUD 클릭은 바로 RPC만 보낸다.
   - Lock 상태가 클라이언트에 도착하기 전 중복 입력이 전송될 수 있고, 서버는 Phase/Processing 검사로 거절하거나 일부 Phase에서 조용히 무시한다.
   - 규칙 변경 없이 눌림/예약 표시와 로컬 중복 방지만 추가할 수 있다.

### 우선순위 중간

4. 입력 복구 UI가 Poll 기반이다.
   - 서버 Unlock 뒤 네트워크 동기화 + 최대 0.05초 Presenter Poll이 필요하다.
   - 체감상 버튼이 한 박자 늦게 풀릴 수 있다.

5. 플레이어 행동 종료와 적 턴 시작 사이에 임시 Release Snapshot이 발행된다.
   - 이동은 `IMMEDIATE_ACTION_COMPLETED`, Execute는 `SKILL_QUEUE_COMPLETED`를 `IsActionProcessing = false`인 PlayerTurn 상태로 Publish한 뒤 즉시 `BeginEnemyTurn`을 호출한다.
   - 서버 함수 안에서는 연속 실행되지만, 두 Revision이 클라이언트에 따로 보이면 HUD가 잠깐 활성화됐다 다시 잠기는 깜빡임이나 헛입력 체감이 생길 수 있다.
   - 후속 Play Test에서 Revision 로그와 버튼 상태를 함께 확인해야 하며, Phase 규칙을 바꾸지 않고 Snapshot 노출 순서만 다룰 수 있는 후보 지점이다.

6. 스킬 Queue 진행 시간과 실제 Impact 시간은 별도 Timer다.
   - Queue는 `ActionTimerId`, 명중은 `ImpactTimerId`를 사용한다.
   - 현재 투사체는 `GetSkillActionDuration`이 최대 Range/Volley 시간을 포함해 이전 Impact가 다음 Cast에 의해 취소되지 않도록 방어한다.
   - 반대로 가까운 대상에도 최악 비행 시간을 기다리므로 실제 명중 뒤 남는 Idle Tail이 생길 수 있다. 후속 Play Test에서 근거리/원거리/Volley 각각을 측정할 필요가 있다.

7. 스킬 준비 한 번마다 적 라운드가 돈다.
   - 현재 의도된 턴 규칙이므로 삭제하거나 우회하면 안 된다.
   - 다만 Queue 등록 확인 효과와 적 행동 시작 연결이 약하면 “클릭이 늦게 먹고 바로 적에게 넘어간다”는 체감이 생길 수 있다.

8. Miss나 조기 사망에도 authored ActionDuration은 유지된다.
   - 전투 연출 일관성에는 유리하지만, 빈 타격이나 마지막 적 처치 직전에는 잔여 대기처럼 느껴질 수 있다.
   - 후속 단계에서는 전투 결과와 Presentation 완료 관계를 Play Test로 먼저 확인해야 한다.

## 후속 Step에서 안전하게 다룰 경계

- 유지해야 할 규칙 중심: `BattleTurnComponent`
  - `BattlePhase`, `IsActionProcessing`, Queue 보존/Freeze, Player↔Enemy Phase 전환은 변경하지 않는다.
- 조작감 개선 후보: `BattleSessionComponent`
  - 입력 직후 피드백 경계
  - 이동의 논리 확정과 화면 보간 분리
  - `EnemyThinkDuration`과 적 Action 사이 Presentation 간격
  - 실제 Impact 완료와 Queue ActionDuration 사이 Idle Tail 측정
- UI는 구조를 바꾸지 않고 기존 Presenter/CommandResult 이벤트로 눌림·대기 상태를 더 빠르게 보여주는 방식이 안전하다.
- 각 후보는 하나씩 적용하고 Maker Play Test와 로그 확인이 통과한 뒤 다음 Step으로 넘어가야 한다.

STEP 1 COMPLETE
