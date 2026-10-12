"""Exercise the remaining action, boss and entry boundaries using production bodies."""
from pathlib import Path
import os, re, sys
if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime
from battle_refactor_fixture import wire_logic_owners

ROOT = Path(__file__).resolve().parents[2]
lua = LuaRuntime(unpack_returned_tuples=True)
wire_logic_owners(lua)
source = Path(os.environ.get("ORIGINAL_SESSION", ROOT / "RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua")).read_text(encoding="utf-8-sig").expandtabs(4)
names = {"OnUpdate", "GetOppositeEdgeCell", "BeginBossOppositeJump", "ResolveBossOppositeLanding", "RollBoardParity", "GetBoardParity", "NotifyBossPhaseAdvanced", "TryQueuePlayerAction", "ExecuteQueuedAction", "GetActionDuration", "CompleteQueuedAction", "AdvancePlayerSkillCooldowns", "AdvanceEnemySkillCooldowns", "GetCellPosition", "GetBoardCenterX"}
names.update({"IsTeamTurn", "GetFacingDirection", "GetTileActionType", "GetSkillSpeedMultiplier", "FlushDamageNumberBatch", "GetPlayerHopDuration"})
methods = lua.table()
for name, parameters, body in re.findall(r"^    method \w+ (\w+)\(([^\n]*)\)\n(.*?)^    end$", source, re.M | re.S):
    if name in names:
        args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
        methods[name] = lua.eval("function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend")
assert set(methods.keys()) == names
lua.globals().M = methods
movement_source = (ROOT / "RootDesk/MyDesk/00_Core/Movement/PlayerGridMovementLogic.mlua").read_text(encoding="utf-8-sig").expandtabs(4)
movement = lua.table()
for name, parameters, body in re.findall(r"^    method \w+ (\w+)\(([^\n]*)\)\n(.*?)^    end$", movement_source, re.M | re.S):
    if name in {"GetHopDuration", "GetDuration"}:
        args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
        movement[name] = lua.eval("function(self," + ",".join(args) + ")\n" + body + "\nend")
assert set(movement.keys()) == {"GetHopDuration", "GetDuration"}
lua.globals()._PlayerGridMovementLogic = movement
lua.execute(r'''
function isvalid(v) return v~=nil and v.Valid~=false end
function log(_) end
log_warning=log
function Vector2(x,y) return {x=x,y=y} end
local checks=0
function check(name,f) f(); checks=checks+1; print('PASS '..name) end
function fixture()
 local s=setmetatable({_T={},Entity={MapComponent={}},CellCount=7,CellStartX=-3,CellSpacing=1.2,UnitY=.4,
  EntryPolicyResolved=true,StageId='stage',BattleResult='',BattlePhase='PlayerTurn',ActionTimerId=0,MoveCompletionFallbackGrace=.02,
  PlayerTurnActionDuration=.2,PushActionDuration=.3,UtilitySkillId='guard',UtilityRemainingCooldown=2,
  Calls={},Units={}}, {__index=M})
 function s:FindUnitEntity(id) return self.Units[id] end
 function s:IsValidCell(cell) return cell>=0 and cell<self.CellCount end
 function s:IsCellOccupied(cell,id) return self.Occupied==cell end
 function s:OnMapEnter(player) self.Entered=player; self.EntryPolicyResolved=true end
 function s:UpdatePrototypeBattleEntryRetry(delta) self.RetryDelta=delta end
 for _,name in ipairs({'UpdatePlayerGridLandingCheck','UpdatePlayerGridMove','UpdateEnemyGridMove','RefreshHudProgressSnapshot','RefreshPlayerHpSnapshot','RefreshHudRelicSnapshot'}) do
  s[name]=function(self) self.Calls[name]=(self.Calls[name] or 0)+1 end
 end
 function s:PublishWaveStateSnapshot(reason) self.WaveReason=reason end
 function s:PublishTurnStateSnapshot(reason) self.TurnReason=reason end
 function s:IsTutorialCommandAllowed() return not self.Guided end
 function s:IsPlayerFrostbitten() return self.Frozen==true end
 function s:TryMove() return self.MoveResult or {Success=true,Reason='OK'} end
 function s:GetPlayerMoveDuration() return .35 end
 function s:TryTurn() return {Success=true,Reason='OK'} end
 function s:FinishPlayerGridMovePresentation() self.MoveFinished=(self.MoveFinished or 0)+1 end
 function s:BeginEnemyTurnFromPlayerAction() self.EnemyTurns=(self.EnemyTurns or 0)+1 end
 s.TurnState={QueuedActionType='',QueuedActionDirection=0}
 function s.TurnState:TryReserveImmediateAction(action,direction)
  if self.QueuedActionType~='' then return {Success=false,Reason='BUSY'} end
  self.QueuedActionType=action; self.QueuedActionDirection=direction; return {Success=true}
 end
 function s.TurnState:CompleteImmediateAction() self.QueuedActionType='' end
 _TimerService={SetTimerOnce=function(_,f,d) s.Timer=f; s.Delay=d; return 1 end}
 _UserService={GetUsersByMapComponent=function() s.Scans=(s.Scans or 0)+1; return s.Users end}
 _BattleGatewayLogic={ValidatePreparedBattleDestination=function() return {Success=not s.InvalidDestination} end}
 _UtilLogic={RandomIntegerRange=function() s.Rolls=(s.Rolls or 0)+1; return s.Rolls%2 end}
 local p={CurrentMap=s.Entity,GetComponent=function(_,name) return s.Entry end}
 s.PlayerEntity=p
 return s,p
end
function unit(s,id,cell,boss)
 local u={UnitId=id,CellIndex=cell,IsBoss=boss==true,IsDead=false,IsAirborne=false,PendingLandingCell=-1}
 function u:SetAirborneState(active,landing) self.IsAirborne=active; self.PendingLandingCell=landing; return {Success=true} end
 function u:ApplyCellChange(next) if self.FailCell then return {Success=false,Reason='CELL_FAILED'} end; self.CellIndex=next; return {Success=true} end
 function u:ApplyFacingState(facing) self.Facing=facing; return {Success=true} end
 local e={GetComponent=function() return u end}
 s.Units[id]=e
 function s:PlaceEntity(entity,pos) self.Placed={entity,pos} end
 function s:ApplyFacing(entity,facing) self.Facing=facing end
 function s:RelocateUnitForMechanic(id,destination,reason)
  self.Pushes=(self.Pushes or 0)+1
  if self.BlockCenter and self.Pushes==1 then return {Success=false,Reason='OCCUPIED'} end
  if self.BlockAll then return {Success=false,Reason='OUT_OF_BOUNDS'} end
  local p=self.Units[id]:GetComponent(); local from=p.CellIndex; p.CellIndex=destination
  return {Success=true,FromCell=from,ToCell=destination}
 end
 function s:TryExecuteSkill() self.Impacts=(self.Impacts or 0)+1; return {Success=true,Reason='OK'} end
 return u,e
end
check('entry retries suspend all presentation updates',function()
 local s=fixture(); s.PrototypeTestEntryPending=true; s:OnUpdate(.05); assert(s.RetryDelta==.05 and s.Scans==nil and next(s.Calls)==nil)
end)
check('unresolved entry polls once and dispatches before gameplay',function()
 local s,p=fixture(); s.EntryPolicyResolved=false; s.Users={p}; s:OnUpdate(.01)
 assert(s.Entered==p and s.Scans==1 and next(s.Calls)==nil)
end)
check('inactive static maps throttle scans and clear presentation state',function()
 local s,p=fixture(); p.CurrentMap={}; s._T.playerGridMove={}; s._T.HudRelicCache={}; s.HudRelicSnapshot='old'
 s:OnUpdate(.01); s:OnUpdate(.01); assert(s.Scans==1 and s.HudRelicSnapshot=='' and s._T.HudRelicCache==nil and s.Calls.RefreshHudProgressSnapshot==nil)
end)
check('prepared rewards do not reenter until the matching transfer was requested',function()
 local s,p=fixture(); s.BattleResult='Victory'; s.Users={p}; s.Entry={EntryState='PREPARED',StageId='stage',RequestId=8,LastTransferRequestId=7}
 s:OnUpdate(.2); assert(s.Entered==nil)
 s.Entry.LastTransferRequestId=8; s:OnUpdate(.2); assert(s.Entered==p)
end)
check('wrong destination and already initialized requests cannot reenter',function()
 local s,p=fixture(); s.BattleResult='Victory'; s.Users={p}; s.Entry={EntryState='PREPARED',StageId='stage',RequestId=8,LastTransferRequestId=8}
 s.InvalidDestination=true; s:OnUpdate(.2); assert(s.Entered==nil)
 s.InvalidDestination=false; s.LastInitializedEntryRequestId=8; s:OnUpdate(.2); assert(s.Entered==nil)
end)
check('boss landing target is frozen at takeoff',function()
 local s=fixture(); local b=unit(s,'boss',0,true); unit(s,'player_01',2,false)
 assert(s:BeginBossOppositeJump('boss').Success and b.PendingLandingCell==6)
 b.CellIndex=4; assert(b.PendingLandingCell==6 and s:GetOppositeEdgeCell(3)==6 and s:GetOppositeEdgeCell(4)==0)
end)
check('missing dead and nonboss units cannot jump',function()
 local s=fixture(); assert(s:BeginBossOppositeJump('boss').Reason=='ENEMY_NOT_FOUND')
 local b=unit(s,'boss',0,false); assert(s:BeginBossOppositeJump('boss').Reason=='BOSS_UNAVAILABLE')
 b.IsBoss=true; b.IsDead=true; assert(not s:BeginBossOppositeJump('boss').Success)
end)
check('landing center push occurs before the boss commits and attacks',function()
 local s=fixture(); local b=unit(s,'boss',6,true); local p=unit(s,'player_01',0,false); b.IsAirborne=true; b.PendingLandingCell=0
 local r=s:ResolveBossOppositeLanding('boss','impact'); assert(r.Success and r.PlayerPushed and p.CellIndex==1 and b.CellIndex==0 and not b.IsAirborne and b.PendingLandingCell==-1 and b.Facing=='Right' and s.Impacts==1)
end)
check('landing tries reverse push and preserves airborne state on unresolved overlap',function()
 local s=fixture(); local b=unit(s,'boss',6,true); unit(s,'player_01',1,false); b.IsAirborne=true; b.PendingLandingCell=1; s.BlockCenter=true
 assert(s:ResolveBossOppositeLanding('boss','').Success and s.Pushes==2)
 s=fixture(); b=unit(s,'boss',6,true); unit(s,'player_01',0,false); b.IsAirborne=true; b.PendingLandingCell=0; s.BlockAll=true
 assert(not s:ResolveBossOppositeLanding('boss','impact').Success and b.IsAirborne and b.CellIndex==6 and s.Impacts==nil)
end)
check('occupied invalid and failed cell landing never attacks',function()
 local s=fixture(); local b=unit(s,'boss',0,true); unit(s,'player_01',2,false); b.IsAirborne=true; b.PendingLandingCell=8
 assert(s:ResolveBossOppositeLanding('boss','impact').Reason=='INVALID_LANDING_CELL')
 b.PendingLandingCell=6; s.Occupied=6; assert(s:ResolveBossOppositeLanding('boss','impact').Reason=='LANDING_CELL_OCCUPIED')
 s.Occupied=nil; b.FailCell=true; assert(s:ResolveBossOppositeLanding('boss','impact').Reason=='CELL_FAILED' and s.Impacts==nil and b.IsAirborne)
end)
check('board parity is frozen per unit and skill and isolated between sessions',function()
 local a=fixture(); local p=a:GetBoardParity('boss','attack'); assert(a:GetBoardParity('boss','attack')==p and a.Rolls==1)
 assert(a:GetBoardParity('other','attack')~=p and a.Rolls==2)
 local b=fixture(); assert(b:GetBoardParity('boss','attack')==p and b.Rolls==1 and a.Rolls==2)
end)
check('boss phase only publishes an armed reinforcement trigger',function()
 local s=fixture(); s:NotifyBossPhaseAdvanced(2); assert(s.WaveReason==nil)
 s.WaveRuntime={PendingWaveNumber=2,ApplyBossPhaseTrigger=function() return {Pended=false} end}; s:NotifyBossPhaseAdvanced(2); assert(s.WaveReason==nil)
 s.WaveRuntime.ApplyBossPhaseTrigger=function() return {Pended=true} end; s:NotifyBossPhaseAdvanced(2); assert(s.WaveReason=='BOSS_PHASE_SPAWN_PENDING')
end)
check('immediate action validates lesson direction and frostbite before reservation',function()
 local s=fixture(); s.Guided=true; assert(s:TryQueuePlayerAction('MOVE',1).Reason=='TUTORIAL_FOLLOW_GUIDE')
 s.Guided=false; assert(s:TryQueuePlayerAction('BAD',1).Reason=='INVALID_ACTION' and s:TryQueuePlayerAction('MOVE',0).Reason=='INVALID_DIRECTION')
 s.Frozen=true; assert(s:TryQueuePlayerAction('MOVE',1).Reason=='PLAYER_FROSTBITTEN' and s.TurnState.QueuedActionType=='')
end)
check('movement fallback keeps action occupied and duplicate completion cannot spend another turn',function()
 local s=fixture(); s._T.playerGridMove={}; s.MoveResult={Success=true,Reason='OK',PresentationStarted=true}
 assert(s:TryQueuePlayerAction('MOVE',1).Success and s.ActionTimerId==1 and s.Delay==.37 and s:TryQueuePlayerAction('MOVE',-1).Reason=='BUSY')
 s.Timer(); s:CompleteQueuedAction('MOVE',true,'DUPLICATE'); assert(s.EnemyTurns==1 and s.MoveFinished==1 and s.TurnState.QueuedActionType=='')
end)
check('rejected movement releases the action without advancing the enemy turn',function()
 local s=fixture(); s.MoveResult={Success=false,Reason='OCCUPIED'}; assert(not s:TryQueuePlayerAction('MOVE',1).Success and s.TurnState.QueuedActionType=='' and s.EnemyTurns==nil and s.Timer==nil)
end)
check('coordinate helpers retain world units and board center',function()
 local s=fixture(); assert(math.abs(s:GetCellPosition(2).x+.6)<.000001 and s:GetCellPosition(2).y==.4 and math.abs(s:GetBoardCenterX()-.6)<.000001)
end)
check('team phase predicate preserves every phase and rejects unknown teams',function()
 local s=fixture()
 for _,phase in ipairs({'Setup','PlayerTurn','EnemyTurn','Ended',''}) do
  s.BattlePhase=phase
  assert(s:IsTeamTurn('Player')==(phase=='PlayerTurn') and s:IsTeamTurn('Enemy')==(phase=='EnemyTurn'))
  assert(not s:IsTeamTurn('Other') and not s:IsTeamTurn('') and s.BattlePhase==phase)
 end
end)
check('facing conversion retains its exact fallback',function()
 local s=fixture(); assert(s:GetFacingDirection('Right')==1)
 for _,facing in ipairs({'Left','right','','Other'}) do assert(s:GetFacingDirection(facing)==-1) end
end)
check('tile action mapping accepts only an explicitly successful validator result',function()
 local s=fixture(); local seen={}
 _ContentValidatorLogic={ValidateSkillById=function(_,id)
  seen[#seen+1]=id; return {Success=id=='valid' and true or (id=='invalid' and false or nil)}
 end}
 assert(s:GetTileActionType('valid')=='EXECUTE_SKILL' and s:GetTileActionType('invalid')=='' and s:GetTileActionType('missing')=='')
 assert(table.concat(seen,',')=='valid,invalid,missing')
end)
check('playback speed guard preserves the lower bound without adding an upper cap',function()
 local s=fixture()
 for _,speed in ipairs({-1,0,.05,.1,.125,1,3,20}) do
  s.SkillSpeedMultiplier=speed; assert(s:GetSkillSpeedMultiplier()==math.max(.1,speed) and s.SkillSpeedMultiplier==speed)
 end
end)
check('shared hop clamp preserves enabled and disabled movement duration',function()
 local s=fixture()
 for _,hop in ipairs({-1,0,.119,.12,.24,.35,1}) do
  s.PlayerHopDuration=hop; local clamped=math.max(.12,math.min(.35,hop))
  assert(s:GetPlayerHopDuration()==clamped and s.PlayerHopDuration==hop)
  for _,move in ipairs({-1,.1,.24,.35,1}) do
   local base=math.max(.1,math.min(.35,move))
   assert(_PlayerGridMovementLogic:GetDuration({MoveActionDuration=move,EnablePlayerHopVisual=true,PlayerHopDuration=hop})==math.max(base,clamped))
   assert(_PlayerGridMovementLogic:GetDuration({MoveActionDuration=move,EnablePlayerHopVisual=false,PlayerHopDuration=hop})==base)
  end
 end
end)
check('empty damage batches do not look up actors or dispatch presentation',function()
 local s=fixture(); local original={}; local batch={Damages=original}
 function s:FindUnitEntity() error('empty batch lookup') end
 function s:PresentDamageNumbers() error('empty batch dispatch') end
 s:FlushDamageNumberBatch(nil); s:FlushDamageNumberBatch({}); s:FlushDamageNumberBatch(batch)
 assert(batch.Damages==original and #original==0)
end)
check('damage batch is consumed before dispatch and cannot replay across callbacks or sessions',function()
 local a=fixture(); local b=fixture(); local amounts={4,7,2}; local batch={SourceUnitId='source',TargetUnitId='target',Damages=amounts}
 local calls=0; local trace={}; local source={}; local target={}
 function a:FindUnitEntity(id) trace[#trace+1]=id; return id=='source' and source or target end
 function a:PresentDamageNumbers(from,to,values,delay)
  calls=calls+1; assert(from==source and to==target and values==amounts and table.concat(values,',')=='4,7,2' and delay==.08)
  assert(batch.Damages~=amounts and #batch.Damages==0); self:FlushDamageNumberBatch(batch)
 end
 a:FlushDamageNumberBatch(batch); a:FlushDamageNumberBatch(batch)
 assert(calls==1 and table.concat(trace,',')=='source,target' and table.concat(amounts,',')=='4,7,2')
 local other={SourceUnitId='other-source',TargetUnitId='other-target',Damages={9}}
 function b:PresentDamageNumbers(_,_,values,delay) assert(values[1]==9 and delay==.08 and #other.Damages==0); self.Seen=true end
 b:FlushDamageNumberBatch(other); assert(b.Seen and calls==1)
end)
print(checks..' session boundary regressions passed')
''')
