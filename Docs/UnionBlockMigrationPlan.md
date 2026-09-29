# Union Block System — Migration Plan

> Planning only. Nothing in this document was implemented during STEP 0.

## Final design source of truth

```text
Dungeon
  -> earn Union Coin
  -> authoritative run-end commit
  -> return to Lobby
  -> interact with Union Manager NPC
  -> purchase permanent geometric Union Blocks
  -> place owned blocks on the Union Battle Map
  -> occupied cells / activated special zones determine bonuses
  -> central UnionEffectSnapshot
  -> future runs capture and use the snapshot
```

Rules:

- Blocks have geometry and ownership only; they never carry direct stats.
- Basic effects come from occupied board cells.
- Major roguelite effects come from explicit special-zone activation rules.
- Placement eventually supports snap, rotation, permitted flip, bounds/overlap rejection, core connectivity, move/remove, and persistence.
- Gameplay systems consume `UnionEffectSnapshot`; they never read cells or placements.

## KEEP

| System | Keep exactly / adapt |
|---|---|
| `UnionProfileRepositoryLogic` DataStorage boundary | Keep identity, cache, lock, `UpdateAndWait`/`SetAndWait`, normalization, validation, defensive snapshots |
| Reward commit | Keep `NextRewardRunId`, `CommittedRewardKeys`, pending reward accumulation, and authoritative one-time commit |
| Rank | Keep lifetime-derived rank; later let definitions gate board tiers, shop blocks, and special zones |
| `UnionEffectResolverLogic` public output | Keep the existing nine-field snapshot contract so downstream gameplay remains unchanged |
| `PlayerRunUnionEffectComponent` | Keep immutable run capture and reward multiplier math |
| Working gameplay hooks | Keep HP, meso, drop rate, coin gain rate, potion, inventory slots, rerolls, and starting skills |
| Lobby NPC | Keep entity, E-key route, range/close behavior, and verified NPC resource |
| UI shell | Keep close/refresh pattern, rank/currency/effect panel, and existing board frame as a temporary presentation base |
| CSV/repository convention | Keep paired `.csv` + `.userdataset`, `_DataService:GetTable`, row DTO conversion, and deterministic validation |

## REPLACE

| Current source | Future source |
|---|---|
| `PurchasedLevels` → cumulative upgrade level effect | Owned blocks + valid placed blocks → occupied cells/special zones |
| `CanPurchaseUpgrade` / `TryPurchaseUpgrade` | `CanPurchaseUnionBlock` / `TryPurchaseUnionBlock` with quantity ownership |
| Hardcoded upgrade node/cell maps | Data-driven board cell and block shape definitions |
| Upgrade details and next-level purchase UI | Block shop list, owned quantity, placement palette, rotation/flip/move/remove controls |
| Upgrade territory coloring | Valid placement preview, occupied cells, selected block, invalid reason, special-zone state |
| User-facing `유니온 포인트` | User-facing `유니온 코인` |

## DEPRECATE LATER

Do not delete these until all profiles are migrated, compensation is idempotent, the block resolver is live, and a rollback window has passed:

- `UnionUpgradeDefinitions.csv` / `.userdataset`.
- `UnionUpgradeLevels.csv` / `.userdataset`.
- `UnionUpgradeDefinitionRepositoryLogic`.
- `PurchasedLevels` in the active profile schema.
- `CanPurchaseUpgrade`, `TryPurchaseUpgrade`, and the no-longer-used `SetActiveUpgradeLevel` compatibility API.
- Upgrade node paths, level-cell maps, detail text, purchase confirmation, and old node handlers in `UnionSystemUILogic`.
- Old upgrade node entities in `ui/UnionSystemUI.ui`.

Archive legacy values for support/audit before eventual removal. Never reinterpret an old purchased level as an arbitrary board placement.

## Proposed data definitions

The project convention favors normalized rows and separate level/detail tables. For shapes, normalized shape-cell rows are safer than packing coordinates into one delimited `Cells` field.

### `UnionBlockDefinitions.csv`

| Field | Purpose |
|---|---|
| `BlockId` | Stable safe-token identifier |
| `DisplayName` | Player-facing name |
| `Description` | Shape/shop description only; no stat claim |
| `ShapeId` | Reference to shape header/cells |
| `ShopCost` | Server-resolved Union Coin cost |
| `RequiredUnionRank` | Purchase gate |
| `MaxOwned` | Quantity cap; positive integer |
| `SortOrder` | Stable shop order |
| `IconRUID` | Optional, verified RUID only; empty is allowed until an asset is verified |

Validation: unique IDs/order, known shape/rank, nonnegative cost, positive ownership cap, valid RUID format only when nonempty.

### `UnionBlockShapeDefinitions.csv`

| Field | Purpose |
|---|---|
| `ShapeId` | Stable shape identifier |
| `DisplayName` | I/L/T/O/Z/etc. |
| `RotationAllowed` | Whether quarter-turn rotation is permitted |
| `FlipAllowed` | Whether reflection is permitted |
| `SortOrder` | Stable ordering |

### `UnionBlockShapeCells.csv`

| Field | Purpose |
|---|---|
| `ShapeId` | Parent shape |
| `CellIndex` | Unique deterministic cell order within shape |
| `OffsetX` | Integer offset from anchor |
| `OffsetY` | Integer offset from anchor |

Validation: every shape has at least one cell; `(OffsetX, OffsetY)` is unique; `(0,0)` is present as canonical anchor; rotations/flips normalize without duplicate cells.

### `UnionBoardCellDefinitions.csv`

| Field | Purpose |
|---|---|
| `GridX`, `GridY` | Unique canonical board coordinate |
| `RegionId` | Inner/outer semantic region |
| `EffectType` | Basic effect or empty for core/special-only cells |
| `EffectValue` | Contribution when occupied; never stored in player save |
| `BoardTier` | Minimum rank-derived board tier |
| `SpecialZoneId` | Optional reference to a special zone |
| `IsCore` | Exactly one core cell/territory anchor |
| `SortOrder` | Deterministic content validation/debug ordering |

Initial basic `EffectType` allow-list:

- `MAX_HP`
- `MESO_GAIN_RATE`
- `ITEM_DROP_RATE`
- `UNION_COIN_GAIN_RATE` (mapped to the existing snapshot field `UnionPointGainRate` during compatibility)

### `UnionSpecialZoneDefinitions.csv`

| Field | Purpose |
|---|---|
| `SpecialZoneId` | Stable zone identifier |
| `DisplayName` | Player-facing name |
| `EffectType` | Major effect type |
| `EffectValue` | Applied only after activation rule passes |
| `ActivationRule` | Allow-list such as `LANDMARK_CELL`, `FULL_ZONE`, `OCCUPIED_CELL_COUNT` |
| `RequiredOccupiedCellCount` | Used only by the count rule |
| `RequiredUnionRank` | Independent major-effect rank gate |
| `SortOrder` | Deterministic order |

Planned special effects:

- `INVENTORY_SLOT`
- `STARTING_POTION`
- `AUGMENT_REROLL`
- `STARTING_SKILL`
- `STARTING_RANDOM_RELIC`
- `ADDITIONAL_SKILL_UNLOCK`

`STARTING_RANDOM_RELIC` and `ADDITIONAL_SKILL_UNLOCK` definitions must remain disabled/unavailable until actual gameplay owners exist.

### Repository convention

Create focused repositories rather than a second generic data framework:

- `UnionBlockDefinitionRepositoryLogic`
- `UnionBoardDefinitionRepositoryLogic`

Each should expose `GetDefinition`, `GetAllDefinitions`, focused shape/cell/zone queries, and `ValidateDefinitions`. Cross-table validation should fail the feature at server startup with one deterministic error snapshot, following the current Union repositories.

## Proposed runtime architecture

```text
UnionProfileRepositoryLogic
  |- UnionCoins / LifetimeUnionCoins
  |- OwnedUnionBlocks
  |- PlacedUnionBlocks
  |- reward receipts / migration state
  |
  +-> UnionBlockPurchaseServiceLogic
  |     server resolves block, price, rank, max owned, request key
  |
  +-> UnionBoardPlacementServiceLogic
        server resolves owned quantity, shape transform, board tier,
        bounds, overlap, special rules, and post-change connectivity
        |
        +-> UnionBoardResolverLogic
              builds valid occupied-cell/special-zone contribution DTO
              |
              +-> UnionEffectResolverLogic
                    maps contributions to existing UnionEffectSnapshot
                    |
                    +-> PlayerRunUnionEffectComponent.CaptureForRun
                          -> unchanged gameplay owners
```

### `UnionBlockPurchaseServiceLogic` minimum API

```text
GetUnionBlockShopSnapshot(user)
CanPurchaseUnionBlock(user, blockId)
TryPurchaseUnionBlock(user, blockId, requestId)
```

Server must resolve cost, rank, maximum quantity, current balance, and result. Reuse the profile mutation lock and persistence boundary. Maintain a bounded purchase-receipt key if requests can be retried across reconnects.

### `UnionBoardPlacementServiceLogic` minimum API

```text
GetUnionBoardSnapshot(user)
CanPlaceUnionBlock(user, blockId, gridX, gridY, rotation, flipped)
TryPlaceUnionBlock(user, blockId, gridX, gridY, rotation, flipped, requestId)
TryMoveUnionBlock(user, instanceId, gridX, gridY, rotation, flipped, requestId)
TryRemoveUnionBlock(user, instanceId, requestId)
```

Client sends intent only. Server canonicalizes `rotation` to `0..3`, rejects flip when disallowed, transforms shape offsets, verifies purchased quantity, and validates the complete resulting board.

### Placement validation order

1. Validate request ID and safe identifiers.
2. Resolve profile, rank/tier, block, and shape from server data.
3. Validate owned quantity and instance/move target.
4. Canonicalize rotation/flip.
5. Transform shape offsets to candidate board coordinates.
6. Reject missing/tier-locked board coordinates.
7. Reject overlap with other placed blocks.
8. Rebuild the entire occupancy graph.
9. Require every occupied cell to be four-direction connected to the core territory.
10. Persist the canonical placement and return an authoritative board/effect snapshot.

The client may calculate a preview for responsiveness, but only the server result changes ownership or placement.

### `UnionBoardResolverLogic` output

Do not persist these derived values:

```lua
{
    Success = true,
    BoardTier = 1,
    OccupiedCells = { ... },
    ActivatedSpecialZones = { ... },
    EffectContributions = {
        MAX_HP = 3,
        MESO_GAIN_RATE = 0,
        ITEM_DROP_RATE = 0,
        UNION_COIN_GAIN_RATE = 0
    },
    ValidationRevision = 1
}
```

`UnionEffectResolverLogic` remains the only component that translates contributions into the gameplay snapshot field names.

## Save migration strategy

Current schema is 3. The first block-capable schema should be version 4 (or the next unused version at implementation time).

### Recommended active profile

```lua
{
    SchemaVersion = 4,
    UnionCoins = 0,
    LifetimeUnionCoins = 0,
    NextRewardRunId = 0,
    CommittedRewardKeys = {},

    OwnedUnionBlocks = {
        ["BLOCK_I_3"] = 1
    },

    PlacedUnionBlocks = {
        ["<32-char-guid>"] = {
            BlockId = "BLOCK_I_3",
            GridX = 0,
            GridY = 1,
            Rotation = 0,
            Flipped = false
        }
    },

    BoardRevision = 0,
    BlockMigrationVersion = 1,
    LegacyPurchasedLevels = { ... }
}
```

Why ownership is quantity-based while placements are instance-keyed:

- Identical blocks can stack compactly in ownership.
- A stable GUID identifies the placement that is moved or removed.
- Server validation enforces placed count per `BlockId` ≤ owned quantity.
- Removing a placement deletes only the placement entry; ownership remains permanent.

Use `_UtilLogic:NewGuid()` on the server for a new placement ID. Never accept an arbitrary new instance ID from the client.

### Migration phases

1. **Additive compatibility:** add new fields and explicit clone/normalize/validate support while old resolver/UI remains active.
2. **Currency migration:** atomically copy `UnionPoints` → `UnionCoins` and `LifetimeUnionPoints` → `LifetimeUnionCoins`; set a migration version. Do not allow two writable balances.
3. **Legacy archive/compensation:** copy `PurchasedLevels` into `LegacyPurchasedLevels`. Do not generate placements from it.
4. **Compensation policy:** recommended default is an idempotent Union Coin refund equal to server-authored historical costs for purchased levels. Keep lifetime progression unchanged. A starter-block grant is an alternative product decision, but must be data-driven and versioned.
5. **Per-profile source switch:** set one explicit mode/version so the effect resolver uses either legacy upgrades or block board, never both.
6. **Block ownership/placement launch:** new players start with empty owned/placed data (or an explicitly data-driven starter grant). Existing players receive the selected compensation exactly once.
7. **Rollback window:** retain legacy archive and old definitions while telemetry/support confirms migration.
8. **Deprecation:** only then remove old UI/APIs/data from active production paths.

### Normalization safety

- Clamp invalid coin/lifetime/owned quantities to nonnegative integers.
- Unknown block ownership should be preserved in a quarantined/legacy field or rejected without deleting other ownership.
- Invalid placements (unknown shape, overlap, out of bounds, locked tier, disconnected) should be unplaced with a warning while ownership is preserved.
- Never persist occupied cells or final effect totals; recalculate from definitions and canonical placements.
- Every mutation must clone, validate, persist atomically, then update cache and return a defensive snapshot.

## Minimum prototype plan

The first playable slice should prove the full economic/save/effect loop with one block and one basic region only.

### Content

- One block: `BLOCK_I_3`, three horizontal cells, rotation allowed, flip unnecessary.
- One small tier-1 board around one core anchor.
- At least three reachable `MAX_HP` cells with `EffectValue = 1` each.
- One shop entry with a data-driven Union Coin cost and rank requirement `UNION_I`.
- No outer/special zones.

### Flow and existing systems used

1. Existing `UnionRewardServiceLogic` commits a dungeon reward; presentation says Union Coin.
2. Existing NPC opens the Union window.
3. New block purchase service uses the existing profile lock/CAS persistence pattern.
4. UI shows one shop block and owned quantity.
5. Player selects the block and a board cell; the first prototype may use click-to-place before drag presentation exists.
6. Server snaps/canonicalizes the anchor, rejects out-of-bounds/overlap, and requires four-way connection to core.
7. Placement is saved with a server GUID.
8. Board resolver sums the three occupied HP cells.
9. Existing effect resolver emits `MaxHPBonus = 3`.
10. Existing run snapshot and `PlayerRunStateComponent` start the next run with +3 max HP.
11. Reconnect reloads ownership/placement and produces the same effect.

### Prototype acceptance checks

- Reward commit cannot duplicate on repeated result callbacks.
- Client cannot choose cost, ownership quantity, effect value, or placement result.
- Buying the same one-copy block twice fails at `MaxOwned = 1`.
- Invalid rotation/flip is rejected or canonicalized according to definition.
- Placement outside defined tier-1 cells fails.
- Placement overlapping core/another block fails according to explicit core rules.
- A disconnected placement fails.
- Moving/removing updates derived HP and persists.
- Reconnect reproduces the same board and HP bonus.
- Starting a run freezes the effect; later lobby moves do not change the active run.

## Implementation order

1. **Definitions/repositories:** block headers, normalized shape cells, board cells, special zones, validation only.
2. **Additive schema:** introduce versioned coin aliases/new fields, owned quantities, placements, clone/normalize/validate; keep legacy effects active.
3. **Pure board resolver:** transform, bounds, overlap, tier, connectivity, basic contribution tests without UI.
4. **Block purchase service:** server-authoritative cost/rank/quantity/idempotency and persistence.
5. **Placement service:** place/move/remove APIs and authoritative snapshots.
6. **Prototype UI:** adapt current shell to one block shop and click-to-place; then add drag/rotation presentation using the same service.
7. **Effect cutover:** feed board contributions into the existing `UnionEffectResolver` and retain the run snapshot contract.
8. **Currency presentation/cutover:** complete Union Point → Union Coin schema migration and UI/result vocabulary.
9. **Legacy migration:** archive/refund purchased levels and switch profiles exactly once.
10. **Special zones:** add only effects with verified gameplay owners; implement relic/additional-skill owners before enabling their zones.
11. **Asset polish:** replace fallbacks only with verified official RUIDs or explicitly approved project assets.
12. **Deprecation:** remove old upgrade node code/data only after Maker/play/save/reconnect verification and rollback window.

## Verification required in future implementation steps

- Static definition validation and pure resolver cases.
- Maker refresh/build logs after every new `.mlua`/`.userdataset` registration.
- Play verification for NPC open, purchase, placement, move/remove, result reward, run HP, and reconnect.
- DataStorage test with a schema-3 player, a new player, an interrupted write, and a duplicate purchase/reward request.
- Resolution/input checks for click and drag separately.
- Resource detail verification before every new RUID assignment.

STEP 0 ends here. No STEP 1 implementation is included.
