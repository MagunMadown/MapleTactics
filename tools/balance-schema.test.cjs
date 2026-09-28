"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const S=require("./balance-schema.js");
const dataDir=path.join(__dirname,"../RootDesk/MyDesk/03_Data");
const all=Object.fromEntries(fs.readdirSync(dataDir).filter(n=>n.endsWith(".csv")).map(n=>[n.slice(0,-4),S.parseCSV(fs.readFileSync(path.join(dataDir,n),"utf8"))]));
const copy=()=>structuredClone(all);
test("all 47 current CSVs pass explicit schema; original bytes round-trip",()=>{
  assert.equal(Object.keys(all).length,47);assert.deepEqual(S.validate(all),[]);
  for(const t of Object.values(all))assert.equal(S.serializeCSV(t),t.raw);
});
test("six legacy union tables read-only, six current tables editable",()=>{
  assert.equal(Object.keys(S.legacy).length,6);
  assert.equal(Object.keys(all).filter(n=>n.startsWith("Union")&&!S.meta(n).legacy).length,6);
  for(const n of Object.keys(S.legacy))assert.equal(S.meta(n).readonly,true);
});
for(const n of ["UnionStatLevelDefinitions","UnionUpgradeLevels"]){
  test(n+" allows same id at different levels and rejects duplicate numeric level",()=>{
    const t=copy();assert.deepEqual(S.validate(t),[]);
    t[n].rows.push({...t[n].rows[0],Level:"01"});
    assert.ok(S.validate(t).some(e=>e.table===n&&e.code==="DUPLICATE_PRIMARY_KEY"));
  });
}
test("TileId points to enemy skills, not player skills or terrain",()=>{
  const t=copy();t.EnemyPatternSteps.rows[0].TileId=t.WarriorSkillDefinitions.rows[0].SkillId;
  assert.ok(S.validate(t).some(e=>e.table==="EnemyPatternSteps"&&e.column==="TileId"));
});
test("board RegionId has no world-region foreign key",()=>{
  assert.equal(S.meta("UnionBoardCellDefinitions").columns.RegionId.ref,null);
  assert.ok(!S.validate(all).some(e=>e.table==="UnionBoardCellDefinitions"));
});
test("unused and presentation-reserved columns read-only",()=>{
  assert.ok(S.meta("RelicDefinitions").columns.EffectDescription.readonly);
  assert.ok(S.meta("TopHudThemeDefinitions").columns.BackdropColor.readonly);
  assert.ok(S.meta("TopHudThemeDefinitions").columns.BackdropAlpha.readonly);
});
for(const [table,column,value,code] of [
  ["UtilitySkillDefinitions","CooldownTurns","four","INVALID_UTILITY_NUMBER"],
  ["UtilitySkillDefinitions","SchemaVersion","2","UNSUPPORTED_SKILL_SCHEMA"],
  ["UtilitySkillDefinitions","RequiredJobTag","typo","REFERENCE_NOT_FOUND"],
  ["UtilitySkillDefinitions","EffectSetId","typo","REFERENCE_NOT_FOUND"],
  ["UtilitySkillDefinitions","CostValue","1","UTILITY_COST_UNSUPPORTED"],
  ["UtilitySkillDefinitions","FreePlay","true","UTILITY_FREE_PLAY_UNSUPPORTED"],
  ["UtilitySkillEffectSteps","EffectType","GUADR","UNKNOWN_UTILITY_EFFECT"],
  ["UtilitySkillEffectSteps","ParameterA","TYPO","INVALID_UTILITY_EFFECT_PARAMETERS"],
  ["UtilitySkillEffectSteps","Value","0.5","INVALID_UTILITY_NUMBER"],
  ["UtilitySkillEffectSteps","ConditionId","IF_TRUE","UTILITY_CONDITION_UNSUPPORTED"],
  ["UtilitySkillEffectSteps","StepIndex","2","INVALID_EFFECT_STEP_SEQUENCE"]
]){
  test(table+"."+column+" invalid data blocked",()=>{
    const t=copy();t[table].rows[0][column]=value;
    assert.ok(S.validate(t).some(e=>e.code.startsWith(code)));
  });
}
test("missing utility dependency prevents export validation",()=>{
  const t=copy();delete t.UtilitySkillEffectSteps;
  assert.ok(S.validate(t).some(e=>e.code==="UTILITY_DATA_MISSING"));
});
test("duplicate utility jobs, missing jobs, orphan steps and skill collision rejected",()=>{
  const t=copy();t.UtilitySkillDefinitions.rows[0].RequiredJobTag="mage";
  t.UtilitySkillDefinitions.rows[0].SkillId=t.WarriorSkillDefinitions.rows[0].SkillId;
  t.UtilitySkillEffectSteps.rows.push({...t.UtilitySkillEffectSteps.rows[0],EffectSetId:"orphan"});
  const codes=S.validate(t).map(e=>e.code);
  for(const code of ["UTILITY_JOB_AMBIGUOUS","UTILITY_JOB_MISSING:warrior","ORPHAN_UTILITY_EFFECT_SET","UTILITY_SKILL_ID_COLLISION"])assert.ok(codes.includes(code),code);
});
test("CSV quoted comma, multiline, escaped quotes, BOM and CRLF survive edit",()=>{
  const raw='\uFEFFid,text\r\n1,"a,b\r\n""hello"""\r\n';
  const t=S.parseCSV(raw);assert.equal(t.rows[0].text,'a,b\r\n"hello"');
  t.dirty=true;assert.equal(S.serializeCSV(t),raw);
  assert.throws(()=>S.parseCSV('a,b\n1,"unclosed'));
  assert.throws(()=>S.parseCSV('a,a\n1,2'));
  assert.throws(()=>S.parseCSV('a,b\n1'));
});
test("browser scripts parse and module exports without Node",()=>{
  const context=vm.createContext({});vm.runInContext(fs.readFileSync(path.join(__dirname,"balance-schema.js"),"utf8"),context);
  assert.equal(typeof context.BalanceSchema.validate,"function");
  const html=fs.readFileSync(path.join(__dirname,"balance-editor.html"),"utf8");
  for(const m of html.matchAll(/<script>([\s\S]*?)<\/script>/g))new vm.Script(m[1]);
  assert.ok(html.includes('ignoreBOM:true'));
  assert.ok(html.includes('if(check().length)'));
});

test("required enemy skill cannot be blank even though WAIT permits blank",()=>{
  const t=copy();t.EnemyPatternSteps.rows[0].TileId="";
  assert.ok(S.validate(t).some(e=>e.code==="PATTERN_TILE_ID_MISSING"));
});
test("THROW_BEHIND utility effect follows ContentValidator.ValidateUtilityEffect",()=>{
  const t=copy();const step=t.UtilitySkillEffectSteps.rows.find(r=>r.EffectType==="THROW_BEHIND");
  assert.ok(step);assert.deepEqual(S.validate(t),[]);
  step.Value="0";
  assert.ok(S.validate(t).some(e=>e.code==="INVALID_UTILITY_EFFECT_PARAMETERS"));
});
