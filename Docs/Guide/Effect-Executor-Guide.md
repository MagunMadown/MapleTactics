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
| `MAX_HP_BUFF` | `BuffEffectExecutorLogic` | 시전자 최대 HP·현재 HP +`Value`, `ParameterA`턴 |
| `DEFENSE_BUFF` | `BuffEffectExecutorLogic` | 시전자가 받는 피해 -`Value`(최소 1), `ParameterA`턴 |

### 버프 EffectType 규칙

세 버프는 한 Executor(`BuffEffectExecutorLogic`)가 소유하고, 상태는 대상의
`BattleUnitComponent`(`NextAttackBonus`, `DefenseBuff*`, `MaxHpBuff*`)가 보관한다.
Router와 Validator는 `IsBuffEffectType`으로 같은 목록을 공유한다.

- `TargetSelector`는 `SELF_UNIT`만 허용한다(`BUFF_REQUIRES_SELF_UNIT`). `Value`는 0 초과(`INVALID_BUFF_VALUE`).
- 지속형(`MAX_HP_BUFF`, `DEFENSE_BUFF`)은 `ParameterA`에 1 이상 정수 턴 수가 필요하다(`INVALID_BUFF_DURATION`).
- 턴은 쿨다운과 같은 경계(`AdvancePlayerSkillCooldowns`, 적 라운드 종료 후 다음 플레이어 턴 직전)에서 1 줄어든다.
  시전 턴 포함 N번의 적 라운드 동안 유지된다.
- 재시전은 중첩하지 않는다. 수치는 큰 값, 지속은 긴 값으로 갱신된다.
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

