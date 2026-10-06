"""Run real movement method bodies against strict native contracts; no Maker runtime claims."""
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
        if name not in names:
            continue
        args = ",".join(p.strip().split()[-1] for p in params.split(",") if p.strip())
        result[name] = lua.execute("return function(self" + ("," + args if args else "") + ")\n" + body + "\nend")
    assert set(names) == set(result.keys()), (path, set(names) - set(result.keys()))
    return result


lua.globals().movement = load("RootDesk/MyDesk/00_Core/Movement/PlayerGridMovementLogic.mlua", {
    "GetProfile", "GetDuration", "EvaluateCurve", "Advance", "HasLocalMove", "BeginLocalMove",
    "ResolveLocalMove", "CancelLocalMove", "OnUpdate", "OnEndPlay", "PlayHop",
    "CancelBlockedMove", "UpdateBlockedMove", "BeginBlockedMove", "IsBlockedMoveReason",
})
lua.globals().battle = load("RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua", {
    "RequestMove", "ReceivePlayerMoveResult", "StartPlayerGridMovePresentation", "UpdatePlayerGridMove", "FinishPlayerGridMovePresentation", "PlayUnitMoveHop",
    "GetPlayerFloorPosition",
})
lua.globals().lobby = load("RootDesk/MyDesk/00_Core/LobbyGridMovementComponent.mlua", {
    "GetStepTargetX", "RequestMove", "ReceiveMoveContext", "ReceiveMoveResult", "OnUpdate", "SetGridControl",
    "UpdateLandingChecks",
})
lua.globals().presenter = load("RootDesk/MyDesk/02_UI/BattleHudPresenterLogic.mlua", {"DispatchLocalCommand"})
lua.execute(r'''
log=function() end; log_warning=function() warnings=warnings+1 end; isvalid=function(x) return x ~= nil and x ~= false end
Vector2=function(x,y) return {x=x,y=y} end
Vector3=setmetatable({zero={x=0,y=0,z=0}}, {__call=function(_,x,y,z) return {x=x,y=y,z=z} end})
-- Empty native proxies reject unknown reads AND writes; raw properties cannot bypass __newindex.
function native(values)
    return setmetatable({}, {__index=function(_,key)
        assert(values[key] ~= nil, 'unknown native read: '..key); return values[key]
    end, __newindex=function(_,key,value)
        assert(values[key] ~= nil, 'unknown native write: '..key); values[key]=value
    end})
end
function scriptProxy(values, reads)
    return setmetatable({}, {__index=function(_,key)
        reads[key]=(reads[key] or 0)+1
        assert(values[key] ~= nil, 'unknown script member: '..key)
        return values[key]
    end})
end
_TimerService={ClearTimer=function() timersCleared=timersCleared+1 end}
_UtilLogic={ElapsedSeconds=0}
_BattleHudPresenterLogic={ReleasePendingLocalCommand=function(_,_,reason) released=released+1; releaseReason=reason end}
_PlayerGridMovementLogic=movement
realPlayHop=movement.PlayHop; realPlayUnitMoveHop=battle.PlayUnitMoveHop
-- Prediction reads the frame clock like the hop does; the engine advances it by each frame's delta.
realMoveUpdate=movement.OnUpdate
movement.OnUpdate=function(self,d) _UtilLogic.ElapsedSeconds=_UtilLogic.ElapsedSeconds+d; return realMoveUpdate(self,d) end
function fixture()
    released=0; releaseReason=''; offsets={}; hops=0; clears=0; timersCleared=0; placements={}; receipts={}; requests=0; serverHops={}; warnings=0
    movement._T={}
    movement.BlockedMoveDistanceRatio=0.18; movement.BlockedMoveForwardDuration=0.06
    movement.BlockedMoveReturnDuration=0.14; movement.LandingSettleDuration=0.1
    movement.PlayHop=realPlayHop
    map={}; other={}; cell={CellIndex=2,Team='Player',UnitId='player_01'}
    presentation={BeginLocalGridMoveHop=function(_,...) hops=hops+1; localHopArgs={...} end,
        PlayMoveHop=function(_,...) serverHops[#serverHops+1]={...} end, PlaySkillSound=function() end,
        SetLocalGridMoveOffset2D=function(_,x) offsets[#offsets+1]=x end,
        ClearLocalGridMoveOffset=function() clears=clears+1 end}
    transform=native({WorldPosition=Vector3(2,0,0), ToLocalPoint=function(self,p)
        return Vector3(p.x-self.WorldPosition.x,p.y-self.WorldPosition.y,p.z-self.WorldPosition.z)
    end})
    player=native({CurrentMap=map, Name='player', TransformComponent=transform, PlayerComponent=native({UserId='owner'}),
        MovementComponent=native({Stop=function() end,SetWorldPosition=function(_,p) transform.WorldPosition=Vector3(p.x,p.y,0) end}),
        GetComponent=function(_,name)
            if name=='script.BattleUnitPresentationComponent' then return presentation end
            if name=='script.BattleUnitComponent' then return cell end
        end,
        PlayerControllerComponent=native({Enable=true}),
        CameraComponent=native({CameraOffset=Vector2(0,0),Damping=Vector2(2.5,5)})})
    _UserService={LocalPlayer=player,GetUserEntityByUserId=function(_,id) if id=='owner' then return player end end,
        GetUsersByMapComponent=function() return {player} end}
    session={EntryRequestId=7,HudContextRevision=3,BattleResult=''}
    map.GetComponent=function(_,name) if name=='script.BattleSessionComponent' then return session end end
    map.GetChildComponentsByTypeName=function() return {} end
    profile=movement:GetProfile(nil)
    for key,value in pairs(profile) do session[key]=value end
    battle._T={}; battle.Entity=map; battle.PlayerEntity=player; battle.EntryRequestId=7; battle.HudContextRevision=3
    for key,value in pairs(profile) do battle[key]=value end
    battle.BattlePhase='PlayerTurn'; battle.ActionTimerId=0; battle.TurnState={QueuedActionType='MOVE',IsActionProcessing=true}
    battle.MoveCurve='QUAD_EASE_OUT'; battle.MoveSnapThreshold=0.01
    battle.GetCellPosition=function(_,n) return Vector2(n,0) end
    battle.GetPlayerMoveDuration=function() return 0.13 end
    battle.PlayUnitMoveHop=realPlayUnitMoveHop
    battle.GetSkillSoundVolume=function() return 1 end
    _MaplePreferencesLogic={JumpSound='jump'}
    battle.PlaceEntity=function(_,who,p) assert(who.CurrentMap==map); placements[#placements+1]=p end
    battle.PublishPlayerCommandResult=function() end
    battle.CompleteQueuedAction=function() completedActions=completedActions+1 end
    battle.ReceivePlayerMoveResult=function(_,...) receipts[#receipts+1]={...} end
    battle.TryQueuePlayerAction=function(self)
        requests=requests+1; cell.CellIndex=cell.CellIndex+1
        self:StartPlayerGridMovePresentation(player,cell.CellIndex-1,cell.CellIndex)
        return {Success=true,Reason='OK'}
    end
    completedActions=0; senderUserId='owner'
end
function verifyMissingHelper(name)
    for mode=1,2 do
        fixture(); local values=presentation; values[name]=nil
        if mode==2 then presentation=scriptProxy(values,{}) end
        local id=movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile)
        assert(id==1 and hops==0 and movement:HasLocalMove(map))
        battle:RequestMove(1,id,7,3); assert(requests==1 and receipts[1][4]==true)
        for n=1,8 do movement:OnUpdate(0.1) end
        assert(#offsets==0 and warnings==1 and movement:HasLocalMove(map) and released==0)
        movement:ResolveLocalMove(map,id,7,3,true,true,3,0,'DONE')
        transform.WorldPosition=Vector3(3,0,0); movement:OnUpdate(0.01)
        assert(not movement:HasLocalMove(map) and clears==0 and released==1)
    end
end
function oldMoveRecord()
    movement._T.localMove={Player=player,Map=map,Entry=7,Context=3,RequestId=1,Presentation=presentation,
        Profile=profile,StartPosition=Vector2(2,0),TargetPosition=Vector2(3,0),Elapsed=0,Age=0,
        Duration=0.13,Confirmed=false,Completed=false}
end
''')

cases = {
    "immediate avatar prediction leaves authoritative root/cell unchanged": r'''
        fixture(); local id=movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile)
        assert(id==1 and hops==1 and movement:HasLocalMove(map))
        assert(localHopArgs[13]==id)
        movement:OnUpdate(0.065)
        assert(offsets[1]>0 and transform.WorldPosition.x==2 and cell.CellIndex==2)
        assert(movement:BeginLocalMove(player,map,7,3,Vector2(4,0),profile)==0)
    ''',
    "matching accept waits for complete and authoritative position": r'''
        fixture(); movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile)
        movement:ResolveLocalMove(map,1,7,3,true,false,3,0,'OK'); movement:OnUpdate(0.3)
        assert(movement:HasLocalMove(map) and offsets[#offsets]==1)
        movement:ResolveLocalMove(map,1,7,3,true,true,3,0,'DONE'); movement:OnUpdate(0.01)
        assert(movement:HasLocalMove(map)); transform.WorldPosition=Vector3(3,0,0)
        movement:OnUpdate(0.01); assert(not movement:HasLocalMove(map) and clears==0 and released==1)
        -- Landed: input is free, the avatar holds its ground line until the settle window ends.
        movement:OnUpdate(0.1); assert(movement._T.localMove==nil and clears==1 and released==1)
    ''',
    "stale request/context/map responses cannot clear newer prediction": r'''
        fixture(); movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile)
        for _,args in ipairs({{map,99,7,3},{map,1,6,3},{map,1,7,2},{other,1,7,3}}) do
            movement:ResolveLocalMove(args[1],args[2],args[3],args[4],false,true,2,0,'OLD')
        end
        assert(movement:HasLocalMove(map) and clears==0)
        movement:ResolveLocalMove(map,1,7,3,false,true,2,0,'BLOCKED')
        assert(not movement:HasLocalMove(map) and clears==1 and transform.WorldPosition.x==2)
        local id=movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile); assert(id==2)
        movement:ResolveLocalMove(map,1,7,3,false,true,2,0,'OLD'); assert(movement:HasLocalMove(map))
    ''',
    "accepted different endpoint corrects visual only": r'''
        fixture(); movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile); movement:OnUpdate(0.065)
        movement:ResolveLocalMove(map,1,7,3,true,false,4,0,'CORRECTED'); movement:OnUpdate(0.11)
        assert(offsets[#offsets]==2 and transform.WorldPosition.x==2 and cell.CellIndex==2)
    ''',
    "timeout map change entry generation and world shutdown clear prediction": r'''
        for mode=1,4 do
            fixture(); movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile)
            if mode==1 then movement:OnUpdate(2)
            elseif mode==2 then player.CurrentMap=other; movement:OnUpdate(0.01)
            elseif mode==3 then session.EntryRequestId=8; movement:OnUpdate(0.01)
            else movement:OnEndPlay() end
            assert(not movement:HasLocalMove(map) and clears==1 and released==1)
        end
    ''',
    "server processes request id once and rejects wrong owner or generation": r'''
        fixture(); battle:RequestMove(1,11,7,3); assert(requests==1)
        battle:RequestMove(1,11,7,3); battle:RequestMove(1,10,7,3); assert(requests==1)
        senderUserId='intruder'; battle:RequestMove(1,12,7,3); assert(requests==1)
        senderUserId='owner'; battle:RequestMove(1,12,6,3); assert(requests==1 and receipts[#receipts][4]==false)
        battle.BattlePhase='EnemyTurn'; battle:RequestMove(1,12,7,3)
        assert(requests==1 and receipts[#receipts][8]=='INVALID_PHASE')
    ''',
    "server completion targets original request and cannot teleport departed actor": r'''
        fixture(); battle:RequestMove(1,11,7,3)
        assert(battle._T.playerGridMove.RequestId==11 and receipts[1][9]=='owner')
        assert(serverHops[1][14]==11)
        -- The requesting client walks its own root, so the server writes it only once, on completion.
        assert(battle._T.playerGridMove.ClientDriven==true and #placements==0)
        battle:UpdatePlayerGridMove(0.05); assert(#placements==0)
        battle:UpdatePlayerGridMove(0.2)
        assert(battle._T.playerGridMove==nil and completedActions==1 and receipts[#receipts][5]==true)
        assert(#placements==1 and placements[1].x==3)
        fixture(); battle:RequestMove(1,12,7,3); local before=#placements
        player.CurrentMap=other; battle.ActionTimerId=42; battle:UpdatePlayerGridMove(0.1)
        assert(battle._T.playerGridMove==nil and #placements==before and completedActions==0 and timersCleared==1)
    ''',
    "lobby clamping and ownership context request gates": r'''
        fixture(); lobby._T={gridMoveContexts={owner=4}}; lobby.Entity=map
        lobby.CellSize=1; lobby.GridOriginX=2; lobby.MinX=0; lobby.MaxX=4
        lobby.ReceiveMoveResult=function(_,...) receipts[#receipts+1]={...} end
        lobby:RequestMove(1,1,3); assert(lobby._T.gridMoves==nil and receipts[1][3]==false)
        lobby:RequestMove(1,2,4); assert(lobby._T.gridMoves.owner.TargetPosition.x==3)
        assert(serverHops[1][14]==2)
        lobby:RequestMove(1,2,4); assert(#receipts==2)
        assert(lobby:GetStepTargetX(0,-1)==0 and lobby:GetStepTargetX(4,1)==4)
        lobby.IsClient=function() return false end; lobby._T.gridPlayers={owner=player}; lobby._T.playerScanRemaining=1
        lobby.LandingCheckDelay=0.5
        -- The client walks its own root; the server only times the step and leaves the transform alone.
        local before=transform.WorldPosition.x
        lobby:OnUpdate(0.3); assert(lobby._T.gridMoves.owner==nil and receipts[#receipts][4]==true)
        assert(transform.WorldPosition.x==before and lobby._T.gridLandingChecks.owner~=nil)
        -- A root that never arrived is corrected once the landing check expires.
        lobby:OnUpdate(0.6); assert(lobby._T.gridLandingChecks.owner==nil and transform.WorldPosition.x==3)
        lobby:ReceiveMoveContext(4); lobby:ReceiveMoveContext(3); assert(lobby._T.moveContext==4)
    ''',
    "reservation success without an actual move rejects prediction": r'''
        fixture(); battle.TryQueuePlayerAction=function() return {Success=true,Reason='RESERVED'} end
        battle:RequestMove(1,1,7,3)
        assert(receipts[1][4]==false and receipts[1][5]==true and battle._T.playerGridMove==nil)
    ''',
    "presenter starts prediction before sending the server request": r'''
        fixture(); session.Entity=map; session.CellCount=7
        session.GetCellPosition=function(_,n) return Vector2(n,0) end
        session.RequestMove=function(_,direction,id,entry,context)
            assert(movement:HasLocalMove(map) and hops==1 and id==1 and direction==1 and entry==7 and context==3)
            assert(transform.WorldPosition.x==2 and cell.CellIndex==2); requests=requests+1
        end
        presenter.TryBeginLocalCommand=function() return true end
        presenter.GetBattleSession=function() return session end
        presenter.ReleasePendingLocalCommand=function() released=released+1 end
        presenter:DispatchLocalCommand('MOVE','',1); assert(requests==1)
    ''',
    "lobby new entry accepts reset ids and still rejects old context": r'''
        fixture(); lobby.Entity=map; lobby._T={gridMoveContexts={owner=4},lastMoveRequestIds={owner=99}}
        lobby.CellSize=1; lobby.GridOriginX=2; lobby.MinX=0; lobby.MaxX=4
        lobby.ReceiveMoveResult=function(_,...) receipts[#receipts+1]={...} end
        lobby.ReceiveMoveContext=function(_,context,userId) assert(context==5 and userId=='owner') end
        lobby:SetGridControl(player,true)
        assert(lobby._T.gridMoveContexts.owner==5 and lobby._T.lastMoveRequestIds.owner==0)
        lobby:RequestMove(1,1,4); assert(lobby._T.gridMoves==nil)
        lobby:RequestMove(1,1,5); assert(lobby._T.gridMoves.owner.RequestId==1)
    ''',
    "missing setter falls back for nil and strict unknown script members": r'''
        verifyMissingHelper('SetLocalGridMoveOffset2D')
    ''',
    "missing begin helper falls back for nil and strict unknown script members": r'''
        verifyMissingHelper('BeginLocalGridMoveHop')
    ''',
    "missing clear helper falls back for nil and strict unknown script members": r'''
        verifyMissingHelper('ClearLocalGridMoveOffset')
    ''',
    "legacy component preserves presenter request and acknowledgement lock": r'''
        fixture(); local values=presentation
        values.SetLocalGridMoveOffset2D=nil; values.ClearLocalGridMoveOffset=nil; values.BeginLocalGridMoveHop=nil
        presentation=scriptProxy(values,{})
        session.Entity=map; session.CellCount=7; session.GetCellPosition=function(_,n) return Vector2(n,0) end
        session.RequestMove=function(_,direction,id,entry,context)
            assert(id==1 and direction==1 and entry==7 and context==3 and movement:HasLocalMove(map))
            requests=requests+1
        end
        presenter.TryBeginLocalCommand=function() return true end
        presenter.GetBattleSession=function() return session end
        presenter.ReleasePendingLocalCommand=function() released=released+1 end
        presenter:DispatchLocalCommand('MOVE','',1); movement:OnUpdate(0.2)
        assert(requests==1 and hops==0 and #offsets==0 and warnings==1 and released==0)
        movement:ResolveLocalMove(map,1,7,3,false,true,2,0,'BLOCKED')
        assert(not movement:HasLocalMove(map) and released==1 and clears==0)
    ''',
    "component swap restores old visual once and uses the new setter": r'''
        fixture(); movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile); movement:OnUpdate(0.03)
        local old=presentation; old.ClearLocalGridMoveOffset=nil
        old.SetLocalGridMoveOffset2D=function() error('stale setter called') end
        local nextOffsets=0; local nextClears=0
        presentation={BeginLocalGridMoveHop=function() error('hop must not restart') end,
            SetLocalGridMoveOffset2D=function() nextOffsets=nextOffsets+1 end,
            ClearLocalGridMoveOffset=function() nextClears=nextClears+1 end}
        for n=1,5 do movement:OnUpdate(0.03) end
        assert(clears==1 and nextOffsets==5 and warnings==0)
        movement:CancelLocalMove('DONE'); assert(clears==1 and nextClears==1)
    ''',
    "removed setter restores through captured clear and avoids repeat errors": r'''
        fixture(); local values=presentation; presentation=scriptProxy(values,{})
        movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile); movement:OnUpdate(0.03)
        values.SetLocalGridMoveOffset2D=nil; values.ClearLocalGridMoveOffset=nil
        movement:OnUpdate(0.03); assert(clears==1 and warnings==1)
        for n=1,20 do movement:OnUpdate(0.03) end
        assert(clears==1 and #offsets==1 and movement:HasLocalMove(map))
        movement:CancelLocalMove('DONE'); assert(clears==1 and released==1)
    ''',
    "refresh restores missing helpers and the next normal move": r'''
        fixture(); local values=presentation; local set=values.SetLocalGridMoveOffset2D
        values.SetLocalGridMoveOffset2D=nil; presentation=scriptProxy(values,{})
        local id=movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile); movement:OnUpdate(0.1)
        assert(hops==0 and #offsets==0 and warnings==1)
        values.SetLocalGridMoveOffset2D=set; movement:OnUpdate(0.5)
        assert(#offsets==1 and hops==0 and movement:HasLocalMove(map))
        movement:ResolveLocalMove(map,id,7,3,true,true,3,0,'DONE')
        transform.WorldPosition=Vector3(3,0,0); movement:OnUpdate(0.01)
        assert(not movement:HasLocalMove(map) and clears==0); movement:OnUpdate(0.1)
        assert(clears==1)
        local nextId=movement:BeginLocalMove(player,map,7,3,Vector2(4,0),profile)
        assert(nextId==2 and hops==1 and warnings==1); movement:OnUpdate(0.03)
        -- One extra offset comes from the landing settle frame before the first move cleared.
        assert(#offsets==4); movement:CancelLocalMove('DONE'); assert(clears==2)
    ''',
    "normal frames probe only the current setter": r'''
        fixture(); local reads={}; presentation=scriptProxy(presentation,reads)
        movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile)
        for n=1,10 do movement:OnUpdate(0.01) end
        assert(reads.SetLocalGridMoveOffset2D==11 and reads.ClearLocalGridMoveOffset==1 and reads.BeginLocalGridMoveHop==1)
        movement:CancelLocalMove('DONE'); assert(reads.ClearLocalGridMoveOffset==1 and clears==1)
    ''',
    "throwing helpers cannot abort the request or retry stale functions": r'''
        for mode=1,3 do
            fixture(); local attempts=0
            if mode==1 then presentation.BeginLocalGridMoveHop=function() attempts=attempts+1; error('stale begin') end
            elseif mode==2 then presentation.SetLocalGridMoveOffset2D=function() attempts=attempts+1; error('stale setter') end
            else presentation.ClearLocalGridMoveOffset=function() attempts=attempts+1; error('stale clear') end end
            local id=movement:BeginLocalMove(player,map,7,3,Vector2(3,0),profile)
            assert(id==1 and movement:HasLocalMove(map))
            for n=1,20 do movement:OnUpdate(0.03) end
            movement:CancelLocalMove('DONE')
            assert(attempts==1 and warnings==1 and released==1)
        end
    ''',
    "live refresh cancels an old record without retrying its server request": r'''
        fixture(); oldMoveRecord(); movement:OnUpdate(0.03)
        assert(not movement:HasLocalMove(map) and clears==1 and released==1 and releaseReason=='SCRIPT_REFRESHED')
        for n=1,5 do movement:OnUpdate(0.03) end
        movement:OnEndPlay(); movement:CancelLocalMove('DONE')
        assert(clears==1 and released==1 and hops==0 and requests==0 and #serverHops==0)
    ''',
    "old record cancellation tolerates missing setter or clear metadata": r'''
        for mode=1,3 do
            for strict=1,2 do
                fixture(); local values=presentation
                if mode~=2 then values.SetLocalGridMoveOffset2D=nil end
                if mode~=1 then values.ClearLocalGridMoveOffset=nil end
                if strict==2 then presentation=scriptProxy(values,{}) end
                oldMoveRecord(); movement:OnUpdate(0.03)
                assert(not movement:HasLocalMove(map) and clears==(mode==1 and 1 or 0) and released==1)
                movement:OnUpdate(0.03); assert(requests==0 and hops==0)
            end
        end
    ''',
    "old record clears only the current component rather than its stale reference": r'''
        fixture(); local old=presentation; oldMoveRecord()
        old.ClearLocalGridMoveOffset=function() error('stale component invoked') end
        local currentClears=0; local reads={}
        presentation=scriptProxy({ClearLocalGridMoveOffset=function() currentClears=currentClears+1 end},reads)
        movement:CancelLocalMove('SCRIPT_REFRESHED'); movement:OnUpdate(0.03)
        assert(currentClears==1 and reads.ClearLocalGridMoveOffset==1 and released==1 and requests==0)
    ''',
    "old record map departure world shutdown and rejection end safely": r'''
        for mode=1,3 do
            for missingClear=1,2 do
                fixture(); local values=presentation; values.SetLocalGridMoveOffset2D=nil
                if missingClear==2 then values.ClearLocalGridMoveOffset=nil end
                presentation=scriptProxy(values,{}); oldMoveRecord()
                if mode==1 then player.CurrentMap=other; movement:OnUpdate(0.03)
                elseif mode==2 then movement:OnEndPlay()
                else movement:ResolveLocalMove(map,1,7,3,false,true,2,0,'BLOCKED') end
                assert(not movement:HasLocalMove(map) and released==1 and clears==(missingClear==1 and 1 or 0))
                movement:OnUpdate(0.03); movement:OnEndPlay(); assert(requests==0 and hops==0)
            end
        end
    ''',
}
for name, code in cases.items():
    lua.execute(code)
    print("PASS", name)
print(f"{len(cases)} movement latency regressions passed")
