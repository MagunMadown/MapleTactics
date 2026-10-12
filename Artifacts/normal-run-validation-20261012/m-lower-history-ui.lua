local p=_UserService.LocalPlayer
assert(p.CurrentMap.Name=="lobby")
local group=_EntityService:GetEntityByPath("/ui/RunHistoryUI")
local ui=group:GetComponent("script.RunHistoryUIComponent") or group:GetFirstChildComponentByTypeName("script.RunHistoryUIComponent",true)
assert(ui~=nil)
ui:SetOpen(true)
for tick=1,50 do if ui._T.Record~=nil then break end wait(0.2) end
local row=ui:Find("Recent/Row1")
assert(isvalid(row))
row:SendEvent(ButtonClickEvent(row))
for tick=1,50 do if ui._T.Record~=nil and ui._T.Record.RunId==ui.SelectedRunId then break end wait(0.2) end
local r=ui._T.Record
assert(r~=nil and r.SchemaVersion==3 and r.ClearedBattleCount==20 and r.EndReason=="COMPLETED")
local latest=_HttpService:JSONDecode(p:GetComponent("script.PlayerRunResultComponent").LatestResultJson)
assert(r.RunId==latest.RunId and r.RunSequence==3)
assert(r.Conditions.Captured and r.Conditions.ObservedStart and r.Conditions.DifficultyId=="NORMAL" and r.Conditions.AccountProgressionMode=="ACCOUNT_APPLIED")
local clearSum,turnSum,hitSum=0,0,0
for _,v in ipairs(r.RegionHistory.Visits) do clearSum=clearSum+v.ClearedBattles turnSum=turnSum+v.ConsumedTurns hitSum=hitSum+v.HitsTaken end
assert(clearSum==r.ClearedBattleCount and turnSum==r.ConsumedTurns and hitSum==r.HitsTaken)
assert(r.RegionHistory.Captured and r.RegionHistory.Complete and #r.RegionHistory.Visits==4)
local expected={"henesys","ellinia","region_05","region_06"}
for i,v in ipairs(r.RegionHistory.Visits) do assert(v.RegionId==expected[i] and v.Completed and v.ClearedBattles==(i==4 and 8 or 4)) end
assert(ui:Find("Detail/Stats/Clears/Value").TextGUIRendererComponent.Text=="20")
ui:Find("TabRegions"):SendEvent(ButtonClickEvent(ui:Find("TabRegions")))
assert(ui.ActiveTab=="Regions" and #ui:GetBuildRows()==4)
for i=1,3 do assert(ui:Find("Build/Row"..i.."/Status/Label").TextGUIRendererComponent.Text=="완료") end
log("[FlowVerify] HISTORY_REGIONS_PASS run="..r.RunId.." route="..ui:Find("RegionRoute").TextGUIRendererComponent.Text)
ui:Find("BuildNext"):SendEvent(ButtonClickEvent(ui:Find("BuildNext")))
local last=r.RegionHistory.Visits[4]
local description="전투 "..ui:FormatNumber(last.ClearedBattles).."회 클리어 · "..ui:FormatNumber(last.ConsumedTurns).."턴 · 피격 "..ui:FormatNumber(last.HitsTaken).."회"
assert(ui.BuildPage==2 and ui:Find("Build/Row1/Description").TextGUIRendererComponent.Text==description)
log("[FlowVerify] HISTORY_STATS_PASS "..description)
for _,tab in ipairs({"Skills","Relics","Augments","Regions"}) do
 local b=ui:Find("Tab"..tab) b:SendEvent(ButtonClickEvent(b))
 assert(ui.ActiveTab==tab and ui.BuildPage==1)
 local isRegion=tab=="Regions"
 assert(ui:Find("Build/Row1/Status").Enable==isRegion)
 log("[FlowVerify] HISTORY_TAB_PASS tab="..tab.." rows="..#ui:GetBuildRows().." badge="..tostring(ui:Find("Build/Row1/Status").Enable))
end
log("[FlowVerify] HISTORY_UI_DONE run="..r.RunId.." clears="..ui:Find("Detail/Stats/Clears/Value").TextGUIRendererComponent.Text)
ui:SetOpen(false)