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

| Stage | 물리 맵 | Wave 수 | 기본 구성 |
|---|---|---:|---|
| `region_01_stage_01` | `region_01_battle` | 3 | 총 3마리. 근접 적만 등장해 기본 전투를 학습 |
| `region_01_stage_02` | `region_01_battle` | 3 | 총 5마리. 근접 중심, 스포아 가중치 1/4, 최대 동시 2 |
| `region_01_stage_03` | `region_01_battle` | 4 | 총 6마리. 스포아 가중치 1/3, 후반 Wave는 2마리 |
| `region_01_stage_04` | `region_01_boss` | 1 | 보스 1, `StageType=BOSS`, 2 Phase |

스포아는 1-2부터 `region_01_spore_ranged` Enemy Definition으로 등장한다. 사거리는 2칸,
기본 피해는 1, HP는 2다. 모든 직업의 기본 시작 공격 피해가 2 이상이므로 초반에는 스킬
한 번으로 처치할 수 있다. `EnemySpawnPools.Weight`를 낮게 두어 원거리 압박이 과해지지 않게 한다.

커닝시티(`region_Kerning_City`) 전투 Stage는 다음처럼 분리돼 있다.

| Stage | 물리 맵 | Wave 수 | 기본 구성 |
|---|---|---:|---|
| `region_kerning_stage_01` | `kerning_city_battle` | 3 | 스티지 5 (2+2+1) |
| `region_kerning_stage_02` | `kerning_city_battle` | 3 | 스티지 2 → 주니어 레이스 2 → 레이스 1 |
| `region_kerning_stage_03` | `kerning_city_battle` | 3 | 주니어 레이스 2 → 레이스 2 → 레이스 1 |
| `region_kerning_stage_04` | `kerning_city_boss` | 2 | 보스 다일 1, `StageType=BOSS`, Phase 2 전환 시 리게이터 2 증원 |

일반 3단계는 Wave당 최대 2마리씩 `TURN_LIMIT`(3턴)으로 나누어 투입하고 `MaxConcurrent=2`로
동시 등장을 제한한다. 마릿수를 정확히 맞춰야 하므로 가중치 혼합 Pool 대신 **적 1종만 담은
전용 Pool**(`region_kerning_stirge_pool` / `_jr_wraith_pool` / `_wraith_pool`)을 Wave별로 지정한다.
가중치 Pool은 어떤 적이 몇 마리 나올지 보장하지 못한다.

커닝시티 적은 모두 전용 `EnemyDefinitions`와 `RootDesk/MyDesk/Models/Monsters/Kerning*.model`을
사용하며 헤네시스 적을 재사용하지 않는다. 보스 규칙은
[Boss-Phase-Authoring-Guide.md](Boss-Phase-Authoring-Guide.md)를 따른다.

Node/REST 연결은 별도 제작 영역이다. Stage 행을 추가하는 작업에서 다른 팀이 소유한
`NodeDefinitions.NextNodeIds`나 REST/상점 Node를 임의로 변경하지 않는다.

현재 통합 흐름은 `1-1 → REST → 1-2 → REST → 1-3 → REST → 1-4 BOSS → REST`다.
`StageMapRoutes`는 1-1~1-3을 일반전 공용 `region_01_battle`로 라우팅하고,
`region_01_stage_04`만 `region_01_boss`로 라우팅한다. 두 맵은 같은 전투 컴포넌트와
`BattleCell1~6` 계약을 유지하므로 Battle Gateway는 물리 맵에 분기를 두지 않고 전달한
StageId로 해당 Stage·Wave 데이터를 시작한다.

## 물리 맵과 장식 교체 규칙

- 일반전 장식은 `region_01_battle.map`, 보스전 장식은 `region_01_boss.map`에서 관리한다.
- 장식 이미지는 맵 엔티티에 직접 하드코딩하지 않고 `RootDesk/MyDesk/Models/Objects/`의
  `Henesys*`, `MushmomBossGrove` 모델에서 `SpriteRUID`를 교체한다.
- 장식은 화면 가장자리와 후경에 두고, 중앙 6칸·유닛·공격 전조·Intent UI 영역은 비운다.
- 연속된 전투 맵의 길은 이전 맵 출구 쪽과 다음 맵 입구 쪽에 같은 나무 군락·버섯 군락처럼
  실루엣이 분명한 오브젝트 조합을 좌우 대응시켜 암시한다. 나무 사이에는 좁은 빈 잔디 구간을
  남겨 길처럼 읽히게 하되, 이동·충돌·Stage 전환 기능은 갖지 않는 시각 요소로 유지한다.
- 새 보스 맵을 만들 때는 일반전 맵의 전투 컴포넌트 계약을 복제한 뒤 배경·장식만 분리한다.
- `region_01_boss`는 원작 머쉬맘의 `남의 집`을 참고해 큰 버섯집·꽃 울타리·작은 버섯·무성한 수풀로 구성한다. 다음 Region 후보는 전투 장식에 섞지 않고 클리어 이후 Node/Run Flow UI에서 표시한다.
- 물리 맵을 추가하거나 이름을 바꾸면 `StageMapRoutes.csv`와 Maker의 Sector 맵 등록을 함께 확인한다.

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
