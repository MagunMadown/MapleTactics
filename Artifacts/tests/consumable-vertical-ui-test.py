"""A-I UI regression scenarios using actual HUD Lua and mocked engine events."""
from consumables_shogun_test import lua

lua.execute('''
uiFixture()
local loads=0
_ResourceService.LoadSpriteAndWait=function(self,ruid)
 loads=loads+1
 return {IsLoadComplete=true,Width=ruid=="wide" and 48 or 24,Height=32}
end
local icon=uiEntity(false)
hud:ApplyItemIcon(icon,"tall")
assert(icon.UITransformComponent.RectSize.x==39 and icon.UITransformComponent.RectSize.y==52)
hud:ApplyItemIcon(icon,"wide")
assert(icon.UITransformComponent.RectSize.x==52)
assert(math.abs(icon.UITransformComponent.RectSize.y-52*32/48)<0.00001)
hud:ApplyItemIcon(icon,"tall")
assert(loads==2 and icon.UITransformComponent.RectSize.x==39)
assert(icon.UITransformComponent.anchoredPosition.x==0 and icon.UITransformComponent.anchoredPosition.y==0)
assert(icon.SpriteGUIRendererComponent.LocalPosition.x==0 and icon.SpriteGUIRendererComponent.LocalPosition.y==0)
assert(icon.SpriteGUIRendererComponent.PreserveSprite==0 and icon.UITransformComponent.sibling==2)
''')
print('PASS: portrait/landscape aspect fit, reused slot image switch, cached metadata and foreground order (mock native API)')

cases = {
    'A: three empty independent slots without text or tooltip': '''
uiFixture(); refreshHud()
assert(#hud.Slots==3 and slotCount()==0 and not hud.MessageText.Entity.Enable)
for i=1,3 do
 assert(hud.Slots[i].Enable and hud.Slots[i].TextGUIRendererComponent.Text=="")
 assert(hud.Slots[i].ButtonComponent.Transition==TransitionType.None)
 assert(hud.Slots[i].SpriteGUIRendererComponent.Color[4]==0)
 assert(hud.Slots[i].SpriteGUIRendererComponent.ImageRUID=="98c34caab88ee34459cb3e5807ac4219")
 assert(hud.Slots[i].children.SlotSkin.SpriteGUIRendererComponent.ImageRUID=="65061d6a2e7642ab916b51bac9c6933b")
 assert(hud.Slots[i].UITransformComponent.anchoredPosition.x==(i-1)*80)
 assert(hud.Slots[i].UITransformComponent.anchoredPosition.y==0 and hud.Slots[i].UITransformComponent.anchoredPosition.x==(i-1)*80)
end
hud.Slots[1].state({state=ButtonState.Hover}); assert(not hud.MessageText.Entity.Enable)
''',
    'B: red orange white icons in horizontal order': '''
uiFixture(); grant("red_potion",1); grant("orange_potion",1); grant("white_potion",1); refreshHud()
for i,id in ipairs({"red_potion","orange_potion","white_potion"}) do
 assert(hud._T.SlotItems[i].ConsumableId==id)
 assert(hud.Slots[i].children.Icon.SpriteGUIRendererComponent.ImageRUID==_ConsumableDefinitionRepositoryLogic:GetDefinition(id).IconKey)
end
''',
    'C: duplicate red icons and empty third slot': '''
uiFixture(); grant("red_potion",2); refreshHud()
assert(slotCount()==2 and not hud.Slots[3].children.Icon.Enable)
assert(hud.Slots[1].children.Icon.SpriteGUIRendererComponent.ImageRUID==hud.Slots[2].children.Icon.SpriteGUIRendererComponent.ImageRUID)
''',
    'D: fourth slot expands right without moving first three': '''
inv.BaseConsumableCapacity=4; inv.ConsumableCapacity=4; refreshHud()
assert(#hud.Slots==4 and hud.Panel.UITransformComponent.RectSize.x==312)
for i=1,4 do assert(hud.Slots[i].UITransformComponent.anchoredPosition.y==0 and hud.Slots[i].UITransformComponent.anchoredPosition.x==(i-1)*80) end
''',
    'E: fifth slot expands right and locks disappear on reset': '''
inv.BaseConsumableCapacity=5; inv.ConsumableCapacity=5; refreshHud()
assert(#hud.Slots==5 and hud.Panel.UITransformComponent.RectSize.x==392)
for i=1,5 do assert(hud.Slots[i].UITransformComponent.anchoredPosition.y==0 and hud.Slots[i].UITransformComponent.anchoredPosition.x==(i-1)*80) end
inv:ResetForRun(2,0); refreshHud()
assert(hud.Slots[3].Enable and not hud.Slots[4].Enable and not hud.Slots[5].Enable)
''',
    'F: right tooltip only on hover; immediate exit and empty hover hide': '''
uiFixture(); grant("red_potion",2); refreshHud()
hud:DescribeSlot(1); assert(not hud.MessageText.Entity.Enable)
hud.Slots[2].state({state=ButtonState.Hover})
assert(hud.MessageText.Entity.Enable and string.find(hud.MessageText.Text,"빨간 포션",1,true))
assert(hud.MessageText.Entity.UITransformComponent.anchoredPosition.x==164 and hud.MessageText.Entity.UITransformComponent.anchoredPosition.y==12)
hud.Slots[1].state({state=ButtonState.Normal}); assert(hud.MessageText.Entity.Enable)
hud.Slots[2].state({state=ButtonState.Normal}); assert(not hud.MessageText.Entity.Enable)
hud.Slots[1].state({state=ButtonState.Hover}); hud.Slots[3].state({state=ButtonState.Hover})
assert(not hud.MessageText.Entity.Enable)
''',
    'G: full HP dimmed; hover reason; click preserves item': '''
uiFixture(); grant("red_potion",1); unit.CurrentHp=unit.MaxHp; refreshHud()
assert(hud.Slots[1].children.Icon.SpriteGUIRendererComponent.Color[1]==0.7)
hud.Slots[1].state({state=ButtonState.Hover}); assert(hud.MessageText.Entity.Enable)
assert(string.find(hud.MessageText.Text,"HP가 가득",1,true))
local before=inv.RunConsumableSnapshot; hud.Slots[1].click(); assert(inv.RunConsumableSnapshot==before)
hud.Slots[1].state({state=ButtonState.Normal}); assert(not hud.MessageText.Entity.Enable)
''',
    'H: click heals, refreshes occupied slots and preserves turn': '''
uiFixture(); grant("red_potion",1); refreshHud()
hud.Slots[1].click(); refreshHud()
assert(unit.CurrentHp==7 and slotCount()==0 and not hud.MessageText.Entity.Enable)
unchangedTurn()
''',
    'I: sand popup right of selected slot, compact rows, cancel and use': '''
uiFixture(); inv:ResetForRun(1,2); grant("red_potion",4); grant("time_sand",1)
inv.RunSkillSnapshot="brandish~1|slash~1"
cd:StartCooldown("brandish",3); refreshHud()
hud.Slots[5].state({state=ButtonState.Hover}); hud.Slots[5].click()
assert(hud.Selector.Enable and not hud.MessageText.Entity.Enable)
assert(hud.Selector.UITransformComponent.anchoredPosition.x==436 and hud.Selector.UITransformComponent.anchoredPosition.y==268)
assert(hud.Selector.UITransformComponent.RectSize.x==304 and hud.Selector.UITransformComponent.RectSize.y==132)
local before=inv.RunConsumableSnapshot; hud.CancelButton.click()
assert(not hud.Selector.Enable and inv.RunConsumableSnapshot==before)
hud.Slots[5].click(); hud.SkillRows[1].click(); refreshHud()
assert(cd:GetRemainingCooldown("brandish")==1 and slotCount()==4 and not hud.Selector.Enable)
unchangedTurn()
''',
}
for name, code in cases.items():
    try:
        lua.execute(code)
        print('PASS', name)
    except Exception:
        print('FAIL', name)
        raise
print('9/9 horizontal HUD scenarios passed offline. Maker render/input: NOT RUN.')
