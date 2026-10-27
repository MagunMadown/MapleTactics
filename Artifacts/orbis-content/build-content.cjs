"use strict";
// Authoring only: uses the existing data formats and MSW builders. Does not create run edges.
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const skills = path.join(root, ".agents/skills/msw-general");
process.env.MSW_MODEL_BUILDER_MOD_CORE_VERSION = "26.10.0.0";
const {ModelBuilder, vector3} = require(path.join(skills, "scripts/model/msw_model_builder.cjs"));
const {MapBuilder} = require(path.join(skills, "scripts/map/msw_map_builder.cjs"));
const schema = require("../../tools/balance-schema.js");
const resources = JSON.parse(fs.readFileSync(path.join(__dirname, "resources.json"), "utf8"));
const data = path.join(root, "RootDesk/MyDesk/03_Data");
const additions = {};
function add(table, row) { (additions[table] ||= []).push(row); }
function asset(key, rel, fallback = "") {
  return resources.resources[key].payload.elements.find(e => e.rel_path === rel)?.ruid || fallback;
}
const monsters = [
  ["star_pixie", "스타픽시", 4, 1, 2, 1.25], ["lunar_pixie", "루나픽시", 5, 1, 2, 1.25],
  ["luster_pixie", "러스터픽시", 6, 2, 3, 1.25], ["nependeath", "네펜데스", 6, 2, 2, 1.25],
  ["dark_nependeath", "다크 네펜데스", 7, 2, 3, 1.25],
  ["jr_cellion", "주니어 샐리온", 6, 2, 1, 1.4], ["jr_lioner", "주니어 라이오너", 6, 2, 1, 1.4],
  ["jr_grupin", "주니어 그류핀", 6, 2, 1, 1.4], ["cellion", "샐리온", 8, 2, 1, 1.1],
  ["lioner", "라이오너", 8, 2, 2, 1.1], ["grupin", "그류핀", 9, 3, 1, 1.1],
  ["jr_lucida", "주니어 루이넬", 8, 2, 1, 1.4], ["lucida", "루이넬", 10, 3, 2, 1.1],
  ["papa_pixie", "파파픽시", 32, 3, 3, 0.75], ["eliza", "엘리쟈", 48, 4, 1, 0.85]
].map(([key, name, hp, damage, range, scale]) => ({key, name, hp, damage, range, scale,
  id: "orbis_" + key, model: "Orbis" + key.split("_").map(s => s[0].toUpperCase() + s.slice(1)).join(""),
  boss: key === "papa_pixie" || key === "eliza", stationary: key.includes("nependeath")}));
const byKey = Object.fromEntries(monsters.map(m => [m.key, m]));
const stageNames = ["별빛 정원 입구", "달빛 정원", "네펜데스 화원", "햇빛 정원", "어두운 화원", "구름 정원 수호진", "파파픽시",
  "어린 수호수의 뜰", "세 갈래 정원", "성체 수호수", "수호수의 영역", "검은 날개", "하늘 계단 수호진", "엘리쟈"];
const rosters = [
  [["star_pixie"], ["star_pixie"], ["star_pixie", "star_pixie"]],
  [["lunar_pixie"], ["lunar_pixie"], ["star_pixie", "lunar_pixie"]],
  [["nependeath"], ["star_pixie", "nependeath"], ["lunar_pixie", "nependeath"]],
  [["luster_pixie"], ["lunar_pixie", "luster_pixie"], ["luster_pixie", "luster_pixie"]],
  [["dark_nependeath"], ["nependeath", "dark_nependeath"], ["dark_nependeath", "dark_nependeath"]],
  [["star_pixie", "dark_nependeath"], ["lunar_pixie", "nependeath"], ["luster_pixie", "dark_nependeath"]],
  [["papa_pixie"]],
  [["jr_cellion"], ["jr_lioner"], ["jr_grupin", "jr_grupin"]],
  [["jr_cellion", "jr_lioner"], ["jr_lioner", "jr_grupin"], ["jr_cellion", "jr_grupin"]],
  [["cellion"], ["lioner"], ["grupin", "grupin"]],
  [["cellion", "jr_cellion"], ["lioner", "jr_lioner"], ["grupin", "jr_grupin"]],
  [["jr_lucida"], ["jr_lucida", "lucida"], ["lucida", "lucida"]],
  [["cellion", "lioner"], ["grupin", "jr_lucida"], ["lucida", "grupin"]],
  [["eliza"]]
];
const mapIds = ["orbis_garden_battle", "orbis_guardian_battle", "orbis_papa_pixie_boss", "orbis_eliza_boss"];
const baseMapPath = path.join(root, "map/henesys_battle.map");
if (MapBuilder.read(baseMapPath).getTileMapMode() !== 0) throw Error("Expected MapleTile source");
const template = path.join(skills, "models/TransformOnly.model");
const fallbackHit = "eed46092f65940a7a8e77a1bd8e2aa75";
const fallbackImpact = schema.parseCSV(fs.readFileSync(path.join(data, "EnemyImpactPresentations.csv"), "utf8")).rows.find(r => r.EntryId === "default").ImpactSoundRuid;
function model(name, ruid, scale = 1, category = "Monsters") {
  const out = path.join(root, "RootDesk/MyDesk/Models", category, name + ".model");
  const b = fs.existsSync(out) ? ModelBuilder.read(out) : ModelBuilder.fromTemplate(template, name);
  b.component("MOD.Core.SpriteRendererComponent")
    .value("MOD.Core.SpriteRendererComponent", "SpriteRUID", ruid, "string")
    .value("MOD.Core.SpriteRendererComponent", "SortingLayer", category === "Monsters" ? "MapLayer2" : "MapLayer0", "string")
    .value("MOD.Core.SpriteRendererComponent", "OrderInLayer", category === "Monsters" ? 3 : 0, "int")
    .value("MOD.Core.TransformComponent", "Scale", vector3(scale, scale, 1), "vector3");
  fs.mkdirSync(path.dirname(out), {recursive: true});
  return {b, out};
}
function pattern(id, steps) {
  steps.forEach((s, i) => add("EnemyPatternSteps", {SchemaVersion: 1, PatternId: id, StepIndex: i + 1,
    ActionType: s[0], ConditionType: s[1] || "ALWAYS", TileId: s[2] || "", TelegraphTurns: s[3] || 0,
    ParamA: s[4] || "", NextStepOnSuccess: s[5] || 1, NextStepOnFailure: s[6] || 1, Enabled: "true"}));
}
function effect(id, damage, sourceBasic, push = false) {
  add("SkillEffectSteps", {SchemaVersion: 1, EffectSetId: id, StepIndex: 1, EffectType: "DAMAGE", TargetSelector: "ALL_SKILL_TARGETS",
    Value: damage, ParameterA: sourceBasic ? "SOURCE_BASIC_ATTACK" : ""});
  if (push) add("SkillEffectSteps", {SchemaVersion: 1, EffectSetId: id, StepIndex: 2, EffectType: "PUSH", TargetSelector: "PRIMARY_TARGET", Value: 1});
}
function skill(m, suffix, label, options = {}) {
  const id = m.id + "_" + suffix;
  const attack = options.motion || (m.key.startsWith("jr_") ? "jump" : "attack1");
  const duration = m.boss ? 0.8 : 0.55;
  const motionFrames = resources.resources[m.key].payload.elements.find(e => e.rel_path === attack)?.payload.frames?.length || 1;
  const rate = Math.max(1, Math.ceil(motionFrames / (duration * 10) * 10) / 10);
  const hit = asset(m.key, "attack1/info/hit", fallbackHit);
  const projectile = options.area ? "" : asset(m.key, "attack1/info/ball");
  add("EnemySkillDefinitions", {SchemaVersion: 1, SkillId: id, DisplayName: m.name + " " + label,
    SkillTags: "attack|enemy|caster_motion" + (m.boss ? "|boss" : "") + (options.area ? "|area|telegraph" : m.range > 1 ? "|ranged" : "|melee"),
    TargetingType: options.area ? "RANGE_OFFSETS" : "FIRST_ENEMY_FORWARD", Range: options.range || m.range,
    TargetOffsets: options.offsets || "", CooldownTurns: 0, CostValue: 0, MotionProfileId: options.area ? "heavy_slash" : "basic_slash",
    EffectSetId: options.effect || "orbis_basic_attack_effects", ActionDuration: duration + 0.15, FreePlay: "false",
    CastEffectRuid: options.area ? "" : asset(m.key, "attack1/info/effect"), HitEffectRuid: hit, EffectScale: 0.75,
    ProjectileRuid: projectile, ProjectileSpeed: projectile ? 8 : 0, ProjectileScale: 0.8, ProjectileLaunchDelay: projectile ? 0.2 : 0,
    SkillTier: 1, CasterMotionRuid: asset(m.key, attack), CasterMotionPlayRate: rate, CasterMotionDuration: duration, EnemyQueueTurns: 1,
    HudIconRuid: asset(m.key, "stand"), ProjectileCount: 1, ProjectileInterval: 0, ProjectileHeight: 0,
    CastSoundRuid: asset(m.key, "_audio/" + attack[0].toUpperCase() + attack.slice(1)),
    HitSoundRuid: asset(m.key, "_audio/CharDam1", fallbackImpact)});
  add("EnemyImpactPresentations", {SchemaVersion: 1, EntryId: "skill_" + id, EnemyDefinitionId: "*", SkillId: id,
    Priority: 200, ImpactSoundRuid: asset(m.key, "_audio/CharDam1", fallbackImpact)});
  return id;
}
effect("orbis_basic_attack_effects", 1, true);
effect("orbis_grupin_attack_effects", 3, true, true);
effect("orbis_papa_burst_effects", 4, false);
effect("orbis_papa_burst_enraged_effects", 5, false);
effect("orbis_eliza_sweep_effects", 5, false);
effect("orbis_eliza_sweep_enraged_effects", 6, false);
const capabilities = [];
for (const m of monsters) {
  const {b, out} = model(m.model, asset(m.key, "stand"), m.scale);
  b.value("MOD.Core.SpriteRendererComponent", "FlipX", true, "bool");
  if (!b.hasChild("BattleHeadAnchor")) b.child("BattleHeadAnchor", ["MOD.Core.TransformComponent"]);
  const idleHeight = resources.resources[m.key].payload.elements.find(e => e.rel_path === "stand").payload.height / 100;
  b.childValue("BattleHeadAnchor", "MOD.Core.TransformComponent", "Position", vector3(0, idleHeight + 0.18, 0), "vector3").write(out);
  const basic = skill(m, "attack", m.range > 1 ? "원거리 공격" : "근접 공격", {effect: m.key === "grupin" ? "orbis_grupin_attack_effects" : undefined});
  const basicRow = additions.EnemySkillDefinitions.find(r => r.SkillId === basic);
  add("EnemyDefinitions", {EnemyDefinitionId: m.id, DisplayName: m.name, MaxHp: m.hp, BasicAttackDamage: m.damage,
    PatternId: m.id + (m.boss ? "_phase_01" : "_pattern"), MovementPolicy: "TRACK_PLAYER", InitialFacingPolicy: "FACE_PLAYER",
    TraitIds: m.stationary ? "HOLD_POSITION" : "", IsBoss: String(m.boss), IdleMotionRuid: asset(m.key, "stand"), IdleMotionPlayRate: 1,
    MoveMotionRuid: asset(m.key, m.stationary ? "stand" : "move"), MoveMotionPlayRate: 1.5,
    HitMotionRuid: asset(m.key, "hit1"), HitMotionPlayRate: 1, HitMotionDuration: 0.25,
    AttackMotionRuid: m.boss ? "" : basicRow.CasterMotionRuid, AttackMotionPlayRate: basicRow.CasterMotionPlayRate, AttackMotionDuration: basicRow.CasterMotionDuration,
    DeathMotionRuid: asset(m.key, "die1"), DeathMotionPlayRate: 1, DeathMotionDuration: m.boss ? 1.2 : 0.65,
    VisualOffsetY: 0, FlatDamageReduction: 0, AscensionHpBonus: 1});
  add("EnemyImpactPresentations", {SchemaVersion: 1, EntryId: m.id, EnemyDefinitionId: m.id, SkillId: "*", Priority: 300,
    DamageSoundRuid: asset(m.key, "_audio/Damage"), DeathSoundRuid: asset(m.key, "_audio/Die")});
  if (!m.boss) {
    pattern(m.id + "_pattern", m.stationary ? [
      ["EXECUTE_TILE", "ALWAYS", basic, 0, "", 1, 2], ["TURN_TO_PLAYER", "ALWAYS", "", 0, "", 1, 3], ["WAIT"]
    ] : [
      ["EXECUTE_TILE", "ALWAYS", basic, 0, "", 1, 2], ["TURN_TO_PLAYER", "ALWAYS", "", 0, "", 1, 3],
      ["MOVE_TOWARD", "CELL_FREE", "", 0, "TOWARD_PLAYER", 1, 4], ["WAIT"]
    ]);
  } else {
    for (let phase = 1; phase <= 2; phase++) {
      const papa = m.key === "papa_pixie";
      const special = skill(m, phase === 1 ? "area" : "area_enraged", phase === 1 ? "광역 공격" : "강화 광역 공격", {
        area: true, motion: "skill1", range: papa ? 1 : phase + 1, offsets: papa ? "-1|1" : phase === 1 ? "1|2" : "1|2|3",
        effect: "orbis_" + (papa ? "papa_burst" : "eliza_sweep") + (phase === 2 ? "_enraged" : "") + "_effects"
      });
      const patternId = m.id + "_phase_0" + phase;
      pattern(patternId, [["EXECUTE_TILE", "ALWAYS", basic, 0, "", 2, 2],
        ["TELEGRAPH_TILE", "ALWAYS", special, 1, "", 3, 1], ["EXECUTE_TILE", "ALWAYS", special, 0, "", 4, 4], ["WAIT"]]);
      add("BossPhaseDefinitions", {SchemaVersion: 1, EnemyDefinitionId: m.id, PhaseIndex: phase, PhaseId: phase === 1 ? "OPENING" : "ENRAGED",
        HpRatioLE: phase === 1 ? 1 : 0.5, PatternId: patternId, Enabled: "true",
        ReinforcementPoolId: papa && phase === 2 ? "orbis_papa_pixie_adds" : "", ReinforcementIntervalTurns: papa && phase === 2 ? 4 : 0,
        ReinforcementMaxAlive: papa && phase === 2 ? 1 : 0, ReinforcementSpawnRange: 0});
    }
  }
  capabilities.push({enemyDefinitionId: m.id, modelId: m.model.toLowerCase(), modelPath: path.relative(root, out).replaceAll("\\", "/"),
    originalResource: resources.resources[m.key].id, components: b.listComponents(), stateSetComponent: false, stateComponent: false,
    playback: "BattleUnitPresentationComponent direct SpriteRUID", attackAction: m.key.startsWith("jr_") ? "jump" : "attack1",
    deathAction: "die1", hitAction: "hit1", facing: "ApplySpriteFacing/FlipX", headAnchor: "BattleHeadAnchor",
    deathOwner: "BattleUnitComponent/BattleOutcomeLogic", bossPhaseOwner: m.boss ? "BossPhaseStateComponent" : null,
    runtimeVerification: "BLOCKED_MAKER_MCP_UNAVAILABLE"});
}
rosters.forEach((waves, index) => {
  const n = index + 1, stageId = "orbis_stage_" + String(n).padStart(2, "0");
  add("StageDefinitions", {SchemaVersion: 3, StageId: stageId, RegionId: "orbis", StageIndex: n,
    StageType: n === 7 || n === 14 ? "BOSS" : "NORMAL", DisplayName: stageNames[index], CellCount: 7, CellStartX: -3.36,
    CellSpacing: 1.12, UnitY: -0.05, PlayerStartCell: 3, QueueCapacity: 3, WaveTableId: stageId + "_waves"});
  add("StageMapRoutes", {SchemaVersion: 1, StageId: stageId,
    MapId: n === 7 ? mapIds[2] : n === 14 ? mapIds[3] : n < 7 ? mapIds[0] : mapIds[1], SpawnX: 0, SpawnY: 0, Enabled: "true"});
  waves.forEach((keys, wi) => {
    const pool = stageId + "_wave_" + (wi + 1);
    const mixed = new Set(keys).size > 1;
    (mixed ? keys : [keys[0]]).forEach((key, si) => add("EnemySpawnPools", {PoolId: pool, EnemyDefinitionId: byKey[key].id,
      EnemyModelId: byKey[key].model.toLowerCase(), Weight: 1, MinWaveIndex: wi + 1, MaxWaveIndex: wi + 1, SpawnIndex: mixed ? si + 1 : 0}));
    add("StageEnemyWaves", {WaveTableId: stageId + "_waves", WaveIndex: wi + 1, SpawnTriggerMode: "CLEAR_ONLY", EnemyPoolId: pool,
      SpawnCount: keys.length, MaxConcurrent: 2, SpawnSidePolicy: "BALANCED", ClearSpawnDelaySeconds: 0.6,
      ForceAfterTurns: 0, ForceAfterSeconds: 0, TriggerPhaseIndex: 0});
  });
});
for (const key of ["star_pixie", "lunar_pixie", "luster_pixie"]) add("EnemySpawnPools", {PoolId: "orbis_papa_pixie_adds",
  EnemyDefinitionId: byKey[key].id, EnemyModelId: byKey[key].model.toLowerCase(), Weight: 1, MinWaveIndex: 1, MaxWaveIndex: 1, SpawnIndex: 0});
add("RegionDefinitions", {SchemaVersion: 1, RegionId: "orbis", DisplayName: "오르비스", RegionOrder: 7, Enabled: "true"});
for (const [name, rows] of Object.entries(additions)) {
  const file = path.join(data, name + ".csv");
  const t = schema.parseCSV(fs.readFileSync(file, "utf8"));
  // This generator owns only Orbis rows. Other regions are retained, including their ordering.
  t.rows = t.rows.filter(r => !Object.values(r).some(v => /^orbis_|^skill_orbis_/.test(v)) && !(name === "RegionDefinitions" && r.RegionId === "orbis"));
  if (name === "EnemySpawnPools" && !t.headers.includes("SpawnIndex")) t.headers.push("SpawnIndex");
  t.rows.push(...rows); t.dirty = true;
  fs.writeFileSync(file, schema.serializeCSV(t));
}
// Shared scenic models are reused across all four maps; no new runtime controller is needed.
const scenery = [
  ["OrbisStoneFloor", "3413251c390346e7acce30580c562ff7", 1],
  ["OrbisGardenPillar", "e58e17b0848641aba9a586e61817df67", 1.5],
  ["OrbisCloudBank", "c5b77d0a8b8b4bbebee53da0edf83c17", 0.6]
];
for (const [name, ruid, scale] of scenery) { const {b, out} = model(name, ruid, scale, "MapObjects"); b.write(out); }
for (const [index, id] of mapIds.entries()) {
  const b = MapBuilder.fromTemplate(baseMapPath, id);
  b.remove("Object_Henesys_battle").remove("TEMP_PlatformPreview");
  b.patchComponent(id, "script.BattleSessionComponent", {AutoStartPrototypeBattle: false, CellCount: 7, CellStartX: -3.36, CellSpacing: 1.12, UnitY: -0.05, PlayerStartCell: 3, QueueCapacity: 3});
  b.patchComponent(id, "script.MapBgmPlaylistComponent", {TrackRUIDs: JSON.stringify({k: "number", v: "string", e: {1: index < 2 ? "c97353f4ebcd4af1b9c69a521fb1a635" : "be5fb97e993e48b29e23b55ca2029610"}})});
  b.patchComponent("Background", "MOD.Core.BackgroundComponent", {Type: 4, TemplateRUID: "", TopColor: index === 2 ? {r: 0.28, g: 0.21, b: 0.52, a: 1} : index === 3 ? {r: 0.34, g: 0.42, b: 0.68, a: 1} : {r: 0.23, g: 0.46, b: 0.8, a: 1},
    MiddleTopColor: {r: 0.6, g: 0.79, b: 0.95, a: 1}, MiddleBottomColor: {r: 0.81, g: 0.88, b: 1, a: 1}, BottomColor: {r: 0.94, g: 0.96, b: 1, a: 1}, MiddleTopRatio: 0.7, MiddleBottomRatio: 0.3});
  // Keep the Maker-authored ground chain (ids/lengths/neighbours unchanged), omit unrelated upper/remote ground.
  const ground = b.getFootholds().filter(f => f.groupID === 2);
  b.patchComponent(id, "MOD.Core.FootholdComponent", {FootholdsByLayer: {1: ground}});
  // Retain native tile physics metadata while replacing its grass visuals with stone scenery.
  b.patchComponent("TileMap", "MOD.Core.TileMapComponent", {Color: {r: 1, g: 1, b: 1, a: 0}});
  b.patch("SpawnLocation", {pos: [0, 0.05, 0]}).patchComponent("SpawnLocation", "MOD.Core.SpriteRendererComponent", {Color: {r: 1, g: 1, b: 1, a: 0}});
  for (let i = 1; i <= 9; i++) b.patch("BattlePlatforms/BattleCell" + i, {enable: false});
  const decoDir = path.join(root, "RootDesk/MyDesk/Models/MapObjects");
  b.placeModel("BattleScenery/CloudBank", path.join(decoDir, "OrbisCloudBank.model"), {pos: [0, 2.7, 0]});
  for (let i = 0; i < 13; i++) b.placeModel("BattleScenery/Stone" + (i + 1), path.join(decoDir, "OrbisStoneFloor.model"), {pos: [(i - 6) * 1.2, -0.30, 0]});
  const pillarXs = index === 0 ? [-5.1, 5.1] : index === 1 ? [-5.1, -3.9, 3.9, 5.1] : [-4.9, -3.7, 3.7, 4.9];
  for (const [pi, x] of pillarXs.entries()) b.placeModel("BattleScenery/Pillar" + (pi + 1), path.join(decoDir, "OrbisGardenPillar.model"), {pos: [x, 0.75, 0]});
  b.write(path.join(root, "map", id + ".map"));
}
// Sector membership only makes the physical arenas loadable. It adds no progression or lobby edge.
const sectorPath = path.join(root, "Global/SectorConfig.config");
const sectorRaw = fs.readFileSync(sectorPath, "utf8");
const sector = JSON.parse(sectorRaw);
const entries = sector.ContentProto.Json.Sectors[0].entries;
for (const id of mapIds) if (!entries.includes("map://" + id)) entries.push("map://" + id);
const sectorNewline = sectorRaw.includes("\r\n") ? "\r\n" : "\n";
fs.writeFileSync(sectorPath, JSON.stringify(sector, null, 2).replaceAll("\n", sectorNewline) + (/[\r\n]$/.test(sectorRaw) ? sectorNewline : ""));
fs.writeFileSync(path.join(__dirname, "model-capabilities.json"), JSON.stringify(capabilities, null, 2) + "\n");
fs.writeFileSync(path.join(__dirname, "expected-content.json"), JSON.stringify({monsters, stageNames, rosters, mapIds}, null, 2) + "\n");
console.log(JSON.stringify({stages: rosters.length, waves: rosters.flat().length, monsters: monsters.length, maps: mapIds.length,
  addedRows: Object.fromEntries(Object.entries(additions).map(([k, r]) => [k, r.length]))}, null, 2));
