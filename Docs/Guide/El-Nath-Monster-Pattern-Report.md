# 엘나스 몬스터·패턴 등록 요약

기준: 2026-10-20 / 대상: 엘나스 7-1~7-6 / 수치: 기본 난이도, 승천 보정 전.

## 1. 몬스터 구성

| 몬스터 | EnemyDefinitionId | HP | 공격·특징 |
|---|---|---:|---|
| 주니어 예티 | `el_nath_jr_yeti` | 6 | 전방 1칸 할퀴기, 피해 1. 기본 근접 적 |
| 페페 | `el_nath_pepe` | 4 | 전방 2칸 첫 대상에게 눈덩이, 피해 1·쿨 3턴. 사용 불가 시 전방 1칸 부리찍기, 피해 1 |
| 예티 | `el_nath_yeti` | 8 | 전방 2칸 지면 강타, 피해 2·1턴 예고·쿨 3턴. 이후 전방 1칸 내려치기, 피해 2 |
| 예티와 페페 | `el_nath_yeti_pepe` | 9 | 전방 1칸 강타, 피해 2. 처치하면 같은 칸에 HP 4 페페가 분리되어 등장 |
| 스노우맨 | `el_nath_snowman` | 36 | 보스. 주먹·냉기 돌풍·중단 가능한 눈보라를 순환 |

모두 플레이어 추적·최초 플레이어 방향 바라보기로 등록했다. HEAVY·AGGRO·QUICK 특성은 없다.
스킬의 `MotionProfileId=heavy_slash`는 연출 프로필 이름이며 HEAVY 특성과는 무관하다.

### 보스 상세

| 공격 | 범위 | 피해·효과 | 쿨타임 |
|---|---|---|---:|
| 주먹 | 전방 1칸 | 피해 2 | 0턴 |
| 냉기 돌풍 | 전방 1~2칸 | 피해 2 + 동상 1행동(이동 제한) | 3턴 |
| 눈보라 집중 | 보스 자신이 선 칸을 제외한 전 보드 | 피해 3. 캐스팅 중 유효한 스킬 피격 1타로 중단 가능 | 5턴 |

- 1페이즈: 주먹 → 냉기 돌풍 → 눈보라 캐스팅 → 눈보라 실행 → 대기.
- HP 50% 이하(기본 HP 18 이하) 2페이즈: 냉기 돌풍 → 주먹 → 눈보라 캐스팅/실행 → 대기.
- `CAST_INTERRUPTIBLE.ParamA=1`은 **중단에 필요한 타수**다. 충전 턴 수가 아니다.

## 2. 스테이지 편성

| 스테이지 | 웨이브 | 웨이브별 소환 수 | 주요 구성 |
|---|---:|---|---|
| 7-1 | 3 | 1 / 1 / 2 | 주니어 예티로 시작, 마지막은 주니어 예티·페페 혼합 |
| 7-2 | 4 | 1 / 1 / 2 / 2 | 페페 단독 웨이브 + 주니어 예티·페페 혼합 |
| 7-3 | 4 | 1 / 2 / 1 / 2 | 예티 단독 웨이브 2회 + 주니어 예티·페페 혼합 |
| 7-4 | 4 | 1 / 2 / 1 / 2 | 예티와 페페 2회 + 일반 적 3종 혼합 |
| 7-5 | 5 | 2 / 1 / 2 / 1 / 3 | 일반 적 3종 혼합 + 예티와 페페 2회 |
| 7-6 | 1 | 1 | 스노우맨 보스전, 추가 잡몹 없음 |

소환 수에는 탑승형 처치 후 분리되는 페페가 포함되지 않는다. 7-4/5는 각각 페페 2마리가 추가된다.
초반 혼합 풀은 주니어 예티:페페 = **3:1**, 후반 혼합 풀은 주니어 예티:페페:예티 = **1:1:1** 가중치다.
혼합 풀의 실제 출현 조합은 시드와 추첨 결과에 따라 달라진다.

일반전은 적이 1마리 남아도 다음 웨이브를 여는 `LONE_ENEMY` 방식이다.
7-1~2는 지연 시 7턴, 7-3~5는 6턴에 강제 소환을 시도하며 동시 적 상한은 각각 3/4마리다.
보스전은 `CLEAR_ONLY`이며 강제 지연 소환은 없다. 모든 전투는 7칸·기본 큐 3칸이다.

## 3. 어떻게 등록했나 / 어디서 수정하나

새 몬스터 전용 전투 AI를 따로 만들지 않고 기존 `BattleSession`·공통 적 큐·스킬 실행기를 재사용한다.
외형은 `RootDesk/MyDesk/Models/Monsters/ElNath*.model`로 분리했다.
아래 CSV는 모두 `RootDesk/MyDesk/03_Data/`에 있다.

| 수정할 내용 | 등록 파일·핵심 필드 |
|---|---|
| 적 이름·HP·특성·기본 모션 | `EnemyDefinitions`: `EnemyDefinitionId`, `MaxHp`, `TraitIds`, `PatternId`, 각 MotionRuid |
| 공격 순서·예고·캐스팅 중단 | `EnemyPatternSteps`: `PatternId`, `StepIndex`, `ActionType`, `TileId`, 성공/실패 다음 단계 |
| 공격 범위·쿨타임·아이콘·연출 | `EnemySkillDefinitions`: `SkillId`, `TargetingType`, `TargetOffsets`, `CooldownTurns`, `HudIconRuid`, `CasterMotionRuid`, 투사체·효과·사운드 필드 |
| 실제 피해·상태이상 | `SkillEffectSteps`: 스킬의 `EffectSetId`에 연결된 `DAMAGE.Value`, `FROSTBITE.ParameterA` 등 |
| 등장 후보·외형 모델·출현 비중 | `EnemySpawnPools`: `PoolId`, `EnemyDefinitionId`, `EnemyModelId`, `Weight` |
| 웨이브 수·마릿수·등장 시점 | `StageEnemyWaves`: `WaveTableId`, `EnemyPoolId`, `SpawnCount`, `SpawnTriggerMode`, `ForceAfterTurns`, `MaxConcurrent` |
| 보스 페이즈 전환 | `BossPhaseDefinitions`: `EnemyDefinitionId`, `HpRatioLE`, 해당 페이즈 `PatternId` |
| 스테이지·물리 맵 연결 | `StageDefinitions.WaveTableId`와 `StageMapRoutes.MapId` |

즉, 스테이지가 웨이브를 고르고 → 웨이브가 출현 풀을 고르고 → 풀이 적 정의와 외형 모델을 연결한다.
적 정의의 `PatternId`가 행동 순서를, 각 행동의 `TileId`가 사용할 공격 스킬을 지정한다.
공격 스킬의 `EffectSetId`가 실제 피해·상태 효과를 연결하므로 **공격 피해를 바꿀 때는 효과 표를 수정한다.**

## 4. 공통 동작과 분리 처리

- 스폰 직후 대기 → 스킬 장전 → 추적/방향 전환 → 범위 조건에 맞으면 실행하는 기존 규칙을 따른다.
  표의 패턴 순서가 각각 한 턴씩 고정된다는 뜻은 아니며 장전·이동·예고 등이 별도로 턴을 소비한다.
- 일반 공격의 `EnemyQueueTurns=1`을 등록했다. 눈보라의 값 0도 즉발 예외가 아니며 공통 최소 장전 규칙을 적용받는다.
- 탑승형의 `DeathSpawnEnemyDefinitionId=el_nath_pepe`, `DeathSpawnModelId=elnathpepe`를 읽어
  `EnemyDefeatSuccessorLogic`이 새 페페를 생성한다. 새 UnitId·빈 큐·스폰 대기로 시작하고, 페페까지 잡아야 끝난다.
- 아이콘·모션·이펙트는 CSV 연결이며, 피격/사망음은 `EnemyImpactPresentations`를 사용한다.
  특수 공격 전용 모션은 기존 `caster_motion` 태그로 우선 적용한다.

현재 다른 지역/상점/REST와의 캠페인 Node 연결은 하지 않았다. 공용 `battle_test_hub`에서 각각 진입한다.
상세 제작 방법은 [제작 가이드](El-Nath-Authoring-Guide.md), 실제 클리어 결과는
[밸런스 검증 보고서](El-Nath-Balance-Test-Report.md)를 참고한다.
