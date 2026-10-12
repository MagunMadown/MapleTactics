"""Execute real entry, result and consumable adapters with deterministic service boundaries."""
from pathlib import Path
import os, re, sys
if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime
from battle_refactor_fixture import wire_logic_owners
ROOT = Path(__file__).resolve().parents[2]
lua = LuaRuntime(unpack_returned_tuples=True)
wire_logic_owners(lua)
source = Path(os.environ.get("ORIGINAL_SESSION", ROOT / "RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua")).read_text(encoding="utf-8-sig").expandtabs(4)
names = {"InitializeFromEntry", "RequestContinueResult", "CaptureBattleResultContext", "IsBattleResultContextCurrent", "TryUseRunConsumable", "TryDiscardRunConsumable", "BuildConsumableHudState", "RecordRoundReward"}
methods = lua.table()
for name, parameters, body in re.findall(r"^    method \w+ (\w+)\(([^\n]*)\)\n(.*?)^    end$", source, re.M | re.S):
    if name in names:
        args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
        methods[name] = lua.eval("function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend")
assert set(methods.keys()) == names
lua.globals().M = methods
lua.execute(r'''
function isvalid(v) return v~=nil and v.Valid~=false end
function log(_) end
log_warning=log; log_error=log
senderUserId='owner'
_UtilLogic={ElapsedSeconds=10}
local checks=0
function check(label,f) f(); checks=checks+1; print('PASS '..label) end
function fixture()
 local s=setmetatable({_T={},Entity={Id='map',Name='battle'},EntryRequestId=7,HudContextRevision=3,StageId='stage',StageNumber=1,
  BattleResult='Victory',ResultReady=true,ResultRecorded=false,ResultDefeatReset={},ResultTransitionTimerId=0,
  ContentValidationState='VALID',LastInitializedEntryRequestId=0,RunSeed=9,TurnState={BattlePhase='PlayerTurn',IsActionProcessing=false},
  Calls={},Events={},ResultGold=0,ResultRewardSnapshot=''}, {__index=M})
 local run={RunLifetimeRevision=1,RunSequence=5,RunSeed=9,RunDifficulty='NORMAL',RunState='Active'}
 local inv={InventoryRevision=4,ActiveRunSequence=5,RunConsumableSnapshot='potion~1|cleanse~1',ConsumableCapacity=3,
  GetDistinctOwnedSkillIds=function() return {'attack'} end,NormalizeLegacyConsumables=function() end}
 local unit={UnitId='player_01',IsDead=false,CurrentHp=5,MaxHp=10,SealTurns=0,FrostbiteTurns=0,ConfuseTurns=0,BurnDamage=0}
 local runtime={CooldownRevision=2,GetRemainingCooldown=function() return 0 end}
 local parts={['script.PlayerRunStateComponent']=run,['script.PlayerRunInventoryComponent']=inv,['script.BattleUnitComponent']=unit,['script.SkillRuntimeStateComponent']=runtime}
 local player={CurrentMap=s.Entity,PlayerComponent={UserId='owner'},GetComponent=function(_,name) return parts[name] end}
 s.PlayerEntity=player
 local entry={RequestId=7}
 parts['script.BattleEntryStateComponent']=entry
 function s:IsValidPlayerRequest(id) return id=='owner' and player.CurrentMap==self.Entity end
 function s:IsTutorialCommandAllowed() return not self.Guided end
 function s:FindUnitEntity(id) return id=='player_01' and player or nil end
 function s:ApplyRunJobConfiguration() self.SelectedJobId='warrior'; table.insert(self.Events,'job') end
 function s:LoadAndApplyStageDefinition(id) table.insert(self.Events,'stage'); self.StageId=id; return {Success=true} end
 function s:RegisterPlayer(p) assert(p==player); table.insert(self.Events,'register') end
 function s:RebuildBattleState(reason) self.Rebuilt=(self.Rebuilt or 0)+1; return {Success=not self.FailRebuild,Reason=reason} end
 function s:RefreshUnionRewardPresentation() self.Refreshed=true end
 function s:ReturnToLobbyAfterDefeat() self.Returned=(self.Returned or 0)+1; return {Success=not self.FailReturn} end
 function s:PublishPlayerCommandResult(command,result) self.Command=command; self.CommandResult=result end
 local function count(k) s.Calls[k]=(s.Calls[k] or 0)+1 end
 _ContentValidatorLogic={ValidateStageById=function() count('validate'); return {Success=not s.InvalidStage,Reason='BAD_STAGE'} end}
 _AscensionDifficultyLogic={ResolveLevel=function(_,d) return d=='NORMAL' and 0 or -1 end,ToDifficulty=function() return 'NORMAL' end}
 _AscensionProgressionLogic={ValidateSelection=function() count('difficulty'); return {Success=not s.Locked,Reason='LOCKED'} end}
 _TutorialRulesLogic={InitializeSession=function() count('tutorial-init') end,ApplyStartingHp=function() count('tutorial-hp') end,
  OnConsumableUsed=function(_,_,r) s.TutorialUsed=r end,IsGuided=function() return s.Guided==true end}
 _NewPlayerTutorialLogic={TryFinishSession=function() count('tutorial-result'); return s.TutorialResult end}
 _RunManagerLogic={StartNewRun=function() count('new'); return s.NoRun and nil or run end,
  EnsureRunState=function() count('ensure'); return s.NoRun and nil or run end,
  ApplyJobSelection=function() count('select'); return {Success=not s.BadJob,Reason='BAD_JOB'} end,
  GetOrCreateRunState=function() return run end,
  RecordBattleResult=function() count('record'); if s.DuringRecord then s:DuringRecord() end; return not s.FailRecord end,
  CanUseRunConsumable=function(_,_,id,key) s.UseKey=key; count('availability'); return {Success=not s.NoConsumable,Reason='EMPTY',AlreadyApplied=s.AlreadyApplied} end,
  ConsumeRunConsumable=function(_,_,id,key) count('consume'); assert(key==s.UseKey); inv.InventoryRevision=inv.InventoryRevision+1; return {Success=not s.FailCommit,Reason='COMMIT_FAILED',ConsumedAmount=1} end}
 _StageTransitionManagerLogic={HandleVictoryTransition=function() count('transition'); if s.DuringTransition then s:DuringTransition() end end,
  HandleCompletedRunTransition=function() count('completed') end}
 _TimerService={SetTimerOnce=function(_,f,d) s.Timer=f; s.Delay=d; return 1 end,ClearTimer=function() end}
 _ConsumableDefinitionRepositoryLogic={GetDefinition=function(_,id) return {Success=not s.InvalidConsumable,Reason='BAD_CONSUMABLE',TargetType='SELF',EffectType=id=='cleanse' and 'CLEANSE' or 'HEAL',RowIndex=id=='cleanse' and 2 or 1,DisplayName=id,EffectValue=3} end}
 _ConsumableEffectRouterLogic={Execute=function(_,_,u,target) count('effect'); return {Success=not s.FailEffect,Reason='EFFECT_FAILED',AppliedAmount=3,HpBefore=u.CurrentHp,HpAfter=u.CurrentHp+3} end}
 function inv:Consume(id,n,key) count('discard'); self.InventoryRevision=self.InventoryRevision+1; return {Success=true,ConsumedAmount=n} end
 return s,player,run,inv,unit,entry
end
function init(s,p,mode,id,difficulty) return s:InitializeFromEntry(p,'stage','character','warrior','loadout',9,mode or 'NEW_RUN',id or 8,difficulty or 'NORMAL') end
check('entry rejects invalid player, stage, duplicate and mode before run mutation',function()
 local s,p=fixture(); assert(init(s,nil).Reason=='INVALID_PLAYER'); s.InvalidStage=true; assert(init(s,p).Reason=='BAD_STAGE')
 s.InvalidStage=false; s.LastInitializedEntryRequestId=8; assert(init(s,p).Reason=='DUPLICATE_ENTRY_INITIALIZATION')
 s.LastInitializedEntryRequestId=0; assert(init(s,p,'BAD').Reason=='INVALID_ENTRY_MODE' and s.Calls.new==nil)
end)
check('new run validates difficulty and job before publishing entry',function()
 local s,p=fixture(); assert(init(s,p,nil,nil,'BAD').Reason=='INVALID_DIFFICULTY')
 s.Locked=true; assert(init(s,p).Reason=='LOCKED' and s.Calls.new==nil)
 s.Locked=false; s.BadJob=true; assert(init(s,p).Reason=='BAD_JOB' and s.EntryRequestId==7 and s.Rebuilt==nil)
end)
check('entry preserves apply order and commits initialized ID only after successful rebuild',function()
 local s,p=fixture(); s.FailRebuild=true; assert(not init(s,p).Success and s.LastInitializedEntryRequestId==0)
 assert(table.concat(s.Events,'|')=='job|stage|register')
 s.FailRebuild=false; assert(init(s,p).Success and s.LastInitializedEntryRequestId==8 and s.EntryRequestId==8)
 assert(init(s,p).Reason=='DUPLICATE_ENTRY_INITIALIZATION' and s.Rebuilt==2)
end)
check('continue entry uses existing run difficulty without selecting a new unlocked level',function()
 local s,p,run=fixture(); assert(init(s,p,'CONTINUE_RUN',9,'BAD').Success and s.Calls.ensure==1 and s.Calls.new==nil and s.Calls.difficulty==nil)
 run.RunDifficulty='BAD'; assert(init(s,p,'CONTINUE_RUN',10).Reason=='INVALID_DIFFICULTY')
end)
check('result RPC rejects another owner, active battle and duplicate continuation',function()
 local s=fixture(); senderUserId='stranger'; s:RequestContinueResult(); assert(s.ResultReady and s.Calls.record==nil)
 senderUserId='owner'; s.BattleResult=''; s:RequestContinueResult(); assert(s.ResultReady)
 s.BattleResult='Victory'; s:RequestContinueResult(); s:RequestContinueResult(); assert(s.Calls.record==1 and s.Calls.transition==1 and not s.ResultReady and s.Delay==8)
end)
check('tutorial result skips normal rewards and transition',function()
 local s=fixture(); s.TutorialResult={Success=true}; s:RequestContinueResult(); assert(s.Calls.record==nil and s.Calls.transition==nil)
end)
check('stale record completion cannot transition or overwrite a new entry',function()
 local s=fixture(); s.DuringRecord=function(self) self.EntryRequestId=8 end; s:RequestContinueResult()
 assert(not s.ResultRecorded and s.Calls.transition==nil and s.Timer==nil)
end)
check('record failure and defeat-transfer failure restore retry eligibility',function()
 local s=fixture(); s.FailRecord=true; s:RequestContinueResult(); assert(s.ResultReady and s.Calls.transition==nil)
 s.FailRecord=false; s.BattleResult='Defeat'; s.FailReturn=true; s:RequestContinueResult(); assert(s.ResultReady and s.Returned==1 and s.Command=='RETURN_TO_LOBBY')
end)
check('transition yield and old retry timer cannot reopen a newer battle result',function()
 local s=fixture(); s.DuringTransition=function(self) self.EntryRequestId=8 end; s:RequestContinueResult(); assert(s.Timer==nil)
 s=fixture(); s:RequestContinueResult(); s.EntryRequestId=8; s.Timer(); assert(not s.ResultReady)
end)
check('consumables reject wrong player, entry, timing and stale inventory without effects',function()
 local s,p=fixture(); s.BattleResult=''; assert(s:TryUseRunConsumable({},'potion',1,'',7,4).Reason=='INVALID_PLAYER')
 assert(s:TryUseRunConsumable(p,'potion',1,'',6,4).Reason=='INVALID_PLAYER')
 s.TurnState.IsActionProcessing=true; assert(s:TryUseRunConsumable(p,'potion',1,'',7,4).Reason=='INVALID_CONSUMABLE_TIMING')
 s.TurnState.IsActionProcessing=false; assert(s:TryUseRunConsumable(p,'potion',1,'',7,3).Reason=='STALE_INVENTORY' and s.Calls.effect==nil)
end)
check('consumable effect and inventory share one receipt without spending a turn',function()
 local s,p=fixture(); s.BattleResult=''; local r=s:TryUseRunConsumable(p,'potion',1,'',7,4)
 assert(r.Success and r.AppliedAmount==3 and r.ConsumedAmount==1 and not r.ConsumesTurn and s.Calls.effect==1 and s.Calls.consume==1 and s.TutorialUsed==r)
 s.AlreadyApplied=true; assert(s:TryUseRunConsumable(p,'potion',1,'',7,4).Reason=='DUPLICATE_USE_IGNORED' and s.Calls.effect==1 and s.Calls.consume==1)
end)
check('failed effect never consumes and failed commit never reports success',function()
 local s,p=fixture(); s.BattleResult=''; s.FailEffect=true; assert(s:TryUseRunConsumable(p,'potion',1,'',7,4).Reason=='EFFECT_FAILED' and s.Calls.consume==nil)
 s.FailEffect=false; s.FailCommit=true; assert(s:TryUseRunConsumable(p,'potion',1,'',7,4).Reason=='CONSUMABLE_COMMIT_FAILED' and s.TutorialUsed==nil)
end)
check('discard retains active run, revision and guided-lesson guards',function()
 local s,p,run,inv=fixture(); s.BattleResult=''; s.Guided=true; assert(s:TryDiscardRunConsumable(p,'potion',1,7,4).Reason=='TUTORIAL_FOLLOW_GUIDE')
 s.Guided=false; assert(s:TryDiscardRunConsumable(p,'potion',1,7,3).Reason=='STALE_INVENTORY')
 assert(s:TryDiscardRunConsumable(p,'potion',1,7,4).ConsumedAmount==1 and s.Calls.effect==nil and s.Calls.discard==1)
end)
check('consumable HUD derives usability from live HP/status/cooldown and returns fresh data',function()
 local s,p,run,inv,u=fixture(); s.BattleResult=''; local dto=s:BuildConsumableHudState(); assert(dto.Success and dto.CanUse and dto.Items[1].Usable and not dto.Items[2].Usable)
 u.CurrentHp=10; u.SealTurns=1; local next=s:BuildConsumableHudState(); assert(not next.Items[1].Usable and next.Items[2].Usable and dto.Items[1].Usable)
 s.BattleResult='Victory'; assert(not s:BuildConsumableHudState().CanUse)
end)
check('accepted round reward is receipt-deduplicated and isolated between sessions',function()
 local a=fixture(); a._T.RoundRewardEntries={}; a._T.RoundRewardReceipts={}; a:RecordRoundReward('CURRENCY','gold',2,'pickup'); a:RecordRoundReward('CURRENCY','gold',2,'pickup')
 assert(a.ResultGold==2 and string.find(a.ResultRewardSnapshot,'CURRENCY~gold~2',1,true))
 local b=fixture(); b._T.RoundRewardEntries={}; b._T.RoundRewardReceipts={}; b:RecordRoundReward('CURRENCY','gold',3,'pickup'); assert(b.ResultGold==3 and a.ResultGold==2)
end)
print(checks..' entry/result/consumable regressions passed')
''')
