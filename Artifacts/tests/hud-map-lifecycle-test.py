"""Verify native map tombstones never reach HUD component lookups. Offline Lua only."""
import os
from pathlib import Path
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
lua = LuaRuntime(unpack_returned_tuples=True)


def load(file, names):
    source = (ROOT / "RootDesk/MyDesk/02_UI" / file).read_text(encoding="utf-8-sig")
    result = lua.table()
    for m in re.finditer(r"^([ \t]+)method\s+\w+\s+(\w+)\((.*?)\)\n(.*?)^\1end\s*$", source, re.M | re.S):
        _, name, params, body = m.groups()
        if name in names:
            args = ",".join(p.strip().split()[-1] for p in params.split(",") if p.strip())
            result[name] = lua.execute("return function(self" + ("," + args if args else "") + ")\n" + body + "\nend")
    assert set(result.keys()) == set(names)
    return result


lua.globals().presenter = load("BattleHudPresenterLogic.mlua", {"GetBattleSession", "GetBattleWaveState", "RefreshState"})
for name, file in [("hp", "BattleUnitHpHudComponent.mlua"), ("queue", "PlayerOverheadQueueHudComponent.mlua"), ("intent", "EnemyIntentHudComponent.mlua")]:
    lua.globals()[name] = load(file, {"GetBattleSession"})
lua.execute(r'''
isvalid=function(value) return value ~= nil and rawget(value,'destroyed') ~= true end
local dead=setmetatable({destroyed=true}, {__index=function() error('native backing object destroyed') end})
local session={}; local wave={}
local calls=0
local map={GetComponent=function(_,key) calls=calls+1; return key=='script.BattleSessionComponent' and session or wave end,
    GetChildByName=function() return nil end}
_UserService={}; presenter._T={}
local function all(expected)
 assert(presenter:GetBattleSession()==expected)
 for _,hud in ipairs({hp,queue,intent}) do assert(hud:GetBattleSession(_UserService.LocalPlayer)==expected) end
end
all(nil)
_UserService.LocalPlayer=dead; all(nil); assert(presenter:GetBattleWaveState()==nil)
_UserService.LocalPlayer={}; all(nil); assert(presenter:GetBattleWaveState()==nil)
_UserService.LocalPlayer.CurrentMap=dead; all(nil); assert(presenter:GetBattleWaveState()==nil)
assert(calls==0)
print('PASS absent/destroyed players and maps never invoke native GetComponent/GetChildByName')
presenter.PublishUnavailableState=function(_,reason) assert(reason=='BATTLE_CONTEXT_MISSING'); presenter.reason=reason end
presenter:RefreshState(false)
assert(presenter.reason=='BATTLE_CONTEXT_MISSING')
_UserService.LocalPlayer.CurrentMap=map; all(session)
assert(presenter:GetBattleWaveState()==wave)
print('PASS map transition hides unavailable HUD state and next valid map is resolved normally')
map.GetChildByName=function() return dead end
assert(presenter:GetBattleWaveState()==wave)
local childWave={}
map.GetChildByName=function() return {GetComponent=function() return childWave end} end
assert(presenter:GetBattleWaveState()==childWave)
print('PASS destroyed wave child uses map fallback; live wave child remains preferred')
map.GetComponent=function() return nil end
all(nil)
print('PASS live non-battle maps return no battle session without exception')
''')
lua.globals().shop = load("../04_Roguelike/Shop/RunShopLogic.mlua", {"GetLocalShopUiState"})
lua.globals().exitButton = load("../04_Roguelike/Shop/ShopExitButtonComponent.mlua", {"OnUpdate", "SetButtonState"})
lua.execute(r'''
local dead=setmetatable({destroyed=true}, {__index=function() error('native backing object destroyed') end})
_UserService.LocalPlayer=dead
assert(shop:GetLocalShopUiState().Reason=='LOCAL_PLAYER_UNAVAILABLE')
local lookups=0
local state={OfferSnapshot='offer~item',PurchasedOfferIds='',ShopState='OPEN',ActiveNodeId='shop_test'}
local inventory={}
local run={RunState='Running',RunFlowState='AWAITING_SHOP',SelectedContentType='SHOP',LastCompletedContentType='SHOP'}
local parts={['script.PlayerRunShopStateComponent']=state,['script.PlayerRunInventoryComponent']=inventory,
 ['script.PlayerRunStateComponent']=run}
local player={CurrentMap={Name='lobby'},GetComponent=function(_,key) lookups=lookups+1; return parts[key] end}
_UserService.LocalPlayer=player
parts['script.PlayerRunInventoryComponent']=dead
assert(shop:GetLocalShopUiState().Reason=='RUN_SHOP_STATE_UNAVAILABLE')
parts['script.PlayerRunInventoryComponent']=inventory
local snapshot=shop:GetLocalShopUiState()
assert(snapshot.Success and snapshot.Commands.CanClose and snapshot.Commands.CanPurchase)
print('PASS shop snapshot rejects disposed player/components and preserves live shop state')

local queries=0
_RunShopLogic={GetLocalShopUiState=function() queries=queries+1; return shop:GetLocalShopUiState() end}
local buttonEntity={TextGUIRendererComponent={}}
exitButton.DepartureButton={Entity=buttonEntity}; exitButton.ClosePending=false
exitButton:SetButtonState(false,false)
for _,name in ipairs({'lobby','battle','newskill'}) do player.CurrentMap={Name=name}; exitButton:OnUpdate(0.016) end
player.CurrentMap=dead; exitButton:OnUpdate(0.016)
_UserService.LocalPlayer=dead; exitButton:OnUpdate(0.016)
assert(queries==0 and not buttonEntity.Visible and not exitButton.DepartureButton.Enable)
print('PASS hidden exit button and non-shop/teardown frames make zero shop queries')

_UserService.LocalPlayer=player; player.CurrentMap={Name='shop'}
exitButton:OnUpdate(0.016)
assert(buttonEntity.Visible and exitButton.DepartureButton.Enable and buttonEntity.TextGUIRendererComponent.Text=='출발')
player.CurrentMap={Name='sleepywood_shop'}; state.ActiveNodeId='shop_sleepywood_balrog'; state.ShopState='CLOSED'
exitButton:OnUpdate(0.016)
assert(buttonEntity.Visible and exitButton.DepartureButton.Enable)
print('PASS ordinary departure and Balrog retry button remain available')

exitButton.ClosePending=true; _UserService.LocalPlayer=dead
local before=queries; exitButton:OnUpdate(0.016)
assert(exitButton.ClosePending and queries==before and not buttonEntity.Visible)
_UserService.LocalPlayer=player; player.CurrentMap={Name='shop'}; state.ActiveNodeId='shop_test'
local opened=0
local minimap={OpenWorldMapMode=function() opened=opened+1; return true end}
_EntityService={GetEntityByPath=function(_,path)
 if path=='/ui/DefaultGroup' then return {GetComponent=function() return minimap end} end
 return nil
end}
log=function() end; log_warning=function() end
exitButton:OnUpdate(0.016)
assert(opened==1 and not exitButton.ClosePending and not buttonEntity.Visible)
print('PASS pending closure survives transient missing player and completes after recovery')
''')
print("All 8 HUD/shop lifecycle groups passed. Maker runtime: NOT RUN.")
