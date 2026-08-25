# MapleTactics M1 Phase 1 - 화면으로 확인하는 기본 전투

상태: 🟡 In progress  
목표: 복잡한 프레임워크를 먼저 만들지 않고, Maker 화면에서 직접 확인할 수 있는 작은 전투 기능을 하나씩 완성한다.  
진행 원칙: 한 Slice를 구현하고 실제 화면과 로그로 검증한 뒤에만 다음 Slice로 넘어간다.

## Skills to reference (this Phase)

- `msw-general`: `platform.md`, 확정 맵 타입의 `platform-*.md`, `workspace.md`, `entity.md`, `authoring.md`, `builder-protocol.md`, `model.md`
- `msw-scripting`: `SKILL.md`, `verify-checklist.md`
- `msw-combat-system`: `SKILL.md`
- `msw-ui-system`: `SKILL.md`, `component-api.md`, `runtime-patterns.md`
- 리소스를 적용할 때: `msw-search`, `msw-sprite-ruid`

## 1. 이 Phase에서 일부러 만들지 않는 것

초기 Slice에서는 다음을 만들지 않는다.

- 범용 Contract/Registry 프레임워크
- 전체 직업·적·스테이지 Definition
- UserDataSet 전체 스키마
- 보스 BT/FSM
- 증강 시스템
- 저장 시스템
- 완성형 애니메이션/사운드

처음에는 한 플레이어, 한 적, 한 공격, 한 스테이지만 하드코딩해도 된다. 같은 종류의 두 번째 사례가 생겼을 때만 공통 인터페이스나 데이터 구조를 추출한다.

## 2. 맵과 화면 기준

- 대상 맵: `map/map01.map`
- 현재 맵: MapleTile(0), `RigidbodyComponent`
- 권장 최종 맵: SideViewRectTile(2), `SideviewbodyComponent`
- 권장 화면: PC 가로 12.8 x 7.2 world units
- 기본 전투 보드: 화면 중앙에 6개 논리 셀
- 현재 초기 배치: Player Cell 1, Enemy Cell 4
- 월드 좌표는 CellIndex에서 계산하고, 판정은 Transform 좌표가 아닌 CellIndex로 한다.

맵 타입 변경은 사용자가 Maker Hierarchy에서 수행한다. 전환 후 `refresh`하고 실제 `TileMapMode`를 다시 확인하기 전에는 이동 Body/API를 확정하지 않는다.

## 3. 진행 규칙

각 Slice는 다음 순서로 끝낸다.

1. 화면 배치 또는 최소 코드를 만든다.
2. 체크리스트를 즉시 `🟡 Implemented (untested)`로 변경한다.
3. `stop -> clear_logs -> refresh -> build logs -> play -> runtime logs -> stop`으로 검증한다.
4. 화면 결과와 positive log가 모두 맞으면 `✅ Tested`로 변경한다.
5. 사용자와 화면을 보며 위치·크기·조작감을 확인한 뒤 다음 Slice로 넘어간다.

## 4. 마이크로 수직 슬라이스

### Slice 0 - 빈 전투 무대와 셀 가이드

- 🟡 상태: Maker verified, user review pending — 기존 발판 위 7개 셀 표식 배치, HUD는 다음 단계
- 화면 결과: 전투 무대, 7개 셀 위치, Player/Enemy 시작 위치 표시가 보인다.
- 최소 구현:
  - 확정된 맵 타입과 Body 기록
  - 셀 중심점 7개를 임시 표식 또는 디버그 오브젝트로 배치
  - 좌측 상단에 `Phase`, `Turn` 텍스트만 배치
- 도입할 최소 인터페이스:
  - `CellToWorld(cellIndex)` 함수 하나
- 아직 하지 않음:
  - 이동, 공격, 실제 적 AI
- 완료 기준:
  - Player Cell 1과 Enemy Cell 5 위치가 한 화면에 보임
  - 셀 간격이 일정하고 PC 화면 안에 모두 들어옴
  - `TileMapMode`, Cell 0/6 월드 좌표 positive log

### Slice 1 - 플레이어와 적 한 명 배치

- 🟡 상태: Maker verified, user review pending — Player 시작점과 Enemy 시각 모델 배치, 런타임 컴포넌트는 다음 단계
- 화면 결과: 플레이어와 적이 지정 셀에 서 있다.
- 최소 구현:
  - 테스트 Player/Enemy 모델 각 1개
  - `CellIndex`, `Facing`, `MaxHp`, `Hp`만 가진 최소 런타임 컴포넌트
  - 유효한 SpriteRUID 또는 명확한 임시 리소스 적용
- 도입할 최소 인터페이스:
  - `PlaceAtCell(entity, cellIndex)`
- 아직 하지 않음:
  - 일반화된 Unit 상속, 적 종류 데이터
- 완료 기준:
  - 두 Entity가 서로 겹치지 않고 정확한 셀에 보임
  - Body가 맵 타입과 일치함
  - 두 Entity의 이름, CellIndex, WorldPosition 로그 일치

### Slice 2 - 한 칸 이동

- 🟡 상태: 이동 코어 Maker verified, UI 버튼·CellIndex 표시 pending
- 화면 결과: 좌/우 키를 누르면 플레이어가 정확히 한 셀 이동한다.
- 최소 구현:
  - `LeftArrow`/`A`, `RightArrow`/`D` 키 입력
  - 보드 범위와 점유만 검사하는 이동 요청
  - 성공 후 CellIndex 변경 및 Body 위치 반영
  - 이동 성공 후 `UnitMovedEvent` 발행 및 구독 로그
  - 이동 중 전투판 중심을 유지하는 카메라 X 오프셋
- 도입할 최소 인터페이스:
  - `TryMove(unitId, direction)`
  - 결과: `Success`, `Reason`, `FromCell`, `ToCell`
- 아직 하지 않음:
  - 좌/우 UI 버튼과 현재 CellIndex 표시
  - 턴 소비, 적 반응, 이동 증강
- 완료 기준:
  - 정상 이동, 보드 밖 이동 거절, 점유 셀 이동 거절
  - UI에 현재 CellIndex 표시
  - expected/actual CellIndex와 WorldPosition 로그 일치

### Slice 3 - 방향 전환

- 🟡 상태: 키보드 방향 전환 코어 구현, UI 버튼 pending
- 화면 결과: `Space` 키로 플레이어가 이동 없이 좌/우를 바라본다.
- 최소 구현:
  - `BattleUnitComponent.Facing`의 `Left`/`Right` 전환
  - `PlayerControllerComponent.LookDirectionX`로 Avatar 방향 표현
  - 성공 후 `UnitTurnedEvent` 발행 및 구독 로그
- 도입할 최소 인터페이스:
  - `TryTurn(unitId)`
- 아직 하지 않음:
  - 방향 전환 UI 버튼
  - 방향별 타깃 규칙 카탈로그
- 완료 기준:
  - 논리 Facing과 화면 방향 일치
  - 두 번 전환하면 원래 방향으로 복귀

### Slice 4 - 인접 기본 공격과 HP

- 🟡 상태: 앞 셀 판정, 고정 피해 3, 적 HP 텍스트, 피격 플래시, 플레이어 기본 공격 모션 구현
- 화면 결과: 공격 버튼을 누르면 바라보는 방향의 바로 앞 적 HP가 감소한다.
- 최소 구현:
  - `F` 키 기본 공격 입력
  - Facing 기준 Front Cell 한 칸의 적을 Hit/Miss로 판정
  - `BasicAttackResolvedEvent` 발행 및 구독 로그
  - 고정 피해 3
  - 적 HP 텍스트 또는 간단한 HP Bar
  - 피격 시 색상 변화나 짧은 플래시 중 하나
- 도입할 최소 인터페이스:
  - `ResolveFrontTarget(sourceId)`
  - `ApplyDamage(sourceId, targetId, amount)`
- 아직 하지 않음:
  - HP Bar 형태의 게이지
  - 별도 무기 모션과 리소스 이펙트
  - 공격의 턴 소비
  - Effect Registry, 치명타, 방어력, 상태 이상
- 완료 기준:
  - 앞에 적이 있을 때만 피해 적용
  - 반대 방향 공격은 Miss
  - 모델 HP와 표시 HP 일치
  - 공격/타깃/피해 전후 positive log

### Slice 5 - 사망과 전투 리셋

- 🟡 상태: HP 0 사망·승패·Reset Maker 검증 완료, 사용자 화면 검토 pending
- 화면 결과: HP가 0이 되면 적이 사라지거나 사망 상태로 바뀌고 승리 문구가 표시된다.
- 최소 구현:
  - HP 0 Clamp
  - Enemy Died 처리
  - `VICTORY` 텍스트와 Reset 버튼
- 도입할 최소 인터페이스:
  - `HandleUnitDied(unitId, cause)`
  - `ResetBattle()`
- 아직 하지 않음:
  - 보상, 다음 스테이지, 드롭
- 완료 기준:
  - 중복 사망 처리 없음
  - Reset 후 시작 위치와 HP 복원
  - 사망과 승리 로그가 한 번씩만 출력

### Slice 6 - 적 Intent와 한 번의 적 행동

- 🟡 상태: 최소 런타임 Intent Maker 검증 완료 — 거리 기반 이동/인접 공격 구현, Intent UI pending
- 화면 결과: 적 머리 위 또는 HUD에 다음 행동이 보이고, `적 행동` 버튼을 누르면 실행된다.
- 최소 구현:
  - Intent 하나: 플레이어 쪽으로 한 칸 이동 또는 인접 공격
  - Intent 아이콘 대신 초기에는 텍스트 허용
  - 적도 플레이어와 같은 `TryMove`/`ApplyDamage` 사용
- 도입할 최소 인터페이스:
  - `BuildEnemyIntent(enemyId)`
  - `ExecuteIntent(intent)`
- 아직 하지 않음:
  - Pattern 데이터, BT, 다중 적 우선순위
- 완료 기준:
  - 표시한 Intent와 실제 행동이 일치
  - 적이 별도 HP/Position 수정 경로를 만들지 않음

### Slice 7 - 플레이어 행동 뒤 적 행동이 이어지는 한 턴

- 🟡 상태: 턴 코어와 최소 큐 HUD Maker 검증 완료 — 공통 행동 큐, 입력 잠금, 적 행동, Turn 증가와 상태 표시 구현; 사망/Reset pending
- 화면 결과: 플레이어가 이동/전환/공격하면 적 행동과 Turn 증가가 자동으로 이어진다.
- 최소 구현:
  - Phase: `PLAYER_INPUT`, `ENEMY_ACTION`, `CLEANUP`
  - 행동 처리 중 입력 잠금
  - 이동/전환/기본 공격은 모두 한 턴 소비
- 도입할 최소 인터페이스:
  - `SubmitPlayerAction(actionType, arg)`
  - `CompletePlayerAction(consumesTurn)`
- 아직 하지 않음:
  - FreePlay, 여러 칸 타일 큐, 네트워크 재접속
- 완료 기준:
  - 입력 중복 실행 없음
  - Phase 순서와 Turn 값이 HUD/로그에서 일치
  - 플레이어 사망 시 `DEFEAT` 표시와 Reset 가능

### Slice 8 - 공격 타일 선택·등록과 실행

- 🟡 상태: 두 공격 선택과 가변 용량 타일 큐 Maker 검증 완료, 사용자 화면 검토 pending
- 화면 결과: `기본 베기`와 `강한 베기`를 기본 2칸 큐에 순서대로 넣고 실행한다.
- 최소 구현:
  - Tile Runtime: `basic_slash`, `heavy_slash`
  - 기본 큐 용량 2칸, `TileQueueCapacity`로 확장
  - 등록/순차 실행/전체 비우기 UI
- 도입할 최소 인터페이스:
  - `TryQueueTile(tileInstanceId)`
  - `ExecuteQueuedTile(tileInstanceId)`
- 아직 하지 않음:
  - 타일 Dataset, 여러 Target/Effect 타입, 쿨다운
- 완료 기준:
  - 빈 큐/가득 찬 큐와 용량 3 확장 검증
  - 각 타일 실행 후 기존 Slice 4의 타깃/피해 경로 재사용
  - 큐 HUD와 실제 큐 상태 일치

### Slice 9 - 두 칸 큐와 재타깃

- 🟡 상태: 밀치기 타일과 두 칸 순차 큐 재타깃 Maker 검증 완료, 사용자 화면 검토 pending
- 화면 결과: `밀치기 -> 검` 두 타일을 순서대로 실행하고, 두 번째 공격이 밀친 뒤의 현재 위치에서 타깃을 다시 찾는다.
- 최소 구현:
  - Push 효과 한 개
  - 큐 최대 2칸
  - 타일별 `Resolve -> Apply -> Death/Victory check` 완료 후 다음 타일 실행
- 도입할 최소 인터페이스:
  - `ExecuteEffect(effectType, context)`는 `DAMAGE`와 `PUSH` 두 종류만 지원
- 아직 하지 않음:
  - 범용 Registry, 8개 타일, 증강
- 완료 기준:
  - 큐 시작 시 전체 타깃을 미리 고정하지 않음
  - Push 전/후 Cell과 두 번째 TargetId 로그 확인
  - 동일 시작 상태와 입력에서 동일 결과

### Slice 10 - 두 번째 사례가 생긴 부분만 인터페이스화

- 🟡 상태: Implemented (core paths tested) — Maker refresh/build 통과, `DAMAGE`/`PUSH` 실제 분기 확인. 경계 밀치기 회귀 검증은 남음
- 화면 결과: 기존 플레이 결과는 변하지 않지만 새 타일 하나를 작은 설정값으로 추가할 수 있다.
- 리팩터링 대상:
  - `DAMAGE`, `PUSH`가 생겼으므로 Effect Router 추출
  - Front와 다른 타깃 규칙이 실제로 필요할 때 Target Resolver 추출
  - 타일이 3개 이상이 되면 Tile Definition 구조 도입
  - 적 Intent가 2개 이상이 되면 Pattern Step 구조 도입
- 원칙:
  - 사용 사례가 하나뿐인 것은 인터페이스로 만들지 않는다.
  - 콘텐츠 ID별 `if`가 두 군데 이상 반복될 때 Router/데이터로 이동한다.
- 완료 기준:
  - 기존 Slice 0~9 회귀 테스트 통과
  - 새 타일 하나가 기존 전투 Manager 수정 없이 추가됨

### Slice 10.5 - 적 Intent 준비·유지·실행 분리

- ✅ 상태: Tested — Maker refresh/build 및 `접근 준비 → 기본 베기 준비 → 밀치기 → 준비한 베기 Miss → 다음 Intent 준비` 런타임 검증 완료
- 화면 결과: 플레이어 턴 동안 적의 다음 행동이 HUD에 미리 보이고, 밀치기·이동·방향 전환 후에도 적이 행동 종류를 다시 고르지 않고 예고한 행동을 실행한다.
- 목적:
  - 현재 `BuildEnemyIntent → 즉시 실행` 구조를 `Prepare → Hold → Execute`로 분리
  - 쇼군 쇼다운처럼 위치 조작으로 이미 준비된 공격의 명중 셀을 바꿀 수 있게 함
  - 최종 `EnemyPatternSteps` 표를 붙일 때 전투 코어를 다시 뜯지 않는 런타임 계약 확정
- 최소 상태:
  - `EMPTY`: 준비된 Intent 없음
  - `PREPARED`: ActionType/TileId/PatternId/StepIndex가 고정되어 HUD 표시 가능
  - `EXECUTING`: 저장된 Intent 실행 중이며 새 Intent 생성 금지
- 최소 인터페이스:
  - `PrepareEnemyIntent(enemyId)`
  - `GetPreparedEnemyIntent(enemyId)`
  - `ExecutePreparedEnemyIntent(enemyId)`
  - `CompletePreparedEnemyIntent(enemyId, success, reason)`
- 실행 규칙:
  - Intent 준비 시 `ActionType`, `TileId`, `PatternId`, `StepIndex`, `PreparedTurn`만 고정한다.
  - `TargetId`와 목표 Cell은 고정하지 않는다. 공격 실행 시 현재 CellIndex/Facing과 Tile Target 규칙으로 다시 판정한다.
  - 밀치기 후에도 `BuildEnemyIntent`를 다시 호출하지 않는다. 준비된 공격이 현재 위치에서 닿지 않으면 `MISS_EMPTY` 또는 `OUT_OF_RANGE`로 끝난다.
  - 준비된 Intent가 없는 적만 다음 Pattern Step을 선택한다.
  - 적 행동 완료 후에만 StepIndex를 전진하고 다음 플레이어 턴용 Intent를 준비한다.
- 표 전환 계약:
  - 프로토타입에서는 한 개의 하드코딩 Pattern으로 위 상태 전이를 먼저 검증한다.
  - Phase 2에서 `EnemyDefinitions.PatternId`와 `EnemyPatternSteps` 행을 로드해 같은 `PreparedIntent` Snapshot을 생성한다.
  - 콘텐츠별 `EnemyId` 분기는 `BattleSessionComponent`에 추가하지 않는다.
- 협업 경계:
  - 전투 코어 개발자: Intent 상태 전이와 실행 순서만 소유
  - 콘텐츠 개발자: `EnemyDefinitions`/`EnemyPatternSteps`의 행과 기존 ActionType 조합만 수정
  - UI 개발자: 읽기 전용 Prepared Intent DTO/Event만 소비하고 AI 판정을 복제하지 않음
- 아직 하지 않음:
  - 실제 UserDataSet/CSV 로더, 다중 적 Intent 순서, Telegraph 아이콘 리소스
- 완료 기준:
  - 적이 `EXECUTE_TILE/basic_slash`를 준비한 뒤 밀려나도 `MOVE_TOWARD`로 재계산하지 않음
  - 준비된 공격이 현재 위치에서 빗나가고 같은 로그의 PatternId/StepIndex가 유지됨
  - HUD 표시 ActionType/TileId와 실제 실행 값이 일치
  - `Prepare → Hold → Execute → Complete` positive log 순서가 한 번씩만 출력

### Slice 10.6 - 공격 타일 보유 상태와 사거리 추적 분리

- ✅ 상태: Tested — Maker에서 근접 등록·접근·예고·회피 Miss, 반대 방향 `NEEDS_TURN`, 2칸 Spore 접근·동시 예고·회피 Miss, QUICK 원거리 추적/사거리 내 즉시 준비, 다중 적·강제 증원·Client DTO를 검증
- 화면 결과: 적은 공격 타일을 먼저 보유하고 접근하며, 공격 가능한 위치에서만 위험 범위를 예고한다. 예고 후 플레이어가 피하면 적은 다시 추적하지 않고 예고 공격을 실행해 빗나간다.
- 목적:
  - 현재 `사거리 확인 → 공격 타일 등록` 순서를 `공격 타일 등록 → 사거리 추적 → 공격 예고 → 고정 실행`으로 교정
  - 공격 큐 보유 상태와 플레이어가 대응해야 하는 `ATTACK_READY` 상태를 분리
  - 근접 Orange Mushroom과 2칸 원거리 Spore가 같은 런타임 규격을 사용하도록 구성
- 최소 상태:
  - `INSERTING`: 기존 `EnemyQueueTurns`만큼 공격 타일 등록 진행
  - `TRACKING`: 타일을 보유한 채 사거리·방향을 맞추는 중
  - `ATTACK_READY`: 공격 예고 완료, 플레이어 대응 Command 뒤 실행
  - `EXECUTING`: 예고한 타일을 현재 Cell/Facing 기준으로 실행
- 최소 인터페이스:
  - `EnemyActionPlanComponent`의 타일 보유 상태와 임시 추적 Command 분리
  - 무상태 Readiness 판정 `READY/NEEDS_TURN/NEEDS_MOVE/BLOCKED`
  - UI DTO `QueueState`, `QueuedTileId`, `ReadinessReason`, `NextCommandType`, `TargetCells`
- 데이터 원칙:
  - 첫 구현에서는 새 CSV 컬럼을 추가하지 않는다.
  - 사거리는 기존 Skill Target 규칙, 등록 시간은 `EnemyQueueTurns`, 빠른 준비는 `QUICK`을 재사용한다.
  - 공격 추적 중에는 Pattern Step을 완료하지 않고, 실제 공격 완료 뒤에만 StepIndex를 전진한다.
- 완료 기준:
  - 근접 적과 Spore가 사거리 밖에서 공격 타일을 잃지 않고 추적한다.
  - 사거리 진입 시 즉시 피해 없이 `ATTACK_READY`가 표시된다.
  - 플레이어가 예고 뒤 벗어나도 적은 재추적하지 않고 공격해 Miss가 발생한다.
  - QUICK은 사거리 안에서만 등록과 준비를 같은 적 행동에 처리한다.
  - 강제 증원·다중 적·Wave·Victory/Defeat/Reset 회귀를 통과한다.

### Slice 11 - 단일 적의 추적 이동과 고정 방향 이동 분리

- ✅ 상태: Tested — 추적 방향 전환, 고정 방향 이동, 경계·점유 WAIT를 Maker 런타임에서 검증 완료
- 화면 결과: 같은 적이 설정에 따라 플레이어를 향해 접근하거나, 생성 시 정해진 방향을 유지한 채 이동한다.
- 최소 구현:
  - 기존 `BuildEnemyIntent`의 무조건적인 플레이어 방향 회전을 제거
  - `TURN_TO_PLAYER`, `MOVE_TOWARD`, `MOVE_FIXED_FACING` 세 행동 의미 분리
  - `MOVE_FIXED_FACING`이 경계/점유에 막히면 위치와 Facing을 유지하고 WAIT 처리
- 아직 하지 않음:
  - Dataset, 적 두 명, 런타임 Spawn, 웨이브
- 완료 기준:
  - 고정 방향 적 뒤로 플레이어가 이동해도 적 Facing이 바뀌지 않음
  - 추적 행동은 플레이어 반대편 이동 후 다음 행동에서 방향을 갱신
  - 이동 실패 때 자동 반전하지 않는 positive log

### Slice 12 - 다중 유닛 Board Registry

- ✅ 상태: Tested — Registry 조회·안정 정렬·사망 제외와 기존 이동/공격/밀치기/Reset 회귀 검증 완료
- 화면 결과: 화면은 기존 한 적 그대로지만 내부 조회가 `EnemyEntity` 단일 참조 대신 UnitId/CellIndex Registry를 사용한다.
- 최소 구현:
  - `BoardStateComponent`에 Register/Unregister/FindByUnitId/FindAtCell/CollectLivingEnemies 추가
  - CellIndex와 SpawnOrder 기준 안정 정렬
  - 기존 이동·공격·밀치기·사망·Reset 경로를 Registry 조회로 교체
- 아직 하지 않음:
  - 두 번째 적 배치, 웨이브, 범용 이벤트 버스
- 완료 기준:
  - 기존 Slice 2~9의 대표 회귀 로그가 동일
  - 사망 유닛이 점유 조회와 생존 적 목록에서 제외
  - Lua `pairs` 순서에 의존하지 않음

### Slice 13 - 좌우 적 두 명 고정 배치

- ✅ 상태: Tested — 좌우 배치, SpawnOrder 행동 순서, 개별 사망 지속, 전체 사망 승리와 Reset 검증 완료
- 화면 결과: 6칸 보드에서 플레이어 양쪽에 적이 보이고 방향 전환으로 공격 대상을 바꾼다.
- 검증 배치:
  - Player Cell 2
  - Left Enemy Cell 0, 초기 Facing Right
  - Right Enemy Cell 5, 초기 Facing Left
- 최소 구현:
  - 같은 적 `.model` 인스턴스 2개 사용
  - SpawnOrder에 따른 결정적 적 행동 순서
  - 한 적 사망 후 다른 적이 살아 있으면 전투 계속
  - 모든 적 사망 후에만 Victory
- 아직 하지 않음:
  - 런타임 Spawn, SpawnPool, 다중 웨이브, 적별 Intent 완성 UI
- 완료 기준:
  - 좌우 Front Cell 공격, 밀치기, 점유 차단이 각각 올바른 UnitId를 대상으로 함
  - 생존 적 두 명의 행동 순서가 매 실행 동일
  - 첫 적 사망 시 Victory가 발생하지 않고 두 번째 적 사망 시 한 번만 발생

### Slice 14 - CSV 기반 일반전 맵 재사용과 보스 맵 분리

- ✅ 상태: Verified — `region_01_boss` 생성, 1-4 CSV 라우팅, 서버 런타임 맵 전환과 콘텐츠 검증 통과.
- 화면 결과: 1-1~1-3은 같은 `region_01_battle` 물리 맵을 재사용하고 1-4는 `region_01_boss`로 이동하며, 각 StageDefinitions·Wave 데이터로 독립 초기화된다.
- 최소 구현:
  - `StageMapRoutes.csv`의 1-1~1-3은 `MapId=region_01_battle`, 1-4는 `MapId=region_01_boss`로 설정
  - 월드맵 지연 진입 요청의 현재 맵 검사를 실제 로비 맵명 `lobby`로 통일
  - 공용 맵의 `BattleSessionComponent.AutoStartPrototypeBattle=false`
  - Static Map 격리를 위해 `sector01.maxUserNo=1`
  - 일반전 공용 물리 맵 `region_01_battle`을 복제해 전투 컴포넌트 계약이 같은 `region_01_boss` 생성
- 불변식:
  - `StageId`는 콘텐츠 식별자이고 `MapId`는 물리 이동 대상이다.
  - 준비된 BattleEntry가 없는 직접 맵 진입은 전투를 자동 시작하지 않는다.
  - 공용 맵 재진입마다 Registry·Turn·Wave·Queue·Drop·BattleResult를 새 StageId 기준으로 초기화한다.
- 완료 기준:
  - 1-1~1-3은 일반전 공용 맵, 1-4는 보스 전용 맵을 반환하고 기존 중복·누락·비활성 검증이 유지됨
  - Stage 1 클리어 후 보상 맵을 거쳐 같은 물리 맵에 Stage 2로 재진입하며 RequestId와 StageId가 갱신됨
  - Stage 3은 일반전 공용 맵, Stage 4는 보스 전용 맵으로 진입함
  - 중복 맵 삭제 후 Sector의 모든 map entry가 실제 파일과 일치하고 build/runtime Error·Warning이 없음

### Slice 15 - 헤네시스 일반전·머쉬맘 보스전 배경 구성

- ✅ 상태: Verified — 교체 가능한 장식 모델과 일반전·보스전 배치 완료, 두 맵의 플레이 카메라 가독성과 오류·경고 0건 확인.
- 화면 결과: 일반전은 밝은 헤네시스 외곽 사냥터, 보스전은 같은 지역의 더 울창한 버섯 숲으로 구분되며 6칸 전투 정보는 가려지지 않는다.
- 최소 구현:
  - 장식 SpriteRUID를 교체 가능한 `.model`로 분리
  - 일반전에는 표지판·관목·나무를 가장자리와 후경에 배치하고, 오른쪽에는 보스전 왼쪽과 같은 나무·버섯 군락으로 이어지는 숲길을 암시
  - 보스전에는 큰 수풀·나무 군락을 배치하고 중앙 전투선과 착지 전조 영역은 비움
  - 기존 `BattleCell1~6`, 카메라, Foothold, 전투 상태 컴포넌트는 변경하지 않음
- 완료 기준:
  - 두 맵 모두 6개 셀·플레이어·적·Intent UI 가독성을 유지함
  - 장식 모델의 SpriteRUID를 한 곳에서 교체할 수 있음
  - 1-1과 1-4 진입 화면이 명확히 구분되고 build/runtime Error·Warning이 없음

## 5. 이후 Phase로 넘길 것

Phase 1이 모두 검증된 뒤 다음 순서로 확장한다.

1. 타일 쿨다운과 FreePlay
2. 일반 적 Pattern과 InitialFacingPolicy 데이터
3. UserDataSet/CSV 이전과 Validator
4. 런타임 적 Spawn과 Registry 수명
5. BALANCED/ANY 웨이브와 스테이지 진행
6. 증강 3택
7. 직업과 콘텐츠 수량 확장
8. 연출, 저장, 재접속
9. 6개 마을의 독립 Region/Stage 데이터 추가
10. 모든 마을 연결 Edge에 공통 상점 노드 추가

### 월드맵 지역 확장 순서

Phase 1의 헤네시스 첫 분기는 이후 지역을 추가하기 위한 기준 구현이다. 후속 콘텐츠는 아래 순서와 계약을 유지한다.

| RegionId | 마을 | 물리 맵 세트 | 연결 |
|---|---|---|---|
| `region_01` | 헤네시스 | `region_01_battle`, `region_01_boss` | 시작 |
| `region_02` | 커닝시티 | `region_02_battle`, `region_02_boss` | `region_01 → region_02 → region_04 → region_06` |
| `region_03` | 엘리니아 | `region_03_battle`, `region_03_boss` | `region_01 → region_03 → region_05 → region_06` |
| `region_04` | 페리온 | `region_04_battle`, `region_04_boss` | 위쪽 중간 지역 |
| `region_05` | 노틸러스 | `region_05_battle`, `region_05_boss` | 아래쪽 중간 지역 |
| `region_06` | 슬리피우드 | `region_06_battle`, `region_06_boss` | 양쪽 경로 합류 |

```text
로비
└─ 헤네시스
   ├─ 상점(Henesys→Kerning) → 커닝시티 → 상점(Kerning→Perion) → 페리온 → 상점(Perion→Sleepywood) ┐
   └─ 상점(Henesys→Ellinia) → 엘리니아 → 상점(Ellinia→Nautilus) → 노틸러스 → 상점(Nautilus→Sleepywood) ┘
                                                                                                      ↓
                                                                                                  슬리피우드
```

후속 구현 체크리스트:

- [ ] `RegionDefinitions`에 커닝시티·엘리니아·페리온·노틸러스·슬리피우드 추가
- [ ] Region마다 `region_XX_battle.map`과 `region_XX_boss.map`을 별도 생성
- [ ] 같은 Region의 일반 Stage만 해당 `region_XX_battle`을 재사용하고 다른 마을 맵은 공유하지 않음
- [ ] `StageMapRoutes`의 모든 StageId를 소속 Region의 일반전/보스전 MapId로 연결
- [ ] `NodeDefinitions`에 도시별 전투/보스 노드와 6개 Edge 상점 노드 추가
- [ ] 모든 상점 표시와 클릭은 공통 `ShopVisitBtn` 및 Shop Controller 사용
- [ ] Edge별 `ShopId`, 출발 `RegionId`, 도착 `RegionId`, 해금 조건을 데이터로 정의
- [ ] 마을 클리어 전에는 다음 상점과 도시를 클릭할 수 없도록 서버 Run Snapshot으로 게이트
- [ ] 상점 방문 완료 후에만 해당 Edge의 다음 마을을 클릭 가능하게 전환
- [ ] `UPPER`/`LOWER` 최초 선택을 Run 동안 유지하고 반대 경로를 비활성화
- [ ] 두 경로가 슬리피우드에서 동일한 진행 상태로 합류하는지 검증
- [ ] UI 코드에 도시별 `if`를 늘리지 않고 Dataset 행 추가만으로 노드를 확장

## 6. 사용자와 함께 확인할 화면 체크포인트

각 Slice가 끝날 때 다음만 함께 확인한다.

- 배치가 이해하기 쉬운가?
- 버튼을 보고 다음 행동을 예상할 수 있는가?
- 실제 행동이 예상과 일치하는가?
- 한 화면에 정보가 너무 많지 않은가?
- 다음에 추가할 기능 하나가 무엇인지 명확한가?

화면 판단이 필요한 항목은 AI가 임의로 `✅ Tested` 처리하지 않는다. 구현은 `🟡`로 두고 사용자 확인 후 `✅`로 변경한다.

## 7. 구현 기록

### 2026-07-18 — 기본 전투 오브젝트 배치

- 현재 맵 타입: `MapleTile(0)`; 기존 상단 발판과 34개 Foothold를 유지
- 전투 셀: 7개, X=`-3.45, -2.3, -1.15, 0, 1.15, 2.3, 3.45`, 간격=`1.15`
- Player 시작점: CellIndex `1`, X=`-2.3`
- Enemy 시작점: CellIndex `5`, X=`2.3`
- 셀 표식 모델: `BattleCellMarker` (`battlecellmarker`)
- 테스트 적 모델: `BattleDummyEnemy` (`battledummyenemy`, Orange Mushroom stand clip)
- Maker 검증: workspace refresh 성공, build error `0`, runtime Entity 9개 좌표 로그 일치
- 남은 작업: Phase/Turn HUD, CellToWorld 함수, Unit 런타임 컴포넌트

### 2026-07-18 — 일자형 발판과 반복 배치 프리셋

- 임시 고양이 발바닥 표식을 `BattlePlatformTile` 일자형 석재 발판으로 교체
- 발판 리소스: `07dc23f375ed4a7c8a09ec45b31b6daa` (180×20)
- 반복 배치 입력값:
  - `tileModelPath`: 배치할 `.model`
  - `count`: 타일 개수
  - `spacing`: 중심점 간격
  - `centerX`: 전체 줄의 중심 X
  - `y`, `z`: 배치 높이와 렌더 깊이
  - `namePrefix`: Entity 이름 접두사
- 자동 계산:
  - `startX = centerX - spacing * (count - 1) / 2`
  - `tileX(index) = startX + spacing * index`
- 재실행 규칙: 같은 `namePrefix + 번호` Entity를 제거한 뒤 선택한 모델로 다시 배치하여 개수 축소·확대 모두 처리
- 현재 프리셋: `count=7`, `spacing=1.15`, `centerX=0`, `y=0.08`, `namePrefix=BattleCell`
- 운영 방식: 사용자가 타일 종류와 개수를 정하면 Codex가 이 프리셋으로 MapBuilder를 실행하고 Maker에서 검증

### 2026-07-18 — 6칸 단색 셀로 단순화

- 셀 개수: `6`
- 표현: 외부 발판 스프라이트 대신 `PixelRendererComponent` 단색 직사각형
- 색상: `Color(0.38, 0.64, 0.20, 1.0)` — 기존 잔디 지면과 어울리는 초록색
- 셀 크기: 폭 `1.0`, 높이 `0.12` world units
- 셀 간 빈 공간: `0.12` world units
- 중심점 간격: `1.12` world units
- 배치 X: `-2.8, -1.68, -0.56, 0.56, 1.68, 2.8`
- 배치 Y: `-0.10`; 셀 윗면이 기존 Foothold 높이 약 `-0.04`에 맞닿음
- Player 시작: CellIndex `1`, X=`-1.68`
- Enemy 시작: CellIndex `4`, X=`1.68`
- 실제 충돌은 기존 `FootholdComponent`가 계속 담당하고 단색 셀은 전투 위치 표시만 담당

### 2026-07-20 — 1칸 행동 큐와 입력 잠금

- 입력 경로: 이동·방향 전환·기본 공격 요청을 `TryQueuePlayerAction`으로 통합
- 큐 크기: 실행 중인 행동 `1개`; 처리 중 추가 요청은 `ACTION_PROCESSING`으로 거절
- 처리 시간: 이동 `0.12초`, 방향 전환 `0.12초`, 기본 공격 `0.45초`
- 기존 로직 재사용: 큐 실행기가 `TryMove`, `TryTurn`, `TryBasicAttack`을 그대로 호출
- 동기화 상태: `QueuedActionType`, `QueuedActionDirection`, `IsActionProcessing`
- Maker 검증: 같은 프레임 기본 공격 2회 요청 시 첫 요청만 실행되고 두 번째 요청 거절
- 회귀 검증: `D → D → F → Space`로 Cell `1 → 3`, 적 HP `100 → 97`, Facing `Right → Left`, 큐 해제 확인

### 2026-07-21 — 최소 행동 큐 HUD

- UI 파일: `ui/BattleQueueHUD.ui`
- 표시 컴포넌트: `02_UI/BattleQueueHudComponent.mlua`
- 표시 상태: `TurnNumber`, `QueuedActionType`, `BattlePhase`, `IsActionProcessing`
- Maker 검증: `D` 입력 시 `대기 → 이동 → 적 행동 준비 → 적 이동 → 대기`, `TURN 1 → TURN 2` 전환 확인
- 런타임 최종 텍스트: `TURN 2 / 대기 / 플레이어 턴 · 입력 가능`
- 범위 구분: 처음에는 즉시 실행 큐 상태 표시로 만들었고, 같은 HUD를 Slice 8의 타일 선택·등록·실행·비우기 UI로 확장
- 행동의 턴 소비, 적 Intent 실행, `TurnNumber` 증가는 같은 날 최소 턴 순환 단계에서 연결

### 2026-07-21 — 최소 적 Intent와 턴 순환

- 턴 순서: `PlayerTurn → EnemyTurn → PlayerTurn`; 적 행동 완료 시 `TurnNumber + 1`
- 입력 잠금: 플레이어 행동 시작부터 적 행동 종료까지 유지
- 적 Intent: 거리가 두 칸 이상이면 플레이어 방향으로 한 칸 이동, 인접하면 기본 공격
- 기존 로직 재사용: 적도 `TryMove`, `TryBasicAttack`, `ApplyDamage` 사용
- 팀별 실행 검증: Player는 `PlayerTurn`, Enemy는 `EnemyTurn`에서만 행동 가능
- Maker 검증: 적이 Cell `4 → 3 → 2`로 접근한 뒤 플레이어를 공격
- 최종 검증 상태: `PlayerTurn`, Turn `5`, Player HP `94`, Enemy HP `94`, 큐 비어 있음
- 중복 입력 회귀 검증: 같은 프레임 두 번째 기본 공격은 `ACTION_PROCESSING`으로 거절
- 아직 하지 않음: Intent 화면 표시, 적 전용 이동/공격 모션, 사망·승패·Reset

### 2026-07-21 — 기본 공격 타일 1칸 큐

- 타일 ID: `basic_slash`; 큐 용량 `1칸`
- UI 조작: `기본 공격 타일`로 등록, `실행`으로 기존 기본 공격 경로 호출, `비우기`로 턴 소비 없이 등록 취소
- 서버 상태: `BattleSessionComponent.QueuedTileId`; UI는 동기화 상태를 읽고 요청만 전달
- 입력 충돌 방지: 타일 등록 중 키보드 즉시 행동은 `TILE_QUEUE_OCCUPIED`로 거절
- UI 상태: `빈 큐 / 타일 선택` → `기본 베기 / 실행 대기` → `기본 공격 / 처리 중`
- Maker 버튼 이벤트 검증: 등록 후 버튼 활성 상태 `false/true/true`, 비우기 후 빈 큐 복귀
- 실행 검증: Player Cell `2`, Enemy Cell `3`에서 실행하여 Enemy HP `100 → 97`; 이어진 적 공격 뒤 Turn `3`, 큐 비어 있음
- Build 검증: error `0`, warning `0`
- 아직 하지 않음: 두 번째 타일, 여러 칸 큐, Dataset, 쿨다운, 버튼 SFX

### 2026-07-21 — 사망·승리·전투 Reset

- HP 처리: `ApplyDamage`에서 0으로 Clamp하고 최초 0 전환만 `HandleUnitDied` 호출
- 결과 상태: `BattlePhase=BattleEnded`, `BattleResult=Victory/Defeat`; 결과 확정 뒤 적 행동과 Turn 증가 중단
- 적 사망 표현: 적 Sprite와 월드 HP 텍스트 숨김
- UI: 중앙 `VICTORY`/`DEFEAT` 패널과 88px 높이 `다시 시작` 버튼
- Reset 범위: 큐·처리 상태·결과·Turn·HP·IsDead·CellIndex·Facing을 초기값으로 복원
- Maker 검증: 적 HP `3 → 0`, `Victory`, 적 숨김, 결과 패널 활성화 확인
- Defeat 검증: Player HP `3 → 0`, `BattleEnded/Defeat`, `DEFEAT` 패널과 Reset 버튼 활성화 확인
- 실제 Reset 버튼 검증: `PlayerTurn`, Turn `1`, Player `Cell 1 / HP 100`, Enemy `Cell 4 / HP 100`, 결과 패널 숨김, 적 다시 표시
- Build/Runtime 검증: error `0`, warning `0`
- 아직 하지 않음: 보상, 다음 스테이지, 드롭, 사망 전용 모션·SFX

### 2026-07-21 — 공격별 아바타 모션 라우터

- 기존 `PlayBasicAttackMotion()`과 직접 `ActionAttack()` 호출을 공용 `PlayCombatMotion()`으로 교체
- 공격 프로필: `MotionKey`, `ActionName`, `PlayRate`, `Duration`
- 기본 경로: 빈 `ActionName`은 장착 무기에 맞는 `MapleAvatarBodyActionState.Attack` 직접 재생
- 커스텀 경로: `ActionStateChangedEvent`를 Avatar Body Entity에 보내고 `Onetime`으로 재생
- 모션 종료: 지정 시간 뒤 `CombatMotionReturnState=IDLE`과 `Stand` Body Action으로 복귀
- `basic_slash` 기본 설정: `basic_slash / swingO1 / 1.0배 / 0.45초`; 반복 실행 시 같은 모션으로 고정
- 반복 검증: 실제 타일 등록·실행을 3회 수행하고 세 번 모두 `CUSTOM_ACTION action=swingO1` 확인
- Maker 기본 경로 검증: `BUILTIN_BODY_ACTION` 시작 후 IDLE 복귀
- Maker 커스텀 경로 검증: `verify_heavy_slash / swingO2 / 1.2배 / 0.35초`, `CUSTOM_ACTION` 시작 후 IDLE 복귀
- Build/Runtime 검증: error `0`, warning `0`
- 아직 하지 않음: 타격 프레임별 `ImpactDelay`, 모션 전용 SFX·이펙트

### 2026-07-21 — 두 번째 공격 타일 `heavy_slash`

- 큐 용량은 한 칸 유지; `basic_slash`와 `heavy_slash` 중 하나만 등록
- 공용 해석기: `TryFrontAttack(sourceUnitId, attackId, damage, motion...)`
- 기본 베기: 피해 `3`, `swingO1`, 1.0배, 0.45초
- 강한 베기: 피해 `6`, `swingO2`, 0.85배, 0.70초
- HUD: 900×320 패널에 `기본 공격 타일`, `강한 베기 타일`, `실행`, `비우기` 배치
- 실제 UI 버튼 검증: 기본 베기 `100 → 97`, 강한 베기 `97 → 91`
- 모션 검증: 기본 `basic_slash/swingO1`, 강한 `heavy_slash/swingO2`; 각 동작 후 IDLE 복귀
- Build/Runtime 검증: error `0`, warning `0`
- 아직 하지 않음: ImpactDelay, 여러 칸 큐, 쿨다운, 공격별 이펙트·SFX

### 2026-07-21 — 가변 용량 타일 큐와 순차 실행

- 당시 프로토타입 기본 용량: `TileQueueCapacity=2`; 2026-08-01부터 기본 3과 Modifier 방식으로 대체
- 등록 상태: `QueuedTileIds`의 `|` 구분 순서 문자열과 `QueuedTileCount`
- 실행 상태: 등록 큐를 `ExecutingTileIds`로 동결하고 `ExecutingTileIndex`를 한 칸씩 증가
- 실행 규칙: 각 타일의 모션·ImpactDelay·피해 해결이 끝난 뒤 다음 타일 시작, 전체 큐 완료 뒤에만 적 턴 전환
- HUD: `[기본 베기] → [강한 베기] (2/2)`와 실행 중 `▶` 인덱스 표시
- Maker 기본 용량 검증: 세 번째 등록은 `QUEUE_FULL`, 두 타일 피해가 `100 → 97 → 91`로 순차 적용
- Maker 확장 검증: 런타임 용량 3에서 세 타일 등록과 `3/3` HUD 상태 확인, 네 번째 등록은 `QUEUE_FULL`
- Build/Runtime/UI lint 검증: error `0`, warning `0`
- 다음 작업: `PUSH` 타일을 추가해 첫 타일 이후 두 번째 타일이 현재 CellIndex에서 타깃을 다시 찾는지 검증

### 2026-07-21 — 밀치기 타일과 큐 재타깃

- 타일 ID와 행동: `push → PUSH`
- 표현 설정: `swingO1`, 0.9배, 모션 0.40초, `PushImpactDelay=0.18`
- 판정: 타격 시점의 Source `CellIndex`·`Facing`으로 앞 셀을 다시 조회하고 대상을 같은 방향으로 한 칸 이동
- 방어 규칙: 보드 밖은 `PUSH_BLOCKED_OUT_OF_BOUNDS`, 점유 셀은 `PUSH_BLOCKED_OCCUPIED`, 빈 앞 셀은 `MISS_EMPTY`
- 상태 변경: 대상 `CellIndex`를 먼저 변경하고 `PlaceEntity`, `UnitMovedEvent` 순서로 반영
- HUD: 기존 스타일의 `밀치기` 버튼 추가, 다섯 버튼을 동일 간격으로 재배치, UUID 자동 바인딩
- 재타깃 검증: Player Cell 1, Enemy Cell 2에서 `push|basic_slash` 실행 → Enemy Cell `2 → 3` → 기본 베기는 Cell 2 `MISS_EMPTY`, HP 100 유지
- 경계 검증: Player Cell 4, Enemy Cell 5에서 밀치기 → 목적지 Cell 6 차단, Enemy Cell 5 유지
- Build/Runtime/UI lint 검증: error `0`, warning `0`
- 다음 작업: 두 번째 Effect 사례를 기준으로 `DAMAGE`·`PUSH`의 작은 Effect Router 추출 여부 검토

### 2026-07-25 — DAMAGE/PUSH 최소 Effect Router

- 상태: 🟡 Implemented (core paths tested)
- 새 파일: `01_Combat/Resolvers/EffectRouterLogic.mlua`
- `DAMAGE`: Router가 기존 `BattleSessionComponent.ApplyDamage` 단일 HP 변경 경로로 전달
- `PUSH`: Router가 기존 `BattleSessionComponent.ResolvePushImpact` 셀 이동 경로로 전달
- 기존 피해, 사망, 피격 플래시, 밀치기 점유/경계, `UnitMovedEvent` 규칙은 변경하지 않음
- Positive log: `[BattleEffectRouter] dispatch/resolved effect=DAMAGE|PUSH`
- 로컬 정적 검사: `git diff --check` 통과
- Maker 연결/작업공간 갱신: `map01` 편집 모드 감지, `refresh` 성공
- Build Console: 중단 오류 및 Warning `0`; 기존 동적 컴포넌트 접근 관련 Info 진단만 확인
- Runtime `DAMAGE`: `dispatch effect=DAMAGE` → HP `100→97` → `resolved success=true reason=OK`
- Runtime `PUSH`: Enemy Cell `2→3`, `UnitMovedEvent` 수신 → `resolved success=true reason=PUSHED`
- 테스트 스크립트에서 존재하지 않는 `RequestPush`를 한 차례 호출해 `LEA-2011`이 발생했으나, 테스트 호출명을 수정하고 로그를 비운 뒤 Router 공개 진입점으로 재검증함
- 남은 재검증: `push|basic_slash` 재타깃과 경계 밀치기 `PUSH_BLOCKED_OUT_OF_BOUNDS`

### 2026-07-25 — 적 Prepared Intent와 HUD 예고

- 상태: ✅ Tested
- 적 Intent 상태: `EMPTY → PREPARED → EXECUTING → EMPTY`
- 준비 Snapshot: `EnemyId`, `PatternId`, `StepIndex`, `ActionType`, `TileId`, `Direction`, `PreparedTurn`, `Reason`
- 실행 흐름: `PrepareEnemyIntent → BeginEnemyTurn(Hold) → ExecutePreparedEnemyIntent → CompletePreparedEnemyIntent`
- HUD: 기존 상태 문구에 `적 예고: 접근` 또는 `적 예고: 기본 베기`를 표시하며, AI 조건을 UI에 복제하지 않고 동기화 Snapshot만 읽음
- 최초 상태 검증: Player Cell 1, Enemy Cell 4에서 Turn 1 `MOVE_TOWARD`, HUD `적 예고: 접근`
- 접근 검증: Player `1→2` 이동 후 준비된 Turn 1 `MOVE_TOWARD`가 Enemy `4→3`으로 실행되고 Turn 2 `EXECUTE_TILE/basic_slash` 준비
- 유지 검증: Turn 2에 `push`로 Enemy `3→4` 이동 후에도 `prototype_basic / step 1 / EXECUTE_TILE / basic_slash / preparedTurn 2` 유지
- 실행 결과: 적이 이동으로 재계획하지 않고 Cell 4에서 Left 방향의 Cell 3을 공격하여 `MISS_EMPTY`; Player는 Cell 2에서 피해 없음
- 완료 후 재계산: 위 공격 완료와 Turn 3 진입 뒤에만 새 `MOVE_TOWARD` Intent 준비
- Positive log 순서: `[BattleEnemyIntent] prepare → hold → execute → complete → clear`
- Maker 검증: workspace refresh 성공, Build Console Error/Warning `0`, runtime Error/Warning `0`

### 2026-07-25 — 추적 이동과 고정 방향 이동 분리

- 상태: ✅ Tested
- 설정값: `BattleSessionComponent.EnemyMovementPolicy`
  - `TRACK_PLAYER`: 현재 Facing과 플레이어 방향이 다르면 `TURN_TO_PLAYER`, 같으면 `MOVE_TOWARD` 또는 앞 칸 `basic_slash`
  - `FIXED_FACING`: 플레이어 위치로 회전하지 않고 현재 Facing을 `MOVE_FIXED_FACING.Direction`으로 고정
- HUD 예고: `플레이어 방향 전환`, `추적 접근`, `고정 방향 전진`, `기본 베기`, `대기`
- 추적 검증: Enemy Cell 1/Left, Player Cell 4에서 `TURN_TO_PLAYER direction=1` 실행 → Enemy Right 유지 → 다음 Turn `MOVE_TOWARD direction=1` 준비
- 고정 방향 검증: 같은 배치에서 `FIXED_FACING`은 Player가 오른쪽에 있어도 Enemy Left를 유지하고 Cell `1→0` 이동
- 경계 검증: Enemy Cell 0/Left에서 이동 시 Cell과 Facing을 유지하고 `WAIT_OUT_OF_BOUNDS`로 정상 완료
- 점유 검증: `MOVE_FIXED_FACING` 준비 뒤 목적지 Cell을 Player가 점유하면 Enemy 위치·Facing을 유지하고 `WAIT_CELL_OCCUPIED`로 정상 완료
- Prepared Intent 유지: 방향과 행동은 준비 시점 Snapshot을 사용하며 실행 시 플레이어 위치로 다시 계산하지 않음
- Maker 검증: workspace refresh 성공, Build Console Error/Warning `0`, runtime Error/Warning `0`

### 2026-07-25 — 다중 유닛 Board Registry

- 상태: ✅ Tested
- 새 파일: `01_Combat/Components/Shared/BoardStateComponent.mlua`
- Registry API: `RegisterUnit`, `UnregisterUnit`, `FindByUnitId`, `FindAtCell`, `CollectLivingEnemies`, `CollectRegisteredUnits`
- 내부 저장은 `UnitId → Entity` Dictionary를 사용하고, 순서가 필요한 조회 결과는 `SpawnOrder → UnitId` 순으로 정렬
- 점유와 생존 적 조회에서 `IsDead=true` 유닛을 제외하며, `FindByUnitId`는 전투 Reset이 기존 Entity를 재사용할 수 있도록 사망 유닛도 반환
- `BattleSessionComponent`의 이동·전방 타깃·공격·밀치기·사망 판정·Reset·전투 시작 조회를 Registry 경로로 전환
- 현재 화면과 배치는 기존 Player 1명/Enemy 1명을 유지하며, 두 번째 적 배치와 런타임 Spawn은 Slice 13 이후로 분리
- Registry 검증: 등록 수 `2`, 안정 순서 `player_01:1,enemy_01:2`, UnitId/Cell 점유 조회 모두 성공
- 사망 제외 검증: Enemy를 임시 사망 상태로 전환했을 때 Cell 점유 없음, 생존 적 수 `0`
- 회귀 검증: Player `1→2→3`, 공격 HP `100→90`, 밀치기 Enemy `4→5`, Reset 후 Player `1`/Enemy `4`/등록 수 `2`
- Maker 검증: workspace refresh 성공, Build Console 중단 Error/Warning `0`(기존 동적 컴포넌트 접근 Info 진단만 존재), runtime Error `0`

### 2026-07-25 — 좌우 적 두 명과 초반 HP 조정

- 상태: ✅ Tested
- 배치: Left Enemy Cell `0`/Right, Player Cell `2`/Right, Right Enemy Cell `5`/Left
- 같은 `BattleDummyEnemy.model`을 `BattleEnemyLeft`, `BattleEnemyRight` 두 인스턴스로 배치
- UnitId와 순서: `enemy_left_01`/SpawnOrder `2`, `enemy_right_01`/SpawnOrder `3`
- 초반 적 HP: `EarlyStageEnemyMaxHp=6`
  - 기본 베기 피해 `3`: 2회 처치
  - 강한 베기 피해 `6`: 1회 처치
- 적 턴: 생존 적을 SpawnOrder 순으로 하나씩 실행하고, 모든 생존 적 행동이 끝난 뒤에만 다음 PlayerTurn 개방
- 행동 순서 검증: Left `0→1` 실행 후 Right `5→4`, 이후 Turn `1→2`
- 첫 적 사망 검증: Left HP `6→0`, `result=CONTINUE`, 생존 적 `1`, Victory 없음
- 전체 사망 검증: Right HP `6→0`, 생존 적 `0`일 때만 `result=Victory`
- Reset 검증: Player Cell `2`, Left `0`/HP `6`, Right `5`/HP `6`, 생존 적 `2`
- 화면 검증: 고정 카메라 안에서 플레이어 양쪽 적과 `HP 6 / 6` 텍스트가 정상 표시
- 아직 분리 유지: 런타임 Spawn/웨이브, 적별 전체 Intent 큐 UI, Dataset 기반 HP 밸런스

### 2026-07-25 — Stage 1 유한 웨이브와 런타임 Spawn

- 상태: ✅ Tested
- 진행 구조: `Stage 1 → Wave 1 → Wave 2 → Wave 3 → Stage Clear`
- 시작 방식: `map01`의 고정 적 두 Entity를 제거하고, 게임 시작부터 `BattleSessionComponent.StartStage(1)`이 Wave 1을 생성
- 생성 원본: `BattleDummyEnemy.model`, `EnemyModelId=battledummyenemy`
- 당시 검증 설정: `TotalWaves=3`, 웨이브당 좌우 적 2명, `EnemyDefinitions.csv` 기준 `early_mushroom` HP 6·`guard_mushroom` HP 9, 웨이브 전환 `0.60초`
- UnitId: `enemy_w{wave}_left`, `enemy_w{wave}_right`; Entity 이름도 Wave 번호를 포함해 런타임 추적 가능
- 스폰 위치: 기본 Cell 0/5를 우선 사용하고, 생존 플레이어가 점유 중이면 해당 가장자리에서 안쪽 빈 셀을 탐색
- 전환 처리: 마지막 적 사망 시 행동·Impact 타이머와 큐를 정리하고 `WaveTransition/Cleared`; 기존 적을 Registry에서 해제·파괴한 뒤 다음 웨이브 생성
- 완료 처리: Wave 1·2 종료는 Victory가 아니며, Wave 3 종료에서만 `BattleEnded/StageCleared/Victory`
- Reset: 런타임 적을 정리하고 플레이어를 초기 Cell 2로 복원한 뒤 동일한 Stage 1 / Wave 1 생성 경로 재사용
- HUD: 넓은 상태 문구에 `STAGE 1 · WAVE 1/3` 표시, 전환 중 `웨이브 완료 · 다음 웨이브 준비` 표시
- 2026-08-03 테스트 난이도 조정: 실제 `StageEnemyWaves.csv`는 Wave 1/2 각 1명, Wave 3 2명(총 4명), `MaxConcurrent=3`으로 낮췄다. 위 2026-07-25 검증 기록은 당시 2명씩 생성한 이력이다.
- 2026-08-03 추가 난이도 조정: Wave 3도 2명 → 1명으로 낮춰 스테이지 전체 등장 수를 4명 → 3명(웨이브당 1명)으로 통일하고 `MaxConcurrent`를 3 → 2로 낮췄다. `EnemyDefinitions.csv`의 HP도 `early_mushroom` 6→4, `guard_mushroom` 9→6으로 낮췄다. `csv_retreat_mushroom`/`csv_telegraph_mushroom`은 stage01 스폰 풀에 없는 CSV 제작 테스트 전용 행이라 그대로 뒀다.
- Maker 검증:
  - 최초 등록 `player_01 + enemy_w1_left + enemy_w1_right`, 적 HP `6 / 6`
  - Wave 1 전멸 → `WaveTransition` → Wave 2 적 2명 생성
  - Wave 2 전멸 → Wave 3 적 2명 생성
  - Wave 3 전멸 → `BattleResult=Victory`, Wave 4 미생성
  - Reset → Wave 1, 생존 적 2명, `BattleResult=""`
- Build Console: 중단 Error/Warning `0`; 기존 동적 컴포넌트 접근 Info 진단만 존재
- 다음 확장: 웨이브별 적 수·모델·HP·스폰 Cell을 Dataset 행으로 이동하고 Stage 2 데이터를 추가

### 2026-07-25 — Dataset 기반 웨이브와 턴·시간 강제 증원

- 상태: ✅ Tested
- 새 데이터:
  - `03_Data/StageEnemyWaves.userdataset` + `StageEnemyWaves.csv`
  - `03_Data/EnemySpawnPools.userdataset` + `EnemySpawnPools.csv`
- 새 로더: `03_Data/Repositories/StageWaveRepositoryLogic.mlua`
- 기본 진행: 모든 생존 적 전멸 → `ClearSpawnDelaySeconds` 후 다음 웨이브
- 선택 가능한 생성 모드:
  - `CLEAR_ONLY`: 전멸할 때만 다음 웨이브
  - `TURN_LIMIT`: 지정 턴을 넘기면 강제 증원 예약
  - `TIME_LIMIT`: 지정 시간이 지나면 강제 증원 예약
  - `TURN_OR_TIME`: 두 제한 중 먼저 도달한 조건으로 예약
- 안전한 생성 시점: 시간 제한 콜백은 `ForceSpawnPending`만 설정하고, 실제 생성은 턴 경계에서 수행
- 겹침 규칙: 강제 증원에서는 이전 웨이브 생존자를 제거하지 않고 다음 웨이브를 빈 Cell에 추가
- 안전 제한: `MaxConcurrent`와 빈 Cell 수를 모두 확인하며, 공간이 부족하면 `CAPACITY_WAIT` 상태로 다음 턴 경계까지 대기
- Stage 1 설정:
  - Wave 1·2: `TURN_LIMIT`, 4턴, 적 2명, 최대 동시 생존 5명
  - Wave 3: `CLEAR_ONLY`, 적 2명
  - 공통 전멸 전환 지연: `0.60초`
- HUD: `증원까지 N턴`, `시간제 증원`, `증원 대기`, `전멸 시 증원`, `마지막 웨이브` 상태 표시
- Maker 검증:
  - Dataset에서 `stage01`, 총 3웨이브 및 웨이브별 설정 정상 로드
  - Wave 1 전멸 → 0.60초 후 Wave 2 생성, 생존 적 2명
  - Wave 1 적 2명 생존 상태에서 4턴 기준 도달 → Wave 2가 겹쳐 생성되고 생존 적 4명
  - 시간 제한 0.20초 표적 검증 → 행동 중 Wave 유지, `ForceSpawnPending=true`, `TIME_LIMIT`
  - 겹친 Wave 1·2 적 4명 전멸 → Wave 3 생성
  - Wave 3 전멸 → `Victory`, `BattleEnded`, 생존 적 0
- Build Console: 중단 Error/Warning `0`; runtime Error/Warning `0`
- 다음 데이터화: 여러 적 정의와 Spawn Pool 가중치 선택, EnemyPatternSteps 실제 Dataset 연결

### 2026-07-25 — Enemy 정의 테이블과 유닛별 전투 수치

- 상태: ✅ Tested
- 새 데이터:
  - `03_Data/EnemyDefinitions.userdataset` + `EnemyDefinitions.csv`
  - 초기 정의 `early_mushroom`: HP `6`, 기본 공격력 `3`, 패턴 `prototype_basic`, 이동 정책 `TRACK_PLAYER`
- 연결 변경:
  - `EnemySpawnPools.csv`가 `EnemyDefinitionId`와 `EnemyModelId`를 함께 보관
  - `StageWaveRepositoryLogic`이 Wave → Pool → Enemy Definition 순서로 검증·변환
  - `BattleSessionComponent`의 적 HP 하드코딩을 제거하고 현재 Wave 정의에서 수치를 적용
  - 스폰된 각 `BattleUnitComponent`가 `EnemyDefinitionId`, `BasicAttackDamage`, `EnemyPatternId`, `EnemyMovementPolicy`를 독립 보관
  - 기본 공격은 세션 공용 피해가 아니라 공격 유닛의 `BasicAttackDamage`를 우선 사용
- 겹침 안전성: 강제 증원으로 서로 다른 웨이브가 동시에 존재해도 각 적의 수치·패턴·이동 정책이 유지됨
- 현재 제한: 실행별 난수 Run Seed는 아직 없으며 같은 데이터는 같은 적 구성을 재현
- Maker 검증:
  - Wave 1·2·3에서 `early_mushroom`, HP `6`, 공격력 `3`, 패턴·이동 정책 정상 재적용
  - 적 기본 공격 1회로 플레이어 HP `100 → 97`
  - Wave 1 전멸 → Wave 2, Wave 2 전멸 → Wave 3 정상 전환
  - Wave 3 전멸 → `Victory`, `BattleEnded`, `StageCleared`, 생존 적 `0`
- Build Console: 중단 Error/Warning `0`; 최종 runtime Error/Warning `0`

### 2026-07-25 — 슬롯별 결정적 가중치 스폰과 혼합 적

- 상태: ✅ Tested
- 두 번째 적 정의:
  - `guard_mushroom`: HP `9`, 기본 공격력 `2`, 패턴 `prototype_basic`, 이동 정책 `FIXED_FACING`
  - 현재 시각 모델은 `early_mushroom`과 동일한 `battledummyenemy`를 재사용
- Pool 설정: `early_mushroom`과 `guard_mushroom`을 `stage01_basic`에 Weight `1:1`로 등록
- 선택 규칙:
  - Wave 전체에서 한 번 고르지 않고 각 SpawnIndex마다 독립 선택
  - 후보를 `EnemyDefinitionId|EnemyModelId`로 결정 정렬
  - WaveIndex·SpawnIndex 기반의 `1..전체 Weight` 결정적 롤 사용
  - 같은 데이터에서는 같은 결과가 나와 테스트와 리플레이를 재현 가능
- 런타임 변경:
  - `GetEnemySpawnDefinition()`이 Pool 행과 Enemy Definition을 합친 슬롯별 정의 반환
  - Wave는 모든 슬롯 정의를 먼저 검증한 뒤에만 Spawn을 시작하여 부분 생성 방지
  - `SpawnWaveEnemy()`가 세션 공용 수치 대신 전달받은 슬롯 정의로 Model·HP·공격력·패턴·이동 정책 적용
- Maker 검증:
  - Wave 1: `early_mushroom → guard_mushroom`, HP `6/9`, 공격력 `3/2`
  - Wave 2: `guard_mushroom → early_mushroom`으로 롤 순서 전환
  - `guard_mushroom` Intent가 `MOVE_FIXED_FACING`, 방향 `-1`로 준비
  - 수비형 적 기본 공격으로 플레이어 HP `100 → 98`
  - 혼합 구성으로 Wave 1→2→3 전환 후 `Victory`, `BattleEnded`, `StageCleared`, 생존 적 `0`
- Build Console: 중단 Error/Warning `0`; 최종 runtime Error/Warning `0`
- 다음 확장: Run Seed를 선택식에 추가해 런마다 구성이 달라지되 같은 Seed는 재현되도록 연결

### 2026-07-25 — Run Seed 기반 웨이브 구성 재현

- 상태: ✅ Tested
- 동기화 상태: `BattleSessionComponent.RunSeed`, 기본값 `1000`
- 새 런 API: `StartNewRun(runSeed)`
  - 진행 중인 행동·Impact·Wave·강제 증원 타이머 정리
  - 기존 적 Registry 해제와 Entity 제거
  - 플레이어 초기화 후 Stage 1 / Wave 1 정상 생성 경로 재사용
- 결과 화면의 `ResetBattle()`은 현재 Run Seed를 유지
- 선택 입력: `RunSeed`, `WaveIndex`, `SpawnIndex`, 후보의 전체 Weight
- 결정 규칙: 후보를 `EnemyDefinitionId|EnemyModelId`로 정렬하고
  `(RunSeed mod ΣWeight) + ((WaveIndex - 1) × 31) + SpawnIndex`로 롤 계산
- Maker 재현 검증:
  - Seed `1000` 첫 실행: `early_mushroom → guard_mushroom`
  - Seed `1000` 재실행: `early_mushroom → guard_mushroom`
  - Seed `1001`: `guard_mushroom → early_mushroom`
  - 세 실행 모두 새 런 완료 후 `PlayerTurn`, Wave `1/3`, 생존 적 `2`
- Runtime Error/Warning: `0`
- 다음 확장: 런 전체를 소유하는 RunManager와 Seed 생성·저장 정책 연결

### 2026-07-25 — 개인별 Run 상태 소유권 분리

- 상태: ✅ Tested
- 새 파일:
  - `04_Roguelike/RunManager/PlayerRunStateComponent.mlua`
  - `04_Roguelike/RunManager/RunManagerLogic.mlua`
- 소유권: 변경 가능한 Run 값은 전역 Logic이 아니라 각 플레이어의 `PlayerRunStateComponent`가 보관
- 조정자: `RunManagerLogic`은 상태를 직접 보관하지 않고 플레이어 컴포넌트 생성·조회, 새 Run 시작, 전투 결과 전달만 담당
- 현재 Run 상태: Seed, Run 순번, 상태, 현재 스테이지, 완료 스테이지 수, 마지막 전투 결과
- 전투 연결:
  - 플레이어 등록 시 기존 Run을 재사용하거나 최초 Run을 초기화
  - `BattleSessionComponent.StartNewRun(seed)`가 Run 상태 초기화와 전투 재구성을 함께 수행
  - 최종 승패 확정 시 `RecordBattleResult`로 해당 플레이어의 Run 상태 갱신
- Maker 새 Run 검증: Seed `2001`, Run 순번 `2`, Stage 1/Wave 1, 생존 적 `2`, Run 상태 `Active`
- Maker 실제 승리 검증: `BattleResult=Victory`, `LastBattleResult=Victory`, 완료 스테이지 `1`, 다음 스테이지 `2`, `runRecorded=true`
- Build Console: 중단 Error/Warning `0`; 최종 runtime Error/Warning `0`
- 다음 확장: Stage 2 전환 또는 Run Seed 생성 정책과 DataStorage 영구 저장

### 2026-07-25 — 메인 UI·대기·캐릭터 선택용 Battle Gateway

- 상태: ✅ Tested
- 새 파일:
  - `01_Combat/Resolvers/BattleGatewayLogic.mlua`
  - `01_Combat/Components/Shared/BattleEntryStateComponent.mlua`
  - `Docs/Guide/Battle-Integration-API.md`
- 외부 진입 Facade:
  - Client 동일 맵 즉시 시작: `RequestBeginBattle(...)`
  - Client 준비/이동 분리: `RequestPrepareBattleEntry(...)` → `RequestStartPreparedBattle()`
  - Server 준비/시작: `PrepareBattleEntry`, `StartPreparedBattle`, `BeginBattle`
  - 취소와 조회: `CancelBattleEntry`, `GetBattleEntrySnapshot`
- 플레이어별 Entry Snapshot: StageId, CharacterId, JobId, LoadoutId, RunSeed, EntryMode, RequestId
- 상태 흐름: `IDLE → PREPARED → STARTED`; 취소 시 `CANCELLED`
- Session 공개 초기화: Gateway 전용 `InitializeFromEntry(...)`, Server 조회용 `GetBattleSnapshot()`
- Stage 시작: 숫자 전용 `StartStage` 외에 정확한 ID를 받는 `StartStageById` 추가
- Prototype 호환: `AutoStartPrototypeBattle=true`는 기존 Play 즉시 시작 유지, 실제 UI 연동 맵은 `false` 권장
- Maker Server 검증: `BeginBattle`로 `character_test_01 / warrior / starter_loadout / seed 4321` 전달 후 `STARTED`, `PlayerTurn`, Wave `1/3`
- Maker Client RPC 검증:
  - 분리 호출 `RequestPrepareBattleEntry → RequestStartPreparedBattle` 성공
  - 단일 Facade 호출 `RequestBeginBattle` 성공
  - 최종 Snapshot `character_facade_01 / mage / facade_loadout / seed 6001`, `STARTED`, `PlayerTurn`, Wave `1/3`
- Build Console: 중단 Error/Warning `0`; 최종 runtime Error/Warning `0`
- 아직 하지 않음: StageId→Map/Instance 이동, Character/Job/Loadout 실제 전투 데이터 적용, 전투 종료 후 보상·로비 이동

### 2026-08-01 — UI 독립 Run Flow 결과 계약

- 상태: ✅ Tested (prototype fallback), 실제 `NodeDefinitions` Dataset 이관은 P0
- 새 파일: `03_Data/Repositories/NodeDefinitionRepositoryLogic.mlua`
- 상위 흐름 원본: `NodeDefinitions.NextNodeIds` 단일 원본
- 공통 결과 DTO: `NextNodeIds`, `NextContentTypes`, `NextContentIds`
  - `BATTLE/BOSS`: ContentId는 StageId
  - `SHOP/EVENT/REST`: ContentId는 NodeId
- 플레이어별 상태: `RunFlowState`, 현재 Graph/Node, 마지막 StageId, 다음 콘텐츠 옵션, Revision
- 결과 멱등 키: `RunSequence:StageId:EntryRequestId`; 같은 결과 재전달은 성공으로 무시
- 현재 HUD는 최종 UI 계약이 아닌 디버그·기능 검증 어댑터로 규정
- Maker 직접 검증:
  - `stage01` 승리 해석 → `AWAITING_NODE_SELECTION`
  - 다음 옵션 → `shop_after_stage01 / SHOP / shop_after_stage01`
  - 같은 키로 결과 2회 기록 → `Revision 3→3`, 중복 1회 무시
- Build Console Error/Warning `0`; Runtime Error/Fatal `0`
- 아직 하지 않음: 실제 `NodeDefinitions.userdataset/.csv`, 노드 선택 승인 API,
  StageReward 지급, Shop Controller, Map/Instance 이동

### 2026-08-01 — 적 드롭과 런 자동 회수 계약

- 상태: ✅ Tested (actual Dataset), fallback 비활성
- 새 파일:
  - `03_Data/Repositories/EnemyDropDefinitionRepositoryLogic.mlua`
  - `03_Data/Repositories/EnemyDropContentValidatorLogic.mlua`
  - `03_Data/Repositories/ContentReferenceResolverLogic.mlua`
  - `01_Combat/Components/Shared/BattleDropComponent.mlua`
- 실제 Definition: `EnemyDropDefinitions` 4행, `CurrencyDefinitions`의 `gold`, `ConsumableDefinitions`의 `potion_hp_small`
- 데이터 책임: Enemy 수치와 분리된 `EnemyDropDefinitions` 독립 행. `ANY_KILL`, `COMBO_KILL`, `BOSS_KILL` Trigger와 `CURRENCY`, `CONSUMABLE` 보상 타입을 규격화
- 결정성: `RunSeed + StageId + WaveIndex + SpawnOrder + UnitId + DropEntryId` 기반 판정
- 수명: 적 사망 결과는 맵 수명의 Pending Drop, 승리 시 플레이어 런 상태로 자동 회수, 패배·세션 종료 시 폐기
- 멱등성: 모든 지급에 RewardKey를 사용하며 같은 키 재전송은 성공으로 무시
- 런 상태: 재화·소모품 Snapshot, 소모품 용량, 초과분 런 재화 전환 설정, RewardRevision 제공
- 공개 API: `RunManagerLogic:GrantRunReward()`, `GetRunRewardSnapshot()` 및 `BattleSessionComponent:GetBattleSnapshot()`의 Drop 필드
- Maker 검증: 같은 Seed 판정 2회가 동일, RewardKey 중복 지급 무시, 소모품 5개 중 3개 수용·2개 골드 전환, 실제 `HandleUnitDied`에서 Pending Drop 생성, 테스트 후 Battle 재구축
- Validator 객체 경계: Repository는 로드·행 불변식, Drop Validator는 중복·교차 참조, Reference Resolver Registry는 실제 Dataset 위치와 정책을 담당하고 `ContentValidatorLogic`은 Facade만 담당
- 참조 계약: `ENEMY_DEFINITION`, `RUN_CURRENCY`, `CONSUMABLE`. 드롭 재화는 `RUN_SCOPED`만 허용해 향후 상점·메타 재화 정책과 분리
- 차단 Gate: `BattleDropComponent.ResolveEnemyDeath()`가 최초 판정 전에 캐시된 전체 검증 결과를 요구하며, 데이터 변경 테스트는 Facade의 Invalidate API를 사용
- Validator 음수 검증: 없는 Enemy/Consumable 참조와 중복 DropEntryId를 각각 `DATA_INVALID_DROP_REFERENCE`, `DATA_DUPLICATE_ID`로 차단
- 최종 양수 검증: 전체 4행 valid, `RUN_CURRENCY/gold` 참조 해결, 처치 후 골드·물약 Pending 2건 생성, 자동 회수 후 `gold~1`, `potion_hp_small~1`
- Build Console Warning/Error/Fatal `0`; 최종 Runtime Error/Fatal `0`
- Dataset 전환 검증: `EnemyDropDefinitions` 4행, `early_mushroom` 2행, `guard_mushroom` 2행, `Source=DATASET`, fallback=false, 누락 적 `NO_DROP_ENTRIES`
- 객체지향 감사 후 교정:
  - HP 초기화·피해·회복·사망을 `BattleUnitComponent` 소유 API로 캡슐화
  - 런 진행 `PlayerRunStateComponent`와 보상 인벤토리 `PlayerRunInventoryComponent` 분리
  - 오래된 Architecture Review를 역사 문서로 표시하고 현재 규격의 협력 Component 소유권으로 교정
  - `EnemyDefinitions.InitialFacingPolicy` 실제 Dataset/Repository/Spawn 적용 누락 보완
- 소모품: `potion_hp_small = HEAL 4 / SELF / BATTLE_FREEPLAY / ConsumesTurn=false`; Definition Repository → Effect Router → Heal Handler → Unit API로 실행
- Trigger: 한 사망에서 `ANY_KILL`, 큐 실행 2번째 처치부터 `COMBO_KILL`, `IsBoss=true`이면 `BOSS_KILL`을 순서대로 함께 해석
- Maker 검증: 피해 `100→97`, 물약 `97→100`, 1개 소비, 동일 UseKey 중복 무시, Full HP 사용 차단·수량 유지, 복합 Trigger 3개 해석, Client Drop/Inventory DTO 확인
- Build Warning/Error/Fatal `0`; Runtime Error/Fatal `0`
- 월드 표시 구현: `BattleDropPickup.model`과 `BattleDropPresentationComponent`를 추가하고
  코인/물약 SpriteRUID, Cell 좌표 배치, 부유 모션, 회수·폐기 시 Entity 제거를 상태 객체와 분리
- 월드 표시 Maker 검증: 코인·물약을 Cell 2/4에 생성해 `pending=2`, `visible=2`,
  두 Entity와 RUID·`TweenFloatingComponent` 유효 확인
- 표시 정리 검증: 폐기 시 `removed=2`, `pending=0`, `visible=0`, 두 Entity 무효화
- 자동 회수 검증: Cell 3의 골드 2개를 회수해 `AUTO_COLLECTED`, `currency=gold~2`,
  `visible 1→0`, `pending=0`; Build Warning/Error/Fatal 0, Runtime Error/Fatal 0
- 아직 하지 않음: 최종 Drop/Icon·소모품 UI, 계정 영구 저장

### 2026-08-01 — StageDefinitions 실제 Dataset 전환

- 상태: ✅ Tested (actual Dataset), compatibility fallback 비활성
- 실제 페어: `03_Data/StageDefinitions.userdataset/.csv`
- `stage01`: 6 Cell, 시작 Cell 2, 큐 3, WaveTable `stage01`
- Repository는 조회된 StageId의 행 수를 `MatchCount`로 제공하고 Validator가 중복 ID를 차단
- Maker 검증: `rows=1`, `source=DATASET`, `fallback=false`, `matchCount=1`, `valid=true`, `waves=3`
- 전투 세션 검증: `sessionStage=stage01`, `sessionWave=1/3`
- 존재하지 않는 Stage: `STAGE_DEFINITION_NOT_FOUND`
- Build Warning/Error/Fatal 0; 양수 회귀 Runtime Error/Fatal 0

### 2026-08-01 — SkillDefinitions·SkillEffectSteps 실제 Dataset 전환

- 상태: ✅ Tested (actual Dataset), compatibility fallback 비활성
- 실제 페어: `03_Data/SkillDefinitions.userdataset/.csv`, `SkillEffectSteps.userdataset/.csv`
- Skill 5행: 기본·빠른·강한 베기, 밀치기, 베고 밀치기
- Effect Step 5행: DAMAGE, PUSH와 DAMAGE→PUSH 2단계 조합
- Maker 검증: `skillRows=5`, `stepRows=5`, 모든 Bundle `source=DATASET`, `matchCount=1`, Validator 통과
- 실제 실행: `slash_push_combo`가 Step 1 DAMAGE `HP 6→5`, Step 2 PUSH `Cell 3→4` 순서로 처리
- Cooldown: 실행 직후 `slash_push_combo:2` 확인
- Build Warning/Error/Fatal 0; Runtime Warning/Error/Fatal 0

### 2026-08-25 — Slice 16: 도시 경로형 월드맵·클리어 게이트·노란 상점 방문

- 상태: 🟡 Implemented (UIBuilder·정적 계약 검증 완료, Maker 런타임 검증 대기)
- `PopupGroup.ui`를 양피지형 전체 화면 지도판으로 재배치하고 지정 `sprite/Object` RUID로 통일
  - 경로·상점: `7e33c3b2fa244e938d425f7b2eef68a1` (`01_yellow_button`)
  - 잠금 도시 노드: `e4c9511644314491a68cd26eecc0a47f` (`02_purple_button`)
  - 6개 도시 오브젝트·전용 명패: 헤네시스, 커닝시티, 페리온, 엘리니아, 노틸러스, 슬리피우드
  - 지도 배경·경로: `01_repaired_base_map_background`, `01_yellow_path_network`
  - 상점 창·상품 카드·제목판: `menu_bg`, `paper`, `shopslot_bg`, `gauge_titlebg` 등록 자산 재사용
- 헤네시스 `1-1` 클리어 후 위·아래 노란 상점 버튼을 동시에 해금하고 최초 선택을 서버 Run 상태의 `SelectedWorldMapBranch`에 고정
- 위쪽 상점 `UPPER`는 커닝시티 `1-2`, 아래쪽 상점 `LOWER`는 엘리니아 `1-2`로 연결하며 선택하지 않은 상점·도시는 비활성
- 페리온·노틸러스·슬리피우드는 다음 지역용 잠금 도시로 표시
- 잠금 안내, 헤네시스 `CLEAR` 배지, 진행 가이드 문구를 동기화된 플레이어 Run 상태에서 갱신
- 공식 `yellow_button` RUID `4d0973b97a1e40f79ecf586592705f76`로 선택 상점 방문 버튼과 닫기 동작 구성
- 상점 방문 패널은 다음 도시 진입 전 선택 동선이며 진행도나 전투 상태를 소비하지 않음
- 선택 도시별 이동 아바타 목표 좌표와 Battle Gateway 결과 수신 노드를 분리
- UIBuilder 계약 검증: 35 Entity, Ellinia gate/StageId/yellow_button/초기 숨김 상태 확인, schema error 0
- 남은 Verify: Maker Refresh → Build log → lobby Play → 클리어 전 잠금 → 1-1 승리 후 해금 → 상점 열기/닫기 → 엘리니아 클릭 및 전환 로그

### 2026-08-26 — 6개 마을·마을 간 상점 확장 기준

- 상태: 📋 Planned — Phase 1 이후 콘텐츠 확장 계약 확정
- 현재 Slice 16의 헤네시스 `1-1 → 상점 → 커닝시티/엘리니아` 흐름을 모든 도시 연결의 기준으로 재사용
- 현재 커닝시티/엘리니아가 헤네시스 전투 Stage를 임시 재사용하는 연결은 프로토타입 전용이며, 지역 콘텐츠 추가 시 각각 `region_02_*`, `region_03_*` 맵과 Stage 데이터로 교체
- 위쪽 경로: `헤네시스 → 상점 → 커닝시티 → 상점 → 페리온 → 상점 → 슬리피우드`
- 아래쪽 경로: `헤네시스 → 상점 → 엘리니아 → 상점 → 노틸러스 → 상점 → 슬리피우드`
- Region/MapId 규칙: 헤네시스 `region_01`, 커닝시티 `region_02`, 엘리니아 `region_03`, 페리온 `region_04`, 노틸러스 `region_05`, 슬리피우드 `region_06`
- 각 Region은 자체 `region_XX_battle`과 `region_XX_boss` 물리 맵을 가지며 같은 Region 내부 Stage만 일반전 맵을 재사용
- 각 상점은 독립 `ShopId`를 가지지만 UI는 `ShopVisitBtn`, 로직은 공통 Shop Controller를 사용
- 각 마을의 최종 전투/보스 클리어가 다음 Edge 상점 해금의 기본 조건이며, 현재 헤네시스 `1-1` 게이트는 프로토타입 예외
- 선택 경로·상점 방문·다음 도시 해금은 `PlayerRunStateComponent`의 서버 권위 상태로 관리
- 구현 완료 기준:
  - 새 도시와 상점이 UI 스크립트의 도시별 분기 추가 없이 데이터 행으로 생성·게이트됨
  - 각 도시 StageId가 다른 도시의 MapId가 아닌 자신의 `region_XX_battle/boss`로 라우팅됨
  - 각 마을 클리어 전 상점/다음 도시 클릭 차단, 클리어 후 상점 해금, 상점 방문 후 다음 도시 해금 순서가 유지됨
  - 반대 경로는 같은 Run에서 계속 잠기며 두 경로 모두 슬리피우드에 정상 합류함
