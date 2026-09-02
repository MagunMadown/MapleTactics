# Union Block Data Design — STEP 1

## Scope

This step defines only the immutable data contract and read-only repositories for the new Union Block system. It does not change player persistence, purchases, placement state, UI interaction, the Union effect resolver, or gameplay integration.

- Existing `UnionPoints` and `LifetimeUnionPoints` remain the future block-purchase currency source.
- Existing Union profile schema version remains `3`.
- The current 96-cell board UI remains unchanged and is represented by logical coordinates only.
- `UnionSpecialZoneDefinitions.csv` intentionally contains no active rows in STEP 1; its schema is reserved for later landmarks and special zones.

## Logical Coordinate System

The board uses integer grid coordinates that are independent of UI entity paths and pixel positions.

- Origin: the center point shared by the four central Core cells.
- Positive X: right.
- Positive Y: up.
- Cell adjacency: Manhattan distance 1 (left, right, up, down).
- A placed shape is translated by adding its normalized local cell coordinates to a future placement origin.

The existing visual board uses 60-pixel center spacing. For the one-time STEP 1 migration mapping, its current local cell centers map as follows:

```text
GridX = (VisualCenterX - 30) / 60
GridY = (VisualCenterY - 30) / 60
```

The formula documents how the current UI was audited; runtime placement must use `GridX` and `GridY`, not pixels or entity names. `VisualCellName` is only a deterministic adapter from the current 96 UI cells to the logical board.

## I3 Shape and Deterministic Rotation

`UnionBlockShapeDefinitions.csv` stores I3 as three local cells:

```text
0:0 | 1:0 | 2:0
```

`GetRotatedCells(shapeId, rotation)` accepts integer quarter-turns. Rotation is counter-clockwise and normalized after rotation so the minimum local X and Y are both zero. Returned cells are sorted by Y and then X.

| Rotation | Normalized cells | Result |
|---:|---|---|
| 0 / 0° | `(0,0) (1,0) (2,0)` | horizontal |
| 1 / 90° | `(0,0) (0,1) (0,2)` | vertical |
| 2 / 180° | `(0,0) (1,0) (2,0)` | horizontal |
| 3 / 270° | `(0,0) (0,1) (0,2)` | vertical |

Negative and larger rotation values are normalized modulo four. I3 has `RotationAllowed=true` and `FlipAllowed=false`, so no reflected variant is produced.

## Initial Block Definition

| BlockId | ShapeId | ShopCost | RequiredUnionRank | MaxOwned |
|---|---|---:|---|---:|
| `union_block_i3_basic` | `I3` | 100 | `UNION_I` | 1 |

This is a definition only. No purchase API, balance mutation, ownership persistence, or client request handler is included in STEP 1.

## Board Mapping

All 96 existing visual cells have one unique logical coordinate and one unique `VisualCellName` in `UnionBoardCellDefinitions.csv`. The tapered board has these logical rows:

| GridY | GridX range | Count | Existing visual cell sequence |
|---:|---|---:|---|
| 4 | -3 through 2 | 6 | `Cell_01_01` through `Cell_01_06` |
| 3 | -4 through 3 | 8 | `Cell_01_07` through `Cell_01_12`, then `Cell_02_01` through `Cell_02_02` |
| 2 | -5 through 4 | 10 | `Cell_02_03` through `Cell_02_12` |
| 1 | -6 through 5 | 12 | `Cell_03_01` through `Cell_03_12` |
| 0 | -6 through 5 | 12 | `Cell_04_01` through `Cell_04_12` |
| -1 | -6 through 5 | 12 | `Cell_05_01` through `Cell_05_12` |
| -2 | -6 through 5 | 12 | `Cell_06_01` through `Cell_06_12` |
| -3 | -5 through 4 | 10 | `Cell_07_01` through `Cell_07_10` |
| -4 | -4 through 3 | 8 | `Cell_07_11` through `Cell_07_12`, then `Cell_08_01` through `Cell_08_06` |
| -5 | -3 through 2 | 6 | `Cell_08_07` through `Cell_08_12` |

The CSV is the authoritative per-cell mapping. The old name pattern looks like eight rows of twelve but is only a sequential identifier; the actual visual board is ten tapered logical rows.

### Region assignment

- `CORE`: the four center cells only.
- `GROWTH`: rows with `GridY >= 1`.
- `TACTICS`: rows with `GridY <= -2`.
- `COMBAT`: middle rows (`GridY` 0 or -1) left of Core (`GridX <= -2`).
- `EXPLORATION`: middle rows (`GridY` 0 or -1) right of Core (`GridX >= 1`).

## Union Core

The logical Core is a contiguous 2×2 group:

| CellId | GridX | GridY | VisualCellName |
|---|---:|---:|---|
| `CELL_XN01_YZ00` | -1 | 0 | `Cell_04_06` |
| `CELL_XZ00_YZ00` | 0 | 0 | `Cell_04_07` |
| `CELL_XN01_YN01` | -1 | -1 | `Cell_05_06` |
| `CELL_XZ00_YN01` | 0 | -1 | `Cell_05_07` |

Core invariants enforced by `ValidateBoard()`:

- Exactly four cells.
- Four-way contiguous.
- `RegionId=CORE`, `BoardTier=1`, `IsCore=true`.
- No ordinary effect and no special-zone reference.

## Prototype MAX_HP Cells

Exactly three contiguous cells form the STEP 1 prototype route immediately left of the Core:

| CellId | GridX | GridY | Effect | Value | VisualCellName |
|---|---:|---:|---|---:|---|
| `CELL_XN04_YZ00` | -4 | 0 | `MAX_HP` | 1 | `Cell_04_03` |
| `CELL_XN03_YZ00` | -3 | 0 | `MAX_HP` | 1 | `Cell_04_04` |
| `CELL_XN02_YZ00` | -2 | 0 | `MAX_HP` | 1 | `Cell_04_05` |

They use `RegionId=COMBAT` and `BoardTier=1`. This is only effect metadata; STEP 1 does not decide occupancy, connectivity from the Core, activation, stacking, or gameplay application.

## BoardTier Mapping

`BoardTier` is editable per-cell data and represents the minimum Union rank at which a cell becomes accessible. For example, `BoardTier=3` means that the cell becomes usable starting at `UNION III`.

The initial assignment expands outward from the 2×2 Core using nested, orthogonally connected territories. Coordinate pairs are selected with 180-degree symmetry around the Core center wherever possible. The required prototype HP route remains a continuous tier-1 path.

### Union Rank Battle Map Expansion

There is one 96-cell source-of-truth Battle Map. Higher Union ranks unlock additional cells from that same map; there are no separate board files per rank.

| Union rank | Accessible BoardTier | Newly added cells | Cumulative accessible cells |
|---|---:|---:|---:|
| `UNION I` | `<= 1` | 18 | 18 / 96 |
| `UNION II` | `<= 2` | 12 | 30 / 96 |
| `UNION III` | `<= 3` | 16 | 46 / 96 |
| `UNION IV` | `<= 4` | 22 | 68 / 96 |
| `UNION V` | `<= 5` | 28 | 96 / 96 |

The exact tier row counts are therefore:

- Tier 1: 18
- Tier 2: 12
- Tier 3: 16
- Tier 4: 22
- Tier 5: 28

Every cumulative territory (`Tier <= N`) is validated as one orthogonally connected region containing the Core. Tier 1 preserves all four Core cells and all three `MAX_HP +1` prototype cells. Expansion remains logical data only; STEP 1.1 does not hide or restyle locked UI cells.

## Repository Contracts

### UnionBlockShapeDefinitionRepositoryLogic

- `GetShape(shapeId)`
- `GetAllShapes()`
- `GetRotatedCells(shapeId, rotation)`
- `ValidateShapes()`

### UnionBlockDefinitionRepositoryLogic

- `GetBlock(blockId)`
- `GetAllBlocks()`
- `ValidateDefinitions()`

### UnionBoardDefinitionRepositoryLogic

- `GetCell(gridX, gridY)`
- `GetCellById(cellId)`
- `GetAllCells()`
- `IsInsideBoard(gridX, gridY)`
- `GetCoreCells()`
- `GetCellsByEffectType(effectType)`
- `GetBoardTier(gridX, gridY)`
- `GetSpecialZone(specialZoneId)`
- `ValidateBoard()`

All APIs are server-only and read definition data through `_DataService`. They do not write player data or mutate definitions.

## Validation Coverage

The repositories reject malformed or ambiguous definition data, including:

- Duplicate or invalid shape, block, cell, special-zone IDs.
- Duplicate shape-local cells, logical board coordinates, visual names, and sort orders.
- Empty or malformed shape cell lists and invalid boolean values.
- Missing shape references, invalid shop cost, rank, and max-owned values.
- Board cell counts other than 96.
- Invalid regions, effect types, effect values, tiers, and special-zone references.
- A Core that is not exactly four contiguous, effect-free cells.
- A prototype HP route that is not exactly three contiguous `COMBAT`, `MAX_HP +1`, tier-1 cells.

## Future Extension

- L, T, O, and Z blocks require only additional shape rows and block rows; the rotation repository already handles arbitrary integer cell sets.
- Special landmark cells can be introduced by adding rows to `UnionSpecialZoneDefinitions.csv` and referencing their IDs from board cells.
- Current reserved special-zone activation rules are `LANDMARK_CELL`, `FULL_ZONE`, and `OCCUPIED_CELL_COUNT`.
- `ADDITIONAL_SKILL_UNLOCK` is reserved as a recognized future board effect identifier. It has no active cell and no gameplay behavior in STEP 1.
- Purchase, ownership save migration, placement, connectivity, effect aggregation, and UI interaction belong to later steps.
