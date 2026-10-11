"""Run enemy planning against real mLua resolvers and enemy-owned state components."""
import os
from pathlib import Path
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
COMBAT = ROOT / "RootDesk/MyDesk/01_Combat"
lua = LuaRuntime(unpack_returned_tuples=True)
METHOD = re.compile(r"^\tmethod\s+\w+\s+(\w+)\(([^)]*)\)\n(.*?)^\tend$", re.M | re.S)
NAMES = {"BuildEnemyIntent", "BuildEnemyCellFreeSnapshot", "IsPatternCellFree", "PrepareEnemyIntent",
         "PrepareNextEnemyIntent", "PrepareEnemyIntentForUnit", "IsTelegraphFollowUp", "RefreshQueuedAttackReadiness"}


def load(path, names=None):
    methods = lua.table()
    for name, parameters, body in METHOD.findall(path.read_text(encoding="utf-8-sig")):
        if names is None or name in names:
            args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
            methods[name] = lua.eval("function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend")
    if names is not None:
        assert set(methods.keys()) == names
    return methods


def component(name):
    path = COMBAT / "Components/Shared" / (name + ".mlua")
    methods = load(path)
    defaults = lua.table()
    for key, value in re.findall(r"^\t(?:@Sync )?property \w+ (\w+) = (.+)$", path.read_text(), re.M):
        defaults[key] = lua.eval(value)
    return lua.eval("function(methods, defaults) return function() local t={} for k,v in pairs(defaults) do t[k]=v end return setmetatable(t,{__index=methods}) end end")(methods, defaults)


g = lua.globals()
g._EnemyPlanningLogic = load(COMBAT / "Resolvers/EnemyPlanningLogic.mlua", NAMES)
g.Session = load(COMBAT / "Components/Shared/BattleSessionComponent.mlua", NAMES - {
    "BuildEnemyCellFreeSnapshot", "IsPatternCellFree", "IsTelegraphFollowUp"})
if os.environ.get("ORIGINAL_SESSION"):
    g.Session = load(Path(os.environ["ORIGINAL_SESSION"]), NAMES)
g._EnemyIntentResolverLogic = load(COMBAT / "Resolvers/EnemyIntentResolverLogic.mlua")
g._EnemyTraitRouterLogic = load(COMBAT / "Resolvers/EnemyTraitRouterLogic.mlua")
g.Plan = component("EnemyActionPlanComponent")
g.Runner = component("EnemyPatternRunnerComponent")

lua.execute(r'''
function isvalid(v) return v~=nil and v.Valid~=false end
function log(_) end
function log_warning(_) end
function log_error(_) end
local definitions,patterns={},{}
_SkillDefinitionRepositoryLogic={GetSkillDefinition=function(_,id) return definitions[id] or {Success=false,Reason='MISSING_SKILL'} end}
_EnemyPatternContentValidatorLogic={ValidateById=function(_,id) return patterns[id] or {Success=false,Reason='MISSING_PATTERN'} end}
_EnemyPatternStepRepositoryLogic={GetPatternStep=function(_,id,index)
    local p=patterns[id]; local step=p and p.Data and p.Data.Steps[index]
    return {Success=step~=nil,Step=step}
end}
_SkillTargetResolverLogic={BuildOffsets=function(_,kind,range,offsets)
    if kind=='INVALID' then return {Success=false,Reason='INVALID_OFFSETS'} end
    local cells={}; for i=1,range do table.insert(cells,i) end
    return {Success=true,Values=cells}
end}
_EnemyTelegraphLogic={BuildSkillAreaTelegraph=function(_,session,unit,id)
    return {Success=true,TargetCells=tostring(unit.CellIndex+(unit.Facing=='Right' and 1 or -1))}
end,BuildChargeTelegraph=function() return {Success=true,TargetCells='2|3'} end}
_TutorialRulesLogic={PrepareEnemyPlan=function(_,s) return s.TutorialResult end}
setmetatable(_EnemyPlanningLogic,{__newindex=function(_,k) error('shared planning state: '..k) end})

function fixture(traits)
    definitions={slash={Success=true,EnemyQueueTurns=1,TargetingType='FIRST_ENEMY_FORWARD',Range=1},
        special={Success=true,EnemyQueueTurns=2,TargetingType='FIRST_ENEMY_FORWARD',Range=2}}
    patterns={pattern={Success=true,Data={Steps={
        {StepIndex=1,ActionType='EXECUTE_TILE',TileId='slash',ConditionType='ALWAYS',NextStepOnSuccess=0,NextStepOnFailure=0}
    }}}}
    local plan,runner=Plan(),Runner()
    plan.SpawnWaitPending=false
    local unit={UnitId='enemy',CellIndex=1,Facing='Right',IsDead=false,IsBoss=false,IsAirborne=false,
        EnemyTraitIds=traits or '',EnemyPatternId='pattern',EnemyMovementPolicy='TRACK_PLAYER',CurrentHp=5,MaxHp=5,SpawnOrder=1}
    local player={UnitId='player_01',CellIndex=2,Facing='Left',IsDead=false}
    local parts={['script.BattleUnitComponent']=unit,['script.EnemyActionPlanComponent']=plan,['script.EnemyPatternRunnerComponent']=runner}
    local enemy={Name='Enemy',GetComponent=function(_,k) return parts[k] end}; runner.Entity=enemy
    assert(runner:InitializePattern('pattern',1).Success)
    local p={GetComponent=function() return player end}
    local enemies={enemy}
    local runtime={Cooldowns={},CanUseSkill=function(self,id) return {Success=not self.Cooldowns[id],RemainingTurns=self.Cooldowns[id] or 0} end}
    local s=setmetatable({BattleResult='',TurnNumber=4,CellCount=6,LastEnemySpawnOrder=0,SkillTestMode=false,
        PreparedEnemyId='',CursorState='EMPTY',EnemyPlanRevision=0,Entities={enemy=enemy,player_01=p},Publications={},ParityRolls=0}, {__index=Session})
    s.BoardState={CollectLivingEnemies=function() return enemies end,FindAtCell=function(_,cell,ignored)
        for _,e in ipairs(enemies) do local u=e:GetComponent('script.BattleUnitComponent'); if not u.IsDead and u.CellIndex==cell and u.UnitId~=ignored then return e end end
        return cell==player.CellIndex and ignored~='player_01' and p or nil
    end}
    function s:FindUnitEntity(id) return self.Entities[id] end
    function s:IsValidCell(cell) return cell>=0 and cell<self.CellCount end
    function s:CanSkeletonSwapWithCommander() return false end
    function s:GetSkillRuntimeState() return runtime end
    function s:GetOppositeEdgeCell(cell) return cell<3 and 5 or 0 end
    function s:RollBoardParity() self.ParityRolls=self.ParityRolls+1 end
    function s:ResetEnemyIntentCursor() self.PreparedEnemyId=''; self.CursorState='EMPTY' end
    function s:GetPreparedEnemyIntent() return {State=self.CursorState} end
    function s:LoadEnemyPlanActionToCompatibility(id) self.PreparedEnemyId=id; self.CursorState='PREPARED'; return {Success=true,Reason='SELECTED'} end
    function s:PublishEnemyPlanSnapshot(reason) table.insert(self.Publications,reason); self.EnemyPlanRevision=self.EnemyPlanRevision+1 end
    function s:ResolveEnemyRelativeMoveDirection(id,kind) local u=self.Entities[id]:GetComponent('script.BattleUnitComponent'); local dir=player.CellIndex>u.CellIndex and 1 or -1; return kind=='MOVE_AWAY' and -dir or dir end
    return s,plan,runner,unit,player,parts,runtime,enemies
end
function case(name,check) check(); print('PASS '..name) end
function queued(s,plan) assert(s:PrepareEnemyIntentForUnit('enemy').Success); assert(plan:AdvanceQueueTurn().Success) end

case('spawn wait leaves pattern and skills untouched',function()
    local s,plan,runner=fixture('QUICK'); plan.SpawnWaitPending=true
    assert(s:PrepareEnemyIntentForUnit('enemy').Success)
    assert(plan:GetCurrentAction().ActionType=='WAIT' and runner.PreparedStepIndex==0 and plan.QueueTurnsRequired==0)
end)
case('missing, dead and invalid-pattern failures preserve their reasons',function()
    local s,_,_,unit,_,parts=fixture(); s.Entities.enemy=nil
    assert(s:BuildEnemyIntent('enemy').Reason=='UNIT_MISSING')
    s,_,_,unit,_,parts=fixture(); unit.IsDead=true
    assert(s:PrepareEnemyIntentForUnit('enemy').Reason=='UNIT_UNAVAILABLE')
    unit.IsDead=false; parts['script.EnemyPatternRunnerComponent']=nil
    assert(s:BuildEnemyIntent('enemy').Reason=='PATTERN_RUNNER_MISSING')
    s=fixture(); patterns.pattern={Success=false,Reason='REJECTED'}
    assert(s:BuildEnemyIntent('enemy').Reason=='PATTERN_INVALID_REJECTED')
end)
case('definition changes resync the runner and cooldowns follow authored failure links',function()
    local s,_,runner,_,_,_,runtime=fixture(); runner.PatternId='obsolete'
    patterns.pattern.Data.Steps={{StepIndex=1,ActionType='EXECUTE_TILE',TileId='special',ConditionType='ALWAYS',NextStepOnFailure=2},
        {StepIndex=2,ActionType='EXECUTE_TILE',TileId='slash',ConditionType='ALWAYS'}}
    runtime.Cooldowns.special=2
    local intent=s:BuildEnemyIntent('enemy'); assert(intent.TileId=='slash' and intent.StepIndex==2 and runner.PatternId=='pattern')
end)
case('ordinary insertion and QUICK retain existing preparation timing',function()
    local s,plan,runner=fixture(); assert(s:PrepareEnemyIntentForUnit('enemy').Success)
    assert(plan.PlanState=='INSERTING' and runner.PreparedStepIndex==1 and plan.PlannedActionCount==2)
    plan:AdvanceQueueTurn(); assert(s:RefreshQueuedAttackReadiness('enemy').Readiness=='READY')
    assert(plan.PlanState=='ATTACK_READY' and plan.TargetCellSnapshot=='2')
    s,plan=fixture('QUICK'); assert(s:PrepareEnemyIntentForUnit('enemy').Success and plan.PlanState=='ATTACK_READY' and plan.QueueTurnsRequired==0)
end)
case('authored retreat removes only the automatic recovery duplicate',function()
    local s,plan=fixture(); patterns.pattern.Data.Steps[2]={StepIndex=2,ActionType='MOVE_AWAY',TileId='',ConditionType='ALWAYS'}
    assert(s:PrepareEnemyIntentForUnit('enemy').Success and plan.PlannedActionCount==1)
end)
case('missing skill and readiness failures cancel the prepared step',function()
    local s,plan,runner=fixture(); definitions.slash=nil
    assert(s:PrepareEnemyIntentForUnit('enemy').Reason=='QUEUE_SKILL_MISSING' and runner.PreparedStepIndex==0)
    s,plan,runner=fixture('QUICK'); definitions.slash.TargetingType='INVALID'
    assert(s:PrepareEnemyIntentForUnit('enemy').Reason=='INVALID_OFFSETS' and runner.PreparedStepIndex==0 and plan.PlanState=='EMPTY')
end)
case('readiness retains cooldown wait, turn, approach and blocked commands',function()
    local s,plan,_,unit,player,_,runtime=fixture(); queued(s,plan); player.CellIndex=4
    assert(s:RefreshQueuedAttackReadiness('enemy').Readiness=='NEEDS_MOVE' and plan.NextCommandType=='MOVE_TOWARD')
    unit.Facing='Left'; assert(s:RefreshQueuedAttackReadiness('enemy').Readiness=='NEEDS_TURN')
    runtime.Cooldowns.slash=3; assert(s:RefreshQueuedAttackReadiness('enemy').RemainingTurns==3 and plan.NextCommandType=='WAIT')
    runtime.Cooldowns.slash=nil; unit.Facing='Right'; s.BoardState.FindAtCell=function() return {} end
    assert(s:RefreshQueuedAttackReadiness('enemy').Readiness=='BLOCKED')
end)
case('living allies block attack lines while bosses keep their exception',function()
    local s,plan,_,unit,player,_,_,enemies=fixture(); queued(s,plan); definitions.slash.Range=3; player.CellIndex=4
    table.insert(enemies,{GetComponent=function() return {UnitId='ally',CellIndex=2,IsDead=false} end})
    assert(s:RefreshQueuedAttackReadiness('enemy').Reason=='ALLY_IN_LINE' and plan.PlanState=='TRACKING')
    unit.IsBoss=true; assert(s:RefreshQueuedAttackReadiness('enemy').Readiness=='READY')
end)
case('HOLD_POSITION and warned follow-ups commit without approaching',function()
    local s,plan,_,_,player=fixture('HOLD_POSITION'); queued(s,plan); player.CellIndex=5
    assert(s:RefreshQueuedAttackReadiness('enemy').Reason=='READY_HOLD_POSITION' and plan.PlanState=='ATTACK_READY')
    local runner; s,plan,runner,_,player=fixture()
    patterns.pattern.Data.Steps[2]={StepIndex=2,ActionType='TELEGRAPH_TILE',TileId='slash',ConditionType='ALWAYS'}
    runner.LastCompletedStepIndex=2; runner.LastCompletionSuccess=true; player.CellIndex=5
    assert(s:PrepareEnemyIntentForUnit('enemy').Success and plan.TelegraphLocked and plan.PlanState=='ATTACK_READY')
    assert(plan.ReadinessReason=='TELEGRAPH_LOCKED' and plan.TargetCellSnapshot=='2')
end)
case('charge cells and board parity are fixed during preparation',function()
    local s,plan=fixture(); patterns.pattern.Data.Steps[1].ActionType='CHARGE_FORWARD'
    assert(s:PrepareEnemyIntentForUnit('enemy').Success and plan.TargetCellSnapshot=='2|3')
    s,plan=fixture(); definitions.slash.TargetingType='BOARD_PARITY'
    assert(s:PrepareEnemyIntentForUnit('enemy').Success and s.ParityRolls==1)
end)
case('summon collaborators receive the owning session and store their preview on the enemy',function()
    local s,plan,_,_,_,parts=fixture()
    patterns.pattern.Data.Steps[1]={StepIndex=1,ActionType='SUMMON_ENEMIES',TileId='',ConditionType='SUMMON_READY'}
    parts['script.FaustSummonComponent']={PrioritizeSummon=true,
        CanSummon=function(_,owner,edge) assert(owner==s and edge==5); return true end,
        PrepareSummon=function(_,owner,edge) assert(owner==s and edge==5); return '5|4' end}
    assert(s:PrepareEnemyIntentForUnit('enemy').Success and plan.TargetCellSnapshot=='5|4')
end)
case('round freezing preserves ready attacks and selects deferred enemies in order',function()
    local s,plan,runner,_,player,_,_,enemies=fixture('QUICK'); assert(s:PrepareEnemyIntent().PreparedCount==1)
    local revision=plan.PlanRevision; player.CellIndex=5
    assert(s:PrepareEnemyIntent().Success and plan.PlanRevision==revision and plan.TargetCellSnapshot=='2' and runner.PreparedStepIndex==1)
    s:ResetEnemyIntentCursor(); plan.DeferredUntilTurn=5; assert(s:PrepareNextEnemyIntent().Reason=='NO_NEXT_LIVING_ENEMY')
    s.TurnNumber=5; assert(s:PrepareNextEnemyIntent().Success)
    assert(s:PrepareNextEnemyIntent().Reason=='INTENT_ALREADY_PREPARED')
    s:ResetEnemyIntentCursor(); s.LastEnemySpawnOrder=1; assert(s:PrepareNextEnemyIntent().Reason=='NO_NEXT_LIVING_ENEMY')
    local other,otherPlan,_,otherUnit=fixture('QUICK')
    assert(other:PrepareEnemyIntentForUnit('enemy').Success); otherUnit.UnitId='later'; otherUnit.SpawnOrder=2
    table.insert(enemies,other.Entities.enemy)
    assert(s:PrepareNextEnemyIntent().Success and s.PreparedEnemyId=='later' and otherPlan.PlanState=='ATTACK_READY')
end)
case('training, tutorial and ended battle gates leave unrelated state alone',function()
    local s,plan,runner=fixture(); s.SkillTestMode=true
    assert(s:PrepareEnemyIntent().PreparedCount==0 and plan.PlanState=='EMPTY' and runner.PreparedStepIndex==0)
    s.SkillTestMode=false; s.TutorialResult={Success=true,Reason='TUTORIAL_PLAN'}
    assert(s:PrepareEnemyIntentForUnit('enemy').Reason=='TUTORIAL_PLAN' and runner.PreparedStepIndex==0)
    s.TutorialResult=nil; s.BattleResult='Victory'
    assert(s:PrepareEnemyIntentForUnit('enemy').Reason=='BATTLE_ENDED' and s:PrepareNextEnemyIntent().Reason=='BATTLE_ENDED')
end)
case('alternating sessions share code but never plans or cursor state',function()
    local a,pa=fixture('QUICK'); local b,pb=fixture()
    assert(a:PrepareEnemyIntent().Success and pa.PlanState=='ATTACK_READY' and pb.PlanState=='EMPTY')
    assert(b:PrepareEnemyIntent().Success and pb.PlanState=='INSERTING' and pa.TargetCellSnapshot=='2')
    assert(rawget(_EnemyPlanningLogic,'session')==nil and rawget(_EnemyPlanningLogic,'BoardState')==nil)
end)
''')
