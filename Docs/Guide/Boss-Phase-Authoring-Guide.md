# 보스 Phase 제작 가이드

보스도 일반 적과 같은 `EnemyDefinitions`, `EnemyPatternSteps`, `SkillDefinitions` 규격을 사용한다.
보스 ID별 코드를 Session에 추가하지 않고 `BossPhaseDefinitions`가 HP 구간·Pattern 교체·선택적 모션 교체를 선언한다.

## 데이터 흐름

```text
StageDefinitions(StageType=BOSS)
→ StageEnemyWaves(WaveTableId)
→ EnemySpawnPools
→ EnemyDefinitions(IsBoss=true)
→ BossPhaseDefinitions
→ EnemyPatternSteps
→ SkillDefinitions / SkillEffectSteps
```

## BossPhaseDefinitions 스키마

| 열 | 타입 | 규칙 |
|---|---|---|
| `SchemaVersion` | integer | 현재 `1` |
| `EnemyDefinitionId` | string | `IsBoss=true`인 Enemy 참조 |
| `PhaseIndex` | integer | 1부터 연속 |
| `PhaseId` | string | 같은 보스 안에서 유일 |
| `HpRatioLE` | number | `(0, 1]`, PhaseIndex가 커질수록 감소 |
| `PatternId` | string | 유효한 Enemy Pattern 참조 |
| `Enabled` | boolean | `true` 행만 사용 |
| `IdleMotionRuid` | string | 선택적 대기 모션. 빈 칸은 EnemyDefinitions 기본값 |
| `MoveMotionRuid` | string | 선택적 이동 모션. 빈 칸은 EnemyDefinitions 기본값 |
| `HitMotionRuid` | string | 선택적 피격 모션. 빈 칸은 EnemyDefinitions 기본값 |
| `DeathMotionRuid` | string | 선택적 사망 모션. 빈 칸은 EnemyDefinitions 기본값 |

모션 열은 SchemaVersion 1의 선택적 확장이다. 기존 행은 네 칸을 비워 기존 외형을 유지한다.
설정한 값은 32자리 16진수 RUID여야 한다. 빈 칸은 **이전 페이즈 값 유지가 아니라 원래 적 기본값 복원**이다.
공격별 모션·발사 이펙트는 계속 `EnemySkillDefinitions`가 소유한다.

첫 Phase는 `HpRatioLE=1.0`이어야 하며 `EnemyDefinitions.PatternId`와 같은 Pattern을 사용한다.
현재 예시는 다음과 같다.

```csv
1,region_01_guardian_boss,1,OPENING,1.0,region_01_boss_phase_01,true
1,region_01_guardian_boss,2,ENRAGED,0.5,region_01_boss_phase_02,true
```

## 실행 규칙

- Phase 상태는 적 Entity의 `BossPhaseStateComponent`가 소유한다.
- 피해 적용 후 HP가 임계값을 넘으면 다음 Pattern을 초기화한다.
- 경계값을 포함한다(`HP / MaxHP <= HpRatioLE`). 페이즈는 역행하지 않으며 회복 후에도 유지한다.
- 플레이어 턴 시작 때 이미 고정된 적 행동은 그대로 실행한다.
- Phase 전환 전에 고정된 옛 행동이 끝나면 옛 Pattern Step 진행만 `PATTERN_SUPERSEDED`로 폐기한다.
- 다음 플레이어 턴부터 새 Phase Pattern을 계획한다.
- 공격 타이밍은 각 `SkillDefinitions.ActionDuration`을 사용한다.
- 페이즈별 외형을 설정한 보스만 전환 시 이전 외형의 대기/피격 재생을 정리한다. 외형을 설정하지 않은 기존 보스의 모션·고정 공격 Queue 계약은 유지한다.

### 휴면 보스 예시: 6-4 포장마차

- 1페이즈: `WAIT` 한 행이 자기 자신으로 돌아간다. 휴면 `stand`를 대기·이동·피격에 지정해 맞을 때 활성 모습으로 튀지 않게 한다.
- 2페이즈: `HpRatioLE=0.999`로 설정해 HP 38의 첫 유효 피해(1 이상) 직후 공격 Pattern으로 교체하고, 모션 네 칸은 비워 활성 기본 모션으로 복원한다. 피해 0·빗나감에는 전환하지 않는다.
- 입장 잡몹은 StageEnemyWaves/EnemySpawnPools에서 함께 생성한다. 이후 페이즈별 보충은 아래 선택 설정으로 분리한다.

### 페이즈별 잡몹 보충

- `ReinforcementPoolId`: EnemySpawnPools 참조. 빈 칸이면 비활성화.
- `ReinforcementIntervalTurns`: 보충 간격(양의 정수). 페이즈 진입 후 이만큼의 턴이 지난 뒤 첫 보충을 시도한다.
- `ReinforcementMaxAlive`: 최초 등장 잡몹을 포함한 살아 있는 일반 적 상한(1~4).
- 매 라운드 종료 경계에서만 시도하며 성공 시 다음 보충 턴을 갱신한다. 상한/빈 칸 부족 시 다음 턴에 재시도한다. 전투 종료·보스 사망·보충 없는 페이즈로 전환 시 중단한다.
- 포장마차 DORMANT는 `region_06_food_cart_adds / 2 / 2`, DINNER_RUSH는 비활성화다. 기존 잡몹은 페이즈 전환 시 남고, 신규 잡몹도 공통 SpawnWaveEnemy와 SPAWN_WAIT 경로를 사용한다.

## 중단 가능한 캐스팅

`CAST_INTERRUPTIBLE`은 보스 ID를 코드에 분기하지 않는 공용 Pattern Action이다.

```csv
1,region_05_king_clang_phase_01,3,CAST_INTERRUPTIBLE,ALWAYS,nautilus_king_clang_bubble_cannon,0,1,,,4,5,true
1,region_05_king_clang_phase_01,4,EXECUTE_TILE,ALWAYS,nautilus_king_clang_bubble_cannon,0,,,,6,5,true
```

- `TileId`: 캐스팅 후 실행할 `EnemySkillDefinitions.SkillId`
- `ParamA`: 캐스팅을 끊는 데 필요한 플레이어 피해 스킬 적중 횟수(1 이상)
- `NextStepOnSuccess`: 같은 `TileId`의 `EXECUTE_TILE` 행
- `EXECUTE_TILE.NextStepOnFailure`: 중단됐을 때 이동할 경직·대기 행
- 같은 큐 타일 실행 안의 여러 `DAMAGE` Effect 행은 중단 횟수 1회로 센다.
- 피해가 0이거나 적중하지 않은 이동·회전·밀치기만으로는 캐스팅이 끊기지 않는다.
- `CAST_INTERRUPTED`가 되면 해당 스킬의 바닥 범위 예고를 즉시 숨긴다. 큐 아이콘과 `중단!` 표시는 행동이 정리될 때까지 남기되, 중단 상태를 소비하는 중간 스냅샷에서 범위가 다시 나타나서는 안 된다. 이 규칙은 모든 `CAST_INTERRUPTIBLE` 패턴에 공통 적용된다.
- 2 Phase처럼 `ParamA=2`로 올리면 한 플레이어 큐 안에서 서로 다른 두 스킬 실행을 맞혀야 끊을 수 있다.

Validator는 캐스팅 Skill 참조, `ParamA >= 1`, 다음 성공 Step의 `EXECUTE_TILE` 및 동일 Skill 연결을 검사한다.

## UI 계약

`GetBattleUiState().EnemyIntents[]`는 다음 값을 제공한다.

- `BossPhaseId`
- `BossPhaseIndex`
- `BossPhaseRevision`
- 현재 고정 행동의 `PatternId`, `CommandType`, `TileId`, `TelegraphTurnsRemaining`
- `CastState` (`NONE`/`CASTING`/`INTERRUPTED`)
- `CastingSkillId`, `InterruptHitsRequired`, `InterruptHitsReceived`, `IsCastInterrupted`

Phase가 바뀌어도 현재 고정 행동의 PatternId는 옛 Pattern일 수 있다. 이는 오류가 아니라
플레이어가 이미 확인한 적 Queue를 바꾸지 않기 위한 규칙이다.

## Region 01 Stage 1-4 머쉬맘 예시

`region_01_stage_04`는 이 규격을 사용하는 첫 실제 보스 스테이지다.

| 구분 | 설정 |
|---|---|
| Stage | `region_01_stage_04`, `StageType=BOSS`, 1 Wave |
| Enemy | `region_01_guardian_boss`, HP 18, `IsBoss=true` |
| Model | `region01mushmomboss` |
| Phase 1 | `OPENING`, `region_01_boss_phase_01` |
| Phase 2 | HP 50% 이하 `ENRAGED`, `region_01_boss_phase_02` |
| 기본 공격 | `boss_basic_strike`, 전방 1칸, 피해 2 |
| 점프 착지 | `boss_jump_slam`, 전방 1~2칸, 피해 3, 쿨타임 2턴 |
| 밀치기 | `boss_push_strike`, 전방 1칸, 피해 2 + 1칸 밀치기 |
| 처치 드롭 | 골드 5~7, 소형 회복 물약 1개 |

모션·이펙트·Queue 아이콘은 `EnemySkillDefinitions`에서 교체한다. 디자인 담당자는 전투 코드를 수정하지 않고 각 RUID와 크기·재생 속도만 바꿀 수 있다.

현재 `boss_jump_slam`은 기존 `RANGE_OFFSETS`와 적 Queue 규격을 재사용하여 공격 실행 시점의 전방 1~2칸을 판정한다. 예고 시 선택한 특정 셀을 끝까지 잠그고 보스 Entity 자체가 그 셀로 점프하는 연출은 별도 Target Lock/Jump 이동 Action이 추가될 때 확장한다.

## Region Kerning City Stage 2-4 다일 예시

`region_kerning_stage_04`는 커닝시티 Region의 보스 스테이지다. 물리 맵은 `kerning_city_boss`이며
일반전 `kerning_city_battle`과 같은 `BattleCell1~6` 계약을 공유한다.

| 구분 | 설정 |
|---|---|
| Stage | `region_kerning_stage_04`, `StageType=BOSS`, 1 Wave (`CLEAR_ONLY`) |
| Enemy | `region_kerning_dyle`, HP 32, `IsBoss=true` |
| Model | `kerningdyle` |
| Phase 1 | `OPENING`, `region_kerning_dyle_phase_01` |
| Phase 2 | HP 50% 이하 `ENRAGED`, `region_kerning_dyle_phase_02` |
| 기본 공격 | `region_kerning_dyle_bite`, 전방 1칸, 피해는 `BasicAttackDamage=3` |
| 예고 광역 | `region_kerning_dyle_tail_sweep`, 1턴 예고 후 전방 1~2칸, 피해 3 |
| 격노 광역 | `region_kerning_dyle_tail_sweep_enraged`, 1턴 예고 후 전방 1~2칸, 피해 4 |
| 증원 소환 | 양 페이즈 패턴 마지막 단계 `SUMMON_ENEMIES`. 모델의 `FaustSummonComponent`가 `region_kerning_swamp_mud_pool` 3개로 늪진흙괴물 3마리를 소환(`RequireEmptyBoard=true`, `SummonCooldownTurns=5`). 소환수가 모두 쓰러져 보스만 남았을 때만 다시 소환하며, 보스 처치 시 소환수는 함께 제거된다 |
| 처치 드롭 | 골드 6~7, 소형 회복 물약 1개 |

2026-09-27부터 Phase 2 전환 증원(리게이터 2마리, `BOSS_PHASE` Wave)은 제거하고 다일의 소환 스킬로 대체했다.
소환은 스켈레톤 지휘관과 같은 `FaustSummonComponent` 경로를 쓰므로 Session에 보스별 조건문을 추가하지 않았다.

Phase 전환에 직접 연동되는 증원이 필요한 보스는 여전히
[Battle-Wave-Guide.md §5.1](./Battle-Wave-Guide.md)의 `BOSS_PHASE` 트리거를 `StageEnemyWaves` 행에 선언해 사용한다.

## Region 06 슬리피우드 Stage 6-8 주니어 발록 예시

`region_06_stage_08`은 슬리피우드 후반전(신전)의 보스 스테이지다. 물리 맵은 `sleepywood_temple_boss`이며
리소스 팩의 공격 3종을 모두 스킬로 사용한다. 증원은 없다.

| 구분 | 설정 |
|---|---|
| Stage | `region_06_stage_08`, `StageType=BOSS`, 1 Wave (`CLEAR_ONLY`), Pool `region_06_stage_08_boss_pool` |
| Enemy | `region_06_jr_balrog`, HP 36, `BasicAttackDamage=5`, `IsBoss=true` |
| Model | `region06jrbalrog` (`Scale=1.2`, 화염구 `ProjectileHeight=1.2`) |
| 할퀴기 (`attack1`) | `region_06_jr_balrog_claw`, 전방 1칸, 피해는 `BasicAttackDamage=5` |
| 화염구 (`attack2`) | `region_06_jr_balrog_fireball`, 전방 3칸 안 첫 적에게 `info/ball` 투사체, 피해 4, 쿨타임 2 |
| 불꽃 휩쓸기 (`attack3`) | `region_06_jr_balrog_flame_sweep`, 1턴 예고 후 전방 1~3칸, 피해 6 |
| 격노 휩쓸기 | `region_06_jr_balrog_flame_sweep_enraged`, 1턴 예고 후 전방 1~3칸, 피해 7 |
| Phase 1 | `OPENING`: 할퀴기 → 화염구 → 대기 → 휩쓸기 예고 → 실행 → 대기 |
| Phase 2 | HP 50% 이하 `ENRAGED`: 격노 휩쓸기 예고 → 실행 → 화염구 → 할퀴기 → 대기 |
| 처치 드롭 | 골드 8~10, 하얀 포션 1개 |

화염구는 적 스킬 최초의 투사체 사용 사례다. 투사체 연출은 플레이어 스킬과 같은
`LaunchSkillProjectile` 경로를 쓰며, 조준 셀은 `_SkillTargetResolverLogic`이 정한다.
각 공격의 `attackN/info/effect`는 `CastEffectRuid`, `attackN/info/hit`는 `HitEffectRuid`에 넣는다.

## 검증 체크리스트

1. 전체 Validator에서 `bossPhaseOwners`가 증가한다.
2. 생성 로그에 `OPENING`, `index=1`, `hpRatio=1.0`이 남는다.
3. 임계 HP에서 `ENRAGED`, `index=2`로 한 번만 전환된다.
4. 이전 계획 완료는 오류가 아니라 `PATTERN_SUPERSEDED`로 기록된다.
5. 새 턴의 EnemyIntent가 Phase 2 Pattern을 사용한다.
6. 예고 행동 뒤 실제 스킬이 실행되고 피해가 적용된다.
7. Build/Runtime Warning·Error가 0인지 확인한다.
8. 캐스팅 중 필요한 횟수만큼 피해 스킬을 맞히면 공격 대신 실패 분기 `WAIT`가 실행된다.
