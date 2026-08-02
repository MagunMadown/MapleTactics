# MapleTactics 현재 개발 현황

기준일: 2026-08-03
기준 브랜치: `codex/battle-core-variable-queue`

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

## 2. 영역별 상태

| 영역 | 상태 | 팀 작업 가능 여부 |
|---|---|---|
| 전투 Turn·행동 Queue | 구현·회귀 검증 완료 | 가능 |
| 논리 Cell 이동·방향·점유 | 구현·회귀 검증 완료 | 가능 |
| Skill·Effect·Target Resolver | 데이터 기반 최소 규격 완료 | 가능 |
| 적 Intent·Pattern Runner | 다중 적과 준비/실행 상태 구현 | 가능 |
| Wave·강제 증원 | 전멸/턴/시간 조건 구현 | 가능 |
| 적 Drop·Stage Reward | 재화·소모품 지급과 중복 방지 구현 | 가능 |
| Job·Augment | 직업 1종과 최소 패시브 파이프라인 구현 | 조건부 가능 |
| Node Graph·Run Flow | 전투→상점→런 완료 구현 | 가능 |
| Run Shop | 데이터 상품, 서버 구매, 종료/건너뛰기 구현 | 가능 |
| 콘텐츠 전체 Validator | 시작 Gate와 행 단위 오류 계약 구현 | 가능 |
| 최종 전투/상점/지도 UI | DTO만 제공 | UI 팀 작업 필요 |
| EVENT·REST 소비기 | Handler만 존재 | 미구현 |
| StageId→MapId Adapter | 계약만 존재 | 미구현 |
| Instance Map 정책 | 미확정 | 합의 필요 |
| 보스 Phase | 미구현 | 후속 작업 |
| 증강 3택·4직업 | 미구현 | 후속 작업 |
| 저장·재접속 | 미구현 | 후속 작업 |

## 3. 현재 실제 콘텐츠 수

마지막 전체 검증 로그 기준:

- Stage: 1
- Skill: 9
- Skill Effect Step: 9
- Job: 1
- Augment: 1
- Node Graph: 1
- Enemy Pattern: 4
- Stage Reward: 1
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

1. 최종 UI 담당자에게 Battle/Run/Shop DTO 인계
2. EVENT와 REST 소비기를 `CompleteCurrentContent()` 규격으로 구현
3. StageId→MapId Adapter와 Instance Map 정책 확정
4. 증강 후보 Pool·충돌·3택 서버 검증
5. 보스 Phase와 두 번째 Stage 데이터 제작
6. Seed+CommandLog 재현과 저장 경계 추가

상세 체크리스트는 [`../MapleTactics-M1-Implementation-Plan.md`](../MapleTactics-M1-Implementation-Plan.md)를
기준으로 한다.
