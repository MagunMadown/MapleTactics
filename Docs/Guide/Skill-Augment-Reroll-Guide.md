# 스킬 증강·리롤 가이드

기준: `develop` `c8c3611` (2026-09-28). 이 문서의 규칙과 수치는 아래 코드와 CSV에서 옮겨 적었다.
코드가 바뀌면 코드가 우선이며, 이 문서를 같은 변경에서 갱신한다.

- 데이터: `03_Data/AugmentDefinitions.csv`, `03_Data/AugmentEffects.csv` (`ExclusiveGroup=SKILL_AUGMENT` 행)
- 판정·적용: `01_Combat/Augments/AugmentRuntimeLogic.mlua` (`CanBindSkillAugment`, `ApplySkillModifier`, `BuildSkillBundle`)
- 데이터 검증: `03_Data/Repositories/AugmentContentValidatorLogic.mlua` (`IsSkillModifierValid`)
- 보유 상태: `04_Roguelike/RunManager/PlayerRunAugmentComponent.mlua`
- 보상 화면: `04_Roguelike/SkillStage/UpgradeSkillStageLogic.mlua`, `NewSkillStageChoiceComponent.mlua`

직업 시작 패시브(`TURN_START` · `HEAL`)는 같은 표를 쓰지만 별개의 기능이다.
[`Augment-Authoring-Guide.md`](./Augment-Authoring-Guide.md)를 따른다.

## 1. 한눈에 보기

```text
전투 승리
 ├─ 리롤권 +1 판정 (보스 100%, 그 외 20%)
 └─ 중간 보상 맵 결정 (StageTransitionManagerLogic.DetermineIntermediateMap)
     ├─ henesys_stage_01 첫 클리어 → new_skill_stage (새 1티어 스킬이 없으면 new_upgrade_stage)
     ├─ 안 가진 1티어 직업 스킬이 없음 → new_upgrade_stage
     └─ 그 외 → 25% new_upgrade_stage / 75% new_skill_stage   ※ §10-1 참고
new_upgrade_stage (강화·증강 3택)          new_skill_stage (새 스킬 2택)
 ├─ 카드 1장 선택 → 강화 또는 증강 적용      ├─ 카드 1장 선택 → 스킬 획득(칸이 차면 교체)
 ├─ 카드별 리롤 (리롤권 1)                   ├─ 카드별 리롤 (리롤권 1)
 └─ 건너뛰기 (항상 가능)                      └─ 건너뛰기/포기
다음 스테이지
```

- 스킬 증강은 **강화가 끝난 스킬**에 붙는 이득·불이익 묶음이다. 한 스킬에 **최대 6단계**까지 쌓인다.
- 증강은 런 동안만 유지된다. 새 런에서, 그리고 그 스킬을 상점에서 팔면 사라진다.
- 리롤권은 업그레이드 스테이지와 새 스킬 스테이지가 **같은 개수**를 나눠 쓴다.

## 2. 증강 14종 (현재 데이터)

모든 스킬 증강 행은 `SchemaVersion=1`, `StackPolicy=UNIQUE`, `MaxStacks=1`, `ExclusiveGroup=SKILL_AUGMENT`,
`AugmentEffects` 1행(`TriggerType=SKILL_BUILD`, `ConditionType=ALWAYS`, `EffectType=SKILL_MODIFIER`,
`TargetType=SKILL`, `Priority=100`)이다. 종류는 `ParamA`, 변화량은 `Amount`, 쿨타임 증감은 `ParamB`,
히든 여부는 `ParamC=HIDDEN`이다. `StackPolicy=UNIQUE`는 전역 증강용 값이며 스킬 증강의 반복 선택을 막지 않는다.

"붙는 스킬 수"는 현재 직업 스킬 68개를 **증강 0단계 상태**로 판정한 값이다(Balance Studio 증강 탭과 같은 판정).
증강을 하나라도 받을 수 있는 스킬은 19개(마지막 강화 단계 17개 + 힐 2개)다.

| AugmentId | 이름 | 등급 | ParamA | Amount | ParamB | 효과 | 붙는 스킬 수 |
|---|---|---|---|---:|---:|---|---:|
| `skill_power` | 강타 | RARE | `POWER` | 2 | +3 | 직접 피해 +2 / 쿨타임 +3 | 7 |
| `skill_quick` | 속공 | RARE | `QUICK` | 1 | −2 | 직접 피해 −1 / 쿨타임 −2 | 13 |
| `skill_volley` | 연사 | RARE | `VOLLEY` | 1 | +2 | 타수 +1 / 쿨타임 +2 | 2 |
| `skill_compact` | 압축 사격 | RARE | `COMPACT` | 1 | −2 | 타수 −1 / 쿨타임 −2 | 2 |
| `skill_area` | 확산 | RARE | `AREA` | 1 | +3 | 대상별 피해 +1 / 쿨타임 +3 | 8 |
| `skill_range` | 장거리 사격 | RARE | `RANGE` | 1 | +1 | 사거리 +1칸 / 쿨타임 +1 | 4 |
| `skill_precise` | 정밀 처형 | RARE | `PRECISE` | 2 | +1 | 딱 맞는 피해로 처치 시 쿨타임 −2 / 쿨타임 +1 | 7 |
| `skill_zero_damage` | 무위의 준비 | RARE | `ZERO_DAMAGE_FREE_LOAD` | 1 | 0 | 직접 피해 0 / 장착 시 턴 소모 없음 | 17 |
| `skill_heal` | 힐 횟수 충전 | RARE | `HEAL_CHARGES` | 2 | 0 | 힐 사용 횟수 +2 (최대 5) | 2 (힐) |
| `hidden_power` | 히든 · 순수한 강타 | EPIC | `POWER` | 2 | 0 | 직접 피해 +2 | 7 |
| `hidden_volley` | 히든 · 순수한 연사 | EPIC | `VOLLEY` | 1 | 0 | 타수 +1 | 2 |
| `hidden_area` | 히든 · 순수한 확산 | EPIC | `AREA` | 1 | 0 | 대상별 피해 +1 | 8 |
| `hidden_cooldown` | 히든 · 신속 | EPIC | `HIDDEN_COOLDOWN` | 2 | −2 | 쿨타임 −2 (최소 1) | 17 |
| `hidden_heal` | 히든 · 무한한 치유 | EPIC | `HEAL_UNLIMITED` | 1 | 0 | 힐 횟수 제한 해제 | 2 (힐) |

### 2.1 데이터 검증 규칙 (`IsSkillModifierValid`)

게임은 아래를 어긴 증강 행을 `INVALID_SKILL_AUGMENT`로 거절한다. Balance Studio 증강 탭도 같은 규칙으로 표시한다.

- `AugmentEffects` 행이 정확히 1개, Trigger/Condition/Effect/Target 값은 위 고정값, `Amount`는 1 이상 정수, `ParamB`는 정수.
- 일반(`ParamC` 빈 값):
  - `QUICK`, `COMPACT`는 `ParamB < 0`.
  - `HEAL_CHARGES`는 `ParamB = 0`.
  - `ZERO_DAMAGE_FREE_LOAD`는 `Amount = 1`, `ParamB = 0`.
  - 나머지는 `ParamB > 0`이다(이득의 대가).
  - `HEAL_UNLIMITED`, `HIDDEN_COOLDOWN`은 일반으로 쓸 수 없다.
- 히든(`ParamC=HIDDEN`): `POWER`, `VOLLEY`, `AREA`, `HEAL_UNLIMITED`는 `ParamB = 0`이고, `HIDDEN_COOLDOWN`은 `ParamB < 0`이다.

## 3. 어떤 스킬에 붙는가 (`CanBindSkillAugment`)

위에서부터 차례로 판정한다.

1. **힐** (`CostType=HEAL_CHARGE`): `HEAL_CHARGES`, `HEAL_UNLIMITED`만 붙는다. 힐이 아닌 스킬에는 이 둘이 붙지 않는다.
2. `SkillTier ≥ 2`이고 `BaseSkillId`가 있으며, **다음 강화가 없는 마지막 단계**(`GetNextSkillUpgrade` = `NO_UPGRADE_PATH`)여야 한다.
3. `HIDDEN_COOLDOWN`: 쿨타임이 2턴 이상이면 붙는다. 여기서 판정이 끝난다.
4. 쿨타임을 줄이는 증강(`ParamB < 0`)은 기절·빙결(`STUN`/`FREEZE`) 단계가 있는 스킬, 쿨타임 1턴 이하 스킬에 붙지 않는다.
5. `DAMAGE` 단계가 정확히 1개여야 하고, `ParameterA=SOURCE_BASIC_ATTACK`이면 안 된다.
6. `ZERO_DAMAGE_FREE_LOAD`: 이미 무위의 준비가 붙었거나 원래 턴 소모 없는(`FreePlay=true`) 스킬에는 붙지 않는다. 피해가 1 이상이어야 한다.
7. 무위의 준비가 붙은 스킬에는 이후 `RANGE`만 붙는다. `HIDDEN_COOLDOWN`은 3번에서 먼저 통과하므로 역시 붙는다.
8. 종류별 조건 (타수는 `ParameterA=MULTI_HIT`일 때 `ParameterB`, 아니면 1. "단일 대상"은 `TargetSelector=PRIMARY_TARGET` 또는 `TargetingType`이 `FRONT_CELL`/`FIRST_ENEMY_FORWARD`):

| 종류 | 조건 |
|---|---|
| `QUICK` | 1타, 적용 후 피해 ≥ 1 |
| `POWER`, `PRECISE` | 1타, 단일 대상 |
| `VOLLEY` | 2타 이상, 무기 `BOW`/`CROSSBOW`/`CLAW`/`GUN` |
| `COMPACT` | 3타 이상, 적용 후 2타 이상 |
| `AREA` | 1타, 단일 대상이 아님 |
| `RANGE` | 자기 이동(`MOVE_SELF`) 없음, 사거리 6 미만, `ProjectileRuid` 있음. `FIRST_ENEMY_FORWARD`/`FIRST_ENEMY_PIERCE`이거나 `RANGE_OFFSETS`의 모든 칸이 앞쪽(양수) |

## 4. 적용 결과 (`ApplySkillModifier`)

증강은 CSV 원본을 바꾸지 않는다. 전투(`BattleSessionComponent.GetEffectiveSkillValidation`),
보상 카드 설명, 큐 시간이 모두 `BuildSkillBundle`의 같은 결과를 읽는다.

- 쿨타임: `max(1, 현재 쿨타임 + ParamB)`. 힐 횟수 충전만 예외다.
- `POWER`/`AREA` 피해 +Amount, `QUICK` 피해 −Amount.
- `VOLLEY`/`COMPACT`는 타수 ±Amount다. 투사체 스킬이면 `ProjectileCount`도 같은 값이 된다.
- `RANGE`: 사거리 +Amount (최대 6). `RANGE_OFFSETS`면 가장 먼 칸 뒤로 칸을 이어 붙인다.
- `PRECISE`: 이 스킬의 피해로 적 HP가 정확히 0이 되면(`ExactLethal`) 남은 쿨타임을 `min(Amount, 남은 쿨타임 − 1)`만큼 줄인다.
- `ZERO_DAMAGE_FREE_LOAD`: 직접 피해가 0으로 **고정**되고 장착해도 턴을 쓰지 않는다(`FreePlay`). 피해 외 효과(밀치기·상태이상 등)는 그대로다.
  - 유물·공격 버프로 피해가 다시 생기지 않는다.
  - 저장된 "다음 공격 강화"도 소모하지 않는다.
- `HEAL_UNLIMITED`: 힐 비용이 0이 되고 `HealUnlimited`가 켜진다. 회복량과 쿨타임은 그대로다.
- `HEAL_CHARGES`: 스킬은 바뀌지 않는다. 적용하면 힐 횟수만 +2(최대 5) 된다.
- 증강이 붙은 스킬은 자기 쿨타임 감소 효과(`REDUCE_OWN_COOLDOWN`)를 써도 남은 쿨타임이 1 아래로 내려가지 않는다(`AugmentCooldownFloor=1`). 일반 턴 경과로는 0까지 내려간다.

### 4.1 누적 (최대 6단계)

- 스킬별 보유 목록은 `SkillAugmentSnapshot`(`skillId~augmentId|…`, 획득 순서)이다. 한 스킬에 최대 6개(`MaxSkillAugmentStages`)가 들어가며, 힐은 제한이 없다.
- `BuildSkillBundle`은 획득 순서대로 한 단계씩 적용한다. 각 단계는 **앞 단계까지 적용된 스킬**로 3장의 조건을 다시 판정하고, 조건을 못 맞춘 단계는 조용히 건너뛴다.
  - 속공은 피해가 1이 될 때까지만 붙는다(피해 3 → 2 → 1).
  - 강타는 조건이 유지되므로 6번 모두 붙을 수 있다(예: 라만차 스피어 피해 3 → 15, 쿨타임 4 → 22).
- 같은 증강을 여러 번 고를 수 있다. 막는 규칙이 없다.
- 카드에는 `증강 단계: n/6`이 표시된다(힐 제외).
- Balance Studio 증강 탭의 **증강 누적 시뮬레이터**가 같은 순서로 계산한다.

## 5. 업그레이드 스테이지 3택 (`UpgradeSkillStageLogic.BuildUpgradeState`)

### 5.1 입장 조건과 보상 키

- `new_upgrade_stage` 맵, 직업 선택 완료, 현재 런 인벤토리·증강 상태, 직전 전투 기록(`LastBattleRecordKey`)이 있어야 한다.
  - 하나라도 없으면 거절하고 이유를 UI로 보낸다: `NOT_IN_UPGRADE_STAGE`, `JOB_NOT_SELECTED`, `RUN_INVENTORY_UNAVAILABLE`, `BATTLE_REWARD_CONTEXT_UNAVAILABLE`, `RUN_AUGMENT_UNAVAILABLE`.
- 보상 키 `upgrade_skill_stage:<LastBattleRecordKey>`가 이미 쓰였으면 `UPGRADE_ALREADY_APPLIED`로 거절한다.
- 제안은 `런 번호:보상 키:스킬 인벤토리 리비전:증강 리비전`으로 **캐시**된다. 화면을 다시 열어도 새로 뽑지 않는다.

### 5.2 판매한 스킬 자리 (우선)

상점에서 스킬을 팔아 `PendingSoldSkillChoices > 0`이고 스킬 칸에 빈 자리가 있으면 이 경로가 우선한다.
이번 보상은 **안 가진 계열의 1티어 기본 스킬**만 최대 3장 제안하고, 강화·증강 카드는 나오지 않는다.
하나를 고르면 `PendingSoldSkillChoices`가 1 줄어든다.

### 5.3 후보 풀

보유 스킬마다 다음 중 하나로 분류한다. 힐은 횟수가 0이어도 후보다.

| 풀 | 조건 |
|---|---|
| 일반 강화 | 다음 강화 단계가 있고 힐이 아님 |
| 증강 | 마지막 단계(또는 힐)이고 증강이 6개 미만(힐은 제한 없음)이며 `CanBindSkillAugment` 통과. 힐은 `HealUnlimited`가 아닐 때만, `skill_heal`은 남은 횟수가 4 미만일 때만 |
| 히든 | 위 증강 조건을 통과한 히든 증강이 있는 스킬마다 **한 번** 3% 판정. 당첨되면 그 스킬의 히든 증강 중 1개가 후보가 된다 |

### 5.4 3장 구성 순서

1. 당첨된 히든 카드 (최대 3장)
2. 증강 카드 1장 (무작위)
3. 일반 강화 카드 1장 (무작위)
4. 남은 일반 강화 + 증강 카드를 섞어 3장이 될 때까지 채움

### 5.5 선택과 건너뛰기

- **일반 강화**: `PlayerRunInventoryComponent.UpgradeSkill`로 스킬을 교체한다.
- **증강**: `PlayerRunAugmentComponent.SetSkillAugment`로 단계를 하나 추가한다.
  - 보상 키가 이미 쓰였으면 `UPGRADE_ALREADY_APPLIED`.
  - 스킬을 안 가졌으면 `SKILL_NOT_OWNED`, 6단계를 넘으면 `SKILL_AUGMENT_LIMIT`.
  - 다시 판정해서 안 붙으면 `INVALID_SKILL_AUGMENT`.
- **힐 횟수 충전**: `GrantHealChargeReward(2)`로 처리한다. 남은 횟수가 4 이상이거나 무한 치유면 `HEAL_CHARGES_SUFFICIENT`로 거절한다.
- **히든 · 무한한 치유**: 증강으로 추가하고 `HealUnlimited=true`로 바꾼다.
- **건너뛰기**: 제안이 있어도 언제든 가능하다. 보상 키를 소모하므로 돌아와도 다시 받을 수 없고, 쓴 리롤권은 돌려주지 않는다.

## 6. 리롤

### 6.1 리롤권 개수 (`PlayerRunAugmentComponent.AvailableRerollCount`)

| 시점 | 변화 |
|---|---|
| 런 시작 (`ResetForRun`) | `BaseRerollCount` 2 + 유니온 `AUGMENT_REROLL` 보너스 |
| 전투 승리 (`GrantClearReroll`) | 보스 처치 시 +1 확정, 그 외 20% 확률로 +1. 같은 전투 완료 키로는 한 번만 판정(꽝도 기록) |

- **유니온 보너스**: `UnionStatDefinitions`의 `AUGMENT_REROLL`(최대 2레벨, 레벨당 +1)이다. 유니온 화면에는 "증강 리롤"로 표시된다.
- **획득 표시**: 얻은 리롤권은 결과 화면 보상 목록에 "증강 리롤권"으로 나온다(`RecordRoundReward("REROLL", …)`).

### 6.2 업그레이드 스테이지 슬롯 리롤 (`RequestReroll`)

- 카드 한 장만 바꾼다. 요청에 슬롯 번호, 리비전, 현재 카드 토큰을 담는다.
  - 셋 중 하나라도 어긋나면 `STALE_OFFER`로 거절하고 화면을 다시 받는다.
- 바꿀 후보는 **같은 스킬의 다른 증강** 중 화면에 없는 것이다. 판매 자리 카드는 다른 새 기본 스킬로 바뀐다.
  - 일반 강화 카드는 대부분 대체 후보가 없다. 강화가 남은 스킬에는 증강 후보가 없기 때문이다.
- 후보 중 히든이 있으면 히든만 고른다. 히든은 제안을 캐시할 때 한 번 판정한 결과만 쓰므로, 리롤을 반복해도 새 히든 판정은 일어나지 않는다.
- 후보가 없으면 `NO_ALTERNATIVE`를 돌려준다. 리롤권은 **차감하지 않는다**("다른 후보가 없습니다 · 리롤권 유지").
- 카드가 실제로 바뀐 경우에만 1장 차감한다. 남은 리롤권이 0이면 `NO_REROLLS`.

### 6.3 새 스킬 스테이지 슬롯 리롤 (`NewSkillStageChoiceComponent.ProcessReroll`)

- 보이는 카드는 `NewSkillChoiceCount`(현재 2)장이다. 리롤하면 한 슬롯을 **아직 안 보인 후보**와 맞바꾼다.
  - 후보는 안 가진 계열의 1티어 스킬이다.
- 후보가 없으면 `NO_ALTERNATIVE`, 리롤권이 없으면 `NO_REROLLS`이다. 둘 다 차감하지 않는다.
- 보상 키·리비전·스킬 인벤토리가 바뀌었으면 `STALE_REWARD_CONTEXT` / `STALE_OFFER`로 거절한다.

## 7. 스킬 판매와 증강

상점 판매 목록에 보유 스킬이 들어간다(`RunShopLogic.CaptureSkillSellCatalog`, `PlayerRunInventoryComponent.ApplySkillSale`).

- 판매 가격(런 재화 `gold`): 강화된 스킬(Tier 2 이상)이나 증강이 붙은 스킬은 40, 그 외 20.
- 마지막 남은 스킬은 팔 수 없다(`LAST_SKILL_REQUIRED`).
- 팔면 그 스킬의 증강이 **모두** 사라지고(`RemoveSkillAugments`) `PendingSoldSkillChoices`가 1 늘어난다(§5.2).
- 힐을 팔면 힐 횟수와 무한 치유 상태도 사라진다.

## 8. 새 스킬 증강 추가 절차

1. 기존 `ParamA` 종류로 충분하면 CSV만 바꾼다.
   1. `AugmentDefinitions`에 새 `AugmentId`, `ExclusiveGroup=SKILL_AUGMENT`, `Rarity`(일반 RARE / 히든 EPIC), 표시 이름(`NameKey`)과 이득·불이익 설명(`DescriptionKey`)을 넣는다.
   2. `AugmentEffects`에 §2의 고정값으로 1행을 넣고 `Amount`/`ParamB`/`ParamC`를 §2.1 규칙에 맞춘다.
2. 새 종류가 필요하면 한 작업으로 묶어 네 곳을 함께 고친다.
   - `AugmentContentValidatorLogic.IsSkillModifierValid`
   - `AugmentRuntimeLogic.CanBindSkillAugment`와 `ApplySkillModifier`
   - 전투 쪽 소비 코드(필요하면)
   - Balance Studio `#vocabCatalog`의 `augment.modifiers`와 `canBindAugment`
3. Balance Studio 증강 탭에서 데이터 오류 0, 붙는 스킬, 누적 시뮬레이터 결과를 확인한다.
   - `node tools/check-balance-vocab.cjs`도 통과해야 한다.
4. Maker **Stop → Refresh → Play**로 확인한다.
   - `_ContentValidatorLogic:ValidateAugmentById(id)`가 성공해야 한다.
   - 업그레이드 스테이지 카드 설명(`증강 단계: n/6`)과 전투 수치가 같아야 한다.
   - 리롤 로그 `[AugmentReroll]`, 적용 로그 `[SkillAugment] applied`가 찍혀야 한다.

## 9. 코드 위치 요약

| 책임 | 위치 |
|---|---|
| 증강 정의 읽기 | `AugmentDefinitionRepositoryLogic.GetSkillAugmentCatalog` |
| 행 검증 | `AugmentContentValidatorLogic.ValidateById` / `IsSkillModifierValid` |
| 붙는지 판정 | `AugmentRuntimeLogic.CanBindSkillAugment` |
| 수치 적용·누적 | `AugmentRuntimeLogic.ApplySkillModifier` / `BuildSkillBundle` / `GetEffectiveSkillBundle` |
| 전투에서 읽기 | `BattleSessionComponent.GetEffectiveSkillValidation` (정밀 처형 환급·무위의 준비 피해 0 처리 포함) |
| 보유·리롤권 상태 | `PlayerRunAugmentComponent` (`SetSkillAugment`, `RemoveSkillAugments`, `GrantClearReroll`, `ResetForRun`) |
| 3택 생성·적용·리롤 | `UpgradeSkillStageLogic` (`BuildUpgradeState`, `RequestApplyUpgrade`, `RequestSkipUpgrade`, `RequestReroll`) |
| 3택 화면 | `UpgradeSkillStageUIComponent` (`ui/UpgradeSkillStageUI`) |
| 새 스킬 리롤 | `NewSkillStageChoiceComponent.ProcessReroll`, `NewSkillSelectionUILogic` |
| 보상 맵 결정 | `StageTransitionManagerLogic.DetermineIntermediateMap` |
| 힐 횟수 | `PlayerRunInventoryComponent` (`GrantHealChargeReward`, `GrantBossHealCharge`, `SpendHealCharge`) |

## 10. 확인이 필요한 점

1. **보상 맵 확률의 주석과 코드가 반대다.**
   - `DetermineIntermediateMap`의 주석은 "75% new_upgrade_stage, 25% new_skill_stage"다.
   - 코드는 `roll <= 25`일 때 `new_upgrade_stage`로 보낸다. 안 가진 1티어 스킬이 남아 있으면 실제 확률은 **업그레이드 25% / 새 스킬 75%**다.
   - 어느 쪽이 의도인지 정해야 한다.
2. **`heal_ii`(힐 II)는 업그레이드 스테이지에서 나오지 않는다.**
   - 힐은 강화 경로가 있어도 증강 풀로만 분류되므로 일반 강화 카드가 만들어지지 않는다.
   - `UpgradeSkill`에는 힐 강화 시 횟수 +1 처리가 있어, 의도된 경로가 있었는지 확인이 필요하다.
3. `PlayerRunAugmentComponent.GetSkillAugmentId`와 `AugmentRuntimeLogic.GetBoundSkillAugment`는 첫 증강 하나만 돌려준다.
   - 현재 호출하는 곳은 없다. 6단계 누적 이전의 흔적이다.
4. 규칙과 수치는 코드·CSV를 읽어 정리했다. 업그레이드 스테이지 화면의 리롤·누적 표시가 Maker에서 실제로 어떻게 보이는지는 이 문서 작성 중 확인하지 않았다.
