# 개인별 로그라이크 구조 가이드

## 1. 확정 방향

MapleTactics는 여러 플레이어가 하나의 전투를 공유하는 멀티플레이 게임이 아니라, 각 플레이어가 자신의 전투와 진행 상태를 가지는 개인별 로그라이크로 구성한다.

핵심 원칙은 수명에 따라 상태를 분리하는 것이다.

```text
플레이어의 한 번의 Run
├── RoguelikeRunComponent    맵을 넘어 유지되는 개인 진행
│   ├── 현재 스테이지
│   ├── 덱과 공격 타일
│   ├── 보유 증강
│   ├── Run Seed
│   └── Run 종료 여부
│
└── 각 전투 맵
    └── BattleSessionComponent
        ├── 현재 턴과 전투 단계
        ├── 해당 맵의 유닛
        ├── 이동·공격 판정
        └── 승리·패배
```

## 2. 컴포넌트 책임

### RoguelikeRunComponent

플레이어 엔티티에 붙는 개인 Run 상태 컴포넌트다. 플레이어 엔티티가 맵을 이동해도 유지되므로 스테이지 사이에 이어져야 하는 값을 보관한다.

- 현재 스테이지 번호
- 선택한 직업
- 덱과 공격 타일
- 획득한 증강
- Run Seed와 난수 진행 상태
- Run 보상과 종료 상태

이 컴포넌트는 실제로 두 번째 스테이지 이동을 구현할 때 만든다. 현재 단일 전투 단계에서는 미리 만들지 않는다.

### BattleSessionComponent

각 전투 맵 루트에 붙는 맵 수명 컴포넌트다. 맵이 종료되면 해당 전투 상태도 함께 끝난다.

- Stage 설정 읽기
- 플레이어와 적 등록
- 턴과 전투 단계 진행
- 행동 요청 검증
- 이동·공격·사망 처리 순서 조정
- 승리 시 Run 컴포넌트에 결과 전달

map01, map02, map03은 같은 스크립트 타입을 사용하고 맵별 설정값만 다르게 가진다.

### BattleUnitComponent

전투에 참가한 플레이어와 적의 현재 셀, 방향, HP, 사망 상태를 보관한다. 전투가 끝나면 적의 상태는 폐기하며, 플레이어의 장기 진행 값은 Run 컴포넌트에만 남긴다.

### BattleHUDController

`ui/` 아래에 두는 클라이언트 전용 표시 컴포넌트다.

- 현재 턴과 전투 단계 표시
- 플레이어와 적 HP 표시
- 이동·회전·공격 입력 전달
- 승리 후 증강 선택 화면 표시

UI가 HP나 셀을 직접 변경해서는 안 된다. UI는 서버의 `BattleSessionComponent`에 행동을 요청하고 동기화된 결과만 표시한다.

## 3. 맵 구성

권장 구성은 정적 로비와 개인 전투용 Instance Map을 분리하는 것이다.

```text
정적 로비 맵
→ Run 시작
→ 플레이어 전용 Instance Room 입장
→ Instance 전투 map01
→ 보상 선택
→ Instance 전투 map02
→ 보상 선택
→ Instance 전투 map03 또는 보스
→ Run 종료
```

Instance Room 안에서는 각 플레이어의 전투 맵과 `BattleSessionComponent`가 다른 플레이어와 섞이지 않는다.

현재 `map01`은 `IsInstanceMap=false`인 화면·전투 프로토타입이다. 기본 전투 루프를 검증하는 동안에는 그대로 유지한다. 실제 스테이지 이동을 구현하기 전에 다음 중 하나를 확정한다.

1. 현재 map01을 첫 Instance 전투 맵으로 전환한다.
2. map01을 테스트 맵으로 남기고 실제 Instance 전투 맵을 별도로 만든다.

맵 전환은 지형과 시작 흐름에 영향을 주므로 이동·공격 수직 슬라이스가 안정된 뒤 진행한다.

## 4. 맵별 Stage 설정

같은 `BattleSessionComponent`를 여러 맵에 재사용하되 맵 인스턴스마다 다음 값을 다르게 설정한다.

```text
StageId
CellCount
CellStartX
CellSpacing
UnitY
PlayerStartCell
EnemyStartCell
TurnLimit
```

초기에는 맵 컴포넌트 속성으로 설정한다. 스테이지가 3개 이상이 되어 반복 데이터가 생기면 `StageDefinition` 또는 Dataset으로 이동한다.

map02 예시:

```text
StageId         = "stage02"
CellCount       = 8
PlayerStartCell = 0
EnemyStartCell  = 6
TurnLimit       = 10
```

현재 `BattleSessionComponent`에는 일부 값만 존재하며 `StageId`, `TurnLimit`, 복수 적 목록은 아직 없다. 실제 map02를 만들 때 필요한 값부터 추가한다.

## 5. 상태 변경 흐름

```text
BattleHUDController 또는 플레이어 입력
→ BattleSessionComponent에 행동 요청
→ 서버에서 턴·범위·점유·생존 상태 검증
→ BattleUnitComponent 상태 변경
→ 화면 위치와 @Sync 값 갱신
→ UI가 결과 표시
```

장기 진행은 다음 흐름을 사용한다.

```text
BattleSession 승리 판정
→ RoguelikeRunComponent에 스테이지 결과 기록
→ 증강 선택
→ 다음 Instance 전투 맵 입장
→ 새 BattleSession 생성
→ 기존 Run 상태를 읽어 전투 초기화
```

## 6. 구현 순서

개인 Run 시스템을 먼저 크게 만들지 않고 현재 화면 중심 Slice를 계속 진행한다.

1. 한 칸 이동
2. 방향 전환
3. 기본 공격과 HP
4. 사망과 리셋
5. 적 Intent
6. 완전한 턴 루프
7. map02용 Stage 설정 분리
8. RoguelikeRunComponent와 Instance Map 흐름
9. 증강 선택과 다음 스테이지 연결

이 순서를 따르면 전투 규칙이 안정되기 전에 Run, 저장, Dataset 구조가 커지는 것을 막을 수 있다.

## 7. 피해야 할 구조

- `BattleSessionComponent`에 덱, 증강, 저장 데이터를 모두 넣지 않는다.
- 전역 `@Logic` 하나에 모든 플레이어의 개인 Run을 단일 값으로 저장하지 않는다.
- UI에서 전투 상태를 직접 변경하지 않는다.
- 이전 맵의 `BattleSessionComponent` 참조를 다음 맵까지 보관하지 않는다.
- 스테이지 하나만 있는 시점에 범용 Stage Registry를 먼저 만들지 않는다.
