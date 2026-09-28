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

현재 Region 05 노틸러스는 작은 범위부터 확장 중이다.

| Stage | 물리 맵 | Wave 수 | 기본 구성 |
|---|---|---:|---|
| `region_05_stage_01` | `nautilus_battle` | 3 | 파란 리본돼지 총 5마리, 최대 동시 2 |
| `region_05_stage_02` | `nautilus_interior_01` | 3 | 노란 불가사리·해파리 총 6마리, 최대 동시 2 |
| `region_05_stage_03` | `nautilus_interior_02` | 4 | 화난 불가사리·쿨한 해파리·클랑 총 8마리, 최대 동시 3 |
| `region_05_stage_04` | `nautilus_boss` | 1 | 킹크랑 1마리, `StageType=BOSS`, 2 Phase·중단 가능 캐스팅 |

`nautilus_battle`의 첫 맵 테마는 노틸러스 항구 부두다. 해안 배경 앞에 X자 지지대가 있는
목재 부두를 전투 발판으로 사용한다. 정확한 노틸러스호 리소스가 없을 때는 유사 선박을 억지로
배치하지 않고 대포·통·화물로 화면 밖에 정박한 배를 암시한다. 5-2는 화물칸, 5-3은 침수 기관실
배경을 사용한다. 5-4는 침수 기관실 구조를 독립 보스 맵으로 복제한다. 전투용 6칸과 Foothold
좌표는 유지하며 Region별 분위기는 장식 모델만 교체한다.

새 `.map` 파일을 만들고 `StageMapRoutes`를 추가한 것만으로 Maker Sector 등록이 끝나지는 않는다.
Maker에서 맵을 Sector에 등록한 뒤 Refresh하고, 맵 이동·Stage 직접 시작을 각각 확인한다.
복제 맵의 최상위 `EntryKey`도 반드시 `map://<새 MapId>`인지 확인한다. 원본 EntryKey가 남으면
`LEA-3015` 중복 오류가 발생하고 새 맵이 목록에 나타나지 않는다.

Maker 직접 실행은 MapId 기준 공통 테스트 진입기를 사용한다. 같은 맵의 가장 낮은 StageIndex가
기본으로 선택되며, 특정 공유 Stage는 `PrototypeTestStageOverride`로만 지정한다. 자세한 절차는
[Battle-Prototype-Test-Guide.md](Battle-Prototype-Test-Guide.md)를 따른다.

노틸러스의 상세 ID·맵·적 확장 순서는
[Region-05-Nautilus-Implementation-Plan.md](Region-05-Nautilus-Implementation-Plan.md)를 따른다.

슬리피우드(`region_06`) 전반전은 물리 맵 두 개로 운영한다.

| Stage | 물리 맵 | Wave 수 | 기본 구성 |
|---|---|---:|---|
| `region_06_stage_01` | `sleepywood_ant_tunnel` | 3 | 뿔버섯 5 |
| `region_06_stage_02` | `sleepywood_ant_tunnel` | 4 | 뿔버섯·좀비버섯 7 |
| `region_06_stage_03` | `sleepywood_ant_tunnel` | 4 | 뿔버섯·좀비버섯·주니어 부기 7 |
| `region_06_stage_04` | `sleepywood_food_cart_boss` | 보스 | 포장마차 2 Phase, Phase 2 좀비버섯 증원 |

세부 패턴·데이터 수정 위치·직접 테스트 방법은
[Region-06-Sleepywood-Implementation-Guide.md](Region-06-Sleepywood-Implementation-Guide.md)를 따른다.

스포아는 1-2부터 `region_01_spore_ranged` Enemy Definition으로 등장한다. 사거리는 2칸,
기본 피해는 1, HP는 2다. 모든 직업의 기본 시작 공격 피해가 2 이상이므로 초반에는 스킬
한 번으로 처치할 수 있다. `EnemySpawnPools.Weight`를 낮게 두어 원거리 압박이 과해지지 않게 한다.

커닝시티(`region_Kerning_City`) 전투 Stage는 다음처럼 분리돼 있다.

| Stage | 물리 맵 | Wave 수 | 기본 구성 |
|---|---|---:|---|
| `region_kerning_stage_01` | `kerning_city_battle` | 3 | 스티지 2 → 주니어 레이스 2 → 레이스 1 |
| `region_kerning_stage_02` | `kerning_city_battle` | 3 | 주니어 레이스 2 → 레이스 2 → 셰이드 2 |
| `region_kerning_stage_03` | `kerning_city_battle2` | 4 | 주니어 네키 2 → 리게이터 2 → 크로코 2 → 늪진흙괴물 1 (`UnitY=0.12`) |
| `region_kerning_stage_04` | `kerning_city_boss` | 1 | 보스 다일 1, `StageType=BOSS`. 다일이 패턴 마지막에 늪진흙괴물 3마리 소환 |

2-1·2-2는 `kerning_city_battle`에서 스티지~셰이드, 2-3은 보스맵을 복제한 늪지대 `kerning_city_battle2`(월드 발판 7개), 2-4는 `kerning_city_boss`(월드 발판 9개)에서 주니어 네키~늪진흙괴물(+2-4 다일)을 사용한다. 두 맵은 `BattlePlatforms` 레이어의 `BattleCell1~N` 링을 쓰며 x 위치는 Stage의 `CellStartX`/`CellSpacing`으로 런타임에 배치된다.
일반 3단계는 Wave당 최대 2마리씩 `TURN_LIMIT`(3턴)으로 나누어 투입하고 `MaxConcurrent=2`로
동시 등장을 제한한다. 마릿수를 정확히 맞춰야 하므로 가중치 혼합 Pool 대신 **적 1종만 담은
전용 Pool**(`region_kerning_stirge_pool` / `_jr_wraith_pool` / `_wraith_pool` / `_ligator_pool` / `_shade_pool` / `_jr_necki_pool` / `_croco_pool` / `_swamp_mud_pool`)을 Wave별로 지정한다.
가중치 Pool은 어떤 적이 몇 마리 나올지 보장하지 못한다.

2026-09-27 난이도 상향(엘리니아 수준): 다일 HP 32. 일반 적은 난이도 순서(스티지 < 주니어 레이스 < 레이스 < 셰이드 < 주니어 네키 < 리게이터 < 크로코 < 늪진흙괴물)에 맞춰 HP 4~8, 기본 공격력 1~4로 배정한다. 기본 공격이 아닌 스킬 피해는 4를 넘을 수 있다.

| 적 | HP | 공격력 |
|---|---:|---:|
| 스티지 | 4 | 1 |
| 주니어 레이스 | 4 | 1 |
| 레이스 | 5 | 2 |
| 셰이드 | 5 | 2 |
| 주니어 네키 | 6 | 3 |
| 리게이터 | 6 | 3 |
| 크로코 | 7 | 4 |
| 늪진흙괴물 | 8 | 4 |

일반 적 패턴은 다음처럼 순환한다. 보스 다일은 기존 패턴 끝에 늪진흙괴물 3마리 소환 단계가 추가됐다([Boss-Phase-Authoring-Guide.md](Boss-Phase-Authoring-Guide.md)).

| 적 | 패턴 순환 | 추가 스킬 |
|---|---|---|
| 스티지 | 방향 전환 → 급강하 → 할퀴기 2회 | `region_kerning_stirge_dive`: 1턴 예고 돌진(최대 5칸), 기본 공격력 피해 |
| 주니어 레이스 | 원혼의 손아귀 → 손톱 2회 | `region_kerning_jr_wraith_grasp`: 전방 3칸 첫 대상, 피해 1 + 바로 앞으로 당기기, 쿨다운 2 |
| 레이스 | 원혼탄 → 원혼 파동 → 원혼탄 → 저주 | `region_kerning_wraith_soul_wave`: 1턴 예고, 전방 1~3칸 피해 2 / `region_kerning_wraith_curse`: 1턴 예고, 전방 1~2칸 봉인 1턴, 쿨다운 4 |
| 주니어 네키 | 독침 뱉기 → 물기 2회 | `region_kerning_jr_necki_spit`: 전방 2칸 첫 대상 피해 3, 쿨다운 2 |
| 크로코 (`HEAVY`) | 물기 2회 → 꼬리 휩쓸기 | `region_kerning_croco_tail_sweep`: 1턴 예고, 앞뒤 1칸 피해 5 |
| 셰이드 | 원한의 손길 → 영혼 흡수 → 방향 전환 → 그림자 급습 | `region_kerning_shade_soul_drain`: 전방 2칸 피해 2 + 자신 HP 2 회복, 쿨다운 3 / `region_kerning_shade_dash`: 1턴 예고 돌진 |
| 늪진흙괴물 | 진흙 덩어리 던지기 → 후려치기 → 진흙 늪 → 후려치기 | `region_kerning_swamp_mud_throw`: 전방 3칸 첫 대상 피해 3, 쿨다운 2 / `region_kerning_swamp_mud_bog`: 전방 1~2칸에 2턴 동안 진흙 늪(지휘관 독안개와 같은 `POISON_MIST`), 턴 종료 시 그 칸에 있으면 피해 1, 쿨다운 4 |
| 리게이터 | 물기 → 꼬리치기 → 크게 물기 | `region_kerning_ligator_tail_whip`: 피해 3 + 밀치기 / `region_kerning_ligator_chomp`: 1턴 예고, 전방 1칸 피해 5 |

커닝시티 적은 모두 전용 `EnemyDefinitions`와 `RootDesk/MyDesk/Models/Monsters/Kerning*.model`을
사용하며 헤네시스 적을 재사용하지 않는다. 보스 규칙은
[Boss-Phase-Authoring-Guide.md](Boss-Phase-Authoring-Guide.md)를 따른다.

슬리피우드(`region_06`) 후반전은 신전 맵 두 개로 운영한다. 메인 런(`prototype_run`)에서 6-4 포장마차
보스 다음 `sleepywood_reward_after_stage04`(REST)를 거쳐 `6-5 → REST → 6-6 → REST → 6-7 → REST → 6-8 BOSS`
순서로 이어진다.

| Stage | 물리 맵 | Wave 수 | 기본 구성 |
|---|---|---:|---|
| `region_06_stage_05` | `sleepywood_temple_battle` | 3 | 와일드카고 2 → 와일드카고 2 → 타우로스피어 1 |
| `region_06_stage_06` | `sleepywood_temple_battle` | 3 | 와일드카고 2 → 타우로스피어 2 → 타우로마시스 1 |
| `region_06_stage_07` | `sleepywood_temple_battle` | 3 | 타우로스피어 2 → 타우로마시스 2 → 타우로마시스 1 |
| `region_06_stage_08` | `sleepywood_temple_boss` | 1 | 보스 주니어 발록 1, `StageType=BOSS`, 2 Phase, 증원 없음 |

커닝시티와 같은 Wave 규칙(`TURN_LIMIT` 3턴, `MaxConcurrent=2`, 적 1종 전용 Pool)을 사용한다.

`sleepywood_temple_battle`은 `kerning_city_battle`을 복제한 맵이라 `BattleCell1~6`이 x `-2.9027`에
있고 칸 아래 발판 높이가 y `-1.93`이다. 따라서 6-5~6-7은 `CellStartX=-2.9027`, `UnitY=-1.93`을
사용한다. `sleepywood_temple_boss`는 발판 높이가 y `0`이라 6-8은 `CellStartX=-2.8`, `UnitY=0`이다.
신전 적의 `EnemyDefinitions.VisualOffsetY`는 비워 둔다(0).

플레이어는 Body가 있어 발판 위에 서지만 적 모델에는 Body가 없어 `UnitY`에 그대로 배치된다. 따라서
`UnitY`는 칸 타일 위치가 아니라 **칸 x 위치의 발판 y값**과 같아야 적 발이 플레이어와 같은 높이에 선다.
물리 맵을 복제해 Stage에 연결할 때는 `MapBuilder.getFootholds()`로 칸 아래 발판 높이를 확인해
`CellStartX`/`UnitY`에 반영한다.

| 적 | HP / 공격 | 역할 |
|---|---|---|
| `region_06_wild_kargo` | 8 / 4 | 근접, `QUICK`. attack 클립이 없어 `jump` 클립을 들이받기 모션으로 사용 |
| `region_06_taurospear` | 9 / 4 | `attack1` 창 찌르기(`FIRST_ENEMY_FORWARD` 2칸, 쿨타임 2) → `attack2` 1턴 예고 휩쓸기(`RANGE_OFFSETS 1\|2`, 피해 5)를 번갈아 사용 |
| `region_06_tauromacis` | 13 / 5 | 근접, `HEAVY`. `attack1/info/hit` 클립을 적중 효과로 사용 |

모델은 `RootDesk/MyDesk/Models/Monsters/Region06*.model`이며 일반 적은 리소스가 커서 `Scale=0.75`,
주니어 발록은 `Scale=1.2`를 사용한다.

신전 적의 피격음·사망음과 스킬별 적중음은 `EnemyImpactPresentations.csv`에서 관리한다. 적 행
(`SkillId=*`)의 `DamageSoundRuid`에 리소스 팩 `audio/Damage`, `DeathSoundRuid`에 `audio/Die`를 넣고,
타우로스피어·주니어 발록의 `audio/CharDamN`은 해당 `SkillId` 행의 `ImpactSoundRuid`로 지정한다.
사망음은 `BattleSessionComponent.HandleUnitDiedFromSource`가 적 사망이 확정된 직후 한 번 재생한다.
몬스터 도감(`MonsterCodexProvider.GetVictoriaRegions`)은 `CollectionUI`의 지역 버튼이 4개뿐이라 아직
슬리피우드를 등록하지 않았다. 버튼 없이 지역만 추가하면 도감 네비게이션 연결 전체가 실패한다.

Node/REST 연결은 별도 제작 영역이다. Stage 행을 추가할 때는 담당자와 연결 ID를 합의한 뒤
`NodeDefinitions.NextNodeIds`를 변경한다. 슬리피우드는 노틸러스 보스 이후의 REST와 6-1~6-4
사이 REST 연결 ID까지 등록했으며, REST 화면·보상 선택 로직 자체는 수정하지 않았다.
후반전(신전)은 `sleepywood_stage04_boss.NextNodeIds`를 `sleepywood_reward_after_stage04`로 바꿔
6-5~6-8 노드를 이어 붙였다.

현재 통합 흐름은 `1-1 → REST → 1-2 → REST → 1-3 → REST → 1-4 BOSS → REST`다.
`StageMapRoutes`는 1-1~1-3을 일반전 공용 `region_01_battle`로 라우팅하고,
`region_01_stage_04`만 `region_01_boss`로 라우팅한다. 두 맵은 같은 전투 컴포넌트와
`BattleCell1~6` 계약을 유지하므로 Battle Gateway는 물리 맵에 분기를 두지 않고 전달한
StageId로 해당 Stage·Wave 데이터를 시작한다.

## 물리 맵과 장식 교체 규칙

- Region별 일반전·보스전 장식은 각 `region_NN_battle.map`, `region_NN_boss.map`에서 관리한다.
- 장식 이미지는 맵 엔티티에 직접 하드코딩하지 않고 `RootDesk/MyDesk/Models/Objects/`의
  `Henesys*`, `MushmomBossGrove` 모델에서 `SpriteRUID`를 교체한다.
- 장식은 화면 가장자리와 후경에 두고, 중앙 6칸·유닛·공격 전조·Intent UI 영역은 비운다.
- 연속된 전투 맵의 길은 이전 맵 출구 쪽과 다음 맵 입구 쪽에 같은 나무 군락·버섯 군락처럼
  실루엣이 분명한 오브젝트 조합을 좌우 대응시켜 암시한다. 나무 사이에는 좁은 빈 잔디 구간을
  남겨 길처럼 읽히게 하되, 이동·충돌·Stage 전환 기능은 갖지 않는 시각 요소로 유지한다.
- 새 보스 맵을 만들 때는 일반전 맵의 전투 컴포넌트 계약을 복제한 뒤 배경·장식만 분리한다.
- `region_01_boss`는 원작 머쉬맘의 `남의 집`을 참고해 큰 버섯집·꽃 울타리·작은 버섯·무성한 수풀로 구성한다. 다음 Region 후보는 전투 장식에 섞지 않고 클리어 이후 Node/Run Flow UI에서 표시한다.
- 물리 맵을 추가하거나 이름을 바꾸면 `StageMapRoutes.csv`와 Maker의 Sector 맵 등록을 함께 확인한다.
- 현재 실제 전투 맵은 `TileMapMode=0` MapleTile이며 서버 권위 Cell Snapshot 이동을 사용한다.
  새 Region 맵은 검증된 전투 맵을 복제하고 맵 타입을 임의로 전환하지 않는다.

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
