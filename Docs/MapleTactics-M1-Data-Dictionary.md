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
| EnemyDefinitionId | string | O | 적 전투 정의 고유 ID |
| DisplayName | string | O | 제작자용 표시 이름 |
| MaxHp | integer | O | 최대 HP |
| BasicAttackDamage | number | O | 기본 공격 피해 |
| PatternId | string | O | EnemyPatternSteps 참조 |
| MovementPolicy | enum | O | 추적 이동 또는 현재 방향 고정 이동 |
| InitialFacingPolicy | enum | O | 생성 순간 한 번만 결정되는 초기 방향 |

허용 MovementPolicy M1: `TRACK_PLAYER`, `FIXED_FACING`.

허용 InitialFacingPolicy M1: `FACE_PLAYER`(생성 시 플레이어를 바라보는 방향으로 결정), `FIXED_LEFT`(항상 왼쪽), `FIXED_RIGHT`(항상 오른쪽). 기본값은 `FACE_PLAYER`. `MovementPolicy`가 전투 중 계속 갱신되는 이동/추적 규칙인 것과 달리, `InitialFacingPolicy`는 스폰 순간에만 한 번 적용되고 이후에는 Pattern Action(§7)만 방향을 바꾼다. `StageEnemySpawns.FacingOverride`(§11)가 비어 있을 때, 그리고 `StageEnemyWaves`(§13)의 웨이브 스폰 시 이 값을 읽는다.

적의 실제 `EnemyModelId`는 외형·컴포넌트 템플릿의 배치 책임이므로 `EnemySpawnPools`에서 연결한다.
Repository가 이 행을 검증·변환하고, Spawn 시 각 `BattleUnitComponent`에 HP·공격력·패턴·이동 정책을 복사한다.
따라서 서로 다른 정의의 적이 같은 보드에 동시에 살아 있어도 세션 공용 값에 서로 덮어쓰지 않는다.

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

- `TURN_TO_PLAYER`: 현재 CellIndex는 유지하고 플레이어 방향으로 `Facing`만 바꾼다.
- `MOVE_TOWARD`: 플레이어 방향으로 `Facing`을 바꾼 뒤 그 방향으로 1칸 이동한다.
- `MOVE_AWAY`: 플레이어 반대 방향으로 `Facing`을 바꾼 뒤 그 방향으로 1칸 이동한다.
- `MOVE_FIXED_FACING`: 플레이어 위치를 참조하거나 `Facing`을 바꾸지 않고 현재 방향으로 1칸 이동한다.
- 이동 목적지가 보드 밖이거나 점유된 경우 위치와 `Facing`을 유지하고 성공 분기는 `WAIT` 결과로 끝낸다. 자동 반전은 허용하지 않는다.

추적형/고정형은 Pattern 전체에 `TURN_TO_PLAYER`가 있는지로 판정하지 않는다. 각 Step의 Action 의미가 독립적이며 하나의 Pattern에서 추적 Action과 고정 방향 Action을 함께 사용할 수 있다.

허용 ConditionType M1: `ALWAYS`, `DISTANCE_EQ`, `HP_RATIO_LE`, `CELL_FREE`.

### 7.1 런타임 PreparedIntent 계약

`EnemyPatternSteps`는 정적 원본이고, 전투 중에는 선택된 한 행을 읽기 전용 `PreparedIntent` Snapshot으로 변환한다. Snapshot은 별도 Dataset이 아니며 저장/동기화 목적의 런타임 값이다.

| 필드 | 원본/생성 규칙 | 실행 중 변경 |
|---|---|:---:|
| EnemyDefinitionId | 실행 유닛 | 불가 |
| PatternId | EnemyDefinitions 또는 PatternOverrideId | 불가 |
| StepIndex | 선택된 EnemyPatternSteps 행 | 불가 |
| ActionType | 선택된 행 | 불가 |
| TileId | 선택된 행 | 불가 |
| TelegraphTurnsRemaining | TelegraphTurns에서 시작 | Tick 때만 감소 |
| PreparedTurn | 준비 시 TurnNumber | 불가 |
| State | EMPTY/PREPARED/EXECUTING | 상태 전이만 허용 |

- Snapshot에는 `TargetId`나 목표 CellIndex를 저장하지 않는다.
- `EXECUTE_TILE`은 실행 시점의 현재 CellIndex/Facing과 `TileDefinitions.TargetType`으로 타깃을 다시 계산한다.
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

## 9. RegionDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| RegionId | string | O | 지역 고유 ID (예: `henesys`) |
| DisplayName | string | O | 표시 이름 (예: 헤네시스) |
| NodeGraphId | string | O | NodeDefinitions 참조 |
| MonsterPoolId | string | O | 이 지역 일반 전투에서 쓰는 EnemySpawnPools 참조 |
| BossStageId | string | O | 지역 보스 전투(StageDefinitions) 참조 |
| UnlockRegionId | string | - | 비어 있으면 처음부터 열림. 값이 있으면 그 지역의 `BossStageId` 클리어 후 열림 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

기본 키: `RegionId` 유일.

예시:

| RegionId | DisplayName | NodeGraphId | MonsterPoolId | BossStageId | UnlockRegionId |
|---|---|---|---|---|---|
| henesys | 헤네시스 | henesys_graph | henesys_common | henesys_boss_mushmom | |
| ellinia | 엘리니아 | ellinia_graph | ellinia_common | ellinia_boss_dollmaster | henesys |
| sleepywood | 슬리피우드 | sleepywood_graph | sleepywood_common | sleepywood_boss_balrog | ellinia |

## 10. NodeDefinitions

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| NodeGraphId | string | O | RegionDefinitions.NodeGraphId 참조 |
| NodeId | string | O | 노드 고유 ID |
| NodeType | enum | O | 등록된 NodeType |
| StageId | string | - | `BATTLE`/`BOSS`에서 StageDefinitions 참조, 그 외 타입은 비움 |
| IsStartNode | boolean | O | 이 NodeGraph에서 지도판 진입 시 처음 여는 노드인지 |
| NextNodeIds | string | - | `\|` 구분 다음 노드 ID 목록 |
| PositionX | number | O | 지도판 표시 X (월드 좌표 아님, UI 배치용) |
| PositionY | number | O | 지도판 표시 Y |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

허용 NodeType M1: `BATTLE`, `SHOP`, `EVENT`, `REST`, `BOSS`.

기본 키: `(NodeGraphId, NodeId)` 유일. 같은 NodeGraphId 안에 `IsStartNode=true`가 정확히 1개여야 한다. `NextNodeIds`가 참조하는 NodeId는 같은 NodeGraphId 안에 존재해야 한다.

예시(`henesys_graph`, 회의 문서의 "헤네시스 1-1/1-2/1-3" 배치를 노드 3개로 표현):

| NodeGraphId | NodeId | NodeType | StageId | IsStartNode | NextNodeIds |
|---|---|---|---|---|---|
| henesys_graph | n1 | BATTLE | henesys_1_1 | true | n2 |
| henesys_graph | n2 | BATTLE | henesys_1_2 | false | n3 |
| henesys_graph | n3 | BOSS | henesys_boss_mushmom | false | |

상점/이벤트 노드가 필요하면 같은 그래프에 `NodeType=SHOP`, `StageId`는 비운 행을 추가한다.

## 11. StageEnemySpawns

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| StageId | string | O | StageDefinitions 참조 |
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
| StageId | string | O | StageDefinitions 참조 |
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
| AugmentId | string | O | 증강 ID |
| NameKey | string | O | Locale 키 |
| DescriptionKey | string | O | Locale 키 |
| Rarity | enum | O | COMMON, RARE, EPIC |
| StackPolicy | enum | O | UNIQUE, STACK_ADD, STACK_REFRESH, EXCLUSIVE_GROUP |
| MaxStacks | integer | O | 1 이상 |
| ExclusiveGroup | string | - | 배타 그룹 ID |
| JobTagFilter | string | - | 비어 있으면 모든 직업 |
| Enabled | boolean | O | 콘텐츠 활성 여부 |

## 15. AugmentEffects

| 열 | 타입 | 필수 | 설명 |
|---|---|:---:|---|
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

허용 TriggerType M1: `TURN_START`, `COMMAND_ACCEPTED`, `TILE_QUEUED`, `BEFORE_TILE_EXECUTE`, `AFTER_DAMAGE`, `UNIT_MOVED`, `ENEMY_DIED`, `STAGE_CLEARED`.

허용 ConditionType M1: `ALWAYS`, `CHANCE_ROLL`(`ConditionValue`=성공 확률, RunSeed 기반 결정적 롤).

허용 TargetType M1: 타일과 같은 `SELF`, `FRONT_CELL`, `RANGE_OFFSETS`, `FIRST_ENEMY_FORWARD`에 `REAR_CELL`(현재 Facing 반대편 바로 뒤 칸)을 추가한다.

`REAR_CELL`은 이번에 새로 추가하는 원시 TargetType이므로 §22(새 데이터 추가 완료 기준)의 "새 원시 Type" 규칙에 따라 Resolver·Validator 허용 목록·회귀 테스트를 함께 갖춘 뒤에만 실전 배치한다.

### 15.1 예시 — 자쿰의투구 (50% 확률 후방 공격)

`AugmentDefinitions` 행:

| AugmentId | NameKey | Rarity | StackPolicy | MaxStacks |
|---|---|---|---|---|
| zakum_helmet | augment.zakum_helmet.name | RARE | UNIQUE | 1 |

`AugmentEffects` 행:

| AugmentId | Seq | TriggerType | ConditionType | ConditionValue | EffectType | TargetType | Amount |
|---|---|---|---|---|---|---|---|
| zakum_helmet | 1 | AFTER_DAMAGE | CHANCE_ROLL | 0.5 | DAMAGE | REAR_CELL | 1.0 |

읽는 법: 플레이어의 공격이 적중(`AFTER_DAMAGE`)할 때마다 50%(`CHANCE_ROLL 0.5`) 확률로, 방금 공격과 같은 피해량 배율(`Amount 1.0`)의 피해를 후방 칸(`REAR_CELL`)에 추가로 적용한다.

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

## 20. ShopItemDefinitions

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

허용 Category M1: `CONSUMABLE`(소모품), `STARTER_RELIC`(시작 유물), `SKILL_UNLOCK`(스킬 해금), `PERMANENT_UPGRADE`(영구 성장), `COSMETIC`(외형), `CHARACTER_UNLOCK`(캐릭터/직업 해금).

허용 EffectRefType M1: `AUGMENT`(AugmentDefinitions 참조), `SKILL`(SkillDefinitions 참조), `JOB`(JobDefinitions 참조), 없으면 비움.

재화 분류(런 소모/메타 영구/캐시)는 `CurrencyDefinitions`(§18)에서 관리한다.

기본 키: `ItemId` 유일. `Category=CHARACTER_UNLOCK`이면 `EffectRefType=JOB`이어야 한다.

예시:

| ItemId | DisplayName | Category | CurrencyId | Price | EffectRefType | EffectRefId |
|---|---|---|---|---|---|---|
| relic_zakum_helmet | 자쿰의 투구 | STARTER_RELIC | cash | 4900 | AUGMENT | zakum_helmet |
| unlock_job_thief | 도적 해금 | CHARACTER_UNLOCK | cash | 9900 | JOB | thief |
| potion_hp_small | 체력 물약(소) | CONSUMABLE | gold | 50 | | |

## 21. Validator 오류 코드

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
| DATA_INVALID_CHARACTER_UNLOCK_REF | ShopItemDefinitions의 Category=CHARACTER_UNLOCK인데 EffectRefType이 JOB이 아님 | O |
| DATA_REWARD_CURRENCY_NOT_ALLOWED | StageRewardDefinitions가 Category=PREMIUM_CASH인 CurrencyId를 참조 | O |
| DATA_UNUSED_ROW | 어디에서도 참조되지 않는 활성 행 | X, 경고 |

로그 예시:

```text
[DATA_MISSING_REFERENCE] Dataset=TileEffects Row=7 Column=TileId Value=unknown_tile
```

## 22. 새 데이터 추가 완료 기준

- Maker에서 wrapper와 CSV가 한 쌍으로 인식된다.
- Runtime name이 로더에 등록된 이름과 일치한다.
- ContentValidator 차단 오류가 0개다.
- 고정 Seed 대표 시나리오에서 의도한 행이 로드되었다는 positive log가 있다.
- 새 원시 Type이 필요했다면 Router, Validator 허용 목록, 데이터 사전, 테스트를 함께 수정했다.
