# Effect Executor 개발 가이드

## 실행 흐름

```text
Skill Definition + Effect Steps
→ SkillExecutionLogic.BuildContext
→ 스킬 모션 재생
→ Impact Timer
→ SkillExecutionLogic.ExecuteEffectSteps
→ EffectRouterLogic.ExecuteEffectStep
→ DamageEffectExecutorLogic / PushEffectExecutorLogic
→ BattleSession 상태 API
```

한 스킬의 Effect Step은 `StepIndex` 오름차순으로 같은 Impact 시점에 실행된다.
앞 Step의 상태 변경이 끝난 뒤 다음 Step이 실행되므로 `DAMAGE → PUSH`처럼 결과 순서가
중요한 조합도 결정적으로 처리된다.

## Effect Context 계약

Context는 한 번의 스킬 요청 동안만 사용하는 table이다.

```lua
{
    BattleSession = session,
    SourceUnitId = "player_01",
    PrimaryTargetUnitId = "enemy_w1_left",
    SkillId = "slash_push_combo",
    CurrentTurn = 1,
    StageTurn = 1,
    StageId = "stage01",
    RunSeed = 1000,
    Definition = definition
}
```

- `BattleSession`: 상태 변경 API 호출 대상
- `SourceUnitId`: 시전자 Runtime Unit ID
- `PrimaryTargetUnitId`: Context 생성 시점의 전방 대상 Snapshot
- `SkillId`: 실행 중인 Skill Definition ID
- `CurrentTurn`, `StageTurn`: 재현과 조건 판정용 Turn Snapshot
- `StageId`, `RunSeed`: Stage·확률 규칙용 Snapshot
- `Definition`: Repository가 반환한 Runtime Definition

Executor가 Context를 property나 전역 table에 저장하면 안 된다.
대상이 Impact 전에 이동할 수 있으므로 실제 대상은 Executor가 Battle 상태에서 다시 판정한다.

## Executor 계약

Executor는 무상태 `@Logic`이며 다음 형태를 따른다.

```lua
@ExecSpace("ServerOnly")
method table Execute(table context, table effectStep)
```

결과에는 최소 다음 필드를 포함한다.

```lua
{
    Success = true,
    Reason = "OK",
    EffectType = "DAMAGE",
    StepIndex = 1,
    Value = 3
}
```

규칙:

- UI, 모션, Sound를 직접 조작하지 않는다.
- 다른 Executor를 직접 호출하지 않는다.
- Effect Step 순서를 직접 진행하지 않는다.
- HP나 Cell property를 외부에서 직접 변경하지 않고 BattleSession의 상태 API를 호출한다.
- 정상적인 Miss나 막힌 Push는 `Success=true`와 구체적인 Reason을 반환할 수 있다.
- 프로그래밍 오류와 지원하지 않는 Context는 `Success=false`로 반환한다.

## 새 EffectType 추가 순서

1. EffectType ID를 `UPPER_SNAKE_CASE`로 정한다.
2. 전용 `{Name}EffectExecutorLogic`을 `01_Combat/Skills/EffectExecutors/`에 추가한다.
3. `Execute(context, effectStep)` 계약을 구현한다.
4. `EffectRouterLogic.ExecuteEffectStep`에 EffectType과 Executor 연결을 한 곳만 추가한다.
5. `ContentValidatorLogic`의 지원 EffectType에 추가한다.
6. `SkillEffectSteps` 예제 행으로 단독 실행을 검증한다.
7. 두 Step 이상의 조합에서 실행 순서를 검증한다.
8. 이 문서와 Skill 제작 가이드에 Parameter 의미를 기록한다.

스킬마다 Executor를 만들지 않는다. 기존 EffectType 조합으로 표현할 수 없는 원자 규칙에만
새 Executor를 추가한다.

## 현재 Executor

| EffectType | Executor | 상태 변경 |
|---|---|---|
| `DAMAGE` | `DamageEffectExecutorLogic` | 전방 대상 피해 |
| `PUSH` | `PushEffectExecutorLogic` | 전방 대상 Cell 이동 |
| `HEAL` | `HealEffectExecutorLogic` | 같은 팀 대상 회복 |
| `NEXT_ATTACK_BONUS` | `BuffEffectExecutorLogic` | 시전자의 다음 피해 스킬 1회 피해 +`Value` |
| `ATTACK_BUFF` | `BuffEffectExecutorLogic` | 시전자가 주는 모든 피해 +`Value`, `ParameterA`턴 |
| `MAX_HP_BUFF` | `BuffEffectExecutorLogic` | 시전자 최대 HP·현재 HP +`Value`, `ParameterA`턴 |
| `DEFENSE_BUFF` | `BuffEffectExecutorLogic` | 시전자가 받는 피해 -`Value`(최소 1), `ParameterA`턴 |
| `GUARD_BUFF` | `BuffEffectExecutorLogic` | 시전자가 받는 피해를 전부 무효, `ParameterA`턴 |
| `MOVE_SELF` | `MoveSelfEffectExecutorLogic` | 시전자를 바라보는 방향으로 이동. 착지 칸은 `ParameterA` 모드가 정한다 |

### `MOVE_SELF` 규칙

피해 스텝 뒤에 붙여 "공격하고 전진"을 만든다. 상태가 아니라 보드 이동이라 버프와 다른 Executor가 소유한다.

- `TargetSelector`는 `SELF_UNIT`만(`MOVE_REQUIRES_SELF_UNIT`), `Value`는 1 이상(`INVALID_MOVE_OFFSET`),
  `ParameterA`는 `FORWARD_OFFSET` 또는 `BEHIND_FARTHEST_TARGET`(`UNSUPPORTED_MOVE_MODE`).

| `ParameterA` | 착지 칸 | `Value`의 뜻 |
|---|---|---|
| `FORWARD_OFFSET` | 시전자 기준 앞으로 `Value`칸 | 전진 칸 수 |
| `BACKWARD_OFFSET` | 시전자 기준 뒤로 `Value`칸(방향 전환 없음) | 후퇴 칸 수 |
| `BEHIND_FARTHEST_TARGET` | 그 스킬이 맞힌 적 중 가장 먼 적의 `Value`칸 뒤 | 적 뒤로 몇 칸인지(`1`이면 바로 뒤) |

- `BEHIND_FARTHEST_TARGET`은 스킬이 실제로 맞힌 대상 스냅샷(`TargetCellsByUnitId`)에서 가장 먼 칸을 고르므로,
  맞힌 적이 하나도 없으면 `MOVE_NO_TARGET`으로 이동하지 않는다. 앞쪽 대상만 계산에 넣는다.
- `ParameterB=ALLOW_OCCUPIED`이면 점유 칸도 허용한다. 비우면 빈 칸일 때만 이동한다.
- 이동은 `BattleSessionComponent.ResolveSkillMoveImpact` → `RelocateUnitForMechanic`을 통과하므로 칸 검증·점유
  검사·드롭 회수·`UnitMovedEvent`가 그대로 적용된다. 플레이어는 그 위에 기존 이동 연출을 얹는다.
- 보드 밖(`MOVE_OUT_OF_BOUNDS`)이거나 칸이 차 있으면(`MOVE_CELL_OCCUPIED`) `Success=true`로 끝난다. 즉 스킬의
  피해는 그대로 남고 이동만 생략된다.

### 버프 EffectType 규칙

네 버프는 한 Executor(`BuffEffectExecutorLogic`)가 소유한다. Router와 Validator는
`IsBuffEffectType` / `IsTimedBuffEffectType`으로 같은 목록을 공유하고, 지속형 EffectType→능력치 매핑은
`GetBuffStat`(`ATTACK_BUFF`→`ATTACK`, `DEFENSE_BUFF`→`DEFENSE`, `MAX_HP_BUFF`→`MAX_HP`) 한 곳에 있다.

- `TargetSelector`는 `SELF_UNIT`만 허용한다(`BUFF_REQUIRES_SELF_UNIT`). `Value`는 0 초과(`INVALID_BUFF_VALUE`).
- 지속형(`ATTACK_BUFF`, `MAX_HP_BUFF`, `DEFENSE_BUFF`)은 `ParameterA`에 1 이상 정수 턴 수가 필요하다(`INVALID_BUFF_DURATION`).
- 턴은 쿨다운과 같은 경계(`AdvancePlayerSkillCooldowns`, 적 라운드 종료 후 다음 플레이어 턴 직전)에서 1 줄어든다.
  실행 후 N번의 적 라운드 동안 유지된다. `1`턴이면 같은 큐의 뒤 스킬과 바로 다음 적 라운드까지 적용된다.
- **중첩 규칙: 스킬이 다르면 합산, 같은 스킬은 갱신.** `BattleUnitComponent`가 `스킬|능력치`별 항목
  (`TimedBuffEntries`, `NextAttackBonusBySkill`, 서버 전용)을 보관하고, 동기화 값
  (`AttackBuffAmount`, `DefenseBuffAmount`, `MaxHpBuffAmount`, `NextAttackBonus`)은 합계, `*Turns`는 가장 긴
  잔여 턴이다. 같은 스킬을 다시 쓰면 그 항목만 큰 수치·긴 지속으로 갱신된다.
  예: 블레스(공격 +1) + 메디테이션(공격 +2) = 공격 +3, 블레스(방어 +1) + 매직 가드(방어 +1) = 방어 +2.
- 한 스킬에 버프 Step이 여러 개면(블레스) 대상 이펙트는 첫 Step에서만 재생한다
  (`context.BuffHitPresentedUnitIds` → `ResolveSkillBuffImpact(..., presentHit)`).
- `ATTACK_BUFF`는 `ApplyDamage`에서 지속시간 동안 모든 피해에 더해진다(다음 공격 보너스와 별개로 합산).
- `NEXT_ATTACK_BONUS`는 `ApplyDamage`에서 더해지고, 피해 스킬의 모든 Step이 끝난 뒤
  하나 이상 적중했을 때 `SkillExecutionLogic.ConsumeNextAttackBonusOnHit`가 소비한다. 그래서 범위기는 모든 대상에 적용된다.
- `DEFENSE_BUFF`는 유물 방어력 뒤에 `max(1, amount - DefenseBuffAmount)`로 적용된다. Utility Guard 무효화가 우선한다.
- `MAX_HP_BUFF`는 전투 전용이다. `SyncRunHp`는 버프를 뺀 최대 HP와 그 이하로 절삭한 현재 HP만 런 상태에 기록하므로
  전투가 버프 도중 끝나도 런 HP가 부풀지 않는다. 만료 시 최대 HP를 원복하고 초과 현재 HP를 절삭한다.
- 툴팁·도감 문구는 `BuffEffectExecutorLogic.DescribeBuffEffects` 한 곳에서 만든다.

## 복합 스킬 예제

`slash_push_combo`는 별도 스킬 클래스를 만들지 않고 두 Effect Step을 조합한다.

```text
Step 1: DAMAGE FRONT_TARGET 1
Step 2: PUSH   FRONT_TARGET 1
```

이 스킬은 규격 검증용 호환 Definition이며 전용 HUD 버튼은 아직 없다.
서버 API나 향후 동적 Skill UI에서 동일한 `SkillId`로 큐에 등록할 수 있다.

