# Combat Feel STEP 7 — Turn Transition Tempo

## 변경 범위

- 턴 소비, 적 계획, 행동 순서, 데미지 및 쿨다운 규칙은 변경하지 않았다.
- 플레이어 행동의 기존 완료 경계에서만 첫 적 행동 전 전환 비트를 시작한다.
  - 즉시 행동 완료: `CompleteQueuedAction`
  - 스킬 예약 완료: `TryQueueSkillTile`의 성공 스냅샷
  - 공격 Queue 완료: `CompleteTileQueueExecution`
  - 턴 소비 아이템 완료: `TryUseConsumable`의 저장 성공 이후
- 마지막 적 행동의 기존 완료 경계인 `CompleteEnemyTurn`에서만 플레이어 입력 복구 전 비트를 시작한다.

## 설정값

- `PlayerToEnemyBeatDuration = 0.12`
  - 허용 범위: 0.08~0.18초
  - 플레이어 입력은 `BeginEnemyTurn`에서 즉시 잠기며, 타이머는 첫 적 행동의 시각적 시작만 늦춘다.
- `EnemyToPlayerBeatDuration = 0.08`
  - 안전 범위: 0.05~0.12초
  - 마지막 적 행동이 완료된 뒤 EnemyTurn 상태를 유지하고, 비트가 끝나면 기존 `CompleteEnemyTurn` 로직으로 PlayerTurn을 연다.

적과 적 사이의 기존 `EnemyThinkDuration` 및 Trait 보정값은 그대로 유지된다.

## 중복 실행 방지

- 전환용 타이머는 `ActionTimerId`와 분리했다.
- 이미 적→플레이어 전환이 예약된 경우 두 번째 예약을 거부한다.
- 세션 종료, 전투 재구축, 모든 적 처치 시 전환 타이머와 pending 상태를 정리한다.
- 타이머 콜백은 데미지, 행동 성공 여부, 턴 소비를 결정하지 않는다. 이미 확정된 완료 결과 뒤의 전환 표시만 담당한다.

## Play Test 체크리스트

- 이동 완료 → 약 0.12초 비트 → 첫 적 행동
- 방향 전환 완료 → 약 0.12초 비트 → 첫 적 행동
- 스킬 예약 완료 → Queue UI 반응 확인 → 첫 적 행동
- 공격 Queue 전체 완료 및 마지막 피격 확인 → 비트 → 첫 적 행동
- 여러 적이 있을 때 적 사이 기존 템포 유지
- 마지막 적 행동 완료 → 약 0.08초 비트 → Player Ready
- 전환 중 입력 연타 시 행동 및 턴 중복 없음
- 적 공격으로 전투 종료 시 PlayerTurn이 다시 열리지 않음
- 웨이브 종료/전투 리셋 중 늦은 전환 콜백 없음

## 정적 검증

- `git diff --check`: 통과
- mLua LSP: errors 0, warnings 0
- Maker Play Test: 실행 필요
