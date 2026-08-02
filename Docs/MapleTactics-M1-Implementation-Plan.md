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

- [x] `map01`은 `TileMapMode=0` MapleTile을 유지하고 전투 유닛은 서버 Cell 스냅 이동을 사용하기로 확정.
- [ ] 개발용 Static Map과 실제 전투용 Instance Map을 분리하거나, 전투 맵의 InstanceMap 정책을 확정한다.
- [x] 맵 타입 전환 불필요를 확정하고 MapleTile 규칙을 유지.
- [x] 보드 전투 유닛은 물리 이동 모델이 아니라 Cell 상태 + Transform Presentation으로 구성.
- [x] Cell 스냅 이동을 서버 권위로 수행.
- [x] Client Request에서 `senderUserId`를 검증.
- [x] 서버 Command 결과를 디버그 HUD DTO로 표시.
- [x] UserDataSet 숫자/불리언 변환과 잘못된 참조 검증 구현.
- [x] 큐 앞 행동의 이동·밀치기 후 다음 타일 Target 재계산 검증.

완료 기준:

- Build error 0.
- Runtime error 0.
- 각 시나리오에 시작/검증/결과 positive log가 있다.
- 맵 타입, Body, 이동 API, 서버/클라이언트 경계가 문서와 일치한다.

### Phase 1 — 전투 코어 수직 슬라이스

목표: 이동, 회전, 큐 등록, 큐 실행, 적 행동, 승패가 이어진다.

- [x] `BattleTurnComponent` Phase/Turn/Queue 상태 소유와 `BattleSessionComponent` 실행 조정 분리.
- [x] `BattleWaveComponent` Wave/강제 증원/Timer 상태 소유와 Session Spawn 조정 분리.
- [x] `BoardStateComponent`와 점유 조회 구현.
- [x] 단일 `EnemyEntity` 참조를 UnitId 기반 다중 유닛 Registry로 교체.
- [x] 플레이어 좌우에 적을 배치하는 다중 적 회귀 시나리오.
- [x] MOVE, TURN Command 검증/적용.
- [x] `BattleTurnComponent` 가변 최대 슬롯과 등록·실행 큐 순서 구현.
- [x] QUEUE_TILE의 FreePlay 턴 소비 예외 구현.
- [x] EXECUTE_QUEUE의 타일별 타깃 재계산 구현.
- [x] DAMAGE, PUSH, TURN, MOVE 원시 Effect 구현.
- [x] 사망 제거, Victory/Defeat 구현.
- [x] `IsResolving`과 ClientSequence 중복 방지 구현.
- [x] 최소 HUD에 Phase, Turn, Queue, Cooldown, Enemy Intent 표시.
- [x] 적 Intent를 `Prepare → Hold → Execute → Complete`로 분리하고 플레이어 턴 동안 PreparedIntent 유지.
- [x] 밀치기 후 ActionType/TileId를 유지하고 실행 시 현재 CellIndex/Facing으로 타깃 재계산.
- [x] 하드코딩 Pattern과 향후 `EnemyPatternSteps`가 공유할 PreparedIntent 계약 구현.
- [x] `EnemyIntentComponent` 상태 소유와 `EnemyIntentResolverLogic` 무상태 판정 분리. Maker에서 Prepared 유지, 두 적 순차 실행, UI DTO 회귀 검증 완료.

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

- [x] 구 TileDefinitions/TileEffects 명칭을 실제 SkillDefinitions/SkillEffectSteps 규격으로 통합.
- [x] `SkillDefinitions` 9행·`SkillEffectSteps` 9행 실제 Dataset과 fallback 비활성.
- [x] `EnemyPatternSteps` 실제 Dataset, Repository·전용 Validator, BattleSession→Resolver 연결, fallback 비활성 완료. 현재 `CELL_FREE`, `prototype_retreat`, `prototype_telegraph`를 포함한 12행으로 확장.
- [x] 적별 `EnemyPatternRunnerComponent` 상태 소유, 실패 분기 탐색, 실행 성공/실패 후 `NextStepOnSuccess/Failure`, 준비 취소 해제 구현. Maker에서 두 적 독립 상태, 성공 `3→1`·`2→1`, 실패 `1→2`, Current Step 2 시작 Resolver 분기, PlayerTurn 복귀를 검증.
- [x] `InitialFacingPolicy`(`FACE_PLAYER`, `FIXED_LEFT`, `FIXED_RIGHT`) Resolver.
- [x] TargetType: FRONT_CELL, FIRST_ENEMY_FORWARD, RANGE_OFFSETS 구현. 타격 시점 공용 Resolver와 UI 대상 Snapshot 포함.
- [x] ConditionType `ALWAYS`, `DISTANCE_EQ`, `HP_RATIO_LE`, `CELL_FREE` Resolver 구현. `CELL_FREE` 네 Selector, 미등록 값 거부, 빈칸/점유/경계, 명시적 WAIT, 준비 후 점유 변경의 실행 재검사와 실패 전이까지 Maker 검증.
- [x] Enemy Action: `MOVE_TOWARD`, `MOVE_AWAY`, `TURN_TO_PLAYER`, `EXECUTE_TILE`, `MOVE_FIXED_FACING`, `WAIT`, `TELEGRAPH_TILE`의 표 기반 선택/실행 구현. `TELEGRAPH_TILE`은 적별 Runner가 남은 턴을 소유하고 Complete 시에만 감소하며, UI DTO로 남은 턴을 제공한다.
- [x] 이동 실패 시 Facing 유지 + WAIT 결과, 자동 반전 금지 검증. 세 이동 Action이 공통 변환을 사용하고 점유 실패·준비 후 점유 변경에서 상태 불변을 Maker 검증.
- [x] ContentValidator의 중복 ID, 참조 무결성, 범위, enum 검사 구현. `ValidateAllContent()`가 행 위치를 포함한 전체 오류 목록을 반환하며 Stage·Skill·Job·Augment·Node Graph·Enemy Pattern·Drop을 통합 검사한다.
- [x] BattleSession 시작·재구축 전 전체 검증 Gate. 실패 시 스폰·턴 시작을 차단하고 `ContentValidation` UI DTO와 RevisionKey를 제공한다.
- [x] CSV만 추가해 스킬 2종과 적 2종을 추가하는 제작 테스트. 장거리 찌르기·갈라치기와 후퇴형·예고형 적을 기존 Resolver/Executor/Pattern/Model 조합만으로 Maker 검증.

완료 기준:

- `.mlua` 변경 없이 기존 Effect/Action 조합의 새 콘텐츠를 추가한다.
- 잘못된 데이터는 전투 시작 전에 오류 코드와 행 정보를 로그로 남기고 차단한다.

### Phase 3 — 스테이지와 보스 패턴

목표: 스테이지 정의만으로 적 배치와 보상 진입을 구성한다.

- [x] `StageDefinitions`, `StageEnemyWaves`, `EnemySpawnPools` 실제 Dataset 로더.
- [x] CellIndex, FacingOverride, WaveIndex, SpawnOrder로 유닛 스폰.
- [ ] Stage별 허용 적, 난이도 배수, 보상 풀 연결.
- [x] CurrencyDefinitions 최소 실제 Dataset + 공통 Reference Registry의 Category 검증(`RUN_SCOPED`).
- [x] StageRewardDefinitions Repository/Validator — Stage 승리 시 CURRENCY/CONSUMABLE을 PlayerRunInventoryComponent에 멱등 지급.
- [x] RUN_SCOPED 외 재화 참조를 `DATA_REWARD_CURRENCY_NOT_ALLOWED`로 차단하고 전체 콘텐츠 시작 Gate에 포함.
- [x] EnemyDropDefinitions Repository와 `ANY_KILL` 결정적 드롭 판정.
- [x] 적 사망별 Pending Drop 상태, 승리 시 자동 회수, 패배 시 폐기.
- [x] PlayerRunInventoryComponent의 런 재화·소모품 Snapshot과 RewardKey/UseKey 중복 처리 방지.
- [x] EnemyDropDefinitions 실제 Dataset 페어 생성, 호환 행 4개 이관, `Source=DATASET`, fallback 비활성.
- [x] EnemyDropDefinitions의 중복 DropEntryId·EnemyDefinitionId·DropRefId 교차 참조 Validator와 전투 드롭 Gate.
- [x] ConsumableDefinitions 최소 실제 Dataset과 `potion_hp_small` 참조 등록.
- [x] 전투 중 데이터 기반 `HEAL` 소모품 사용, 사용 멱등성, 무료/턴 소비 계약 연결.
- [x] `ANY_KILL` + 큐 실행 2번째 처치 `COMBO_KILL` + `IsBoss` 기반 `BOSS_KILL` Trigger Resolver 연결.
- [x] 실제 월드 Drop Sprite Presentation — 코인/물약 RUID, Cell 위치 생성, 부유 모션, 자동 회수·폐기 시 제거.
- [ ] 최종 Drop/Icon·소모품 UI. 현재 DTO/H 키/HUD는 기능 검증용이며 UI 제작자가 교체.
- [x] EnemySpawnPools 실제 Dataset 로더.
- [x] StageEnemyWaves 로더 및 `SpawnTriggerMode`(`CLEAR_ONLY`, `TURN_LIMIT`, `TIME_LIMIT`, `TURN_OR_TIME`) 처리.
- [x] `SpawnedAtStageTurn`/`SpawnedAtSeconds`와 Stage 전체 `StageTurnNumber` 기록.
- [x] `ForceAfterTurns` 도달 시 다음 안전한 턴 경계에서 강제 증원.
- [x] `ForceAfterSeconds` 도달 시 Pending 설정 후 행동·모션 종료 경계에서 증원.
- [x] TURN/TIME 중 먼저 충족한 조건 하나만 소비하고 동일 Wave 중복 Spawn 방지.
- [x] 겹친 Wave 생존 적 EnemyTurn 포함과 `MaxConcurrent`/빈 칸 부족 대기 처리.
- [x] RunSeed 기반 결정적 빈 칸 선택(`BALANCED`/`ANY`).
- [ ] 보스 Phase 조건과 PatternId 교체.
- [ ] Pattern만으로 표현할 수 없는 요구가 실제로 발생한 경우에만 BT Spike 수행.
- [ ] 스테이지 완료 -> 증강 선택 -> 다음 스테이지 전환.
- [ ] 양방향(플레이어 좌/우 동시 교전) 시나리오 회귀 테스트.
- [x] NodeDefinitions 단일 Node 조회·Stage 역조회·다음 콘텐츠 DTO와 행 단위 검증 골격.
- [x] `NodeDefinitions` 실제 Dataset 2행 이관, fallback 비활성, 그래프 시작점·참조·도달 가능성 검증.
- [x] 다음 노드 선택 RPC, 플레이어별 전환 Snapshot, BATTLE/BOSS·SHOP·EVENT·REST Handler Router와 Client UI DTO.
- [x] `OPEN_SHOP` 최소 서버 소비기 — ShopDefinitions/ShopEntries, Validator, 구매 원자성, Client DTO/Request.
- [x] SHOP 구매/건너뛰기 완료 → 공통 비전투 콘텐츠 완료 → 다음 노드 또는 `RUN_COMPLETED`, 종료 요청 멱등성, Client DTO.
- [ ] 최종 상점 UI와 `OPEN_EVENT`·`OPEN_REST` 소비기, StageId→MapId 전환 Adapter.
- [ ] RegionDefinitions 로더와 NodeGraph 전체 검증 — 지역별 노드 그래프 로드, `IsStartNode` 정확히 1개, 전체 참조·도달 가능성 검증.
- [ ] 지도판 UI가 NodeDefinitions를 읽어 현재 진행 가능한 노드만 선택 가능하게 표시.
- [ ] 지역 보스(`BossStageId`) 클리어 시 `UnlockRegionId`로 다음 지역 잠금 해제.

완료 기준:

- StageId만 바꿔 다른 적 조합과 패턴을 로드한다.
- 동일 Seed/StageId에서 동일한 배치와 보상 후보가 나온다.
- 웨이브가 진행돼도 좌우 배치와 등장 순서가 동일 Seed에서 동일하게 재현된다.
- `CLEAR_ONLY`는 전멸 전 다음 웨이브를 생성하지 않고, `TURN_LIMIT`은 지정 턴 경계에서 남은 적과 함께 다음 웨이브를 정확히 한 번 생성한다.
- 마지막 웨이브가 출현한 뒤 모든 웨이브의 생존 적이 0명일 때만 Stage Clear가 발생한다.
- RegionId만 바꿔 다른 노드 그래프와 몬스터 풀을 로드한다.
- 스테이지 클리어 시 StageRewardDefinitions에 정의된 재화가 정확히 한 번 지급된다.
- 적 드롭은 같은 Seed와 사망 식별자에서 동일하게 재현되고, 같은 RewardKey를 두 번 처리해도 런 보상은 한 번만 증가한다.

### Phase 4 — 직업 4종과 증강

목표: Player 클래스 상속 없이 데이터와 패시브 조합으로 직업을 확장한다.

- [x] JobDefinitions/JobStartingSkillEntries 로더와 참조 Validator.
- [x] 선택한 JobId의 시작 HP·큐 크기를 RunState에, 시작 스킬 수량을 RunInventory에 적용하고 큐 소유권을 검증.
- [x] JobMechanic Router에 `FORWARD_PUSH` Handler를 등록하고 기존 MOVE 턴 경계에 연결.
- [x] JobPassiveSetId를 Augment 런타임에 적용.
- [x] AugmentDefinitions/AugmentEffects 로더와 참조 Validator.
- [ ] StageAugmentPools/AugmentConflicts 로더와 참조 Validator.
- [x] Trigger/Condition/Effect 최소 파이프라인 구현 (`TURN_START`, `ALWAYS`/`HP_RATIO_LE`, `HEAL`/`SELF`).
- [ ] Unique/StackAdd/StackRefresh/ExclusiveGroup 구현.
- [x] 재진입 SourceTag 차단과 최대 이벤트 깊이 구현.
- [ ] 증강 3택 UI와 서버 선택 검증.
- [ ] 4직업 최소 데이터와 각 직업 대표 패시브 1개.
- [ ] `ConditionType=CHANCE_ROLL`(RunSeed 기반 결정적 확률 판정) 구현.
- [ ] `TargetType=REAR_CELL`(현재 Facing 반대편 뒤 칸) Resolver 구현.
- [x] ShopDefinitions/ShopEntries 로더 + SHOP Node·RUN_SCOPED Currency·SKILL/CONSUMABLE 참조 Validator.
- [x] 상점 구매 → SKILL/CONSUMABLE 지급과 재화 차감 원자성, 방문/요청 중복 방지.
- [ ] 상점 RewardType을 AUGMENT/JOB까지 확장하고 전용 상태 소유자 지급 경로 연결.

완료 기준:

- JobId 변경만으로 초기 빌드가 달라진다.
- StageAugmentPool 변경만으로 후보군이 달라진다.
- 충돌 증강이나 최대 스택 초과 선택이 서버에서 거절된다.

### Phase 5 — 콘텐츠 제작 도구와 회귀 테스트

목표: 다른 제작자가 안전하게 값을 추가할 수 있다.

- [ ] 데이터 사전과 허용 타입 목록 고정.
- [x] ContentValidator 전체 실행 진입점과 전투 시작 Gate, 구조화된 행 단위 오류 목록.
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
