# Union Block System — STEP 0 Audit

> Scope: inspection and architecture planning only. No Union Blocks, placement logic, save migration, gameplay change, UI redesign, or production asset change was implemented in this step.

## Verification labels

- **CODE INSPECTED** — production mLua, CSV/UserDataSet registrations, UIBuilder output, and MapBuilder output were inspected statically.
- **MAKER INSPECTED — NOT VERIFIED** — `msw-maker-mcp` (refresh/play/log/screenshot) is not available in this session, so no Maker runtime claim is made.
- **RESOURCE VERIFIED** — the validated `msw-search` resource wrapper returned current resource metadata and tags for the listed RUIDs.
- **NOT VERIFIED** — runtime behavior, DataStorage migration, visual interaction, and play results were not executed because this is an audit-only step.

## 1. Current Union file inventory

### Union-owned implementation files

| Area | Actual path | Role |
|---|---|---|
| Profile/save | `RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.mlua` | Server-authoritative Union profile, DataStorage load/save, mutation lock, reward receipts, upgrade purchase |
| Profile metadata | `RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.codeblock` | Maker-generated script metadata; read-only |
| Effect resolver | `RootDesk/MyDesk/00_Core/UnionEffectResolverLogic.mlua` | Converts purchased upgrade levels into the central effect snapshot |
| Effect metadata | `RootDesk/MyDesk/00_Core/UnionEffectResolverLogic.codeblock` | Maker-generated script metadata; read-only |
| Rank transition | `RootDesk/MyDesk/00_Core/UnionRankProgressionLogic.mlua` | Compares lifetime totals and sends rank-up presentation |
| Rank metadata | `RootDesk/MyDesk/00_Core/UnionRankProgressionLogic.codeblock` | Maker-generated script metadata; read-only |
| Run reward service | `RootDesk/MyDesk/00_Core/UnionRewardServiceLogic.mlua` | Accumulates Stage/Boss/Run reward definitions and commits the run reward once |
| Reward metadata | `RootDesk/MyDesk/00_Core/UnionRewardServiceLogic.codeblock` | Maker-generated script metadata; read-only |
| Union UI controller | `RootDesk/MyDesk/02_UI/UnionSystemUILogic.mlua` | Client UI binding, snapshot RPC, upgrade selection/purchase request, node/cell presentation |
| UI metadata | `RootDesk/MyDesk/02_UI/UnionSystemUILogic.codeblock` | Maker-generated script metadata; read-only |
| Upgrade repository | `RootDesk/MyDesk/03_Data/Repositories/UnionUpgradeDefinitionRepositoryLogic.mlua` | Reads and validates upgrade/level datasets |
| Upgrade metadata | `RootDesk/MyDesk/03_Data/Repositories/UnionUpgradeDefinitionRepositoryLogic.codeblock` | Maker-generated script metadata; read-only |
| Rank repository | `RootDesk/MyDesk/03_Data/Repositories/UnionRankDefinitionRepositoryLogic.mlua` | Reads ranks and derives rank from lifetime total |
| Rank metadata | `RootDesk/MyDesk/03_Data/Repositories/UnionRankDefinitionRepositoryLogic.codeblock` | Maker-generated script metadata; read-only |
| Reward repository | `RootDesk/MyDesk/03_Data/Repositories/UnionRewardDefinitionRepositoryLogic.mlua` | Reads and validates Union run reward definitions |
| Reward metadata | `RootDesk/MyDesk/03_Data/Repositories/UnionRewardDefinitionRepositoryLogic.codeblock` | Maker-generated script metadata; read-only |
| Upgrade definitions | `RootDesk/MyDesk/03_Data/UnionUpgradeDefinitions.csv` | Nine old upgrade-node definitions |
| Upgrade registration | `RootDesk/MyDesk/03_Data/UnionUpgradeDefinitions.userdataset` | Registers the CSV as an MSW UserDataSet |
| Upgrade levels | `RootDesk/MyDesk/03_Data/UnionUpgradeLevels.csv` | Twenty-five old level/cost/effect/rank/prerequisite rows |
| Level registration | `RootDesk/MyDesk/03_Data/UnionUpgradeLevels.userdataset` | Registers the CSV as an MSW UserDataSet |
| Rank definitions | `RootDesk/MyDesk/03_Data/UnionRankDefinitions.csv` | Five lifetime thresholds and board tiers |
| Rank registration | `RootDesk/MyDesk/03_Data/UnionRankDefinitions.userdataset` | Registers the CSV as an MSW UserDataSet |
| Reward definitions | `RootDesk/MyDesk/03_Data/UnionRewardDefinitions.csv` | StageClear 15, BossClear 20, RunClear 20 base points |
| Reward registration | `RootDesk/MyDesk/03_Data/UnionRewardDefinitions.userdataset` | Registers the CSV as an MSW UserDataSet |
| Run snapshot | `RootDesk/MyDesk/04_Roguelike/RunManager/PlayerRunUnionEffectComponent.mlua` | Immutable-per-run effect copy and pending/committed Union reward state |
| Run snapshot metadata | `RootDesk/MyDesk/04_Roguelike/RunManager/PlayerRunUnionEffectComponent.codeblock` | Maker-generated script metadata; read-only |
| Root UI | `ui/UnionSystemUI.ui` | Current 188-entity Union window, 96-cell board, node hit areas, right panel, confirmation, rank toast |
| Prior integration audit | `Docs/UnionSystemIntegrationAudit.md` | Historical STEP 0 record; portions are stale compared with the current implementation |
| Prior asset audit | `Docs/UnionAssetAudit.md` | Verified/rejected resource history and current fallback asset record |

### Non-Union owners that currently integrate Union

| Actual path | Union responsibility |
|---|---|
| `RootDesk/MyDesk/00_Core/Lobby/LobbyInteractionComponent.mlua` | E-key NPC interaction calls `_UnionSystemUILogic:OpenWindow()` and closes on range exit |
| `RootDesk/MyDesk/04_Roguelike/RunManager/RunManagerLogic.mlua` | Resolves/captures run snapshot; applies HP, skill, inventory, potion, reroll, meso; starts and commits Union rewards |
| `RootDesk/MyDesk/04_Roguelike/RunManager/PlayerRunStateComponent.mlua` | Applies Max HP and starting-skill slot bonuses to run-owned job state |
| `RootDesk/MyDesk/04_Roguelike/RunManager/PlayerRunInventoryComponent.mlua` | Owns run consumable capacity, potion grant, and run skills |
| `RootDesk/MyDesk/04_Roguelike/RunManager/PlayerRunAugmentComponent.mlua` | Owns run reroll count |
| `RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua` | Copies drop rate to battle state, passes it to the real drop resolver, and synchronizes result reward presentation |
| `RootDesk/MyDesk/01_Combat/Components/Shared/BattleDropComponent.mlua` | Passes captured item-drop rate into drop-definition resolution |
| `RootDesk/MyDesk/03_Data/Repositories/EnemyDropDefinitionRepositoryLogic.mlua` | Applies the bonus only to nonzero, nonguaranteed drop chances |
| `RootDesk/MyDesk/02_UI/BattleQueueHudComponent.mlua` | Displays the committed Union run reward on the existing result presentation |
| `map/lobby.map` | Contains the dedicated Union Manager NPC entity |

The whole-project Korean/English search found no separate `UnionCoin`, `UnionCurrency`, `UnionShop`, permanent block ownership, block placement, or `ADDITIONAL_SKILL_UNLOCK` implementation beyond the files described here.

## 2. Current Union architecture

| System | Actual file | Actual API | Current responsibility | Reuse status |
|---|---|---|---|---|
| Profile repository | `RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.mlua` | `GetUnionProfile`, `GetUnionSnapshot`, `AddUnionPoints`, `TryCommitUnionReward`, `TryPurchaseUpgrade`, `ReloadUnionProfile` | Sole custom persistent player-data owner in the project; loads, normalizes, validates, caches, mutates, and persists Union data | **KEEP / EXTEND** |
| Reward identity | same | `AllocateUnionRewardRunId`, `TryCommitUnionReward` | Monotonic reward ID plus retained idempotency receipts | **KEEP** |
| Rank repository | `RootDesk/MyDesk/03_Data/Repositories/UnionRankDefinitionRepositoryLogic.mlua` | `GetRankForLifetimePoints`, `ValidateDefinitions` | Derives the highest reached rank and board tier from lifetime total | **KEEP / MODIFY DEFINITIONS LATER** |
| Rank transition | `RootDesk/MyDesk/00_Core/UnionRankProgressionLogic.mlua` | `NotifyRankTransition`, client rank-up receiver | Rank-up notification only | **KEEP** |
| Upgrade repositories | `RootDesk/MyDesk/03_Data/Repositories/UnionUpgradeDefinitionRepositoryLogic.mlua` | `GetDefinition`, `GetLevelDefinition`, `GetAllDefinitions`, `ValidateDefinitions` | Old node/level/cost/prerequisite content | **DEPRECATE LATER** |
| Upgrade purchase | `RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.mlua` | `CanPurchaseUpgrade`, `TryPurchaseUpgrade` | Server resolves the next level and cost, subtracts currency, persists | **REPLACE SEMANTICS; KEEP MUTATION PATTERN** |
| Central effect resolver | `RootDesk/MyDesk/00_Core/UnionEffectResolverLogic.mlua` | `GetEffectSnapshot`, `ResolveFromProfile`, `CreateEmptyEffectSnapshot`, `ApplyEffectValue` | Converts `PurchasedLevels` into the stable gameplay DTO | **KEEP CONTRACT; REPLACE SOURCE** |
| Stable run snapshot | `RootDesk/MyDesk/04_Roguelike/RunManager/PlayerRunUnionEffectComponent.mlua` | `CaptureForRun`, `GetSnapshot` | Freezes bonuses for one run so lobby changes cannot affect an active run | **KEEP** |
| Run reward service | `RootDesk/MyDesk/00_Core/UnionRewardServiceLogic.mlua` | `BeginRun`, `ProcessBattleResult`, `CommitPendingRunReward` | Data-driven pending reward and authoritative end-of-run commit | **KEEP; RENAME PRESENTATION LATER** |
| Current board UI | `ui/UnionSystemUI.ui`, `RootDesk/MyDesk/02_UI/UnionSystemUILogic.mlua` | `InitializeUpgradeNodePaths`, `InitializeUpgradeCellPaths`, `ApplyTerritoryVisual`, `SubmitPurchaseRequest` | Presents and purchases old upgrade levels on a territory-styled board | **REPLACE INTERACTION/PRESENTATION** |
| Lobby entry | `map/lobby.map`, `RootDesk/MyDesk/00_Core/Lobby/LobbyInteractionComponent.mlua` | `OnInteract` → `_UnionSystemUILogic:OpenWindow()` | Dedicated NPC access | **KEEP** |

Current pipeline:

```text
UnionProfile.PurchasedLevels
  -> UnionEffectResolverLogic
  -> EffectSnapshot
  -> PlayerRunUnionEffectComponent.CaptureForRun
  -> existing gameplay owners
```

The separation is good. Future gameplay code should continue consuming the same snapshot and must never inspect grid cells.

## 3. Current save structure

### Exact stored profile (`StorageKey = "UnionProfile"`, schema 3)

```lua
{
    SchemaVersion = 3,
    UnionPoints = 0,
    LifetimeUnionPoints = 0,
    NextRewardRunId = 0,
    CommittedRewardKeys = {
        ["union_run:<RewardRunId>"] = CommittedAmount
    },
    PurchasedLevels = {
        ["MESO_GAIN_RATE"] = 0,
        ["ITEM_DROP_RATE"] = 0,
        ["UNION_POINT_GAIN_RATE"] = 0,
        ["MAX_HP"] = 0,
        ["STARTING_POTION"] = 0,
        ["AUGMENT_REROLL"] = 0,
        ["STARTING_SKILL"] = 0,
        ["INVENTORY_SLOT"] = 0,
        ["STARTING_RANDOM_RELIC"] = 0
    }
}
```

Persistence details:

- Server-only `_DataStorageService:GetUserDataStorage(storageUserKey)`.
- `ProfileCode` is preferred as identity; `UserId` is fallback.
- JSON uses `_HttpService:JSONEncode` / `JSONDecode`.
- Existing values use `UpdateAndWait(oldRaw, newRaw)`; new values use `SetAndWait`.
- A per-profile mutation lock prevents simultaneous in-process mutations.
- Write conflict `2000000` evicts the cache so a later call reloads authoritative storage.
- Current receipt retention is 64 entries.
- Missing/old saves are normalized to defaults. Unknown upgrade IDs are removed and levels are clamped.
- Schema-3 normalization explicitly ignores legacy `ActiveLevels`, preset, and loadout fields.

No other production mLua file calls `_DataStorageService`. The Union profile repository is therefore the existing persistent architecture to extend; introducing a second Union save system would be a regression.

### Ownership classification

| Data | Classification | Notes |
|---|---|---|
| `UnionPoints` | Server-authoritative persisted | Current spendable balance |
| `LifetimeUnionPoints` | Server-authoritative persisted | Lifetime earned total; never reduced by upgrade purchases |
| `NextRewardRunId` | Server-authoritative persisted | Generates durable reward identities |
| `CommittedRewardKeys` | Server-authoritative persisted | Commit idempotency receipts |
| `PurchasedLevels` | Server-authoritative persisted | Old permanent progression source |
| Union Rank | Derived server data | Highest rank whose threshold is reached; not stored |
| Board tier | Derived server data | `UnlockedBoardTier` from derived rank; not stored |
| Node unlock state | Derived server data | Required rank plus prerequisite upgrade/level |
| Permanent bonus totals | Derived server data | Not stored; resolved from `PurchasedLevels` |
| Run effect snapshot | Server run-scoped transient | Stored on `PlayerRunUnionEffectComponent`, not DataStorage |
| Pending run reward | Server run-scoped transient, target-user synced | Committed only at authoritative run end |
| Selected UI node, hover, request IDs, confirmation | Client-only presentation | Never trusted as price, level, effect, or balance |

### Unique IDs and serialization

- The project currently has no custom persistent item-instance ID implementation.
- Native `_UtilLogic:NewGuid()` exists and returns a 32-character GUID; it is suitable for future placement IDs.
- Nested maps/lists are already viable because the whole profile is JSON encoded.
- No reusable profile serializer beyond the explicit clone/normalize/validate functions exists. Future block fields must receive the same explicit treatment.

## 4. Union Point versus Union Coin

Current code uses only `UnionPoints` / `LifetimeUnionPoints`. There is no `UnionCoin` or `UnionCurrency` field.

- `AddUnionPoints` and `TryCommitUnionReward` add earned amount to both current and lifetime totals.
- `TryPurchaseUpgrade` subtracts only `UnionPoints`.
- Rank uses `LifetimeUnionPoints`, so current balance and lifetime progression are already correctly separated.

Recommended canonical logical currency ID: **`union_coin`**. This follows the existing lower-snake currency ID convention (`gold`) while persisted profile fields can use project-style PascalCase (`UnionCoins`, `LifetimeUnionCoins`).

This can be migrated safely, but it must be an explicit schema migration rather than a search/replace. Until that migration is shipped atomically, player-facing text may say `유니온 코인` while the schema-3 backing field remains `UnionPoints`. Do not make both old and new fields independently writable.

## 5. Current Union Rank

`UnionRankDefinitions.csv` currently contains:

| Rank | Lifetime threshold | Board tier |
|---|---:|---:|
| UNION I | 0 | 1 |
| UNION II | 1,000 | 2 |
| UNION III | 3,000 | 3 |
| UNION IV | 7,000 | 4 |
| UNION V | 15,000 | 5 |

`GetRankForLifetimePoints` sorts definitions by threshold and returns the highest reached row. Rank is not independently saved. This is reusable for board expansion, block shop requirements, and special-zone access. The current tier descriptions and exact thresholds are tuning data and can change later without a save rewrite.

## 6. Current gameplay integrations

| Effect | Actual file | Actual API/function | Applied when | Scope | Safe to reuse? |
|---|---|---|---|---|---|
| `MAX_HP` | `RootDesk/MyDesk/04_Roguelike/RunManager/RunManagerLogic.mlua`; `PlayerRunStateComponent.mlua` | `ApplyJobSelection` → `ApplyJobBundle(..., maxHpBonus)` → `EnsureRunHpInitialized` | Job bundle is first applied for the run | Per-run, initialized once | **YES** |
| `MESO_GAIN_RATE` | `RunManagerLogic.mlua`; `PlayerRunUnionEffectComponent.mlua` | `GrantRunReward` → `CalculateMesoReward` | Actual `gold` currency grant | Per reward using stable run rate | **YES** |
| `ITEM_DROP_RATE` | `BattleSessionComponent.mlua`; `BattleDropComponent.mlua`; `EnemyDropDefinitionRepositoryLogic.mlua` | `ResolveEnemyDeath(..., itemDropRate)` → `ResolveDrops` | Enemy death drop roll | Per roll using stable battle copy | **YES**. Only chances strictly between 0 and 1000 permille are multiplied; zero and guaranteed drops are preserved |
| `UNION_POINT_GAIN_RATE` | `PlayerRunUnionEffectComponent.mlua`; `UnionRewardServiceLogic.mlua` | `AccumulateUnionReward` → `CalculateUnionPointReward`; commit via `TryCommitUnionReward` | Pending total changes, then authoritative run end | Per-run stable rate; persistent at commit | **YES**, rename vocabulary to Coin later |
| `STARTING_POTION` | `RunManagerLogic.mlua`; `PlayerRunInventoryComponent.mlua` | `InitializeNewRunOwnedState` → `GrantRunReward("CONSUMABLE", "potion_hp_small", ...)` | Once during new run-owned state initialization | Per-run | **YES** |
| `INVENTORY_SLOT` | `RunManagerLogic.mlua`; `PlayerRunInventoryComponent.mlua` | `ResetForRun(runSequence, InventorySlotBonus)` | Once at run initialization | Per-run consumable capacity | **YES** |
| `AUGMENT_REROLL` | `RunManagerLogic.mlua`; `PlayerRunAugmentComponent.mlua` | `ResetForRun(runSequence, AugmentRerollBonus)` | Once at run initialization | Per-run | **YES** |
| `STARTING_SKILL` | `RunManagerLogic.mlua`; `PlayerRunStateComponent.mlua`; `PlayerRunInventoryComponent.mlua` | `ApplyJobBundle` increases slot count and selects eligible authored starting skills; `InitializeStartingSkills` grants them | Job selection/run setup | Per-run | **YES**, but it cannot exceed the job's authored eligible starting-skill rows |
| `STARTING_RANDOM_RELIC` | Resolver and run snapshot only | `ApplyEffectValue`, `CaptureForRun` | Never consumed by a relic owner | Snapshot-only, no gameplay application | **NO — INCOMPLETE** |
| `ADDITIONAL_SKILL_UNLOCK` | No production implementation | None | Never | None | **NO — NOT IMPLEMENTED** |

There is no Relic/Artifact repository, random relic selector, persistent/run relic inventory, or grant API in the current project. A comment mentioning “Relic” in `BattleSessionComponent` is not an implementation. `STARTING_RANDOM_RELIC` must not be reported as working.

## 7. Union effect resolver audit

`UnionEffectResolverLogic` is the correct architectural seam:

- `GetEffectSnapshot(user)` loads the server profile.
- `ResolveFromProfile(profile)` validates all purchased levels.
- It reads one cumulative `EffectValue` row at the purchased level.
- `ApplyEffectValue` maps validated effect types into one DTO.
- Gameplay receives only the DTO.
- `PlayerRunUnionEffectComponent:CaptureForRun` freezes it for the run.

The resolver currently supports nine fields:

```text
MesoGainRate, ItemDropRate, AugmentRerollBonus,
UnionPointGainRate, StartingPotionBonus, MaxHPBonus,
InventorySlotBonus, StartingSkillBonus, StartingRandomRelicBonus
```

Recommended future seam:

```text
Union Profile
  -> OwnedUnionBlocks + PlacedUnionBlocks
  -> UnionBoardResolver
  -> occupied-cell and activated-special-zone contributions
  -> UnionEffectResolver
  -> same UnionEffectSnapshot contract
  -> same run snapshot and gameplay systems
```

Only the resolver source should change for the nine existing fields. `ADDITIONAL_SKILL_UNLOCK` needs a new, explicitly designed gameplay contract because no current owner exists.

## 8. Current Union UI

UIBuilder inspection of `ui/UnionSystemUI.ui` found:

- 188 total entities.
- Disabled root window `/ui/UnionSystemUI/UnionWindow`.
- Main frame `/UnionFrame`, 1540×900.
- Left board panel 1000×710 and board frame 940×630.
- Right panel 420×710.
- `GridCellLayer` contains 96 pre-authored 56×56 cells.
- Four region containers: Growth, Combat, Exploration, Tactics.
- Center `UnionCore` is 50×50 and is not an upgrade purchase target.
- Nine transparent ButtonComponent node/hit areas correspond to the nine old upgrades.
- Rank, current/lifetime points, applied effects, selected-upgrade details, purchase button, major confirmation overlay, and rank-up toast exist.

Actual rendering/controller boundaries:

| UI responsibility | Actual owner |
|---|---|
| Root layout, frames, 96 cells, node hit areas, right panel | `ui/UnionSystemUI.ui` |
| Node path table | `UnionSystemUILogic:InitializeUpgradeNodePaths` |
| Old upgrade-level-to-cell mapping | `UnionSystemUILogic:InitializeUpgradeCellPaths` |
| Cell color/state | `ApplyTerritoryVisual`, `ApplyTerritoryCellVisual` |
| Rank/tier tint | `ApplyBoardTierVisuals`, `SetRegionTint` |
| Details and purchase | `SelectUpgrade`, `RefreshDetailPanel`, `SubmitPurchaseRequest` |
| Server snapshot | `RequestUnionSnapshot`, `SendAuthoritativeSnapshot`, `SendUpgradeRows` |
| Server purchase | `RequestPurchaseUpgrade` → `_UnionProfileRepositoryLogic:TryPurchaseUpgrade` |

The board is not generated from board-cell data. It is a static `.ui` hierarchy plus hardcoded node/cell path maps in mLua. There is no owned-block palette, block sprite, placement preview, rotation, flip, drag, occupancy model, or placement request.

Reusable UI pieces: outer shell, close/refresh flow, snapshot request pattern, currency/rank/effects panel, existing 96-cell visual footprint, and lobby-only open/close rules. Replace the upgrade hit areas, hardcoded level paths, purchase detail semantics, and node visuals later.

## 9. Lobby Union NPC

Status: **IMPLEMENTED** (direct-open interaction; no dialogue sequence).

| Item | Actual value |
|---|---|
| Map | `map/lobby.map` (`TileMapMode = 0`, MapleTile) |
| Entity | `/maps/lobby/Lobby_2F/Facilities/UnionManagerNPC` |
| Position | `(-25.75, -7.92, 999.999)` world units |
| Body | `RigidbodyComponent`, correct for MapleTile |
| Interaction component | `script.LobbyInteractionComponent` |
| Interaction ID | `Union` |
| Key/prompt | `E`, `[E] 유니온 관리` |
| Open call | `_UnionSystemUILogic:OpenWindow()` |
| Close behavior | Escape, explicit close, leaving range, or leaving lobby |
| NPC label | `유니온 관리자` |
| NPC resource | `c2919dc57fac457c9ce94fe32f8b69d2` |

The NPC has `ChatBalloonComponent`, but chat mode is disabled and `OnInteract` opens the Union window directly. There is no Union-specific dialogue tree. That is not a blocker for the block system.

## 10. Existing shop systems

### Project run shop

| Actual file | Useful behavior | Why it cannot own Union Blocks directly |
|---|---|---|
| `RootDesk/MyDesk/04_Roguelike/Shop/RunShopLogic.mlua` | Server resolves shop entry, request ID guard, duplicate-offer guard, delegates atomic inventory purchase | Requires an active run and `AWAITING_SHOP`; purchases run rewards, not account-meta ownership |
| `RootDesk/MyDesk/04_Roguelike/Shop/PlayerRunShopStateComponent.mlua` | Per-visit offers, purchased IDs, request-key idempotency, synced UI state | Reset per run/visit and not persistent |
| `RootDesk/MyDesk/03_Data/Repositories/ShopDefinitionRepositoryLogic.mlua` | CSV repository conversion/validation pattern | Schema is run reward-specific |
| `RootDesk/MyDesk/04_Roguelike/RunManager/PlayerRunInventoryComponent.mlua` | Atomic currency spend + reward apply and duplicate purchase key | Currency/inventory are run-scoped |

Conclusion: reuse its request-id, server price resolution, duplicate-key, and repository-validation patterns. Do not route account-meta Union Blocks through the run shop or run inventory.

### Existing Union purchase boundary

`TryPurchaseUpgrade` already demonstrates the closer pattern: server-resolved definitions and costs, mutation lock, balance check, atomic profile persist, and authoritative snapshot return. Its mutation infrastructure should be extended into a small dedicated `UnionBlockPurchaseService`; its upgrade-level semantics must not be reused.

### Official MSWPackages reviewed

- `shop-package` is a `WorldShopService` product/premium purchase system; it is not an in-game Union Coin shop.
- `resource-package` can persist and synchronize generic resources, but adopting it now would create a second currency/save owner beside `UnionProfileRepositoryLogic`.
- `inventory-package` supports GUID item instances, equipment, item use, and PlayerDBManager, but is significantly broader than account-meta geometric blocks.
- `player-data-package` provides a separate PlayerDBManager/DataStorage framework; replacing the current profile during this migration would multiply risk.

Recommendation: do not install these packages for the first block prototype. Keep the current Union profile as the single save authority and build the minimum dedicated block purchase/placement APIs on it.

## 11. Existing grid and drag systems

| Candidate | Finding | Reuse status |
|---|---|---|
| Current Union 96-cell layer | Static cell entities and known screen positions exist | **Reuse visual shell/coordinates cautiously**; it has no board data model |
| `UnionSystemUILogic` cell mapping | Maps upgrade levels to 25 selected cell paths | **Replace**; it is not geometric occupancy |
| Lobby grid movement | World movement/grid navigation, unrelated to UI block placement | **Do not reuse** |
| Battle board/grid | Tactical combat cells and unit placement rules, tightly coupled to battle state | **Do not couple to meta board**; algorithms may inspire tests only |
| UI drag-and-drop | No production handler for `UITouchBeginDragEvent`, `UITouchDragEvent`, or `UITouchEndDragEvent` | **NOT IMPLEMENTED** |
| Rotation/flip | No block/UI rotation or flip controller | **NOT IMPLEMENTED** |
| Overlap/bounds/core connection | No Union placement validator | **NOT IMPLEMENTED** |
| Persistent placed-item model | None | **NOT IMPLEMENTED** |

Native MSW drag events and UI transform APIs are available, but there is no project-level reusable drag framework. The first prototype should keep placement validation independent from pointer presentation so click-to-place and drag-to-place can share one server validator.

## 12. Verified MSW Union assets

The connected toolset exposes `msw-mcp` documentation/resource/storage/world-item tools. No `msw-maker-mcp` runtime tools are available. Searches and detail checks were routed through the validated `msw-search` wrapper, not guessed from thumbnails.

| Purpose | Exact resource | RUID | Verified source | Status |
|---|---|---|---|---|
| Union Coin | `유니온 코인` (`sprite-136452`, 28×28) | `95632823c5e44dab89b9859ff439165b` | `item/etc/0431.img`, `04310229/info/iconRaw` | **RESOURCE VERIFIED** |
| Union Raid background | `sprite-9094183` (432×460) | `83f4c25c940e49aca6f240619ba4ff6c` | `map/back/mapleunion.img`, `back/4`; tags include `유니온 레이드` | **RESOURCE VERIFIED** |
| Union Raid preparation prop | `sprite-9091020` (168×160) | `2aefbe890905430ca0afe18a5a9bc96f` | `map/back/mapleunion.img`, `back/21`; tags include `유니온 레이드` | **RESOURCE VERIFIED** |
| Union preset coupon icon | `유니온 프리셋 쿠폰` (`sprite-127058`, 32×24) | `3575be5e97b04c5fa67662e006aee13b` | `item/consume/0243.img`, `02436884/info/iconRaw` | **RESOURCE VERIFIED**, but not a preset button |
| Lobby administrator fallback | Nineheart stand animationclip (52×80) | `c2919dc57fac457c9ce94fe32f8b69d2` | `npc/1530070.img`, `stand`; Korean tags include `나인하트` | **RESOURCE VERIFIED** |

Still **NOT VERIFIED / MANUAL_RESOURCE_SEARCH_REQUIRED**:

- Exact `UIWindow6.img/attackerSetting` management window/frame.
- Exact `UIWindow6.img/unionRaid` management UI.
- Official battle-map grid cells and occupied/selected/hover states.
- Official Union emblem/rank badge family.
- Official Union shop frame/button family.
- Official Union block visuals/slot backgrounds.

Current UI also uses Maple-style project resources (for example `7995ae...`, `360816...`, `c24ade...`, `a7928e...`, and generic cell sprite `286013...`). They are **FOUND_IN_PROJECT**, not verified as official Union resources.

## 13. KEEP / REPLACE / REMOVE LATER

| Current system | Decision | Reason |
|---|---|---|
| DataStorage identity, cache, lock, CAS persist, normalization | **KEEP** | Correct single server-authoritative profile boundary |
| Reward run IDs and commit receipts | **KEEP** | Already prevents duplicate run rewards across callbacks/reconnects |
| Spendable/lifetime separation | **KEEP** | Correct economic model; only vocabulary/schema field names need staged migration |
| Rank derivation from lifetime total | **KEEP** | Fits board expansion/shop gating |
| `UnionEffectSnapshot` contract | **KEEP** | Clean separation from gameplay |
| Stable per-run capture | **KEEP** | Prevents mid-run loadout changes |
| Eight working gameplay hooks | **KEEP** | Owners and once-per-run boundaries are correct |
| `STARTING_RANDOM_RELIC` claim | **DO NOT KEEP AS WORKING** | Snapshot exists but no relic system consumes it |
| Old `PurchasedLevels` effect source | **MIGRATE / DEPRECATE** | Final design requires occupancy-derived effects |
| `UnionUpgradeDefinitions` / `UnionUpgradeLevels` | **DEPRECATE LATER** | Old skill-tree economy; keep until cutover/compensation completes |
| `CanPurchaseUpgrade` / `TryPurchaseUpgrade` semantics | **REPLACE** | Permanent block purchase is quantity ownership, not next level |
| Floating/transparent upgrade-node interactions | **REPLACE** | Must become owned block palette and placement interaction |
| Hardcoded `UpgradeCellPaths` | **REPLACE** | Board cells and effects must be data-driven |
| Current outer UI shell/right rank-currency-effects panel | **KEEP / ADAPT** | Useful presentation and NPC entry shell |
| Lobby Union NPC and E-key route | **KEEP** | Already dedicated and functional by code inspection |
| Current run shop as Union shop | **DO NOT REUSE DIRECTLY** | Wrong lifetime and ownership domain |
| Old files/data | **REMOVE LATER ONLY** | Keep through migration, rollback window, and save conversion |

## 14. Risks

1. **Double-source bonuses:** allowing both `PurchasedLevels` and placed cells to contribute would duplicate stats. A profile must use exactly one progression mode during cutover.
2. **Destructive currency rename:** independently writable `UnionPoints` and `UnionCoins` can diverge. Migration must be atomic and versioned.
3. **Unfair legacy conversion:** upgrade levels cannot be translated geometrically without inventing positions. Refund or explicit compensation is safer than automatic placement.
4. **Paid ownership loss:** invalid/corrupt placement must unplace a block, never delete its ownership.
5. **Client trust:** shape, cost, ownership quantity, transformed cells, rank/tier, overlap, bounds, and core connectivity must all resolve server-side.
6. **Connectivity ambiguity:** define whether diagonal adjacency counts. Recommendation: four-direction edge adjacency only.
7. **Rotation normalization:** store canonical quarter-turns (`0/1/2/3`), not arbitrary degrees. Flip must be definition-gated.
8. **DataStorage contention/size:** purchases and placements share one profile blob. Preserve the current lock/CAS pattern and avoid saving derived occupied cells/effects.
9. **Disconnected islands after move/remove:** every post-mutation board must be revalidated from the core, not only the moved block.
10. **Missing gameplay owners:** `STARTING_RANDOM_RELIC` and `ADDITIONAL_SKILL_UNLOCK` cannot safely activate until real systems and eligibility rules exist.
11. **Static UI dependency:** current 96 cells are presentation entities, not a canonical board. Logic must not infer region/effect data from UI paths.
12. **Resource gaps:** official management-frame/grid/block RUIDs remain unavailable; no future task may fabricate them.
13. **Runtime status:** Maker play/log/screenshot verification is unavailable in this session, so all behavior findings are code-level only.

## Audit conclusion

The current system already has strong server authority, idempotent rewards, rank derivation, a central effect snapshot, stable per-run capture, and eight reusable gameplay hooks. The redesign should introduce block ownership and board occupancy between the profile and effect resolver, not rewrite the downstream gameplay systems. The old upgrade data and UI must remain intact until an explicit, versioned cutover and compensation strategy is implemented.
