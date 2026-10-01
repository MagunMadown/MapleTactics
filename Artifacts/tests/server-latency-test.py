"""Actual mLua methods with controlled asynchronous storage/resource callbacks.
Offline regression only; does not claim MSW rendering, tick, or network behavior.
"""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
base = ROOT / 'Artifacts/tests/union-free-job-token-test.py'
source = base.read_text(encoding='utf-8-sig')
context = {'__file__': str(base), '__name__': '__main__'}
exec(compile(source, str(base), 'exec'), context)
lua, load = context['lua'], context['load_methods']

def methods(path):
    text = (ROOT / path).read_text(encoding='utf-8-sig')
    names = set(re.findall(r'^\s+method\s+\w+\s+(\w+)\(', text, re.M))
    return load(path, names), len(names)

compiled = 0
for path in ['RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.mlua',
             'RootDesk/MyDesk/00_Core/UnionShopServiceLogic.mlua',
             'RootDesk/MyDesk/00_Core/Lobby/MonsterCollectionLogic.mlua',
             'RootDesk/MyDesk/01_Combat/Components/Shared/BattleDropPresentationComponent.mlua']:
    obj, count = methods(path)
    compiled += count
    if 'MonsterCollectionLogic' in path: lua.globals().collection = obj
    if 'BattleDropPresentationComponent' in path: lua.globals().drops = obj
    if 'UnionProfileRepository' in path:
        lua.globals().repo.GetUnionShopSnapshot = obj.GetUnionShopSnapshot
        lua.globals().repo.TryCommitPaidUnionCoins = obj.TryCommitPaidUnionCoins
    if 'UnionShopService' in path:
        lua.globals().shop.RequestShop = obj.RequestShop
print(f'PASS syntax: {compiled} actual method bodies compile in Lua 5.4')

lua.execute(r'''
logs={}
log=function(s) table.insert(logs,s) end
log_warning=log; log_error=log
isvalid=function(v) return type(v)=='table' and v.Invalid~=true end
Vector2=function(x,y) return {x=x,y=y} end
Vector3=function(x,y,z) return {x=x,y=y,z=z} end
repo._T={}
local scans={upgrade=0,stat=0,level=0,rank=0,lifetime=0}
local u=_UnionUpgradeDefinitionRepositoryLogic.GetAllDefinitions
_UnionUpgradeDefinitionRepositoryLogic.GetAllDefinitions=function(self) scans.upgrade=scans.upgrade+1 return u(self) end
local s=_UnionStatDefinitionRepositoryLogic.GetStat
_UnionStatDefinitionRepositoryLogic.GetStat=function(self,id) scans.stat=scans.stat+1 return s(self,id) end
local l=_UnionStatDefinitionRepositoryLogic.GetLevel
_UnionStatDefinitionRepositoryLogic.GetLevel=function(self,id,n) scans.level=scans.level+1 return l(self,id,n) end
local r=_UnionRankDefinitionRepositoryLogic.GetDefinition
_UnionRankDefinitionRepositoryLogic.GetDefinition=function(self,id) scans.rank=scans.rank+1 return r(self,id) end
local q=_UnionRankDefinitionRepositoryLogic.GetRankForLifetimePoints
_UnionRankDefinitionRepositoryLogic.GetRankForLifetimePoints=function(self,n) scans.lifetime=scans.lifetime+1 return q(self,n) end
local p=fixture(5000)
p.AllocatedUnionStats={attack=3}
assert(repo:ValidateProfileData(p).Success)
local a,b,c,d,e=scans.upgrade,scans.stat,scans.level,scans.rank,scans.lifetime
assert(repo:ValidateProfileData(p).Success)
assert(scans.upgrade==a and scans.stat==b and scans.level==c and scans.rank==d and scans.lifetime==e)
p.AllocatedUnionStats.attack=11
assert(not repo:ValidateProfileData(p).Success)
p.AllocatedUnionStats={bogus=1}
assert(not repo:ValidateProfileData(p).Success)
assert(not repo:ValidateProfileData(p).Success and scans.stat==b+2)
repo:GetProfileLifetimeRank(1); repo:GetProfileLifetimeRank(1)
assert(scans.lifetime==e+1)
repo:GetProfileLifetimeRank(2)
assert(scans.lifetime==e+2)
''')
print('PASS definition caching: repeat CSV reads disappear; invalid state and failed lookup remain rejected/retryable')

lua.execute(r'''
local p=fixture(5000)
function repo:EnsureProfileLoaded(user) return {Success=true,StorageUserKey='test-account'} end
local snapshot=repo:GetUnionShopSnapshot(player)
assert(snapshot.Success and snapshot.Snapshot.Coins==5000)
snapshot.Snapshot.JobTokens=999
assert(cached().UnionShop.JobTokens==0)
_UtilLogic.ElapsedSeconds=0
local original=storage.UpdateAndWait
storage.UpdateAndWait=function(self,...) _UtilLogic.ElapsedSeconds=_UtilLogic.ElapsedSeconds+0.125 return original(self,...) end
local result=repo:TryCommitUnionShopAction(player,'BUY','job_unlock_free',0,0)
assert(result.Success and durable().UnionShop.JobTokens==1 and durable().UnionShop.FreeJobTokenClaimed)
local hasTiming=false
for _,line in ipairs(logs) do if string.find(line,'phase=SAVE',1,true) and string.find(line,'storageMs=125',1,true) then hasTiming=true end end
assert(hasTiming)
player.CurrentMap={Name='lobby'}; player.GetComponent=function() return nil end
_UserService={GetUserEntityByUserId=function() return player end}
_UnionProfileRepositoryLogic=repo; senderUserId='test'
local response
shop.ReceiveShop=function(self,id,success,reason,state) response={Id=id,Success=success,State=state} end
shop:RequestShop('OPEN','',0,91)
assert(response.Id==91 and response.Success and response.State.FreeJobTokenClaimed)
fixture(5000)
local paid=repo:TryCommitPaidUnionCoins(player,'native-receipt-1','coin-product',2000)
assert(paid.Success and durable().UnionPoints==7000 and durable().PaidPurchaseReceipts['native-receipt-1'].Amount==2000)
local writes=storage.Writes
assert(repo:TryCommitPaidUnionCoins(player,'native-receipt-1','coin-product',2000).Success and storage.Writes==writes)
assert(not repo:TryCommitPaidUnionCoins(player,'native-receipt-1','other-product',2000).Success and storage.Writes==writes)
storage.FailNext=1000004
assert(not repo:TryCommitPaidUnionCoins(player,'native-receipt-2','coin-product',2000).Success)
assert(cached().UnionPoints==7000 and cached().PaidPurchaseReceipts['native-receipt-2']==nil)
assert(repo:TryCommitPaidUnionCoins(player,'native-receipt-2','coin-product',2000).Success and durable().UnionPoints==9000)
''')
print('PASS shop DTO/durable timing: private copy, persisted token+flag, actual CAS duration, request response')

lua.execute(r'''
collection._T={}; collection.StorageKey='MonsterCollectionV1'; collection.Records={}; collection.Closing=false
function collectionFixture()
 collection.Records={}; collection.Closing=false
 _UtilLogic.ElapsedSeconds=0; senderUserId='collector'
 collector={PlayerComponent={UserId='collector',ProfileCode='collection-account'}}
 _UserService={UserEntities={Values={collector}},GetUserEntityByUserId=function() return collector end}
 timerCallbacks={}; nextTimer=0
 _TimerService={SetTimerOnce=function(self,cb,delay) nextTimer=nextTimer+1; timerCallbacks[nextTimer]=cb; return nextTimer end,
                ClearTimer=function(self,id) timerCallbacks[id]=nil end}
 collectionIO={GetCalls=0,WaitReads=0,WriteCalls=0,Raw='',Code=0}
 function collectionIO:GetAndWait() self.WaitReads=self.WaitReads+1 error('inline collection read forbidden') end
 function collectionIO:GetAsync(key,cb) assert(key==collection.StorageKey); self.GetCalls=self.GetCalls+1; self.LoadCallback=cb end
 function collectionIO:SetAsync(key,raw,cb) self.WriteCalls=self.WriteCalls+1; self.Candidate=raw; self.SaveCallback=cb end
 function collectionIO:UpdateAsync(key,old,raw,cb) assert(old==self.Raw); self:SetAsync(key,raw,cb) end
 function collectionIO:SetAndWait(key,raw) self.WriteCalls=self.WriteCalls+1; self.Raw=raw; return 0 end
 function collectionIO:UpdateAndWait(key,old,raw) assert(old==self.Raw); return self:SetAndWait(key,raw) end
 _DataStorageService={GetUserDataStorage=function() return collectionIO end}
 snapshots={}
 collection.ReceiveSnapshot=function(self,raw,loaded,id) table.insert(snapshots,{Raw=raw,Loaded=loaded,Discovered=id}) end
 wait=function(seconds) _UtilLogic.ElapsedSeconds=_UtilLogic.ElapsedSeconds+seconds end
end
function completeCollectionLoad(code,raw)
 local callback=collectionIO.LoadCallback; collectionIO.LoadCallback=nil
 collectionIO.Raw=raw or ''; _UtilLogic.ElapsedSeconds=_UtilLogic.ElapsedSeconds+0.2
 callback(code,collection.StorageKey,raw)
end
function completeCollectionSave()
 local callback=collectionIO.SaveCallback; collectionIO.SaveCallback=nil; collectionIO.Raw=collectionIO.Candidate
 callback(0,collection.StorageKey,collectionIO.Raw)
end
collectionFixture(); collection:OnBeginPlay()
assert(collectionIO.GetCalls==1)
collection:RecordDefeat(collector,'known'); collection:RecordDefeat(collector,'new')
collection:MarkRead('new')
local record=collection.Records.collector
assert(not record.Loaded and record.Pending.new==2 and collectionIO.WaitReads==0)
for _,snapshot in ipairs(snapshots) do assert(snapshot.Discovered=='') end
completeCollectionLoad(0,collection:EncodeRecords({known=2}))
assert(record.Loaded and record.Entries.known==2 and record.Entries.new==2)
assert(snapshots[#snapshots].Loaded and snapshots[#snapshots].Discovered=='new')
assert(collection:FlushRecord(record,false))
collection:RecordDefeat(collector,'later')
completeCollectionSave()
assert(record.Pending.later==1 and record.Pending.new==nil)
assert(collection:FlushRecord(record,false)); completeCollectionSave()
local saved=collection:DecodeRecords(collectionIO.Raw)
assert(saved.known==2 and saved.new==2 and saved.later==1 and next(record.Pending)==nil)
''')
print('PASS async collection join/death/read/save race: zero synchronous reads, canonical merge, newer pending survives write')

lua.execute(r'''
collectionFixture(); collection:RecordDefeat(collector,'first')
local record=collection.Records.collector
completeCollectionLoad(1000004,'')
assert(not record.Loaded and record.Pending.first==1 and collectionIO.WriteCalls==0)
_UtilLogic.ElapsedSeconds=11; collection:LoadRecord(record)
completeCollectionLoad(1000002,'')
assert(record.Loaded and not record.Exists)
assert(collection:FlushRecord(record,false)); completeCollectionSave()
assert(collection:DecodeRecords(collectionIO.Raw).first==1)
collectionFixture(); collection:RecordDefeat(collector,'new')
record=collection.Records.collector
completeCollectionLoad(0,'corrupt')
assert(record.Invalid and not collection:FlushRecord(record,false) and collectionIO.WriteCalls==0)
collectionFixture(); collection:RecordDefeat(collector,'old')
record=collection.Records.collector
collection.Records.collector={Loaded=true,Entries={replacement=2}}
completeCollectionLoad(0,collection:EncodeRecords({old=2}))
assert(collection.Records.collector.Entries.old==nil)

-- A repeated completion must not roll a durable generation back to its old read.
collectionFixture(); collection:RecordDefeat(collector,'first')
record=collection.Records.collector
local repeatedRead=collectionIO.LoadCallback
completeCollectionLoad(1000002,'')
assert(collection:FlushRecord(record,false)); completeCollectionSave()
local persistedRaw=record.Raw; local snapshotCount=#snapshots
repeatedRead(1000002,collection.StorageKey,'')
assert(record.Raw==persistedRaw and record.Entries.first==1 and #snapshots==snapshotCount)

-- A stale failed-read callback must not complete the next retry generation.
collectionFixture(); collection:RecordDefeat(collector,'first')
record=collection.Records.collector; repeatedRead=collectionIO.LoadCallback
completeCollectionLoad(1000004,'')
_UtilLogic.ElapsedSeconds=11; collection:LoadRecord(record)
snapshotCount=#snapshots
repeatedRead(1000002,collection.StorageKey,'')
assert(record.Loading and not record.Loaded and #snapshots==snapshotCount)
completeCollectionLoad(0,collection:EncodeRecords({known=2}))
assert(record.Loaded and record.Entries.known==2 and record.Entries.first==1)

-- Repeating the previous write cannot clear a newer write or notify a new session.
assert(collection:FlushRecord(record,false))
local repeatedSave=collectionIO.SaveCallback
completeCollectionSave()
collection:RecordDefeat(collector,'second'); assert(collection:FlushRecord(record,false))
persistedRaw=record.Raw; snapshotCount=#snapshots
repeatedSave(0,collection.StorageKey,persistedRaw)
assert(record.Saving and record.Raw==persistedRaw and #snapshots==snapshotCount)
local oldSessionSave=collectionIO.SaveCallback
collection.Records.collector={Loaded=true,Entries={replacement=2}}
oldSessionSave(0,collection.StorageKey,collectionIO.Candidate)
assert(collection.Records.collector.Entries.second==nil and #snapshots==snapshotCount)
''')
print('PASS async collection failure/missing/corrupt/duplicate/stale generations: no overwrite or loss of pending discovery')

lua.execute(r'''
collectionFixture(); collection:RecordDefeat(collector,'logout')
local record=collection.Records.collector
local completed=false
wait=function(seconds)
 _UtilLogic.ElapsedSeconds=_UtilLogic.ElapsedSeconds+seconds
 if not completed then completed=true completeCollectionLoad(1000002,'') end
end
assert(collection:FlushFinalRecord(record))
assert(collection:DecodeRecords(collectionIO.Raw).logout==1 and next(record.Pending)==nil)
collectionFixture(); collection:RecordDefeat(collector,'late')
record=collection.Records.collector
assert(not collection:FlushFinalRecord(record) and record.FinalFlushRequested and record.Pending.late==1)
completeCollectionLoad(1000002,'')
assert(not record.FinalFlushRequested and next(record.Pending)==nil and collection:DecodeRecords(collectionIO.Raw).late==1)
''')
print('PASS logout while load pending: bounded wait and late completion both preserve final persistence')

lua.execute(r'''
function dropFixture()
 drops._T={}; drops.Entity={Name='battle-map'}
 drops.CurrencySpriteRuid='coin'; drops.ConsumableSpriteRuid='default'
 drops.DropModelId='drop-model'; drops.SpawnSequence=0
 drops.CellStartX=-2.8; drops.CellSpacing=1.12; drops.UnitY=0.12; drops.DropHeightOffset=0.04
 drops.FloatAmplitude=0.06; drops.FloatCycleTime=0.9
 timerCallbacks={}; nextTimer=0
 _TimerService={SetTimerOnce=function(self,cb,delay) assert(delay>0); nextTimer=nextTimer+1; timerCallbacks[nextTimer]=cb; return nextTimer end}
 preloadCallbacks={}; resourceWaits=0; showing=false
 ResourceType={Sprite='sprite',AnimationClip='clip'}
 _ResourceService={
  PreloadAsync=function(self,ids,cb) table.insert(preloadCallbacks,cb) end,
  GetTypeAndWait=function(self,id) assert(not showing); resourceWaits=resourceWaits+1; return ResourceType.Sprite end,
  LoadSpriteAndWait=function(self,id) assert(not showing); resourceWaits=resourceWaits+1; return {IsLoadComplete=true,Width=100,PivotPixel={x=75},PixelPerUnit=100} end,
 }
 _ConsumableDefinitionRepositoryLogic={GetDefinition=function(self,id) return {Success=true,IconKey='potion-'..id} end}
 _SpawnService={SpawnByModelId=function(self,model,name,pos,parent)
  assert(parent==drops.Entity)
  return {SpriteRendererComponent={},TransformComponent={WorldPosition=pos}}
 end}
 _UtilLogic.ElapsedSeconds=0
 drops:OnBeginPlay()
end
dropFixture(); assert(nextTimer==0 and resourceWaits==0)
showing=true
local shown=drops:ShowDrop('reward','CURRENCY','gold',1,0)
showing=false
assert(shown.Success and shown.Entity.TransformComponent.WorldPosition.x==-2.8 and resourceWaits==0 and nextTimer==1)
assert(drops:ResolveSpriteCenterOffsetX('coin')==0 and nextTimer==1)
local flying={SpriteRendererComponent={SpriteRUID='coin'},TransformComponent={WorldPosition=Vector3(9,0,0)}}
drops.SpawnedDropEntities.flying=flying; drops._T.MagnetFlights={flying={}}
timerCallbacks[1](); assert(resourceWaits==0 and #preloadCallbacks==1)
_UtilLogic.ElapsedSeconds=0.5; preloadCallbacks[1]()
assert(resourceWaits==2 and math.abs(shown.Entity.TransformComponent.WorldPosition.x+2.55)<0.00001)
assert(flying.TransformComponent.WorldPosition.x==9 and drops:ResolveSpriteCenterOffsetX('coin')==0.25)
assert(nextTimer==1 and resourceWaits==2)
preloadCallbacks[1]()
assert(resourceWaits==2 and math.abs(shown.Entity.TransformComponent.WorldPosition.x+2.55)<0.00001)
''')
print('PASS drop hotpath: no resource waits, deduplicated preload, cached center, late correction leaves magnet flights alone')

lua.execute(r'''
dropFixture(); drops:ConfigureBoard(-2.8,1.12,0.12)
local timers=nextTimer
assert(timers==7 and resourceWaits==0)
drops:ConfigureBoard(-2.8,1.12,0.12); assert(nextTimer==timers)
timerCallbacks[1](); assert(#preloadCallbacks==1)
drops:OnEndPlay(); preloadCallbacks[1]()
assert(resourceWaits==0 and drops.SpriteCenterOffsets.coin==nil)
dropFixture()
_ResourceService.LoadSpriteAndWait=function() resourceWaits=resourceWaits+1; return {IsLoadComplete=false} end
assert(drops:ResolveSpriteCenterOffsetX('coin')==0)
timerCallbacks[1](); preloadCallbacks[1]({false})
assert(drops:ResolveSpriteCenterOffsetX('coin')==0 and resourceWaits==2)
assert(string.find(logs[#logs],'success=false',1,true))
showing=true
assert(drops:ShowDrop('fallback','CURRENCY','gold',1,0).Success)
showing=false
''')
print('PASS resource lifecycle: entered map warmup only, once per map, stale callbacks ignored after teardown')
print('PASS 7 new behavioral groups + existing 10 durable free-token groups')
