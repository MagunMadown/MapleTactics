"""Run actual settlement bodies; ORIGINAL_SESSION replays the pre-extraction entrypoints."""
from pathlib import Path
import os
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime
from battle_refactor_fixture import wire_logic_owners

ROOT = Path(__file__).resolve().parents[2]
COMBAT = ROOT / "RootDesk/MyDesk/01_Combat"
lua = LuaRuntime(unpack_returned_tuples=True)
wire_logic_owners(lua)


def load(path, names=None):
    result = lua.table()
    source = path.read_text(encoding="utf-8-sig").expandtabs(4)
    for name, parameters, body in re.findall(r"^    method \w+ (\w+)\(([^\n]*)\)\n(.*?)^    end$", source, re.M | re.S):
        if names is None or name in names:
            args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
            result[name] = lua.eval("function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend")
    if names is not None:
        assert set(result.keys()) == names
    return result


g = lua.globals()
g.Session = load(Path(os.environ.get("ORIGINAL_SESSION", COMBAT / "Components/Shared/BattleSessionComponent.mlua")), {
    "HandleUnitDied", "HandleUnitDiedFromSource", "FinishEmptyBattlefield", "CleanupRegisteredEnemies",
    "CleanupDefeatedEnemies", "AdvanceWaveAfterMotion", "CaptureBattleResultContext", "IsBattleResultContextCurrent",
    "CompleteQueuedAction", "CompleteTileQueueExecution",
})
g._BattleOutcomeLogic = load(COMBAT / "Resolvers/BattleOutcomeLogic.mlua")
g._BattleQueueLogic = load(COMBAT / "Skills/BattleQueueLogic.mlua")
g.Unit = load(COMBAT / "Components/Shared/BattleUnitComponent.mlua", {"MarkDead"})
g.Turn = load(COMBAT / "Components/Shared/BattleTurnComponent.mlua", {
    "ClearActionState", "ClearTransientState", "SetPhase", "CompleteSkillQueue", "CompleteImmediateAction",
    "IncrementStateRevision", "IncrementQueueOrderRevision", "GetTileIdCount",
})
lua.execute(r'''
function isvalid(v) return v~=nil and v.Valid~=false end
function log(_) end
log_warning=log; log_error=log
_UtilLogic={ElapsedSeconds=100}
local timers={}
_TimerService={SetTimerOnce=function(_,f) table.insert(timers,f); return #timers end,
    ClearTimer=function(_,id) timers[id]=nil end}
_EntityService={Destroy=function(_,e) e.Valid=false end}
_TutorialRulesLogic={ShouldRecordProgress=function(_,s) return not s.TutorialActive end,
    OnWaveStarted=function(_,s,w) s.TutorialWave=w end}
_EnemyImpactPresentationLogic={GetDeathSound=function() return '' end}
_MonsterCollectionLogic={RecordDefeat=function(_,p) p.Defeats=(p.Defeats or 0)+1 end}
_EnemyDropTriggerResolverLogic={Resolve=function() return {TriggerSnapshot='ONE'} end}
_RunManagerLogic={RecordBattleResult=function(_,p) p.Records=(p.Records or 0)+1; if p.OnRecord then p:OnRecord() end; return true end}
setmetatable(_BattleOutcomeLogic,{__newindex=function(_,k) error('shared battle state '..k) end})

function fixture()
    timers={}
    local s=setmetatable({_T={},Units={},Trace={},EntryRequestId=1,StageId='stage',StageNumber=1,
        CurrentWave=1,TotalWaves=1,BattleResult='',ResultKillCount=0,ResultReady=false,
        ResultStartTime=90,TurnNumber=4,ActionTimerId=0,CurrentPlayerActionKillCount=0,
        RunSeed=10,UnionItemDropRate=0,CurrentClearSpawnDelay=.2,EnemyDeathPresentationDelay=.3}, {__index=Session})
    s.Entity={}
    function s:trace(v) table.insert(self.Trace,v) end
    function s:add(id,team,boss)
        local u=setmetatable({UnitId=id,Team=team,CurrentHp=0,IsDead=false,IsBoss=boss==true,
            EnemyDefinitionId='monster',SpawnOrder=1,CellIndex=2,ComboChainCount=0}, {__index=Unit})
        function u:SyncRunHp() self.Syncs=(self.Syncs or 0)+1 end
        function u:ClearAttackBuffs() self.BuffsCleared=true end
        local e={CurrentMap=s.Entity,Components={['script.BattleUnitComponent']=u}}
        function e:GetComponent(n) return self.Components[n] end
        u.Entity=e; self.Units[id]=e; return e,u
    end
    s.PlayerEntity,s.PlayerUnit=s:add('player','Player')
    function s:FindUnitEntity(id) return self.Units[id] end
    s.BoardState={}
    function s.BoardState:CollectRegisteredUnits() local a={} for _,e in pairs(s.Units) do table.insert(a,e) end return a end
    function s.BoardState:CollectLivingEnemies()
        local a={} for _,e in pairs(s.Units) do local u=e:GetComponent('script.BattleUnitComponent')
            if isvalid(e) and u and u.Team=='Enemy' and not u.IsDead then table.insert(a,e) end end return a
    end
    function s.BoardState:UnregisterUnit(id) s.Units[id]=nil end
    s.TurnState=setmetatable({BattlePhase='PlayerTurn',TurnNumber=4,StateRevision=0,QueueOrderRevision=0,
        QueuedTileIds='brandish',ExecutingTileIds='brandish',QueuedTileCount=1,ExecutingTileIndex=0,IsActionProcessing=false,QueuedActionType=''}, {__index=Turn})
    s.WaveRuntime={PendingSpawnCount=0,SetWaveState=function(self,v) self.State=v end,
        CancelPendingSpawns=function(self) self.PendingSpawnCount=0 end,
        ScheduleWaveTransition=function(self,from,to) self.From=from; self.To=to; self.Transitions=(self.Transitions or 0)+1 end,
        MarkWaveActive=function(self) self.State='Active' end}
    s.DropRuntime={LastEnemyKillKey='',Calls=0,Collections=0,
        ResolveEnemyDeath=function(self) self.Calls=self.Calls+1; if self.OnResolve then self:OnResolve() end; return {Success=true} end,
        AutoCollectLastEnemy=function(self) self.Collections=self.Collections+1; return {Success=true} end,
        DiscardPending=function(self) self.Discarded=true end}
    function s:GetSkillSoundVolume() return 1 end
    function s:GetPreparedEnemyIntent() return {} end
    function s:SendMotionPresentation(e) e.Motions=(e.Motions or 0)+1 end
    function s:RemovePoisonMistsForSource(id) self.RemovedMist=id end
    function s:ClearPoisonMists() self.MistsCleared=true end
    function s:PublishEnemyPlanSnapshot() self.Snapshots=(self.Snapshots or 0)+1 end
    function s:ClearForcedSpawnSchedule() self:trace('clear-spawns') end
    function s:ClearTurnTransitionTimer() self:trace('clear-transition') end
    function s:ClearMotionCompletionWaits() self:trace('clear-waits') end
    function s:ResetPlayerSkillChain() self:trace('reset-chain') end
    function s:BeginEnemyTurnFromPlayerAction() self.EnemyTurns=(self.EnemyTurns or 0)+1 end
    function s:CompletePlayerCombatPresentationHandoff() self:trace('handoff') end
    function s:ClearEnemyToEnemyPresentationHandoff() self:trace('clear-enemy-handoff') end
    function s:ClearSkillImpactTimers() self:trace('clear-impacts') end
    function s:PublishTurnStateSnapshot() self.BattlePhase=self.TurnState.BattlePhase end
    function s:PublishWaveStateSnapshot() end
    function s:ClearPreparedEnemyIntent() self:trace('clear-intent') end
    function s:BeginMotionCompletionWait(f) self.Motion=f; return 1 end
    function s:SealMotionCompletionWhenImpactsFinish() end
    function s:MarkMotionCompletionReady() self.Motion() end
    function s:RecordRoundReward() self.Rewards=(self.Rewards or 0)+1 end
    function s:RefreshUnionRewardPresentation() self:trace('rewards') end
    function s:AdvanceConsumedPlayerActionEffects(reason) self.Consumed=(self.Consumed or 0)+1; self.ConsumedReason=reason end
    return s
end
local checks=0
function check(label,f) f(); checks=checks+1; print('PASS '..label) end

check('death validation and duplicate death settle once',function()
    local s=fixture(); local e,u=s:add('enemy','Enemy')
    s:HandleUnitDied('missing','TEST'); assert(s.ResultKillCount==0)
    s:HandleUnitDiedFromSource('enemy','DAMAGE','player')
    assert(u.IsDead and u.Syncs==1 and e.Motions==1 and s.ResultKillCount==1)
    assert(s.DropRuntime.Calls==1 and s.DropRuntime.Collections==1 and s.PlayerEntity.Records==1 and s.BattleResult=='Victory')
    s:HandleUnitDiedFromSource('enemy','DAMAGE','player'); s:FinishEmptyBattlefield('enemy','TEST','Enemy')
    assert(s.ResultKillCount==1 and s.DropRuntime.Calls==1 and s.PlayerEntity.Records==1)
    timers[#timers](); assert(s.ResultReady)
end)
check('a surviving enemy keeps the encounter active',function()
    local s=fixture(); s:add('first','Enemy'); s:add('second','Enemy')
    s:HandleUnitDied('first','TEST'); assert(s.BattleResult=='' and s.ResultKillCount==1 and s.DropRuntime.Collections==0)
    s:FinishEmptyBattlefield('first','TEST','Enemy'); assert(s.BattleResult=='')
end)
check('drop load may yield across reentry without ending the new encounter',function()
    local s=fixture(); s:add('enemy','Enemy')
    s.DropRuntime.OnResolve=function() s.EntryRequestId=2; s:add('new','Enemy') end
    s:HandleUnitDied('enemy','TEST')
    assert(s.EntryRequestId==2 and s.BattleResult=='' and not s.ResultReady and s.DropRuntime.Collections==0)
end)
check('nested drop callbacks retain pending count and last kill identity',function()
    local s=fixture(); s:add('first','Enemy'); s:add('second','Enemy')
    s.DropRuntime.OnResolve=function(self) if self.Calls==1 then s:HandleUnitDied('second','TEST') end end
    s:HandleUnitDied('first','TEST')
    assert(s.BattleResult=='Victory' and s.ResultKillCount==2 and s.DropRuntime.Calls==2 and s.DropRuntime.Collections==1)
    assert(s._T.EnemyDeathSettlement.PendingCount==0 and s.DropRuntime.LastEnemyKillKey=='stage:1:1:second')
end)
check('boss removes surviving adds without their drops or kills',function()
    local s=fixture(); s:add('boss','Enemy',true); local add=s:add('add','Enemy')
    s.CurrentWave=1; s.TotalWaves=3; s.WaveRuntime.PendingSpawnCount=2
    s:HandleUnitDied('boss','TEST')
    assert(s._T.BossDefeated and not isvalid(add) and s.Units.add==nil)
    assert(s.BattleResult=='Victory' and s.ResultKillCount==1 and s.DropRuntime.Calls==1)
end)
check('queue and utility kills defer until their accepted action completes',function()
    for _,kind in ipairs({'SKILL_QUEUE','UTILITY'}) do
        local s=fixture(); s:add('enemy','Enemy'); s.TurnState.IsActionProcessing=true
        s.TurnState.QueuedActionType=kind; s.TurnState.ExecutingTileIndex=kind=='SKILL_QUEUE' and 1 or 0
        s:HandleUnitDied('enemy','TEST'); assert(s.BattleResult=='' and s._T.PendingClear.Entry==1)
        if kind=='SKILL_QUEUE' then s:CompleteTileQueueExecution(true,'DONE') else s:CompleteQueuedAction('UTILITY',true,'DONE') end
        assert(s.BattleResult=='Victory' and s.Consumed==1 and s._T.PendingClear==nil and s.EnemyTurns==nil)
        if kind=='SKILL_QUEUE' then s:CompleteTileQueueExecution(true,'DUPLICATE') else s:CompleteQueuedAction('UTILITY',true,'DUPLICATE') end
        assert(s.Consumed==1 and s.PlayerEntity.Records==1 and s.EnemyTurns==nil)
        assert(not _BattleOutcomeLogic:CompletePendingClear(s,true,kind) and s.Consumed==1)
    end
end)
check('stale pending clear and rejected action cannot consume new state',function()
    local s=fixture(); s._T.PendingClear={Entry=0,UnitId='old',Cause='TEST'}
    assert(not _BattleOutcomeLogic:CompletePendingClear(s,true,'DONE') and s.Consumed==nil)
    s._T.PendingClear={Entry=1,UnitId='enemy',Cause='TEST'}
    assert(_BattleOutcomeLogic:CompletePendingClear(s,false,'DONE') and s.Consumed==nil and s.BattleResult=='Victory')
end)
check('wave transition preserves editable queue and schedules one continuation',function()
    local s=fixture(); s:add('enemy','Enemy'); s.TotalWaves=3
    s:HandleUnitDied('enemy','TEST'); s:HandleUnitDied('enemy','TEST')
    assert(s.BattleResult=='' and s.TurnState.BattlePhase=='WaveTransition' and s.TurnState.QueuedTileIds=='brandish')
    assert(s.WaveRuntime.To==2 and s.WaveRuntime.Transitions==1 and s._T.waveMotionCompletion.Entry==1)
end)
check('player settlement requires actual player death and discards pending drops',function()
    local s=fixture(); s:FinishEmptyBattlefield('player','TEST','Player'); assert(s.BattleResult=='')
    s:FinishEmptyBattlefield('other','TEST','Player'); s:FinishEmptyBattlefield('enemy','TEST','Other'); assert(s.BattleResult=='')
    s:HandleUnitDied('player','TEST')
    assert(s.BattleResult=='Defeat' and s.DropRuntime.Discarded and s.ResultKillCount==0 and s.MistsCleared)
end)
check('yielding result save and old readiness callbacks cannot mutate a new entry',function()
    local s=fixture(); s:add('enemy','Enemy')
    s.PlayerEntity.OnRecord=function() s.EntryRequestId=2; s.BattleResult='' end
    s:HandleUnitDied('enemy','TEST'); assert(not s.ResultReady and s.Motion==nil)
    s=fixture(); s:add('enemy','Enemy'); s:HandleUnitDied('enemy','TEST')
    s.EntryRequestId=2; s.BattleResult=''; timers[#timers](); assert(not s.ResultReady)
end)
check('tutorial outcome bypasses progress and reward storage',function()
    local s=fixture(); s.TutorialActive=true; s:add('enemy','Enemy'); s:HandleUnitDied('enemy','TEST')
    assert(s.BattleResult=='Victory' and s.ResultRecorded and s.ResultKillCount==1)
    assert(s.PlayerEntity.Records==nil and s.PlayerEntity.Defeats==nil and s.DropRuntime.Calls==0)
end)
check('cleanup keeps player and living reinforcement; two sessions stay isolated',function()
    local a=fixture(); local b=fixture(); local dead,u=a:add('dead','Enemy'); u.IsDead=true
    local live=a:add('live','Enemy'); b:add('other','Enemy')
    a:CleanupDefeatedEnemies('TEST'); assert(not isvalid(dead) and isvalid(live) and a.Units.player)
    a:CleanupRegisteredEnemies('TEST'); assert(not isvalid(live) and a.Units.player and #b.BoardState:CollectLivingEnemies()==1)
end)
print(checks..' outcome regressions passed')
''')
