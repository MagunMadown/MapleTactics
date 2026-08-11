# MapleTactics 현재 개발 현황

기준일: 2026-08-08
기준 브랜치: `feat/battle-new-enemy-logic`

## 1. 현재 도달한 수직 슬라이스

현재 백엔드 규격은 다음 한 사이클을 실행할 수 있다.

```text
새 Run
→ 직업 적용
→ Stage 1 전투
→ 이동·회전·행동 큐 실행
→ 적 Intent·Wave 처리
→ 승리 보상과 적 Drop 회수
→ 다음 Node 선택
→ Run Shop 진입
→ 구매 또는 건너뛰기
→ SHOP Node 완료
→ RUN_COMPLETED
```

최종 UI와 연출은 아직 제작 대상이다. 현재 HUD와 Snapshot은 기능 검증 및 UI 연동 계약이다.

주의: 1-1~1-4 전투 데이터는 준비됐지만 현재 통합 Node Graph에는 1-1만 연결돼 있다.
1-2~1-4의 정식 Run 진입은 REST/증강 담당자의 Node 연결 이후 가능하다.

## 2. 영역별 상태

| 영역 | 상태 | 팀 작업 가능 여부 |
|---|---|---|
| 전투 Turn·행동 Queue | 구현·회귀 검증 완료 | 가능 |
| 논리 Cell 이동·방향·점유 | 구현·회귀 검증 완료 | 가능 |
| Skill·Effect·Target Resolver | 데이터 기반 최소 규격 완료 | 가능 |
| 적 Intent·Pattern Runner | 적별 동시 계획·행동 Queue·Trait 최소 규격 회귀 완료 | 가능 |
| Wave·강제 증원 | 전멸/턴/시간 조건 구현 | 가능 |
| 적 Drop·Stage Reward | 재화·소모품 지급과 중복 방지 구현 | 가능 |
| Job·Augment | 직업 1종과 최소 패시브 파이프라인 구현 | 조건부 가능 |
| Node Graph·Run Flow | 전투→상점→런 완료 구현 | 가능 |
| Region·Stage Identity | Region/StageIndex/StageType 명시 규격 및 ID 파싱 제거 완료 | 가능 |
| Region 1 일반 전투 | 1-1~1-3 Stage/Wave/Pool 및 근접·원거리 적 데이터 완료 | 가능 |
| Region 1 보스 전투 | 1-4 보스, 2 Phase, 예고→범위 공격 규격·데이터 완료 | 가능 |
| Run Shop | 데이터 상품, 서버 구매, 종료/건너뛰기 구현 | 가능 |
| 콘텐츠 전체 Validator | 시작 Gate와 행 단위 오류 계약 구현 | 가능 |
| 최종 전투/상점/지도 UI | DTO만 제공 | UI 팀 작업 필요 |
| EVENT·REST 소비기 | Handler만 존재 | 미구현 |
| StageId→MapId Adapter | 계약만 존재 | 미구현 |
| Instance Map 정책 | 미확정 | 합의 필요 |
| 보스 Phase | HP 임계 전환·Pattern 교체·UI DTO 최소 규격 완료 | 확장 가능 |
| 증강 3택·4직업 | 미구현 | 후속 작업 |
| 저장·재접속 | 미구현 | 후속 작업 |

## 3. 현재 실제 콘텐츠 수

마지막 전체 검증 로그 기준:

- Stage: 4
- Region: 1
- Skill: 11
- Skill Effect Step: 11
- Job: 1
- Augment: 1
- Node Graph: 1
- Enemy Pattern: 7
- Boss Phase Owner: 1
- Stage Reward: 4
- Shop: 1
- Shop Entry: 2

## 4. 마지막 Maker 검증

검증 환경은 `map01`, `TileMapMode=0` MapleTile이다. 전투 유닛 이동은 물리 이동이 아니라
서버 권위 논리 Cell Snapshot 방식이다.

- Build Console: Info 247, Warning 0, Error 0
- Runtime Warning/Error: 0
- Content Integrity Gate: `VALID`
- 상점 구매 없이 건너뛰기: `RUN_COMPLETED`
- 물약 구매: Gold `5 → 3`, `potion_hp_small` 1개 지급
- 동일 종료 요청: `DUPLICATE_CONTENT_COMPLETION_IGNORED`
- 종료 뒤 추가 종료: `SHOP_NOT_OPEN`
- BATTLE 완료 우회: `CONTENT_TYPE_NOT_COMPLETABLE`
- Client Run/Shop DTO 동기화: 통과
- 적별 동시 계획: Turn 1의 생존 적 `2/2`를 플레이어 행동 전에 고정
- 계획 불변 실행: 첫 적 이동 뒤 두 번째 적의 고정 Action을 재판정 없이 실행
- Client 적 계획 DTO: `PER_ENEMY_FROZEN_PLAN_V1`, `count=2`, `parsed=2`
- `HEAVY`: 밀치기 결과 `PUSH_BLOCKED_HEAVY_TRAIT`, Cell `4→4`
- `DOUBLE_STRIKE`: 동일 Pattern Step의 행동 Queue `ActionCount=2`, Index `1→2`
- 이번 변경 Build Console: Info 262, Warning 0, Error 0
- 이번 변경 Runtime Warning/Error/Fatal: 0
- Region/Stage 규격: `region_01`, `region_01_stage_01`, `StageIndex=1`, `StageType=NORMAL` 로드 통과
- Region 1 일반 Stage: 1-1 2 Wave, 1-2 2 Wave, 1-3 3 Wave 전체 Validator 통과
- 공용 원거리 공격: 3칸 타게팅 후 `enemy_ranged_shot`, 플레이어 HP `10→8` 실행 통과
- 1-4 보스: `OPENING → ENRAGED`, 옛 계획 `PATTERN_SUPERSEDED`, 1턴 예고 후 범위 피해 실행 통과

## 5. 지금 병렬로 진행 가능한 작업

### 콘텐츠 개발자

- 기존 타입을 조합한 Skill, Enemy Pattern, Wave, Drop, Shop Entry 추가
- CSV 변경 후 전체 Validator와 대표 런타임 경로 확인
- 새 원시 타입이 필요하지 않으면 전투 Session 수정 금지

### UI 개발자

- `GetBattleUiState()` 기반 전투 HUD
- `GetLocalRunFlowUiState()` 기반 Node/전환 화면
- `GetLocalShopUiState()` 기반 Run Shop
- UI는 가격·피해·보상·다음 Node를 직접 계산하지 않음

### 전투 개발자

- 기존 Resolver/Executor/Pattern Runner를 통한 원시 행동 확장
- 상태 변경은 상태 소유자 API를 통해 수행
- Session에 Content ID별 조건문을 추가하지 않음

## 6. 다음 우선순위

1. 적별 동시 계획·Trait Queue Battle DTO를 UI 담당자에게 인계
2. `EXPLOSIVE`, `REACTIVE_SHIELD` Trait 실행기 구현
3. EVENT와 REST 소비기를 `CompleteCurrentContent()` 규격으로 구현
4. StageId→MapId Adapter와 Instance Map 정책 확정
5. 증강 후보 Pool·충돌·3택 서버 검증
6. Region 1 Stage/Node/REST 연결을 다른 팀 데이터와 통합 검증
7. Seed+CommandLog 재현과 저장 경계 추가

상세 체크리스트는 [`../MapleTactics-M1-Implementation-Plan.md`](../MapleTactics-M1-Implementation-Plan.md)를
기준으로 한다.
