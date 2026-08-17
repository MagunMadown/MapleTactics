# 적 사거리 추적형 공격 큐 수정 계획

## 0. 목적

현재 적은 공격 사거리에 들어오기 전에는 이동 Intent만 만들고, 사거리에 들어온 뒤 공격
타일을 큐에 넣는다. 이를 다음 흐름으로 수정한다.

```text
공격 타일 선택·등록
→ 사거리/방향이 맞지 않으면 타일을 보유한 채 회전·추적
→ 조건이 맞으면 공격 예고(ATTACK_READY)
→ 플레이어 대응 Command 1회
→ 예고한 공격을 현재 위치·방향 기준으로 고정 실행
→ 명중 또는 빗나감
```

핵심은 `공격 타일을 큐에 보유한 상태`와 `다음 턴에 실행할 공격을 예고한 상태`를
분리하는 것이다. 플레이어가 예고 후 사거리 밖으로 벗어나도 적은 추적으로 재계획하지
않고 예고한 공격을 실행해 빗나갈 수 있어야 한다.

## 1. 참고작 기준으로 고정할 규칙

- 일반 적은 자신의 공격 타일을 먼저 큐에 등록한다.
- 큐에 타일이 있어도 사거리나 방향이 맞지 않으면 회전 또는 이동하며 타일을 유지한다.
- 공격 조건이 맞은 시점에만 공격을 다음 행동으로 예고한다.
- 공격 예고 뒤에는 플레이어에게 대응 Command 1회를 준다.
- 대응 후에는 거리·대상을 다시 골라 추적하지 않고, 예고한 공격을 현재 보드 기하로 실행한다.
- 따라서 플레이어가 피하면 빈 칸을 공격하고, 다른 유닛이 그 칸에 들어오면 그 유닛이 맞을 수 있다.
- `QUICK`은 타일을 등록한 같은 적 행동에서 공격 조건까지 맞으면 바로 `ATTACK_READY`가 될 수 있다.
- `QUICK`도 사거리 밖에서 공격하지는 않으며, 타일을 보유한 채 정상적으로 추적한다.

참고 링크:

- Ume/QUICK: <https://shogunshowdown.wiki.gg/wiki/Ume_the_Unrelenting>
- Enemy sequence examples: <https://shogun-showdown.fandom.com/wiki/Enemies>
- Ashigaru action sequence: <https://shogun-showdown.fandom.com/wiki/Ashigaru>

## 2. 현재 구조와 차이

현재 `prototype_tracker`와 `region_01_spore_ranged`는 `DISTANCE_EQ` 또는
`DISTANCE_LE`가 성공해야 `EXECUTE_TILE`로 진입한다. 즉 사거리 밖에서는 공격 큐가
비어 있고, `TURN_TO_PLAYER`/`MOVE_TOWARD`만 반복한다.

유지할 부분:

- 이미 `ATTACK_READY`에 해당하는 준비가 끝난 뒤에는 ActionType/TileId를 재선택하지 않는다.
- 실행 시 현재 CellIndex/Facing과 Skill Target 규칙으로 명중 칸을 다시 계산한다.
- 강제 증원과 웨이브 전환 중 적별 Action Plan을 보존한다.
- SpawnOrder 기반 적 실행 순서를 유지한다.

수정할 부분:

- 공격 타일 등록을 사거리 조건보다 먼저 수행한다.
- 큐 타일과 매 턴의 임시 추적 Command를 서로 다른 상태로 보관한다.
- 단순 큐 준비 완료와 공격 예고 완료를 분리한다.
- UI DTO가 `큐 보유`, `추적 중`, `공격 예고`, `실행 중`을 구분해 반환하도록 한다.

## 3. 상태 규격

`EnemyActionPlanComponent`의 공격 주기를 다음 상태로 확장한다.

| 상태 | 의미 | 플레이어에게 보일 정보 |
|---|---|---|
| `EMPTY` | 보유한 공격 타일 없음 | 다음 패턴 선택 |
| `INSERTING` | 공격 타일 등록 턴 진행 중 | 타일 아이콘, 준비 수치 |
| `TRACKING` | 타일은 등록됐지만 사거리/방향 미충족 | 타일 아이콘, 회전/이동 예고 |
| `ATTACK_READY` | 공격 조건 충족, 다음 적 행동에서 고정 실행 | 공격 범위와 위험 경고 |
| `EXECUTING` | 예고한 공격 처리 중 | 입력 잠금, 실행 연출 |

상태 전이:

```text
EMPTY
→ INSERTING
→ TRACKING ── 조건 미충족 ──> TRACKING
→ ATTACK_READY ── 플레이어 대응 Command ──> EXECUTING
→ EMPTY
```

`QUICK`은 조건이 맞을 때 `INSERTING → ATTACK_READY`를 같은 적 행동 안에서 처리한다.

## 4. 객체 책임

### EnemyActionPlanComponent — 적별 변경 상태

- 보유 공격 타일 ID, 등록 진행도, 현재 QueueState를 소유한다.
- 공격 타일을 유지한 채 여러 턴의 추적 Command를 허용한다.
- `ATTACK_READY` 진입 시 PatternId/StepIndex/TileId/PreparedTurn을 고정한다.
- 공격 완료·사망·전투 종료 때만 큐를 비운다.

권장 공개 메서드:

```text
BeginTileInsertion(tileId, requiredTurns)
AdvanceTileInsertion()
SetTracking(reason)
MarkAttackReady(preparedTurn)
BeginExecution()
CompleteExecution(success, reason)
GetQueueSnapshot()
```

### EnemyIntentResolverLogic — 기존 무상태 판정 확장

- 별도 Readiness Logic을 만들지 않고 현재 방향·거리·Pattern Action을 판정하는 Resolver를 확장한다.
- 적 상태, 플레이어 상태, Skill Definition, Board 조회 결과만 입력받는다.
- `READY`, `NEEDS_TURN`, `NEEDS_MOVE`, `BLOCKED` 중 하나를 반환한다.
- 사거리와 방향은 `SkillTargetResolverLogic.BuildOffsets()`의 기존 `TargetingType`, `Range`, `TargetOffsets` 해석을 재사용한다.
- EnemyId나 StageId별 분기를 두지 않는다.

### EnemyPatternRunnerComponent — 패턴 커서

- 공격 주기가 시작되면 해당 Pattern Step을 완료 처리하지 않고 유지한다.
- 추적 Command가 성공해도 공격 StepIndex를 전진시키지 않는다.
- 공격 실행이 끝난 뒤에만 성공/실패 분기로 다음 Step을 선택한다.

### BattleSessionComponent — 순서 조정

- 적별 QueueState를 읽어 등록, 추적, 예고, 실행 중 하나만 진행한다.
- 판정 규칙이나 적 종류별 정책은 직접 소유하지 않는다.
- 다중 적은 기존 SpawnOrder 순서를 유지한다.

## 5. 데이터 규격 원칙

첫 수정에서는 새 CSV 컬럼을 추가하지 않는다.

- 공격 사거리: 기존 `SkillDefinitions`의 Targeting/Range 데이터
- 등록 소요 턴: 기존 `EnemySkillDefinitions.EnemyQueueTurns`
- 공격 타일: 기존 `EnemyPatternSteps.TileId`
- 추적 방식: 기존 `TURN_TO_PLAYER`, `MOVE_TOWARD`와 MovementPolicy
- 빠른 등록: 기존 `QUICK` Trait

`EnemyQueueTurns`는 **공격 타일 등록에 필요한 적 행동 수**이며, 공격 예고 후 플레이어가
받는 대응 턴 수가 아니다. 후자를 콘텐츠별로 바꿀 실제 요구가 생길 때만 별도 컬럼을
추가한다.

현재 `EXECUTE_TILE` 이름은 호환을 위해 유지하되, 런타임 의미를 “즉시 공격”이 아니라
“해당 타일의 등록·추적·예고·실행 주기를 시작하거나 계속 진행”으로 문서화한다.

## 6. UI/디버그 읽기 계약

`GetBattleUiState()`의 적 항목에 다음 읽기 전용 값을 제공한다.

```text
QueueState
QueuedTileId
QueueTurnsRequired
QueueTurnsElapsed
ReadinessReason
NextCommandType
IsAttackReady
PreparedTurn
TargetCells
```

- `QueuedTileId`는 `INSERTING`부터 표시한다.
- `TRACKING`에서는 공격 범위를 빨간 위험 칸으로 확정 표시하지 않는다.
- `ATTACK_READY`에서만 실행 예정 범위를 표시한다.
- UI는 사거리와 다음 행동을 자체 계산하지 않고 서버 DTO만 표현한다.
- 현재 HUD는 기능 검증용이며, 최종 UI 제작자가 같은 DTO를 교체 사용한다.

## 7. 마이크로 구현 순서

### Slice A — 상태와 Snapshot 추가

- 기존 행동 변화 없이 QueueState와 DTO 필드를 추가한다.
- 기존 `QueueTurnsRequired/Elapsed`, `IsQueueReady`를 새 상태와 호환시킨다.
- 구 UI가 새 필드를 읽지 않아도 동작하도록 하위 호환을 유지한다.

### Slice B — 사거리 밖 공격 타일 보존

- `EXECUTE_TILE` Step 진입 시 공격 타일을 먼저 등록한다.
- 사거리 밖에서는 타일을 유지하고 임시 회전·추적 Command만 실행한다.
- 추적 성공만으로 Pattern Step이 끝나지 않는지 검증한다.

### Slice C — Readiness 판정과 공격 예고

- 기존 `EnemyIntentResolverLogic`에서 Skill Target 규칙으로 `READY/NEEDS_TURN/NEEDS_MOVE/BLOCKED`를 판정한다.
- 조건 충족 시 `ATTACK_READY`로 전환하고 플레이어 대응 Command를 연다.
- 이 시점부터 공격 Plan을 불변으로 취급한다.

### Slice D — 고정 실행과 빗나감

- 대응 후 플레이어가 벗어나도 추적으로 되돌아가지 않는다.
- 현재 Cell/Facing 기준으로 예고 공격을 실행해 Hit/Miss를 확정한다.
- 밀치기·방향 변경·다른 유닛 진입도 같은 규칙으로 검증한다.

### Slice E — QUICK와 다중 적

- 사거리 안 QUICK은 등록과 `ATTACK_READY`를 같은 적 행동에서 처리한다.
- 사거리 밖 QUICK은 타일만 보유하고 추적한다.
- 여러 적의 서로 다른 QueueState와 SpawnOrder 실행을 검증한다.

### Slice F — 1지역 데이터 적용

- Orange Mushroom: 근접 1칸, 일반 등록 → 추적 → 예고 → 실행.
- Spore: 원거리 최대 2칸, 낮은 피해·낮은 스폰 비율 유지.
- Spore는 1-2부터 등장하고, 사거리 2칸에 들어왔을 때만 공격 예고한다.
- 기존 Stage/Wave/Drop/승패 데이터에는 변경을 만들지 않는다.

### Slice G — 문서와 Maker 회귀

- Data Dictionary, Enemy Authoring Guide, UI DTO Guide를 실제 필드와 맞춘다.
- Maker에서 Build/Runtime 오류와 아래 회귀 시나리오를 확인한다.
- 기능별 커밋은 A~G 경계를 기준으로 나눈다.

## 8. 필수 회귀 시나리오

1. 근접 적이 먼 거리에서 공격 타일을 등록한 뒤 타일을 잃지 않고 접근한다.
2. 추적 중에는 공격 위험 경고가 아니라 이동/회전 예고가 표시된다.
3. 근접 1칸 도달 시 공격이 예고되지만 즉시 피해가 발생하지 않는다.
4. 예고 후 플레이어가 뒤로 이동하면 적은 다시 추적하지 않고 빈 칸을 공격한다.
5. 플레이어가 머물면 예고한 공격이 정상 명중한다.
6. 예고 후 적이 밀리거나 방향이 바뀌면 현재 기하 기준으로 빗나가거나 다른 유닛을 맞힌다.
7. Spore가 거리 3 이상에서 타일을 보유하고, 거리 2에서 예고한다.
8. Spore 예고 뒤 플레이어가 거리 3으로 벗어나면 원거리 공격이 빗나간다.
9. QUICK은 사거리 안에서 같은 적 행동에 준비되고, 사거리 밖에서는 공격하지 않는다.
10. 강제 증원 뒤에도 기존 적의 QueueState/TileId/진행도가 유지된다.
11. 여러 적이 SpawnOrder 순서로 행동하며 각자의 큐 상태를 섞지 않는다.
12. 사망, Victory/Defeat, Reset, Wave 전환, Drop 회수, 플레이어 큐를 회귀시킨다.

## 9. 완료 조건

- 표 데이터만으로 근접/원거리 적이 같은 공격 주기 규격을 사용한다.
- 사거리 밖 추적 중에도 적 공격 타일이 Snapshot에서 보존된다.
- 공격 예고 후에는 플레이어 이동에 따라 행동 종류를 재선택하지 않는다.
- UI가 `TRACKING`과 `ATTACK_READY`를 구분할 수 있다.
- 모든 필수 회귀에 시작·분기·완료 positive log가 있다.
- Maker Build/Runtime Error가 0이다.

## 10. 이번 계획에서 제외

- 보스 점프·착지 패턴
- 공격 후 후퇴/Aggro Trait의 세부 콘텐츠 밸런스
- 최종 적 Intent 아트/UI
- 새 적 종류와 신규 원시 ActionType

위 항목은 기본 공격 주기의 Maker 회귀가 끝난 뒤 별도 Slice로 진행한다.

## 11. 2026-08-15 구현·검증 기록

- ✅ Slice A: Plan Snapshot에 `ReadinessReason`, `NextCommandType`, `NextCommandDirection`, `TargetCells` 추가
- ✅ Slice B: Orange Mushroom/Spore가 사거리 밖에서 공격 Tile을 먼저 등록하고 추적 중 보존
- ✅ Slice C: 기존 `EnemyIntentResolverLogic` 확장으로 `NEEDS_TURN/NEEDS_MOVE/READY/BLOCKED` 판정
- ✅ Slice D: 근접과 2칸 원거리 모두 예고 후 플레이어 이동 시 `NO_TARGET/MISS_EMPTY` 고정 실행
- ✅ Slice E: QUICK 사거리 밖 `TRACKING 0/0`, 사거리 안 `ATTACK_READY 0/0`; 다중 적 Readiness 동시 동결
- ✅ Slice F: `prototype_tracker`, `region_01_spore_ranged`의 첫 `EXECUTE_TILE`을 `ALWAYS` 공격 주기로 이관
- ✅ Slice G: Client DTO `PER_ENEMY_RANGE_AWARE_QUEUE_V2`, Maker Build/Runtime Error 0 검증

검증에서 뒤 SpawnOrder 적의 Readiness가 첫 적 행동 뒤 계산되면 대응 턴이 사라지는 문제를 발견해,
`PrepareEnemyIntent()`가 모든 생존 적의 Readiness를 플레이어 턴 전에 먼저 동결하도록 보정했다.
