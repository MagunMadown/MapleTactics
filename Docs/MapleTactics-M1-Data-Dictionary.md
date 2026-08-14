# MapleTactics M1 데이터 사전

상태: M1 초안  
저장 형식: 각 표는 `<Name>.userdataset` + `<Name>.csv` 한 쌍  
런타임: `_DataService:GetTable("<runtime name>")`

## 1. 공통 규칙

- CSV 셀은 모두 문자열이다. 로더가 숫자와 불리언을 명시적으로 변환한다.
- 빈 셀은 `nil` 또는 `""` 양쪽을 누락으로 처리한다.
- ID는 ASCII `lower_snake_case`를 기본으로 한다.
- ID 열은 대소문자를 구분하며 공백을 허용하지 않는다.
- 순서가 필요한 표는 `Seq`, `StepIndex`, `SpawnOrder`, `WaveIndex` 중 하나를 반드시 가진다.
- 참조 ID는 로드 직후 전체 테이블을 대상으로 무결성 검사한다.
- `pairs` 순서를 사용하지 않는다. 배열로 수집한 뒤 명시적 키로 정렬한다.
- 불리언은 `true`/`false` 소문자만 허용한다.
- 소수는 `.`을 사용하고 퍼센트는 `0.0~1.0` 비율로 기록한다.
- 한 셀에 JSON 배열이나 실행 코드를 저장하지 않는다.

문서의 지원 상태는 다음 의미로 사용한다.

- `IMPLEMENTED`: 실제 Dataset/Repository/Validator/Runtime 경로가 연결되어 콘텐츠 제작자가 사용할 수 있다.
- `PLANNED`: 목표 스키마 또는 예약 값이다. Dataset이나 Router/Validator가 아직 없을 수 있으므로 실전 데이터에 사용하지 않는다.
- 별도 상태가 없는 기존 표는 실제 Dataset 존재 여부와 해당 제작 가이드를 함께 확인한다. 새 표에는 상태를 명시한다.

## 2. JobDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| JobId | string | O | 직업 고유 ID |
| DisplayName | string | O | 제작자용 표시 이름. UI 현지화 키 분리는 이후 가능 |
| JobTags | string | O | `melee\|control` 형식의 스킬·증강 필터 태그 |
| BaseMaxHp | integer | O | 시작 최대 HP, 1 이상 |
| BaseQueueCapacity | integer | O | 기본 큐 크기, 1~6 |
| StartingSkillSetId | string | O | JobStartingSkillEntries의 세트 ID |
| JobMechanicId | string | O | JobMechanicRouter에 등록된 직업 고유 규칙 ID. 큐 스킬이 아님 |
| JobPassiveSetId | string | - | 시작 패시브/증강 세트 ID. 비어 있으면 없음 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

기본 키: `JobId` 유일. `JobMechanicId`는 반드시 Router에 등록되어야 한다.
직업은 `SkillDefinitions`를 상속하거나 수정하지 않는다. 시작 공격은 `StartingSkillSetId`,
이동·교환·밀치기·관통 같은 캐릭터 규칙은 `JobMechanicId`로 독립 구성한다.

현재 실제 `JobDefinitions.userdataset/.csv`에는 5개 직업이 등록되어 있다.

| JobId | DisplayName | JobTags | JobMechanicId | StartingSkillSetId | JobPassiveSetId |
|---|---|---|---|---|---|
| warrior | 전사 | melee\|control | FORWARD_PUSH | warrior_start | warrior_recovery |
| mage | 마법사 | ranged\|magic | NONE | mage_start | mage_focus |
| archer | 궁수 | ranged\|piercing | NONE | archer_start | archer_focus |
| thief | 도적 | melee\|mobility | NONE | thief_start | thief_focus |
| pirate | 해적 | melee\|control | NONE | pirate_start | pirate_focus |

`warrior`만 기준 구현인 `FORWARD_PUSH` JobMechanic을 가지며, 나머지 4개 직업은 아직 고유
메커니즘 없이 `JobMechanicId=NONE`으로 스탯·시작 스킬 구성만 다른 상태다. 각 직업 고유
메커니즘은 후속 범위이며, 추가할 때는 `Job-Authoring-Guide.md`의 절차대로 독립 Handler를
만들고 `JobMechanicRouterLogic`에 등록한다.

## 3. JobStartingSkillEntries

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| StartingSkillSetId | string | O | 시작 스킬 세트 ID |
| SlotIndex | integer | O | 지급/표시 순서, 1부터 연속 |
| SkillId | string | O | SkillDefinitions 참조 |
| Count | integer | O | 지급 수량, 1 이상 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

기본 키: `(StartingSkillSetId, SlotIndex)`는 유일해야 한다. 같은 세트에서 같은 SkillId를
중복 행으로 작성하지 않고 수량은 `Count`로 표현한다.

런 시작 시 이 수량은 `PlayerRunInventoryComponent.RunSkillSnapshot`의 `SkillId~Count`
형식으로 변환된다. 현재 큐 등록은 보유 수량이 1 이상인지 검사하며, 한 큐 안의 동일 SkillId
허용 수는 별도 큐/쿨타임 규칙을 따른다.

현재 모든 시작 스킬은 §4.1의 직업별 SkillDefinitions 테이블에서 온다. 공용
`SkillDefinitions`를 참조하는 시작 슬롯은 더 이상 없다. 직업별 슬롯 구성은 다음과 같다.

| StartingSkillSetId | 슬롯 수 | SkillId |
|---|:---:|---|
| warrior_start | 3 | `brandish`, `divine_swing`, `spear_pulling` |
| mage_start | 6 | `cold_beam`, `thunder_bolt`, `flame_orb`, `poison_breath`, `holy_arrow`, `heal` |
| archer_start | 3 | `piercing`, `wind_shot`, `cardinal_discharge` |
| thief_start | 3 | `shuriken_burst`, `savage_blow`, `fatal_blow` |
| pirate_start | 3 | `magnum_shot`, `slug_shot`, `shock_wave` |

전투 HUD의 스킬 슬롯은 3칸이므로, 보유 스킬이 슬롯 수보다 많은 직업(현재 마법사)은
전투 시작 시 보유 스킬 중 3개가 무작위로 배정된다. 배정은 서버가 수행하며 자세한 규칙은
§4.2를 따른다.

## 4. SkillDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| SkillId | string | O | 큐에 넣어 실행하는 일반 스킬 ID |
| DisplayName | string | O | 표시 이름 |
| SkillTags | string | - | `attack\|starter` 형식 태그 |
| TargetingType | enum | O | `SELF`, `FRONT_CELL`, `FIRST_ENEMY_FORWARD`, `RANGE_OFFSETS` |
| Range | integer | O | Cell 기준 최대 사거리, 1 이상. `SELF`도 Validator 규칙상 1 이상을 넣는다 |
| TargetOffsets | string | 조건부 | `RANGE_OFFSETS`일 때 필수. Facing 기준 정수 오프셋을 `|`로 구분 |
| CooldownTurns | integer | O | 실행 후 쿨다운 턴, 0 이상 |
| CostType | string | - | 비용 종류 |
| CostValue | number | O | 비용 수치, 0 이상 |
| MotionProfileId | string | O | 공격 모션 프로필 |
| EffectSetId | string | O | SkillEffectSteps 참조 |
| RequiredJobTag | string | - | 비어 있으면 공용 스킬 |
| ActionDuration | number | O | 실행 연출 시간, 0 초과. 1배속 기준 원본 값이며 §4.3의 배속으로 나눠 사용된다 |
| FreePlay | boolean | O | 큐 등록 시 턴 미소비 여부 |
| CastEffectRuid | string | - | 시전자에게 재생할 animationclip RUID. 비우면 시전 이펙트 없음 |
| HitEffectRuid | string | - | 피격 대상에게 재생할 animationclip RUID. 비우면 피격 이펙트 없음 |
| EffectScale | number | - | 두 이펙트에 공통 적용할 배율. 비우면 `1` |
| WeaponType | string | - | §4.4 `WeaponDefinitions.WeaponType` 참조. 비우면 현재 장착 무기를 유지 |

내부 `SkillDefinitions`는 쇼군 쇼다운식 공격 타일에 해당한다. 직업 고유 능력과
런 패시브(Augment)는 이 표에 넣지 않는다.

`TargetingType=SELF`는 보드 Cell을 하나도 잡지 않는다. 대상은 §5의 `SELF_UNIT`
TargetSelector로 정해지므로, 사거리 안에 적이 없어도 시전할 수 있는 지원 스킬에 사용한다.

### 4.0 이펙트 RUID 규칙

`CastEffectRuid`/`HitEffectRuid`는 `sprite`가 아니라 **`animationclip` RUID**여야 한다.
값은 각 스킬의 공식 리소스 팩에서 가져오며, 팩 안의 `effect` 엘리먼트가 시전,
`hit/0`이 피격에 해당한다. 팩에 `hit` 클립이 없으면(예: 스피어 풀링) 같은 계열 스킬의
피격 클립을 재사용한다.

메이플 스킬 클립은 피벗이 이미 캐릭터 기준점에 맞춰 저작되어 있으므로 별도 오프셋을
주지 않는다. `BattleUnitPresentationComponent.SkillEffectOffsetY` 기본값이 `0`인 이유이며,
값을 올리면 이펙트가 유닛 머리 위로 뜬다.

`EffectScale`은 클립 원본 크기가 셀 간격(약 1.12 월드 유닛) 대비 과도할 때만 낮춘다.
현재 대부분 `0.9`이고, 폭이 넓은 피어싱만 `0.7`이다.

### 4.1 스킬 테이블 분리

스킬 행은 **같은 열 스키마를 가진 7개 테이블**에 나뉘어 있다. 각각
`RootDesk/MyDesk/03_Data/`에 `.userdataset`+`.csv` 쌍으로 존재한다.

| 구분 | 테이블 이름 (runtime name) | 수록 SkillId |
|---|---|---|
| 공용 | `SkillDefinitions` | (없음 — 헤더만) |
| 무기 카탈로그 | `WeaponDefinitions` | (SkillId 아님 — §4.4 참조) |
| 전사 | `WarriorSkillDefinitions` | `brandish`, `divine_swing`, `spear_pulling` |
| 마법사 | `MageSkillDefinitions` | `cold_beam`, `thunder_bolt`, `flame_orb`, `poison_breath`, `holy_arrow`, `heal` |
| 궁수 | `ArcherSkillDefinitions` | `piercing`, `wind_shot`, `cardinal_discharge` |
| 도적 | `ThiefSkillDefinitions` | `shuriken_burst`, `savage_blow`, `fatal_blow` |
| 해적 | `PirateSkillDefinitions` | `magnum_shot`, `shock_wave`, `slug_shot` |
| 적 전용 | `EnemySkillDefinitions` | `enemy_basic_attack` |

공용 `SkillDefinitions`는 현재 **행이 하나도 없다**. 이전의 범용 프로토타입 타일
(`basic_slash`, `quick_slash`, `heavy_slash`, `push`, `slash_push_combo`, `prototype_*`,
`csv_*`, 직업 맛보기 스킬 7종)은 모두 제거되었고, 플레이어가 쓸 수 있는 스킬은 전부
직업별 테이블에서 온다. 표 자체는 여러 직업이 공유할 스킬이 생길 때를 위해 남겨 둔다.

`EnemySkillDefinitions`는 몬스터만 쓰는 행을 담는다. 예전에는 적이 플레이어 스킬
`basic_slash`를 그대로 재사용했기 때문에 플레이어 스킬을 수정하면 몬스터 공격이 조용히
깨졌다. 이 표를 분리해 그 결합을 끊었다.

#### 조회 경로

| 메서드 | 대상 테이블 | 용도 |
|---|---|---|
| `GetSkillDataSetNames()` | 7개 전부 | 스킬 정의 조회·무결성 검사 |
| `GetPlayerGrantableSkillIds()` | 적 전용 제외 6개 | 플레이어에게 지급 가능한 SkillId 목록 |

`SkillDefinitionRepositoryLogic.JobSkillDataSetNames`(쉼표 구분 문자열)가 직업 5개 테이블
이름을, `EnemySkillDataSetName`이 적 전용 테이블 이름을 보관한다.
`GetSkillDefinition(skillId)`는 `GetSkillDataSetNames()` 전체를 순회하므로
`ValidateSkillById`·상점 구매·`GrantRunSkill` 등 호출부는 스킬이 어느 테이블에 있는지 알
필요가 없다. 중복 `SkillId` 검사도 7개 테이블 전체를 대상으로 한다.

플레이어 지급 경로는 `GetPlayerGrantableSkillIds()`를 써서 적 전용 행을 제외한다. 이
구분이 없으면 보상·상점·HUD 슬롯에 `enemy_basic_attack`이 노출될 수 있다.

`SkillEffectSteps`는 나누지 않고 공용 표로 유지한다. 적 전용 스킬도 같은
`SkillEffectSteps`에서 `EffectSetId`로 Effect Step을 참조한다.

`ContentIntegrityValidatorLogic.ValidateAllContent()`의 전체 무결성 감사도 같은 7개 테이블을
전부 스캔한다 — 누락되면 해당 테이블 스킬이 참조하는 `EffectSetId`가
`ORPHAN_EFFECT_SET`으로 오탐지된다.

프로토타입 호환 fallback은 제거되었다. `SkillDefinitionRepositoryLogic`에 하드코딩되어 있던
`AllowPrototypeCompatibilityFallback` 속성과 관련 메서드가 없으므로, 이제 Dataset에 없는
SkillId는 예외 없이 `UNKNOWN_SKILL`이다.

새 직업 전용 스킬을 추가할 때는:

1. 그 직업의 `{Job}SkillDefinitions.csv`에 행을 추가한다 (공용 `SkillDefinitions`에는 넣지 않는다).
2. `SkillEffectSteps.csv`에 `EffectSetId` 행을 추가한다.
3. `JobStartingSkillEntries.csv`에 필요하면 슬롯을 추가한다.
4. `CastEffectRuid`/`HitEffectRuid`를 §4.0 규칙대로 채운다.
5. `WeaponType`을 §4.4 목록에서 고른다. 무기를 바꾸지 않는 스킬이면 비운다.
6. `_ContentValidatorLogic:ValidateAllContent()`가 통과하는지 확인한다.

### 4.2 HUD 스킬 슬롯 배정

전투 HUD는 스킬 버튼 3칸을 가진다. 어떤 스킬이 어느 칸에 오는지는 CSV가 아니라 런타임이
정한다.

- 배정 주체는 **서버**다. `BattleSessionComponent.RefreshSkillSlots()`가 보유 스킬 스냅샷을
  Fisher-Yates로 섞어 앞에서 `SkillSlotCount`(현재 3)개를 고른다.
- 결과는 `SkillSlotIds`/`SkillSlotNames`로 동기화된다. 표시 이름을 함께 내려보내는 이유는
  스킬 Dataset이 `serveronly=true`라 클라이언트가 `DisplayName`을 직접 읽을 수 없기 때문이다.
- 클라이언트가 슬롯을 정하지 않으므로 보유하지 않은 스킬을 큐에 넣을 수 없다.
- 재추첨 시점은 보유 스킬 집합이 바뀔 때다. 전투 도중 스킬을 새로 얻어도 그 전투의 슬롯은
  유지되고 다음 배정부터 후보에 들어간다.

보유 스냅샷은 `SkillId~Count` 형식(§3)이므로, 슬롯 후보를 뽑을 때 `~` 앞부분만 SkillId로
사용한다.

### 4.3 스킬 배속

`BattleSessionComponent.SkillSpeedMultiplier`가 스킬 연출·판정 속도를 한 번에 조절한다.
현재 값은 `1.25`이며 최소 `0.1`로 하한이 걸려 있다.

CSV와 모션 프로필의 값은 **1배속 기준 원본 그대로** 두고, 읽는 시점에 배속을 적용한다.
따라서 배속을 바꾸거나 1로 되돌려도 원본 데이터는 손상되지 않는다.

| 대상 | 적용 |
|---|---|
| 모션 재생속도 (`PlayRate`) | × 배속 |
| 모션 지속시간 (`Duration`) | ÷ 배속 |
| 임팩트 시점 (`ImpactDelay`) | ÷ 배속 |
| 이펙트 클립 재생속도 | × 배속 |
| 큐 액션 지속시간 (`ActionDuration`) | ÷ 배속 |

다섯 항목을 함께 스케일해야 한다. 특히 마지막 항목을 빼면 애니메이션이 먼저 끝나는데 큐
슬롯이 원래 시간만큼 턴을 붙잡아 전투가 늘어진다.

`ImpactDelay`는 스킬별 값이 아니라 `MotionProfileId`가 결정한다. 현재 프로필은
`basic_slash`(1배속 0.18초), `heavy_slash`(0.38초), `push`(0.18초) 세 가지이며 같은 프로필을
쓰는 스킬은 임팩트 시점을 공유한다. 스킬마다 다른 임팩트가 필요해지면 `SkillDefinitions`에
`ImpactDelay` 열을 추가하는 것이 다음 단계다.

### 4.4 WeaponDefinitions (IMPLEMENTED)

런타임 이름 `WeaponDefinitions`. `SkillDefinitions.WeaponType`이 참조하는 무기 카탈로그다.
스킬 행에는 토큰만 두고 실제 아바타 RUID와 장착 슬롯은 이 표가 소유하므로, 무기 아트를
교체할 때 스킬 행을 건드리지 않는다.

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| WeaponType | string | O | 무기 종류 ID. `UPPER_SNAKE_CASE` |
| DisplayName | string | O | 도감 표시 이름 |
| EquipSlot | enum | O | `ONE_HANDED` 또는 `TWO_HANDED` |
| WeaponRuid | string | O | `avataritem` RUID |
| Enabled | boolean | O | `false`면 참조하는 스킬이 검증에서 탈락 |

기본 키: `WeaponType` 유일. 현재 12행이 등록되어 있다.

| EquipSlot | WeaponType |
|---|---|
| ONE_HANDED | `ONE_HANDED_SWORD`, `WAND`, `DAGGER`, `CLAW`, `GUN`, `KNUCKLE` |
| TWO_HANDED | `TWO_HANDED_SWORD`, `SPEAR`, `POLEARM`, `BOW`, `CROSSBOW`, `STAFF` |

`POLEARM`은 아직 참조하는 스킬이 없는 예약 행이다.

#### 실행 경로

```text
SkillDefinition.WeaponType
→ BattleSessionComponent.ApplySkillWeapon
→ SkillWeaponEquipLogic.ApplyWeaponForSkill
→ WeaponDefinitionRepositoryLogic.GetWeaponDefinition
→ CostumeManagerComponent.SetEquip
```

- 장착은 **모션 재생 직전**에 일어나므로 스윙 모션이 해당 무기로 보인다.
- 순수 표현이며 전투를 막지 않는다. 실패는 전부 `log_warning`으로 끝나고 스킬은 그대로
  해결된다. 반환 Reason은 `OK`, `ALREADY_EQUIPPED`, `NO_WEAPON_REQUIRED`,
  `UNKNOWN_WEAPON_TYPE`, `WEAPON_DISABLED`, `WEAPON_RUID_MISSING`,
  `UNSUPPORTED_WEAPON_EQUIP_SLOT`, `COSTUME_MANAGER_MISSING`, `UNIT_UNAVAILABLE`이다.
- 같은 무기를 이미 들고 있으면 재장착을 건너뛴다(`ALREADY_EQUIPPED`). 불필요한 코스튬
  재구성과 그에 따른 깜빡임을 막기 위한 것이다.
- `TWO_HANDED`는 1H·보조무기 슬롯을 함께 쓰므로 장착 전에 두 슬롯을 모두 비운다.
- 적 유닛에는 `CostumeManagerComponent`가 없다. 그래서 `EnemySkillDefinitions` 3행은
  `WeaponType`이 모두 비어 있고, 적 스킬에 값을 넣는 것은 데이터 실수다.
- 무기는 스킬이 바꾸기 전까지 유지된다. 턴이나 전투가 끝나도 되돌리지 않는다.

## 5. SkillEffectSteps

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| EffectSetId | string | O | SkillDefinitions.EffectSetId 참조 |
| StepIndex | integer | O | 효과 실행 순서, 1부터 연속 |
| EffectType | enum | O | 등록된 EffectType |
| TargetSelector | enum | O | `SELF_UNIT`, `FRONT_TARGET`(호환), `PRIMARY_TARGET`, `ALL_SKILL_TARGETS` |
| Value | number | O | 피해량·회복량·거리 등 원시 효과 수치 |
| ParameterA | string | - | 효과별 확장 값 |
| ParameterB | string | - | 효과별 확장 값 |
| ConditionId | string | - | 조건 규격 참조용 예약 필드 |

현재 구현 EffectType M1: `DAMAGE`, `PUSH`, `HEAL`. 새 타입은 Executor, Router, Validator,
데이터 사전을 함께 수정한 뒤 사용한다.

`HEAL`은 `HealEffectExecutorLogic`이 처리하며 `BattleSessionComponent.ResolveSkillHealImpact`로
내려간다. 같은 팀 대상만 회복하고 사망한 유닛은 부활시키지 않는다.

`SELF_UNIT`은 보드 타깃 스냅샷을 보지 않고 시전자 자신을 반환한다. `TargetingType=SELF`
(§4)와 짝을 이뤄, 사거리 안에 적이 없어도 성립하는 지원 스킬을 만든다. 현재 조합 사용
사례는 마법사의 `heal`(`SELF` + `HEAL`/`SELF_UNIT`)이다.

`ParameterA=SOURCE_BASIC_ATTACK`은 `Value` 대신 시전 유닛의
`BattleUnitComponent.BasicAttackDamage`를 피해량으로 사용한다. 적마다 다른 공격력을 쓰는
`enemy_basic_attack_effects`가 이 방식을 쓴다.

## 6. EnemyDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| EnemyDefinitionId | string | O | 적 전투 정의 고유 ID |
| DisplayName | string | O | 제작자용 표시 이름 |
| MaxHp | integer | O | 최대 HP |
| BasicAttackDamage | number | O | 기본 공격 피해 |
| PatternId | string | O | EnemyPatternSteps 참조 |
| MovementPolicy | enum | O | 추적 이동 또는 현재 방향 고정 이동 |
| InitialFacingPolicy | enum | O | 생성 순간 한 번만 결정되는 초기 방향 |
| IsBoss | boolean | O | `true`이면 사망 시 `BOSS_KILL` 드롭 Trigger를 함께 발행 |

허용 MovementPolicy M1: `TRACK_PLAYER`, `FIXED_FACING`.

허용 InitialFacingPolicy M1: `FACE_PLAYER`(생성 시 플레이어를 바라보는 방향으로 결정), `FIXED_LEFT`(항상 왼쪽), `FIXED_RIGHT`(항상 오른쪽). 기본값은 `FACE_PLAYER`. `MovementPolicy`가 전투 중 계속 갱신되는 이동/추적 규칙인 것과 달리, `InitialFacingPolicy`는 스폰 순간에만 한 번 적용되고 이후에는 Pattern Action(§7)만 방향을 바꾼다. `StageEnemySpawns.FacingOverride`(§11)가 비어 있을 때, 그리고 `StageEnemyWaves`(§13)의 웨이브 스폰 시 이 값을 읽는다.

적의 실제 `EnemyModelId`는 외형·컴포넌트 템플릿의 배치 책임이므로 `EnemySpawnPools`에서 연결한다.
Repository가 이 행을 검증·변환하고, Spawn 시 각 `BattleUnitComponent`에 HP·공격력·패턴·이동 정책을 복사한다.
따라서 서로 다른 정의의 적이 같은 보드에 동시에 살아 있어도 세션 공용 값에 서로 덮어쓰지 않는다.

## 7. EnemyPatternSteps

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| PatternId | string | O | 패턴 ID |
| StepIndex | integer | O | 실행 순서, 1 이상 |
| ActionType | enum | O | 등록된 EnemyActionType |
| ConditionType | enum | O | 실행 조건, 기본 ALWAYS |
| TileId | string | - | TELEGRAPH/EXECUTE_TILE에서 사용. 적이 쓰는 값이므로 `EnemySkillDefinitions`(§4.1)의 SkillId를 넣는다 |
| TelegraphTurns | integer | O | 준비 턴 수, 0 이상 |
| ParamA | string | - | 행동별 인자 |
| ParamB | string | - | 행동별 인자 |
| ParamC | string | - | 행동별 인자 |
| NextStepOnSuccess | integer | - | 비어 있으면 다음 StepIndex |
| NextStepOnFailure | integer | - | 비어 있으면 다음 StepIndex |
| Enabled | boolean | O | `true`인 행만 Repository가 로드 |

허용 ActionType M1: `WAIT`, `TURN_TO_PLAYER`, `MOVE_TOWARD`, `MOVE_AWAY`, `MOVE_FIXED_FACING`, `TELEGRAPH_TILE`, `EXECUTE_TILE`.

- `TURN_TO_PLAYER`: 현재 CellIndex는 유지하고 플레이어 방향으로 `Facing`만 바꾼다.
- `MOVE_TOWARD`: 플레이어 방향으로 `Facing`을 바꾼 뒤 그 방향으로 1칸 이동한다.
- `MOVE_AWAY`: 플레이어 반대 방향으로 `Facing`을 바꾼 뒤 그 방향으로 1칸 이동한다.
- `MOVE_FIXED_FACING`: 플레이어 위치를 참조하거나 `Facing`을 바꾸지 않고 현재 방향으로 1칸 이동한다.
- `TELEGRAPH_TILE`: `TileId`를 `TelegraphTurns`회 예고한다. 보드·HP를 바꾸지 않으며 카운트가 끝난 뒤 성공 Step으로 이동한다.
- `EXECUTE_TILE`: 예고와 분리된 실제 타일 실행이다. 실행 시점의 보드 상태로 대상을 다시 판정한다.
- 이동 목적지가 보드 밖이거나 점유된 경우 위치와 `Facing`을 유지하고 성공 분기는 `WAIT` 결과로 끝낸다. 자동 반전은 허용하지 않는다.

추적형/고정형은 Pattern 전체에 `TURN_TO_PLAYER`가 있는지로 판정하지 않는다. 각 Step의 Action 의미가 독립적이며 하나의 Pattern에서 추적 Action과 고정 방향 Action을 함께 사용할 수 있다.

허용 ConditionType M1: `ALWAYS`, `DISTANCE_EQ`, `DISTANCE_LE`, `HP_RATIO_LE`, `CELL_FREE`.

현재 수직 슬라이스는 `prototype_tracker` 4행, `prototype_fixed` 3행,
`prototype_retreat` 2행, `prototype_telegraph` 3행, `region_01_ranged_basic` 4행을
실제 `EnemyPatternSteps` Dataset으로 제공한다.
Repository는 `PatternId → StepIndex`로 정렬하고,
전용 Validator는 SchemaVersion, 연속 StepIndex, Action/Condition enum, TileId와 거리 인자를
검사한다. Resolver는 `ALWAYS`, `DISTANCE_EQ`, `DISTANCE_LE`, `HP_RATIO_LE`, `CELL_FREE`와 `WAIT`,
`TURN_TO_PLAYER`, `MOVE_TOWARD`, `MOVE_AWAY`, `MOVE_FIXED_FACING`, `TELEGRAPH_TILE`, `EXECUTE_TILE`을
실행 가능 타입으로 받는다. `prototype_retreat`는 `MOVE_AWAY`, `prototype_telegraph`는 2턴 예고 뒤
`enemy_basic_attack` 실행으로 이어지는 재사용 제작 샘플이다.

`EXECUTE_TILE` 분기는 특정 SkillId를 하드코딩하지 않고 `TileId`를 그대로
`TryExecuteSkill(enemyId, intent.TileId)`에 넘긴다. 따라서 적에게 새 행동을 주려면
`EnemySkillDefinitions`에 행을 추가하고 패턴의 `TileId`만 바꾸면 되며, 전투 코드는 수정하지
않는다.

`EXECUTE_TILE`과 `TELEGRAPH_TILE`의 `TileId`는 `EnemySkillDefinitions.SkillId` 참조다.
특정 스킬 ID를 Session에서 분기하지 않으며, 적 공격도 공용 Skill Targeting/Effect 파이프라인으로 실행한다.
`DISTANCE_LE`의 `ParamA`는 1 이상의 최대 Cell 거리다.

`CELL_FREE`는 `ParamA`를 셀 선택자로 사용한다.

| ParamA | 검사 Cell |
|---|---|
| `FRONT` | 현재 Facing 앞 1칸 |
| `BACK` | 현재 Facing 뒤 1칸 |
| `TOWARD_PLAYER` | 플레이어 방향 1칸 |
| `AWAY_FROM_PLAYER` | 플레이어 반대 방향 1칸 |

보드 밖이거나 살아 있는 다른 유닛이 점유하면 `false`다. Session은 준비 시점의
`BoardStateComponent` 점유를 Selector별 boolean Snapshot으로 변환하고 Resolver는 이 값만
읽는다. 이동 Action은 실행 시 `TryMove()`에서 경계와 점유를 다시 검사한다. 준비 후 실행
사이에 점유가 달라졌다면 이동하지 않고 실패 결과로 Runner 전이를 적용한다.

`MOVE_AWAY`는 Resolver가 플레이어 반대 방향을 PreparedIntent에 저장한다. 실행기는 목적지
경계와 점유를 먼저 검사한 뒤 Facing 변경과 1칸 이동을 한 행동으로 처리한다. 사전 검사에서
막히면 위치와 Facing을 모두 유지하고 실패 분기로 이동한다. 예상 밖 이동 실패가 발생해도
Facing을 이전 값으로 복구한다.

현재 `EnemyPatternRunnerComponent`가 적 Entity마다 `CurrentStepIndex`와 준비 중 Step을
소유한다. Resolver는 Current Step에서 시작해 조건 또는 Action 적용 가능성 실패 시
`NextStepOnFailure`를 따라가며, 실행할 행을 PreparedIntent로 고정한다. 실제 행동 성공/실패가
확정된 뒤에만 Runner가 선택된 행의 `NextStepOnSuccess`/`NextStepOnFailure`로 Current Step을
갱신한다. 빈 다음 Step 값은 현재 Step 다음 행을 사용하고 마지막 행 뒤에는 Step 1로 순환한다.
동일 Prepare 중 방문한 Step을 다시 만나면 `PATTERN_FAILURE_BRANCH_CYCLE`로 중단한다.

`TELEGRAPH_TILE`의 남은 턴도 각 적 Runner가 소유한다. 첫 Prepare는 행의 `TelegraphTurns`에서
시작하고, 성공적으로 Complete될 때만 1 감소한다. 남은 값이 있으면 같은 Step을 유지하고,
0이 되면 `NextStepOnSuccess`로 이동한다. PreparedIntent가 취소되면 준비 중 복사본만 버리고
확정 카운트는 줄이지 않으므로 취소·재준비로 턴이 잘못 소비되지 않는다.

### 7.1 런타임 PreparedIntent 계약

`EnemyPatternSteps`는 정적 원본이고, 전투 중에는 선택된 한 행을 읽기 전용 `PreparedIntent` Snapshot으로 변환한다. Snapshot은 별도 Dataset이 아니며 저장/동기화 목적의 런타임 값이다.

| 필드 | 원본/생성 규칙 | 실행 중 변경 |
|---|---|:---:|
| EnemyDefinitionId | 실행 유닛 | 불가 |
| PatternId | EnemyDefinitions 또는 PatternOverrideId | 불가 |
| StepIndex | 선택된 EnemyPatternSteps 행 | 불가 |
| ActionType | 선택된 행 | 불가 |
| TileId | 선택된 행 | 불가 |
| TelegraphTurnsRemaining | Runner의 확정 남은 값 또는 TelegraphTurns에서 시작 | TELEGRAPH_TILE Complete 때만 감소 |
| PreparedTurn | 준비 시 TurnNumber | 불가 |
| State | EMPTY/PREPARED/EXECUTING | 상태 전이만 허용 |

- Snapshot에는 `TargetId`나 목표 CellIndex를 저장하지 않는다.
- `EXECUTE_TILE`은 실행 시점의 현재 CellIndex/Facing과 `SkillDefinitions.TargetingType`으로 타깃을 다시 계산한다.
- 밀치기·이동·회전은 Snapshot의 ActionType/TileId를 바꾸거나 다음 Step을 다시 선택하지 않는다.
- 실행 성공/실패가 확정된 뒤에만 `NextStepOnSuccess`/`NextStepOnFailure`를 적용한다.
- Client에는 HUD에 필요한 EnemyId/ActionType/TileId/남은 준비 턴만 읽기 전용 DTO/Event로 전달한다.

### 7.2 표 기반 협업 규칙

- 콘텐츠 개발자는 기존 enum 범위 안에서 `EnemyDefinitions`와 `EnemyPatternSteps`의 독립 행을 수정한다.
- 행은 물리적 줄 번호가 아니라 `EnemyDefinitionId`, `PatternId`, `StepIndex`로 참조한다.
- 같은 PatternId 안의 StepIndex는 한 개발자가 한 변경 단위에서 소유하고, 다른 패턴 행은 동시에 수정할 수 있다.
- CSV는 `PatternId → StepIndex`로 결정 정렬한다. 행 순서 자체를 게임 규칙으로 사용하지 않는다.
- 전투/UI 코드가 `_DataService`를 직접 호출하지 않는다. 공용 Loader/Repository가 검증·변환한 Definition만 전달한다.
- 기존 ActionType 조합으로 만든 새 적은 Router나 `BattleSessionComponent` 수정 없이 추가되어야 한다.
- 새 ActionType 추가는 코어 개발자가 Router, Validator enum, 데이터 사전, positive log 테스트를 함께 변경한다.
- 동일 CSV에서 실제 병합 충돌이 반복되기 전에는 별도 생성기를 도입하지 않는다. 충돌이 반복되면 PatternId별 소스 조각을 결정적으로 병합하는 도구를 Phase 5 제작자 도구 범위로 추가한다.

### 7.3 BossPhaseDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| EnemyDefinitionId | string | O | `IsBoss=true`인 EnemyDefinitions 참조 |
| PhaseIndex | integer | O | 1부터 연속 |
| PhaseId | string | O | 보스 안에서 유일한 표시/상태 ID |
| HpRatioLE | number | O | `(0,1]`, 뒤 Phase일수록 작은 임계값 |
| PatternId | string | O | EnemyPatternSteps 참조 |
| Enabled | boolean | O | 활성 행 여부 |

첫 Phase는 `HpRatioLE=1.0`이고 `EnemyDefinitions.PatternId`와 같아야 한다.
Phase 전환은 이미 고정된 적 Queue를 바꾸지 않으며, 다음 라운드 계획부터 새 Pattern을 사용한다.

## 8. StageDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `2` |
| StageId | string | O | 고유 스테이지 ID |
| RegionId | string | O | `RegionDefinitions.RegionId` 참조 |
| StageIndex | integer | O | Region 안 전투 순서, 1 이상 |
| StageType | enum | O | 현재 `NORMAL`, `BOSS` |
| DisplayName | string | O | 표시 이름 |
| CellCount | integer | O | 1차원 Cell 수, 1 이상 |
| CellStartX | number | O | Cell 0의 월드 X |
| CellSpacing | number | O | Cell 중심 간격, 0보다 큼 |
| UnitY | number | O | 유닛 기준 월드 Y |
| PlayerStartCell | integer | O | 0 이상 `CellCount` 미만 |
| QueueCapacity | integer | O | 기본 큐 용량, 1 이상 |
| WaveTableId | string | O | `StageEnemyWaves.WaveTableId` 참조 |
| NextStageId | string | - | 초기 호환 열. 실제 다음 콘텐츠는 NodeDefinitions가 결정 |
| StageRuleId | string | - | 특수 Stage 규칙 ID |

`CellStartX/UnitY/CellSpacing`은 월드 좌표 표현용이며 논리 판정은 CellIndex를 사용한다.
현재 `region_01_stage_01`은 실제 Dataset에서 로드되고 compatibility fallback은 제거됐다.
`StageId`는 조회에만 사용한다. 코드가 ID 문자열에서 Region, 순서, Type을 추출하면 안 된다.

## 9. RegionDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| RegionId | string | O | 변경하지 않는 지역 고유 ID |
| DisplayName | string | O | 화면 표시 이름 |
| RegionOrder | integer | O | Region 표시 순서, 1 이상 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

기본 키: `RegionId` 유일.

예시:

| RegionId | DisplayName | RegionOrder | Enabled |
|---|---|---:|---|
| region_01 | Region 1 | 1 | true |

Region은 소속과 표시 순서만 소유한다. Node Graph, 공통 적 Pool, 보스 Stage는 각각
`NodeDefinitions`, `EnemySpawnPools`, `StageDefinitions`가 소유하며 Region 행에 중복 저장하지 않는다.

## 10. NodeDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1`, Loader 지원 버전과 일치해야 함 |
| NodeGraphId | string | O | 독립된 진행 그래프 ID. RegionId와 문자열 파싱으로 연결하지 않음 |
| NodeId | string | O | 노드 고유 ID |
| NodeType | enum | O | 등록된 NodeType |
| StageId | string | - | `BATTLE`/`BOSS`에서 StageDefinitions 참조, 그 외 타입은 비움 |
| IsStartNode | boolean | O | 이 NodeGraph에서 지도판 진입 시 처음 여는 노드인지 |
| NextNodeIds | string | - | `\|` 구분 다음 노드 ID 목록 |
| PositionX | number | O | 지도판 표시 X (월드 좌표 아님, UI 배치용) |
| PositionY | number | O | 지도판 표시 Y |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

허용 NodeType M1: `BATTLE`, `SHOP`, `EVENT`, `REST`, `BOSS`.
신규 데이터는 보스도 `NodeType=BATTLE`로 작성하고 `StageDefinitions.StageType=BOSS`로 구분한다.
`NodeType=BOSS`는 기존 데이터 호환용으로만 허용한다.

기본 키: `(NodeGraphId, NodeId)` 유일. 같은 NodeGraphId 안에 `IsStartNode=true`가 정확히 1개여야 한다. `NextNodeIds`가 참조하는 NodeId는 같은 NodeGraphId 안에 존재해야 한다.

`StageDefinitions.NextStageId`는 초기 호환 열이며 Run의 실제 다음 콘텐츠를 결정하지 않는다.
전투 종료 뒤 이동 가능한 대상은 `NodeDefinitions.NextNodeIds`만 원본으로 사용한다.
런타임은 각 다음 노드를 다음 공통 DTO로 정규화한다.

```text
NextNodeIds         노드 식별자 목록
NextContentTypes    BATTLE/BOSS/SHOP/EVENT/REST 목록
NextContentIds      BATTLE/BOSS는 StageId, 그 외는 NodeId
```

세 문자열은 같은 인덱스끼리 한 옵션이며 `|`로 구분한다. UI, 맵 이동, 상점은 이 DTO를
읽는 소비자일 뿐 `PlayerRunStateComponent`의 진행 상태를 직접 변경하지 않는다.
`NodeDefinitionRepositoryLogic`은 SchemaVersion, NodeType, StageId 사용 규칙,
자기 참조·중복 NextNodeId, 비활성 행을 차단한다.

현재 실제 `NodeDefinitions.userdataset/.csv`에는 `prototype_run` 그래프의
`stage01_battle(BATTLE) → shop_after_stage01(SHOP)` 두 행이 등록되어 있다.
`NodeContentValidatorLogic`은 시작 노드가 정확히 1개인지, NodeId 중복·다음 노드·Stage 참조·
시작점에서 도달 불가능한 노드가 없는지를 그래프 단위로 검증한다. Maker에서 두 행의
`Source=DATASET`, `StartNodeId=stage01_battle`, 승리 후 `NextContentTypes=SHOP`을 확인했으며
Repository의 prototype fallback은 비활성 상태다.

예시(`henesys_graph`, 회의 문서의 "헤네시스 1-1/1-2/1-3" 배치를 노드 3개로 표현):

| NodeGraphId | NodeId | NodeType | StageId | IsStartNode | NextNodeIds |
|---|---|---|---|---|---|
| henesys_graph | n1 | BATTLE | henesys_1_1 | true | n2 |
| henesys_graph | n2 | BATTLE | henesys_1_2 | false | n3 |
| henesys_graph | n3 | BOSS | henesys_boss_mushmom | false | |

상점/이벤트 노드가 필요하면 같은 그래프에 `NodeType=SHOP`, `StageId`는 비운 행을 추가한다.
SHOP의 `NextContentId`는 NodeId다. 현재 런 상점은 SHOP Node와 같은 NodeGraphId/NodeId를 가진
`ShopDefinitions`를 찾고, `ShopEntries.ShopId`로 상품을 구성한다. 전투 StageId나
`ShopEntryId`를 `NextNodeIds`에 직접 넣지 않는다. 계획 단계의 메타/월드 상점
`ShopItemDefinitions`는 NodeDefinitions 진행 그래프에 연결하지 않는다.

## 11. StageEnemySpawns

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| WaveTableId | string | O | `StageDefinitions.WaveTableId`가 참조하는 웨이브 표 ID |
| WaveIndex | integer | O | 몇 번째 웨이브 소속인지. 첫 웨이브는 `1`이며 스테이지 시작 시 런타임 생성 |
| SpawnOrder | integer | O | 같은 Wave 안 결정적 생성/행동 동률 순서 |
| EnemyId | string | O | EnemyDefinitions 참조 |
| CellIndex | integer | O | 스테이지 보드 범위 안 |
| FacingOverride | integer | - | 비우면 EnemyDefinitions.InitialFacingPolicy 사용, 값은 `-1` 또는 `1` |
| PatternOverrideId | string | - | 특정 배치만 패턴 교체 |
| HpMultiplier | number | O | 0보다 큼 |

같은 StageId·WaveIndex에서 CellIndex 중복 점유를 허용하지 않는다. `WaveIndex=1` 행은 스테이지 시작과 동시에 `SpawnByModelId`로 생성하며 플레이어 좌/우 양쪽 CellIndex를 사용할 수 있다. 맵 파일에 전투 적을 고정 배치하지 않는다.

## 12. EnemySpawnPools

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| PoolId | string | O | 스폰 후보 풀 ID |
| EnemyDefinitionId | string | O | EnemyDefinitions 참조 |
| EnemyModelId | string | O | spawn 가능한 프로젝트 model ID |
| Weight | integer | O | 1 이상 |
| MinWaveIndex | integer | O | 최소 등장 웨이브 |
| MaxWaveIndex | integer | O | 최대 등장 웨이브 |

기본 키: `(PoolId, EnemyDefinitionId, EnemyModelId)`는 유일해야 한다.
현재 Phase 1 런타임은 유효 후보를 `EnemyDefinitionId|EnemyModelId`로 정렬한 뒤
`(RunSeed mod ΣWeight) + ((WaveIndex - 1) × 31) + SpawnIndex`를 선택 순번으로 사용하는
결정적 가중치 순환을 수행한다.
선택 롤은 `1..ΣWeight` 범위이며 누적 Weight 구간에 들어간 후보를 선택한다.
같은 RunSeed와 Stage 데이터는 같은 스폰 구성을 재현하고, 스폰 슬롯마다 독립적으로 정의를 선택하므로
한 Wave 안에서도 서로 다른 HP·공격력·패턴·이동 정책의 적이 함께 등장할 수 있다.
현재 플레이어의 `PlayerRunStateComponent.RunSeed`가 Run 전체 Seed의 원본을 보관한다.
`BattleSessionComponent.RunSeed`는 현재 전투에서 사용하는 복사본이다. 새 런 시작은
`StartNewRun(runSeed)`, 결과 화면 재시작은 현재 Seed를 유지하는 `ResetBattle()`을 사용한다.

## 13. StageEnemyWaves

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| WaveTableId | string | O | `StageDefinitions.WaveTableId`가 참조하는 웨이브 표 ID |
| WaveIndex | integer | O | `1`부터 시작하는 웨이브 순서. 첫 행도 Stage 시작 시 같은 런타임 Spawn 경로 사용 |
| SpawnTriggerMode | enum | O | 전멸 기본 조건과 강제 증원 예외 방식 |
| EnemyPoolId | string | O | EnemySpawnPools 참조 |
| SpawnCount | integer | O | 이번 웨이브에 등장할 적 수 |
| MaxConcurrent | integer | O | 보드에 동시 존재 가능한 최대 적 수 |
| SpawnSidePolicy | enum | O | 좌우 빈 칸 분배 정책 |
| ClearSpawnDelaySeconds | number | O | 직전 전투 그룹 전멸 후 다음 웨이브까지 지연, 0 이상 |
| ForceAfterTurns | integer | O | 해당 웨이브 생성 후 강제 증원까지 완료 턴 수, 0은 비활성 |
| ForceAfterSeconds | number | O | 해당 웨이브 생성 후 강제 증원까지 실시간 초, 0은 비활성 |

허용 `SpawnTriggerMode`:

- `CLEAR_ONLY`: 현재까지 생성된 적이 모두 죽었을 때만 다음 웨이브를 시작한다.
- `TURN_LIMIT`: 전멸 또는 `ForceAfterTurns` 중 먼저 충족한 조건으로 다음 웨이브를 예약한다.
- `TIME_LIMIT`: 전멸 또는 `ForceAfterSeconds` 중 먼저 충족한 조건으로 다음 웨이브를 예약한다.
- `TURN_OR_TIME`: 전멸, 턴 제한, 시간 제한 중 먼저 충족한 조건으로 다음 웨이브를 예약한다.

`TURN_LIMIT`과 `TURN_OR_TIME`은 `ForceAfterTurns > 0`, `TIME_LIMIT`과 `TURN_OR_TIME`은 `ForceAfterSeconds > 0`이어야 한다. 마지막 WaveIndex 행의 강제 증원 값은 `0`으로 두며 Loader가 0이 아닌 값을 오류로 차단한다.

허용 SpawnSidePolicy M1: `BALANCED`, `ANY`.

웨이브가 시작되면 플레이어가 서 있는 칸과 이미 점유된 칸을 제외하고, 남은 빈 칸을 플레이어 CellIndex 기준 Left/Right 배열로 나눈 뒤 각각 CellIndex 오름차순으로 정렬한다.

- `BALANCED`: `SpawnCount >= 2`이고 양쪽에 빈 칸이 있으면 좌우에서 최소 1칸씩 먼저 선택한다. 남은 수량은 양쪽을 합친 빈 칸에서 선택한다.
- `ANY`: 좌우를 강제하지 않고 전체 빈 칸에서 선택한다.

모든 선택은 `RunSeed + StageIndex + WaveIndex` 기반 결정적 RNG를 사용한다. 생성된 적의 방향은 `EnemyDefinitions.InitialFacingPolicy`로 결정하고 고정 배치에만 `FacingOverride`를 적용한다. `MaxConcurrent`를 넘거나 빈 칸이 부족한 요청은 빈 칸이 다시 생길 때까지 `SpawnOrder`를 유지한 채 대기한다.

턴 제한은 Stage 전체에서 단조 증가하는 `StageTurnNumber`를 사용한다. 웨이브마다 `SpawnedAtStageTurn`을 저장하고 `StageTurnNumber - SpawnedAtStageTurn >= ForceAfterTurns`일 때 조건이 충족된다. 새 웨이브가 겹쳐 생성돼도 StageTurnNumber를 초기화하지 않는다.

시간 제한은 서버 경과 시간을 기준으로 하되, 제한 도달 시 전투 상태를 즉시 변경하지 않는다. `ForcedSpawnPending`을 기록하고 플레이어 큐·Impact·적 행동이 모두 끝난 안전한 턴 경계에서 한 번만 소비한다. 전멸 조건과 제한 조건이 같은 경계에서 함께 충족되면 하나의 Spawn 요청으로 합친다.

Stage Clear 조건은 `마지막 WaveIndex까지 생성 완료 AND 대기 중 Spawn 요청 없음 AND Board Registry 전체 생존 적 수 0`이다. 강제 증원으로 이전 웨이브 적이 남아 있어도 이 조건 전에는 Victory를 허용하지 않는다.

## 14. AugmentDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| AugmentId | string | O | 증강 ID |
| NameKey | string | O | Locale 키 |
| DescriptionKey | string | O | Locale 키 |
| Rarity | enum | O | COMMON, RARE, EPIC |
| StackPolicy | enum | O | 현재 `UNIQUE`만 구현. `STACK_ADD`, `STACK_REFRESH`, `EXCLUSIVE_GROUP`은 PLANNED |
| MaxStacks | integer | O | 현재 반드시 `1`. 다중 스택 구현 후 1 이상으로 확장 |
| ExclusiveGroup | string | - | 배타 그룹 ID |
| JobTagFilter | string | - | 비어 있으면 모든 직업 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

## 15. AugmentEffects

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| AugmentId | string | O | AugmentDefinitions 참조 |
| Seq | integer | O | 증강 내부 순서 |
| TriggerType | enum | O | 반응할 BattleEvent 종류 |
| ConditionType | enum | O | 실행 조건 |
| ConditionValue | number | - | ConditionType이 값을 필요로 할 때 사용 (예: `CHANCE_ROLL`의 0.0~1.0 확률) |
| EffectType | enum | O | 등록된 EffectType |
| TargetType | enum | O | 효과 대상 |
| Priority | integer | O | 이벤트 체인 우선순위 |
| Amount | number | - | 효과량 (피해량 배율 등) |
| ParamA | string | - | 확장 값 |
| ParamB | string | - | 확장 값 |
| ParamC | string | - | 확장 값 |
| Enabled | boolean | O | 효과 행 활성 여부 |

허용 TriggerType M1: `TURN_START`, `COMMAND_ACCEPTED`, `TILE_QUEUED`, `BEFORE_TILE_EXECUTE`, `AFTER_DAMAGE`, `UNIT_MOVED`, `ENEMY_DIED`, `STAGE_CLEARED`.

현재 `IMPLEMENTED` ConditionType은 `ALWAYS`, `HP_RATIO_LE`다. `HP_RATIO_LE`는
`ConditionValue`에 0 초과 1 이하의 HP 비율을 사용한다.

현재 `IMPLEMENTED` TargetType은 `SELF`다. 현재 구현된 전체 최소 조합은
`TURN_START`, `ALWAYS`/`HP_RATIO_LE`, `HEAL`/`SELF`다.

`CHANCE_ROLL`(`ConditionValue`=0.0~1.0의 성공 확률, RunSeed 기반 결정적 롤)과
`FRONT_CELL`, `RANGE_OFFSETS`, `FIRST_ENEMY_FORWARD`, `REAR_CELL`은 `PLANNED`다.
이 값들은 §23(새 데이터 추가 완료 기준)의 "새 원시 Type" 규칙에 따라 Router/Resolver,
Validator 허용 목록, 회귀 테스트를 함께 갖춘 뒤에만 `IMPLEMENTED`로 전환하고 실전 데이터에 배치한다.
`JobDefinitions.JobPassiveSetId`는 현재 하나의 `AugmentId`를 참조하며, 그 ID에 속한 여러
`AugmentEffects` 행이 직업 시작 패시브 세트가 된다. 효과 실행 순서는 낮은 `Priority`부터이며,
동률은 런 획득 순서 → `Seq` → `AugmentId`로 고정한다. 현재 5개 직업은 각각 `warrior_recovery`,
`mage_focus`, `archer_focus`, `thief_focus`, `pirate_focus`를 런 시작 시 UNIQUE 1스택으로
지급받는다. 다섯 모두 같은 `TURN_START`/`HP_RATIO_LE 0.99`/`HEAL`/`SELF` 최소 조합을 재사용해
턴 시작에 HP가 99% 이하이면 자신을 1 회복하는 동일한 패턴이며, 직업별 차별화된 패시브 효과는
아직 설계되지 않았다. 문서의 나머지 M1 Type은 계획된 확장 규격이며 아직 Validator에 등록되지 않았다.

### 15.1 계획 예시 — 자쿰의투구 (50% 확률 후방 공격, PLANNED)

`AugmentDefinitions` 행:

| AugmentId | NameKey | Rarity | StackPolicy | MaxStacks |
|---|---|---|---|---|
| zakum_helmet | augment.zakum_helmet.name | RARE | UNIQUE | 1 |

`AugmentEffects` 행:

| AugmentId | Seq | TriggerType | ConditionType | ConditionValue | EffectType | TargetType | Amount |
|---|---|---|---|---|---|---|---|
| zakum_helmet | 1 | AFTER_DAMAGE | CHANCE_ROLL | 0.5 | DAMAGE | REAR_CELL | 1.0 |

읽는 법: 플레이어의 공격이 적중(`AFTER_DAMAGE`)할 때마다 50%(`CHANCE_ROLL 0.5`) 확률로, 방금 공격과 같은 피해량 배율(`Amount 1.0`)의 피해를 후방 칸(`REAR_CELL`)에 추가로 적용한다. 현재 Router/Validator에는 `CHANCE_ROLL`, `DAMAGE`, `REAR_CELL` 조합이 등록되지 않았으므로 이 행은 설계 예시일 뿐 CSV에 추가할 수 없다.

## 16. StageAugmentPools

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| PoolId | string | O | 후보 풀 ID |
| AugmentId | string | O | AugmentDefinitions 참조 |
| Weight | integer | O | 1 이상 |
| MinStageIndex | integer | O | 최소 등장 스테이지 |
| MaxStageIndex | integer | O | 최대 등장 스테이지 |
| RequiredJobTag | string | - | 직업 태그 조건 |

## 17. AugmentConflicts

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| AugmentId | string | O | 기준 증강 |
| ConflictAugmentId | string | O | 함께 보유할 수 없는 증강 |
| ReasonCode | string | O | UI/로그용 사유 코드 |

충돌은 방향과 무관하게 취급한다. Validator는 A->B만 있어도 B->A를 런타임 인덱스에 함께 등록한다.

## 18. CurrencyDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| CurrencyId | string | O | 재화 고유 ID |
| DisplayName | string | O | 표시 이름 |
| Category | enum | O | 등록된 Category |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

허용 Category M1: `RUN_SCOPED`(런 종료 시 초기화, 전투/스테이지 보상으로 지급), `META_PERSISTENT`(플레이어 저장 데이터에 누적되어 런 간 유지, M1에서는 정의만 하고 실제 지급 경로는 아직 연결하지 않음), `PREMIUM_CASH`(실제 결제로만 채우는 캐시성 재화. 결제 연동 자체는 여전히 M1 범위 밖이며, 이 값은 "보상으로 지급하지 않는다"는 분류로만 쓰인다).

기본 키: `CurrencyId` 유일.

### 18.1 예시

| CurrencyId | DisplayName | Category |
|---|---|---|
| gold | 골드 | RUN_SCOPED |
| cash | 캐시 | PREMIUM_CASH |

현재 실제 `CurrencyDefinitions.userdataset/.csv`에는 `gold / RUN_SCOPED / Enabled=true`가 등록되어 있다. 적 드롭의 `CURRENCY` 참조는 현재 `RUN_SCOPED`만 허용한다.

### 18.2 ConsumableDefinitions

전투 드롭·상점·런 인벤토리가 같은 소모품 ID를 참조하고, 사용 효과를 원시 Effect Handler에 연결하기 위한 정의다.

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| ConsumableId | string | O | 소모품 고유 ID |
| DisplayName | string | O | 표시 이름 |
| MaxStack | integer | O | 런에서 보유 가능한 기본 수량 |
| UseTiming | enum | O | 현재 `BATTLE_FREEPLAY` |
| ConsumesTurn | boolean | O | 사용 시 턴 소비 여부 |
| EffectType | enum | O | 등록된 원시 효과. 현재 `HEAL` |
| EffectValue | number | O | 효과 기본 수치, 0 초과 |
| TargetType | enum | O | 현재 `SELF` |
| Enabled | boolean | O | 활성 여부 |

현재 실제 Dataset에는 `potion_hp_small / MaxStack=3 / BATTLE_FREEPLAY /
ConsumesTurn=false / HEAL 4 / SELF`가 등록되어 있다. 사용 성공 뒤에만
`PlayerRunInventoryComponent`가 수량을 차감하며, 같은 UseKey는 효과와 소비 모두 한 번만 처리한다.

## 19. StageRewardDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| StageId | string | O | StageDefinitions 참조 |
| CurrencyId | string | O | CurrencyDefinitions 참조 |
| Amount | integer | O | 1 이상 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

기본 키: `(StageId, CurrencyId)`는 유일해야 한다. 한 StageId에 여러 CurrencyId 행을 추가하면 스테이지 클리어 시 여러 재화를 동시에 지급한다.

`Category=PREMIUM_CASH`인 CurrencyId는 이 표에서 참조할 수 없다(`DATA_REWARD_CURRENCY_NOT_ALLOWED`).

이 표는 전투/스테이지 클리어 보상만 다룬다. `NodeType=BATTLE`/`BOSS` 노드는 `StageId`를 통해 이 표를 간접 참조한다. `NodeType=SHOP`/`EVENT`/`REST` 노드 자체의 보상은 아직 게임플레이가 정의되지 않았으므로 M1 범위에 포함하지 않는다. 필요해지면 같은 CurrencyId 참조 패턴을 그대로 재사용한다.

### 19.1 예시

| StageId | CurrencyId | Amount |
|---|---|---|
| henesys_1_1 | gold | 20 |
| henesys_boss_mushmom | gold | 100 |

## 20. 상점 데이터

상점은 수명과 재화 책임에 따라 두 시스템으로 분리한다. 현재 플레이 가능한 것은
`RUN_SCOPED` 재화를 사용하는 런 상점이며, 영구 상품·직업 해금·캐시 결제를 다루는
메타/월드 상점은 계획 단계다. 두 시스템은 `CurrencyDefinitions`와 보상 대상 ID를 공유할 수
있지만, 구매 상태와 검증 경로를 합치지 않는다.

### 20.1 ShopDefinitions (IMPLEMENTED)

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| ShopId | string | O | 런 상점 고유 ID |
| DisplayName | string | O | 제작자/UI 표시 이름 |
| NodeGraphId | string | O | NodeDefinitions.NodeGraphId 참조 |
| NodeId | string | O | 같은 그래프의 `NodeType=SHOP` NodeId 참조 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

기본 키는 `ShopId`이며 전역에서 유일해야 한다. 현재 규격에서는 `ShopId`와 `NodeId`가 같아야 한다.

### 20.2 ShopEntries (IMPLEMENTED)

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1` |
| ShopEntryId | string | O | 전체 런 상점에서 유일한 상품 행 ID |
| ShopId | string | O | ShopDefinitions.ShopId 참조 |
| DisplayName | string | O | 제작자/UI 표시 이름 |
| RewardType | enum | O | 현재 `SKILL`, `CONSUMABLE` |
| RewardRefId | string | O | RewardType에 맞는 SkillId 또는 ConsumableId |
| RewardAmount | integer | O | 지급 수량, 1 이상 |
| PriceCurrencyId | string | O | `RUN_SCOPED` CurrencyDefinitions.CurrencyId 참조 |
| PriceAmount | integer | O | 가격, 0 이상 |
| DisplayOrder | integer | O | 같은 ShopId 안의 오름차순 표시 순서 |
| MaxPurchasesPerVisit | integer | O | 현재 반드시 `1` |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

현재 실제 Dataset에는 `shop_after_stage01` 상점과 `potion_hp_small` 상품 1행이 등록되어 있다.
`RewardType=SKILL` 상품은 현재 없다 — 판매하던 `heavy_slash`가 §4.1의 스킬 정리에서
제거되면서 함께 삭제했다. 서버는 Dataset의 가격과 보상 참조를 다시 조회한 뒤 재화 차감과
지급을 원자적으로 확정한다. 자세한 제작·API 규격은 `Guide/Run-Shop-Authoring-Guide.md`를
따른다.

`RewardType=SKILL` 상품을 다시 넣을 때는 `RewardRefId`가 §4.1의
`GetPlayerGrantableSkillIds()` 범위 안에 있어야 한다. 적 전용 SkillId를 넣으면 플레이어가
몬스터 전용 행을 보유하게 된다.

### 20.3 ShopItemDefinitions (PLANNED — Meta/World Shop)

이 표는 영구 상품·시작 유물·직업 해금·캐시성 상품을 위한 목표 스키마다. 현재 대응하는
`.userdataset`/`.csv`, Repository, Validator, 구매 Runtime은 없으므로 콘텐츠 제작에 사용할 수 없다.
런 상점 상품은 이 표가 아니라 §20.1~20.2를 사용한다.

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| ItemId | string | O | 상점 아이템 고유 ID |
| DisplayName | string | O | 표시 이름 |
| Category | enum | O | 등록된 Category |
| CurrencyId | string | O | CurrencyDefinitions 참조 |
| Price | integer | O | 0 이상 |
| EffectRefType | enum | - | `Category`가 다른 표를 참조할 때 어떤 표인지. 참조가 없으면 비움 |
| EffectRefId | string | - | `EffectRefType`이 가리키는 표의 ID (예: AugmentId, JobId) |
| UnlockConditionId | string | - | 선행 해금 조건. 비어 있으면 즉시 구매 가능 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

계획 Category: `CONSUMABLE`(소모품), `STARTER_RELIC`(시작 유물), `SKILL_UNLOCK`(스킬 해금), `PERMANENT_UPGRADE`(영구 성장), `COSMETIC`(외형), `CHARACTER_UNLOCK`(캐릭터/직업 해금).

계획 EffectRefType: `AUGMENT`(AugmentDefinitions 참조), `SKILL`(SkillDefinitions 참조), `JOB`(JobDefinitions 참조), 없으면 비움.

재화 분류(런 소모/메타 영구/캐시)는 `CurrencyDefinitions`(§18)에서 관리한다.

기본 키: `ItemId` 유일. `Category=CHARACTER_UNLOCK`이면 `EffectRefType=JOB`이어야 한다.

예시:

| ItemId | DisplayName | Category | CurrencyId | Price | EffectRefType | EffectRefId |
|---|---|---|---|---|---|---|
| relic_zakum_helmet | 자쿰의 투구 | STARTER_RELIC | cash | 4900 | AUGMENT | zakum_helmet |
| unlock_job_thief | 도적 해금 | CHARACTER_UNLOCK | cash | 9900 | JOB | thief |
| potion_hp_small | 체력 물약(소) | CONSUMABLE | gold | 50 | | |

## 21. EnemyDropDefinitions

적 사망 시 전투 중 생성되는 보상을 정의한다. 스테이지를 완료해서 받는 `StageRewardDefinitions`와 책임을 섞지 않는다. 적 밸런스 담당자는 `EnemyDefinitions`, 드롭 담당자는 이 표의 독립 행을 수정한다.

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| SchemaVersion | integer | O | 현재 `1`만 허용 |
| DropEntryId | string | O | 드롭 행 고유 ID |
| EnemyDefinitionId | string | O | `EnemyDefinitions` 참조 |
| TriggerType | enum | O | `ANY_KILL`, `COMBO_KILL`, `BOSS_KILL` |
| DropType | enum | O | `CURRENCY`, `CONSUMABLE` |
| DropRefId | string | O | CURRENCY면 `CurrencyDefinitions.CurrencyId`, CONSUMABLE이면 `ConsumableDefinitions.ConsumableId` |
| ChancePermille | integer | O | 0~1000. 1000은 100% |
| MinAmount | integer | O | 1 이상 |
| MaxAmount | integer | O | MinAmount 이상 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

기본 키는 `DropEntryId`이며 전역에서 유일해야 한다. 한 적에 여러 행을 연결할 수 있고 각 행은 서로 독립적으로 판정한다. 행이 없는 적은 오류가 아니라 드롭 없음으로 처리한다.

`ANY_KILL`은 모든 적 사망, `COMBO_KILL`은 한 번의 플레이어 큐 실행에서 두 번째 이후
처치, `BOSS_KILL`은 `EnemyDefinitions.IsBoss=true`인 적 사망에 추가로 발행한다. 한 사망은
여러 Trigger를 만족할 수 있지만 KillKey는 한 번만 소비한다.

판정은 `RunSeed + StageId + WaveIndex + SpawnOrder + UnitId + DropEntryId`를 입력으로 하는 결정적 RNG를 사용한다. 같은 입력을 재생하면 종류·성공 여부·수량이 같아야 한다. `BattleDropComponent`는 결과를 전투장 Pending 상태로 소유한다. 플레이어가 해당 Cell로 이동하면 즉시 `PlayerRunInventoryComponent`로 회수하고, 밟지 않은 나머지는 최종 승리 때 자동 회수한다. 패배·세션 종료 시 Pending 드롭은 폐기한다.

런 보상 지급 API는 `RewardKey`를 필수로 받아 같은 키가 재전송되어도 한 번만 반영한다. 현재 소모품 기본 용량은 3이며 초과분은 `OverflowCurrencyId`와 `OverflowCurrencyPerItem` 설정에 따라 런 재화로 전환한다. 이는 런 상태 규격이며 계정 영구 저장·메타 재화 지급은 아직 포함하지 않는다.

### 21.1 Prototype 호환 행

| DropEntryId | EnemyDefinitionId | TriggerType | DropType | DropRefId | ChancePermille | MinAmount | MaxAmount |
|---|---|---|---|---|---:|---:|---:|
| early_gold | early_mushroom | ANY_KILL | CURRENCY | gold | 1000 | 1 | 1 |
| early_potion | early_mushroom | ANY_KILL | CONSUMABLE | potion_hp_small | 250 | 1 | 1 |
| guard_gold | guard_mushroom | ANY_KILL | CURRENCY | gold | 1000 | 1 | 2 |
| guard_potion | guard_mushroom | ANY_KILL | CONSUMABLE | potion_hp_small | 150 | 1 | 1 |

`RootDesk/MyDesk/03_Data/EnemyDropDefinitions.userdataset/.csv` 페어에 위 4행이 이관되어 있다. Maker 런타임에서 `Source=DATASET`과 각 적 2행을 확인했으며 Repository의 prototype fallback은 비활성 상태다.

## 22. Validator 오류 코드

| 코드 | 의미 | 전투 시작 차단 |
|---|---|:---:|
| DATA_DUPLICATE_ID | 고유 ID 중복 | O |
| DATA_MISSING_REQUIRED | 필수 셀 누락 | O |
| DATA_INVALID_NUMBER | 숫자 변환 실패 | O |
| DATA_OUT_OF_RANGE | 허용 범위 밖 | O |
| DATA_INVALID_BOOLEAN | true/false 외 값 | O |
| DATA_INVALID_ENUM | 등록되지 않은 타입 | O |
| DATA_MISSING_REFERENCE | 참조 대상 없음 | O |
| DATA_DUPLICATE_ORDER | 같은 부모 안 순서 키 중복 | O |
| DATA_CELL_OCCUPIED | 스테이지 시작 셀 중복 | O |
| DATA_DISABLED_REFERENCE | 활성 콘텐츠가 비활성 콘텐츠 참조 | O |
| DATA_SPAWN_POOL_EMPTY | EnemySpawnPools의 PoolId에 활성 EnemyId가 하나도 없음 | O |
| DATA_SPAWN_COUNT_EXCEEDS_BOARD | StageEnemyWaves의 SpawnCount가 BoardSize보다 큼 | O |
| DATA_NO_START_NODE | NodeDefinitions의 한 NodeGraphId에 IsStartNode=true가 0개 또는 2개 이상 | O |
| DATA_INVALID_CHARACTER_UNLOCK_REF | PLANNED: Meta/World Shop의 Category=CHARACTER_UNLOCK인데 EffectRefType이 JOB이 아님 | O |
| DATA_REWARD_CURRENCY_NOT_ALLOWED | StageRewardDefinitions가 Category=PREMIUM_CASH인 CurrencyId를 참조 | O |
| DATA_INVALID_DROP_REFERENCE | EnemyDropDefinitions의 EnemyDefinitionId 또는 DropRefId 참조가 잘못됨 | O |
| DATA_INVALID_DROP_RANGE | ChancePermille 또는 MinAmount/MaxAmount 범위가 잘못됨 | O |
| DATA_UNUSED_ROW | 어디에서도 참조되지 않는 활성 행 | X, 경고 |
| INVALID_SKILL_WEAPON_REFERENCE | SkillDefinitions의 WeaponType이 비어 있지 않은데 §4.4에서 유효하지 않음 | O |
| UNSUPPORTED_WEAPON_EQUIP_SLOT | WeaponDefinitions의 EquipSlot이 ONE_HANDED/TWO_HANDED가 아님 | O |
| WEAPON_RUID_MISSING | WeaponDefinitions의 WeaponRuid가 비어 있음 | O |
| WEAPON_DISABLED | 활성 스킬이 Enabled=false인 무기를 참조 | O |

로그 예시:

```text
[DATA_MISSING_REFERENCE] Dataset=SkillEffectSteps Row=7 Column=EffectSetId Value=unknown_effect_set
```

`DATA_INVALID_CHARACTER_UNLOCK_REF`는 §20.3 목표 스키마에 예약된 코드이며 현재 런 상점
Validator가 반환하는 코드가 아니다.

## 23. 새 데이터 추가 완료 기준

- Maker에서 wrapper와 CSV가 한 쌍으로 인식된다.
- Runtime name이 로더에 등록된 이름과 일치한다.
- ContentValidator 차단 오류가 0개다.
- 고정 Seed 대표 시나리오에서 의도한 행이 로드되었다는 positive log가 있다.
- 새 원시 Type이 필요했다면 Router, Validator 허용 목록, 데이터 사전, 테스트를 함께 수정했다.
