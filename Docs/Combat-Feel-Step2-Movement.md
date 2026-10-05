# 전투 조작감 개선 STEP 2 — 플레이어 한 칸 이동

## 구현 범위

- 변경 파일: `RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua`
- 플레이어의 기존 논리 Cell 확정, 목적지 계산, 이동 가능 여부, 턴 소비, 적 행동 흐름은 유지한다.
- 플레이어 월드 위치 표현만 서버 `OnUpdate`에서 짧게 보간한다.
- 적 이동은 기존 `PlaceEntity` 경로를 그대로 사용한다.
- Rigidbody Force나 물리 속도를 사용하지 않는다. 전투 진입 때 비활성화된 기본 PlayerController 위에서 기존 `MovementComponent:SetPosition` 배치 경로만 반복 호출한다.

## 조절값

| Inspector 속성 | 기본값 | 동작 |
|---|---:|---|
| `MoveActionDuration` | `0.24` | 플레이어 이동(점프) 표현과 기존 MOVE 액션 잠금 시간. 런타임 적용값은 `0.10~0.35`초로 제한한다. |
| `MoveCurve` | `QUAD_EASE_OUT` | 적 이동 보간 Curve. 빠르게 반응하고 목적지 직전에 감속한다. `LINEAR`, `SMOOTH_STEP`, `QUAD_EASE_IN_OUT`도 선택할 수 있다. 알 수 없는 값은 기본 Ease Out으로 처리한다. |
| `PlayerMoveCurve` | `LINEAR` | 플레이어 이동 보간 Curve. 점프 포물선 아래에서 일정한 속도로 가로 이동해야 점프처럼 보인다. 선택지는 `MoveCurve`와 같다. |
| `MoveSnapThreshold` | `0.01` | 목적지까지 남은 X/Y 거리가 모두 임계값 이하면 셀 중앙으로 즉시 스냅한다. |

## 기존 규칙 보존 근거

1. `TryMove`의 경계, 점유, 생존, 팀 턴, 직업 Mechanic 검사를 변경하지 않았다.
2. `BattleUnitComponent.ApplyCellChange(result.ToCell)`의 위치와 실행 시점을 변경하지 않았다.
3. Drop 수집과 `UnitMovedEvent`는 기존처럼 논리 이동 성공 직후 실행한다.
4. `CompleteQueuedAction`에서 `BeginEnemyTurn`으로 넘어가는 기존 턴 소비 지점을 변경하지 않았다.
5. MOVE 액션의 기본 타이머는 `0.24`초다(점프 높이 `PlayerHopHeight = 0.30`).
6. `BattleTurnComponent.TryReserveImmediateAction`의 `IsActionProcessing` 잠금을 변경하지 않아 연타 중 두 번째 입력은 계속 `ACTION_PROCESSING`으로 거절된다.
7. 적 AI와 적 이동 코드는 수정하지 않았다.

## 이동 표현 흐름

1. 기존 서버 검증 통과
2. 기존 `ApplyCellChange`로 논리 Cell 확정
3. 시작 Cell 중앙으로 한 번 정렬
4. `OnUpdate`에서 Curve가 적용된 월드 좌표 보간
5. Snap Threshold 또는 Duration 도달 시 목적 Cell 중앙으로 정확히 배치
6. 기존 MOVE 액션 타이머가 끝날 때 한 번 더 목적 Cell 중앙 배치를 보장
7. 기존 `CompleteQueuedAction`이 적 턴 시작

## 검증 진행표

| 항목 | 상태 | 근거 |
|---|---|---|
| 변경 범위 | 통과 | 전투 Session 스크립트와 이 문서만 변경. Turn/AI/Skill/UI 파일 변경 없음 |
| mLua 정적 진단 회귀 | 통과 | 변경 브랜치와 기준 develop 모두 진단 58개/오류 2개로 동일. 기존 `KeyDownEvent` 환경 진단만 존재 |
| Git whitespace 검사 | 실행 예정 | 커밋 전 `git diff --check` 수행 |
| A 한 번 = 왼쪽 한 칸 | Maker Play Test 필요 | 현재 세션에 Maker Play/keyboard/log 도구가 연결되지 않음 |
| D 한 번 = 오른쪽 한 칸 | Maker Play Test 필요 | 동일 |
| 연타 시 두 칸 이동 방지 | 정적 경로 확인, Maker Play Test 필요 | 기존 `IsActionProcessing` 잠금 유지 |
| 이동 후 턴/적 행동 | 정적 경로 확인, Maker Play Test 필요 | 기존 `CompleteQueuedAction` → `BeginEnemyTurn` 유지 |
| 위치 오차 없음 | 정적 경로 확인, Maker Play Test 필요 | Visual 완료 및 Action 완료에서 `GetCellPosition(toCell)`로 강제 스냅 |

## 런타임 로그

- 시작: `[BattleMoveVisual] started ...`
- 완료 및 정확한 목표 좌표: `[BattleMoveVisual] completed ... snappedX=... snappedY=...`

Maker에서 Play Test할 때 위 로그 사이에 한 번의 MOVE만 발생하는지와, 완료 좌표가 해당 Cell의 `GetCellPosition` 값과 같은지 확인한다.
