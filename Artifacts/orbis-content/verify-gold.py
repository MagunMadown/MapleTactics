"""Verify the approved opening budget and execute production shop offer selection."""
import json
import runpy
from pathlib import Path
ns = runpy.run_path(str(Path(__file__).with_name("verify-shops.py")))
lua, load = ns["lua"], ns["load"]
load("StageRewardDefinitionRepositoryLogic")
load("RunShopLogic")
load("PlayerRunShopStateComponent")
lua.execute('''
local rewards=_StageRewardDefinitionRepositoryLogic
local budget=0
for i=1,16 do
  local r=rewards:GetRewardsForStage(string.format('orbis_stage_%02d',i))
  assert(r.Success and #r.Entries>=1)
  for _,entry in ipairs(r.Entries) do
    assert(entry.RewardType=='CURRENCY' and entry.RewardRefId=='gold' and entry.Amount>0)
    if i<=3 then budget=budget+entry.Amount end
  end
end
assert(budget==39)
local service=_RunShopLogic
local bundle=_ShopDefinitionRepositoryLogic:GetShopBundle('shop_relic')
assert(bundle.Success)
local cheapest=math.huge
local defs={}
for _,e in ipairs(bundle.Entries) do
  cheapest=math.min(cheapest,e.PriceAmount)
  defs[e.RewardRefId]={DisplayName=e.DisplayName,AttackBonus=0,MaxHpBonus=0,DefenseBonus=0,EffectDescription=''}
end
assert(cheapest==35 and budget>=cheapest)
local run,visit,relics,draws,seed,owned,pools
local inventory={ActiveRunSequence=9}
local player={}
_RunManagerLogic={GetOrCreateRunState=function() return run end,GetOrCreateRunInventory=function() return inventory end}
service.GetOrCreateShopState=function() return visit end
service.GetOrCreateRelicEffects=function() return relics end
service.BuildPotionOffers=function() return {Success=true,Entries={}} end
service.CaptureSellCatalog=function() end
service.CaptureSkillSellCatalog=function() end
local sourceVisit=_PlayerRunShopStateComponent
for _,node in ipairs({'orbis_shop_after_stage03','orbis_shop_after_stage10','shop_upper'}) do
  for value=0,127 do
    seed=value;draws=0;owned={};pools={}
    -- Vary starting ownership and prior purchases without introducing ineligible offers.
    if value%2==1 then owned[bundle.Entries[1].RewardRefId]=true end
    visit=setmetatable({ShopRevision=0},{__index=sourceVisit})
    visit:ResetForRun(9)
    run={RunSequence=9,RunFlowState='AWAITING_SHOP',ContentTransitionState='READY',SelectedContentType='SHOP',
      SelectedContentId='shop_relic',SelectedNodeId=node,LastContentSelectionKey='9:'..value}
    relics={IsInitialized=true,ActiveRunSequence=9,ShopBundle=bundle,Definitions=defs,
      CanAcquireRelic=function(_,id) return not owned[id] end,
      SelectRelicIndex=function(_,ids)
        draws=draws+1;pools[draws]=#ids
        return #ids>0 and ((seed+draws)%#ids+1) or 0
      end}
    local opened=service:OpenShop(player,'shop_relic')
    assert(opened.Success and draws==3)
    local count=0
    for _,offer in pairs(visit.OfferedEntries) do count=count+1;assert(not owned[offer.RewardRefId]) end
    assert(count==3)
    if node=='orbis_shop_after_stage03' then
      assert(visit.OfferedEntry.PriceAmount==cheapest and visit.OfferedEntry.PriceAmount<=budget)
    else
      local expected=#bundle.Entries-(owned[bundle.Entries[1].RewardRefId] and 1 or 0)
      assert(pools[1]==expected,'other shops must retain the full weighted pool')
    end
    local snapshot=visit.OfferSnapshot
    assert(service:OpenShop(player,'shop_relic').Success and draws==3 and visit.OfferSnapshot==snapshot,'reopen must not reroll')
  end
end
''')
report={"result":"PASS","firstShopBaseGold":39,"initialSupport":20,"cheapestRelic":35,"offerCases":384,
        "scope":"Actual reward repository and shop offer methods; RNG/player boundaries are doubles",
        "checks":["16 stages have positive gold rewards","first slot affordable with opening budget","distinct eligible relics",
                  "non-opening shops retain full weighted pool","same visit does not reroll"],
        "maker":"Tracked separately in gold-maker-verification.json"}
Path(__file__).with_name("gold-lua-verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print(json.dumps(report,ensure_ascii=False))
