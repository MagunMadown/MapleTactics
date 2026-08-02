# 증강·직업 패시브 제작 가이드

## 현재 지원 범위

직업 시작 패시브와 향후 상점·보상 증강은 같은 `AugmentDefinitions`와 `AugmentEffects` 규격을
사용한다. 현재 런타임에서 지원하는 최소 조합은 다음과 같다.

| 구분 | 구현 값 |
|---|---|
| TriggerType | `TURN_START` |
| ConditionType | `ALWAYS`, `HP_RATIO_LE` |
| EffectType / TargetType | `HEAL` / `SELF` |
| StackPolicy | `UNIQUE`, `MaxStacks=1` |

## 새 증강 추가 순서

1. `AugmentDefinitions.csv`에 전역 유일한 `AugmentId`와 `SchemaVersion=1`을 추가한다.
2. `AugmentEffects.csv`에 같은 ID의 효과를 `Seq=1`부터 빈 번호 없이 추가한다.
3. 낮은 `Priority`가 먼저 실행된다는 기준으로 우선순위를 정한다.
4. `_ContentValidatorLogic:ValidateAugmentById(augmentId)`가 성공하는지 확인한다.
5. 런 지급은 `_RunManagerLogic:GrantRunAugment(player, augmentId, sourceType, rewardKey)`만 사용한다.
6. Maker에서 같은 RewardKey의 중복 지급, Trigger 실행 결과, Run 재시작 초기화를 확인한다.

직업 시작 패시브라면 마지막으로 `JobDefinitions.JobPassiveSetId`에 해당 `AugmentId`를 기록한다.
한 ID에 여러 Effect 행을 연결할 수 있으므로 별도 PassiveSet Dataset은 만들지 않는다.

## 확장 규칙

새 원시 Type은 특정 AugmentId 분기로 구현하지 않는다. Trigger는
`AugmentTriggerRouterLogic`, Condition은 `AugmentConditionRouterLogic`, Effect는 독립 Handler와
`AugmentEffectRouterLogic`에 등록하고 Validator 허용 여부와 회귀 테스트를 함께 추가한다.
Runtime 실행 순서는 `Priority → AcquiredOrder → Seq → AugmentId`이며 모든 비교는 오름차순이다.

효과 Handler는 HP나 런 상태를 직접 대입하지 않고 상태 소유자의 `Apply...` API를 호출한다.
파생 이벤트를 다시 발행할 때는 현재 `SourceTag`를 전달하고 `Depth`를 증가시킨다. 동일 효과의
SourceTag 재진입과 깊이 4 이상은 Runtime이 차단한다.

## UI 계약

UI는 `BattleSessionComponent.GetBattleUiState().RunAugments`만 읽는다. 보유 형식은
`AugmentId~Stacks~AcquiredOrder~SourceType`을 `|`로 구분한 문자열이다. UI에서 효과 발동 여부를
재계산하거나 `PlayerRunAugmentComponent` 값을 직접 변경하지 않는다. 현재 HUD는 기능 검증용이며
최종 연출은 DTO와 별도의 향후 이벤트 계약 위에서 교체한다.
