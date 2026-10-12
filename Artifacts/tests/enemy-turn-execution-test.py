"""Execute actual enemy-turn mLua methods with deterministic service/timer boundaries."""
import os
from pathlib import Path
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime
from battle_refactor_fixture import wire_logic_owners

ROOT = Path(__file__).resolve().parents[2]
COMBAT = ROOT / "RootDesk/MyDesk/01_Combat"
SHARED = COMBAT / "Components/Shared"
METHOD = re.compile(r"^\tmethod\s+\w+\s+(\w+)\(([^)]*)\)\n(.*?)^\tend$", re.M | re.S)
lua = LuaRuntime(unpack_returned_tuples=True)
wire_logic_owners(lua)


def load(path, names=None):
    result = lua.table()
    for name, parameters, body in METHOD.findall(path.read_text(encoding="utf-8-sig")):
        if names is None or name in names:
            args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
            result[name] = lua.eval("function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend")
    if names is not None:
        assert set(result.keys()) == names
    return result


def component(name):
    path = SHARED / (name + ".mlua")
    defaults = lua.table()
    for key, value in re.findall(r"^\t(?:@Sync )?property \w+ (\w+) = (.+)$", path.read_text(), re.M):
        defaults[key] = lua.eval(value)
    return lua.eval("function(methods, defaults) return function() local t={} for k,v in pairs(defaults) do t[k]=v end return setmetatable(t,{__index=methods}) end end")(load(path), defaults)


g = lua.globals()
g._EnemyTurnExecutionLogic = load(COMBAT / "Resolvers/EnemyTurnExecutionLogic.mlua")
names = set(g._EnemyTurnExecutionLogic.keys())
assert len(names) == 20
g.Session = load(Path(os.environ.get("ORIGINAL_SESSION", SHARED / "BattleSessionComponent.mlua")),
                 names | {"GetPreparedEnemyIntent", "ResetEnemyIntentCursor", "ClearTurnTransitionTimer"})
g._EnemyTraitRouterLogic = load(COMBAT / "Resolvers/EnemyTraitRouterLogic.mlua")
g._EnemyIntentResolverLogic = load(COMBAT / "Resolvers/EnemyIntentResolverLogic.mlua")
for name in ("EnemyActionPlanComponent", "EnemyIntentComponent", "EnemyPatternRunnerComponent", "BattleTurnComponent"):
    g[name] = component(name)

lua.execute(r'''
function isvalid(v) return v~=nil and v.Valid~=false end
function log(_) end
log_warning=log; log_error=log
local timers,nextTimer,step,definition
_TimerService={SetTimerOnce=function(_,callback,delay)
    nextTimer=nextTimer+1; timers[nextTimer]={Callback=callback,Delay=delay}; return nextTimer
end,ClearTimer=function(_,id) timers[id]=nil end}
function fire(id) local t=assert(timers[id]); timers[id]=nil; t.Callback() end
_EnemyPatternStepRepositoryLogic={GetPatternStep=function() return {Success=true,Step=step,StepCount=2} end}
_ContentValidatorLogic={ValidateSkillById=function() return definition end}
_TutorialRulesLogic={GetEnemyExecuteDelay=function(_,s,queue,id,delay) assert(s.Entities and id=='enemy'); return delay end,
    GetEnemyBeatDuration=function(_,s,action,delay) assert(s.Entities); return delay end,
    OnEnemyRoundCompleted=function(_,s) assert(s.Entities); s.TutorialCompletions=s.TutorialCompletions+1 end}
setmetatable(_EnemyTurnExecutionLogic,{__newindex=function(_,key) error('shared execution state: '..key) end})

function fixture(kind,tile,traits,actions)
    timers={}; nextTimer=0
    step={ActionType=kind or 'WAIT',ParamA='2',NextStepOnSuccess=2,NextStepOnFailure=1}
    definition={Success=true,Data={Definition={CasterMotionDuration=.4,ActionDuration=.8,MotionProfileId='motion'}}}
    local plan,runner,intent,turn=EnemyActionPlanComponent(),EnemyPatternRunnerComponent(),EnemyIntentComponent(),BattleTurnComponent()
    local u={UnitId='enemy',CellIndex=1,Facing='Right',SpawnOrder=1,EnemyTraitIds=traits or '',StopActionTurns=0,IsDead=false,BurnDamage=0}
    local p={CellIndex=3,Facing='Right',IsDead=false}
    local parts={['script.BattleUnitComponent']=u,['script.EnemyActionPlanComponent']=plan,['script.EnemyPatternRunnerComponent']=runner}
    local entity={Name='Enemy',GetComponent=function(_,key) return parts[key] end}; runner.Entity=entity
    local s=setmetatable({_T={},Entity={},Entities={enemy=entity,player_01={GetComponent=function() return p end}},
        EnemyIntentRuntime=intent,TurnState=turn,BattleResult='',TurnNumber=4,CurrentWave=1,EntryRequestId=8,
        LastEnemySpawnOrder=0,PreparedEnemyId='',ActionTimerId=0,TurnTransitionTimerId=0,SkillTestMode=false,
        PlayerToEnemyBeatPending=false,PendingPlayerToEnemyHandoffDelay=-1,EnemyToEnemyHandoffPending=false,
        PendingEnemyHandoffSourceId='',PendingEnemyHandoffActionType='',PlayerToEnemyBeatDuration=.1,
        PlayerPresentationSettledBeatDuration=.02,QueuePopDuration=.11,EnemyToEnemyBeatDuration=.04,
        QuickEnemyToEnemyBeatDuration=.02,EnemyThinkDuration=.2,EnemyToPlayerBeatDuration=.04,
        EnemyMoveActionDuration=.2,TurnActionDuration=.1,MoveCompletionFallbackGrace=.1,
        Publications={},Executions={},RoundCompletions=0,TutorialCompletions=0,NextEnemy=false}, {__index=Session})
    function s:FindUnitEntity(id) return self.Entities[id] end
    function s:EnsureEnemyIntentComponent() return self.EnemyIntentRuntime end
    function s:PublishEnemyIntentSnapshot(reason) self.PreparedEnemyId=intent.EnemyId; table.insert(self.Publications,reason) end
    function s:PublishEnemyPlanSnapshot(reason) table.insert(self.Publications,reason) end
    function s:PublishTurnStateSnapshot(reason) self.TurnNumber=turn.TurnNumber; table.insert(self.Publications,reason) end
    function s:PrepareNextEnemyIntent() return {Success=self.NextEnemy,Reason='NO_NEXT_LIVING_ENEMY'} end
    function s:AdvanceEnemySkillCooldowns() end
    function s:AdvanceConsumedPlayerActionEffects(reason) self.PlayerCompletion=reason end
    function s:PrepareEnemyIntent() self.RoundCompletions=self.RoundCompletions+1 end
    function s:AdvancePlayerSkillCooldowns() end
    function s:ProcessAugmentTrigger() end
    function s:EvaluateForcedSpawnAtTurnBoundary() end
    function s:GetSkillActionDuration() return .8 end
    function s:HasSkillProjectile() return self.Projectile==true end
    function s:GetSkillSpeedMultiplier() return 2 end
    function s:GetSkillMotionProfile() return {ImpactDelay=.3} end
    function s:BeginMotionCompletionWait(callback) self.CompleteAction=callback; return 1 end
    function s:SealMotionCompletionWhenImpactsFinish(sequence) assert(sequence==1); self.Sealed=true end
    function s:MarkMotionCompletionReady(sequence) assert(sequence==1); self.CompleteAction() end
    function s:FinishEnemyGridMovePresentation(reason,complete)
        local m=self._T.enemyGridMove; self._T.enemyGridMove=nil
        if m then _TimerService:ClearTimer(m.TimerId); if complete then m.CompleteAction() end end
    end
    local function result(self,kind,...)
        table.insert(self.Executions,{Kind=kind,Args={...}})
        return self.ActionResult or {Success=true,Reason='OK'}
    end
    function s:TryMoveInternal(...) return result(self,'MOVE',...) end
    function s:TryMoveAwayInternal(...) return result(self,'AWAY',...) end
    function s:TryFaceDirection(id,direction) u.Facing=direction==1 and 'Right' or 'Left'; return result(self,'TURN',id,direction) end
    function s:TryExecuteSkill(...) return result(self,'SKILL',...) end
    function s:TryChargeForward(...) return result(self,'CHARGE',...) end
    function s:BeginBossOppositeJump(...) return result(self,'JUMP',...) end
    function s:ResolveBossOppositeLanding(...) return result(self,'LAND',...) end
    function s:ApplyStatusDamage() u.IsDead=true end
    s.BoardState={CollectLivingEnemies=function() return {entity} end}
    turn:OpenPlayerTurn(4,'FIXTURE'); turn:BeginEnemyTurn('ENEMY_WAIT',0,'FIXTURE')
    assert(runner:InitializePattern('pattern',1).Success)
    assert(runner:TryMarkPrepared('pattern',1,2,kind or 'WAIT',0).Success)
    local first={ActionType=kind or 'WAIT',TileId=tile or '',Direction=1,PatternId='pattern',StepIndex=1,Reason='FIXTURE'}
    assert(plan:ReplacePlan('enemy',actions or {first},4,traits or '', 'FIXTURE',0).Success)
    if plan.PlanState=='INSERTING' then assert(plan:AdvanceQueueTurn().Success) end
    if plan.PlanState=='TRACKING' then assert(plan:MarkAttackReady('READY','2').Success) end
    assert(s:LoadEnemyPlanActionToCompatibility('enemy').Success)
    return s,plan,runner,u,p,parts
end
function finish(s) fire(s.ActionTimerId); if s.TurnTransitionTimerId>0 then fire(s.TurnTransitionTimerId) end end
local count=0
function case(name,check) check(); count=count+1; print('PASS '..name) end

case('missing intent and plan preserve rejection reasons',function()
    local s=fixture(); s.EnemyIntentRuntime:ResetIntent('RESET'); s:ExecutePreparedEnemyIntent()
    assert(s.TurnTransitionTimerId>0 and #s.Executions==0)
    local parts; s,_,_,_,_,parts=fixture(); parts['script.EnemyActionPlanComponent']=nil
    s:ExecutePreparedEnemyIntent(); assert(s.TurnTransitionTimerId>0 and #s.Executions==0)
end)
case('movement dispatch and completion consume a pattern once',function()
    for _,kind in ipairs({'MOVE_TOWARD','MOVE_AWAY','MOVE_FIXED_FACING'}) do
        local s,plan,runner=fixture(kind); s:ExecutePreparedEnemyIntent(); assert(#s.Executions==1 and s.Sealed)
        assert(plan.PlanState=='EXECUTING'); local callback=s.CompleteAction; finish(s); callback()
        assert(plan.PlanState=='COMPLETED' and runner.CurrentStepIndex==2 and s.RoundCompletions==1)
    end
end)
case('turning before movement leaves the movement and pattern prepared',function()
    local s,plan,runner,u=fixture('MOVE_TOWARD'); u.Facing='Left'; s:ExecutePreparedEnemyIntent(); finish(s)
    assert(s.Executions[1].Kind=='TURN' and plan.PlanState=='PREPARED' and runner.PreparedStepIndex==1)
end)
case('tracking consumes a turn without consuming the committed skill',function()
    local s,plan,runner=fixture('EXECUTE_TILE','slash'); plan.PlanState='TRACKING'
    plan.NextCommandType='MOVE_TOWARD'; plan.NextCommandDirection=1
    s:LoadEnemyPlanActionToCompatibility('enemy'); s:ExecutePreparedEnemyIntent(); finish(s)
    assert(s.Executions[1].Kind=='MOVE' and plan.PlanState=='TRACKING' and runner.PreparedStepIndex==1 and plan.TargetCellSnapshot=='2')
end)
case('only spatial blocks become successful waits',function()
    local s=fixture(); for _,reason in ipairs({'OUT_OF_BOUNDS','CELL_OCCUPIED'}) do
        local r=s:ConvertBlockedEnemyMoveToWait('enemy','MOVE_TOWARD',1,{Success=false,Reason=reason,FromCell=1,ToCell=2})
        assert(r.Success and r.WasBlocked and r.Reason=='WAIT_'..reason and r.ToCell==2)
    end
    local r={Success=false,Reason='PHASE_REJECTED'}; assert(s:ConvertBlockedEnemyMoveToWait('enemy','MOVE_TOWARD',1,r)==r)
end)
case('movement frame completion and fallback cannot finish twice',function()
    for _,fallback in ipairs({false,true}) do
        local s,plan=fixture('MOVE_TOWARD'); local m={UnitId='enemy',Duration=.2,TimerId=0}; s._T.enemyGridMove=m
        s.ActionResult={Success=true,Reason='OK',PresentationStarted=true}; s:ExecutePreparedEnemyIntent()
        local callback=m.CompleteAction; assert(timers[m.TimerId].Delay==.3 or math.abs(timers[m.TimerId].Delay-.3)<1e-9)
        if fallback then fire(m.TimerId) else s:FinishEnemyGridMovePresentation('VISUAL_COMPLETE',true) end
        callback(); assert(plan.PlanState=='COMPLETED'); fire(s.TurnTransitionTimerId); assert(s.RoundCompletions==1)
    end
end)
case('cast interruption does not resurrect its telegraph or execute a skill',function()
    local s,plan=fixture('EXECUTE_TILE','slash')
    assert(s:BeginEnemyInterruptibleCast('enemy','pattern',1,'slash').Success and plan.InterruptHitsRequired==2)
    plan:RegisterInterruptHit('slash','1'); plan:RegisterInterruptHit('slash','2')
    local before=#s.Publications; local cast=s:ConsumeEnemyInterruptibleCast('enemy','slash')
    assert(not cast.CanExecute and #s.Publications==before)
    plan:BeginInterruptibleCast('slash',1); plan:RegisterInterruptHit('slash','3')
    s:ExecutePreparedEnemyIntent(); finish(s); assert(#s.Executions==0)
end)
case('summon collaborator receives the owning session',function()
    local s,_,_,_,_,parts=fixture('SUMMON_ENEMIES')
    parts['script.FaustSummonComponent']={TryPreparedSummon=function(_,owner,cells) assert(owner==s and cells==''); return {Success=false,Reason='BLOCKED'} end}
    s:ExecutePreparedEnemyIntent(); assert(s.TurnState.QueuedActionType=='ENEMY_WAIT'); finish(s)
end)
case('charge and boss actions dispatch and lethal burn suppresses the action',function()
    for _,kind in ipairs({'CHARGE_FORWARD','BOSS_JUMP_TELEGRAPH','BOSS_LAND_OPPOSITE'}) do
        local s=fixture(kind); s:ExecutePreparedEnemyIntent(); assert(#s.Executions==1); finish(s)
    end
    local s,_,runner,u=fixture('CHARGE_FORWARD'); u.BurnDamage=1
    s:ExecutePreparedEnemyIntent(); finish(s); assert(#s.Executions==0 and runner.CurrentStepIndex==1)
end)
case('ready skill uses its presentation boundary and frozen target',function()
    local s,plan=fixture('EXECUTE_TILE','slash'); s.ActionResult={Success=true,Reason='MISS',PresentationHandoffDuration=.01}
    s:ExecutePreparedEnemyIntent(); assert(s.Executions[1].Kind=='SKILL' and timers[s.ActionTimerId].Delay==.01 and plan.TargetCellSnapshot=='2'); finish(s)
end)
case('post attack movement defers to the next round',function()
    local actions={{ActionType='WAIT',PatternId='pattern',StepIndex=1,Reason='OK'},
        {ActionType='MOVE_AWAY',PatternId='pattern',StepIndex=1,Reason='POST_ATTACK_RETREAT'}}
    local s,plan,runner=fixture('WAIT',nil,nil,actions); s:ExecutePreparedEnemyIntent(); finish(s)
    assert(plan.PlanState=='PREPARED' and plan.CurrentActionIndex==2 and plan.DeferredUntilTurn==5 and runner.PreparedStepIndex==1)
end)
case('replacement patterns cannot be advanced by an old frozen action',function()
    local s,_,runner=fixture(); runner:InitializePattern('replacement',1)
    assert(s:CompleteEnemyPatternStep('enemy','pattern',1,true).Reason=='PATTERN_SUPERSEDED' and runner.CurrentStepIndex==1)
end)
case('spawn wait consumes only its one time flag',function()
    local s,plan,runner=fixture('WAIT',nil,nil,{{ActionType='WAIT',PatternId='pattern',StepIndex=1,Reason='SPAWN_WAIT'}})
    s:ExecutePreparedEnemyIntent(); finish(s); assert(not plan.SpawnWaitPending and runner.PreparedStepIndex==1)
end)
case('queue cancellation releases the cursor and runner, execution rejects cancellation',function()
    local s,plan,runner=fixture('EXECUTE_TILE','slash'); local r=s:CancelEnemyQueuedSkills('enemy','UTILITY_CANCEL')
    assert(r.Success and r.CancelledSkillIds=='slash' and plan.PlanState=='EMPTY' and runner.PreparedStepIndex==0 and s.EnemyIntentRuntime.IntentState=='EMPTY')
    s,plan=fixture('EXECUTE_TILE','slash'); plan:TryBeginCurrentAction()
    assert(s:CancelEnemyQueuedSkills('enemy','UTILITY_CANCEL').Reason=='PLAN_EXECUTING')
end)
case('round reset cancels movement, all frozen plans and cursor',function()
    local s,plan,runner=fixture('MOVE_TOWARD'); s._T.enemyGridMove={TimerId=0}
    s:ClearPreparedEnemyIntent('MAP_LEAVE')
    assert(s._T.enemyGridMove==nil and plan.PlanState=='EMPTY' and runner.PreparedStepIndex==0 and s.EnemyIntentRuntime.IntentState=='EMPTY')
end)
case('begin turn preserves insertion and control status semantics',function()
    local s,plan,runner=fixture('EXECUTE_TILE','slash'); plan.PlanState='INSERTING'; plan.QueueTurnsElapsed=0
    s:BeginEnemyTurn(); assert(s.TurnState.QueuedActionType=='ENEMY_QUEUE_TILE'); fire(s.ActionTimerId)
    assert(plan.QueueTurnsElapsed==1 and runner.PreparedStepIndex==1)
    local u; s,plan,runner,u=fixture(); u.StopActionTurns=1; s:BeginEnemyTurn(); fire(s.ActionTimerId)
    assert(u.StopActionTurns==0 and #s.Executions==0 and runner.PreparedStepIndex==1)
end)
case('handoff cadence remains bounded and training still advances a turn',function()
    local s=fixture(); s:BeginEnemyTurnFromPlayerAction('SKILL_QUEUED'); assert(timers[s.ActionTimerId].Delay==.11 and s.PlayerCompletion=='SKILL_QUEUED')
    s=fixture(nil,nil,'QUICK'); s:BeginEnemyTurnFromEnemyAction('previous','WAIT'); assert(timers[s.ActionTimerId].Delay==.02)
    s=fixture(); s.SkillTestMode=true; s:BeginEnemyTurn(); fire(s.TurnTransitionTimerId)
    assert(s.TurnNumber==5 and #s.Executions==0 and s.TutorialCompletions==1)
end)
case('duplicate and stale round timers cannot reopen a different turn or entry',function()
    for _,stale in ipairs({'entry','turn','phase','none'}) do
        local s=fixture(); s:CompleteEnemyTurn('WAIT',true,'OK'); local id=s.TurnTransitionTimerId
        s:CompleteEnemyTurn('WAIT',true,'OK'); assert(s.TurnTransitionTimerId==id and nextTimer==1)
        if stale=='entry' then s.EntryRequestId=9 elseif stale=='turn' then s.TurnState.TurnNumber=10 elseif stale=='phase' then s.TurnState.BattlePhase='PlayerTurn' end
        fire(id); assert(s.RoundCompletions==(stale=='none' and 1 or 0))
    end
end)
case('transition cleanup and ended battles never reopen the player phase',function()
    local s=fixture(); s:CompleteEnemyTurn('WAIT',true,'OK'); local id=s.TurnTransitionTimerId
    s:ClearTurnTransitionTimer('SESSION_END'); assert(timers[id]==nil and s.TurnTransitionTimerId==0)
    s.BattleResult='Victory'; s:CompleteEnemyTurn('WAIT',true,'OK'); assert(s.RoundCompletions==0 and nextTimer==1)
end)
case('duration and relative direction preserve existing policy',function()
    local s,_,_,u,p=fixture(); assert(s:GetEnemySkillPresentationReadyDuration('slash')==.3)
    s.Projectile=true; assert(s:GetEnemySkillPresentationReadyDuration('slash')==.8)
    definition={Success=false}; assert(s:GetEnemySkillPresentationReadyDuration('slash')==.8)
    assert(s:ResolveEnemyRelativeMoveDirection('enemy','MOVE_AWAY')==-1)
    p.CellIndex=0; assert(s:ResolveEnemyRelativeMoveDirection('enemy','MOVE_TOWARD')==-1)
    p.CellIndex=u.CellIndex; assert(s:ResolveEnemyRelativeMoveDirection('enemy','MOVE_TOWARD')==0)
end)
case('two sessions own independent completion callbacks and timers',function()
    local a=fixture('MOVE_TOWARD'); local b=fixture('MOVE_AWAY')
    a:ExecutePreparedEnemyIntent(); b:ExecutePreparedEnemyIntent(); a.CompleteAction()
    assert(b.EnemyIntentRuntime.IntentState=='EXECUTING' and b.TurnTransitionTimerId==0)
    assert(a.TurnTransitionTimerId>0 and rawget(_EnemyTurnExecutionLogic,'session')==nil)
end)
print('All '..count..' enemy turn execution groups passed (mock execution).')
''')
