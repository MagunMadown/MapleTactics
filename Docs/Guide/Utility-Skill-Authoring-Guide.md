# 유틸리티 스킬 작성 가이드

## 책임 구분

- `{Job}SkillDefinitions`: 직업별 일반 공격 타일. 직업당 한 테이블.
- **`UtilitySkillDefinitions`: 모든 직업의 유틸리티 스킬을 한 테이블에 모은 공용 카탈로그.**
- **`UtilitySkillEffectSteps`: 위 카탈로그 전용 Effect Step 테이블.**
- `JobMechanic`: 큐 밖에서 동작하는 직업 고유 전투 규칙. 유틸리티 스킬과 다르다.

유틸리티 스킬은 가짓수가 직업당 1개 수준이라 직업별 테이블을 5개로 나누지 않고 한 테이블에
모은다. 소속 직업은 행의 `RequiredJobTag`가 소유한다.

기준일 `2026-08-22`.

## 현재 상태 — 데이터 전용, 런타임 미배선

> ⚠️ **두 테이블은 아직 어떤 코드도 읽지 않는다.** 발동 방식이 확정되지 않아 의도적으로
> 분리된 상태로 두었다. 이 상태에서는 기존 전투에 아무 영향이 없다.

배선하지 않은 이유는 취향이 아니라 **검증 게이트가 막기 때문**이다.

| 지금 배선하면 | 무슨 일이 일어나는가 |
|---|---|
| `SkillDefinitionRepositoryLogic.GetSkillDataSetNames()`에 `UtilitySkillDefinitions` 추가 | `ContentIntegrityValidatorLogic.CollectSkillDataSets()`가 이 테이블을 집어 전 행에 `ValidateSkillById`를 돌린다. 아래 EffectType 3종이 미구현이라 `UNKNOWN_EFFECT`로 떨어지고 **전투 시작 Gate 전체가 차단**된다. |
| Effect Step을 `SkillEffectSteps.csv`에 추가 | 참조하는 스킬 테이블이 등록돼 있지 않으므로 전 행이 `ORPHAN_EFFECT_SET`이 되어 같은 Gate가 차단된다. |
| `JobStartingSkillEntries.csv`에 유틸리티 스킬 추가 | `JobContentValidatorLogic`이 시작 스킬마다 `ValidateSkillById`를 호출한다. 등록되지 않은 SkillId라 `INVALID_STARTING_SKILL_REFERENCE` → `JobDefinitions` 도메인 검증 실패 → 역시 Gate 차단. |

따라서 **배선은 EffectType Executor 3종 구현과 반드시 한 작업으로 묶는다.** 데이터만 먼저
연결하는 중간 상태는 존재할 수 없다.

## 테이블 스키마

두 테이블 모두 기존 스킬 스키마를 그대로 쓴다. 열 의미는
[`Skill-Authoring-Guide.md`](./Skill-Authoring-Guide.md)가 단일 소유자다.

- `UtilitySkillDefinitions.csv` — `{Job}SkillDefinitions`와 **동일한 34열**
- `UtilitySkillEffectSteps.csv` — `SkillEffectSteps`와 **동일한 9열**

스키마를 재사용하므로 배선 시점에 `ConvertSkillRow`·`ConvertEffectStepRow`를 고칠 필요가 없다.
데이터셋 이름만 Repository에 추가하면 된다.

## 현재 5행

| SkillId | 직업 | 표시명 | TargetingType | Range | Cooldown | 설명 |
|---|---|---|---|---|---:|---|
| `royal_guard` | warrior | 로얄 가드 | `SELF` | 1 | 4 | 다음 플레이어 턴까지 받는 모든 피해를 무효화한다 |
| `teleport` | mage | 텔레포트 | `SELF` | 1 | 4 | 바라보는 방향의 비어있는 칸 중 가장 먼 칸으로 이동한다 |
| `fairy_turn` | archer | 페어리 턴 | `FRONT_CELL` | 1 | 4 | 바로 앞 적을 바라보는 방향으로 최대 2칸 민다. 막히면 그 앞까지만 |
| `rapid_evasion` | thief | 래피드 이베이젼 | `SELF` | 1 | 4 | 전방에서 가장 먼 적의 1칸 뒤로 이동한다. 그 칸이 없거나 점유돼 있으면 실패 |
| `tidal_wave` | pirate | 파도 | `RANGE_OFFSETS` | 5 | 4 | 전방의 적과 시전자가 벽에 막힐 때까지 같은 거리만큼 함께 밀려난다 |

`SELF` 행의 `Range=1`은 `heal` 행과 같은 관례다. `SkillTargetResolverLogic.BuildOffsets`가
`SELF`에서 빈 오프셋을 돌려주므로 Range는 판정에 쓰이지 않지만 Validator가 `Range > 0`을
요구한다. 실제 스캔 거리 같은 수치는 Range가 아니라 **Effect Step의 `Value`·`ParameterA`가
소유한다.**

`CooldownTurns=4`는 유틸리티 스킬 전 행 공통값이다. 직업별 스킬은 단계 번호를 그대로 쓰지만
(1단계 `1`턴 / 2단계 `2`턴) 유틸리티는 전투 형태를 크게 흔드는 대신 다시 쓰기까지 오래
기다리는 축이라 그 계단 밖에 둔다. 규칙 표는
[`Skill-Authoring-Guide.md`](./Skill-Authoring-Guide.md) "저작값 규칙"이 소유한다.
`FreePlay=false`로 기존 스킬과 같은 턴 소비 규칙을 따른다.

> 이 값은 **배선 전까지 아무 코드도 읽지 않는다.** 위 "현재 상태" 절 그대로 두 테이블은
> 여전히 Repository에 등록되지 않았으므로, `4`턴은 Executor 3종 구현과 함께 배선되는
> 시점에 실제로 적용된다.

## Effect Step 계약 (미구현)

세 EffectType 모두 아직 Executor가 없다. 아래는 데이터가 표현하는 **의도**이며,
구현 시 이 계약을 그대로 만족시킨다.

```csv
SchemaVersion,EffectSetId,StepIndex,EffectType,TargetSelector,Value,ParameterA,ParameterB,ConditionId
1,royal_guard_effects,1,GUARD,SELF_UNIT,0,UNTIL_NEXT_PLAYER_TURN,ALL_DAMAGE,
1,teleport_effects,1,MOVE_SELF,SELF_UNIT,0,FARTHEST_EMPTY_FORWARD,,
1,fairy_turn_effects,1,PUSH_DISTANCE,PRIMARY_TARGET,2,STOP_BEFORE_BLOCKED,,
1,rapid_evasion_effects,1,MOVE_SELF,SELF_UNIT,1,BEHIND_FARTHEST_ENEMY_FORWARD,REQUIRE_EMPTY,
1,tidal_wave_effects,1,PUSH_DISTANCE,ALL_SKILL_TARGETS,0,MAX,CARRY_CASTER,
```

다섯 스킬 모두 Step이 하나다. 「파도」도 적 이동과 시전자 이동을 **하나의 원자 연산**으로
묶는다 — 자세한 이유는 아래 `PUSH_DISTANCE`의 `CARRY_CASTER` 항목에 있다.

### `GUARD`

| 항목 | 값 |
|---|---|
| `Value` | 피격 시 적용할 피해값. `0`이면 완전 무효화 |
| `ParameterA` | 지속 기간. 현재 `UNTIL_NEXT_PLAYER_TURN`만 |
| `ParameterB` | 대상 피해 종류. 현재 `ALL_DAMAGE`만 |

상태 소유자는 **시전자의 `BattleUnitComponent`**여야 한다. `Session`이나 `@Logic`에
플레이어별 가드 상태를 두지 않는다. 소비·만료는 `ApplyDamage` 경로와 플레이어 턴 시작
경계에서 각각 처리하고, 만료 시 `log`로 흔적을 남긴다.

### `MOVE_SELF`

| `ParameterA` | 동작 |
|---|---|
| `FARTHEST_EMPTY_FORWARD` | Facing 방향으로 스캔해 비어있는 칸 중 가장 먼 칸으로 이동 |
| `BEHIND_FARTHEST_ENEMY_FORWARD` | Facing 방향에서 가장 먼 적을 찾아 그 `Value`칸 뒤로 이동 |

`ParameterB=REQUIRE_EMPTY`는 목표 칸이 점유·경계 밖이면 이동을 포기하고 `Success=true` +
구체 Reason으로 끝낸다(정상 실패). 이동은 반드시
`BattleSessionComponent.RelocateUnitForMechanic`처럼 **점유·경계 검사와 드롭 회수를 포함한
기존 경계**를 통과해야 한다. `ApplyCellChange`를 직접 호출하지 않는다.

### `PUSH_DISTANCE`

| 항목 | 값 |
|---|---|
| `Value` | 최대 밀림 칸 수. `0`은 무제한(`ParameterA=MAX`) |
| `ParameterA` | `STOP_BEFORE_BLOCKED` 또는 `MAX` |
| `ParameterB` | 비움 또는 `CARRY_CASTER` |

기존 `PUSH`는 항상 1칸 고정이므로 대체가 아니라 **별도 EffectType**으로 둔다. 기존 `PUSH`
행의 동작을 바꾸지 않기 위해서다. 구현은 `ResolvePushImpactOnTarget`을 1칸씩 반복 적용하는
형태가 되며, 다음을 반드시 보존한다.

- `HEAVY` Trait의 `PUSH_BLOCKED_HEAVY_TRAIT` 거부
- 경계 밖·점유 칸에서 `Success=true` + 차단 Reason
- `ALL_SKILL_TARGETS`일 때 **밀리는 방향 기준 먼 적부터** 처리해야 서로 막지 않는다

#### `ParameterB=CARRY_CASTER` — 시전자가 함께 밀려나는 형태

「파도」전용 플래그다. 대상들과 **시전자가 같은 거리만큼 한 번에** 이동한다.

이걸 `MOVE_SELF` Step을 하나 더 붙이는 방식으로 만들지 않는 이유는 **이동 거리가 서로
묶여 있기 때문**이다. 뒤따르는 Step으로 분리하면 그 Step이 앞 Step의 실제 이동 거리를 알아야
하는데, Effect Context에는 이전 Step의 결과를 넘기는 필드가 없다. 한 Executor 안에서 이동
거리 N을 한 번만 계산하면 이 결합 자체가 사라진다.

이동 거리 N은 **가장 앞선 대상이 벽에 막히기 전까지 갈 수 있는 칸 수**이며, 대상 전원과
시전자가 동일하게 N칸 이동한다. 따라서 대열의 간격은 보존된다.

```text
보드 0~5, 플레이어 2번칸(Right), 적 4번칸

적 4 → 5 (벽에 막힘, N=1)
플레이어 2 → 3 (동일하게 1칸)
사이의 빈칸은 그대로 유지된다
```

`ALL_SKILL_TARGETS`와 함께 쓰며, 대상이 하나도 없으면 시전자도 움직이지 않는다
(`Success=true`, `MISS_EMPTY`).

> ⚠️ **연출 경로가 현재 서로 다르다.** 밀리는 적은 `ResolvePushImpactOnTarget` →
> `PlaceEntity`로 **즉시 순간이동**하고, 플레이어는 `TryMove` →
> `StartPlayerGridMovePresentation`으로 **트윈 이동**한다. 판정이 같은 Impact 시점이어도
> 화면에서는 적만 툭 끊겨 보여 "함께 밀려나는" 느낌이 나지 않는다. `CARRY_CASTER` 구현 시
> 밀리는 대상도 같은 이동 연출을 타도록 표현 경로를 맞춘다.

## 배선 체크리스트 (발동 방식 확정 후)

1. `GuardEffectExecutorLogic`, `MoveSelfEffectExecutorLogic`, `PushDistanceEffectExecutorLogic`을
   `01_Combat/Skills/EffectExecutors/`에 추가한다.
2. `EffectRouterLogic.ExecuteEffectStep`에 세 EffectType 분기를 한 곳만 추가한다.
3. `ContentValidatorLogic`의 지원 EffectType 목록에 세 개를 추가한다.
4. `SkillDefinitionRepositoryLogic`에 `UtilitySkillDataSetName`을 추가하고
   `GetSkillDataSetNames()`·`GetPlayerGrantableSkillIds()`에 포함한다.
5. Effect Step 조회가 `UtilitySkillEffectSteps`도 읽도록 `GetEffectSteps`를 확장한다.
   (또는 배선 시점에 행을 `SkillEffectSteps`로 이관한다 — 둘 중 하나를 고르고 문서에 남긴다.)
6. `GetJobSkillDefinitions`가 유틸리티 행을 어떻게 다룰지 정한다.
   현재 이 메서드는 `RequiredJobTag`로만 거르므로 **그대로 두면 신규 스킬 선택·강화 스테이지·
   도감에 유틸리티 스킬이 섞여 나온다.** 게이팅을 함께 정한다.
7. 직업 자동 보유로 확정했으므로 `JobStartingSkillEntries.csv`에 직업별 1행씩 추가한다.
   `SlotIndex`는 해당 `StartingSkillSetId`의 마지막 다음 번호로 연속이어야 한다.
8. Maker Refresh → `[ContentIntegrity] valid` → 스킬별 실행·쿨다운·정상 실패 경로를 검증한다.

## 남은 저작 항목

- `CastEffectRuid`, `HitEffectRuid`, `IconRuid`가 모두 비어 있다. 비어 있어도 스킬은 동작하고
  표현 계층이 기본 스프라이트로 대체한다. 실제 RUID는 `msw-search`로 각 스킬 리소스 팩을
  찾아 채운다. 절차는 [`Skill-Authoring-Guide.md`](./Skill-Authoring-Guide.md) "아이콘"을 따른다.
- `CastSoundRuid`/`HitSoundRuid`는 5행 모두 채워져 있지만, `UtilitySkillDefinitions`는 아직
  어떤 리포지토리도 로드하지 않으므로 런타임에서 재생되지 않는다. 데이터셋을
  `SkillDefinitionRepositoryLogic`에 연결하는 시점에 함께 살아난다.
- `MotionProfileId`는 기존 `basic_slash`/`heavy_slash`를 재사용한다. 유틸리티 전용 모션이
  필요하면 Motion Profile을 먼저 확장한다.
- 2단계 강화 행은 없다. 전 행이 `SkillTier=1`, `BaseSkillId` 비움이다.
