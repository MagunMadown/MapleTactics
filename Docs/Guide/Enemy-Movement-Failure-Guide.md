# 적 이동 실패 규격

## 게임 규칙

적이 이동하려는 칸이 다른 유닛에게 점유됐거나 보드 밖이면 해당 행동은 `WAIT`로 소비한다.
반대 방향의 빈칸을 다시 찾지 않으며, 현재 Cell과 Facing을 유지한다.

이 규칙은 다음 Action에 동일하게 적용한다.

- `MOVE_TOWARD`
- `MOVE_AWAY`
- `MOVE_FIXED_FACING`

## 개발 계약

각 Action은 먼저 `TryMove` 또는 `TryMoveAway`를 호출한다. 공간 실패 결과만
`ConvertBlockedEnemyMoveToWait`가 공통 결과로 변환한다.

```text
Success = true
Reason = WAIT_CELL_OCCUPIED | WAIT_OUT_OF_BOUNDS
WasBlocked = true
BlockedReason = CELL_OCCUPIED | OUT_OF_BOUNDS
OriginalActionType = 원래 이동 Action
FromCell / ToCell = 시도한 Cell
```

Turn Snapshot의 Action은 `ENEMY_WAIT`, Direction은 `0`이다. Pattern Runner에서는 행동을
소비한 성공으로 취급하므로 `NextStepOnSuccess`로 이동한다.

## 대기로 바꾸지 않는 실패

다음 오류는 데이터나 실행 흐름 문제이므로 숨기지 않고 실패로 유지한다.

- `INVALID_DIRECTION`
- `UNIT_NOT_FOUND`, `UNIT_COMPONENT_MISSING`, `UNIT_DEAD`
- `INVALID_PHASE`
- 상태 변경 API 자체의 실패

## 필수 회귀

1. `MOVE_TOWARD` 앞칸 점유: Cell/Facing 불변, `WAIT_CELL_OCCUPIED`.
2. `MOVE_AWAY` 준비 후 실행 직전 점유: Cell/Facing 불변, `WAIT_CELL_OCCUPIED`.
3. 보드 끝 이동: Cell/Facing 불변, `WAIT_OUT_OF_BOUNDS`.
4. 정상 빈칸 이동: 한 Cell 이동하고 기존 성공 Event 발생.
5. 적 라운드 종료 후 PlayerTurn과 다음 Pattern Step 정상 전환.

2026-08-02 Maker에서 추적 이동 점유 실패와 후퇴 이동 준비 후 점유 변경을 검증했다.
