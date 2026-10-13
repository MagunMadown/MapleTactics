local root=_EntityService:GetEntityByPath("/ui/DefaultGroup")
local m=isvalid(root) and root:GetComponent("script.MinimapUI") or nil
assert(m~=nil,"MINIMAP_MISSING")
local names={"KerningCityBranchBtn","ElliniaBranchBtn"}
local oldMode,oldRoute=m.CurrentMode,m.SelectedRouteId
for _,name in ipairs(names) do
 local e=_EntityService:GetEntityByPath("/ui/PopupGroup/MapTeleportPopup/"..name)
 local c=isvalid(e) and e:GetComponent("script.WorldMapFutureRegionButtonComponent") or nil
 assert(c~=nil and e.ButtonComponent~=nil,"REGION_BUTTON_MISSING")
 local oldPending,oldEnable=c.RequestPending,e.ButtonComponent.Enable
 m.CurrentMode="POST_SHOP_ROUTE"; m.SelectedRouteId=c.RequiredRouteId
 c.RequestPending=false; e.ButtonComponent.Enable=false
 c:HandleEntryResult(false,"UNSOLICITED_TEST")
 assert(not c.RequestPending and not e.ButtonComponent.Enable and m.SelectedRouteId==c.RequiredRouteId,"UNSOLICITED_REPLY_CHANGED_STATE")
 c.RequestPending=true; m.SelectedRouteId=c.RequiredRouteId=="shop_upper" and "shop_lower" or "shop_upper"
 local other=m.SelectedRouteId
 c:HandleEntryResult(false,"STALE_ROUTE_TEST")
 assert(c.RequestPending and not e.ButtonComponent.Enable and m.SelectedRouteId==other,"STALE_ROUTE_REPLY_CHANGED_STATE")
 m.SelectedRouteId=c.RequiredRouteId; m.CurrentMode="SHOP_CHOICE"
 c:HandleEntryResult(false,"STALE_SCREEN_TEST")
 assert(c.RequestPending and not e.ButtonComponent.Enable and m.CurrentMode=="SHOP_CHOICE","STALE_SCREEN_REPLY_CHANGED_STATE")
 m.CurrentMode="POST_SHOP_ROUTE"
 c:HandleEntryResult(false,"VALID_REJECTION_TEST")
 assert(not c.RequestPending and e.ButtonComponent.Enable and m.CurrentMode=="POST_SHOP_ROUTE" and m.SelectedRouteId==c.RequiredRouteId,"VALID_REJECTION_NOT_RETRYABLE")
 c:HandleEntryResult(false,"DUPLICATE_TEST")
 assert(not c.RequestPending and e.ButtonComponent.Enable and m.SelectedRouteId==c.RequiredRouteId,"DUPLICATE_REPLY_CHANGED_ROUTE")
 c.RequestPending=oldPending; e.ButtonComponent.Enable=oldEnable
 log("[CommitVerify] ROUTE_GUARD_PASS button="..name.." cases=5 route="..c.RequiredRouteId)
end
m:CloseWorldMap("COMMIT_VERIFY_RESTORE")
m.CurrentMode=oldMode; m.SelectedRouteId=oldRoute
log("[CommitVerify] ROUTE_UI_RESTORED mode="..m.CurrentMode)