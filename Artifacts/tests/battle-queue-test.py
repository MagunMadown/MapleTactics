"""Run queue/quickbar bodies with the real BattleTurnComponent state owner."""
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
    "TryQueueTile", "TryExecuteQueuedTile", "ExecuteNextQueuedTile", "CompleteTileQueueExecution",
    "GetQueueSkillHandoffDuration", "TryClearQueuedTile", "TryRemoveQueuedTileAt", "TryReorderQueuedTile",
    "TryMoveQueuedTile", "GetTileIdAt", "QueueContainsSkill", "GetTileIdCount", "TryReorderBattleSkillSlot",
    "ParseSkillSlotPipe", "SerializeSkillSlotPipe", "RequestReorderBattleSkillSlot", "ResetPlayerSkillChain",
})
g._BattleQueueLogic = load(COMBAT / "Skills/BattleQueueLogic.mlua")
g._BattleQuickbarLogic = load(COMBAT / "Skills/BattleQuickbarLogic.mlua")
g.Turn = load(COMBAT / "Components/Shared/BattleTurnComponent.mlua")
lua.execute(r'''
function isvalid(v) return v~=nil and v.Valid~=false end
function log(_) end
log_warning=log; log_error=log
_TutorialRulesLogic={IsGuided=function(_,s) return s.Guided end,CanEditSkillQueue=function(_,s) return not s.EditBlocked end}
_RunManagerLogic={CanUseRunSkill=function(_,p,id) return {Success=id~='unowned',Reason='NOT_OWNED'} end}
_ContentValidatorLogic={ValidateSkillById=function(_,id) return {Success=id~='invalid',Reason='INVALID'} end}
_BattleOutcomeLogic={CompletePendingClear=function(_,s,consumed) s.ClearConsumed=consumed; return false end}
function fixture()
    local t=setmetatable({BattlePhase='PlayerTurn',TurnNumber=1,IsActionProcessing=false,QueuedActionType='',QueuedActionDirection=0,
        QueuedTileIds='',QueuedTileCount=0,ExecutingTileIds='',ExecutingTileIndex=0,TileQueueCapacity=3,StateRevision=0,QueueOrderRevision=0},{__index=Turn})
    local s=setmetatable({_T={},TurnState=t,BattleResult='',ContentValidationState='VALID',EntryRequestId='entry',ActionTimerId=0,
        ImpactTimerId=0,TileQueueCapacity=3,SkillSlotCount=6,SkillSlotIds='a|b||||',SkillSlotNames='A|B||||',SkillSlotCooldownTurns='2|0||||',
        SkillSlotRevision=1,SkillSlotSourceRunOrderRevision=1,LastProcessedSkillSlotReorderRequestId=0,EnemyRounds=0,Timers={},Casts={},Cell=0},
        {__index=function(o,k) return Session[k] or t[k] end})
    s.Unit={ComboChainCount=0,ComboAttackBonus=0,PreviousSkillWasAttack=false}
    s.Inventory={RunSkillSnapshot='a~1|b~1',Revision=1}
    function s.Inventory:CommitRunSkillBarOrder(before,after,reason)
        if self.Fail then return {Success=false,Reason='SAVE_FAILED'} end
        self.Before=before; self.After=after; self.Revision=self.Revision+1
        return {Success=true,Revision=self.Revision}
    end
    s.PlayerEntity={GetComponent=function(_,kind) if kind=='script.PlayerRunInventoryComponent' then return s.Inventory end
        if kind=='script.BattleUnitComponent' then return s.Unit end end}
    function s:FindUnitEntity(_) return self.PlayerEntity end
    function s:IsTutorialCommandAllowed() return not self.GuideBlocked end
    function s:IsPlayerSealed() return self.Sealed end
    function s:GetEffectiveSkillValidation(_,id) return {Success=id~='invalid',Reason='INVALID',Data={Definition={CooldownTurns=id=='a' and 2 or 0,FreePlay=id=='free',ActionDuration=.2,MotionProfileId='cast'}}} end
    s.Runtime={CanUseSkill=function(_,id) return {Success=id~='cooling',Reason='COOLDOWN',RemainingTurns=2} end}
    function s:GetSkillRuntimeState() return self.Runtime end
    function s:PublishTurnStateSnapshot(reason) self.Published=reason end
    function s:BeginEnemyTurnFromPlayerAction(reason) self.EnemyRounds=self.EnemyRounds+1; t:BeginEnemyTurn('WAIT',0,reason) end
    function s:GetTileActionType(id) return id=='unknown' and '' or 'EXECUTE_SKILL' end
    function s:TryExecuteSkill(_,id)
        table.insert(self.Casts,{Id=id,Cell=self.Cell,Repeat=self._T.ReplayingRelicSkill})
        if id=='fail' then return {Success=false,Reason='NO_TARGET'} end
        self._T.QueueExecutionConsumedAction=true; self.Cell=self.Cell+1
        return {Success=true,Reason='OK'}
    end
    function s:GetSkillSpeedMultiplier() return 2 end
    function s:GetSkillMotionProfile() return {Duration=.3} end
    function s:GetSkillActionDuration() return .6 end
    function s:CompletePlayerCombatPresentationHandoff(reason) self.Handoff=reason end
    function s:BeginMotionCompletionWait(done) self.Done=done; return #self.Casts end
    function s:SealMotionCompletionWhenImpactsFinish(sequence) self.SealedSequence=sequence end
    function s:MarkMotionCompletionReady(sequence) self.Done() end
    _TimerService={SetTimerOnce=function(_,f,d) table.insert(s.Timers,{Callback=f,Duration=d}); return #s.Timers end}
    function s:tick() assert(#self.Timers>0); table.remove(self.Timers,1).Callback() end
    function s:IsValidPlayerRequest(sender) return sender=='owner' end
    function s:PublishSkillSlotReorderReceipt(_,_,r) self.Receipt=r; self.Receipts=(self.Receipts or 0)+1 end
    return s,t
end
local checks=0
function check(label,f) f(); checks=checks+1; print('PASS '..label) end
check('free load keeps the decision phase; normal load preserves queue across enemy round',function()
    local s,t=fixture(); assert(s:TryQueueTile('free').Success and s.EnemyRounds==0)
    assert(s:TryQueueTile('b').Success and s.EnemyRounds==1 and t.QueuedTileIds=='free|b')
    t:CompleteEnemyTurn('done'); assert(t.QueuedTileIds=='free|b' and t.TurnNumber==2)
end)
check('reservation, ownership, cooldown, seal and guide rejection do not append',function()
    local s,t=fixture(); s:TryQueueTile('a'); t:CompleteEnemyTurn('done')
    assert(s:TryQueueTile('a').Reason=='COOLDOWN_RESERVED')
    assert(s:TryQueueTile('unowned').Reason=='NOT_OWNED' and s:TryQueueTile('cooling').Reason=='COOLDOWN')
    s.Sealed=true; assert(s:TryQueueTile('b').Reason=='PLAYER_SEALED'); s.Sealed=false
    s.GuideBlocked=true; assert(s:TryQueueTile('b').Reason=='TUTORIAL_FOLLOW_GUIDE' and t.QueuedTileIds=='a')
end)
check('capacity and active phase guards preserve full queue',function()
    local s,t=fixture(); for i=1,3 do assert(s:TryQueueTile('free').Success) end
    assert(s:TryQueueTile('free').Reason=='QUEUE_FULL'); t.IsActionProcessing=true
    assert(s:TryRemoveQueuedTileAt(1).Reason=='ACTION_PROCESSING' and t.QueuedTileCount==3)
end)
check('queue reorder requires integer current revision and preserves turn',function()
    local s,t=fixture(); t:TryAppendSkill('a'); t:TryAppendSkill('b'); local r=t.QueueOrderRevision
    assert(s:TryReorderQueuedTile(1.5,2,r).Reason=='INVALID_QUEUE_INDEX_TYPE')
    assert(s:TryReorderQueuedTile(1,2,r-1).Reason=='STALE_QUEUE_REVISION')
    assert(s:TryReorderQueuedTile(1,2,r).Success and t.QueuedTileIds=='b|a' and t.TurnNumber==1 and s.EnemyRounds==0)
    assert(s:TryRemoveQueuedTileAt(1).RemovedSkillId=='b' and t.QueuedTileIds=='a')
    assert(s:TryClearQueuedTile().Success and t.QueuedTileCount==0)
end)
check('guide permits individual cancel but blocks whole queue clear and reorder',function()
    local s,t=fixture(); t:TryAppendSkill('a'); t:TryAppendSkill('b'); s.Guided=true
    assert(s:TryClearQueuedTile().Reason=='TUTORIAL_FOLLOW_GUIDE')
    assert(s:TryReorderQueuedTile(1,2,t.QueueOrderRevision).Reason=='TUTORIAL_FOLLOW_GUIDE')
    assert(s:TryRemoveQueuedTileAt(1).Success and t.QueuedTileIds=='b')
end)
check('sequential execution freezes ids and reads current cell for every cast',function()
    local s,t=fixture(); t:TryAppendSkill('a'); t:TryAppendSkill('b')
    assert(s:TryExecuteQueuedTile().Success and t.ExecutingTileIds=='a|b' and t.QueuedTileIds=='')
    assert(#s.Casts==1 and s.Casts[1].Cell==0 and s.Timers[1].Duration==.3)
    assert(not s:TryReorderQueuedTile(1,2,t.QueueOrderRevision).Success)
    s:tick(); assert(#s.Casts==2 and s.Casts[2].Cell==1); s:tick()
    assert(t.ExecutingTileIds=='' and t.ExecutingTileIndex==0 and s.EnemyRounds==1)
end)
check('impact still pending delays handoff without replaying the cast',function()
    local s,t=fixture(); t:TryAppendSkill('b'); s:TryExecuteQueuedTile(); s.ImpactTimerId=7
    s:tick(); assert(#s.Casts==1 and s.EnemyRounds==0 and s.Timers[1].Duration==.02)
    s.ImpactTimerId=0; s:tick(); assert(s.EnemyRounds==1)
end)
check('old entry and old queue callback cannot advance a new action',function()
    local s,t=fixture(); t:TryAppendSkill('b'); s:TryExecuteQueuedTile(); local done=s.Done
    s.EntryRequestId='new'; s:tick(); done(); assert(#s.Casts==1 and s.EnemyRounds==0 and t.ExecutingTileIndex==1)
    s.EntryRequestId='entry'; t.ExecutingTileIds='other'; done(); assert(t.ExecutingTileIndex==1)
end)
check('first rejected cast is free; partial execution failure consumes once',function()
    local s,t=fixture(); t:TryAppendSkill('fail'); s:TryExecuteQueuedTile(); assert(s.EnemyRounds==0 and not t.IsActionProcessing)
    s,t=fixture(); t:TryAppendSkill('b'); t:TryAppendSkill('fail'); s:TryExecuteQueuedTile(); s:tick()
    assert(s.EnemyRounds==1 and not s._T.QueueExecutionConsumedAction and t.ExecutingTileIds=='')
end)
check('motion completion duplication cannot consume a second enemy round',function()
    local s,t=fixture(); t:TryAppendSkill('b'); s:TryExecuteQueuedTile(); local done=s.Done
    s:tick(); done(); assert(s.EnemyRounds==1 and #s.Casts==1)
end)
check('slot move and swap keep parallel data and queued skill identities',function()
    local s,t=fixture(); t:TryAppendSkill('a'); t:TryAppendSkill('b'); t.ExecutingTileIds='a|b'
    assert(s:TryReorderBattleSkillSlot(1,3,1).Operation=='MOVE' and s.SkillSlotIds=='|b|a|||')
    assert(s.SkillSlotNames=='|B|A|||' and s.SkillSlotCooldownTurns=='|0|2|||')
    assert(s:TryReorderBattleSkillSlot(2,3,2).Operation=='SWAP' and s.SkillSlotIds=='|a|b|||')
    assert(t.QueuedTileIds=='a|b' and t.ExecutingTileIds=='a|b' and t.TurnNumber==1)
end)
check('slot commit failure, stale revision and duplicates leave presentation unchanged',function()
    local s,t=fixture(); s.Inventory.Fail=true
    assert(s:TryReorderBattleSkillSlot(1,3,1).Reason=='SAVE_FAILED' and s.SkillSlotIds=='a|b||||' and s.SkillSlotRevision==1)
    assert(s:TryReorderBattleSkillSlot(1,3,0).Reason=='STALE_SLOT_REVISION')
    s.Inventory.Fail=false; s.SkillSlotIds='a|a||||'
    assert(s:TryReorderBattleSkillSlot(1,3,1).Reason=='DUPLICATE_SKILL_SLOT')
end)
check('slot RPC retains sender and monotonic request validation',function()
    local s=fixture(); senderUserId='intruder'; s:RequestReorderBattleSkillSlot(1,3,1,1); assert(s.Receipts==nil)
    senderUserId='owner'; s:RequestReorderBattleSkillSlot(1,3,1,1); assert(s.Receipts==1 and s.Receipt.Success)
    s:RequestReorderBattleSkillSlot(3,4,1,2); s:RequestReorderBattleSkillSlot(3,4,0,2)
    assert(s.Receipts==1 and s.SkillSlotIds=='|b|a|||')
end)
check('queue execution and slot order remain independent between sessions',function()
    local a,ta=fixture(); ta:TryAppendSkill('a'); a:TryExecuteQueuedTile(); local b,tb=fixture()
    b:TryReorderBattleSkillSlot(1,6,1); assert(a.SkillSlotIds=='a|b||||' and #b.Casts==0 and tb.ExecutingTileIds=='')
    a:tick(); assert(b.EnemyRounds==0)
end)
print(checks..' queue/quickbar regressions passed')
''')
