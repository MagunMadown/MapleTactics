/* Explicit runtime contracts. No Id/Index name heuristics. Browser + Node, no dependencies. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.BalanceSchema = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";
  const keys = {
    JobDefinitions:["JobId"], JobStartingSkillEntries:["StartingSkillSetId","SlotIndex"],
    WeaponDefinitions:["WeaponType"], AugmentDefinitions:["AugmentId"], AugmentEffects:["AugmentId","Seq"],
    EnemyDefinitions:["EnemyDefinitionId"], EnemyPatternSteps:["PatternId","StepIndex"],
    EnemySpawnPools:["PoolId","EnemyDefinitionId","EnemyModelId"], EnemyDropDefinitions:["DropEntryId"],
    EnemyImpactPresentations:["EntryId"], BossPhaseDefinitions:["EnemyDefinitionId","PhaseIndex"],
    RegionDefinitions:["RegionId"], NodeDefinitions:["NodeGraphId","NodeId"], StageDefinitions:["StageId"],
    StageMapRoutes:["StageId"], StageEnemyWaves:["WaveTableId","WaveIndex"], StageRewardDefinitions:["StageRewardEntryId"],
    TopHudThemeDefinitions:["RegionId"], CurrencyDefinitions:["CurrencyId"], ShopDefinitions:["ShopId"],
    ShopEntries:["ShopEntryId"], ShopNodeBindings:["NodeGraphId","NodeId"], RelicDefinitions:["RelicId"],
    ConsumableDefinitions:["ConsumableId"], UnionRankDefinitions:["RankId"], UnionRewardDefinitions:["RewardId"],
    UnionJobGradeDefinitions:["GradeId"], UnionJobMilestoneDefinitions:["MilestoneId"], UnionStatDefinitions:["StatId"],
    UnionStatLevelDefinitions:["StatId","Level"], UnionUpgradeDefinitions:["UpgradeId"], UnionUpgradeLevels:["UpgradeId","Level"],
    UnionBlockDefinitions:["BlockId"], UnionBlockShapeDefinitions:["ShapeId"], UnionBoardCellDefinitions:["CellId"],
    UnionSpecialZoneDefinitions:["SpecialZoneId"], SkillEffectSteps:["EffectSetId","StepIndex"], UtilitySkillEffectSteps:["EffectSetId","StepIndex"]
  };
  const skillTables = ["SkillDefinitions","WarriorSkillDefinitions","MageSkillDefinitions","ArcherSkillDefinitions","ThiefSkillDefinitions","PirateSkillDefinitions","EnemySkillDefinitions"];
  for (const name of [...skillTables,"UtilitySkillDefinitions"]) keys[name] = ["SkillId"];
  const legacy = {
    UnionUpgradeDefinitions:"구형 구매 차단. 기존 저장 데이터 호환·환급 검증용으로 보존.",
    UnionUpgradeLevels:"구형 구매 차단. 이전 업그레이드의 환급 비용·레벨 검증에 사용.",
    UnionBlockDefinitions:"구형 구매 차단. 호환용 정의·검증만 남아 있음.",
    UnionBlockShapeDefinitions:"구형 블록 모양. 호환용 정의·검증만 남아 있음.",
    UnionBoardCellDefinitions:"현재 게임 진행에서 사용하지 않는 구형 보드.",
    UnionSpecialZoneDefinitions:"현재 게임 진행에서 사용하지 않는 구형 특수 구역."
  };
  const columns = {
    EnemyPatternSteps:{TileId:{label:"적 스킬 ID (TileId)",note:"타일이 아님. EnemySkillDefinitions.SkillId 참조.",ref:["EnemySkillDefinitions","SkillId"],optional:true}},
    UnionBoardCellDefinitions:{RegionId:{label:"보드 영역 (RegionId)",note:"GROWTH / COMBAT / CORE / EXPLORATION / TACTICS. RegionDefinitions와 관계없음.",ref:null}},
    RelicDefinitions:{IsOpen:{label:"유물 개방 (IsOpen)",note:"true: 획득 가능 / false: 상점·시작 추첨·지급 차단. 변경은 새 런부터 적용."},RequiredJobId:{ref:["JobDefinitions","JobId"],optional:true},EffectDescription:{label:"미사용 설명 (EffectDescription)",note:"런타임은 능력치와 특수 효과로 설명을 생성함.",readonly:true}},
    TopHudThemeDefinitions:{
      RegionId:{ref:["RegionDefinitions","RegionId"],allow:["default"]},
      BackdropColor:{label:"화면 미반영 (BackdropColor)",note:"테마 검증에서는 읽지만 배경 렌더링에는 적용하지 않음.",readonly:true},
      BackdropAlpha:{label:"화면 미반영 (BackdropAlpha)",note:"0~0.20 검증은 유지되지만 화면 배경에는 적용하지 않음.",readonly:true}
    },
    UnionStatLevelDefinitions:{StatId:{ref:["UnionStatDefinitions","StatId"]},RequiredUnionRank:{ref:["UnionRankDefinitions","RankId"]}},
    UnionUpgradeLevels:{UpgradeId:{ref:["UnionUpgradeDefinitions","UpgradeId"]},RequiredUpgradeId:{ref:["UnionUpgradeDefinitions","UpgradeId"],optional:true}},
    UnionStatDefinitions:{IsImplemented:{note:"ADDITIONAL_SKILL_UNLOCK은 규칙 미정으로 비활성. STARTING_RANDOM_RELIC은 현재 Repository에서 true로 보정됨. CSV 값만으로 구현 여부를 단정하지 마세요.",readonly:true}},
    UtilitySkillDefinitions:{
      RequiredJobTag:{ref:["JobDefinitions","JobId"]},
      EffectSetId:{ref:["UtilitySkillEffectSteps","EffectSetId"]},
      WeaponType:{ref:["WeaponDefinitions","WeaponType"],optional:true}
    },
    UtilitySkillEffectSteps:{EffectSetId:{ref:["UtilitySkillDefinitions","EffectSetId"]}}
  };
  function meta(name) {
    return {key:keys[name] || [], legacy:!!legacy[name], readonly:!!legacy[name] || !keys[name],
      note:legacy[name] || (keys[name] ? "명시된 키·참조 규칙만 검사합니다. 전체 게임 규칙은 Maker 콘텐츠 검증으로 확인하세요." : "스키마 미등록: 추론하지 않고 읽기 전용으로 표시합니다."),
      columns:columns[name] || {}};
  }
  function parseCSV(raw) {
    const bom=raw.startsWith("\uFEFF"), text=bom?raw.slice(1):raw;
    const newline=text.includes("\r\n")?"\r\n":text.includes("\r")?"\r":"\n";
    const trailing=/[\r\n]$/.test(text);
    let records=[], row=[], value="", quoted=false, closed=false;
    function cell(){row.push(value);value="";closed=false;}
    function record(){cell();records.push(row);row=[];}
    for(let i=0;i<text.length;i++){
      const c=text[i];
      if(quoted){
        if(c==='"'){if(text[i+1]==='"'){value+='"';i++;}else{quoted=false;closed=true;}}
        else value+=c;
      } else if(c==='"'){
        if(value!=="" || closed) throw Error("CSV: 잘못된 따옴표");
        quoted=true;
      } else if(c===',') cell();
      else if(c==='\n'||c==='\r'){record();if(c==='\r'&&text[i+1]==='\n')i++;}
      else {if(closed)throw Error("CSV: 닫는 따옴표 뒤의 문자");value+=c;}
    }
    if(quoted)throw Error("CSV: 닫히지 않은 따옴표");
    if(value!==""||row.length||closed)record();
    if(!records.length)throw Error("CSV: 헤더 없음");
    const headers=records.shift();
    if(headers.some(h=>!h)||new Set(headers).size!==headers.length)throw Error("CSV: 빈/중복 컬럼명");
    const rows=records.map((cells,i)=>{
      if(cells.length!==headers.length)throw Error("CSV: "+(i+2)+"행 컬럼 수 불일치");
      return Object.fromEntries(headers.map((h,j)=>[h,cells[j]]));
    });
    return {headers,rows,raw,bom,newline,trailing,dirty:false};
  }
  function serializeCSV(table) {
    if(!table.dirty && typeof table.raw==="string")return table.raw;
    const quote=v=>/[",\r\n]/.test(String(v))?'"'+String(v).replace(/"/g,'""')+'"':String(v);
    return (table.bom?"\uFEFF":"")+[table.headers,...table.rows.map(r=>table.headers.map(h=>r[h]??""))]
      .map(c=>c.map(quote).join(",")).join(table.newline||"\r\n")+(table.trailing?(table.newline||"\r\n"):"");
  }
  function numberOK(value,min,integer,optional=false) {
    if(value===""||value==null)return optional;
    return String(value).trim()!=="" && Number.isFinite(Number(value)) && Number(value)>=min && (!integer||Number.isInteger(Number(value)));
  }
  const utilityNumbers = [
    ["SchemaVersion",1,true],["Range",1,true],["CooldownTurns",0,true],["CostValue",0,false],
    ["ActionDuration",0.000001,false],["SkillTier",1,true],["EffectScale",0.000001,false,true],
    ["ProjectileSpeed",0,false,true],["ProjectileScale",0.000001,false,true],["ProjectileLaunchDelay",0,false,true],
    ["CasterMotionPlayRate",0.000001,false,true],["CasterMotionDuration",0.000001,false,true],
    ["EnemyQueueTurns",0,true,true],["ProjectileCount",1,true,true],["ProjectileInterval",0,false,true],["ProjectileHeight",0,false,true]
  ];
  function effectReason(d,s) {
    if(s.ConditionId)return "UTILITY_CONDITION_UNSUPPORTED";
    const a=s.ParameterA||"",b=s.ParameterB||"",v=Number(s.Value);
    if(s.EffectType==="GUARD"){
      if(d.TargetingType==="SELF"&&s.TargetSelector==="SELF_UNIT"&&v===0&&a==="UNTIL_NEXT_PLAYER_TURN"&&b==="ALL_DAMAGE")return "";
    } else if(s.EffectType==="MOVE_SELF"){
      if(d.TargetingType==="SELF"&&s.TargetSelector==="SELF_UNIT"){
        if(a==="FARTHEST_EMPTY_FORWARD"&&v===0&&b==="")return "";
        if(a==="BEHIND_FARTHEST_ENEMY_FORWARD"&&Number.isInteger(v)&&v>=1&&b==="REQUIRE_EMPTY")return "";
      }
    } else if(s.EffectType==="THROW_BEHIND"){
      if(d.TargetingType!=="SELF"&&s.TargetSelector==="PRIMARY_TARGET"&&Number.isInteger(v)&&v>=1&&b==="")return "";
    } else if(s.EffectType==="PUSH_DISTANCE"){
      if(d.TargetingType!=="SELF"&&["PRIMARY_TARGET","ALL_SKILL_TARGETS"].includes(s.TargetSelector)&&["","CARRY_CASTER"].includes(b)){
        if(a==="MAX"&&v===0)return "";
        if(a==="STOP_BEFORE_BLOCKED"&&Number.isInteger(v)&&v>=1)return "";
      }
    } else return "UNKNOWN_UTILITY_EFFECT";
    return "INVALID_UTILITY_EFFECT_PARAMETERS";
  }
  function validate(tables) {
    const issues=[];
    const add=(table,row,column,code)=>issues.push({table,row,column,code});
    for(const [name,t] of Object.entries(tables)){
      const m=meta(name),seen=new Set();
      for(const h of m.key) if(!t.headers.includes(h))add(name,1,h,"REQUIRED_KEY_COLUMN");
      t.rows.forEach((r,i)=>{
        const row=i+2;
        if(name==="RelicDefinitions" && !["true","false"].includes(r.IsOpen))add(name,row,"IsOpen","INVALID_RELIC_OPEN_FLAG");
        if(name==="EnemyPatternSteps"&&["EXECUTE_TILE","TELEGRAPH_TILE","CHARGE_FORWARD","CAST_INTERRUPTIBLE","BOSS_JUMP_TELEGRAPH","BOSS_LAND_OPPOSITE"].includes(r.ActionType)&&!r.TileId)add(name,row,"TileId","PATTERN_TILE_ID_MISSING");
        if(m.key.length){
          // Level is numeric in runtime; "01" and "1" must collide.
          const key=JSON.stringify(m.key.map(k=>k==="Level"?Number(r[k]):r[k]));
          if(m.key.some(k=>r[k]==null||r[k]===""))add(name,row,m.key.join("+"),"EMPTY_PRIMARY_KEY");
          else if(seen.has(key))add(name,row,m.key.join("+"),"DUPLICATE_PRIMARY_KEY");
          seen.add(key);
        }
        if(name==="UnionStatLevelDefinitions"||name==="UnionUpgradeLevels"){
          if(!numberOK(r.Level,1,true))add(name,row,"Level","INVALID_LEVEL");
        }
        for(const [col,rule] of Object.entries(m.columns)){
          if(!rule.ref)continue;
          const v=r[col], [target,key]=rule.ref;
          if((!v&&rule.optional)||(rule.allow||[]).includes(v))continue;
          if(!tables[target])add(name,row,col,"REFERENCE_TABLE_NOT_LOADED:"+target);
          else if(!tables[target].rows.some(x=>x[key]===v))add(name,row,col,"REFERENCE_NOT_FOUND:"+target+"."+key);
        }
      });
    }
    const defs=tables.UtilitySkillDefinitions, effects=tables.UtilitySkillEffectSteps;
    if(defs||effects){
      if(!defs||!effects) add("UtilitySkillDefinitions",0,"","UTILITY_DATA_MISSING");
      else {
        const seenJobs=new Set(),usedSets=new Set();
        defs.rows.forEach((d,i)=>{
          const fail=(col,code)=>add("UtilitySkillDefinitions",i+2,col,code);
          for(const [c,min,int,opt] of utilityNumbers)if(!numberOK(d[c],min,int,opt))fail(c,"INVALID_UTILITY_NUMBER");
          if(Number(d.SchemaVersion)!==1)fail("SchemaVersion","UNSUPPORTED_SKILL_SCHEMA");
          if(!d.DisplayName)fail("DisplayName","SKILL_DISPLAY_NAME_MISSING");
          if(seenJobs.has(d.RequiredJobTag))fail("RequiredJobTag","UTILITY_JOB_AMBIGUOUS");
          seenJobs.add(d.RequiredJobTag);usedSets.add(d.EffectSetId);
          for(const name of skillTables){
            if(!tables[name])fail("SkillId","REFERENCE_TABLE_NOT_LOADED:"+name);
            else if(tables[name].rows.some(r=>r.SkillId===d.SkillId))fail("SkillId","UTILITY_SKILL_ID_COLLISION");
          }
          if(!["SELF","FRONT_CELL","FIRST_ENEMY_FORWARD","RANGE_OFFSETS"].includes(d.TargetingType))fail("TargetingType","UNSUPPORTED_TARGETING_TYPE");
          if(d.TargetingType==="RANGE_OFFSETS"){
            const parts=(d.TargetOffsets||"").split("|"),nums=parts.map(Number);
            if(!parts.every(p=>p.trim()!=="")||nums.some(n=>!Number.isInteger(n)||n===0||Math.abs(n)>Number(d.Range))||new Set(nums).size!==nums.length)fail("TargetOffsets","INVALID_TARGET_OFFSETS");
          }
          if(d.CostType||Number(d.CostValue)!==0)fail("CostValue","UTILITY_COST_UNSUPPORTED");
          if(d.FreePlay!=="false")fail("FreePlay","UTILITY_FREE_PLAY_UNSUPPORTED");
          if(Number(d.SkillTier)!==1||d.BaseSkillId)fail("SkillTier","UTILITY_UPGRADE_UNSUPPORTED");
          if(d.ProjectileRuid)fail("ProjectileRuid","UTILITY_PROJECTILE_UNSUPPORTED");
          if(Number(d.ProjectileHeight)>0||Number(d.ProjectileCount)>1||Number(d.ProjectileInterval)>0)fail("ProjectileCount","PROJECTILE_WITHOUT_PROJECTILE");
          if(d.HudIconBackgroundColor&&!/^#[a-f0-9]{8}$/i.test(d.HudIconBackgroundColor))fail("HudIconBackgroundColor","INVALID_HUD_ICON_BACKGROUND_COLOR");
          if(d.CasterMotionRuid&&(!numberOK(d.CasterMotionPlayRate,0.000001,false)||!numberOK(d.CasterMotionDuration,0.000001,false)))fail("CasterMotionRuid","INVALID_CASTER_MOTION");
          const steps=effects.rows.filter(s=>s.EffectSetId===d.EffectSetId);
          if(steps.length!==1)fail("EffectSetId","UTILITY_EFFECT_COUNT_INVALID");
          else {const reason=effectReason(d,steps[0]);if(reason)fail("EffectSetId",reason);}
        });
        for(const j of tables.JobDefinitions?.rows||[])if(!seenJobs.has(j.JobId))add("UtilitySkillDefinitions",0,"RequiredJobTag","UTILITY_JOB_MISSING:"+j.JobId);
        effects.rows.forEach((s,i)=>{
          const fail=(col,code)=>add("UtilitySkillEffectSteps",i+2,col,code);
          if(Number(s.SchemaVersion)!==1)fail("SchemaVersion","UNSUPPORTED_EFFECT_SCHEMA");
          if(!numberOK(s.StepIndex,1,true)||Number(s.StepIndex)!==1)fail("StepIndex","INVALID_EFFECT_STEP_SEQUENCE");
          if(!numberOK(s.Value,0,true))fail("Value","INVALID_UTILITY_NUMBER");
          if(!usedSets.has(s.EffectSetId))fail("EffectSetId","ORPHAN_UTILITY_EFFECT_SET");
        });
      }
    }
    return issues;
  }
  return {meta,keys,legacy,columns,parseCSV,serializeCSV,validate,effectReason};
});
