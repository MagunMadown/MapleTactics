# 유틸리티 스킬 작성 가이드

기준일: 2026-09-22. 데이터의 의도가 아니라 현재 실행 코드와 검증 계약을 설명한다.

## 현재 실행 경로

두 유틸리티 테이블은 이미 런타임에서 사용한다.

`BattleSessionComponent.RequestUtilitySkill → TryUseUtilitySkill → SkillDefinitionRepositoryLogic.GetUtilitySkillBundle → ExecuteUtilityEffect`

유틸리티는 직업당 1개인 즉시 행동이다. 일반 공격 스킬의 획득·강화·예약 큐와 분리한다.
`GetSkillDataSetNames`, `GetPlayerGrantableSkillIds`, `JobStartingSkillEntries`에 추가하지 않는다.
일반 큐의 `MoveSelfEffectExecutorLogic`과 유틸리티의 이동 모드는 서로 다른 계약이다.

검증 경로:
- 전투 시작: `RunContentValidationGate → ValidateAllContent → ContentIntegrityValidatorLogic.ValidateRegisteredDomains → ContentValidatorLogic.ValidateUtilitySkills`.
- 사용 직전: `GetUtilitySkillBundle`이 같은 유틸리티 카탈로그 검증을 통과해야 번들을 반환한다. 실패하면 즉시 행동 예약 전에 거부한다.
- 공통 스킬 규칙: 유틸리티 번들도 `ValidateSkillBundle`에서 스키마·대상·범위·무기·쿨다운·효과 순서를 검사한다. 유틸리티 전용 효과 계약은 `ValidateUtilityEffect`가 검사한다.
- CSV 내보내기: 로컬 [밸런스 편집기](../../tools/balance-editor.html)가 명시적 키·참조 및 유틸리티 규칙을 검사한다. 전체 게임 규칙·리소스 존재 검증을 대신하지 않는다.

## 테이블

- `UtilitySkillDefinitions.csv`: 일반 스킬과 동일한 37열, 기본키 `SkillId`.
- `UtilitySkillEffectSteps.csv`: 9열, 기본키 `(EffectSetId, StepIndex)`.
- `RequiredJobTag`는 `JobDefinitions.JobId`를 참조하며 직업마다 정확히 한 행이 필요하다.
- `EffectSetId`는 유틸리티 전용 효과 테이블을 참조한다. 각 스킬에 정확히 한 Step, `StepIndex=1`이 필요하다.
- 일반·적 스킬과 중복된 SkillId, 중복 직업, 고아 효과, 숫자 오타는 거부한다. 숫자 검사 후에만 Repository 변환을 적용해 기본값·반올림으로 오타가 숨지 않게 한다.

## 현재 동작

| 스킬 | 직업 | 효과 |
|---|---|---|
| royal_guard | warrior | 다음 플레이어 턴까지 가드 상태로 피해 무효화 |
| teleport | mage | 전방의 빈 칸 중 가장 먼 칸으로 이동 |
| fairy_turn | archer | 바로 앞 적을 최대 2칸 밀며 막히면 중단 |
| rapid_evasion | thief | 전방에서 가장 먼 적의 1칸 뒤로 이동. 경계 밖·점유 시 실패 |
| tidal_wave | pirate | 범위 내 적들을 먼 순서로 끝까지 민 뒤 시전자를 전방의 연속된 빈 칸 끝으로 이동 |

파도는 적과 시전자가 동일 거리로 함께 이동하는 원자 연산이 아니다. 현재 구현은 각 이동을 순서대로 해결한다. 기존 문서의 대열 간격 보존 설명은 구현과 달랐다.

현재 5개 모두 `CooldownTurns=4`, `FreePlay=false`, `SkillTier=1`이다.
`SELF`의 Range도 공통 검증상 양수여야 한다. 이동 스캔은 보드 전체를 기준으로 한다.

## 허용 효과 계약

| EffectType | TargetSelector / TargetingType | Value | ParameterA | ParameterB |
|---|---|---|---|---|
| GUARD | SELF_UNIT / SELF | 0 | UNTIL_NEXT_PLAYER_TURN | ALL_DAMAGE |
| MOVE_SELF | SELF_UNIT / SELF | 0 | FARTHEST_EMPTY_FORWARD | 비움 |
| MOVE_SELF | SELF_UNIT / SELF | 양의 정수 | BEHIND_FARTHEST_ENEMY_FORWARD | REQUIRE_EMPTY |
| PUSH_DISTANCE | PRIMARY_TARGET 또는 ALL_SKILL_TARGETS / SELF 제외 | 양의 정수 | STOP_BEFORE_BLOCKED | 비움 또는 CARRY_CASTER |
| PUSH_DISTANCE | PRIMARY_TARGET 또는 ALL_SKILL_TARGETS / SELF 제외 | 0 | MAX | 비움 또는 CARRY_CASTER |

`ConditionId`는 실행 코드에서 평가하지 않으므로 비워야 한다.
비용 차감·유틸리티 강화·투사체는 지원하지 않으므로 `CostType=""`, `CostValue=0`, `SkillTier=1`, `BaseSkillId=""`, `ProjectileRuid=""`을 유지한다. FreePlay는 false만 허용한다.
실행되지 않는 값을 채워 기능이 적용된 것처럼 보이는 저작을 검증에서 거부한다.

이동 목적지 없음은 `Success=false / UTILITY_NO_EMPTY_DESTINATION`,
대상 없음은 `Success=false / UTILITY_NO_TARGET`,
대상이 있지만 전혀 밀리지 않는 경우는 `Success=true / UTILITY_PUSH_BLOCKED`다. 이 경우 현재 구현은 턴과 쿨다운을 소비한다. 이동 목적지·대상 없음과 구분한다.

## 연출과 검증 절차

CastEffectRuid와 CastSoundRuid는 현재 데이터에 채워져 있다. 아이콘·피격 연출 등 선택 필드는 필요할 때 실제 리소스를 확인해 작성한다.
MotionProfileId는 현재 basic_slash / heavy_slash를 사용한다.

1. 편집기에서 `RootDesk/MyDesk/03_Data` 폴더 전체를 연다.
2. 수정 후 전체 검사, 오류가 없으면 현재 CSV를 다운로드한다.
3. 원본 CSV에 적용한 뒤 Maker Refresh를 실행한다.
4. 전투 콘텐츠 게이트의 `utilities checked=5 errors=0` 및 전체 검증 성공을 확인한다.
5. 변경한 직업의 발동·쿨다운·대상 없음 동작을 실제 플레이에서 확인한다.

유틸리티 효과·파라미터 계약을 확장할 때는 실행 코드, ContentValidatorLogic, tools/balance-schema.js, 이 문서를 함께 갱신한다.
