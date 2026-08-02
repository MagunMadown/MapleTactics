# 기본 전투 코어 간단 가이드

공동 개발 시 상태 소유권, 스키마와 확장 절차는
[`Architecture-Standard-v0.1.md`](./Architecture-Standard-v0.1.md)를 우선 기준으로 사용한다.
사람 개발자와 AI의 작업 분담, 수정 허용 범위와 검증 절차는
[`Development-Workflow-Guide.md`](./Development-Workflow-Guide.md)를 따른다.
메인 UI·대기·캐릭터 선택 시스템의 전투 호출은
[`Battle-Integration-API.md`](./Battle-Integration-API.md)를 따른다.
스킬 Definition과 Effect Step 제작은
[`Skill-Authoring-Guide.md`](./Skill-Authoring-Guide.md)를 따른다.

## 1. 현재 구현 범위

현재 전투 코어는 6칸 전투 보드에서 플레이어와 좌우의 초반 적 두 명을 배치하고 화면 위치를 논리 셀과 맞추는 단계다.

- 플레이어: 셀 `2`, 오른쪽 방향, HP 100
- 왼쪽 적: 셀 `0`, 오른쪽 방향, 현재 `early_mushroom` HP 6
- 오른쪽 적: 셀 `5`, 왼쪽 방향, 현재 `guard_mushroom` HP 9
- 전투 시작 상태: `PlayerTurn`, 1턴; 플레이어 행동 뒤 생존 적이 `SpawnOrder` 순으로 한 번씩 행동하고 다음 턴으로 복귀
- 셀 번호: `0`부터 `5`까지 사용
- 좌·우 한 칸 이동과 `UnitMovedEvent` 구현
- 이동 없는 방향 전환과 `UnitTurnedEvent` 구현
- 바라보는 앞 셀의 공용 공격 Hit/Miss 판정과 공격 ID가 포함된 `BasicAttackResolvedEvent` 구현
- 기본 베기 피해 3, 강한 베기 피해 6을 같은 `ApplyDamage` 경로로 적용
- 앞 셀의 대상을 한 칸 밀고 이후 타일이 변경된 보드에서 다시 타깃을 찾는 `push` 타일
- `DAMAGE`와 `PUSH`를 기존 판정 함수로 전달하는 최소 `EffectRouterLogic`
- 적 모델의 머리 위에 동기화된 `HP 현재 / 최대` 월드 텍스트 표시
- 설정 가능한 색상과 지속시간을 사용하는 피격 플래시
- 공격마다 고정 ActionName·속도·지속시간을 사용하는 설정형 아바타 모션
- 기본 베기 `0.18`초, 강한 베기 `0.38`초의 공격별 타격 지연과 타격 시점 셀 재판정
- 이동·방향 전환·기본 공격이 공통으로 통과하는 서버 기준 행동 큐와 처리 중 입력 잠금
- Turn·Phase·행동 슬롯·Skill 큐를 맵 수명의 `BattleTurnComponent`가 단일 소유
- Wave 진행·강제 증원 예약·Wave Timer를 `BattleWaveComponent`가 단일 소유
- 기본 용량 3인 가변 타일 큐에 `basic_slash`·`heavy_slash`·`push`를 순서대로 등록·실행·전체 비우기 하는 하단 중앙 `BattleQueueHUD`
- HP 0 사망 판정, `VICTORY`/`DEFEAT` 결과 고정, 현재 전투를 초기화하는 `다시 시작` 버튼
- 적이 멀면 한 칸 접근하고 인접하면 기본 공격하는 최소 Intent
- 플레이어 턴 시작 전에 적 행동을 `PreparedIntent`로 고정하고 HUD에 `접근` 또는 `기본 베기`로 표시
- 한 적이 죽어도 다른 적이 살아 있으면 전투를 계속하고, 모든 적이 죽었을 때만 `VICTORY`
- 적 전용 모션, HP Bar, 별도 무기 이펙트와 Intent 아이콘은 아직 구현하지 않음

## 2. 파일 구조

```text
RootDesk/MyDesk/
├── 01_Combat/
│   ├── Components/
│   │   └── Shared/
│   │       ├── BattleSessionComponent.mlua
│   │       ├── BattleTurnComponent.mlua
│   │       ├── BattleWaveComponent.mlua
│   │       ├── EnemyIntentComponent.mlua
│   │       ├── BoardStateComponent.mlua
│   │       ├── BattleUnitComponent.mlua
│   │       ├── BattleUnitPresentationComponent.mlua
│   │       └── BattleTileColor.mlua
│   ├── Resolvers/
│   │   ├── EffectRouterLogic.mlua
│   │   ├── EnemyIntentResolverLogic.mlua
│   │   └── BattleGatewayLogic.mlua
│   └── Events/
│       ├── BasicAttackResolvedEvent.mlua
│       ├── UnitMovedEvent.mlua
│       └── UnitTurnedEvent.mlua
├── 05_UI/
│   └── HUD/
│       └── BattleQueueHudComponent.mlua
├── 04_Roguelike/
│   └── RunManager/
│       ├── PlayerRunStateComponent.mlua
│       ├── PlayerRunInventoryComponent.mlua
│       └── RunManagerLogic.mlua
└── Models/
    ├── Characters/
    │   └── BattleDummyEnemy.model
    └── Objects/
        └── BattlePlatformTile.model

ui/
└── BattleQueueHUD.ui
```

플레이어별 Pending 전투 요청은
`01_Combat/Components/Shared/BattleEntryStateComponent.mlua`에 저장한다.

`01_Combat/Components/Shared`에는 플레이어와 적이 공통으로 사용하거나 전투 맵 전체에서 사용하는 컴포넌트를 둔다. 플레이어 전용 또는 적 전용 동작이 생기면 각각 `Player`, `Enemy` 하위 폴더를 추가한다.

## 3. 컴포넌트 역할

### BattleSessionComponent

`map01` 루트에 연결된 서버 전용 전투 진행 컴포넌트다.

- 6개 셀의 좌표 계산
- 플레이어와 적 등록
- 유닛 초기 위치 배치
- `BattleTurnComponent` 연결과 행동 실행 조정
- 플레이어의 기본 자유 이동 잠금
- 플레이어 행동 접수·실행·완료와 중복 입력 거절
- 일반 타일 등록마다 적 턴을 진행하되 등록 큐를 유지하고, 별도 실행 명령에서 전체 큐를 순서대로 해소
- 큐를 가진 상태에서도 다음 플레이어 턴에 이동·방향 전환·추가 등록 허용
- 기본값+Modifier 합산 방식의 큐 용량과 Job/Augment/Relic용 추가·제거 API 제공
- 큐 항목의 1-based 개별 제거·순서 변경 Request/API 제공; 두 편집은 턴을 소비하지 않음
- `QueuedTileIds`, `ExecutingTileIds`, `ExecutingTileIndex`로 등록 큐와 실행 큐를 분리
- 두 공격이 공유하는 `TryFrontAttack → ResolveFrontAttackImpact` 모션·타깃·피해·이벤트 경로
- `EnemyIntentComponent`가 소유한 Prepared Snapshot을 사용해 적 행동 실행을 조정하고 다음 Turn 개방
- 밀치기 등으로 보드가 바뀌어도 준비한 ActionType/TileId는 유지하고 실행 시 현재 셀에서 명중 판정
- HP 0 최초 전환의 사망·승패 확정과 현재 Entity를 재사용하는 전투 Reset

전투는 Play 시작 시 자동으로 초기화되므로 현재 단계에서는 별도로 메서드를 호출할 필요가 없다.

### BattleTurnComponent

전투 Phase, Turn, 즉시 행동 슬롯, Skill 등록·실행 큐와 입력 잠금을 소유한다.
Session의 같은 이름 필드는 기존 외부 코드용 호환 Snapshot이므로 직접 대입하지 않는다.
신규 UI는 Turn 컴포넌트를 읽고, 명령은 계속 Session의 `Request...` API로 보낸다.
상세 규격은 [`Battle-Turn-Guide.md`](./Battle-Turn-Guide.md)를 따른다.

### BattleWaveComponent

현재 Wave, 전체 Wave 수, Spawn Trigger, 증원 예약과 Wave 관련 Timer를 소유한다.
Session은 Wave 컴포넌트의 요청을 받아 실제 적 생성과 승패를 처리한다. 신규 HUD는
`BattleWaveState` Entity의 동기화 상태를 읽는다. 상세 규격은
[`Battle-Wave-Guide.md`](./Battle-Wave-Guide.md)를 따른다.

### EnemyIntentComponent와 EnemyIntentResolverLogic

`EnemyIntentComponent`는 전투 맵 수명의 `PreparedIntent` 상태를 단일 소유한다. Session의
`PreparedEnemy...` 동기화 필드는 기존 HUD와 외부 코드용 호환 Snapshot이므로 직접 대입하지
않는다. `EnemyIntentResolverLogic`은 적·플레이어의 논리 Cell/Facing/HP와 검증된
PatternStep 묶음을 입력받아 ActionType/TileId/Direction을 계산하는 무상태 규칙이다.
Session은 유닛 상태를 읽어 Resolver에 전달하고, 실행·Timer·다음 적 순서만 조정한다.

적 행동 정의는 `03_Data/EnemyPatternSteps.csv`가 원본이다.
`EnemyPatternStepRepositoryLogic`은 활성 행을 정렬·변환하고,
`EnemyPatternContentValidatorLogic`은 실행기가 지원하는 타입만 통과시킨다. 콘텐츠 개발자는
기존 ActionType 조합이면 CSV만 수정하고, `_DataService`를 전투/UI에서 직접 호출하지 않는다.
각 적 Entity의 `EnemyPatternRunnerComponent`가 Current/Prepared/Last Completed Step을
독립 소유한다. Resolver는 Runner의 Current Step에서 실패 분기를 탐색하고, 행동 완료 뒤
Runner만 성공/실패 다음 Step을 갱신한다. Session은 준비·실행 순서를 연결할 뿐 Step 상태를
직접 보관하지 않는다.

`CELL_FREE` 조건은 `FRONT`, `BACK`, `TOWARD_PLAYER`, `AWAY_FROM_PLAYER` 중 하나를
`ParamA`로 사용한다. Session이 `BoardStateComponent`를 통해 준비 시점의 빈칸 boolean만
Resolver에 전달하며, Resolver나 UI는 Board Registry를 직접 조회하지 않는다. 실제 이동은
`TryMove()`가 다시 점유와 보드 경계를 검사한다.

`MOVE_AWAY`는 `AWAY_FROM_PLAYER`가 비어 있을 때 플레이어 반대 방향으로 Facing을 맞추고
1칸 이동한다. `BattleSessionComponent.TryMoveAway()`가 경계·점유를 먼저 검사하므로 막힌
행동은 위치와 Facing을 모두 유지한다. Stage 1 적에는 아직 배정하지 않았고,
`prototype_retreat`가 제작·검증용 재사용 패턴을 제공한다.

`TELEGRAPH_TILE`은 피해를 주지 않는 예고 Action이다. `TileId`와 `TelegraphTurns`를 지정하면
각 적의 `EnemyPatternRunnerComponent`가 남은 턴을 소유한다. Complete마다 `2→1→0`으로
감소하고 0에서 성공 Step으로 이동하므로, 다음 Step에 같은 `TileId`의 `EXECUTE_TILE`을 둔다.
취소된 PreparedIntent는 카운트를 소비하지 않는다. 제작 예시는 `prototype_telegraph`를 본다.

신규 UI는 `GetBattleUiState()`의 `EnemyIntents`만 읽는다. 현재 `EnemyIntentMode`는
`PER_ENEMY_FROZEN_PLAN_V1`이며 플레이어 행동 전에 모든 생존 적 계획이 같은 보드 상태에서
고정된다. 각 항목에는 `SpawnOrder`, `CurrentActionIndex`, `ActionCount`, `TraitIds`, `Revision`,
`TelegraphTurnsRemaining`이 포함된다. UI에서 Intent 조건을 다시 계산하거나 Session의 호환
`PreparedEnemy*` Cursor를 전체 계획으로 해석하지 않는다. 제작 규격은
[`Enemy-Plan-Trait-Guide.md`](./Enemy-Plan-Trait-Guide.md)를 따른다.

새 Run은 `BattleSessionComponent.StartNewRun(seed)`로 시작한다. 이 메서드는 `RunManagerLogic`을 통해 플레이어의 `PlayerRunStateComponent`를 초기화한 뒤 같은 Seed로 Stage 1/Wave 1을 다시 구성한다. 전투 맵의 `RunSeed`는 계산에 쓰는 복사본이며 원본 소유자는 플레이어의 Run 상태다.

### PlayerRunStateComponent와 RunManagerLogic

`PlayerRunStateComponent`는 플레이어별 Run 상태의 원본이다. `RunSeed`, `RunSequence`, `RunState`, `CurrentStageNumber`, `CompletedStageCount`, `LastBattleResult`를 보관한다.

런 재화·소모품과 지급/사용 멱등 키는 별도 `PlayerRunInventoryComponent`가 소유한다.
외부 시스템은 두 컴포넌트를 직접 조합하지 않고 `RunManagerLogic` Facade를 사용한다.

`RunManagerLogic`은 이 컴포넌트를 찾고 호출하는 무상태 조정자다. 전역 Logic 안에 특정 사용자의 진행 값을 저장하지 않으므로 이후 map02에서도 같은 플레이어 컴포넌트를 읽어 Run을 이어갈 수 있다. Stage 1 승리 시 현재 구현은 `CompletedStageCount=1`, `CurrentStageNumber=2`, `LastBattleResult=Victory`를 기록한다.

### BoardStateComponent

전투 맵 수명 동안 모든 참가자를 `UnitId`로 등록하고, 셀 점유와 생존 적 목록을 제공하는 서버 전용 Registry다. `BattleSessionComponent`가 Play 시작 시 맵 루트에 한 번 추가하고 유닛 설정 직후 자동 등록한다.

- `RegisterUnit(entity)`: 설정이 끝난 `BattleUnitComponent` 등록 또는 갱신
- `UnregisterUnit(unitId)`: 런타임 Despawn 전에 등록 해제
- `FindByUnitId(unitId)`: 사망 여부와 관계없이 Entity 조회
- `FindAtCell(cellIndex, ignoredUnitId)`: 해당 셀의 살아 있는 유닛 조회
- `CollectLivingEnemies()`: 살아 있는 적을 안정된 순서로 수집
- `CollectRegisteredUnits()`: 모든 유닛을 `SpawnOrder`, 동률이면 `UnitId` 순으로 정렬

새 적을 추가할 때는 고유 `UnitId`와 `SpawnOrder`를 먼저 지정한 다음 `RegisterUnit`을 호출한다. 셀 충돌이나 공격 대상을 찾을 때 별도의 Entity 배열을 만들지 말고 이 Registry를 사용한다.

### BattleUnitComponent

각 전투 참가자의 논리 상태를 보관한다.

| 속성 | 의미 |
|---|---|
| `UnitId` | 전투 내부 유닛 식별자 |
| `Team` | `Player` 또는 `Enemy` |
| `SpawnOrder` | 여러 유닛의 결정적 처리 순서 |
| `CellIndex` | 현재 논리 셀 번호 |
| `Facing` | `Left` 또는 `Right` |
| `MaxHp` | 최대 HP |
| `CurrentHp` | 현재 HP |
| `IsDead` | 사망 여부 |

적에게는 맵에서 컴포넌트가 연결되어 있다. 플레이어는 런타임에 생성되므로 `BattleSessionComponent`가 자동으로 컴포넌트를 추가한다.

적 모델의 `BattleHpText` 자식은 `TextRendererComponent`를 사용한다. `BattleUnitComponent.OnSyncProperty`가 `CurrentHp` 또는 `MaxHp` 변경을 감지하면 `HP 97 / 100` 형태로 갱신한다. HP의 원본은 텍스트가 아니라 항상 `CurrentHp`다.

### BattleUnitPresentationComponent

전투 수치와 분리된 클라이언트 표현 설정을 보관한다. 현재는 HP 텍스트, 피격 플래시와 공격별 아바타 모션 재생을 담당한다. 표현을 바꿀 때 피해·타깃 판정 로직을 수정하지 않는다.

플레이어는 런타임 생성 Entity이므로 `BattleSessionComponent`가 표현 컴포넌트를 자동으로 추가한다. 모든 공격 모션은 `PlayCombatMotion(unitId, motionKey, actionName, playRate, duration)`을 통과한다.

- `actionName=""`: 장착 무기에 맞는 기본 `Attack` Body Action 재생
- `actionName="swingO2"`처럼 지정: 해당 액션을 `ActionStateChangedEvent`의 일회성 동작으로 재생
- `motionKey`: 로그와 콘텐츠 식별에 사용하는 공격별 모션 ID
- `playRate`, `duration`: 공격마다 별도로 설정하는 재생 속도와 복귀 시간
- 재생이 끝나면 `CombatMotionReturnState`와 `Stand` Body Action으로 복귀

현재 `basic_slash`의 설정은 `BattleSessionComponent.BasicSlashMotionKey`, `BasicSlashActionName`, `BasicSlashMotionPlayRate`, `BasicSlashMotionDuration`, `BasicSlashImpactDelay`에서 교체할 수 있다. `BasicSlashActionName`은 `swingO1`로 고정되어 같은 타일을 반복해도 같은 모션을 재생한다. 예를 들어 다른 스킬의 ActionName을 `swingO2`로 지정하면 피해 로직과 분리된 다른 모션을 사용할 수 있다.

### EffectRouterLogic

서버에서 원시 EffectType을 기존 전투 상태 변경 함수로 전달하는 작은 무상태 Router다.

- `DAMAGE` → `BattleSessionComponent.ApplyDamage`
- `PUSH` → `BattleSessionComponent.ResolvePushImpact`

Router는 HP나 CellIndex를 직접 변경하지 않는다. `[BattleEffectRouter] dispatch/resolved` 로그로 실제 분기와 결과를 확인하며, 아직 `DAMAGE`와 `PUSH` 외 EffectType은 거절한다.

`ImpactDelay`는 모션 시작 후 실제 셀 판정과 피해가 발생할 때까지의 시간이다. 기본 베기는 `0.18`, 강한 베기는 `0.38`이며 반드시 해당 공격의 `MotionDuration`과 `ActionDuration`보다 짧게 둔다. 이 값만 조정하면 애니메이션에서 무기가 닿는 프레임과 피해 시점을 맞출 수 있다.

커스텀 액션 이름은 실제 아바타가 지원하는 Action ID여야 한다. 활의 `shoot1`처럼 장비가 필요한 자세는 모션뿐 아니라 해당 무기도 장착해야 자연스럽게 표시된다.

### BattleTileColor

각 `BattleCell`의 `PixelRendererComponent`를 단색으로 채우는 클라이언트 표시용 컴포넌트다. 전투 판정에는 관여하지 않는다.

### BattleQueueHudComponent

`BattleQueueHUD.ui`에 연결된 클라이언트 UI 컴포넌트다. `BattleSessionComponent.GetBattleUiState()`의 읽기 전용 DTO를 통해 `TURN`, 등록 타일, Phase, 처리 상태와 준비된 적 행동을 표시하고, 버튼 클릭을 서버 요청으로 전달한다. 전투 판정은 계속 `BattleSessionComponent`가 담당하므로 UI 이미지·색상·배치를 교체해도 피해 규칙은 바뀌지 않는다.

- `기본 공격 타일`: 남은 슬롯에 `basic_slash` 추가
- `강한 베기 타일`: 남은 슬롯에 `heavy_slash` 추가
- `밀치기 타일`: 남은 슬롯에 `push` 추가
- `실행`: 등록 순서대로 모든 타일 실행
- `전체 비우기`: 턴을 소비하지 않고 등록된 타일 전부 제거

버튼 활성 상태도 DTO의 `Commands`와 함께 동기화된다. 플레이어 턴에는 큐가 가득 차기 전까지 타일을 추가할 수 있고, 한 개 이상 등록되면 실행·전체 비우기 버튼을 사용할 수 있다. 일반 타일 등록은 적 턴을 소비하지만 큐는 다음 플레이어 턴까지 유지된다. 기본 용량은 3이며 `BaseQueueCapacity + QueueCapacityBonus`를 1~6 범위로 제한한 값이 실제 용량이다.

개별 제거와 순서 변경은 `RequestRemoveQueuedTile(index)`,
`RequestMoveQueuedTile(fromIndex, toIndex)`를 사용한다. 서버 API와 DTO는 구현됐으며,
현재 HUD의 슬롯별 버튼/드래그 조작은 후속 시각 UI Slice다.

적 HP가 0이 되면 해당 적 Sprite와 HP 텍스트만 숨겨진다. 다른 적이 살아 있으면 전투를
계속한다. 현재 Wave의 모든 적이 사망하면 마지막 Wave가 아닌 경우 `WaveTransition`을
거쳐 다음 Wave를 생성하고, 마지막 Wave를 완료했을 때만 중앙에 `VICTORY`와
`다시 시작` 버튼이 나타난다. 플레이어 HP가 0이면 즉시 `DEFEAT`가 표시된다. Reset 후
결과 패널은 다시 숨겨지고 플레이어 HP 100, 시작 셀과 방향, Turn 1로 복원되며 Wave 1의
적은 현재 적 정의에 따라 다시 생성된다.

초반 적 체력은 `RootDesk/MyDesk/03_Data/EnemyDefinitions.csv`의 `MaxHp`에서 적 정의별로 조정한다. 현재 `early_mushroom`은 HP 6, `guard_mushroom`은 HP 9이며, Stage의 Wave·Pool 설정이 사용할 적 정의를 선택한다. `BattleSessionComponent.EarlyStageEnemyMaxHp`는 신규 밸런스 설정 경로로 사용하지 않는다.

## 4. 셀과 화면 좌표

논리 위치의 원본은 `TransformComponent.Position`이 아니라 `BattleUnitComponent.CellIndex`다.

```text
CellIndex:  0      1      2      3      4      5
World X:  -2.80  -1.68  -0.56   0.56   1.68   2.80
```

좌표 계산식은 다음과 같다.

```text
WorldX = -2.8 + CellIndex × 1.12
WorldY = 0.12
```

앞으로 이동이나 밀치기를 구현할 때는 먼저 `CellIndex`를 검증하고 변경한 다음 화면 위치를 갱신해야 한다. 화면의 Transform 값을 읽어서 전투 셀을 판단하지 않는다.

## 5. Maker에서 확인하는 방법

1. Maker가 편집 모드인지 확인한다.
2. Workspace Refresh를 실행한다.
3. Build Console 오류가 0건인지 확인한다.
4. Play를 실행한다.
5. Console에서 다음 로그를 확인한다.

```text
[BattleSession] unit registered id=enemy_01 team=Enemy cell=4
[BattleSession] unit registered id=player_01 team=Player cell=1
[BattleSession] ready phase=PlayerTurn turn=1
```

`PlayerControllerComponent`의 자유 이동은 비활성화되어 있다. 화면 하단에서는 `기본 공격 타일 → 실행` 순서로 공격할 수 있다. `비우기`는 등록만 취소하고 턴을 넘기지 않는다.

다음 키는 개발 중 회귀 확인을 위한 즉시 실행 단축키로 유지한다.

- 왼쪽: `LeftArrow` 또는 `A`
- 오른쪽: `RightArrow` 또는 `D`
- 방향 전환: `Space`
- 기본 공격 판정: `F`

이동 성공 시 `CellIndex`와 월드 위치가 함께 변경되고 `UnitMovedEvent`가 발생한다. 보드 밖이나 다른 생존 유닛이 점유한 셀로는 이동할 수 없다.

카메라는 플레이어 카메라의 오프셋을 이동마다 보정하지 않는다. `BattleCameraAnchor`의 고정 카메라로 한 번 전환한 뒤 6칸 보드의 X 중심을 계속 바라보므로, 플레이어가 셀 사이를 이동해도 화면이 따라갔다 돌아오지 않는다.

방향 전환은 셀을 이동하거나 턴을 넘기지 않고 `Facing`만 `Left`/`Right`로 바꾼다. 기본 아바타는 `PlayerControllerComponent.LookDirectionX`를 통해 같은 방향으로 표시되며, 성공하면 `UnitTurnedEvent`가 발생한다.

기본 공격은 모션을 먼저 시작하고 `BasicSlashImpactDelay=0.18`초 뒤 현재 `CellIndex`와 `Facing`을 다시 읽어 바로 앞 한 셀을 검사한다. 적이 있으면 `HIT`와 함께 `ApplyDamage`가 적 HP를 3 감소시키고, 빈 셀이면 `MISS_EMPTY`, 보드 바깥이면 `MISS_OUT_OF_BOUNDS`로 해결된다. 강한 베기도 같은 경로를 사용하지만 `HeavySlashImpactDelay=0.38`초와 피해 6을 사용한다. 따라서 화면 Sprite나 Collider가 겹치는지가 아니라 타격 시점의 논리 타일 점유가 피해를 결정한다. Miss도 유효한 행동이므로 적 행동으로 이어지고 턴을 소비한다.

밀치기는 `PushImpactDelay=0.18`초 뒤 현재 앞 셀을 다시 찾고, 대상의 `CellIndex`를 바라보는 방향으로 한 칸 이동한다. 목적지가 보드 밖이면 `PUSH_BLOCKED_OUT_OF_BOUNDS`, 다른 생존 유닛이 점유하면 `PUSH_BLOCKED_OCCUPIED`로 위치를 유지한다. 밀치기 자체는 피해를 주지 않으며 성공한 이동은 기존 `UnitMovedEvent`를 발행한다.

적 머리 위 HP 텍스트는 공격 적중 후 `100 / 100 → 97 / 100`처럼 자동 갱신된다. 적 Entity의 자식이므로 이후 적이 이동하더라도 같은 상대 위치를 따라간다.

키보드의 즉시 행동 요청은 `TryQueuePlayerAction`을 통과한다. 타일 큐 실행은 등록 문자열을 `ExecutingTileIds`로 동결한 뒤 `ExecutingTileIndex`를 한 칸씩 증가시키며 각 타일의 Resolve와 모션 시간을 끝까지 기다린다. 마지막 타일까지 끝난 뒤에만 `EnemyTurn`으로 전환되고, `0.25`초의 짧은 판단 시간 뒤 적 행동 하나가 실행된다. 적 행동까지 끝나면 `TurnNumber`가 1 증가하고 `PlayerTurn`으로 돌아오며 입력 잠금이 해제된다.

화면 하단의 `BattleQueueHUD`는 `빈 큐 (0/2)`, `[밀치기] → [기본 베기] (2/2)`처럼 전체 순서를 표시한다. 실행 중인 타일에는 `▶`가 붙고 상태 문구에는 현재 실행 인덱스가 표시된다. 등록된 타일이 있을 때 키보드 즉시 행동은 `TILE_QUEUE_OCCUPIED`로 거절된다.

적 이동 방식은 `BattleSessionComponent.EnemyMovementPolicy`에서 선택한다. 기본값 `TRACK_PLAYER`는 플레이어가 현재 Facing 반대편에 있으면 `TURN_TO_PLAYER`를 한 행동으로 준비하고, 이미 플레이어를 바라보면 `MOVE_TOWARD` 또는 앞 칸 `EXECUTE_TILE/basic_slash`를 준비한다. `FIXED_FACING`은 플레이어 위치로 회전하지 않고 현재 Facing을 `MOVE_FIXED_FACING`의 방향으로 사용한다.

준비 결과는 플레이어 턴 동안 `PreparedEnemy*` 동기화 속성에 보관되고 HUD에는 `적 예고: 플레이어 방향 전환`, `추적 접근`, `고정 방향 전진`, `기본 베기`, `대기` 중 하나로 보인다. 고정 방향 이동이 경계 또는 다른 생존 유닛의 점유에 막히면 자동 반전하지 않고 현재 Cell과 Facing을 유지한 채 `WAIT_OUT_OF_BOUNDS` 또는 `WAIT_CELL_OCCUPIED`로 행동을 완료한다.

플레이어 행동으로 적이 밀려나도 이미 준비한 행동 종류는 다시 고르지 않는다. 준비한 것이 기본 베기라면 이동 대신 현재 위치와 준비 당시 Facing을 사용해 앞 셀을 공격하며, 닿지 않으면 `MISS_EMPTY`로 턴을 소비한다. 행동을 완료한 뒤 다음 플레이어 턴이 열릴 때만 새 Intent를 준비한다. 별도 BT나 범용 AI 프레임워크는 아직 만들지 않았다.

대표 재타깃 순서는 `push|basic_slash`다. 플레이어 Cell 1, 적 Cell 2에서 실행하면 밀치기가 적을 Cell 3으로 옮긴다. 두 번째 기본 베기는 큐 등록 당시의 적을 기억하지 않고 현재 앞 셀인 Cell 2를 다시 검사하므로 `MISS_EMPTY`가 된다.

HP가 0이 되면 `ApplyDamage → HandleUnitDied`가 한 번만 실행된다. 플레이어가 사망하면 즉시 `Defeat`이며, 웨이브의 마지막 적이 사망하면 `WaveTransition`으로 들어간다. 마지막 웨이브까지 끝났을 때만 `BattlePhase=BattleEnded`, `WaveState=StageCleared`, `BattleResult=Victory`가 된다.

`map01`에는 적을 고정 배치하지 않는다. `BattleSessionComponent`가 시작할 때 `BattleDummyEnemy.model`의 ID인 `battledummyenemy`로 Wave 1을 생성하고, 웨이브 완료 시 기존 적을 Registry에서 해제·파괴한 뒤 다음 웨이브를 생성한다. 현재 Stage 1은 `TotalWaves=3`, 웨이브당 좌우 적 2명이며 HP는 `EnemyDefinitions.csv`의 적 정의를 따른다. 현재 `early_mushroom`은 HP 6, `guard_mushroom`은 HP 9다. `다시 시작`도 같은 런타임 생성 경로로 Stage 1 / Wave 1을 다시 만든다.

## 6. 다음 기능을 추가할 때

현재 타일 행동 처리 흐름은 다음과 같다.

```text
기본 공격 타일 버튼
→ RequestQueueTile("basic_slash")
→ TryQueueTile이 남은 용량과 PlayerTurn 검사 후 순서대로 추가
→ 실행 버튼 / RequestExecuteQueuedTile()
→ 등록 큐를 ExecutingTileIds로 동결
→ ExecutingTileIndex의 타일을 기존 공격 행동으로 변환
→ 공격 모션·ImpactDelay·타격 시점 재판정·Event까지 완료
→ 다음 인덱스를 같은 방식으로 실행
→ 마지막 타일까지 완료된 뒤 EnemyTurn 시작
→ 이미 PREPARED 상태인 적 Intent를 Hold
→ 저장된 TURN_TO_PLAYER / MOVE_TOWARD / MOVE_FIXED_FACING / EXECUTE_TILE을 그대로 실행
→ Complete 후 TurnNumber 증가
→ 플레이어 SkillRuntimeState의 Cooldown 1 감소
→ PlayerTurn 복귀, 다음 Intent 준비와 입력 잠금 해제
```

스킬 Cooldown은 각 전투 참가자의 `SkillRuntimeStateComponent`가 소유한다. 큐 등록과
실행 직전에 서버가 각각 검사하며, Cooldown이 있는 같은 스킬은 한 큐에 중복 등록할 수
없다. HUD는 `CD 강한 베기 1`처럼 동기화된 남은 턴을 표시하고 해당 버튼을
비활성화한다. 상세 규칙은
[`Cooldown-Runtime-Guide.md`](./Cooldown-Runtime-Guide.md)를 따른다.

다른 스크립트가 `CellIndex`, HP, 턴을 직접 변경하지 않도록 한다. 전투 상태 변경은 항상 `BattleSessionComponent` 또는 이후에 추출될 전용 Resolver를 통해 수행한다.

큐를 통과한 이동 결과는 다음 로그로 확인한다.

```text
[BattleInput] move requested direction=1
[BattleQueue] queued action=MOVE direction=1
[BattleQueue] started action=MOVE direction=1
[BattleMove] success unit=player_01 from=1 to=2 x=-0.56
[BattleEvent] UnitMovedEvent received unit=player_01 from=1 to=2
[BattleQueue] completed action=MOVE success=true reason=OK
```

공격 타일의 등록·실행·비우기는 다음 로그로 확인한다.

```text
[BattleTileQueue] registered tile=basic_slash turn=2
[BattleTileQueue] executed tile=basic_slash action=BASIC_ATTACK turn=2
[BattleTileQueue] cleared tile=basic_slash turn=2
```

`registered` 뒤에는 실행 또는 비우기 중 하나만 발생한다. 타일이 등록된 동안 이동·방향 전환·즉시 공격을 요청하면 `[BattleQueue] rejected ... reason=TILE_QUEUE_OCCUPIED`가 남는다.

방향 전환은 다음 로그로 확인한다.

```text
[BattleInput] turn requested
[BattleTurn] success unit=player_01 from=Right to=Left cell=1
[BattleEvent] UnitTurnedEvent received unit=player_01 from=Right to=Left
```

기본 공격 판정은 다음 로그로 확인한다.

```text
[BattleInput] basic attack requested
[BattleQueue] queued action=BASIC_ATTACK direction=0
[BattleQueue] started action=BASIC_ATTACK direction=0
[BattleMotion] started unit=player_01 motion=basic_slash mode=CUSTOM_ACTION action=swingO1 rate=1 duration=0.45
[BattleImpact] scheduled attack=basic_slash delay=0.18
[BattleImpact] triggered attack=basic_slash elapsed=0.19
[BattleDamage] applied source=player_01 target=enemy_01 amount=3 hp=100->97
[BattleAttack] resolved attack=basic_slash source=player_01 facing=Right target=enemy_01 cell=2 hit=true reason=HIT damage=3 hp=100->97
[BattleEvent] BasicAttackResolvedEvent attack=basic_slash source=player_01 target=enemy_01 cell=2 hit=true reason=HIT damage=3 hp=100->97
[BattlePresentation] hp refreshed unit=enemy_01 text=HP 97 / 100
[BattlePresentation] hit flash started unit=enemy_01 duration=0.18
[BattlePresentation] hit flash restored unit=enemy_01
[BattleQueue] completed action=BASIC_ATTACK success=true reason=IMPACT_PENDING
[BattleMotion] restored unit=player_01 motion=basic_slash state=IDLE
```

행동 자체가 유효하지 않으면 `OUT_OF_BOUNDS`, `CELL_OCCUPIED`, `INVALID_PHASE`, `UNIT_DEAD` 등의 이유로 큐가 즉시 비워지고 적 턴도 시작하지 않는다. 처리 중 다시 입력하면 `[BattleQueue] rejected ... reason=ACTION_PROCESSING` 로그가 남고 두 번째 행동은 실행되지 않는다.

한 턴의 전체 순서는 다음 로그로 확인한다.

```text
[BattleEnemyIntent] prepare enemy=enemy_01 pattern=prototype_basic step=1 action=EXECUTE_TILE tile=basic_slash turn=2
[BattleEnemyIntent] hold enemy=enemy_01 pattern=prototype_basic step=1 action=EXECUTE_TILE tile=basic_slash turn=2
[BattleTurnFlow] phase=EnemyTurn turn=2
[BattleEnemyIntent] execute enemy=enemy_01 pattern=prototype_basic step=1 action=EXECUTE_TILE tile=basic_slash preparedTurn=2 currentTurn=2
[BattleEnemyIntent] complete enemy=enemy_01 pattern=prototype_basic step=1 action=EXECUTE_TILE tile=basic_slash success=true
[BattleTurnFlow] phase=PlayerTurn turn=3
```

웨이브 전환과 Reset은 다음 로그로 확인한다.

```text
[BattleWave] spawned stage=1 wave=1/3 enemies=2 hp=6
[BattleWave] cleared stage=1 wave=1/3 nextWave=2
[BattleWave] spawned stage=1 wave=2/3 enemies=2 hp=6
[BattleResult] result=Victory stage=1 wave=3/3 turn=1
[BattleReset] completed stage=1 wave=1/3 playerCell=2 enemyHp=6
```

## 7. 파일 작업 주의사항

- `.mlua` 파일을 변경하거나 이동한 뒤에는 Maker Refresh가 필요하다.
- `.codeblock`과 `.directory`는 Maker가 자동 생성하므로 직접 수정하지 않는다.
- `map01`은 현재 `MapleTile(0)`이며 플레이어 물리는 `RigidbodyComponent` 계열을 사용한다.
- 스크립트 참조 이름은 폴더 경로와 무관하게 `script.BattleSessionComponent`처럼 파일 이름을 사용한다.

## 8. 개인별 로그라이크 확장

개인별 로그라이크의 맵·런 수명과 컴포넌트 책임은 [`Solo-Roguelike-Architecture.md`](Solo-Roguelike-Architecture.md)를 따른다.

## 9. 스테이지 웨이브와 강제 증원 설정

웨이브 진행값과 적 전투 수치는 `03_Data`의 세 CSV에서 수정한다.

- `StageEnemyWaves.csv`: 웨이브 순서, 생성 조건, 수량, 동시 생존 제한, 지연값
- `EnemySpawnPools.csv`: Pool ID에 적 정의 ID와 실제 적 Model ID를 연결
- `EnemyDefinitions.csv`: 적 HP, 기본 공격력, 패턴, 이동 정책을 정의

새 적을 추가할 때는 먼저 `EnemyDefinitions.csv`에 전투 수치를 등록한 뒤,
`EnemySpawnPools.csv`에서 `EnemyDefinitionId`와 `EnemyModelId`를 연결한다.

`EnemyDefinitions.csv`의 주요 열은 다음과 같다.

| 열 | 의미 |
|---|---|
| `EnemyDefinitionId` | 코드와 스폰 풀이 참조하는 적 정의 키 |
| `DisplayName` | 제작자가 표에서 구분하기 위한 이름 |
| `MaxHp` | 생성 시 적용할 최대·현재 HP |
| `BasicAttackDamage` | 해당 적 유닛의 기본 공격 피해 |
| `PatternId` | 적 Intent를 만드는 패턴 키 |
| `MovementPolicy` | `TRACK_PLAYER` 또는 `FIXED_FACING` |

```csv
EnemyDefinitionId,DisplayName,MaxHp,BasicAttackDamage,PatternId,MovementPolicy
early_mushroom,초급 주황버섯,6,3,prototype_basic,TRACK_PLAYER
```

각 스폰된 `BattleUnitComponent`가 이 값을 복사해 보관한다. 따라서 강제 증원으로
서로 다른 웨이브가 겹치더라도 적마다 HP·공격력·패턴·이동 정책을 독립적으로 사용할 수 있다.
`EnemySpawnPools.Weight`는 양의 정수 가중치로 실제 선택에 사용한다. 후보를
`EnemyDefinitionId|EnemyModelId`로 정렬한 뒤 `RunSeed`, `WaveIndex`, 스폰 슬롯 번호로
결정적 가중치 롤을 만든다. 같은 Seed와 같은 데이터는 항상 같은 구성을 만들기 때문에
테스트와 리플레이가 재현되며, Seed를 바꾸면 같은 Wave에서도 다른 구성을 만들 수 있다.

```csv
PoolId,EnemyDefinitionId,EnemyModelId,Weight,MinWaveIndex,MaxWaveIndex
stage01_basic,early_mushroom,battledummyenemy,1,1,3
stage01_basic,guard_mushroom,battledummyenemy,1,1,3
```

현재 1:1 설정에서 기본 `RunSeed=1000`의 Wave 1은 `early → guard`,
`RunSeed=1001`의 Wave 1은 `guard → early` 순으로 생성된다. 서버에서 새 런을
시작할 때는 `BattleSessionComponent.StartNewRun(runSeed)`를 호출한다. 이 메서드는
진행 중인 타이머와 적 Registry를 먼저 정리하고 Stage 1 / Wave 1을 정상 생성 경로로
다시 만든다. 결과 화면의 `다시 시작`은 현재 Seed를 유지하는 `ResetBattle()`을 사용한다.

`StageEnemyWaves.csv`의 주요 열은 다음과 같다.

| 열 | 의미 |
|---|---|
| `StageId` | `stage01`처럼 스테이지를 구분하는 키 |
| `WaveIndex` | 1부터 시작하는 웨이브 순서 |
| `SpawnTriggerMode` | `CLEAR_ONLY`, `TURN_LIMIT`, `TIME_LIMIT`, `TURN_OR_TIME` |
| `EnemyPoolId` | `EnemySpawnPools.csv`에서 찾을 적 풀 |
| `SpawnCount` | 해당 웨이브에서 생성할 적 수 |
| `MaxConcurrent` | 이전 웨이브 생존자를 포함한 최대 동시 생존 적 수 |
| `ClearSpawnDelaySeconds` | 전멸 후 다음 웨이브가 등장하기까지의 지연 |
| `ForceAfterTurns` | 현재 웨이브 생성 후 강제 증원까지 허용할 턴 수 |
| `ForceAfterSeconds` | 시간 기준 강제 증원까지 허용할 초 |

기본 규칙은 적 전멸 후 다음 웨이브 생성이다. 제한에 먼저 도달하면 즉시 행동 중간에 생성하지 않고 `ForceSpawnPending`으로 대기한 뒤, 안전한 턴 경계에서 다음 웨이브를 생성한다. 이전 웨이브의 살아 있는 적은 유지되므로 웨이브가 겹칠 수 있다.

설정 예시는 다음과 같다.

```csv
StageId,WaveIndex,SpawnTriggerMode,EnemyPoolId,SpawnCount,MaxConcurrent,SpawnSidePolicy,ClearSpawnDelaySeconds,ForceAfterTurns,ForceAfterSeconds
stage01,1,TURN_LIMIT,stage01_basic,2,5,BALANCED,0.6,4,0
stage01,3,CLEAR_ONLY,stage01_basic,2,5,BALANCED,0.6,0,0
```

설정 변경 후 Maker에서 Refresh하고 Play한다. Console에서 아래 순서로 확인할 수 있다.

```text
[StageWaveData] stage loaded stage=stage01 totalWaves=3
[EnemyData] loaded id=early_mushroom hp=6 attack=3 pattern=prototype_basic movement=TRACK_PLAYER
[StageWaveData] wave loaded stage=stage01 wave=1 enemy=early_mushroom hp=6 attack=3 mode=TURN_LIMIT
[EnemyPool] selected pool=stage01_basic wave=1 slot=2 seed=1000 roll=2/2 definition=guard_mushroom weight=1
[EnemyData] applied unit=enemy_w1_right definition=guard_mushroom hp=9.0 attack=2.0 pattern=prototype_basic movement=FIXED_FACING roll=2/2
[BattleWave] spawned stage=1 wave=1/3 seed=1000 enemies=2 livingTotal=2 composition=early_mushroom,guard_mushroom
[BattleWave] force pending reason=TURN_LIMIT wave=1 nextWave=2
[BattleWave] spawned stage=1 wave=2/3 enemies=2 livingTotal=4
[BattleWave] force spawned reason=TURN_LIMIT wave=2
```

최종 승리는 마지막 웨이브가 이미 생성되었고, 이전 웨이브 생존자를 포함한 모든 적이 사망했을 때만 발생한다.

## 10. 적 드롭과 런 자동 회수

- `EnemyDropDefinitionRepositoryLogic`은 적 ID와 TriggerType으로 드롭 행을 읽고 고정 Seed 기반으로 판정한다.
- `BattleDropComponent`는 적 사망 시 생긴 Pending Drop만 맵 수명 동안 소유한다. 최종 UI는 `BattleSessionComponent:GetBattleSnapshot()`의 `PendingDropSnapshot`, `PendingDropCount`, `DropRevision`을 읽어 임시 표시할 수 있다.
- Stage 승리 시 Pending Drop은 `RunManagerLogic:GrantRunReward()`를 통해 자동 회수된다. 패배하거나 맵 세션이 끝나면 폐기된다.
- 회수된 상태는 `RunManagerLogic:GetRunRewardSnapshot(player)`로 읽는다. 반환값에는 `CurrencySnapshot`, `ConsumableSnapshot`, `ConsumableCapacity`, `ConsumableCount`, `Revision`이 있다.
- Snapshot 문자열은 전송용 DTO다. 다른 기능이 문자열을 직접 수정하면 안 되며, 지급 API와 공개 조회 API만 사용한다.
- 실제 드롭 표는 `RootDesk/MyDesk/03_Data/EnemyDropDefinitions.userdataset`과 `.csv` 페어이며 데이터 사전 §20.1 규격을 따른다. 초반 적 2종의 4개 행은 실제 Dataset에서 로드되고 Repository fallback은 비활성 상태다.
