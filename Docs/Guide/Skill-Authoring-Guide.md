# Skill 제작 가이드

## 현재 적용 범위

플레이어 큐의 스킬 실행은 다음 경로를 사용한다.

```text
SkillId
→ SkillDefinitionRepositoryLogic
→ ContentValidatorLogic
→ BattleSessionComponent.TryExecuteSkill
→ EffectRouterLogic
→ Battle 상태 변경
```

큐 등록 가능 여부와 실행 분기는 더 이상 `basic_slash`, `heavy_slash`, `push` 문자열 목록으로
판정하지 않는다. 유효한 Skill Definition과 Effect Step이 있으면 공통
`EXECUTE_SKILL` 경로로 진입한다.

현재 `DAMAGE`와 `PUSH` Effect Step을 하나 이상 조합할 수 있다. Effect는 같은 Impact
시점에 `StepIndex` 순서로 실행된다. `CooldownTurns`는 전투 참가자마다 붙는
`SkillRuntimeStateComponent`가 소유하며 큐 등록과 실제 실행에서 모두 검증한다.

## 턴 기반 Cooldown 규칙

```text
TryQueueTile
→ 현재 Cooldown과 같은 큐의 예약 중복 검사
→ TryExecuteSkill에서 서버 최종 검사
→ 실행 시작 시 CooldownTurns 기록
→ 적 행동 전체 완료
→ 다음 PlayerTurn을 열기 직전에 1 감소
→ CooldownSnapshot 동기화와 HUD 갱신
```

- `CooldownTurns=0`: 같은 큐에 여러 번 등록할 수 있다.
- `CooldownTurns=1`: 같은 큐에 중복 등록할 수 없고, 다음 플레이어 턴에 다시 준비된다.
- `CooldownTurns=2`: 다음 플레이어 턴에는 1이 남으며 두 번째 플레이어 턴에 준비된다.
- 타격이 빗나가도 스킬 실행 자체가 시작되었다면 Cooldown을 소비한다.
- Cooldown은 Session이나 Repository가 아니라 각 전투 유닛이 독립적으로 보관한다.
- 서버의 `CanUseSkill` 결과가 판정 기준이며 HUD 버튼 비활성화는 안내용이다.

동기화 문자열은 `heavy_slash:1|slash_push_combo:2` 형식이다. UI는
`CooldownSnapshot`을 읽기만 하고 값을 직접 변경하거나 Cooldown 규칙을 다시 계산하지
않는다.

## SkillDefinitions

| 열 | 타입 | 예시 | 규칙 |
|---|---|---|---|
| `SchemaVersion` | integer | `1` | 현재 지원 버전은 1 |
| `SkillId` | string | `basic_slash` | 고유 `lower_snake_case` ID |
| `DisplayName` | string | `기본 베기` | 빈 문자열 금지 |
| `SkillTags` | string | `attack|starter` | `|`로 구분 |
| `TargetingType` | string | `FRONT_CELL` | `FRONT_CELL`, `FIRST_ENEMY_FORWARD`, `RANGE_OFFSETS` |
| `Range` | integer | `1` | 1 이상, Cell 기준 최대 사거리 |
| `TargetOffsets` | string | `1|2` | `RANGE_OFFSETS` 전용, Facing 기준 칸 오프셋을 `|`로 구분 |
| `CooldownTurns` | integer | `0` | 0 이상 |
| `CostType` | string | 빈 문자열 | 비용이 없으면 비움 |
| `CostValue` | number | `0` | 0 이상 |
| `MotionProfileId` | string | `basic_slash` | 표현 프로필 ID |
| `EffectSetId` | string | `basic_slash_effects` | Effect Step 묶음 |
| `RequiredJobTag` | string | 빈 문자열 | 제한이 없으면 비움 |
| `ActionDuration` | number | `0.45` | 큐에서 다음 스킬로 넘어가기까지의 시간 |
| `FreePlay` | boolean | `false` | `false`면 등록 자체가 턴을 소비하고, `true`면 등록 후 플레이어 턴 유지 |

현재 실제 Dataset Definition은 다음과 같다.

```csv
SchemaVersion,SkillId,DisplayName,SkillTags,TargetingType,Range,TargetOffsets,CooldownTurns,CostType,CostValue,MotionProfileId,EffectSetId,RequiredJobTag,ActionDuration,FreePlay
1,basic_slash,기본 베기,attack|starter,FRONT_CELL,1,,0,,0,basic_slash,basic_slash_effects,,0.45,false
1,quick_slash,빠른 베기,attack|starter|freeplay,FRONT_CELL,1,,0,,0,basic_slash,basic_slash_effects,,0.35,true
1,heavy_slash,강한 베기,attack|heavy,FRONT_CELL,1,,1,,0,heavy_slash,heavy_slash_effects,,0.70,false
1,push,밀치기,control|displacement,FRONT_CELL,1,,1,,0,push,push_effects,,0.40,false
1,slash_push_combo,베고 밀치기,attack|control|combo,FRONT_CELL,1,,2,,0,basic_slash,slash_push_combo_effects,,0.55,false
1,prototype_line_slash,전방 참격,attack|prototype,FIRST_ENEMY_FORWARD,3,,0,,0,basic_slash,line_slash_effects,,0.45,false
1,prototype_sweep,휩쓸기,attack|prototype,RANGE_OFFSETS,2,1|2,0,,0,heavy_slash,sweep_effects,,0.60,false
```

`FreePlay`는 효과 타입에서 자동 추론하지 않는다. 같은 `DAMAGE` 스킬이라도 Definition의
값에 따라 턴 소비 여부가 달라진다. CSV 셀은 문자열로 읽히므로 `true`/`1`/`yes`를
참으로 해석하며, 그 외 값과 빈 셀은 `false`로 취급한다. 현재 `quick_slash`는 이 흐름을
검증하기 위한 실제 Definition이며 기본 베기의 모션·효과를 재사용한다.

2026-08-01 Maker 회귀에서 `quick_slash` 등록은 `ConsumesTurn=false`로 같은
PlayerTurn을 유지했고, 뒤이어 일반 `basic_slash`를 등록했을 때만 적 라운드와 Turn 증가가
발생했다. 두 스킬의 큐 순서는 적 라운드 뒤에도 유지되고 전체 실행 후 정상적으로 비워졌다.

## SkillEffectSteps

| 열 | 타입 | 예시 | 규칙 |
|---|---|---|---|
| `SchemaVersion` | integer | `1` | Skill 스키마와 같은 버전 |
| `EffectSetId` | string | `basic_slash_effects` | Skill Definition과 연결 |
| `StepIndex` | integer | `1` | 1부터 빈 번호 없이 증가 |
| `EffectType` | string | `DAMAGE` | 현재 `DAMAGE`, `PUSH` 지원 |
| `TargetSelector` | string | `PRIMARY_TARGET` | `FRONT_TARGET`(호환), `PRIMARY_TARGET`, `ALL_SKILL_TARGETS` |
| `Value` | number | `3` | 0 이상 |
| `ParameterA` | string | `SOURCE_BASIC_ATTACK` | Effect별 선택 매개변수 |
| `ParameterB` | string | 빈 문자열 | Effect별 선택 매개변수 |
| `ConditionId` | string | 빈 문자열 | 조건이 없으면 비움 |

현재 실제 Dataset Effect Step은 다음과 같다.

```csv
SchemaVersion,EffectSetId,StepIndex,EffectType,TargetSelector,Value,ParameterA,ParameterB,ConditionId
1,basic_slash_effects,1,DAMAGE,FRONT_TARGET,3,SOURCE_BASIC_ATTACK,,
1,heavy_slash_effects,1,DAMAGE,FRONT_TARGET,6,,,
1,push_effects,1,PUSH,FRONT_TARGET,1,,,
1,slash_push_combo_effects,1,DAMAGE,FRONT_TARGET,1,,,
1,slash_push_combo_effects,2,PUSH,FRONT_TARGET,1,,,
1,line_slash_effects,1,DAMAGE,PRIMARY_TARGET,2,,,
1,sweep_effects,1,DAMAGE,ALL_SKILL_TARGETS,1,,,
```

`SOURCE_BASIC_ATTACK`은 고정 `Value` 대신 시전자
`BattleUnitComponent.BasicAttackDamage`를 사용하는 공용 규칙이다.

## 새 단일 Effect 스킬 추가 순서

`SkillDefinitions`와 `SkillEffectSteps` Dataset 전환이 완료되어 아래 절차로 바로 추가할 수 있다.

1. `SkillDefinitions`에 고유 `SkillId` 행을 추가한다.
2. 고유 `EffectSetId`를 정하고 `SkillEffectSteps`에 Step 1을 추가한다.
3. 현재 지원하는 Targeting과 EffectType인지 확인한다.
4. 큐 또는 서버 테스트에서 `TryQueueTile(SkillId)`를 호출한다.
5. `[ContentValidation] skill valid`와 `[SkillExecution] started` 로그를 확인한다.
6. 타격 Cell, 피해 또는 밀치기, 모션, 큐 완료 시점을 확인한다.

새 스킬을 추가하기 위해 `TryQueueTile`이나 `ExecuteNextQueuedTile`에 SkillId 분기를 넣지 않는다.

## 아직 Handler가 필요한 경우

대상 규칙은 다음처럼 고른다.

| 만들고 싶은 공격 | `TargetingType` | 동작 |
|---|---|---|
| 바로 앞 한 칸 공격 | `FRONT_CELL` | Facing 앞의 한 칸만 검사 |
| 빈칸을 넘어 가장 가까운 적 공격 | `FIRST_ENEMY_FORWARD` | 1칸부터 `Range`까지 순서대로 찾아 첫 적 선택 |
| 정해진 여러 칸 범위 공격 | `RANGE_OFFSETS` | `TargetOffsets`의 모든 칸 검사. 예: `1|2` |

`TargetSelector`는 한 Effect가 확정된 대상 중 누구에게 적용되는지 정한다.
`PRIMARY_TARGET`은 첫 대상 한 명, `ALL_SKILL_TARGETS`는 모든 대상을 사용한다.
`FRONT_TARGET`은 기존 데이터 호환용이며 `PRIMARY_TARGET`과 같다. 대상은 스킬 등록 시점이
아니라 실제 타격 시점에 한 번 확정되므로 모션 도중 이동한 결과가 반영되고, 같은 스킬의
여러 Effect Step은 동일한 대상 Snapshot을 공유한다.

다음 중 하나라면 현재 데이터 행만으로는 추가할 수 없다.

- 위 세 종류 이외의 타기팅
- `DAMAGE`, `PUSH` 이외의 EffectType
- 새로운 Motion Profile
- 조건식 또는 비용 소비

이 경우 기존 스킬을 복사하지 않고 해당 Target Resolver, Effect Executor 또는
Motion Profile Repository를 공통 계약으로 확장한다.

## 검증 실패

| Reason | DetailReason | 의미 |
|---|---|---|
| `UNKNOWN_SKILL` | 없음 | Skill Definition이 없음 |
| `EFFECT_SET_NOT_FOUND` | 없음 | 연결된 Effect Step이 없음 |
| `CONTENT_VALIDATION_FAILED` | `UNSUPPORTED_SKILL_SCHEMA` | SchemaVersion이 지원 버전(1)과 다름 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_SKILL_ID` | SkillId가 비어있음 |
| `CONTENT_VALIDATION_FAILED` | `DATA_DUPLICATE_SKILL_ID` | 같은 SkillId가 여러 행에 존재 |
| `CONTENT_VALIDATION_FAILED` | `SKILL_DISPLAY_NAME_MISSING` | DisplayName이 비어있음 |
| `CONTENT_VALIDATION_FAILED` | `UNSUPPORTED_TARGETING_TYPE` | 지원하지 않는 타기팅 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_SKILL_RANGE` | Range가 없거나 음수 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_SKILL_COOLDOWN` | CooldownTurns가 없거나 음수 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_SKILL_COST` | CostValue가 없거나 음수 |
| `CONTENT_VALIDATION_FAILED` | `EFFECT_SET_ID_MISSING` | EffectSetId가 비어있음 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_ACTION_DURATION` | ActionDuration이 없거나 0 이하 |
| `CONTENT_VALIDATION_FAILED` | `EFFECT_STEPS_EMPTY` | 연결된 Effect Step이 하나도 없음 |
| `CONTENT_VALIDATION_FAILED` | `UNSUPPORTED_EFFECT_SCHEMA` | Effect Step의 SchemaVersion이 스킬과 다름 |
| `CONTENT_VALIDATION_FAILED` | `EFFECT_SET_MISMATCH` | Effect Step의 EffectSetId가 스킬 정의와 다름 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_EFFECT_STEP_SEQUENCE` | StepIndex 중복 또는 누락 |
| `CONTENT_VALIDATION_FAILED` | `UNKNOWN_EFFECT` | 등록되지 않은 EffectType |
| `CONTENT_VALIDATION_FAILED` | `UNSUPPORTED_TARGET_SELECTOR` | 지원하지 않는 대상 선택 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_EFFECT_VALUE` | Effect Step의 Value가 없거나 음수 |
| `COOLDOWN_ACTIVE` | 없음 | 이전 사용으로 남은 Cooldown이 있음 |
| `COOLDOWN_RESERVED` | 없음 | Cooldown이 있는 같은 스킬이 현재 큐에 이미 등록됨 |
| `SKILL_RUNTIME_STATE_MISSING` | 없음 | 전투 유닛의 Runtime State 초기화 실패 |

Effect Executor의 Context와 새 EffectType 추가 방법은
[`Effect-Executor-Guide.md`](./Effect-Executor-Guide.md)를 따른다.

## Dataset 상태

`SkillDefinitions` 5행과 `SkillEffectSteps` 5행의 실제 Dataset 전환이 완료됐다.
`AllowPrototypeCompatibilityFallback=false`이며 production Skill 하드코딩을 다시 추가하지
않는다. 새 Dataset을 만들 때는 기존 `.userdataset` ID를 복제하지 않는다.

신규 Skill 제작 Gate B는 열려 있다. 기존 Dataset 페어의 CSV에 Definition과 Effect
Step을 함께 추가하고 Maker Refresh 후 `source=DATASET`, Validator, 실제 Effect와 Cooldown을
검증한다. 새 Dataset을 만들 때는 기존 `.userdataset` ID를 복제하지 않는다.
