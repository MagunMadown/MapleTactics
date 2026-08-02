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
→ ContentValidatorLogic
→ BattleSessionComponent.LoadAndApplyStageDefinition
→ WaveTableId
→ StageWaveRepositoryLogic
```

`BattleSessionComponent`는 더 이상 `StageId`를 웨이브 테이블 ID로 가정하지 않는다.
보드 크기, Cell 간격, 플레이어 시작 Cell, 큐 용량도 Stage Definition에서 적용한다.

현재 `stage01`은 `StageDefinitions.userdataset/.csv` 실제 Dataset에서 로드된다.
Repository의 compatibility fallback은 비활성이다.

## 현재 부족 상태

Stage 개발 Gate는 열려 있다. 새 Stage는 기존 Dataset 페어의 CSV 행을 추가하고 Maker
Refresh 후 `source=DATASET`, Wave 참조, 시작·Victory를 검증한다. `.userdataset`
메타데이터는 새 Dataset을 만들 때만 Maker가 생성하며 기존 파일의 ID를 복제하지 않는다.

## StageDefinitions 스키마

| 열 | 타입 | 예시 | 규칙 |
|---|---|---|---|
| `SchemaVersion` | integer | `1` | 현재 지원 버전은 1 |
| `StageId` | string | `stage01` | 고유한 `lower_snake_case` ID |
| `DisplayName` | string | `Stage 1` | 빈 문자열 금지 |
| `CellCount` | integer | `6` | 1 이상 |
| `CellStartX` | number | `-2.8` | Cell 0의 world X |
| `CellSpacing` | number | `1.12` | 0보다 커야 함 |
| `UnitY` | number | `0.12` | 유닛 배치 world Y |
| `PlayerStartCell` | integer | `2` | 0 이상, `CellCount` 미만 |
| `QueueCapacity` | integer | `3` | 1 이상 |
| `WaveTableId` | string | `stage01` | `StageEnemyWaves.StageId`와 연결 |
| `NextStageId` | string | 빈 문자열 | 마지막 Stage면 비움 |
| `StageRuleId` | string | 빈 문자열 | 공용 규칙이면 비움 |

현재 Stage 1 기준 행은 다음 값과 같다.

```csv
SchemaVersion,StageId,DisplayName,CellCount,CellStartX,CellSpacing,UnitY,PlayerStartCell,QueueCapacity,WaveTableId,NextStageId,StageRuleId
1,stage01,Stage 1,6,-2.8,1.12,0.12,2,3,stage01,,
```

MSW 좌표는 world unit이며 `1 unit = 100 px` 기준이다. 화면 픽셀 값을 그대로 입력하지 않는다.

## 새 Stage 추가 순서

1. `StageDefinitions`에 고유 `StageId` 행을 추가한다.
2. `StageEnemyWaves`에 `WaveTableId`와 같은 `StageId`를 가진 Wave 행을 추가한다.
3. 기존 `EnemySpawnPools`를 재사용하거나 새 Pool을 추가한다.
4. 새 적 규격이 필요할 때만 `EnemyDefinitions`를 추가한다.
5. 외부 화면에서 `BattleGatewayLogic.BeginBattle(...)` 또는 `RequestBeginBattle(...)`로
   `StageId`를 넘긴다.
6. Maker 로그에서 `[ContentValidation] stage valid`를 확인한다.
7. 시작 위치, 큐 용량, Wave 전환, Victory, Reset을 확인한다.

일반 Stage를 추가할 때 `BattleSessionComponent`에 Stage별 `if` 분기를 넣지 않는다.

## 검증 실패

외부 호출 결과의 대표 Reason은 다음과 같다.

| Reason | DetailReason | 의미 |
|---|---|---|
| `STAGE_DEFINITION_NOT_FOUND` | 없음 | Stage 행과 호환 Definition이 없음 |
| `CONTENT_VALIDATION_FAILED` | `UNSUPPORTED_STAGE_SCHEMA` | 지원하지 않는 스키마 버전 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_CELL_COUNT` | Cell 수가 1 미만 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_PLAYER_START_CELL` | 시작 Cell이 보드 범위 밖 |
| `CONTENT_VALIDATION_FAILED` | `INVALID_QUEUE_CAPACITY` | 큐 용량이 1 미만 |
| `CONTENT_VALIDATION_FAILED` | `WAVE_TABLE_NOT_FOUND` | 연결된 Wave가 없음 |
| `CONTENT_VALIDATION_FAILED` | `NEXT_STAGE_SELF_REFERENCE` | 다음 Stage가 자기 자신 |
| `CONTENT_VALIDATION_FAILED` | `DATA_DUPLICATE_STAGE_ID` | 같은 StageId가 여러 행에 존재 |

UI는 `DetailReason`을 그대로 사용자 문구로 표시하지 않고 별도의 현지화 문구로 변환한다.

## 호환 상태

`AllowStage01CompatibilityFallback=false` 전환이 완료됐다. 존재하지 않는 Stage는
`STAGE_DEFINITION_NOT_FOUND`로 거절하며 production Stage 하드코딩을 다시 추가하지 않는다.
