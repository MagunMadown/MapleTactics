# Region 05 노틸러스 구현 계획과 현재 상태

기준일: 2026-09-04

노틸러스는 지역 목록상 `region_05`다. `RegionOrder=5`는 표시·정렬 값이며 난이도나
진행 순서를 코드에서 파싱하는 값이 아니다. 월드 지도 연결은 Node 담당자가
`NodeDefinitions.NextNodeIds`로 엘리니아 → 노틸러스 → 슬리피우드 경로를 구성한다.

## 현재 상태

- ✅ `region_05`와 5-1~5-3 Stage/Wave/Route/Reward 데이터 추가
- ✅ `nautilus_battle.map` 항구 외부 화면과 기존 전투 규격 Maker 검증
- ✅ 파란 리본돼지·불가사리·해파리·클랑 모델/패턴/스킬/드롭 추가
- ✅ `nautilus_interior_01.map` 화물칸 생성 — Maker 등록·화면·5-2 Wave 1 스폰 검증
- ✅ `nautilus_interior_02.map` 침수 기관실 생성 — Maker 등록·화면·5-3 Wave 1 스폰 검증
- ✅ 킹크랑 전용 모델·2 Phase·중단 가능 버블 캐논 데이터/공용 로직 구현
- ✅ `nautilus_boss.map`과 5-4 Stage/Wave/Spawn Pool/Route/Reward/Drop 연결
- 🟡 5-4 직접 플레이 밸런스와 바닥 전조·Queue 아이콘 시각 품질 검증
- ✅ 엘리니아 보스 보상 노드에서 노틸러스 5-1~5-4 Node 체인 연결

## ID 계약

| 항목 | 값 |
|---|---|
| Region | `region_05` |
| 첫 Stage | `region_05_stage_01` |
| 일반전 물리 맵 | `nautilus_battle` |
| 첫 Wave Table | `region_05_stage_01_waves` |
| 첫 Pool | `region_05_stage_01_pool` |
| 첫 적 | `region_05_blue_ribbon_pig` |
| 첫 적 모델 | `region05blueribbonpig` |
| 보스 Stage | `region_05_stage_04` |
| 보스 물리 맵 | `nautilus_boss` |
| 보스 Spawn Pool | `region_05_stage_04_boss_pool` |
| 보스 적/모델 | `region_05_king_clang` / `region05kingclang` |

ID의 숫자나 단어를 `match`, `find`, `sub`로 해석하지 않는다. 소속·순서·Type은 각각
`RegionId`, `StageIndex`, `StageType` 열을 사용한다.

## 5-1 콘텐츠

- 6 Cell, 플레이어 시작 Cell 2, Queue 기본 3칸
- Wave 3개, `1 → 1 → 2마리`로 총 4마리, 최대 동시 2마리
- 파란 리본돼지 HP 7, 피해 2
- 행동: 공격 Tile 보유 → 추적·회전 → 전방 1칸 돌진 → 다음 행동 주기의 공통 후퇴
- 처치 드롭: Gold 2~3, 소형 회복 물약 15%
- Stage 클리어 보상: Gold 10

## 5-2 콘텐츠

- 물리 맵: `nautilus_interior_01` (노틸러스 화물칸)
- Wave 4개, `1 → 2 → 2 → 2마리`로 총 7마리, 최대 동시 2마리
- 노란 불가사리: HP 4, 전방 1칸 근접 공격
- 해파리: HP 6, 전방 최대 2칸 원거리 공격, 재사용 대기 3
- 해파리 Idle/Move/Hit/Death는 원본 리소스 팩의 `stand/move/hit1/die1`을 각각 사용한다.
- Spawn Pool 가중치: 노란 불가사리 3, 해파리 1이며 해파리는 Wave 2부터 등장
- Stage 클리어 보상: Gold 12

## 5-3 콘텐츠

- 물리 맵: `nautilus_interior_02` (침수 기관실)
- Wave 4개, 총 8마리, 최대 동시 3마리
- 화난 불가사리: HP 5, 인접 시 1턴 예고 후 피해 2
- 쿨한 해파리: HP 7, 전방 최대 2칸 원거리 공격, 재사용 대기 4
- 클랑: HP 7, 전방 1칸 근접 공격
- Spawn Pool 가중치: 화난 불가사리 3, 쿨한 해파리 1, 클랑 2
- Stage 클리어 보상: Gold 15

## 5-4 콘텐츠

- 물리 맵: `nautilus_boss` (킹크랑이 침입한 침수 선내)
- 단일 Wave, 킹크랑 1마리, 최대 동시 1마리
- 킹크랑: HP 26, 기본 피해 3, HP 50%에서 Phase 2 전환
- 행동: 집게 근접 공격, 공통 후퇴, 중단 가능한 버블 캐논 캐스팅
- Phase 1 버블 캐논은 플레이어 공격 1회 적중, Phase 2는 2회 적중으로 중단
- 처치 드롭: Gold 7~10, 소형 회복 물약 1개
- Stage 클리어 보상: Gold 20
- 직접 Play 테스트를 위해 맵 루트 `BattleSessionComponent`의 `StageId`는
  `region_05_stage_04`, `AutoStartPrototypeBattle`은 `true`로 설정한다. Node 경유 진입 시에는
  준비된 Stage 정보가 우선된다.

5-2와 5-3의 원거리 적 비중은 낮게 시작한다. 초반에는 근접 적을 처리하는 동안 원거리 예고를
읽는 경험이 목적이며, 2칸 밖에서 일방적으로 공격받는 구성을 만들지 않는다.

## 물리 맵 계약

Region 05의 네 전투 맵은 검증된 전투 구조를 MapBuilder로 복제한다. 다음 Entity
이름과 컴포넌트 계약은 유지한다.

- 맵 루트 `BattleSessionComponent`
- `BattleBoardState`, `BattleTurnState`, `BattleWaveState`
- `BattleCameraAnchor`
- `BattleCell1`~`BattleCell6`
- `SpawnLocation`

실제 전투 맵은 `TileMapMode=0` MapleTile이다. 전투 유닛은 물리 자유 이동 대신 서버 권위
Cell Snapshot으로 이동한다. 노틸러스에서도 맵 타입을 바꾸지 않는다.

## Maker 단독 Stage 테스트

로비와 Node를 거치지 않고 노틸러스 전투만 확인할 때는 원하는 물리 맵을 Maker에서 연 뒤
바로 Play한다. 네 맵의 루트 `BattleSessionComponent`에는 다음 테스트 설정이 들어 있다.

| 물리 맵 | 자동 시작 Stage |
|---|---|
| `nautilus_battle` | `region_05_stage_01` |
| `nautilus_interior_01` | `region_05_stage_02` |
| `nautilus_interior_02` | `region_05_stage_03` |
| `nautilus_boss` | `region_05_stage_04` |

`AutoStartPrototypeBattle=true`인 단독 Play는 단순히 Wave만 생성하지 않는다. 정식 전투 진입과
동일한 `NEW_RUN` 초기화 경로를 사용해 직업 HP, 시작 스킬, Queue 크기, Run 인벤토리와 Stage
데이터를 함께 구성한다. 기본 테스트 직업은 `warrior`, Seed는 `5001`이다. 다른 직업을 확인하려면
맵 루트의 `PrototypeTestJobId`를 `mage`, `archer`, `thief`, `pirate` 중 하나로 바꾼다.
Play 직후 Union 프로필이 아직 로딩 중이면 최대 20초 동안 0.25초 간격으로 진입을 재시도하며,
준비되기 전에 HP 100 등의 부분 초기화 상태로 전투를 시작하지 않는다.

Node 담당 경로에서 `BattleEntryState=PREPARED`로 진입한 경우에는 준비된 실제 Run 정보가 항상
테스트 설정보다 우선한다. 따라서 이 설정은 정상 Stage 이동의 직업·HP·재화 상태를 덮어쓰지 않는다.

직접 Maker Play로 자동 시작된 전투에서는 `F8`을 누르면 현재 Stage를 강제로 클리어할 수 있다.
이 기능은 남은 Wave를 건너뛴 뒤 마지막 적을 기존 서버 권위 데미지·사망·승리 경로로 처리하므로
Stage 보상 기록과 다음 Node 준비를 실제 클리어와 동일하게 검증한다. 로비나 Node에서
`BattleEntryState=PREPARED`로 들어온 정상 플레이에서는 서버가 요청을 거절한다.

5-2는 4웨이브까지 노란 불가사리·젤리피쉬 출현 후보를 유지한다 (`MaxWaveIndex=4`). 첫 웨이브는 노란 불가사리만, 2~4웨이브는 가중치 3:1을 사용한다.

현재 진행 연결은 `ellinia_stage_04 → shop_ellinia_nautilus(SHOP) → region_05_stage_01`이며,
이후에도 각 노틸러스 전투 사이의 보상 Node를 거쳐 5-4 보스까지 이어진다.
엘리니아 보스 맵 `ellinia_boss`도 단독 검증을 위해 `StageId=ellinia_stage_04`,
`AutoStartPrototypeBattle=true`로 설정되어 있으므로 해당 맵에서 바로 Play한 뒤 `F8`로 이 연결을
확인할 수 있다.

## 장식 교체 규칙

노틸러스 장식은 `RootDesk/MyDesk/Models/Objects/Nautilus*.model`에서 관리한다. 맵에는
모델 인스턴스와 위치·크기만 둔다. 디자인 담당자는 전투 코드나 `.map` 구조를 수정하지 않고
모델의 `SpriteRUID`를 교체할 수 있다.

- 5-1 항구: 해안 배경, `NautilusDockPlatform`, `NautilusCannon`, `NautilusBarrel`
- 5-2 화물칸: `NautilusInteriorCargoBackdrop`, 흰 금속 테두리·목재 중앙의 `NautilusDeckSurface`
- 5-3 기관실: `NautilusInteriorEngineBackdrop`, 청회색 틴트를 적용한 `NautilusDeckSurface`
- 5-4 보스전: 5-3 선내 구성을 독립 맵으로 복제해 이후 보스 전조·침입 흔적을 별도 수정

내부 전투 바닥은 외부 부두용 목재 지지대나 검은 석재형 발판을 재사용하지 않는다. 노틸러스
선체의 곡선 금속 프레임과 목재 갑판이 함께 보이는 전용 모델을 사용하되, Foothold 좌표는
전투 규격을 유지한다.

5-1에는 외형이 맞지 않는 대체 선박을 배치하지 않는다. 실제 노틸러스호가 화면 밖에 정박한 것처럼
부두·대포·화물만으로 장소를 암시한다. 나중에 정확한 선박 리소스가 확보되면 장식 모델만 추가한다.

중앙 6 Cell, 유닛 머리 위 Queue, 바닥 전조 영역을 가리지 않도록 큰 장식은 좌우 가장자리와
후경에 둔다.

## 다음 구현 순서

1. 중단 가능한 버블 캐논의 바닥 전조·캐스팅 모션·Queue 아이콘 시각 품질 검증
2. 5-2·5-4 전체 Wave 플레이로 진행 시간과 피격 빈도 측정
3. 측정 결과에 따라 일반전 Pool 가중치와 킹크랑 HP·중단 횟수 조정
4. 5-4 이후 다음 Region Node 연결 계약 확정

## 검증 기준

- `[ContentIntegrity] valid regions=2 stages=8 stageMapRoutes=8`
- `[BattleContentGate] valid trigger=SESSION_BEGIN`
- Stage Definition `source=DATASET`
- 파란 리본돼지가 `INSERTING → TRACKING → ATTACK_READY → EXECUTING`으로 동작
- 적 공격 후 공통 후퇴가 같은 적 턴에 즉시 실행되지 않음
- 5-4 단일 보스 Wave와 Victory가 정상 종료
- Region 01 전투 회귀 이상 없음
- Build/Runtime Warning·Error 0

2026-08-30 첫 Refresh에서는 복제 맵의 `EntryKey`가 원본 `map://nautilus_battle`로 남아
`LEA-3015`가 발생했다. 각 맵의 고유 EntryKey로 수정한 뒤 Maker 등록과 이동이 정상화됐다.
5-2는 노란 불가사리 2마리, 5-3은 화난 불가사리 1마리의 Wave 1 스폰까지 직접 검증했다.
2026-09-04에는 `nautilus_boss`를 별도 생성하고 5-4 데이터 연결 및 직접 Play 자동 시작 설정을 추가했다.
