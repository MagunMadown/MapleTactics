"""Shogun inventory integration: actual mLua bodies, mocked native engine/RPC only."""
from consumables_test import ROOT, base, lua, load, rows
import csv

def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

before = csv_rows(ROOT / 'Artifacts/tests/fixtures/EnemyDropDefinitions-before-shogun.csv')
after = csv_rows(ROOT / base / '03_Data/EnemyDropDefinitions.csv')
assert len(before) == len(after) == 14
replacements = {'early_potion': 'red_potion', 'region_01_mushmom_potion': 'white_potion', 'region_kerning_dyle_potion': 'white_potion'}
for original, current in zip(before, after):
    expected = dict(original)
    expected['DropRefId'] = replacements.get(original['DropEntryId'], original['DropRefId'])
    assert current == expected, (original, current)
assert sum(r['DropType'] == 'CONSUMABLE' for r in after) == 6
assert {r['DropRefId'] for r in after if r['DropType']=='CONSUMABLE'} == {'red_potion','orange_potion','white_potion'}
print('PASS P: all 14 rows preserve IDs, triggers, chances, amount ranges and order; only 3 potion references changed')

datasets = {'ConsumableDefinitions': rows, 'EnemyDropDefinitions': after}
lua.globals().datasets = lua.table_from({name: lua.table_from([lua.table_from(r) for r in values]) for name, values in datasets.items()})
lua.execute('''_DataService={GetTable=function(self,name)
 local values=datasets[name]; if not values then return nil end
 return {GetRowCount=function() return #values end,GetCell=function(self,i,k) return values[i][k] end}
end}''')
drop_repo = load(base + '03_Data/Repositories/EnemyDropDefinitionRepositoryLogic.mlua')
drop_repo.DataSetName = 'EnemyDropDefinitions'
drop_repo.SupportedSchemaVersion = 1
drop_repo.AllowPrototypeCompatibilityFallback = False
lua.globals()._EnemyDropDefinitionRepositoryLogic = drop_repo
lua.globals().DropMethods = load(base + '01_Combat/Components/Shared/BattleDropComponent.mlua')
lua.globals().PresentationMethods = load(base + '01_Combat/Components/Shared/BattleDropPresentationComponent.mlua')
lua.globals().DropValidator = load(base + '03_Data/Repositories/EnemyDropContentValidatorLogic.mlua')
lua.globals()._RunManagerLogic.GrantRunReward = load(base + '04_Roguelike/RunManager/RunManagerLogic.mlua', {'GrantRunReward'}).GrantRunReward
enemies = csv_rows(ROOT / base / '03_Data/EnemyDefinitions.csv')
lua.globals().references = lua.table_from({
    'ENEMY_DEFINITION': lua.table_from({r['EnemyDefinitionId']: True for r in enemies}),
    'CONSUMABLE': lua.table_from({r['ConsumableId']: True for r in rows}),
    'RUN_CURRENCY': lua.table_from({'gold': True}),
})
lua.execute('''
_ContentReferenceResolverLogic={ResolveReference=function(self,kind,id)
 return {Success=references[kind]~=nil and references[kind][id]==true,Reason="REFERENCE_NOT_FOUND"}
end}
_ContentValidatorLogic={ValidateEnemyDrops=function() return DropValidator:ValidateAll() end}
Vector3=function(x,y,z) return {x=x,y=y,z=z} end
EaseType={QuadEaseInOut="quad"}
_SpawnService={SpawnByModelId=function(self,id,name,position,parent)
 assert(parent==map, "Drop must spawn under the actual map")
 return {Name=name,SpriteRendererComponent={},TweenFloatingComponent={RestartFromCurrentPosition=function() end}}
end}
_EntityService={Destroy=function(self,entity) entity.destroyed=true end}
function dropFixture()
 uiFixture()
 _RunManagerLogic.MesoCurrencyId="gold"
 _RunManagerLogic.GetOrCreateRunUnionEffectState=function() return {
   IsInitialized=true,ActiveRunSequence=run.RunSequence,MesoGainRate=0,CalculateMesoReward=function(self,n) return n end}
 end
 presentation=object(PresentationMethods,{Entity=map,DropModelId="battledroppickup",CurrencySpriteRuid="gold-icon",
 ConsumableSpriteRuid="fallback-icon",CellStartX=-2.8,CellSpacing=1.12,UnitY=0.12,DropHeightOffset=0.42,
 FloatAmplitude=0.12,FloatCycleTime=0.9,SpawnSequence=0,SpawnedDropEntities={}})
 drops=object(DropMethods,{Entity=map,Presentation=presentation,PendingDropSnapshot="",PendingDropCount=0,DropRevision=0,ProcessedKillKeys=""})
end
function refreshHud() hud:OnUpdate(0.016); hud:OnUpdate(0.016) end
function slotCount() local n=0; for _,slot in ipairs(hud.Slots) do if slot.Enable and slot.children.Icon.Enable then n=n+1 end end; return n end
''')

cases = {
 'A/B/C: base 3, Union +1=4/+2=5 and clamp; duplicate kinds occupy all five slots': '''
 for bonus=0,2 do
  uiFixture(); inv:ResetForRun(1,bonus); grant("red_potion",5); refreshHud()
  assert(inv.ConsumableCapacity==3+bonus and #hud.Slots==3+bonus and slotCount()==3+bonus)
  assert(inv:GetSnapshotTotal(inv.RunConsumableSnapshot)==3+bonus)
 end
 inv:ResetForRun(2,99); assert(inv.ConsumableCapacity==5)
 inv:ResetForRun(3,-1); assert(inv.ConsumableCapacity==3)
 ''',
 'D: red/red/orange uses three individual icons in one horizontal row': '''
 uiFixture(); grant("red_potion",2); grant("orange_potion",1); refreshHud()
 assert(slotCount()==3 and hud._T.SlotItems[1].ConsumableId=="red_potion" and hud._T.SlotItems[2].ConsumableId=="red_potion" and hud._T.SlotItems[3].ConsumableId=="orange_potion")
 for i=1,3 do assert(hud.Slots[i].UITransformComponent.anchoredPosition.x==(i-1)*80 and hud.Slots[i].UITransformComponent.anchoredPosition.y==0) end
 hud.Slots[3].state({state=ButtonState.Hover}); assert(string.find(hud.MessageText.Text,"주황 포션",1,true))
 ''',
 'E/M: seeded enemy death -> ground icon -> cell pickup -> HUD; duplicate death/reward ignored': '''
 dropFixture(); local seed=nil
 for candidate=0,100 do
  local r=_EnemyDropDefinitionRepositoryLogic:ResolveDrops("early_mushroom","ANY_KILL",candidate,"stage1",1,"mushroom",1,0)
  for _,entry in ipairs(r.Drops) do if entry.DropRefId=="red_potion" then seed=candidate end end
  if seed then break end
 end
 assert(seed~=nil)
 local r=drops:ResolveEnemyDeath(seed,"stage1",1,"early_mushroom","mushroom",1,2,"ANY_KILL",0)
 assert(r.Success and r.AddedCount==2 and drops.PendingDropCount==2 and presentation:GetVisibleDropCount()==2)
 local potionKey="stage1:1:1:mushroom:early_potion"
 local entity=presentation.SpawnedDropEntities[potionKey]
 assert(entity.SpriteRendererComponent.SpriteRUID==rows[1].IconKey)
 assert(drops:ResolveEnemyDeath(seed,"stage1",1,"early_mushroom","mushroom",1,2,"ANY_KILL",0).AddedCount==0)
 assert(drops:CollectAtCell(player,"battle1",1).CollectedCount==0)
 assert(drops:CollectAtCell(player,"battle1",2).CollectedCount==2)
 refreshHud(); assert(slotCount()==1 and hud._T.SlotItems[1].ConsumableId=="red_potion")
 assert(drops.PendingDropCount==0 and presentation:GetVisibleDropCount()==0 and entity.destroyed)
 local revision=inv.InventoryRevision; local money=inv.RunCurrencySnapshot
 assert(drops:CollectAtCell(player,"battle1",2).CollectedCount==0)
 assert(_RunManagerLogic:GrantRunReward(player,"CONSUMABLE","red_potion",1,"battle1:drop:"..potionKey).Reason=="DUPLICATE_REWARD_IGNORED")
 assert(inv.InventoryRevision==revision and inv.RunCurrencySnapshot==money and slotCount()==1)
 ''',
 'F: full pickup -> exactly one gold, ground removed, slots unchanged': '''
 dropFixture(); grant("red_potion",3); refreshHud()
 drops:AddPendingDrop("full","CONSUMABLE","white_potion",1,2)
 local entity=presentation.SpawnedDropEntities.full
 assert(drops:CollectAtCell(player,"battle1",2).Success)
 refreshHud(); assert(slotCount()==3 and inv.RunCurrencySnapshot=="gold~1" and inv.RunConsumableSnapshot=="red_potion~3")
 assert(entity.destroyed and drops.PendingDropCount==0 and presentation:GetVisibleDropCount()==0)
 ''',
 'G/H/I: HUD click heal/clamp/full rejection with no turn or failed-use mutation': '''
 uiFixture(); grant("red_potion",1); grant("white_potion",1); refreshHud()
 hud:ClickSlot(1); assert(unit.CurrentHp==7); refreshHud(); assert(slotCount()==1)
 unit.CurrentHp=8; refreshHud(); hud:ClickSlot(1); assert(unit.CurrentHp==10); unchangedTurn()
 grant("red_potion",1); refreshHud(); local revision=inv.InventoryRevision; local requests=session.ConsumableRequestSequence
 hud:ClickSlot(1); assert(inv.InventoryRevision==revision and session.ConsumableRequestSequence==requests)
 assert(slotCount()==1 and string.find(hud.MessageText.Text,"HP가 가득",1,true)); unchangedTurn()
 ''',
 'J/K/L: sand target/cancel and unavailable all cure keep inventory and guard': '''
 uiFixture(); grant("time_sand",2); grant("all_cure_potion",1); cd:StartCooldown("brandish",3); refreshHud()
 hud:ClickSlot(1); assert(hud.Selector.Enable); local before=inv.RunConsumableSnapshot
 hud.CancelButton.click(); assert(not hud.Selector.Enable and inv.RunConsumableSnapshot==before)
 hud:ClickSlot(1); hud:ClickSkill(1); assert(cd:GetRemainingCooldown("brandish")==1); refreshHud()
 before=inv.RunConsumableSnapshot; hud:ClickSlot(2); assert(inv.RunConsumableSnapshot==before and unit.UtilityGuardActive)
 unchangedTurn()
 ''',
 'N/O: victory autocollect fills last slot, converts surplus and replay cannot grant twice': '''
 dropFixture(); grant("red_potion",2)
 drops:AddPendingDrop("victory1","CONSUMABLE","orange_potion",2,1)
 drops:AddPendingDrop("victory2","CONSUMABLE","white_potion",1,2)
 local entity=presentation.SpawnedDropEntities.victory1
 local pending=drops.PendingDropSnapshot
 assert(drops:AutoCollectAll(player,"battle1").CollectedCount==2); refreshHud()
 assert(slotCount()==3 and inv.RunCurrencySnapshot=="gold~2" and entity.destroyed and presentation:GetVisibleDropCount()==0)
 local revision=inv.InventoryRevision
 drops.PendingDropSnapshot=pending; drops.PendingDropCount=2
 assert(drops:AutoCollectAll(player,"battle1").Success)
 assert(inv.InventoryRevision==revision and inv.RunCurrencySnapshot=="gold~2" and drops.PendingDropCount==0)
 ''',
 'Restored legacy overflow normalizes once; stage entry and Union capacity refresh': '''
 uiFixture(); inv.RunConsumableSnapshot="potion_hp_small~2|red_potion~3"; refreshHud(); refreshHud()
 assert(slotCount()==3 and inv.RunCurrencySnapshot=="gold~2")
 local revision=inv.InventoryRevision; inv:NormalizeLegacyConsumables(); assert(inv.InventoryRevision==revision and inv.RunCurrencySnapshot=="gold~2")
 inv.ConsumableCapacity=4; refreshHud(); assert(hud.Slots[4].Enable and not hud.Slots[4].children.Icon.Enable)
 session.EntryRequestId=8; refreshHud(); assert(hud.Panel.Enable and slotCount()==3 and hud.SelectedConsumableId=="")
 inv.ConsumableCapacity=5; refreshHud(); assert(hud.Slots[5].Enable)
 inv:ResetForRun(2,0); refreshHud(); assert(hud.Slots[3].Enable and not hud.Slots[4].Enable and not hud.Slots[5].Enable and slotCount()==0)
 ''',
 'All five ground icons distinct; only unknown resource uses placeholder': '''
 dropFixture(); local seen={}
 for _,row in ipairs(rows) do
  local r=presentation:ShowDrop(row.ConsumableId,"CONSUMABLE",row.ConsumableId,1,1)
  assert(r.Success and r.Entity.SpriteRendererComponent.SpriteRUID==row.IconKey and not seen[row.IconKey]); seen[row.IconKey]=true
 end
 assert(presentation:GetVisibleDropCount()==5)
 assert(presentation:ResolveSpriteRuid("CONSUMABLE","missing")=="fallback-icon")
 assert(DropValidator:ValidateAll().ValidatedCount==14)
 ''',
}
for name, code in cases.items():
    try:
        lua.execute(code)
        print('PASS', name)
    except Exception:
        print('FAIL', name)
        raise
print(f'{len(cases)+1}/{len(cases)+1} Shogun offline integration cases passed. Native Maker runtime: NOT RUN.')
