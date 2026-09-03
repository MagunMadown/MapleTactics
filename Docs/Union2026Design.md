# Union 2026 Design

> 상태: NEW STEP 5 완료 — `AllocatedUnionStats` 기반 production 효과 cutover와 8개 구현 효과의 Run Snapshot 연결까지 검증
> 목표: 직업별 B/A/S/SS/SSS 등급이 총 Union Stat Point를 만들고, 플레이어가 Basic/Expanded 스탯에 자유 배분하는 MapleTactics용 Union

## 1. 제품 원칙

1. Battle Map, 블록 모양, 캐릭터/블록 배치를 사용하지 않는다.
2. `Union Coin`, `Union Stat Point`, `Union Growth/Level`을 서로 다른 개념과 필드로 유지한다.
3. 총 Stat Point는 직업 등급에서 파생한다. 획득/소비 화폐처럼 저장하지 않는다.
4. 배분 결과는 서버가 검증하고 저장한다.
5. 효과는 Resolver → Run Snapshot → 게임플레이 소유자 경계를 유지한다.
6. 기존 Coin 구매 레벨을 새 배분 레벨로 자동 변환하지 않는다.
7. 구현되지 않은 효과는 데이터/UI에서 활성화하지 않는다.

## 2. 세 가지 Union 자원

| 개념 | 원본 | 증가 | 감소 | 사용처 |
|---|---|---|---|---|
| Union Coin | 저장된 `UnionPoints` | 권위 있는 Stage/Boss/Run 보상 | 향후 별도 Coin 상점/서비스 | 저장명은 유지하고 의미만 Union Coin으로 확정 |
| Union Stat Point | 직업 등급 기여 합계에서 파생 | 직업 등급 상승 | 감소하지 않음. 배분 시 Available만 줄어듦 | Basic/Expanded 스탯 배분 |
| Union Growth/Level | 저장된 `LifetimeUnionPoints`에서 Rank 파생 | 권위 있는 Union 성장 보상 | 감소하지 않음 | 저장명은 유지하고 의미만 Lifetime Union Growth로 확정 |

`UnionPoints`와 `LifetimeUnionPoints`는 저장명이 유지되지만 서로 독립된 값이다. 한 전투 결과에서 함께 지급될 수 있어도 같은 값이거나 `LifetimeUnionPoints >= UnionPoints`일 필요는 없다.

## 3. 직업 성장과 등급

### 3.1 저장 원본

```lua
JobUnionProgress = {
    warrior = 0,
    mage = 0,
    archer = 0,
    thief = 0,
    pirate = 0
}
```

프로필에는 위 숫자만 저장하며 의미는 **해당 Job으로 완료한 가장 높은 Union Milestone ProgressValue**다. 성공 런 횟수가 아니며 값은 절대 감소하지 않는다. `JobUnionGrades`는 등급 정의에서 계산해 서버 스냅샷에 포함하고 중복 저장하지 않는다.

```lua
JobUnionGrades = {
    warrior = "B",
    mage = "NONE",
    archer = "NONE",
    thief = "NONE",
    pirate = "NONE"
}
```

### 3.2 진행도 지급 원천

현재 프로젝트에는 `RegionClear`/`ChapterClear`가 없으므로 서버 `RunManagerLogic:RecordBattleResult`의 `Victory`와 현재 `prototype_run` 노드가 권위 경계다. JobId는 같은 서버 `PlayerRunStateComponent.SelectedJobId`에서 읽으며 클라이언트가 전달한 JobId를 받지 않는다.

| 지역 의미 | 실제 서버 Target | Progress | Grade | 구현 |
|---|---|---:|---|---|
| Henesys | `stage01_battle` | 0 | `NONE` | Milestone 행 없음 |
| Ellinia | `prototype_run / stage02_battle / LOWER` | 1 | `B` | 활성 |
| Perion | `prototype_run / stage03_battle` | 2 | `A` | 활성 |
| Sleepywood | 실제 런 노드/Stage 없음 | 3 | `S` | 비활성 메타데이터 |

`region_01_stage_02`는 UPPER에서 Kerning, LOWER에서 Ellinia이므로 StageId만으로 Ellinia를 판정하지 않는다. Sleepywood는 UI의 미래 잠금 표기만 존재하며 실제 전투 TargetId를 만들지 않는다.

### 3.3 등급 정의

**PROTOTYPE TUNING** — 초기 데이터 검증용 값이며 공식 MapleStory 수치를 복제하거나 최종 밸런스를 확정한다는 의미가 아니다.

| Grade | 필요 누적 Job Growth | 총 포인트 기여 |
|---|---:|---:|
| `NONE` | 0 | 0 |
| `B` | 1 | 1 |
| `A` | 2 | 2 |
| `S` | 3 | 3 |
| `SS` | 4 | 4 |
| `SSS` | 5 | 5 |

등급 기여는 해당 등급의 총 기여량이다. 진행도는 `max(현재값, 완료 Milestone.ProgressValue)`로 갱신하므로 재클리어로 누적되지 않는다. 5를 초과한 안전 입력도 SSS/5점으로 파생된다.

```text
TotalUnionStatPoints =
    contribution(warrior grade)
  + contribution(mage grade)
  + contribution(archer grade)
  + contribution(thief grade)
  + contribution(pirate grade)
```

현재 다섯 직업이 모두 SSS이면 최대 25점이다. 새 직업 추가 시 계산이 자동 확장되도록 활성 `JobDefinitions`와 교차 검증한다.

## 4. 스탯 배분 모델

### 4.1 저장 형태

```lua
AllocatedUnionStats = {
    MESO_GAIN_RATE = 2,
    ITEM_DROP_RATE = 1,
    MAX_HP = 1
}
```

값은 해당 StatId의 최종 배분 레벨이다. 사용 포인트는 서버 데이터의 각 레벨 `PointCost`를 1부터 목표 레벨까지 합산해 계산한다.

```text
SpentUnionStatPoints = sum(cost(statId, 1..allocatedLevel))
AvailableUnionStatPoints = TotalUnionStatPoints - SpentUnionStatPoints
```

프로필에 `TotalUnionStatPoints`, `SpentUnionStatPoints`, `AvailableUnionStatPoints`를 저장하지 않는다. 모두 스냅샷 생성 시 파생한다.

### 4.2 서버 검증

배분 변경 요청은 서버에서 다음 순서로 원자 검증한다.

1. 프로필과 데이터셋 로드
2. 활성 JobId와 Job Growth로 등급/총 포인트 재계산
3. StatId 존재, Basic/Expanded 해금, Rank, MaxLevel 확인
4. 요청 후 전체 PointCost 재계산
5. `spent <= total` 확인
6. 새 `AllocatedUnionStats`를 한 번에 저장
7. 저장 성공 후 새 스냅샷 반환

클라이언트가 보낸 총 포인트, 효과값, 등급은 신뢰하지 않는다.

## 5. Basic Union Stats

Basic은 처음부터 보이며 낮은 복잡도의 범용 효과로 구성한다.

| StatId | 표시 효과 | 현재 통합 | 초기 MaxLevel/비용 제안 |
|---|---|---|---|
| `MESO_GAIN_RATE` | Meso/Run Gold 획득량 | 구현 완료 | 5 / 레벨당 1점 |
| `ITEM_DROP_RATE` | 아이템 드롭률 | 구현 완료 | 5 / 레벨당 1점 |
| `UNION_COIN_GAIN_RATE` | Union Coin 획득량 | 구 `UNION_POINT_GAIN_RATE` 경로 구현 | 3 / 레벨당 1점 |
| `MAX_HP` | 런 최대 HP | 구현 완료 | 3 / 레벨당 1점 |

`UNION_POINT_GAIN_RATE`는 한 버전의 호환 별칭으로만 받아 새 스냅샷 필드에 매핑한 뒤 제거한다.

## 6. Expanded Union Stats

Expanded는 Union Rank에 따라 행과 상한을 해금한다.

| StatId/가족 | 표시 효과 | 초기 해금 제안 | 상태 |
|---|---|---|---|
| `STARTING_POTION` | 시작 포션 | `UNION_II` | 구현 완료 |
| `INVENTORY_SLOT` | 소모품 인벤토리 슬롯 | `UNION_II` | 구현 완료 |
| `AUGMENT_REROLL` | 시작 증강 재굴림 | `UNION_III` | 구현 완료 |
| `STARTING_SKILL` | 시작 스킬 슬롯 | `UNION_IV` | 구현 완료, 작성 스킬 수가 상한 |
| `STARTING_RANDOM_RELIC` | 시작 랜덤 유물 | `UNION_V` | 소비처 미구현. UI 비활성/숨김 유지 |
| `ADDITIONAL_SKILL_UNLOCK` | 추가 스킬 해금 | `UNION_V` | 전체 파이프라인 미구현. UI 비활성/숨김 유지 |
| `FUTURE_UNION_CHARACTER_EFFECT_*` | 향후 Union 캐릭터 효과 | `UNION_V` 이후 | 예약 가족. 구체 효과/소유자가 생기기 전 데이터 행 생성 금지 |

기존 `UnionRankDefinitions`의 임계치 0/1,000/3,000/7,000/15,000은 초기값으로 유지할 수 있다. `BoardTier`는 `ExpandedUnlockTier`/`StatCapTier` 의미로 교체한다.

## 7. 초기화와 프리셋

### 권장: B — Reset 버튼만 먼저 제공

- 로비 Union 창에서 `Reset All`을 누르면 모든 배분을 서버 원자 트랜잭션으로 0으로 만든다.
- 초기 버전의 Reset은 무료이며 Union Coin을 소모하지 않는다.
- Reset 뒤 Basic/Expanded에 다시 자유 배분한다.
- 개별 감소 버튼은 이후 UX 개선으로 추가 가능하지만 첫 구현의 필수 조건은 아니다.

판정:

| 기능 | 분류 | 이유 |
|---|---|---|
| 단일 배분 세트 + Reset | `CORE` | 자유 재배분을 충족하면서 저장/동시성 표면 최소화 |
| 개별 +/- 감소와 임시 편집/Apply | `LATER` | UX 개선이지만 최소 슬라이스에 불필요 |
| 다중 프리셋 저장/전환 | `LATER` | 유용하지만 상태·UI·멱등성·전환 규칙이 추가됨 |
| 프리셋 쿠폰 소비로 슬롯 해금 | `UNNECESSARY` | 현재 목표에 없는 별도 경제 시스템 |
| Coin을 사용한 스탯 Reset | `UNNECESSARY` | Coin/Stat Point 분리를 흐리고 자유 배분 목표와 충돌 |

## 8. Union Coin의 미래 역할

Union Coin은 스탯 레벨 구매에 사용하지 않는다.

첫 수직 슬라이스에서는 다음만 한다.

- 기존 `UnionPoints` 저장명을 유지하고 플레이어/도메인 의미를 Union Coin으로 확정
- Stage/Boss/Run 결과에서 획득
- 현재 Coin 아이콘으로 보유량 표시
- 소비처가 없음을 UI에서 숨기거나 “향후 상점”으로 명확히 표시

향후 별도 승인 후 가능한 소비처는 외형, 계정 편의, 제한형 소모품, 주간 교환 상점이다. 블록 상점은 되살리지 않는다.

## 9. 데이터 계약

향후 구현 시 권장 데이터 구성은 다음과 같다.

### `UnionJobGradeDefinitions`

- `GradeId`
- `RequiredJobGrowth`
- `StatPointContribution`
- `DisplayName`
- `SortOrder`

### `UnionStatDefinitions`

- `StatId`
- `Category` = `BASIC` 또는 `EXPANDED`
- `DisplayName`
- `Description`
- `EffectType`
- `MaxLevel`
- `RequiredUnionRank`
- `Enabled`
- `SortOrder`

### `UnionStatLevelDefinitions`

- `StatId`
- `Level`
- `PointCost`
- `EffectValue` — 현재와 같이 해당 레벨의 누적값
- 선택적 `RequiredUnionRank`

### `UnionRewardDefinitions`

- 현재 `RewardId`, `TriggerType`, `StageFilter` 유지
- `CoinAmount`
- `LifetimeGrowthAmount`
- `JobGrowthAmount`

기존 Upgrade 정의/레벨은 위 Stat 파일로 변환하되, 새 데이터와 구 데이터를 장기간 병렬 운영하지 않는다. 전환 배포에서 Resolver와 UI를 새 데이터로 자른 뒤 구 파일을 제거한다.

## 10. 저장 스키마 5 실제 계약

```lua
{
    SchemaVersion = 5,
    UnionPoints = 0, -- 의미: Union Coin
    LifetimeUnionPoints = 0, -- 의미: Lifetime Union Growth
    NextRewardRunId = 0,
    CommittedRewardKeys = {},
    JobUnionProgress = {
        warrior = 0,
        mage = 0,
        archer = 0,
        thief = 0,
        pirate = 0
    },
    AllocatedUnionStats = {},
    PurchasedLevels = { ... } -- 환급 후 보존되는 Legacy read-only 데이터. production 효과에서는 무시
}
```

`JobUnionGrades`, `UnionRank`, `TotalUnionStatPoints`, `UnionStatPoints`, 총/사용/잔여 Stat Point, 효과값은 저장하지 않고 서버 스냅샷에서 파생한다. `OwnedUnionBlocks`, `NextBlockPurchaseReceiptOrder`, `BlockPurchaseReceipts`는 환급 성공과 같은 원자 저장에서 제거된다.

## 11. Schema 4 → 5 마이그레이션

순서는 데이터 유실과 중복 환급을 막기 위해 중요하다.

1. Schema 4 프로필을 clone하고 레거시 필드를 먼저 읽는다.
2. `UnionPoints` 저장명과 값을 유지하고 의미를 Union Coin으로 확정한다.
3. `LifetimeUnionPoints` 저장명과 값을 유지하고 의미를 Lifetime Union Growth로 확정한다.
4. `NextRewardRunId`, `CommittedRewardKeys` 유지.
5. 정확한 다섯 JobId의 `JobUnionProgress`를 0으로 초기화한다.
6. `JobUnionGrades`는 저장하지 않고 성장도에서 계산한다.
7. `AllocatedUnionStats = {}`로 시작한다.
8. `PurchasedLevels`의 1..구매 레벨별 실제 Legacy `Cost`를 합산해 `UnionPoints`에 한 번만 환급한다.
9. 블록은 완전한 영수증 연속열이 있으면 실제 `Receipt.Cost` 합계를 사용하고, 영수증이 전혀 없으면 소유 수량 × 권위 있는 `ShopCost`를 사용한다. 부분/모순/알 수 없는 데이터는 추측하지 않고 마이그레이션을 중단한다.
10. `SchemaVersion = 5`, 환급된 `UnionPoints`, 신규 필드, 제거된 블록 필드를 하나의 CAS 저장으로 커밋한다. 별도 환급 플래그 대신 성공적으로 저장된 Schema 5가 멱등 마커다.
11. `PurchasedLevels`는 환급 후에도 Legacy 검증/후속 정리를 위해 그대로 보존하되 구매 API를 `LEGACY_UNION_SYSTEM_DISABLED`로 동결하고 production 효과에서는 무시한다.
12. `OwnedUnionBlocks`, `NextBlockPurchaseReceiptOrder`, `BlockPurchaseReceipts`는 환급과 같은 저장에서 제거하며 블록 구매 API도 동결한다.

직접 레벨 변환 대신 환급을 권장하는 이유는, 기존 레벨이 Coin 구매 결과이고 새 레벨이 직업 등급 포인트 배분 결과이기 때문이다. 자동 변환하면 새 총 포인트보다 많은 배분이 생길 수 있다.

환급은 `LifetimeUnionPoints`나 `AllocatedUnionStats`를 증가시키지 않는다. 따라서 Coin 잔액이 Lifetime Growth보다 커지는 상태도 유효하다.

## 12. 효과 Resolver 전환

기존 Resolver의 출력 계약과 런 캡처 시점을 유지한다.

```text
AllocatedUnionStats
  → UnionStatDefinitions / UnionStatLevels 검증
  → 현재 배분 Level 행의 누적 EffectValue를 한 번 적용
  → UnionEffectSnapshot
  → PlayerRunUnionEffectComponent.CaptureForRun
  → 기존 게임플레이 소비처
```

전환 시 필수 호환 작업:

- player-facing 의미는 Union Coin이지만 기존 gameplay 계약인 `UnionPointGainRate` 필드 하나만 유지한다. 경쟁 필드/중복 배율은 만들지 않는다.
- Starting Random Relic은 소비처 완성 전 항상 0 또는 disabled
- Additional Skill Unlock은 Resolver/스냅샷/스킬 소유자까지 한 묶음으로 구현
- 런 도중 배분을 바꿔도 현재 런 Snapshot은 바꾸지 않는다. 다음 런부터 적용

## 13. UI 구조

기존 1540×900 창 셸과 우측 정보 패널을 재사용하는 구조다. 실제 `.ui` 수정은 후속 구현에서 UIBuilder로만 수행한다.

### Header

- `UNION`
- Refresh
- Close
- Block Shop 버튼 제거

### Main/Left

- Job Grade Summary: 다섯 직업, 현재 Grade, 다음 Grade까지 Growth, 기여 포인트
- `BASIC` / `EXPANDED` 탭 또는 두 연속 섹션
- 각 스탯 행: 이름, 설명, 현재 레벨/상한, 누적 효과, PointCost, `+`
- 잠긴 Expanded 행: 필요한 Union Rank 표시
- `Reset All`과 서버 적용 결과 메시지

### Right Summary

- Union Rank와 다음 Rank까지 Lifetime Growth
- Total / Spent / Available Union Stat Points
- Union Coin 보유량과 검증된 아이콘 `95632823c5e44dab89b9859ff439165b`
- 현재 적용 효과 요약

### 제거

- BattleMapBackdrop, BoardPanel, GridCellLayer 96개, Region/Core/BoardTier
- 업그레이드 노드와 보드 위치 하드코딩
- 구매 상세/주요 구매 확인
- Block Shop 전체

최신 관리 UI 프레임/버튼 RUID는 아직 검증되지 않았다. 현재 Maple 스타일 프레임을 대체재로 사용하되 공식 Union 전용 에셋이라고 표기하지 않는다.

## 14. 최소 수직 슬라이스

첫 승인 구현은 다음 범위만 포함한다.

1. 개발/마이그레이션 프로필에서 `warrior`의 Job Growth가 B 기준을 충족한다.
2. Warrior Grade `B`가 총 Union Stat Point 1점을 제공한다.
3. Basic `MAX_HP`에 1점을 배분한다.
4. 서버 저장 후 재접속해 배분이 유지된다.
5. Union 창에 Warrior B, Total 1, Spent 1, Available 0, MAX_HP Lv.1이 표시된다.
6. 새 런 시작 시 Resolver → Run Snapshot → RunManager 경로로 최대 HP가 정확히 한 번 증가한다.
7. 런 도중 배분을 Reset해도 현재 런은 변하지 않고 다음 런부터 적용된다.
8. Union Coin과 Lifetime Growth는 별도 수치로 표시되고 배분에 차감되지 않는다.
9. 블록/보드/상점 UI는 진입 불가다.

첫 슬라이스에서 Mage/Archer/Thief/Pirate는 데이터와 스냅샷에 존재하되 `NONE/0`이어도 된다. StageClear 기반 실제 B 승급은 같은 보상 커밋 경로의 다음 얇은 확장으로 붙인다.

## 15. 구현 순서 — 승인 후

1. 새 데이터 계약과 저장 Schema 5 마이그레이션
2. Job Growth 지급과 Grade/Point 파생 서비스
3. Stat Repository와 서버 배분/Reset API
4. Effect Resolver 입력 전환과 호환 별칭
5. UIBuilder로 새 Job/Basic/Expanded UI 작성
6. Warrior B → MAX_HP 1점 수직 슬라이스 검증
7. 기존 구현 완료 효과 순차 노출
8. 블록/보드/상점 프로덕션 파일과 레거시 저장 필드 제거
9. 블록 문서 Archive 이동
10. 프리셋 및 미구현 Expanded 효과는 별도 승인 작업

## 16. 완료 조건

- Union Coin, Stat Point, Growth가 코드/데이터/UI/저장 모두에서 혼용되지 않는다.
- 다섯 실제 JobId만 성장도 원본으로 인정된다.
- 총 포인트는 등급 기여 합과 항상 일치한다.
- 사용 포인트가 총 포인트를 넘는 저장은 생성되지 않는다.
- 효과는 런 시작 Snapshot으로만 캡처된다.
- 재접속, 중복 결과 커밋, 중복 배분 요청, Reset, 랭크 잠금이 서버 권위로 안전하다.
- 배치/블록 코드와 데이터가 활성 경로에 남지 않는다.
- 구현되지 않은 효과가 UI에서 구매/배분 가능 상태로 노출되지 않는다.

## 17. NEW STEP 1 실제 정의

NEW STEP 1은 신규 정의 데이터와 읽기 전용 Repository만 추가한다. 아래의 모든 수치는 **PROTOTYPE TUNING**이며 CSV에서 수정 가능하다. 저장 Schema, 플레이어 진행도, 포인트 배분, 효과 적용, UI는 이 단계의 범위가 아니다.

### Union Stat Definition Schema

`UnionStatDefinitions.csv/.userdataset`의 실제 열:

- `StatId`
- `Category` — 정확히 `BASIC` 또는 `EXPANDED`
- `DisplayName`
- `Description`
- `EffectType`
- `MaxLevel`
- `RequiredUnionRank`
- `IsImplemented`
- `SortOrder`

`UnionStatLevelDefinitions.csv/.userdataset`의 실제 열:

- `StatId`
- `Level`
- `PointCost`
- `EffectValue` — 해당 레벨에서 실제 적용될 누적값
- `RequiredUnionRank`
- `SortOrder`

모든 레벨의 `PointCost`는 첫 구현에서 1이다. 비용은 Repository가 데이터에서 읽으며 mLua에 하드코딩하지 않는다.

### Basic Stats

| StatId | MaxLevel | EffectValue | RequiredUnionRank | PointCost |
|---|---:|---|---|---:|
| `MAX_HP` | 5 | 1/2/3/4/5 | `UNION_I` | 레벨당 1 |
| `MESO_GAIN_RATE` | 5 | 0.05/0.10/0.15/0.20/0.25 | `UNION_I` | 레벨당 1 |
| `ITEM_DROP_RATE` | 5 | 0.05/0.10/0.15/0.20/0.25 | `UNION_I` | 레벨당 1 |
| `UNION_COIN_GAIN_RATE` | 5 | 0.05/0.10/0.15/0.20/0.25 | `UNION_I` | 레벨당 1 |

`UNION_COIN_GAIN_RATE`의 데이터 StatId는 새 의미를 사용하지만, `EffectType`은 현재 게임플레이와 호환되는 `UNION_POINT_GAIN_RATE`다. 경쟁하는 새 런타임 EffectType을 만들지 않는다.

### Expanded Stats

| StatId | MaxLevel | EffectValue | RequiredUnionRank | PointCost |
|---|---:|---|---|---:|
| `STARTING_POTION` | 1 | 1 | `UNION_II` | 1 |
| `INVENTORY_SLOT` | 2 | 1/2 | `UNION_II` | 레벨당 1 |
| `AUGMENT_REROLL` | 2 | 1/2 | `UNION_III` | 레벨당 1 |
| `STARTING_SKILL` | 1 | 1 | `UNION_IV` | 1 |
| `STARTING_RANDOM_RELIC` | 1 | 1 | `UNION_V` | 1 |
| `ADDITIONAL_SKILL_UNLOCK` | 1 | 1 | `UNION_V` | 1 |

### Implementation Availability

| 상태 | StatId |
|---|---|
| `IsImplemented = true` | `MAX_HP`, `MESO_GAIN_RATE`, `ITEM_DROP_RATE`, `UNION_COIN_GAIN_RATE`, `STARTING_POTION`, `INVENTORY_SLOT`, `AUGMENT_REROLL`, `STARTING_SKILL` |
| `IsImplemented = false` | `STARTING_RANDOM_RELIC`, `ADDITIONAL_SKILL_UNLOCK` |

미구현 정의도 구조 검증 대상에는 포함되지만, 향후 런타임 배분/효과 사용에서는 거절하거나 숨겨야 한다.

### Job Union Grade Schema

`UnionJobGradeDefinitions.csv/.userdataset`의 실제 열:

- `GradeId`
- `DisplayName`
- `StatPointContribution`
- `RequiredJobProgress`
- `SortOrder`

다섯 직업이 공유하는 단일 등급 표다. `warrior`, `mage`, `archer`, `thief`, `pirate`용 중복 표를 만들지 않는다.

### Grade Point Contributions

| GradeId | 총 StatPointContribution |
|---|---:|
| `B` | 1 |
| `A` | 2 |
| `S` | 3 |
| `SS` | 4 |
| `SSS` | 5 |

기여값은 누적 보상이 아니라 해당 등급의 **총 기여량**이다. 예를 들어 S는 1+2+3이 아니라 총 3점이다.

### Prototype Progress Thresholds

**PROTOTYPE TUNING**

| GradeId | RequiredJobProgress |
|---|---:|
| `B` | 1 |
| `A` | 2 |
| `S` | 3 |
| `SS` | 4 |
| `SSS` | 5 |

진행도 0은 `NONE`/0점이며, 각 임계치 이상에서는 충족한 가장 높은 등급을 결정한다. NEW STEP 3에서 실제 서버 런 노드 Victory와 연결했다.

### Future Total Union Stat Point Calculation

`UnionJobGradeDefinitionRepositoryLogic:CalculateTotalStatPoints(gradeIds)`는 이미 결정된 등급 ID 목록만 받는 순수 합산 도우미다. 플레이어 저장을 읽지 않는다.

```text
warrior S(3) + mage A(2) + archer B(1)
+ thief NONE(0) + pirate NONE(0) = 6
```

실제 총점은 `UnionJobProgressionServiceLogic`이 다섯 JobId 각각의 진행도에서 등급을 파생한 뒤 위 총 기여량을 합산하며 저장하지 않는다.

### Rank Unlock Mapping

| Union Rank | 새 Stat 해금 |
|---|---|
| `UNION_I` | 모든 Basic Stat |
| `UNION_II` | `STARTING_POTION`, `INVENTORY_SLOT` |
| `UNION_III` | `AUGMENT_REROLL` |
| `UNION_IV` | `STARTING_SKILL` |
| `UNION_V` | `STARTING_RANDOM_RELIC`, `ADDITIONAL_SKILL_UNLOCK` |

Rank ID는 기존 `UnionRankDefinitions`를 조회해 검증한다. 기존 `BoardTier`는 이 신규 정의에서 사용하지 않으며 생산 Rank 로직 자체도 아직 수정하지 않는다.

### Read-only Repository

`UnionStatDefinitionRepositoryLogic`:

- `GetStat`
- `GetAllStats`
- `GetStatsByCategory`
- `GetLevel`
- `GetMaxLevel`
- `GetRequiredUnionRank`
- `IsImplemented`
- `ValidateDefinitions`

`UnionJobGradeDefinitionRepositoryLogic`:

- `GetGrade`
- `GetAllGrades`
- `ResolveGradeByProgress`
- `GetStatPointContribution`
- `CalculateTotalStatPoints`
- `ValidateDefinitions`

두 Repository는 `_DataService` 정의만 읽는다. 프로필 저장, Job 진행도 지급, Stat 배분, Resolver, 게임플레이를 호출하거나 변경하지 않는다.

## 18. 단계별 변경 선언

STEP 0에서 생성한 문서:

- `Docs/Union2026MigrationAudit.md`
- `Docs/Union2026Design.md`

NEW STEP 1에서 생성하는 데이터/Repository:

- `UnionStatDefinitions.csv/.userdataset`
- `UnionStatLevelDefinitions.csv/.userdataset`
- `UnionJobGradeDefinitions.csv/.userdataset`
- `UnionStatDefinitionRepositoryLogic.mlua`
- `UnionJobGradeDefinitionRepositoryLogic.mlua`

NEW STEP 1에서 수정하는 기존 파일은 이 설계 문서뿐이다. Schema 4, `PurchasedLevels`, 블록 저장 데이터, `UnionEffectResolver`, 게임플레이, `UnionSystemUI.ui`는 변경하지 않는다.

## 19. NEW STEP 2 구현 결과

NEW STEP 2의 변경 범위는 다음 두 런타임 파일과 본 문서/감사 문서다.

- `RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.mlua`
- `RootDesk/MyDesk/00_Core/UnionBlockShopServiceLogic.mlua`

구현된 계약:

- Schema 4 이하 프로필을 Schema 5로 정규화하고 기존 `UnionPoints`, `LifetimeUnionPoints`, 보상 영수증, `PurchasedLevels`를 보존한다.
- 업그레이드 구매 레벨별 실제 Legacy 비용과 검증 가능한 블록 구매 비용을 `UnionPoints`에 정확히 한 번 환급한다.
- 신규 `JobUnionProgress` 다섯 키는 모두 0, `AllocatedUnionStats`는 빈 맵으로 시작한다.
- 환급 성공 후 블록 소유/영수증 필드는 canonical 프로필과 JSON 저장에서 제거한다.
- Schema 5 저장 자체를 멱등 마커로 사용하며 재정규화/재접속에서 환급을 반복하지 않는다.
- `PurchasedLevels`는 효과 parity를 위해 보존하되 업그레이드·블록 구매 mutation은 `LEGACY_UNION_SYSTEM_DISABLED`로 거절한다.
- 신규 스탯·직업 등급 정의도 프로필 초기화 전 서버 정의 검증에 포함한다.
- `TotalUnionStatPoints`와 `UnionStatPoints`는 저장하지 않는다.

검증 결과:

- 환급 없음: Coin 500 / Growth 1000 유지
- `MESO_GAIN_RATE` Lv.2: 실제 비용 100 + 200 = 300 환급
- 블록 영수증 완전 보유: 영수증 실제 비용 사용
- 블록 영수증 없음: 권위 있는 `ShopCost` 사용
- 결합 환급 400 후 Schema 5 재정규화 환급 0, 추가 저장 불필요
- JSON 빈 맵 마커 왕복 후 추가 저장 불필요
- 알 수 없는 업그레이드/블록, 음수 수량, 소유 없는 영수증, 비정수 Schema 거부
- 환급 전후 `PurchasedLevels` 기반 효과 Snapshot 동일
- Legacy 업그레이드/블록 구매 mutation 모두 차단
- 고유한 합성 DataStorage 프로필에서 Schema 4 저장 → Schema 5 CAS → 캐시 제거 후 재로드를 수행했고, Coin 500·Growth 1000·신규 필드·블록 제거 상태가 안정적으로 유지

NEW STEP 2에서는 Job 진행, 등급/총 포인트 계산의 프로필 연결, Stat 배분/Reset API, Resolver 입력 전환, UI 변경을 구현하지 않았다. Job milestone 연결은 아래 NEW STEP 3에서 추가했다.

## 20. NEW STEP 3 구현 결과

### Job Union Progress Semantics

`JobUnionProgress[jobId]`는 성공 런 횟수가 아니라 해당 Job으로 완료한 **가장 높은 데이터 기반 Milestone ProgressValue**다.

```text
newProgress = max(currentProgress, completedMilestone.ProgressValue)
```

같은 milestone 재호출과 낮은 milestone 재클리어는 저장하지 않으며, 높은 milestone을 직접 완료하면 중간 값을 순서대로 기록하지 않고 바로 해당 값으로 이동한다.

### Current Milestones

현재 프로젝트의 실제 권위 진행 단위는 Region/Chapter가 아니라 `prototype_run`의 서버 Run Node Victory다.

| Milestone | TargetType | 실제 TargetId/조건 | Progress | Grade | 상태 |
|---|---|---|---:|---|---|
| Henesys | `RUN_NODE_CLEAR` | `stage01_battle` | 0 | `NONE` | 정의 없음 |
| Ellinia | `RUN_NODE_CLEAR` | `stage02_battle`, graph=`prototype_run`, branch=`LOWER` | 1 | `B` | 구현 |
| Perion | `RUN_NODE_CLEAR` | `stage03_battle`, graph=`prototype_run` | 2 | `A` | 구현 |
| Sleepywood | `RUN_NODE_CLEAR` | 실제 TargetId 없음 | 3 | `S` | `IsImplemented=false` |

Sleepywood는 미래 상점 잠금 UI 이름만 있고 `NodeDefinitions`/`StageDefinitions`에 실제 전투가 없다. 따라서 가짜 ID를 만들지 않았다. SS/SSS 역시 Grade 임계치 4/5는 지원하지만 활성 milestone은 없다.

### Authoritative Result Integration

`RunManagerLogic:RecordBattleResult`가 `Victory`를 처리할 때 다음 서버 소스만 사용한다.

- Job: `PlayerRunStateComponent.SelectedJobId`
- Graph/Node: 현재 `CurrentNodeGraphId`, `CurrentNodeId`
- Stage: `NodeDefinition.StageId`와 실제 결과 StageId 일치 검증
- Branch: `SelectedWorldMapBranch`

클라이언트 JobId, GradeId, ProgressValue, MilestoneId를 입력받는 RPC는 만들지 않았다. 실패/중단/Defeat 경로에서는 서비스 호출 자체를 하지 않는다.

### Derived Point Summary

`UnionJobProgressionServiceLogic`이 다음 값을 런타임 계산한다.

- `TotalUnionStatPoints`: 다섯 Job Grade 기여 합
- `SpentUnionStatPoints`: `AllocatedUnionStats`의 1..Level `PointCost` 합
- `AvailableUnionStatPoints = Total - Spent`

세 값 모두 저장하지 않으며 allocation mutation은 구현하지 않았다.

### Verification

- Henesys: milestone 없음
- Ellinia LOWER: 0→1/B, UPPER: milestone 없음
- Ellinia replay: 1 유지, 저장 불필요
- Perion: 1→2/A 및 0→2 직행
- 3→Ellinia: 3 유지
- Grade: 0/NONE, 1/B, 2/A, 3/S, 4/SS, 5+/SSS
- Multi-job 3+2+1+0+0: 총 6점
- Total 6, MAX_HP Lv.2 사용 2, Available 4
- 합성 DataStorage 재접속: warrior 1/B/총 1 유지, replay 개선 없음

실사용 개발 계정에서 Henesys→Ellinia→Perion 런을 강제로 진행해 영구 값을 0→2로 바꾸는 검증은 권한 안전장치가 차단해 수행하지 않았다. 구현/데이터/합성 persistence와 Play 런타임 로드는 검증 완료했다.

## 21. NEW STEP 4 구현 결과

### Allocation Mutation

`UnionStatAllocationServiceLogic`은 클라이언트 의도가 될 수 있는 `StatId`와 요청 ID만 받아 서버 정의와 현재 프로필을 다시 조회한다. 실제 저장은 `UnionProfileRepositoryLogic`의 기존 프로필별 mutation lock과 DataStorage CAS 경계 안에서 한 번 더 검증한 뒤 `AllocatedUnionStats[StatId]`만 1 증가시킨다.

클라이언트가 보낸 PointCost, NextLevel, EffectValue, MaxLevel, RequiredUnionRank, IsImplemented, Total/Available 값은 입력 계약에 없으며 신뢰하지 않는다. 개별 감소와 프리셋은 구현하지 않았다.

### Total / Spent / Available

- `TotalUnionStatPoints`: 다섯 `JobUnionProgress` → Job Grade → `StatPointContribution` 합으로 매번 파생
- `SpentUnionStatPoints`: 각 `AllocatedUnionStats[StatId]`의 1..Level `UnionStatLevelDefinitions.PointCost` 합으로 매번 파생
- `AvailableUnionStatPoints = Total - Spent`

세 값은 Schema 5에 저장하지 않는다. 유효한 mutation은 Available을 음수로 만들 수 없으며, 저장 데이터에서 Spent가 Total보다 크면 손상 프로필로 거절한다.

### Server Validation

Increase는 프로필/StatId/정의/구현 상태/현재 레벨/다음 레벨/MaxLevel/현재 Union Rank/필요 Rank/PointCost/총점/사용점/잔여점을 서버에서 확인한다. 사전 확인 후 프로필 mutation lock을 획득하고 최신 캐시를 같은 규칙으로 다시 확인한 뒤 CAS 저장한다.

동일 요청 ID는 사용자별 최대 64건의 bounded world-session receipt로 중복 처리한다. 같은 ID와 같은 intent 재시도는 다시 증가하지 않고 현재 권위 스냅샷을 반환하며, 같은 ID를 다른 Stat/동작에 재사용하면 `ALLOCATION_REQUEST_ID_CONFLICT`로 거절한다. 잠금 충돌과 저장 충돌 같은 일시 오류는 receipt로 고정하지 않아 안전한 재시도가 가능하다.

### Free Full Reset

`TryResetUnionStats`는 무료이며 `AllocatedUnionStats`만 `{}`로 원자 교체한다. Union Coin, Lifetime Growth, Job 진행도, `PurchasedLevels`를 변경하지 않는다. 이미 빈 상태의 Reset은 성공적인 no-op이고 동일 요청 재시도도 추가 mutation을 만들지 않는다.

### Rank Locks

현재 Rank는 `LifetimeUnionPoints`에서 `UnionRankDefinitions`로 파생한다. Stat 정의와 다음 레벨 정의의 `RequiredUnionRank` 중 높은 요구치를 사용하며, Job Grade는 Rank 잠금 판정에 사용하지 않는다.

### Unimplemented Stat Lock

`STARTING_RANDOM_RELIC`, `ADDITIONAL_SKILL_UNLOCK`처럼 `IsImplemented=false`인 Stat은 `STAT_NOT_IMPLEMENTED`로 거절한다. 저장 프로필에 이런 배분이 이미 존재해도 정상으로 해석하지 않고 `ALLOCATED_UNION_STAT_NOT_IMPLEMENTED` 손상으로 로드를 거절한다.

### Malformed Allocation Policy

알 수 없는 StatId, 음수/분수 레벨, MaxLevel 초과, 미구현 Stat 배분, Rank 미충족 배분, Spent > Total은 자동 삭제나 재분배 없이 `PROFILE_VALIDATION_FAILED`로 거절하고 서버 로그에 남긴다. JSON 빈 맵 마커와 명시적 0레벨만 기존 canonical 규칙에 따라 제거한다.

### Legacy Effect Separation

NEW STEP 4 시점에는 `AllocatedUnionStats`가 활성 저장 데이터였지만 gameplay 입력은 아니었다. 당시 `PurchasedLevels`가 임시 Legacy 효과 원본이었고 신규 효과 cutover는 NEW STEP 5로 이관했다.

## 22. NEW STEP 5 구현 결과

### Effect Source Cutover

production 효과 원천은 원자적으로 `PurchasedLevels`에서 `AllocatedUnionStats`로 교체했다. `UnionEffectResolverLogic:GetEffectSnapshot(Entity)`와 `ResolveFromProfile(table)` 출력 계약, `UnionEffectSnapshot`, `PlayerRunUnionEffectComponent:CaptureForRun` 이후의 gameplay 소비 계약은 유지했다. gameplay owner는 `AllocatedUnionStats`를 직접 읽지 않는다.

각 `AllocatedUnionStats[StatId] = Level`은 `UnionStatDefinitions`의 `EffectType`과 `UnionStatLevelDefinitions`의 **현재 Level 행**을 조회한다. 현재 행의 `EffectValue`는 그 레벨의 누적 총효과이므로 이전 레벨 행을 합산하지 않고 정확히 한 번 적용한다. 예를 들어 Meso Lv2는 `0.05 + 0.10`이 아니라 `0.10`이다.

### Union Effect Mapping

| StatId | 기존 UnionEffectSnapshot 필드 | 실제 소비처 |
|---|---|---|
| `MAX_HP` | `MaxHPBonus` | `PlayerRunStateComponent.ApplyJobBundle`의 Job Max HP 초기화 |
| `MESO_GAIN_RATE` | `MesoGainRate` | run gold reward 정수 내림 배율 |
| `ITEM_DROP_RATE` | `ItemDropRate` | 비보장 drop chance permille 배율 |
| `UNION_COIN_GAIN_RATE` | `UnionPointGainRate` | 기존 Union reward 배율. 저장은 `UnionPoints`, 의미는 Union Coin |
| `STARTING_POTION` | `StartingPotionBonus` | run inventory의 시작 `potion_hp_small` 지급 |
| `INVENTORY_SLOT` | `InventorySlotBonus` | run consumable capacity 초기화 |
| `AUGMENT_REROLL` | `AugmentRerollBonus` | run augment reroll allowance 초기화 |
| `STARTING_SKILL` | `StartingSkillBonus` | 선택 Job의 시작 스킬 슬롯/유효한 authored 스킬 초기화 |

### Legacy PurchasedLevels Status

`PurchasedLevels`는 Schema 5에 저장되고 환급 검증·debug·후속 cleanup을 위해 보존된다. 신규 구매는 계속 `LEGACY_UNION_SYSTEM_DISABLED`이며, Resolver는 값의 존재·레벨·손상 여부까지 참조하지 않는다. 빈 `AllocatedUnionStats`는 Legacy 구매 레벨과 무관하게 모든 gameplay 보너스가 0이다.

### Run Snapshot Freeze

Resolver 결과는 run 시작 때 player-owned `PlayerRunUnionEffectComponent`에 한 번 복사된다. 같은 `RunSequence`의 재캡처는 `RUN_SNAPSHOT_ALREADY_CAPTURED`로 기존 값을 반환한다. 런 중 배분 초기화는 현재 HP/보상/인벤토리/증강/스킬 효과를 바꾸지 않고 다음 run의 새 캡처부터 반영된다.

### Unimplemented Effect Behavior

`STARTING_RANDOM_RELIC`, `ADDITIONAL_SKILL_UNLOCK`은 계속 `IsImplemented=false`다. Allocation Service와 프로필 검증이 배분을 거절하고, Resolver도 이런 손상 배분을 `PROFILE_VALIDATION_FAILED / ALLOCATED_UNION_STAT_NOT_IMPLEMENTED`로 명시 거절한다. `StartingRandomRelicBonus` 호환 필드는 0으로 유지할 뿐 실제 효과를 생성하지 않는다.

### Next Cleanup

`PurchasedLevels`의 저장 스키마 제거는 신규 Union UI와 전체 시스템 검증 이후 별도 schema migration으로 수행한다. NEW STEP 5에서는 SchemaVersion 5, 기존 UI, Reset/Increase 동작을 유지하며 개별 감소와 프리셋을 구현하지 않는다.

## 23. NEW STEP 6 — 2026 Allocation UI Cutover

### Final Information Architecture

- 좌측 상단: BASIC 4장 + EXPANDED 4장의 고정 4×2 스탯 카드 그리드
- 좌측 하단: warrior / mage / archer / thief / pirate 직업별 Grade·Progress·기여 포인트 카드
- 우측: 현재 Union Rank, Union Coin, Lifetime Growth, Total/Spent/Available Point, 활성 효과
- 하단 제어: 각 스탯의 [+]와 무료 전체 초기화만 제공
- 미래 표시: STARTING_RANDOM_RELIC, ADDITIONAL_SKILL_UNLOCK은 UNION V · 준비 중 잠금 카드이며 상호작용이 없다.

개별 감소, Min/Max, 프리셋, 활성 Loadout, 블록 구매, 보드 배치, Battle Map, BoardTier는 UI 계약에 없다. 닫기/Escape와 Lobby Union NPC의 OpenWindow/CloseWindow 흐름은 유지한다.

### Authoritative UI Contract

창을 열 때와 Increase/Reset 처리 후마다 서버에서 다음 두 스냅샷을 새로 조회한다.

1. UnionStatAllocationServiceLogic:GetUnionStatAllocationSnapshot
2. UnionEffectResolverLogic:GetEffectSnapshot

클라이언트는 Increase에서 StatId와 멱등 요청 ID만 보내며 PointCost, NextLevel, Rank, EffectValue를 보내지 않는다. Reset도 요청 ID만 보낸다. 서버 결과가 도착할 때까지 모든 [+]와 Reset을 비활성화하고, mutation 결과와 최신 authoritative snapshot을 같은 request sequence로 다시 렌더링한다.

### Legacy Boundary

UnionSystemUILogic은 PurchasedLevels, UnionUpgradeDefinitions, UnionBlockShopServiceLogic, Board/Region/Cell/BoardTier를 읽지 않는다. PurchasedLevels와 Legacy 데이터 파일은 후속 schema cleanup 전까지 저장·감사용으로만 유지하고 UI에는 표시하지 않는다.

### Maker / Play Verification

- UIBuilder의 교체 서브트리는 형제 `displayOrder`를 0부터 재정규화한다. 교체 전 카운터가 남긴 순서 공백 때문에 Maker가 자식을 마운트하지 않는 문제를 Play에서 발견하고 수정했다.
- 실제 권위 스냅샷으로 `stats=10`, `jobs=5`, UNION I, Coin/Point 0 상태를 열고 닫기/Escape/재오픈을 확인했다.
- 합성 presenter 스냅샷으로 0 진행, 전사 A +2·마법사 B +1·나머지 - +0(총 3), MAX_HP 0→1, 무료 Reset 1→0, UNION I Rank lock, 두 미래 Stat의 준비 중 표시를 확인했다. 합성 allocation/reset 전후 Coin 777은 바뀌지 않았다.
- 로비 `UnionManagerNPC`의 단독 형제 `displayOrder=14`를 MapBuilder로 0으로 정규화해 런타임에서 `LobbyInteraction ready id=Union`이 다시 생성되도록 했다. `LobbyInteractionComponent.OnInteract → UnionSystemUILogic.OpenWindow → authoritative snapshot` 경로와 Escape close를 Play에서 확인했다.
- 최종 Play 구간에는 Union runtime Error/Warning이 없었다. Build에는 범위 밖의 기존 `GetSnapshotAmount` 인자 수 경고 1건만 남아 있다.
