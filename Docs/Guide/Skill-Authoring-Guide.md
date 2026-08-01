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
| `TargetingType` | string | `FRONT_CELL` | 현재 `FRONT_CELL`만 지원 |
| `Range` | integer | `1` | 0 이상 |
| `CooldownTurns` | integer | `0` | 0 이상 |
| `CostType` | string | 빈 문자열 | 비용이 없으면 비움 |
| `CostValue` | number | `0` | 0 이상 |
| `MotionProfileId` | string | `basic_slash` | 표현 프로필 ID |
| `EffectSetId` | string | `basic_slash_effects` | Effect Step 묶음 |
| `RequiredJobTag` | string | 빈 문자열 | 제한이 없으면 비움 |
| `ActionDuration` | number | `0.45` | 큐에서 다음 스킬로 넘어가기까지의 시간 |

현재 호환 Definition은 다음과 같다.

```csv
SchemaVersion,SkillId,DisplayName,SkillTags,TargetingType,Range,CooldownTurns,CostType,CostValue,MotionProfileId,EffectSetId,RequiredJobTag,ActionDuration
1,basic_slash,기본 베기,attack|starter,FRONT_CELL,1,0,,0,basic_slash,basic_slash_effects,,0.45
1,heavy_slash,강한 베기,attack|heavy,FRONT_CELL,1,1,,0,heavy_slash,heavy_slash_effects,,0.70
1,push,밀치기,control|displacement,FRONT_CELL,1,1,,0,push,push_effects,,0.40
1,slash_push_combo,베고 밀치기,attack|control|combo,FRONT_CELL,1,2,,0,basic_slash,slash_push_combo_effects,,0.55
```

## SkillEffectSteps

| 열 | 타입 | 예시 | 규칙 |
|---|---|---|---|
| `SchemaVersion` | integer | `1` | Skill 스키마와 같은 버전 |
| `EffectSetId` | string | `basic_slash_effects` | Skill Definition과 연결 |
| `StepIndex` | integer | `1` | 1부터 빈 번호 없이 증가 |
| `EffectType` | string | `DAMAGE` | 현재 `DAMAGE`, `PUSH` 지원 |
| `TargetSelector` | string | `FRONT_TARGET` | 현재 `FRONT_TARGET`만 지원 |
| `Value` | number | `3` | 0 이상 |
| `ParameterA` | string | `SOURCE_BASIC_ATTACK` | Effect별 선택 매개변수 |
| `ParameterB` | string | 빈 문자열 | Effect별 선택 매개변수 |
| `ConditionId` | string | 빈 문자열 | 조건이 없으면 비움 |

현재 호환 Effect Step은 다음과 같다.

```csv
SchemaVersion,EffectSetId,StepIndex,EffectType,TargetSelector,Value,ParameterA,ParameterB,ConditionId
1,basic_slash_effects,1,DAMAGE,FRONT_TARGET,3,SOURCE_BASIC_ATTACK,,
1,heavy_slash_effects,1,DAMAGE,FRONT_TARGET,6,,,
1,push_effects,1,PUSH,FRONT_TARGET,1,,,
1,slash_push_combo_effects,1,DAMAGE,FRONT_TARGET,1,,,
1,slash_push_combo_effects,2,PUSH,FRONT_TARGET,1,,,
```

`SOURCE_BASIC_ATTACK`은 고정 `Value` 대신 시전자
`BattleUnitComponent.BasicAttackDamage`를 사용하는 현재 호환 규칙이다.

## 새 단일 Effect 스킬 추가 순서

> ⚠ 현재 `SkillDefinitions`/`SkillEffectSteps` Dataset 자체가 프로젝트에 없다(맨 아래 "Dataset 전환" 참고). 아래 순서는 Dataset이 준비된 뒤에만 그대로 실행된다 — 먼저 "Dataset 전환"의 "Gate B를 열기 위한 순서"부터 완료한다. 이 Dataset은 Maker의 생성·가져오기 화면에서만 만들 수 있고, `.userdataset`을 직접 JSON으로 편집하지 않는다.

1. `SkillDefinitions`에 고유 `SkillId` 행을 추가한다.
2. 고유 `EffectSetId`를 정하고 `SkillEffectSteps`에 Step 1을 추가한다.
3. 현재 지원하는 Targeting과 EffectType인지 확인한다.
4. 큐 또는 서버 테스트에서 `TryQueueTile(SkillId)`를 호출한다.
5. `[ContentValidation] skill valid`와 `[SkillExecution] started` 로그를 확인한다.
6. 타격 Cell, 피해 또는 밀치기, 모션, 큐 완료 시점을 확인한다.

새 스킬을 추가하기 위해 `TryQueueTile`이나 `ExecuteNextQueuedTile`에 SkillId 분기를 넣지 않는다.

## 아직 Handler가 필요한 경우

다음 중 하나라면 현재 데이터 행만으로는 추가할 수 없다.

- `FRONT_CELL` 이외의 타기팅
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

## Dataset 전환

현재 네 스킬(`basic_slash`, `heavy_slash`, `push`, `slash_push_combo`)은 기존 동작을
유지하기 위한 호환 Definition을 사용한다.
Maker에서 `SkillDefinitions`와 `SkillEffectSteps` UserDataSet을 추가하면 Dataset 행이
자동으로 우선한다. 두 Dataset의 대표 스킬 회귀 테스트가 끝난 뒤
`SkillDefinitionRepositoryLogic.AllowPrototypeCompatibilityFallback`을 `false`로 바꾼다.

UserDataSet 메타데이터와 CSV는 직접 JSON을 수정하지 않고 Maker의 UserDataSet
생성·가져오기 절차를 사용한다.

현재 프로젝트에는 두 Dataset의 `.userdataset/.csv` 페어가 모두 없다. 따라서 신규 Skill
대량 제작 Gate B는 닫혀 있다.

Gate B를 열기 위한 순서:

1. Maker의 `RootDesk/MyDesk/03_Data/`에서 `SkillDefinitions`,
   `SkillEffectSteps` UserDataSet을 각각 생성한다.
2. 각 `.userdataset`과 같은 이름의 `.csv`가 같은 폴더에 생성됐는지 확인한다.
3. 본 문서의 호환 Definition 4개와 Effect Step을 Maker Dataset 화면에서 입력하거나
   가져온다.
4. 네 Skill 모두 `[ContentValidation] skill valid` 로그와
   `[SkillDefinition] loaded` 로그의 `source=DATASET`을 확인한다.
5. DAMAGE, PUSH, 복합 Step, Cooldown 0·1·2 회귀 테스트를 통과한다.
6. `AllowPrototypeCompatibilityFallback=false`로 바꾸고 존재하지 않는 Skill과 Effect
   Set이 정상적으로 거절되는지 확인한다.

`.userdataset` 메타데이터는 직접 JSON으로 편집하지 않는다. CSV는 실제 행 데이터
sidecar이지만 최초 페어와 열 정의는 Maker가 생성하도록 한다.
