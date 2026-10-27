"""Execute production mLua method bodies with native services replaced by small test doubles.

Requires Python + lupa (pip install lupa). ORBIS_LUA_PATH may point to an isolated installation.
This verifies Lua data/decisions, not Maker compilation, networking, physics or rendering.
"""
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.environ.get("ORBIS_LUA_PATH", str(ROOT / ".codex-artifacts/orbis-lua")))
from lupa.lua53 import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
files = {p.stem: p for p in (ROOT / "RootDesk/MyDesk").rglob("*.mlua")}
expected = json.loads((Path(__file__).parent / "expected-content.json").read_text(encoding="utf8"))


def lt(value):
    if isinstance(value, dict):
        return lua.table_from({k: lt(v) for k, v in value.items()})
    if isinstance(value, list):
        return lua.table_from([lt(v) for v in value])
    return value


def load(name, original=None):
    source = original if original is not None else files[name].read_text(encoding="utf-8-sig")
    code = ["local M={_T={}}"]
    for field, value in re.findall(r"^\s*(?:@Sync\s+)?property\s+\S+\s+(\w+)\s*=\s*([^\r\n]+)", source, re.M):
        code.append(f"M.{field}={value}")
    for match in re.finditer(r"^\tmethod\s+\S+\s+(\w+)\(([^\n]*)\)\r?\n(.*?)^\tend\s*$", source, re.M | re.S):
        method, signature, body = match.groups()
        args = ",".join(p.strip().split()[-1] for p in signature.split(",") if p.strip())
        code.append(f"function M:{method}({args})\n{body}\nend")
    code.append("return M")
    obj = lua.execute("\n".join(code), name=name)
    lua.globals()["_" + name] = obj
    return obj


lua.execute("""
function log(...) end
function log_warning(...) end
function log_error(...) end
function isvalid(e) return e ~= nil and e.valid ~= false end
function Vector2(x,y) return {x=x,y=y} end
function Vector3(x,y,z) return {x=x,y=y,z=z} end
function Color(r,g,b,a) return {r=r,g=g,b=b,a=a} end
function dataset(rows)
  return {rows=rows,GetRowCount=function(self) return #self.rows end,
    GetCell=function(self,i,k) return self.rows[i][k] end,
    FindRow=function(self,k,v) for _,r in ipairs(self.rows) do if r[k]==v then
      return setmetatable({GetItem=function(_,column) return r[column] end},{__index=r})
    end end end}
end
_DataService={Tables={}, GetTable=function(self,n) return self.Tables[n] end}
function entity(components)
  return {Name='test',components=components,GetComponent=function(self,n) return self.components[n] end}
end
""")
tables = {}
for p in (ROOT / "RootDesk/MyDesk/03_Data").glob("*.csv"):
    tables[p.stem] = list(csv.DictReader(p.open(encoding="utf-8-sig", newline="")))
    lua.globals()._DataService.Tables[p.stem] = lua.globals().dataset(lt(tables[p.stem]))

for name in ["SkillDefinitionRepositoryLogic", "ContentValidatorLogic", "BuffEffectExecutorLogic", "MoveSelfEffectExecutorLogic",
             "StageDefinitionRepositoryLogic", "RegionDefinitionRepositoryLogic", "RegionContentValidatorLogic", "StageMapRouteRepositoryLogic",
             "EnemyPatternStepRepositoryLogic", "EnemyPatternContentValidatorLogic", "BossPhaseDefinitionRepositoryLogic",
             "BossPhaseContentValidatorLogic", "EnemyTraitRouterLogic", "EnemyDefeatSuccessorLogic", "StageWaveRepositoryLogic", "EnemyIntentResolverLogic"]:
    load(name)

checks = []


def check(label, condition):
    assert condition, label
    checks.append(label)


def success(label, result):
    check(label + ": " + str(result["Reason"]) + "/" + str(result["DetailReason"]), result["Success"] is True)


repo = lua.globals()._StageWaveRepositoryLogic
validator = lua.globals()._ContentValidatorLogic
for row in tables["EnemySkillDefinitions"]:
    if row["SkillId"].startswith("orbis_"):
        success(row["SkillId"], validator.ValidateSkillById(validator, row["SkillId"]))
for m in expected["monsters"]:
    success(m["id"], repo.GetEnemyDefinition(repo, m["id"]))
for si, waves in enumerate(expected["rosters"], 1):
    stage = f"orbis_stage_{si:02}"
    success(stage, validator.ValidateStageById(validator, stage))
    check(stage + " wave count", repo.GetTotalWaveCount(repo, stage + "_waves") == len(waves))
    for wi, roster in enumerate(waves, 1):
        success(f"{stage}/{wi}", repo.GetWaveDefinition(repo, stage + "_waves", wi, 0))
        variants = set()
        for seed in range(3):
            variants.add(repo.GetSpawnVariantIndex(repo, stage, seed))
            variant_seed = repo.GetSpawnVariantSeed(repo, stage, seed)
            actual = []
            for slot in range(1, len(roster) + 1):
                spawn = repo.GetVariantEnemySpawnDefinition(repo, stage + f"_wave_{wi}", wi, slot, variant_seed)
                success(f"{stage}/{wi}/seed{seed}/slot{slot}", spawn)
                actual.append(spawn["EnemyDefinitionId"])
            check(f"{stage}/{wi}/variant{seed} exact roster", actual == ["orbis_" + key for key in roster])
        check(f"{stage}/{wi} three variants", variants == {1, 2, 3})

# Compare every legacy pool's deterministic rolls with the unchanged version in Git HEAD.
previous = subprocess.check_output(["git", "show", "HEAD:RootDesk/MyDesk/03_Data/Repositories/StageWaveRepositoryLogic.mlua"], cwd=ROOT).decode("utf-8-sig")
old = load("LegacyStageWaveRepositoryLogic", previous)
for pool in sorted({r["PoolId"] for r in tables["EnemySpawnPools"] if not r["PoolId"].startswith("orbis_")}):
    for wave in [1, 2, 3, 8]:
        for slot in [1, 2, 3]:
            for seed in [0, 1, 42, 104729, -77]:
                a, b = old.GetEnemyPoolEntry(old, pool, wave, slot, seed), repo.GetEnemyPoolEntry(repo, pool, wave, slot, seed)
                check(f"legacy/{pool}/{wave}/{slot}/{seed}", all(a[k] == b[k] for k in ["Success", "Reason", "EnemyDefinitionId", "SelectionRoll", "TotalWeight"]))
for invalid in ["-1", "0.5", "oops", "1e999", " "]:
    lua.globals()._DataService.Tables["EnemySpawnPools"] = lua.globals().dataset(lt([dict(PoolId="bad", SpawnIndex=invalid)]))
    check("invalid slot " + invalid, repo.GetEnemyPoolEntry(repo, "bad", 1, 1, 0)["Reason"] == "INVALID_POOL_SPAWN_INDEX")
lua.globals()._DataService.Tables["EnemySpawnPools"] = lua.globals().dataset(lt(tables["EnemySpawnPools"]))

# Exercise actual phase, plan and reinforcement methods; mock only entity/session services.
load("EnemyPatternRunnerComponent")
load("EnemyActionPlanComponent")
load("BossPhaseStateComponent")
load("EnemyPlanningLogic")
load("EnemyTurnExecutionLogic")
load("SkillTargetResolverLogic")
for key, hp in [("papa_pixie", 32), ("eliza", 48)]:
    lua.globals().boss_key, lua.globals().boss_hp = key, hp
    lua.execute("""
local runner=_EnemyPatternRunnerComponent
local plan=_EnemyActionPlanComponent
local phase=_BossPhaseStateComponent
runner.PatternId='';runner.PatternRevision=0
plan.PlanState='EMPTY';plan.SpawnWaitPending=false
phase.PhaseIndex=0;phase.PhaseId='';phase.PhaseRevision=0
local unit={UnitId='boss',IsBoss=true,IsDead=false,CellIndex=6,SpawnOrder=1}
local player=entity({['script.BattleUnitComponent']={UnitId='player_01',IsDead=false,CellIndex=3}})
local boss=entity({['script.BattleUnitComponent']=unit,['script.EnemyPatternRunnerComponent']=runner,
  ['script.EnemyActionPlanComponent']=plan,['script.BossPhaseStateComponent']=phase})
runner.Entity=boss;plan.Entity=boss;phase.Entity=boss
local session={StageTurnNumber=10,RunSeed=0,BattleResult='',spawned={},living={boss},
  FindUnitEntity=function(self,id) if id=='player_01' then return player end return boss end,
  PublishEnemyPlanSnapshot=function() end,NotifyBossPhaseAdvanced=function() end}
session.BoardState={CollectLivingEnemies=function() return session.living end}
session.WaveRuntime={GetAvailableSlots=function() return 1 end,SelectSpawnCell=function() return 0 end}
function session:SpawnWaveEnemy(id,cell,facing,order,spawn)
  local add=entity({['script.BattleUnitComponent']={UnitId=id,CellIndex=cell,IsBoss=false,IsDead=false}})
  table.insert(self.spawned,spawn);table.insert(self.living,add);return add
end
local map=entity({['script.BattleSessionComponent']=session});boss.CurrentMap=map
assert(phase:InitializePhases('orbis_'..boss_key,boss_hp,boss_hp).Success)
assert(phase.PhaseIndex==1)
local oldPattern=runner.PatternId
local oldSkill='orbis_'..boss_key..'_area'
assert(runner:TryMarkPrepared(oldPattern,3,4,'EXECUTE_TILE',0).Success)
assert(plan:ReplacePlan('boss',{{ActionType='EXECUTE_TILE',TileId=oldSkill,PatternId=oldPattern,StepIndex=3}},10,'','warning',1).Success)
assert(plan:LockTelegraphFollowUp().Success)
assert(plan:MarkAttackReady('warned','4|5').Success)
assert(phase:RefreshPhase(boss_hp/2+0.01,boss_hp,'ABOVE').Changed==false)
assert(phase:RefreshPhase(boss_hp/2,boss_hp,'THRESHOLD').Changed)
assert(phase.PhaseIndex==2)
assert(plan:GetCurrentAction().TileId==oldSkill and plan.TargetCellSnapshot=='4|5')
assert(plan.TelegraphLocked and plan.PlanState=='ATTACK_READY')
assert(phase.PendingPatternId=='orbis_'..boss_key..'_phase_02')
assert(runner.PatternId==oldPattern)
assert(_EnemyTurnExecutionLogic:CompleteEnemyPatternStep(session,'boss',oldPattern,3,true).Success)
assert(phase.PendingPatternId=='' and runner.PatternId==phase.PatternId)
assert(runner.CurrentStepIndex==1)
assert(not phase:RefreshPhase(boss_hp,boss_hp,'HEAL').Changed)
if boss_key=='papa_pixie' then
  assert(phase.NextReinforcementTurn==14)
  assert(phase:TrySpawnPhaseReinforcement(session).Reason=='REINFORCEMENT_COOLDOWN')
  session.StageTurnNumber=14
  assert(phase:TrySpawnPhaseReinforcement(session).Success and #session.spawned==1)
  session.StageTurnNumber=18
  assert(phase:TrySpawnPhaseReinforcement(session).Reason=='REINFORCEMENT_CAP')
  session.living={boss}
  assert(phase:TrySpawnPhaseReinforcement(session).Success and #session.spawned==2)
  unit.IsDead=true
  assert(phase:TrySpawnPhaseReinforcement(session).Reason=='BATTLE_ENDED')
else
  assert(phase:TrySpawnPhaseReinforcement(session).Reason=='PHASE_REINFORCEMENTS_DISABLED')
end

-- A phase threshold during TELEGRAPH_TILE must still lead to the original EXECUTE_TILE.
unit.IsDead=false;phase.PhaseIndex=0;phase.PhaseId='';phase.PendingPatternId='';plan:ResetPlan('TEST_RESET')
assert(phase:InitializePhases('orbis_'..boss_key,boss_hp,boss_hp).Success)
oldPattern=runner.PatternId
assert(runner:TryMarkPrepared(oldPattern,2,4,'TELEGRAPH_TILE',1).Success)
assert(plan:ReplacePlan('boss',{{ActionType='TELEGRAPH_TILE',TileId=oldSkill,PatternId=oldPattern,StepIndex=2}},10,'','warning',1).Success)
assert(phase:RefreshPhase(boss_hp/2,boss_hp,'DURING_WARNING').Changed)
assert(runner.PatternId==oldPattern and phase.PendingPatternId~='')
assert(_EnemyTurnExecutionLogic:CompleteEnemyPatternStep(session,'boss',oldPattern,2,true).Success)
assert(runner.CurrentStepIndex==3 and runner.PatternId==oldPattern)
assert(_EnemyPlanningLogic:IsTelegraphFollowUp(session,runner,oldPattern,oldSkill))
assert(runner:TryMarkPrepared(oldPattern,3,4,'EXECUTE_TILE',0).Success)
assert(_EnemyTurnExecutionLogic:CompleteEnemyPatternStep(session,'boss',oldPattern,3,false).Success)
assert(runner.PatternId==phase.PatternId and phase.PendingPatternId=='')

-- An explicit queue cancel releases the pending phase instead of replaying a cancelled warning.
phase.PhaseIndex=0;phase.PhaseId='';plan:ResetPlan('TEST_RESET')
assert(phase:InitializePhases('orbis_'..boss_key,boss_hp,boss_hp).Success)
oldPattern=runner.PatternId
assert(runner:TryMarkPrepared(oldPattern,2,4,'TELEGRAPH_TILE',1).Success)
assert(plan:ReplacePlan('boss',{{ActionType='TELEGRAPH_TILE',TileId=oldSkill,PatternId=oldPattern,StepIndex=2}},10,'','warning',1).Success)
assert(phase:RefreshPhase(boss_hp/2,boss_hp,'BEFORE_CANCEL').Changed)
assert(_EnemyTurnExecutionLogic:CancelEnemyQueuedSkills(session,'boss','TEST_CANCEL').Success)
assert(phase.PendingPatternId=='' and runner.PatternId==phase.PatternId)

-- Also cover the gap after the warning completed but before a follow-up plan exists.
phase.PhaseIndex=0;phase.PhaseId='';plan:ResetPlan('TEST_RESET')
assert(phase:InitializePhases('orbis_'..boss_key,boss_hp,boss_hp).Success)
oldPattern=runner.PatternId
assert(runner:TryMarkPrepared(oldPattern,2,4,'TELEGRAPH_TILE',1).Success)
assert(_EnemyTurnExecutionLogic:CompleteEnemyPatternStep(session,'boss',oldPattern,2,true).Success)
assert(phase:RefreshPhase(boss_hp/2,boss_hp,'AFTER_WARNING').Changed)
assert(runner.PatternId==oldPattern and phase.PendingWarningSkillId==oldSkill)
assert(runner:TryMarkPrepared(oldPattern,3,4,'EXECUTE_TILE',0).Success)
assert(_EnemyTurnExecutionLogic:CompleteEnemyPatternStep(session,'boss',oldPattern,3,true).Success)
assert(phase.PendingPatternId=='' and runner.PatternId==phase.PatternId)

-- Use the production targeting resolver for both facings and every player cell, including evasion.
unit.Team='Enemy';unit.CellIndex=3;player.components['script.BattleUnitComponent'].Team='Player'
function session:IsValidCell(cell) return cell>=0 and cell<7 end
function session.BoardState:FindAtCell(cell,ignored)
  if player.components['script.BattleUnitComponent'].CellIndex==cell then return player end
end
for _,facing in ipairs({'Left','Right'}) do
  unit.Facing=facing
  local dir=facing=='Right' and 1 or -1
  for _,suffix in ipairs({'area','area_enraged'}) do
    local skill=_SkillDefinitionRepositoryLogic:GetSkillDefinition('orbis_'..boss_key..'_'..suffix)
    local reach=boss_key=='papa_pixie' and 1 or (suffix=='area' and 2 or 3)
    for cell=0,6 do
      player.components['script.BattleUnitComponent'].CellIndex=cell
      local target=_SkillTargetResolverLogic:Resolve(session,'boss',skill)
      local offset=(cell-3)*dir
      local hit=boss_key=='papa_pixie' and math.abs(offset)==1 or boss_key=='eliza' and offset>=1 and offset<=reach
      assert((#target.TargetUnitIds>0)==hit, boss_key..' '..suffix..' '..facing..' cell='..cell)
    end
  end
end
""")
    check(key + " threshold/monotonic phase/frozen warning/follow-up/cancel/targeting/reinforcement", True)

# Existing bosses still switch immediately when no warning is committed.
legacy_bosses = sorted({r["EnemyDefinitionId"] for r in tables["BossPhaseDefinitions"] if not r["EnemyDefinitionId"].startswith("orbis_")})
for enemy_id in legacy_bosses:
    lua.globals().legacy_enemy_id = enemy_id
    lua.execute("""
local phase=_BossPhaseStateComponent
local runner=_EnemyPatternRunnerComponent
phase.PhaseIndex=0;phase.PhaseId='';phase.PendingPatternId='';phase.PendingWarningSkillId=''
local unit={IsDead=false}
local session={StageTurnNumber=0,PublishEnemyPlanSnapshot=function() end,NotifyBossPhaseAdvanced=function() end}
local boss=entity({['script.BattleUnitComponent']=unit,['script.EnemyPatternRunnerComponent']=runner})
boss.CurrentMap=entity({['script.BattleSessionComponent']=session})
phase.Entity=boss;runner.Entity=boss
assert(phase:InitializePhases(legacy_enemy_id,100,100).Success, legacy_enemy_id)
for _,definition in ipairs(phase.Definitions) do
  assert(phase:RefreshPhase(definition.HpRatioLE*100-0.000001,100,'REGRESSION').Success)
  assert(phase.PhaseIndex==definition.PhaseIndex,legacy_enemy_id..' phase='..definition.PhaseIndex..' actual='..phase.PhaseIndex)
  assert(runner.PatternId==definition.PatternId and unit.EnemyPatternId==definition.PatternId)
  assert(phase.PendingPatternId=='')
end
""")
    check(enemy_id + " existing phase transitions", True)

load("BattleUnitComponent")
load("EnemySpecialEffectExecutorLogic")
lua.execute("""
local unit=_BattleUnitComponent
unit:InitializeBattleState('player_01','Player',3,'Right',50,0)
local player=entity({['script.BattleUnitComponent']=unit})
unit.Entity=player
local source=entity({['script.BattleUnitComponent']={Team='Enemy',IsDead=false}})
local special=_EnemySpecialEffectExecutorLogic
local session={FindUnitEntity=function(self,id) return id=='player_01' and player or source end,
  IsTeamTurn=function(self,team) return team=='Enemy' end,
  IsHostileStatusEffect=function(self,kind) return special:IsHostileStatusEffect(kind) end,
  GetPlayerStatusUnit=function() return unit end}
local context={SourceUnitId='source',PrimaryTargetUnitId='player_01',TargetUnitIds={'player_01'}}
for _,key in ipairs({'fire_stoneball','ice_stoneball'}) do
  unit:ClearBattleBuffs()
  local skill=_SkillDefinitionRepositoryLogic:GetSkillDefinition('orbis_'..key..'_attack')
  local bundle=_SkillDefinitionRepositoryLogic:GetEffectSteps(skill.EffectSetId)
  local step=nil
  for _,effect in ipairs(bundle.Steps or bundle) do if effect.EffectType=='IGNITE' or effect.EffectType=='FROSTBITE' then step=effect end end
  assert(step,'missing authored hostile effect '..key)
  assert(special:ExecuteEnemySpecialEffect(session,context,step).Hit)
  if key=='fire_stoneball' then
    assert(unit.BurnDamage==1 and unit.BurnTurns==2)
    assert(special:ExecuteEnemySpecialEffect(session,context,step).Hit)
    assert(unit.BurnDamage==1 and unit.BurnTurns==2,'burn refresh must not stack')
    unit:AdvanceNegativeStatusTurns();assert(unit.BurnDamage==1 and unit.BurnTurns==1)
    unit:AdvanceNegativeStatusTurns();assert(unit.BurnDamage==0 and unit.BurnTurns==0)
  else
    assert(unit.FrostbiteTurns==1 and special:IsPlayerFrostbitten(session))
    for i=2,3 do assert(special:ExecuteEnemySpecialEffect(session,context,step).Reason=='CONTROL_RESISTED') end
    assert(unit.FrostbiteTurns==1,'three ice sentinels must not stack duration')
    unit:AdvanceNegativeStatusTurns();assert(unit.FrostbiteTurns==0 and not special:IsPlayerFrostbitten(session))
  end
  unit:ClearBattleBuffs()
  assert(not special:ExecuteEnemySpecialEffect(session,{SourceUnitId='source',TargetUnitIds={}},step).Hit)
  assert(unit.BurnDamage==0 and unit.FrostbiteTurns==0,'empty impact must not apply status')
  source.components['script.BattleUnitComponent'].IsDead=true
  assert(not special:ExecuteEnemySpecialEffect(session,context,step).Success)
  source.components['script.BattleUnitComponent'].IsDead=false
end
""")
check("tower authored ignite/frostbite: apply, refresh/resist three hits, expiry, empty impact, dead source", True)

report = {"result": "PASS", "checks": len(checks), "stages": len(expected["rosters"]), "waves": sum(map(len, expected["rosters"])), "monsters": len(expected["monsters"]),
          "legacyBosses": len(legacy_bosses),
          "luaVersion": "5.3",
          "scope": "Actual Lua repository/validator/phase/plan methods with service doubles; not Maker runtime",
          "maker": "Tracked separately in tower-maker-verification.json"}
(Path(__file__).parent / "lua-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
print(json.dumps(report, ensure_ascii=False))
