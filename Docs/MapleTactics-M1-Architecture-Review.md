# MapleTactics M1 아키텍처 구현 가능성 검토

문서 상태: 검토 완료  
검토 기준: MSW CoreVersion `26.5.0.0`, 현재 저장소, mLua 실행 공간, UserDataSet, UI/Model/Map Builder 규칙  
대상 맵: `map/map01.map`

## 1. 최종 판정

기획의 핵심인 **1차원 논리 보드, 이동/회전/큐 등록의 턴 소비, 공격 큐의 순차 실행, 스테이지별 적 패턴, 직업 4종, 스테이지 증강 선택**은 MSW에서 구현 가능하다.

다만 기존 설계 문서의 일반 Lua 예시를 그대로 코드로 옮기면 안 된다. 다음 네 가지 교정이 선행되어야 한다.

1. `require`와 메타테이블 기반 클래스/인터페이스 대신 MSW의 `@Logic`, `@Component`, `@Event`, `@Struct`를 사용한다.
2. 사용자 스크립트가 `Service`를 확장한다고 가정하지 않는다. 전역 무상태 기능은 `@Logic`, 맵 수명 전투 상태는 맵 엔티티의 `@Component`, 유닛 상태는 유닛 엔티티의 `@Component`가 소유한다.
3. 모든 적에게 BT, FSM, Pattern을 동시에 적용하지 않는다. 일반 적은 데이터 기반 Pattern Runner 하나를 사용하고, 복잡한 보스만 선택적으로 BT를 사용한다.
4. 콘텐츠 제작자가 값만으로 만들 수 있는 범위는 이미 구현된 `ActionType`, `EffectType`, `ConditionType`, `TargetType`의 조합으로 제한한다. 새로운 원시 동작은 프로그래머 작업이다.

이 교정을 적용한 구조는 구현 가능성이 높다. 전체 개발 전에 Phase 0 기술 검증 4개를 통과해야 “확정 구조”로 간주한다.

## 2. 저장소에서 확인한 사실

- 현재 `RootDesk/MyDesk` 아래에는 폴더 메타데이터만 있고 실제 `.mlua` 구현은 없다.
- `map/map01.map`은 `TileMapMode = 0`, 즉 MapleTile이다.
- `map01`은 `InstanceMap = false`인 Static Map이다.
- 현재 맵은 5개 엔티티, 629개 타일, 34개 foothold를 가진 기본 맵에 가깝다.
- 프로젝트 CoreVersion은 `26.5.0.0`으로 저장소 규칙과 일치한다.
- UI에는 `DefaultGroup.ui`, `PopupGroup.ui`, `ToastGroup.ui`가 있다.

따라서 지금은 기존 코드와 충돌을 걱정하기보다, 맵 타입과 전투 수명 경계를 먼저 고정하기 좋은 시점이다.

Static Map의 맵 루트에 `BattleSessionComponent` 하나를 두면 같은 World Instance의 여러 사용자가 상태를 공유할 수 있다. M1 싱글 플레이 전투는 **플레이어당 하나의 Instance Room/Instance Map**을 기본 전제로 한다. `map01`을 개발용으로만 유지하거나, 별도의 전투 Instance Map을 만들어야 한다. 세계 최대 인원을 1명으로 고정하는 대안도 있지만 이후 확장성이 낮다.

## 3. 1차 검토 — MSW 언어와 실행 모델

### 통과한 부분

- 서버 권위 턴제 전투는 `@ExecSpace("Server")` 요청과 `ServerOnly` 해석으로 구현할 수 있다.
- UI는 ClientOnly, 전투 판정은 ServerOnly로 분리할 수 있다.
- 커스텀 이벤트는 `@Event script XxxEvent extends EventType`으로 명시할 수 있다.
- 정적 밸런스 데이터는 UserDataSet과 CSV로 관리할 수 있다.
- `.model`에 공통 컴포넌트를 조립하고 런타임에 `SpawnByModelId`로 생성할 수 있다.

### 수정이 필요한 부분

| 기존 가정 | 문제 | 교정 |
|---|---|---|
| `Class.create`, `setmetatable`, `require` 기반 도메인 객체 | 일반 Lua 모듈 패턴이며 mLua 등록·컴포넌트 수명·코드블록 흐름과 맞지 않음 | MSW 스크립트 타입과 명시적 협력 객체 사용 |
| `TurnManager extends Service` | 사용자 게임 시스템이 엔진 Service처럼 동작한다고 가정 | `BattleSessionComponent` 또는 무상태 `@Logic` |
| `BaseUnit -> PlayerUnit/EnemyUnit` 상속 | mLua 사용자 컴포넌트 상속 계층에 의존하고 조립성이 낮음 | `UnitRuntimeComponent` 공통 컴포넌트 + 역할별 컴포넌트 조합 |
| 문자열 이벤트 테이블 | 실행 공간과 payload 타입을 보장하지 못함 | 타입이 있는 `@Event`와 RPC 경계 분리 |
| UI가 전투 객체를 직접 수정 | UI는 ClientOnly이고 서버 권위와 충돌 | UI는 Command DTO만 서버에 요청 |

## 4. 2차 검토 — 전투 상태와 의존성

### 단일 상태 권한

전투의 유일한 상태 권한은 맵 엔티티에 붙은 `BattleSessionComponent`로 둔다.

이 문장의 전제는 해당 전투 맵이 한 플레이어만 포함하는 Instance Map이라는 것이다. Static Map을 사용한다면 `BattleSessionComponent` 하나로는 부족하며 UserId별 세션 분리가 추가로 필요하다.

```text
BattleSessionComponent (ServerOnly, map-scoped)
├─ Phase / Turn / IsResolving / CommandSequence
├─ BoardState
├─ UnitRuntime 조회
├─ Player Command 검증과 적용
├─ Enemy Pattern 실행
└─ 승패/정리
```

`TurnManager`, `CombatManager`, `RegenManager`가 각각 턴이나 유닛을 수정하면 순서와 상태 권한이 분산된다. 이름은 유지할 수 있어도 다음처럼 역할을 바꾼다.

| 이름 | 권장 형태 | 상태 소유 여부 |
|---|---|---|
| BattleSessionComponent | 맵 엔티티 `@Component` | 전투 상태의 유일한 소유자 |
| TargetResolverLogic | 무상태 `@Logic` | 없음 |
| EffectRouterLogic | 무상태 `@Logic` | 없음 |
| ContentCatalogLogic | 읽기 전용 캐시 `@Logic` | 정적 데이터 캐시만 |
| ReinforcementSchedulerComponent | BattleSession의 하위 협력 컴포넌트 | 독립 상태 수정 금지 |
| PlayerRunStateComponent | 플레이어 엔티티 `@Component` | 플레이어별 런 상태 |

### 커맨드 처리 순서

```text
Client UI/Input
  -> RequestCommand(commandType, arg1, arg2, clientSequence)
  -> Server: 플레이어/페이즈/중복/범위/쿨다운 검증
  -> IsResolving 잠금
  -> Command 적용
  -> 즉시 이벤트 전부 해결
  -> 사망/승패 검사
  -> consumesTurn=true 이면 적 단계와 Cleanup
  -> 다음 플레이어 입력 단계
  -> Client 표현 갱신
  -> 잠금 해제
```

필수 방어 규칙:

- 같은 `clientSequence`의 재전송을 한 번만 처리한다.
- `IsResolving = true`인 동안 새 요청을 거절한다.
- 클라이언트가 보낸 피해량, 턴 소비 여부, 타깃 결과를 신뢰하지 않는다.
- 서버가 `TileId`, 현재 쿨다운, 큐 크기, FreePlay 속성을 다시 조회한다.
- 한 커맨드의 모든 즉시 이벤트 처리가 끝나기 전 다음 커맨드를 받지 않는다.

## 5. 3차 검토 — 이동과 공격 큐

### 논리 보드가 원본

`TransformComponent`나 실제 월드 X 좌표를 전투 상태의 원본으로 사용하지 않는다.

```text
원본: UnitRuntime.CellIndex = 3
파생: BoardWorldAdapter.CellToWorld(3)
표현: Body.SetWorldPosition(worldPosition)
```

Body가 있는 엔티티는 `TransformComponent.Position`을 직접 바꾸면 물리가 다음 프레임에 덮어쓸 수 있다. 스냅 이동은 `MovementComponent:SetWorldPosition` 또는 맵 타입에 맞는 Body의 `SetWorldPosition`을 사용한다.

### 이동 커맨드

1. 현재 Phase가 PlayerInput인지 확인한다.
2. 방향이 `-1` 또는 `1`인지 확인한다.
3. 목적 셀이 보드 안인지 확인한다.
4. 점유·이동 금지·상태 이상 규칙을 검사한다.
5. 논리 `CellIndex`를 갱신한다.
6. `UnitMovedEvent`를 발생시킨다.
7. 이동은 기본적으로 턴을 소비한다.

### 큐 등록 커맨드

1. Tile Runtime Instance의 소유자를 검증한다.
2. 쿨다운이 0인지 검증한다.
3. 큐 최대 크기를 검증한다.
4. 중복 허용 규칙을 검증한다.
5. 큐 끝에 Runtime Instance Id를 추가한다.
6. `FreePlay = true`면 턴을 소비하지 않고 입력 단계로 돌아간다.
7. 일반 타일이면 적 단계까지 진행한다.

### 큐 실행 커맨드

큐 시작 시 전체 타깃을 미리 고정하지 않는다.

```text
for queueIndex = 1..N
  현재 보드에서 타깃 재계산
  Effect를 Seq 순서로 실행
  생성된 이벤트 전부 해결
  사망 제거와 승패 검사
  현재 타일 쿨다운 시작
end
큐 비우기
```

밀치기와 사망으로 다음 타일의 타깃이 달라지므로, 매 타일마다 현재 상태를 다시 읽어야 한다.

## 6. 4차 검토 — AI와 스테이지 조립성

### 일반 적

일반 적은 다음 두 데이터 테이블만으로 동작하게 한다.

- `EnemyDefinitions`: HP, ModelId, PatternId, 시작 방향, 태그
- `EnemyPatternSteps`: PatternId, StepIndex, ActionType, ParamA/B/C, TelegraphTurns, ConditionType

`EnemyPatternRunnerComponent`가 현재 StepIndex를 보유하고, `ActionType`을 `EnemyActionRouterLogic`에 위임한다.

### 보스

보스도 우선 PatternStep과 Phase 조건으로 만든다. 다음 조건에 해당할 때만 BT를 도입한다.

- 여러 목표 중 우선순위를 매 프레임 또는 매 턴 평가해야 한다.
- PatternStep만으로 표현하기 어려운 분기·재시도·병렬 행동이 있다.
- 같은 행동 노드를 여러 보스가 재사용한다.

MSW `.behaviourtree`는 codeblock UUID, Blackboard 타입 문자열, 노드 부모/자식 양방향 연결을 요구한다. 비개발자가 직접 JSON을 편집하는 방식은 조립형 제작에 적합하지 않다. BT를 사용한다면 반드시 생성 도구와 검증기를 함께 제공한다.

### 값만으로 가능한 범위

가능:

- 기존 적 모델과 스탯 조합
- 기존 ActionType으로 패턴 순서 작성
- 기존 타일 효과와 타깃 규칙 조합
- 기존 증강 Trigger/Condition/Effect 조합
- 스테이지별 적 배치, 보상 풀, 증강 풀 조정

코드가 필요한 경우:

- 새로운 ActionType
- 새로운 EffectType
- 새로운 TargetType
- 새로운 ConditionType
- 기존 이벤트 수명으로 표현할 수 없는 보스 기믹

이 경계를 콘텐츠 제작 가이드에 명시해야 “값만 넣으면 다 된다”는 잘못된 기대를 막을 수 있다.

## 7. 맵 타입 결정

현재 맵은 `MapleTile(0)`이지만, 이 게임은 자유 배치 foothold보다 **1차원 셀 기반의 측면 전술 퍼즐**에 가깝다.

M1 권장값은 `SideViewRectTile(2)`이다.

- 측면 시점을 유지한다.
- 사각 타일 기반 셀과 월드 좌표 대응이 단순하다.
- 적/플레이어 Body를 `SideviewbodyComponent`로 통일할 수 있다.
- 비개발자가 스테이지를 조립할 때 foothold 선분보다 셀 좌표가 다루기 쉽다.

맵 타입 전환은 AI가 `.map` 값을 직접 수정하지 않는다. Maker Hierarchy에서 사용자가 `map01`을 SideViewRectTile로 전환한 뒤, AI가 Refresh 후 `TileMapMode=2`를 다시 확인해야 한다.

MapleTile을 유지해야 한다면 구조 자체는 사용할 수 있지만 `BoardWorldAdapter`가 foothold 높이와 Cell X를 별도로 관리해야 하며, 모든 유닛 모델은 `RigidbodyComponent`를 사용해야 한다.

## 8. 정규화된 데이터 모델

UserDataSet은 모든 셀을 문자열로 제공한다. 중첩 JSON 한 셀에 의존하지 말고 관계형으로 나눈다.

```text
JobDefinitions
TileDefinitions
TileEffects
EnemyDefinitions
EnemyPatternSteps
StageDefinitions
StageEnemySpawns
AugmentDefinitions
AugmentEffects
StageAugmentPools
AugmentConflicts
```

공통 규칙:

- 모든 ID는 ASCII `snake_case` 또는 `lower.dot` 규칙으로 고정한다.
- 모든 숫자는 로드 시 `tonumber` 후 범위 검증한다.
- 빈 문자열과 nil을 모두 누락으로 처리한다.
- 순서가 필요한 행은 `Seq` 또는 `StepIndex`를 가진다.
- `pairs` 순회 순서를 게임 규칙에 사용하지 않는다.
- 효과 우선순위는 `Priority`, `Seq`, `Id` 순으로 안정 정렬한다.
- 참조 대상이 없는 ID는 전투 시작 전에 오류로 차단한다.

## 9. 증강 시스템 검토

증강은 다음 세 층으로 분리하면 구현 가능하다.

```text
AugmentDefinition  정적 설명/희귀도/중첩 정책
AugmentEffect      Trigger + Condition + Effect + Priority
AugmentInstance    플레이어가 실제 보유한 스택/획득 순서
```

서버 전투 이벤트 흐름:

```text
BattleEvent 발생
  -> 보유 AugmentInstance 조회
  -> Trigger가 맞는 AugmentEffect 필터
  -> Condition 평가
  -> Priority/획득순서/Effect Seq로 정렬
  -> 효과 실행
  -> 재귀 이벤트 깊이 제한 검사
```

필수 안전장치:

- 한 이벤트 체인의 최대 파생 깊이를 제한한다.
- 동일 Effect가 자신이 만든 동일 Event에 무한 반응하지 않도록 SourceTag를 둔다.
- `Unique`, `StackAdd`, `StackRefresh`, `ExclusiveGroup` 정책을 데이터로 명시한다.
- 증강 후보 생성은 런 Seed와 StageIndex에서 파생한 결정적 RNG를 사용한다.
- 선택 결과는 `PlayerRunStateComponent`가 소유한다.

## 10. 검토 후 확정 인터페이스

여기서 인터페이스는 언어 키워드가 아니라 **고정된 메서드 계약과 데이터 스키마**를 뜻한다.

| 계약 | 책임 | 구현 형태 |
|---|---|---|
| BattleCommand | 플레이어 요청 입력 | 문자열 CommandType + 제한된 인자 DTO |
| BattleEvent | 해석 결과 전달 | 타입이 있는 `@Event` |
| TargetRule | 현재 보드에서 대상 계산 | TargetResolverLogic 메서드 |
| EffectExecutor | 한 원시 효과 실행 | EffectRouterLogic의 등록된 EffectType |
| EnemyAction | 적의 한 원시 행동 실행 | EnemyActionRouterLogic의 등록된 ActionType |
| ContentDefinition | 정적 콘텐츠 값 | UserDataSet 행 |
| RuntimeInstance | 전투 중 변하는 값 | Component property/table |
| BattleViewSnapshot | 서버 결과의 클라이언트 표현 | Client RPC DTO 또는 제한된 Sync 속성 |

## 11. Phase 0에서 반드시 증명할 항목

아래 중 하나라도 실패하면 전체 구현 전에 구조를 수정한다.

1. `map01` 권장 맵 타입 확정 및 한 셀 스냅 이동 왕복.
2. 전투 맵의 InstanceMap 격리 또는 세계 최대 인원 1명 정책 확정.
3. UI 버튼 -> Server Command 검증 -> Client 결과 표시 왕복.
4. 두 타일 큐 실행 중 첫 타일 밀치기 후 두 번째 타일 타깃 재계산.
5. UserDataSet 네 개 행 로드, 숫자 변환, 잘못된 참조 ID 차단.

## 12. 결론

기획은 구현 가능하다. 그러나 확정판은 “일반 Lua 객체지향 프레임워크”가 아니라 다음 문장으로 정의해야 한다.

> 서버의 맵 범위 `BattleSessionComponent`가 전투 상태를 단독 소유하고, 데이터로 정의된 Command/Action/Effect를 무상태 Logic에 위임하며, MSW Entity/Component는 런타임 상태와 표현을 연결한다.

이 구조라면 네 직업과 스테이지별 적·증강을 값과 조립 중심으로 확장할 수 있고, 새 원시 기믹만 코드 작업으로 격리할 수 있다.
