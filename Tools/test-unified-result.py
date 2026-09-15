"""Execute production mLua method bodies with mocked MSW boundaries (not a Maker playtest)."""
import os, re, sys
from pathlib import Path
sys.path.insert(0, os.environ.get('LUPA_PATH', str(Path(__file__).parent / 'test-deps')))
from lupa.lua54 import LuaRuntime
lua = LuaRuntime(unpack_returned_tuples=True)
root = Path(__file__).parent
if len(sys.argv) > 1:
    root = Path(sys.argv[1])
sources = {
    'BattleSessionComponent.mlua': 'RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua',
    'BattleQueueHudComponent.mlua': 'RootDesk/MyDesk/02_UI/BattleQueueHudComponent.mlua',
    'PlayerRunInventoryComponent.mlua': 'RootDesk/MyDesk/04_Roguelike/RunManager/PlayerRunInventoryComponent.mlua',
}
def install(file, owner, names):
    source = (root / (sources[file] if len(sys.argv) > 1 else file)).read_text(encoding='utf-8-sig')
    for name in names:
        match = re.search(r'\bmethod\s+\S+\s+'+name+r'\((.*?)\)\n(.*?)\n\tend', source, re.S)
        assert match, name
        args = [a.strip().split()[-1] for a in match[1].split(',') if a.strip()]
        lua.execute(f'function {owner}:{name}({",".join(args)})\n{match[2]}\nend')

lua.execute('''
log=function() end; log_error=log; isvalid=function(e) return e~=nil end
inventory={ActiveRunSequence=3,RunItemSnapshot='',AppliedRewardKeys='',InventoryRevision=0}
session={EntryRequestId=8,HudContextRevision=12,ResultReady=true,ResultRecorded=true,
 BattleResult='Victory',ResultRewardReceipt={},ResultRelicOffers={},ResultSelectedRelicId='',
 ResultRewardRunSequence=3,StageId='stage01',StageType='BOSS',ResultOffersPrepared=false,UnionRewardRunEnded=false}
player={}; session.PlayerEntity=player
session.IsValidPlayerRequest=function(self,user) return user=='owner' end
senderUserId='owner'
effects={IsInitialized=true,ActiveRunSequence=3,Definitions={}}
for i=1,5 do effects.Definitions['r'..i]={RelicId='r'..i,DisplayName='Relic '..i,IconImageRUID='icon'..i,EffectDescription='effect'} end
_RunShopLogic={GetOrCreateRelicEffects=function() return effects end}
_RunManagerLogic={GetOrCreateRunInventory=function() return inventory end}
_UtilLogic={RandomIntegerRange=function(a,b) return 1 end}
_ConsumableDefinitionRepositoryLogic={GetDefinition=function() return {Success=true,DisplayName='Potion',IconKey='potion'} end}
local function validateJson(value)
 if type(value)=='table' then
  assert(next(value)~=nil, 'LuaTableToJsonType.UnknownType: empty table')
  for key,child in pairs(value) do validateJson(child) end
 else assert(type(value)=='string' or type(value)=='number' or type(value)=='boolean', 'Unsupported JSON value') end
end
_HttpService={JSONEncode=function(self,value) validateJson(value); encoded=value; return 'encoded' end}
''')
install('PlayerRunInventoryComponent.mlua','inventory',['IsSafeToken','ContainsDelimitedKey','AppendDelimitedKey','GetSnapshotAmount','AddSnapshotAmount','SetSnapshotAmount','GrantBattleRelic'])
install('BattleSessionComponent.mlua','session',['AccumulateResultReward','PrepareResultRelics','PublishResultRewardSnapshot','RequestConfirmResultReward','RequestContinueResult'])
lua.execute('''
inventory.RunItemSnapshot='r1~1'
session.StageType='NORMAL';session:PrepareResultRelics();assert(#session.ResultRelicOffers==0)
session:PublishResultRewardSnapshot();assert(encoded.Relics==nil and encoded.Rewards==nil)
assert(encoded.Entry==8 and encoded.Context==12)
session.ResultOffersPrepared=false;session.StageType='ELITE';session:PrepareResultRelics();assert(#session.ResultRelicOffers==0)
session.ResultOffersPrepared=false;session.StageType='BOSS'
session:PrepareResultRelics()
assert(#session.ResultRelicOffers==3 and session.ResultRelicOffers[1].Id=='r2')
local offer=session.ResultRelicOffers[1].Id
session:PrepareResultRelics(); assert(session.ResultRelicOffers[1].Id==offer)
session:AccumulateResultReward('CURRENCY','gold',8)
session:AccumulateResultReward('CURRENCY','gold',2)
session:AccumulateResultReward('CONSUMABLE','red_potion',1)
session:AccumulateResultReward('CONSUMABLE','red_potion',0)
session:PublishResultRewardSnapshot()
assert(#encoded.Rewards==2 and session.ResultRewardReceipt['CURRENCY:gold'].Amount==10)
assert(encoded.Entry==8 and encoded.Context==12)
local continued=0; local grants=0
session.ContinueConfirmedResult=function(self) continued=continued+1; self.ResultReady=false end
_RunManagerLogic.GrantBattleResultRelic=function(self,p,id,sequence,key)
 grants=grants+1; return inventory:GrantBattleRelic(id,key)
end
session:RequestConfirmResultReward(7,12,'r2'); assert(grants==0)
session:RequestConfirmResultReward(8,11,'r2'); assert(grants==0)
senderUserId='intruder';session:RequestConfirmResultReward(8,12,'r2');assert(grants==0)
senderUserId='owner';session:RequestConfirmResultReward(8,12,'not-offered');assert(grants==0 and continued==0)
session:RequestContinueResult();assert(continued==0)
session:RequestConfirmResultReward(8,12,'r2'); assert(grants==1 and continued==1)
assert(inventory:GetSnapshotAmount(inventory.RunItemSnapshot,'r2')==1)
session:RequestConfirmResultReward(8,12,'r3');assert(grants==1)
session.ResultReady=true;session:RequestConfirmResultReward(8,12,'r3');assert(grants==1 and continued==2)
assert(inventory:GetSnapshotAmount(inventory.RunItemSnapshot,'r3')==0)
assert(inventory:GrantBattleRelic('r2','battle-relic:3:stage01:8').Success)
assert(inventory:GetSnapshotAmount(inventory.RunItemSnapshot,'r2')==1)
assert(not inventory:GrantBattleRelic('r2','other-key').Success)
session.ResultOffersPrepared=false;session.BattleResult='Defeat';session:PrepareResultRelics();assert(#session.ResultRelicOffers==0)
session.ResultOffersPrepared=false;session.BattleResult='Victory';session.UnionRewardRunEnded=true
session:PrepareResultRelics();assert(#session.ResultRelicOffers==0)
session:PublishResultRewardSnapshot();assert(encoded.Relics==nil and #encoded.Rewards==2)
session.StageType='NORMAL';session.ResultReady=true;session.ResultSelectedRelicId='';session.UnionRewardRunEnded=false
session:RequestConfirmResultReward(8,12,'');assert(continued==3 and grants==1)
session.StageType='BOSS'
session.ResultOffersPrepared=false;session.UnionRewardRunEnded=false; inventory.RunItemSnapshot='r1~1|r2~1|r3~1|r4~1'
session:PrepareResultRelics();assert(#session.ResultRelicOffers==1)
session.ResultOffersPrepared=false;inventory.RunItemSnapshot=inventory.RunItemSnapshot..'|r5~1'
session:PrepareResultRelics();assert(#session.ResultRelicOffers==0)
''')
print('PASS server: boss-only offers (NORMAL/ELITE excluded), frozen distinct offers, ownership filtering, 0/1/3 candidates, receipt totals, sender/context validation, duplicate clicks, transfer retry, terminal/defeat exclusion')

lua.execute('''
Vector2=function(x,y) return {x=x,y=y} end
Color=function(r,g,b,a) return {r=r,g=g,b=b,a=a} end
nodes={}; local baseY={ResultText=340,Divider=270,RewardsTitle=217,RewardsEmpty=132,RewardPages=217,FooterDivider=-305,FooterStats=-363,BtnReset=-363,Status=-285}
_EntityService={GetEntityByPath=function(self,path)
 if nodes[path]==nil then
  local name=path:match('([^/]+)$')
  nodes[path]={Enable=true,SetEnable=function(self,v) self.Enable=v end,
   UITransformComponent={anchoredPosition={x=0,y=baseY[name] or 0},RectSize={x=0,y=0}},
   TextGUIRendererComponent={},SpriteGUIRendererComponent={},ButtonComponent={}}
 end
 return nodes[path]
end}
hud={_T={},ResultPanelEntity={UITransformComponent={}},ResetButton={},ResetButtonText={}}
session.Entity={Id='map'};session.ResultRewardSnapshot='one';session.ResultSelectedRelicId='';session.ResultReady=true
session.StageTurnNumber=8;session.ResultKillCount=6;session.ResultRewardError='';session.BattleResult='Victory';session.UnionRewardRunEnded=false
receipt={Entry=8,Context=12,Rewards={{Name='Coins',Amount=5,Icon='coin'}},Relics={{Id='r2',Name='Relic',Icon='relic',Description='effect'}}}
_HttpService.JSONDecode=function() return receipt end
_BattleHudPresenterLogic={GetBattleSession=function() return session end}
''')
install('BattleQueueHudComponent.mlua','hud',['GetResultView','SetResultLabel','SetResultNodeVisible','RenderResultRewards','SelectResultRelic'])
lua.execute('''
hud:RenderResultRewards(session);assert(not hud.ResetButton.Enable)
hud:SelectResultRelic(1);assert(hud.ResetButton.Enable and hud._T.ResultChoice=='r2')
assert(hud:GetResultView('Relic1/Selected').Enable)
receipt.Relics=nil;session.ResultRewardSnapshot='two';hud:RenderResultRewards(session)
assert(hud.ResultPanelEntity.UITransformComponent.RectSize.y==500)
assert(hud:GetResultView('Reward1').UITransformComponent.RectSize.x==520)
assert(hud:GetResultView('Reward1').UITransformComponent.anchoredPosition.x==-324)
assert(hud:GetResultView('Reward1/Icon').SpriteGUIRendererComponent.Color.a==1)
assert(hud:GetResultView('ResultText').UITransformComponent.anchoredPosition.y==160)
hud:RenderResultRewards(session);assert(hud:GetResultView('ResultText').UITransformComponent.anchoredPosition.y==160)
receipt.Relics={{Id='r2',Name='Relic',Icon='relic',Description='effect'}};session.ResultRewardSnapshot='three';hud:RenderResultRewards(session)
assert(hud.ResultPanelEntity.UITransformComponent.RectSize.y==860)
assert(hud:GetResultView('ResultText').UITransformComponent.anchoredPosition.y==340)
session.EntryRequestId=9;hud:RenderResultRewards(session);assert(not hud.ResetButton.Enable and hud._T.ResultChoice=='')
session.EntryRequestId=8;receipt.Rewards={};for i=1,10 do receipt.Rewards[i]={Name='Reward '..i,Amount=i,Icon=''} end
session.ResultRewardSnapshot='four';hud:RenderResultRewards(session);hud._T.RewardPage=4;hud:RenderResultRewards(session)
assert(hud:GetResultView('Reward1/Name').TextGUIRendererComponent.Text=='Reward 10')
assert(not hud:GetResultView('Reward3').Enable)
assert(hud:GetResultView('FooterStats/TurnValue').TextGUIRendererComponent.Text=='8')
assert(hud:GetResultView('FooterStats/KillValue').TextGUIRendererComponent.Text=='6')
''')
print('PASS client: choose/confirm gate, selected state, compact/full layout without drift, stale snapshot rejection, receipt pagination')
print('Maker runtime: NOT RUN')
