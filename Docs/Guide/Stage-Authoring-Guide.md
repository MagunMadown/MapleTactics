# Stage 제작 가이드

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

현재 `stage01`은 기존 동작을 보존하기 위한 호환 Definition을 내장하고 있다.
Maker에서 `StageDefinitions` UserDataSet을 추가하면 Dataset 행이 호환 Definition보다
우선한다. `StageDefinitions.userdataset`과 원본 데이터 파일은 JSON을 직접 편집하지 않고
Maker의 UserDataSet 생성·가져오기 절차를 사용한다.

## 현재 부족 상태

현재 프로젝트에는 `StageDefinitions.userdataset`과 `StageDefinitions.csv` 페어가 없다.
따라서 `stage01`은 `StageDefinitionRepositoryLogic`의 compatibility fallback으로
동작하며 Stage 개발 Gate B는 닫혀 있다.

Stage 2 제작 전에 다음 순서를 먼저 완료한다.

1. Maker의 `RootDesk/MyDesk/03_Data/`에서 이름이 정확히 `StageDefinitions`인
   UserDataSet을 생성한다.
2. Maker가 생성한 `StageDefinitions.userdataset`과 `StageDefinitions.csv`가 같은
   폴더에 있는지 확인한다.
3. 아래 Stage 1 기준 CSV를 Maker Dataset 화면에서 입력하거나 가져온다.
4. Workspace Refresh 후 Play에서
   `[StageDefinition] loaded` 로그의 `stage=stage01`, `source=DATASET`을 확인한다.
5. Stage 1의 시작·Wave·Victory·Reset 회귀 테스트를 통과한다.
6. `AllowStage01CompatibilityFallback=false`로 바꾸고 존재하지 않는 Stage 실패도 확인한다.

`.userdataset` 메타데이터는 직접 JSON으로 편집하지 않는다. CSV는 실제 행 데이터
sidecar이지만 최초 페어와 열 정의는 Maker가 생성하도록 한다.

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
| `QueueCapacity` | integer | `2` | 1 이상 |
| `WaveTableId` | string | `stage01` | `StageEnemyWaves.StageId`와 연결 |
| `NextStageId` | string | 빈 문자열 | 마지막 Stage면 비움 |
| `StageRuleId` | string | 빈 문자열 | 공용 규칙이면 비움 |

현재 Stage 1 기준 행은 다음 값과 같다.

```csv
SchemaVersion,StageId,DisplayName,CellCount,CellStartX,CellSpacing,UnitY,PlayerStartCell,QueueCapacity,WaveTableId,NextStageId,StageRuleId
1,stage01,Stage 1,6,-2.8,1.12,0.12,2,2,stage01,,
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

UI는 `DetailReason`을 그대로 사용자 문구로 표시하지 않고 별도의 현지화 문구로 변환한다.

## 호환 Definition 제거 조건

다음 조건을 모두 통과한 뒤
`StageDefinitionRepositoryLogic.AllowStage01CompatibilityFallback`을 `false`로 바꾼다.

1. `StageDefinitions`에서 `stage01`이 정상 조회된다.
2. 로그의 Definition `source`가 `DATASET`이다.
3. Stage 1 전체 회귀 테스트가 통과한다.
4. 존재하지 않는 Stage가 `STAGE_DEFINITION_NOT_FOUND`로 거절된다.
