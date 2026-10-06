"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const S=require("./balance-schema.js");
const dataDir=path.join(__dirname,"../RootDesk/MyDesk/03_Data");
const all=Object.fromEntries(fs.readdirSync(dataDir).filter(n=>n.endsWith(".csv")).map(n=>[n.slice(0,-4),S.parseCSV(fs.readFileSync(path.join(dataDir,n),"utf8"))]));
const copy=()=>structuredClone(all);
const unionProduct=(table,productId)=>{
  const row=table.rows.find(r=>r.ProductId===productId);
  assert.ok(row,"missing union product: "+productId);
  return row;
};
test("all 48 current CSVs pass explicit schema; original bytes round-trip",()=>{
  assert.equal(Object.keys(all).length,48);assert.deepEqual(S.validate(all),[]);
  for(const t of Object.values(all))assert.equal(S.serializeCSV(t),t.raw);
});
test("six legacy union tables read-only, seven current tables editable",()=>{
  assert.equal(Object.keys(S.legacy).length,6);
  assert.equal(Object.keys(all).filter(n=>n.startsWith("Union")&&!S.meta(n).legacy).length,7);
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
test("THROW_FORWARD utility effect follows ContentValidator.ValidateUtilityEffect",()=>{
  const t=copy();const step=t.UtilitySkillEffectSteps.rows.find(r=>r.EffectType==="THROW_FORWARD");
  assert.ok(step);assert.deepEqual(S.validate(t),[]);
  step.Value="1";
  assert.ok(S.validate(t).some(e=>e.code==="INVALID_UTILITY_EFFECT_PARAMETERS"));
});
test("THROW_BEHIND utility effect follows ContentValidator.ValidateUtilityEffect",()=>{
  const t=copy();const step=t.UtilitySkillEffectSteps.rows.find(r=>r.EffectType==="THROW_FORWARD");
  assert.ok(step);Object.assign(step,{EffectType:"THROW_BEHIND",Value:"1",ParameterA:""});
  assert.deepEqual(S.validate(t),[]);
  step.Value="0";
  assert.ok(S.validate(t).some(e=>e.code==="INVALID_UTILITY_EFFECT_PARAMETERS"));
});

for(const modifier of ["","CARRY_CASTER","CANCEL_QUEUE","CARRY_CASTER|CANCEL_QUEUE","CANCEL_QUEUE|CARRY_CASTER"]){
  test("PUSH_DISTANCE accepts supported modifier set "+JSON.stringify(modifier),()=>{
    const t=copy(),step=t.UtilitySkillEffectSteps.rows.find(r=>r.EffectType==="PUSH_DISTANCE");
    assert.ok(step);step.ParameterB=modifier;
    assert.deepEqual(S.validate(t),[]);
  });
}
for(const modifier of ["CANCEL","CARRY_CASTER|CARRY_CASTER","CANCEL_QUEUE|CANCEL_QUEUE","CARRY_CASTER|CANCEL_QUEUE|CARRY_CASTER","CARRY_CASTER|UNKNOWN"," CANCEL_QUEUE"]){
  test("PUSH_DISTANCE rejects unknown or repeated modifier "+JSON.stringify(modifier),()=>{
    const t=copy(),step=t.UtilitySkillEffectSteps.rows.find(r=>r.EffectType==="PUSH_DISTANCE");
    assert.ok(step);step.ParameterB=modifier;
    assert.ok(S.validate(t).some(e=>e.code==="INVALID_UTILITY_EFFECT_PARAMETERS"));
  });
}

test("UnionShopProducts is editable and current sale prices survive CSV round-trip",()=>{
  assert.equal(S.meta("UnionShopProducts").readonly,false);
  assert.deepEqual(S.meta("UnionShopProducts").key,["ProductId"]);
  const rows=all.UnionShopProducts.rows;
  assert.equal(rows.filter(r=>r.Enabled==="true").length,3);
  assert.equal(rows.find(r=>r.ProductId==="supply_potion").Price,"20");
  assert.equal(rows.find(r=>r.ProductId==="job_unlock").Price,"2000");
  const free=unionProduct(all.UnionShopProducts,"job_unlock_free");
  assert.equal(free.DisplayName,"직업 해제 토큰 (무료)");
  assert.equal(free.Kind,"JOB_TOKEN");assert.equal(free.RefId,"job_unlock");assert.equal(free.Price,"0");
  assert.equal(free.IconRUID,unionProduct(all.UnionShopProducts,"job_unlock").IconRUID);
  assert.equal(free.SortOrder,"15");assert.equal(free.SchemaVersion,"1");
  assert.equal(free.Description,"계정당 한 번 무료로 받을 수 있습니다. 캐릭터 선택창에서 잠긴 직업 1개를 영구 해금합니다.");
  const t=copy();t.UnionShopProducts.rows.find(r=>r.ProductId==="job_unlock").Price="2200";
  t.UnionShopProducts.dirty=true;
  assert.deepEqual(S.validate(t),[]);
  assert.equal(S.parseCSV(S.serializeCSV(t.UnionShopProducts)).rows.find(r=>r.ProductId==="job_unlock").Price,"2200");
});

const unionCases=[
  ["supply_potion","SchemaVersion","2","UNSUPPORTED_SCHEMA"],
  ["supply_potion","ProductId","supply|bad","INVALID_PRODUCT_ID"],
  ["supply_potion","DisplayName","   ","REQUIRED_FIELD_MISSING"],
  ["supply_potion","Kind","PACKAGE","UNKNOWN_PRODUCT_KIND"],
  ["supply_potion","Price","0","INVALID_PRODUCT_NUMBER"],
  ["supply_potion","Price","-1","INVALID_PRODUCT_NUMBER"],
  ["supply_potion","Price","1.5","INVALID_PRODUCT_NUMBER"],
  ["supply_potion","Price","oops","INVALID_PRODUCT_NUMBER"],
  ["supply_potion","Price","9007199254740991","INVALID_PRODUCT_NUMBER"],
  ["supply_potion","SortOrder","1.5","INVALID_PRODUCT_NUMBER"],
  ["supply_potion","SortOrder","0","INVALID_PRODUCT_NUMBER"],
  ["supply_potion","Enabled","maybe","INVALID_PRODUCT_FLAGS"],
  ["supply_potion","Retired","","INVALID_PRODUCT_FLAGS"],
  ["supply_potion","Removed","maybe","INVALID_PRODUCT_FLAGS"],
  ["supply_potion","Retired","true","RETIRED_PRODUCT_ENABLED"],
  ["supply_potion","Removed","true","REMOVED_PRODUCT_NOT_RETIRED"],
  ["supply_potion","IconRUID","not-an-icon","INVALID_PRODUCT_PRESENTATION"],
  ["supply_potion","Description","  ","INVALID_PRODUCT_PRESENTATION"],
  ["supply_potion","RefId","white_potion","UNSUPPORTED_SUPPLY_REF"],
  ["job_unlock","RefId","warrior","UNSUPPORTED_JOB_TOKEN_REF"],
  ["job_unlock","Price","0","INVALID_PRODUCT_NUMBER"],
  ["job_unlock","Price","-1","INVALID_PRODUCT_NUMBER"],
  ["job_unlock_free","Price","1","INVALID_PRODUCT_NUMBER"],
  ["job_unlock_free","Price","-1","INVALID_PRODUCT_NUMBER"],
  ["job_unlock_free","Price","0.5","INVALID_PRODUCT_NUMBER"],
  ["job_unlock_free","Price","oops","INVALID_PRODUCT_NUMBER"],
  ["job_unlock_free","Price","","INVALID_PRODUCT_NUMBER"],
  ["job_unlock_free","Price","  ","INVALID_PRODUCT_NUMBER"],
  ["job_unlock_free","Kind","SUPPLY","INVALID_FREE_JOB_TOKEN_PRODUCT"],
  ["job_unlock_free","RefId","orange_potion","INVALID_FREE_JOB_TOKEN_PRODUCT"],
  ["job_unlock_free","ProductId","job_unlock_bonus","INVALID_PRODUCT_NUMBER"],
  ["union_forest","RefId","union_blade","INVALID_SKIN_REF"],
];
for(const [productId,column,value,code] of unionCases){
  test("union shop rejects "+productId+"."+column+"="+JSON.stringify(value),()=>{
    const t=copy();unionProduct(t.UnionShopProducts,productId)[column]=value;
    assert.ok(S.validate(t).some(e=>e.table==="UnionShopProducts"&&e.code===code));
  });
}
test("union product IDs and numeric display order cannot collide",()=>{
  const t=copy(),paid=unionProduct(t.UnionShopProducts,"job_unlock");
  paid.ProductId=unionProduct(t.UnionShopProducts,"supply_potion").ProductId;
  paid.SortOrder="010";
  const codes=S.validate(t).filter(e=>e.table==="UnionShopProducts").map(e=>e.code);
  assert.ok(codes.includes("DUPLICATE_PRIMARY_KEY"));
  assert.ok(codes.includes("DUPLICATE_SORT_ORDER"));
});
test("retired skins remain valid without native skin FK or active presentation",()=>{
  const t=copy();for(const r of t.UnionShopProducts.rows.filter(r=>r.Kind==="SKIN")){
    r.IconRUID="";r.Description="";
    assert.ok(!t.DamageSkinDefinitions.rows.some(s=>s.SkinId===r.RefId));
  }
  assert.deepEqual(S.validate(t),[]);
  unionProduct(t.UnionShopProducts,"union_forest").Retired="false";
  assert.ok(S.validate(t).some(e=>e.code==="REMOVED_PRODUCT_NOT_RETIRED"));
});
test("union flags mirror accepted native boolean spellings",()=>{
  const t=copy(),supply=unionProduct(t.UnionShopProducts,"supply_potion");supply.Enabled="YES";
  supply.Retired="0";supply.Removed="No";
  assert.deepEqual(S.validate(t),[]);
});

function studioUnionValidator(){
  const html=fs.readFileSync(path.join(__dirname,"balance-studio.html"),"utf8").replace(/\r\n/g,"\n");
  const begin=html.indexOf("  function unionShopProductIssues(");
  const end=html.indexOf("  // ---------- Navigation UI ----------",begin);
  assert.ok(begin>=0&&end>begin);
  const context=vm.createContext({
    state:{idIndex:new Map(),tables:new Map([["DamageSkinDefinitions",{header:all.DamageSkinDefinitions.headers,rows:all.DamageSkinDefinitions.rows.map(r=>all.DamageSkinDefinitions.headers.map(h=>r[h]))}]])},validateVocabRow(){},
    normalizeRuid:v=>/^[0-9a-f]{32}$/i.test(v)?v:null,
  });
  vm.runInContext(html.slice(begin,end)+";globalThis.checkUnionTable=validateTable;",context);
  return t=>{
    const def={fileName:"UnionShopProducts.csv",header:t.headers,keys:["ProductId"],
      columns:t.headers.map((name,idx)=>({name,idx,type:"text",isRealRef:false})),
      rows:t.rows.map(r=>t.headers.map(h=>r[h]))};
    return context.checkUnionTable(def);
  };
}
test("Balance Studio uses the union category and validates the same authored products",()=>{
  const html=fs.readFileSync(path.join(__dirname,"balance-studio.html"),"utf8");
  assert.ok(html.includes('UnionShopProducts: "union_live"'));
  assert.ok(html.includes('UnionShopProducts: ["ProductId"]'));
  for(const script of html.matchAll(/<script>([\s\S]*?)<\/script>/g))new vm.Script(script[1]);
  const check=studioUnionValidator();
  assert.equal(check(all.UnionShopProducts).filter(e=>e.level==="error").length,0);
  for(const [productId,column,value,code] of unionCases){
    const t=structuredClone(all.UnionShopProducts);unionProduct(t,productId)[column]=value;
    assert.ok(check(t).some(e=>e.level==="error"&&e.msg.includes(code)),column+":"+code);
  }
  const duplicate=structuredClone(all.UnionShopProducts);
  const paid=unionProduct(duplicate,"job_unlock");
  paid.ProductId=unionProduct(duplicate,"supply_potion").ProductId;paid.SortOrder="010";
  const errors=check(duplicate).filter(e=>e.level==="error");
  assert.ok(errors.some(e=>e.col==="ProductId"));
  assert.ok(errors.some(e=>e.msg.includes("DUPLICATE_SORT_ORDER")));
});

test("active union skins require native catalog references while retired aliases remain compatible",()=>{
  const t=copy(),skin=t.UnionShopProducts.rows.find(r=>r.ProductId==="union_blade");
  skin.Enabled="true";skin.Retired="false";skin.IconRUID=unionProduct(t.UnionShopProducts,"supply_potion").IconRUID;
  assert.deepEqual(S.validate(t),[]);
  const studio=studioUnionValidator();
  assert.equal(studio(t.UnionShopProducts).filter(e=>e.level==="error").length,0);
  skin.ProductId="missing_skin";skin.RefId="missing_skin";
  assert.ok(S.validate(t).some(e=>e.code==="UNKNOWN_DAMAGE_SKIN_REF"));
  assert.ok(studio(t.UnionShopProducts).some(e=>e.msg.includes("UNKNOWN_DAMAGE_SKIN_REF")));
  skin.Enabled="false";skin.Retired="true";skin.IconRUID="";
  assert.deepEqual(S.validate(t),[]);
  assert.equal(studio(t.UnionShopProducts).filter(e=>e.level==="error").length,0);
});
