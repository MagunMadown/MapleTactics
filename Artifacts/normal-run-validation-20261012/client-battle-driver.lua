local p = _UserService.LocalPlayer
local acted, lastGuardTurn, lastMap = 0, -1, ""
log("[NormalVerify] DRIVER_STARTED")
for tick = 1, 2400 do
    if not isvalid(p) or not isvalid(p.CurrentMap) then wait(0.2) else
        local map = p.CurrentMap
        if map.Name ~= lastMap then
            lastMap = map.Name
            lastGuardTurn = -1
            log("[NormalVerify] DRIVER_MAP " .. map.Name)
        end
        if map.Name == "new_skill_stage" then
            if not _NewSkillSelectionUILogic.Loading and not _NewSkillSelectionUILogic.SelectionPending
                and _NewSkillSelectionUILogic.Offers ~= nil and _NewSkillSelectionUILogic.Offers[1] ~= nil then
                _NewSkillSelectionUILogic:SelectChoice(1)
            end
        elseif map.Name == "upgrade_skill_stage" then
            local controller = _EntityService:GetEntityByPath("/ui/UpgradeSkillStageUI")
            local ui = isvalid(controller) and controller:GetComponent("script.UpgradeSkillStageUIComponent") or nil
            if ui ~= nil then ui:OnSkipClicked() end
        else
            local s = map:GetComponent("script.BattleSessionComponent")
            if s ~= nil then
                if s.BattleResult ~= "" then
                    if s.StageId == "henesys_stage_04" or s.BattleResult == "Defeat" then
                        log("[NormalVerify] DRIVER_STOP stage="..s.StageId.." result="..s.BattleResult.." turn="..s.TurnNumber.." commands="..acted)
                        break
                    end
                    if s.ResultReady then s:RequestContinueResult() end
                else
                    local ui = s:GetBattleUiState()
                    local u = p:GetComponent("script.BattleUnitComponent")
                    if ui.Success and ui.Phase == "PlayerTurn" and not ui.IsProcessing and u ~= nil
                        and not _BattleHudPresenterLogic:IsLocalInputBlocked() then
                        local nearest, distance = nil, 999
                        for _, enemy in ipairs(map:GetChildComponentsByTypeName("script.BattleUnitComponent", true)) do
                            if enemy.Team == "Enemy" and not enemy.IsDead and enemy.CurrentHp > 0 then
                                local d = math.abs(enemy.CellIndex - u.CellIndex)
                                if d < distance then nearest, distance = enemy, d end
                            end
                        end
                        if nearest ~= nil then
                            local direction = nearest.CellIndex > u.CellIndex and 1 or -1
                            local facing = u.Facing == "Right" and 1 or -1
                            if u.CurrentHp <= 4 and string.find(ui.RunInventory.ConsumableSnapshot, "orange_potion~", 1, true) ~= nil then
                                s:SubmitConsumableUse("orange_potion", "")
                            elseif ui.PlayerQueue.Count > 0 and ui.Commands.CanExecute then
                                _BattleHudPresenterLogic:RequestExecuteQueue()
                            elseif distance > 1 and ui.Commands.CanMove then
                                _BattleHudPresenterLogic:SubmitLocalCommand("MOVE", "", direction)
                            elseif facing ~= direction and ui.Commands.CanTurn then
                                _BattleHudPresenterLogic:SubmitLocalCommand("TURN", "", 0)
                            elseif s.UtilityRemainingCooldown == 0 and lastGuardTurn ~= s.TurnNumber then
                                lastGuardTurn = s.TurnNumber
                                _BattleHudPresenterLogic:SubmitLocalCommand("UTILITY", "", 0)
                            else
                                local cooldowns = {}
                                for id, value in string.gmatch(ui.CooldownSnapshot, "([^|:]+):([^|]+)") do cooldowns[id]=tonumber(value) or 0 end
                                local selected = ""
                                for _, id in ipairs({"divine_swing","brandish"}) do
                                    if (cooldowns[id] or 0) == 0 and string.find("|"..s.SkillSlotIds.."|", "|"..id.."|", 1, true) ~= nil then selected=id break end
                                end
                                if selected ~= "" and ui.Commands.CanQueue then _BattleHudPresenterLogic:RequestQueueTile(selected)
                                elseif ui.Commands.CanTurn then _BattleHudPresenterLogic:SubmitLocalCommand("TURN", "", 0) end
                            end
                            acted = acted + 1
                            if acted % 20 == 0 then log("[NormalVerify] DRIVER_PROGRESS stage="..s.StageId.." turn="..s.TurnNumber.." hp="..u.CurrentHp.." commands="..acted) end
                        end
                    end
                end
            end
        end
        wait(0.35)
    end
end
log("[NormalVerify] DRIVER_DONE")