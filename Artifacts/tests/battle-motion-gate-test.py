"""Execute extracted mLua gate bodies with deterministic RPC/timer mocks, not Maker."""
from pathlib import Path
import os
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "RootDesk/MyDesk/01_Combat/Components/Shared"
PATTERN = re.compile(r"^\tmethod\s+\w+\s+(\w+)\(([^)]*)\)\n(.*?)^\tend$", re.M | re.S)


def methods(runtime, filename):
    result = runtime.table()
    source = (SHARED / filename).read_text(encoding="utf-8-sig")
    for name, parameters, body in PATTERN.findall(source):
        names = [parameter.strip().split()[-1] for parameter in parameters.split(",") if parameter.strip()]
        result[name] = runtime.eval("function(self" + ("," + ",".join(names) if names else "") + ")\n" + body + "\nend")
    assert len(list(result.keys())) > 0, filename
    return result


SETUP = r'''
clock = 0
events = {}
nextTimer = 0
rpcCount = {}
drop = {}
receiptDelay = {}
networkDelay = 0.1
senderUserId = "owner"
_UtilLogic = { ElapsedSeconds = 0 }
function isvalid(value) return value ~= nil and value.Valid ~= false end
function log(value) end
function log_warning(value) end
function Vector3(x,y,z) return {x=x,y=y,z=z} end
_TimerService = {}
function _TimerService:SetTimerOnce(callback, delay)
    nextTimer = nextTimer + 1
    events[nextTimer] = {At=clock+delay, Callback=callback}
    return nextTimer
end
function _TimerService:ClearTimer(timer) events[timer] = nil end
function advance(untilTime)
    local iterations = 0
    while true do
        local firstId, first = nil, nil
        for id, event in pairs(events) do
            if event.At <= untilTime and (first == nil or event.At < first.At or (event.At == first.At and id < firstId)) then
                firstId, first = id, event
            end
        end
        if first == nil then break end
        events[firstId] = nil
        clock = first.At
        _UtilLogic.ElapsedSeconds = clock
        first.Callback()
        iterations = iterations + 1
        assert(iterations < 50000, "timer loop did not terminate")
    end
    clock = untilTime
    _UtilLogic.ElapsedSeconds = clock
end
map = {Valid=true, Name="battle"}
presentations = {}
map.Scans = 0
function map:GetChildComponentsByTypeName(name, recursive)
    assert(name == "script.BattleUnitPresentationComponent" and recursive == true)
    self.Scans = self.Scans + 1
    return presentations
end
player = {Valid=true, CurrentMap=map, PlayerComponent={UserId="owner"}}
function player:GetComponent(name) return self.Presentation end
_UserService = { LocalPlayer=player }
function unit()
    local entity = {Valid=true, CurrentMap=map, BattleUnit={IsDead=false}}
    local presentation = {_T={}, Entity=entity, PendingUntil=0, Calls=0}
    function presentation:IsFullMotionPending() return clock < self.PendingUntil end
    function presentation:PlayCombatMotion(id, key, action, rate, duration, handoff)
        self.Calls = self.Calls + 1
        self.PendingUntil = math.max(clock, self.PendingUntil) + duration
    end
    function presentation:PlaySpriteMotion(id, ruid, rate, duration, facing, hit)
        self.Calls = self.Calls + 1
        self.PendingUntil = math.max(clock, self.PendingUntil) + duration
    end
    function presentation:PlayHitImpact(id, strong, normalStop, strongStop, reaction, flash, skip)
        self.Calls = self.Calls + 1
        if not skip then self.PendingUntil = math.max(clock, self.PendingUntil) + 0.5 end
    end
    function presentation:RefreshDefeatedDisplay(id, team, dead)
        if self.Calls > 0 and dead and self.Entity.BattleUnit.IsDead then return end
        self.Calls = self.Calls + 1
        self.PendingUntil = clock + 0.65
        _TimerService:SetTimerOnce(function() self.Entity.BattleUnit.IsDead=true end,.02)
    end
    function entity:GetComponent(name)
        if name == "script.BattleUnitComponent" then return self.BattleUnit end
        assert(name == "script.BattleUnitPresentationComponent")
        return presentation
    end
    table.insert(presentations, presentation)
    return entity, presentation
end
server = setmetatable({_T={}, EntryRequestId=1, Entity=map, PlayerEntity=player, ImpactTimerId=0}, {__index=M})
client = setmetatable({_T={}, EntryRequestId=0, Entity=map, PlayerEntity=player}, {__index=M})
function network(target, name, ...)
    rpcCount[name] = (rpcCount[name] or 0) + 1
    if (drop[name] or 0) > 0 then drop[name]=drop[name]-1; return end
    local args = table.pack(...)
    local delay = networkDelay
    if name == "ReceiveMotionPresentation" then delay = receiptDelay[args[4]] or delay end
    _TimerService:SetTimerOnce(function() M[name](target, table.unpack(args,1,args.n)) end, delay)
end
function server:ReceiveMotionPresentation(...) network(client,"ReceiveMotionPresentation",...) end
function server:AwaitClientMotionCompletion(...) network(client,"AwaitClientMotionCompletion",...) end
function server:CancelClientMotionCompletionWaits(...) network(client,"CancelClientMotionCompletionWaits",...) end
function server:DiscardClientMotionPresentationLedger(...) network(client,"DiscardClientMotionPresentationLedger",...) end
function server:CancelMotionPresentationReceipt(...) network(client,"CancelMotionPresentationReceipt",...) end
function client:ConfirmMotionCompletion(...) network(server,"ConfirmMotionCompletion",...) end
function client:RequestMissingMotionPresentations(...) network(server,"RequestMissingMotionPresentations",...) end
released = 0
releasedAt = nil
function gate(minimum, seal)
    local sequence = server:BeginMotionCompletionWait(function() released=released+1; releasedAt=clock end)
    if seal ~= false then server:SealMotionCompletionWhenImpactsFinish(sequence) end
    _TimerService:SetTimerOnce(function() server:MarkMotionCompletionReady(sequence) end, minimum)
    return sequence
end
function combat(entity,duration)
    server:SendMotionPresentation(entity,"COMBAT",{UnitId="actor",MotionKey="ATTACK",ActionName="",PlayRate=1,Duration=duration})
end
function hit(entity)
    server:SendMotionPresentation(entity,"HIT",{UnitId="target",Strong=false,NormalStop=.04,StrongStop=.065,Reaction=.08,Flash=.1,SkipMotion=false})
end
'''


def scenario(name, body):
    runtime = LuaRuntime(unpack_returned_tuples=True)
    runtime.globals().M = methods(runtime, "BattleSessionComponent.mlua")
    runtime.globals().P = methods(runtime, "BattleUnitPresentationComponent.mlua")
    methods(runtime, "FaustSummonComponent.mlua")
    runtime.execute(SETUP)
    runtime.execute(body)
    print("PASS", name)


# These two legacy bodies are copied verbatim from pre-change HEAD. They do not
# understand confirmedDeathAwaitSync and may clear death state on an early HP sync.
LEGACY_SETUP = r'''
local legacy={}
for name,method in pairs(P) do
    if name~="ResetConfirmedDeathPresentation" and name~="PlayConfirmedDeathPresentation" then legacy[name]=method end
end
legacy.IsFullMotionPending=function(self)
    return self._T.fullMotion ~= nil or (self._T.fullMotionQueue ~= nil and #self._T.fullMotionQueue > 0) or self.DeathMotionActive
end
legacy.RefreshDefeatedDisplay=function(self,unitId,team,isDead)
    -- Airborne bosses use the same visibility boundary while remaining alive in the turn order.
    if team ~= "Enemy" then
        local currentMap = self.Entity.CurrentMap
        if self.Entity.PlayerComponent ~= nil and isvalid(currentMap) and currentMap.Name == "lobby" then
            self:RestoreAvatarDeathMotion("LOBBY_SYNC")
            return
        end
        if isDead and self.DeathMotionActive == false and self.DeathMotionCompleted == false and self.Entity.AvatarRendererComponent ~= nil then
            self:CancelCombatMotionHandoff(unitId, "DEATH_STARTED", false)
            local body = self.Entity.AvatarRendererComponent:GetBodyEntity()
            if isvalid(body) then
                self.DeathMotionActive = true
                self:WatchFullMotion(body, "AVATAR_DEATH", function()
                    self.DeathMotionActive = false
                    self.DeathMotionCompleted = true
                end)
                local deathEvent = BodyActionStateChangeEvent()
                deathEvent.ActionState = MapleAvatarBodyActionState.Dead
                deathEvent.needResetAction = true
                deathEvent.playRate = self:GetLocalMotionSpeed()
                self.Entity:SendEvent(deathEvent)
            end
        elseif isDead == false then
            self:RestoreAvatarDeathMotion("UNIT_ALIVE")
            self.DeathMotionActive = false
            self.DeathMotionCompleted = false
        end
        return
    end
    local unit = self.Entity:GetComponent("script.BattleUnitComponent")
    local isAirborne = unit ~= nil and unit.IsAirborne == true
    local shouldEnable = isDead == false and isAirborne == false
    if isDead then
        self:StopMoveHopVisual("UNIT_DEFEATED")
        self:PlayDeathMotion(unitId)
    else
        if self.DeathMotionTimerId > 0 then
            _TimerService:ClearTimer(self.DeathMotionTimerId)
            self.DeathMotionTimerId = 0
        end
        self.DeathMotionActive = false
        self.DeathMotionCompleted = false
    end
    if self.Entity.SpriteRendererComponent ~= nil then
        if isDead == false or self.DeathMotionRuid == "" then
            self.Entity.SpriteRendererComponent.Enable = shouldEnable
        end
    end
    log("[BattlePresentation] visibility unit=" .. unitId .. " enabled=" .. tostring(shouldEnable) .. " dead=" .. tostring(isDead) .. " airborne=" .. tostring(isAirborne))
end
battleUnit={UnitId="enemy",Team="Enemy",IsDead=false,IsAirborne=false}
renderer={Enable=true,SpriteRUID="idle",PlayRate=1,StartFrameIndex=0,EndFrameIndex=100}
entity={Valid=true,CurrentMap=map,SpriteRendererComponent=renderer}
actor=setmetatable({_T={},Entity=entity,DeathMotionActive=false,DeathMotionCompleted=false,DeathMotionRuid="death",DeathMotionPlayRate=3,DeathMotionHoldDuration=.3,DeathMotionTimerId=0}, {__index=legacy})
function entity:GetComponent(name)
    if name=="script.BattleUnitPresentationComponent" then return actor end
    if name=="script.BattleUnitComponent" then return battleUnit end
    error("unexpected component "..name)
end
function actor:StopMoveHopVisual(reason) end
function actor:CancelFullMotionPlayback(reason) self._T.fullMotion=nil end
function actor:StopSpriteMotion(id,reason) end
function actor:ApplySpriteFacing(id,facing) end
function actor:GetLocalMotionSpeed() return 1 end
starts=0
function actor:WatchFullMotion(target,kind,complete)
    starts=starts+1; self._T.fullMotion={Kind=kind}
    _TimerService:SetTimerOnce(function() self._T.fullMotion=nil; complete() end,.4)
end
table.insert(presentations,actor)
server:SendMotionPresentation(entity,"DEATH",{UnitId="enemy",Team="Enemy"})
gate(.2)
'''


scenario("parallel acknowledgement preserves minimum and avoids post-minimum query", r'''
actor,p = unit(); combat(actor,.25); sequence=gate(.8)
advance(.79); assert(released==0)
assert(server._T.motionCompletionWaits[sequence].ClientReady==true)
advance(.81); assert(released==1 and math.abs(releasedAt-.8)<.000001)
assert(map.Scans==1 and client.EntryRequestId==0)
advance(2); assert(released==1)
''')
scenario("delayed launch cannot be mistaken for an empty completed scene", r'''
actor,p = unit(); receiptDelay[1]=.7; combat(actor,.3); gate(.2)
advance(.69); assert(released==0)
advance(.99); assert(released==0)
advance(1.2); assert(released==1 and releasedAt>=1.1)
''')
scenario("reordered launches and duplicate receipts", r'''
actor,p = unit(); receiptDelay[1]=.4; receiptDelay[2]=.1
combat(actor,.2); hit(actor); gate(.05)
advance(.2); assert(released==0)
M.ReceiveMotionPresentation(client,actor,"HIT",{UnitId="target",SkipMotion=false},2,1,1)
assert(p.Calls==1)
advance(1.01); assert(released==1 and p.Calls==2)
assert(releasedAt>=.9)
''')
scenario("producer stays unsealed until late impact and queued HIT finish", r'''
actor,p = unit(); combat(actor,.45); server.ImpactTimerId=123; sequence=gate(.2)
_TimerService:SetTimerOnce(function() hit(actor); server.ImpactTimerId=0 end,.35)
advance(.34); assert(released==0 and not server._T.motionCompletionWaits[sequence].Sealed)
advance(.9); assert(released==0)
advance(1.2); assert(released==1 and releasedAt>=1.15)
assert(rpcCount.RequestMissingMotionPresentations==nil)
''')
scenario("death display and final hold still gate the next action", r'''
actor,p = unit(); server:SendMotionPresentation(actor,"DEATH",{UnitId="target",Team="Enemy"}); gate(.3)
advance(.74); assert(released==0)
advance(.9); assert(released==1 and releasedAt>=.85)
''')
scenario("late emission invalidates a previously acknowledged receipt count", r'''
actor,p = unit(); combat(actor,.1); sequence=gate(.8)
advance(.4); assert(server._T.motionCompletionWaits[sequence].ClientReady)
hit(actor); assert(not server._T.motionCompletionWaits[sequence].ClientReady)
M.ConfirmMotionCompletion(server,sequence,1,1,1)
advance(.81); assert(released==0)
advance(1.2); assert(released==1)
''')
scenario("dropped motion RPC is replayed without duplicated playback", r'''
actor,p = unit(); drop.ReceiveMotionPresentation=1; combat(actor,.2); gate(.05)
advance(.6); assert(released==0)
advance(1.3); assert(released==1 and p.Calls==1)
assert(rpcCount.RequestMissingMotionPresentations>=1)
''')
scenario("dropped acknowledgement is retried without a 60 second wait", r'''
actor,p = unit(); drop.ConfirmMotionCompletion=1; combat(actor,.1); gate(.05)
advance(.5); assert(released==0)
advance(1.4); assert(released==1 and releasedAt<2)
''')
scenario("lost seal marker is recovered by idempotent retry", r'''
actor,p = unit(); combat(actor,.1)
drop.AwaitClientMotionCompletion=2; gate(.05)
advance(.9); assert(released==0)
advance(1.5); assert(released==1 and p.Calls==1)
''')
scenario("clear and delayed old seal cannot resurrect a cancelled gate", r'''
actor,p = unit(); combat(actor,.2); sequence=gate(.5)
server:ClearMotionCompletionWaits(); advance(.3)
M.AwaitClientMotionCompletion(client,sequence,1,1,1)
advance(1.3); assert(released==0)
assert(client._T.clientMotionCompletionWaits[sequence]==nil)
''')
scenario("old epoch receipt and acknowledgement cannot release a new entry", r'''
actor,p = unit(); old=gate(.8); advance(.2)
server:ClearMotionCompletionWaits(); server.EntryRequestId=2
combat(actor,.1); current=gate(.5)
advance(.45); before=p.Calls
M.ReceiveMotionPresentation(client,actor,"COMBAT",{UnitId="old",MotionKey="ATTACK",ActionName="",PlayRate=1,Duration=10},1,1,1)
assert(p.Calls==before)
M.ConfirmMotionCompletion(server,current,1,1,0)
advance(.69); assert(released==0)
advance(.8); assert(released==1)
''')
scenario("map leave and forged ownership never release an action", r'''
actor,p = unit(); sequence=gate(.3)
senderUserId="intruder"; M.ConfirmMotionCompletion(server,sequence,1,1,0)
assert(not server._T.motionCompletionWaits[sequence].ClientReady)
senderUserId="owner"; player.CurrentMap={Valid=true,Name="lobby"}
advance(61); assert(released==0)
assert(server._T.motionPresentationLedger==nil and next(server._T.motionCompletionWaits)==nil)
assert(client._T.clientMotionPresentationLedger==nil and next(client._T.clientMotionCompletionWaits or {})==nil)
''')
scenario("emergency timeout does not start before the server minimum", r'''
actor,p = unit(); drop.ConfirmMotionCompletion=1000; sequence=gate(65)
advance(64); assert(released==0 and server._T.motionCompletionWaits[sequence]~=nil)
advance(65.1); assert(released==0)
advance(125.1); assert(released==1)
''')

# Actual presentation helpers, native visual root/tween boundaries mocked.
scenario("prediction offsets preserve hop baseline and late server-hop dedup", r'''
visual={Valid=true,TransformComponent={Position=Vector3(.25,2,0),Scale=Vector3(1,1,1),Rotation=0}}
entity={Valid=true,AvatarRendererComponent={},CurrentMap=map}
function entity.AvatarRendererComponent:GetAvatarRootEntity() return visual end
actor=setmetatable({_T={},Entity=entity,UseCustomMoveHopProfile=false,DeathMotionActive=false,DeathMotionCompleted=false}, {__index=P})
function actor:StartMoveHopAnimation(state,ruid,rate) end
function actor:RestoreMoveHopAnimation(state,reason) end
_TweenLogic={}
EaseType={Linear=1}
function _TweenLogic:PlayTween(a,b,duration,ease,callback)
    self.Count=(self.Count or 0)+1; self.LastCallback=callback
    local tween={}
    function tween:Destroy() self.Destroyed=true end
    function tween:SetOnEndCallback(callback) self.EndCallback=callback end
    self.LastTween=tween
    return tween
end
actor:SetLocalGridMoveOffset(.5)
actor:BeginLocalGridMoveHop("owner",.13,.09,.02,.04,1.03,.97,1.05,.95,.5,"",3,7)
_TweenLogic.LastCallback(.5)
assert(math.abs(visual.TransformComponent.Position.x-.75)<.000001)
assert(visual.TransformComponent.Position.y>2)
actor:ClearLocalGridMoveOffset()
assert(visual.TransformComponent.Position.x==.25 and visual.TransformComponent.Position.y==2)
actor:PlayMoveHop("owner",.13,.09,.02,.04,1.03,.97,1.05,.95,.5,"",3,true,7)
assert(_TweenLogic.Count==1)
actor:PlayMoveHop("owner",.13,.09,.02,.04,1.03,.97,1.05,.95,.5,"",3,true,0)
assert(_TweenLogic.Count==2)
actor:SetLocalGridMoveOffset(.3); actor:ClearLocalGridMoveOffset()
assert(actor._T.moveHopVisual~=nil)
''')
scenario("actual fixed HIT duration remains 0.5 seconds", r'''
actor={_T={}}
local completed=0
actor._T.fullMotion={Kind="HIT",Finish=function() completed=completed+1 end}
P.SetHitMotionDuration(actor)
advance(.499); assert(completed==0)
advance(.5); assert(completed==1)
''')
scenario("confirmed death survives HP sync arriving before IsDead", r'''
local battleUnit={IsDead=false,IsAirborne=false}
local renderer={Enable=true,SpriteRUID="idle",PlayRate=1,StartFrameIndex=0,EndFrameIndex=100}
entity={Valid=true,CurrentMap=map,SpriteRendererComponent=renderer}
function entity:GetComponent(name) return battleUnit end
actor=setmetatable({_T={},Entity=entity,DeathMotionActive=false,DeathMotionCompleted=false,DeathMotionRuid="death",DeathMotionPlayRate=3,DeathMotionHoldDuration=.3,DeathMotionTimerId=0}, {__index=P})
function actor:StopMoveHopVisual(reason) end
function actor:CancelFullMotionPlayback(reason) self._T.fullMotion=nil end
function actor:StopSpriteMotion(id,reason) end
function actor:ApplySpriteFacing(id,facing) end
function actor:GetLocalMotionSpeed() return 1 end
function actor:WatchFullMotion(target,kind,complete)
    self._T.fullMotion={Kind=kind}
    _TimerService:SetTimerOnce(function() self._T.fullMotion=nil; complete() end,.4)
end
actor:PlayConfirmedDeathPresentation("enemy","Enemy")
actor:RefreshDefeatedDisplay("enemy","Enemy",false)
assert(actor.DeathMotionActive)
advance(.699); assert(actor:IsFullMotionPending())
advance(.701); assert(not actor:IsFullMotionPending() and actor.DeathMotionCompleted)
battleUnit.IsDead=true; actor:RefreshDefeatedDisplay("enemy","Enemy",true)
assert(not actor._T.confirmedDeathAwaitSync)
''')

scenario("client component replication catches up before receipt acknowledgement", r'''
actor,p = unit(); combat(actor,.2); gate(.05)
local getter=actor.GetComponent
local serverVisible=true
function actor:GetComponent(name)
    if serverVisible then return getter(self,name) end
    return nil
end
-- The initial server dispatch already saw its presentation; only the first client delivery misses it.
serverVisible=false
advance(.3); assert(released==0 and client._T.clientMotionPresentationLedger.Count==0)
serverVisible=true
advance(1.3); assert(released==1 and p.Calls==1)
''')
scenario("no server presentation produces no receipt", r'''
actor={Valid=true,CurrentMap=map}
function actor:GetComponent(name) return nil end
combat(actor,.2); gate(.1)
advance(.5); assert(released==1 and server._T.motionPresentationLedger.Count==0)
''')
scenario("removed server target cancels the missing receipt without a ghost animation", r'''
actor,p=unit(); drop.ReceiveMotionPresentation=1; combat(actor,.2); gate(.1)
actor.Valid=false
advance(1.3); assert(released==1 and p.Calls==0)
assert(rpcCount.CancelMotionPresentationReceipt==1)
''')
scenario("enemy sprite fallback dispatch uses its source entity", r'''
actor,p=unit(); p.AttackMotionRuid="attack"; p.AttackMotionDuration=.35; p.AttackMotionPlayRate=3
local getter=actor.GetComponent
function actor:GetComponent(name)
    if name=="script.BattleUnitComponent" then return {Facing="Left",EnemyDefinitionId="test"} end
    return getter(self,name)
end
function server:GetSkillSpeedMultiplier() return 2 end
server:PlayEnemyAttackMotion(actor,"enemy",{SkillId="test",ActionDuration=.35})
gate(.1); advance(.5)
assert(released==1 and p.Calls==1 and server._T.motionPresentationLedger.Count==1)
''')
scenario("client entity creation after the RPC is recovered", r'''
actor,p=unit(); combat(actor,.2); gate(.05)
actor.Valid=false
advance(.3); assert(released==0 and client._T.clientMotionPresentationLedger.Count==0)
actor.Valid=true
advance(1.3); assert(released==1 and p.Calls==1)
''')
scenario("yielding impact stays unsealed until its final death launch", r'''
actor,p=unit(); combat(actor,.2); server.ImpactTimerId=123; sequence=gate(.1)
_TimerService:SetTimerOnce(function() hit(actor) end,.3)
_TimerService:SetTimerOnce(function()
    server:SendMotionPresentation(actor,"DEATH",{UnitId="enemy",Team="Enemy"})
    server.ImpactTimerId=0
end,1.2)
advance(1.1); assert(released==0 and not server._T.motionCompletionWaits[sequence].Sealed)
advance(2); assert(released==0)
advance(2.3); assert(released==1 and releasedAt>=2.05)
assert(rpcCount.RequestMissingMotionPresentations==nil)
''')
scenario("reentrant duplicate launch is ignored before its first dispatch returns", r'''
actor,p=unit(); local play=p.PlayCombatMotion
function p:PlayCombatMotion(id,key,action,rate,duration,handoff)
    M.ReceiveMotionPresentation(client,actor,"COMBAT",{UnitId=id,MotionKey=key,ActionName=action,PlayRate=rate,Duration=duration},1,1,1)
    play(self,id,key,action,rate,duration,handoff)
end
combat(actor,.1); gate(.05); advance(.5)
assert(released==1 and p.Calls==1 and client._T.clientMotionPresentationLedger.Count==1)
''')
scenario("late emit after logout or missing PlayerComponent is harmless", r'''
actor,p=unit(); combat(actor,.1); sequence=gate(.8)
advance(.35); assert(server._T.motionCompletionWaits[sequence].ClientReady)
player.Valid=false
combat(actor,.2); server:SealMotionCompletionWait(sequence)
assert(server:BeginMotionCompletionWait(function() error("invalid player release") end)==0)
M.ConfirmMotionCompletion(server,sequence,1,1,1)
advance(1.2); assert(released==0 and server._T.motionPresentationLedger==nil)
player.Valid=true; player.PlayerComponent=nil
combat(actor,.2); server:SealMotionCompletionWait(sequence)
assert(server:BeginMotionCompletionWait(function() error("missing component release") end)==0)
M.ConfirmMotionCompletion(server,sequence,1,1,1)
M.RequestMissingMotionPresentations(server,sequence,1,1,"1")
assert(server._T.motionPresentationLedger==nil)
''')
scenario("legacy presentation without new methods still resets and gates confirmed death", r'''
local battleUnit={IsDead=false,IsAirborne=false}
local renderer={Enable=true,SpriteRUID="idle",PlayRate=1,StartFrameIndex=0,EndFrameIndex=100}
local legacy={}
for name,method in pairs(P) do
    if name~="ResetConfirmedDeathPresentation" and name~="PlayConfirmedDeathPresentation" then legacy[name]=method end
end
entity={Valid=true,CurrentMap=map,SpriteRendererComponent=renderer}
actor=setmetatable({_T={confirmedDeathAwaitSync=true},Entity=entity,DeathMotionActive=false,DeathMotionCompleted=false,DeathMotionRuid="death",DeathMotionPlayRate=3,DeathMotionHoldDuration=.3,DeathMotionTimerId=0}, {__index=legacy})
function entity:GetComponent(name)
    if name=="script.BattleUnitPresentationComponent" then return actor end
    if name=="script.BattleUnitComponent" then return battleUnit end
    error("unexpected component "..name)
end
function actor:StopMoveHopVisual(reason) end
function actor:CancelFullMotionPlayback(reason) self._T.fullMotion=nil end
function actor:StopSpriteMotion(id,reason) end
function actor:ApplySpriteFacing(id,facing) end
function actor:GetLocalMotionSpeed() return 1 end
local starts=0
function actor:WatchFullMotion(target,kind,complete)
    starts=starts+1; self._T.fullMotion={Kind=kind}
    _TimerService:SetTimerOnce(function() self._T.fullMotion=nil; complete() end,.4)
end
table.insert(presentations,actor)
player.Presentation=actor
assert(actor.ResetConfirmedDeathPresentation==nil and actor.PlayConfirmedDeathPresentation==nil)
M.GetClientMotionPresentationLedger(client,1,1)
assert(actor._T.confirmedDeathAwaitSync==false)
server:SendMotionPresentation(entity,"DEATH",{UnitId="enemy",Team="Enemy"})
gate(.2)
advance(.12)
assert(actor._T.confirmedDeathAwaitSync and actor.DeathMotionActive)
actor:RefreshDefeatedDisplay("enemy","Enemy",false)
M.ReceiveMotionPresentation(client,entity,"DEATH",{UnitId="enemy",Team="Enemy"},1,1,1)
assert(starts==1 and actor.DeathMotionActive)
_TimerService:SetTimerOnce(function() battleUnit.IsDead=true end,.08)
advance(.79); assert(released==0)
advance(1); assert(released==1 and starts==1)
''')
scenario("old death body clears active flag mid-clip but original hold is preserved", LEGACY_SETUP+r'''
advance(.2); actor:RefreshDefeatedDisplay("enemy","Enemy",false)
assert(actor.DeathMotionActive==false)
advance(.39); assert(released==0)
battleUnit.IsDead=true -- The value arrives before its OnSync handler executes.
advance(.79); assert(released==0 and starts==1)
advance(1); assert(released==1 and releasedAt>=.9 and starts==1)
''')
scenario("old death body cancels final hold but gate restores complete playback", LEGACY_SETUP+r'''
advance(.55); actor:RefreshDefeatedDisplay("enemy","Enemy",false)
assert(actor.DeathMotionTimerId==0 and not actor:IsFullMotionPending())
advance(.6); assert(released==0)
battleUnit.IsDead=true
advance(1.2); assert(released==0)
advance(1.6); assert(released==1 and starts==2 and releasedAt>=1.4)
''')
scenario("old death finishes before IsDead sync without an early acknowledgement", LEGACY_SETUP+r'''
advance(.2); actor:RefreshDefeatedDisplay("enemy","Enemy",false)
advance(.89); assert(released==0 and actor.DeathMotionCompleted)
battleUnit.IsDead=true
advance(1.2); assert(released==1 and starts==1 and releasedAt>=.99)
''')
scenario("ordinary motion polling never reads a unit component for death compatibility", r'''
entity,p=unit(); local getter=entity.GetComponent; local reads=0
function entity:GetComponent(name)
    if name=="script.BattleUnitComponent" then reads=reads+1 end
    return getter(self,name)
end
combat(entity,.5); gate(.1); advance(.8)
assert(released==1 and reads==0)
''')
scenario("map enter without a new clear helper still restores the lobby avatar", r'''
local restored=0
actor={_T={confirmedDeathAwaitSync=true}}
function actor:RestoreAvatarDeathMotion(reason) assert(reason=="LOBBY_ENTER"); restored=restored+1 end
P.OnMapEnter(actor,{Valid=true,Name="lobby"})
assert(restored==1 and not actor._T.confirmedDeathAwaitSync)
''')
scenario("map enter with strict unknown member lookup still restores the lobby avatar", r'''
local restored=0
actor=setmetatable({_T={confirmedDeathAwaitSync=true}}, {__index=function(self,key) error("unknown member "..key) end})
function actor:RestoreAvatarDeathMotion(reason) assert(reason=="LOBBY_ENTER"); restored=restored+1 end
P.OnMapEnter(actor,{Valid=true,Name="lobby"})
assert(restored==1 and not actor._T.confirmedDeathAwaitSync)
''')
scenario("map enter invokes the clear helper once and restores the lobby avatar", r'''
local restored,cleared=0,0
actor={_T={confirmedDeathAwaitSync=true}}
function actor:ClearLocalGridMoveOffset() cleared=cleared+1 end
function actor:RestoreAvatarDeathMotion(reason) assert(reason=="LOBBY_ENTER"); restored=restored+1 end
P.OnMapEnter(actor,{Valid=true,Name="lobby"})
assert(cleared==1 and restored==1 and not actor._T.confirmedDeathAwaitSync)
''')
scenario("map enter with a throwing clear helper still restores the lobby avatar", r'''
local restored,cleared=0,0
actor={_T={confirmedDeathAwaitSync=true}}
function actor:ClearLocalGridMoveOffset() cleared=cleared+1; error("old visual disappeared") end
function actor:RestoreAvatarDeathMotion(reason) assert(reason=="LOBBY_ENTER"); restored=restored+1 end
P.OnMapEnter(actor,{Valid=true,Name="lobby"})
assert(cleared==1 and restored==1 and not actor._T.confirmedDeathAwaitSync)
''')
print("All 33 battle motion gate scenarios passed (mock execution; Maker runtime not tested).")
