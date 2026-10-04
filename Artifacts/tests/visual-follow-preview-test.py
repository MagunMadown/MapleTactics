"""Actual mLua visual-follow and preview regressions. Native Maker is not simulated."""
import os
from pathlib import Path
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
lua = LuaRuntime(unpack_returned_tuples=True)


def load(path, names):
    result = lua.table()
    source = (ROOT / path).read_text(encoding="utf-8-sig")
    for match in re.finditer(r"^([ \t]+)method\s+\w+\s+(\w+)\((.*?)\)\n(.*?)^\1end\s*$", source, re.M | re.S):
        _, name, params, body = match.groups()
        if name in names:
            args = ",".join(p.strip().split()[-1] for p in params.split(",") if p.strip())
            result[name] = lua.execute("return function(self" + ("," + args if args else "") + ")\n" + body + "\nend")
    assert set(names) == set(result.keys())
    return result


lua.globals().hp = load("RootDesk/MyDesk/02_UI/BattleUnitHpHudComponent.mlua", {
    "UpdateWorldBar", "UpdateLobbyName", "UpdatePlayerName", "ClearView", "AssignView", "GetHpRatio",
    "EnsureLobbyNameFollower", "FindLobbyNameTemplate", "DestroyLobbyNameFollower"})
lua.globals().queue = load("RootDesk/MyDesk/02_UI/PlayerOverheadQueueHudComponent.mlua", {"UpdatePlayerTracking"})
lua.globals().preview = load("RootDesk/MyDesk/04_Roguelike/SkillStage/NewSkillSelectionUILogic.mlua", {
    "PlayFittedPreview", "SetPreviewThumbnail", "ReleasePreviewFit", "ClearPreviewFits", "SetCardHighlight"})
lua.execute(r'''
isvalid=function(x) return x ~= nil and x.destroyed ~= true end
Vector2=function(x,y) return {x=x,y=y} end
Color=function(...) return {...} end
DataRef=function(x) return x end
log=function() end; log_warning=function() end
_UILogic={WorldToScreenPosition=function(_,p) return p end, ScreenToUIPosition=function(_,p) return p end}
local map={}
local visual={TransformComponent={WorldPosition=Vector2(8,3)}}
local unit={IsDead=false,IsBoss=false,UnitId='p',CurrentHp=3,MaxHp=4}
local player={TransformComponent={WorldPosition=Vector2(1,0)},CurrentMap=map,
    AvatarRendererComponent={GetAvatarRootEntity=function() return visual end},
    GetComponent=function() return unit end}
player.NameTagComponent={Enable=true,Name='Player',Entity=player}
local view={Root={UITransformComponent={}},NameText={TextGUIRendererComponent={}},UnitEntity=player,UnitId='p'}
hp._T={ContextMap=map,PlayerView=view}; hp.RefreshViewVisual=function() end; hp.SmoothDuration=0.1
queue.ReservationQueueTransform={}; queue.UtilitySkillHUDTransform={}
queue.QueueMaxSlots=6; queue.CurrentVisibleSlotCount=1; queue.QueueFirstSlotCenterOffsetY=0
queue.QueueSlotSpacing=10; queue.PlayerHeadOffsetY=1; queue.UtilityHudOffsetX=0; queue.UtilityHudOffsetY=-2
hp:UpdateWorldBar(view,0.016,-1); queue:UpdatePlayerTracking(player)
assert(view.Root.UITransformComponent.anchoredPosition.x==8)
assert(view.Root.UITransformComponent.anchoredPosition.y==3-1-28)
assert(queue.ReservationQueueTransform.anchoredPosition.x==8)
assert(queue.UtilitySkillHUDTransform.anchoredPosition.x==8)
assert(view.NameText.TextGUIRendererComponent.Text=='Player' and view.NameText.Enable)
assert(not player.NameTagComponent.Enable)
visual.TransformComponent.WorldPosition=Vector2(9,4)
hp:UpdateWorldBar(view,0.016,-1); queue:UpdatePlayerTracking(player)
assert(view.Root.UITransformComponent.anchoredPosition.x==9 and queue.ReservationQueueTransform.anchoredPosition.x==9)
assert(player.TransformComponent.WorldPosition.x==1)
print('PASS avatar prediction/hop position drives name, HP, queue and utility without moving server root')
hp:ClearView(view); assert(player.NameTagComponent.Enable)
player.NameTagComponent.Enable=false
hp:AssignView(view,player,unit); hp:UpdateWorldBar(view,0.016,-1)
assert(not view.NameText.Enable)
hp:ClearView(view); assert(not player.NameTagComponent.Enable)
player.NameTagComponent.Enable=true
hp:AssignView(view,player,unit); hp:UpdateWorldBar(view,0.016,-1)
local other={}; hp:AssignView(view,other,unit)
assert(player.NameTagComponent.Enable and view.NativeNameTag==nil)
print('PASS nickname restoration on hide/rebind and originally hidden names stay hidden')
hp:AssignView(view,player,unit)
player.AvatarRendererComponent.GetAvatarRootEntity=function() return nil end
hp:UpdateWorldBar(view,0.016,-1); queue:UpdatePlayerTracking(player)
assert(view.Root.UITransformComponent.anchoredPosition.x==1 and queue.ReservationQueueTransform.anchoredPosition.x==1)
unit.IsDead=true; hp:UpdateWorldBar(view,0.016,-1); assert(player.NameTagComponent.Enable)
print('PASS missing avatar fallback and death restore native nickname')

-- Lobby names use the world-space native tag: the screen-space line is placed through WorldToScreenPosition,
-- which trails the camera while it follows a lobby step. No battle unit is required.
local lobby={Name='lobby'}
player.CurrentMap=lobby
player.GetComponent=function() error('lobby name must not query a battle unit') end
player.AvatarRendererComponent.GetAvatarRootEntity=function() return visual end
view.Frame={Enable=true}; view.Fill={Enable=false}; view.PipLayer={Enable=true}
local anchored=view.Root.UITransformComponent.anchoredPosition
local clears=0
hp.HideAllBars=function(self) clears=clears+1; self:ClearView(view) end
hp:UpdateLobbyName(player)
assert(clears==1 and not view.Root.Enable and player.NameTagComponent.Enable)
assert(view.Root.UITransformComponent.anchoredPosition==anchored)
visual.TransformComponent.WorldPosition=Vector2(12,4)
hp:UpdateLobbyName(player)
assert(clears==1 and not view.Root.Enable and player.NameTagComponent.Enable)
assert(player.TransformComponent.WorldPosition.x==1)
hp:ClearView(view)
assert(player.NameTagComponent.Enable and not view.Root.Enable)
assert(view.Frame.Enable and not view.Fill.Enable and view.PipLayer.Enable)
print('PASS lobby native tag, no battle dependency, no HP, no screen-space line and exact restoration')

-- With a lobby NameLabel to copy, the name lives under the avatar root so the hierarchy carries the hop height.
local spawned={}
Vector3=Vector3 or function(x,y,z) return {x=x,y=y,z=z} end
_SpawnService={SpawnByEntity=function(_,template,name,position,parent,includeChild)
    local copy={Name=name,Parent=parent,TransformComponent={},NameTagComponent={Enable=true,Name=template.NameTagComponent.Name,OffsetY=-0.98},
        Destroy=function(self) self.destroyed=true end}
    spawned[#spawned+1]=copy; return copy
end}
local label={Name='NameLabel',NameTagComponent={Name='Codex'}}
local lobby2={Name='lobby',Children={{Name='Zone',Children={label}}}}
player.CurrentMap=lobby2
player.NameTagComponent.Name='Haze'; player.NameTagComponent.OffsetY=0; player.NameTagComponent.NameTagRUID='tag'
player.NameTagComponent.FontColor='white'; player.NameTagComponent.FontSize=1; player.NameTagComponent.FontOffset='fo'; player.NameTagComponent.Bold=false
hp:UpdateLobbyName(player)
local follower=spawned[1]
assert(#spawned==1 and follower.Parent==visual and not view.Root.Enable)
assert(follower.NameTagComponent.Name=='Haze' and follower.NameTagComponent.OffsetY==0 and follower.NameTagComponent.NameTagRUID=='tag')
assert(follower.NameTagComponent.Enable and not player.NameTagComponent.Enable)
hp:UpdateLobbyName(player); assert(#spawned==1)
-- A rebuilt avatar root gets a fresh follower; the old one is destroyed.
local rebuilt={TransformComponent={WorldPosition=Vector2(8,3)}}
player.AvatarRendererComponent.GetAvatarRootEntity=function() return rebuilt end
hp:UpdateLobbyName(player)
assert(#spawned==2 and follower.destroyed and spawned[2].Parent==rebuilt)
hp:ClearView(view)
assert(spawned[2].destroyed and player.NameTagComponent.Enable and hp._T.LobbyNameFollower==nil)
player.AvatarRendererComponent.GetAvatarRootEntity=function() return visual end
print('PASS lobby name follows the avatar root through the hierarchy and is cleaned up with the view')

ImageType={Simple=1}; PreserveSpriteType={None=0,NativeSize=1}
SpriteAnimClipPlayType={Loop=1}; ResourceType={AnimationClip=1}
local pending={}; local loads=0
local frames={
 {FrameIndex=0,FrameSprite={IsLoadComplete=true,Width=20,Height=30,PivotPixel=Vector2(15,10)}},
 {FrameIndex=1,FrameSprite={IsLoadComplete=true,Width=90,Height=60,PivotPixel=Vector2(-5,40)}}}
_ResourceService={PreloadAsync=function(_,ids,cb) table.insert(pending,cb) end,
 GetTypeAndWait=function(_,id) return id=='static' and 2 or 1 end,
 LoadAnimationClipAndWait=function() loads=loads+1; return {IsLoadComplete=true,Frames={ToTable=function() return frames end}} end}
local function flush() local q=pending; pending={}; for _,cb in ipairs(q) do cb() end end
local function card(id) return {Id=id,Enable=true,UITransformComponent={RectSize=Vector2(330,180)},SpriteGUIRendererComponent={},
 ConnectEvent=function() error('per-frame layout callback must not be registered') end} end
preview._T={}; preview.GroupPath='/ui/cards'; preview.HoveredSlot=0
local left,right=card('left'),card('right')
preview:PlayFittedPreview(left,'clip'); preview:PlayFittedPreview(right,'clip'); flush()
assert(left.Enable and right.Enable and loads==1)
for _,c in ipairs({left,right}) do
 local r=c.SpriteGUIRendererComponent
 assert(r.EndFrameIndex>1 and r.PlayRate==1 and r.AnimClipPlayType==SpriteAnimClipPlayType.Loop)
 assert(r.PreserveSprite==PreserveSpriteType.NativeSize)
 assert(c.UITransformComponent.RectSize.x==330 and c.UITransformComponent.RectSize.y==180)
 for _,f in ipairs(frames) do
  local s=f.FrameSprite; local scale=r.LocalScale.x; local p=r.LocalPosition
  assert(-s.PivotPixel.x*scale+p.x>=-165-0.001)
  assert((s.Width-s.PivotPixel.x)*scale+p.x<=165+0.001)
  assert(-s.PivotPixel.y*scale+p.y>=-90-0.001)
  assert((s.Height-s.PivotPixel.y)*scale+p.y<=90+0.001)
 end
end
print('PASS both clips loop with fixed UI rectangles and stable pivot-aware bounds')
_EntityService={GetEntityByPath=function() return {} end}
local leftState=preview._T.PreviewFits.left
for i=1,20 do preview:SetCardHighlight(1,true); preview:SetCardHighlight(1,false); preview:SetCardHighlight(2,true) end
assert(preview._T.PreviewFits.left==leftState and #pending==0 and loads==1)
print('PASS repeated hover does not reset playback, hide previews or reload resources')
local stale=card('stale'); preview:PlayFittedPreview(stale,'clip'); preview:ClearPreviewFits(); flush()
assert(not stale.Enable and stale.SpriteGUIRendererComponent.ImageRUID==nil)
local replaced=card('replace'); preview:PlayFittedPreview(replaced,'clip'); preview:PlayFittedPreview(replaced,'newclip'); flush()
assert(replaced.SpriteGUIRendererComponent.ImageRUID=='newclip')
print('PASS delayed loads cannot restore closed or replaced previews')
local static=card('static'); preview:PlayFittedPreview(static,'static'); flush(); flush()
assert(static.Enable and static.SpriteGUIRendererComponent.EndFrameIndex==0)
print('PASS non-animation resource retains thumbnail fallback')
''')
print("All 8 visual-follow/preview groups passed. Maker runtime: NOT RUN.")
