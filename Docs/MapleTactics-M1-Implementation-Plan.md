# MapleTactics M1 실제 구현 계획

상태: 구현 전  
목표: 한 스테이지를 시작해 이동·회전·타일 큐 등록·큐 실행·적 행동·증강 선택까지 한 사이클을 완료하는 수직 슬라이스  
범위: 싱글 플레이 우선, 직업 1종/일반 적 2종/보스 1종으로 구조를 증명한 뒤 데이터로 4직업과 추가 스테이지를 확장

## 0. 확정 결정

| 항목 | 결정 |
|---|---|
| 전투 권위 | 서버 |
| 전투 상태 수명 | 전투 맵 엔티티의 `BattleSessionComponent` |
| 전투 격리 | 플레이어당 Instance Room/Instance Map 하나 |
| 플레이어별 런 상태 | 플레이어 엔티티의 `PlayerRunStateComponent` |
| 전투 보드 | 월드 좌표와 분리된 1차원 논리 셀 |
| 추천 맵 | `SideViewRectTile(2)`; 현재 `map01`은 사용자 전환 필요 |
| 클래스 설계 | 깊은 상속 금지, MSW 컴포넌트 조합 |
| 일반 적 AI | 데이터 기반 Pattern Runner |
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

- [ ] `BattleSessionComponent` phase machine 구현.
- [ ] `BoardStateComponent`와 점유 조회 구현.
- [ ] MOVE, TURN Command 검증/적용.
- [ ] `AttackQueueComponent` 최대 슬롯과 등록 순서 구현.
- [ ] QUEUE_TILE의 FreePlay 턴 소비 예외 구현.
- [ ] EXECUTE_QUEUE의 타일별 타깃 재계산 구현.
- [ ] DAMAGE, PUSH, TURN, MOVE 원시 Effect 구현.
- [ ] 사망 제거, Victory/Defeat 구현.
- [ ] `IsResolving`과 ClientSequence 중복 방지 구현.
- [ ] 최소 HUD에 Phase, Turn, Queue, Cooldown, Enemy Intent 표시.

완료 기준:

- 한 전투를 시작부터 승리 또는 패배까지 플레이할 수 있다.
- 같은 입력을 두 번 보내도 한 번만 처리된다.
- FreePlay만 적 턴을 넘기지 않는다.
- 밀치기 후 다음 타일이 변경된 위치를 대상으로 계산한다.

### Phase 2 — 데이터 기반 타일과 적

목표: 기존 원시 타입 조합만으로 새 타일과 일반 적을 추가한다.

- [ ] TileDefinitions/TileEffects 로더.
- [ ] EnemyDefinitions/EnemyPatternSteps 로더.
- [ ] TargetType: FRONT_CELL, FIRST_ENEMY_FORWARD, RANGE_OFFSETS 구현.
- [ ] ConditionType: ALWAYS, DISTANCE_EQ, HP_RATIO_LE, CELL_FREE 구현.
- [ ] Enemy Action: MOVE_TOWARD, TURN_TO_PLAYER, TELEGRAPH, EXECUTE_TILE, RETREAT, MOVE_FIXED_FACING 구현.
- [ ] ContentValidator의 중복 ID, 참조 무결성, 범위, enum 검사 구현.
- [ ] CSV만 추가해 타일 2종과 적 2종을 추가하는 제작 테스트.

완료 기준:

- `.mlua` 변경 없이 기존 Effect/Action 조합의 새 콘텐츠를 추가한다.
- 잘못된 데이터는 전투 시작 전에 오류 코드와 행 정보를 로그로 남기고 차단한다.

### Phase 3 — 스테이지와 보스 패턴

목표: 스테이지 정의만으로 적 배치와 보상 진입을 구성한다.

- [ ] StageDefinitions/StageEnemySpawns 로더.
- [ ] CellIndex, Facing, WaveIndex, SpawnOrder로 유닛 스폰.
- [ ] Stage별 허용 적, 난이도 배수, 보상 풀 연결.
- [ ] EnemySpawnPools 로더.
- [ ] StageEnemyWaves 로더 및 TriggerType(ON_WAVE_CLEARED) 처리.
- [ ] 웨이브 시작 시 결정적 빈 칸 선택 로직 (RunSeed+StageIndex+WaveIndex, 플레이어 좌우 칸 모두 후보).
- [ ] 보스 Phase 조건과 PatternId 교체.
- [ ] Pattern만으로 표현할 수 없는 요구가 실제로 발생한 경우에만 BT Spike 수행.
- [ ] 스테이지 완료 -> 증강 선택 -> 다음 스테이지 전환.
- [ ] 양방향(플레이어 좌/우 동시 교전) 시나리오 회귀 테스트.

완료 기준:

- StageId만 바꿔 다른 적 조합과 패턴을 로드한다.
- 동일 Seed/StageId에서 동일한 배치와 보상 후보가 나온다.
- 웨이브가 진행돼도 좌우 배치와 등장 순서가 동일 Seed에서 동일하게 재현된다.

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
4. `StageEnemySpawns`(Wave 0 고정 배치) 또는 `StageEnemyWaves`+`EnemySpawnPools`(후속 웨이브)에 CellIndex/WaveIndex/SpawnOrder를 추가한다.
5. `StageAugmentPools`에 후보군을 연결한다.
6. ContentValidator를 실행한다.
7. 고정 Seed로 플레이해 Intent와 승패를 확인한다.

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
