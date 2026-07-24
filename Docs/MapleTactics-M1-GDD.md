# MapleTactics M1 GDD

Stage: Planning complete, implementation not started  
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
- 보스는 HP 조건에 따라 PatternId를 바꾼다.
- BT는 PatternStep으로 표현하기 어려운 요구가 확인된 후에만 도입한다.
- 적은 `TURN_TO_PLAYER` 포함 여부로 성격이 갈린다 — 포함하면 플레이어 위치를 따라 방향을 바꾸는 추적형, 빼면 `DefaultFacing`을 계속 유지하는 고정 방향형이다.
- 이동도 같은 원리다 — `MOVE_TOWARD`/`MOVE_AWAY`는 플레이어 상대 위치에 반응하고, `MOVE_FIXED_FACING`은 플레이어 위치와 무관하게 현재 Facing 방향으로만 이동한다.
- 스테이지는 초기 배치(Wave 0)를 EnemyId, CellIndex, Facing, WaveIndex로 정의한다.
- 초기 배치 외 후속 웨이브는 `EnemySpawnPools`에서 가중치로 뽑아 좌우 빈 칸에 채우며, 직전 웨이브 전멸 시 다음 웨이브가 시작된다.
- 웨이브 등장 칸 선택은 RunSeed+StageIndex+WaveIndex 기반 결정적 규칙을 따른다.
- 스테이지는 AugmentPoolId를 데이터로 정의한다.

## 7. 증강 원칙

- 각 스테이지 완료 후 3개 후보 중 하나를 선택한다.
- 후보는 RunSeed와 StageIndex에서 결정적으로 생성한다.
- 증강은 Trigger + Condition + Effect 조합이다.
- Unique, StackAdd, StackRefresh, ExclusiveGroup 정책을 지원한다.
- 이벤트 무한 재귀를 막기 위해 SourceTag와 MaxDepth를 둔다.

## 8. MSW 구현 결정

| 시스템 | MSW 구현 |
|---|---|
| 전투 세션 | 맵 엔티티 `BattleSessionComponent` |
| 전투 격리 | 플레이어당 Instance Room/Instance Map |
| 플레이어 런 상태 | 플레이어 엔티티 `PlayerRunStateComponent` |
| 정적 데이터 | UserDataSet + CSV |
| UI | `.ui` + UIBuilder + ClientOnly Logic |
| 적/플레이어 엔티티 | `.model` + ModelBuilder |
| 맵 배치 | `.map` + MapBuilder |
| 전투 이벤트 | `@Event extends EventType` |
| 무상태 규칙 | `@Logic` Resolver/Router |
| 권장 맵 타입 | SideViewRectTile(2) |

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
- 메타 진행, 상점, 과금, 랭킹은 M1 코어 루프 이후로 미룬다.

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
