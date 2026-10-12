"""Execute hostile effects, poison hazards and modifiers with their real unit methods."""
from pathlib import Path
import os
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime
from battle_refactor_fixture import wire_logic_owners

ROOT = Path(__file__).resolve().parents[2]
COMBAT = ROOT / "RootDesk/MyDesk/01_Combat"
lua = LuaRuntime(unpack_returned_tuples=True)
wire_logic_owners(lua)


def load(path, names=None):
    result = lua.table()
    if not path.exists():
        return result
    source = path.read_text(encoding="utf-8-sig").expandtabs(4)
    for name, parameters, body in re.findall(r"^    method \w+ (\w+)\(([^\n]*)\)\n(.*?)^    end$", source, re.M | re.S):
        if names is None or name in names:
            args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
            result[name] = lua.eval("function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend")
    if names is not None:
        assert set(result.keys()) == names
    return result


g = lua.globals()
g.Session = load(Path(os.environ.get("ORIGINAL_SESSION", COMBAT / "Components/Shared/BattleSessionComponent.mlua")), {
    "IsHostileStatusEffect", "ExecuteEnemySpecialEffect", "ClearPoisonMists", "RemovePoisonMistsForSource",
    "PublishPoisonMistCells", "AdvancePoisonMists", "IsCombatModifierEffect", "ExecuteCombatModifier", "ApplyPoisonOnMove",
})
g._EnemySpecialEffectExecutorLogic = load(COMBAT / "Skills/EffectExecutors/EnemySpecialEffectExecutorLogic.mlua")
g._CombatModifierEffectExecutorLogic = load(COMBAT / "Skills/EffectExecutors/CombatModifierEffectExecutorLogic.mlua")
g._EffectRouterLogic = load(COMBAT / "Resolvers/EffectRouterLogic.mlua", {"ExecuteEffectStep"})
g.Unit = load(COMBAT / "Components/Shared/BattleUnitComponent.mlua", {"ApplyHostileStatus", "ApplyPoison", "ApplySeal"})
lua.execute(r'''
function isvalid(v) return v~=nil and v.Valid~=false end
function log(_) end
log_warning=log; log_error=log
_SkillTargetResolverLogic={SelectEffectTargets=function(_,c) return c.TargetUnitIds or {} end}
_UtilLogic={RandomIntegerRange=function() return 50 end}
for _,owner in ipairs({_EnemySpecialEffectExecutorLogic,_CombatModifierEffectExecutorLogic}) do
    setmetatable(owner,{__newindex=function(_,key) error('shared battle state '..key) end})
end

function fixture()
    local s=setmetatable({_T={PoisonMists={}},Units={},BattleResult='',TeamTurn='Enemy',PoisonMistCellSnapshot='',Damage={}}, {__index=Session})
    function s:add(id,team,cell)
        local u=setmetatable({UnitId=id,Team=team,CellIndex=cell,IsDead=false,IsAirborne=false,CurrentHp=10,
            BurnDamage=0,BurnTurns=0,BurnSourceUnitId='',SealTurns=0,FrostbiteTurns=0,ConfuseTurns=0,
            PoisonDamage=0,PoisonSourceUnitId='',PoisonMarkerRuid='',StopActionTurns=0,NextArrowCount=0}, {__index=Unit})
        local e={Unit=u}; function e:GetComponent(_) return self.Unit end
        s.Units[id]=e; return e,u
    end
    s.PlayerEntity,s.Player=s:add('player_01','Player',2)
    s.EnemyEntity,s.Enemy=s:add('enemy','Enemy',4)
    function s:FindUnitEntity(id) return self.Units[id] end
    function s:IsTeamTurn(team) return team==self.TeamTurn end
    function s:IsValidCell(cell) return cell>=0 and cell<5 end
    function s:PlayActiveHitEffect(id) self.HitEffect=id end
    function s:ApplyDamage(source,target,amount,attack)
        table.insert(self.Damage,{Source=source,Target=target,Amount=amount,Attack=attack})
        local u=self.Units[target].Unit; u.CurrentHp=math.max(0,u.CurrentHp-amount)
        if u.CurrentHp==0 then u.IsDead=true; self.BattleResult='Defeat' end
        return {Success=true,AppliedAmount=amount}
    end
    function s:ApplyStatusDamage(target,amount,source,attack) return self:ApplyDamage(source,target,amount,attack) end
    s.Runtime={Cooldown=6,GetRemainingCooldown=function(r) return r.Cooldown end,
        ReduceCooldown=function(r,skill,amount) r.Cooldown=math.max(0,r.Cooldown-amount); r.LastReduction=amount end}
    function s:GetSkillRuntimeState(_) return self.Runtime end
    function s:ResolvePushImpactOnTarget(source,target)
        self.Pushes=(self.Pushes or 0)+1
        return {Success=true,Hit=true,Reason=self.Pushes==2 and 'PUSH_BLOCKED_OCCUPIED' or 'PUSHED'}
    end
    return s
end
function context(s,source,targets)
    return {BattleSession=s,SourceUnitId=source or 'enemy',TargetUnitIds=targets or {'player_01'},
        TargetCellIndices={2},SkillId='test',PrimaryTargetUnitId='player_01',Definition={}}
end
function step(kind,value,turns) return {EffectType=kind,Value=value or 1,ParameterA=tostring(turns or 2),TargetSelector='TARGET',StepIndex=1} end
local checks=0
function check(label,f) f(); checks=checks+1; print('PASS '..label) end

check('hostile effects reject wrong team, turn, dead caster and invalid duration',function()
    local s=fixture(); local c=context(s)
    s.TeamTurn='Player'; assert(s:ExecuteEnemySpecialEffect(c,step('SEAL')).Reason=='INVALID_HOSTILE_EFFECT_SOURCE')
    s.TeamTurn='Enemy'; s.Enemy.IsDead=true
    assert(not s:ExecuteEnemySpecialEffect(c,step('SEAL')).Success)
    s.Enemy.IsDead=false; assert(s:ExecuteEnemySpecialEffect(c,step('SEAL',1,0)).Reason=='INVALID_HOSTILE_EFFECT_DURATION')
    assert(not s:ExecuteEnemySpecialEffect(context(s,'player_01'),step('SEAL')).Success and s.Player.SealTurns==0)
end)
check('hostile control uses actual mutual exclusion and timed burn refresh',function()
    local s=fixture(); local c=context(s)
    assert(s:ExecuteEnemySpecialEffect(c,step('FROSTBITE',1,3)).Hit and s.Player.FrostbiteTurns==3)
    assert(not s:ExecuteEnemySpecialEffect(c,step('CONFUSE')).Hit and s.Player.ConfuseTurns==0)
    assert(s:ExecuteEnemySpecialEffect(c,step('IGNITE',2,3)).Hit)
    s:ExecuteEnemySpecialEffect(c,step('IGNITE',1,1))
    assert(s.Player.BurnDamage==2 and s.Player.BurnTurns==3 and s.Player.BurnSourceUnitId=='enemy')
end)
check('seal refreshes only living player snapshot targets',function()
    local s=fixture(); local _,friend=s:add('friend','Enemy',3)
    local c=context(s,'enemy',{'player_01','friend','missing'})
    assert(s:ExecuteEnemySpecialEffect(c,step('SEAL',1,3)).Hit and s.Player.SealTurns==3 and friend.SealTurns==0)
    s:ExecuteEnemySpecialEffect(c,step('SEAL',1,1)); assert(s.Player.SealTurns==3)
    s.Player.IsDead=true; assert(not s:ExecuteEnemySpecialEffect(c,step('SEAL')).Hit)
end)
check('mist refresh replaces only its caster and publishes unique valid cells',function()
    local s=fixture(); s:add('other','Enemy',3)
    local c=context(s); c.TargetCellIndices={-1,2,2,5}
    assert(s:ExecuteEnemySpecialEffect(c,step('POISON_MIST',1,3)).Success)
    assert(s.PoisonMistCellSnapshot=='2' and #s._T.PoisonMists==1)
    s:ExecuteEnemySpecialEffect(context(s,'other'),step('POISON_MIST',1,2))
    c.TargetCellIndices={1}; s:ExecuteEnemySpecialEffect(c,step('POISON_MIST',2,4))
    assert(#s._T.PoisonMists==2 and s.PoisonMistCellSnapshot=='2|1')
end)
check('mist ticks once per hazard after movement and expires at its duration',function()
    local s=fixture(); local c=context(s); c.TargetCellIndices={2,2}
    s:ExecuteEnemySpecialEffect(c,step('POISON_MIST',1,2)); s:AdvancePoisonMists()
    assert(s.Player.CurrentHp==9 and #s.Damage==1 and s._T.PoisonMists[1].Turns==1)
    s.Player.CellIndex=1; s:AdvancePoisonMists()
    assert(s.Player.CurrentHp==9 and #s._T.PoisonMists==0 and s.PoisonMistCellSnapshot=='')
end)
check('airborne player avoids the tick while hazard duration advances',function()
    local s=fixture(); s:ExecuteEnemySpecialEffect(context(s),step('POISON_MIST',1,1))
    s.Player.IsAirborne=true; s:AdvancePoisonMists()
    assert(#s.Damage==0 and s.PoisonMistCellSnapshot=='')
end)
check('dead caster and explicit death cleanup remove its mist without damaging',function()
    local s=fixture(); s:ExecuteEnemySpecialEffect(context(s),step('POISON_MIST',1,3))
    s.Enemy.IsDead=true; s:AdvancePoisonMists(); assert(#s.Damage==0 and #s._T.PoisonMists==0)
    s.Enemy.IsDead=false; s:ExecuteEnemySpecialEffect(context(s),step('POISON_MIST',1,3))
    s:RemovePoisonMistsForSource('enemy'); assert(s.PoisonMistCellSnapshot=='')
end)
check('lethal tick stops later hazards and reset releases all state',function()
    local s=fixture(); s:add('other','Enemy',3); s.Player.CurrentHp=1
    s:ExecuteEnemySpecialEffect(context(s),step('POISON_MIST',1,3))
    s:ExecuteEnemySpecialEffect(context(s,'other'),step('POISON_MIST',1,3))
    s:AdvancePoisonMists(); assert(#s.Damage==1 and s.BattleResult=='Defeat' and #s._T.PoisonMists==0)
    s._T.PoisonMists={{Cells={2}}}; s.PoisonMistCellSnapshot='2'; s:ClearPoisonMists()
    assert(#s._T.PoisonMists==0 and s.PoisonMistCellSnapshot=='')
end)
check('modifier poison stacks are capped and movement tick retains its source',function()
    local s=fixture(); local c=context(s,'player_01',{'enemy'})
    for i=1,3 do s:ExecuteCombatModifier(c,step('POISON',2)) end
    assert(s.Enemy.PoisonDamage==5 and s.Enemy.PoisonSourceUnitId=='player_01')
    s:ApplyPoisonOnMove('enemy'); assert(#s.Damage==1 and s.Damage[1].Amount==5 and s.Damage[1].Source=='player_01')
    s.BattleResult='Victory'; s:ApplyPoisonOnMove('enemy'); assert(#s.Damage==1)
end)
check('freeze probability, stun refresh and indefinite burn preserve actual unit state',function()
    local s=fixture(); local c=context(s,'player_01',{'enemy'})
    assert(not s:ExecuteCombatModifier(c,step('FREEZE',0)).Hit and s.Enemy.StopActionTurns==0)
    s:ExecuteCombatModifier(c,step('FREEZE',100,3)); s:ExecuteCombatModifier(c,step('STUN',100,1))
    assert(s.Enemy.StopActionTurns==3 and s.Enemy.StopMarkerRuid=='602b777092204ca7a4b191d538b72de9')
    s:ExecuteCombatModifier(c,step('BURN',3)); s:ExecuteCombatModifier(c,step('BURN',1))
    assert(s.Enemy.BurnDamage==3 and s.Enemy.BurnTurns==0 and s.Enemy.BurnSourceUnitId=='player_01')
end)
check('cooldown reduction respects combo floor and next arrow keeps the larger count',function()
    local s=fixture(); local c=context(s,'player_01'); c.Definition.AugmentCooldownFloor=4
    s:ExecuteCombatModifier(c,step('REDUCE_OWN_COOLDOWN',5)); assert(s.Runtime.Cooldown==4 and s.Runtime.LastReduction==2)
    s:ExecuteCombatModifier(c,step('REDUCE_OWN_COOLDOWN',5)); assert(s.Runtime.Cooldown==4)
    s:ExecuteCombatModifier(c,step('NEXT_ARROW',3)); s:ExecuteCombatModifier(c,step('NEXT_ARROW',1))
    assert(s.Player.NextArrowCount==3 and s.Player.NextArrowSkillId=='test')
end)
check('adjacent push stops at a blocker and ignores distant or dead targets',function()
    local s=fixture(); s.Enemy.CellIndex=3; local c=context(s,'player_01',{'enemy'})
    assert(s:ExecuteCombatModifier(c,step('PUSH_ADJACENT',5)).Hit and s.Pushes==2)
    s.Enemy.CellIndex=4; s:ExecuteCombatModifier(c,step('PUSH_ADJACENT',5)); assert(s.Pushes==2)
    s.Enemy.CellIndex=3; s.Enemy.IsDead=true; assert(not s:ExecuteCombatModifier(c,step('POISON',2)).Hit)
    s.Player.IsDead=true; assert(s:ExecuteCombatModifier(c,step('NEXT_ARROW',2)).Reason=='SOURCE_DEAD')
end)
check('actual router dispatches modifier and hostile paths with metadata',function()
    local s=fixture()
    local a=_EffectRouterLogic:ExecuteEffectStep(context(s,'player_01',{'enemy'}),step('POISON',2))
    assert(a.Success and a.Hit and a.EffectType=='POISON' and a.StepIndex==1 and s.Enemy.PoisonDamage==2)
    local b=_EffectRouterLogic:ExecuteEffectStep(context(s),step('CONFUSE',1,2))
    assert(b.Success and b.Hit and b.EffectType=='CONFUSE' and s.Player.ConfuseTurns==2)
end)
check('two sessions have independent hazards, snapshots and modifier state',function()
    local a=fixture(); local b=fixture()
    a:ExecuteEnemySpecialEffect(context(a),step('POISON_MIST',1,3))
    b:ExecuteCombatModifier(context(b,'player_01',{'enemy'}),step('POISON',2))
    assert(#b._T.PoisonMists==0 and b.PoisonMistCellSnapshot=='' and a.Enemy.PoisonDamage==0)
    a:ClearPoisonMists(); assert(b.Enemy.PoisonDamage==2)
end)
print(checks..' status-effect regressions passed')
''')
