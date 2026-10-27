"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const schema = require("../../tools/balance-schema.js");
const {MapBuilder} = require("../../.agents/skills/msw-general/scripts/map/msw_map_builder.cjs");
const {ModelBuilder} = require("../../.agents/skills/msw-general/scripts/model/msw_model_builder.cjs");
const expected = require("./expected-content.json");
const manifest = require("./resources.json");
const dataPath = path.join(root, "RootDesk/MyDesk/03_Data");
const tables = Object.fromEntries(fs.readdirSync(dataPath).filter(n => n.endsWith(".csv")).map(n => [n.slice(0, -4), schema.parseCSV(fs.readFileSync(path.join(dataPath, n), "utf8"))]));
const rows = n => tables[n].rows;
const find = (n, key, value) => rows(n).find(r => r[key] === value);
const orbis = n => rows(n).filter(r => Object.values(r).some(v => /^orbis_|^skill_orbis_/.test(v)));

function authoringBaselineBytes(file) {
  const bytes = fs.readFileSync(path.join(root, file));
  if (!file.endsWith(".csv")) return bytes;
  // Historical Orbis snapshots predate El Nath; its rows and successor columns have separate coverage.
  const table = schema.parseCSV(bytes.toString("utf8"));
  table.headers = table.headers.filter(h => !["DeathSpawnEnemyDefinitionId", "DeathSpawnModelId"].includes(h));
  table.rows = table.rows.filter(r => !Object.values(r).some(v => /^el_nath(?:_|$)/.test(v)));
  table.dirty = true;
  return Buffer.from(schema.serializeCSV(table));
}

function legacyEconomyBytes(file) {
  const bytes=authoringBaselineBytes(file);
  if(!/\/(ShopEntries|RelicDefinitions)\.csv$/.test(file)) return bytes;
  const lines=bytes.toString("utf8").trimEnd().split(/\r?\n/);
  const header=lines[0].split(","), originalColumns=file.endsWith("RelicDefinitions.csv") ? header.indexOf("AcquisitionType") : header.length;
  if(originalColumns<0) return bytes;
  return Buffer.from(lines.filter((l,i)=>i===0||!/^orbis_(star_fragment|moon_fragment|sun_fragment|stone_fragment|papa_crown|eliza_feather),/.test(l)&&!/^1,orbis_(star_fragment|moon_fragment|sun_fragment|stone_fragment),/.test(l)).map(l=>l.split(",").slice(0,originalColumns).join(",")).join("\r\n")+"\r\n");
}

test("16 stages / 44 waves / 19 enemies / 23 skills; references and fixed mixed slots", () => {
  assert.deepEqual(schema.validate(tables), []);
  assert.equal(orbis("StageDefinitions").length, 16);
  assert.equal(orbis("StageEnemyWaves").length, 44);
  assert.equal(orbis("EnemyDefinitions").length, 19);
  assert.equal(orbis("EnemySkillDefinitions").length, 23);
  for (let i = 1; i <= 16; i++) {
    const id = `orbis_stage_${String(i).padStart(2, "0")}`;
    const stage = find("StageDefinitions", "StageId", id);
    const waves = rows("StageEnemyWaves").filter(w => w.WaveTableId === stage.WaveTableId);
    const boss = i === 7 || i === 14;
    assert.equal(stage.StageType, boss ? "BOSS" : "NORMAL");
    assert.equal(waves.length, boss ? 1 : 3);
    assert.equal(Number(stage.CellCount), 7);
    assert.equal(Number(stage.CellSpacing), 1.12);
    assert.equal(Number(stage.UnitY), -0.05);
    const route = find("StageMapRoutes", "StageId", id);
    assert.ok(expected.mapIds.includes(route.MapId));
    assert.equal(route.Enabled, "true");
    for (const [wi, wave] of waves.entries()) {
      const roster = expected.rosters[i - 1][wi];
      assert.equal(Number(wave.WaveIndex), wi + 1);
      assert.equal(wave.SpawnTriggerMode, "CLEAR_ONLY");
      assert.equal(Number(wave.SpawnCount), roster.length);
      assert.equal(Number(wave.MaxConcurrent), i >= 15 ? 3 : 2);
      assert.equal(Number(wave.ClearSpawnDelaySeconds), 0.6);
      const pool = rows("EnemySpawnPools").filter(r => r.PoolId === wave.EnemyPoolId);
      for (let slot = 1; slot <= roster.length; slot++) {
        const eligible = pool.filter(r => Number(r.SpawnIndex) === 0 || Number(r.SpawnIndex) === slot);
        assert.equal(eligible.length, 1);
        assert.equal(eligible[0].EnemyDefinitionId, "orbis_" + roster[slot - 1]);
      }
    }
  }
  assert.ok(rows("NodeDefinitions").filter(r => r.StageId.startsWith("orbis_")).every(r => r.NodeGraphId === "orbis_run"));
  assert.equal(rows("ShopNodeBindings").filter(r => r.NodeGraphId === "orbis_run").length, 2);
});

test("models, motions, effects and sounds resolve to original resources or existing shared resources", () => {
  const known = new Set(Object.values(manifest.resources).flatMap(r => r.payload.elements.map(e => e.ruid)));
  // Shared fallback assets must already be used outside Orbis.
  for (const table of ["EnemySkillDefinitions", "EnemyImpactPresentations"]) for (const row of rows(table).filter(r => !Object.values(r).some(v => /orbis/.test(v)))) {
    for (const [key, value] of Object.entries(row)) if (/Ruid$/.test(key) && value) known.add(value);
  }
  for (const table of ["EnemyDefinitions", "EnemySkillDefinitions", "EnemyImpactPresentations"]) for (const row of orbis(table)) {
    for (const [key, value] of Object.entries(row)) if (/Ruid$/.test(key) && value) assert.ok(known.has(value), `${table}.${key}: ${value}`);
  }
  const children = new Set();
  for (const m of expected.monsters) {
    const row = find("EnemyDefinitions", "EnemyDefinitionId", m.id);
    assert.equal(Number(row.MaxHp), m.hp);
    assert.equal(Number(row.BasicAttackDamage), m.damage);
    assert.equal(Number(find("EnemySkillDefinitions", "SkillId", m.id + "_attack").Range), m.range);
    const b = ModelBuilder.read(path.join(root, "RootDesk/MyDesk/Models/Monsters", m.model + ".model"));
    assert.deepEqual(b.listComponents().sort(), ["MOD.Core.SpriteRendererComponent", "MOD.Core.TransformComponent"]);
    assert.equal(b.getValue("MOD.Core.SpriteRendererComponent", "SpriteRUID"), row.IdleMotionRuid);
    assert.equal(b.getValue("MOD.Core.SpriteRendererComponent", "SortingLayer"), "MapLayer2");
    assert.ok(!children.has(b.getChild("BattleHeadAnchor").Id));
    children.add(b.getChild("BattleHeadAnchor").Id);
    const basic = find("EnemySkillDefinitions", "SkillId", m.id + "_attack");
    const action = m.attackAction || (m.key.startsWith("jr_") ? "jump" : "attack1");
    assert.equal(basic.CasterMotionRuid, manifest.resources[m.key].payload.elements.find(e => e.rel_path === action).ruid);
    for (const field of ["IdleMotionRuid", "MoveMotionRuid", "HitMotionRuid", "DeathMotionRuid"]) assert.ok(row[field]);
    assert.ok(find("EnemyPatternSteps", "PatternId", row.PatternId));
    const steps = rows("EnemyPatternSteps").filter(r => r.PatternId === row.PatternId);
    if (m.stationary) {
      assert.equal(row.TraitIds, "HOLD_POSITION");
      assert.ok(!steps.some(r => r.ActionType.startsWith("MOVE")));
    }
  }
  for (const r of orbis("EnemySpawnPools")) {
    const m = expected.monsters.find(m => m.id === r.EnemyDefinitionId);
    assert.ok(m);
    assert.equal(r.EnemyModelId, m.model.toLowerCase());
  }
  for (const r of orbis("EnemyPatternSteps").filter(r => r.TileId)) assert.ok(find("EnemySkillDefinitions", "SkillId", r.TileId));
  for (const r of orbis("EnemySkillDefinitions")) assert.ok(find("SkillEffectSteps", "EffectSetId", r.EffectSetId));
});

test("boss phases, damage increase, front/both-side offsets and summon cap are authored", () => {
  for (const key of ["papa_pixie", "eliza"]) {
    const phases = rows("BossPhaseDefinitions").filter(r => r.EnemyDefinitionId === "orbis_" + key);
    assert.deepEqual(phases.map(r => Number(r.HpRatioLE)), [1, 0.5]);
    const skills = ["area", "area_enraged"].map(suffix => find("EnemySkillDefinitions", "SkillId", `orbis_${key}_${suffix}`));
    assert.deepEqual(skills.map(s => s.TargetOffsets), key === "papa_pixie" ? ["-1|1", "-1|1"] : ["1|2", "1|2|3"]);
    const damages = skills.map(s => Number(find("SkillEffectSteps", "EffectSetId", s.EffectSetId).Value));
    assert.ok(damages[1] > damages[0]);
    for (const phase of phases) {
      const p = rows("EnemyPatternSteps").filter(r => r.PatternId === phase.PatternId);
      assert.ok(p.some(r => r.ActionType === "TELEGRAPH_TILE" && Number(r.TelegraphTurns) === 1));
    }
    if (key === "papa_pixie") {
      assert.equal(Number(phases[1].ReinforcementIntervalTurns), 4);
      assert.equal(Number(phases[1].ReinforcementMaxAlive), 1);
    }
  }
  const grupin = find("EnemySkillDefinitions", "SkillId", "orbis_grupin_attack");
  assert.ok(rows("SkillEffectSteps").some(r => r.EffectSetId === grupin.EffectSetId && r.EffectType === "PUSH" && Number(r.Value) === 1));
});

test("five independent MapleTile maps preserve ground chains, spawn above ground, and 7-cell common layout", () => {
  const ids = new Set();
  const sector = JSON.parse(fs.readFileSync(path.join(root, "Global/SectorConfig.config"), "utf8"));
  const source = MapBuilder.read(path.join(root, "map/henesys_battle.map"));
  const ground = source.getFootholds().filter(f => f.groupID === 2).map(({OwnerId, ...f}) => f);
  for (const id of expected.mapIds) {
    const b = MapBuilder.read(path.join(root, "map", id + ".map"));
    assert.equal(b.getTileMapMode(), 0);
    assert.ok(sector.ContentProto.Json.Sectors.some(s => s.entries.includes("map://" + id)));
    const session = b.component(id, "script.BattleSessionComponent");
    assert.equal(session.CellCount, 7); assert.equal(session.CellSpacing, 1.12);
    assert.equal(session.AutoStartPrototypeBattle, false);
    const all = b.listEntities();
    for (const e of all) {assert.ok(!ids.has(e.id)); ids.add(e.id); assert.ok(!e.name.startsWith("TEMP_"));}
    const own = new Set(all.map(e => e.id));
    const footholds = b.getFootholds();
    assert.deepEqual(footholds.map(({OwnerId, ...f}) => f), ground);
    for (const f of footholds) assert.ok(own.has(f.OwnerId));
    const footholdIds = new Set(footholds.map(f => f.Id));
    for (const f of footholds) for (const link of [f.NextFootholdId, f.PreviousFootholdId]) assert.ok(link === 0 || footholdIds.has(link));
    for (let cell = 0; cell < 7; cell++) {
      const x = session.CellStartX + cell * session.CellSpacing;
      assert.ok(footholds.some(f => f.StartPoint.x <= x && f.EndPoint.x >= x && Math.abs(f.StartPoint.y - session.UnitY) < 1e-6 && Math.abs(f.EndPoint.y - session.UnitY) < 1e-6));
      assert.ok(b.find("BattlePlatforms/BattleCell" + (cell + 1)));
    }
    assert.ok(b.component("SpawnLocation", "MOD.Core.TransformComponent").Position.y > session.UnitY);
    assert.equal(b.component("TileMap", "MOD.Core.TileMapComponent").Color.a, 0);
    const background = b.component("Background", "MOD.Core.BackgroundComponent");
    assert.equal(background.Type, id === "orbis_tower_battle" ? 1 : 4);
    if (id === "orbis_tower_battle") {
      assert.equal(background.TemplateRUID, "1089d1a3ea414480b5ca8a09d5f6e93f");
      for (const name of ["BattleBoardState", "BattleTurnState", "BattleWaveState", "BattleCameraAnchor"]) assert.ok(b.find(name));
      assert.equal(all.filter(e => e.name === "SpawnLocation").length, 1);
      assert.equal(new Set(all.map(e => e.path)).size, all.length);
      assert.ok(!all.some(e => /CustomFootholdComponent|ClimbableComponent|PortalComponent|AIWanderComponent|NameTagComponent/.test(e.componentNames)));
    }
  }
});

test("tower waves use the approved 7/8 totals and elemental attacks reuse hostile status semantics", () => {
  for (const [stage, counts] of [[15, [2, 2, 3]], [16, [2, 3, 3]]]) {
    const waves = rows("StageEnemyWaves").filter(w => w.WaveTableId === `orbis_stage_${stage}_waves`);
    assert.deepEqual(waves.map(w => Number(w.SpawnCount)), counts);
    assert.ok(waves.every(w => Number(w.MaxConcurrent) === 3));
    assert.equal(find("StageMapRoutes", "StageId", `orbis_stage_${stage}`).MapId, "orbis_tower_battle");
  }
  for (const [key, status, value, turns] of [["fire_stoneball", "IGNITE", 1, 2], ["ice_stoneball", "FROSTBITE", 0, 1]]) {
    const skill = find("EnemySkillDefinitions", "SkillId", `orbis_${key}_attack`);
    const effects = rows("SkillEffectSteps").filter(s => s.EffectSetId === skill.EffectSetId);
    assert.equal(skill.TargetingType, "FIRST_ENEMY_FORWARD");
    assert.equal(Number(skill.Range), 2); assert.equal(Number(skill.EnemyQueueTurns), 1); assert.equal(Number(skill.CooldownTurns), 0);
    assert.deepEqual(effects.map(s => s.EffectType), ["DAMAGE", status]);
    assert.equal(effects[0].ParameterA, "SOURCE_BASIC_ATTACK");
    assert.equal(effects[1].TargetSelector, "PRIMARY_TARGET");
    assert.equal(Number(effects[1].Value), value); assert.equal(Number(effects[1].ParameterA), turns);
  }
});

test("incremental tower authoring preserves old CSVs/arenas and models except Maker CoreVersion normalization", () => {
  const crypto = require("node:crypto");
  const baseline = require("./tower-authoring-baseline.json");
  for (const [relative, before] of Object.entries(baseline.files)) {
    const after = authoringBaselineBytes(relative);
    let preserved = relative.endsWith(".csv") ? after.subarray(0, before.bytes) : after;
    if (relative.endsWith(".model")) {
      // Maker upgrades the old template wrapper to the approved project core; values/children must be identical.
      const model = ModelBuilder.read(path.join(root, relative)).build();
      assert.equal(model.CoreVersion, "26.10.0.0");
      model.CoreVersion = "26.7.0.0";
      const m = baseline.expected.monsters.find(m => relative.endsWith("/" + m.model + ".model"));
      const anchor = model.ContentProto.Json.Children.find(c => c.Name === "BattleHeadAnchor");
      const position = anchor.Model.Values.find(v => v.Name === "Position").Value;
      const authoredY = manifest.resources[m.key].payload.elements.find(e => e.rel_path === "stand").payload.height / 100 + 0.18;
      assert.ok(Math.abs(position.y - authoredY) < 1e-6, relative + " head anchor");
      position.y = authoredY; // Maker also normalizes insignificant decimal tails.
      preserved = Buffer.from(JSON.stringify(model, null, 2) + "\n");
    }
    assert.equal(crypto.createHash("sha256").update(preserved).digest("hex"), before.sha256, relative);
  }
  assert.deepEqual(expected.monsters.slice(0, 15), baseline.expected.monsters);
  assert.deepEqual(expected.rosters.slice(0, 14), baseline.expected.rosters);
});

test("Balance Studio parses and previews each fixed slot without diluting exact mixed probabilities", () => {
  const html = fs.readFileSync(path.join(root, "tools/balance-studio.html"), "utf8");
  for (const m of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) if (!m[0].startsWith('<script type="application/json"')) new vm.Script(m[1]);
  const source = html.slice(html.indexOf("  function poolCandidates("), html.indexOf("  // RegionDefinitions still"));
  const rowsFor = n => rows(n).map((r, rowIndex) => ({rowIndex, get: k => r[k] ?? ""}));
  const context = vm.createContext({tableRowsOf: rowsFor});
  vm.runInContext(source + ";globalThis.candidates=poolCandidates;", context);
  for (const wave of orbis("StageEnemyWaves")) for (let slot = 1; slot <= Number(wave.SpawnCount); slot++) {
    const choices = context.candidates(wave.EnemyPoolId, Number(wave.WaveIndex), slot);
    assert.equal(choices.length, 1);
  }
});

test("Balance Studio mirrors fixed-slot uniqueness and accepts legacy blank slots", () => {
  const html = fs.readFileSync(path.join(root, "tools/balance-studio.html"), "utf8");
  const functionSource = name => {const start = html.indexOf("  function " + name + "("); return html.slice(start, html.indexOf("\n  function ", start + 10));};
  const keys = html.slice(html.indexOf("  const EXPLICIT_KEYS ="), html.indexOf("  function detectKeyColumns("));
  const catalog = JSON.parse(html.match(/<script[^>]*id="vocabCatalog"[^>]*>([\s\S]*?)<\/script>/)[1]);
  const schemaTables = html.match(/  const SKILL_SCHEMA_TABLES = new Set\(\[[\s\S]*?\]\);/)[0];
  const jobTables = html.match(/  const JOB_SKILL_TABLES = new Set\([^;]*;/)[0];
  const context = vm.createContext({state:{tables:new Map()},VOCAB:catalog});
  vm.runInContext(schemaTables + jobTables + keys + functionSource("validateVocabRow") + functionSource("detectKeyColumns") + functionSource("validateTable") + ";globalThis.check={detectKeyColumns,validateTable};", context);
  const header = tables.EnemySpawnPools.headers;
  const validate = records => context.check.validateTable({fileName:"EnemySpawnPools.csv",header,rows:records.map(r=>header.map(k=>r[k]??"")),keys:context.check.detectKeyColumns("EnemySpawnPools",header),columns:[]});
  const fixed = rows("EnemySpawnPools").filter(r=>r.PoolId==="orbis_stage_15_wave_3");
  assert.equal(validate(fixed).length,0);
  assert.ok(validate([...fixed,{...fixed[1],SpawnIndex:"02"}]).some(e=>e.level==="error"));
  const legacy = rows("EnemySpawnPools").find(r=>r.SpawnIndex==="");
  assert.equal(validate([legacy]).length,0);
  assert.ok(validate([legacy,{...legacy,SpawnIndex:"0"}]).some(e=>e.level==="error"));
});


test("Orbis route places only two shops after reward selection and preserves the production graph and legacy economy", () => {
  const crypto = require("node:crypto");
  const baseline = require("./shop-authoring-baseline.json").files;
  for (const [file, before] of Object.entries(baseline)) {
    if (file.endsWith(".mlua")) continue;
    const current = legacyEconomyBytes(file);
    const appendOnly = /NodeDefinitions|ShopNodeBindings|StageRewardDefinitions/.test(file);
    const original = appendOnly ? current.subarray(0, before.bytes) : current;
    assert.equal(crypto.createHash("sha256").update(original).digest("hex"), before.sha256, file);
  }
  const nodes = rows("NodeDefinitions").filter(r => r.NodeGraphId === "orbis_run");
  const byId = new Map(nodes.map(r => [r.NodeId, r]));
  assert.equal(nodes.length, 33);
  assert.equal(nodes.filter(r => r.IsStartNode === "true").length, 1);
  const visited = [];
  let node = nodes.find(r => r.IsStartNode === "true");
  while (node) {
    assert.ok(!visited.includes(node.NodeId), "route cycle");
    visited.push(node.NodeId);
    assert.ok(!node.NextNodeIds.includes("|"));
    node = node.NextNodeIds ? byId.get(node.NextNodeIds) : null;
  }
  assert.equal(visited.length, 33);
  assert.deepEqual(visited.map(id => byId.get(id).StageId).filter(Boolean), Array.from({length:16}, (_, i) => `orbis_stage_${String(i + 1).padStart(2, "0")}`));
  assert.deepEqual(nodes.filter(r => r.NodeType === "SHOP").map(r => r.NodeId), ["orbis_shop_after_stage03", "orbis_shop_after_stage10"]);
  for (const n of [3, 10]) {
    const key = String(n).padStart(2, "0"), next = String(n + 1).padStart(2, "0");
    const battle = byId.get(`orbis_stage${key}_battle`);
    const reward = byId.get(battle.NextNodeIds);
    const shop = byId.get(reward.NextNodeIds);
    assert.equal(reward.NodeType, "REST");
    assert.equal(shop.NodeType, "SHOP");
    assert.equal(byId.get(shop.NextNodeIds).StageId, `orbis_stage_${next}`);
    assert.equal(rows("ShopNodeBindings").find(r => r.NodeGraphId === "orbis_run" && r.NodeId === shop.NodeId).ShopId, "shop_relic");
  }
});


test("Orbis opening gold is Henesys base rewards plus 20 support, with complete early-region stage rewards", () => {
  const crypto = require("node:crypto");
  const baseline = require("./gold-authoring-baseline.json").files;
  for (const [file, before] of Object.entries(baseline)) {
    const current = legacyEconomyBytes(file);
    const original = file.endsWith("StageRewardDefinitions.csv") ? current.subarray(0, before.bytes) : current;
    assert.equal(crypto.createHash("sha256").update(original).digest("hex"), before.sha256, file);
  }
  const entries = rows("StageRewardDefinitions").filter(r => r.StageId.startsWith("orbis_"));
  assert.equal(entries.length, 17);
  const amounts = [5,6,8,7,8,10,15,8,9,10,9,10,12,18,12,14];
  for (let i = 1; i <= 16; i++) {
    const stage = `orbis_stage_${String(i).padStart(2,"0")}`;
    const clear = entries.find(r => r.StageRewardEntryId === `${stage}_clear_gold`);
    assert.equal(Number(clear.Amount), amounts[i-1]);
    assert.equal(clear.RewardType, "CURRENCY");
    assert.equal(clear.RewardRefId, "gold");
    assert.equal(clear.Enabled, "true");
    if (i <= 3) assert.equal(clear.Amount, rows("StageRewardDefinitions").find(r => r.StageId === `henesys_stage_${String(i).padStart(2,"0")}`).Amount);
  }
  const support = entries.find(r => r.StageRewardEntryId === "orbis_opening_support_gold");
  assert.equal(support.StageId,"orbis_stage_01");
  assert.equal(Number(support.Amount),20);
  const budget = entries.filter(r => ["orbis_stage_01","orbis_stage_02","orbis_stage_03"].includes(r.StageId)).reduce((n,r)=>n+Number(r.Amount),0);
  assert.equal(budget,39);
  const minPrice = Math.min(...rows("ShopEntries").filter(r=>r.ShopId==="shop_relic"&&r.Enabled==="true"&&r.PriceCurrencyId==="gold").map(r=>Number(r.PriceAmount)));
  assert.equal(minPrice,35);
  assert.ok(budget >= minPrice && budget <= 40);
  assert.equal(entries.reduce((n,r)=>n+Number(r.Amount),0),181);
});


test("Orbis souvenirs keep six zero-stat all-job definitions and four original-icon shop entries",()=>{
  const ids=["star_fragment","moon_fragment","sun_fragment","stone_fragment","papa_crown","eliza_feather"];
  const effects=["QUEUE_FINISHER_BONUS","TURN_HIT_COOLDOWN","MULTI_TARGET_HEAL","STATIONARY_GUARD","WAVE_TRANSITION_HEAL","FIRST_DEBUFF_WINDOW"];
  const prices=[35,40,50,45];
  for(const [index,key] of ids.entries()) {
    const id="orbis_"+key,d=find("RelicDefinitions","RelicId",id);
    assert.ok(d);assert.equal(d.IsOpen,"true");assert.equal(d.RequiredJobId,"");
    for(const f of ["AttackBonus","DefenseBonus","MaxHpBonus"])assert.equal(Number(d[f]),0,id);
    assert.equal(d.SpecialEffectType,effects[index]);assert.equal(Number(d.SpecialEffectValue),1);
    assert.equal(d.AcquisitionType,index<4?"REGION_SHOP":"BOSS_CLEAR");
    assert.equal(d.AcquisitionSourceId,index<4?"orbis":index===4?"orbis_stage_07":"orbis_stage_14");
    const entries=rows("ShopEntries").filter(e=>e.RewardRefId===id);
    assert.equal(entries.length,index<4?1:0);
    if(index<4){assert.equal(Number(entries[0].PriceAmount),prices[index]);assert.equal(entries[0].IconImageRUID,d.IconImageRUID);assert.match(d.IconImageRUID,/^[0-9a-f]{32}$/);}
    else assert.match(d.IconImageRUID,/^thumbnail:\/\/[0-9a-f]{32}$/);
  }
  const legacy=rows("RelicDefinitions").filter(d=>!ids.some(k=>d.RelicId==="orbis_"+k));
  assert.equal(legacy.length,50);assert.ok(legacy.every(d=>d.AcquisitionType==="GENERAL"&&d.AcquisitionSourceId===""));
});

test("relic content hooks use shared damage, action and wave owners without expanding the session",()=>{
  const source=(p)=>fs.readFileSync(path.join(root,"RootDesk/MyDesk",p),"utf8");
  const damage=source("01_Combat/Resolvers/BattleDamageLogic.mlua");
  assert.ok(damage.indexOf("ContentRelicTriggerLogic:DirectHit")<damage.indexOf('session:HandleUnitDiedFromSource(targetUnitId'));
  assert.ok(damage.includes("ContentRelicTriggerLogic:FinisherBonus"));
  const owner=source("04_Roguelike/RunManager/PlayerRunRelicEffectComponent.mlua");
  assert.ok(owner.indexOf("ConsumeGuardUse() then return 0")<owner.indexOf("ContentRelicTriggerLogic:IncomingDirectDamage"));
  assert.ok(owner.indexOf("ContentRelicTriggerLogic:IncomingDirectDamage")<owner.indexOf("if amount >= currentHp"));
  assert.ok(owner.includes("self.ContentRelicBattleKey ~= key"));
  const html=fs.readFileSync(path.join(root,"tools/balance-studio.html"),"utf8");
  const vocab=JSON.parse(html.match(/<script[^>]*id="vocabCatalog"[^>]*>([\s\S]*?)<\/script>/)[1]);
  assert.deepEqual(Object.keys(vocab.relic.acquisitionTypes),["GENERAL","REGION_SHOP","BOSS_CLEAR"]);
});


test("Balance Studio combines fixed spawn slots with defeat-successor drops", () => {
  const html = fs.readFileSync(path.join(root, "tools/balance-studio.html"), "utf8");
  const functionSource = name => { const start = html.indexOf("  function " + name + "("); return html.slice(start, html.indexOf("\n  function ", start + 10)); };
  const parent = find("EnemyDefinitions", "EnemyDefinitionId", "el_nath_yeti_pepe");
  const child = parent.DeathSpawnEnemyDefinitionId;
  const pools = [
    { PoolId: "verify", EnemyDefinitionId: parent.EnemyDefinitionId, EnemyModelId: "parent", Weight: "1", SpawnIndex: "1" },
    { PoolId: "verify", EnemyDefinitionId: "orbis_star_pixie", EnemyModelId: "orbisstarpixie", Weight: "1", SpawnIndex: "2" },
    { PoolId: "registration", EnemyDefinitionId: child, EnemyModelId: parent.DeathSpawnModelId, Weight: "1" }
  ];
  const wrap = records => records.map(r => ({ get: key => r[key] ?? "" }));
  const context = vm.createContext({
    GOLD_ID: "gold",
    tableRowsOf: name => wrap(name === "EnemyDefinitions" ? rows(name) : name === "EnemySpawnPools" ? pools : []),
    stageWaves: () => wrap([{ SpawnCount: "2", EnemyPoolId: "verify", WaveIndex: "1" }])
  });
  vm.runInContext(functionSource("poolCandidates") + functionSource("deathSpawnCheck") + functionSource("stageEconomy") + ";globalThis.estimate=stageEconomy;", context);
  const drops = new Map([
    [parent.EnemyDefinitionId, { gold: 10, items: new Map([["token", 1]]) }],
    [child, { gold: 3, items: new Map([["token", 2]]) }],
    ["orbis_star_pixie", { gold: 2, items: new Map() }]
  ]);
  const result = context.estimate("verify", new Map([["verify", { waveTableId: "verify" }]]), drops, {});
  assert.equal(result.enemies, 2);
  assert.equal(result.dropGold, 15);
  assert.equal(result.items.get("token"), 3);
});
