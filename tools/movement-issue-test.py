"""Lua 5.3 regression for client prediction, obstruction approval and shared landings."""
import os,re,sys
from pathlib import Path
if os.environ.get('LUPA_PATH'): sys.path.insert(0,os.environ['LUPA_PATH'])
from lupa.lua53 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute('''
function Vector2(x,y) return {x=x,y=y} end
function Vector3(x,y,z) return {x=x,y=y,z=z} end
function isvalid(x) return x~=nil and not x.destroyed end
function log(...) end
function log_warning(...) end
_UtilLogic={ElapsedSeconds=0}
_BattleHudPresenterLogic={ReleasePendingLocalCommand=function() end}
move={_T={}}
''')
text=(ROOT/'RootDesk/MyDesk/00_Core/Movement/PlayerGridMovementLogic.mlua').read_text(encoding='utf-8-sig')
for key,value in re.findall(r'^\s*property \w+ (\w+) = ([^\n]+)',text,re.M):lua.execute('move.'+key+'='+value)
for key,args,body in re.findall(r'^\tmethod \w+ (\w+)\(([^\n]*)\)\n(.*?)^\tend',text,re.M|re.S):
    names=','.join(a.strip().split()[-1] for a in args.split(',') if a.strip())
    lua.execute('function move:'+key+'('+names+')\n'+body+'\nend')
lua.execute('''
local session={EntryRequestId=1,HudContextRevision=1,BattleResult=''}
local map={Name='battle',GetComponent=function() return session end}
local hops,writes,offset=0,0,0
local presentation={IsFullMotionPending=function() return false end,
 BeginLocalGridMoveHop=function() hops=hops+1 end,
 SetLocalGridMoveOffset2D=function(_,x,y) offset=x end,
 ClearLocalGridMoveOffset=function() offset=0 end}
local player={CurrentMap=map,Name='test',PlayerComponent={UserId='test'},CameraComponent={Damping=Vector2(2,3)},
 TransformComponent={WorldPosition=Vector3(0,0,0)}}
player.TransformComponent.ToLocalPoint=function(_,p) local a=player.TransformComponent.WorldPosition;return Vector3(p.x-a.x,p.y-a.y,p.z-a.z) end
player.MovementComponent={SetWorldPosition=function(_,p) writes=writes+1;player.TransformComponent.WorldPosition=Vector3(p.x,p.y,0) end}
player.GetComponent=function(_,name) if name=='script.BattleUnitPresentationComponent' then return presentation end end
_UserService={LocalPlayer=player}
local function begin(blocked,dir,entry)
 move:CancelLocalMove('RESET');player.TransformComponent.WorldPosition=Vector3(0,0,0);hops=0;writes=0;offset=0;_UtilLogic.ElapsedSeconds=0
 local profile=move:GetProfile(nil);profile.ClientRoot=true;profile.ObstructionHint=blocked;profile.AttemptDirection=dir;profile.AttemptCellSize=1
 return move:BeginLocalMove(player,map,entry or 1,1,Vector2(dir,0),profile)
end
local function tick(t) _UtilLogic.ElapsedSeconds=t;move:OnUpdate(0.02) end
for _,entry in ipairs({0,1}) do
 for _,direction in ipairs({-1,1}) do
  local id=begin(false,direction,entry);assert(hops==1)
  tick(0.12);assert(math.abs(player.TransformComponent.WorldPosition.x-direction*0.5)<0.001)
  move:ResolveLocalMove(map,id,entry,1,true,true,direction,0,'OK')
  tick(0.24);assert(player.TransformComponent.WorldPosition.x==direction and move._T.localMove.Arrived)
  local prior=writes;tick(0.26);assert(writes==prior,'no post-landing root writes')
 end
end
local id=begin(true,1);tick(0.1);assert(hops==0 and writes==0 and offset==0,'obstruction stays on floor')
move:ResolveLocalMove(map,id,1,1,true,false,1,0,'OK');assert(hops==1,'approved obstruction starts normal hop')
tick(0.22);assert(math.abs(player.TransformComponent.WorldPosition.x-0.5)<0.001,'approved move begins at actual root')
move:ResolveLocalMove(map,id,1,1,true,true,1,0,'OK');assert(hops==1,'duplicate receipts do not restart hop')
tick(0.34);assert(player.TransformComponent.WorldPosition.x==1)
id=begin(true,-1);tick(0.1);move:ResolveLocalMove(map,id,1,1,false,false,0,0,'BOUNDARY')
assert(move._T.localMove==nil and move._T.localBlockedMove~=nil and hops==0)
move:UpdateBlockedMove(0.06);assert(offset<0 and player.TransformComponent.WorldPosition.x==0)
move:UpdateBlockedMove(0.14);assert(move._T.localBlockedMove==nil and offset==0)
id=begin(false,1);move:ResolveLocalMove(map,id+1,1,1,false,false,0,0,'BOUNDARY');assert(move._T.localMove~=nil,'stale receipt ignored')
player.CurrentMap={};tick(0.1);assert(move._T.localMove==nil and player.CameraComponent.Damping.x==2,'map transfer cleanup')
player.CurrentMap=map
local check=move:CreateLandingCheck(player,map,Vector2(0,0),1,1,1);writes=0
assert(not move:UpdateLandingCheck(check,0.49));assert(move:UpdateLandingCheck(check,0.011));assert(writes==0,'normal landing has no snap')
check=move:CreateLandingCheck(player,map,Vector2(1,0),2,1,1);assert(move:UpdateLandingCheck(check,0.5));assert(writes==1 and player.TransformComponent.WorldPosition.x==1)
assert(move:UpdateLandingCheck(check,1));assert(writes==1,'landing check only once')
''')
print('PASS lobby/battle left-right trajectories, blocked approval hop, single rejection recoil, stale receipts, transition cleanup, common landing correction')
