# Combat Feel STEP 8 — Final Polish

## 단일 조절 지점

전투 규칙과 분리된 조작감 기본값은 `BattleSessionComponent`의 `Combat-feel tuning` 블록에서 조절한다.

| 설정 | 기본값 | 사용처 |
|---|---:|---|
| `MoveActionDuration` | 0.12 | 플레이어 한 칸 이동 보간 |
| `MoveCurve` | `QUAD_EASE_OUT` | 이동 보간 Curve |
| `MoveSnapThreshold` | 0.01 | Cell 중앙 Snap |
| `PlayerToEnemyBeatDuration` | 0.12 | 플레이어 행동 완료 후 첫 적 행동 전 Beat |
| `EnemyToPlayerBeatDuration` | 0.08 | 마지막 적 행동 후 Player Ready 전 Beat |
| `QueuePopDuration` | 0.10 | 스킬 클릭 Punch / Queue 확정 Pop |
| `NormalHitStopDuration` | 0.04 | 일반 타격 Hit Stop |
| `StrongHitStopDuration` | 0.065 | 강한 타격 Hit Stop |
| `HitFlashDuration` | 0.065 | 피격 Flash |
| `HitReactionDuration` | 0.08 | 피격 Squash/Stretch |
| `ImpactCameraShakeDuration` | 0.08 | 기존 카메라 Shake |

`BattleUnitPresentationComponent`는 타격 시 서버가 전달한 설정값만 사용한다. `BattleQueueHudComponent`는 UI 경계를 유지하기 위해 기존 `BattleHudPresenterLogic`의 DTO에 포함된 `CombatFeel` 값을 사용한다.

## 변경하지 않은 규칙

- Grid 위치와 이동 가능 여부
- 턴 소비 시점과 TurnNumber 증가
- Queue 최대 개수와 등록/실행 순서
- Skill ID, Damage, Cooldown, Target 판정
- 적 계획, 행동 순서, Knockback, 사망 처리
- 전투 승패와 웨이브 전환

## 정적 검증

- `git diff --check`: 통과
- `BattleSessionComponent.mlua`: errors 0, warnings 0
- `BattleUnitPresentationComponent.mlua`: errors 0, warnings 0
- `BattleQueueHudComponent.mlua`: errors 0, warnings 0
- 기존 정보 진단만 남아 있으며 STEP 8 변경 줄에는 신규 오류·경고가 없다.

## Maker Play Test

현재 세션에는 Maker의 `refresh`, `play`, `logs`, `keyboard_input`, `mouse_input` 도구가 연결되어 있지 않아 아래 항목은 실제 실행 검증 대기 상태다.

- A/D 한 칸 이동, 정지, 적 행동 및 연타 방지
- 스킬 등록 즉시 UI 피드백, 턴 소비, Queue 순서
- Queue 1개/최대치 및 Skill 1→2→3 순차 실행
- 각 Skill Hit 후 마지막에만 Enemy Turn 진입
- 적 사망, Knockback, 이동 공간 없음, 인접 상태
- 빠른 이동/Execute 연타 중 중복 행동 없음
- 플레이어 사망 후 PlayerTurn 재개 없음

Maker 도구 연결 후 위 항목과 Build/Normal 로그를 모두 확인해야 최종 완료로 판정한다.
