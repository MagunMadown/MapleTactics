# 전투 조작감 개선 STEP 3 — 입력 반응과 행동 Lock

## 구현 원칙

- 새로운 전투 상태 머신을 만들지 않는다.
- 서버의 `BattleTurnComponent.BattlePhase`, `IsActionProcessing`, `QueuedActionType`, `ExecutingTileIds`, `QueuedTileCount`가 계속 유일한 규칙 근거다.
- UI에 필요한 상태명은 위 권위 상태에서 읽기 전용으로 파생한다.
- 서버 Lock 전에 생기는 짧은 동기화 틈만 `BattleHudPresenterLogic.PendingLocalCommand` 하나로 닫는다.
- 다음 턴 입력 Buffer는 적용하지 않았다. 적 턴 중 입력을 저장하면 오래전에 누른 키가 다음 턴에 실행될 수 있으므로, 이번 단계에서는 즉시 거절 피드백이 더 안전하다.

## 파생 플레이어 상태

| 표시 상태 | 기존 상태 근거 |
|---|---|
| `READY` | PlayerTurn, 처리 중 아님, 준비 Queue 없음 |
| `MOVING` | PlayerTurn, 처리 중, 즉시 행동이 MOVE |
| `TURNING` | PlayerTurn, 처리 중, 즉시 행동이 TURN |
| `PREPARING_ATTACK` | PlayerTurn, 처리 중 아님, 준비 Queue 있음 |
| `EXECUTING_ATTACK` | PlayerTurn, 처리 중, 실행 Queue 있음 |
| `WAITING_ENEMY_TURN` | PlayerTurn이 아님 |
| `LOCKED` | 전투 종료·Content 검증 실패·기타 처리 상태 |

`ResolvePlayerActionState`는 상태를 소유하거나 전환하지 않고 기존 값을 읽어 이름만 정한다.

## 즉시 입력 피드백

1. Move, Turn, Queue Tile, Execute 입력이 들어오면 Presenter가 현재 권위 상태를 읽는다.
2. 허용 입력은 같은 프레임에 `INPUT_RECEIVED` UI 이벤트를 내보낸다.
3. HUD는 상태 문구를 `입력 확인`으로 바꾸고 스킬·Execute·Clear 버튼을 즉시 잠근다.
4. 첫 입력의 서버 결과 또는 권위 상태 변경 전까지 추가 입력은 `LOCAL_INPUT_PENDING`으로 차단한다.
5. 서버의 기존 `TryReserveImmediateAction` 또는 `TryFreezeSkillQueue`가 최종 Lock을 다시 검증한다.
6. 서버 결과가 오면 로컬 Pending을 해제한다. 결과가 유실된 경우 0.40초 안전 타임아웃으로 로컬 Lock만 해제하며, 서버 Lock 규칙은 그대로 남는다.

## 방향 전환

- Space 입력이 로컬 검증을 통과하면 `PlayerControllerComponent.LookDirectionX`만 즉시 반전한다.
- `BattleUnitComponent.Facing`은 클라이언트에서 변경하지 않는다.
- 서버가 기존 `TryTurn`으로 논리 Facing과 턴 소비를 처리한다.
- 서버는 처리 직후 `ConfirmLocalPlayerFacing`으로 권위 Facing을 다시 전달하여 승인 또는 롤백한다.

## 중복 행동 방지 경로

| 상황 | 1차 방어 | 2차 방어 | 결과 |
|---|---|---|---|
| 이동키 연타 | Presenter Pending MOVE | `TryReserveImmediateAction.IsActionProcessing` | 첫 입력만 서버 행동 가능 |
| Execute 연타 | 버튼 즉시 Disable + Presenter Pending | `TryFreezeSkillQueue.IsActionProcessing` | Queue 실행 한 번 |
| 공격 준비 직후 이동 | Pending QUEUE_TILE | Queue 등록이 시작한 EnemyTurn | 이동 실행 안 됨 |
| Execute 직후 이동 | Pending EXECUTE_QUEUE | 실행 Queue의 IsActionProcessing | 이동 실행 안 됨 |
| 적 행동 종료 직전 이동 | WAITING 상태에서 즉시 거절 표시 또는 READY 동기화 후 한 번 승인 | 서버 Phase 검사 | 중복 턴 없음 |

## 변경하지 않은 규칙

- Cell 목적지와 점유 검사
- MOVE 및 TURN 턴 소비 위치
- 스킬 Queue 등록 턴 소비
- Execute Queue 순서와 공격 명중
- 적 AI와 적 행동 순서
- `BattleTurnComponent` 구현
- 스킬 데이터와 `.ui` 구조

## 검증 진행표

| 항목 | 상태 |
|---|---|
| 세 변경 파일 mLua 진단 | 통과 — 오류 0, 경고 0 |
| Git whitespace 검사 | 통과 |
| 변경 범위 | Session·Presenter·기존 HUD 스크립트만 변경 |
| 이동키 빠른 연타 | 정적 이중 Lock 확인, Maker Play Test 필요 |
| 빠른 방향 전환 | 로컬 Preview + 서버 Confirm 확인, Maker Play Test 필요 |
| 공격 준비 직후 이동 | 정적 이중 Lock 확인, Maker Play Test 필요 |
| 공격 실행 직후 이동 | 정적 이중 Lock 확인, Maker Play Test 필요 |
| 적 행동 종료 직전 이동 | 정적 Phase 경계 확인, Maker Play Test 필요 |

현재 세션에는 Maker Play·keyboard_input·logs 도구가 연결되지 않아 런타임 정상 동작을 주장하지 않는다.
