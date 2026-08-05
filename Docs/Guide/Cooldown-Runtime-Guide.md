# 턴 기반 Cooldown Runtime 가이드

## 책임과 수명

`SkillRuntimeStateComponent`는 플레이어와 적을 포함한 각 전투 참가자 Entity에 붙는다.
따라서 같은 SkillId를 사용하더라도 유닛마다 남은 Cooldown이 독립적이다.

```text
SkillDefinitionRepositoryLogic  (CooldownTurns 정의)
              ↓
BattleSessionComponent          (Turn 흐름과 호출 조정)
              ↓
SkillRuntimeStateComponent      (변경 상태의 단일 소유자)
              ↓
CooldownSnapshot                (Client 표시 전용)
```

파일은
`RootDesk/MyDesk/01_Combat/Components/Shared/SkillRuntimeStateComponent.mlua`다. 현재 폴더
정리 마이그레이션이 끝나면 규격의 `Components/Unit`으로 이동할 수 있지만, 스크립트
참조는 `script.SkillRuntimeStateComponent`이므로 호출 계약은 유지된다.

## 서버 API

| 메서드 | 용도 |
|---|---|
| `CanUseSkill(skillId)` | 현재 사용 가능 여부와 `RemainingTurns` 반환 |
| `GetRemainingCooldown(skillId)` | 남은 턴 조회 |
| `StartCooldown(skillId, cooldownTurns)` | 실행 시작 시 Cooldown 기록 |
| `AdvanceCooldowns(elapsedTurns, reason)` | 소유자 Turn 경계에서 감소 |
| `ResetSkillRuntimeState(reason)` | 유닛 재구성·전투 Reset 시 초기화 |

외부 코드가 `RemainingCooldowns`나 `CooldownSnapshot`을 직접 변경하지 않는다.

## 큐와 Cooldown

`BattleSessionComponent.TryQueueTile`은 현재 남은 Cooldown을 확인한다. Cooldown이 1
이상인 스킬이 같은 큐에 이미 있으면 `COOLDOWN_RESERVED`로 두 번째 등록을 막는다.
`TryExecuteSkill`은 실행 직전 다시 `CanUseSkill`을 호출하므로 Client 표시나 큐 상태가
오래되었더라도 서버 판정은 안전하다.

실행이 시작되면 타격 성공 여부와 무관하게 Cooldown을 기록한다. 이는 빗나간 공격도
행동과 턴을 소비하는 현재 전투 규칙과 같다.

## Turn 의미

플레이어 Cooldown은 `CompleteEnemyTurn`에서 다음 `PlayerTurn`이 열리기 전에 1
감소한다.

| 설정값 | 사용 직후 | 다음 PlayerTurn | 그 다음 PlayerTurn |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |
| 1 | 1 | 0 | 0 |
| 2 | 2 | 1 | 0 |

향후 적이 Cooldown 스킬을 사용할 때도 같은 컴포넌트를 재사용하되, 적 Turn 전체가 아닌
각 적의 행동 주기 경계에서 `AdvanceCooldowns`를 호출하도록 Turn Controller를
확장한다.

## UI 연결

`BattleQueueHudComponent`는 `CooldownSnapshot`과 `CooldownRevision`을 읽어 상태 문구를
갱신한다. 남은 Cooldown이 있는 버튼과 같은 큐에 이미 예약된 Cooldown 스킬 버튼은
비활성화한다. 새로운 스킬 버튼을 만들 때는 다음 두 표시 조건을 추가한다.

1. `GetCooldownTurns(snapshot, skillId) <= 0`
2. `CooldownTurns > 0`인 스킬이면 현재 큐에 같은 SkillId가 없는지 확인

UI 검사는 사용자 안내일 뿐이다. 최종 사용 가능 여부는 항상 서버의
`SkillRuntimeStateComponent.CanUseSkill`이 결정한다.
