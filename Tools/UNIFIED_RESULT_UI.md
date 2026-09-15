# Unified battle result UI

Implementation: dark teal result panel, white text, mint relic selection, actual accepted rewards.
The title has no subtitle; there is no acquired-complete badge.

## Reward policy

- Only continuing boss victories (StageDefinitions.StageType = BOSS) offer up to three randomly selected, distinct, unowned relics from the run's frozen catalog.
- Normal and elite battles show acquired rewards only; they generate no relic candidates.
- Selecting a card is a local preview. Continue/E confirms and grants exactly one on the server.
- Defeat, terminal victory and an exhausted relic catalog show a compact receipt without cards.
- The server validates the player, entry, HUD context, run sequence and offered ID.
- The inventory's reward key prevents another grant on duplicate clicks or transition retries.
- Reward tiles show accepted quantities, including consumable overflow converted to currency.
- More than eight receipt entries can be paged with left/right arrow keys.

## Verification

Mocked Lua tests pass for ownership filtering, 0/1/3 offers, sender/context checks,
duplicate requests, transition retries, selection gating, compact/full positioning,
stale snapshots and receipt pagination. These execute extracted production methods,
but are not a MapleStory Worlds runtime test.

Run with Python and Lupa (Lua 5.4):

```text
python Tools/test-unified-result.py <repository-root>
node Tools/build-unified-result-ui.cjs
node .agents/skills/msw-ui-system/scripts/ui_lint.cjs ui/BattleQueueHUD.ui
git diff --check
```

UI lint: zero errors; warnings include hidden legacy/empty labels overlapping their
replacement areas and desktop buttons smaller than the mobile touch-target guideline.
Existing entities outside ResultPanel are semantically unchanged; ResultBackdrop is new.

## Required Maker check

Maker was not connected during implementation. Refresh project files, then check a
continuing victory, defeat and terminal victory. Confirm actual icons, Korean text,
button/card hit testing, dimmer layering, next-map transfer and relic stat application.
Also check repeated E/click input and a second battle to ensure selection resets.
