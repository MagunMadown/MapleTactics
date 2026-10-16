"""Run with Python + lupa installed; executes production mLua repository method bodies."""
import csv, io, json, os, re, subprocess, sys
from pathlib import Path
if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
BASE = "48baef800fa2bd8e922a1fc6dc56ea59a02c567d"
PREFIX = "RootDesk/MyDesk/03_Data/Repositories/"
def source(name, baseline=False):
    p = PREFIX + name + ".mlua"
    if baseline:
        return subprocess.check_output(["git", "show", BASE + ":" + p], cwd=ROOT).decode("utf-8-sig")
    return (ROOT/p).read_text(encoding="utf-8-sig")
def load(lua, text, name):
    lua.execute(name + " = {_T={}}")
    for typ, key, value in re.findall(r"^\s*property (\w+) (\w+) = ([^\n]+)", text, re.M):
        lua.execute(name + "." + key + " = " + value)
    methods = re.findall(r"^\tmethod \w+ (\w+)\(([^\n]*)\)\n(.*?)^\tend", text, re.M|re.S)
    assert methods, name
    for key, args, body in methods:
        names = ",".join(a.strip().split()[-1] for a in args.split(",") if a.strip())
        lua.execute("function " + name + ":" + key + "(" + names + ")\n" + body + "\nend")
    return lua.globals()[name]
def plain(value):
    if hasattr(value, "items"):
        return {k:plain(v) for k,v in value.items()}
    return value
def environment(baseline=False):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
      reads=0; tables={}
      function log(...) end
      function log_warning(...) end
      function log_error(...) end
      _DataService={}
      function _DataService:GetTable(name) return tables[name] end
      function dataset(rows)
        return {rows=rows, GetRowCount=function(self) return #self.rows end,
          GetCell=function(self,i,key) reads=reads+1; return self.rows[i][key] end}
      end
    """)
    for path in (ROOT/"RootDesk/MyDesk/03_Data").glob("*.csv"):
        rows=list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
        lua.globals().tables[path.stem]=lua.globals().dataset(lua.table_from([lua.table_from(r) for r in rows]))
    skill=load(lua,source("SkillDefinitionRepositoryLogic",baseline),"skill")
    pattern=load(lua,source("EnemyPatternStepRepositoryLogic",baseline),"pattern")
    return lua,skill,pattern

old,oskill,opattern=environment(True)
new,nskill,npattern=environment()
counts={"definitions":0,"effects":0,"patterns":0,"steps":0}
names=list(plain(nskill.GetSkillDataSetNames(nskill)).values())
for name in names:
    for _, row in new.globals().tables[name].rows.items():
        skill_id=row.SkillId
        assert plain(oskill.GetSkillDefinition(oskill,skill_id))==plain(nskill.GetSkillDefinition(nskill,skill_id)),skill_id
        counts["definitions"]+=1
effect_ids={r.EffectSetId for _,r in new.globals().tables.SkillEffectSteps.rows.items()}
for effect_id in effect_ids:
    assert plain(oskill.GetEffectSteps(oskill,effect_id))==plain(nskill.GetEffectSteps(nskill,effect_id)),effect_id
    counts["effects"]+=1
pattern_ids={r.PatternId for _,r in new.globals().tables.EnemyPatternSteps.rows.items()}
for pattern_id in pattern_ids:
    before=opattern.GetPatternSteps(opattern,pattern_id)
    after=npattern.GetPatternSteps(npattern,pattern_id)
    assert plain(before)==plain(after),pattern_id
    counts["patterns"]+=1
    for _,step in after.Steps.items():
        assert plain(opattern.GetPatternStep(opattern,pattern_id,step.StepIndex))==plain(npattern.GetPatternStep(npattern,pattern_id,step.StepIndex))
        counts["steps"]+=1

new.execute("""
  local id = tables.WarriorSkillDefinitions.rows[1].SkillId
  local def = skill:GetSkillDefinition(id)
  local effectId = def.EffectSetId
  local baseRange = def.Range
  def.Range = 99999
  assert(skill:GetSkillDefinition(id).Range == baseRange, "definition copy isolation")
  skill:SetTestDefinitionOverride(id, "Range", 17)
  assert(skill:GetSkillDefinition(id).Range == 17, "live override")
  skill.TestOverridesSuspended = true
  assert(skill:GetSkillDefinition(id).Range == baseRange, "export suspension")
  skill.TestOverridesSuspended = false
  skill:ClearTestOverridesForSkill(id, effectId)
  assert(skill:GetSkillDefinition(id).Range == baseRange, "override removal")
  local effects = skill:GetEffectSteps(effectId)
  local value = effects.Steps[1].Value
  local index = effects.Steps[1].StepIndex
  effects.Steps[1].Value = 99999
  assert(skill:GetEffectSteps(effectId).Steps[1].Value == value, "effect copy isolation")
  skill:SetTestEffectOverride(effectId, index, "Value", 77)
  assert(skill:GetEffectSteps(effectId).Steps[1].Value == 77)
  skill:ClearTestOverridesForSkill(id, effectId)
  assert(skill:GetEffectSteps(effectId).Steps[1].Value == value)
  local patternId = tables.EnemyPatternSteps.rows[1].PatternId
  local bundle = pattern:GetPatternSteps(patternId)
  local stepIndex = bundle.Steps[1].StepIndex
  local action = bundle.Steps[1].ActionType
  bundle.Steps[1].ActionType = "BROKEN"
  local step = pattern:GetPatternStep(patternId, stepIndex)
  assert(step.Step.ActionType == action, "pattern copy isolation")
  step.Step.ActionType = "BROKEN"
  assert(pattern:GetPatternStep(patternId,stepIndex).Step.ActionType == action)

  reads=0
  for i=1,1000 do
    skill:GetSkillDefinition(id)
    skill:GetEffectSteps(effectId)
    pattern:GetPatternStep(patternId,stepIndex)
  end
  assert(reads == 0, "warm lookups must not read CSV cells")

  local original = tables.WarriorSkillDefinitions.rows[1].Range
  tables.WarriorSkillDefinitions.rows[1].Range = "37"
  skill:InvalidateCache()
  assert(skill:GetSkillDefinition(id).Range == 37, "explicit refresh")
  tables.WarriorSkillDefinitions.rows[1].Range = original
  skill:OnEndPlay()
  skill:OnBeginPlay()
  assert(skill:GetSkillDefinition(id).Range == baseRange, "session invalidation")

  -- Duplicate definitions and steps stay visible to ContentValidator.
  table.insert(tables.WarriorSkillDefinitions.rows, tables.WarriorSkillDefinitions.rows[1])
  skill:InvalidateCache()
  assert(skill:GetSkillDefinition(id).MatchCount == 2, "duplicate definition lost")
  local previous = #pattern:GetPatternSteps(patternId).Steps
  table.insert(tables.EnemyPatternSteps.rows, tables.EnemyPatternSteps.rows[1])
  pattern:InvalidateCache()
  assert(#pattern:GetPatternSteps(patternId).Steps == previous+1, "duplicate step lost")
  local previousEffects = #skill:GetEffectSteps(effectId).Steps
  for _,r in ipairs(tables.SkillEffectSteps.rows) do
    if r.EffectSetId == effectId then
      table.insert(tables.SkillEffectSteps.rows,r)
      break
    end
  end
  skill:InvalidateCache()
  assert(#skill:GetEffectSteps(effectId).Steps == previousEffects+1, "duplicate effect lost")

  local prior = tables.WarriorSkillDefinitions
  tables.WarriorSkillDefinitions = dataset({{SkillId="replacement",Range="8"}})
  assert(skill:GetSkillDefinition("replacement").Range==8, "dataset identity change")
  tables.WarriorSkillDefinitions = prior
  skill.JobSkillDataSetNames = "Missing"
  assert(skill:GetSkillDefinition(id).Success == false, "dataset name change")
  assert(skill:GetSkillDefinition("").Reason == "INVALID_SKILL_ID")
  assert(pattern:GetPatternStep("",1).Reason == "INVALID_PATTERN_ID")
  assert(pattern:GetPatternStep("missing",1).Reason == "PATTERN_NOT_FOUND")
""")
print(json.dumps({"status":"PASS","equivalent":counts,"warm_queries":3000,"warm_cell_reads":0,"mutation_override_duplicate_refresh_checks":"PASS"}))
