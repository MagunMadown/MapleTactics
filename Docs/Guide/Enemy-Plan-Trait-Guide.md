# 적 행동 계획·Trait 제작 가이드

## 1. 전투 흐름

플레이어 턴이 열릴 때 `BattleSessionComponent`는 모든 생존 적을 `SpawnOrder`로 수집하고,
각 적의 다음 행동을 같은 보드 Snapshot에서 확정한다. 이후 플레이어가 턴 소비 행동을 해도
적 AI를 다시 판정하지 않으며, 이미 확정된 계획만 순서대로 실행한다.

```text
PlayerTurn 시작
→ 모든 적 Pattern 판정
→ 적별 EnemyActionPlanComponent에 계획 고정
→ GetBattleUiState().EnemyIntents로 전체 공개
→ 플레이어 Command
→ 공격 Tile이면 첫 적 턴에 Queue 추가
→ 다음 PlayerTurn에서 Queue와 대상 정보를 계속 공개
→ 다음 적 턴에 고정 계획을 SpawnOrder 순으로 실행
→ 다음 PlayerTurn
```

`EnemyPatternRunnerComponent`는 적별 Pattern Step 진행 상태를 소유하고,
`EnemyActionPlanComponent`는 이번 라운드의 실행 Queue를 소유한다.
`BattleSessionComponent`는 두 객체를 직접 대체하지 않고 준비·순서·턴 경계만 조정한다.

## 2. UI 계약

UI는 `GetBattleUiState()`에서 다음 필드를 읽는다.

- `EnemyIntentMode = PER_ENEMY_FROZEN_PLAN_V1`
- `EnemyPlanCount`, `EnemyPlanRevision`
- `EnemyIntents[]`
- 각 항목의 `UnitId`, `SpawnOrder`, `State`, `CommandType`, `TileId`
- 보스 항목의 `BossPhaseId`, `BossPhaseIndex`, `BossPhaseRevision`
- `CurrentActionIndex`, `ActionCount`, `QueuedActionSnapshot`, `QueuedTileIds`
- `QueueTurnsRequired`, `QueueTurnsElapsed`, `IsQueueReady`
- `TraitIds`, `TelegraphTurnsRemaining`, `PatternId`, `StepIndex`, `Revision`

UI는 Pattern 조건이나 Trait 결과를 다시 계산하지 않는다. `PreparedEnemy*` 동기화 속성은
기존 UI 호환을 위한 현재 실행 Cursor이므로 신규 UI의 전체 적 표시에는 사용하지 않는다.

## 3. 적 Trait 입력

`EnemyDefinitions.csv`의 `TraitIds`에 Trait ID를 `|`로 구분해 입력한다.

```csv
EnemyDefinitionId,...,TraitIds,IsBoss
guard_mushroom,...,HEAVY,false
elite_swordsman,...,QUICK|DOUBLE_STRIKE,false
aggressive_swordsman,...,AGGRO,false
ranged_turret,...,HOLD_POSITION,false
```

지원 ID:

| Trait | 현재 계약 |
|---|---|
| `QUICK` | 공격 Tile을 Queue에 추가한 같은 적 턴에 바로 실행한다. 이동·회전에는 영향 없음. |
| `HEAVY` | 강제 이동, 현재는 `PUSH`, 을 거부한다. |
| `DOUBLE_STRIKE` | `EXECUTE_TILE` 계획을 동일 타일 2회 Queue로 장식한다. Pattern Step은 Queue 전체 뒤 한 번만 진행한다. |
| `EXPLOSIVE` | ID와 Validator 예약 완료. 사망 효과 Executor는 후속 구현 대상이다. |
| `REACTIVE_SHIELD` | ID와 Validator 예약 완료. 피격 반응 Executor는 후속 구현 대상이다. |
| `AGGRO` | 일반 적의 기본 공격 후 후퇴를 1칸 접근으로 바꾼다. |
| `HOLD_POSITION` | 공격 후 이동을 생략한다. `AGGRO`와 함께 쓸 수 없다. |

Trait가 없는 일반 적은 `EXECUTE_TILE` 뒤 1칸 후퇴를 예약하지만 같은 적 턴에 즉시 움직이지 않는다. 플레이어가 다음 행동을 마친 뒤 돌아오는 적 턴에 `MOVE_AWAY`를 실행하며, 방향은 그 실행 시점의 플레이어 위치로 계산한다. `AGGRO`는 같은 타이밍에 `MOVE_TOWARD`, `HOLD_POSITION`은 이동 없음으로 처리한다. 보스는 이 공통 후처리에서 제외하고 Pattern에 이동을 명시한다. 알 수 없는 ID, 중복 ID, `AGGRO|HOLD_POSITION` 충돌 조합은 `StageWaveRepositoryLogic`에서 적 정의를 거부한다.

## 4. 새 Trait 개발 규칙

1. `EnemyTraitRouterLogic.ValidateTraitIds()`의 지원 목록에 ID를 등록한다.
2. 계획 변경은 `BuildActionPlan()`에서 base Intent를 복사한 뒤 수행한다.
3. 밀치기·피격·사망처럼 계획 외 규칙은 Router의 의미별 Query 메서드로 노출한다.
4. Session이나 Skill ID 조건문에 특정 EnemyDefinitionId를 추가하지 않는다.
5. Trait는 Pattern 진행 상태, BoardState, UI 상태를 직접 소유하지 않는다.
6. 복수 행동 Trait는 한 Queue 안에서 실행하되 Pattern Step은 Queue 전체 완료 후 한 번만 갱신한다.

## 5. 최소 회귀 항목

- 플레이어 턴 시작 로그에 `[EnemyRoundPlan] frozen ... living=N prepared=N`이 남는다.
- 두 적 이상일 때 `EnemyPlanSnapshot`에 같은 턴의 모든 적이 포함된다.
- 첫 적 이동 뒤 두 번째 적의 `PatternId`, `StepIndex`, `CommandType`이 다시 선택되지 않는다.
- `HEAVY` 적 밀치기가 `PUSH_BLOCKED_HEAVY_TRAIT`로 종료되고 Cell이 유지된다.
- `DOUBLE_STRIKE`는 `ActionCount=2`, `CurrentActionIndex=1→2`로 실행된다.
- Trait가 없는 일반 적은 `적 공격 → 플레이어 행동 → 다음 적 턴 MOVE_AWAY` 순서로 실행된다.
- `AGGRO` 일반 적은 다음 적 턴에 `MOVE_TOWARD`, `HOLD_POSITION` 적은 공격만 실행한다.
- 공격 직후 Plan은 `DeferredUntilTurn`이 현재 턴보다 크며, 같은 적 라운드에서는 선택되지 않는다. 다음 플레이어 턴 HUD는 예약된 이동을 읽기 전용으로 미리 표시할 수 있다.
- 보스의 명시적 `MOVE_AWAY`와 일반 적 공통 후퇴가 중복되지 않는다.
- 공격 계획은 `INSERTING 0/1 → TRACKING 1/1 → ATTACK_READY → EXECUTING`으로 전환된다.
- `INSERTING 0/1`은 아직 실제 Queue가 아니므로 `QueuedTileIds/QueuedIconRuids`는 비어 있다. 첫 적 행동으로 `TRACKING 1/1`이 된 뒤부터 머리 위 Queue에 표시한다.
- `TRACKING`은 보유 Tile을 유지한 채 `TURN_TO_PLAYER` 또는 `MOVE_TOWARD`를 실행하고 Pattern Step은 전진시키지 않는다.
- 모든 생존 적의 Readiness는 플레이어 턴이 열리기 전에 함께 동결되어, 뒤 SpawnOrder 적도 대응 턴 없이 갑자기 공격하지 않는다.
- 증원 Spawn이 발생해도 생존 적의 `INSERTING/TRACKING/ATTACK_READY` 계획은 유지된다.
- 실행 완료 뒤 다음 플레이어 턴에서 새 계획 Revision이 생성된다.

## 6. 근접·원거리 공격 제작 규칙

`EnemyPatternSteps.ActionType=EXECUTE_TILE`일 때 `TileId`는 실제 `SkillDefinitions.SkillId`다.
Session에 특정 스킬 ID 분기를 추가하지 않는다. 실행은 항상 공용 Skill Targeting/Effect 경로를 사용한다.

- 근접 공격: `DISTANCE_EQ=1` + `FRONT_CELL`
- 원거리 공격: `DISTANCE_LE=N` + `FIRST_ENEMY_FORWARD`, `Range=N`
- `EXECUTE_TILE`은 적이 플레이어를 바라볼 때만 적용 가능하다.
- 실제 사거리와 피해량은 Pattern이 아니라 `SkillDefinitions`와 `SkillEffectSteps`에서 정한다.
- Validator는 `TileId`가 유효한 Skill인지 검사한다.

현재 예시는 `region_01_spore_ranged → enemy_ranged_shot`이며 최대 2칸 앞의 첫 플레이어를 공격한다.
일반 주황버섯과 스포아 공격은 모두 `EnemyQueueTurns=1`이다. 주황버섯은 같은 리소스 팩의 `jump` 클립을 몸통박치기 자세로 사용하고,
발밑 먼지를 준비 효과, 노란 충격을 적중 효과로 사용한다. 머리 위 Queue에는 노란 주먹 아이콘을 표시한다.
스포아는 전용 이동 클립을 공격 모션으로 사용하며 실행 완료 뒤 각 모델의 대기 클립으로 복구된다.
스포아의 `CooldownTurns=5`는 스포아 자신의 행동마다 감소한다. 다음 포자탄이 아직 쿨타임이면
보유한 공격 Tile을 유지한 채 `TRACKING + WAIT`로 한 행동을 소비하여 플레이어에게 재배치 시간을 준다.

`EXECUTE_TILE`을 `ConditionType=ALWAYS`로 작성하면 사거리 밖에서도 공격 Tile을 먼저 등록하는
사거리 추적형 공격 주기를 사용한다. 실제 준비 가능 거리는 Skill의 `TargetingType`, `Range`,
`TargetOffsets`로 판정하므로 Pattern CSV에 같은 거리 숫자를 중복 작성하지 않는다.

## 7. 이동 연출 클립은 적 Model에서 지정한다

`BattleSessionComponent.EnemyHopAnimationRuid`의 기본값은 주황버섯 animationclip
(`6df12df0c9ce4caea61385606a4d40d3`)이며 **모든 적이 공유한다**. 이 값을 그대로 두면 이동
Hop 동안 `SpriteRUID`가 주황버섯 클립으로 교체됐다가 복구되므로, 주황버섯이 아닌 적은 이동할
때마다 주황버섯이 스쳐 보인다. 로그에는 오류가 남지 않는다.

새 적을 만들 때는 해당 적의 `.model`에 `script.BattleUnitPresentationComponent`를 포함하고
다음 값을 설정한다. `BattleSessionComponent`는 모델에 이미 붙어 있는 presentation 컴포넌트를
재사용하므로 전투 코어를 수정할 필요가 없다.

| 값 | 설정 |
|---|---|
| `UseCustomMoveHopProfile` | `true` |
| `CustomMoveHopEnabled` | `true` |
| `CustomMoveHopAnimationRuid` | 해당 적 리소스 팩의 `move` 클립 RUID |
| `CustomMoveHopAnimationPlayRate` | `1.8` |
| `CustomMoveHopDuration` / `Height` | `0.12` / `0.06` |
| `CustomMoveHopTakeoffDuration` / `LandingDuration` | `0.02` / `0.04` |
| `CustomMoveHopSquashScale` / `LandingScale` | `(1.04, 0.95)` / `(1.06, 0.93)` |
| `CustomMoveHopPeakProgress` | `0.50` |

`UseCustomMoveHopProfile=true`는 RUID뿐 아니라 Hop 타이밍 값 전체를 커스텀 값으로 대체하므로,
위 수치는 Session의 `Enemy*` 기본값과 같게 두어 연출 감각을 유지한다.

검증은 `[MoveHopAnimation] started ... kind=SPRITE ruid=<적의 move 클립>`과 뒤이은
`restored ... ruid=<적의 stand 클립>` 로그로 확인한다. Hop은 0.12초라 스크린샷으로는 잡히지 않는다.

커닝시티 적 5종에는 적용돼 있다. Region 4(페리온·발굴지) 적 4종은 아직 미적용이라 이동 시
주황버섯이 보인다.
