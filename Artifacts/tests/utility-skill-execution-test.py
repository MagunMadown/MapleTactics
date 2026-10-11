"""Replay actual utility methods before/after extraction; engine/displacement boundaries are mocks."""
import os
from pathlib import Path
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
COMBAT = ROOT / "RootDesk/MyDesk/01_Combat"
METHOD = re.compile(r"^\tmethod\s+\w+\s+(\w+)\(([^)]*)\)\n(.*?)^\tend$", re.M | re.S)
lua = LuaRuntime(unpack_returned_tuples=True)


def load(path, names=None):
    result = lua.table()
    for name, parameters, body in METHOD.findall(path.read_text(encoding="utf-8-sig")):
        if names is None or name in names:
            args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
            result[name] = lua.eval("function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend")
    if names is not None:
        assert set(result.keys()) == names
    return result


g = lua.globals()
g.Session = load(Path(os.environ.get("ORIGINAL_SESSION", COMBAT / "Components/Shared/BattleSessionComponent.mlua")), {
    "RequestUtilitySkill", "TryUseUtilitySkill", "ExecuteUtilityEffect", "ApplyFairyTurnCollisionStun",
})
g._UtilitySkillExecutionLogic = load(COMBAT / "Skills/UtilitySkillExecutionLogic.mlua")
g.Turn = load(COMBAT / "Components/Shared/BattleTurnComponent.mlua", {"TryReserveImmediateAction", "IncrementStateRevision"})
g.Runtime = load(COMBAT / "Components/Shared/SkillRuntimeStateComponent.mlua", {
    "CanUseSkill", "GetRemainingCooldown", "EnsureCooldownTable", "StartCooldown", "StartPlayerCooldown",
})

lua.execute(r'''
function log(_) end
log_warning=log; log_error=log
function isvalid(v) return v~=nil and v.Valid~=false end
local timers,nextTimer,bundle
_TimerService={SetTimerOnce=function(_,fn,delay)
    if timerUnavailable then return 0 end
    nextTimer=nextTimer+1; timers[nextTimer]={Callback=fn,Delay=delay}; return nextTimer
end}
function fire(id) local t=assert(timers[id]); timers[id]=nil; t.Callback() end
_SkillDefinitionRepositoryLogic={GetUtilitySkillBundle=function(_,job) lastJob=job; return bundle end}
_TutorialRulesLogic={IsUtilityAllowed=function(_,s) return not s.TutorialEffectBlocked end,
    OnUtilityUsed=function(_,s) table.insert(s.Trace,'tutorial') end}
_EnemyTraitRouterLogic={BlocksForcedDisplacement=function(_,traits) return traits=='HEAVY' end}
_SkillTargetResolverLogic={Resolve=function(_,s) return s.TargetFailure or s.Targets end}
setmetatable(_UtilitySkillExecutionLogic,{__newindex=function(_,key) error('shared utility state: '..key) end})

function fixture(effect)
    timers={}; nextTimer=0; timerUnavailable=false
    local d={SkillId='utility',IconRuid='icon',CooldownTurns=4,ActionDuration=.5,
        HitEffectRuid='',HitSoundRuid='',EffectScale=1}
    local step={EffectType=effect or 'GUARD',TargetSelector='SELF_UNIT',Value=0,
        ParameterA='UNTIL_NEXT_PLAYER_TURN',ParameterB='ALL_DAMAGE'}
    bundle={Success=true,Definition=d,Step=step}
    local s=setmetatable({Entity={},EntryRequestId=7,CellCount=6,BattlePhase='PlayerTurn',BattleResult='',
        SelectedJobId='warrior',SkillTestMode=false,SkillTestUtilityJobId='',UtilitySkillId='',
        ActionTimerId=0,Trace={},Completions={},Moves={},Pushes={},Cancels={},Visuals={},Units={}}, {__index=Session})
    local turn=setmetatable({BattlePhase='PlayerTurn',IsActionProcessing=false,QueuedActionType='',
        QueuedActionDirection=0,QueuedTileIds='attack|heal',TurnNumber=2,StateRevision=0}, {__index=Turn})
    local runtime=setmetatable({RemainingCooldowns={},FreshPlayerCooldowns={},Entity={Name='player'}}, {__index=Runtime})
    function runtime:RefreshCooldownSnapshot() table.insert(s.Trace,'cooldown') end
    s.TurnState=turn; s.Runtime=runtime
    function s:add(id,team,cell)
        local u={UnitId=id,Team=team,CellIndex=cell,Facing='Right',IsDead=false,IsAirborne=false,
            PreviousSkillWasAttack=true,BurnDamage=0,BurnSourceUnitId='enemy',StopActionTurns=0,
            StopMarkerRuid='',EnemyTraitIds=''}
        local parts={['script.BattleUnitComponent']=u,
            ['script.BattleUnitPresentationComponent']={PlaySkillEffect=function(_,id) table.insert(s.Visuals,id) end,
                PlaySkillSound=function() end},
            ['script.PlayerRunRelicEffectComponent']={OnSkillCompleted=function() table.insert(s.Trace,'relic') end}}
        local e={CurrentMap=s.Entity,PlayerComponent={UserId='owner'},GetComponent=function(_,name) return parts[name] end}
        u.Entity=e; s.Units[id]=u
        return u,parts
    end
    local p,parts=s:add('player_01','Player',2); local e=s:add('enemy','Enemy',3)
    s.PlayerEntity=p.Entity
    s.Targets={Success=true,PrimaryTargetUnitId='enemy',TargetUnitIds={'enemy'},TargetCellsByUnitId={enemy=3}}
    s.BoardState={FindAtCell=function(_,cell,exclude)
        for id,u in pairs(s.Units) do if id~=exclude and u.CellIndex==cell and not u.IsDead and not u.IsAirborne then return u.Entity end end
    end}
    function s:IsValidCell(cell) return cell>=0 and cell<self.CellCount end
    function s:IsCellOccupied(cell,id) return self.BoardState:FindAtCell(cell,id)~=nil end
    function s:FindUnitEntity(id) return self.Units[id] and self.Units[id].Entity end
    function s:IsTutorialCommandAllowed() return not self.TutorialBlocked end
    function s:IsPlayerSealed() return self.Sealed==true end
    function s:IsPlayerFrostbitten() return self.Frostbitten==true end
    function s:GetSkillRuntimeState() if not self.MissingRuntime then return runtime end end
    function s:GetSkillSpeedMultiplier() return 2 end
    function s:GetSkillSoundVolume() return .8 end
    function s:CompleteQueuedAction(action,success,reason)
        table.insert(self.Completions,{Success=success,Reason=reason}); table.insert(self.Trace,'complete')
        turn.QueuedActionType=''; turn.IsActionProcessing=false; self.ActionTimerId=0
    end
    function s:BeginSkillEffectPresentation() table.insert(self.Trace,'cast') end
    function s:PublishTurnStateSnapshot() table.insert(self.Trace,'snapshot') end
    function s:PublishPlayerCommandResult(_,result) self.Receipt=result end
    function s:ApplyStatusDamage() table.insert(self.Trace,'burn'); if self.BurnLethal then p.IsDead=true end end
    function s:RelocateUnitForMechanic(id,cell)
        if self.RelocationFailure then return self.RelocationFailure end
        table.insert(self.Moves,{Id=id,Cell=cell}); self.Units[id].CellIndex=cell
        return {Success=true,Reason='RELOCATED'}
    end
    function s:TryFaceDirection(id,dir) self.Units[id].Facing=dir==1 and 'Right' or 'Left'; self.FaceCalls=(self.FaceCalls or 0)+1 end
    function s:ResolvePushImpactOnTarget(_,id)
        table.insert(self.Pushes,id)
        if self.PushResult then return self.PushResult end
        local u=self.Units[id]; local cell=u.CellIndex+(p.Facing=='Right' and 1 or -1)
        if not self:IsValidCell(cell) then return {Success=true,Reason='PUSH_BLOCKED_OUT_OF_BOUNDS',ToCell=cell} end
        if self:IsCellOccupied(cell,id) then return {Success=true,Reason='PUSH_BLOCKED_OCCUPIED',ToCell=cell} end
        u.CellIndex=cell; return {Success=true,Reason='PUSHED',ToCell=cell}
    end
    function s:CancelEnemyQueuedSkills(id,reason) table.insert(self.Cancels,id); return {Success=true} end
    function s:HasSkillProjectile() return self.Projectile==true end
    function s:GetProjectileLaunchDelay() return .1 end
    function s:LaunchSkillProjectile(_,_,delay) self.LaunchCell=e.CellIndex; return .2 end
    return s,p,e,d,step,parts
end
function cast(s) return s:TryUseUtilitySkill() end
function move(step,mode) step.EffectType='MOVE_SELF'; step.ParameterA=mode; step.ParameterB='REQUIRE_EMPTY' end
function push(step) step.EffectType='PUSH_DISTANCE'; step.TargetSelector='PRIMARY_TARGET'; step.ParameterA='STOP_BEFORE_BLOCKED'; step.ParameterB=''; step.Value=2 end
local count=0
function case(name,check) check(); count=count+1; print('PASS '..name) end

case('RPC ownership and map checks reject without changing state',function()
    local s,p=fixture(); senderUserId='forged'; s:RequestUtilitySkill(); assert(s.Receipt==nil and not p.UtilityGuardActive)
    senderUserId='owner'; p.Entity.CurrentMap={}; s:RequestUtilitySkill(); assert(s.Receipt==nil)
    p.Entity.CurrentMap=s.Entity; s:RequestUtilitySkill(); assert(s.Receipt.Success and p.UtilityGuardActive)
end)
case('tutorial, seal, phase, dead and airborne gates precede reservation',function()
    for key,reason in pairs({TutorialBlocked='TUTORIAL_FOLLOW_GUIDE',Sealed='PLAYER_SEALED'}) do
        local s=fixture(); s[key]=true; assert(cast(s).Reason==reason and not s.TurnState.IsActionProcessing)
    end
    local s,p=fixture(); s.BattlePhase='EnemyTurn'; assert(cast(s).Reason=='INVALID_PHASE')
    s.BattlePhase='PlayerTurn'; p.IsDead=true; assert(cast(s).Reason=='UNIT_UNAVAILABLE'); p.IsDead=false; p.IsAirborne=true
    assert(cast(s).Reason=='UNIT_UNAVAILABLE')
end)
case('content, frostbite, tutorial-effect and runtime gates preserve cooldown',function()
    local s,p,e,d,step=fixture(); bundle={Success=false,Reason='INVALID_CONTENT'}; assert(cast(s).Reason=='INVALID_CONTENT')
    s,p,e,d,step=fixture(); move(step,'FARTHEST_EMPTY_FORWARD'); s.Frostbitten=true; assert(cast(s).Reason=='PLAYER_FROSTBITTEN')
    s=fixture(); s.TutorialEffectBlocked=true; assert(cast(s).Reason=='TUTORIAL_FOLLOW_GUIDE')
    s=fixture(); s.MissingRuntime=true; assert(cast(s).Reason=='SKILL_RUNTIME_STATE_MISSING')
end)
case('cooldown, active action and occupied immediate slot reject',function()
    local s=fixture(); s.Runtime.RemainingCooldowns.utility=3
    local r=cast(s); assert(r.Reason=='COOLDOWN_ACTIVE' and r.RemainingTurns==3 and #s.Trace==0)
    s=fixture(); s.TurnState.IsActionProcessing=true; assert(cast(s).Reason=='ACTION_PROCESSING')
    s=fixture(); s.TurnState.QueuedActionType='MOVE'; assert(cast(s).Reason=='QUEUE_FULL')
end)
case('guard preserves skill queue, starts cooldown once and completes on original timer',function()
    local s,p=fixture(); assert(cast(s).Reason=='UTILITY_GUARD_ACTIVE' and p.UtilityGuardActive)
    assert(not p.PreviousSkillWasAttack and s.TurnState.QueuedTileIds=='attack|heal')
    assert(s.Runtime:GetRemainingCooldown('utility')==4 and s.Runtime.FreshPlayerCooldowns.utility)
    assert(table.concat(s.Trace,',')=='cast,cooldown,relic,tutorial,snapshot')
    assert(#s.Completions==0 and timers[s.ActionTimerId].Delay==.25); fire(s.ActionTimerId)
    assert(#s.Completions==1 and s.Completions[1].Success and s.ActionTimerId==0)
end)
case('failed effect releases action without cast, relic or cooldown costs',function()
    local s,p,e,d,step=fixture(); step.EffectType='UNKNOWN'; local r=cast(s)
    assert(r.Reason=='UTILITY_EFFECT_UNSUPPORTED' and #s.Completions==1 and not s.Completions[1].Success)
    assert(table.concat(s.Trace,',')=='complete' and s.Runtime:GetRemainingCooldown('utility')==0 and p.PreviousSkillWasAttack)
end)
case('burn occurs after effect acceptance, lethal burn stops presentation and cooldown',function()
    local s,p=fixture(); p.BurnDamage=1; s.BurnLethal=true
    assert(cast(s).Reason=='BURN_LETHAL' and p.UtilityGuardActive and table.concat(s.Trace,',')=='burn')
    assert(s.ActionTimerId==0 and s.Runtime:GetRemainingCooldown('utility')==0)
end)
case('timer fallback completes once and stale actor/map/entry/turn cannot complete',function()
    local s=fixture(); timerUnavailable=true; assert(cast(s).Success and #s.Completions==1)
    for _,change in ipairs({'player','map','entry','turn','entity'}) do
        s=fixture(); assert(cast(s).Success); local id=s.ActionTimerId
        if change=='player' then s.PlayerEntity={}
        elseif change=='map' then s.PlayerEntity.CurrentMap={}
        elseif change=='entry' then s.EntryRequestId=8
        elseif change=='turn' then s.TurnState.TurnNumber=3
        else s.Entity.Valid=false end
        fire(id); assert(#s.Completions==0)
    end
end)
case('practice job override and simultaneous sessions retain independent state',function()
    local s,p=fixture(); s.SkillTestMode=true; s.SkillTestUtilityJobId='mage'; assert(cast(s).Success and lastJob=='mage')
    local other,op=fixture(); assert(not op.UtilityGuardActive); assert(cast(other).Success)
    assert(p.UtilityGuardActive and op.UtilityGuardActive and s.TurnState~=other.TurnState)
end)
case('teleport searches farthest empty forward cell in either direction',function()
    for _,facing in ipairs({'Right','Left'}) do
        local s,p,e,d,step=fixture(); move(step,'FARTHEST_EMPTY_FORWARD'); p.Facing=facing
        assert(cast(s).Success and p.CellIndex==(facing=='Right' and 5 or 0) and s.FaceCalls==nil)
    end
end)
case('behind landing faces enemy, blocked/off-board landing falls back in front',function()
    local s,p,e,d,step=fixture(); move(step,'BEHIND_FARTHEST_ENEMY_FORWARD'); step.Value=1
    assert(cast(s).Success and p.CellIndex==4 and p.Facing=='Left' and s.FaceCalls==1)
    s,p,e,d,step=fixture(); move(step,'BEHIND_FARTHEST_ENEMY_FORWARD'); step.Value=1; e.CellIndex=5
    assert(cast(s).Success and p.CellIndex==4 and p.Facing=='Right' and s.FaceCalls==nil)
    s,p,e,d,step=fixture(); move(step,'BEHIND_FARTHEST_ENEMY_FORWARD'); step.Value=1; e.CellIndex=4; s:add('block','Player',5)
    assert(cast(s).Success and p.CellIndex==3 and p.Facing=='Right')
end)
case('blocked move or rejected relocation never flips caster or spends cooldown',function()
    local s,p,e,d,step=fixture(); move(step,'BEHIND_FARTHEST_ENEMY_FORWARD'); step.Value=1; s:add('block','Player',4)
    assert(cast(s).Reason=='UTILITY_NO_EMPTY_DESTINATION' and p.CellIndex==2 and s.FaceCalls==nil)
    s,p,e,d,step=fixture(); move(step,'FARTHEST_EMPTY_FORWARD'); s.RelocationFailure={Success=false,Reason='STALE_MOVE'}
    assert(cast(s).Reason=='STALE_MOVE' and p.CellIndex==2 and s.Runtime:GetRemainingCooldown('utility')==0)
end)
case('throw target failure, heavy resistance and no landing reject before relocation',function()
    local s,p,e,d,step=fixture(); step.EffectType='THROW_FORWARD'; step.TargetSelector='PRIMARY_TARGET'
    s.TargetFailure={Success=false,Reason='NO_TARGET'}; assert(cast(s).Reason=='NO_TARGET'); s.TargetFailure=nil
    s.Targets.PrimaryTargetUnitId=''; assert(cast(s).Reason=='UTILITY_NO_TARGET'); s.Targets.PrimaryTargetUnitId='enemy'
    e.EnemyTraitIds='HEAVY'; assert(cast(s).Reason=='UTILITY_TARGET_HEAVY'); e.EnemyTraitIds=''; e.CellIndex=5
    assert(cast(s).Reason=='UTILITY_NO_EMPTY_DESTINATION' and #s.Moves==0)
end)
case('forward and behind throws use relocation and play one accepted hit',function()
    for _,kind in ipairs({'THROW_FORWARD','THROW_BEHIND'}) do
        local s,p,e,d,step=fixture(); step.EffectType=kind; step.TargetSelector='PRIMARY_TARGET'; step.Value=1
        assert(cast(s).Success and e.CellIndex==(kind=='THROW_FORWARD' and 5 or 1))
        assert(#s.Moves==1 and #s.Visuals==1 and s.Visuals[1]=='enemy')
    end
end)
case('multi-target push sorts farthest first, cancels queues and carries caster',function()
    local s,p,e,d,step=fixture(); push(step); step.TargetSelector='ALL_SKILL_TARGETS'; step.ParameterB='CARRY_CASTER|CANCEL_QUEUE'
    s:add('far','Enemy',4); s.Targets.TargetUnitIds={'enemy','far'}; s.Targets.TargetCellsByUnitId.far=4
    assert(cast(s).Reason=='UTILITY_PUSHED' and s.Pushes[1]=='far' and #s.Cancels==2)
    assert(s.Units.far.CellIndex==5 and e.CellIndex==4 and p.CellIndex==3)
end)
case('blocked pushes may cancel queue without displacement; zero moves still consume action',function()
    local s,p,e,d,step=fixture(); push(step); step.ParameterB='CANCEL_QUEUE'; s.PushResult={Success=true,Reason='PUSH_BLOCKED_HEAVY'}
    assert(cast(s).Reason=='UTILITY_QUEUE_CANCELLED' and #s.Cancels==1 and #s.Moves==0)
    s,p,e,d,step=fixture(); push(step); s.PushResult={Success=true,Reason='PUSH_BLOCKED_HEAVY'}
    assert(cast(s).Reason=='UTILITY_PUSH_BLOCKED' and s.Runtime:GetRemainingCooldown('utility')==4)
end)
case('fairy collision stuns enemy/wall only, never heavy or player blocker',function()
    for _,kind in ipairs({'wall','enemy','player','heavy','failed'}) do
        local s,p,e,d,step=fixture(); push(step); d.SkillId='fairy_turn'
        if kind=='wall' then e.CellIndex=5
        elseif kind=='heavy' then s.PushResult={Success=true,Reason='PUSH_BLOCKED_HEAVY'}
        elseif kind=='failed' then s.PushResult={Success=false,Reason='INVALID'}
        else s:add('block',kind=='enemy' and 'Enemy' or 'Player',4) end
        assert(cast(s).Success)
        assert(e.StopActionTurns==((kind=='wall' or kind=='enemy') and 1 or 0))
    end
end)
case('cosmetic projectile captures aim before push and delays hit independently',function()
    local s,p,e,d,step=fixture(); push(step); s.Projectile=true; d.HitEffectRuid='hit'
    assert(cast(s).Success and s.LaunchCell==3 and e.CellIndex==5 and #s.Visuals==0)
    fire(1); assert(#s.Visuals==1); fire(s.ActionTimerId); assert(#s.Completions==1)
end)
print('PASS '..count..' utility execution regression groups')
''')
