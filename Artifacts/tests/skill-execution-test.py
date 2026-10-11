"""Run actual skill orchestration and effect mLua with deterministic timer boundaries."""
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
g._SkillExecutionLogic = load(Path(os.environ.get("ORIGINAL_SKILL_LOGIC", COMBAT / "Skills/SkillExecutionLogic.mlua")))
g.Session = load(Path(os.environ.get("ORIGINAL_SESSION", COMBAT / "Components/Shared/BattleSessionComponent.mlua")), {
    "TryExecuteSkill", "GetEffectiveSkillValidation", "GetSkillActionDuration", "ClearSkillImpactTimers",
    "GetProjectileLaunchDelay", "HasSkillProjectile", "GetSkillProjectileSpeed", "IsSequentialProjectileVolley",
    "LaunchSequentialProjectileVolley", "GetProjectileAimCell", "LaunchSkillProjectile",
})

lua.execute(r'''
function isvalid(v) return v~=nil and v.Valid~=false end
function log(_) end
log_warning=log; log_error=log
function Vector2(x,y) return {x=x,y=y} end
local timers,nextTimer,bundle,validation
_TimerService={SetTimerOnce=function(_,callback,delay)
    nextTimer=nextTimer+1; timers[nextTimer]={Callback=callback,Delay=delay}; return nextTimer
end,ClearTimer=function(_,id) timers[id]=nil end}
function fire(id) local t=assert(timers[id]); timers[id]=nil; t.Callback() end
_ContentValidatorLogic={ValidateSkillById=function() return validation or {Success=true,Data=bundle} end}
_SkillDefinitionRepositoryLogic={GetCooldownGroupId=function(_,tags) return tags or '' end,
    GetCooldownGroupSkillIds=function() return {'skill','sibling'} end,
    GetSkillDefinition=function() return {ProjectileRuid='extra-arrow',ProjectileSpeed=8,ProjectileScale=1,ProjectileHeight=.5} end}
_AugmentRuntimeLogic={BuildSkillBundle=function(_,source,definition,steps)
    source.AugmentCalls=(source.AugmentCalls or 0)+1; return {Definition=definition,EffectSteps=steps}
end,CompleteSkillAugment=function(_,context)
    context.BattleSession.Completions=context.BattleSession.Completions+1
end}
_SkillTargetResolverLogic={Resolve=function(_,s,id,d)
    s.Resolves=s.Resolves+1
    return s.TargetFailure or {Success=true,Reason='OK',TargetingType=d.TargetingType,
        PrimaryTargetUnitId=s.AimTarget,TargetUnitIds={s.AimTarget},TargetCellIndices=s.AimCells,
        TargetCellsByUnitId={[s.AimTarget]=s.AimCells[1]}}
end,SerializeStrings=function(_,v) return table.concat(v,',') end,
    SerializeIntegers=function(_,v) return table.concat(v,',') end}
_EffectRouterLogic={ExecuteEffectStep=function(_,context,step)
    local s=context.BattleSession
    assert(s._T.RelicDamageContext==context)
    table.insert(s.Effects,{Type=step.EffectType,Target=context.PrimaryTargetUnitId})
    if step.EffectType=='MOVE_SELF' then s.Unit.CellIndex=1; s.AimTarget='far'; s.AimCells={3} end
    if s.EndOnEffect then s.BattleResult='Victory' end
    return {Success=not s.FailEffect,Reason=s.FailEffect and 'EFFECT_REJECTED' or 'OK',EffectType=step.EffectType,Hit=s.Hit}
end}
_DamageEffectExecutorLogic={GetHitCount=function(_,step) return tonumber(step.ParameterB) or 1 end,
    Execute=function(_,context,step) return context.BattleSession:ResolveSkillDamageImpact(context.SourceUnitId,context.SkillId,'near',1,step.Value) end}
setmetatable(_SkillExecutionLogic,{__newindex=function(_,key) error('shared skill state: '..key) end})

function fixture(team)
    timers={}; nextTimer=0; validation=nil
    local d={SkillId='skill',CostType='NONE',CostValue=1,CooldownTurns=3,SkillTags='',TargetingType='RANGE_OFFSETS',
        MotionProfileId='motion',ActionDuration=.8,Range=4,ProjectileRuid='',ProjectileSpeed=0,
        ProjectileCount=1,ProjectileInterval=.2,ProjectileLaunchDelay=0,ProjectileHeight=.5,ProjectileScale=1}
    bundle={Definition=d,EffectSteps={{StepIndex=1,EffectType='DAMAGE',Value=10,ParameterA='',ParameterB='1'}}}
    local u={UnitId=team=='Enemy' and 'enemy' or 'player_01',Team=team or 'Player',IsDead=false,CurrentHp=50,MaxHp=100,
        BurnDamage=0,BurnSourceUnitId='enemy',CellIndex=0,Facing='Right',PreviousSkillWasAttack=false,NextArrowCount=0}
    local s=setmetatable({_T={},Unit=u,EntryRequestId=7,TurnNumber=2,StageTurnNumber=2,StageId='stage',RunSeed=9,
        BattleResult='',ImpactTimerId=0,ProjectileSpawnCount=0,CellSpacing=1,TurnState={ExecutingTileIndex=1},
        Effects={},Events={},Shots={},Cooldowns={},Publications={},DamageHits={},Completions=0,BonusSpent=0,Resolves=0,
        AimTarget='near',AimCells={1,2,3,4},Hit=true,Speed=2,Motion={ImpactDelay=0,Duration=.4,MotionKey='ATTACK',ActionName='swing',PlayRate=1}}, {__index=Session})
    function u:ConsumeNextAttackBonus() s.BonusSpent=s.BonusSpent+1 end
    local inventory={HealUnlimited=false,Charges=2,GetHealCharges=function(self) return self.Charges end,
        SpendHealCharge=function(self,n) table.insert(s.Events,'spend'); self.Charges=self.Charges-n end}
    local relic={Extra=0,Reduction=0,Completed=0,GetExtraShurikenCount=function(self) return self.Extra end,
        ConsumeLoadedCooldownReduction=function(self) return self.Reduction end,
        OnSkillCompleted=function(self) self.Completed=self.Completed+1 end}
    local parts={['script.BattleUnitComponent']=u,['script.PlayerRunInventoryComponent']=inventory,
        ['script.PlayerRunRelicEffectComponent']=relic,['script.BattleUnitPresentationComponent']={}}
    local source={PlayerControllerComponent=team~='Enemy' and {} or nil,GetComponent=function(_,key) return parts[key] end}
    s.Source=source; s.Entities={[u.UnitId]=source}
    local near={UnitId='near',Team='Enemy',CurrentHp=10,IsDead=false}
    local far={UnitId='far',Team='Enemy',CurrentHp=10,IsDead=false}
    s.Targets={[1]=near,[3]=far}
    s.BoardState={FindAtCell=function(_,cell) local target=s.Targets[cell]; return target and {GetComponent=function() return target end} end}
    local runtime={CanUseSkill=function() return s.CooldownResult or {Success=true} end,
        StartPlayerCooldown=function(_,id,n) s.Cooldowns[id]=n end,
        StartCooldown=function(_,id,n) s.Cooldowns[id]=n end}
    function s:FindUnitEntity(id) return self.Entities[id] end
    function s:IsPlayerSealed() return self.Sealed==true end
    function s:IsTeamTurn(_) return not self.InvalidPhase end
    function s:GetSkillRuntimeState() if not self.MissingRuntime then return runtime end end
    function s:GetSkillSpeedMultiplier() return self.Speed end
    function s:GetSkillMotionProfile() return self.Motion end
    function s:ResolvePlayerConfusion(_,definition) if self.Confused then definition.Range=2 end end
    function s:PlayEnemyAttackMotion() table.insert(self.Events,'enemy-motion') end
    function s:ApplyStatusDamage() table.insert(self.Events,'burn'); if self.BurnLethal then u.IsDead=true end end
    function s:AdvanceComboChain() table.insert(self.Events,'combo') end
    function s:ApplySkillWeapon() table.insert(self.Events,'weapon') end
    function s:SendMotionPresentation() table.insert(self.Events,'motion') end
    function s:BeginSkillEffectPresentation() table.insert(self.Events,'visual') end
    function s:PublishSkillTargetResolution(...) table.insert(self.Publications,{...}) end
    function s:GetCellPosition(cell) return {x=cell*self.CellSpacing,y=0} end
    function s:SpawnSkillProjectile(id,name,start,finish,speed,ruid,scale,flip)
        table.insert(self.Shots,{Id=id,Name=name,Start=start,Finish=finish,Speed=speed,Ruid=ruid,Flip=flip})
    end
    function s:ResolveSkillDamageImpact(sourceId,skillId,targetId,cell,damage)
        assert(self._T.AttackBuffHit and self._T.RelicDamageContext)
        table.insert(self.DamageHits,{Target=targetId,Cell=cell,Damage=damage,Fixed=self._T.AttackBuffHit.FixedFollowup})
        if self.KillFirst and #self.DamageHits==1 then near.IsDead=true; near.CurrentHp=0 end
        return {Success=true,Reason='HIT',Hit=true}
    end
    return s,d,bundle.EffectSteps,parts,inventory,relic
end
function cast(s) return s:TryExecuteSkill(s.Unit.UnitId,'skill') end
function projectile(d) d.ProjectileRuid='projectile'; d.ProjectileSpeed=8 end
function volley(d,steps) projectile(d); d.WeaponType='CLAW'; d.TargetingType='FIRST_ENEMY_FORWARD'; steps[1].ParameterA='MULTI_HIT'; steps[1].ParameterB='2' end
local count=0
function case(name,check) check(); count=count+1; print('PASS '..name) end

case('content, sealed and runtime gates precede irreversible costs',function()
    local s=fixture(); validation={Success=false,Reason='INVALID_CONTENT',DetailReason='COLUMN'}
    local r=cast(s); assert(not r.Success and r.DetailReason=='COLUMN' and #s.Events==0)
    s=fixture(); s.Sealed=true; assert(cast(s).Reason=='PLAYER_SEALED')
    s=fixture(); s.MissingRuntime=true; assert(cast(s).Reason=='SKILL_RUNTIME_STATE_MISSING' and #s.Effects==0)
end)
case('context preserves authoritative actor and phase checks',function()
    assert(_SkillExecutionLogic:BuildContext(nil,'player_01','skill',{}).Reason=='SESSION_MISSING')
    local s,d,_,parts=fixture(); s.Entities.player_01=nil
    assert(_SkillExecutionLogic:BuildContext(s,'player_01','skill',d).Reason=='SOURCE_NOT_FOUND')
    s,d,_,parts=fixture(); parts['script.BattleUnitComponent']=nil
    assert(_SkillExecutionLogic:BuildContext(s,'player_01','skill',d).Reason=='SOURCE_COMPONENT_MISSING')
    s,d=fixture(); s.InvalidPhase=true; assert(cast(s).Reason=='INVALID_PHASE')
    s=fixture(); s.Unit.IsDead=true; assert(cast(s).Reason=='SOURCE_DEAD')
end)
case('augment applies to the actor and confusion cannot mutate repository data',function()
    local s,d,_,parts=fixture(); parts['script.PlayerRunAugmentComponent']={}; s.Confused=true
    assert(cast(s).Success and s.Source.AugmentCalls==1 and d.Range==4)
end)
case('enemy attack attempt animates even when cooldown rejects it',function()
    local s=fixture('Enemy'); s.CooldownResult={Success=false,Reason='COOLDOWN',RemainingTurns=2}
    local r=cast(s); assert(r.Reason=='COOLDOWN' and r.RemainingTurns==2 and s.Events[1]=='enemy-motion' and #s.Effects==0)
end)
case('accepted queue action and lethal burn precede charge spending',function()
    local s,d,_,_,inventory=fixture(); d.CostType='HEAL_CHARGE'; s.Unit.BurnDamage=1; s.BurnLethal=true
    local r=cast(s); assert(r.Success and r.Reason=='BURN_LETHAL' and s._T.QueueExecutionConsumedAction)
    assert(inventory.Charges==2 and s.Events[1]=='burn' and #s.Effects==0)
end)
case('healing rejects empty charges and full HP, relic replay skips spending and cooldown',function()
    local s,d,_,_,inventory=fixture(); d.CostType='HEAL_CHARGE'; inventory.Charges=0
    assert(cast(s).Reason=='HEAL_CHARGES_EMPTY' and not s._T.QueueExecutionConsumedAction)
    s,d=fixture(); d.CostType='HEAL_CHARGE'; s.Unit.CurrentHp=100; assert(cast(s).Reason=='HP_FULL')
    s,d,_,_,inventory=fixture(); d.CostType='HEAL_CHARGE'; assert(cast(s).Success and inventory.Charges==1)
    s,d,_,_,inventory=fixture(); d.CostType='HEAL_CHARGE'; s._T.ReplayingRelicSkill=true
    s.CooldownResult={Success=false,Reason='COOLDOWN'}
    assert(cast(s).Success and inventory.Charges==2 and next(s.Cooldowns)==nil)
end)
case('cooldown reduction reaches group members and enemy cooldown owner',function()
    for _,team in ipairs({'Player','Enemy'}) do
        local s,d,_,_,_,relic=fixture(team); d.SkillTags='shared'; relic.Reduction=1
        assert(cast(s).Success and s.Cooldowns.skill==2 and s.Cooldowns.sibling==2)
    end
end)
case('weapon and motion precede effects, immediate hit consumes bonus and completes once',function()
    local s=fixture(); local r=cast(s)
    assert(r.Success and r.PresentationHandoffDuration==.01 and #s.Effects==1 and s.ImpactTimerId==0)
    assert(table.concat(s.Events,',')=='combo,weapon,motion,visual' and s.BonusSpent==1 and s.Completions==1)
end)
case('miss preserves next attack bonus and effect failure preserves spent action',function()
    local s=fixture(); s.Hit=false; assert(cast(s).Success and s.BonusSpent==0)
    s=fixture(); s.FailEffect=true; local r=cast(s)
    assert(not r.Success and r.Reason=='EFFECT_REJECTED' and s._T.QueueExecutionConsumedAction and s.Completions==0)
end)
case('delayed effects resolve the target at impact and restore relic context',function()
    local s=fixture(); s.Motion.ImpactDelay=.3; s._T.RelicDamageContext='outer'
    local r=cast(s); assert(r.Reason=='IMPACT_PENDING' and #s.Effects==0 and s.Resolves==0)
    assert(timers[s.ImpactTimerId].Delay==.3); s.AimTarget='far'; fire(s.ImpactTimerId)
    assert(s.Effects[1].Target=='far' and s.ImpactTimerId==0 and s._T.RelicDamageContext=='outer')
end)
case('superseded callback cannot hit or erase the new cast timer',function()
    local s=fixture(); s.Motion.ImpactDelay=.3; cast(s); local old=timers[s.ImpactTimerId].Callback
    cast(s); local current=s.ImpactTimerId; old()
    assert(s.ImpactTimerId==current and #s.Effects==0); fire(current); assert(#s.Effects==1)
end)
case('entry, battle end, death, destruction and replaced actor cancel delayed impacts',function()
    for _,stale in ipairs({'entry','battle','dead','hp','invalid','replacement'}) do
        local s=fixture(); s.Motion.ImpactDelay=.3; cast(s); local id=s.ImpactTimerId
        if stale=='entry' then s.EntryRequestId=8 elseif stale=='battle' then s.BattleResult='Defeat'
        elseif stale=='dead' then s.Unit.IsDead=true elseif stale=='hp' then s.Unit.CurrentHp=0
        elseif stale=='invalid' then s.Source.Valid=false else s.Entities.player_01={} end
        fire(id); assert(#s.Effects==0 and s.ImpactTimerId==0 and s.Completions==0)
    end
end)
case('last projectile arrival defines impact and queue duration with independent flight speed',function()
    local s,d=fixture(); projectile(d); d.ProjectileCount=3; d.ProjectileLaunchDelay=.4
    local r=cast(s); assert(r.Reason=='IMPACT_PENDING' and math.abs(r.PresentationHandoffDuration-1.4)<1e-9)
    assert(math.abs(s:GetSkillActionDuration('skill')-1.4)<1e-9 and s:GetSkillProjectileSpeed(d)==4)
    for _,id in ipairs(s._T.projectileTimerIds) do fire(id) end
    assert(#s.Shots==3 and s.Shots[1].Start.y==.5 and s.Shots[1].Finish.x==4 and #s.Effects==0)
    fire(s.ImpactTimerId); assert(#s.Effects==1)
end)
case('all pending launches and impacts clear without cancelling pending wave completion',function()
    local s,d=fixture(); projectile(d); d.ProjectileCount=3; d.ProjectileLaunchDelay=.4; cast(s)
    s._T.PendingWaveCompletion='keep'; local sequence=s._T.projectileCastSequence
    s:ClearSkillImpactTimers(); assert(next(timers)==nil and s.ImpactTimerId==0 and #s._T.projectileTimerIds==0)
    assert(s._T.projectileCastSequence==sequence+1 and s._T.PendingWaveCompletion=='keep' and #s.Shots==0)
end)
case('projectile guard and range clamp keep invalid launches out of the queue',function()
    local s,d=fixture(); assert(not s:HasSkillProjectile(nil)); d.ProjectileRuid='half'
    assert(not s:HasSkillProjectile(d)); projectile(d); s.AimCells={1,3,9}; assert(s:GetProjectileAimCell('player_01',d)==3)
    s.AimCells={9}; assert(s:LaunchSkillProjectile('player_01',d,0)==0 and #s.Shots==0)
    s.AimCells={}; assert(s:GetProjectileAimCell('player_01',d)==-1)
end)
case('extra arrow visuals use their own RUID and do not mutate the authored skill',function()
    local s,d=fixture(); s.Unit.NextArrowCount=2; s.Unit.NextArrowSkillId='arrow'
    cast(s); for _,id in ipairs(s._T.projectileTimerIds) do fire(id) end
    assert(#s.Shots==2 and s.Shots[1].Ruid=='extra-arrow' and s.Unit.NextArrowCount==0 and d.ProjectileRuid=='')
end)
case('move step refreshes targets before the next damage and battle end stops later steps',function()
    local s,_,steps=fixture(); steps[1].EffectType='MOVE_SELF'; steps[2]={StepIndex=2,EffectType='DAMAGE'}
    assert(cast(s).Success and s.Effects[2].Target=='far' and s.Resolves==2)
    s,_,steps=fixture(); steps[2]={StepIndex=2,EffectType='DAMAGE'}; s.EndOnEffect=true
    assert(cast(s).Reason=='BATTLE_ENDED' and #s.Effects==1 and s.Completions==1)
end)
case('sequential volley retargets survivors, restores contexts and completes after last shot',function()
    local s,d,steps=fixture(); volley(d,steps); s.KillFirst=true
    s._T.RelicDamageContext='outer'; s._T.AttackBuffHit='outer-hit'; local r=cast(s)
    assert(r.Reason=='PROJECTILE_VOLLEY_PENDING' and #s.Shots==1 and #s.DamageHits==0)
    fire(s.ImpactTimerId); assert(s.DamageHits[1].Target=='near' and s.Completions==0)
    fire(s.ImpactTimerId); assert(#s.Shots==2 and s.Shots[2].Finish.x==3)
    fire(s.ImpactTimerId); assert(s.DamageHits[2].Target=='far' and s.DamageHits[2].Damage==1 and s.DamageHits[2].Fixed)
    assert(s.ImpactTimerId==0 and s.Completions==1 and s.BonusSpent==1 and s._T.RelicDamageContext=='outer' and s._T.AttackBuffHit=='outer-hit')
end)
case('sequential volley rejects stale entry, direction, cell and replaced source',function()
    for _,stale in ipairs({'entry','facing','cell','replacement'}) do
        local s,d,steps=fixture(); volley(d,steps); cast(s)
        if stale=='entry' then s.EntryRequestId=8 elseif stale=='facing' then s.Unit.Facing='Left'
        elseif stale=='cell' then s.Unit.CellIndex=1 else s.Entities.player_01={} end
        fire(s.ImpactTimerId); assert(#s.DamageHits==0 and #s.Shots==1 and s.ImpactTimerId==0)
    end
end)
case('empty volley misses without spending bonus and invalid targets preserve rejection',function()
    local s,d,steps=fixture(); volley(d,steps); s.AimCells={}; assert(cast(s).Success and s.Completions==1 and s.BonusSpent==0 and s.ImpactTimerId==0)
    s,d,steps=fixture(); volley(d,steps); s.TargetFailure={Success=false,Reason='NO_TARGETS'}
    assert(cast(s).Reason=='NO_TARGETS' and s.ImpactTimerId==0 and #s.Shots==0)
end)
case('two sessions keep impact cancellation and completion independent',function()
    local a=fixture(); local b=fixture(); a.Motion.ImpactDelay=.3; b.Motion.ImpactDelay=.3
    cast(a); cast(b); a:ClearSkillImpactTimers(); fire(b.ImpactTimerId)
    assert(#a.Effects==0 and #b.Effects==1 and a.Completions==0 and b.Completions==1)
end)
print('All '..count..' skill execution groups passed (mock execution).')
''')
