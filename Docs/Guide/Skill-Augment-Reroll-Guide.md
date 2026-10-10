# 스킬 증강·리롤 가이드

기준: `develop` `f85c18d` (2026-10-10, main `b5d1018`과 내용 동일). 이 문서의 규칙과 수치는 아래 코드와 CSV에서 옮겨 적었다.
코드가 바뀌면 코드가 우선이며, 이 문서를 같은 변경에서 갱신한다.

- 데이터: `03_Data/AugmentDefinitions.csv`, `03_Data/AugmentEffects.csv` (`ExclusiveGroup=SKILL_AUGMENT` 행)
- 판정·적용: `01_Combat/Augments/AugmentRuntimeLogic.mlua` (`CanBindSkillAugment`, `ApplySkillModifier`, `BuildSkillBundle`)
- 전투 중 추가 효과: `AugmentRuntimeLogic` (`GetConditionalDamageBonus`, `OnSkillDamageApplied`, `CompleteSkillAugment`, `QueueSkillRegeneration`, `AdvanceSkillRegeneration`)
- 데이터 검증: `03_Data/Repositories/AugmentContentValidatorLogic.mlua` (`IsSkillModifierValid`)
- 보유 상태: `04_Roguelike/RunManager/PlayerRunAugmentComponent.mlua`
- 보상 화면: `04_Roguelike/SkillStage/UpgradeSkillStageLogic.mlua`, `NewSkillStageChoiceComponent.mlua`
- 보상 종류 결정: `04_Roguelike/RunManager/StageTransitionManagerLogic.mlua` (`DetermineIntermediateMap`, `ChooseRewardKind`)

직업 시작 패시브(`TURN_START` · `HEAL`)는 같은 표를 쓰지만 별개의 기능이다.
[`Augment-Authoring-Guide.md`](./Augment-Authoring-Guide.md)를 따른다.

> **09-28판에서 바뀐 점**
> - 증강 14종 → **23종**(일반 18 · 히든 5). 강타 쿨타임 +3 → **+2**.
> - 한 스킬에 쌓을 수 있는 증강 6단계 → **4단계**. 힐도 이 제한에 들어간다.
> - **스킬 티어와 무관하게** 붙는다. "Tier 2 이상 · 마지막 강화 단계" 조건과 기절·빙결 제외 조건이 없어졌다.
> - 업그레이드 보상은 **증강 카드만** 나온다. 스킬 티어 강화는 로비 스킬 트리(§8)로 옮겨 갔다.
> - `new_upgrade_stage` 맵이 없어졌다. 두 보상 모두 `new_skill_stage` 맵에서 열린다.
> - 히든 판정 3% → **10%**.

## 1. 한눈에 보기

```text
전투 승리
 ├─ 리롤권 +1 판정 (보스 100%, 그 외 20%)
 └─ 보상 종류 결정 (StageTransitionManagerLogic.ChooseRewardKind)
     ├─ 스킬 칸이 가득 참 → UPGRADE
     ├─ henesys_stage_01 → NEW (안 가진 1티어 스킬이 없으면 UPGRADE)
     ├─ 안 가진 1티어 직업 스킬이 없음 → UPGRADE
     └─ 그 외 → 25% UPGRADE / 75% NEW
    결과는 RewardSelectionContext = "<런 번호>:<전투 기록 키>|NEW" 또는 "|UPGRADE"로 저장되고,
    어느 쪽이든 new_skill_stage 맵으로 이동한다.
new_skill_stage · UPGRADE (증강 3택)        new_skill_stage · NEW (새 스킬 2택)
 ├─ 카드 1장 선택 → 증강 적용                 ├─ 카드 1장 선택 → 스킬 획득(칸이 차면 교체)
 ├─ 카드별 리롤 (리롤권 1)                    ├─ 카드별 리롤 (리롤권 1)
 └─ 건너뛰기 (항상 가능)                       └─ 건너뛰기/포기
다음 스테이지
```

- 스킬 증강은 보유한 스킬 하나에 붙는 이득·불이익 묶음이다. 한 스킬에 **최대 4단계**까지 쌓인다.
- 증강은 런 동안만 유지된다. 새 런에서, 그리고 그 스킬을 상점에서 팔면 사라진다.
- 리롤권은 두 보상이 **같은 개수**를 나눠 쓴다.
- 보상 화면은 저장된 보상 종류와 맞을 때만 열린다. 아니면 `WRONG_REWARD_KIND`로 거절한다.

## 2. 증강 23종 (현재 데이터)

모든 스킬 증강 행은 `SchemaVersion=1`, `StackPolicy=UNIQUE`, `MaxStacks=1`, `ExclusiveGroup=SKILL_AUGMENT`,
`AugmentEffects` 1행(`TriggerType=SKILL_BUILD`, `ConditionType=ALWAYS`, `EffectType=SKILL_MODIFIER`,
`TargetType=SKILL`, `Priority=100`)이다. 종류는 `ParamA`, 변화량은 `Amount`, 쿨타임 증감은 `ParamB`,
히든 여부는 `ParamC=HIDDEN`이다. `StackPolicy=UNIQUE`는 전역 증강용 값이며 스킬 증강의 반복 선택을 막지 않는다.

"붙는 스킬 수"는 현재 직업 스킬 68개(1티어 50 · 2티어 18)를 **증강 0단계 상태**로 판정한 값이다(Balance Studio 증강 탭과 같은 판정).
68개 모두 증강을 하나 이상 받을 수 있다.

### 2.1 일반 (RARE) 18종

| AugmentId | 이름 | ParamA | Amount | ParamB | 효과 | 붙는 스킬 수 |
|---|---|---|---:|---:|---|---:|
| `skill_power` | 강타 | `POWER` | 2 | +2 | 직접 피해 +2 / 쿨타임 +2 | 27 |
| `skill_quick` | 속공 | `QUICK` | 1 | −2 | 직접 피해 −1 / 쿨타임 −2 | 36 |
| `skill_volley` | 연사 | `VOLLEY` | 1 | +2 | 타수 +1 / 쿨타임 +2 | 6 |
| `skill_compact` | 압축 사격 | `COMPACT` | 1 | −2 | 타수 −1 / 쿨타임 −2 | 3 |
| `skill_area` | 확산 | `AREA` | 1 | +3 | 대상별 피해 +1 / 쿨타임 +3 | 23 |
| `skill_range` | 장거리 사격 | `RANGE` | 1 | +1 | 사거리 +1칸 / 쿨타임 +1 | 21 |
| `skill_precise` | 정밀 처형 | `PRECISE` | 2 | +1 | 딱 맞는 피해로 처치 시 쿨타임 −2 / 쿨타임 +1 | 27 |
| `skill_zero_damage` | 무위의 준비 | `ZERO_DAMAGE_FREE_LOAD` | 1 | 0 | 직접 피해 0 / 장착 시 턴 소모 없음 | 66 |
| `skill_heal` | 힐 횟수 충전 | `HEAL_CHARGES` | 2 | 0 | 힐 사용 횟수 +2 (최대 5) | 2 (힐) |
| `skill_buff_cooldown` | 버프 신속 | `BUFF_COOLDOWN` | 2 | −2 | 쿨타임 −2 / 버프 효과 유지 | 10 |
| `skill_first_strike` | 선제 타격 | `FIRST_STRIKE` | 2 | +1 | 최대 HP 대상 첫 타격 피해 +2 / 쿨타임 +1 | 56 |
| `skill_execute` | 마무리 일격 | `EXECUTE` | 3 | +1 | HP 30% 이하 대상 첫 타격 피해 +3 / 쿨타임 +1 | 56 |
| `skill_kill_refund` | 몰아치기 | `KILL_REFUND` | 1 | 0 | 직접 처치 시 남은 쿨타임 −1 | 55 |
| `skill_shockwave` | 충격파 | `SHOCKWAVE` | 1 | +2 | 첫 적중 대상 양옆 1칸에 피해 1 / 쿨타임 +2 | 31 |
| `skill_heavy_push` | 묵직한 일격 | `HEAVY_PUSH` | 1 | +1 | 공격 완료 시 적중한 적 1칸 밀침 / 쿨타임 +1 | 45 |
| `skill_battle_stance` | 전투 태세 | `BATTLE_STANCE` | 1 | +1 | 피해를 주면 다음 적 턴 종료까지 방어 +1 / 쿨타임 +1 | 56 |
| `skill_regen_heal` | 지속 치유 | `REGEN_HEAL` | 1 | 0 | 즉시 회복 −1 / 다음 2턴 시작마다 HP +1 | 2 (힐) |
| `skill_buff_duration` | 효과 연장 | `BUFF_DURATION` | 1 | +2 | 턴 기반 버프 지속 +1턴 / 쿨타임 +2 | 6 |

### 2.2 히든 (EPIC) 5종

| AugmentId | 이름 | ParamA | Amount | ParamB | 효과 | 붙는 스킬 수 |
|---|---|---|---:|---:|---|---:|
| `hidden_power` | 히든 · 순수한 강타 | `POWER` | 2 | 0 | 직접 피해 +2 | 27 |
| `hidden_volley` | 히든 · 순수한 연사 | `VOLLEY` | 1 | 0 | 타수 +1 | 6 |
| `hidden_area` | 히든 · 순수한 확산 | `AREA` | 1 | 0 | 대상별 피해 +1 | 23 |
| `hidden_cooldown` | 히든 · 신속 | `HIDDEN_COOLDOWN` | 2 | −2 | 쿨타임 −2 (최소 1) | 65 |
| `hidden_heal` | 히든 · 무한한 치유 | `HEAL_UNLIMITED` | 1 | 0 | 힐 횟수 제한 해제 | 2 (힐) |

### 2.3 데이터 검증 규칙 (`IsSkillModifierValid`)

게임은 아래를 어긴 증강 행을 `INVALID_SKILL_AUGMENT`로 거절한다. Balance Studio 증강 탭도 같은 규칙으로 표시한다.

- `ParamA`는 위 20개 종류 중 하나, Trigger/Condition/Effect/Target 값은 위 고정값, `Amount`는 1 이상 정수, `ParamB`는 정수.
- 히든(`ParamC=HIDDEN`): `POWER`, `VOLLEY`, `AREA`, `HEAL_UNLIMITED`는 `ParamB = 0`, `HIDDEN_COOLDOWN`은 `ParamB < 0`. 다른 종류는 히든이 될 수 없다.
- 일반(`ParamC` 빈 값): `HEAL_UNLIMITED`, `HIDDEN_COOLDOWN`은 쓸 수 없다. 나머지는 아래와 같다.

| 종류 | `ParamB` | `Amount` |
|---|---|---|
| `HEAL_CHARGES` | 0 | 1 이상 |
| `KILL_REFUND`, `REGEN_HEAL`, `ZERO_DAMAGE_FREE_LOAD` | 0 | 1 |
| `HEAVY_PUSH`, `BATTLE_STANCE`, `BUFF_DURATION` | > 0 | 1 |
| `QUICK`, `COMPACT`, `BUFF_COOLDOWN` | < 0 | 1 이상 |
| 그 밖의 종류 (`POWER`, `VOLLEY`, `AREA`, `RANGE`, `PRECISE`, `FIRST_STRIKE`, `EXECUTE`, `SHOCKWAVE`) | > 0 (이득의 대가) | 1 이상 |

## 3. 어떤 스킬에 붙는가 (`CanBindSkillAugment`)

코드 주석대로 "스킬 티어 강화와 스킬 증강은 독립"이다. 1티어 스킬에도 붙는다. 판정은 **지금까지 쌓인 증강을 적용한 스킬**(`GetEffectiveSkillBundle`)을 대상으로 하며, 위에서부터 차례로 본다.

1. 행이 §2.3 규칙을 어기면 붙지 않는다.
2. **힐** (`CostType=HEAL_CHARGE`): `REGEN_HEAL`은 아래 4번으로 넘어간다. 그 밖에는 `HEAL_CHARGES`, `HEAL_UNLIMITED`만 붙는다. 힐이 아닌 스킬에는 이 둘이 붙지 않는다.
3. `HIDDEN_COOLDOWN`: 쿨타임이 2턴 이상이면 붙는다. 여기서 판정이 끝난다.
4. 스킬의 효과 단계를 훑는다(`DAMAGE` 개수, 마지막 `HEAL`, 버프 단계 여부, `MOVE_SELF` 여부). 버프는 `BuffEffectExecutorLogic.IsBuffEffectType`이 인정하는 종류다(`NEXT_ATTACK_BONUS`, `ATTACK_BUFF`, `DEFENSE_BUFF`, `MAX_HP_BUFF`, `GUARD_BUFF`, `DAMAGE_CAP_BUFF`, `VENOM_BUFF`, `COMBO_BUFF`).
   - `REGEN_HEAL`: `HEAL` 단계가 있고 회복량이 `Amount`보다 크며, 아직 지속 치유가 없으면 붙는다.
   - `BUFF_DURATION`: 효과 연장이 2회 미만이고, `DEFENSE_BUFF`/`MAX_HP_BUFF`/`GUARD_BUFF`/`DAMAGE_CAP_BUFF` 중 `ParameterA`(지속 턴)가 1 이상인 단계가 있으면 붙는다.
   - `BUFF_COOLDOWN`: 버프 단계가 있고 `DAMAGE` 단계가 없으며 쿨타임이 2턴 이상이면 붙는다.
5. **피해 없는 버프 스킬**에는 위 셋과 `HIDDEN_COOLDOWN` 말고는 `ZERO_DAMAGE_FREE_LOAD`만 붙는다(아직 무위의 준비가 없고 원래 `FreePlay=false`일 때).
6. 쿨타임을 줄이는 증강(`ParamB < 0`)은 쿨타임 1턴 이하 스킬에 붙지 않는다.
7. `DAMAGE` 단계가 정확히 1개여야 하고, `ParameterA=SOURCE_BASIC_ATTACK`이면 안 된다.
8. `ZERO_DAMAGE_FREE_LOAD`: 이미 무위의 준비가 붙었거나 원래 턴 소모 없는 스킬에는 붙지 않는다. 피해가 1 이상이어야 한다.
9. 무위의 준비가 붙은 스킬에는 이후 `RANGE`만 붙는다(`HIDDEN_COOLDOWN`은 3번에서 먼저 통과하므로 역시 붙는다).
10. 종류별 조건. 타수는 `ParameterA=MULTI_HIT`일 때 `ParameterB`, 아니면 1이다. "단일 대상"은 `TargetSelector=PRIMARY_TARGET` 또는 `TargetingType`이 `FRONT_CELL`/`FIRST_ENEMY_FORWARD`다.

| 종류 | 조건 |
|---|---|
| `FIRST_STRIKE`, `EXECUTE` | 피해 ≥ 1, 같은 종류 2회 미만 |
| `KILL_REFUND` | 피해 ≥ 1, 쿨타임 2턴 이상, 아직 없음 |
| `SHOCKWAVE` | 피해 ≥ 1, 단일 대상, 아직 없음 |
| `HEAVY_PUSH` | 피해 ≥ 1, `MOVE_SELF`·`PUSH`·`PULL` 단계 없음, 아직 없음 |
| `BATTLE_STANCE` | 피해 ≥ 1, 아직 없음 |
| `QUICK` | 1타, 적용 후 피해 ≥ 1 |
| `POWER`, `PRECISE` | 1타, 단일 대상 |
| `VOLLEY` | 2타 이상, 무기 `BOW`/`CROSSBOW`/`CLAW`/`GUN` |
| `COMPACT` | 3타 이상, 적용 후 2타 이상 |
| `AREA` | 1타, 단일 대상이 아님 |
| `RANGE` | 자기 이동(`MOVE_SELF`) 없음, 사거리 6 미만, `ProjectileRuid` 있음. `FIRST_ENEMY_FORWARD`/`FIRST_ENEMY_PIERCE`이거나 `RANGE_OFFSETS`의 모든 칸이 앞쪽(양수) |

예: 브랜디쉬(전사 T1, 피해 2, 쿨타임 3)와 라만차 스피어(전사 T2, 피해 3, 쿨타임 4)는 같은 12종을 받는다 — 강타, 속공, 정밀 처형, 무위의 준비, 선제 타격, 마무리 일격, 몰아치기, 충격파, 묵직한 일격, 전투 태세, 히든 · 순수한 강타, 히든 · 신속.
아이언 월(전사 T1 버프, 쿨타임 8)은 무위의 준비, 버프 신속, 효과 연장, 히든 · 신속을 받는다.

## 4. 적용 결과 (`ApplySkillModifier`)

증강은 CSV 원본을 바꾸지 않는다. 전투(`BattleSessionComponent.GetEffectiveSkillValidation`),
보상 카드 설명, 큐 시간, 스킬 HUD가 모두 `GetEffectiveSkillBundle` → `BuildSkillBundle`의 같은 결과를 읽는다.

### 4.1 수치 변화

- 쿨타임: `max(1, 현재 쿨타임 + ParamB)`. 힐 횟수 충전만 예외다(스킬을 바꾸지 않음).
- `POWER`/`AREA` 피해 +Amount, `QUICK` 피해 −Amount(최소 1).
- `VOLLEY`/`COMPACT`는 타수 ±Amount다. 투사체 스킬이면 `ProjectileCount`도 같은 값이 된다.
- `RANGE`: 사거리 +Amount (최대 6). `RANGE_OFFSETS`면 가장 먼 칸 뒤로 칸을 이어 붙인다.
- `REGEN_HEAL`: `HEAL` 단계 회복량 −Amount(최소 1).
- `BUFF_DURATION`: `DEFENSE_BUFF`/`MAX_HP_BUFF`/`GUARD_BUFF`/`DAMAGE_CAP_BUFF` 단계의 `ParameterA`(지속 턴) +Amount. 공격 버프·독 버프의 횟수와 콤보는 늘지 않는다.
- `BUFF_COOLDOWN`, `HIDDEN_COOLDOWN`: 쿨타임만 바뀐다.
- `ZERO_DAMAGE_FREE_LOAD`: 직접 피해가 0으로 **고정**되고 장착해도 턴을 쓰지 않는다(`FreePlay`). 피해 외 효과(밀치기·상태이상 등)는 그대로다.
  - 유물·공격 버프로 피해가 다시 생기지 않는다. 선제 타격 등 아래 전투 추가 효과도 모두 꺼진다.
- `HEAL_UNLIMITED`: 힐 비용이 0이 된다. 회복량과 쿨타임은 그대로다. 적용 시 인벤토리의 `HealUnlimited`가 켜진다.
- `HEAL_CHARGES`: 스킬은 바뀌지 않는다. 적용하면 힐 횟수만 +2(최대 5) 된다.
- 증강이 하나라도 붙은 스킬은 자기 쿨타임 감소 효과(`REDUCE_OWN_COOLDOWN`)를 써도 남은 쿨타임이 1 아래로 내려가지 않는다(`AugmentCooldownFloor=1`). 일반 턴 경과로는 0까지 내려간다.

### 4.2 전투 중 추가 효과

아래 효과는 플레이어가 적에게 쓴 스킬에만 동작하고, 무위의 준비가 붙은 스킬에서는 모두 꺼진다.

| 종류 | 동작 | 코드 |
|---|---|---|
| `FIRST_STRIKE` | 시전마다 대상별 첫 직접 타격 때 대상 HP가 최대면 피해 +합계 Amount. 투사체도 같다 | `GetConditionalDamageBonus` |
| `EXECUTE` | 같은 시점에 대상 HP가 1 이상이고 최대 HP의 30% 이하면 피해 +합계 Amount | `GetConditionalDamageBonus` |
| `PRECISE` | 이 스킬의 피해로 적 HP가 정확히 0이 되면(`ExactLethal`) 남은 쿨타임을 `min(합계 Amount, 남은 쿨타임 − 1)`만큼 줄인다 | `BattleSessionComponent` |
| `KILL_REFUND` | 직접 피해로 적 HP가 0이 되면 시전당 1회, 남은 쿨타임을 `min(Amount, 남은 쿨타임 − 1)`만큼 줄인다 | `OnSkillDamageApplied` |
| `BATTLE_STANCE` | 피해를 주면 시전당 1회 방어 +Amount 버프(`ApplyTimedBuff` 지속 1, CSV 설명은 "다음 적 턴 종료까지"). 공용 키 `AUGMENT_BATTLE_STANCE`라 여러 스킬에서 겹치지 않고 갱신된다 | `OnSkillDamageApplied` |
| `SHOCKWAVE` | 원래 타격이 모두 끝난 뒤, 첫 적중 대상 칸의 양옆 1칸에 있는 다른 적에게 고정 피해 Amount. 별도 공격 ID(`AUGMENT_SHOCKWAVE`)라 공격 버프·독·환급·연쇄 충격파가 붙지 않는다 | `CompleteSkillAugment` |
| `HEAVY_PUSH` | 원래 타격이 모두 끝난 뒤, 적중한 적마다 1칸 밀친다 | `CompleteSkillAugment` |
| `REGEN_HEAL` | 회복 대상에 지속 치유를 걸고, 다음 2번의 턴 시작마다 HP +Amount. 시전한 턴에는 회복하지 않고, 다시 쓰면 2회로 갱신된다. 죽거나 다른 전투로 넘어가면 사라진다 | `QueueSkillRegeneration`, `AdvanceSkillRegeneration` |

### 4.3 누적 (최대 4단계)

- 스킬별 보유 목록은 `SkillAugmentSnapshot`(`skillId~augmentId|…`, 획득 순서)이다. 한 스킬에 최대 4개(`MaxSkillAugmentStages=4`)가 들어간다. **힐도 같은 제한을 받는다**(§10-2).
- 같은 증강을 여러 번 고를 수 있지만 종류별 한도가 있다.
  - 최대 2회: 선제 타격, 마무리 일격, 효과 연장
  - 1회: 몰아치기, 충격파, 묵직한 일격, 전투 태세, 지속 치유, 무위의 준비
  - 제한 없음(4단계 안에서): 강타, 속공, 연사, 압축 사격, 확산, 장거리 사격, 정밀 처형, 버프 신속, 히든 증강, 힐 횟수 충전
- 증강을 **제안·적용할 때** 앞 단계까지 적용된 스킬로 §3을 다시 판정한다.
  - 속공은 피해가 1이 될 때까지만 붙는다. 브랜디쉬(피해 2)는 한 번만 받는다(피해 2 → 1, 쿨타임 3 → 1).
  - 강타는 조건이 유지되므로 4번 모두 붙을 수 있다(예: 라만차 스피어 피해 3 → 5 → 7 → 9 → 11, 쿨타임 4 → 6 → 8 → 10 → 12).
- `BuildSkillBundle`은 보유한 증강을 획득 순서대로 **다시 판정하지 않고** 모두 적용한다. 코드 주석은 "자격은 지급·제안할 때 확인한다. 보유한 수정치의 재적용은 티어 강화 뒤에도 유지돼야 한다"이다.
- 카드에는 `증강 횟수: n/4`가 표시된다(선택 전 / 선택 후).
- Balance Studio 증강 탭의 **증강 누적 시뮬레이터**가 같은 순서로 계산한다.

## 5. 업그레이드 보상 3택 (`UpgradeSkillStageLogic.BuildUpgradeState`)

### 5.1 입장 조건과 보상 키

- `new_skill_stage` 맵, `RewardSelectionContext`가 이번 전투의 `|UPGRADE`, 직업 선택 완료, 현재 런 인벤토리·증강 상태, 직전 전투 기록(`LastBattleRecordKey`)이 있어야 한다.
  - 하나라도 없으면 거절하고 이유를 UI로 보낸다: `NOT_IN_UPGRADE_STAGE`, `WRONG_REWARD_KIND`, `JOB_NOT_SELECTED`, `RUN_INVENTORY_UNAVAILABLE`, `BATTLE_REWARD_CONTEXT_UNAVAILABLE`, `RUN_AUGMENT_UNAVAILABLE`.
- 보상 키 `upgrade_skill_stage:<LastBattleRecordKey>`가 이미 쓰였으면 `UPGRADE_ALREADY_APPLIED`로 거절한다.
- 제안은 `런 번호:보상 키:스킬 인벤토리 리비전:증강 리비전`으로 **캐시**된다. 화면을 다시 열어도 새로 뽑지 않는다.

### 5.2 판매한 스킬 자리 (우선)

상점에서 스킬을 팔아 `PendingSoldSkillChoices > 0`이고 스킬 칸에 빈 자리가 있으면 이 경로가 우선한다.
이번 보상은 **안 가진 계열의 1티어 기본 스킬**만 최대 3장 제안하고, 증강 카드는 나오지 않는다.
카드에 나오는 스킬은 출발 때 저장한 스킬 트리 해금(`SkillTreeUnlockSnapshot`)을 적용한 단계다.
하나를 고르면 `PendingSoldSkillChoices`가 1 줄어든다.

### 5.3 후보 풀

보유한 스킬마다(힐은 횟수가 0이어도) 다음을 본다.

| 풀 | 조건 |
|---|---|
| 증강 | 그 스킬의 증강이 4개 미만이고 `CanBindSkillAugment` 통과. 무한 치유가 있으면 힐 횟수 충전·무한 치유는 빠진다. `skill_heal`은 남은 횟수가 4 미만일 때만 |
| 히든 | 위 조건을 통과한 히든 증강이 있는 스킬마다 **한 번** 10% 판정. 당첨되면 그 스킬의 히든 증강 중 1개가 후보가 된다 |

일반 강화 카드는 더 이상 만들지 않는다(코드에 `normal` 목록이 남아 있지만 항상 비어 있다).

### 5.4 3장 구성 순서

1. 당첨된 히든 카드 (최대 3장)
2. 증강 카드 1장 (무작위)
3. 남은 증강 카드를 섞어 3장이 될 때까지 채움

같은 스킬에 서로 다른 증강 카드가 여러 장 나올 수 있다.

### 5.5 선택과 건너뛰기

- **증강**: `PlayerRunAugmentComponent.SetSkillAugment`로 단계를 하나 추가한다.
  - 보상 키가 이미 쓰였으면 `UPGRADE_ALREADY_APPLIED`.
  - 스킬을 안 가졌으면 `SKILL_NOT_OWNED`, 4단계가 찼으면 `SKILL_AUGMENT_LIMIT`.
  - 지금 상태로 다시 판정해서 안 붙으면 `INVALID_SKILL_AUGMENT`.
- **힐 횟수 충전**: 증강으로 추가하고 힐 횟수를 +2(최대 5) 한다.
- **히든 · 무한한 치유**: 증강으로 추가하고 `HealUnlimited=true`로 바꾼다.
- **판매 자리 새 스킬**: `GrantSkill`로 스킬을 준다. 빈 자리가 없으면 `NO_SOLD_SKILL_SLOT`.
- **건너뛰기**: 제안이 있어도 언제든 가능하다. 보상 키를 소모하므로 돌아와도 다시 받을 수 없고, 쓴 리롤권은 돌려주지 않는다.

## 6. 리롤

### 6.1 리롤권 개수 (`PlayerRunAugmentComponent.AvailableRerollCount`)

| 시점 | 변화 |
|---|---|
| 런 시작 (`ResetForRun`) | `BaseRerollCount` 2 + 유니온 `AUGMENT_REROLL` 보너스 |
| 전투 승리 (`GrantClearReroll`) | 보스 처치 시 +1 확정, 그 외 20% 확률로 +1. 같은 전투 완료 키로는 한 번만 판정(꽝도 기록) |

- **유니온 보너스**: `UnionStatDefinitions`의 `AUGMENT_REROLL`(최대 2레벨, 레벨당 +1)이다. 유니온 화면에는 "증강 리롤"로 표시된다.
- **획득 표시**: 얻은 리롤권은 결과 화면 보상 목록에 "증강 리롤권"으로 나온다(`RecordRoundReward("REROLL", …)`).

### 6.2 업그레이드 보상 슬롯 리롤 (`RequestReroll`)

- 카드 한 장만 바꾼다. 요청에 슬롯 번호, 리비전, 현재 카드 토큰을 담는다.
  - 셋 중 하나라도 어긋나면 `STALE_OFFER`로 거절하고 화면을 다시 받는다.
- 바꿀 후보는 **같은 스킬의 다른 증강** 중 화면에 없는 것이다. 판매 자리 카드는 다른 새 기본 스킬로 바뀐다.
- 후보 중 히든이 있으면 히든만 고른다. 히든은 제안을 캐시할 때 한 번 판정한 결과만 쓰므로, 리롤을 반복해도 새 히든 판정은 일어나지 않는다.
- 화면에 없는 후보가 없으면, 다른 카드에 이미 나와 있는 **같은 스킬의 다른 증강**으로 바꾼다. 다른 카드가 그 스킬의 후보를 모두 차지해서 리롤이 막히지 않게 하기 위해서다.
- 그래도 후보가 없으면 `NO_ALTERNATIVE`를 돌려준다. 리롤권은 **차감하지 않는다**("다른 후보가 없습니다 · 리롤권 유지").
- 카드가 실제로 바뀐 경우에만 1장 차감한다. 남은 리롤권이 0이면 `NO_REROLLS`.

### 6.3 새 스킬 보상 슬롯 리롤 (`NewSkillStageChoiceComponent.ProcessReroll`)

- 보이는 카드는 `NewSkillChoiceCount`(현재 2)장이다. 리롤하면 한 슬롯을 **아직 안 보인 후보**와 맞바꾼다.
  - 후보는 안 가진 계열의 1티어 스킬이며, 출발 때 저장한 스킬 트리 해금 단계로 바뀌어 나온다.
- 후보가 없으면 `NO_ALTERNATIVE`, 리롤권이 없으면 `NO_REROLLS`이다. 둘 다 차감하지 않는다.
- 보상 종류가 `|NEW`가 아니면 `WRONG_REWARD_KIND`, 보상 키·리비전·스킬 인벤토리가 바뀌었으면 `STALE_REWARD_CONTEXT` / `STALE_OFFER`로 거절한다.

## 7. 스킬 판매와 증강

상점 판매 목록에 보유 스킬이 들어간다(`RunShopLogic.CaptureSkillSellCatalog`, `PlayerRunInventoryComponent.ApplySkillSale`).

- 판매 가격(런 재화 `gold`): Tier 2 이상이거나 증강이 붙은 스킬은 40, 그 외 20. 판매 목록에는 "강화 횟수: n회"(증강 수)가 표시된다.
- 마지막 남은 스킬은 팔 수 없다(`LAST_SKILL_REQUIRED`).
- 팔면 그 스킬의 증강이 **모두** 사라지고(`RemoveSkillAugments`) `PendingSoldSkillChoices`가 1 늘어난다(§5.2).
- 힐을 팔면 힐 횟수와 무한 치유 상태도 사라진다.

## 8. 스킬 티어 강화와의 관계 (로비 스킬 트리)

- 스킬 티어 강화는 런 안에서 일어나지 않는다. 로비의 스킬 강화 NPC에서 **유니온 코인 200**(`SkillTreeServiceLogic.GetUnlockCoinCost`)으로 다음 단계를 영구 해금한다.
- 런을 시작할 때 해금 상태를 `SkillTreeUnlockSnapshot`에 저장하고, 시작 스킬과 새 스킬 카드는 그 단계로 바뀌어 나온다(`ResolveSkill`).
- 그래서 같은 계열이라도 계정마다 1티어 또는 2티어로 런을 시작하고, 어느 쪽이든 같은 규칙으로 증강을 받는다.
- `PlayerRunInventoryComponent.UpgradeSkill`(런 중 티어 교체)과 그 안의 `TransferSkillAugments`(증강을 강화된 스킬로 옮김)는 코드에 남아 있지만 **지금은 부르는 곳이 없다**.

## 9. 새 스킬 증강 추가 절차

1. 기존 `ParamA` 종류로 충분하면 CSV만 바꾼다.
   1. `AugmentDefinitions`에 새 `AugmentId`, `ExclusiveGroup=SKILL_AUGMENT`, `Rarity`(일반 RARE / 히든 EPIC), 표시 이름(`NameKey`)과 이득·불이익 설명(`DescriptionKey`)을 넣는다.
      - 카드는 설명을 `/`로 나눠 한 줄씩 보여 주고 "불이익 없음"은 생략한다.
   2. `AugmentEffects`에 §2의 고정값으로 1행을 넣고 `Amount`/`ParamB`/`ParamC`를 §2.3 규칙에 맞춘다.
2. 새 종류가 필요하면 한 작업으로 묶어 다섯 곳을 함께 고친다.
   - `AugmentContentValidatorLogic.IsSkillModifierValid`
   - `AugmentRuntimeLogic.CanBindSkillAugment`와 `ApplySkillModifier`
   - 전투 쪽 소비 코드(필요하면 `GetConditionalDamageBonus`·`OnSkillDamageApplied`·`CompleteSkillAugment` 등)
   - Balance Studio `#vocabCatalog`의 `augment.modifiers`, `skillAugmentProblems`, `canBindAugment`, `applyAugmentToConcept`
   - 이 문서 §2~§4
3. Balance Studio 증강 탭에서 데이터 오류 0, 붙는 스킬, 누적 시뮬레이터 결과를 확인한다.
   - `node tools/check-balance-vocab.cjs`도 통과해야 한다.
4. Maker **Stop → Refresh → Play**로 확인한다.
   - `_ContentValidatorLogic:ValidateAugmentById(id)`가 성공해야 한다.
   - 업그레이드 보상 카드 설명(`증강 횟수: n/4`)과 전투 수치가 같아야 한다.
   - 리롤 로그 `[AugmentReroll]`, 적용 로그 `[SkillAugment] applied`가 찍혀야 한다.

## 10. 코드 위치 요약

| 책임 | 위치 |
|---|---|
| 증강 정의 읽기 | `AugmentDefinitionRepositoryLogic.GetSkillAugmentCatalog` |
| 행 검증 | `AugmentContentValidatorLogic.ValidateById` / `IsSkillModifierValid` |
| 붙는지 판정 | `AugmentRuntimeLogic.CanBindSkillAugment` |
| 수치 적용·누적 | `AugmentRuntimeLogic.ApplySkillModifier` / `BuildSkillBundle` / `GetEffectiveSkillBundle` |
| 전투 추가 효과 | `AugmentRuntimeLogic.GetConditionalDamageBonus` / `OnSkillDamageApplied` / `CompleteSkillAugment` / `QueueSkillRegeneration` / `AdvanceSkillRegeneration` |
| 전투에서 읽기 | `BattleSessionComponent.GetEffectiveSkillValidation` (정밀 처형 환급·무위의 준비 피해 0 처리 포함), `SkillExecutionLogic` (시전 완료 시 `CompleteSkillAugment`) |
| 보유·리롤권 상태 | `PlayerRunAugmentComponent` (`SetSkillAugment`, `RemoveSkillAugments`, `GrantClearReroll`, `ResetForRun`) |
| 3택 생성·적용·리롤 | `UpgradeSkillStageLogic` (`BuildUpgradeState`, `RequestApplyUpgrade`, `RequestSkipUpgrade`, `RequestReroll`) |
| 3택 화면 | `UpgradeSkillStageUIComponent` (`ui/UpgradeSkillStageUI`) |
| 새 스킬 리롤 | `NewSkillStageChoiceComponent.ProcessReroll`, `NewSkillSelectionUILogic` |
| 보상 종류 결정 | `StageTransitionManagerLogic.DetermineIntermediateMap` / `ChooseRewardKind` |
| 힐 횟수 | `PlayerRunInventoryComponent` (`GrantHealChargeReward`, `GrantBossHealCharge`, `SpendHealCharge`) |
| 스킬 트리 | `SkillTreeServiceLogic` (`GetUnlockCoinCost`, `ResolveSkill`, `EvaluatePurchase`) |

## 11. 확인이 필요한 점

1. **부르는 곳이 없는 코드가 남아 있다.**
   - `PlayerRunInventoryComponent.UpgradeSkill`과 `PlayerRunAugmentComponent.TransferSkillAugments`(§8).
   - `PlayerRunAugmentComponent.GetSkillAugmentId`, `AugmentRuntimeLogic.GetBoundSkillAugment`(첫 증강 하나만 돌려주는 누적 이전의 흔적).
   - `BuildUpgradeState`의 `normal`(일반 강화) 목록은 항상 비어 있다.
2. **힐 횟수 충전도 4단계 제한에 들어간다.**
   - 힐 후보도 `GetSkillAugmentIds(힐) < 4`일 때만 만들어진다. 힐 횟수 충전을 4번 고르면 그 런에서 힐은 더 이상 충전 카드를 받지 못한다.
   - 09-28판까지는 힐이 이 제한에서 빠져 있었다. 의도한 변경인지 확인이 필요하다.
3. **보유한 증강은 다시 판정하지 않고 적용한다(§4.3).**
   - 런 도중에는 문제가 없지만, CSV를 바꿔 조건이 깨진 증강도 저장된 순서대로 그대로 적용된다.
4. `Docs/Skill-Matrix-Implementation.md`는 스킬 트리 해금 가격을 30으로 적었다. 코드(`GetUnlockCoinCost`)는 200이다.
5. 규칙과 수치는 코드·CSV를 읽어 정리했다. 업그레이드 보상 화면의 리롤·누적 표시와 전투 추가 효과가 Maker에서 실제로 어떻게 보이는지는 이 문서 작성 중 확인하지 않았다.
