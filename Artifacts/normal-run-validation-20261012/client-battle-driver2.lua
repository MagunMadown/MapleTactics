local ranges={brandish=1,divine_swing=2,spear_pulling=3,brave_slash=2,divine_charge=2,la_mancha_spear=3,flash_slash=2,aura_blade=3,page_order=2}
local p=_UserService.LocalPlayer
local commands,lastGuardTurn,lastMap=0,-1,""
log("[NormalVerify] DRIVER2_STARTED")
for tick=1,2400 do
    if isvalid(p) and isvalid(p.CurrentMap) then
        local map=p.CurrentMap
        if map.Name~=lastMap then lastMap=map.Name lastGuardTurn=-1 log("[NormalVerify] DRIVER2_MAP "..map.Name) end
        if map.Name=="new_skill_stage" then
            if not _NewSkillSelectionUILogic.Loading and not _NewSkillSelectionUILogic.SelectionPending and _NewSkillSelectionUILogic.Offers~=nil then
                local choice,best=1,0
                for i,offer in ipairs(_NewSkillSelectionUILogic.Offers) do local rank=ranges[offer.SkillId] or 0 if rank>best then choice,best=i,rank end end
                if _NewSkillSelectionUILogic.Offers[choice]~=nil then _NewSkillSelectionUILogic:SelectChoice(choice) end
            end
        elseif map.Name=="upgrade_skill_stage" then
            local e=_EntityService:GetEntityByPath("/ui/UpgradeSkillStageUI")
            local c=isvalid(e) and e:GetComponent("script.UpgradeSkillStageUIComponent") or nil
            if c~=nil then c:OnSkipClicked() end
        else
            local s=map:GetComponent("script.BattleSessionComponent")
            if s~=nil then
                if s.BattleResult~="" then
                    if s.StageId=="henesys_stage_04" or s.BattleResult=="Defeat" then
                        log("[NormalVerify] DRIVER2_STOP stage="..s.StageId.." result="..s.BattleResult.." turns="..s.TurnNumber.." commands="..commands)
                        break
                    elseif s.ResultReady then s:RequestContinueResult() end
                else
                    local ui=s:GetBattleUiState()
                    local u=p:GetComponent("script.BattleUnitComponent")
                    if ui.Success and ui.Phase=="PlayerTurn" and not ui.IsProcessing and u~=nil and not _BattleHudPresenterLogic:IsLocalInputBlocked() then
                        local enemies=map:GetChildComponentsByTypeName("script.BattleUnitComponent",true)
                        local target,distance=nil,999
                        for _,enemy in ipairs(enemies) do if enemy.Team=="Enemy" and not enemy.IsDead and enemy.CurrentHp>0 then
                            local d=math.abs(enemy.CellIndex-u.CellIndex)
                            if d<distance then target,distance=enemy,d end
                        end end
                        if target~=nil then
                            local direction=target.CellIndex>u.CellIndex and 1 or -1
                            local facing=u.Facing=="Right" and 1 or -1
                            local cooldowns={}
                            for id,n in string.gmatch(ui.CooldownSnapshot,"([^|:]+):([^|]+)") do cooldowns[id]=tonumber(n) or 0 end
                            local selected,reach="",0
                            for id in string.gmatch(s.SkillSlotIds,"([^|]+)") do
                                if ranges[id]~=nil and (cooldowns[id] or 0)==0 and ranges[id]>=distance and ranges[id]>reach then selected,reach=id,ranges[id] end
                            end
                            local queued=ui.PlayerQueue.Items[1]
                            local queuedReach=queued~=nil and (ranges[queued.SkillId] or 1) or 0
                            if u.CurrentHp<=4 and string.find(ui.RunInventory.ConsumableSnapshot,"orange_potion~",1,true)~=nil then s:SubmitConsumableUse("orange_potion","")
                            elseif facing~=direction and ui.Commands.CanTurn then _BattleHudPresenterLogic:SubmitLocalCommand("TURN","",0)
                            elseif queued~=nil and distance<=queuedReach and ui.Commands.CanExecute then _BattleHudPresenterLogic:RequestExecuteQueue()
                            elseif (queued~=nil and distance>queuedReach or queued==nil and selected=="" and distance>1) and ui.Commands.CanMove then _BattleHudPresenterLogic:SubmitLocalCommand("MOVE","",direction)
                            elseif s.UtilityRemainingCooldown==0 and lastGuardTurn~=s.TurnNumber then lastGuardTurn=s.TurnNumber _BattleHudPresenterLogic:SubmitLocalCommand("UTILITY","",0)
                            elseif selected~="" and ui.Commands.CanQueue then _BattleHudPresenterLogic:RequestQueueTile(selected)
                            elseif ui.Commands.CanTurn then _BattleHudPresenterLogic:SubmitLocalCommand("TURN","",0) end
                            commands=commands+1
                            if commands%20==0 then log("[NormalVerify] DRIVER2_PROGRESS stage="..s.StageId.." turn="..s.TurnNumber.." hp="..u.CurrentHp.." commands="..commands) end
                        end
                    end
                end
            end
        end
    end
    wait(0.35)
end
log("[NormalVerify] DRIVER2_DONE")