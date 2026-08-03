# Battle Wave 개발 가이드

## 1. 책임

`BattleWaveComponent`는 전투 맵 수명 동안 다음 상태의 단일 소유자다.

- 현재 Wave와 전체 Wave 수
- `Setup`, `Spawning`, `Active`, `SpawnPending`, `Cleared`, 종료 상태
- 현재 Wave의 Spawn Trigger와 제한 값
- Turn/시간 제한 강제 증원 예약
- 다음 Wave 전환 Timer와 시간 제한 Timer

실제 적 Definition 조회, 빈 Cell 판정, `SpawnByModelId`, 유닛 등록과 승패 확정은
`BattleSessionComponent`가 담당한다.

`map01`에서는 `BattleWaveState` 자식 Entity가 컴포넌트를 소유한다. 새 전투 맵도
`BattleBoardState`, `BattleTurnState`, `BattleWaveState` 이름을 유지한다.

## 2. 기본 흐름

```text
Stage Definition 적용
→ ResetWaveState / SetTotalWaves
→ Session이 Wave Definition 검증
→ BeginWave
→ Session이 적 Spawn
→ MarkWaveActive
→ ScheduleForcedSpawnTimer
```

전멸 시 다음 Wave가 남았다면:

```text
ScheduleWaveTransition
→ Wave Timer 만료
→ Session.AdvanceClearedWave
→ Session.SpawnWave
```

Turn 또는 시간 제한이 먼저 충족되면 `MarkSpawnPending`만 수행한다. 실제 Spawn은
플레이어 큐와 적 라운드가 끝난 `EvaluateForcedSpawnAtTurnBoundary`에서 요청한다.

## 3. 공개 API

아래 API는 모두 `ServerOnly`이며 Session 또는 Wave Timer callback만 호출한다. Client HUD는
동기화된 property를 읽기만 한다.

| 메서드 서명 | 반환 | 주 호출자 | 용도 |
|---|---|---|---|
| `ResetWaveState(integer total, string reason)` | void | Session | Stage 시작·Reset·종료 정리 |
| `SetTotalWaves(integer total, string reason)` | void | Session | 검증된 Stage Definition 적용 |
| `SetWaveState(string state, string reason)` | void | Session | 오류·승리·패배 상태 반영 |
| `BeginWave(integer wave, string mode, integer forceTurns, number forceSeconds, integer spawnCount, integer maxConcurrent, number clearDelay, integer stageTurn)` | table | Session | 현재 Wave 규칙 Snapshot과 `Spawning` 설정 |
| `MarkWaveActive(string reason)` | void | Session | Spawn 완료 |
| `MarkSpawnPending(integer wave, string reason)` | void | Wave/Session | 시간·Turn·수용량 대기 등록 |
| `ScheduleForcedSpawnTimer()` | void | Session | 시간 제한 Timer 예약 |
| `ClearForcedSpawnSchedule(string reason)` | void | Session | 예약과 시간 Timer 해제 |
| `EvaluateForcedSpawnAtTurnBoundary(integer stageTurn, boolean battleEnded)` | table | Session | 안전한 경계에서 Spawn 요청 반환 |
| `ScheduleWaveTransition(integer clearedWave, integer nextWave, number delaySeconds)` | void | Session | 전멸 후 다음 Wave Timer 예약 |
| `ClearWaveTransitionTimer(string reason)` | void | Wave/Session | 다음 Wave Timer만 해제 |
| `ClearAllTimers(string reason)` | void | Session | Reset·맵 종료 시 전체 Timer 해제 |

`BeginWave` 결과는 `Success`, `Reason`을 확인한다.
`EvaluateForcedSpawnAtTurnBoundary` 결과는 `Success`, `Reason`, `ShouldSpawn`,
`WaveNumber`, `PendingReason`을 확인한 뒤 처리한다. Timer callback은 실제 적을 직접 생성하지
않고 parent Map의 Session API를 호출한다.

## 4. 호환 Snapshot

Session의 기존 Wave `@Sync` 필드는 외부 시스템 보호용 복사본이다.

- Session에서 Wave 필드에 직접 대입하지 않는다.
- 변경 직후 `PublishWaveStateSnapshot(reason)`으로만 복사한다.
- 신규 HUD는 `BattleWaveComponent`를 직접 읽는다.
- 서버 외부 연동은 당분간 `GetBattleSnapshot()`을 사용할 수 있다.

## 5. Stage 개발 규칙

- 일반 Stage 추가는 `BattleWaveComponent`나 Session을 수정하지 않는다.
- `StageEnemyWaves`에서 `SpawnTriggerMode`, 제한 값, Spawn 수를 설정한다.
- `CLEAR_ONLY`, `TURN_LIMIT`, `TIME_LIMIT`, `TURN_OR_TIME` 외 규칙이 필요할 때만
  Wave 공개 API와 Validator를 함께 확장한다.
- Timer callback에서 직접 적을 생성하지 않는다. 항상 Session Spawn 경로를 사용한다.
- `SpawnByModelId`의 parent는 전투 맵 Entity여야 한다.

## 6. 검증 체크리스트

1. Stage 시작 시 Wave 1과 전체 Wave 수가 Definition과 같은지 확인한다.
2. 전멸 시 설정된 지연 후 다음 Wave가 한 번만 생성되는지 확인한다.
3. Turn 제한 도달 전에는 증원이 생성되지 않는지 확인한다.
4. 제한 도달 시 행동 중 즉시 생성되지 않고 Turn 경계에서 생성되는지 확인한다.
5. 수용량 부족 시 `CAPACITY_WAIT` 상태가 유지되는지 확인한다.
6. Reset과 맵 종료 시 두 Timer가 모두 해제되는지 확인한다.
7. HUD와 Session 호환 Snapshot이 Wave 원본과 일치하는지 확인한다.
