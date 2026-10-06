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
    "SpawnUnitLabel", "GetHopSource", "DestroyLabel", "EnsurePlayerLabel", "DestroyPlayerLabel"})
lua.globals().preview = load("RootDesk/MyDesk/04_Roguelike/SkillStage/NewSkillSelectionUILogic.mlua", {
    "PlayFittedPreview", "SetPreviewThumbnail", "ReleasePreviewFit", "ClearPreviewFits", "SetCardHighlight"})
lua.execute(r'''
isvalid=function(x) return x~=nil and not x.destroyed end
Vector2=function(x,y) return {x=x,y=y} end
Vector3=function(x,y,z) return {x=x,y=y,z=z} end
Color=function(...) return {...} end
DataRef=function(x) return x end
log=function() end; log_warning=log
local map={Name="lobby"}
local avatar={}
local player={CurrentMap=map,AvatarRendererComponent={GetAvatarRootEntity=function() return avatar end}}
local added,spawned=0,0
local includeComponent=false
local attachSuccess=true
_SpawnService={SpawnByModelId=function(_,id,name,pos,parent)
 assert(id=='unitworldlabel' and parent==map)
 spawned=spawned+1
 local e={Parent=parent,Destroy=function(self) self.destroyed=true end}
 local label={Entity=e,SetOffsetSource=function(self,source) self.Source=source end}
 e.GetComponent=function() return includeComponent and label or nil end
 e.AddComponent=function(_,name) assert(name=='script.UnitWorldLabelComponent'); added=added+1; return label end
 e.AttachTo=function(self,parent) self.Parent=parent; return attachSuccess end
 return e
end}
hp._T={}
local label=hp:EnsurePlayerLabel(player)
assert(label~=nil and added==1 and spawned==1 and label.Entity.Parent==player and label.Source==avatar)
assert(hp:EnsurePlayerLabel(player)==label and added==1 and spawned==1)
avatar={}; hp:EnsurePlayerLabel(player); assert(label.Source==avatar and spawned==1)
local tag={Entity=player,Enable=false}
hp._T.NativeNameTag=tag; hp._T.NativeNameTagEnabled=true
hp:DestroyPlayerLabel(); assert(label.Entity.destroyed and tag.Enable)
includeComponent=true
label=hp:EnsurePlayerLabel(player); assert(label~=nil and added==1 and spawned==2)
hp:DestroyPlayerLabel(); attachSuccess=false
assert(hp:EnsurePlayerLabel(player)==nil)
local failures=spawned
assert(hp:EnsurePlayerLabel(player)==nil and spawned==failures)
print('PASS world label: missing component repair, reuse, avatar replacement, native tag restore, failed-map retry guard')
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
print("World-label lifecycle and preview groups passed. Maker runtime: NOT RUN.")
