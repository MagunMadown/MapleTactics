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
| `CastEffectRuid` | string | 32자리 hex | 시전자에게 붙는 이펙트. 비우면 생략 |
| `HitEffectRuid` | string | 32자리 hex | 피격 대상에게 붙는 이펙트. 비우면 생략 |
| `EffectScale` | number | `0.9` | 이펙트 배율. 0.05 미만은 0.05로 보정 |
| `WeaponType` | string | `ONE_HANDED_SWORD` | `WeaponDefinitions.WeaponType` 참조. 비우면 현재 장착 무기 유지 |
| `ProjectileRuid` | string | 32자리 hex | 날아가는 투사체 animationclip. 비우면 비행 단계 없음 |
| `ProjectileSpeed` | number | `14` | `ProjectileRuid`가 있으면 필수, 0 초과. 월드 유닛/초 |
| `ProjectileScale` | number | `0.9` | 투사체 배율. 비우면 `1` |
| `ProjectileLaunchDelay` | number | `0` | 발사를 늦출 초. `0`이면 시전과 동시 발사 |
| `ProjectileHeight` | number | `0` | 투사체가 셀보다 위로 날 높이(월드 유닛). `0`이면 바닥을 스친다 |
| `ProjectileCount` | integer | `1` | 한 번 시전에 날리는 투사체 수. 2 이상이면 `ProjectileInterval` 필수 |
| `ProjectileInterval` | number | `0` | 연발 간 간격(초). 0이면 겹쳐 나가 한 발처럼 보인다 |
| `IconRuid` | string | 32자리 hex | 스킬 아이콘 sprite. 비우면 기본 스프라이트로 대체 |
| `SkillTier` | integer | `1` | 스킬 정의의 정적 강화 단계. 1 이상. 아래 "스킬 강화 단계" 참조 |
| `BaseSkillId` | string | 빈 문자열 | 이 스킬이 강화되어 나온 원본 `SkillId`. 1단계는 비우고 2단계부터 필수 |
| `CasterMotionRuid` | string | animationclip RUID | Sprite 기반 적 공격 모션. Avatar 플레이어는 비움 |
| `CasterMotionPlayRate` | number | `1.6` | 적 공격 모션 배속. 모션 사용 시 0 초과 |
| `CasterMotionDuration` | number | `0.35` | 적 공격 모션 유지 시간. 비우면 `ActionDuration` |
| `EnemyQueueTurns` | integer | `1` | 적이 공격 Tile을 준비하는 데 소비할 적 턴 수 |
| `HudIconRuid` | string | sprite/animationclip RUID | 적 머리 위 Queue와 전투 HUD용 아이콘 |

## WeaponType과 무기 카탈로그

`WeaponType`은 "이 스킬을 어떤 무기로 사용하는가"를 나타내며 실제 RUID와 장착 슬롯은
`WeaponDefinitions` Dataset이 소유한다. 스킬 CSV에는 토큰만 적으므로 무기 아트를 교체할 때
스킬 행을 건드리지 않는다.

| 열 | 타입 | 예시 | 규칙 |
|---|---|---|---|
| `SchemaVersion` | integer | `1` | 현재 지원 버전은 1 |
| `WeaponType` | string | `BOW` | 고유 `UPPER_SNAKE_CASE` ID |
| `DisplayName` | string | `활` | 도감 표시용. 빈 문자열 금지 |
| `EquipSlot` | string | `TWO_HANDED` | `ONE_HANDED` 또는 `TWO_HANDED` |
| `WeaponRuid` | string | 32자리 hex | 주 손 `avataritem` RUID. 빈 문자열 금지 |
| `Enabled` | boolean | `true` | `false`면 참조하는 스킬이 검증에서 탈락 |
| `SubWeaponRuid` | string | 빈 문자열 | 보조무기 슬롯에 함께 드는 `avataritem` RUID. 이도류 전용 |

현재 등록된 14종: `ONE_HANDED_SWORD`, `TWO_HANDED_SWORD`, `SPEAR`, `POLEARM`, `BOW`,
`CROSSBOW`, `WAND`, `STAFF`, `DAGGER`, `CLAW`, `GUN`, `KNUCKLE`, `CANNON`, `DUAL_BLADE`.

`SubWeaponRuid`는 **`EquipSlot=ONE_HANDED`일 때만** 유효하다. 두손무기는 이미 보조무기
슬롯을 점유하므로 함께 지정하면 `SUB_WEAPON_ON_TWO_HANDED`로 거절된다. 자세한 내용은
[`MapleTactics-M1-Data-Dictionary.md`](../MapleTactics-M1-Data-Dictionary.md) §4.4를 본다.

런타임 경로는 다음과 같다.

```text
SkillDefinition.WeaponType
→ BattleSessionComponent.ApplySkillWeapon
→ SkillWeaponEquipLogic.ApplyWeaponForSkill
→ WeaponDefinitionRepositoryLogic.GetWeaponDefinition
→ CostumeManagerComponent.SetEquip
```

- 무기 장착은 **모션 재생 직전**에 일어나므로 스윙 모션이 해당 무기로 보인다.
- 순수 표현이며 전투를 막지 않는다. Costume이 없거나(적 유닛) 데이터가 잘못돼도
  `log_warning`만 남기고 스킬은 그대로 해결된다.
- 이미 같은 무기를 들고 있으면 재장착을 건너뛴다(`ALREADY_EQUIPPED`).
- `TWO_HANDED`는 1H·보조무기 슬롯을 함께 쓰므로 장착 전에 두 슬롯을 모두 비운다.
- 빈 `WeaponType`은 유효한 저작 선택이다. 적 스킬 3행은 모두 비어 있다.

## 투사체

`ProjectileRuid`를 채우면 시전자 셀에서 목표 셀까지 실제로 날아가는 엔티티가 생긴다.
판정은 갖지 않으며(피해는 Effect Step이 소유) 대신 **임팩트 시점을 비행시간만큼 뒤로 민다**.

```text
0                모션 시작 + 시전 이펙트 + 투사체 발사
+ 비행시간        Effect Step 실행 = 피해 · 밀치기 · 피격 이펙트
```

- **투사체는 시전 이펙트와 동시에 나가는 것이 기본이다.** 근접 스킬의 피해 시점인 모션
  `ImpactDelay`에 묶지 않는다. 늦춰야 하는 스킬만 `ProjectileLaunchDelay`에 양수를 적는다.
  현재 사례는 `poison_breath`(`0.25`)와 `arrow_stream`(`0.15`)다. 값은 이론이 아니라 플레이로 정한다 —
  0초로 먼저 확인하고, 이르게 보이면 조금씩 올린다.
- 비행시간은 저작값이 아니라 `거리 / (ProjectileSpeed × 배속)`이다. 가까운 적은 빨리,
  먼 적은 늦게 맞는다.
- 큐 슬롯 시간은 `max(ActionDuration, 발사지연 + 최대사거리 비행시간)`으로 자동 보정되므로
  `ActionDuration`을 직접 늘리지 않아도 피해보다 먼저 끝나지 않는다.
- 조준 셀은 Target Resolver가 돌려준 마지막 대상 칸이다. 적이 없으면 사거리 끝까지 날아가고
  사라지며 Effect Step은 그대로 `NO_TARGET`이 된다.
- `TargetingType=SELF`에는 쓸 수 없다.
- **투사체 이미지는 그 스킬 리소스 팩에 실제로 날아가는 물체(`ball` 등)가 있을 때만 쓴다**
  (`effect`=시전, `hit`=피격과 같은 팩). 팩에 없다고 다른 스킬 것을 빌려오면 서로 같은
  그림이 되어 구분이 사라지므로, 그런 스킬은 투사체 없이 즉발로 둔다. 확인 방법은
  `CastEffectRuid`로 팩을 역추적하는 것이다 —
  `node scripts/msw_resource_api.cjs packs <CastEffectRuid>` 결과의 `elements`에
  `rel_path: "ball"`이 있는지 본다.
- `ProjectileScale`은 클립 픽셀 크기를 셀 간격(1.12 유닛 = 112px)에 맞추는 값이다.

전체 목록과 엔티티 구성은
[`MapleTactics-M1-Data-Dictionary.md`](../MapleTactics-M1-Data-Dictionary.md) §4.5를 본다.

## 아이콘

`IconRuid`도 그 스킬 리소스 팩에서 가져온다. 투사체와 같은 절차로 `CastEffectRuid`를
역추적한 뒤 `rel_path: "icon"`인 엘리먼트를 쓴다. 플레이어 스킬 18행이 모두 32×32
`sprite`이고, 적 전용 3행은 비워둔다 — 적 스킬은 Codex에도 HUD에도 나오지 않는다.

- 이미 아이콘용 sprite이므로 `thumbnail://` 접두사를 붙이지 않는다.
- 아이콘은 Codex와 머리 위 예약 큐 HUD 두 곳에서 읽는다. HUD 쪽은 스킬 DataSet이
  `serveronly`라 정의를 직접 못 읽고, `BattleSessionComponent.SkillIconSnapshot`(`@Sync`)을
  거친다. **새 스킬을 추가하면서 아이콘이 HUD에 안 나오면 이 스냅샷부터 본다.**
- 비어 있으면 양쪽 다 기본 스프라이트로 떨어진다. 즉 아이콘을 안 채워도 스킬은 동작한다.

자세한 표시 경로는 [`MapleTactics-M1-Data-Dictionary.md`](../MapleTactics-M1-Data-Dictionary.md) §4.6에 있다.

## 스킬 강화 단계

`SkillTier`는 **스킬 정의 자체의 정적 등급**이다. 1단계는 직업이 기본으로 갖는 형태이고,
N단계 행은 `BaseSkillId`가 가리키는 N-1단계 스킬의 상위 버전이다. 2단계 스킬은 1단계 행을
고치는 게 아니라 **별도의 행**으로 추가한다.

```text
brandish            SkillTier=1  BaseSkillId=
brandish_ii         SkillTier=2  BaseSkillId=brandish
```

- 링크는 **자식이 부모를 가리키는** 한 방향뿐이다. 새 상위 단계를 추가할 때 원본 행을 건드리지
  않으므로 두 행이 어긋날 수 없고, 아직 없는 SkillId를 미리 참조하는 일도 없다.
- 부모는 같은 직업(`RequiredJobTag`)이어야 하고, 단계가 정확히 1 작아야 한다.
- 적 스킬은 강화 대상이 아니지만 `ConvertSkillRow`가 모든 스킬 테이블에 공용이라 스키마를
  맞추기 위해 같은 두 컬럼을 갖는다. 전부 `SkillTier=1`, `BaseSkillId` 비움이다.

현재 올라간 2단계 16행은 **전투 형태(타기팅·사거리·쿨다운·모션·무기·ActionDuration)를
원본에서 그대로 물려받고 피해만 +2** 한 구성이다. 이펙트와 아이콘은 그 스킬 자기 리소스
팩에서만 가져온다. 자세한 규칙과 예외는
[`MapleTactics-M1-Data-Dictionary.md`](../MapleTactics-M1-Data-Dictionary.md) §4.7에 있다.

> ⚠️ **강화 스테이지가 UI에 보내는 "레벨"과 다른 값이다.** 그쪽(`UpgradeSkillStageLogic`의
> `skillLevels`)은 `PlayerRunInventoryComponent.OwnedAmount` — 같은 스킬을 런 중에 중첩
> 획득한 누적 수치이고 런이 끝나면 사라진다. `SkillTier`는 데이터 고정값이라 런과 무관하다.

> ⚠️ **획득 경로는 아직 단계를 구분하지 않는다.** `GetJobSkillDefinitions`는 `RequiredJobTag`로만
> 거르므로 2단계 행을 넣는 순간 신규 스킬 선택·강화 스테이지·도감에 그대로 노출된다.
> 2단계 스킬을 추가할 때 게이팅을 함께 정해야 한다.

## 적 공격 모션과 Queue 아이콘

플레이어 스킬은 `WeaponType`·`Projectile*`·`IconRuid`와 Avatar `MotionProfileId`를 사용한다.
Sprite 기반 적 스킬은 같은 행의 `CasterMotion*`, `EnemyQueueTurns`, `HudIconRuid`를 추가로 사용한다.
두 필드군은 하나의 통합 스키마에 공존하며, 사용하지 않는 쪽은 빈 셀로 둔다.

`EnemyIntentHudComponent`의 `QueueOffsetX/Y`, `QueueSlotSpacing`, `SkillIconOffsetX/Y`,
`SkillIconSize`는 Maker Inspector에서 적 HUD 위치와 크기를 조절하는 공통 디자인 값이다.

현재 실제 Dataset Definition은 다음과 같다.

```csv
SchemaVersion,SkillId,...,WeaponType,ProjectileRuid,ProjectileSpeed,ProjectileScale,ProjectileLaunchDelay,IconRuid,SkillTier,BaseSkillId,CasterMotionRuid,CasterMotionPlayRate,CasterMotionDuration,EnemyQueueTurns,HudIconRuid,ProjectileCount,ProjectileInterval,ProjectileHeight
1,brandish,...,ONE_HANDED_SWORD,,0,1,0,429228115d56462ab0f65e7294a51609,1,,,,,,,1,0,0
```

행 전체는 코드 대신 실제 CSV를 본다. 스킬은 직업별 테이블로 나뉘어 있으며 어느 파일에
무엇이 들어 있는지는 [`MapleTactics-M1-Data-Dictionary.md`](../MapleTactics-M1-Data-Dictionary.md) §4.1이
소유한다. 공용 `SkillDefinitions`는 현재 헤더만 있고 행이 없다.

`FreePlay`는 효과 타입에서 자동 추론하지 않는다. 같은 `DAMAGE` 스킬이라도 Definition의
값에 따라 턴 소비 여부가 달라진다. CSV 셀은 문자열로 읽히므로 `true`/`1`/`yes`를
참으로 해석하며, 그 외 값과 빈 셀은 `false`로 취급한다. 현재 모든 행이 `FreePlay=false`다.

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

한 `EffectSetId`에 여러 Step을 붙이면 같은 임팩트 시점에 `StepIndex` 순서로 실행된다.

```csv
SchemaVersion,EffectSetId,StepIndex,EffectType,TargetSelector,Value,ParameterA,ParameterB,ConditionId
1,enemy_basic_attack_effects,1,DAMAGE,FRONT_TARGET,3,SOURCE_BASIC_ATTACK,,
1,magnum_shot_effects,1,DAMAGE,PRIMARY_TARGET,4,,,
1,magnum_shot_effects,2,PUSH,PRIMARY_TARGET,1,,,
```

현재 지원 `EffectType`은 `DAMAGE`, `PUSH`, `HEAL` 세 가지다. 전체 행은
`RootDesk/MyDesk/03_Data/SkillEffectSteps.csv`를 직접 본다.

`SOURCE_BASIC_ATTACK`은 고정 `Value` 대신 시전자
`BattleUnitComponent.BasicAttackDamage`를 사용하는 공용 규칙이다.

## 새 단일 Effect 스킬 추가 순서

`SkillDefinitions`와 `SkillEffectSteps` Dataset 전환이 완료되어 아래 절차로 바로 추가할 수 있다.

1. 해당 직업의 `{Job}SkillDefinitions.csv`에 고유 `SkillId` 행을 추가한다.
2. 고유 `EffectSetId`를 정하고 `SkillEffectSteps`에 Step 1을 추가한다.
3. 현재 지원하는 Targeting과 EffectType인지 확인한다.
4. `WeaponType`을 `WeaponDefinitions`의 14종 중에서 고른다. 무기를 바꾸지 않으면 비운다.
5. `SkillTier`를 채운다. 새 기본 스킬이면 `1`에 `BaseSkillId`를 비우고, 기존 스킬의 상위
   단계면 부모의 단계 + 1과 부모 `SkillId`를 적는다.
6. 큐 또는 서버 테스트에서 `TryQueueTile(SkillId)`를 호출한다.
7. `[ContentValidation] skill valid ... tier=`와 `[SkillExecution] started` 로그를 확인한다.
8. 무기를 지정했다면 `[SkillWeapon] equipped ...` 로그도 함께 확인한다.
9. 타격 Cell, 피해 또는 밀치기, 모션, 큐 완료 시점을 확인한다.

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
| `CONTENT_VALIDATION_FAILED` | `INVALID_SKILL_WEAPON_REFERENCE` | WeaponType이 비어있지 않은데 `WeaponDefinitions`에서 유효하지 않음 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_PROJECTILE_SPEED` | ProjectileRuid가 있는데 ProjectileSpeed가 없거나 0 이하 |
| `CONTENT_VALIDATION_FAILED` | `PROJECTILE_ON_SELF_TARGETING` | TargetingType=SELF인 스킬에 ProjectileRuid를 지정 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_PROJECTILE_LAUNCH_DELAY` | ProjectileRuid가 있는데 ProjectileLaunchDelay가 음수 |
| `CONTENT_VALIDATION_FAILED` | `PROJECTILE_HEIGHT_WITHOUT_PROJECTILE` | ProjectileRuid가 비어 있는데 ProjectileHeight가 0 초과 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_PROJECTILE_COUNT` | ProjectileRuid가 있는데 ProjectileCount가 1 미만 |
| `CONTENT_VALIDATION_FAILED` | `PROJECTILE_VOLLEY_WITHOUT_INTERVAL` | ProjectileCount가 2 이상인데 ProjectileInterval이 0 이하 |
| `CONTENT_VALIDATION_FAILED` | `PROJECTILE_VOLLEY_WITHOUT_PROJECTILE` | ProjectileRuid가 비어 있는데 연발 컬럼이 채워짐 |
| `CONTENT_VALIDATION_FAILED` | `SUB_WEAPON_ON_TWO_HANDED` | EquipSlot=TWO_HANDED인 무기에 SubWeaponRuid를 지정 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_SKILL_TIER` | SkillTier가 없거나 1 미만 |
| `CONTENT_VALIDATION_FAILED` | `TIER_1_BASE_SKILL_PRESENT` | SkillTier=1인데 BaseSkillId가 채워져 있음 |
| `CONTENT_VALIDATION_FAILED` | `BASE_SKILL_ID_MISSING` | SkillTier가 2 이상인데 BaseSkillId가 비어 있음 |
| `CONTENT_VALIDATION_FAILED` | `BASE_SKILL_SELF_REFERENCE` | BaseSkillId가 자기 자신을 가리킴 |
| `CONTENT_VALIDATION_FAILED` | `BASE_SKILL_NOT_FOUND` | BaseSkillId가 어느 스킬 테이블에도 없음 |
| `CONTENT_VALIDATION_FAILED` | `BASE_SKILL_TIER_MISMATCH` | BaseSkillId가 가리키는 스킬의 SkillTier가 자신보다 정확히 1 작지 않음 |
| `CONTENT_VALIDATION_FAILED` | `BASE_SKILL_JOB_MISMATCH` | BaseSkillId가 가리키는 스킬의 RequiredJobTag가 자신과 다름 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_ENEMY_QUEUE_TURNS` | EnemyQueueTurns가 없거나 음수 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_CASTER_MOTION_PLAY_RATE` | 적 모션 RUID가 있는데 배속이 0 이하 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_CASTER_MOTION_DURATION` | 적 모션 RUID가 있는데 유지 시간이 0 이하 |
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

플레이어 스킬 34행(직업별 5개 테이블 — 1단계 18행 + 2단계 16행), 적 전용 5행,
Effect Step 44행, 무기 12행이 실제 Dataset으로 올라가 있다. 그중 투사체를 쓰는 플레이어 스킬은
9행이다. `thunder_bolt`와 `heal`만 아직 상위 단계가 없다.
`AllowPrototypeCompatibilityFallback=false`이며 production
Skill 하드코딩을 다시 추가하지 않는다. 새 Dataset을 만들 때는 기존 `.userdataset` ID를
복제하지 않는다.

신규 Skill 제작 Gate B는 열려 있다. 기존 Dataset 페어의 CSV에 Definition과 Effect
Step을 함께 추가하고 Maker Refresh 후 `source=DATASET`, Validator, 실제 Effect와 Cooldown을
검증한다. 새 Dataset을 만들 때는 기존 `.userdataset` ID를 복제하지 않는다.
