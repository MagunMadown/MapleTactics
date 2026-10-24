"""Run production relic acquisition/shop/trigger methods in Lua 5.3, with only engine boundaries doubled."""
import csv, json, runpy
from pathlib import Path
ns=runpy.run_path(str(Path(__file__).with_name('verify-gold.py')))
lua,load=ns['lua'],ns['load']
from lupa.lua53 import lua_type

def from_lua(value):
    if lua_type(value) != 'table': return value
    items=dict(value.items())
    if items and set(items)==set(range(1,len(items)+1)):
        return [from_lua(items[i]) for i in range(1,len(items)+1)]
    return {key:from_lua(v) for key,v in items.items()}

def into_lua(value):
    if isinstance(value,dict): return lua.table_from({k:into_lua(v) for k,v in value.items()})
    if isinstance(value,list): return lua.table_from([into_lua(v) for v in value])
    return value

lua.globals()._HttpService=lua.table_from({
    'JSONEncode':lambda _,value:json.dumps(from_lua(value),ensure_ascii=False,sort_keys=True),
    'JSONDecode':lambda _,value:into_lua(json.loads(value))})
for name in ['RunRelicFeedbackLogic','ContentRelicTriggerLogic','RelicDefinitionRepositoryLogic','PlayerRunInventoryComponent','PlayerRunRelicEffectComponent','BattleUnitComponent','RunShopLogic','PlayerRunShopStateComponent','CombatModifierEffectExecutorLogic']:
    load(name)
lua.execute('''
_PremiumBenefitsLogic={MagnetRelicId='premium_magnet_pet',GetMagnetRelicDefinition=function() return {RelicId='premium_magnet_pet',DisplayName='premium',IconImageRUID='x',IsOpen=false,RequiredJobId='',AttackBonus=0,MaxHpBonus=0,DefenseBonus=0,SpecialEffectType='MAGNET_PET',SpecialEffectValue=1} end}
_UtilLogic={RandomIntegerRange=function(self,a,b) return a end}
local catalog=_RelicDefinitionRepositoryLogic:GetAllDefinitions()
assert(catalog.Success,catalog.Reason)
local souvenirs={'orbis_star_fragment','orbis_moon_fragment','orbis_sun_fragment','orbis_stone_fragment','orbis_papa_crown','orbis_eliza_feather'}
for _,id in ipairs(souvenirs) do local d=catalog.Definitions[id];assert(d and d.IsOpen and d.RequiredJobId=='' and d.AttackBonus+d.MaxHpBonus+d.DefenseBonus==0) end
local bundle=_ShopDefinitionRepositoryLogic:GetShopBundle('shop_relic');assert(bundle.Success)
local function instance(proto) return setmetatable({_T={}},{__index=proto}) end
function relicFixture(job)
 local inv=instance(_PlayerRunInventoryComponent)
 inv.ActiveRunSequence=1;inv.RunItemSnapshot='';inv.AppliedRewardKeys='';inv.InventoryRevision=0
 inv.SetRelicConsumableSlotBonus=function() end
 local owner=instance(_PlayerRunRelicEffectComponent)
 owner.IsInitialized=true;owner.ActiveRunSequence=1;owner.Definitions=catalog.Definitions;owner.ShopBundle=bundle
 owner.ActiveBattleKey='';owner.ContentRelicBattleKey='';owner.SpecialEffects={};owner.ExhaustedRelics={};owner.RemainingUses={};owner.BossRelicRolls={}
 owner.PublishInventoryDisplay=function() end
 local run={RunSequence=1,SelectedJobId=job or 'warrior',RunHpInitialized=false,RunCurrentHp=5,RunMaxHp=10,
   SetRunHp=function(self,hp,maxHp) self.RunCurrentHp=hp;self.RunMaxHp=maxHp end}
 local runtime={cooldowns={},ReduceCooldown=function(self,id,n) self.cooldowns[id]=math.max(0,(self.cooldowns[id] or 0)-n) end}
 local unit=instance(_BattleUnitComponent)
 local player=entity({['script.PlayerRunRelicEffectComponent']=owner,['script.PlayerRunInventoryComponent']=inv,
   ['script.PlayerRunStateComponent']=run,['script.BattleUnitComponent']=unit,['script.SkillRuntimeStateComponent']=runtime})
 player.PlayerComponent={};owner.Entity=player;inv.Entity=player;unit.Entity=player
 unit:InitializeBattleState('player_01','Player',3,'Right',10,0);unit.CurrentHp=5
 _ContentRelicTriggerLogic:Reset(owner)
 owner:BeginBattle('orbis_stage_16',101)
 return owner,inv,unit,run,runtime,player
end
local function own(owner,inv,id)
 local d=owner.Definitions[id]
 local r=inv:GrantRelicFrom(id,'test:'..id,d.AcquisitionType or 'GENERAL',d.AcquisitionSourceId or '')
 assert(r.Success,r.Reason..' '..id)
end
local R=_ContentRelicTriggerLogic
local function context(index,count,skill)
 return {SkillId=skill or 'slash',BattleSession={TurnState={ExecutingTileIndex=index,ExecutingTileIds=count,
   GetTileIdCount=function(self,ids) return ids end}}}
end
-- Source gating and starting rolls across every job.
for _,job in ipairs({'warrior','mage','archer','thief','pirate'}) do
 local o,i,u,r,rt,p=relicFixture(job)
 for _,id in ipairs(souvenirs) do assert(not i:GrantRelic(id,'wrong:'..id).Success) end
 assert(not i:GrantRelicFrom('orbis_papa_crown','wrongboss','BOSS_CLEAR','orbis_stage_14').Success)
 i.RunCurrencySnapshot='gold~100';i.AppliedPurchaseKeys=''
 assert(not i:ApplyShopPurchase('gold',1,'ITEM','orbis_papa_crown',1,'wrong_shop').Success and i.RunCurrencySnapshot=='gold~100')
 assert(o:GrantStartingRelics(3).Success)
 for _,id in ipairs(souvenirs) do assert(i:GetSnapshotAmount(i.RunItemSnapshot,id)==0) end
 local first=o:GrantBossContentRelic('orbis_stage_07','first');assert(first.Success and first.RelicId=='orbis_papa_crown')
 assert(o:GrantBossContentRelic('orbis_stage_07','retry-other-entry').Success)
 assert(i:GetSnapshotAmount(i.RunItemSnapshot,'orbis_papa_crown')==1)
 assert(o:GrantBossContentRelic('orbis_stage_14','second').RelicId=='orbis_eliza_feather')
 local oldRoll=false;o.GrantBossClassRelic=function() oldRoll=true;return {Success=true} end
 assert(o:GrantBossContentRelic('stage_04','legacy').Success and oldRoll)
end
-- Catalog defaults and invalid source references (actual repository).
local data=_DataService.Tables.RelicDefinitions
local legacy={};for k,v in pairs(data.rows[1]) do legacy[k]=v end
legacy.AcquisitionType=nil;legacy.AcquisitionSourceId=nil
_DataService.Tables.RelicDefinitions=dataset({legacy})
assert(_RelicDefinitionRepositoryLogic:GetAllDefinitions().Definitions[legacy.RelicId].AcquisitionType=='GENERAL')
for _,bad in ipairs({{'UNKNOWN',''},{'GENERAL','orbis'},{'REGION_SHOP','missing'},{'BOSS_CLEAR','orbis_stage_01'}}) do
 legacy.AcquisitionType=bad[1];legacy.AcquisitionSourceId=bad[2]
 assert(_RelicDefinitionRepositoryLogic:GetAllDefinitions().Reason=='INVALID_RELIC_ACQUISITION')
end
_DataService.Tables.RelicDefinitions=data
-- Shop distribution, ownership depletion, legacy exclusion, reopen, and sale values.
local svc=_RunShopLogic
_ConsumableDefinitionRepositoryLogic={ShopBasePrices={},GetDefinition=function() return {Success=false} end}
svc.BuildPotionOffers=function() return {Success=true,Entries={}} end
svc.CaptureSkillSellCatalog=function() end
for seed=0,127 do
 for _,node in ipairs({'orbis_shop_after_stage03','orbis_shop_after_stage10','shop_upper'}) do
  local o,i,u,r,rt,p=relicFixture()
  for k=1,seed%5 do own(o,i,souvenirs[k]) end
  local visit=instance(_PlayerRunShopStateComponent);visit.ShopRevision=0;visit:ResetForRun(1)
  r.RunFlowState='AWAITING_SHOP';r.ContentTransitionState='READY';r.SelectedContentType='SHOP';r.SelectedContentId='shop_relic';r.SelectedNodeId=node;r.LastContentSelectionKey='visit:'..seed
  _RunManagerLogic={GetOrCreateRunState=function() return r end,GetOrCreateRunInventory=function() return i end}
  svc.GetOrCreateShopState=function() return visit end;svc.GetOrCreateRelicEffects=function() return o end
  _UtilLogic.RandomIntegerRange=function(self,a,b) return a+(seed%(b-a+1)) end
  assert(svc:OpenShop(p,'shop_relic').Success)
  local general,regional=0,0
  for _,e in pairs(visit.OfferedEntries) do
   local d=o.Definitions[e.RewardRefId];assert(o:CanAcquireRelic(e.RewardRefId))
   if d.AcquisitionType=='REGION_SHOP' then regional=regional+1 else assert(d.AcquisitionType=='GENERAL');general=general+1 end
  end
  local wantRegional=node~='shop_upper' and seed%5<4 and 1 or 0
  assert(regional==wantRegional and general==3-wantRegional,node)
  if node=='orbis_shop_after_stage03' then assert(visit.OfferedEntry.PriceAmount==35 and visit.OfferedEntry.PriceAmount<=39) end
  local snap=visit.OfferSnapshot;assert(svc:OpenShop(p,'shop_relic').Success and snap==visit.OfferSnapshot)
  assert(visit.SellCatalog.orbis_papa_crown==nil and visit.SellCatalog.orbis_eliza_feather==nil)
  assert(visit.SellCatalog.orbis_star_fragment==24 and visit.SellCatalog.orbis_moon_fragment==28 and visit.SellCatalog.orbis_sun_fragment==35 and visit.SellCatalog.orbis_stone_fragment==31)
 end
end
local o,i,u,r,rt,p=relicFixture()
for _,id in ipairs(souvenirs) do own(o,i,id) end
-- Last registered slot, not repeated cast count; only one impact per queue.
R:QueueStarted(o)
local a=context(1,2);R:SkillStarted(o,a,true);assert(R:FinisherBonus(o,a)==0)
local b=context(2,2);R:SkillStarted(o,b,true);assert(R:FinisherBonus(o,b)==1 and R:FinisherBonus(o,b)==0)
local repeatCast=context(2,2);R:SkillStarted(o,repeatCast,true);assert(R:FinisherBonus(o,repeatCast)==0)
R:QueueEnded(o);R:QueueStarted(o)
local single=context(1,1);R:SkillStarted(o,single,true);assert(R:FinisherBonus(o,single)==0)
local utility=context(2,2);R:SkillStarted(o,utility,false);assert(R:FinisherBonus(o,utility)==0)
-- Ordinary facing charge, nonattack preservation, miss consumption and one successful refund.
R:Turned(o);R:Turned(o);R:SkillStarted(o,utility,false);assert(o.ContentRelicState.Moon)
local miss=context(1,1);R:SkillStarted(o,miss,true);assert(not o.ContentRelicState.Moon and miss.ContentMoon)
local afterMiss=context(1,1);R:SkillStarted(o,afterMiss,true);assert(not afterMiss.ContentMoon)
R:Turned(o);rt.cooldowns.slash=3;local hit=context(1,1);R:SkillStarted(o,hit,true)
R:DirectHit(o,hit,'e1',0);assert(rt.cooldowns.slash==3)
R:DirectHit(o,hit,'e1',1);R:DirectHit(o,hit,'e1',1);assert(rt.cooldowns.slash==2)
-- Same cast distinct positive direct hits; one heal per queue and carry HP before settlement.
R:QueueStarted(o);u.CurrentHp=5;local multi=context(1,2);R:SkillStarted(o,multi,true)
R:DirectHit(o,multi,'e1',1);R:DirectHit(o,multi,'e1',1);R:DirectHit(o,multi,'e2',0);assert(u.CurrentHp==5)
R:DirectHit(o,multi,'e2',2);assert(u.CurrentHp==6 and r.RunCurrentHp==6)
local other=context(2,2);R:SkillStarted(o,other,true);R:DirectHit(o,other,'e3',1);R:DirectHit(o,other,'e4',1);assert(u.CurrentHp==6)
R:QueueEnded(o);o:EndBattleEffects();assert(r.RunCurrentHp==6)
o:BeginBattle('orbis_stage_16',101);assert(o.ContentRelicState.SunUsed)
o:BeginBattle('orbis_stage_15',102);assert(not o.ContentRelicState.SunUsed)
-- Stone charges at consumed boundaries, moving cancels only unfinished progress.
R:PlayerActionStarted(o);R:PlayerActionCompleted(o);assert(o.ContentRelicState.Stationary==1)
u:ApplyCellChange(4);assert(o.ContentRelicState.Stationary==0)
R:PlayerActionCompleted(o);assert(o.ContentRelicState.Stationary==0)
R:PlayerActionStarted(o);R:QueueStarted(o);R:QueueEnded(o);R:PlayerActionCompleted(o);assert(o.ContentRelicState.Stationary==1)
R:PlayerActionCompleted(o);assert(o.ContentRelicState.Stone)
u:ApplyCellChange(3);assert(o.ContentRelicState.Stone and o.ContentRelicState.Stationary==0)
o.IncomingDirectDamage=false;assert(o:ResolveIncomingDamage(1,5)==1 and o.ContentRelicState.Stone)
o.IncomingDirectDamage=true;assert(o:ResolveIncomingDamage(1,5)==0 and not o.ContentRelicState.Stone)
-- An earlier full guard leaves stone ready, then stone precedes lethal survival.
own(o,i,'pot_lid')
o.ContentRelicState.Stone=true;o.FirstHitGuardUsed=false
assert(o:ResolveIncomingDamage(8,5)==0 and o.ContentRelicState.Stone)
i.RunItemSnapshot=i:SetSnapshotAmount(i.RunItemSnapshot,'pot_lid',0)
i.RunItemSnapshot=i:SetSnapshotAmount(i.RunItemSnapshot,'von_leon_war_belt',1);o:Recalculate()
assert(o:ResolveIncomingDamage(5,5)==4 and not o.LethalSurvivalUsed)
o.ContentRelicState.Stone=true;assert(o:ResolveIncomingDamage(6,5)==4 and o.LethalSurvivalUsed)
-- Forced movement between actions resets previous progress; next stationary action counts.
u:ApplyCellChange(2);R:PlayerActionStarted(o);R:PlayerActionCompleted(o);assert(o.ContentRelicState.Stationary==1)
-- All six harmful categories share the immunity window; three Ice Stoneballs do not spend it.
o:BeginBattle('orbis_stage_16',103)
for n=1,3 do assert(u:ApplyHostileStatus('FROSTBITE',1,0,'ice'..n).Reason=='RELIC_STATUS_IMMUNE') end
assert(u.FrostbiteTurns==0 and o.ContentRelicState.FeatherUsed and o.ContentRelicState.FeatherActive)
assert(u:ApplySeal(1).Reason=='RELIC_STATUS_IMMUNE')
assert(u:ApplyHostileStatus('IGNITE',2,1,'fire').Reason=='RELIC_STATUS_IMMUNE')
assert(u:ApplyHostileStatus('CONFUSE',1,0,'boss').Reason=='RELIC_STATUS_IMMUNE')
assert(u:ApplyPoison('enemy',1,'').Reason=='RELIC_STATUS_IMMUNE')
local enemy=entity({['script.BattleUnitComponent']={Team='Enemy',CurrentHp=10,IsDead=false}})
local sess={FindUnitEntity=function(self,id) return id=='enemy' and enemy or p end}
local ctx={SourceUnitId='enemy',TargetUnitIds={'player_01'},SkillId='status'}
for _,kind in ipairs({'STUN','FREEZE'}) do
 assert(not _CombatModifierEffectExecutorLogic:ExecuteCombatModifier(sess,ctx,{EffectType=kind,Value=100,ParameterA='1',TargetSelector='ALL_TARGETS'}).Hit)
end
assert(u.StopActionTurns==0)
R:PlayerActionStarted(o) -- a free/rejected input never invokes the consumed boundary
assert(o.ContentRelicState.FeatherActive)
R:PlayerActionCompleted(o);assert(not o.ContentRelicState.FeatherActive)
assert(u:ApplyHostileStatus('FROSTBITE',1,0,'ice').Hit)
u:AdvanceNegativeStatusTurns();assert(u.FrostbiteTurns==0)
assert(not R:BlockNegativeStatus(o))
o:EndBattleEffects();o:BeginBattle('orbis_stage_16',103);assert(not R:BlockNegativeStatus(o))
o:BeginBattle('orbis_stage_16',104);assert(R:BlockNegativeStatus(o))
-- Wave transition receipts survive same-entry reinit; first/forced/final do not call a clear transition.
u.CurrentHp=5;R:WaveStarted(o,1,true);R:WaveStarted(o,2,false);assert(u.CurrentHp==5)
R:WaveStarted(o,2,true);assert(u.CurrentHp==6 and r.RunCurrentHp==6)
R:WaveStarted(o,2,true);assert(u.CurrentHp==6)
o:EndBattleEffects();o:BeginBattle('orbis_stage_16',104);R:WaveStarted(o,2,true);assert(u.CurrentHp==6)
o:BeginBattle('orbis_stage_16',105);R:WaveStarted(o,2,true);assert(u.CurrentHp==7)
u.IsDead=true;R:WaveStarted(o,3,true);assert(u.CurrentHp==7)
u.IsDead=false;u.CurrentHp=10;R:WaveStarted(o,4,true);assert(u.CurrentHp==10)
-- Removing a sold shop relic clears its outstanding charge without resetting battle receipts.
o.ContentRelicState.Moon=true;o.ContentRelicState.Stone=true;o.ContentRelicState.Stationary=1
for _,id in ipairs({'orbis_moon_fragment','orbis_stone_fragment'}) do i.RunItemSnapshot=i:SetSnapshotAmount(i.RunItemSnapshot,id,0) end
o:Recalculate();assert(not o.ContentRelicState.Moon and not o.ContentRelicState.Stone and o.ContentRelicState.Stationary==0)
''')
report={'result':'PASS','shopCases':384,'jobs':5,'relics':6,'luaVersion':'5.3',
 'checks':['source gating and legacy default','guaranteed once-per-stage gifts and class fallback','starting relic exclusion',
 'regional/general slots, depletion, stable reopen and 39-gold affordability','70-percent sale and boss exclusion',
 'queue finisher and repeat limits','turn charge miss/hit cooldown refund','positive unique-target healing and run HP carry',
 'stationary charge, forced movement, full guard and survival order','all six hostile categories and three-Ice immunity expiry',
 'wave receipts and same-entry preservation/new-entry reset','selling clears outstanding charges'],
 'scope':'Production Lua methods with engine/player service doubles; Maker evidence is tracked separately'}
Path(__file__).with_name('relic-lua-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
