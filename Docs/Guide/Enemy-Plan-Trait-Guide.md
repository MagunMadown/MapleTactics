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
→ 고정 계획을 SpawnOrder 순으로 실행
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
- `CurrentActionIndex`, `ActionCount`, `QueuedActionSnapshot`, `QueuedTileIds`
- `TraitIds`, `TelegraphTurnsRemaining`, `PatternId`, `StepIndex`, `Revision`

UI는 Pattern 조건이나 Trait 결과를 다시 계산하지 않는다. `PreparedEnemy*` 동기화 속성은
기존 UI 호환을 위한 현재 실행 Cursor이므로 신규 UI의 전체 적 표시에는 사용하지 않는다.

## 3. 적 Trait 입력

`EnemyDefinitions.csv`의 `TraitIds`에 Trait ID를 `|`로 구분해 입력한다.

```csv
EnemyDefinitionId,...,TraitIds,IsBoss
guard_mushroom,...,HEAVY,false
elite_swordsman,...,QUICK|DOUBLE_STRIKE,false
```

지원 ID:

| Trait | 현재 계약 |
|---|---|
| `QUICK` | 해당 적의 계획 실행 준비 지연을 최소화한다. 행동 턴 자체를 삭제하지 않는다. |
| `HEAVY` | 강제 이동, 현재는 `PUSH`, 을 거부한다. |
| `DOUBLE_STRIKE` | `EXECUTE_TILE` 계획을 동일 타일 2회 Queue로 장식한다. Pattern Step은 Queue 전체 뒤 한 번만 진행한다. |
| `EXPLOSIVE` | ID와 Validator 예약 완료. 사망 효과 Executor는 후속 구현 대상이다. |
| `REACTIVE_SHIELD` | ID와 Validator 예약 완료. 피격 반응 Executor는 후속 구현 대상이다. |

알 수 없는 ID나 중복 ID는 `StageWaveRepositoryLogic`에서 적 정의를 거부한다.

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
- 다음 플레이어 턴에서 이전 계획이 초기화되고 새 계획 Revision이 생성된다.
