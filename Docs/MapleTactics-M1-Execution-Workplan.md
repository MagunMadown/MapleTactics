# MapleTactics M1 실행 작업계획

상태: 구현 착수 전  
기준 문서: 전투 시스템 핸드북 v1.1, M1 GDD, Architecture Review, Implementation Plan, Data Dictionary, Phase 0  
목표: MSW에서 실제로 검증 가능한 순서로 수직 슬라이스를 구현하고, 이후 콘텐츠를 데이터 조립으로 확장한다.

## 1. 문서 검토 결론

핸드북의 핵심 방향은 프로젝트와 잘 맞는다.

- 논리 상태를 원본으로 두고 Entity/Transform은 표현 계층으로 제한한다.
- Command -> Event -> Resolver -> State -> View 흐름을 공통 경로로 사용한다.
- 타일 큐는 타일마다 현재 보드에서 타깃을 다시 계산한다.
- 적/직업/스테이지/증강 차이는 가능한 한 Definition 조합으로 표현한다.
- 새 코드가 필요한 경계는 새로운 원시 Action, Effect, Target, Condition이다.
- 고정 Seed와 CommandLog로 상태와 EventLog의 결정론을 검증한다.

다만 핸드북의 일반 Lua 예제는 개념 예시로만 사용한다. 실제 구현은 다음 MSW 규칙으로 치환한다.

| 핸드북 표현 | MSW 구현 |
|---|---|
| 일반 Lua 객체/Contract 테이블 | `@Component`, `@Logic`, `@Struct`, 명시적 메서드 계약 |
| 전역 Manager/Service | 맵 수명 `BattleSessionComponent` 또는 무상태 `@Logic` |
| 문자열 이벤트 테이블 | 타입이 있는 `@Event`와 서버/클라이언트 RPC 경계 |
| 런타임 Definition 테이블 | UserDataSet + CSV를 읽어 만든 읽기 전용 카탈로그 |
| Registry 객체 생성 | Router/Resolver Logic의 허용 Type 카탈로그와 명시적 디스패치 |
| Transform 기반 판정 | `CellIndex` 기반 논리 판정 후 Body 위치에 단방향 반영 |

## 2. 착수 전 확정 사항

### 2.1 맵과 전투 격리

- 현재 `map01`은 MapleTile(0), Static Map이다.
- M1 권장은 SideViewRectTile(2)와 `SideviewbodyComponent`다.
- 맵 타입 변경은 Maker Hierarchy에서 사용자가 수행한다. `.map`의 `TileMapMode`를 직접 수정하지 않는다.
- 실제 전투는 플레이어당 Instance Room/Instance Map 하나를 원칙으로 한다.
- 전환 후 `refresh`하고 MapBuilder로 `TileMapMode=2`를 다시 확인하기 전에는 유닛 모델과 이동 코드를 확정하지 않는다.

### 2.2 상태 권한

- `BattleSessionComponent`: 현재 전투의 Phase, Turn, BoardState, Unit 조회, Command 잠금과 해결을 단독 소유한다.
- `PlayerRunStateComponent`: Seed, StageIndex, 보유 증강, Pending Offer를 플레이어별로 소유한다.
- Resolver/Router Logic: 무상태 계산과 허용 Type 디스패치만 수행한다.
- UI: ClientOnly이며 Command 요청과 확정 결과 표현만 담당한다.

## 3. 구현 순서

> 2026-07-18 계획 변경: 아래 Gate는 전체 방향을 설명하는 상위 단계다. 실제 구현은 한 Gate를 한 번에 만들지 않는다. 세부 실행 단위는 `MapleTactics-M1-Phase1.md`의 화면 중심 마이크로 Slice를 따른다. 공통 Contract/Registry/Dataset은 실제 두 번째 사용 사례가 생긴 뒤에만 추출한다.

### Gate 0 - MSW 기술 검증

목적: 전체 구조를 쌓기 전에 실패 가능성이 큰 MSW 경계를 증명한다.

1. 맵 타입, Instance Map 정책, 유닛 Body와 위치 이동 API를 확정한다.
2. `CellIndex 0 -> 1 -> 0` 이동을 Body의 월드 위치 반영으로 검증한다.
3. UI 버튼 -> Server Command -> 검증 -> Client 결과 표시 왕복을 만든다.
4. Push 타일 뒤 공격 타일이 변경된 보드에서 타깃을 다시 계산하는지 검증한다.
5. UserDataSet 정상 행과 고의 오류 행을 로드해 타입 변환과 참조 오류를 확인한다.

산출물:

- 최소 테스트용 `.mlua`, 테스트 유닛 `.model`, 테스트 UI
- Phase 0 시나리오별 positive log
- 맵/Body/Instance 정책을 기록한 As-built 문서

통과 조건:

- build/runtime error 0
- 다섯 시나리오 모두 기대값과 실제값 로그 일치
- 실패 시 Phase 1을 시작하지 않고 맵/실행 공간/API 계약부터 수정

### Gate 1 - 전투 코어 수직 슬라이스

목적: UI 없이 Command 배열로 한 전투 턴을 끝까지 처리한다.

구현:

- `BattleSessionComponent`, Phase, Turn, `IsResolving`, `ClientSequence`
- BoardState와 UnitRuntime의 CellIndex/HP/Facing
- Move, Turn, QueueTile, ExecuteQueue Command
- 타입이 있는 핵심 BattleEvent와 순차 Event Queue
- TargetResolver, MovementResolver, EffectRouter
- Damage, Push, Death, Cooldown 원시 효과

대표 시나리오:

`Move -> Queue normal -> Queue FreePlay -> Execute Push -> Execute Attack -> EnemyPhase -> Cleanup`

통과 조건:

- 상태 변경 지점이 Resolver/API로 제한됨
- 각 타일 뒤 이벤트가 완전히 해결된 뒤 다음 타일 실행
- 고정 입력을 두 번 실행했을 때 State/EventLog 동일

### Gate 2 - 데이터 카탈로그와 검증기

목적: 코드에 콘텐츠 ID 분기를 넣지 않고 타일과 적을 데이터로 조립한다.

구현 순서:

1. Job/Tile/TileEffect 데이터 로더
2. Enemy/Pattern 데이터 로더
3. Stage/Spawn 데이터 로더
4. Schema, Reference, Range, Order, Occupancy Validator
5. 오류에 Dataset/Row/Column/Value/Suggestion 포함

통과 조건:

- 미등록 Type과 참조 ID가 전투 시작 전에 차단됨
- 타일 4종과 일반 적 2종을 기존 Router 수정 없이 추가 가능
- 데이터 순서는 `Seq/Priority/Id`로 안정 정렬되고 `pairs` 순서에 의존하지 않음

### Gate 3 - 적 Intent와 스테이지

목적: 한 스테이지의 시작, 적 행동, 승리까지 데이터로 재현한다.

구현:

- 일반 적 `EnemyPatternRunnerComponent`
- Intent 생성과 Client 전송, Intent HUD
- StageDefinition/Spawn/Rule/Victory 조립
- 보스는 Pattern + HP Phase부터 구현하고 BT는 실제 분기 요구가 확인된 경우에만 도입

통과 조건:

- Intent 표시와 실제 Range/Action 일치
- 일반 적 2종과 보스 1종이 Definition/Pattern으로 동작
- 스테이지 전용 Manager나 EnemyId별 분기 없음

### Gate 4 - 증강 3택 수직 슬라이스

목적: 승리 후 결정적 후보 생성, 서버 선택 검증, 다음 전투 적용을 완성한다.

구현:

- `AugmentDefinition`, Effect, Pool, Conflict 데이터
- `AugmentOfferGenerator`, PoolResolver, SelectionService
- RunSeed + StageId + OfferIndex 기반 결정적 RNG
- Pending Offer 저장과 재복원 구조
- Trigger/Condition/Effect 적용과 SourceTag/MaxDepth 안전장치
- 증강 선택 Popup ViewModel

우선 구현 증강:

- Weapon 피해 +1
- 첫 이동 턴 미소비
- 밀치기 충돌 추가 피해

통과 조건:

- 같은 Seed/Stage/OfferIndex에서 동일 후보
- 후보 외 ID, 중복 선택, SelectCount 초과가 서버에서 거절됨
- 중첩 한도와 ExclusiveGroup이 후보 필터에 반영됨
- 활성화 전/후 값이 positive log로 남음

### Gate 5 - 콘텐츠 확장과 제작자 인수 테스트

목적: 코어 개발자가 아닌 작업자가 템플릿과 데이터만으로 콘텐츠를 추가한다.

목표 수량:

- 직업 4종
- 일반 적 2종 이상, 보스 1종
- 스테이지 3개
- 공격 타일 8개 이상
- 증강 12개 이상

통과 조건:

- 기존 원시 Type 조합의 신규 콘텐츠는 데이터/모델/UI 조립만 변경
- 00_Core와 01_Combat에 콘텐츠 ID 분기가 추가되지 않음
- 전체 Validator와 대표 Scenario 회귀 테스트 통과

### Gate 6 - 연출, 저장, 출시 준비

목적: 기능 검증을 플레이 가능한 품질로 마감한다.

- BattleEvent 기반 애니메이션, 피격, 사망, 사운드, 카메라 연출
- 유효한 SpriteRUID/효과 RUID 적용
- RunState 저장 시 DataStorage 비용을 고려한 캐시/dirty/debounce 정책 적용
- 재접속, 맵 이탈, 중복 요청, 스폰/파괴 중간 상태 테스트
- 콘텐츠 카탈로그, 변경 로그, Definition 버전/마이그레이션 정책 작성

## 4. 첫 실행 배치

첫 구현 배치는 Gate 0만 수행한다.

| 순서 | 작업 | 완료 증거 |
|---:|---|---|
| 1 | 사용자가 `map01`을 SideViewRectTile로 전환 | MapBuilder `TileMapMode=2` |
| 2 | Instance Map 또는 1인 제한 정책 확정 | 설정값과 문서 기록 |
| 3 | 테스트 유닛과 Cell 이동 작성 | 0->1->0 expected/actual 로그 |
| 4 | 테스트 버튼 Command 왕복 | 정상/중복/위조 요청 로그 |
| 5 | Push->Attack 큐 재타깃 | 타일별 target 로그 |
| 6 | 테스트 UserDataSet 로드/검증 | 정상 행과 MissingReference 로그 |
| 7 | 통합 검증 | build/runtime 0 + positive log 묶음 |

## 5. 매 작업 공통 완료 정의

- 구현 전 `.d.mlua`에서 실제 API 서명과 ExecSpace를 확인한다.
- `.mlua`는 `RootDesk/MyDesk` 기능 폴더에 두고 `.codeblock`은 수정하지 않는다.
- `.model`, `.map`, `.ui`는 각 Builder를 사용한다.
- 동적 엔티티 Body는 확정된 TileMapMode와 일치시킨다.
- `SpawnByModelId` parent는 `self.Entity.CurrentMap` 등 유효한 맵 엔티티다.
- 시각 엔티티의 SpriteRUID는 비어 있지 않다.
- `stop -> clear_logs -> refresh -> build logs -> play -> runtime logs -> stop` 순서로 검증한다.
- 오류가 없다는 사실만으로 PASS 처리하지 않고 핵심 분기와 값의 positive log를 남긴다.

## 6. 즉시 필요한 사용자 결정

구현 착수 전 다음 두 항목만 확정하면 된다.

1. `map01`을 권장안인 SideViewRectTile(2)로 전환할지 여부
2. 전투 격리를 Instance Room/Instance Map으로 할지, M1 동안 월드 최대 인원을 1명으로 제한할지 여부

권장안은 SideViewRectTile(2) + 플레이어당 Instance Map이다. 1차원 셀 기반 측면 전투와 Body/타일 좌표 대응이 단순하고, 이후 사용자별 RunState가 섞이지 않는다.
