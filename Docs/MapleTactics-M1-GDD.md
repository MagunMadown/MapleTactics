# MapleTactics M1 GDD

Stage: Phase 1 prototype in progress, bidirectional combat expansion planned

Milestone: M1 playable vertical slice

## 1. 게임 한 줄 설명

1차원 전장에서 이동과 방향 전환으로 적의 예고 행동을 피하고, 공격 타일을 큐에 조합해 순차 실행하는 턴제 전술 로그라이크.

## 2. M1 플레이 루프

```text
직업 선택
-> 월드맵에서 현재 마을 선택
-> 마을 스테이지 시작
-> 이동/회전/타일 큐 등록/큐 실행
-> 적 Intent 해결
-> 승리
-> 증강 3택
-> 마을 클리어
-> 다음 마을로 가는 경로 상점 방문
-> 다음 마을 해금
```

M1 수직 슬라이스는 헤네시스와 첫 분기만 검증한다. 이후 콘텐츠 확장에서도
`마을 전투 → 경로 상점 → 다음 마을` 순서는 동일하게 재사용한다.

## 3. 핵심 규칙

- 전투는 서버 권위이며 가능한 한 결정적이다.
- 이동, 회전, 일반 타일 큐 등록, 큐 실행은 턴을 소비한다.
- FreePlay 타일 큐 등록만 턴을 소비하지 않는다.
- 큐는 3칸을 기본값으로 하며 `기본값 + 직업/증강/유물 보너스`를 상하한 안에서 합산한다.
- 일반 타일을 등록해 적 턴을 보낸 뒤에도 큐는 유지되며, 다음 플레이어 턴에 이동·회전·추가 등록 후 별도 실행 명령으로 한 번에 해소한다.
- 턴과 큐 항목은 1:1이 아니다. FreePlay 등록·제거·순서 변경은 턴을 넘기지 않고 여러 번 수행할 수 있으며, 일반 등록과 전체 큐 실행만 각각 하나의 턴 소비 Command다.
- 큐 실행 중 각 타일은 현재 보드에서 타깃을 다시 계산한다.
- 적의 공격 타일 보유 상태와 공격 예고 상태를 분리한다. 적은 공격 타일을 먼저 등록하고, 사거리·방향이 맞지 않으면 타일을 유지한 채 회전·추적한다.
- 공격 조건이 맞아 `ATTACK_READY`가 된 다음 행동만 플레이어에게 공격으로 미리 표시하며, 그 사이 플레이어 대응 Command 1회를 허용한다.
- `ATTACK_READY` Intent는 ActionType/TileId가 고정되며, 플레이어가 위치를 바꿔도 실행 직전에 추적이나 다른 행동으로 재선택하지 않는다.
- 예고된 공격은 TargetId를 저장하지 않고 실행 시점의 현재 CellIndex/Facing과 타일 Target 규칙으로 명중 셀을 계산하므로 피하면 빗나갈 수 있다.
- 전투 월드 위치와 논리 CellIndex를 분리한다.
- 적은 플레이어 좌우 어느 빈 칸에도 배치될 수 있어, 방향 전환은 전투 내내 반복적으로 필요한 핵심 조작이다.

## 4. M1 콘텐츠 범위

| 콘텐츠 | M1 목표 |
|---|---:|
| 직업 | 4 |
| 일반 적 | 2 이상 |
| 보스 | 1 |
| 스테이지 | 3 |
| 공격 타일 | 8 이상 |
| 증강 | 12 이상 |
| 원시 EffectType | 6 |
| 원시 EnemyActionType | 7 |

구조 검증은 직업 1종, 적 2종, 보스 1종, 타일 4종, 증강 3종으로 먼저 수행한다. 구조가 통과한 뒤 값으로 목표 수량까지 확장한다.

### 4.1 확장 월드맵 콘텐츠 목표

M1 이후에는 다음 6개 마을을 하나의 도시 경로 그래프로 확장한다.

| 순서 | 출발 마을 | 경로 상점 | 도착 마을 | 경로 |
|---:|---|---|---|---|
| 1 | 헤네시스 | 헤네시스→커닝시티 상점 | 커닝시티 | `UPPER` |
| 2 | 헤네시스 | 헤네시스→엘리니아 상점 | 엘리니아 | `LOWER` |
| 3 | 커닝시티 | 커닝시티→페리온 상점 | 페리온 | `UPPER` |
| 4 | 엘리니아 | 엘리니아→노틸러스 상점 | 노틸러스 | `LOWER` |
| 5 | 페리온 | 페리온→슬리피우드 상점 | 슬리피우드 | `UPPER` |
| 6 | 노틸러스 | 노틸러스→슬리피우드 상점 | 슬리피우드 | `LOWER` |

- 한 Run에서는 헤네시스 이후 `UPPER` 또는 `LOWER` 중 하나를 선택하며, 선택하지 않은 경로는 해당 Run 동안 잠긴다.
- 위쪽은 `헤네시스 → 커닝시티 → 페리온 → 슬리피우드`, 아래쪽은 `헤네시스 → 엘리니아 → 노틸러스 → 슬리피우드` 순서다.
- 슬리피우드는 두 경로가 합류하는 공통 후반 지역이다.
- 각 마을은 독립 `RegionId`와 복수 전투/보스 노드를 가질 수 있으며, 실제 스테이지 수는 지역 데이터로 확장한다.

마을별 Region과 물리 맵 명명 규칙:

| RegionId | 마을 | 일반전 MapId | 보스전 MapId | 경로 순서 |
|---|---|---|---|---|
| `region_01` | 헤네시스 | `region_01_battle` | `region_01_boss` | 시작 지역 |
| `region_02` | 커닝시티 | `region_02_battle` | `region_02_boss` | `UPPER` 2번째 |
| `region_03` | 엘리니아 | `region_03_battle` | `region_03_boss` | `LOWER` 2번째 |
| `region_04` | 페리온 | `region_04_battle` | `region_04_boss` | `UPPER` 3번째 |
| `region_05` | 노틸러스 | `nautilus_battle` | `nautilus_boss` | `LOWER` 3번째 |
| `region_06` | 슬리피우드 | `sleepywood_ant_tunnel` | `sleepywood_food_cart_boss` | 공통 합류 지역 |

- 일반전 물리 맵 재사용 범위는 같은 Region 내부로 제한한다. 예를 들어 커닝시티의 여러 일반 Stage는 `region_02_battle`을 함께 사용하지만 헤네시스의 `region_01_battle`은 사용하지 않는다.
- 보스전은 지역별 배경과 전조 연출을 독립 제작할 수 있도록 각 Region의 `region_XX_boss` 맵으로 분리한다.
- `StageId`는 콘텐츠 식별자이고 `MapId`는 물리 맵이므로 계속 분리한다. 표시용 `2-1` 같은 번호는 Region/Stage 데이터에서 결정한다.

## 5. 직업 설계 원칙

직업은 클래스를 상속하지 않고 `JobDefinitions`, `JobStartingSkillEntries`, 공통
`PlayerCombatComponent`, 독립 `JobMechanic` Handler의 조합으로 만든다.

M1 직업 슬롯:

1. 근접/밀치기 중심
2. 원거리/관통 중심
3. 방어/반격 중심
4. 이동/쿨다운 조작 중심

각 직업은 시작 HP, 큐 크기, 시작 스킬 세트, 직업 고유 메커니즘, 대표 패시브로 구분한다.
시작 스킬은 일반 `SkillDefinitions`를 재사용하지만 직업 고유 메커니즘은 큐에 등록되지 않는다.

## 6. 적과 스테이지 원칙

- 일반 적은 `EnemyPatternSteps`의 순차 패턴으로 행동한다.
- `EnemyActionPlanComponent`는 공격 타일의 `INSERTING → TRACKING → ATTACK_READY → EXECUTING` 상태를 적별로 소유한다.
- `EnemyPatternRunnerComponent`는 공격 주기 중 StepIndex를 유지하며, 추적 이동이 아니라 공격 실행이 끝난 뒤에만 다음 Step으로 전진한다.
- `ATTACK_READY` 뒤의 밀치기나 이동은 준비된 ActionType/TileId를 바꾸지 않는다. 위치가 달라져 사거리가 맞지 않으면 예고 공격이 빗나간다.
- `QUICK`은 현재 사거리·방향이 맞을 때만 타일 등록과 `ATTACK_READY`를 같은 적 행동에서 처리한다.
- 보스는 HP 조건에 따라 PatternId를 바꾼다.
- BT는 PatternStep으로 표현하기 어려운 요구가 확인된 후에만 도입한다.
- 적의 초기 `Facing`은 생성 순간 한 번 결정한다. 기본 정책은 `FACE_PLAYER`이며, 특수 적이나 연출은 `FIXED_LEFT`/`FIXED_RIGHT` 또는 스테이지 배치의 `FacingOverride`를 사용한다.
- `TURN_TO_PLAYER`는 제자리 회전, `MOVE_TOWARD`/`MOVE_AWAY`는 플레이어 상대 방향으로 회전 후 이동, `MOVE_FIXED_FACING`은 현재 `Facing`을 바꾸지 않고 그 방향으로 이동한다.
- 고정 방향 이동이 보드 끝이나 점유 셀에 막히면 해당 행동은 `WAIT`로 끝나며 자동 반전하지 않는다.
- 추적형/고정형은 몬스터 종류를 상속으로 나누지 않고 `EnemyPatternSteps`에 어떤 Action을 조합했는지로 구분한다.
- 스테이지의 첫 배치는 Wave 1이며 맵에 적을 고정하지 않고 `StageEnemySpawns`의 EnemyId, CellIndex, FacingOverride, SpawnOrder를 읽어 런타임 생성한다.
- 후속 웨이브는 `EnemySpawnPools`에서 가중치로 뽑아 좌우 빈 칸에 채운다. 기본 진행은 현재까지 생성된 적 전멸 후 다음 웨이브 시작이다.
- 스테이지 데이터는 `CLEAR_ONLY`, `TURN_LIMIT`, `TIME_LIMIT`, `TURN_OR_TIME` 중 하나를 선택할 수 있다. 제한 모드는 적이 남아 있어도 지정 턴 또는 시간이 지나면 다음 웨이브를 강제 증원한다.
- 턴 제한은 웨이브 생성 뒤 완료된 턴 수로 계산한다. 시간 제한이 행동 도중 충족되면 현재 행동을 끊지 않고 다음 안전한 턴 경계에서 증원한다.
- 강제 증원으로 여러 웨이브가 겹치면 남은 적과 새 적이 같은 적 턴에 참여한다. 마지막 웨이브 출현 후 전체 생존 적이 0명이 되어야 스테이지가 완료된다.
- 후속 웨이브의 기본 배치 정책은 `BALANCED`다. 양쪽에 빈 칸이 있고 2명 이상 생성하면 좌우에 최소 1명씩 먼저 배치하고, 남은 적은 전체 빈 칸에서 뽑는다. `ANY`는 방향 강제 없이 전체 빈 칸에서 뽑는다.
- 웨이브 등장 칸 선택은 RunSeed+StageIndex+WaveIndex 기반 결정적 규칙을 따른다.
- 스테이지는 AugmentPoolId를 데이터로 정의한다.
- 여러 스테이지는 `RegionDefinitions`/`NodeDefinitions`로 묶은 지역 단위 지도판·노드맵으로 진행한다. 지역 하나는 일반 전투 노드 여러 개와 보스 노드 하나로 구성되고, 다음 지역은 `UnlockRegionId`로 이전 지역 보스 클리어를 조건으로 연다.
- 지역별 등장 몬스터는 `EnemySpawnPools`(MonsterPoolId)로 정의하며, 헤네시스/엘리니아/슬리피우드처럼 지역마다 다른 몬스터 구성을 원시 타입 변경 없이 표로 교체한다.
- 모든 마을 간 연결은 `출발 마을 → SHOP 노드 → 도착 마을`의 3단계 Edge로 정의한다. 도시 UI가 상점 로직을 직접 소유하지 않는다.
- 출발 마을의 클리어 조건을 만족하면 해당 Edge의 상점이 열리고, 상점 방문을 마치면 연결된 다음 마을이 선택 가능해진다.
- 현재 프로토타입은 헤네시스 `1-1` 클리어를 첫 Edge 해금 조건으로 사용한다. 정식 지역 확장 시에는 각 `RegionDefinitions`의 최종 노드 또는 보스 클리어를 기본 조건으로 사용한다.
- 상점 방문 여부, 구매 결과, 선택 경로와 현재 마을은 서버 권위의 플레이어 Run 상태가 소유한다. 월드맵 UI는 이 Snapshot을 표시하고 요청만 전송한다.
- 각 Edge 상점은 서로 다른 `ShopId`를 사용하되 `ShopVisitBtn` UI와 공통 Shop Controller를 재사용한다.
- `StageMapRoutes`는 각 StageId를 소속 Region의 `region_XX_battle` 또는 `region_XX_boss`로 라우팅한다. 서로 다른 마을을 하나의 Region 물리 맵으로 합치지 않는다.
- 헤네시스 보스 뒤에는 위·아래 상점 중 하나를 고르는 배타적 분기가 있다. 서버가 승인한 `SelectedContentId`가 현재 런의 경로 원본이며, 상점 완료 뒤에도 반대 경로는 잠긴다.
- 두 분기는 같은 `shop` 물리 맵을 재사용하되 각자의 `ShopId`와 CSV 상품 목록을 사용한다. 구매 아이템은 능력치 없이 현재 런에만 보관한다.

## 7. 증강 원칙

- 각 스테이지 완료 후 3개 후보 중 하나를 선택한다.
- 후보는 RunSeed와 StageIndex에서 결정적으로 생성한다.
- 증강은 Trigger + Condition + Effect 조합이다.
- 최종 규격은 Unique, StackAdd, StackRefresh, ExclusiveGroup 정책을 지원한다. 현재 구현은 Unique 1스택뿐이며 나머지는 계획 단계다.
- 이벤트 무한 재귀를 막기 위해 SourceTag와 MaxDepth를 둔다.
- 계획된 확률 기반 증강(예: "50% 확률로 후방 공격")은 `ConditionType=CHANCE_ROLL`과 `ConditionValue`(0.0~1.0)로 표현하며, 판정은 RunSeed 기반 결정적 롤을 사용한다. Router/Validator 구현 전에는 실전 데이터에 사용하지 않는다.
- 유물(상점에서 얻는 시작 증강 포함)도 같은 `AugmentDefinitions`/`AugmentEffects` 스키마를 사용한다. 유물 전용 별도 테이블을 만들지 않는다.

## 8. MSW 구현 결정

| 시스템 | MSW 구현 |
|---|---|
| 전투 세션 | 맵 엔티티 `BattleSessionComponent` |
| 보드 점유와 다중 유닛 | 맵 엔티티 `BoardStateComponent` |
| 개별 적 패턴 상태 | 적 엔티티 `EnemyPatternRunnerComponent` |
| 개별 적 공격 큐 상태 | 적 엔티티 `EnemyActionPlanComponent` |
| 적 Intent 읽기 모델 | 서버 `PreparedIntent` Snapshot + Client용 읽기 전용 DTO/Event |
| 스테이지/웨이브 진행 | 맵 엔티티 `StageFlowComponent` |
| 전투 격리 | 플레이어당 Instance Room/Instance Map |
| 플레이어 런 상태 | 플레이어 엔티티 `PlayerRunStateComponent` |
| 정적 데이터 | UserDataSet + CSV |
| UI | `.ui` + UIBuilder + ClientOnly Logic |
| 적/플레이어 엔티티 | `.model` + ModelBuilder |
| 맵 배치 | Region별 `region_XX_battle.map` + `region_XX_boss.map`; 같은 Region 내부 일반 Stage만 전투 맵을 재사용하고 `StageId`와 `MapId`는 CSV로 분리 라우팅 |
| 월드맵 진행 | `RegionDefinitions` + `NodeDefinitions` + 서버 `PlayerRunStateComponent` Snapshot |
| 마을 간 상점 | Edge별 `ShopId`, 공통 `ShopVisitBtn`, RUN_SCOPED Shop Controller |
| 전투 이벤트 | `@Event extends EventType` |
| 무상태 규칙 | `@Logic` Resolver/Router |
| 현재 전투 맵 타입 | MapleTile(0); 전투 유닛 이동은 물리 이동이 아닌 서버 권위 Cell Snapshot |

협업 시 소유권은 다음과 같이 분리한다.

- 콘텐츠 개발자는 기존 `EnemyActionType`을 조합해 `EnemyDefinitions.csv`와 `EnemyPatternSteps.csv` 행을 추가·수정한다.
- 전투 코어 개발자는 Loader/Validator, Pattern Runner, Resolver/Router를 소유하며 EnemyId별 분기를 만들지 않는다.
- UI 개발자는 Prepared Intent DTO/Event만 읽고 서버의 조건·타깃 판정을 UI 코드에 복제하지 않는다.
- 기존 ActionType만 사용하는 새 적은 `.mlua` 수정 없이 표 행 추가로 완성하는 것을 기본 완료 기준으로 한다.
- 새 원시 ActionType이 정말 필요할 때만 Router, Validator 허용 목록, 데이터 사전, 회귀 테스트를 한 변경 단위로 확장한다.

## 9. 로드맵

- [ ] Phase 0 — 맵/이동/RPC/데이터/큐 재타깃 기술 검증
- [ ] Phase 1 — 전투 코어 수직 슬라이스 + CSV 기반 단일 전투 맵 재사용
  - [ ] 헤네시스 이후 분기형 런 상점 — 월드맵 선택·이동 연출, 33종 CSV 상품, NPC 상점 UI, 무구매 퇴장, 선택 경로 잠금
  - 🟡 엘리니아 전투 무대 1차 시각 패스 — 전투 구조는 유지하고 헤네시스 복제 장식을 엘리니아 숲 테마로 교체, Maker 화면 검토 대기
- [ ] Phase 2 — 데이터 기반 타일과 일반 적
- [ ] Phase 3 — 스테이지와 보스 패턴
- [ ] Phase 4 — 직업 4종과 증강
- [ ] Phase 5 — 제작자 검증 도구와 재현 테스트
- [ ] Phase 6 — 연출, 저장, 출시 준비

M1 이후 콘텐츠 확장 트랙:

- [ ] 헤네시스 첫 분기 계약을 Dataset 기반 공통 City/Shop Edge로 전환
- [ ] 커닝시티 지역 + 커닝시티→페리온 상점
- [ ] 엘리니아 지역 + 엘리니아→노틸러스 상점
- [ ] 페리온 지역 + 페리온→슬리피우드 상점
- [ ] 노틸러스 지역 + 노틸러스→슬리피우드 상점
- [ ] 슬리피우드 합류 지역과 양쪽 경로 회귀 검증

세부 완료 조건은 `MapleTactics-M1-Implementation-Plan.md`를 따른다.

## 10. 제외 범위

- M1에서 실시간 멀티플레이 전투는 제외한다.
- 새로운 효과를 완전히 무코드로 정의하는 범용 스크립팅 언어는 만들지 않는다.
- 모든 일반 적을 BT로 제작하지 않는다.
- 메타 진행, 과금 연동, 랭킹은 M1 코어 루프 이후로 미룬다.
- M1은 `ShopDefinitions`/`ShopEntries` 기반 RUN_SCOPED 런 상점의 서버 흐름, NPC 상점 UI와 디버그 DTO를 포함한다. `ShopItemDefinitions` 기반 Meta/World Shop, 능력치·장착, 영구 구매 상태, 실제 결제 연동은 이후 범위다.
- 커닝시티·엘리니아·페리온·노틸러스·슬리피우드의 완성 전투 콘텐츠는 M1 수직 슬라이스 이후 범위다. M1에서는 6개 도시 표시, 첫 분기, 공통 상점 Edge 계약까지만 검증한다.
- 상점 퇴장 뒤 엘리니아·커닝시티 경로의 잠금 표시는 M1에 포함하지만 실제 목적지 맵과 Stage 연결은 후속 Backlog다.
- 스테이지 클리어 보상(`StageRewardDefinitions`)으로 `RUN_SCOPED`/`META_PERSISTENT` 재화를 지급하는 흐름은 M1 범위에 포함한다. `PREMIUM_CASH` 재화는 보상으로 지급하지 않는다.

## 11. 성공 기준

- 한 플레이어가 직업을 선택해 3개 스테이지와 증강 선택을 완료할 수 있다.
- 같은 Seed와 CommandLog가 같은 핵심 전투 상태를 재현한다.
- 기존 원시 타입 조합의 새 타일/적/스테이지/증강은 코드 수정 없이 추가된다.
- 데이터 오류가 전투 시작 전에 명확한 행/열 정보와 함께 차단된다.
- 핵심 시나리오는 Maker build/runtime 로그와 positive log로 검증된다.

## 12. 계획 변경 기록

| 날짜 | 유형 | 변경 | 이유 | 영향 |
|---|---|---|---|---|
| 2026-08-30 | 추가 | `ellinia_battle` 1차 시각 패스를 Phase 1 준비 작업으로 선행 | 아래쪽 상점 경로의 다음 지역 분위기를 먼저 확정하기 위함 | 전투 구조·Stage 라우팅은 유지하고 맵 장식만 변경; 실제 엘리니아 Stage 연결은 Roadmap Backlog 유지 |
| 2026-07-17 | 수정 | 일반 Lua 상속/인터페이스에서 MSW Component 조합으로 변경 | mLua 등록과 실행 공간에 맞추기 위함 | 구현 구조 전반 |
| 2026-07-17 | 수정 | Service 확장 Manager를 BattleSessionComponent/Logic으로 변경 | 사용자 스크립트 수명과 상태 권한 교정 | 00_Core/01_Combat |
| 2026-07-17 | 수정 | 일반 적 BT+FSM+Pattern 중첩을 Pattern Runner로 단순화 | 상태 권한 중복과 제작 난이도 감소 | AI 구조 |
| 2026-07-17 | 추가 | Phase 0 기술 검증 게이트 | 실제 MSW 경계를 본 구현 전에 증명 | 전체 일정 |
| 2026-07-18 | 수정 | 큰 시스템 단위 로드맵을 화면 중심 마이크로 수직 슬라이스로 세분화 | Maker 화면을 보며 기능 하나씩 이해·검증하고, 실제 두 번째 사례가 생긴 뒤 인터페이스를 추출하기 위함 | Phase 1은 배치→이동→전환→공격→사망→적 행동→턴→타일 큐 순으로 진행. Registry·Dataset·증강은 후속 Phase로 이동 |
| 2026-07-24 | 수정 | 스테이지 적 배치를 고정 단일 로스터에서 양방향 배치 + 다중 웨이브(`EnemySpawnPools`/`StageEnemyWaves`) 구조로 확장 | 참고작(쇼군 쇼다운)처럼 좌우에서 적이 계속 보충되며 이어지는 전투를 지원 | Data-Dictionary(StageEnemySpawns 수정, EnemySpawnPools·StageEnemyWaves 신설), GDD §3/§6, Implementation-Plan Phase 3 |
| 2026-07-24 | 추가 | EnemyActionType에 `MOVE_FIXED_FACING` 추가 | 플레이어 위치와 무관하게 한 방향으로만 움직이는 몬스터와, 플레이어를 따라 도는 몬스터를 데이터만으로 구분 표현하기 위함 | Data-Dictionary §7, GDD §4 콘텐츠 수량, Implementation-Plan Phase 2/3 |
| 2026-07-25 | 수정 | 초기 방향 결정과 전투 중 방향 행동을 분리하고, 웨이브 배치에 `BALANCED`/`ANY` 정책을 추가 | 생성 위치에 따라 고정 방향 적이 보드 바깥을 향하는 문제를 막고 객체별 책임을 명확히 하기 위함 | EnemyDefinitions, StageEnemySpawns, StageEnemyWaves, 적 Action 의미, Phase 1~3 구현 순서 |
| 2026-07-25 | 추가 | 적 Intent를 `Prepare → Hold → Execute → Complete` 상태로 분리하고 `EnemyPatternSteps` 표에서 생성되는 PreparedIntent 계약과 개발자별 소유권을 명시 | 밀치기 직후 적이 행동을 재선택해 위치 조작이 무의미해지는 문제를 막고, 여러 개발자가 전투 코어 충돌 없이 표 행으로 적을 확장하기 위함 | Phase 1 Slice 10.5, GDD §3/§6/§8, Data-Dictionary §7.1/§7.2, Implementation-Plan 전투 코어 완료 기준 |
| 2026-07-25 | 추가 | 웨이브 전멸 기본 진행에 턴/시간 제한 강제 증원 예외와 겹친 웨이브의 최종 승리 조건 추가 | 턴을 오래 소비할수록 적 증원이 누적되는 압박을 만들고, 스테이지 제작자가 표에서 증원 속도를 조절하기 위함 | GDD §6, Data-Dictionary StageEnemyWaves, Implementation-Plan Phase 3 |
| 2026-07-28 | 추가 | 지역/노드맵 구조(`RegionDefinitions`/`NodeDefinitions`) 신설 | 팀 회의에서 확정된 마을→지도판→노드맵→전투 흐름을 여러 스테이지 데이터로 표현하기 위함 | GDD §6, Data-Dictionary §9/§10, Implementation-Plan Phase 3 |
| 2026-07-28 | 추가 | 상점 데이터 구조(`ShopItemDefinitions`) 신설, 제외범위에서 "상점 데이터/화면"과 "결제 연동"을 분리 | 팀이 상점(캐시샵 포함) 콘텐츠 구조를 M1 범위에서 먼저 결정하기로 함 | GDD §10, 현재 Data-Dictionary §20.3 |
| 2026-07-28 | 추가 | AugmentEffects에 `ConditionValue`, `ConditionType=CHANCE_ROLL`, `TargetType=REAR_CELL` 추가 | "자쿰의 투구: 50% 확률 후방 공격"처럼 확률 기반·후방 타깃 유물을 코드 수정 없이 표로 표현하기 위함 | GDD §7, Data-Dictionary §15 |
| 2026-07-30 | 추가 | 재화 레지스트리(`CurrencyDefinitions`) 신설, `ShopItemDefinitions.CurrencyType` 고정 enum을 `CurrencyId` 참조로 변경, 스테이지 클리어 보상(`StageRewardDefinitions`) 신설 | 체력을 재화로 쓰는 방식은 보류하고, 상점과 스테이지 보상이 같은 재화 정의 하나를 참조해 어떤 표든 재화 종류만 데이터로 바꿔 쓸 수 있게 하기 위함 | GDD §10, 현재 Data-Dictionary §18(CurrencyDefinitions)/§19(StageRewardDefinitions)/§20.3(ShopItemDefinitions)/§22(Validator 오류 코드) |
| 2026-07-31 | 수정 | `EnemyDefinitions` 표에 빠져 있던 `InitialFacingPolicy`(`FACE_PLAYER`/`FIXED_LEFT`/`FIXED_RIGHT`) 컬럼을 추가 | `StageEnemySpawns`(§11)와 `StageEnemyWaves`(§13)가 이미 `EnemyDefinitions.InitialFacingPolicy`를 참조하고 있었는데 정작 §6 표 정의에는 해당 컬럼이 없던 문서 불일치를 바로잡음 | Data-Dictionary §6. 실제 `EnemyDefinitions.userdataset`/`.csv`에 이 컬럼을 추가하는 작업은 Maker의 UserDataSet 편집 화면에서 별도로 진행 필요(직접 JSON 편집 금지) |
| 2026-08-01 | 추가 | 적 사망 드롭을 `EnemyDropDefinitions`로 분리하고 Pending Drop→승리 자동 회수→런 재화·소모품 상태 흐름을 추가 | 적 밸런스와 드롭표의 파일 충돌을 줄이고, Stage 보상·상점과 같은 런 보상 지급 경계를 재사용하기 위함 | Data-Dictionary §21, Implementation Plan Phase 3, Battle Core Guide §10. 실제 Dataset 페어 이관과 fallback 비활성까지 완료; 전투 중 소모품 사용 효과는 후속 작업 |
| 2026-08-01 | 수정 | 일반 타일 등록과 큐 실행을 분리하고, 등록 후 적 턴에도 큐를 유지하는 쇼군식 흐름 및 기본+Modifier 큐 용량 계약을 확정 | 큐를 쌓는 동안 위치·방향을 조정한 뒤 별도 실행 키로 전체 큐를 해소하는 핵심 플레이를 구현하기 위함 | BattleTurn/BattleSession, BattleQueueHUD, UI 상태 DTO, Queue Modifier API |
| 2026-08-01 | 수정 | 직업 시작 스킬과 직업 고유 메커니즘을 분리하고 구 TileDefinitions 명칭을 실제 SkillDefinitions 규격으로 통합 | 쇼군식 공격 타일과 캐릭터 고유 이동·전투 규칙은 실행 수명과 턴/쿨타임 계약이 다르므로 독립 확장점이 필요함 | JobDefinitions, JobStartingSkillEntries, JobMechanic Router, Data Dictionary §2~5 |
| 2026-08-03 | 수정 | 구현 상태 표기와 상점 책임을 정리하고, 증강 허용값·StackPolicy·EnemyDrop 장 번호를 실제 코드에 맞춤 | 표 기반 제작자가 미구현 값을 지원 값으로 오해하거나 런 상점과 Meta/World Shop 데이터를 혼용하지 않도록 하기 위함 | Data-Dictionary §1/§14/§15/§20~23, GDD §7/§10, 관련 제작 가이드 |
| 2026-08-15 | 수정 | 적 공격 타일 등록과 공격 예고를 분리하고, 타일을 보유한 채 사거리까지 추적한 뒤 대응 턴 후 고정 실행하는 흐름으로 확장 | 사거리 진입 뒤에야 큐를 만드는 현재 동작을 참고작의 읽을 수 있는 적 공격 주기에 맞추고, 회피·밀치기로 예고 공격을 빗나가게 하는 전술을 보존하기 위함 | GDD §3/§6/§8, Phase 1 Slice 10.6, Shogun Queue Plan Slice 6, 전용 수정 계획 |
| 2026-08-22 | 수정 | 모든 전투 StageId를 `region_01_battle` 물리 맵으로 라우팅하고 스테이지 콘텐츠는 CSV의 StageId로만 선택 | 전투 맵을 한 번만 꾸미고 여러 스테이지가 동일한 컴포넌트 구성을 재사용하도록 하기 위함 | StageMapRoutes, BattleSession 맵 설정, SectorConfig, Phase 1 Slice 14; Static Map 운영을 위해 월드 최대 인원 1명으로 제한 |
| 2026-08-22 | 수정 | 1-1~1-3은 헤네시스 일반전 공용 맵을 유지하고 1-4는 `region_01_boss` 전용 물리 맵으로 분리 | 일반 스테이지 재사용 이점은 유지하면서 머쉬맘 보스전의 배경·전조 가독성과 공간 연출을 독립 조정하기 위함 | StageMapRoutes, 물리 맵 2종, Phase 1 Slice 14~15 |
| 2026-08-25 | 수정 | 등록 CSV 자산으로 6도시 월드맵을 재구성하고 헤네시스 클리어 후 위·아래 상점 중 하나를 선택하는 분기 추가. 위쪽은 커닝시티, 아래쪽은 엘리니아의 동일 1-2 전투로 연결 | 참고 이미지의 상·하 경로 선택과 다음 전투 전 선택적 상점 동선을 구현하기 위함 | `PopupGroup.ui`, `MinimapUI`, `PlayerRunStateComponent`, `RunManagerLogic`, 월드맵 Stage 버튼, Phase 1 Slice 16 |
| 2026-08-26 | 수정 | 6개 마을 전체 경로와 모든 마을 사이의 Edge 상점을 확정하고 각 마을을 `region_01`~`region_06` 독립 Region·물리 맵 세트로 분리 | 첫 분기 전용 구현을 반복 가능한 구조로 확장하면서 마을별 배경·몬스터·보스 연출을 독립 제작하기 위함 | GDD 플레이 루프·지역/맵 규칙·MSW 구현 결정·로드맵, Phase 1 후속 확장 순서 |
| 2026-08-29 | 추가 | 헤네시스 보스 뒤 위·아래 런 상점 분기와 선택 경로 잠금, 33종 무능력치 런 아이템 상점 UI를 M1에 추가 | 보스 뒤 선택·소비·다음 지역 예고까지 하나의 플레이 가능한 런 흐름으로 연결하기 위함 | GDD §6/§9/§10, Phase 1 분기형 런 상점, NodeDefinitions·ShopDefinitions·ShopEntries, 월드맵·shop.map |
| 2026-08-29 | 수정 | 전투 맵 타입 문서를 실제 `MapleTile(0)` 구현에 맞추고 `region_05` 노틸러스 콘텐츠 확장을 시작 | 문서의 SideViewRectTile 표기가 실제 전투 맵·Foothold 구성과 달랐으며, 지역 번호와 진행 난이도를 분리해야 함 | GDD §8, Region/Stage/Map 데이터, 노틸러스 제작 가이드 |
| 2026-09-03 | 추가 | 적 Pattern 공용 행동에 피해 스킬로 끊을 수 있는 `CAST_INTERRUPTIBLE`을 추가하고 킹크랑 2 Phase 버블 캐논에 적용 | 플레이어가 보스의 강한 공격을 수동적으로 피하기만 하지 않고 큐 구성과 공격 횟수로 대응하게 하며, 보스 ID 하드코딩 없이 다른 적도 같은 규격을 재사용하기 위함 | EnemyPatternSteps, EnemyActionPlan, Battle UI DTO, Boss 제작 가이드 |
