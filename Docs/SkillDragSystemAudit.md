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
