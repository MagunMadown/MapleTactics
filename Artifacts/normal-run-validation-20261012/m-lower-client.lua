local p=_UserService.LocalPlayer
local root=_EntityService:GetEntityByPath("/ui/PopupGroup/MapTeleportPopup")
local m=_EntityService:GetEntityByPath("/ui/DefaultGroup"):GetComponent("script.MinimapUI")
local shopUi=_EntityService:GetEntityByPath("/ui/RunShopUI"):GetComponent("script.RunShopUIComponent")
local run=p:GetComponent("script.PlayerRunStateComponent")
local sequence=run.RunSequence
local continued,selected,departed,opened={},{},{},{}
local lastMap=""
log("[FlowVerify] ROUTE_UI_STARTED sequence="..sequence)
for tick=1,3600 do
 if run.RunSequence~=sequence then break end
 local map=p.CurrentMap
 local flow=_RunManagerLogic:GetLocalRunFlowUiState()
 if map.Name~=lastMap then lastMap=map.Name log("[FlowVerify] ROUTE_MAP "..map.Name) end
 if map.Name=="lobby" and (run.RunState=="Completed" or run.RunState=="Failed") then
  wait(2)
  log("[FlowVerify] ROUTE_FINAL_RECORD "..p:GetComponent("script.PlayerRunResultComponent").LatestResultJson)
  break
 elseif map.Name=="new_skill_stage" then
  if string.find(run.RewardSelectionContext or "", "|UPGRADE", 1, true)~=nil then
   local group=_EntityService:GetEntityByPath("/ui/UpgradeSkillStageUI")
   local upgrade=isvalid(group) and (group:GetComponent("script.UpgradeSkillStageUIComponent") or group:GetFirstChildComponentByTypeName("script.UpgradeSkillStageUIComponent",true)) or nil
   if upgrade~=nil and upgrade._T.UpgradeStateReady and not upgrade.ApplyLocked and isvalid(upgrade.SkipButton) then
    upgrade.SkipButton.Entity:SendEvent(ButtonClickEvent(upgrade.SkipButton.Entity))
    log("[FlowVerify] ROUTE_UPGRADE_SKIPPED context="..run.RewardSelectionContext)
   end
  elseif not _NewSkillSelectionUILogic.Loading and not _NewSkillSelectionUILogic.SelectionPending and _NewSkillSelectionUILogic.Offers~=nil and _NewSkillSelectionUILogic.Offers[1]~=nil then _NewSkillSelectionUILogic:SelectChoice(1) end
 elseif map.Name=="shop" or map.Name=="sleepywood_shop" then
  local shop=_RunShopLogic:GetLocalShopUiState()
  local key=shop.NodeId..":"..shop.VisitSequence
  if shop.ShopState=="OPEN" and not opened[key] then opened[key]=true shopUi:OpenUi() log("[FlowVerify] ROUTE_SHOP_OPEN node="..shop.NodeId.." visit="..shop.VisitSequence.." run="..shop.RunSequence.." gold="..shop.CurrencySnapshot.." purchased="..shop.PurchasedOfferIds) end
  if shop.ShopState=="OPEN" and sequence==1 and shop.VisitSequence>1 and shopUi._T.VerificationBoughtRef==nil then
   local first=string.match(shop.OfferSnapshot,"^([^~]+)~")
   if shopUi.Offers[1]~=nil and shopUi.Offers[1].OfferId==first then
    local gold=tonumber(string.match(shop.CurrencySnapshot,"gold~(%d+)")) or 0
    for index,offer in ipairs(shopUi.Offers) do
     if offer.RewardType=="ITEM" and offer.Price<=gold then
      local row=shopUi:GetEntity("ShopPopup/ListFrame/ListScroll/OfferRow"..index)
      assert(isvalid(row))
      row:SendEvent(ButtonClickEvent(row)) row:SendEvent(ButtonClickEvent(row))
      wait(1)
      local after=_RunShopLogic:GetLocalShopUiState()
      assert(after.LastPurchase.Success and string.find(after.ItemSnapshot,offer.RewardRefId.."~1",1,true)~=nil)
      shopUi._T.VerificationBoughtRef=offer.RewardRefId
      log("[FlowVerify] FINAL_SOURCE_PURCHASE_PASS node="..shop.NodeId.." ref="..offer.RewardRefId.." gold="..after.CurrencySnapshot)
      break
     end
    end
   end
   if shopUi._T.VerificationBoughtRef==nil then wait(0.35) end
  end
  if shop.ShopState=="OPEN" and not departed[key] and (sequence~=1 or shop.VisitSequence==1 or shopUi._T.VerificationBoughtRef~=nil) then
   departed[key]=true
   local exit=_EntityService:GetEntityByPath("/ui/ShopDepartureUI/Controller"):GetComponent("script.ShopExitButtonComponent")
   if isvalid(exit.DepartureButton) then exit.DepartureButton.Entity:SendEvent(ButtonClickEvent(exit.DepartureButton.Entity)) end
  elseif shop.ShopState=="CLOSED" and m.CurrentMode=="POST_SHOP_ROUTE" and m.SelectedRouteId==shop.NodeId and not selected[key] then
   if shop.NodeId=="shop_lower" then
    assert(shop.VisitSequence==1 and shop.PurchasedOfferIds=="")
    assert(string.find("|"..flow.AvailableNodeIds.."|","|ellinia_stage01_battle|",1,true)~=nil)
    assert(string.find("|"..flow.AvailableNodeIds.."|","|kerning_stage01_battle|",1,true)==nil)
    local inactive=root:GetChildByName("KerningCityBranchBtn",true):GetComponent("script.WorldMapFutureRegionButtonComponent")
    assert(inactive.RequestPending)
    log("[FlowVerify] STALE_PENDING_PRECONDITION_PASS oldRoute="..inactive.RequiredRouteId.." currentRoute="..m.SelectedRouteId)
    local mode,route=m.CurrentMode,m.SelectedRouteId
    _RunManagerLogic:RequestSelectNextContent("kerning_stage01_battle",910003)
    wait(0.8)
    assert(m.CurrentMode==mode and m.SelectedRouteId==route and route=="shop_lower")
    log("[FlowVerify] LOWER_LOCK_REJECTION_PASS route="..route.." available="..flow.AvailableNodeIds)
   end
   for _,button in ipairs(root:GetChildComponentsByTypeName("script.WorldMapFutureRegionButtonComponent",true)) do
    if button.RequiredRouteId==shop.NodeId and string.find("|"..flow.AvailableNodeIds.."|","|"..button.TargetNodeId.."|",1,true)~=nil then
     selected[key]=true button.Entity:SendEvent(ButtonClickEvent(button.Entity)) log("[FlowVerify] ROUTE_REGION_BUTTON node="..button.TargetNodeId.." route="..shop.NodeId) break
    end
   end
  end
 else
  local s=map:GetComponent("script.BattleSessionComponent")
  if s~=nil and s.BattleResult~="" and s.ResultReady and not continued[s.EntryRequestId] then
   continued[s.EntryRequestId]=true s:RequestContinueResult()
  end
  if flow.Commands.CanSelectNode and m.CurrentMode=="SHOP_CHOICE" then
   local target=string.find("|"..flow.AvailableNodeIds.."|","|shop_lower|",1,true)~=nil and "shop_lower" or string.match(flow.AvailableNodeIds,"^([^|]+)")
   local key="choice:"..flow.CurrentNodeId
   if not selected[key] then
    for _,button in ipairs(root:GetChildComponentsByTypeName("script.WorldMapRunNodeButtonComponent",true)) do
     if button.NodeId==target then selected[key]=true button.Entity:SendEvent(ButtonClickEvent(button.Entity)) log("[FlowVerify] ROUTE_SHOP_BUTTON node="..target) break end
    end
   end
  end
 end
 wait(0.35)
end
log("[FlowVerify] ROUTE_UI_DONE sequence="..sequence.." state="..run.RunState)