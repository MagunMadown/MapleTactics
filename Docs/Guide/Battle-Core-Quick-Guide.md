# 기본 전투 코어 간단 가이드

## 1. 현재 구현 범위

현재 전투 코어는 6칸 전투 보드에서 플레이어와 더미 적의 초기 상태를 만들고 화면 위치를 논리 셀과 맞추는 단계다.

- 플레이어: 셀 `1`, 오른쪽 방향, HP 100
- 적: 셀 `4`, 왼쪽 방향, HP 100
- 전투 시작 상태: `PlayerTurn`, 1턴; 플레이어 행동 뒤 `EnemyTurn`을 거쳐 다음 턴으로 복귀
- 셀 번호: `0`부터 `5`까지 사용
- 좌·우 한 칸 이동과 `UnitMovedEvent` 구현
- 이동 없는 방향 전환과 `UnitTurnedEvent` 구현
- 바라보는 앞 셀의 공용 공격 Hit/Miss 판정과 공격 ID가 포함된 `BasicAttackResolvedEvent` 구현
- 기본 베기 피해 3, 강한 베기 피해 6을 같은 `ApplyDamage` 경로로 적용
- 앞 셀의 대상을 한 칸 밀고 이후 타일이 변경된 보드에서 다시 타깃을 찾는 `push` 타일
- 적 모델의 머리 위에 동기화된 `HP 현재 / 최대` 월드 텍스트 표시
- 설정 가능한 색상과 지속시간을 사용하는 피격 플래시
- 공격마다 고정 ActionName·속도·지속시간을 사용하는 설정형 아바타 모션
- 기본 베기 `0.18`초, 강한 베기 `0.38`초의 공격별 타격 지연과 타격 시점 셀 재판정
- 이동·방향 전환·기본 공격이 공통으로 통과하는 서버 기준 행동 큐와 처리 중 입력 잠금
- 기본 용량 2인 가변 타일 큐에 `basic_slash`·`heavy_slash`·`push`를 순서대로 등록·실행·전체 비우기 하는 하단 중앙 `BattleQueueHUD`
- HP 0 사망 판정, `VICTORY`/`DEFEAT` 결과 고정, 현재 전투를 초기화하는 `다시 시작` 버튼
- 적이 멀면 한 칸 접근하고 인접하면 기본 공격하는 최소 Intent
- 적 Intent UI, 적 전용 모션, HP Bar, 별도 무기 이펙트는 아직 구현하지 않음

## 2. 파일 구조

```text
RootDesk/MyDesk/
├── 01_Combat/
│   └── Components/
│       └── Shared/
│           ├── BattleSessionComponent.mlua
│           ├── BattleUnitComponent.mlua
│           ├── BattleUnitPresentationComponent.mlua
│           └── BattleTileColor.mlua
│   └── Events/
│       ├── BasicAttackResolvedEvent.mlua
│       ├── UnitMovedEvent.mlua
│       └── UnitTurnedEvent.mlua
├── 05_UI/
│   └── HUD/
│       └── BattleQueueHudComponent.mlua
└── Models/
    ├── Characters/
    │   └── BattleDummyEnemy.model
    └── Objects/
        └── BattlePlatformTile.model

ui/
└── BattleQueueHUD.ui
```

`01_Combat/Components/Shared`에는 플레이어와 적이 공통으로 사용하거나 전투 맵 전체에서 사용하는 컴포넌트를 둔다. 플레이어 전용 또는 적 전용 동작이 생기면 각각 `Player`, `Enemy` 하위 폴더를 추가한다.

## 3. 컴포넌트 역할

### BattleSessionComponent

`map01` 루트에 연결된 서버 전용 전투 진행 컴포넌트다.

- 6개 셀의 좌표 계산
- 플레이어와 적 등록
- 유닛 초기 위치 배치
- 현재 전투 단계와 턴 보관
- 플레이어의 기본 자유 이동 잠금
- 플레이어 행동 접수·실행·완료와 중복 입력 거절
- `TileQueueCapacity`까지 타일을 순서대로 등록하고 전체 큐가 끝날 때까지 적 턴 전환을 보류
- `QueuedTileIds`, `ExecutingTileIds`, `ExecutingTileIndex`로 등록 큐와 실행 큐를 분리
- 두 공격이 공유하는 `TryFrontAttack → ResolveFrontAttackImpact` 모션·타깃·피해·이벤트 경로
- 플레이어 행동 완료 후 적 Intent 실행과 다음 Turn 개방
- HP 0 최초 전환의 사망·승패 확정과 현재 Entity를 재사용하는 전투 Reset

전투는 Play 시작 시 자동으로 초기화되므로 현재 단계에서는 별도로 메서드를 호출할 필요가 없다.

### BattleUnitComponent

각 전투 참가자의 논리 상태를 보관한다.

| 속성 | 의미 |
|---|---|
| `UnitId` | 전투 내부 유닛 식별자 |
| `Team` | `Player` 또는 `Enemy` |
| `CellIndex` | 현재 논리 셀 번호 |
| `Facing` | `Left` 또는 `Right` |
| `MaxHp` | 최대 HP |
| `CurrentHp` | 현재 HP |
| `IsDead` | 사망 여부 |

적에게는 맵에서 컴포넌트가 연결되어 있다. 플레이어는 런타임에 생성되므로 `BattleSessionComponent`가 자동으로 컴포넌트를 추가한다.

적 모델의 `BattleHpText` 자식은 `TextRendererComponent`를 사용한다. `BattleUnitComponent.OnSyncProperty`가 `CurrentHp` 또는 `MaxHp` 변경을 감지하면 `HP 97 / 100` 형태로 갱신한다. HP의 원본은 텍스트가 아니라 항상 `CurrentHp`다.

### BattleUnitPresentationComponent

전투 수치와 분리된 클라이언트 표현 설정을 보관한다. 현재는 HP 텍스트, 피격 플래시와 공격별 아바타 모션 재생을 담당한다. 표현을 바꿀 때 피해·타깃 판정 로직을 수정하지 않는다.

플레이어는 런타임 생성 Entity이므로 `BattleSessionComponent`가 표현 컴포넌트를 자동으로 추가한다. 모든 공격 모션은 `PlayCombatMotion(unitId, motionKey, actionName, playRate, duration)`을 통과한다.

- `actionName=""`: 장착 무기에 맞는 기본 `Attack` Body Action 재생
- `actionName="swingO2"`처럼 지정: 해당 액션을 `ActionStateChangedEvent`의 일회성 동작으로 재생
- `motionKey`: 로그와 콘텐츠 식별에 사용하는 공격별 모션 ID
- `playRate`, `duration`: 공격마다 별도로 설정하는 재생 속도와 복귀 시간
- 재생이 끝나면 `CombatMotionReturnState`와 `Stand` Body Action으로 복귀

현재 `basic_slash`의 설정은 `BattleSessionComponent.BasicSlashMotionKey`, `BasicSlashActionName`, `BasicSlashMotionPlayRate`, `BasicSlashMotionDuration`, `BasicSlashImpactDelay`에서 교체할 수 있다. `BasicSlashActionName`은 `swingO1`로 고정되어 같은 타일을 반복해도 같은 모션을 재생한다. 예를 들어 다른 스킬의 ActionName을 `swingO2`로 지정하면 피해 로직과 분리된 다른 모션을 사용할 수 있다.

`ImpactDelay`는 모션 시작 후 실제 셀 판정과 피해가 발생할 때까지의 시간이다. 기본 베기는 `0.18`, 강한 베기는 `0.38`이며 반드시 해당 공격의 `MotionDuration`과 `ActionDuration`보다 짧게 둔다. 이 값만 조정하면 애니메이션에서 무기가 닿는 프레임과 피해 시점을 맞출 수 있다.

커스텀 액션 이름은 실제 아바타가 지원하는 Action ID여야 한다. 활의 `shoot1`처럼 장비가 필요한 자세는 모션뿐 아니라 해당 무기도 장착해야 자연스럽게 표시된다.

### BattleTileColor

각 `BattleCell`의 `PixelRendererComponent`를 단색으로 채우는 클라이언트 표시용 컴포넌트다. 전투 판정에는 관여하지 않는다.

### BattleQueueHudComponent

`BattleQueueHUD.ui`에 연결된 클라이언트 UI 컴포넌트다. `BattleSessionComponent`의 동기화 속성을 읽어 `TURN`, 등록 타일, Phase와 처리 상태를 표시하고, 버튼 클릭을 서버 요청으로 전달한다. 전투 판정은 계속 `BattleSessionComponent`가 담당하므로 UI 이미지·색상·배치를 교체해도 피해 규칙은 바뀌지 않는다.

- `기본 공격 타일`: 남은 슬롯에 `basic_slash` 추가
- `강한 베기 타일`: 남은 슬롯에 `heavy_slash` 추가
- `밀치기 타일`: 남은 슬롯에 `push` 추가
- `실행`: 등록 순서대로 모든 타일 실행
- `전체 비우기`: 턴을 소비하지 않고 등록된 타일 전부 제거

버튼 활성 상태도 동기화된다. 플레이어 턴에는 큐가 가득 차기 전까지 타일을 계속 추가할 수 있고, 한 개 이상 등록되면 실행·전체 비우기 버튼을 사용할 수 있다. 기본 `TileQueueCapacity=2`이며 이 값을 3 이상으로 바꿔도 큐 저장·검증·순차 실행과 HUD의 `현재/용량` 표시는 그대로 확장된다.

적 HP가 0이 되면 적 Sprite와 HP 텍스트가 숨겨지고 중앙에 `VICTORY`와 `다시 시작` 버튼이 나타난다. 플레이어 HP가 0이면 `DEFEAT`가 표시된다. Reset 후 결과 패널은 다시 숨겨지고 양쪽 HP 100, 시작 셀, 시작 방향, Turn 1로 복원된다.

## 4. 셀과 화면 좌표

논리 위치의 원본은 `TransformComponent.Position`이 아니라 `BattleUnitComponent.CellIndex`다.

```text
CellIndex:  0      1      2      3      4      5
World X:  -2.80  -1.68  -0.56   0.56   1.68   2.80
```

좌표 계산식은 다음과 같다.

```text
WorldX = -2.8 + CellIndex × 1.12
WorldY = 0.12
```

앞으로 이동이나 밀치기를 구현할 때는 먼저 `CellIndex`를 검증하고 변경한 다음 화면 위치를 갱신해야 한다. 화면의 Transform 값을 읽어서 전투 셀을 판단하지 않는다.

## 5. Maker에서 확인하는 방법

1. Maker가 편집 모드인지 확인한다.
2. Workspace Refresh를 실행한다.
3. Build Console 오류가 0건인지 확인한다.
4. Play를 실행한다.
5. Console에서 다음 로그를 확인한다.

```text
[BattleSession] unit registered id=enemy_01 team=Enemy cell=4
[BattleSession] unit registered id=player_01 team=Player cell=1
[BattleSession] ready phase=PlayerTurn turn=1
```

`PlayerControllerComponent`의 자유 이동은 비활성화되어 있다. 화면 하단에서는 `기본 공격 타일 → 실행` 순서로 공격할 수 있다. `비우기`는 등록만 취소하고 턴을 넘기지 않는다.

다음 키는 개발 중 회귀 확인을 위한 즉시 실행 단축키로 유지한다.

- 왼쪽: `LeftArrow` 또는 `A`
- 오른쪽: `RightArrow` 또는 `D`
- 방향 전환: `Space`
- 기본 공격 판정: `F`

이동 성공 시 `CellIndex`와 월드 위치가 함께 변경되고 `UnitMovedEvent`가 발생한다. 보드 밖이나 다른 생존 유닛이 점유한 셀로는 이동할 수 없다.

카메라는 플레이어 카메라의 오프셋을 이동마다 보정하지 않는다. `BattleCameraAnchor`의 고정 카메라로 한 번 전환한 뒤 6칸 보드의 X 중심을 계속 바라보므로, 플레이어가 셀 사이를 이동해도 화면이 따라갔다 돌아오지 않는다.

방향 전환은 셀을 이동하거나 턴을 넘기지 않고 `Facing`만 `Left`/`Right`로 바꾼다. 기본 아바타는 `PlayerControllerComponent.LookDirectionX`를 통해 같은 방향으로 표시되며, 성공하면 `UnitTurnedEvent`가 발생한다.

기본 공격은 모션을 먼저 시작하고 `BasicSlashImpactDelay=0.18`초 뒤 현재 `CellIndex`와 `Facing`을 다시 읽어 바로 앞 한 셀을 검사한다. 적이 있으면 `HIT`와 함께 `ApplyDamage`가 적 HP를 3 감소시키고, 빈 셀이면 `MISS_EMPTY`, 보드 바깥이면 `MISS_OUT_OF_BOUNDS`로 해결된다. 강한 베기도 같은 경로를 사용하지만 `HeavySlashImpactDelay=0.38`초와 피해 6을 사용한다. 따라서 화면 Sprite나 Collider가 겹치는지가 아니라 타격 시점의 논리 타일 점유가 피해를 결정한다. Miss도 유효한 행동이므로 적 행동으로 이어지고 턴을 소비한다.

밀치기는 `PushImpactDelay=0.18`초 뒤 현재 앞 셀을 다시 찾고, 대상의 `CellIndex`를 바라보는 방향으로 한 칸 이동한다. 목적지가 보드 밖이면 `PUSH_BLOCKED_OUT_OF_BOUNDS`, 다른 생존 유닛이 점유하면 `PUSH_BLOCKED_OCCUPIED`로 위치를 유지한다. 밀치기 자체는 피해를 주지 않으며 성공한 이동은 기존 `UnitMovedEvent`를 발행한다.

적 머리 위 HP 텍스트는 공격 적중 후 `100 / 100 → 97 / 100`처럼 자동 갱신된다. 적 Entity의 자식이므로 이후 적이 이동하더라도 같은 상대 위치를 따라간다.

키보드의 즉시 행동 요청은 `TryQueuePlayerAction`을 통과한다. 타일 큐 실행은 등록 문자열을 `ExecutingTileIds`로 동결한 뒤 `ExecutingTileIndex`를 한 칸씩 증가시키며 각 타일의 Resolve와 모션 시간을 끝까지 기다린다. 마지막 타일까지 끝난 뒤에만 `EnemyTurn`으로 전환되고, `0.25`초의 짧은 판단 시간 뒤 적 행동 하나가 실행된다. 적 행동까지 끝나면 `TurnNumber`가 1 증가하고 `PlayerTurn`으로 돌아오며 입력 잠금이 해제된다.

화면 하단의 `BattleQueueHUD`는 `빈 큐 (0/2)`, `[밀치기] → [기본 베기] (2/2)`처럼 전체 순서를 표시한다. 실행 중인 타일에는 `▶`가 붙고 상태 문구에는 현재 실행 인덱스가 표시된다. 등록된 타일이 있을 때 키보드 즉시 행동은 `TILE_QUEUE_OCCUPIED`로 거절된다.

현재 적 Intent는 두 종류뿐이다. 플레이어와 거리가 두 칸 이상이면 플레이어 방향으로 한 칸 이동하고, 바로 옆 셀이면 같은 `TryBasicAttack → ApplyDamage` 경로로 플레이어를 공격한다. 별도 BT나 범용 AI 프레임워크는 아직 만들지 않았다.

대표 재타깃 순서는 `push|basic_slash`다. 플레이어 Cell 1, 적 Cell 2에서 실행하면 밀치기가 적을 Cell 3으로 옮긴다. 두 번째 기본 베기는 큐 등록 당시의 적을 기억하지 않고 현재 앞 셀인 Cell 2를 다시 검사하므로 `MISS_EMPTY`가 된다.

HP가 0이 되면 `ApplyDamage → HandleUnitDied`가 한 번만 실행되고 `BattlePhase=BattleEnded`, `BattleResult=Victory/Defeat`로 고정된다. 이 상태에서는 다음 적 행동이나 Turn 증가가 발생하지 않는다. `다시 시작`은 새 Entity를 Spawn하지 않고 기존 플레이어와 적의 전투 상태를 초기화한다.

## 6. 다음 기능을 추가할 때

현재 타일 행동 처리 흐름은 다음과 같다.

```text
기본 공격 타일 버튼
→ RequestQueueTile("basic_slash")
→ TryQueueTile이 남은 용량과 PlayerTurn 검사 후 순서대로 추가
→ 실행 버튼 / RequestExecuteQueuedTile()
→ 등록 큐를 ExecutingTileIds로 동결
→ ExecutingTileIndex의 타일을 기존 공격 행동으로 변환
→ 공격 모션·ImpactDelay·타격 시점 재판정·Event까지 완료
→ 다음 인덱스를 같은 방식으로 실행
→ 마지막 타일까지 완료된 뒤 EnemyTurn 시작
→ BuildEnemyIntent가 MOVE 또는 BASIC_ATTACK 선택
→ 적 행동 완료 후 TurnNumber 증가
→ PlayerTurn 복귀와 입력 잠금 해제
```

다른 스크립트가 `CellIndex`, HP, 턴을 직접 변경하지 않도록 한다. 전투 상태 변경은 항상 `BattleSessionComponent` 또는 이후에 추출될 전용 Resolver를 통해 수행한다.

큐를 통과한 이동 결과는 다음 로그로 확인한다.

```text
[BattleInput] move requested direction=1
[BattleQueue] queued action=MOVE direction=1
[BattleQueue] started action=MOVE direction=1
[BattleMove] success unit=player_01 from=1 to=2 x=-0.56
[BattleEvent] UnitMovedEvent received unit=player_01 from=1 to=2
[BattleQueue] completed action=MOVE success=true reason=OK
```

공격 타일의 등록·실행·비우기는 다음 로그로 확인한다.

```text
[BattleTileQueue] registered tile=basic_slash turn=2
[BattleTileQueue] executed tile=basic_slash action=BASIC_ATTACK turn=2
[BattleTileQueue] cleared tile=basic_slash turn=2
```

`registered` 뒤에는 실행 또는 비우기 중 하나만 발생한다. 타일이 등록된 동안 이동·방향 전환·즉시 공격을 요청하면 `[BattleQueue] rejected ... reason=TILE_QUEUE_OCCUPIED`가 남는다.

방향 전환은 다음 로그로 확인한다.

```text
[BattleInput] turn requested
[BattleTurn] success unit=player_01 from=Right to=Left cell=1
[BattleEvent] UnitTurnedEvent received unit=player_01 from=Right to=Left
```

기본 공격 판정은 다음 로그로 확인한다.

```text
[BattleInput] basic attack requested
[BattleQueue] queued action=BASIC_ATTACK direction=0
[BattleQueue] started action=BASIC_ATTACK direction=0
[BattleMotion] started unit=player_01 motion=basic_slash mode=CUSTOM_ACTION action=swingO1 rate=1 duration=0.45
[BattleImpact] scheduled attack=basic_slash delay=0.18
[BattleImpact] triggered attack=basic_slash elapsed=0.19
[BattleDamage] applied source=player_01 target=enemy_01 amount=3 hp=100->97
[BattleAttack] resolved attack=basic_slash source=player_01 facing=Right target=enemy_01 cell=2 hit=true reason=HIT damage=3 hp=100->97
[BattleEvent] BasicAttackResolvedEvent attack=basic_slash source=player_01 target=enemy_01 cell=2 hit=true reason=HIT damage=3 hp=100->97
[BattlePresentation] hp refreshed unit=enemy_01 text=HP 97 / 100
[BattlePresentation] hit flash started unit=enemy_01 duration=0.18
[BattlePresentation] hit flash restored unit=enemy_01
[BattleQueue] completed action=BASIC_ATTACK success=true reason=IMPACT_PENDING
[BattleMotion] restored unit=player_01 motion=basic_slash state=IDLE
```

행동 자체가 유효하지 않으면 `OUT_OF_BOUNDS`, `CELL_OCCUPIED`, `INVALID_PHASE`, `UNIT_DEAD` 등의 이유로 큐가 즉시 비워지고 적 턴도 시작하지 않는다. 처리 중 다시 입력하면 `[BattleQueue] rejected ... reason=ACTION_PROCESSING` 로그가 남고 두 번째 행동은 실행되지 않는다.

한 턴의 전체 순서는 다음 로그로 확인한다.

```text
[BattleQueue] completed action=BASIC_ATTACK success=true reason=HIT
[BattleTurnFlow] phase=EnemyTurn turn=3
[BattleEnemy] intent action=BASIC_ATTACK direction=0 reason=PLAYER_ADJACENT
[BattleDamage] applied source=enemy_01 target=player_01 amount=3 hp=100->97
[BattleEnemy] completed action=BASIC_ATTACK success=true reason=HIT
[BattleTurnFlow] phase=PlayerTurn turn=4
```

사망과 Reset은 다음 로그로 확인한다.

```text
[BattleDeath] unit=enemy_01 cause=DAMAGE result=Victory
[BattleResult] result=Victory turn=2
[BattleReset] completed turn=1 playerCell=1 enemyCell=4
```

## 7. 파일 작업 주의사항

- `.mlua` 파일을 변경하거나 이동한 뒤에는 Maker Refresh가 필요하다.
- `.codeblock`과 `.directory`는 Maker가 자동 생성하므로 직접 수정하지 않는다.
- `map01`은 현재 `MapleTile(0)`이며 플레이어 물리는 `RigidbodyComponent` 계열을 사용한다.
- 스크립트 참조 이름은 폴더 경로와 무관하게 `script.BattleSessionComponent`처럼 파일 이름을 사용한다.

## 8. 개인별 로그라이크 확장

개인별 로그라이크의 맵·런 수명과 컴포넌트 책임은 [`Solo-Roguelike-Architecture.md`](Solo-Roguelike-Architecture.md)를 따른다.
