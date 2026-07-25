# MapleTactics M1 실제 구현 계획

상태: Phase 1 프로토타입 진행 중, 양방향 전투 확장 계획 반영

목표: 한 스테이지를 시작해 이동·회전·타일 큐 등록·큐 실행·적 행동·증강 선택까지 한 사이클을 완료하는 수직 슬라이스  
범위: 싱글 플레이 우선, 직업 1종/일반 적 2종/보스 1종으로 구조를 증명한 뒤 데이터로 4직업과 추가 스테이지를 확장

## 0. 확정 결정

| 항목 | 결정 |
|---|---|
| 전투 권위 | 서버 |
| 전투 상태 수명 | 전투 맵 엔티티의 상태별 `@Component` (`BattleTurnComponent` 등) |
| 전투 격리 | 플레이어당 Instance Room/Instance Map 하나 |
| 플레이어별 런 상태 | 플레이어 엔티티의 `PlayerRunStateComponent` |
| 전투 보드 | 월드 좌표와 분리된 1차원 논리 셀 |
| 추천 맵 | `SideViewRectTile(2)`; 현재 `map01`은 사용자 전환 필요 |
| 클래스 설계 | 깊은 상속 금지, MSW 컴포넌트 조합 |
| 일반 적 AI | 데이터 기반 Pattern Runner |
| 초기 방향 | 생성 시 `InitialFacingPolicy`로 한 번 결정, 이후 Pattern Action만 변경 |
| 웨이브 배치 | 기본 `BALANCED`, 특수 스테이지는 `ANY` |
| 보스 AI | Pattern 우선, 필요할 때만 BT |
| 정적 데이터 | UserDataSet + CSV |
| 런타임 데이터 | Component property/table |
| UI | ClientOnly 표현, 서버 Command 요청만 전송 |
| 랜덤 | 런 Seed 기반 프로젝트 전용 결정적 RNG |
| 전투 판정 | 논리 상태에서 결정, 월드 엔티티는 표현/브리지 |

## 1. 목표 폴더 구조

실제 `.directory` 파일은 만들지 않는다. 폴더만 생성하고 Maker Refresh가 메타데이터를 생성하게 한다.

```text
RootDesk/MyDesk/
├─ 00_Core/
│  ├─ Events/                    # @Event: BattlePhaseChanged, UnitMoved, DamageApplied...
│  ├─ Structs/                   # @Struct: CommandResult, TargetResult 등
│  ├─ Validation/               # ContentValidatorLogic
│  └─ Random/                   # DeterministicRngLogic
│
├─ 01_Combat/
│  ├─ Battle/
│  │  ├─ BattleSessionComponent.mlua
│  │  ├─ BattleCommandRouterComponent.mlua
│  │  └─ BattleViewBridgeComponent.mlua
│  ├─ Board/
│  │  ├─ BoardStateComponent.mlua
│  │  └─ BoardWorldAdapterComponent.mlua
│  ├─ Components/
│  │  ├─ Shared/UnitRuntimeComponent.mlua
│  │  ├─ Player/PlayerCombatComponent.mlua
│  │  └─ Enemy/EnemyPatternRunnerComponent.mlua
│  ├─ Resolvers/
│  │  ├─ TargetResolverLogic.mlua
│  │  ├─ MovementResolverLogic.mlua
│  │  ├─ EffectRouterLogic.mlua
│  │  └─ EnemyActionRouterLogic.mlua
│  └─ AI/
│     ├─ BTNodes/                # M1 기본 범위에서는 비움
│     └─ BehaviourTrees/         # 복잡한 보스가 필요할 때만 추가
│
├─ 02_Deck/
│  ├─ Components/
│  │  ├─ AttackQueueComponent.mlua
│  │  └─ TileInventoryComponent.mlua
│  └─ Catalog/
│     └─ TileCatalogLogic.mlua
│
├─ 03_Data/
│  ├─ Combat/
│  ├─ Stages/
│  ├─ Jobs/
│  └─ Augments/                 # 각 UserDataSet wrapper + CSV pair
│
├─ 04_Roguelike/
│  ├─ Run/PlayerRunStateComponent.mlua
│  ├─ Stage/StageFlowComponent.mlua
│  └─ Augment/
│     ├─ AugmentCatalogLogic.mlua
│     ├─ AugmentOfferLogic.mlua
│     └─ AugmentTriggerLogic.mlua
│
├─ 05_UI/
│  ├─ HUD/BattleHUDLogic.mlua
│  └─ Popup/AugmentSelectLogic.mlua
│
├─ 06_Characters/
│  └─ Models/
│     ├─ Players/
│     └─ Enemies/
│
├─ 07_Effects/
│  └─ BattlePresentationLogic.mlua
│
└─ 99_Test/
   ├─ BattleScenarioTestComponent.mlua
   └─ ContentValidationTestComponent.mlua

Docs/                              # 계획과 프롬프트; RootDesk 밖
```

## 2. 핵심 데이터 계약

### 2.1 BattleCommand

클라이언트가 서버에 보낼 수 있는 값은 다음으로 제한한다.

```text
CommandType: MOVE | TURN | QUEUE_TILE | EXECUTE_QUEUE | USE_SKILL
ArgId: TileRuntimeId 또는 SkillId
ArgInt: Direction 등 제한된 정수
ClientSequence: 중복 방지 번호
```

클라이언트는 `Damage`, `ConsumesTurn`, `TargetId`, `Cooldown`을 보내지 않는다.

### 2.2 UnitRuntime

```text
UnitId
OwnerUserId
Faction
DefinitionId
Hp / MaxHp
CellIndex
Facing (-1|1)
Alive
StatusMap
SpawnOrder
```

### 2.3 TileRuntime

```text
RuntimeId
DefinitionId
OwnerUnitId
RemainingCooldown
DamageBonus
CooldownReduction
EnchantIds
AcquiredOrder
```

### 2.4 안정 정렬 규칙

동일 이벤트에 여러 효과가 반응할 때:

```text
Priority ASC
OwnerAcquiredOrder ASC
EffectSeq ASC
DefinitionId ASC
```

Lua `pairs` 순서는 규칙에 사용하지 않는다.

### 2.5 양방향 전투 객체 영향도

| 객체 | 현재/목표 책임 | 이번 확장의 변경 | 직접 변경하지 않는 것 |
|---|---|---|---|
| `BattleSessionComponent` | Phase, Turn, Command, 행동 완료 순서 조정 | 단일 `EnemyEntity` 직접 소유를 제거하고 `BoardStateComponent`의 생존 적 목록을 순서대로 요청 | 개별 적 PatternStep, 스폰 칸 추첨, UI 표현 |
| `BoardStateComponent` | `UnitId -> Entity/UnitRuntime`, Cell 점유의 단일 원본 | 플레이어 1명과 적 N명 등록, 빈 칸/좌우 칸/점유 조회, 안정 정렬 제공 | 적 행동 선택, 웨이브 진행 |
| `BattleUnitComponent` | UnitId, Team, CellIndex, Facing, HP, 사망 상태 | 기존 상태 유지, 다중 적에서도 UnitId와 SpawnOrder만 고유하게 부여 | 초기 방향 정책과 Pattern 정의 보관 |
| `EnemyPatternRunnerComponent` | 적 한 개의 PatternId, StepIndex, Telegraph 상태 | 해당 적의 다음 Action을 만들고 완료 결과에 따라 StepIndex 갱신 | 보드 상태 직접 수정 |
| `EnemyActionRouterLogic` | EnemyActionType을 무상태 규칙으로 해석 | 추적 회전/이동과 `MOVE_FIXED_FACING`을 분리하고 이동 실패를 `WAIT` 결과로 표준화 | 적별 mutable state 보관 |
| `StageFlowComponent` | Stage/Wave 진행, 턴·시간 기준 증원 예약, 런타임 스폰 요청 | 기본 전멸 스폰과 `TURN_LIMIT`/`TIME_LIMIT` 예외를 평가하고, 안전한 턴 경계에서 모델 Spawn 후 세션에 등록 요청 | Cell 점유 직접 변경, 전투 행동 실행 |
| `BattleUnitPresentationComponent` | Facing/HP/사망/모션의 클라이언트 표현 | 논리 Facing 결과를 표시하고 다중 적 인스턴스 각각 갱신 | 방향 결정과 전투 판정 |
| `BattleQueueHudComponent` | 플레이어 큐와 전투 상태 표시 | Stage/Wave와 `증원까지 N턴` 또는 시간제 증원 대기 상태를 읽기 전용으로 표시 | 서버 전투 상태 변경, 증원 조건 재계산 |
| 적 `.model` | 반복 배치와 런타임 Spawn 가능한 시각/물리 템플릿 | 같은 모델을 좌우 고정 배치와 후속 웨이브에 재사용 | 스테이지별 CellIndex/FacingOverride |

객체 간 상태 변경 흐름:

```text
StageFlowComponent
-> SpawnByModelId(parent = battle map)
-> BattleSessionComponent.RegisterUnit
-> BoardStateComponent.Register/Occupy
-> EnemyPatternRunnerComponent.BuildNextAction
-> EnemyActionRouterLogic.Resolve
-> BoardStateComponent.Move/Turn
-> BattleUnitPresentationComponent 표시
```

웨이브 진행은 전멸을 기본 조건으로 유지한다. 각 웨이브는 생성 시 `SpawnedAtStageTurn`과 `SpawnedAtSeconds`를 기록하고, 데이터가 허용할 때만 턴 또는 시간 제한을 예외 조건으로 평가한다. 시간 제한이 행동·모션 도중 충족돼도 즉시 스폰하지 않고 `ForcedSpawnPending`만 설정한 뒤, 현재 플레이어 큐와 적 행동이 모두 끝난 턴 경계에서 다음 웨이브를 생성한다.

강제 증원으로 여러 웨이브가 겹칠 수 있으므로 `CurrentWave` 하나를 승리 판정에 사용하지 않는다. `HighestSpawnedWave`, 웨이브별 생성 여부, 대기 중 Spawn 요청, Board Registry의 전체 생존 적 수를 함께 관리한다. 마지막 계획 웨이브까지 생성됐고 대기 중 Spawn이 없으며 전체 생존 적 수가 0일 때만 Stage Clear다.

`StageFlowComponent`, Pattern Runner, Router는 `BattleUnitComponent.CellIndex`나 `Facing`을 임의로 직접 쓰지 않는다. 실제 상태 변경은 세션이 승인한 Board/Resolver 경로 하나만 사용한다.

### 2.6 양방향·고정 방향 확장 순서

한 번에 웨이브 전체를 만들지 않고 화면에서 검증 가능한 일곱 단계로 나눈다.

1. **Intent 준비/유지/실행** — 단일 적과 하드코딩 Pattern으로 `Prepare → Hold → Execute → Complete`를 만들고, 밀치기 후 예고 공격이 재선택되지 않는지 확인한다.
2. **단일 적 방향 분리** — 준비된 Intent의 Action 의미에서 `MOVE_TOWARD`와 `MOVE_FIXED_FACING` 차이를 검증한다.
3. **다중 유닛 Registry** — `EnemyEntity` 단일 참조를 Board Registry로 교체하되 화면에는 적 한 명만 유지해 기존 전투 회귀를 확인한다.
4. **좌우 고정 배치** — 6칸 보드에서 테스트 시 Player Cell 2, Enemy Cell 0/5를 사용해 공격·밀치기·점유·사망·Victory를 검증한다.
5. **Pattern/초기 방향 데이터** — `InitialFacingPolicy`와 ActionType을 하드코딩에서 EnemyDefinitions/EnemyPatternSteps로 이전한다.
6. **런타임 Spawn** — 같은 적 모델을 `SpawnByModelId(..., self.Entity.CurrentMap)`로 한 명 생성하고 Registry 등록/해제 수명을 검증한다.
7. **웨이브 분배** — 마지막에 `EnemySpawnPools`, `StageEnemyWaves`, `BALANCED`/`ANY`, Seed 재현을 연결한다.

각 단계는 이전 단계의 Maker build/runtime positive log와 화면 검토가 끝난 뒤에만 다음 단계로 진행한다. 3단계 전에는 범용 Registry를 만들지 않고, 6단계 전에는 웨이브용 새 모델이나 데이터셋을 만들지 않는다.

## 3. 전체 구현 단계

### Phase 0 — 기술 검증과 구조 잠금

목표: 본 구현 전에 가장 위험한 MSW 경계를 작은 코드로 증명한다.

- [ ] `map01`을 SideViewRectTile로 전환할지 확정한다.
- [ ] 개발용 Static Map과 실제 전투용 Instance Map을 분리하거나, 전투 맵의 InstanceMap 정책을 확정한다.
- [ ] 전환한다면 Maker에서 사용자가 수행하고 AI가 `TileMapMode=2`를 재확인한다.
- [ ] 맵 타입에 맞는 Body + MovementComponent를 가진 테스트 유닛 모델을 만든다.
- [ ] Cell 0 -> 1 -> 0 스냅 이동을 서버에서 수행한다.
- [ ] UI 버튼에서 Server Command를 요청하고 senderUserId를 검증한다.
- [ ] 서버 결과를 Client UI 텍스트로 표시한다.
- [ ] UserDataSet을 읽어 숫자/불리언 변환과 잘못된 참조 검증을 수행한다.
- [ ] 두 타일 큐에서 첫 타일 Push 후 두 번째 타일 Target 재계산 테스트를 통과한다.

완료 기준:

- Build error 0.
- Runtime error 0.
- 각 시나리오에 시작/검증/결과 positive log가 있다.
- 맵 타입, Body, 이동 API, 서버/클라이언트 경계가 문서와 일치한다.

### Phase 1 — 전투 코어 수직 슬라이스

목표: 이동, 회전, 큐 등록, 큐 실행, 적 행동, 승패가 이어진다.

- [x] `BattleTurnComponent` Phase/Turn/Queue 상태 소유와 `BattleSessionComponent` 실행 조정 분리.
- [x] `BattleWaveComponent` Wave/강제 증원/Timer 상태 소유와 Session Spawn 조정 분리.
- [ ] `BoardStateComponent`와 점유 조회 구현.
- [ ] 단일 `EnemyEntity` 참조를 UnitId 기반 다중 유닛 Registry로 교체.
- [ ] 플레이어 좌우에 적 1명씩 둔 고정 배치 회귀 시나리오.
- [ ] MOVE, TURN Command 검증/적용.
- [x] `BattleTurnComponent` 가변 최대 슬롯과 등록·실행 큐 순서 구현.
- [ ] QUEUE_TILE의 FreePlay 턴 소비 예외 구현.
- [ ] EXECUTE_QUEUE의 타일별 타깃 재계산 구현.
- [ ] DAMAGE, PUSH, TURN, MOVE 원시 Effect 구현.
- [ ] 사망 제거, Victory/Defeat 구현.
- [ ] `IsResolving`과 ClientSequence 중복 방지 구현.
- [ ] 최소 HUD에 Phase, Turn, Queue, Cooldown, Enemy Intent 표시.
- [ ] 적 Intent를 `Prepare → Hold → Execute → Complete`로 분리하고 플레이어 턴 동안 PreparedIntent를 유지.
- [ ] 밀치기 후 ActionType/TileId는 유지하고 실행 시 현재 CellIndex/Facing으로 타깃을 다시 계산.
- [ ] Phase 1 하드코딩 Pattern과 Phase 2 `EnemyPatternSteps`가 같은 PreparedIntent 계약을 사용.

완료 기준:

- 한 전투를 시작부터 승리 또는 패배까지 플레이할 수 있다.
- 같은 입력을 두 번 보내도 한 번만 처리된다.
- FreePlay만 적 턴을 넘기지 않는다.
- 밀치기 후 다음 타일이 변경된 위치를 대상으로 계산한다.
- 밀치기 후 적이 Intent를 다시 선택하지 않으며, HUD에 예고된 공격과 실제 실행 ActionType/TileId가 일치한다.

협업/소유권 기준:

- 콘텐츠 개발자: `EnemyDefinitions.csv`, `EnemyPatternSteps.csv`의 기존 타입 조합과 밸런스 값
- 전투 코어 개발자: Dataset Loader/Validator, `EnemyPatternRunnerComponent`, Intent 상태 전이, Resolver/Router
- UI 개발자: PreparedIntent 읽기 DTO/Event와 HUD 표현
- 새 적 추가 PR은 기존 ActionType만 사용하면 전투 `.mlua`를 수정하지 않는 것을 기본으로 한다.
- 새 ActionType PR은 Router + Validator + 데이터 사전 + 대표 회귀 로그를 함께 포함한다.

### Phase 2 — 데이터 기반 타일과 적

목표: 기존 원시 타입 조합만으로 새 타일과 일반 적을 추가한다.

- [ ] TileDefinitions/TileEffects 로더.
- [ ] EnemyDefinitions/EnemyPatternSteps 로더.
- [ ] `InitialFacingPolicy`(`FACE_PLAYER`, `FIXED_LEFT`, `FIXED_RIGHT`) Resolver.
- [ ] TargetType: FRONT_CELL, FIRST_ENEMY_FORWARD, RANGE_OFFSETS 구현.
- [ ] ConditionType: ALWAYS, DISTANCE_EQ, HP_RATIO_LE, CELL_FREE 구현.
- [ ] Enemy Action: MOVE_TOWARD, MOVE_AWAY, TURN_TO_PLAYER, TELEGRAPH, EXECUTE_TILE, MOVE_FIXED_FACING 구현.
- [ ] 이동 실패 시 Facing 유지 + WAIT 결과, 자동 반전 금지 검증.
- [ ] ContentValidator의 중복 ID, 참조 무결성, 범위, enum 검사 구현.
- [ ] CSV만 추가해 타일 2종과 적 2종을 추가하는 제작 테스트.

완료 기준:

- `.mlua` 변경 없이 기존 Effect/Action 조합의 새 콘텐츠를 추가한다.
- 잘못된 데이터는 전투 시작 전에 오류 코드와 행 정보를 로그로 남기고 차단한다.

### Phase 3 — 스테이지와 보스 패턴

목표: 스테이지 정의만으로 적 배치와 보상 진입을 구성한다.

- [ ] StageDefinitions/StageEnemySpawns 로더.
- [ ] CellIndex, FacingOverride, WaveIndex, SpawnOrder로 유닛 스폰.
- [ ] Stage별 허용 적, 난이도 배수, 보상 풀 연결.
- [ ] EnemySpawnPools 로더.
- [ ] StageEnemyWaves 로더 및 `SpawnTriggerMode`(`CLEAR_ONLY`, `TURN_LIMIT`, `TIME_LIMIT`, `TURN_OR_TIME`) 처리.
- [ ] 웨이브 생성 시 `SpawnedAtStageTurn`/`SpawnedAtSeconds` Snapshot과 Stage 전체에서 증가하는 `StageTurnNumber` 기록.
- [ ] 전멸 전 `ForceAfterTurns` 도달 시 다음 턴 경계에서 강제 증원.
- [ ] 선택 기능인 `ForceAfterSeconds` 도달 시 `ForcedSpawnPending`만 설정하고 행동·모션 종료 후 증원.
- [ ] 두 제한을 함께 쓰면 먼저 충족한 조건 하나만 소비하고 동일 Wave의 중복 Spawn을 방지.
- [ ] 겹친 웨이브의 모든 생존 적을 같은 EnemyTurn 대상에 포함하고, `MaxConcurrent`/빈 칸 부족 시 Spawn 요청을 순서 보존 대기.
- [ ] 웨이브 시작 시 결정적 빈 칸 선택 로직 (RunSeed+StageIndex+WaveIndex, `BALANCED`/`ANY`).
- [ ] 보스 Phase 조건과 PatternId 교체.
- [ ] Pattern만으로 표현할 수 없는 요구가 실제로 발생한 경우에만 BT Spike 수행.
- [ ] 스테이지 완료 -> 증강 선택 -> 다음 스테이지 전환.
- [ ] 양방향(플레이어 좌/우 동시 교전) 시나리오 회귀 테스트.

완료 기준:

- StageId만 바꿔 다른 적 조합과 패턴을 로드한다.
- 동일 Seed/StageId에서 동일한 배치와 보상 후보가 나온다.
- 웨이브가 진행돼도 좌우 배치와 등장 순서가 동일 Seed에서 동일하게 재현된다.
- `CLEAR_ONLY`는 전멸 전 다음 웨이브를 생성하지 않고, `TURN_LIMIT`은 지정 턴 경계에서 남은 적과 함께 다음 웨이브를 정확히 한 번 생성한다.
- 마지막 웨이브가 출현한 뒤 모든 웨이브의 생존 적이 0명일 때만 Stage Clear가 발생한다.

### Phase 4 — 직업 4종과 증강

목표: Player 클래스 상속 없이 데이터와 패시브 조합으로 직업을 확장한다.

- [ ] JobDefinitions 로더.
- [ ] 시작 HP, 큐 크기, 시작 타일, JobPassiveId 적용.
- [ ] AugmentDefinitions/AugmentEffects/Pool/Conflict 로더.
- [ ] Trigger/Condition/Effect 파이프라인 구현.
- [ ] Unique/StackAdd/StackRefresh/ExclusiveGroup 구현.
- [ ] 재귀 이벤트 SourceTag와 최대 깊이 구현.
- [ ] 증강 3택 UI와 서버 선택 검증.
- [ ] 4직업 최소 데이터와 각 직업 대표 패시브 1개.

완료 기준:

- JobId 변경만으로 초기 빌드가 달라진다.
- StageAugmentPool 변경만으로 후보군이 달라진다.
- 충돌 증강이나 최대 스택 초과 선택이 서버에서 거절된다.

### Phase 5 — 콘텐츠 제작 도구와 회귀 테스트

목표: 다른 제작자가 안전하게 값을 추가할 수 있다.

- [ ] 데이터 사전과 허용 타입 목록 고정.
- [ ] ContentValidator 전체 실행 진입점.
- [ ] 대표 전투 시나리오 자동 재생 Command 목록.
- [ ] Seed + CommandLog 기록과 재현.
- [ ] 제작자 체크리스트와 오류 코드 문서.
- [ ] Model/Stage/Enemy/Tile/Augment 추가 예제 각 1개.

완료 기준:

- 새 제작자가 코드 수정 없이 기존 원시 타입으로 스테이지 하나를 추가한다.
- CI 또는 Maker 테스트에서 모든 데이터 참조 오류를 한 번에 확인할 수 있다.

### Phase 6 — 연출과 출시 준비

- [ ] 논리 즉시 해결과 클라이언트 연출 큐 분리.
- [ ] 이동/밀치기/공격/사망 애니메이션.
- [ ] 짧은 연출은 create/destroy positive log로 검증.
- [ ] 모바일 터치 크기와 PC 입력 경로 검증.
- [ ] 저장은 캐시/dirty/debounce 패턴으로 추가.
- [ ] 성능과 네트워크 payload 점검.

## 4. 첫 구현에서 만들 원시 타입

조립식 제작을 가능하게 하는 최소 어휘다. M1에서는 이 목록을 먼저 안정화한다.

### Commands

`MOVE`, `TURN`, `QUEUE_TILE`, `EXECUTE_QUEUE`

### TargetTypes

`SELF`, `FRONT_CELL`, `RANGE_OFFSETS`, `FIRST_ENEMY_FORWARD`

### EffectTypes

`DAMAGE`, `PUSH`, `MOVE_SELF`, `TURN_TARGET`, `APPLY_STATUS`, `MODIFY_COOLDOWN`

### EnemyActionTypes

`WAIT`, `TURN_TO_PLAYER`, `MOVE_TOWARD`, `MOVE_AWAY`, `MOVE_FIXED_FACING`, `TELEGRAPH_TILE`, `EXECUTE_TILE`

### AugmentTriggers

`TURN_START`, `COMMAND_ACCEPTED`, `TILE_QUEUED`, `BEFORE_TILE_EXECUTE`, `AFTER_DAMAGE`, `UNIT_MOVED`, `ENEMY_DIED`, `STAGE_CLEARED`

## 5. 데이터 제작 절차

새 스테이지를 추가하는 제작자는 다음 순서만 수행한다.

1. 필요한 EnemyId가 존재하는지 확인한다.
2. 새 행동이 아니라 기존 ActionType 조합으로 가능한지 확인한다.
3. `StageDefinitions`에 한 행을 추가한다.
4. `StageEnemySpawns`의 Wave 1 런타임 배치에 CellIndex/WaveIndex/SpawnOrder와 필요한 경우 FacingOverride를 추가한다.
5. 후속 웨이브라면 `StageEnemyWaves`+`EnemySpawnPools`에 SpawnSidePolicy와 후보를 추가한다.
6. `StageAugmentPools`에 후보군을 연결한다.
7. ContentValidator를 실행한다.
8. 고정 Seed로 플레이해 Intent와 승패를 확인한다.

새 원시 타입이 필요하면 데이터에 임의 문자열을 먼저 넣지 않는다. 설계 이슈로 등록하고 Router + Validator + 테스트를 함께 추가한다.

## 6. 구현 세션 공통 완료 규칙

AI는 각 작업을 다음 순서로 완료한다.

1. 기존 구현과 Phase 문서를 읽는다.
2. Native API `.d.mlua` 서명을 확인한다.
3. `.mlua`를 작성한다. `.codeblock`과 `.directory`는 건드리지 않는다.
4. `.model/.map/.ui`는 전용 Builder만 사용한다.
5. Maker `stop -> clear_logs -> refresh -> build logs -> play -> runtime logs -> stop` 순으로 검증한다.
6. 오류 없음만으로 PASS하지 않고 의도한 분기와 값의 positive log를 남긴다.
7. 구현 직후 상태를 `Implemented (untested)`, 검증 후 `Tested`로 문서에 갱신한다.
8. 한 Phase의 구현 가능한 항목을 의존성 순서로 계속 진행하고, 진짜 blocker에서만 멈춘다.

## 7. 주요 리스크와 대응

| 리스크 | 대응 |
|---|---|
| 현재 맵 타입이 설계와 불일치 | Phase 0에서 사용자 전환 후 재확인 |
| Static Map의 세션을 여러 사용자가 공유 | 플레이어당 Instance Map 사용, 또는 UserId별 세션으로 재설계 |
| UI가 서버 상태를 직접 수정 | Server Command 단일 진입점 |
| BT/FSM/Pattern 상태 충돌 | 일반 적은 Pattern Runner만 사용 |
| 데이터 조합이 새 코드처럼 무한 확장된다는 기대 | 원시 타입 목록과 확장 경계 명시 |
| 이벤트 무한 재귀 | SourceTag + MaxDepth |
| Lua table 순서 비결정성 | Seq/Priority/Id 안정 정렬 |
| 중복 네트워크 요청 | ClientSequence + IsResolving |
| 모델이 스크립트 등록 전에 로드 | `.mlua -> refresh -> codeblock 확인 -> model 조립 -> refresh` |
| 물리가 Transform 위치를 덮음 | Movement/Body SetWorldPosition 사용 |
| 한 전역 RunManager가 여러 사용자 상태를 섞음 | 플레이어 엔티티별 PlayerRunStateComponent |
| 단일 EnemyEntity 가정이 다중 적 확장을 막음 | BoardStateComponent를 UnitId/CellIndex의 단일 원본으로 만들고 Session은 조회만 수행 |
| 고정 방향 적이 생성 직후 보드 바깥을 향함 | 기본 InitialFacingPolicy를 FACE_PLAYER로 두고 방향은 생성 순간 한 번만 결정 |
| BALANCED 스폰이 한쪽 빈 칸 부족으로 멈춤 | 가능한 쪽 최소 배치를 수행하고 나머지는 전체 빈 칸 후보로 결정적 fallback |

## 8. M1 완료 정의

다음이 모두 참이면 M1이 완료다.

- 직업 4종 중 하나를 선택해 런을 시작한다.
- 이동/회전/큐 등록/큐 실행의 턴 규칙이 동작한다.
- 적 Intent와 Pattern이 데이터에서 로드된다.
- 스테이지 완료 후 결정적 증강 3택이 표시되고 서버가 선택을 검증한다.
- 다음 스테이지에서 선택 증강이 전투 이벤트에 반영된다.
- 기존 원시 타입만 사용한 새 타일/적/스테이지/증강은 CSV와 모델 조립으로 추가된다.
- 고정 Seed + CommandLog로 대표 전투를 재현한다.
- Build/runtime 오류가 없고 각 핵심 시나리오에 positive log 증거가 있다.
