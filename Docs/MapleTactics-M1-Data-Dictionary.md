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

## 2. JobDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| JobId | string | O | 직업 고유 ID |
| NameKey | string | O | LocaleDataSet 키 |
| MaxHp | integer | O | 시작 최대 HP, 1 이상 |
| QueueSize | integer | O | 기본 큐 크기, 1~6 |
| StartingTileSetId | string | O | TileSetEntries의 세트 ID |
| PassiveId | string | - | 시작 패시브/증강 ID |
| JobTag | string | O | 증강 풀 필터 태그 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

## 3. TileSetEntries

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| TileSetId | string | O | 타일 세트 ID |
| Seq | integer | O | 지급 순서, 1부터 시작 |
| TileId | string | O | TileDefinitions 참조 |
| Count | integer | O | 지급 수량, 1 이상 |

기본 키: `(TileSetId, Seq)`는 유일해야 한다.

## 4. TileDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| TileId | string | O | 타일 고유 ID |
| NameKey | string | O | 표시 이름 Locale 키 |
| DescriptionKey | string | O | 설명 Locale 키 |
| Cooldown | integer | O | 기본 쿨다운, 0 이상 |
| TargetType | enum | O | 등록된 TargetType |
| RangeValue | integer | O | 타깃 규칙의 기본 범위 |
| FreePlay | boolean | O | 큐 등록 시 턴 미소비 여부 |
| QueueDuplicateAllowed | boolean | O | 같은 Runtime Tile 중복 등록 허용 |
| Tags | string | - | `tag_a|tag_b` 형식의 검색 태그 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

허용 TargetType M1: `SELF`, `FRONT_CELL`, `RANGE_OFFSETS`, `FIRST_ENEMY_FORWARD`.

## 5. TileEffects

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| TileId | string | O | TileDefinitions 참조 |
| Seq | integer | O | 타일 내부 실행 순서 |
| EffectType | enum | O | 등록된 EffectType |
| TargetTypeOverride | enum | - | 비어 있으면 TileDefinitions 값 사용 |
| Amount | number | - | 피해/회복/변경량 |
| Distance | integer | - | 이동/밀치기 거리 |
| StatusId | string | - | 상태 효과 참조 |
| DurationTurns | integer | - | 상태 지속 턴 |
| Priority | integer | O | 같은 이벤트 내 우선순위 |
| ParamA | string | - | 타입별 확장 값 |
| ParamB | string | - | 타입별 확장 값 |
| ParamC | string | - | 타입별 확장 값 |

허용 EffectType M1: `DAMAGE`, `PUSH`, `MOVE_SELF`, `TURN_TARGET`, `APPLY_STATUS`, `MODIFY_COOLDOWN`.

## 6. EnemyDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| EnemyId | string | O | 적 고유 ID |
| NameKey | string | O | Locale 키 |
| ModelId | string | O | spawn 가능한 프로젝트 model ID |
| MaxHp | integer | O | 최대 HP |
| PatternId | string | O | EnemyPatternSteps 참조 |
| TileSetId | string | - | 적이 사용할 타일 세트 |
| DefaultFacing | integer | O | `-1` 또는 `1` |
| IntentIconId | string | - | UI용 리소스/카탈로그 ID |
| Tags | string | - | 적 태그 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

## 7. EnemyPatternSteps

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| PatternId | string | O | 패턴 ID |
| StepIndex | integer | O | 실행 순서, 1 이상 |
| ActionType | enum | O | 등록된 EnemyActionType |
| ConditionType | enum | O | 실행 조건, 기본 ALWAYS |
| TileId | string | - | TELEGRAPH/EXECUTE_TILE에서 사용 |
| TelegraphTurns | integer | O | 준비 턴 수, 0 이상 |
| ParamA | string | - | 행동별 인자 |
| ParamB | string | - | 행동별 인자 |
| ParamC | string | - | 행동별 인자 |
| NextStepOnSuccess | integer | - | 비어 있으면 다음 StepIndex |
| NextStepOnFailure | integer | - | 비어 있으면 다음 StepIndex |

허용 ActionType M1: `WAIT`, `TURN_TO_PLAYER`, `MOVE_TOWARD`, `MOVE_AWAY`, `MOVE_FIXED_FACING`, `TELEGRAPH_TILE`, `EXECUTE_TILE`.

`MOVE_FIXED_FACING`은 플레이어 위치를 참조하지 않고 유닛의 현재 `Facing` 방향으로 1칸 이동한다. 패턴에 `TURN_TO_PLAYER`가 없으면 `DefaultFacing`이 끝까지 유지되어 한 방향 고정형 몬스터가 되고, 있으면 플레이어 위치를 따라 도는 추적형이 된다.

허용 ConditionType M1: `ALWAYS`, `DISTANCE_EQ`, `HP_RATIO_LE`, `CELL_FREE`.

## 8. StageDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| StageId | string | O | 스테이지 ID |
| NameKey | string | O | Locale 키 |
| BoardSize | integer | O | 1차원 셀 수, 3 이상 |
| OriginX | number | O | Cell 0의 월드 X |
| OriginY | number | O | 유닛 기준 월드 Y |
| CellWidth | number | O | 셀 간 월드 거리 |
| PlayerStartCell | integer | O | 0~BoardSize-1 |
| AugmentPoolId | string | O | StageAugmentPools 참조 |
| DifficultyMultiplier | number | O | 0보다 큼 |
| NextStageId | string | - | 마지막 스테이지면 비움 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

`OriginX/OriginY/CellWidth`는 월드 좌표 표현용이며 논리 판정에는 사용하지 않는다.

## 9. StageEnemySpawns

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| StageId | string | O | StageDefinitions 참조 |
| WaveIndex | integer | O | 몇 번째 웨이브 소속인지. `0`은 전투 시작과 동시 고정 배치 |
| SpawnOrder | integer | O | 같은 Wave 안 결정적 생성/행동 동률 순서 |
| EnemyId | string | O | EnemyDefinitions 참조 |
| CellIndex | integer | O | 스테이지 보드 범위 안 |
| Facing | integer | O | `-1` 또는 `1` |
| PatternOverrideId | string | - | 특정 배치만 패턴 교체 |
| HpMultiplier | number | O | 0보다 큼 |

같은 StageId·WaveIndex에서 CellIndex 중복 점유를 허용하지 않는다. `WaveIndex=0` 행은 플레이어 좌/우 양쪽 CellIndex에 모두 배치될 수 있다 — 기존 데이터는 전부 `WaveIndex=0`으로 채우면 하위호환된다.

## 10. EnemySpawnPools

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| PoolId | string | O | 스폰 후보 풀 ID |
| EnemyId | string | O | EnemyDefinitions 참조 |
| Weight | integer | O | 1 이상 |
| MinWaveIndex | integer | O | 최소 등장 웨이브 |
| MaxWaveIndex | integer | O | 최대 등장 웨이브 |

기본 키: `(PoolId, EnemyId)`는 유일해야 한다. `StageAugmentPools`와 동일한 가중치 후보 풀 구조를 재사용한다.

## 11. StageEnemyWaves

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| StageId | string | O | StageDefinitions 참조 |
| WaveIndex | integer | O | `1`부터 시작하는 후속 웨이브 순서 |
| TriggerType | enum | O | 웨이브 시작 조건 |
| EnemyPoolId | string | O | EnemySpawnPools 참조 |
| SpawnCount | integer | O | 이번 웨이브에 등장할 적 수 |
| MaxConcurrent | integer | O | 보드에 동시 존재 가능한 최대 적 수 |

허용 TriggerType M1: `ON_WAVE_CLEARED` (직전 WaveIndex의 모든 적이 죽으면 시작).

웨이브가 시작되면 그 시점의 빈 칸을 CellIndex 오름차순으로 모은 뒤 `RunSeed + StageIndex + WaveIndex` 기반 결정적 RNG로 `SpawnCount`개를 뽑는다. 플레이어가 서 있는 칸과 이미 점유된 칸은 후보에서 제외하며, 플레이어 좌/우 양쪽 칸이 모두 후보에 포함된다. `MaxConcurrent`를 넘는 스폰 요청은 빈 칸이 다시 생길 때까지 대기한다.

## 12. AugmentDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| AugmentId | string | O | 증강 ID |
| NameKey | string | O | Locale 키 |
| DescriptionKey | string | O | Locale 키 |
| Rarity | enum | O | COMMON, RARE, EPIC |
| StackPolicy | enum | O | UNIQUE, STACK_ADD, STACK_REFRESH, EXCLUSIVE_GROUP |
| MaxStacks | integer | O | 1 이상 |
| ExclusiveGroup | string | - | 배타 그룹 ID |
| JobTagFilter | string | - | 비어 있으면 모든 직업 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

## 13. AugmentEffects

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| AugmentId | string | O | AugmentDefinitions 참조 |
| Seq | integer | O | 증강 내부 순서 |
| TriggerType | enum | O | 반응할 BattleEvent 종류 |
| ConditionType | enum | O | 실행 조건 |
| EffectType | enum | O | 등록된 EffectType |
| TargetType | enum | O | 효과 대상 |
| Priority | integer | O | 이벤트 체인 우선순위 |
| Amount | number | - | 효과량 |
| ParamA | string | - | 확장 값 |
| ParamB | string | - | 확장 값 |
| ParamC | string | - | 확장 값 |

허용 TriggerType M1: `TURN_START`, `COMMAND_ACCEPTED`, `TILE_QUEUED`, `BEFORE_TILE_EXECUTE`, `AFTER_DAMAGE`, `UNIT_MOVED`, `ENEMY_DIED`, `STAGE_CLEARED`.

## 14. StageAugmentPools

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| PoolId | string | O | 후보 풀 ID |
| AugmentId | string | O | AugmentDefinitions 참조 |
| Weight | integer | O | 1 이상 |
| MinStageIndex | integer | O | 최소 등장 스테이지 |
| MaxStageIndex | integer | O | 최대 등장 스테이지 |
| RequiredJobTag | string | - | 직업 태그 조건 |

## 15. AugmentConflicts

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| AugmentId | string | O | 기준 증강 |
| ConflictAugmentId | string | O | 함께 보유할 수 없는 증강 |
| ReasonCode | string | O | UI/로그용 사유 코드 |

충돌은 방향과 무관하게 취급한다. Validator는 A->B만 있어도 B->A를 런타임 인덱스에 함께 등록한다.

## 16. Validator 오류 코드

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
| DATA_UNUSED_ROW | 어디에서도 참조되지 않는 활성 행 | X, 경고 |

로그 예시:

```text
[DATA_MISSING_REFERENCE] Dataset=TileEffects Row=7 Column=TileId Value=unknown_tile
```

## 17. 새 데이터 추가 완료 기준

- Maker에서 wrapper와 CSV가 한 쌍으로 인식된다.
- Runtime name이 로더에 등록된 이름과 일치한다.
- ContentValidator 차단 오류가 0개다.
- 고정 Seed 대표 시나리오에서 의도한 행이 로드되었다는 positive log가 있다.
- 새 원시 Type이 필요했다면 Router, Validator 허용 목록, 데이터 사전, 테스트를 함께 수정했다.
