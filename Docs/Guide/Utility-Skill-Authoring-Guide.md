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
| royal_guard (새크로생티티) | warrior | 다음 플레이어 턴까지 가드 상태로 피해 무효화 |
| teleport | mage | 전방의 빈 칸 중 가장 먼 칸으로 이동 |
| fairy_turn (드래곤 펄스) | archer | 앞 1~2칸(`RANGE_OFFSETS` 1|2, Range 2)의 적을 최대 2칸 밀며 막히면 중단. 투사체·피격 연출은 시각 전용 |
| rapid_evasion (인투 다크니스) | thief | 전방에서 가장 먼 적의 1칸 뒤로 이동. 경계 밖·점유 시 실패 |
| somersault_kick | pirate | 바로 앞 적을 붙잡아 시전자 바로 뒤 칸으로 넘긴다. 대상 없음·HEAVY·뒤 칸이 막히거나 보드 밖이면 실패(쿨다운 미소모) |

해적 유틸은 파도(`tidal_wave`, 밀기 + 장전 취소)에서 써머솔트 킥으로 교체됐다. 파도가 쓰던 `PUSH_DISTANCE`
토큰(`CARRY_CASTER`, `CANCEL_QUEUE`)은 코드와 계약에 그대로 남아 있어 다른 유틸에서 다시 쓸 수 있다.

현재 5개 모두 `CooldownTurns=4`, `FreePlay=false`, `SkillTier=1`이다.
`SELF`의 Range도 공통 검증상 양수여야 한다. 이동 스캔은 보드 전체를 기준으로 한다.

## 허용 효과 계약

| EffectType | TargetSelector / TargetingType | Value | ParameterA | ParameterB |
|---|---|---|---|---|
| GUARD | SELF_UNIT / SELF | 0 | UNTIL_NEXT_PLAYER_TURN | ALL_DAMAGE |
| MOVE_SELF | SELF_UNIT / SELF | 0 | FARTHEST_EMPTY_FORWARD | 비움 |
| MOVE_SELF | SELF_UNIT / SELF | 양의 정수 | BEHIND_FARTHEST_ENEMY_FORWARD | REQUIRE_EMPTY |
| PUSH_DISTANCE | PRIMARY_TARGET 또는 ALL_SKILL_TARGETS / SELF 제외 | 양의 정수 | STOP_BEFORE_BLOCKED | 비움 또는 아래 토큰 조합 |
| PUSH_DISTANCE | PRIMARY_TARGET 또는 ALL_SKILL_TARGETS / SELF 제외 | 0 | MAX | 비움 또는 아래 토큰 조합 |
| THROW_BEHIND | PRIMARY_TARGET / SELF 제외 | 양의 정수(시전자 뒤 몇 번째 칸) | 비움 | 비움 |

PUSH_DISTANCE의 `ParameterB`는 `|`로 구분한 토큰 집합이며 중복은 거부한다.

| 토큰 | 효과 |
|---|---|
| CARRY_CASTER | 한 칸이라도 밀었으면 시전자를 전방의 연속된 빈 칸 끝으로 이동 |
| CANCEL_QUEUE | 사거리 안 대상이 장전(예약·예고·시전) 중인 스킬을 모두 취소 |

`CANCEL_QUEUE`는 밀기 성공 여부와 무관하게 사거리 안의 모든 대상에 적용한다(벽·다른 유닛·`HEAVY` 특성으로 한 칸도 밀리지 않아도 취소된다). 취소는 그 적의 `EnemyActionPlanComponent`
계획과 진행 중인 Interruptible Cast를 함께 비우고, Pattern Runner의 준비 단계도 해제하므로 적은
다음 턴에 같은 패턴 단계를 처음부터 다시 장전한다. 이미 실행 중(`EXECUTING`)인 계획은 취소하지 않는다.
밀기는 0칸이어도 취소가 하나라도 발생하면 결과는 `Success=true / UTILITY_QUEUE_CANCELLED`다.

`ConditionId`는 실행 코드에서 평가하지 않으므로 비워야 한다.
비용 차감·유틸리티 강화는 지원하지 않으므로 `CostType=""`, `CostValue=0`, `SkillTier=1`, `BaseSkillId=""`을 유지한다.
투사체(`ProjectileRuid`)는 `PUSH_DISTANCE` 유틸리티에서만 허용한다(`TargetingType=SELF` 불가, `ProjectileSpeed>0` 필요). 투사체는 시각 전용이며 밀기는 발사 즉시 해결되고, `HitEffectRuid`·`HitSoundRuid`는 투사체 도착 시점에 밀린 대상에게 재생된다. 다른 효과에 넣으면 `UTILITY_PROJECTILE_UNSUPPORTED`로 거부한다. FreePlay는 false만 허용한다.
실행되지 않는 값을 채워 기능이 적용된 것처럼 보이는 저작을 검증에서 거부한다.

이동 목적지 없음은 `Success=false / UTILITY_NO_EMPTY_DESTINATION`,
대상 없음은 `Success=false / UTILITY_NO_TARGET`,
대상이 있지만 전혀 밀리지 않는 경우는 `Success=true / UTILITY_PUSH_BLOCKED`다. 이 경우 현재 구현은 턴과 쿨다운을 소비한다. 이동 목적지·대상 없음과 구분한다.

## 연출과 검증 절차

CastEffectRuid와 CastSoundRuid는 현재 데이터에 채워져 있다. 리소스는 해당 스킬 리소스 팩(`effect`·`icon`·`ball`·`hit/0`·`audio/*`)에서 가져온다. 팩의 `repeat`·`audio/Loop`(지속 오라)는 아직 대응 열이 없어 사용하지 않는다.
MotionProfileId는 현재 basic_slash / heavy_slash를 사용한다.

1. 편집기에서 `RootDesk/MyDesk/03_Data` 폴더 전체를 연다.
2. 수정 후 전체 검사, 오류가 없으면 현재 CSV를 다운로드한다.
3. 원본 CSV에 적용한 뒤 Maker Refresh를 실행한다.
4. 전투 콘텐츠 게이트의 `utilities checked=5 errors=0` 및 전체 검증 성공을 확인한다.
5. 변경한 직업의 발동·쿨다운·대상 없음 동작을 실제 플레이에서 확인한다.

유틸리티 효과·파라미터 계약을 확장할 때는 실행 코드, ContentValidatorLogic, tools/balance-schema.js, 이 문서를 함께 갱신한다.
