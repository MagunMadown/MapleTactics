"""Run: LUPA_PATH=/path/to/lupa python3 Artifacts/tests/tutorial-dodge-highlight-test.py."""
from pathlib import Path
from battle_refactor_fixture import wire_logic_owners
import os
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa import LuaRuntime

root = Path(__file__).resolve().parents[2]
lua = LuaRuntime()
wire_logic_owners(lua)

def load(path, name, receiver):
    source = (root / path).read_text(encoding="utf-8-sig").expandtabs(4)
    match = re.search(r"^([ \t]+)method \w+ " + name + r"\(([^\n]*)\)\n(.*?)^\1end", source, re.M | re.S)
    assert match, name
    params = ", ".join(p.strip().split()[-1] for p in match[2].split(",") if p.strip())
    lua.execute(f"function {receiver}:{name}({params})\n{match[3]}end")

lua.execute("hud = {}; tutorial = {}; keys = {}; _TutorialPresentationLogic = tutorial")
load("RootDesk/MyDesk/02_UI/KeyGuideHudComponent.mlua", "GetRowItems", "keys")
load("RootDesk/MyDesk/02_UI/EnemyIntentHudComponent.mlua", "UpdateViewPositions", "hud")
presentation = "RootDesk/MyDesk/00_Core/Lobby/Tutorial/TutorialPresentationLogic.mlua"
for name in ("GetGuideMessage", "TrackDecoration", "ResetHudHighlights", "UpdateMonsterHighlight",
             "UpdateKeyHighlight", "UpdateConsumableHighlight", "UpdatePlatformTarget", "GetPlatformColor",
             "UpdateQueueHighlight", "SetQueueHighlightTarget"):
    load(presentation, name, "tutorial")
lua.execute('''
isvalid = function(v) return v ~= nil end
log = function() end
Vector2 = function(x,y) return {x=x,y=y} end
Vector3 = function(x,y,z) return {x=x,y=y,z=z} end
Color = function(r,g,b,a) return {r=r,g=g,b=b,a=a} end
_UtilLogic = {ElapsedSeconds=0}
local zoom = 100
_UILogic = {
    WorldToScreenPosition=function(_,v) return Vector2(v.x*zoom,v.y*zoom) end,
    ScreenToUIPosition=function(_,v) return v end
}
local serial=0
local function decoration()
    serial=serial+1
    return {Id=tostring(serial),Enable=false,UITransformComponent={UIScale=Vector3(1.2,1.3,1),
        RectSize=Vector2(80,90),anchoredPosition=Vector2(7,9)},SpriteGUIRendererComponent={Color=Color(.2,.3,.4,.5)}}
end
local frame = decoration()
local originalScale=frame.UITransformComponent.UIScale
local originalSize=frame.UITransformComponent.RectSize
local originalColor=frame.SpriteGUIRendererComponent.Color
local record = {
    View={UITransformComponent={}},
    Enemy={TransformComponent={WorldPosition=Vector3(2,3,0)}},
    HeadMarker={TransformComponent={WorldPosition=Vector3(2,4,0)}},
    MonsterHighlight=frame
}
hud._T = {EnemyViews={enemy=record},ViewQueues={enemy={"enemy_skill"}}}
local session = {TutorialActive=true,CellSpacing=1.1,BattleResult="",BattlePhase="PlayerTurn",PlayerStartCell=0,
    QueuedTileCount=0,QueuedTileIds="",SkillSlotIds="brandish|divine_swing||||",TutorialGuardUsed=false}
for step=1,10 do
    session.TutorialStep=step
    hud:UpdateViewPositions(session)
    assert(frame.Enable == (step==3 or step==8), "wrong step " .. step)
end
session.TutorialStep=8; hud._T.ViewQueues.enemy={}
hud:UpdateViewPositions(session); assert(not frame.Enable)
hud._T.ViewQueues.enemy={"enemy_skill"}
session.TutorialStep=3
hud:UpdateViewPositions(session)
assert(math.abs(frame.UITransformComponent.RectSize.x-110)<0.001)
assert(frame.UITransformComponent.RectSize.y==124)
assert(frame.UITransformComponent.anchoredPosition.y==50)
zoom=200
hud:UpdateViewPositions(session)
assert(math.abs(frame.UITransformComponent.RectSize.x-220)<0.001)
assert(frame.UITransformComponent.RectSize.y==224)
session.BattleResult="Victory"
hud:UpdateViewPositions(session)
assert(not frame.Enable and frame.UITransformComponent.UIScale==originalScale
    and frame.UITransformComponent.RectSize==originalSize and frame.SpriteGUIRendererComponent.Color==originalColor)
session.BattleResult=""
session.TutorialActive=false
hud:UpdateViewPositions(session)
assert(not frame.Enable)
record.MonsterHighlight=nil
hud:UpdateViewPositions(session) -- Missing template is safe.
local hints={"오른쪽","브랜디쉬","왼쪽","오른쪽","실행","디바인","포션","가드","드래그","자유전투"}
for step,hint in ipairs(hints) do assert(tutorial:GetGuideMessage(step,0,""):find(hint,1,true)) end
assert(tutorial:GetGuideMessage(6,1,""):find("실행",1,true))
assert(tutorial:GetGuideMessage(9,2,""):find("실행 순서",1,true))
assert(tutorial:GetGuideMessage(10,0,"Victory"):find("저장",1,true))
assert(tutorial:GetGuideMessage(10,0,"Defeat"):find("재도전",1,true))

-- Cell targets track the actor, disappear during enemy execution, and do not survive ordinary battles.
local playerUnit={CellIndex=3}
local player={CurrentMap={GetComponent=function() return session end},GetComponent=function() return playerUnit end}
_UserService={LocalPlayer=player}
session.TutorialActive=true; session.TutorialStep=1
tutorial:UpdatePlatformTarget(hud,player,session); assert(hud._T.TutorialCell==4)
session.TutorialStep=3
tutorial:UpdatePlatformTarget(hud,player,session); assert(hud._T.TutorialCell==2)
session.BattlePhase="EnemyTurn"
tutorial:UpdatePlatformTarget(hud,player,session); assert(hud._T.TutorialCell==-1)
session.BattlePhase="PlayerTurn"; session.TutorialActive=false
tutorial:UpdatePlatformTarget(hud,player,session); assert(hud._T.TutorialCell==-1)
assert(tutorial:GetPlatformColor(hud,2,Color(1,1,1,1))==nil)

-- All six keys follow the actual dragged quickbar, then restore the original fill tint.
local function cap()
    local children={Highlight=decoration(),Fill=decoration()}
    return {GetChildByName=function(_,name) return children[name] end,Children=children}
end
local keyHud={CurrentContext="BATTLE",_T={RowCaps={}}}
local caps={cap(),cap(),cap(),cap(),cap(),cap()}
keyHud._T.RowCaps["BattlePanel/Row5"]=caps
session.TutorialActive=true; session.TutorialStep=9
session.SkillSlotIds="||brandish|||divine_swing"; session.QueuedTileCount=0
tutorial:UpdateKeyHighlight(keyHud,0)
assert(caps[3].Children.Highlight.Enable and not caps[1].Children.Highlight.Enable, "dragged brandish key missing")
session.QueuedTileCount=1; session.QueuedTileIds="brandish"
local fillColor=caps[6].Children.Fill.SpriteGUIRendererComponent.Color
tutorial:UpdateKeyHighlight(keyHud,0)
assert(caps[6].Children.Highlight.Enable and not caps[3].Children.Highlight.Enable, "dragged divine key missing")
session.BattleResult="Victory"
tutorial:UpdateKeyHighlight(keyHud,0)
assert(not caps[6].Children.Highlight.Enable and caps[6].Children.Fill.SpriteGUIRendererComponent.Color==fillColor)
tutorial:ResetHudHighlights(keyHud)
assert(keyHud._T.TutorialDecorations==nil)
keyHud._T.RowCaps={}; tutorial:UpdateKeyHighlight(keyHud,0) -- Missing key template is safe.

-- Potion frame requires the actual item and restores geometry after consumption/result.
session.BattleResult=""; session.TutorialStep=7
local potionFrame=decoration()
local potionSize=potionFrame.UITransformComponent.RectSize
local potionHud={Slots={{GetChildByName=function() return potionFrame end}},_T={SlotItems={{ConsumableId="orange_potion"}}}}
tutorial:UpdateConsumableHighlight(potionHud,session); assert(potionFrame.Enable)
session.BattleResult="Victory"
tutorial:UpdateConsumableHighlight(potionHud,session)
assert(not potionFrame.Enable and potionFrame.UITransformComponent.RectSize==potionSize)
_EntityService={GetEntityByPath=function() return nil end}
potionHud.Slots={{GetChildByName=function() return nil end}}
session.BattleResult=""; tutorial:UpdateConsumableHighlight(potionHud,session)

-- Guided tutorials expose six individual caps; ordinary battles retain the compact range.
_TutorialRulesLogic={IsGuided=function(_,s) return s.TutorialActive and s.TutorialStep<10 end}
_GameSettingsLogic={GetBinding=function(_,action) return tonumber(action:match("%d+")) end}
local spec={Slots=true}
session.TutorialStep=9
assert(#keys:GetRowItems(spec)==6)
session.TutorialStep=10
assert(#keys:GetRowItems(spec)==3)

-- Quickbar highlights follow slots 3~6, reuse their cloned frame, and tolerate absent templates/buttons.
local clones=0
local function sprite()
    local e=decoration()
    e.SpriteGUIRendererComponent.Entity=e
    return e.SpriteGUIRendererComponent
end
local slotChildren={}
local queueHud={_T={},SlotSkillIds="||brandish|||divine_swing"}
for i=1,6 do
    slotChildren[i]={}
end
queueHud.GetSkillSlotButton=function(_,i)
    if not slotChildren[i] then return nil end
    return {Entity={Index=i,GetChildByName=function(_,name) return slotChildren[i][name] end}}
end
queueHud.SkillSlot1TutorialHighlight=sprite()
queueHud.SkillSlot2TutorialHighlight=sprite()
queueHud.ExecuteTutorialHighlight=sprite()
queueHud.ResultResetTutorialHighlight=sprite()
queueHud.SkillSlot1TutorialHighlight.Entity.Clone=function(_,name)
    clones=clones+1
    local e=sprite().Entity
    e.AttachTo=function(_,parent) slotChildren[parent.Index][name]=e; return true end
    return e
end
queueHud.GetFixedSkillSlotToken=function(_,source,index)
    local n=0
    for token in (source.."|"):gmatch("(.-)|") do
        n=n+1; if n==index then return token end
    end
end
session.TutorialStep=9; session.QueuedTileCount=0; session.SkillSlotIds=queueHud.SlotSkillIds
tutorial:UpdateQueueHighlight(queueHud,0)
assert(slotChildren[3].TutorialHighlight.Enable and clones==1)
tutorial:UpdateQueueHighlight(queueHud,0); assert(clones==1)
session.QueuedTileCount=1; session.QueuedTileIds="brandish"
tutorial:UpdateQueueHighlight(queueHud,0)
assert(slotChildren[6].TutorialHighlight.Enable and not slotChildren[3].TutorialHighlight.Enable and clones==2)
session.QueuedTileCount=2
tutorial:UpdateQueueHighlight(queueHud,0)
assert(queueHud.ExecuteTutorialHighlight.Enable and not slotChildren[6].TutorialHighlight.Enable)
session.TutorialActive=false
tutorial:UpdateQueueHighlight(queueHud,0)
assert(not queueHud.ExecuteTutorialHighlight.Enable)
queueHud.SkillSlot1TutorialHighlight=nil
tutorial:SetQueueHighlightTarget(queueHud,3)
assert(queueHud.ExecuteTutorialHighlight.Enable)
slotChildren[4]=nil
tutorial:SetQueueHighlightTarget(queueHud,8)
assert(not queueHud.ExecuteTutorialHighlight.Enable)
''')
print("PASS: 10-step prompts, dodge/guard frames, zoom, cell/key/potion highlights, dragged slots and restoration")
