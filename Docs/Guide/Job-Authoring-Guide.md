# 직업 콘텐츠 작성 가이드

## 책임 구분

- `SkillDefinitions`: 큐에 넣어 실행하는 일반 공격 타일.
- `JobStartingSkillEntries`: 직업이 런 시작 시 받는 일반 스킬 구성.
- `JobMechanic`: 이동·교환·밀치기·관통처럼 직업 자체가 바꾸는 전투 규칙.
- `AugmentDefinitions`: 상점·보상 런 패시브와 직업 시작 패시브가 공유하는 정의.
- `NodeDefinitions`: 전투·상점·이벤트 등 진행 경로. 직업/스킬 노드가 아니다.

## 새 직업 추가 순서

1. `JobDefinitions.csv`에 JobId와 기본 HP·큐 크기를 추가한다.
2. 고유한 `StartingSkillSetId`를 정하고 `JobStartingSkillEntries.csv`에 SlotIndex 1부터 연속으로 작성한다.
3. 시작 SkillId가 모두 `SkillDefinitions`에 존재하는지 확인한다.
4. 고유 기능이 없으면 `JobMechanicId=NONE`을 사용한다.
5. 고유 기능이 있으면 별도 Handler를 만들고 `JobMechanicRouterLogic`에 등록한다.
6. `_ContentValidatorLogic:ValidateJobById(jobId)`가 성공하는지 확인한다.

## JobMechanic 구현 계약

```text
CanActivate(mechanicId, context)
Execute(mechanicId, context)
GetPreview(mechanicId, context)
GetUiState(mechanicId, context)
```

실제 Handler도 같은 의미의 결과 필드를 유지한다.

- `Success`, `Reason`, `MechanicId`
- `CanActivate`
- `ConsumedTurn`
- `SourceCell`, `TargetCell`, `PreviewType`
- UI용 `CooldownRemaining`

수치·활성 조건은 Dataset에 두고, 위치 교환이나 투척처럼 알고리즘이 다른 동작은 Handler가
소유한다. Handler는 BattleSession의 공개 메서드를 호출하며 Board Registry나 Turn 상태를
직접 수정하지 않는다.

현재 `FORWARD_PUSH`는 이 규칙의 기준 구현이다.

1. 플레이어가 바라보는 방향으로 `MOVE`를 시도한다.
2. 바로 앞 칸의 적과 그 다음 칸을 `CanActivate`에서 읽기 전용으로 검사한다.
3. 실행 시 Handler는 `BattleSession.RelocateUnitForMechanic`만 호출해 적을 한 칸 민다.
4. 기존 `TryMove`가 비워진 칸으로 플레이어를 이동한다.
5. 이 동작은 별도 스킬을 큐에 넣은 것이 아니라 원래 `MOVE` 명령을 확장한 것이므로, 기존
   MOVE 턴 소비 규칙을 그대로 따른다.

런 시작 시 `RunManagerLogic.ApplyJobSelection`이 직업 데이터를 검증하고
`PlayerRunStateComponent`에 HP, 기본 큐 용량, 시작 SkillId, MechanicId, PassiveSetId를 스냅샷으로 저장한다.
전투·상점·결과 화면은 원본 Dataset을 다시 해석하지 않고 이 런 스냅샷 또는 공개 DTO를 사용한다.

실제 보유 스킬은 `PlayerRunInventoryComponent.RunSkillSnapshot`의 `SkillId~Count` 형식으로
별도 관리한다. `BattleSession.TryQueueTile`은 `_RunManagerLogic:CanUseRunSkill(...)`만 호출하며
Inventory 문자열을 직접 해석하지 않는다. 현재 `Count`는 보유 수량을 보존하지만 큐 등록은
`Count > 0`인 SkillId 허용 여부만 검사한다. 동일 스킬의 중복 큐 제한은 스킬 쿨타임과 별도
큐 규칙이 담당한다.

상점·이벤트·보상에서 스킬을 추가할 때는 Dataset이나 Inventory를 직접 수정하지 않고
`_RunManagerLogic:GrantRunSkill(player, skillId, amount, rewardKey)`를 호출한다. 이 경계는
SkillDefinitions 참조 검증과 중복 RewardKey 방지를 함께 수행한다.

## 직업 시작 패시브

`JobPassiveSetId`에는 별도 직업 전용 스크립트 이름이 아니라 `AugmentDefinitions.AugmentId`를
기록한다. 같은 AugmentId의 `AugmentEffects` 여러 행이 한 세트를 이룬다. 런 시작 시
`RunManagerLogic.ApplyJobSelection`이 검증 후 `PlayerRunAugmentComponent`에 UNIQUE 증강으로
지급하므로, 전투·상점·UI가 직업별 분기를 만들 필요가 없다.

새 패시브는 [`Augment-Authoring-Guide.md`](./Augment-Authoring-Guide.md)의 순서로 추가한다.
현재 구현된 원시 조합 밖의 Trigger·Condition·Effect가 필요하면 데이터만 먼저 추가하지 말고
독립 Handler와 Router 등록, Validator, Maker 회귀 검증을 한 작업으로 묶는다.

## 금지 사항

- 직업 고유 기능을 억지로 `SkillDefinitions`에 넣지 않는다.
- 전역 SkillDefinition 원본을 직업별로 수정하지 않는다.
- UI가 JobMechanic 실행 가능 여부를 자체 계산하지 않는다.
- `NodeDefinitions`에 직업 스킬 트리 데이터를 넣지 않는다.

현재 프로토타입은 `prototype_warrior`, 시작 스킬 `basic_slash`와 `push`,
`JobMechanicId=FORWARD_PUSH`를 제공한다. 직업 스냅샷·스킬 소유권·큐 등록·실제 이동
메커니즘과 `prototype_warrior_recovery` 시작 패시브가 연결됐다. 런 상점은
`ShopDefinitions`/`ShopEntries` 기반으로 `SKILL`·`CONSUMABLE` 구매와 지급까지 연결됐으며,
최종 상점 화면·추가 직업 데이터·증강 선택 UI는 후속 범위다.
