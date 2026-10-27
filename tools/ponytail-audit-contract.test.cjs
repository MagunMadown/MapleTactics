"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const childProcess = require("node:child_process");

const root = path.resolve(__dirname, "..");
const read = relative => fs.readFileSync(path.join(root, relative), "utf8");
const teleport = read("RootDesk/MyDesk/02_UI/MapTeleportManager.mlua");
const settings = read("RootDesk/MyDesk/00_Core/GameSettingsLogic.mlua");
const session = read("RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua");
const presenter = read("RootDesk/MyDesk/02_UI/BattleHudPresenterLogic.mlua");
const tooltip = read("RootDesk/MyDesk/02_UI/MouseTooltipUIComponent.mlua");
const keyGuide = read("RootDesk/MyDesk/02_UI/KeyGuideHudComponent.mlua");

function method(source, name) {
  const found = source.match(new RegExp("\\tmethod [^\\n]* " + name + "\\([^\\n]*\\)([\\s\\S]*?)\\n\\tend"));
  assert.ok(found, "method missing: " + name);
  return found[0];
}

test("client map transfer cannot choose an arrival coordinate", () => {
  const request = method(teleport, "RequestTeleport");
  assert.match(request, /method void RequestTeleport\(string destinationMapName, Vector3 ignoredClientPosition, string source\)/);
  assert.match(request, /ResolveAuthorizedRunTarget\(playerEntity\)/);
  assert.equal((request.match(/ignoredClientPosition/g) || []).length, 1);
});

test("settings saves flush on close and serialize writes per user", () => {
  assert.match(settings, /method void FlushPendingSave\(string reason\)/);
  const save = method(settings, "SaveSettings");
  const drain = method(settings, "DrainSaveQueue");
  assert.match(save, /queue\.PendingRaw = raw/);
  assert.match(drain, /if queue == nil or queue\.InFlight or queue\.PendingRaw == nil then return end/);
  assert.match(drain, /queue\.InFlight = true/);
  assert.match(drain, /if queue\.PendingRaw ~= nil then\s+self:DrainSaveQueue\(userKey\)/);
  assert.match(drain, /else\s+queues\[userKey\] = nil/);
});

test("battle session publishes tooltip data without resolving a UI entity", () => {
  assert.doesNotMatch(session, /MouseTooltipGroup/);
  assert.match(session, /PublishTooltipRequest/);
  assert.match(presenter, /BattleTooltipRequestedEvent\(\)/);
  assert.match(tooltip, /ConnectEvent\(BattleTooltipRequestedEvent/);
});

test("key guide relies on its PC-only UI authoring instead of deprecated platform queries", () => {
  assert.doesNotMatch(keyGuide, /IsPCPlatform/);
  assert.doesNotMatch(keyGuide, /IsMobilePlatform/);
  assert.match(keyGuide, /UITransform\.ActivePlatform=PC/);
});

test("literal UI paths resolve through UIBuilder", () => {
  childProcess.execFileSync(process.execPath, [path.join(__dirname, "check-ui-path-contract.cjs")], { stdio: "pipe" });
});
