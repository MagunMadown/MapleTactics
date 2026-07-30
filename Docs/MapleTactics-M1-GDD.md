# MapleTactics M1 GDD

Stage: Phase 1 prototype in progress, bidirectional combat expansion planned

Milestone: M1 playable vertical slice

## 1. 게임 한 줄 설명

1차원 전장에서 이동과 방향 전환으로 적의 예고 행동을 피하고, 공격 타일을 큐에 조합해 순차 실행하는 턴제 전술 로그라이크.

## 2. M1 플레이 루프

```text
직업 선택
-> 스테이지 시작
-> 이동/회전/타일 큐 등록/큐 실행
-> 적 Intent 해결
-> 승리
-> 증강 3택
-> 다음 스테이지
```

## 3. 핵심 규칙

- 전투는 서버 권위이며 가능한 한 결정적이다.
- 이동, 회전, 일반 타일 큐 등록, 큐 실행은 턴을 소비한다.
- FreePlay 타일 큐 등록만 턴을 소비하지 않는다.
- 큐는 최대 3칸을 기본값으로 하며 직업/증강이 변경할 수 있다.
- 큐 실행 중 각 타일은 현재 보드에서 타깃을 다시 계산한다.
- 적의 다음 행동은 플레이어에게 미리 표시된다.
- 적 Intent는 플레이어 턴 전에 준비되어 ActionType/TileId가 고정되며, 플레이어가 위치를 바꿔도 실행 직전에 다른 행동으로 재선택하지 않는다.
- 준비된 공격은 TargetId를 저장하지 않고 실행 시점의 현재 CellIndex/Facing과 타일 Target 규칙으로 명중 셀을 계산한다.
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

## 5. 직업 설계 원칙

직업은 클래스를 상속하지 않고 `JobDefinitions` 데이터와 공통 `PlayerCombatComponent`의 조합으로 만든다.

M1 직업 슬롯:

1. 근접/밀치기 중심
2. 원거리/관통 중심
3. 방어/반격 중심
4. 이동/쿨다운 조작 중심

각 직업은 시작 HP, 큐 크기, 시작 타일 세트, 대표 패시브로 구분한다.

## 6. 적과 스테이지 원칙

- 일반 적은 `EnemyPatternSteps`의 순차 패턴으로 행동한다.
- `EnemyPatternRunnerComponent`는 표의 다음 Step을 `PreparedIntent` 런타임 Snapshot으로 만들고 `Prepare → Hold → Execute → Complete` 상태를 관리한다.
- 밀치기나 이동은 준비된 ActionType/TileId를 바꾸지 않는다. 위치가 달라져 사거리가 맞지 않으면 예고 공격이 빗나간다.
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

## 7. 증강 원칙

- 각 스테이지 완료 후 3개 후보 중 하나를 선택한다.
- 후보는 RunSeed와 StageIndex에서 결정적으로 생성한다.
- 증강은 Trigger + Condition + Effect 조합이다.
- Unique, StackAdd, StackRefresh, ExclusiveGroup 정책을 지원한다.
- 이벤트 무한 재귀를 막기 위해 SourceTag와 MaxDepth를 둔다.
- 확률 기반 증강(예: "50% 확률로 후방 공격")은 `ConditionType=CHANCE_ROLL`과 `ConditionValue`(0.0~1.0)로 표현하며, 판정은 RunSeed 기반 결정적 롤을 사용한다.
- 유물(상점에서 얻는 시작 증강 포함)도 같은 `AugmentDefinitions`/`AugmentEffects` 스키마를 사용한다. 유물 전용 별도 테이블을 만들지 않는다.

## 8. MSW 구현 결정

| 시스템 | MSW 구현 |
|---|---|
| 전투 세션 | 맵 엔티티 `BattleSessionComponent` |
| 보드 점유와 다중 유닛 | 맵 엔티티 `BoardStateComponent` |
| 개별 적 패턴 상태 | 적 엔티티 `EnemyPatternRunnerComponent` |
| 적 Intent 읽기 모델 | 서버 `PreparedIntent` Snapshot + Client용 읽기 전용 DTO/Event |
| 스테이지/웨이브 진행 | 맵 엔티티 `StageFlowComponent` |
| 전투 격리 | 플레이어당 Instance Room/Instance Map |
| 플레이어 런 상태 | 플레이어 엔티티 `PlayerRunStateComponent` |
| 정적 데이터 | UserDataSet + CSV |
| UI | `.ui` + UIBuilder + ClientOnly Logic |
| 적/플레이어 엔티티 | `.model` + ModelBuilder |
| 맵 배치 | `.map` + MapBuilder |
| 전투 이벤트 | `@Event extends EventType` |
| 무상태 규칙 | `@Logic` Resolver/Router |
| 권장 맵 타입 | SideViewRectTile(2) |

협업 시 소유권은 다음과 같이 분리한다.

- 콘텐츠 개발자는 기존 `EnemyActionType`을 조합해 `EnemyDefinitions.csv`와 `EnemyPatternSteps.csv` 행을 추가·수정한다.
- 전투 코어 개발자는 Loader/Validator, Pattern Runner, Resolver/Router를 소유하며 EnemyId별 분기를 만들지 않는다.
- UI 개발자는 Prepared Intent DTO/Event만 읽고 서버의 조건·타깃 판정을 UI 코드에 복제하지 않는다.
- 기존 ActionType만 사용하는 새 적은 `.mlua` 수정 없이 표 행 추가로 완성하는 것을 기본 완료 기준으로 한다.
- 새 원시 ActionType이 정말 필요할 때만 Router, Validator 허용 목록, 데이터 사전, 회귀 테스트를 한 변경 단위로 확장한다.

## 9. 로드맵

- [ ] Phase 0 — 맵/이동/RPC/데이터/큐 재타깃 기술 검증
- [ ] Phase 1 — 전투 코어 수직 슬라이스
- [ ] Phase 2 — 데이터 기반 타일과 일반 적
- [ ] Phase 3 — 스테이지와 보스 패턴
- [ ] Phase 4 — 직업 4종과 증강
- [ ] Phase 5 — 제작자 검증 도구와 재현 테스트
- [ ] Phase 6 — 연출, 저장, 출시 준비

세부 완료 조건은 `MapleTactics-M1-Implementation-Plan.md`를 따른다.

## 10. 제외 범위

- M1에서 실시간 멀티플레이 전투는 제외한다.
- 새로운 효과를 완전히 무코드로 정의하는 범용 스크립팅 언어는 만들지 않는다.
- 모든 일반 적을 BT로 제작하지 않는다.
- 메타 진행, 과금 연동, 랭킹은 M1 코어 루프 이후로 미룬다.
- 상점은 `ShopItemDefinitions`/`CurrencyDefinitions` 데이터 구조와 화면만 M1 범위에 포함하고, 실제 결제(카드/인앱 결제 등) 연동은 미룬다.
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
| 2026-07-28 | 추가 | 상점 데이터 구조(`ShopItemDefinitions`) 신설, 제외범위에서 "상점 데이터/화면"과 "결제 연동"을 분리 | 팀이 상점(캐시샵 포함) 콘텐츠 구조를 M1 범위에서 먼저 결정하기로 함 | GDD §10, Data-Dictionary §18 |
| 2026-07-28 | 추가 | AugmentEffects에 `ConditionValue`, `ConditionType=CHANCE_ROLL`, `TargetType=REAR_CELL` 추가 | "자쿰의 투구: 50% 확률 후방 공격"처럼 확률 기반·후방 타깃 유물을 코드 수정 없이 표로 표현하기 위함 | GDD §7, Data-Dictionary §15 |
| 2026-07-30 | 추가 | 재화 레지스트리(`CurrencyDefinitions`) 신설, `ShopItemDefinitions.CurrencyType` 고정 enum을 `CurrencyId` 참조로 변경, 스테이지 클리어 보상(`StageRewardDefinitions`) 신설 | 체력을 재화로 쓰는 방식은 보류하고, 상점과 스테이지 보상이 같은 재화 정의 하나를 참조해 어떤 표든 재화 종류만 데이터로 바꿔 쓸 수 있게 하기 위함 | GDD §10, Data-Dictionary §18(CurrencyDefinitions 신설)/§19(StageRewardDefinitions 신설)/§20(ShopItemDefinitions, 구 §18)/§21(Validator 오류 코드, 구 §19) |
