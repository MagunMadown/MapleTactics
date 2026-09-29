# Union 2026 Migration Audit

> 기준일: 2026-08-31
> 범위: STEP 0 감사 + NEW STEP 2~5 구현 결과 반영
> 기준 변경: 전투지도/블록 배치 제거, 직업 등급 합산 스탯 포인트 배분 방식으로 전환

## 1. 결론

현재 Union 구현은 완전한 블록 배치 시스템이 아니라, **기존 구매형 업그레이드 시스템 위에 블록 소유/상점만 추가된 중간 상태**다. 플레이어가 블록을 배치하거나 블록으로 효과를 얻는 경로는 없지만, 저장 스키마에는 블록 소유와 구매 영수증이 이미 들어가 있다.

따라서 안전한 전환 방향은 다음과 같다.

- 유지: 프로필 저장 경계, 보상 커밋/멱등성, 랭크 진행, 효과 Resolver와 Run Snapshot, 구현 완료된 게임플레이 소비처, 로비 NPC 진입과 창 외곽 구조
- 변환: `UnionPoints`, `LifetimeUnionPoints`, `PurchasedLevels`, Union 업그레이드/레벨/보상/랭크 데이터
- 제거 예정: 전투지도, 96셀, 블록 모양/소유/상점, BoardTier와 배치 관련 UI·저장 필드·서비스
- 신규: 직업별 성장도, 직업 등급, 등급 합산 스탯 포인트, Basic/Expanded 배분, 무료 초기화

NEW STEP 2~5에서 Schema 5 전환과 1회성 Legacy 환급, 구매 동결, 직업 성장/등급/포인트 파생, 서버 배분/무료 초기화, `AllocatedUnionStats` 기반 Resolver cutover를 완료했다. 신규 2026 Union UI, 개별 감소, 프리셋, 미구현 효과는 후속 범위다.

## 2. 감사 기준과 확인 경로

주요 확인 대상은 다음과 같다.

- 저장/보상: `RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.mlua`, `UnionRewardServiceLogic.mlua`
- 랭크/효과: `UnionRankProgressionLogic.mlua`, `UnionEffectResolverLogic.mlua`
- 블록: `UnionBlockShopServiceLogic.mlua`, `RootDesk/MyDesk/03_Data/Repositories/UnionBlock*`, `UnionBoardDefinitionRepositoryLogic.mlua`
- 직업/런: `RootDesk/MyDesk/03_Data/JobDefinitions.csv`, Lobby 선택 → BattleGateway → RunManager → BattleSession 경로
- 효과 소비처: `PlayerRunUnionEffectComponent.mlua`, RunManager, BattleSession, BattleDrop, 인벤토리/증강 시스템
- UI: `ui/UnionSystemUI.ui`를 UIBuilder로 읽어 확인했으며 현재 엔티티 수는 208개다.
- 에셋: 검증된 `msw-search` 리소스 API를 한국어/영어 현재형 Union UI 키워드로 재검색하고 상세 조회했다.

## 3. 현재 저장 스키마

### 3.1 정확한 버전과 필드

STEP 0 감사 당시 버전은 4였고, NEW STEP 2 완료 후 `UnionProfileRepositoryLogic.CurrentSchemaVersion`은 **5**다.

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

저장 키는 `UnionProfile`이며 서버 `UserDataStorage`를 사용한다. `ProfileCode`를 우선하고 `UserId`를 대체 키로 사용한다. 기존 프로필 갱신은 `UpdateAndWait`, 최초 저장은 `SetAndWait` 패턴이며, 프로필 단위 잠금과 보상/구매 영수증이 있다.

### 3.2 현재 필드의 정확한 의미

| 필드 | 현재 의미 | 2026 설계와의 관계 |
|---|---|---|
| `UnionPoints` | 저장명은 유지하며 플레이어/도메인 의미는 **Union Coin** | Legacy 구매액 환급도 이 값에만 더함. 스탯 포인트로 사용 금지 |
| `LifetimeUnionPoints` | 저장명은 유지하며 의미는 **Lifetime Union Growth** | 환급으로 증가하지 않으며 Union Rank 원본 유지 |
| `PurchasedLevels` | 환급 후 구매가 동결된 Legacy read-only 저장 데이터 | production Resolver는 무시하며 후속 schema cleanup까지 보존 |
| `ActiveLevels` | Schema 4에 저장되지 않으며 활성 로직도 없음 | 조치 불필요. 레거시 입력은 정규화 과정에서 무시 |
| `OwnedUnionBlocks` | 구매한 블록 수량 | 환급 검증 후 Schema 5 저장에서 제거 |
| `BlockPurchaseReceipts` | 블록 구매 요청 멱등 영수증 | 실제 비용 환급 검증 후 Schema 5 저장에서 제거 |

`AddUnionPoints`와 현재 Union 보상 커밋은 두 값을 함께 증가시키지만 두 값의 검증은 독립적이다. 환급으로 `UnionPoints > LifetimeUnionPoints`가 되어도 정상이다.

### 3.3 예상과 달랐던 블록 저장 상태

- 존재: `OwnedUnionBlocks`, 블록 구매 영수증, 실제 Union Coin 차감, 블록 상점 UI/RPC
- 없음: `PlacedUnionBlocks`, 배치 좌표/회전, 배치 저장, 배치 검증 서비스, 블록 유래 효과
- 결과: “블록 기능이 플레이어 데이터에 없다”가 아니라 **“소유/상점 데이터만 있고 배치 데이터는 없다”**가 정확하다.

## 4. 현재 Union 랭크

`UnionRankDefinitions.csv`는 다음 다섯 단계다.

| RankId | 누적 임계치 | 기존 Tier |
|---|---:|---:|
| `UNION_I` | 0 | 1 |
| `UNION_II` | 1,000 | 2 |
| `UNION_III` | 3,000 | 3 |
| `UNION_IV` | 7,000 | 4 |
| `UNION_V` | 15,000 | 5 |

`UnionRankProgressionLogic`은 `LifetimeUnionPoints`에서 가장 높은 충족 임계치를 선택한다. 이 **누적 성장 → 데이터 기반 랭크 → 랭크업 알림** 구조는 재사용 가능하다. 단, `BoardTier`와 보드 영역 해금 의미는 폐기하고 Expanded 스탯 해금, 스탯 상한, 향후 기능 해금 메타데이터로 바꿔야 한다.

## 5. 실제 직업과 현재 진행 경로

### 5.1 실제 JobId 다섯 개

`JobDefinitions.csv`에 활성화된 실제 JobId는 아래와 같다.

| JobId | 표시명 | 기본 최대 HP | 기본 Queue | 무기 계열 |
|---|---|---:|---:|---|
| `warrior` | 전사 | 10 | 3 | `ONE_HANDED_SWORD` |
| `mage` | 마법사 | 7 | 3 | `WAND` |
| `archer` | 궁수 | 8 | 3 | `BOW` |
| `thief` | 도적 | 8 | 4 | `DAGGER` |
| `pirate` | 해적 | 12 | 3 | `GUN` |

### 5.2 현재 직업 선택은 영구 진행도가 아니다

현재 선택은 다음 경로로 런에 전달된다.

`TemporaryClassSelectionStateComponent.SelectedJobId`
→ `LobbyStartButtonComponent`
→ `BattleGatewayLogic` / `BattleEntryStateComponent.JobId`
→ `RunManagerLogic:ApplyJobSelection`
→ `PlayerRunStateComponent.SelectedJobId`
→ `BattleSessionComponent.SelectedJobId`

이 값은 런 단위 상태이며 패배/새 런에서 초기화된다. 현재는 직업별 영구 성장도나 B/A/S/SS/SSS 등급 저장이 없다.

### 5.3 직업 등급 진행도의 권장 원천

권장 원천은 **실제 선택 JobId로 완료한 권위 있는 전투 결과에서 지급되는 직업별 누적 성장도**다.

- `StageClear`: 모든 승리
- `BossClear`: `StageType == BOSS`인 승리
- `RunClear`: `RUN_COMPLETED` 또는 종결 전투
- 귀속 JobId: 결과 처리 시점의 `PlayerRunStateComponent.SelectedJobId`
- 멱등 키: 현재 전투 결과 키/Union 보상 커밋 패턴 재사용

단순 런 횟수는 보스와 종결 성과의 차이를 표현하지 못하고, 최고 스테이지는 분기형 맵에 취약하며, 보스 처치만 사용하면 진행 빈도가 너무 낮다. 현재 존재하는 세 트리거에 가중치를 부여한 `JobUnionProgress[jobId]`가 가장 잘 맞는다.

## 6. 현재 보상 파이프라인

`UnionRewardDefinitions.csv`의 현재 행은 다음과 같다.

| RewardId | Trigger | Amount |
|---|---|---:|
| `STAGE_CLEAR_ANY` | `StageClear` | 15 |
| `BOSS_CLEAR_ANY` | `BossClear` | 20 |
| `RUN_CLEAR_ANY` | `RunClear` | 20 |

런 시작 시 단조 증가 `RewardRunId`를 확보하고, 전투 결과마다 대기 보상을 쌓은 뒤 패배 또는 런 클리어 때 `union_run:<RewardRunId>` 키로 한 번만 커밋한다. 이 구조는 유지할 가치가 높다. 새 설계에서는 한 행의 단일 Amount를 `CoinAmount`, `LifetimeGrowthAmount`, `JobGrowthAmount`로 분리해 각 개념을 독립 조정해야 한다.

## 7. 현재 효과 적용 파이프라인

NEW STEP 5 이전 경로는 다음과 같았다.

`UnionProfile.PurchasedLevels`
→ `UnionEffectResolverLogic:ResolveFromProfile`
→ `UnionEffectSnapshot`
→ `PlayerRunUnionEffectComponent:CaptureForRun`
→ 각 게임플레이 소유 시스템

NEW STEP 5 완료 후 production 경로는 다음과 같다.

`UnionProfile.AllocatedUnionStats`
→ 동일 Resolver 계약
→ 동일 Run Snapshot
→ 동일 게임플레이 소유 시스템

게임플레이 시스템이 프로필 또는 배분 테이블을 직접 읽게 만들면 안 된다.

### 7.1 효과별 구현 상태

| 후보 효과 | 현재 EffectType | 상태 | 재사용/추가 작업 |
|---|---|---|---|
| Meso Gain | `MESO_GAIN_RATE` | 구현됨 | `GrantRunReward`의 `gold` 지급 배율 경로 재사용. UI 명칭은 Meso/Gold 정합성 검토 |
| Item Drop Rate | `ITEM_DROP_RATE` | 구현됨 | 비보장 드롭 확률에만 배율 적용, 0..1000 clamp와 안정 시드 경로 재사용 |
| Union Coin Gain | `UNION_POINT_GAIN_RATE` | 구현됨(구 명칭) | 효과 의미를 `UNION_COIN_GAIN_RATE`로 명시 변경하고 호환 매핑 제공 |
| Max HP | `MAX_HP` | 구현됨 | 런 시작 Job Bundle에 보너스 적용하는 경로 재사용 |
| Starting Potion | `STARTING_POTION` | 구현됨 | 인벤토리 초기화 뒤 `potion_hp_small` 지급 경로 재사용 |
| Augment Reroll | `AUGMENT_REROLL` | 구현됨 | 증강 런 상태의 초기 재굴림 수 보너스 경로 재사용 |
| Starting Skill | `STARTING_SKILL` | 구현됨 | 시작 스킬 슬롯 증가 경로 재사용. 작성된 시작 스킬 수가 실질 상한 |
| Inventory Slot | `INVENTORY_SLOT` | 구현됨 | 소모품 기본 용량 + 보너스 초기화 경로 재사용 |
| Starting Random Relic | `STARTING_RANDOM_RELIC` | 미구현 | 호환 Snapshot 필드는 0, 배분과 Resolver는 명시 거절. 유물 저장소·랜덤 선택·지급 소유자 없음 |
| Additional Skill Unlock | 기존 보드 허용 문자열만 존재 | 미구현 | Resolver 필드, 런 스냅샷, 스킬 소유/해금 규칙 모두 필요 |
| Future Union Character Effects | 없음 | 미구현/예약 | 구체 EffectType와 실제 소비 시스템이 생길 때만 추가 |

## 8. 데이터 파일 재사용성

### 8.1 변환 가치가 높은 파일

| 현재 파일 | 현재 내용 | 권장 변환 |
|---|---|---|
| `UnionUpgradeDefinitions.csv/.userdataset` | 9개 효과의 ID, 표시명, 설명, EffectType, MaxLevel, 정렬 | `UnionStatDefinitions`로 변환. `BoardRegion`, `IsMajor`, 구매 전제조건 의미 제거 |
| `UnionUpgradeLevels.csv/.userdataset` | 25개 레벨의 누적 효과값, 구매 비용, 랭크 조건 | `UnionStatLevels`로 변환. 효과값/랭크 조건은 재사용, Coin Cost는 새 PointCost로 그대로 복사하지 않음 |
| `UnionRankDefinitions.csv/.userdataset` | 누적 임계치와 5단계 랭크 | 랭크/임계치/표시 정보 유지, BoardTier를 Expanded/Cap 해금 메타데이터로 교체 |
| `UnionRewardDefinitions.csv/.userdataset` | Stage/Boss/Run 보상 | Coin/Growth/JobGrowth 세 값을 갖는 보상 정의로 확장 |

현재 구매 비용은 100 단위 이상인 반면 새 스탯 포인트는 직업 등급 합산으로 최대 25점 규모다. 따라서 기존 `Cost`를 새 `PointCost`로 기계적으로 복사해서는 안 된다.

### 8.2 폐기 대상 데이터

- `UnionBlockDefinitions.csv/.userdataset`
- `UnionBlockShapeDefinitions.csv/.userdataset`
- `UnionBoardCellDefinitions.csv/.userdataset` — 현재 96셀
- `UnionSpecialZoneDefinitions.csv/.userdataset`

## 9. 블록/전투지도 아티팩트 분류

### KEEP

- `UnionProfileRepositoryLogic`: 저장 경계, 잠금, clone/normalize, CAS 패턴
- `UnionRewardServiceLogic`: 런 보상 누적과 멱등 커밋 패턴
- 블록 구매 구현에서 검증된 요청 ID/영수증 설계 원칙만 재사용
- 현재 Union UI의 외곽 창, 닫기/새로고침, 서버 스냅샷 요청/응답 패턴

### REPLACE

- `UnionEffectResolverLogic`의 입력: `PurchasedLevels` → `AllocatedUnionStats`
- `UnionRankDefinitionRepositoryLogic`의 BoardTier 출력 → Expanded/Cap 해금
- `UnionSystemUILogic`의 구매/노드/보드 바인딩 → 직업 등급 및 Basic/Expanded 배분 바인딩
- `UnionPoints`/`LifetimeUnionPoints` 표시 → Coin/Growth/Stat Point 3종 표시

### REMOVE_LATER

- `RootDesk/MyDesk/00_Core/UnionBlockShopServiceLogic.mlua`와 짝 `.codeblock`
- `UnionBlockDefinitionRepositoryLogic`, `UnionBlockShapeDefinitionRepositoryLogic`, `UnionBoardDefinitionRepositoryLogic`와 짝 `.codeblock`
- 위 8.2의 블록/보드 데이터 쌍
- 프로필의 `OwnedUnionBlocks`, `NextBlockPurchaseReceiptOrder`, `BlockPurchaseReceipts`
- 블록 구매/소유 API와 UI RPC
- `ui/UnionSystemUI.ui` 안의 `BlockShopButton`, `BlockShopPanel`, 블록 카드/미리보기/구매 버튼

### NO_LONGER_NEEDED

- 96셀 `GridCellLayer`
- `BattleMapBackdrop`, 4개 Region, Core, 연결선/영역/BoardTier 표현
- I3 모양, 셀 좌표/회전, 보드 연결/영역 확장이라는 도메인 개념
- 9개 업그레이드 노드를 보드 위치에 하드코딩하는 경로

### ARCHIVE_DOC_ONLY

구현 전환 완료 후 다음 문서는 삭제하지 말고 역사 자료로 Archive 이동하는 편이 안전하다.

- `Docs/UnionBlockMigrationPlan.md`
- `Docs/UnionBlockDataDesign.md`
- `Docs/UnionBlockSystemAudit.md`의 블록 관련 결론
- `Docs/UnionAssetAudit.md`의 전투지도/블록 에셋 부분

이번 STEP 0에서는 어떤 파일도 이동하거나 삭제하지 않는다.

## 10. 현재 UI 감사

### 유지 가능한 구조

- 로비 `UnionManagerNPC`와 `[E] 유니온 관리` 진입
- `UnionWindow` / `UnionFrame` 외곽 Maple 스타일 셸
- Header, Close, Refresh
- `RightPanel`의 정보 요약 영역
- Union Rank 표시와 Rank-up toast
- 적용 효과 요약 영역
- 서버 권위 스냅샷 요청/응답과 로비에서만 여는 제약

### 교체해야 하는 구조

- 전체 `BoardPanel`, 96셀, Region/Core/배경/노드
- 업그레이드 선택 → 상세 → UnionPoints 구매 흐름
- Major 구매 확인창
- Block Shop 전체
- `CurrentUnionPoints`, `LifetimeUnionPoints` 라벨과 의미

새 화면의 주 영역은 Job Grade 요약과 Basic/Expanded 스탯 목록이어야 하며, 오른쪽에는 Rank, Growth, 총/사용/잔여 Stat Point, Union Coin, 적용 효과를 배치하는 것이 현재 셸을 가장 적게 흔든다.

## 11. 현재형 Union 에셋 재검색

재검색 키워드는 `유니온`, `유니온 스탯`, `스탯 설정`, `유니온 프리셋`, `Union Stat`, `Union Preset`, `Union UI`, `Union Rank`, `Union Coin`이었다. Resource Pack 우선 검색 뒤 sprite 상세 조회를 수행했다.

### 검증 완료

| 용도 | 이름 | RUID | 판정 |
|---|---|---|---|
| Union Coin | 유니온 코인, 28×28 sprite/item | `95632823c5e44dab89b9859ff439165b` | 새 Coin 표시에서 직접 사용 가능 |
| 향후 프리셋 관련 아이템 | 유니온 프리셋 쿠폰, 32×24 sprite/item | `3575be5e97b04c5fa67662e006aee13b` | 쿠폰 아이콘일 뿐 프리셋 버튼이 아님. 프리셋 구현 전에는 사용하지 않음 |
| 현재 로비 관리자 대체 NPC | 나인하트 stand animationclip | `c2919dc57fac457c9ce94fe32f8b69d2` | 프로젝트에서 사용 중인 대체 관리자. 공식 Union NPC라고 주장하지 않음 |

### 채택하지 않은 결과

- `16134c59ea6641ed8cc1f20bdd4486da`, `2df3149a9c3149708af9739f51d9c129`: “유니온 스탯 UI” 의미 검색에 나온 이름 없는 232×52 UI 조각. 출처 경로/상태 관계가 없어 미검증 처리
- `d753b8a54bff4e01a4c49e83b4cbc1c9`, `a6fa6d6ad3de40e4951281b5ff746a29`: 프리셋 의미 검색 후보. 후자는 기존 감사에서 장비 코디 프리셋 버튼으로 판명되어 Union 전용으로 사용 불가
- `83f4c25c940e49aca6f240619ba4ff6c`, `2aefbe890905430ca0afe18a5a9bc96f`: 검증된 Union Raid 배경/소품이나 새 설계는 Battle Map을 제거하므로 사용하지 않음
- 검색 결과의 Union Aura 스킬, Union PVP mob, 랭킹 게시판은 관리 UI가 아니므로 제외

정확한 최신 Union 관리 창, Basic/Expanded 탭, 랭크 배지, +/- 배분 컨트롤은 공식 검색 인덱스에서 검증되지 않았다. 구현 전 Maker 수동 리소스 탐색이 필요하며, 그 전에는 현재 프로젝트의 일반 Maple 스타일 프레임을 명시적 대체재로만 사용한다.

## 12. 주요 마이그레이션 위험

1. 현재 스키마 정규화는 알 수 없는 블록 ID를 제거한다. 레거시 환급 전에 데이터 정의를 먼저 제거하면 소유 증거를 잃을 수 있다.
2. `PurchasedLevels`는 Coin으로 구매한 값이다. 이를 새 Stat Point 배분으로 그대로 옮기면 등급으로 얻지 않은 포인트가 생성된다.
3. `UnionPoints`를 이름만 `UnionStatPoints`로 바꾸면 소비 화폐와 배분 한도가 다시 혼합된다.
4. 직업 등급을 저장 값과 성장도에서 동시에 관리하면 불일치가 생긴다. 성장도를 원본으로, 등급은 데이터 기반 파생값으로 유지해야 한다.
5. Resolver를 우회해 각 게임플레이 시스템이 배분 데이터를 읽기 시작하면 런 스냅샷의 결정성과 재현성이 깨진다.
6. 아직 소비처가 없는 Starting Random Relic/Additional Skill Unlock을 UI에서 활성화하면 표시 수치만 오르는 가짜 기능이 된다.

## 13. 감사 판정

2026 전환은 기존 시스템 전면 폐기보다 **저장/보상/랭크/효과 파이프라인을 보존하고, 입력 모델과 UI를 교체하는 마이그레이션**으로 진행하는 것이 맞다. 상세 데이터 계약, 배분 규칙, 마이그레이션과 최소 수직 슬라이스는 `Docs/Union2026Design.md`에 정의한다.

## 14. NEW STEP 2 마이그레이션 판정

실제 구현은 감사에서 확인한 저장 경계를 유지하고 다음과 같이 확정했다.

1. 환급은 `NormalizeProfile`이 Schema 4 이하 원본을 읽을 때 계산한다.
2. 업그레이드는 `PurchasedLevels`의 각 도달 레벨 비용을 Legacy 레벨 정의에서 합산한다.
3. 블록은 영수증이 소유 수량 전체를 연속적으로 증명하면 실제 영수증 비용을 사용한다.
4. 영수증이 전혀 없는 소유 블록만 권위 있는 정의 가격으로 환급한다.
5. 부분 영수증, 중복 순서/수량, 소유 없는 영수증, 알 수 없는 ID, 음수/비정수 값은 데이터 유실 없이 실패한다.
6. 환급액은 `UnionPoints`에만 더하고 `LifetimeUnionPoints`, Job 진행도, Stat 배분에는 반영하지 않는다.
7. Schema 5 전체 후보를 검증한 뒤 기존 `UpdateAndWait` CAS 한 번으로 저장하므로, 성공한 Schema 5가 1회성 환급의 멱등 마커가 된다.
8. 저장 실패 시 캐시를 갱신하지 않으므로 다음 로드에서 Schema 4 원본으로 동일 계산을 재시도한다.
9. 저장 성공 후 블록 소유/구매 영수증은 canonical 데이터에서 사라진다.
10. NEW STEP 2 당시 `PurchasedLevels`는 기존 Resolver의 임시 효과 원본으로 유지하고 신규 구매만 차단했다. NEW STEP 5에서 production 효과 원천을 `AllocatedUnionStats`로 교체했다.

Maker 검증에서 Schema 4→5 정상/결합/재실행, JSON 왕복, 손상 데이터 거부, 효과 parity, 구매 동결이 통과했다. 또한 실사용 계정 대신 고유한 합성 DataStorage 키로 Schema 4 저장 → Schema 5 CAS → 캐시 제거/재로드를 검증해 환급과 신규 필드가 지속되고 두 번째 환급이 없음을 확인했다. 실사용 프로필에 구매 mutation을 강제로 호출하는 검증은 영구 데이터 변형 위험 때문에 수행하지 않았다.

## 15. NEW STEP 5 Effect Source Cutover 판정

### Effect Source Cutover

- OLD: `PurchasedLevels → UnionEffectResolverLogic`
- NEW: `AllocatedUnionStats → UnionStatDefinitions/UnionStatLevelDefinitions → UnionEffectResolverLogic`
- 현재 Level 행의 cumulative `EffectValue`를 한 번만 사용한다.
- Resolver public API와 Run Snapshot/gameplay owner 계약은 유지했다.

### Legacy PurchasedLevels Status

`PurchasedLevels`는 Schema 5에 저장되고, Schema 4→5 환급·정규화·검증·복제, legacy inspection API, 교체 전 UI 표시에만 남아 있다. legacy 구매 API는 Schema 5에서 계속 `LEGACY_UNION_SYSTEM_DISABLED`다. Resolver와 combat/roguelike gameplay 보너스 계산에는 `PurchasedLevels` read가 없다.

### Union Effect Mapping

구현된 8개 매핑은 `MAX_HP→MaxHPBonus`, `MESO_GAIN_RATE→MesoGainRate`, `ITEM_DROP_RATE→ItemDropRate`, `UNION_COIN_GAIN_RATE→UnionPointGainRate`, `STARTING_POTION→StartingPotionBonus`, `INVENTORY_SLOT→InventorySlotBonus`, `AUGMENT_REROLL→AugmentRerollBonus`, `STARTING_SKILL→StartingSkillBonus`다. Union Coin은 기존 내부 필드 하나를 재사용하며 이중 gain-rate 필드를 만들지 않았다.

### Run Snapshot Freeze

같은 `RunSequence` 재캡처는 기존 Snapshot을 반환하며, 배분 Reset은 활성 run에 소급되지 않는다. 다음 run은 새 Resolver 결과를 캡처한다. Play의 임시 production owner 엔티티에서 MAX HP `10→11`, 반복 초기화 `11`, 다음 무배분 run `10`을 확인했다.

### Unimplemented Effect Behavior

`STARTING_RANDOM_RELIC`과 `ADDITIONAL_SKILL_UNLOCK`은 `IsImplemented=false`이며 Allocation Service/프로필 검증/Resolver 모두 손상 배분을 명시 거절한다. placeholder gameplay는 만들지 않았다.

### Verification and Next Cleanup

합성 Resolver 검증에서 empty-vs-Legacy 0, MAX HP +1, no-double-stack, Basic 4종, Expanded 4종, 두 미구현 Stat 거절이 통과했다. 임시 Play 엔티티의 실제 production owner에서 Meso/Union Coin `100→105`, drop chance `250→262` permille, 시작 포션 1, inventory `3→5`, reroll 2, 시작 스킬 슬롯 `2→3`을 확인했다. 합성 DataStorage 키 `codex_step5_reconnect_20260831_a6f94c`는 allocation 재로드 `+1`, Reset 직후/재로드 `0`, Schema 5와 `PurchasedLevels` 보존을 확인했다.

`PurchasedLevels` 필드 제거는 신규 UI/전체 시스템 검증 후 별도 schema migration으로 미룬다. SchemaVersion은 5이며 UI redesign, 개별 감소, 프리셋은 이 단계에서 변경하지 않았다.

## NEW STEP 6 UI Cutover Audit

### Replaced Runtime Surface

ui/UnionSystemUI.ui의 기존 UnionWindow 203개 엔티티를 UIBuilder로 제거하고 2026 배분 화면 117개 엔티티로 재구성했다. 루트 UnionSystemUI와 UnionRankUpToast는 보존했다.

제거 확인 대상:

- 96-cell GridCellLayer
- BattleMapBackdrop, Region, path/node, Union Core, BoardTier
- BlockShopPanel과 블록 구매 버튼/상태
- Legacy Upgrade 상세/구매/확인 UI

신규 UnionSystemUILogic의 Legacy 문자열 정적 감사 결과 PurchasedLevels, BoardTier, BlockShop, UnionUpgrade, PurchaseUpgrade, UnionBlock 참조는 모두 0건이다.

### Schema and Gameplay Safety

- SchemaVersion은 계속 5다.
- 저장 필드와 migration/환급 로직은 변경하지 않았다.
- PurchasedLevels와 Legacy 정의/서비스 파일은 삭제하지 않았다.
- gameplay 효과 원천은 계속 AllocatedUnionStats → UnionEffectResolver → run snapshot이다.
- UI mutation은 기존 TryIncreaseUnionStat과 TryResetUnionStats만 호출한다.
- 실제 개발 프로필을 강제로 변경하는 검증은 하지 않고, mutation 검증은 합성 storage key와 거절/no-op 경로를 사용한다.

### Remaining Cleanup

Legacy PurchasedLevels, 블록/보드 데이터, Legacy Repository/Service 실제 파일 제거와 Schema bump는 이번 UI Cutover에 포함하지 않는다. 전체 배포 검증 후 별도 migration으로 수행한다.

### NEW STEP 6 Maker / Play Audit

- UIBuilder 결과: 전체 122 entities, 신규 UnionWindow subtree 117 entities, UI lint error 0 / reserved-zone warning 3.
- old UI string/path audit: Board, Battle, Region, Cell_, BlockShop, UpgradeDetail, Purchase 0건.
- 권위 로드: `UnionUI2026 snapshot ... stats=10 jobs=5`.
- zero visual: 직업 5종 -/+0, Total/Spent/Available 0/0/0, 모든 active Stat Lv0, Reset disabled.
- mixed visual: warrior A/+2, mage B/+1, 나머지 -/+0, Total 3.
- controlled allocation presenter: MAX_HP Lv0→Lv1, 효과 +1, Spent 0→1, Available 1→0, Coin 777 유지.
- controlled reset presenter: MAX_HP Lv1→Lv0, Spent 1→0, Available 0→1, Coin 777 유지.
- lock/not-implemented: UNION I의 STARTING_POTION은 UNION II 잠금, 미래 두 카드는 준비 중이며 버튼이 없다.
- NPC route: MapBuilder로 `UnionManagerNPC`의 stale displayOrder 14→0을 복구했다. Play 로그에서 `ready id=Union`, NPC OnInteract를 호출한 OpenWindow, stats=10/jobs=5 snapshot, Escape close, reopen 최신 snapshot을 확인했다.
- 최종 Play 구간 runtime Error/Warning 0. Build Error 0; 기존 `GetSnapshotAmount` argument-count warning 1은 유지했다.
