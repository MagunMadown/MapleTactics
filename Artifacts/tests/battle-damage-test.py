"""Exercise actual damage/support methods and unit mutations; engine boundaries are mocks.

Run with LUPA_PATH. ORIGINAL_SESSION/ORIGINAL_HEAL/ORIGINAL_BUFF can replay pre-extraction code.
"""
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


g = lua.globals()
g.Session = load(Path(os.environ.get("ORIGINAL_SESSION", COMBAT / "Components/Shared/BattleSessionComponent.mlua")), {
    "ResolveFrontAttackImpact", "ResolveSkillDamageImpact", "ApplyDamage", "TryRegisterEnemyCastInterrupt",
    "ApplyPushCollisionDamage", "ApplyStatusDamage", "ResolveSkillHealImpact", "ResolveSkillBuffImpact", "IsTeamTurn",
})
g._BattleDamageLogic = load(COMBAT / "Resolvers/BattleDamageLogic.mlua")
executors = COMBAT / "Skills/EffectExecutors"
g._HealEffectExecutorLogic = load(Path(os.environ.get("ORIGINAL_HEAL", executors / "HealEffectExecutorLogic.mlua")))
g._BuffEffectExecutorLogic = load(Path(os.environ.get("ORIGINAL_BUFF", executors / "BuffEffectExecutorLogic.mlua")))
g._DamageEffectExecutorLogic = load(executors / "DamageEffectExecutorLogic.mlua")
g._EffectRouterLogic = load(COMBAT / "Resolvers/EffectRouterLogic.mlua", {"ExecuteEffect"})
g.Unit = load(COMBAT / "Components/Shared/BattleUnitComponent.mlua", {
    "ApplyDamage", "ApplyHealing", "RestoreCurrentHp", "ApplyNextAttackBonus", "ApplyTimedBuff",
    "ConsumeAttackBuffHit", "ConsumeVenomBuffHit", "ApplyPoison", "SumTableValues",
    "RecomputeBuffTotals", "RefreshActiveBuffSnapshot",
})

lua.execute(r'''
function log(_) end
log_warning=log; log_error=log
function isvalid(v) return v~=nil and v.Valid~=false end
function BasicAttackResolvedEvent() return {} end
_TutorialRulesLogic={GetDamageAmount=function(_,s,target,amount) return amount end}
_SkillDefinitionRepositoryLogic={GetSkillDefinition=function() return {Success=true,SkillTags='buff',IconRuid='icon'} end}
_SkillTargetResolverLogic={SelectEffectTargets=function(_,context) return context.TargetUnitIds end}
_AugmentRuntimeLogic={GetConditionalDamageBonus=function(_,context) return context and context.Bonus or 0 end,
    OnSkillDamageApplied=function(_,context) context.AugmentHits=(context.AugmentHits or 0)+1 end,
    QueueSkillRegeneration=function(_,context) context.RegenCalls=(context.RegenCalls or 0)+1; return context.Regen==true end}
_SkillTestLogic={RecordDummyHit=function(self,id,amount) self.Hits=(self.Hits or 0)+1; self.Amount=amount end}
setmetatable(_BattleDamageLogic,{__newindex=function(_,key) error('shared damage state: '..key) end})

function fixture()
    local s=setmetatable({_T={},Units={},Events={},Trace={},Numbers={},HitEffects={},Snapshots={},
        BattlePhase='PlayerTurn',BattleResult='',TurnNumber=3,ExecutingTileIndex=2,
        StrongHitDamageThreshold=5,NormalHitStopDuration=.04,StrongHitStopDuration=.08,
        HitReactionDuration=.1,HitFlashDuration=.1,PushCollisionDamage=2,
        PushCollisionAttackId='COLLISION',VenomPoisonAttackId='POISON'}, {__index=Session})
    function s:trace(value) table.insert(self.Trace,value) end
    function s:add(id,team,cell)
        local u=setmetatable({UnitId=id,Team=team,CellIndex=cell,Facing='Right',CurrentHp=30,MaxHp=30,
            IsDead=false,UtilityGuardActive=false,IsBoss=false,EnemyDefinitionId='',
            NextAttackBonus=0,ComboAttackBonus=0,NextAttackBonusBySkill={},NextAttackBonusSequence={},
            TimedBuffEntries={},TimedBuffApplySequence=0,ActiveBuffSnapshot='',
            AttackBuffAmount=0,AttackBuffHits=0,AttackBuffTurns=0,DefenseBuffAmount=0,DefenseBuffTurns=0,
            MaxHpBuffAmount=0,MaxHpBuffTurns=0,GuardBuffAmount=0,GuardBuffTurns=0,
            VenomBuffAmount=0,VenomBuffTurns=0,ComboBuffAmount=0,ComboBuffTurns=0,AttackDamageCap=0,
            VenomMarkerRuid='',PoisonDamage=0,PoisonSourceUnitId='',PoisonMarkerRuid='',
            BurnDamage=0,BurnTurns=0,BurnSourceUnitId='',BasicAttackDamage=4,DifficultyAttackBonus=0}, {__index=Unit})
        u.Components={['script.BattleUnitComponent']=u}
        local e={Unit=u,GetComponent=function(_,name) return u.Components[name] end}
        u.Entity=e
        function u:SyncRunHp(reason) self.SyncReason=reason end
        s.Units[id]=u
        return u
    end
    function s:FindUnitEntity(id) return self.Units[id] and self.Units[id].Entity end
    function s:IsValidCell(cell) return cell>=0 and cell<=4 end
    function s:ResolveFrontTarget(id)
        local u=self.Units[id]; local cell=u.CellIndex+(u.Facing=='Right' and 1 or -1)
        return self.BoardState:FindAtCell(cell,id)
    end
    s.BoardState={FindAtCell=function(_,cell,exclude)
        for id,u in pairs(s.Units) do if id~=exclude and u.CellIndex==cell and not u.IsDead then return u.Entity end end
    end}
    s.Entity={SendEvent=function(_,event) table.insert(s.Events,event) end}
    function s:PresentDamageNumber(source,target,amount) table.insert(self.Numbers,amount); self:trace('number') end
    function s:FlushDamageNumberBatch(batch)
        if #batch.Damages>0 then self:trace('batch'); table.insert(self.Numbers,table.concat(batch.Damages,',')); batch.Damages={} end
    end
    function s:PlayAcceptedEnemyImpact() self:trace('impact') end
    function s:PlayImpactCameraShake() self:trace('shake') end
    function s:SendMotionPresentation() self:trace('motion') end
    function s:PlayActiveHitEffect(id) table.insert(self.HitEffects,id) end
    function s:RefreshPlayerHpSnapshot(reason) table.insert(self.Snapshots,reason) end
    function s:PublishEnemyPlanSnapshot(reason) self.PlanSnapshotCount=(self.PlanSnapshotCount or 0)+1 end
    function s:HandleUnitDiedFromSource(id,status,source)
        self:trace('death:'..id); self.Units[id].IsDead=true
        if self.OnDeath then self:OnDeath(id) end
    end
    local p=s:add('player','Player',1); local e=s:add('enemy','Enemy',2)
    return s,p,e
end
function context(s,ids)
    return {BattleSession=s,SourceUnitId='player',SkillId='skill',PrimaryTargetUnitId='enemy',
        TargetUnitIds=ids or {'enemy'},TargetCellsByUnitId={enemy=2,other=3},Definition={SkillTags=''}}
end
local checks=0
function check(label,fn) fn(); checks=checks+1; print('PASS '..label) end

check('source/target/phase/team/death validation stays on original entry points',function()
    local s,p,e=fixture()
    assert(s:ApplyDamage('player','enemy',0,'skill').Reason=='INVALID_AMOUNT')
    assert(s:ApplyDamage('missing','enemy',1,'skill').Reason=='SOURCE_NOT_FOUND')
    assert(s:ApplyDamage('player','missing',1,'skill').Reason=='TARGET_NOT_FOUND')
    assert(s:ApplyDamage('player','player',1,'skill').Reason=='SAME_TEAM')
    s.BattlePhase='EnemyTurn'
    assert(s:ResolveFrontAttackImpact('player','skill',1).Reason=='INVALID_PHASE')
    assert(s:ResolveSkillDamageImpact('player','skill','enemy',2,1).Reason=='INVALID_PHASE')
    assert(s:ResolveSkillHealImpact('player','heal','player',1).Reason=='INVALID_PHASE')
    assert(s:ResolveSkillBuffImpact('player','buff','player','ATTACK_BUFF',1,1,true).Reason=='INVALID_PHASE')
    s.BattlePhase='PlayerTurn'; e.Components['script.BattleUnitComponent']=nil
    assert(s:ApplyDamage('player','enemy',1,'skill').Reason=='UNIT_COMPONENT_MISSING')
    e.Components['script.BattleUnitComponent']=e; e.IsDead=true
    assert(s:ResolveSkillDamageImpact('player','skill','enemy',2,1).Reason=='UNIT_DEAD')
    assert(e.CurrentHp==30 and #s.Events==0 and #s.Trace==0)
end)

check('front impact reads current facing and emits one hit/miss event',function()
    local s,p,e=fixture()
    assert(s:ResolveFrontAttackImpact('player','basic',4).DamageAmount==4 and e.CurrentHp==26)
    p.Facing='Left'
    assert(s:ResolveFrontAttackImpact('player','basic',4).Reason=='MISS_EMPTY')
    p.CellIndex=0
    assert(s:ResolveFrontAttackImpact('player','basic',4).Reason=='MISS_OUT_OF_BOUNDS')
    assert(#s.Events==3 and s.Events[1].TargetCell==2 and not s.Events[3].Hit)
end)

check('enemy friendly fire remains valid but player allies reject damage',function()
    local s,p,e=fixture(); local ally=s:add('ally','Player',0); local other=s:add('other','Enemy',3)
    assert(s:ApplyDamage('player','ally',4,'skill').Reason=='SAME_TEAM')
    s.BattlePhase='EnemyTurn'
    assert(s:ResolveSkillDamageImpact('enemy','skill','other',3,4).DamageAmount==4)
end)

check('defense/cap/armor and both unit guards retain order',function()
    local s,p,e=fixture(); e.DefenseBuffAmount=2; e.AttackDamageCap=3; e.EnemyDefinitionId='region_04_iron_hog'
    assert(s:ApplyDamage('player','enemy',10,'skill').AppliedAmount==2)
    assert(s:ApplyDamage('player','enemy',1,'skill').Reason=='IRON_ARMOR_BLOCKED')
    e.EnemyDefinitionId=''; e.UtilityGuardActive=true
    assert(s:ApplyDamage('player','enemy',10,'skill').AppliedAmount==0)
    e.UtilityGuardActive=false; e.GuardBuffAmount=1
    assert(s:ApplyStatusDamage('enemy',10,'gone','BURN').AppliedAmount==0)
    assert(e.CurrentHp==28 and #s.Numbers==1)
end)

check('zero-base skills cannot acquire minimum-one damage from defenses',function()
    local s,p,e=fixture(); local c=context(s); c.Definition.ZeroDamage=true; s._T.RelicDamageContext=c
    e.DefenseBuffAmount=10
    assert(s:ApplyDamage('player','enemy',0,'skill').Reason=='ZERO_BASE_DAMAGE')
    assert(e.CurrentHp==30 and #s.Trace==0)
end)

check('fixed collision/shockwave ignore attack charges and attack-only defenses',function()
    local s,p,e=fixture(); p:ApplyTimedBuff('buff','ATTACK',8,2); p.NextAttackBonus=5; p.ComboAttackBonus=6
    e.DefenseBuffAmount=10; e.AttackDamageCap=1
    assert(s:ApplyDamage('player','enemy',2,'COLLISION').AppliedAmount==2)
    assert(s:ApplyDamage('player','enemy',2,'AUGMENT_SHOCKWAVE').AppliedAmount==2)
    assert(p.AttackBuffHits==2 and p.NextAttackBonus==5)
end)

check('multi-hit area shares charges across targets and follow-up stays fixed',function()
    local s,p,e=fixture(); local other=s:add('other','Enemy',3); local c=context(s,{'enemy','other'})
    p:ApplyTimedBuff('attack','ATTACK',3,3); p:ApplyTimedBuff('venom','VENOM',2,3); p.NextAttackBonus=5
    p.VenomMarkerRuid='venom'; s._T.RelicDamageContext=c
    local r=_DamageEffectExecutorLogic:Execute(c,{EffectType='DAMAGE',Value=4,ParameterA='MULTI_HIT',ParameterB='2'})
    assert(r.Success and #r.Results==4 and e.CurrentHp==17 and other.CurrentHp==17)
    assert(r.Results[1].DamageAmount==12 and r.Results[2].DamageAmount==1 and r.Results[3].DamageAmount==12)
    assert(p.AttackBuffHits==1 and p.VenomBuffTurns==1 and p.NextAttackBonus==5)
    assert(e.PoisonDamage==4 and other.PoisonDamage==4 and #s.HitEffects==2 and #s.Numbers==2)
    assert(s.Numbers[1]=='12,1' and s._T.AttackBuffHit==nil and s._T.damageNumberBatch==nil)
end)

check('failed damage restores executor batch and hit scope',function()
    local s,p,e=fixture(); local c=context(s); p.IsDead=true
    local oldBatch={}; local oldHit={}; s._T.damageNumberBatch=oldBatch; s._T.AttackBuffHit=oldHit
    assert(not _DamageEffectExecutorLogic:Execute(c,{Value=4,ParameterA='MULTI_HIT',ParameterB='2'}).Success)
    assert(s._T.damageNumberBatch==oldBatch and s._T.AttackBuffHit==oldHit and e.CurrentHp==30)
end)

check('interrupt keys deduplicate a skill queue entry and skip zero damage',function()
    local s,p,e=fixture(); local keys={}
    e.Components['script.EnemyActionPlanComponent']={RegisterInterruptHit=function(_,skill,key)
        local duplicate=keys[key]; keys[key]=true
        return {Success=true,Reason=duplicate and 'INTERRUPT_HIT_DUPLICATE' or 'INTERRUPT_HIT',Interrupted=not duplicate}
    end}
    s.TurnState={ExecutingTileIndex=7}
    assert(s:TryRegisterEnemyCastInterrupt('player','skill','enemy',0).Reason=='NO_APPLIED_DAMAGE')
    s:ResolveSkillDamageImpact('player','skill','enemy',2,1)
    s:ResolveSkillDamageImpact('player','skill','enemy',2,1)
    assert(keys['3:7:skill'] and s.PlanSnapshotCount==1)
end)

check('exact lethal refunds stop at one cooldown; overkill does not refund',function()
    local s,p,e=fixture(); p.Components['script.PlayerRunAugmentComponent']={}
    local runtime={Remaining=3,ReduceCooldown=function(self,skill,amount) self.Remaining=self.Remaining-amount end,
        GetRemainingCooldown=function(self) return self.Remaining end}
    function s:GetEffectiveSkillValidation() return {Success=true,Data={Definition={PreciseRefund=9}}} end
    function s:GetSkillRuntimeState() return runtime end
    e.CurrentHp=4
    assert(s:ResolveSkillDamageImpact('player','skill','enemy',2,4).Success and runtime.Remaining==1)
    e.IsDead=false; e.CurrentHp=4; runtime.Remaining=3
    s:ResolveSkillDamageImpact('player','skill','enemy',2,5)
    assert(runtime.Remaining==3)
end)

check('poison detonates once before new venom and updates returned HP',function()
    local s,p,e=fixture(); local c=context(s); c.Definition.SkillTags='fire'; s._T.RelicDamageContext=c
    e.PoisonDamage=2; p:ApplyTimedBuff('venom','VENOM',1,2)
    p.Components['script.PlayerRunRelicEffectComponent']={IsInitialized=false,
        GetSpecialEffectValue=function(_,key) return key=='POISON_DETONATION' and 2 or 0 end}
    local r=s:ApplyDamage('player','enemy',3,'skill')
    assert(r.HpAfter==23 and e.PoisonDamage==1 and c.RelicDetonatedTargets.enemy)
    r=s:ApplyDamage('player','enemy',3,'skill')
    assert(r.HpAfter==20 and e.PoisonDamage==2 and c.AugmentHits==2)
end)

check('lethal batch flush and relic kill run before encounter death cleanup',function()
    local s,p,e=fixture(); local c=context(s); s._T.RelicDamageContext=c; e.CurrentHp=4
    p.Components['script.PlayerRunRelicEffectComponent']={IsInitialized=false,OnSkillKill=function() s:trace('relic-kill') end}
    s._T.damageNumberBatch={SourceUnitId='player',TargetUnitId='enemy',Damages={},HitCount=0}
    local r=s:ApplyDamage('player','enemy',4,'skill')
    assert(r.ExactLethal and e.IsDead)
    local trace=table.concat(s.Trace,',')
    assert(string.find(trace,'batch,relic%-kill,death:enemy') and s.Numbers[1]=='4')
end)

check('training lethal refills without death or precise kill refund',function()
    local s,p,e=fixture(); s.SkillTestMode=true; e.CurrentHp=2
    local r=s:ApplyDamage('player','enemy',8,'skill')
    assert(r.AppliedAmount==2 and not r.ExactLethal and e.CurrentHp==30 and not e.IsDead)
    assert(_SkillTestLogic.Amount==8 and not string.find(table.concat(s.Trace,','),'death'))
end)

check('status damage survives missing caster and bypasses attack-only cap',function()
    local s,p,e=fixture(); e.AttackDamageCap=1; e.DefenseBuffAmount=100
    assert(s:ApplyStatusDamage('enemy',5,'gone','BURN').AppliedAmount==5)
    assert(e.CurrentHp==25 and #s.Numbers==1)
    e.CurrentHp=1
    assert(s:ApplyStatusDamage('enemy',1,'gone','POISON').ReachedZero and e.IsDead)
    assert(s:ApplyStatusDamage('enemy',1,'gone','POISON').Reason=='TARGET_DEAD')
end)

check('push collision captures both IDs before first death mutates board',function()
    local s,p,e=fixture(); local other=s:add('other','Enemy',3); e.CurrentHp=1
    function s:OnDeath(id) if id=='enemy' then other.UnitId='renamed-by-cleanup' end end
    s:ApplyPushCollisionDamage('player',e,3)
    assert(e.IsDead and other.CurrentHp==28)
    local before=other.CurrentHp
    s:ApplyPushCollisionDamage('player',other,4)
    assert(other.CurrentHp==before)
end)

check('fire boar ignites only positive non-fixed hits and preserves indefinite burn',function()
    local s,p,e=fixture(); e.EnemyDefinitionId='region_04_fire_boar'; s.BattlePhase='EnemyTurn'
    p.UtilityGuardActive=true; s:ApplyDamage('enemy','player',4,'skill'); assert(p.BurnDamage==0)
    p.UtilityGuardActive=false; p.BurnDamage=3; p.BurnTurns=0
    s:ApplyDamage('enemy','player',4,'skill'); assert(p.BurnDamage==3 and p.BurnTurns==0)
    p.BurnDamage=0; s:ApplyDamage('enemy','player',2,'COLLISION'); assert(p.BurnDamage==0)
    s:ApplyDamage('enemy','player',4,'skill'); assert(p.BurnDamage==1 and p.BurnTurns==1)
end)

check('heal clamps HP and full-HP regeneration remains a successful hit',function()
    local s,p,e=fixture(); local c=context(s,{'player'}); c.SkillId='heal'; p.CurrentHp=28; s._T.RelicDamageContext=c
    local r=_HealEffectExecutorLogic:Execute(c,{Value=5})
    assert(r.Success and r.Results[1].HealAmount==2 and p.CurrentHp==30)
    assert(s:ResolveSkillHealImpact('player','heal','player',5).Reason=='HEAL_FAILED_HP_ALREADY_FULL')
    c.Regen=true
    r=s:ResolveSkillHealImpact('player','heal','player',5)
    assert(r.Success and r.Hit and r.HealAmount==0 and #s.HitEffects==2)
    assert(s:ResolveSkillHealImpact('player','heal','enemy',5).Reason=='TARGET_NOT_ALLY')
    assert(s:ResolveSkillHealImpact('player','heal','player',0).Reason=='HEAL_FAILED_INVALID_AMOUNT')
end)

check('buff executor deduplicates effects, refreshes rather than stacks and snapshots max HP',function()
    local s,p,e=fixture(); local c=context(s,{'player'})
    assert(_BuffEffectExecutorLogic:Execute(c,{EffectType='ATTACK_BUFF',Value=3,ParameterA='2'}).Success)
    assert(_BuffEffectExecutorLogic:Execute(c,{EffectType='DEFENSE_BUFF',Value=2,ParameterA='2'}).Success)
    assert(#s.HitEffects==1 and p.AttackBuffAmount==3 and p.DefenseBuffAmount==2)
    assert(s:ResolveSkillBuffImpact('player','skill','player','ATTACK_BUFF',1,1,false).Reason=='ATTACK_BUFF_REFRESHED')
    assert(p.AttackBuffAmount==3 and p.AttackBuffHits==2)
    s:ResolveSkillBuffImpact('player','hp','player','MAX_HP_BUFF',5,2,true)
    assert(p.MaxHp==35 and p.CurrentHp==35 and s.Snapshots[1]=='MAX_HP_BUFF_APPLIED')
    s:ResolveSkillBuffImpact('player','next','player','NEXT_ATTACK_BONUS',4,0,false)
    s:ResolveSkillBuffImpact('player','next','player','NEXT_ATTACK_BONUS',2,0,false)
    assert(p.NextAttackBonus==4)
    assert(s:ResolveSkillBuffImpact('player','bad','player','UNKNOWN',1,1,true).Reason=='UNSUPPORTED_BUFF_TYPE')
    assert(s:ResolveSkillBuffImpact('player','bad','enemy','ATTACK_BUFF',1,1,true).Reason=='TARGET_NOT_ALLY')
end)

check('two encounters keep damage contexts, batches and support state isolated',function()
    local a,pa,ea=fixture(); local b,pb,eb=fixture(); local c=context(a); c.Bonus=2; a._T.RelicDamageContext=c
    a:ResolveSkillBuffImpact('player','buff','player','ATTACK_BUFF',3,1,true)
    a:ApplyDamage('player','enemy',4,'skill'); b:ApplyDamage('player','enemy',4,'skill')
    assert(ea.CurrentHp==21 and eb.CurrentHp==26 and pb.AttackBuffHits==0 and b._T.RelicDamageContext==nil)
    assert(#a.HitEffects==1 and #b.HitEffects==0)
end)
print(tostring(checks)..' damage/support regressions passed')
''')
