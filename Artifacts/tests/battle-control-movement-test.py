"""Run the actual control/movement rules and their session/executor callers."""
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
    "ResolvePushImpact", "ResolvePushImpactOnTarget", "ResolvePullImpactOnTarget", "ResolveTurnImpactOnTarget",
    "ResolveSkillMoveImpact", "RelocateUnitForMechanic", "TryMoveInternal", "TryMoveAwayInternal",
    "TryChargeForward", "TryTurn", "GetChargeDamage", "PlaceEntity", "FinishPlayerGridMovePresentation",
})
g._BattleMovementLogic = load(COMBAT / "Resolvers/BattleMovementLogic.mlua")
g._PushEffectExecutorLogic = load(COMBAT / "Skills/EffectExecutors/PushEffectExecutorLogic.mlua")
g._MoveSelfEffectExecutorLogic = load(COMBAT / "Skills/EffectExecutors/MoveSelfEffectExecutorLogic.mlua")
g.Unit = load(COMBAT / "Components/Shared/BattleUnitComponent.mlua", {"ApplyCellChange", "ApplyFacingState"})
lua.execute(r'''
function isvalid(v) return v~=nil and v.Valid~=false end
function log(_) end
log_warning=log; log_error=log
function Vector2(x,y) return {x=x,y=y} end
function Vector3(x,y,z) return {x=x,y=y,z=z} end
function UnitMovedEvent() return {Kind='MOVE'} end
function UnitTurnedEvent() return {Kind='TURN'} end
_EnemyTraitRouterLogic={BlocksForcedDisplacement=function(_,traits) return traits=='HEAVY' end}
_SkillTargetResolverLogic={SelectEffectTargets=function(_,context) return context.TargetUnitIds end}
_SkillDefinitionRepositoryLogic={GetSkillDefinition=function(_,id)
    return {Success=id=='charge',Range=3,ActionDuration=.4,CasterMotionRuid='motion'} end,
    GetEffectSteps=function() return {Success=true,Steps={{EffectType='DAMAGE',Value=0,ParameterA='SOURCE_BASIC_ATTACK'}}} end}
for _,owner in ipairs({_BattleMovementLogic,_PushEffectExecutorLogic,_MoveSelfEffectExecutorLogic}) do
    setmetatable(owner,{__newindex=function(_,key) error('shared battle state '..key) end})
end

function fixture()
    local s=setmetatable({_T={},Units={},Events={},BattleResult='',TeamTurn='Player',CellSpacing=1,UnitY=0,
        SelectedJobMechanicId='NONE',JobMechanicRevision=0,EntryRequestId=1,ActionTimerId=0}, {__index=Session})
    s.Entity={SendEvent=function(_,e) table.insert(s.Events,e) end}
    function s:add(id,team,cell,facing)
        local u=setmetatable({UnitId=id,Team=team,CellIndex=cell,Facing=facing or 'Right',IsDead=false,
            IsAirborne=false,EnemyTraitIds='',BasicAttackDamage=3}, {__index=Unit})
        local e={Name=id,CurrentMap=s.Entity,TransformComponent={Position=Vector3(cell,0,0)},Components={['script.BattleUnitComponent']=u}}
        function e:GetComponent(n) return self.Components[n] end
        u.Entity=e; s.Units[id]=e; return e,u
    end
    s.PlayerEntity,s.PlayerUnit=s:add('player_01','Player',2)
    s.PlayerEntity.PlayerComponent={UserId='owner'}
    s.PlayerEntity.MovementComponent={SetPosition=function(_,p) s.PlayerEntity.TransformComponent.Position=Vector3(p.x,p.y,0); s.PositionWrites=(s.PositionWrites or 0)+1 end}
    function s:FindUnitEntity(id) return self.Units[id] end
    function s:IsTeamTurn(team) return team==self.TeamTurn end
    function s:IsValidCell(cell) return cell>=0 and cell<7 end
    s.BoardState={FindAtCell=function(_,cell,exclude)
        for id,e in pairs(s.Units) do local u=e:GetComponent('script.BattleUnitComponent')
            if id~=exclude and not u.IsDead and u.CellIndex==cell then return e end end end}
    function s:IsCellOccupied(cell,id) return isvalid(self.BoardState:FindAtCell(cell,id)) end
    function s:ResolveFrontTarget(id) local u=self.Units[id]:GetComponent('script.BattleUnitComponent')
        return self.BoardState:FindAtCell(u.CellIndex+(u.Facing=='Right' and 1 or -1),id) end
    function s:GetCellPosition(cell) return Vector2(cell,0) end
    function s:ApplyFacing(e,f) e.VisualFacing=f end
    function s:PlayActiveHitEffect(id) self.HitEffects=(self.HitEffects or 0)+1; self.LastHit=id end
    function s:ApplyPushCollisionDamage(source,target,cell) self.Collision={Source=source,Target=target.UnitId,Cell=cell} end
    function s:CollectDropsForMovedUnit(u,cell) self.Pickup={Unit=u.UnitId,Cell=cell}; return {CollectedCount=1} end
    function s:StartPlayerGridMovePresentation(e,from,to) self.PlayerMove={Entity=e,From=from,To=to}; return true end
    function s:StartEnemyGridMovePresentation(e,from,to)
        if self.RefusePresentation then return false end
        self._T.enemyGridMove={Entity=e,FromCell=from,ToCell=to,StartPosition=Vector2(from,0),TargetPosition=Vector2(to,0)}
        return true
    end
    function s:PlayUnitMoveHop(e) e.Hopped=true end
    function s:ReceivePlayerMoveResult(id,entry,context,success,final,x,y,reason)
        self.MoveResponse={Id=id,Success=success,Final=final,X=x,Y=y,Reason=reason}
    end
    function s:SendMotionPresentation(e,kind,data) self.Motion={Entity=e,Kind=kind,Data=data} end
    function s:BeginSkillEffectPresentation(id,definition) self.SkillPresentation=id end
    function s:ResolveSkillDamageImpact(id,skill,target,cell,damage) self.ChargeHit={Source=id,Target=target,Cell=cell,Damage=damage} end
    return s
end
local checks=0
function check(label,f) f(); checks=checks+1; print('PASS '..label) end

check('front push validates source, turn, life and current target',function()
    local s=fixture(); assert(s:ResolvePushImpact('missing').Reason=='SOURCE_NOT_FOUND')
    s.TeamTurn='Enemy'; assert(s:ResolvePushImpact('player_01').Reason=='INVALID_PHASE')
    s.TeamTurn='Player'; s.PlayerUnit.IsDead=true; assert(s:ResolvePushImpact('player_01').Reason=='SOURCE_DEAD')
    s.PlayerUnit.IsDead=false; assert(s:ResolvePushImpact('player_01').Reason=='MISS_EMPTY')
    s.PlayerUnit.CellIndex=6; assert(s:ResolvePushImpact('player_01').Reason=='MISS_OUT_OF_BOUNDS')
end)
check('front push changes one logical cell before the moved event',function()
    local s=fixture(); local e,u=s:add('enemy','Enemy',3)
    local r=s:ResolvePushImpact('player_01')
    assert(r.Success and r.Hit and u.CellIndex==4 and r.FromCell==3 and r.ToCell==4)
    assert(e.TransformComponent.Position.x==4 and #s.Events==1 and s.Events[1].ToCell==4)
end)
check('selected push goes away from the caster on either side',function()
    for _,cell in ipairs({1,3}) do local s=fixture(); local _,u=s:add('enemy','Enemy',cell)
        local r=s:ResolvePushImpactOnTarget('player_01','enemy')
        assert(r.Success and u.CellIndex==(cell==1 and 0 or 4) and s.HitEffects==1)
    end
end)
check('heavy and board edge are successful impacts without displacement',function()
    local s=fixture(); local _,u=s:add('enemy','Enemy',3); u.EnemyTraitIds='HEAVY'
    assert(s:ResolvePushImpactOnTarget('player_01','enemy').Reason=='PUSH_BLOCKED_HEAVY_TRAIT' and u.CellIndex==3)
    u.EnemyTraitIds=''; u.CellIndex=6
    assert(s:ResolvePushImpactOnTarget('player_01','enemy').Reason=='PUSH_BLOCKED_OUT_OF_BOUNDS' and #s.Events==0)
end)
check('occupied push keeps both cells and calls shared collision damage',function()
    local s=fixture(); local _,u=s:add('enemy','Enemy',3); local _,b=s:add('blocker','Enemy',4)
    assert(s:ResolvePushImpactOnTarget('player_01','enemy').Reason=='PUSH_BLOCKED_OCCUPIED')
    assert(u.CellIndex==3 and b.CellIndex==4 and s.Collision.Target=='enemy' and s.Collision.Cell==4 and #s.Events==0)
end)
check('control rejects dead and same-team player targets',function()
    local s=fixture(); local _,u=s:add('friend','Player',3)
    assert(s:ResolvePushImpactOnTarget('player_01','friend').Reason=='TARGET_SAME_TEAM')
    assert(s:ResolvePullImpactOnTarget('player_01','friend',1).Reason=='TARGET_SAME_TEAM')
    assert(s:ResolveTurnImpactOnTarget('player_01','friend').Reason=='TARGET_SAME_TEAM')
    u.IsDead=true; assert(s:ResolvePushImpactOnTarget('player_01','friend').Reason=='UNIT_DEAD')
end)
check('pull lands in the nearest available authored cell and collects drops',function()
    local s=fixture(); local _,u=s:add('enemy','Enemy',6); s:add('blocker','Enemy',3)
    local r=s:ResolvePullImpactOnTarget('player_01','enemy',1)
    assert(r.Reason=='PULLED' and u.CellIndex==4 and s.Pickup.Unit=='enemy' and s.Events[1].FromCell==6)
end)
check('pull blocked, already close and heavy outcomes never move',function()
    local s=fixture(); local _,u=s:add('enemy','Enemy',4); s:add('blocker','Enemy',3)
    assert(s:ResolvePullImpactOnTarget('player_01','enemy',1).Reason=='PULL_BLOCKED_OCCUPIED')
    u.CellIndex=3; assert(s:ResolvePullImpactOnTarget('player_01','enemy',1).Reason=='PULL_ALREADY_CLOSE')
    u.EnemyTraitIds='HEAVY'; assert(s:ResolvePullImpactOnTarget('player_01','enemy',1).Reason=='PULL_BLOCKED_HEAVY_TRAIT')
    assert(#s.Events==0)
end)
check('target turn uses caster timing and flips presentation in place',function()
    local s=fixture(); local e,u=s:add('enemy','Enemy',3,'Left'); local marks=0
    e.Components['script.BattleUnitPresentationComponent']={ShowConfusionMarker=function() marks=marks+1 end}
    local r=s:ResolveTurnImpactOnTarget('player_01','enemy')
    assert(r.Hit and r.CurrentFacing=='Right' and u.CellIndex==3 and e.VisualFacing=='Right' and marks==1)
    assert(s.Events[1].Kind=='TURN' and s.Events[1].PreviousFacing=='Left')
end)
check('control executor dispatches actual push, pull and turn rules',function()
    for _,kind in ipairs({'PUSH','PULL','TURN_TARGET'}) do
        local s=fixture(); local _,u=s:add('enemy','Enemy',5,'Left')
        local r=_PushEffectExecutorLogic:Execute({BattleSession=s,SourceUnitId='player_01',TargetUnitIds={'enemy'}},{EffectType=kind,Value=1})
        assert(r.Success and r.Hit and #r.Results==1)
        assert((kind=='PUSH' and u.CellIndex==6) or (kind=='PULL' and u.CellIndex==3) or (kind=='TURN_TARGET' and u.Facing=='Right'))
    end
end)
check('skill move applies signed offset along facing',function()
    for _,f in ipairs({'Left','Right'}) do for _,offset in ipairs({-1,1}) do
        local s=fixture(); s.PlayerUnit.Facing=f
        local r=s:ResolveSkillMoveImpact('player_01','dash',offset,true)
        local destination=2+(f=='Right' and 1 or -1)*offset
        assert(r.Success and r.Moved and s.PlayerUnit.CellIndex==destination and s.PlayerMove.To==destination)
        assert(s.PositionWrites==1 and s.Pickup.Cell==destination and #s.Events==1)
    end end
end)
check('skill move rejects invalid input but blocked landing preserves the cast',function()
    local s=fixture(); assert(s:ResolveSkillMoveImpact('player_01','dash',0,true).Reason=='INVALID_MOVE_OFFSET')
    local r=s:ResolveSkillMoveImpact('player_01','dash',8,true); assert(r.Success and not r.Moved and r.Reason=='MOVE_OUT_OF_BOUNDS')
    s:add('enemy','Enemy',3); r=s:ResolveSkillMoveImpact('player_01','dash',1,true)
    assert(r.Success and not r.Moved and r.Reason=='MOVE_CELL_OCCUPIED')
    r=s:ResolveSkillMoveImpact('player_01','dash',1,false)
    assert(r.Success and not r.Moved and r.Reason=='MOVE_BLOCKED_CELL_OCCUPIED' and s.PlayerUnit.CellIndex==2)
end)
check('forced relocation cancels an older client move and landing check',function()
    local s=fixture(); local request={Player=s.PlayerEntity,Id=7,Entry=1,Context='old'}
    s._T.lastPlayerMoveRequest=request; s._T.playerGridLandingCheck={ToCell=3}
    s._T.playerGridMove={Entity=s.PlayerEntity,ClientDriven=true,TargetPosition=Vector2(3,0),FromCell=2,ToCell=3,RequestId=7,Entry=1,Context='old',UserId='owner'}
    local r=s:RelocateUnitForMechanic('player_01',0,'FORCED')
    assert(r.Success and request.Cancelled and s._T.playerGridMove==nil and s._T.playerGridLandingCheck==nil)
    assert(s.MoveResponse.Id==7 and not s.MoveResponse.Success and s.MoveResponse.X==3 and s.PositionWrites==1)
    assert(s.PlayerUnit.CellIndex==0 and s.PlayerEntity.TransformComponent.Position.x==0)
    assert(s:TryMoveInternal('player_01',1,false).Success and s.PlayerMove.From==0 and s.PlayerMove.To==1)
end)
check('move validates bounds, occupancy, phase and life without writes',function()
    local s=fixture(); s:add('enemy','Enemy',3)
    assert(s:TryMoveInternal('player_01',0,false).Reason=='INVALID_DIRECTION')
    assert(s:TryMoveInternal('player_01',1,false).Reason=='CELL_OCCUPIED')
    s.PlayerUnit.CellIndex=0; assert(s:TryMoveInternal('player_01',-1,false).Reason=='OUT_OF_BOUNDS')
    s.TeamTurn='Enemy'; assert(s:TryMoveInternal('player_01',1,false).Reason=='INVALID_PHASE')
    s.TeamTurn='Player'; s.PlayerUnit.IsDead=true; assert(s:TryMoveInternal('player_01',1,false).Reason=='UNIT_DEAD')
    assert(#s.Events==0 and s.PositionWrites==nil)
end)
check('ordinary player movement uses the common presentation without server position writes',function()
    local s=fixture(); local r=s:TryMoveInternal('player_01',-1,false)
    assert(r.Success and r.PresentationStarted and s.PlayerUnit.CellIndex==1 and s.PlayerUnit.Facing=='Right')
    assert(s.PositionWrites==nil and s.PlayerMove.From==2 and s.PlayerMove.To==1 and s.Pickup.Cell==1)
end)
check('move-away is atomic on blocked destination and failed cell mutation',function()
    local s=fixture(); s.TeamTurn='Enemy'; local e,u=s:add('enemy','Enemy',0,'Right')
    assert(s:TryMoveAwayInternal('enemy',-1,true).Reason=='OUT_OF_BOUNDS' and u.Facing=='Right')
    u.CellIndex=4; u.ApplyCellChange=function() return {Success=false,Reason='REFUSED'} end
    assert(s:TryMoveAwayInternal('enemy',-1,true).Reason=='REFUSED' and u.Facing=='Right' and e.VisualFacing=='Right')
    assert(#s.Events==0)
end)
check('enemy move-away changes facing and cell with smooth presentation',function()
    local s=fixture(); s.TeamTurn='Enemy'; local _,u=s:add('enemy','Enemy',4,'Right')
    local r=s:TryMoveAwayInternal('enemy',-1,true)
    assert(r.Success and r.PresentationStarted and u.CellIndex==3 and u.Facing=='Left')
    assert(s._T.enemyGridMove.ToCell==3 and #s.Events==2 and s.Events[1].Kind=='MOVE' and s.Events[2].Kind=='TURN')
end)
check('charge follows the committed lane and hits its current occupant',function()
    local s=fixture(); s.TeamTurn='Enemy'; local e,u=s:add('charger','Enemy',0); s.PlayerUnit.CellIndex=3
    local r=s:TryChargeForward('charger',1,'charge','1|2|3|4')
    assert(r.Success and r.ToCell==2 and r.TargetUnitId=='player_01' and r.TraversedCells=='1|2')
    assert(u.CellIndex==2 and s._T.enemyGridMove.IsCharge and s._T.enemyGridMove.Height==0)
    s._T.enemyGridMove.Impact(); assert(s.ChargeHit.Cell==3 and s.ChargeHit.Damage==3)
    u.IsDead=true; s.ChargeHit=nil; s._T.enemyGridMove.Impact(); assert(s.ChargeHit==nil)
end)
check('charge rejects absent snapshot and rolls back unavailable presentation',function()
    local s=fixture(); s.TeamTurn='Enemy'; local _,u=s:add('charger','Enemy',0)
    assert(s:TryChargeForward('charger',1,'charge','').Reason=='CHARGE_TARGET_SNAPSHOT_MISSING')
    s.RefusePresentation=true
    assert(s:TryChargeForward('charger',1,'charge','1|2').Reason=='CHARGE_PRESENTATION_UNAVAILABLE' and u.CellIndex==0)
end)
check('movement and control owners keep independent session state',function()
    local a=fixture(); local b=fixture(); a:add('enemy','Enemy',3); b:add('enemy','Enemy',5)
    a:ResolvePushImpactOnTarget('player_01','enemy'); b:ResolvePullImpactOnTarget('player_01','enemy',1)
    assert(a.Units.enemy:GetComponent('script.BattleUnitComponent').CellIndex==4)
    assert(b.Units.enemy:GetComponent('script.BattleUnitComponent').CellIndex==3)
    assert(#a.Events==1 and #b.Events==1)
end)
print(checks..' control/movement regressions passed')
''')
