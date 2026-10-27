"""Exercise Orbis shop flow using production Lua methods; native/player boundaries are doubles."""
import runpy
from pathlib import Path
ns = runpy.run_path(str(Path(__file__).with_name("verify-runtime.py")))
lua, load = ns["lua"], ns["load"]
for name in ["NodeDefinitionRepositoryLogic", "NodeContentValidatorLogic", "ShopNodeBindingRepositoryLogic", "ShopDefinitionRepositoryLogic", "StageTransitionManagerLogic", "RunShopLogic", "PlayerRunShopStateComponent"]:
    load(name)
lua.execute('''
local graph=_ContentValidatorLogic:ValidateNodeGraph('orbis_run')
assert(graph.Success and graph.NodeCount==33)
for _,stage in ipairs({3,10}) do
  local id=string.format('orbis_stage_%02d',stage)
  local flow=_NodeDefinitionRepositoryLogic:ResolveBattleOutcome('','',id,'Victory')
  assert(flow.Success and flow.NodeGraphId=='orbis_run' and flow.NextContentTypes=='REST')
  local route=_StageTransitionManagerLogic:ResolveGraphTransition(id)
  assert(route.Success and route.Reason=='REWARD_THEN_SHOP' and route.NextShopMapId=='shop')
  local rest=_NodeDefinitionRepositoryLogic:ResolveContentCompletion('orbis_run',route.RewardNodeId)
  assert(rest.Success and rest.NextContentTypes=='SHOP' and rest.NextContentIds=='shop_relic')
  local departure=_NodeDefinitionRepositoryLogic:ResolveContentCompletion('orbis_run',rest.NextNodeIds)
  assert(departure.Success and departure.NextContentTypes=='BATTLE')
  assert(departure.NextContentIds==string.format('orbis_stage_%02d',stage+1))
end
for _,stage in ipairs({2,7,9,14,15}) do
  local route=_StageTransitionManagerLogic:ResolveGraphTransition(string.format('orbis_stage_%02d',stage))
  assert(route.Success and route.NextBattleStageId==string.format('orbis_stage_%02d',stage+1))
end
assert(_ContentValidatorLogic:ValidateNodeGraph('prototype_run').Success)
local service=_RunShopLogic
local visit=_PlayerRunShopStateComponent
visit.ShopRevision=0
local run,player,notified,transfers,selections,closed,failTransfer
local function reset(graphId,nodeId,map)
  visit:ResetForRun(9)
  visit:Open(9,'shop_relic',nodeId,'shop','visit:'..nodeId,'')
  run={RunSequence=9,CurrentNodeGraphId=graphId,RunState='Active',RunFlowState='AWAITING_SHOP',
    SelectedContentId='shop_relic',SelectedContentType='SHOP',SelectedNodeId=nodeId,RunFlowRevision=1,LastContentCompletionKey=''}
  player={CurrentMap={Name=map}}
  transfers=0;selections=0;closed=0;notified=nil;failTransfer=false
end
_UserService={GetUserEntityByUserId=function(_,id) assert(id=='owner');return player end}
senderUserId='owner'
service.GetOrCreateShopState=function() return visit end
service.NotifyCloseShopResult=function(_,ok,reason,owner) assert(owner=='owner');notified={ok=ok,reason=reason} end
_RunManagerLogic={GetOrCreateRunState=function() return run end,
  CompleteCurrentContent=function(_,p,kind,request)
    assert(p==player and kind=='SHOP')
    local flow=_NodeDefinitionRepositoryLogic:ResolveContentCompletion(run.CurrentNodeGraphId,visit.ActiveNodeId)
    assert(flow.Success)
    closed=closed+1;run.LastContentCompletionKey='9:'..request;run.AvailableNodeIds=flow.NextNodeIds
    run.RunFlowState=flow.FlowState;run.RunFlowRevision=run.RunFlowRevision+1
    return {Success=true,Reason='OK',RunFlowState=run.RunFlowState,RunState='Active',AvailableNodeIds=flow.NextNodeIds}
  end,
  SelectNextContent=function(_,p,id,request)
    selections=selections+1
    assert(p==player and id==run.AvailableNodeIds)
    local next=_NodeDefinitionRepositoryLogic:GetNodeDefinition(run.CurrentNodeGraphId,id)
    run.SelectedNodeId=id;run.SelectedContentId=next.StageId;run.SelectedContentType=next.NodeType;run.AvailableNodeIds=""
    return {Success=true}
  end}
_RunContentMapTransitionAdapterLogic={ConsumeSelectedBattle=function(_,p)
  assert(p==player);transfers=transfers+1
  return {Success=not failTransfer,Reason=failTransfer and 'TEST_TRANSFER_FAILED' or 'TRANSFER_REQUESTED'}
end}
for _,case in ipairs({{'orbis_run','orbis_shop_after_stage03','shop','orbis_stage_04'},
  {'orbis_run','orbis_shop_after_stage10','shop','orbis_stage_11'},
  {'prototype_run','shop_sleepywood_balrog','sleepywood_shop','region_06_stage_08'}}) do
  reset(case[1],case[2],case[3])
  service:RequestCloseShop(501)
  assert(notified and notified.ok and run.SelectedContentId==case[4])
  assert(closed==1 and transfers==1 and selections==1 and visit.ShopState=='CLOSED')
  service:RequestCloseShop(501)
  assert(notified.ok and notified.reason=='DUPLICATE_CONTENT_COMPLETION_IGNORED')
  assert(closed==1 and transfers==1 and selections==1)
  reset(case[1],case[2],'lobby')
  service:RequestCloseShop(502)
  assert(notified.ok==false and notified.reason=='SHOP_MAP_REQUIRED' and closed==0 and transfers==0)
  reset(case[1],case[2],case[3]);failTransfer=true
  service:RequestCloseShop(503)
  assert(notified.ok==false and visit.ShopState=='CLOSED' and closed==1 and transfers==1)
  failTransfer=false;service:RequestCloseShop(504)
  assert(notified.ok and closed==1 and transfers==2 and selections==1,'retry must not recomplete or reselect')
end
reset('prototype_run','shop_upper','shop')
service:RequestCloseShop(505)
assert(closed==1 and transfers==0 and selections==0 and notified==nil,'cross-region world map behavior preserved')
''')
print('PASS Orbis shop graphs/reward chains, direct 4/11/Balrog departure, no-purchase close, owner/map guard, duplicate idempotence, failed-transfer retry, cross-region regression')

import json
report = {"result":"PASS","scope":"Actual Lua graph/reward-chain and shop request methods; player/native boundaries use doubles","graphs":["orbis_run","prototype_run"],"directDepartureStages":["orbis_stage_04","orbis_stage_11","region_06_stage_08"],"cases":["existing reward chain retained","no-purchase departure","wrong shop map rejected","same request does not dispatch twice","failed transfer retries without completing again","regional world map departure retained"],"maker":"Tracked separately in shops-maker-verification.json"}
Path(__file__).with_name("shops-lua-verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
