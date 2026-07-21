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
- 기본 전투 보드: 화면 중앙에 7개 논리 셀
- 권장 초기 배치: Player Cell 1, Enemy Cell 5
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

- ⬜ 상태: Not started
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

## 5. 이후 Phase로 넘길 것

Phase 1이 모두 검증된 뒤 다음 순서로 확장한다.

1. 타일 쿨다운과 FreePlay
2. 일반 적 Pattern 데이터
3. UserDataSet/CSV 이전과 Validator
4. 스테이지 시작/승리/다음 스테이지
5. 증강 3택
6. 직업과 콘텐츠 수량 확장
7. 연출, 저장, 재접속

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
- 표시 컴포넌트: `05_UI/HUD/BattleQueueHudComponent.mlua`
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

- 기본 용량: `TileQueueCapacity=2`; 값 변경만으로 3칸 이상 확장
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
