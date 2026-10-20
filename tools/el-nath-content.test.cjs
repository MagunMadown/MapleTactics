"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const S=require("./balance-schema.js");
const dir=path.join(__dirname,"../RootDesk/MyDesk/03_Data");
const tables=()=>Object.fromEntries(fs.readdirSync(dir).filter(n=>n.endsWith(".csv")).map(n=>[n.slice(0,-4),S.parseCSV(fs.readFileSync(path.join(dir,n),"utf8"))]));
test("El Nath stages are contiguous, independently routed, and outside campaign nodes",()=>{
  const t=tables(), stages=t.StageDefinitions.rows.filter(r=>r.RegionId==="el_nath").sort((a,b)=>+a.StageIndex-+b.StageIndex);
  assert.ok(stages.length>0);
  stages.forEach((s,i)=>{
    assert.equal(+s.StageIndex,i+1);
    assert.equal(+s.CellCount,7);
    const route=t.StageMapRoutes.rows.find(r=>r.StageId===s.StageId);
    assert.ok(route&&route.MapId.startsWith("el_nath_"));
    assert.ok(fs.existsSync(path.join(__dirname,"../map",route.MapId+".map")));
    const waves=t.StageEnemyWaves.rows.filter(r=>r.WaveTableId===s.WaveTableId).sort((a,b)=>+a.WaveIndex-+b.WaveIndex);
    assert.ok(waves.length>0);waves.forEach((w,j)=>assert.equal(+w.WaveIndex,j+1));
    assert.ok(!t.NodeDefinitions.rows.some(r=>Object.values(r).includes(s.StageId)));
  });
  assert.equal(stages.at(-1).StageType,"BOSS");
  assert.deepEqual(S.validate(t),[]);
});
test("Yeti and Pepe has exactly one configured, non-recursive Pepe successor",()=>{
  const t=tables(),rider=t.EnemyDefinitions.rows.find(r=>r.EnemyDefinitionId==="el_nath_yeti_pepe"),pepe=t.EnemyDefinitions.rows.find(r=>r.EnemyDefinitionId==="el_nath_pepe");
  assert.equal(rider.DeathSpawnEnemyDefinitionId,pepe.EnemyDefinitionId);assert.equal(rider.DeathSpawnModelId,"elnathpepe");
  assert.equal(pepe.DeathSpawnEnemyDefinitionId,"");assert.equal(pepe.DeathSpawnModelId,"");
  assert.ok(t.EnemySpawnPools.rows.some(r=>r.EnemyDefinitionId===pepe.EnemyDefinitionId&&r.EnemyModelId===rider.DeathSpawnModelId));
});
test("all enemies reachable from El Nath waves, including defeat successors, exclude heavy aggro and quick",()=>{
  const t=tables(),waveIds=new Set(t.StageDefinitions.rows.filter(r=>r.RegionId==="el_nath").map(r=>r.WaveTableId));
  const pools=new Set(t.StageEnemyWaves.rows.filter(r=>waveIds.has(r.WaveTableId)).map(r=>r.EnemyPoolId));
  const ids=new Set(t.EnemySpawnPools.rows.filter(r=>pools.has(r.PoolId)).map(r=>r.EnemyDefinitionId));
  const definitions=new Map(t.EnemyDefinitions.rows.map(r=>[r.EnemyDefinitionId,r]));
  for(const id of ids){
    const enemy=definitions.get(id);assert.ok(enemy,"reachable enemy missing: "+id);
    if(enemy.DeathSpawnEnemyDefinitionId)ids.add(enemy.DeathSpawnEnemyDefinitionId);
    for(const trait of (enemy.TraitIds||"").split("|").filter(Boolean))
      assert.ok(!["HEAVY","AGGRO","QUICK"].includes(trait),id+" has forbidden trait "+trait);
  }
  assert.ok(ids.size>0,"El Nath must have at least one reachable enemy");
});
for(const [label,mutate,reason]of [
  ["half pair",(r,t)=>{r.DeathSpawnModelId="";},"DEATH_SPAWN_PAIR_REQUIRED"],
  ["unregistered model",r=>{r.DeathSpawnModelId="missing_model";},"DEATH_SPAWN_MODEL_PAIR_NOT_REGISTERED"],
  ["cycle",(r,t)=>{const p=t.EnemyDefinitions.rows.find(e=>e.EnemyDefinitionId==="el_nath_pepe");p.DeathSpawnEnemyDefinitionId=r.EnemyDefinitionId;p.DeathSpawnModelId="elnathyetipepe";},"DEATH_SPAWN_CYCLE"],
  ["boss source",r=>{r.IsBoss="true";},"DEATH_SPAWN_BOSS_NOT_SUPPORTED"]
])test("defeat successor rejects "+label,()=>{const t=tables(),r=t.EnemyDefinitions.rows.find(e=>e.EnemyDefinitionId==="el_nath_yeti_pepe");mutate(r,t);assert.ok(S.validate(t).some(e=>e.code===reason));});
test("all El Nath actors have idle/move/hit/attack/death art and specials use existing queue actions",()=>{
  const t=tables();for(const e of t.EnemyDefinitions.rows.filter(r=>r.EnemyDefinitionId.startsWith("el_nath_")))for(const k of ["IdleMotionRuid","MoveMotionRuid","HitMotionRuid","AttackMotionRuid","DeathMotionRuid"])assert.match(e[k],/^[a-f0-9]{32}$/);
  const skills=t.EnemySkillDefinitions.rows.filter(r=>r.SkillId.startsWith("el_nath_"));
  for(const s of skills){assert.ok(s.HudIconRuid);assert.ok(t.EnemyPatternSteps.rows.some(p=>p.TileId===s.SkillId));}
  for(const id of ["el_nath_yeti_stomp","el_nath_snowman_frost","el_nath_snowman_blizzard"])assert.ok(skills.find(s=>s.SkillId===id).SkillTags.split("|").includes("caster_motion"));
  const cast=t.EnemyPatternSteps.rows.filter(p=>p.TileId==="el_nath_snowman_blizzard"&&p.ActionType==="CAST_INTERRUPTIBLE");assert.equal(cast.length,2);cast.forEach(p=>assert.equal(p.ParamA,"1"));
});
