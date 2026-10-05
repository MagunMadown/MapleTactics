"""Offline Lua regressions for delayed replies and inactive battle maps.

Executes the current mLua method bodies with a deterministic clock and RPC queue.
These tests do not replace Maker build/play or production network measurements.
Run with Python 3.12 and lupa, optionally setting LUPA_PATH.
"""

import os
from pathlib import Path
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
lua = LuaRuntime(unpack_returned_tuples=True)


def methods(path, names):
    source = (ROOT / path).read_text(encoding="utf-8-sig")
    result = lua.table()
    for match in re.finditer(
        r"^([ \t]+)method\s+\w+\s+(\w+)\((.*?)\)\n(.*?)^\1end\s*$",
        source, re.MULTILINE | re.DOTALL,
    ):
        _, name, params, body = match.groups()
        if name in names:
            args = ",".join(p.strip().split()[-1] for p in params.split(",") if p.strip())
            result[name] = lua.execute("return function(self" + ("," + args if args else "") + ")\n" + body + "\nend")
    assert set(result.keys()) == set(names), (path, set(names) - set(result.keys()))
    return result


lua.globals().tooltipMethods = methods(
    "RootDesk/MyDesk/02_UI/MouseTooltipUIComponent.mlua",
    {"Show", "ForceHide", "RequestSkillHover", "ReceiveSkillHover", "RequestEnemySkillHover", "ColorizeSkillText"},
)
lua.globals().sessionMethods = methods(
    "RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua", {"OnUpdate"},
)
lua.globals().navigationMethods = methods(
    "RootDesk/MyDesk/02_UI/MapTeleportManager.mlua", {"TeleportPlayer"},
)
lua.globals().shopMethods = methods(
    "RootDesk/MyDesk/02_UI/RunShopUIComponent.mlua",
    {"SendUnionAction", "ReceiveUnionShop", "UpdateUnionRequestFeedback", "OnUpdate"},
)

lua.execute(r'''
function isvalid(value) return value ~= nil and value ~= false end
function Vector2(x, y) return {x=x, y=y} end
function log(_) end
TextHorizontalAlignmentOption = {Left=1}
TextVerticalAlignmentOption = {Top=1}
_UtilLogic = {ElapsedSeconds=0}
_InputService = {GetCursorPosition=function() return Vector2(0,0) end}
_GameUIPolishLogic = {BringUIGroupToFront=function() end,FitVerticalScrollLayouts=function() end}

-- Native proxies throw on both unknown reads and writes, including existing fields.
function strict(values)
    return setmetatable({}, {
        __index=function(_, key) assert(values[key] ~= nil, "unknown native read: " .. key); return values[key] end,
        __newindex=function(_, key, value) assert(values[key] ~= nil, "unknown native write: " .. key); values[key]=value end,
    })
end
function attach(object, source)
    for name, method in pairs(source) do object[name]=method end
    return object
end
function newTooltip()
    local requests = {}
    local session = {RequestSkillHover=function(_, id, request) table.insert(requests, {id,request}) end}
    local map = {GetComponent=function() return session end}
    local tip = attach({
        _T={}, Entity={}, ActiveOwnerKey="", HoverMap=nil, HoverSkillId="", SkillHoverRequestId=0,
        SkillHoverRefreshInterval=1, SkillHoverResponseTimeout=3, IsShowing=false,
        TooltipPanel=strict({Enable=false, Visible=true}),
        TooltipTextEntity=strict({Enable=true, Visible=true}),
        TooltipText=strict({Text="", IsRichText=false, HorizontalAlignment=1, VerticalAlignment=1}),
        LayoutCalls=0, RangeCalls=0,
    }, tooltipMethods)
    tip.ResizeToText=function(self) self.LayoutCalls=self.LayoutCalls+1 end
    tip.UpdatePosition=function() end
    tip.ApplySkillRange=function(self, _, cells) self.RangeCalls=self.RangeCalls+1; self.Cells=cells end
    return tip, map, requests
end

-- A reply taking 900ms must remain current despite the HUD checking every 150ms.
local tip, map, requests = newTooltip()
tip:RequestSkillHover(map, "slash", "entry:turn1")
for i=1,6 do _UtilLogic.ElapsedSeconds=i*0.15; tip:RequestSkillHover(map,"slash","entry:turn1") end
assert(#requests==1 and tip.SkillHoverRequestId==1)
tip:ReceiveSkillHover(map,"slash",1,"Slash\nDamage 10",{2,3})
assert(tip.IsShowing and tip.LayoutCalls==1 and tip.Cells[1]==2)

-- A fresh cached hover and an unchanged live reply preserve layout and scroll state.
_UtilLogic.ElapsedSeconds=1.1
tip:RequestSkillHover(map,"slash","entry:turn1")
assert(#requests==1)
_UtilLogic.ElapsedSeconds=2
tip:RequestSkillHover(map,"slash","entry:turn1")
assert(#requests==2)
tip:ReceiveSkillHover(map,"slash",2,"Slash\nDamage 10",{3,4})
assert(tip.LayoutCalls==1 and tip.Cells[1]==3)
tip:ForceHide()
tip:RequestSkillHover(map,"slash","entry:turn1")
assert(#requests==2 and tip.IsShowing and tip.LayoutCalls==2)

-- State changes during a pending request trigger exactly one replacement after its reply.
_UtilLogic.ElapsedSeconds=4
tip:RequestSkillHover(map,"slash","entry:turn1")
local before=#requests
tip:RequestSkillHover(map,"slash","entry:turn2")
tip:RequestSkillHover(map,"slash","entry:turn3")
assert(#requests==before)
local oldId=tip.SkillHoverRequestId
tip:ReceiveSkillHover(map,"slash",oldId,"outdated",{1})
assert(#requests==before+1 and tip.SkillHoverRequestId==oldId+1 and tip.TooltipText.Text~="outdated")
tip:ReceiveSkillHover(map,"slash",tip.SkillHoverRequestId,"current",{5})
assert(tip.TooltipText.Text:find("current",1,true))

-- Lost replies can be retried after the deadline; old or hidden replies are rejected.
_UtilLogic.ElapsedSeconds=6
tip:RequestSkillHover(map,"slash","entry:turn4")
local lostId=tip.SkillHoverRequestId
_UtilLogic.ElapsedSeconds=9.1
tip:RequestSkillHover(map,"slash","entry:turn4")
assert(tip.SkillHoverRequestId==lostId+1)
tip:ReceiveSkillHover(map,"slash",lostId,"late",{})
assert(not tip.TooltipText.Text:find("late",1,true))
tip:ForceHide()
tip:ReceiveSkillHover(map,"slash",tip.SkillHoverRequestId-1,"hidden",{})
assert(not tip.IsShowing)
print("PASS tooltip: slow RPC, cache, changed state, retry, stale reply, native fields")

-- Nineteen empty static battle maps must not query users on every server frame.
local scans, refreshes=0,0
_UserService={GetUsersByMapComponent=function() scans=scans+1; return {} end}
function newSession()
    local map={MapComponent={}}
    local session=attach({_T={},Entity=map,EntryPolicyResolved=false,PrototypeTestEntryPending=false,
        BattleResult="",StageId="stage_1",PlayerExitObservedAfterBattle=false,HudRelicSnapshot="",BattlePhase="PlayerTurn"},sessionMethods)
    session.UpdatePrototypeBattleEntryRetry=function() error("unexpected retry") end
    session.OnMapEnter=function(self,player) self.PlayerEntity=player; self.EntryPolicyResolved=true end
    for _, name in ipairs({"RefreshHudProgressSnapshot","UpdatePlayerGridMove","UpdateEnemyGridMove","RefreshPlayerHpSnapshot","RefreshHudRelicSnapshot"}) do
        session[name]=function() refreshes=refreshes+1 end
    end
    session.TryStartBattle=function() error("unexpected battle start") end
    return session,map
end
local sessions={}
for i=1,19 do sessions[i]=newSession() end
for i=1,60 do for _,s in ipairs(sessions) do s:OnUpdate(1/60) end end
assert(scans<=19*8 and scans>=19*5 and refreshes==0, "empty-map poll budget: scans="..scans.." refreshes="..refreshes)
local active,activeMap=newSession()
active.EntryPolicyResolved=true
active.PlayerEntity={CurrentMap=activeMap}
local scansBefore=scans
active:OnUpdate(1/60)
assert(scans==scansBefore and refreshes==5)
active.PlayerEntity.CurrentMap={}
active.HudRelicSnapshot="previous"
refreshes=0
active:OnUpdate(1/60)
assert(refreshes==0 and active.HudRelicSnapshot=="")
local entry={EntryState="PREPARED",RequestId=2,LastTransferRequestId=2,StageId="stage_1"}
local incoming={CurrentMap=activeMap,GetComponent=function() return entry end}
_BattleGatewayLogic={}
_BattleGatewayLogic.ValidatePreparedBattleDestination=function(_,player,session)
    return {Success=player.CurrentMap==session.Entity and entry.StageId=="stage_1"}
end
active.PlayerExitObservedAfterBattle=true
active.LastInitializedEntryRequestId=1
active._T.EntryUserScanRemaining=0
_UserService.GetUsersByMapComponent=function() return {incoming} end
active:OnUpdate(1/60)
assert(active.PlayerEntity==incoming and refreshes==5, "re-entry must still resume")
print("PASS session: 19 empty maps, active update, departed map, prepared re-entry")

-- Re-entry must not depend on observing an empty map between two visits.
local function pollEntry(phase, result, state, transferId, stage, expected)
    local s,m=newSession()
    s.EntryPolicyResolved=true
    s.BattlePhase=phase
    s.BattleResult=result
    s.LastInitializedEntryRequestId=1
    local calls=0
    s.OnMapEnter=function() calls=calls+1 end
    s.TryStartBattle=function() end
    entry.EntryState=state
    entry.LastTransferRequestId=transferId
    entry.StageId=stage
    incoming.CurrentMap=m
    if phase=="Victory" then s.PlayerEntity=incoming end
    _UserService.GetUsersByMapComponent=function() return {incoming} end
    s:OnUpdate(0.16)
    assert(calls==expected, phase.."/"..state.."/"..stage..": "..calls)
end
pollEntry("Victory","VICTORY","PREPARED",2,"stage_1",1)
pollEntry("Setup","","PREPARED",2,"stage_1",1)
pollEntry("Victory","VICTORY","PREPARED",1,"stage_1",0)
pollEntry("Victory","VICTORY","PREPARED",2,"other_map_stage",0)
pollEntry("Setup","","INITIALIZING",2,"stage_1",0)
pollEntry("Setup","","STARTED",2,"stage_1",0)
print("PASS entry: missed exit, idle setup, reward guard, destination guard, no duplicate initialization")

-- Reward -> boss uses direct navigation, so it must also arm the entry poll.
log_warning=function() end
local marked,teleports=0,0
local prepared={EntryState="PREPARED",StageId="henesys_stage_04",RequestId=3,
    TryMarkTransferRequested=function(self,id) marked=marked+1; self.LastTransferRequestId=id end}
local traveler={Name="tester",PlayerComponent={UserId="test"},GetComponent=function() return prepared end}
local nav=attach({PreTransferUiDelay=0.15},navigationMethods)
nav.CapturePendingTransfer=function() return {} end
nav.PrepareClientForMapTransfer=function() end
nav.WatchTransferArrival=function() end
nav.ConsumePendingTransfer=function() return true end
local delayed
_EntityService={GetEntityByPath=function() return {MapComponent={}} end}
_TimerService={SetTimerOnce=function(_,callback) delayed=callback; return 1 end}
_TeleportService={TeleportToMapPosition=function() teleports=teleports+1 end}
_StageMapRouteRepositoryLogic={GetMapRoute=function() return {Success=true,MapId="henesys_boss"} end}
nav:TeleportPlayer(traveler,"new_skill_stage",{},"VICTORY_REWARD")
delayed()
assert(marked==0 and teleports==1,"reward transfer must not arm battle initialization")
nav:TeleportPlayer(traveler,"henesys_boss",{},"NEW_SKILL_STAGE_COMPLETE")
assert(marked==0,"do not arm a transfer before its stale-request check")
delayed()
assert(marked==1 and prepared.LastTransferRequestId==3 and teleports==2)
nav.ConsumePendingTransfer=function() return false end
nav:TeleportPlayer(traveler,"henesys_boss",{},"NEW_SKILL_STAGE_COMPLETE")
delayed()
assert(marked==1 and teleports==2,"stale transfer must not arm or teleport")
local waiting=false
nav.PendingTransfers={}
nav.CapturePendingTransfer=function() local p={UserId='test'}; nav.PendingTransfers.test=p; return p end
nav.WaitForDestination=function() waiting=true end
_EntityService.GetEntityByPath=function() return nil end
local rejectedResult=nav:TeleportPlayer(traveler,"new_upgrade_stage",{},"VICTORY_REWARD")
assert(rejectedResult.Success and rejectedResult.Reason=="WAITING_FOR_DESTINATION" and waiting)
assert(teleports==2,'unavailable map must never detach the player')
print("PASS navigation: reward -> boss entry marker, intermediate reward guard, stale transfer guard")

-- A durable purchase sends immediately without rebuilding/loading the product lists.
local sent=0
_UnionShopServiceLogic={RequestShop=function() sent=sent+1 end}
_GameSettingsLogic={PlayUISound=function() end}
local buy={TextGUIRendererComponent={Text=""},ButtonComponent={Enable=true}}
local equip={ButtonComponent={Enable=true}}
local popup={Enable=true}
local shop=attach({_T={},UnionMode=true,UnionPending=false,UnionRequestId=0,UnionRequestAge=0,
    UnionSnapshot={Revision=1,Coins=2000,JobTokens=0},UnionMessage="",AvatarBound=true,
    ClickSoundRUID="",FullRefreshes=0,Status=""},shopMethods)
shop.GetEntity=function(_,path)
    if path=="ShopPopup" then return popup end
    if path=="ShopPopup/BuybackButton" then return buy end
    if path=="ShopPopup/SellButton" then return equip end
end
shop.SetStatus=function(self,text) self.Status=text end
shop.RefreshUnionShop=function(self) self.FullRefreshes=self.FullRefreshes+1 end
shop.UpdateTooltipHover=function() end
shop.CloseUi=function() error("unexpected close") end
shop.BindPlayerAvatar=function() error("unexpected portrait load") end
_UserService.LocalPlayer={CurrentMap={Name="lobby"}}
_UtilLogic.ElapsedSeconds=10
shop:SendUnionAction("BUY","token")
assert(sent==1 and shop.UnionPending and shop.FullRefreshes==0 and not buy.ButtonComponent.Enable)
shop:SendUnionAction("BUY","token")
assert(sent==1, "one purchase in flight")
shop:OnUpdate(16)
assert(not shop.UnionPending and shop._T.UnionRequestUncertain)
assert(shop.UnionSnapshot.Coins==2000 and shop.UnionSnapshot.Revision==1)
shop:SendUnionAction("BUY","token")
assert(sent==1, "uncertain outcome cannot be blindly purchased again")
_UtilLogic.ElapsedSeconds=26
shop:ReceiveUnionShop(1,true,"PURCHASED",{Revision=2,Coins=0,JobTokens=1})
assert(not shop._T.UnionRequestUncertain and shop.UnionSnapshot.JobTokens==1 and shop.FullRefreshes==1)
shop:ReceiveUnionShop(0,true,"PURCHASED",{Revision=3,Coins=999})
assert(shop.UnionSnapshot.Revision==2, "ignore an old opening's reply")
shop:SendUnionAction("EQUIP","skin")
assert(sent==2 and shop.FullRefreshes==1)
shop:ReceiveUnionShop(2,false,"LOAD_FAILED",{})
assert(shop.UnionSnapshot.Revision==2 and shop._T.UnionRequestUncertain)
print("PASS shop: immediate request, duplicate guard, timeout safety, late confirmation, failed snapshot")
''')
