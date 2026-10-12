local p=_RunManagerLogic._T.NormalVerifyPlayer
local run=p:GetComponent("script.PlayerRunStateComponent")
local sequence=run.RunSequence
local seen={}
log("[FlowVerify] ROUTE_DAMAGE_STARTED sequence="..sequence)
for tick=1,3600 do
 if run.RunSequence~=sequence or run.RunState=="Completed" or run.RunState=="Failed" then break end
 if p.CurrentMap.Name=="kerning_city_battle" then log("[FlowVerify] M_UPPER_DAMAGE_STOP") break end
 local s=isvalid(p.CurrentMap) and p.CurrentMap:GetComponent("script.BattleSessionComponent") or nil
 if s~=nil and s.PlayerEntity==p and s.StageId~="" and s.BattleResult=="" and s.ContentValidationState=="VALID" and s.TurnState~=nil and s.TurnState.BattlePhase=="PlayerTurn" and not s.TurnState.IsActionProcessing then
  if not seen[s.EntryRequestId] then seen[s.EntryRequestId]=true log("[FlowVerify] ROUTE_BATTLE map="..p.CurrentMap.Name.." stage="..s.StageId.." entry="..s.EntryRequestId.." playerBody="..tostring(isvalid(p.RigidbodyComponent))) end
  for _,e in ipairs(s.BoardState:CollectLivingEnemies()) do
   if isvalid(e) then
    local u=e:GetComponent("script.BattleUnitComponent")
    if u~=nil and not u.IsDead then local hit=s:ApplyDamage("player_01",u.UnitId,100000,"FLOW_VERIFICATION_DAMAGE") assert(hit.Success,hit.Reason) end
   end
  end
 end
 wait(0.25)
end
log("[FlowVerify] ROUTE_DAMAGE_DONE sequence="..sequence.." state="..run.RunState)