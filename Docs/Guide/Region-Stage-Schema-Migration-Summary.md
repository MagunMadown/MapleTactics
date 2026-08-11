# Region·Stage·Enemy 규격 변경 요약

기준 브랜치: `feat/battle-new-enemy-logic`

## 1. 핵심 변경

| 구분 | 이전 | 현재 |
|---|---|---|
| Region | 별도 원본 없음 | `RegionDefinitions`가 소속·표시 순서 소유 |
| Stage ID | `stage01` 등 의미가 불명확한 ID | `region_01_stage_01` 형식의 조회 전용 ID |
| Stage 순서 | StageId 문자열에서 숫자 추출 | `StageIndex` 명시 |
| Stage 종류 | ID나 NodeType으로 추측 | `StageType=NORMAL/BOSS` 명시 |
| Wave 연결 | `StageEnemyWaves.StageId`가 실제로 Wave 표 ID 역할 | `WaveTableId`로 명칭과 의미 통일 |
| 적 공격 | Session이 `basic_slash`를 직접 분기 | Pattern의 `TileId → SkillId` 공용 실행 |
| 원거리 조건 | 인접 공격 중심 | `DISTANCE_LE` + Skill의 Targeting/Range 조합 |
| 보스 Phase | `IsBoss` 표시만 존재 | `BossPhaseDefinitions`가 HP 임계값과 Pattern 교체 선언 |
| UI 상태 | 적 Queue 중심 | 적 Queue에 Boss Phase ID/Index/Revision 추가 |

## 2. ID 규칙

```text
RegionId    region_01
StageId     region_01_stage_01
WaveTableId region_01_stage_01_waves
PoolId      region_01_stage_01_pool
```

ID는 조회와 참조에만 사용한다. 코드에서 `match`, `find`, `sub`로 Region, 순서, Type을
추출하지 않는다. 의미가 필요한 객체는 다음 명시 필드를 읽는다.

- 소속: `RegionId`
- Region 내부 전투 순서: `StageIndex`
- 일반/보스 구분: `StageType`
- 다음 콘텐츠: `NodeDefinitions.NextNodeIds`
- Wave 원본: `WaveTableId`

## 3. StageDefinitions v2

필수 식별 필드는 다음과 같다.

```csv
SchemaVersion,StageId,RegionId,StageIndex,StageType,...,WaveTableId,NextStageId,StageRuleId
2,region_01_stage_01,region_01,1,NORMAL,...,region_01_stage_01_waves,,
```

- `(RegionId, StageIndex)`는 유일해야 한다.
- `RegionId`는 활성 `RegionDefinitions` 행을 참조한다.
- `StageType`은 현재 `NORMAL`, `BOSS`만 허용한다.
- `NextStageId`는 호환 열이며 신규 진행 흐름은 Node Graph가 소유한다.
- Repository의 `stage01` 하드코딩 fallback은 제거됐다.

## 4. StageEnemyWaves

첫 열은 다음처럼 변경됐다.

```text
StageId → WaveTableId
```

`StageDefinitions.WaveTableId`와 `StageEnemyWaves.WaveTableId`가 정확히 일치해야 한다.
StageId와 WaveTableId는 서로 다른 타입의 식별자이므로 같은 값으로 가정하지 않는다.

## 5. 적 공격 규격

`EnemyPatternSteps.ActionType=EXECUTE_TILE` 또는 `TELEGRAPH_TILE`일 때 `TileId`는
`SkillDefinitions.SkillId` 참조다.

```text
Enemy Pattern
→ TileId/SkillId
→ Skill Target Resolver
→ Effect Router
→ Damage/Push Executor
```

Session에 EnemyDefinitionId나 SkillId별 조건문을 추가하지 않는다. 근접·원거리·범위 공격은
Skill의 `TargetingType`, `Range`, `TargetOffsets`, `EffectSetId`로 확장한다.

## 6. 보스 Phase 규격

`BossPhaseDefinitions`가 다음 값을 소유한다.

- `EnemyDefinitionId`
- 연속된 `PhaseIndex`
- 고유 `PhaseId`
- 감소하는 `HpRatioLE`
- Phase별 `PatternId`

첫 Phase는 `HpRatioLE=1.0`이며 Enemy 정의의 초기 Pattern과 같아야 한다. Phase 전환 전에
공개된 적 Queue는 그대로 실행하고 옛 Pattern Step 진행만 `PATTERN_SUPERSEDED`로 폐기한다.

UI는 `GetBattleUiState().EnemyIntents[]`의 다음 값을 표시만 한다.

- `BossPhaseId`
- `BossPhaseIndex`
- `BossPhaseRevision`
- 현재 Queue의 `PatternId`, `CommandType`, `TileId`, `TelegraphTurnsRemaining`

## 7. Node·REST 팀 경계

- Node는 `NodeType`으로 BATTLE/REST/SHOP/EVENT를 구분한다.
- 신규 보스 Node도 `NodeType=BATTLE`, 연결된 Stage의 `StageType=BOSS`를 사용한다.
- BATTLE의 ContentId는 StageId, REST의 ContentId는 NodeId다.
- REST 완료는 `CompleteCurrentContent(player, "REST", requestId)`를 사용한다.
- 전투 콘텐츠 작업은 다른 팀의 REST 행과 `NextNodeIds`를 임의로 바꾸지 않는다.

현재 1-1~1-4 전투 데이터는 준비됐지만 통합 Node Graph에는 1-1만 연결돼 있다.

## 8. 기존 데이터 마이그레이션 체크리스트

1. Region 행을 추가한다.
2. StageId를 새 규칙으로 바꾸고 모든 외래 참조를 함께 변경한다.
3. Stage 행에 `RegionId`, `StageIndex`, `StageType`을 채운다.
4. Wave 표 첫 열을 `WaveTableId`로 바꾼다.
5. 적 공격 Pattern의 TileId가 실제 SkillId인지 확인한다.
6. 보스는 `IsBoss=true`와 Boss Phase 행을 함께 추가한다.
7. NodeId 문자열은 유지할 수 있지만 BATTLE 행의 StageId 참조는 새 ID로 바꾼다.
8. Maker Refresh 후 전체 Content Integrity Gate와 대표 전투 실행을 확인한다.
