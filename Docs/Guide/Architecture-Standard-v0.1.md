# MapleTactics 공동 개발 아키텍처 규격 v0.1

## 0. 문서 상태

| 항목 | 값 |
|---|---|
| 규격 버전 | `0.1` |
| 대상 | Stage, 전투, 스킬, 직업, 증강, 아이템 개발 |
| 기준 구현 | `map01` Stage 1 전투 |
| 현재 맵 방식 | `MapleTile(TileMapMode=0)` |
| 상태 | 초안 규격. Stage 1 마이그레이션과 Stage 2 검증 후 `1.0` 확정 |

이 문서는 여러 개발자가 같은 규칙으로 콘텐츠와 기능을 추가하기 위한 기준이다.
구현되어 있는 기능과 앞으로 도입할 규격을 구분하기 위해 다음 표기를 사용한다.

사람 개발자와 AI의 실제 작업 순서, 파일 소유권, 병렬 개발 Gate와 검증·인수인계 규칙은
[`Development-Workflow-Guide.md`](./Development-Workflow-Guide.md)를 필수 동반
문서로 사용한다.
현재 구현에서 부족한 항목과 우선순위, 각 Gate의 해제 조건은 해당 문서의
`2.1 현재 부족한 항목`을 단일 기준으로 사용한다.
2026-08-01 객체 책임 감사 결과와 수정·유지·남은 부채는
[`Architecture-OOP-Audit-2026-08-01.md`](./Architecture-OOP-Audit-2026-08-01.md)에 기록한다.

- **필수**: 신규 코드와 데이터가 반드시 지켜야 한다.
- **권장**: 특별한 이유가 없다면 따른다.
- **계획됨**: 스키마와 책임만 먼저 정했으며 런타임 구현은 아직 없다.
- **구현됨**: Stage 1에서 Maker 검증까지 끝난 기준 구현이다.

이 문서에서 고정하는 것은 상태 소유권, 호출 방향, 확장 절차다. Dataset의 세부 열과 내부
알고리즘은 호환 규칙을 지키면서 이후 버전에서 확장할 수 있다.

---

## 1. 목표와 비목표

### 1.1 목표

- Stage 개발자는 공용 전투 코드를 수정하지 않고 Stage와 Wave 데이터를 추가한다.
- 스킬 개발자는 기존 Effect 조합만으로 새 스킬을 추가할 수 있다.
- 완전히 새로운 게임 규칙만 새 Executor 또는 Handler를 요구한다.
- 직업, 아이템, 증강은 스킬 코드를 복사하지 않고 Definition과 Modifier로 조합한다.
- UI, 모션, 이펙트 교체가 서버 전투 판정을 변경하지 않는다.
- Dataset 스키마가 바뀌어도 Repository 밖의 수정 범위를 최소화한다.
- 각 기능의 상태 소유자와 변경 진입점을 파일만 보고 판단할 수 있게 한다.

### 1.2 비목표

- 모든 미래 기능을 v0.1에서 구현하지 않는다.
- 스킬마다 별도 클래스를 만드는 대규모 상속 트리를 만들지 않는다.
- Stage 하나만을 위해 범용 비주얼 에디터나 코드 생성기를 만들지 않는다.
- Repository가 Runtime 전투 상태를 보관하지 않는다.
- 전역 `@Logic`이 플레이어별 또는 전투별 변경 상태를 소유하지 않는다.

---

## 2. 변경에 강한 핵심 계약

다음 계약은 v0.1부터 안정 영역으로 취급한다.

1. 플레이어 장기 진행은 `PlayerRunStateComponent`가 소유한다.
2. 전투 맵의 변경 상태는 해당 맵에 붙은 `@Component`가 소유한다.
3. 유닛 HP, Cell, Facing, 사망 상태는 `BattleUnitComponent`가 소유한다.
4. Dataset은 Repository를 통해서만 읽는다.
5. UI는 요청을 보내고 동기화된 상태를 표시할 뿐 전투 상태를 직접 변경하지 않는다.
6. 콘텐츠는 Entity 참조가 아니라 안정된 문자열 ID로 연결한다.
7. 행동은 `Request → Try → Resolve → Apply → Event/Sync → Presentation` 순서를 따른다.
8. `@Logic`은 Repository, Resolver, Router처럼 무상태 서비스로 사용한다.
9. 새 콘텐츠는 기본적으로 데이터 행을 추가한다. 새 규칙이 생길 때만 Handler를 추가한다.
10. 현재 성공한 Stage 1 동작을 유지하면서 책임을 한 영역씩 이동한다.

### 2.1 객체지향 원리 적용 기준

MSW에서는 일반 Lua 클래스 계층보다 Entity/Component 조립과 명시적 메서드 계약을 객체 경계로 사용한다.

- **단일 책임**: 진행, 인벤토리, 전투, 유닛, 표시 상태는 수명과 변경 이유가 다르면 별도 Component가 소유한다.
- **캡슐화**: 외부 객체는 `CurrentHp` 같은 필드를 직접 대입하지 않고 소유자의 `Initialize/Apply/Mark/Consume` API를 호출한다.
- **개방-폐쇄**: 새 콘텐츠는 Dataset 행으로 추가한다. 새 원시 규칙만 Router 한 곳과 독립 Handler를 확장한다.
- **의존 역전**: Session은 구체 Dataset이나 특정 콘텐츠 ID가 아니라 Repository, Validator, Resolver, Facade 계약에 의존한다.
- **조합 우선**: 직업·스킬·소모품별 상속 클래스를 늘리지 않고 Definition + Runtime Component + Handler를 조합한다.
- **인터페이스 분리**: UI는 읽기 DTO와 Request API만 사용하며 서버 내부 상태 소유 API를 호출하지 않는다.

Router의 `EffectType`/`ActionType` 분기는 허용되는 닫힌 확장점이다. 특정 `SkillId`,
`ConsumableId`, `EnemyDefinitionId` 분기는 공용 Runtime에 두지 않는다.

---

## 3. 계층과 의존 방향

```text
Definition Dataset
        ↓
Repository / Validator
        ↓
Runtime State Component
        ↓
Session / Controller
        ↓
Resolver / Effect Executor
        ↓
Event + @Sync
        ↓
UI / Motion / Effect Presentation
```

Validator는 다음 객체 경계를 지킨다.

```text
ContentValidatorLogic (Facade)
        ↓
도메인 Validator (예: EnemyDropContentValidatorLogic)
        ↓
Repository의 행 객체 + ContentReferenceResolverLogic Registry
        ↓
실제 Definition Dataset
```

- Repository는 로드·변환·행 자체의 타입/범위를 소유한다.
- 도메인 Validator는 중복과 여러 Definition 사이의 참조 무결성을 소유한다.
- `ContentReferenceResolverLogic`은 참조 계약별 Dataset·키·활성/정책 열을 Registry로 캡슐화한다. `RUN_CURRENCY`처럼 사용 문맥을 이름에 포함해 상점·메타 재화 정책과 섞이지 않게 한다.
- Session과 Runtime Component는 구체 Dataset을 알지 않고 `ContentValidatorLogic` Facade만 호출한다.
- 새 참조 종류는 Validator의 조건문을 복사하지 않고 Registry spec을 등록한다.

역방향 접근은 금지한다.

- Dataset이 Runtime Entity를 참조하지 않는다.
- Repository가 BattleSession을 변경하지 않는다.
- Presentation이 HP, Cell, Cooldown을 직접 변경하지 않는다.
- Effect Executor가 UI 노드를 직접 조작하지 않는다.
- UI가 Dataset을 직접 조회해 전투 규칙을 재계산하지 않는다.

---

## 4. 상태 소유권

| 상태 | 단일 소유자 | 변경 진입점 | 수명 |
|---|---|---|---|
| Run Seed, 현재 Stage, 완료 Stage | `PlayerRunStateComponent` | `RunManagerLogic` | 플레이어 Run |
| 런 재화, 소모품, 지급·사용 멱등 키 | `PlayerRunInventoryComponent` | `RunManagerLogic` | 플레이어 Run |
| 보유 증강, 스택, 획득 순서, 지급 멱등 키 | `PlayerRunAugmentComponent` | `RunManagerLogic` | 플레이어 Run |
| BattlePhase, Turn, 행동 큐, 입력 잠금 | `BattleTurnComponent` | Turn 공개 API | 전투 맵 |
| 승패, Stage 연결, 전체 실행 조정 | `BattleSessionComponent` | Session 공개 API | 전투 맵 |
| Wave, 증원 예약, Spawn Timer | `BattleWaveComponent` | Wave 공개 API | 전투 맵 |
| Unit HP, Cell, Facing, IsDead | `BattleUnitComponent` | `Apply...` 계열 전투 API | 유닛 |
| 보드 등록과 Cell 점유 | `BoardStateComponent` | Registry API | 전투 맵 |
| 보유 Skill과 Cooldown | `SkillRuntimeStateComponent` | Skill 실행·Turn API | 전투 참가자 |
| 준비된 적 Intent | `EnemyIntentComponent` 또는 Turn Controller | Intent API | 전투 맵/적 |
| 전투 중 미회수 드롭 | `BattleDropComponent` | Drop API | 전투 맵 |
| UI 표시 캐시 | UI Controller | `Refresh...` | 클라이언트 UI |

현재 `SkillRuntimeStateComponent`, `BattleTurnComponent`, `BattleWaveComponent`는
**구현됨** 상태다. `EnemyIntentComponent`는 **계획됨** 상태이며 마이그레이션
전까지 해당 맵 상태는 `BattleSessionComponent`에 존재한다.

`BattleSessionComponent`의 기존 Turn/Queue와 Wave `@Sync` 필드는 단계적
마이그레이션을 위한 호환 Snapshot이다. 직접 변경하지 않고
`PublishTurnStateSnapshot()` 또는 `PublishWaveStateSnapshot()`으로만 갱신한다.
신규 서버 기능은 각 상태 소유 컴포넌트의 공개 메서드를 호출한다. UI는 소유 컴포넌트
경로를 직접 조합하지 않고 Session/Gateway가 제공하는 읽기 DTO와 Request API만 사용한다.

### 4.1 상태 변경 금지 규칙

- 소유자 외부에서 `CurrentHp`, `CellIndex`, `Cooldown`을 직접 대입하지 않는다.
- 외부 모듈은 소유자의 `Try...`, `Apply...`, `Record...` 메서드를 호출한다.
- 상태를 두 컴포넌트에 중복 보관하지 않는다.
- 표시를 위한 복사본이 필요하면 `@Sync` 읽기 전용 Snapshot임을 이름과 문서에 표시한다.
- Timer ID는 Timer를 생성하고 해제하는 컴포넌트가 소유한다.

---

## 5. 목표 폴더 구조

```text
RootDesk/MyDesk/
├── 01_Combat/
│   ├── Components/
│   │   ├── Session/
│   │   │   ├── BattleSessionComponent.mlua
│   │   │   ├── BattleTurnComponent.mlua
│   │   │   └── BattleWaveComponent.mlua
│   │   ├── Unit/
│   │   │   ├── BattleUnitComponent.mlua
│   │   │   ├── SkillRuntimeStateComponent.mlua
│   │   │   └── BattleUnitPresentationComponent.mlua
│   │   └── Board/
│   │       └── BoardStateComponent.mlua
│   ├── Skills/
│   │   ├── SkillExecutionComponent.mlua
│   │   └── EffectExecutors/
│   ├── AI/
│   │   └── EnemyIntentResolverLogic.mlua
│   ├── Modifiers/
│   │   └── ModifierPipelineLogic.mlua
│   ├── Resolvers/
│   │   └── EffectRouterLogic.mlua
│   ├── Jobs/
│   │   └── JobMechanicRouterLogic.mlua
│   └── Events/
├── 00_Core/
│   └── Lobby/
│       ├── LobbyCharacterSelectionLogic.mlua
│       ├── LobbyJobSelectionProvider.mlua
│       ├── LobbyCodexLogic.mlua (+ Monster/Skill/ItemCodexProvider)
│       └── LobbyInteractionComponent.mlua
├── 02_UI/
│   ├── BattleHudPresenterLogic.mlua
│   ├── BattleQueueHudComponent.mlua (대체됨 — §20 참고, 삭제 예정)
│   ├── MapTeleportManager.mlua / MapTeleportButton.mlua
│   └── MinimapUI.mlua
├── 03_Data/
│   ├── Repositories/
│   ├── StageDefinitions.userdataset
│   ├── RegionDefinitions.userdataset
│   ├── StageEnemyWaves.userdataset
│   ├── EnemyDefinitions.userdataset
│   ├── EnemySpawnPools.userdataset
│   ├── EnemyPatternSteps.userdataset
│   ├── BossPhaseDefinitions.userdataset
│   ├── SkillDefinitions.userdataset (공용, 현재 0행 — 실제 스킬은 §11.2 참고)
│   ├── {Warrior,Mage,Archer,Thief,Pirate,Enemy}SkillDefinitions.userdataset
│   ├── SkillEffectSteps.userdataset
│   ├── JobDefinitions.userdataset
│   ├── JobStartingSkillEntries.userdataset
│   ├── AugmentDefinitions.userdataset
│   ├── ConsumableDefinitions.userdataset (§12.2의 옛 ItemDefinitions 계획을 대체)
│   ├── CurrencyDefinitions.userdataset
│   └── StageRewardDefinitions.userdataset
└── 04_Roguelike/
    └── RunManager/
```

MSW 인식 규칙에 따라 `.mlua`와 `.model`은 `RootDesk/MyDesk/`, `.map`은 `map/`,
`.ui`는 `ui/` 아래에 둔다. `.ui`, `.map`, `.model`은 해당 Builder를 통해 수정한다.
`.codeblock`은 직접 수정하지 않는다.

폴더 이동은 기능 마이그레이션과 동시에 수행한다. 빈 폴더를 먼저 대량 생성하지 않는다.

`02_UI/`를 런타임 UI 스크립트의 단일 진입 폴더로 사용한다(`05_UI`는 2026-08 중 여기로
통합·삭제됐다). Deck은 현재 범위에 포함하지 않으며, 보유 타일·장착 구성·드로우/셔플 같은
독립 덱 기능을 실제로 개발할 때만 `05_Deck/`을 생성한다. 전투 행동 큐의 실행 상태는 Deck이
아니라 Combat Runtime이 소유한다.

로비(캐릭터/직업 선택, 도감)는 `00_Core/Lobby/` 아래에서 전투와 분리된 자체 컴포넌트로
구현한다. 로비 이동 `00_Core/LobbyGridMovementComponent`는 `BoardStateComponent`나
`BattleSessionComponent.TryMove()`의 논리 Cell/점유 판정을 쓰지 않고 `MinX`/`MaxX` 범위로만
제한하지만, 방향 입력·이동 시간·곡선·홉 연출은 전투와 같은 `00_Core/Movement/PlayerGridMovementLogic`
을 공유한다(2026-09-05 통합).

---

## 6. 컴포넌트와 서비스 책임

### 6.1 BattleSessionComponent

최종적으로 다음 책임만 가진다.

- 전투 시작과 종료
- Player 등록
- Board, Turn, Wave, Skill 컴포넌트 연결
- 승패 확정
- RunManager에 Stage 결과 전달
- 전체 Reset과 다음 Stage 전환 조정

스킬별 피해, 적 패턴 분기, Wave 데이터 해석을 직접 구현하지 않는다.

### 6.2 BattleTurnComponent — 구현됨

- 현재 Turn과 Phase
- 즉시 행동 슬롯과 가변 Skill 큐
- 등록 큐와 실행 큐의 분리
- 기본+Modifier 방식의 큐 용량과 상하한
- 적 라운드를 지나 유지되는 플레이어 등록 큐
- 턴 소비 Command와 무료 큐 편집을 분리하는 1:N 상태 계약
- 실행 중 입력 잠금
- 행동 완료 후 적 Turn 전환
- Wave 전환과 전투 종료 Phase 반영

상태 변경은 `ResetTurnState`, `ConfigureQueueCapacity`,
`UpsertQueueCapacityModifier`, `RemoveQueueCapacityModifier`, `OpenPlayerTurn`,
`TryReserveImmediateAction`, `TryAppendSkill`, `TryFreezeSkillQueue`,
`BeginEnemyTurn`, `CompleteEnemyTurn`, `SetPhase`를 통해서만 수행한다.
Session은 타깃·피해·모션·적 Intent 실행을 조정하고
행동 경계에서 Turn API를 호출한다. 자세한 사용법은
[`Battle-Turn-Guide.md`](./Battle-Turn-Guide.md)를 따른다.

Client UI는 Turn Entity 경로와 Session 호환 필드를 직접 조합하지 않고
`BattleSessionComponent.GetBattleUiState()`의 읽기 전용 DTO를 사용한다.

### 6.3 BattleWaveComponent — 구현됨

- Stage Wave 진행
- 전멸 후 다음 Wave
- Turn/시간 제한 강제 증원 예약
- Spawn 수와 동시 생존 수 검증
- Spawn/Cleanup Timer 소유

Wave 번호, 상태, 현재 Spawn 규칙, 강제 증원 예약과 Wave/시간 Timer를 소유한다.
Session은 실제 Enemy Definition 조회와 Spawn, 보드 수용량 판정, 승패 확정을 담당한다.
맵에는 `BattleWaveState` 자식 Entity로 배치한다. 사용 규격은
[`Battle-Wave-Guide.md`](./Battle-Wave-Guide.md)를 따른다.

### 6.4 BattleUnitComponent — 구현됨

- `UnitId`, `Team`, `SpawnOrder`
- `CellIndex`, `Facing`
- `MaxHp`, `CurrentHp`, `IsDead`
- 적 Definition과 전투 수치 Snapshot

상태 초기화·피해·회복·사망·셀·방향 변경은 각각 `InitializeBattleState`,
`ApplyDamage`, `ApplyHealing`, `MarkDead`, `ApplyCellChange`, `ApplyFacingState`를
통한다. Session과 Effect Handler가 소유 필드를 직접 대입하지 않는다.

### 6.5 BoardStateComponent — 구현됨

- `UnitId → Entity` Registry
- Cell 점유 조회
- 생존 적 조회
- 결정적인 `SpawnOrder → UnitId` 정렬

### 6.6 SkillRuntimeStateComponent — 구현됨

- 전투 참가자별 `SkillId → RemainingTurns` 상태 소유
- 스킬 사용 가능 여부의 서버 판정
- 실행이 시작된 스킬의 Cooldown 기록
- 다음 소유자 Turn 시작 시 Cooldown 감소
- UI가 읽는 `CooldownSnapshot`과 `CooldownRevision` 동기화

현재 플레이어 Cooldown은 적 행동 전체가 끝나 다음 `PlayerTurn`이 열리기 직전에 1
감소한다. `CooldownTurns=1`은 사용한 턴의 같은 큐에서 재사용할 수 없고 다음 플레이어
턴에 다시 사용할 수 있다. `CooldownTurns=2`는 다음 플레이어 턴에도 1이 남고 그 다음
플레이어 턴에 준비된다.

### 6.7 Repository Logic

- Dataset 행 조회
- 필수 필드 검증
- 기본값 적용
- 문자열을 Runtime Definition table로 변환
- 구버전 스키마 호환

Runtime Entity와 Timer를 보관하지 않는다.

### 6.8 Resolver와 Executor

- Resolver는 대상과 결과를 계산한다.
- Executor는 하나의 원자적인 Effect를 적용한다.
- Router는 `EffectType`을 Executor에 연결한다.
- Executor는 다른 Executor를 직접 호출하지 않는다.
- 복수 Effect 순서는 `SkillExecutionComponent`가 조정한다.

### 6.9 BattleGatewayLogic — 구현됨

메인 UI, 대기 화면, 캐릭터 선택, 맵 이동 시스템이 사용하는 전투 진입 Facade다.
플레이어별 Pending 정보는 `BattleEntryStateComponent`가 소유하고 Gateway Logic은
상태를 직접 보관하지 않는다.

외부 호출 규격은
[`Battle-Integration-API.md`](./Battle-Integration-API.md)를 따른다.

### 6.10 BattleEntryStateComponent — 구현됨

- StageId, CharacterId, JobId, LoadoutId, RunSeed Snapshot
- `NEW_RUN` 또는 `CONTINUE_RUN`
- `IDLE → PREPARED → STARTED` 입장 상태
- 플레이어별 증가하는 RequestId
- 실패 및 취소 Reason

MSW 컴포넌트는 외부에서 생성자를 호출하지 않는다. Gateway가 플레이어에 컴포넌트를
찾거나 추가하고, `Prepare(...)`와 `BattleSession.InitializeFromEntry(...)`를 사용한다.

### 6.11 Drop·Run Inventory·Consumable — 구현됨

- `BattleDropComponent`: 사망별 Trigger 집합 판정 결과와 Pending Drop 수명 소유
- `BattleDropPresentationComponent`: Pending Drop을 월드 오브젝트로 표시하고 표시 Entity 수명만 소유
- `EnemyDropTriggerResolverLogic`: `ANY_KILL`, 큐 실행 중 2번째 처치부터 `COMBO_KILL`, `IsBoss=true`의 `BOSS_KILL` 조합
- `PlayerRunInventoryComponent`: 런 재화·소모품과 지급/사용 멱등 키 소유
- `ConsumableDefinitionRepositoryLogic`: 사용 시점·턴 소비·효과 DTO 검증
- `ConsumableEffectRouterLogic`: 원시 EffectType을 독립 Handler에 연결
- `ConsumableHealEffectLogic`: 유닛 소유 API로 회복 적용

최종 UI는 `GetBattleUiState().Drops`, `RunInventory`를 읽고
`RequestUseConsumable(consumableId, requestId)`만 호출한다.

드롭 판정과 표시를 분리한다. `BattleDropComponent`의 Pending Snapshot이 권위 상태이며,
표시 Entity 생성 실패는 보상 판정이나 자동 회수를 취소하지 않는다. 스프라이트·부유 모션·
OrderInLayer는 `BattleDropPresentationComponent`와 `BattleDropPickup.model`에서 교체한다.

---

## 7. 메서드 명명과 공통 결과

### 7.1 접두사 규격

| 접두사 | 의미 |
|---|---|
| `Request...` | Client/UI에서 호출 가능한 요청 진입점 |
| `Try...` | 서버 검증 후 성공 여부 반환 |
| `Resolve...` | 대상·범위·수치 판정 |
| `Apply...` | 상태 소유자에게 실제 변경 적용 |
| `Execute...` | 검증된 Definition 또는 Effect 실행 |
| `Record...` | Run 결과나 누적 기록 반영 |
| `Get...` | 상태를 변경하지 않는 조회 |
| `Collect...` | 정렬된 복수 결과 조회 |
| `Refresh...` | UI·모션 등 표현 갱신 |
| `Reset...` | 소유 상태를 정의된 초기값으로 복원 |

### 7.2 공통 결과 table

`Try`, `Resolve`, `Execute`, `Apply` 계열은 가능하면 다음 필드를 사용한다.

```lua
{
    Success = true,
    Reason = "OK",
    SourceUnitId = "player_01",
    TargetUnitId = "enemy_w1_left",
    Value = 3,
    Data = nil
}
```

- `Success`: 필수 boolean
- `Reason`: 필수 string
- 나머지 필드는 해당 기능에 필요한 경우 사용
- 정상 실패는 Lua Error 대신 `Success=false`와 Reason으로 반환
- 프로그래밍 오류나 필수 Definition 누락은 로그를 남기고 실행을 중단

### 7.3 Reason ID

Reason은 `UPPER_SNAKE_CASE`를 사용한다.

```text
OK
INVALID_REQUEST
INVALID_TURN
ACTION_PROCESSING
UNKNOWN_SKILL
UNKNOWN_EFFECT
COOLDOWN_ACTIVE
INSUFFICIENT_COST
INVALID_TARGET
CELL_OCCUPIED
OUT_OF_BOUNDS
TARGET_DEAD
CONTENT_VALIDATION_FAILED
```

UI 표시 문구는 Reason ID와 분리한다. 서버 Reason을 그대로 사용자 문구로 사용하지 않는다.

---

## 8. ID와 직렬화 규격

- 콘텐츠 ID는 `lower_snake_case`를 사용한다.
- Runtime Unit ID는 의미와 Wave를 포함한다. 예: `enemy_w2_left`.
- DisplayName은 ID로 사용하지 않는다.
- Dataset 간 참조는 Entity가 아니라 문자열 ID를 사용한다.
- 태그 목록은 v0.1에서 `|` 구분 문자열을 사용하고 Repository에서 table로 변환한다.
- 순서가 중요한 데이터는 문자열 목록보다 `StepIndex` 행 구조를 사용한다.
- 수치가 없는 상태를 `-1`, 빈 문자열, `0` 중 무엇으로 표현할지 스키마별로 명시한다.

---

## 9. Dataset 접근과 버전 규칙

### 9.1 필수 규칙

- 전투 코드에서 `_DataSetService`를 직접 호출하지 않는다.
- 각 Dataset은 담당 Repository를 가진다.
- Repository는 외부에 원본 Row를 그대로 반환하지 않는다.
- Repository 반환 table은 필드명과 기본값이 안정된 Runtime 계약이다.
- Dataset 누락이나 잘못된 참조는 Spawn이나 전투 시작 전에 검증한다.

### 9.2 스키마 버전

신규 Definition Dataset은 `SchemaVersion` 열을 가진다. 초기값은 `1`이다.

스키마 변경은 다음 순서를 따른다.

1. 가능한 경우 새 선택 필드를 추가한다.
2. Repository에서 누락 필드 기본값을 제공한다.
3. 기존 필드는 최소 한 버전 동안 읽을 수 있게 유지한다.
4. 소비 코드는 새 필드가 아니라 Repository 계약만 본다.
5. 필드 제거 시 변경 기록과 데이터 마이그레이션 절차를 문서화한다.

---

## 10. Stage 콘텐츠 규격

### 10.1 StageDefinitions — 실제 Dataset 전환 완료

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `SchemaVersion` | integer | O | 초기값 `1` |
| `StageId` | string | O | 고유 ID |
| `DisplayName` | string | O | 표시 이름 |
| `CellCount` | integer | O | 보드 Cell 수 |
| `CellStartX` | number | O | Cell 0의 X |
| `CellSpacing` | number | O | Cell 중심 간격 |
| `UnitY` | number | O | 유닛 배치 Y |
| `PlayerStartCell` | integer | O | Player 시작 Cell |
| `QueueCapacity` | integer | O | 기본 타일 큐 용량 |
| `WaveTableId` | string | O | Wave 묶음 ID |
| `StageRuleId` | string |  | 특수 규칙 Handler ID |

Map Entity에는 가능하면 `StageId`만 설정하고 세부 값은 Repository에서 읽는다.

`StageDefinitionRepositoryLogic`과 `ContentValidatorLogic`이 구현되어
`BattleSessionComponent` 진입 전에 Definition과 Wave 참조를 검증한다. `stage01`은
실제 `StageDefinitions` Dataset 1행으로 이관됐으며 compatibility fallback은 비활성이다.
중복 `StageId`는 `DATA_DUPLICATE_STAGE_ID`로 차단한다. 제작 절차는
[`Stage-Authoring-Guide.md`](./Stage-Authoring-Guide.md)를 따른다.

### 10.2 기존 Stage Dataset — 구현됨

- `StageEnemyWaves`: Wave 수, Spawn Trigger, Pool, SpawnCount, 제한 설정
- `EnemySpawnPools`: Pool별 Enemy Definition과 Model, Weight, 적용 Wave
- `EnemyDefinitions`: HP, 공격력, Pattern, 이동 정책

기존 열은 v0.1 마이그레이션 동안 유지한다. `StageDefinitions` 도입 후 중복 기본값은
Repository가 우선순위를 정한다.

### 10.3 Stage 개발자 절차

1. 고유 `StageId`를 만든다.
2. `StageDefinitions` 행을 추가한다.
3. `StageEnemyWaves`에 Wave 행을 추가한다.
4. 기존 Pool을 재사용하거나 `EnemySpawnPools`에 새 Pool을 추가한다.
5. 필요한 Enemy가 없을 때만 `EnemyDefinitions`를 추가한다.
6. Map Root에 공용 Battle 컴포넌트와 `StageId`를 설정한다.
7. Content Validation을 통과한다.
8. Maker에서 시작, Wave 전환, Victory, Reset을 검증한다.

일반 Stage 추가를 위해 `BattleSessionComponent`를 수정하지 않는다.

---

## 11. Skill과 Effect 규격

### 11.1 설계 원칙

스킬 하나는 실행 클래스 하나가 아니라 Definition과 Effect Step의 조합이다.

```text
SkillDefinition
→ Target 검증
→ Cooldown 사용 가능 검증
→ Modifier 적용
→ Cooldown 기록
→ SkillEffectStep 1 실행
→ SkillEffectStep 2 실행
→ ...
```

### 11.2 SkillDefinitions — 실제 Dataset 전환 완료

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `SchemaVersion` | integer | O | 초기값 `1` |
| `SkillId` | string | O | 고유 ID |
| `DisplayName` | string | O | 표시 이름 |
| `SkillTags` | string |  | `|` 구분 태그 |
| `TargetingType` | string | O | 대상 선택 규칙 |
| `Range` | integer | O | Cell 기준 사거리 |
| `TargetOffsets` | string |  | `RANGE_OFFSETS`의 Facing 기준 Cell 목록 (`1|2`) |
| `CooldownTurns` | integer | O | 0 이상 |
| `CostType` | string |  | 비용이 없으면 빈 문자열 |
| `CostValue` | number | O | 비용이 없으면 0 |
| `MotionProfileId` | string |  | 표현 설정 ID |
| `EffectSetId` | string | O | Effect Step 묶음 |
| `RequiredJobTag` | string |  | 제한이 없으면 빈 문자열 |
| `ActionDuration` | number | O | 큐의 다음 행동까지 기다리는 시간 |
| `FreePlay` | boolean | O | 등록 시 Turn 소비 여부 |

현재 `FRONT_CELL`, `FIRST_ENEMY_FORWARD`, `RANGE_OFFSETS`를 지원한다.
`SkillTargetResolverLogic`이 실제 타격 시점에 대상 Snapshot을 한 번 만들고, 모든 Effect
Executor와 UI DTO는 이 결과를 공유한다. Session이나 UI에서 별도로 사거리 판정을 복제하지 않는다.

위 필드 스키마는 **같은 열 구성을 가진 7개 Dataset**(`SkillDefinitions`, `{Warrior,Mage,
Archer,Thief,Pirate}SkillDefinitions`, `EnemySkillDefinitions`)에 공통으로 적용된다 — 스킬은
직업별 테이블로 분리돼 있고 공용 `SkillDefinitions`는 현재 헤더만 있는 빈 테이블이다. 어느
테이블에 있는지는 호출부가 알 필요 없이 `SkillDefinitionRepositoryLogic`이 전체를 순회해서
찾는다. 정확한 테이블 목록·조회 경로·플레이어 지급 가능 스킬 구분은
[`MapleTactics-M1-Data-Dictionary.md` §4.1](../MapleTactics-M1-Data-Dictionary.md)을 단일
기준으로 한다.

### 11.3 SkillEffectSteps — 실제 Dataset 전환 완료

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `SchemaVersion` | integer | O | 초기값 `1` |
| `EffectSetId` | string | O | Effect 묶음 |
| `StepIndex` | integer | O | 1부터 시작 |
| `EffectType` | string | O | Executor 선택 ID |
| `TargetSelector` | string | O | Effect 대상 |
| `Value` | number | O | 기본 수치 |
| `ParameterA` | string |  | Effect별 추가 값 |
| `ParameterB` | string |  | Effect별 추가 값 |
| `ConditionId` | string |  | 조건이 없으면 빈 문자열 |

같은 `EffectSetId` 안에서는 `StepIndex` 오름차순으로 실행한다. 중복 StepIndex는
Validation 실패다.

`SkillDefinitionRepositoryLogic`과 `ContentValidatorLogic`이 Definition과 Effect Step을
조회·변환·검증한다. 기본 스킬 5개, TargetType 검증용 2개, CSV 제작 예제 2개와 Effect Step 9개가
실제 Dataset으로 이관됐고 fallback은 비활성이다. 중복 SkillId와
누락·중복 StepIndex를 차단하며 복수 Effect Step은 `StepIndex` 순서로 실행한다. Cooldown은 유닛의
`SkillRuntimeStateComponent`가 기록하고 Turn 경계에서 감소시킨다.
세부 제작 절차는 [`Skill-Authoring-Guide.md`](./Skill-Authoring-Guide.md)를 따른다.

### 11.4 EffectType

| EffectType | 상태 | 의미 |
|---|---|---|
| `DAMAGE` | 구현됨 | HP 감소 |
| `PUSH` | 구현됨 | 대상 Cell 이동 |
| `HEAL` | 계획됨 | HP 회복 |
| `MOVE_SELF` | 계획됨 | 시전자 이동 |
| `APPLY_STATUS` | 계획됨 | 상태이상 부여 |
| `SPAWN_OBJECT` | 계획됨 | 전투 오브젝트 생성 |

새 EffectType을 추가할 때는 기존 스킬 클래스를 상속하지 않는다. 공통 Executor 계약을
따르는 Handler를 하나 추가하고 Router에 등록한다.

### 11.5 Effect 실행 Context — 구현됨

Executor는 다음 의미를 가진 Context를 받는다.

```lua
{
    BattleSession = session,
    SourceUnitId = "player_01",
    PrimaryTargetUnitId = "enemy_w1_left",
    SkillId = "basic_slash",
    CurrentTurn = 1,
    RunSeed = 1000
}
```

Context는 요청 동안만 사용하는 값이다. Executor가 Context를 전역 상태로 보관하지 않는다.
실제 Executor 계약과 확장 절차는
[`Effect-Executor-Guide.md`](./Effect-Executor-Guide.md)를 따른다.

### 11.6 상속과 조합

- 스킬, 직업, 아이템마다 별도 상속 클래스를 만들지 않는다.
- 공통 계약을 강제할 필요가 있는 Executor 계열에만 얕은 상속을 허용한다.
- 상속 깊이는 기본 Executor 포함 2단계를 권장 상한으로 한다.
- 여러 효과는 다중 상속이 아니라 `SkillEffectSteps` 조합으로 표현한다.
- 기존 Effect 조합으로 만들 수 없는 규칙일 때만 새 Executor를 추가한다.

### 11.7 스킬 개발자 절차

1. 기존 EffectType으로 표현 가능한지 확인한다.
2. `SkillDefinitions` 행을 추가한다.
3. `SkillEffectSteps`에 순서대로 Effect를 추가한다.
4. 필요한 Motion Profile과 UI 표현을 연결한다.
5. Cooldown, Target, Effect 순서를 Maker에서 검증한다.
6. 기존 Effect로 불가능할 때만 Executor와 Router 등록을 추가한다.

---

## 12. 직업, 아이템, 증강 규격

이 영역은 직업 정의와 시작 스킬 로더/검증기, 런 직업 스냅샷, 첫 실제
`FORWARD_PUSH` JobMechanic, 런 스킬 소유권과 큐 허용 검사까지 구현되었다. 또한
`JobPassiveSetId → AugmentId` 참조, 플레이어별 증강 상태, 최소 Trigger→Condition→Effect
파이프라인까지 구현되었다. 증강 후보 풀·충돌/다중 스택 정책과 실제 상점 구매 어댑터는 후속 단계다.

직업의 고정 선택값은 `PlayerRunStateComponent`, 런 중 추가될 수 있는 스킬 수량은
`PlayerRunInventoryComponent`가 소유한다. BattleSession과 외부 노드는 두 Component를
직접 조합하지 않고 `RunManagerLogic`의 `CanUseRunSkill`, `GrantRunSkill`,
`GetRunSkillSnapshot`, `GrantRunAugment`, `GetRunAugmentSnapshot` 경계를 사용한다.

### 12.1 JobDefinitions

| 필드 | 설명 |
|---|---|
| `JobId` | 직업 ID |
| `DisplayName` | 표시 이름 |
| `JobTags` | 사용 가능한 스킬·장비 태그 |
| `BaseMaxHp` | 기본 최대 HP |
| `BaseQueueCapacity` | 기본 큐 크기 |
| `StartingSkillSetId` | JobStartingSkillEntries 참조 |
| `JobMechanicId` | 큐 외부에서 동작하는 직업 고유 규칙 |
| `JobPassiveSetId` | 시작 패시브/증강 세트 |

직업별 Skill 클래스를 만들지 않는다. 시작 공격은 기존 `SkillDefinitions` 조합이며,
고유 이동·교환·밀치기·관통 규칙만 `JobMechanicRouterLogic` 계약을 사용한다.

### 12.1.1 JobMechanic 계약

모든 직업 메커니즘은 `CanActivate`, `Execute`, `GetPreview`, `GetUiState`에 대응하는
정규화 결과를 제공한다. mLua에서 임의의 깊은 상속 트리를 만들지 않고 Router가 독립
Handler로 위임한다. 데이터는 Mechanic ID와 수치를 보관하고 알고리즘은 Handler가 소유한다.

`JobMechanic`은 `SkillDefinitions`가 아니므로 스킬 큐·스킬 쿨타임·EffectSet을 자동 적용하지
않는다. 턴 소비 여부는 실행 결과의 `ConsumedTurn`, UI 표시는 `GetUiState`로 명시한다.

### 12.2 ItemDefinitions — 계획됨(미구현), 실제로는 ConsumableDefinitions로 대체됨

아래 표는 v0.1 초안 당시의 장비·소비 통합 계획이며 `ItemDefinitions` Dataset은 실제로 만들어진
적이 없다. 실제 소비 아이템 파이프라인은 `ConsumableDefinitions`(사용 시점·턴 소비·효과 DTO)
+ `ConsumableEffectRouterLogic`(원시 EffectType Router) + `ConsumableHealEffectLogic` 등
독립 Handler로 §6.11에 이미 **구현됨** 상태로 존재한다. 장비(EquipSlot 개념)는 아직 어떤
형태로도 구현되지 않았다.

| 필드 | 설명 |
|---|---|
| `ItemId` | 아이템 ID |
| `ItemType` | 장비, 소비, 전투 아이템 등 |
| `EquipSlot` | 장착 위치 |
| `ItemTags` | 분류 태그 |
| `StatModifierSetId` | 능력치 Modifier |
| `GrantedSkillId` | 부여 스킬 |
| `PassiveEffectSetId` | 패시브 효과 |
| `RequiredJobTag` | 직업 제한 |

### 12.3 AugmentDefinitions

| 필드 | 설명 |
|---|---|
| `AugmentId` | 증강 ID |
| `DisplayName` | 표시 이름 |
| `TriggerType` | 적용 시점 |
| `FilterTags` | 적용 대상 Skill/Effect 태그 |
| `ModifierType` | ADD, MULTIPLY, APPEND_EFFECT 등 |
| `TargetField` | 변경 대상 필드 |
| `Value` | 변경 값 |
| `Priority` | 적용 순서 |

### 12.4 Modifier 적용 순서

```text
원본 SkillDefinition
→ 직업 Modifier
→ 아이템 Modifier
→ 증강 Modifier
→ 최종 실행 Definition
```

- 원본 Dataset Row를 직접 수정하지 않는다.
- 실행마다 복사된 Runtime Definition에 Modifier를 적용한다.
- 동일 Priority는 안정된 Modifier ID 순서로 처리한다.
- Modifier 적용 결과는 재현 가능해야 한다.
- Run Seed가 필요한 확률 효과는 공용 결정 규칙을 사용한다.

---

## 13. Enemy Pattern 규격

### 13.1 EnemyPatternSteps — 구현됨

| 필드 | 설명 |
|---|---|
| `PatternId` | 패턴 ID |
| `StepIndex` | 실행 순서 |
| `ConditionType` | `ALWAYS`, `DISTANCE_EQ`, `HP_RATIO_LE`, `CELL_FREE` |
| `ActionType` | `WAIT`, `TURN_TO_PLAYER`, `MOVE_TOWARD`, `MOVE_AWAY`, `MOVE_FIXED_FACING`, `TELEGRAPH_TILE`, `CAST_INTERRUPTIBLE`, `EXECUTE_TILE`, `BOSS_JUMP_TELEGRAPH`, `BOSS_LAND_OPPOSITE` |
| `TileId` | 예고·실행할 스킬 타일 ID |
| `TelegraphTurns` | `TELEGRAPH_TILE` 예고 턴 수, 1 이상 |
| `ParamA/B/C` | 조건·행동별 인자 |
| `NextStepOnSuccess` | 성공 시 다음 Step |
| `NextStepOnFailure` | 실패 시 다음 Step |

`EnemyPatternStepRepositoryLogic`과 전용 Validator가 행을 로드·검증하고,
`EnemyIntentResolverLogic`이 Pattern Definition을 읽어 Prepared Intent Snapshot을 만든다.
각 적의 `EnemyPatternRunnerComponent`가 Step과 Telegraph 카운트다운을 독립 소유하며,
`BattleSessionComponent`는 준비·실행·완료 순서와 실제 보드 명령만 조정한다.

UI는 Pattern 조건을 다시 계산하지 않고 Prepared Intent Snapshot만 표시한다.
보스 점프의 공중 여부와 고정 착지 칸은 보스의 `BattleUnitComponent`가 소유하며,
`BoardStateComponent`는 공중 보스를 Cell 점유·공격 대상으로 노출하지 않는다.

---

## 14. UI와 Presentation 규격

- `.ui`는 UI Builder를 통해 수정한다.
- UI Controller는 동기화된 Runtime 상태만 읽는다.
- 버튼은 `Request...` 진입점만 호출한다.
- UI 노드 UUID는 UI Controller의 Component property로 연결한다.
- 표시 이름과 설명은 전투 ID와 분리한다.
- SpriteRUID, 모션, 색상, 지속시간은 Presentation 또는 Motion Profile이 소유한다.
- 피해·사거리·쿨타임 판정에 화면 Transform이나 Sprite 크기를 사용하지 않는다.
- 월드 좌표는 MSW world unit을 사용한다. `1 unit = 100 px` 기준을 따른다.

---

## 15. Event 규격

상태 변경이 완료된 뒤 Event를 발행한다.

권장 이름:

```text
UnitMovedEvent
UnitTurnedEvent
SkillResolvedEvent
EffectAppliedEvent
UnitDiedEvent
TurnChangedEvent
WaveChangedEvent
BattleResultEvent
```

Event는 이미 완료된 사실을 전달한다. Event 수신자가 같은 상태를 다시 변경하지 않는다.
핵심 판정은 Event 수신 순서에 의존하지 않는다.

---

## 16. 로그 규격

핵심 흐름에는 다음 Tag를 사용한다.

```text
[BattleSession]
[BattleTurn]
[BattleWave]
[BoardState]
[SkillExecution]
[BattleEffect]
[EnemyIntent]
[PlayerRunState]
[RunManager]
[ContentValidation]
```

개발·검증 중 사용하는 Positive log에는 최소한 ID와 결과를 포함한다. 확인 결과를 작업
기록에 남기고, 기능 완료 전에 반복 성공 로그를 제거한다. 운영에 필요한 드문 주요 사건만
유지한다. 세부 기준은 [`Runtime-Logging-Guide.md`](./Runtime-Logging-Guide.md)를 따른다.

```text
[SkillExecution] resolved skill=basic_slash source=player_01 success=true reason=OK
```

거절은 정상 흐름과 오류를 구분한다.

```text
[SkillExecution] rejected skill=heavy_slash reason=COOLDOWN_ACTIVE remaining=2
```

---

## 17. 금지 규칙

- UI에서 `CurrentHp`, `CellIndex`, `BattlePhase` 직접 변경
- Battle 코드에서 Dataset Row 직접 조회
- 스킬 ID별 `if/elseif`를 여러 파일에 반복
- 새 Stage를 위해 공용 Session에 Stage 전용 분기 추가
- 한 `@Logic`에 모든 플레이어의 Run 상태 저장
- `SpawnByModelId(..., parent=nil)` 호출
- 이전 맵의 `BattleSessionComponent` 참조 유지
- 화면 Transform을 읽어 논리 Cell 판정
- `.ui`, `.map`, `.model` Raw JSON 직접 수정
- `.codeblock`, `Global/`, `Environment/` 수정
- Definition ID를 DisplayName이나 UI 문구로 사용
- 검증 없이 Dataset 필드 삭제 또는 이름 변경

---

## 18. Definition of Done

### 18.1 새 Stage

- StageId와 모든 참조 ID가 유효하다.
- Cell과 시작 위치가 범위 안이다.
- 모든 Wave가 Pool을 찾을 수 있다.
- SpawnCount와 MaxConcurrent가 유효하다.
- 시작, 강제 증원, 전멸 전환, 마지막 Victory가 동작한다.
- Reset 후 동일한 초기 상태로 돌아온다.
- Build와 Runtime에 Error/Warning이 없다.

### 18.2 새 Skill

- SkillId가 고유하다.
- 모든 Effect Step이 연속적인 순서를 가진다.
- EffectType과 TargetSelector가 등록되어 있다.
- Cooldown과 비용이 서버에서 검증된다.
- Miss와 실패 Reason이 정의되어 있다.
- 같은 Seed와 상태에서 결과가 재현된다.
- UI는 실행 가능 상태를 표시할 뿐 판정을 복제하지 않는다.

### 18.3 새 EffectType

- 공통 Executor 계약을 따른다.
- Router 등록 위치가 한 곳이다.
- 상태 소유자의 Apply API를 사용한다.
- 성공, 정상 실패, 경계 조건을 검증한다.
- Effect 실행 로그가 있다.
- 기존 DAMAGE와 PUSH 회귀 검증을 통과한다.

---

## 19. 마이그레이션 순서

현재 Stage 1을 유지하면서 다음 순서로 진행한다.

1. 이 규격을 공동 기준으로 승인
2. `StageDefinitions` Repository와 Content Validator 추가 — 실제 Dataset 전환 및 fallback 비활성 완료
3. `SkillDefinitions`, `SkillEffectSteps`와 Repository 추가 — 실제 Dataset 전환 및 fallback 비활성 완료
4. 기본 베기·강한 베기·밀치기를 데이터 기반 Skill 실행으로 이전 — 단일 Effect 경로 구현
5. Effect Context와 Executor 계약 정리 — DAMAGE/PUSH 및 다중 Step 실행 구현
6. `SkillRuntimeStateComponent`와 Cooldown 골격 추가 — 구현됨
7. Turn·큐 책임을 `BattleTurnComponent`로 이동 — 구현됨
8. Wave·Spawn Timer 책임을 `BattleWaveComponent`로 이동 — 구현됨
9. `EnemyPatternSteps`와 Intent Resolver 연결
10. 직업·아이템·증강 Modifier 스키마와 빈 파이프라인 추가
11. Stage 1 전체 회귀 검증
12. Stage 2를 공용 코드 수정 없이 제작해 규격 검증
13. 발견된 부족한 필드를 호환 방식으로 v0.2에 반영
14. 대표 콘텐츠 검증 후 규격 v1.0 확정

각 단계는 기존 메서드가 새 모듈에 위임하도록 먼저 변경한다. Maker 검증이 끝난 뒤에만
이전 구현을 제거한다.

---

## 20. 현재 구현 대응표

| 현재 구현 | 규격상 위치 | 처리 |
|---|---|---|
| `BattleSessionComponent` | 전투 흐름 조정 + Turn/Wave 호환 Snapshot | Turn·Wave·SkillRuntime 상태를 전용 컴포넌트에 위임하고 호환 API만 유지 |
| `BattleGatewayLogic` | 외부 시스템 전투 진입 Facade | 유지 |
| `BattleEntryStateComponent` | 플레이어별 Pending 전투 입장 | 유지 |
| `BattleUnitComponent` | Unit Runtime State | 유지 |
| `BoardStateComponent` | Board Registry | 유지 |
| `BattleUnitPresentationComponent` | Presentation | 유지 |
| `SkillRuntimeStateComponent` | 유닛별 Cooldown Runtime State | 구현됨 |
| `EffectRouterLogic` | Effect Router | DAMAGE/PUSH Executor 연결 구현 |
| `SkillExecutionLogic` | Effect Context 생성·Step 순차 실행 | 구현됨 |
| `DamageEffectExecutorLogic` | DAMAGE 원자 효과 | 구현됨 |
| `PushEffectExecutorLogic` | PUSH 원자 효과 | 구현됨 |
| `StageWaveRepositoryLogic` | Stage/Enemy Repository | 책임별 Repository로 확장 |
| `StageDefinitionRepositoryLogic` | Stage Definition Repository | 구현됨, Stage 1 Dataset 전환 후 호환값 제거 |
| `ContentValidatorLogic` | 전투 시작 전 콘텐츠 참조 검증 | 구현됨 |
| `ContentReferenceResolverLogic` | Definition 참조 Registry/Resolver | ENEMY_DEFINITION·RUN_CURRENCY·CONSUMABLE 구현됨 |
| `EnemyDropContentValidatorLogic` | Drop ID 중복·Enemy/Reward 교차 참조 검증 | 구현됨, 결과 Cache 사용 |
| `SkillDefinitionRepositoryLogic` | Skill·Effect Step Repository | 구현됨, Dataset 전환 후 호환값 제거 |
| `StageEnemyWaves` | Stage Wave Definition | 유지 |
| `EnemySpawnPools` | Spawn Pool Definition | 유지 |
| `EnemyDefinitions` | Enemy Definition | 유지 |
| `PlayerRunStateComponent` | Player Run State | 유지 |
| `PlayerRunInventoryComponent` | Run Reward/Consumable State | 진행 상태와 분리 완료 |
| `ConsumableDefinitionRepositoryLogic` | Consumable Definition Repository | 구현됨 |
| `ConsumableEffectRouterLogic` | Consumable primitive effect Router | HEAL Handler 구현됨 |
| `RunManagerLogic` | Run Coordinator | 유지 |
| `BattleQueueHudComponent` | (구) HUD Request/Presentation | **대체됨** — 아래 `BattleHudPresenterLogic`으로 교체된 뒤 `AddComponent`/`.map` 어디에도 붙지 않는 죽은 코드로 남음. 삭제 대상 |
| `BattleHudPresenterLogic` | 전투 HUD 상태를 Event(`BattleHudStateChangedEvent`/`BattleHudCommandResultEvent`)로 발행하는 Client 전용 Presenter | 구현됨 |
| `RegionDefinitionRepositoryLogic` | Region Definition Repository | 구현됨 |
| `BossPhaseDefinitionRepositoryLogic` | 보스 Phase 임계치·Pattern 교체 Repository | 구현됨 |
| `LobbyCharacterSelectionLogic` / `LobbyJobSelectionProvider` / `LobbyCodexLogic` | 로비 캐릭터·직업 선택, 도감(Codex) | 구현됨, 규격 문서화는 미완 |
| `LobbyGridMovementComponent` | 로비 좌우 이동(전투 Board 점유 판정 없음, 이동 연출은 `PlayerGridMovementLogic` 공유) | 구현됨 |

---

## 21. 규격 변경 절차

### 유물 특수능력 확장 (2026-09-24)

- `RelicDefinitions`는 기존 능력치 열을 유지하고 선택 열 `SpecialEffectType`, `SpecialEffectValue`를 추가한다. 빈 효과는 기존 능력치 유물로 읽는다.
- `PlayerRunRelicEffectComponent`가 런에 고정된 정의·합산 효과와 전투별 발동 횟수를 소유한다. HP·Cooldown·재화 원본은 기존 소유자에 남는다.
- Session의 전투 시작·처치 확정 → 유물 API → Unit/SkillRuntime 공개 API, RunManager의 승리 처리 → 유물 API → 보상 Facade 순서로 호출한다.
- 특정 RelicId 분기는 전투 코어에 추가하지 않는다. 상점·HUD는 Repository가 생성한 동일한 설명을 사용한다.
- 구현 및 검증 범위와 초기 수치는 `Run-Shop-Authoring-Guide.md`의 유물 특수능력 규격을 따른다. Maker 미검증 상태는 구현 완료와 구별한다.

1. 변경 이유와 영향을 받는 Definition/Component를 기록한다.
2. 기존 Stage 1 데이터가 새 Repository에서 계속 읽히는지 확인한다.
3. 가능하면 필드 추가 방식으로 변경한다.
4. 호환이 불가능하면 SchemaVersion을 올린다.
5. Repository에 구버전 변환 경로를 추가한다.
6. Stage, Skill, UI 개발 가이드를 함께 갱신한다.
7. Stage 1과 대표 신규 사례를 Maker에서 재검증한다.

규격 문서와 코드가 다르면 코드를 임의로 따라가지 않는다. 구현 오류인지 규격 변경인지
먼저 결정하고, 승인된 규격 변경만 문서 버전을 올려 반영한다.
