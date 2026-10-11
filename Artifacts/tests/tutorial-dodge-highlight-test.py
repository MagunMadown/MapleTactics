"""Run: LUPA_PATH=/path/to/lupa python3 Artifacts/tests/tutorial-dodge-highlight-test.py."""
from pathlib import Path
import os
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa import LuaRuntime

root = Path(__file__).resolve().parents[2]
lua = LuaRuntime()

def load(path, name, receiver):
    source = (root / path).read_text(encoding="utf-8-sig")
    match = re.search(r"^([ \t]+)method \w+ " + name + r"\(([^\n]*)\)\n(.*?)^\1end", source, re.M | re.S)
    assert match, name
    params = ", ".join(p.strip().split()[-1] for p in match[2].split(",") if p.strip())
    lua.execute(f"function {receiver}:{name}({params})\n{match[3]}end")

lua.execute("hud = {}; tutorial = {}")
load("RootDesk/MyDesk/02_UI/EnemyIntentHudComponent.mlua", "UpdateViewPositions", "hud")
load("RootDesk/MyDesk/00_Core/Lobby/NewPlayerTutorialLogic.mlua", "GetGuideMessage", "tutorial")
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
local frame = {Enable=false,UITransformComponent={},SpriteGUIRendererComponent={}}
local record = {
    View={UITransformComponent={}},
    Enemy={TransformComponent={WorldPosition=Vector3(2,3,0)}},
    HeadMarker={TransformComponent={WorldPosition=Vector3(2,4,0)}},
    MonsterHighlight=frame
}
hud._T = {EnemyViews={enemy=record}}
local session = {TutorialActive=true,CellSpacing=1.1}
for step=1,7 do
    session.TutorialStep=step
    hud:UpdateViewPositions(session)
    assert(frame.Enable == (step==3 or step==4), "wrong step " .. step)
end
session.TutorialStep=3
hud:UpdateViewPositions(session)
assert(math.abs(frame.UITransformComponent.RectSize.x-110)<0.001)
assert(frame.UITransformComponent.RectSize.y==124)
assert(frame.UITransformComponent.anchoredPosition.y==50)
zoom=200
hud:UpdateViewPositions(session)
assert(math.abs(frame.UITransformComponent.RectSize.x-220)<0.001)
assert(frame.UITransformComponent.RectSize.y==224)
session.TutorialActive=false
hud:UpdateViewPositions(session)
assert(not frame.Enable)
record.MonsterHighlight=nil
hud:UpdateViewPositions(session) -- Missing template is safe.
assert(tutorial:GetGuideMessage(4,1,""):find("회피 성공",1,true))
assert(tutorial:GetGuideMessage(5,1,""):find("장전해 둔 브랜디쉬",1,true))
assert(tutorial:GetGuideMessage(5,1,""):find("반격",1,true))
''')
print("PASS: dodge highlight steps, zoom tracking, cleanup state and counterattack prompts")
