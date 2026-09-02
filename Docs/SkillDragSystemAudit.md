# Skill Drag System — Step 0 Audit

## Scope and baseline

This document is an audit only. It does not implement drag-and-drop, change combat behavior, alter skill data, or introduce a persistence migration.

- Audited code state: `origin/develop` at `6f0429b8fb69d891cd6947f86e9a2bca3a2b437a`.
- Working branch at audit time: `union-system-2026-ui-rework` at `405410cb634d06c7e3ff3317b4fff8e684967370`.
- Relationship: the working branch is an ancestor of `origin/develop` and is four commits behind it (`HEAD...origin/develop = 0 4`). The Union work is present in the audited develop state.
- Existing unrelated dirty files were left untouched. All source conclusions below were checked against `origin/develop` without resetting or replacing the user's worktree.

## Executive finding

MapleTactics does **not** currently have a persistent equipped-skill/loadout model or a visible owned-skill inventory UI. The six buttons in `BattleQueueHUD` are a battle-local, server-produced display set derived from the current run inventory. The set is deduplicated, shuffled when the owned snapshot changes, capped at six, and exposed as synchronized parallel strings on `BattleSessionComponent`.

Consequently, a drag swap between these six buttons can be a safe first gesture/input-isolation prototype, but it must be described as **battle skill-bar ordering**, not as the final persistent equip system. The eventual owned-to-equipped UX needs a dedicated loadout source of truth and persistence contract before implementation.

## Current Skill UI

### Production UI and logic

| Purpose | UI | Runtime logic | Current role |
|---|---|---|---|
| Battle skill bar and action controls | `ui/BattleQueueHUD.ui` | `RootDesk/MyDesk/02_UI/BattleQueueHudComponent.mlua`, `RootDesk/MyDesk/02_UI/BattleHudPresenterLogic.mlua` | Displays up to six battle-local skills, accepts click selection, shows cooldown and reservation state, and exposes clear/execute controls. |
| Player overhead reservation display | `ui/TacticsPlayerOverheadHUD.ui` | `RootDesk/MyDesk/02_UI/PlayerOverheadQueueHudComponent.mlua` | Rebuilds the currently reserved SkillId sequence above the player. |
| Job and starting-skill preview | `ui/CharacterSelectionUI.ui` | `RootDesk/MyDesk/00_Core/Lobby/LobbyCharacterSelectionLogic.mlua`, `RootDesk/MyDesk/00_Core/Lobby/LobbyJobSelectionProvider.mlua` | Shows two starting-skill preview slots; it is not an equipment editor. |
| Skill collection/codex | `ui/CollectionUI.ui` | `RootDesk/MyDesk/00_Core/Lobby/LobbyCodexLogic.mlua`, `RootDesk/MyDesk/00_Core/Lobby/SkillCodexProvider.mlua` | Catalog/detail UI. The provider currently exposes grantable definitions as discovered, so it is not an owned/unlocked inventory source. |
| Run skill upgrade choice | `ui/UpgradeSkillStageUI.ui` | `RootDesk/MyDesk/04_Roguelike/SkillStage/UpgradeSkillStageUIComponent.mlua`, `RootDesk/MyDesk/04_Roguelike/SkillStage/UpgradeSkillStageLogic.mlua` | Displays up to six owned skills that have a next upgrade; it is stage-scoped, not a loadout editor. |
| New run-skill choice | world-space choice entities | `RootDesk/MyDesk/04_Roguelike/SkillStage/NewSkillStageChoiceComponent.mlua` | Offers unowned tier-one skill families for the selected job and grants the server-validated choice. |
| Shared skill tooltip | `ui/MouseTooltipGroup.ui` | `RootDesk/MyDesk/02_UI/MouseTooltipUIComponent.mlua` | Cursor-following tooltip infrastructure. It can inform future ghost placement conventions but is not a drag implementation. |

There is no dedicated skill inventory/loadout `.ui` and no current screen where an owned list and equipped slots coexist. A future owned/equipped editor logically belongs in a lobby or between-stage skill-management screen, not inside the reservation queue.

### Builder status

No feature-specific committed skill UI builder was found. Existing structured `.ui` assets must continue to be changed through the project UI builder protocol, using `.agents/skills/msw-ui-system/scripts/msw_ui_builder.cjs`; raw JSON editing is not appropriate.

### Data and repositories

- `RootDesk/MyDesk/00_Core/Data/SkillDefinitionRepositoryLogic.mlua` is the definition lookup and catalog source.
- `RootDesk/MyDesk/00_Core/Data/JobStartingSkillRepositoryLogic.mlua` and the job bundle/provider path determine ordered starting skills.
- `RootDesk/MyDesk/04_Roguelike/Player/PlayerRunInventoryComponent.mlua` owns the current run's skill inventory.
- Skill datasets are `SkillDefinitions.csv` plus `WarriorSkillDefinitions.csv`, `MageSkillDefinitions.csv`, `ArcherSkillDefinitions.csv`, `ThiefSkillDefinitions.csv`, and `PirateSkillDefinitions.csv`, with their registered dataset assets.
- `JobStartingSkillEntries.csv` supplies job/slot-index starting entries.

## Equipped Skill Source of Truth

### Actual current structure

There is no distinct `EquippedSkills` profile or loadout collection. The closest current structure is the battle-session presentation state:

```text
BattleSessionComponent
  @Sync SkillSlotIds                 = "skillA|skillB|..."
  @Sync SkillSlotNames               = "nameA|nameB|..."
  @Sync SkillSlotCooldownTurns       = "turnsA|turnsB|..."
  @Sync SkillIconSnapshot            = "skillA~ruidA|skillB~ruidB|..."
  @Sync SkillSlotSourceSnapshot      = owned run-skill snapshot used to build slots
  SkillSlotCount                     = 6
```

`BattleSessionComponent:RefreshSkillSlots(reason)` reads `PlayerRunInventoryComponent.RunSkillSnapshot`, with `SelectedJobStartingSkillIds` as a fallback. It parses `skillId~amount` entries, deduplicates by SkillId, shuffles the candidates with Fisher-Yates, and takes at most six. It keeps the result while the source snapshot is unchanged, then rebuilds when ownership changes or a new battle session initializes.

This means:

- Equipped Skill IDs: **not stored as a durable equipped list**; the synchronized `SkillSlotIds` string is only the current battle bar.
- Explicit slot order: the pipe order is explicit for the current battle bar, but it is generated rather than player-authored or persisted.
- Empty slots: supported when fewer than six unique run skills exist. Missing positions render as empty/disabled slots.
- Maximum displayed slots: six.
- Duplicate displayed skills: not allowed; `RefreshSkillSlots` deduplicates SkillIds even when an inventory amount exceeds one.
- Job restriction: definitions and run acquisition are job-scoped; a future equip mutation must still validate the current job server-side.
- Persistence: the battle bar does not persist across sessions, reconnects, or a new battle-session rebuild.

`BattleEntryStateComponent.LoadoutId` and the run entry context contain a `LoadoutId` seam, but `RunManagerLogic` currently produces an empty value and marks it as not required. No production consumer gives it equipped-skill semantics.

## Owned / Available Skill Source

The current architecture has four different concepts and they must remain separate:

| Concept | Actual source | Meaning |
|---|---|---|
| Available/grantable catalog | `SkillDefinitionRepositoryLogic:GetPlayerGrantableSkillIds` and the per-job datasets | Static player-facing skill definitions. Enemy definitions are excluded. Dataset order is not an equipment order. |
| Job-available skills | `SkillDefinitionRepositoryLogic:GetJobSkillDefinitions(jobId)` | Definitions whose job dataset/tag matches the selected job. |
| Starting skills | `JobStartingSkillEntries.csv`, ordered by `SlotIndex`, then `PlayerRunStateComponent:ApplyJobBundle` | The first `EffectiveStartingSkillSlotCount` entries become run inventory. Base count is two and can be modified by Union effects. |
| Owned/available this run | `PlayerRunInventoryComponent.@TargetUserSync RunSkillSnapshot` | Server-owned serialized inventory, `skillId~amount|...`, with `SkillInventoryRevision`. New-skill and upgrade stages mutate this state through run-manager validation. |
| Permanently unlocked | None found | No persistent player skill-unlock profile is currently implemented. |
| Equipped | None | No separate loadout/equipped collection exists. |

The collection UI is not proof of ownership: `SkillCodexProvider` currently marks the exposed grantable definitions as discovered. New-skill stages offer eligible unowned tier-one families; upgrade stages display owned skills with a valid next tier. Both are run progression UIs, not permanent unlock/loadout sources.

## Skill Icon Source

- Authoritative mapping: `SkillDefinitionRepositoryLogic:ConvertSkillRow` maps each SkillId to definition fields including `IconRuid` and `HudIconRuid`.
- Current player datasets populate `IconRuid`; `HudIconRuid` is presently blank. Battle and overhead HUDs use `IconRuid`.
- `BattleSessionComponent:RefreshSkillSlots` serializes the owned candidate icon map as `SkillIconSnapshot = skillId~IconRuid|...`.
- `BattleQueueHudComponent:SyncIconSnapshot` reparses only when the serialized snapshot changes and caches the result in `_T.IconMap`.
- `BattleQueueHudComponent:GetSkillIconRuid` returns the cached RUID or the shared fallback `1705e3c5b2c146ac9a699f96fb067408`.
- `PlayerOverheadQueueHudComponent`, new-skill choice, upgrade UI, and codex use the same fallback. The codex may additionally fall back to `thumbnail://` cast/hit resources before the default.

A future battle-bar drag ghost should reuse the already-resolved client icon map rather than issue a resource lookup during a gesture. A future lobby loadout editor should use the repository DTO's `IconRuid` and the same fallback policy.

## Slot Order Semantics

Current battle-bar pipe order affects presentation and click lookup, but it is not a persisted gameplay loadout order.

| Consumer | Does current slot order affect it? | Detail |
|---|---|---|
| UI display | Yes | Slot N displays the Nth SkillId/name/cooldown entry. |
| Keyboard binding | No | Slot labels show `1`–`6`, but the slot buttons have no project number-key binding. Skill selection is currently button/click driven. |
| Skill selection | Yes, indirectly | Clicking slot N resolves the Nth SkillId locally and submits that SkillId. |
| Skill execution | No direct slot dependency | Server execution reads a stable SkillId from the reservation queue, not the UI slot number or entity. |
| Combat reservation order | No | Reservation order is append order in `QueuedTileIds`; it is independent of the bar order. |
| Starting-skill initialization | No | Starting order comes from `JobStartingSkillEntries.SlotIndex`, but the battle bar subsequently shuffles unique owned candidates. |
| Save/load order | No | No equipped-order persistence field exists. |

Therefore, swapping two current bar positions changes which SkillId a click on each screen position resolves, while existing queued entries and execution order remain unchanged. A future persistent loadout may intentionally assign input-slot meaning, but that behavior does not exist yet.

## Combat Input Path

The production click-to-effect path is:

```text
BattleQueueHUD slot ButtonClickEvent
  -> BattleQueueHudComponent:OnSkillSlotNClicked()
  -> BattleQueueHudComponent:RequestSlotSkill(slotIndex)
       resolves Nth SkillId from SlotSkillIds
  -> BattleHudPresenterLogic:RequestQueueTile(skillId)
  -> BattleSessionComponent:RequestQueueTile(skillId)  [@ExecSpace("Server")]
       validates requesting user
  -> BattleSessionComponent:TryQueueTile(skillId)
       validates definition/content, run ownership, cooldown,
       queue capacity, and duplicate reservation policy
  -> BattleTurnComponent.QueuedTileIds appends SkillId
  -> TryFreezeSkillQueue copies IDs to ExecutingTileIds
  -> ExecuteNextQueuedTile reads next SkillId
  -> TryExecuteSkill("player_01", skillId)
  -> SkillExecutionLogic builds context and runs effect/presentation steps
```

The client sends a SkillId, not a UI entity UUID. `BattleSessionComponent` checks the sender against the registered player and revalidates skill ownership and usability. No UI entity identity is trusted for gameplay execution.

## Reservation Queue Path

The combat reservation system is a separate server-authoritative model:

- Source: `BattleTurnComponent.@Sync QueuedTileIds`, a pipe-delimited SkillId sequence, plus `QueuedTileCount` and the effective queue capacity.
- Queue length: capacity-driven (the present battle UI is designed around a short three-entry reservation display), not the six bar slots.
- Ordering: click/reservation append order.
- Mutation support already in server code: remove by index, move from/to index, clear, and execute/freeze. There is no current queue drag/reorder UI binding.
- Item identity: SkillIds only, not UI references.
- Consumption: freezing copies editable `QueuedTileIds` to `ExecutingTileIds`, clears the editable queue, and `ExecuteNextQueuedTile` advances through the frozen SkillIds.
- Presentation: `PlayerOverheadQueueHudComponent` dynamically rebuilds visible entries from synchronized queue state and the icon snapshot.

The duplicate reservation check applies when a skill has a positive cooldown; it is queue policy, not the battle-bar duplicate rule. Reservation reordering is explicitly outside the first drag implementation.

## Equipped Order Versus Reservation Order

These are two independent sequences:

```text
Battle bar order:       screen position -> SkillId selected by a click
Reservation order:      SkillId -> SkillId -> SkillId execution sequence
```

A bar reorder must not rewrite, reorder, clear, or reinterpret `QueuedTileIds`/`ExecutingTileIds`. Already-reserved skills remain stable because the queue stores SkillIds. One structure must not be reused for both concerns.

## Persistence

No `_DataStorageService` path was found for run skills, battle slots, or the reservation queue. The only relevant durable profile work found elsewhere is unrelated Union profile state.

| Lifecycle boundary | Owned run skills | Battle bar order | Reservation queue |
|---|---|---|---|
| Leave lobby/start run | Initialized from the selected job's ordered starting skills, subject to effective starting count | Generated from the run inventory when battle initializes | Created as battle-turn state |
| Move between stages/maps during active run | Player-component run inventory remains the authoritative temporary state | Rebuilt for a new battle session; stable only while that session/source snapshot remains stable | Preserved or cleared according to explicit battle/wave policy, not as a loadout |
| End run/defeat | Reset through run inventory reset/default flow | Discarded with battle session | Cleared by battle/result reset paths |
| Reconnect | No durable restoration contract found | Not guaranteed | Not guaranteed |
| Game restart | Not persisted | Not persisted | Not persisted |

Character selection stores temporary job choice and previews starting skills; it does not store equipment. `RunManagerLogic` initializes an empty `RunSkillSnapshot` from starting skills and later grants/upgrades the temporary run inventory. No persistent loadout fallback exists beyond starting-skill initialization.

## Existing Drag Infrastructure

No production project-authored skill/item drag system was found. In particular, there is no reusable pointer-down/move/up state machine, drag threshold, drag ghost, drop-target controller, inventory drag, or UI reorder gesture.

Relevant adjacent conventions are:

- `UnionSystemUILogic:ResetStatCardScroll` delegates wheel, drag, clipping, clamping, and click-versus-drag suppression to native `ScrollLayoutGroupComponent`; it does not implement a custom threshold.
- `NewSkillStageChoiceComponent` uses touch events for selection and, on PC, combines `_InputService:IsPointerOverUI()`, `_InputService:GetCursorPosition()`, `_UILogic:ScreenToWorldPosition()`, and bounds checks for world-space hover.
- `MouseTooltipUIComponent` follows the cursor and clamps a topmost overlay to the screen. Its positioning/overlay convention is reusable for a ghost, but its code is not a drag controller.
- Existing skill slots use `ButtonComponent` transition states and `ButtonClickEvent`; they do not currently have `UITouchReceiveComponent`.

If a future owned list is scrollable, native scroll behavior must remain in control until a real drag begins. The drag ghost must live outside the scroll content/mask and have raycast disabled.

## Verified MSW Pointer APIs

The following capabilities were verified in the MSW API reference, not inferred:

### `UITouchReceiveComponent` client events

- `UITouchDownEvent`
- `UITouchUpEvent`
- `UITouchBeginDragEvent`
- `UITouchDragEvent`
- `UITouchEndDragEvent`
- `UITouchEnterEvent`
- `UITouchExitEvent`

Begin/end drag events provide `Entity`, `TouchId`, and `TouchPoint`; drag events additionally provide `TouchDelta`. UI touch mouse IDs are left `-1`, middle `-2`, right `-3`, while mobile touches start at `1`.

### Input and coordinate services

- `_InputService` exposes `ScreenTouchEvent`, `ScreenTouchHoldEvent`, `ScreenTouchReleaseEvent`, `MouseMoveEvent`, `GetCursorPosition()`, and `IsPointerOverUI()`/`IsPointerOverUI(pointerId)`.
- `IsPointerOverUI` ignores UI whose `RaycastTarget` is false.
- Screen-touch event mouse IDs use a different convention from UI-touch mouse IDs; an implementation must not mix them.
- `_UILogic` exposes `ScreenToUIPosition`, `ScreenToWorldPosition`, `WorldToScreenPosition`, `LocalUIToWorldPosition`, and `UIToWorldPosition`.
- `UITransformComponent` exposes `anchoredPosition`, `RectSize`, `Pivot`, anchors, scale/world position, and `GetWorldCorners()`.
- `MaskComponent` and native scroll-layout clipping are available.

Engine UI routing plus raycast targets can drive enter/exit/drop targeting. If geometric fallback is required, use verified coordinate conversion with `UITransformComponent` bounds/`GetWorldCorners()`; do not invent a `ContainsPoint` API.

## Current Slot Entity Structure

`BattleQueueHUD` contains six 88x88 button slots under `QueuePanel`, positioned at X `-240, -144, -48, 48, 144, 240`:

| Index | Entity name | Entity UUID |
|---:|---|---|
| 1 | `BtnBasicSlash` | `6c09c873-3f2a-4205-866a-506bb96e8ea3` |
| 2 | `BtnHeavySlash` | `bc90b79c-4e8f-4299-81f8-204963e1ac3f` |
| 3 | `BtnPush` | `1d567770-8c5d-4fce-bd4d-3927c5883427` |
| 4 | `SkillSlot_04` | `3a0b0b69-33e8-4bfc-a58a-a65f4fcbfc52` |
| 5 | `SkillSlot_05` | `5d604800-9d64-41c2-964d-4c70b847ac9d` |
| 6 | `SkillSlot_06` | `98b36a26-1796-4c37-8cf2-c1b601abd215` |

The first three legacy names are misleading: all six are dynamically bound, not fixed to those named skills. Each slot has `Background`, four cooldown pips, `CooldownText`, `QueueOrderBadge`, `SelectedHighlight`, a 72x72 `SkillIcon`, and `SlotKeyText`.

- Slot index: authored/bound array position 1–6.
- Current SkillId: Nth entry of the synchronized `SkillSlotIds`/client `SlotSkillIds` pipe sequence.
- Empty state: no Nth SkillId; UI clears/disabled the slot and retains its number label.
- Lock state: no distinct persistent lock model. Runtime enablement depends on phase, ownership/usability, cooldown, and reservation state.
- Hover state: `ButtonComponent` highlighted/pressed/selected/disabled transitions only.
- Click handler: one `ButtonClickEvent` per slot leading to `RequestSlotSkill(index)`.
- Keyboard binding: none, despite visual `1`–`6` labels.

Slots 4–6 are authored disabled but runtime logic sets enable state. A future drag target should not rely solely on `ButtonComponent.Enable`, because empty/temporarily disabled slots still need deliberate drop-target policy.

## Future Drag Sources and Targets

- Source A — owned/available list: desired for the final feature, but no suitable visible list currently exists. The codex and upgrade choice are not equipment inventories.
- Source B — current active/equipped-like slot: six battle bar slots exist and are suitable for a narrow gesture prototype.
- Source C — reservation queue: intentionally out of scope.
- First drop targets: the six battle bar slots for a prototype, or future dedicated equipped slots once a real loadout UI/model exists.

The final owned/equipped UI should live in a dedicated lobby or between-stage management surface backed by a loadout model. It should not overload `CollectionUI`, stage reward selection, or combat reservation state.

## Recommended Drag Semantics

For a future real loadout, use these deterministic rules:

| Case | Recommended result |
|---|---|
| Available skill -> empty equipped slot | Equip into the target slot. |
| Available skill -> occupied equipped slot | Replace the target; return the displaced SkillId to the available list. |
| Equipped A -> occupied B | Atomically swap A and B. |
| Equipped A -> empty B | Move A to B and leave A empty. |
| Drop outside a valid target | Cancel and restore without model mutation. |
| Same SkillId already equipped | Reject/no-op; current battle display already enforces unique SkillIds. |
| Source and target are the same slot | No-op. |

All accepted changes must preserve ownership and job restrictions. No equip/order operation may mutate the current combat reservation sequence.

## UI Visual Feedback Plan

The minimum future states and placement are:

| State | Recommended placement/behavior |
|---|---|
| Normal | Existing slot button/background/icon hierarchy and ButtonComponent transitions. |
| Drag source | Temporary tint/alpha on the source slot's icon/background; preserve its SkillId until authoritative success. |
| Drag ghost | A new raycast-disabled overlay under the skill-management UI root, outside scroll content and masks; follow/clamp using the tooltip convention. |
| Valid drop target | A dedicated target-highlight child per slot. Do not reuse `SelectedHighlight`, which currently represents reservation state. |
| Invalid drop target | Separate invalid tint/outline on hovered target or ghost; never mutate model state. |
| Drop success | Small local scale/punch feedback on source/target only after authoritative acknowledgement and refresh. |
| Drop cancel | Remove ghost/highlights, restore source tint, and optionally show a short invalid pulse. |

Use `UITouchBeginDragEvent` as the transition from click intent to drag intent so the existing skill click does not fire after a drag. If an owned list becomes scrollable, preserve native scroll gestures until that transition.

## Authority Model

Combat and run inventory are server-authoritative even though current combat is player-centric:

- Run inventory mutations are server-only.
- Client requests enter through `@ExecSpace("Server")` methods.
- The server validates the requesting user, SkillId, ownership, job/content restrictions, cooldown, queue state, and phase.
- Synchronized fields are outputs, not client-owned input.

A future client drag controller should own only transient presentation: source/target tracking, ghost movement, and highlight state. It must request a mutation and wait for server-produced state before committing visuals.

For the narrow battle-bar swap prototype, the authoritative request belongs on `BattleSessionComponent`. It should validate sender identity, source/target indices in 1–6, source nonempty, both SkillIds still owned/valid, uniqueness, and a safe battle phase, then atomically swap every index-coupled slot field and publish a revision/refresh. Direct client mutation of `SkillSlotIds` is not acceptable.

For the final persistent lobby loadout, introduce a dedicated player loadout/profile owner and server mutation API, storing stable SkillIds with explicit slot indices. Persistence should use the project's player-profile/DataStorage ownership pattern. Do not overload Union profile data, `QueuedTileIds`, or the currently unused `LoadoutId` without a separate schema/contract decision.

## Risks

### CRITICAL

- Treating the random battle `SkillSlotIds` display as an already-existing persistent equipped model.
- Mutating synchronized slot strings directly on the client or trusting UI entity identity.
- Conflating equipped/bar order with reservation/execution order and thereby changing queued actions.

### HIGH

- Swapping `SkillSlotIds` without atomically swapping parallel names/cooldown data, producing mismatched labels or cooldowns.
- Allowing the existing `ButtonClickEvent` to fire at drag end, accidentally reserving a skill.
- Changing visible slots during execution or reservation without preserving SkillId-based badges and the frozen queue.
- Omitting server validation for job restriction, current ownership, duplicate rule, empty source, or battle phase.
- Advertising persistence that the current run/battle state does not provide.

### MEDIUM

- Gesture competition with native `ScrollLayoutGroupComponent` once an owned list is introduced.
- Incorrect mouse/mobile `TouchId` assumptions, multi-touch handling, or missing cancel cleanup.
- `RefreshSkillSlots` rerandomizing and overwriting local ordering after the owned snapshot changes.
- Disabled/cooldown/empty buttons failing to receive intended drop targeting if Button enablement is reused as drag enablement.
- Starting-skill order or run-earned skill changes being mistaken for equipped order.

### LOW

- Ghost clipping under masks, incorrect sorting, or a ghost with `RaycastTarget=true` intercepting its own drop.
- Tooltip/hover audio competing with drag feedback.
- Legacy slot entity names misleading future bindings.

## Minimum Vertical Slice

The architecture supports only one honest minimal first slice without inventing a loadout system:

> Drag one populated **current battle skill-bar slot** onto another populated bar slot, request an authoritative index swap, refresh the six-slot presentation, confirm that clicks now submit the swapped SkillIds, and confirm that the existing `QueuedTileIds` sequence is unchanged.

Scope of that later implementation:

1. Add touch-drag handling to the existing six slot entities through the UI builder/runtime component.
2. Show source, ghost, and valid/invalid target feedback.
3. On A-to-B drop, send source/target indices to a server-authoritative battle-session swap request.
4. Atomically swap the current battle slot ID/name/cooldown entries and refresh the HUD.
5. Verify click-to-reservation uses the new positional SkillIds.
6. Verify already-reserved and executing SkillId sequences do not change.
7. State the persistence boundary explicitly: current battle session only; a later refresh/new session may regenerate the bar.

This slice validates drag gesture isolation, visual targeting, server authority, and preservation of combat semantics. It is **not** the final Shogun Showdown-style owned-to-equipped feature. Before that final feature, a separate architecture step must define a visible owned list, explicit equipped slots, loadout persistence, initialization/fallback, and server mutation contract.

## Step 0 Final State

- Production files modified: **NONE**
- Audit document created: `Docs/SkillDragSystemAudit.md`
- Drag-and-drop implementation: **NOT STARTED**
- Combat, skill data, save data, UI assets, and input bindings: **UNCHANGED**

### STEP 1 Battle Slot Swap

#### Scope

Step 1 implements one battle-session-only vertical slice: drag one occupied `BattleQueueHUD` skill slot onto another occupied slot and request a server-authoritative positional swap. It does not introduce a permanent loadout, inventory-to-slot equipment, removal, reservation queue reorder, save data, or new input bindings.

#### Mutation owner

`BattleSessionComponent` remains the only authoritative owner. `RefreshSkillSlots(reason)` is still the initialization/rebuild path for `SkillSlotIds`; the new `RequestSwapBattleSkillSlots(sourceIndex, targetIndex, requestId, expectedRevision)` and `TrySwapBattleSkillSlots(...)` methods are the only post-initialization reorder path.

On success the server swaps the two `SkillSlotIds` entries and their index-coupled `SkillSlotNames` and `SkillSlotCooldownTurns` presentation entries. It increments `SkillSlotRevision`. `SkillIconSnapshot` remains a SkillId map, and `SkillSlotSourceSnapshot` remains the owned-source snapshot.

#### Drag source and drop target

- Source: one occupied slot among the existing six battle-bar positions.
- Target: a different occupied slot among those same six positions.
- Empty, same-slot, outside-bar, non-skill, and invalid-index drops are rejected/cancelled.
- `UITouchReceiveComponent` is attached to each existing slot through `UIBuilder`.
- Engine `UITouchEnterEvent`/`UITouchExitEvent` maintains hover feedback. Drag/end target resolution converts the pointer with `ScreenToUIPosition` and compares it against the existing BottomCenter queue/slot anchors, pivots, and `RectSize` in that same top-level UI coordinate space. Maker Play exposed that `GetWorldCorners()` reports editor-view coordinates that must not be mixed with simulated screen input.

#### Drag threshold and click suppression

- Native events: `UITouchBeginDragEvent` -> `UITouchDragEvent` -> `UITouchEndDragEvent`.
- The client accumulates `TouchDelta` distance and enters real drag mode only after `SkillSlotDragThreshold = 12` screen pixels.
- A normal short click keeps the existing `ButtonClickEvent -> RequestSlotSkill(index)` path.
- Once the threshold is crossed, `RequestSlotSkill` rejects while the gesture is still a drag candidate/active and for `0.25` seconds after release. The state guard is required because Maker can deliver `ButtonClickEvent` before `UITouchEndDragEvent`; the timer alone is insufficient for a long drag.

#### Ghost and target feedback

- `SkillDragGhost` is a disabled-by-default, raycast-disabled root overlay sprite with `OrderInLayer = 250` and alpha `0.72`.
- It reuses the existing synchronized `SkillIconSnapshot` lookup and default icon fallback.
- The source icon is temporarily muted; authoritative slot data is never cleared or optimistically reordered.
- Each slot has a separate raycast-disabled `DragTargetHighlight`. Existing reservation `SelectedHighlight` entities are not reused or changed.
- Success/reject keeps the ghost/highlight in a short pending state until the synchronized server receipt arrives; a bounded `0.75` second cleanup timeout prevents stuck visuals.

#### Server swap API and validation

The client proposes only `sourceIndex`, `targetIndex`, a monotonically increasing battle-local `requestId`, and the observed `SkillSlotRevision`. It never sends source/target SkillIds.

The server validates:

1. requesting user matches the registered battle player;
2. request ID is positive and newer than the single bounded last receipt;
3. both indices are integers inside `1..SkillSlotCount`;
4. source and target differ;
5. observed revision equals current `SkillSlotRevision`;
6. content state is `VALID` and the battle has no result;
7. `TurnState` exists, phase is `PlayerTurn`, and `IsActionProcessing == false`;
8. both current authoritative slots are occupied;
9. both current SkillIds pass content validation;
10. both current SkillIds are still owned by the run player.

Duplicate/replayed IDs are ignored, and older IDs are rejected. The client initializes its next ID from the synchronized last receipt, so HUD reload does not reuse an already-consumed ID. A changed slot revision produces `STALE_SLOT_REVISION` without mutation.

#### Battle-state rule

Swap is allowed only in the existing idle player decision state:

```text
ContentValidationState == "VALID"
BattleResult == ""
TurnState.BattlePhase == "PlayerTurn"
TurnState.IsActionProcessing == false
```

Enemy turn, action execution, transition/not-ready content, and result states reject the request.

#### Queue and execution independence

The swap code never writes `QueuedTileIds`, `ExecutingTileIds`, `ExecutingTileIndex`, or the overhead queue UI. Those sequences already contain stable SkillIds, so an already-reserved or executing action keeps the same semantic skill after a bar reorder.

After a successful swap, the unchanged click handler resolves the Nth entry from the newly synchronized `SlotSkillIds`, so position 1/2 now selects the new SkillId in that position. There are still no keyboard bindings for the six visual number labels.

#### No-persistence rule

The swap exists only for the current `BattleSessionComponent`. No DataStorage, profile/loadout field, schema migration, reconnect restoration, or character-selection behavior was added. A later `RefreshSkillSlots` rebuild/new battle session keeps its previous initialization behavior.

#### Step 1 test matrix

| Test | Maker Play result |
|---|---|
| Basic A/B swap | PASS — actual pointer drag changed `divine_swing|brandish` to `brandish|divine_swing`; revision `2 -> 3`. |
| Reverse swap | PASS — actual pointer drag from slot 2 back to slot 1 restored the original order; revision `3 -> 4`. |
| Same slot | PASS — actual long drag back onto slot 1 cancelled with target `1`; slots and queue were unchanged. |
| Outside/empty drop | PASS — outside release resolved target `0` and cancelled; server probe of occupied slot 1 to empty slot 3 returned `TARGET_SLOT_EMPTY`. |
| Normal click | PASS — a real `ButtonClickEvent` on slot 1 followed the unchanged handler and queued `divine_swing`. |
| Drag release | PASS after runtime fix — long same-slot drag logged `slot click suppressed`; post-release queue remained empty. |
| Queued skill stability | PASS — swapping while `QueuedTileIds=divine_swing` kept it byte-for-byte unchanged. |
| Execution stability | PASS — controlled `ExecutingTileIds=divine_swing` probe rejected during processing and preserved/restored both session and turn execution snapshots. |
| Post-swap click identity | PASS — with authoritative order `divine_swing|brandish`, existing slot-1 then slot-2 click handlers queued `divine_swing|brandish` in the same positional order. |
| Index tamper | PASS — controlled `source=0`, `target=999` returned `SLOT_INDEX_OUT_OF_RANGE`; no mutation. Fractional wire input is excluded by the typed integer RPC signature. |
| Duplicate/stale request ID | PASS — request `119179` replay returned `DUPLICATE_REQUEST`; `119178` returned `STALE_REQUEST`. |
| Stale slot revision | PASS — old revision returned `STALE_SLOT_REVISION`; no mutation. |
| State lock | PASS — processing returned `ACTION_PROCESSING`; EnemyTurn probe returned `NOT_PLAYER_DECISION_STATE`; state was restored. |
| Visual state/cleanup | PASS — runtime probe reported active ghost and slot-2 highlight, then both false after cleanup. |
| Build/runtime errors | PASS for Step 1 — refreshed build contained zero errors and no runtime error stack referenced the new drag/swap methods. |

Maker evidence was collected in Play at 1920x1080 simulated resolution. The pre-existing `INVALID_PLAYER` RunManager/UnionEffect entry logs still occur when entering the controlled test battle and are outside this Step 1 drag-swap change.

### STEP 2 Empty-slot Move / Full Reorder

#### Generalized authoritative mutation

Step 2 replaces the narrow Step 1 swap naming with one reorder path:

```text
BattleQueueHudComponent:RequestAuthoritativeSkillSlotReorder
  -> BattleHudPresenterLogic:RequestReorderBattleSkillSlot
  -> BattleSessionComponent:RequestReorderBattleSkillSlot
  -> BattleSessionComponent:TryReorderBattleSkillSlot
```

The request still contains only source/target indices, request ID, and the observed slot revision. The server resolves current SkillIds from the authoritative session. Existing sender, index, replay, stale-revision, content, ownership, and idle-`PlayerTurn` validation remains in force.

#### Fixed six-slot representation

Step 1's nonempty-token parser would compact a snapshot after a move. Step 2 replaces it with fixed-position parsing and serialization for exactly six indices, preserving empty tokens.

Example:

```text
A|B|C
source 1 -> empty target 4
|B|C|A||
```

No insertion, compaction, dynamic slot creation, or index rebinding occurs. The client uses the same fixed-position token semantics for IDs, names, cooldowns, queue labels, and click lookup.

#### Reorder semantics

- Occupied source -> occupied target: direct `SWAP`.
- Occupied source -> empty target: direct `MOVE`; source becomes empty and target receives the source ID/name/cooldown.
- Empty source: cannot enter drag state and sends no request.
- Same slot or outside/non-slot target: client cancel/no mutation.
- Empty and occupied targets share the same subtle target-highlight family. Because an empty slot has no icon, its highlighted fixed frame reads as a move destination without new text or colors.
- The server rejects an already-corrupt authoritative bar containing duplicate nonempty SkillIds with `DUPLICATE_SKILL_SLOT`. A valid reorder is a permutation/move and cannot create a duplicate.
- There are still no number-key bindings. Slot position remains the click/input position, so a moved SkillId is resolved by its new slot's existing handler.

#### Queue, execution, and persistence boundaries

`QueuedTileIds`, `ExecutingTileIds`, execution indices, the overhead queue, and queue order are not written by the reorder path. They remain stable SkillId sequences. Reorder is still current-`BattleSessionComponent` state only: no DataStorage, loadout profile, reconnect restoration, or initialization change was added.

#### Step 2 Maker Play matrix

| Test | Maker Play result |
|---|---|
| Occupied -> empty | PASS — actual drag `1 -> 4` changed `divine_swing|brandish` to `|brandish||divine_swing||`; operation `MOVE`. |
| Occupied -> occupied | PASS — actual drag `4 -> 2` produced `|divine_swing||brandish||`; operation `SWAP`. |
| Empty source | PASS — actual drag attempt from empty slot 1 left candidate/active/ghost false and revision unchanged. |
| Empty target highlight | PASS — runtime drag over empty slot 5 reported target 5, highlight true, ghost true; cleanup returned both false. |
| Six-index stability | PASS — subsequent actual moves placed `brandish` in slot 1 and `divine_swing` in slot 6 as `brandish|||||divine_swing`. |
| Same/outside drop | PASS — same-slot target 2 and outside target 0 cancelled; revision and queue were unchanged, visuals cleared. |
| Normal/post-move click | PASS — after moving `divine_swing` to slot 6, the unchanged slot-6 click handler queued `divine_swing`. |
| Queued SkillId stability | PASS — moving queued `divine_swing` from slot 2 to slot 5 kept `QueuedTileIds=divine_swing`. |
| Executing SkillId stability | PASS — controlled `ExecutingTileIds=divine_swing` probe rejected with `ACTION_PROCESSING` and preserved session/turn execution snapshots. |
| Duplicate protection | PASS — controlled duplicate authoritative snapshot rejected with `DUPLICATE_SKILL_SLOT` and was restored. |
| Index/same/stale validation | PASS — returned `SLOT_INDEX_OUT_OF_RANGE`, `SAME_SLOT`, and `STALE_SLOT_REVISION` without mutation. |
| Replay protection | PASS — repeated/latest request returned `DUPLICATE_REQUEST`; lower request returned `STALE_REQUEST`. |
| Build/runtime | PASS — refreshed build had zero errors and no runtime error stack referenced Step 2 reorder/fixed-slot methods. |

Maker evidence was collected in an actual battle at 1920x1080 simulated resolution. The three pre-existing `INVALID_PLAYER` RunManager/UnionEffect entry errors remain unrelated to the reorder implementation.

### STEP 3 Direct Drag UX Polish

#### Client-only tuning

Step 3 changes only `BattleQueueHudComponent` presentation. The Step 2 request payload, authoritative mutation, fixed six-slot representation, queue/execution snapshots, persistence boundary, skill definitions, and battle rules are unchanged.

- Activation threshold: `12px -> 10px`. Direct clicks still use the existing button path; drag feedback starts only after the threshold.
- Ghost: existing skill icon at `1.04x`, `86%` alpha, with a small `(+14px, +18px)` pointer offset. Invalid space reduces it to a muted `58%` alpha.
- Source: the original icon remains in place at a muted cool-gray `34%` alpha, so origin remains readable without duplicating emphasis.
- Occupied target: existing gold target frame at `90%` alpha, communicating `SWAP`.
- Empty target: the same gold frame at `58%` alpha, communicating a quieter `MOVE` destination without adding text or assets.
- Pending: ghost snaps to the resolved target at `62%` alpha while the existing `0.75s` authoritative timeout remains active.
- Success: source and target icons run a `0.14s` `0.90 -> 1.04 -> 1.00` snap after the authoritative receipt is rendered. Gameplay state is not delayed.
- Cancel/reject/timeout: ghost returns to the source and fades for `0.12s`; no popup or sound is added.
- Input transition guard: a successful skill click blocks new drag activation for `0.25s`, closing the short client/server state-update window before noneditable battle state is presented.

#### Step 3 Maker Play matrix

| Test | Maker Play result |
|---|---|
| Build | PASS — workspace refresh completed with zero build errors. |
| Occupied target close-up | PASS — held `1 -> 2` showed muted source, offset `86%` ghost, and the stronger occupied gold frame; authoritative result was `brandish|divine_swing||||`. |
| Empty target close-up | PASS — held `2 -> 4` showed the quieter empty-frame treatment; authoritative result was `brandish|||divine_swing||`. |
| Rapid `4 -> 6 -> 4` | PASS — both `40ms`/fast-pointer end positions resolved to their actual fixed targets and produced two successful `MOVE` receipts. |
| Queue-HUD crossing | PASS — crossing the execute/cancel area produced no slot highlight and a muted invalid ghost; snapping back to slot 6 at release resolved target 6. |
| Success motion | PASS — each successful receipt logged and ran bounded `0.14s` source/target snap feedback after the refreshed icons were rendered. |
| Cancel motion and cleanup | PASS — outside drop resolved target 0, returned/faded for `0.12s`, and a new drag begun after `170ms` succeeded, proving no hung visual/input state. |
| Direct click | PASS — normal click still queued the current slot SkillId and ran the existing queue feedback. |
| Noneditable transition | PASS — click followed by a drag attempt `40ms` later produced no drag candidate/activation while battle processing changed to true. |
| Queue stability | PASS — existing queued SkillIds remained unchanged by reorder; no queue/execution method was edited. |
| Runtime | PASS — Step 3 test window produced zero runtime errors. The separately observed three pre-existing `INVALID_PLAYER` RunManager/UnionEffect entry errors remain unrelated. |

Captured Maker evidence (1920x1080 simulated input space):

- occupied target: `maker_play_20260902_150505_725.png`
- empty target: `maker_play_20260902_150605_995.png`
- invalid queue-HUD crossing: `maker_play_20260902_150651_514.png`
- settled result: `maker_play_20260902_151556_505.png`

### STEP 4 Loadout Necessity Audit

#### Decision

**NEEDS ACTIVE LOADOUT: NO.**

The current production game cannot naturally produce more than six distinct run-owned skills. All reachable owned skills therefore fit in the existing six fixed Battle slots. An Available Skills -> Active 6 Skills equip layer would not create a real choice today; it would add an inventory-management step around a set that is already fully displayable.

The appropriate next boundary, if player-authored order should survive more than one Battle, is a **run-scoped ordered Battle-bar configuration**. It should preserve the Step 1-3 order across Battles without changing which skills are active. No permanent account loadout or DataStorage schema is justified.

#### Every `RunSkillSnapshot` mutation and acquisition path

| Path | Production behavior | Changes distinct count? | Reachable with current data? |
|---|---|---:|---|
| Run reset | `PlayerRunInventoryComponent:ResetForRun` clears `RunSkillSnapshot`. | Resets to 0 before initialization | Yes |
| Starting skills | `RunManagerLogic:ApplyJobSelection` calls `InitializeStartingSkills` when the snapshot is empty. `PlayerRunStateComponent:ApplyJobBundle` takes the first `EffectiveStartingSkillSlotCount` authored entries. | Establishes 2 or 3 distinct skills | Yes |
| New-skill reward map | `NewSkillStageChoiceComponent` offers only unowned tier-1 families for the selected job, then calls `RunManagerLogic:GrantRunSkill` -> `PlayerRunInventoryComponent:GrantSkill`. | +1 distinct family per successful choice | Yes |
| Upgrade reward map | `UpgradeSkillStageLogic` validates the authored upgrade path, then calls `PlayerRunInventoryComponent:UpgradeSkill`. The method removes one base copy and adds one upgrade copy atomically. | Normally 0; replacement, not addition | Yes |
| Stage-clear reward | `RunManagerLogic:GrantRunReward` -> inventory `GrantRunReward` accepts only `CURRENCY` and `CONSUMABLE`. Current `StageRewardDefinitions.csv` contains only gold. | No | Yes, but not for skills |
| Shop | `ApplyShopPurchase` supports a generic `SKILL` reward and has no six-skill cap. Current `ShopEntries.csv` contains only `ITEM` rewards, so no authored shop offer reaches this branch. | Could add a distinct skill | Logic seam exists; current data does not use it |
| Union unlock | `ADDITIONAL_SKILL_UNLOCK` is authored with `IsImplemented=false`; the production Union resolver does not expose or apply it. | No current mutation | No |
| Augment/passive/relic | These mutate their own run-owned augment/item state. No production caller grants a skill through them. | No | No skill path |
| Public future grant seam | `RunManagerLogic:GrantRunSkill` validates any skill definition and delegates to uncapped `GrantSkill`. Its only current production caller is the new-skill stage. | Could add distinct skills if a future adapter calls it | Not beyond the current new-skill stage |

`RunSkillSnapshot` is an amount snapshot, not an ordered loadout. `AddSnapshotAmount`/`SetSnapshotAmount` rebuild it in lexicographic SkillId order. Acquisition order is therefore not retained.

#### Actual distinct-skill bounds

Current tier-1 family counts are:

| Job | Tier-1 families | Authored starting entries | Reachable family cap |
|---|---:|---:|---:|
| Warrior | 3 | 3 | 3 |
| Mage | 6 | 6 | 6 |
| Archer | 3 | 3 | 3 |
| Thief | 3 | 3 | 3 |
| Pirate | 3 | 3 | 3 |

The base starting count is exactly `StartingSkillSlotCount = 2`. The production Union effect source is `AllocatedUnionStats`; its implemented `STARTING_SKILL` stat has one level worth `+1`. `UnionUpgradeDefinitions.csv` is legacy/non-production for effect resolution, and `ADDITIONAL_SKILL_UNLOCK` is disabled. Thus a run starts with exactly 2 distinct skills, or 3 with the maximum currently implemented Starting Skill bonus.

Each production node graph has three REST reward boundaries. For `region_01_stage_01`, the first reward is a new-skill map when an unowned family exists. Later Region 01 rewards use 75% upgrade / 25% new-skill selection; Kerning rewards use that same 75% / 25% branch from their first REST. A new-skill selection adds one unowned family, while an upgrade keeps the distinct count unchanged.

| Measure | Actual result |
|---|---|
| Minimum | **2** distinct skills: base run start; also a possible Kerning completion count when all three reward rolls choose upgrades. |
| Normal/modal | **3** for the four three-family jobs. In the default Region 01 graph, Mage normally ends with 3 without the Union bonus or 4 with it when the two later 75% branches choose upgrades. Kerning commonly remains in the 2-3/3-4 range depending on Union and the reward rolls. |
| Maximum | **6**, reachable only by Mage: start with 3 using the implemented `+1` Union bonus, then receive three new-family rewards. Without that bonus, Mage's maximum is 5. Every other job is hard-limited by its three tier-1 families. |

The exact current production answer to the key question is therefore: **`RunSkillSnapshot` has uncapped storage APIs, but production gameplay/data cannot make it contain more than six distinct skills.**

#### What would happen above six today

There is no acquisition-time cap in `GrantSkill` or the shop's `SKILL` branch. If future data or a new caller created seven or more distinct entries, acquisition would succeed and all entries would remain in `RunSkillSnapshot`.

At Battle initialization, however, `BattleSessionComponent:RefreshSkillSlots` would:

1. read `RunSkillSnapshot`, falling back to `SelectedJobStartingSkillIds` only when it is empty;
2. extract and deduplicate every SkillId;
3. Fisher-Yates shuffle the complete candidate list;
4. take `min(6, candidateCount)` into `SkillSlotIds`;
5. build names/cooldowns for those selected six, while keeping icon/presentation records for all candidates.

So the present hypothetical overflow behavior is **random-six truncation at presentation time**. It is not first-six, acquisition order, job-definition order, overwrite, scroll/paging, an error, or an enforced ownership cap. The omitted skills remain owned but have no normal Battle-bar button, making them effectively inaccessible through the current click UI. This latent behavior should be revisited before any future content raises a job above six families or authors a shop/event skill grant.

#### Battle-to-Battle order

Step 1-3 reorder writes only the current map-scoped `BattleSessionComponent.SkillSlotIds` and its parallel presentation fields. It never writes `RunSkillSnapshot` or another player-owned ordered configuration.

Every Battle entry calls `ApplyRunJobConfiguration` -> `RefreshSkillSlots`. The result across Battles is conditional but not reliably persistent:

- When the reward map changes ownership by adding or upgrading a skill, the new snapshot differs from `SkillSlotSourceSnapshot`; the next Battle reshuffles and rebuilds the bar, discarding the player-authored order.
- Entering a different physical Battle map (for example Region 01 Battle -> boss map) uses that map's separate session state and rebuilds from an empty source cache.
- If the same physical Battle map is reused and the owned snapshot is byte-for-byte unchanged, the source-snapshot early return can incidentally retain the existing order. This is an implementation side effect, not a run persistence contract.

A new Battle does **not** restore job/acquisition order. When it rebuilds, it generates another random order. The Step 1-3 arrangement therefore does not safely survive Battle 1 -> Battle 2 for the same run.

#### Model A / B / C evaluation

| Model | Fit for current MapleTactics | Decision |
|---|---|---|
| A — all owned run skills active, maximum six, reorder only | Matches every reachable production state. Keeps all build rewards usable, preserves the readable six-slot bar, and adds no between-Battle equip friction. | **Recommended** |
| B — own more than six, equip an active six | No current run can reach the condition that gives equip meaningful gameplay value. Implementing it now would create schema/UI/validation work without a real seventh-skill decision. | Defer until production content can exceed six |
| C — own more than six, page/scroll the Battle bar | Also solves a nonexistent current problem and weakens one-glance positional readability during short tactical decisions. It would make direct drag ordering and slot memory less predictable. | Not recommended |

Shogun Showdown is useful here as interaction inspiration: its combat is built around readable attack tiles, deliberate ordering, upgrades, and a short execution queue. MapleTactics should preserve that directness, but it should not copy an inventory/equip structure that its own skill economy does not require. Model A keeps combat decisions quick, leaves roguelike build choice in acquisition/upgrade decisions, keeps six-slot readability, and imposes the least management friction.

References used only for the interaction comparison: [Official Shogun Showdown Tiles wiki](https://shogunshowdown.wiki.gg/wiki/Tiles), [Shogun Showdown on Steam](https://store.steampowered.com/app/2084000/Shogun_Showdown/).

#### Persistence recommendation

| Scope | Benefit | Cost/risk | Recommendation |
|---|---|---|---|
| Battle-only | Already implemented; no additional state. | Reorder is lost on ownership change/new Battle map and cannot establish reliable positional memory. | Acceptable prototype, not the desired final Step 1-3 behavior |
| Run-only | Preserves one ordered six-position bar while the owned set evolves; naturally resets with the run and selected job. | Needs one player-owned, server-authoritative ordered slot field plus reconciliation when a skill is added/upgraded. | **Recommended next scope** |
| Permanent account | Could remember preferences across runs. | Run skill sets vary by job and rewards; creates stale/missing SkillIds, migration/fallback policy, and DataStorage complexity without current gameplay value. | Do not implement |

For Model A, the minimum future architecture is not an equip system: keep `RunSkillSnapshot` as ownership and add a separate **run-scoped ordered six-position bar configuration** owned by player run state (or a dedicated player-owned run skill-bar component). Battle reorder requests should update that owner after server validation, and Battle initialization should reconcile the saved order against current ownership: retain surviving positions, replace an upgraded SkillId in place, and place a newly acquired SkillId into the first empty position. This remains per-run and must not use DataStorage.

#### UI recommendation

No `보유 스킬` equip UI is needed for Model A. The existing `BattleQueueHUD` is the correct and sufficient place to reorder the six active/owned skills.

If future production content genuinely raises the reachable family count above six and Model B becomes necessary, use the **run inventory UI** as the single `보유 스킬` location. It keeps equipment decisions between Battles, avoids expanding the combat HUD, and is lower-friction than a separate settings overlay. Do not add that UI under current rules.

#### Step 4 final state

- NEEDS ACTIVE LOADOUT: **NO**
- Recommended model: **Model A**
- Recommended persistence: **run-only ordered Battle-bar configuration**
- Recommended current UI: **existing BattleQueueHUD; no owned-skill equip panel**
- Production files modified: **NONE**
- Documentation modified: `Docs/SkillDragSystemAudit.md` only
- Loadout/equip implementation: **NOT STARTED**
- Step 4 stop condition: **satisfied**

### STEP 5 Run-scoped Skill Bar Order

#### Ownership and lifecycle

`PlayerRunInventoryComponent` now owns a separate server-authoritative, fixed six-position Battle skill-bar order:

- `RunSkillSnapshot` remains the ownership/amount source of truth.
- `RunSkillBarSlotIds` stores exactly six run-scoped positions, including empty gaps.
- `RunSkillBarRevision` versions authoritative order mutations.
- `ResetForRun` clears the order and revision, so a new run receives a fresh arrangement.
- No DataStorage, account profile, active-loadout model, equip UI, or reservation-queue persistence was added.

The first Battle initialization performs the existing Fisher-Yates default generation once, then commits that result to the run owner. Every later Battle copies the stored order instead of shuffling again.

#### Reconciliation rules

The run owner reconciles order against current ownership without compacting valid positions:

- still-owned unique skills remain in their existing positions;
- removed skills clear their positions;
- a newly owned distinct skill enters the first empty position;
- an upgrade replaces the exact base-skill position with the validated upgrade SkillId;
- duplicate/corrupt positions are cleared and repaired from the owned set;
- fixed empty gaps remain fixed and are serialized explicitly;
- more than six distinct owned skills returns/logs `FUTURE_CONTENT_GUARD`, preserves the existing active six where possible, and reports overflow IDs instead of silently selecting a new random six.

Battle reorder validation still occurs in `BattleSessionComponent`. A successful occupied swap or empty-slot move must first commit the same six-position result through `PlayerRunInventoryComponent:CommitRunSkillBarOrder`; only then does the map-scoped synchronized Battle snapshot publish it. A rejected owner commit leaves the Battle session unchanged.

#### Entry-order correction

`InitializeFromEntry` previously called `ApplyRunJobConfiguration` before `RegisterPlayer`, while that method read `self.PlayerEntity`. On the first entry frame this value was not yet valid, producing the known `INVALID_PLAYER` Union/run errors and a temporary nonpersistent fallback shuffle.

`ApplyRunJobConfiguration` and `RefreshSkillSlots` now receive the validated entry player explicitly. This removes the fallback frame without changing registration order or other Battle lifecycle behavior.

#### Queue and UI boundaries

- `QueuedTileIds`, `ExecutingTileIds`, execution indices, cooldown rules, and queue ordering remain independent SkillId sequences.
- Existing queued/executing skills are never rewritten by bar reorder.
- STEP 3 threshold, ghost, source dim, target feedback, success/cancel motion, and click suppression are unchanged.
- No `.ui` file, slot UUID, slot count, icon source, hotkey behavior, skill definition, or gameplay rule changed.

#### Step 5 Maker Play matrix

| Test | Maker Play result |
|---|---|
| Clean build | PASS — refreshed build contained 500 Info, 2 Warning, and 0 Error entries. |
| First Battle initialization | PASS — one Fisher-Yates result was committed immediately as run order; no `INVALID_PLAYER` or nonpersistent fallback entry occurred after the entry-owner correction. |
| Actual occupied drag | PASS — actual drag `1 -> 2` committed `brandish|divine_swing|||| -> divine_swing|brandish||||` to both BattleSession and the run owner. |
| Reorder queue isolation | PASS — the successful reorder receipt logged empty queued/executing snapshots, matching the pre-drag state. |
| Direct click after reorder | PASS — slot 1 queued its new SkillId through the unchanged click path. |
| Battle 1 -> 2 -> 3 | PASS — controlled real-session entries for stages 1, 2, and 3 all resolved `divine_swing|brandish||||`; both continuation initializations succeeded. |
| Different physical map | PASS — transfer from `region_01_battle` to `region_01_boss` initialized stage 4 with the same run order and revision. |
| New skill | PASS — a granted distinct skill entered the first empty position while existing positions remained fixed. |
| Upgrade | PASS — `brandish -> brave_slash` retained the exact previous slot. |
| Removal | PASS — the removed skill's position cleared without compacting later positions. |
| Duplicate repair | PASS — reconciliation retained one owned occurrence and repaired duplicate/corrupt positions. |
| Six-skill run | PASS — a six-skill Mage order persisted exactly after an authoritative custom reorder. |
| Overflow guard | PASS — a controlled seventh distinct skill produced explicit `FUTURE_CONTENT_GUARD` evidence and preserved the existing six. |
| New run reset | PASS — the previous six-skill/custom order cleared to empty revision 0 before the new run's first initialization. |

Captured Maker evidence used for the final physical-map close-up:

- boss-map persisted order: `maker_play_20260902_162431_093.png`

#### Step 5 final state

- Active loadout/equip system: **NOT ADDED**
- Persistence scope: **current run only**
- Authoritative owner: **PlayerRunInventoryComponent**
- Battle initialization: **stored run order; no per-Battle reshuffle**
- Reservation queue drag/order changes: **NONE**
- UI asset changes: **NONE**
- DataStorage/account persistence: **NONE**
- STEP 5B stop condition: **satisfied**

### STEP 6 Final Regression

#### Final production architecture

The production responsibility boundary remains intentionally narrow:

```text
PlayerRunInventoryComponent
  RunSkillSnapshot       = run-owned SkillId/amount ownership
  RunSkillBarSlotIds     = run-owned fixed six-position order
  RunSkillBarRevision    = authoritative order version
             |
             | Battle initialization copies; validated drag commits here first
             v
BattleSessionComponent
  SkillSlotIds           = map-scoped Battle presentation/input order
  SkillSlotRevision      = Battle receipt/version state

BattleTurnState / BattleSession execution fields
  QueuedTileIds          = queued SkillIds
  ExecutingTileIds       = executing SkillIds
  ExecutingTileIndex     = execution progress
```

`RunSkillSnapshot` never became an equip/loadout order. `RunSkillBarSlotIds` never became a queue. `BattleSessionComponent.SkillSlotIds` remains presentation/input state and does not own run inventory. Queue and execution sequences retain SkillIds and are not rewritten when the bar moves.

The only normal Fisher-Yates path is the first `GetOrInitializeRunSkillBarOrder` call of a new run. The remaining shuffle in `BattleSessionComponent:RefreshSkillSlots` is a documented compatibility fallback used only when a valid run owner is unavailable; it was not reached in valid first-entry, continuation, or different-map tests.

#### Authoritative mutation and lifecycle rules

- A click remains a click until accumulated pointer movement reaches the exact 10 px threshold.
- Occupied target means swap; empty target means move without compaction.
- Same slot, outside target, empty source, stale revision, replayed request, invalid index, non-decision phase, action processing, ended Battle, and unavailable content all reject without mutation.
- A successful request commits the expected six-slot transition to `PlayerRunInventoryComponent` before publishing the matching Battle snapshot.
- Acquisition reconciles a new distinct SkillId into the first empty slot while preserving every surviving position.
- Upgrade replaces the base SkillId in its exact position. Removal clears only the removed position.
- A seventh distinct owned SkillId is retained in ownership but reported by `FUTURE_CONTENT_GUARD`; the active six remain stable and no random replacement occurs.
- `StartNewRun` clears the order, revision, and ownership snapshot before the new job initializes. Starting another run before using the first one follows the same clean reset path.
- Drag cleanup owns candidate/active/cancelling flags, source/target indices, pending request state, timers, ghost, source treatment, and all target highlights. Success, cancel, server rejection, timeout, and map transfer all converge on the same cleared state.

#### A-X final regression matrix

| ID | Regression | Result | Evidence |
|---|---|---|---|
| A | Refresh/build | PASS | 500 Info, 2 pre-existing Warning, 0 Error. |
| B | Fresh Play startup | PASS | 292 Info, 0 Warning, 0 Error. |
| C | Normal slot click | PASS | Slots 1 and 2 queued their displayed SkillIds; no drag activation occurred. |
| D | 10 px activation threshold | PASS | 5 px jitter stayed a candidate; a 10 px drag activated. |
| E | Occupied-slot swap | PASS | Actual `1 -> 2` swapped both Battle and run order exactly once. |
| F | Empty-slot move | PASS | Actual `1 -> 4` preserved the empty gap and did not compact. |
| G | Same-slot release | PASS | Cancelled as `INVALID_TARGET`; no order or revision mutation. |
| H | Outside/HUD-edge release | PASS | World, queue-HUD area, and 25 stress releases cancelled with target 0. |
| I | Empty source | PASS | No candidate, request, receipt, or mutation was created. |
| J | Click after moved skill | PASS | The moved slot queued its new displayed SkillId through the unchanged click path. |
| K | Rapid sequential reorders | PASS | `1<->2`, `2->4`, `4->6`, `6->1` completed sequentially without loss, duplication, or ghost mutation. |
| L | 50-gesture stress | PASS | 25 accepted swaps + 25 outside cancels; 50 candidates/activations, 0 rejects, 0 stale/replay, 0 runtime Error. |
| M | Queue/execution isolation | PASS | Queued/executing SkillIds, execution index, queued action, and turn number were stable across controlled reorder. |
| N | Battle-state guards | PASS | `CONTENT_NOT_READY`, `BATTLE_ALREADY_ENDED`, `NOT_PLAYER_DECISION_STATE`, and `ACTION_PROCESSING` rejected. |
| O | Slot/index guards | PASS | Zero, negative, seven, huge, and fractional inputs rejected with the expected range/type reasons. |
| P | Stale/replay protection | PASS | Duplicate request mutated once then returned `DUPLICATE_REQUEST`; old request returned `STALE_REQUEST`; old revision returned `STALE_SLOT_REVISION`. |
| Q | Battle 1 -> 2 -> 3 | PASS | The exact latest run order was copied into all three initialized Battle sessions. |
| R | Different physical Battle map | PASS | `region_01_battle -> region_01_boss` retained the exact order with the run owner available. |
| S | Acquisition and multiple acquisition | PASS | New skills filled the first available gaps in sequence without moving existing entries. |
| T | Upgrade after manual reorder | PASS | Warrior `brandish -> brave_slash` and six-skill Mage `cold_beam -> ice_strike` retained the exact slots. |
| U | Skill removal | PASS | Removed SkillId cleared its position; later positions did not compact. |
| V | Mage six / Union start count | PASS | Mage reached and persisted six unique slots; captured run effects initialized exactly 2 skills without bonus and 3 with `StartingSkillBonus=1`. |
| W | Overflow and run reset/restart | PASS | Seventh skill reported explicit overflow while preserving six; new run and immediate restart cleared revision/order and initialized fresh job sets. |
| X | Cleanup, timeout, and mid-drag map transfer | PASS | Success/cancel/reject/10 ms forced timeout/map-transfer paths ended with flags false, indices/request/timers 0, ghost hidden, and 0 highlights. |

#### Detailed stress and close-state evidence

The 50-gesture sequence ended with six unique SkillIds and byte-identical Battle/run order:

`holy_arrow|heal|poison_breath|flame_orb|thunder_bolt|cold_beam`

It produced exactly 25 `[BattleSkillSlotReorder] success` entries, 25 client success feedback entries, and 25 `INVALID_TARGET` cancels. No server rejection, stale receipt, duplicate receipt, Warning, or Error occurred in that sequence. Three additional cross-pair swaps exercised `1<->6`, `2<->5`, and `3<->4`, then restored the same arrangement.

The mid-drag transfer deliberately kept pointer-down active while moving from `region_01_battle` to `region_01_boss`. The late release produced a safe `STALE_SLOT_REVISION` rejection. The client then reported candidate/active/cancelling false, source/target 0, pending request 0, both timers 0, ghost hidden, and zero target highlights. A controlled 10 ms pending timeout independently converged on the same clean state.

#### Test boundaries and non-production setup

- The Union 2/3 count was verified at real run reset/owned-state initialization boundaries using captured effect snapshots. A persistent Union profile round-trip was intentionally abandoned when the asynchronous storage test did not complete; no profile or DataStorage mutation was used for skill-bar persistence.
- Guard probes temporarily changed runtime-only Battle fields and restored them in the same script. The overflow probe temporarily added one snapshot SkillId, asserted the guard, then restored the original snapshot and reconciled it.
- One upgrade-stage attempt first returned `NEXT_STAGE_MAP_UNAVAILABLE` because the controlled entry omitted a route. After supplying the test route, the unchanged production upgrade request completed and the next Battle retained the upgraded slot.
- No raw `.ui` edit, new loadout/equip system, permanent account setting, hotkey change, queue drag, skill-data change, or gameplay rule was introduced.

#### Step 6 final state

- Production script changes required by final regression: **NONE**
- Documentation modified: `Docs/SkillDragSystemAudit.md` only
- Runtime regressions found: **NONE**
- Build/runtime errors after final refresh: **0 / 0**
- Run-scoped order persistence: **PASS**
- Server authority and replay protection: **PASS**
- Queue/execution isolation: **PASS**
- Cleanup and stress hardening: **PASS**
- Merge readiness: **READY**
- Push/merge performed: **NO**
- STEP 6 stop condition: **satisfied**
