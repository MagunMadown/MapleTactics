# Stage 제작 가이드

클리어 보상은 Stage 행에 직접 넣지 않고
[`Stage-Reward-Authoring-Guide.md`](./Stage-Reward-Authoring-Guide.md)의
`StageRewardDefinitions`에 독립 행으로 작성한다. 따라서 밸런스 담당자가 Wave 구성과 보상
구성을 서로 충돌 없이 수정할 수 있다.

## 현재 적용 범위

Stage 진입은 다음 순서를 사용한다.

```text
StageId
→ StageDefinitionRepositoryLogic
→ RegionDefinitionRepositoryLogic
→ ContentValidatorLogic
→ BattleSessionComponent.LoadAndApplyStageDefinition
→ WaveTableId
→ StageWaveRepositoryLogic
```

`BattleSessionComponent`는 더 이상 `StageId`를 웨이브 테이블 ID로 가정하지 않는다.
보드 크기, Cell 간격, 플레이어 시작 Cell, 큐 용량도 Stage Definition에서 적용한다.

현재 `region_01_stage_01`은 `StageDefinitions.userdataset/.csv` 실제 Dataset에서 로드된다.
Repository의 compatibility fallback은 제거됐다. ID는 조회 키일 뿐이며 코드에서 숫자·Type·소속을
`match`, `find`, `sub`로 추출하지 않는다.

## 현재 부족 상태

Stage 개발 Gate는 열려 있다. 새 Stage는 기존 Dataset 페어의 CSV 행을 추가하고 Maker
Refresh 후 `source=DATASET`, Wave 참조, 시작·Victory를 검증한다. `.userdataset`
메타데이터는 새 Dataset을 만들 때만 Maker가 생성하며 기존 파일의 ID를 복제하지 않는다.

## StageDefinitions 스키마

| 열 | 타입 | 예시 | 규칙 |
|---|---|---|---|
| `SchemaVersion` | integer | `3` | 현재 지원 버전은 3 |
| `StageId` | string | `region_01_stage_01` | 변경하지 않는 고유 조회 ID |
| `RegionId` | string | `region_01` | `RegionDefinitions.RegionId` 참조 |
| `StageIndex` | integer | `1` | Region 안의 전투 순서, 1 이상 |
| `StageType` | enum | `NORMAL` | 현재 `NORMAL`, `BOSS` |
| `DisplayName` | string | `1-1` | 화면 표시 이름, 빈 문자열 금지 |
| `CellCount` | integer | `6` | 1 이상 |
| `CellStartX` | number | `-2.8` | Cell 0의 world X |
| `CellSpacing` | number | `1.12` | 0보다 커야 함 |
| `UnitY` | number | `0.12` | 유닛 배치 world Y |
| `PlayerStartCell` | integer | `2` | 0 이상, `CellCount` 미만 |
| `QueueCapacity` | integer | `3` | 1 이상 |
| `WaveTableId` | string | `region_01_stage_01_waves` | `StageEnemyWaves.WaveTableId`와 연결 |
| `StageRuleId` | string | 빈 문자열 | 공용 규칙이면 비움 |

현재 Stage 1 기준 행은 다음 값과 같다.

```csv
SchemaVersion,StageId,RegionId,StageIndex,StageType,DisplayName,CellCount,CellStartX,CellSpacing,UnitY,PlayerStartCell,QueueCapacity,WaveTableId,StageRuleId
3,region_01_stage_01,region_01,1,NORMAL,1-1,6,-2.8,1.12,0.12,2,3,region_01_stage_01_waves,
```

MSW 좌표는 world unit이며 `1 unit = 100 px` 기준이다. 화면 픽셀 값을 그대로 입력하지 않는다.

## 새 Stage 추가 순서

1. `RegionDefinitions`에 Region 행이 존재하는지 확인한다.
2. `StageDefinitions`에 고유 `StageId`, 명시적 `RegionId`, `StageIndex`, `StageType`을 추가한다.
3. `StageEnemyWaves`에 같은 `WaveTableId`를 가진 Wave 행을 추가한다.
4. 기존 `EnemySpawnPools`를 재사용하거나 새 Pool을 추가한다.
5. 새 적 규격이 필요할 때만 `EnemyDefinitions`를 추가한다.
6. 외부 화면에서 `BattleGatewayLogic.BeginBattle(...)` 또는 `RequestBeginBattle(...)`로
   `StageId`를 넘긴다.
7. Maker 로그에서 `[ContentValidation] region valid`, `[ContentValidation] stage valid`를 확인한다.
8. 시작 위치, 큐 용량, Wave 전환, Victory, Reset을 확인한다.

일반 Stage를 추가할 때 `BattleSessionComponent`에 Stage별 `if` 분기를 넣지 않는다.

현재 Region 1 전투 Stage는 다음처럼 분리돼 있다.

| Stage | Wave 수 | 기본 구성 |
|---|---:|---|
| `region_01_stage_01` | 2 | 근접 1 → 원거리 1 |
| `region_01_stage_02` | 2 | 근접/원거리 혼합, 최대 동시 2 |
| `region_01_stage_03` | 3 | 혼합 비중 증가, 마지막 Wave 2 |
| `region_01_stage_04` | 1 | 보스 1, `StageType=BOSS`, 2 Phase |

Node/REST 연결은 별도 제작 영역이다. Stage 행을 추가하는 작업에서 다른 팀이 소유한
`NodeDefinitions.NextNodeIds`나 REST/상점 Node를 임의로 변경하지 않는다.

보스 Stage 제작 규칙은 [Boss-Phase-Authoring-Guide.md](Boss-Phase-Authoring-Guide.md)를 따른다.

## 검증 실패

외부 호출 결과의 대표 Reason은 다음과 같다.

| Reason | DetailReason | 의미 |
|---|---|---|
| `STAGE_DEFINITION_NOT_FOUND` | 없음 | Stage 행과 호환 Definition이 없음 |
| `CONTENT_VALIDATION_FAILED` | `UNSUPPORTED_STAGE_SCHEMA` | 지원하지 않는 스키마 버전 |
| `CONTENT_VALIDATION_FAILED` | `REGION_REFERENCE_MISSING` | RegionDefinitions 참조가 없음 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_STAGE_INDEX` | StageIndex가 1 미만 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_STAGE_TYPE` | 지원하지 않는 StageType |
| `CONTENT_VALIDATION_FAILED` | `DUPLICATE_STAGE_INDEX_IN_REGION` | 같은 Region에 같은 StageIndex가 중복 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_CELL_COUNT` | Cell 수가 1 미만 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_PLAYER_START_CELL` | 시작 Cell이 보드 범위 밖 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_QUEUE_CAPACITY` | 큐 용량이 1 미만 |
| `CONTENT_VALIDATION_FAILED` | `WAVE_TABLE_NOT_FOUND` | 연결된 Wave가 없음 |
| `CONTENT_VALIDATION_FAILED` | `DATA_DUPLICATE_STAGE_ID` | 같은 StageId가 여러 행에 존재 |

UI는 `DetailReason`을 그대로 사용자 문구로 표시하지 않고 별도의 현지화 문구로 변환한다.

## 호환 상태

Stage와 Node의 prototype compatibility fallback은 제거됐다. 존재하지 않는 Stage는
`STAGE_DEFINITION_NOT_FOUND`로 거절하며 production Content ID 하드코딩을 다시 추가하지 않는다.
