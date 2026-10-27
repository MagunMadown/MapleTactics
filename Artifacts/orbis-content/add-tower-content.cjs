"use strict";
// Incremental authoring: never rebuilds the existing fourteen stages or their maps.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const root = path.resolve(__dirname, "../..");
process.env.MSW_MODEL_BUILDER_MOD_CORE_VERSION = "26.10.0.0";
const {ModelBuilder, vector3} = require("../../.agents/skills/msw-general/scripts/model/msw_model_builder.cjs");
const {MapBuilder} = require("../../.agents/skills/msw-general/scripts/map/msw_map_builder.cjs");
const api = require("../../.agents/skills/msw-search/scripts/msw_resource_api.cjs");
const schema = require("../../tools/balance-schema.js");
const data = path.join(root, "RootDesk/MyDesk/03_Data");
const manifestPath = path.join(__dirname, "resources.json");
const expectedPath = path.join(__dirname, "expected-content.json");
const mapId = "orbis_tower_battle";
const monsters = [
  {key:"jr_stoneball",name:"주니어 스톤볼",hp:8,damage:2,range:1,scale:1.4,model:"OrbisJrStoneBall",pack:"mob/5200000.img",attackAction:"move"},
  {key:"stoneball",name:"스톤볼",hp:10,damage:3,range:2,scale:1.25,model:"OrbisStoneBall",pack:"mob/3000000.img",attackAction:"attack1"},
  {key:"fire_stoneball",name:"파이어 스톤볼",hp:10,damage:2,range:2,scale:1.25,model:"OrbisFireStoneBall",pack:"mob/5200002.img",attackAction:"attack1",status:"IGNITE",statusValue:1,statusTurns:2},
  {key:"ice_stoneball",name:"아이스 스톤볼",hp:10,damage:2,range:2,scale:1.25,model:"OrbisIceStoneBall",pack:"mob/5200001.img",attackAction:"attack1",status:"FROSTBITE",statusValue:0,statusTurns:1}
].map(m=>({...m,id:"orbis_"+m.key,boss:false,stationary:false}));
const stages = [
  {number:15,name:"오르비스 탑 상층",rosters:[["jr_stoneball","jr_stoneball"],["stoneball","stoneball"],["jr_stoneball","stoneball","stoneball"]]},
  {number:16,name:"오르비스 탑 원소 회랑",rosters:[["fire_stoneball","fire_stoneball"],["ice_stoneball","ice_stoneball","ice_stoneball"],["fire_stoneball","fire_stoneball","ice_stoneball"]]}
];
const tableNames = ["EnemyDefinitions","EnemySkillDefinitions","EnemyImpactPresentations","EnemyPatternSteps","SkillEffectSteps","StageDefinitions","StageMapRoutes","StageEnemyWaves","EnemySpawnPools"];
const readTable = name => schema.parseCSV(fs.readFileSync(path.join(data,name+".csv"),"utf8"));
const saveJSON = (file,value) => fs.writeFileSync(file,JSON.stringify(value,null,2)+"\n");
const additions = {};
const add = (name,row) => (additions[name] ||= []).push(row);
function captureBaseline() {
  const file = path.join(__dirname,"tower-authoring-baseline.json");
  if (fs.existsSync(file)) return;
  const expected = JSON.parse(fs.readFileSync(expectedPath,"utf8"));
  const paths = tableNames.map(n=>"RootDesk/MyDesk/03_Data/"+n+".csv").concat(expected.mapIds.map(id=>"map/"+id+".map"),expected.monsters.map(m=>"RootDesk/MyDesk/Models/Monsters/"+m.model+".model"));
  saveJSON(file,{files:Object.fromEntries(paths.map(p=>{const b=fs.readFileSync(path.join(root,p));return [p,{bytes:b.length,sha256:crypto.createHash("sha256").update(b).digest("hex")}];})),expected});
}
function appendRows(name, rows) {
  const file = path.join(data,name+".csv"), original = fs.readFileSync(file,"utf8"), table=readTable(name);
  const keys = {EnemyDefinitions:["EnemyDefinitionId"],EnemySkillDefinitions:["SkillId"],EnemyImpactPresentations:["EntryId"],EnemyPatternSteps:["PatternId","StepIndex"],SkillEffectSteps:["EffectSetId","StepIndex"],StageDefinitions:["StageId"],StageMapRoutes:["StageId"],StageEnemyWaves:["WaveTableId","WaveIndex"],EnemySpawnPools:["PoolId","SpawnIndex","EnemyDefinitionId"]}[name];
  const fresh=rows.filter(row=>{
    const previous=table.rows.find(r=>keys.every(k=>String(r[k]??"")===String(row[k]??"")));
    if (!previous) return true;
    if (!table.headers.every(k=>String(previous[k]??"")===String(row[k]??""))) throw Error("Refusing to overwrite authored row: "+name+" "+keys.map(k=>row[k]).join("/"));
    return false;
  });
  if (!fresh.length) return;
  const eol=original.includes("\r\n")?"\r\n":"\n";
  const cell=v=>{const s=String(v??"");return /[",\r\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s;};
  fs.writeFileSync(file,original+(/\r?\n$/.test(original)?"":eol)+fresh.map(r=>table.headers.map(k=>cell(r[k])).join(",")).join(eol)+eol);
}
async function main() {
  captureBaseline();
  const manifest=JSON.parse(fs.readFileSync(manifestPath,"utf8"));
  await Promise.all(monsters.map(async m=>{manifest.resources[m.key] ||= await api.getResource(m.pack);}));
  manifest.towerRetrievedAt ||= new Date().toISOString();
  saveJSON(manifestPath,manifest);
  const defaultImpact=readTable("EnemyImpactPresentations").rows.find(r=>r.EntryId==="default").ImpactSoundRuid;
  const capabilities=JSON.parse(fs.readFileSync(path.join(__dirname,"model-capabilities.json"),"utf8"));
  for (const m of monsters) {
    const elements=manifest.resources[m.key].payload.elements;
    const asset=(rel,fallback="")=>elements.find(e=>e.rel_path===rel)?.ruid||fallback;
    const clip=elements.find(e=>e.rel_path===m.attackAction);
    if (!clip) throw Error("Missing original attack motion: "+m.pack+"/"+m.attackAction);
    const rate=Math.max(1,Math.ceil((clip.payload?.frames?.length||1)/(.55*10)*10)/10);
    const effectSet=m.status?m.id+"_attack_effects":"orbis_basic_attack_effects";
    const hit=asset("attack1/info/hit","eed46092f65940a7a8e77a1bd8e2aa75");
    const impact=asset("_audio/CharDam1",defaultImpact);
    add("EnemyDefinitions",{EnemyDefinitionId:m.id,DisplayName:m.name,MaxHp:m.hp,BasicAttackDamage:m.damage,PatternId:m.id+"_pattern",MovementPolicy:"TRACK_PLAYER",InitialFacingPolicy:"FACE_PLAYER",TraitIds:"",IsBoss:"false",IdleMotionRuid:asset("stand"),IdleMotionPlayRate:1,MoveMotionRuid:asset("move"),MoveMotionPlayRate:1.5,HitMotionRuid:asset("hit1"),HitMotionPlayRate:1,HitMotionDuration:.25,AttackMotionRuid:asset(m.attackAction),AttackMotionPlayRate:rate,AttackMotionDuration:.55,DeathMotionRuid:asset("die1"),DeathMotionPlayRate:1,DeathMotionDuration:.65,VisualOffsetY:0,FlatDamageReduction:0,AscensionHpBonus:1});
    add("EnemySkillDefinitions",{SchemaVersion:1,SkillId:m.id+"_attack",DisplayName:m.name+(m.status==="IGNITE"?" 화염 공격 (화상)":m.status==="FROSTBITE"?" 냉기 공격 (이동 봉쇄)":m.range>1?" 원거리 공격":" 근접 공격"),SkillTags:"attack|enemy|caster_motion|"+(m.range>1?"ranged":"melee")+(m.status?"|status":""),TargetingType:"FIRST_ENEMY_FORWARD",Range:m.range,TargetOffsets:"",CooldownTurns:0,CostType:"",CostValue:0,MotionProfileId:"basic_slash",EffectSetId:effectSet,ActionDuration:.7,FreePlay:"false",CastEffectRuid:asset("attack1/info/effect"),HitEffectRuid:hit,EffectScale:.75,ProjectileRuid:"",ProjectileSpeed:0,ProjectileScale:.8,ProjectileLaunchDelay:0,SkillTier:1,CasterMotionRuid:asset(m.attackAction),CasterMotionPlayRate:rate,CasterMotionDuration:.55,EnemyQueueTurns:1,HudIconRuid:asset("stand"),ProjectileCount:1,ProjectileInterval:0,ProjectileHeight:0,CastSoundRuid:asset("_audio/Attack1"),HitSoundRuid:impact});
    add("EnemyImpactPresentations",{SchemaVersion:1,EntryId:"skill_"+m.id+"_attack",EnemyDefinitionId:"*",SkillId:m.id+"_attack",Priority:200,ImpactSoundRuid:impact});
    add("EnemyImpactPresentations",{SchemaVersion:1,EntryId:m.id,EnemyDefinitionId:m.id,SkillId:"*",Priority:300,DamageSoundRuid:asset("_audio/Damage"),DeathSoundRuid:asset("_audio/Die")});
    if (m.status) {
      add("SkillEffectSteps",{SchemaVersion:1,EffectSetId:effectSet,StepIndex:1,EffectType:"DAMAGE",TargetSelector:"ALL_SKILL_TARGETS",Value:1,ParameterA:"SOURCE_BASIC_ATTACK"});
      add("SkillEffectSteps",{SchemaVersion:1,EffectSetId:effectSet,StepIndex:2,EffectType:m.status,TargetSelector:"PRIMARY_TARGET",Value:m.statusValue,ParameterA:m.statusTurns});
    }
    const steps=[["EXECUTE_TILE","ALWAYS",m.id+"_attack","",1,2],["TURN_TO_PLAYER","ALWAYS","","",1,3],["MOVE_TOWARD","CELL_FREE","","TOWARD_PLAYER",1,4],["WAIT","ALWAYS","","",1,1]];
    steps.forEach((s,i)=>add("EnemyPatternSteps",{SchemaVersion:1,PatternId:m.id+"_pattern",StepIndex:i+1,ActionType:s[0],ConditionType:s[1],TileId:s[2],TelegraphTurns:0,ParamA:s[3],NextStepOnSuccess:s[4],NextStepOnFailure:s[5],Enabled:"true"}));
    const output=path.join(root,"RootDesk/MyDesk/Models/Monsters",m.model+".model");
    if (!fs.existsSync(output)) {
      const b=ModelBuilder.fromTemplate(path.join(root,".agents/skills/msw-general/models/TransformOnly.model"),m.model);
      b.component("MOD.Core.SpriteRendererComponent").value("MOD.Core.SpriteRendererComponent","SpriteRUID",asset("stand"),"string").value("MOD.Core.SpriteRendererComponent","SortingLayer","MapLayer2","string").value("MOD.Core.SpriteRendererComponent","OrderInLayer",3,"int").value("MOD.Core.SpriteRendererComponent","FlipX",true,"bool").value("MOD.Core.TransformComponent","Scale",vector3(m.scale,m.scale,1),"vector3").child("BattleHeadAnchor",["MOD.Core.TransformComponent"]).childValue("BattleHeadAnchor","MOD.Core.TransformComponent","Position",vector3(0,elements.find(e=>e.rel_path==="stand").payload.height/100+.18,0),"vector3").write(output);
    }
    if (!capabilities.some(c=>c.enemyDefinitionId===m.id)) capabilities.push({enemyDefinitionId:m.id,modelId:m.model.toLowerCase(),modelPath:path.relative(root,output).replaceAll("\\","/"),originalResource:m.pack,components:["MOD.Core.TransformComponent","MOD.Core.SpriteRendererComponent"],stateSetComponent:false,stateComponent:false,playback:"BattleUnitPresentationComponent direct SpriteRUID",attackAction:m.attackAction,deathAction:"die1",hitAction:"hit1",facing:"ApplySpriteFacing/FlipX",headAnchor:"BattleHeadAnchor",deathOwner:"BattleUnitComponent/BattleOutcomeLogic",bossPhaseOwner:null,runtimeVerification:"PENDING_MAKER"});
  }
  for (const stage of stages) {
    const id="orbis_stage_"+stage.number;
    add("StageDefinitions",{SchemaVersion:3,StageId:id,RegionId:"orbis",StageIndex:stage.number,StageType:"NORMAL",DisplayName:stage.name,CellCount:7,CellStartX:-3.36,CellSpacing:1.12,UnitY:-.05,PlayerStartCell:3,QueueCapacity:3,WaveTableId:id+"_waves"});
    add("StageMapRoutes",{SchemaVersion:1,StageId:id,MapId:mapId,SpawnX:0,SpawnY:0,Enabled:"true"});
    stage.rosters.forEach((roster,wi)=>{
      const pool=id+"_wave_"+(wi+1),mixed=new Set(roster).size>1;
      (mixed?roster:[roster[0]]).forEach((key,si)=>add("EnemySpawnPools",{PoolId:pool,EnemyDefinitionId:"orbis_"+key,EnemyModelId:monsters.find(m=>m.key===key).model.toLowerCase(),Weight:1,MinWaveIndex:wi+1,MaxWaveIndex:wi+1,SpawnIndex:mixed?si+1:0}));
      add("StageEnemyWaves",{WaveTableId:id+"_waves",WaveIndex:wi+1,SpawnTriggerMode:"CLEAR_ONLY",EnemyPoolId:pool,SpawnCount:roster.length,MaxConcurrent:3,SpawnSidePolicy:"BALANCED",ClearSpawnDelaySeconds:.6,ForceAfterTurns:0,ForceAfterSeconds:0,TriggerPhaseIndex:0});
    });
  }
  for (const [name,rows] of Object.entries(additions)) appendRows(name,rows);
  const expected=JSON.parse(fs.readFileSync(expectedPath,"utf8"));
  for (const m of monsters) if (!expected.monsters.some(p=>p.id===m.id)) expected.monsters.push(m);
  for (const stage of stages) if (expected.stageNames.length<stage.number) {expected.stageNames.push(stage.name);expected.rosters.push(stage.rosters);}
  if (!expected.mapIds.includes(mapId)) expected.mapIds.push(mapId);
  saveJSON(expectedPath,expected);
  saveJSON(path.join(__dirname,"model-capabilities.json"),capabilities);
  const mapPath=path.join(root,"map",mapId+".map");
  if (!fs.existsSync(mapPath)) MapBuilder.fromTemplate(path.join(root,"map/orbis_guardian_battle.map"),mapId).write(mapPath);
  const sectorPath=path.join(root,"Global/SectorConfig.config"),raw=fs.readFileSync(sectorPath,"utf8"),sector=JSON.parse(raw);
  const entries=sector.ContentProto.Json.Sectors[0].entries;
  if (!entries.includes("map://"+mapId)) {entries.push("map://"+mapId);const eol=raw.includes("\r\n")?"\r\n":"\n";fs.writeFileSync(sectorPath,JSON.stringify(sector,null,2).replaceAll("\n",eol)+(/[\r\n]$/.test(raw)?eol:""));}
  console.log(JSON.stringify({stages:16,waves:44,monsters:19,maps:5,towerSpawnCounts:stages.map(s=>s.rosters.map(r=>r.length)),note:"Tower map seeded; import original 200080200 in Maker and adapt before verification."}));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
