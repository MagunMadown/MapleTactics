"""Offline regression tests: execute actual mLua method bodies in Lua 5.4.

Engine services, entities, and RPC transport are mocks. This is not Maker build/play validation.
Run with Python and lupa installed, or set LUPA_PATH to a local lupa installation.
"""
import csv
import os
from pathlib import Path
import re
import sys

if os.environ.get('LUPA_PATH'):
    sys.path.insert(0, os.environ['LUPA_PATH'])
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute('log=function(...) end; log_warning=log; log_error=log; isvalid=function(x) return x~=nil and not x.destroyed end')

def load(path, names=None):
    text = (ROOT / path).read_text(encoding='utf-8-sig')
    obj = lua.table()
    found = set()
    for m in re.finditer(r'^([ \t]+)method\s+\w+\s+(\w+)\((.*?)\)\n(.*?)^\1end', text, re.M | re.S):
        _, name, params, body = m.groups()
        if names is not None and name not in names:
            continue
        args = ','.join(p.strip().split()[-1] for p in params.split(',') if p.strip())
        obj[name] = lua.execute('return function(self' + (',' + args if args else '') + ')\n' + body + '\nend')
        found.add(name)
    if names is not None:
        assert set(names) <= found, (path, set(names) - found)
    # Component defaults are supplied by Maker; reproduce scalar defaults in isolated fixtures.
    for name, value in re.findall(r'^\s*(?:@Sync\s+)?property\s+(?:integer|number|boolean|string)\s+(\w+)\s*=\s*(.+)$', text, re.M):
        obj[name] = lua.eval(value.strip())
    return obj

base = 'RootDesk/MyDesk/'
repo = load(base + '03_Data/Repositories/ConsumableDefinitionRepositoryLogic.mlua')
repo.DataSetName = 'ConsumableDefinitions'
repo.SupportedSchemaVersion = 1
rows = list(csv.DictReader((ROOT / base / '03_Data/ConsumableDefinitions.csv').open(encoding='utf-8-sig')))
assert len(rows) == 5
lua.globals().rows = lua.table_from([lua.table_from(row) for row in rows])
lua.execute('_DataService={GetTable=function() return {GetRowCount=function() return #rows end,GetCell=function(self,i,k) return rows[i][k] end} end}')
lua.globals()._ConsumableDefinitionRepositoryLogic = repo
lua.globals()._TutorialRulesLogic = load(base + '00_Core/Lobby/Tutorial/TutorialRulesLogic.mlua', {'IsGuided','IsCommandAllowed','OnConsumableUsed'})
lua.globals().InventoryMethods = load(base + '04_Roguelike/RunManager/PlayerRunInventoryComponent.mlua')
lua.globals().CooldownMethods = load(base + '01_Combat/Components/Shared/SkillRuntimeStateComponent.mlua')
lua.globals().UnitMethods = load(base + '01_Combat/Components/Shared/BattleUnitComponent.mlua', {'ApplyHealing', 'SyncRunHp', 'RemoveNegativeStatusEffects'})
lua.globals().SessionMethods = load(base + '01_Combat/Components/Shared/BattleSessionComponent.mlua', {
    'IsTutorialCommandAllowed', 'TryUseRunConsumable', 'BuildConsumableHudState', 'SubmitConsumableUse', 'RequestUseConsumable',
    'ReceiveConsumableUseResult', 'RequestConsumableHudState', 'ReceiveConsumableHudState'})
lua.globals().HudMethods = load(base + '02_UI/BattleConsumableHudComponent.mlua')
lua.globals()._ConsumableHealEffectLogic = load(base + '01_Combat/Resolvers/ConsumableHealEffectLogic.mlua')
lua.globals()._ConsumableEffectRouterLogic = load(base + '01_Combat/Resolvers/ConsumableEffectRouterLogic.mlua')
lua.globals()._RunManagerLogic = load(base + '04_Roguelike/RunManager/RunManagerLogic.mlua', {'CanUseRunConsumable', 'ConsumeRunConsumable'})

lua.execute('''
function object(methods, values)
    values = values or {}
    values._T = values._T or {}
    for k,v in pairs(methods) do if values[k]==nil then values[k]=v end end
    return values
end
function fixture()
    map={Id="map-id"}
    player={Name="player", PlayerComponent={UserId="owner"}, CurrentMap=map}
    inv=object(InventoryMethods, {Entity=player, ActiveRunSequence=1, ConsumableCapacity=3, BaseConsumableCapacity=3, RelicConsumableSlotBonus=0,
        RunConsumableSnapshot="", RunCurrencySnapshot="", RunSkillSnapshot="brandish~1|slash~1", RunItemSnapshot="",
        AppliedUseKeys="", AppliedRewardKeys="", AppliedPurchaseKeys="", InventoryRevision=1,
        SkillInventoryRevision=1, RunSkillBarRevision=0, RunSkillBarSlotIds="", OverflowCurrencyPerItem=1, OverflowCurrencyId="gold"})
    cd=object(CooldownMethods,{Entity=player,RemainingCooldowns={},CooldownSnapshot="",CooldownRevision=0})
    run={RunSequence=1,SetRunHp=function(self,current,max) self.CurrentHp=current; self.MaxHp=max end}
    unit=object(UnitMethods,{Entity=player,CurrentHp=5,MaxHp=10,IsDead=false,Team="Player",UtilityGuardActive=true})
    player.GetComponent=function(self,name)
        return ({["script.PlayerRunInventoryComponent"]=inv,["script.SkillRuntimeStateComponent"]=cd,
          ["script.BattleUnitComponent"]=unit,["script.PlayerRunStateComponent"]=run})[name]
    end
    session=object(SessionMethods,{Entity=map,PlayerEntity=player,EntryRequestId=7,StageId="stage1",ContentValidationState="VALID",
        BattleResult="",BattlePhase="PlayerTurn",IsActionProcessing=false,TurnState={BattlePhase="PlayerTurn",IsActionProcessing=false,QueuedTileIds="slash",TurnNumber=3},
        ConsumableRequestSequence=0,_T={}})
    session.FindUnitEntity=function() return player end
    session.BeginEnemyTurnFromPlayerAction=function() error("Consumable advanced enemy turn") end
    _RunManagerLogic.GetOrCreateRunState=function() return run end
    _RunManagerLogic.GetOrCreateRunInventory=function() return inv end
    _SkillDefinitionRepositoryLogic={GetSkillDefinition=function(self,id) return {DisplayName=id,Success=true} end}
    _UserService={LocalPlayer=player}
    request=0
end
function grant(id,amount)
    local r=inv:GrantRunReward("CONSUMABLE",id,amount,"reward:"..id..":"..tostring(inv.InventoryRevision))
    assert(r.Success,r.Reason)
    return r
end
function use(id,skill,revision,entry)
    request=request+1
    return session:TryUseRunConsumable(player,id,request,skill or "",entry or 7,revision or inv.InventoryRevision)
end
function unchangedTurn()
    assert(session.TurnState.BattlePhase=="PlayerTurn")
    assert(session.TurnState.TurnNumber==3 and session.TurnState.QueuedTileIds=="slash")
end
function uiEntity(withChildren)
    local entity={Enable=true,Id="mock",Path="/mock/Icon",Parent={Path="/mock"},UITransformComponent={},ButtonComponent={},TextGUIRendererComponent={},SpriteGUIRendererComponent={},children={}}
    if withChildren then
        entity.children.Icon=uiEntity(false)
        entity.children.SlotSkin=uiEntity(false)
        entity.children.Count=uiEntity(false)
        entity.children.Hotkey=uiEntity(false)
        entity.children.Discard=uiEntity(false)
    end
    entity.GetChildByName=function(self,key) return self.children[key] end
    entity.Clone=function() return uiEntity(withChildren) end
    entity.ConnectEvent=function(self,event,callback) self[event]=callback; return callback end
    entity.DisconnectEvent=function(self,event) self[event]=nil end
    entity.Destroy=function(self) self.destroyed=true end
    return entity
end
function uiFixture()
    _GameSettingsLogic={PlayUISound=function() end,IsInputBlocked=function() return false end}
    _TutorialPresentationLogic={ResetHudHighlights=function() end,GetRevisionToken=function() return "" end,UpdateConsumableHighlight=function() end}
    ImageType={Simple=0}; PreserveSpriteType={None=0}
    Vector3=function(x,y,z) return {x=x,y=y,z=z} end
    _UILogic={SetSiblingIndex=function(self,t,i) t.sibling=i end,GetSiblingIndex=function(self,t) return t.sibling end}
    _ResourceService={LoadSpriteAndWait=function(self,ruid) return {IsLoadComplete=true,Width=24,Height=32} end}
    fixture()
    senderUserId="owner"
    _BattleHudPresenterLogic={GetBattleSession=function() return session end}
    _SoundService={PlaySound=function() end}
    Color=function(...) return {...} end
    DataRef=function(s) return s end
    Vector2=function(x,y) return {x=x,y=y} end
    ButtonClickEvent="click"
    ButtonStateChangeEvent="state"; ButtonState={Normal=0,Hover=1}
    TransitionType={None=0,ColorTint=1,SpriteSwap=2}
    hud=object(HudMethods,{Panel=uiEntity(),Selector=uiEntity(),SlotTemplate=uiEntity(true),SkillTemplate=uiEntity(),
        CancelButton=uiEntity(),PreviousButton=uiEntity(),NextButton=uiEntity(),MessageText={},Columns=3,SkillsPerPage=4,
        EventLinks={},Slots={},SkillRows={},IconSizes={},RefreshElapsed=0,QueryId=0,SkillPage=1,SelectedConsumableId="",_T={}})
    hud.MessageText.Entity=uiEntity()
    hud.MessageText.GetPreferredHeight=function() return 52 end
    hud:OnBeginPlay()
end
''')

cases = {
    'Potion Heal + consume + turn + run HP': '''fixture(); grant("red_potion",2); local r=use("red_potion"); assert(r.Success and unit.CurrentHp==7 and r.ConsumedAmount==1); assert(inv:GetSnapshotAmount(inv.RunConsumableSnapshot,"red_potion")==1); assert(run.CurrentHp==7); unchangedTurn()''',
    'Orange data value': '''fixture(); grant("orange_potion",1); assert(use("orange_potion").Success and unit.CurrentHp==8); unchangedTurn()''',
    'White MaxHP clamp': '''fixture(); grant("white_potion",1); unit.CurrentHp=8; local r=use("white_potion"); assert(r.Success and unit.CurrentHp==10 and r.AppliedAmount==2); unchangedTurn()''',
    'Full HP / dead rejects without consume': '''fixture(); grant("white_potion",2); unit.CurrentHp=10; local before=inv.RunConsumableSnapshot; assert(not use("white_potion").Success); assert(inv.RunConsumableSnapshot==before); unit.IsDead=true; unit.CurrentHp=0; assert(not use("white_potion").Success and inv.RunConsumableSnapshot==before)''',
    'Time Sand 3 -> 1 + untouched other cooldown': '''fixture(); grant("time_sand",2); cd:StartCooldown("brandish",3); cd:StartCooldown("slash",4); local rev=cd.CooldownRevision; local r=use("time_sand","brandish"); assert(r.Success and cd:GetRemainingCooldown("brandish")==1 and cd:GetRemainingCooldown("slash")==4); assert(cd.CooldownRevision==rev+1 and r.ConsumedAmount==1); unchangedTurn()''',
    'Time Sand 1 -> 0 clamp / snapshot': '''fixture(); grant("time_sand",1); cd:StartCooldown("brandish",1); assert(use("time_sand","brandish").Success); assert(cd:GetRemainingCooldown("brandish")==0 and cd.CooldownSnapshot==""); unchangedTurn()''',
    'Time Sand invalid targets / all ready': '''fixture(); grant("time_sand",3); local before=inv.RunConsumableSnapshot; for _,skill in ipairs({"", "brandish", "foreign"}) do assert(not use("time_sand",skill).Success) end; cd:StartCooldown("foreign",3); assert(not use("time_sand","foreign").Success); assert(inv.RunConsumableSnapshot==before); local d=session:BuildConsumableHudState(); assert(#d.Skills==0 and not d.Items[1].Usable)''',
    'Time Sand target list only owned cooling skills': '''fixture(); grant("time_sand",1); cd:StartCooldown("brandish",3); cd:StartCooldown("foreign",3); local d=session:BuildConsumableHudState(); assert(#d.Skills==1 and d.Skills[1].SkillId=="brandish" and d.Items[1].Usable)''',
    'All Cure no statuses / guard buff retained': '''fixture(); grant("all_cure_potion",1); local before=inv.RunConsumableSnapshot; local r=use("all_cure_potion"); assert(not r.Success and r.Reason=="NO_NEGATIVE_STATUS_EFFECTS"); assert(inv.RunConsumableSnapshot==before and unit.UtilityGuardActive); unchangedTurn()''',
    'All Cure future interface contract (mock provider only)': '''fixture(); grant("all_cure_potion",1); unit.RemoveNegativeStatusEffects=function(self) return {Success=true,AppliedAmount=2,Reason="CLEANSED"} end; local r=use("all_cure_potion"); assert(r.Success and r.ConsumedAmount==1 and unit.UtilityGuardActive); unchangedTurn()''',
    'All Cure zero removals rejects even success flag': '''fixture(); grant("all_cure_potion",1); unit.RemoveNegativeStatusEffects=function() return {Success=true,AppliedAmount=0} end; assert(not use("all_cure_potion").Success); assert(inv:GetSnapshotAmount(inv.RunConsumableSnapshot,"all_cure_potion")==1)''',
    'Duplicate successful request has no second effect': '''fixture(); grant("red_potion",3); local revision=inv.InventoryRevision; local r=use("red_potion"); local hp=unit.CurrentHp; local snapshot=inv.RunConsumableSnapshot; local r2=session:TryUseRunConsumable(player,"red_potion",request,"",7,revision); assert(r2.Success and r2.Reason=="DUPLICATE_USE_IGNORED"); assert(unit.CurrentHp==hp and inv.RunConsumableSnapshot==snapshot)''',
    'Stale inventory / entry / map / sender rejected': '''fixture(); grant("red_potion",2); local before=inv.RunConsumableSnapshot; assert(not use("red_potion","",1).Success); assert(not use("red_potion","",nil,6).Success); player.CurrentMap={}; assert(not use("red_potion").Success); player.CurrentMap=map; senderUserId="foreign"; session:RequestUseConsumable("red_potion",1,"",7,inv.InventoryRevision); assert(unit.CurrentHp==5 and inv.RunConsumableSnapshot==before)''',
    'Enemy turn / executing / battle over reject': '''fixture(); grant("red_potion",2); local before=inv.RunConsumableSnapshot; session.TurnState.BattlePhase="EnemyTurn"; assert(not use("red_potion").Success); session.TurnState.BattlePhase="PlayerTurn"; session.TurnState.IsActionProcessing=true; assert(not use("red_potion").Success); session.TurnState.IsActionProcessing=false; session.BattleResult="DEFEAT"; assert(not use("red_potion").Success); assert(unit.CurrentHp==5 and inv.RunConsumableSnapshot==before)''',
    'Three slots / total quantity / overflow / freed slot': '''fixture(); grant("red_potion",2); assert(grant("orange_potion",2).AcceptedAmount==1); assert(grant("time_sand",1).AcceptedAmount==0); assert(inv:GetSnapshotTotal(inv.RunConsumableSnapshot)==3); assert(inv.RunCurrencySnapshot=="gold~2"); inv:Consume("red_potion",1,"clear"); assert(grant("white_potion",1).AcceptedAmount==1)''',
    'Union configurable slot expansion': '''fixture(); inv:ResetForRun(2,2); assert(inv.ConsumableCapacity==5); for _,id in ipairs({"red_potion","orange_potion","white_potion","time_sand","all_cure_potion"}) do assert(grant(id,1).AcceptedAmount==1) end''',
    'Shop rejects overflow before charging and accepts an exact fit': '''fixture(); inv.RunCurrencySnapshot="gold~20"; grant("red_potion",2); local r=inv:ApplyShopPurchase("gold",5,"CONSUMABLE","red_potion",2,"buy1"); assert(not r.Success and r.Reason=="CONSUMABLE_CAPACITY_FULL" and r.BalanceAfter==20); assert(inv.RunCurrencySnapshot=="gold~20" and inv:GetSnapshotAmount(inv.RunConsumableSnapshot,"red_potion")==2); local fit=inv:ApplyShopPurchase("gold",5,"CONSUMABLE","red_potion",1,"buy1"); assert(fit.Success and fit.AcceptedAmount==1 and fit.OverflowAmount==0 and fit.BalanceAfter==15); local money=inv.RunCurrencySnapshot; local bad=inv:ApplyShopPurchase("gold",5,"CONSUMABLE","missing",1,"bad"); assert(not bad.Success and inv.RunCurrencySnapshot==money)''',
    'Legacy potion alias migrates without quantity loss': '''fixture(); inv.RunConsumableSnapshot="orange_potion~1|potion_hp_small~2"; inv:NormalizeLegacyConsumables(); assert(inv.RunConsumableSnapshot=="orange_potion~3"); local def=_ConsumableDefinitionRepositoryLogic:GetDefinition("potion_hp_small"); assert(def.ConsumableId=="orange_potion" and def.EffectValue==3); assert(use("potion_hp_small").Success and unit.CurrentHp==8)''',
    'All five catalog rows validated / turn cost guarded': '''fixture(); for _,row in ipairs(rows) do local def=_ConsumableDefinitionRepositoryLogic:GetDefinition(row.ConsumableId); assert(def.Success); def.TurnCost=1; assert(not _ConsumableDefinitionRepositoryLogic:ValidateDefinition(def).Success) end''',
    'UI cancel / no-target selection never consumes': '''fixture(); grant("time_sand",1); local hud=object(HudMethods,{Selector={},SelectedConsumableId="time_sand",_T={Data={Skills={}}}}); hud:CloseSelection(); assert(hud.SelectedConsumableId=="" and not hud.Selector.Enable); hud.SelectedConsumableId="time_sand"; hud:RenderSkills(); assert(hud.SelectedConsumableId==""); assert(inv:GetSnapshotAmount(inv.RunConsumableSnapshot,"time_sand")==1)''',
    'UI/RPC pending guard / stale read receipts': '''fixture(); local calls=0; session.RequestUseConsumable=function() calls=calls+1 end; assert(session:SubmitConsumableUse("time_sand","brandish")); assert(not session:SubmitConsumableUse("time_sand","brandish")); assert(calls==1); session:ReceiveConsumableUseResult({Success=false,RequestId=1},6); assert(session._T.ConsumablePending); session:ReceiveConsumableUseResult({Success=false,RequestId=1},7); assert(not session._T.ConsumablePending); session:ReceiveConsumableHudState({mark=2},2,7); session:ReceiveConsumableHudState({mark=1},1,7); assert(session._T.ConsumableHudState.mark==2)''',
    'HUD selection -> server -> quantity/cooldown refresh (mock transport)': '''uiFixture(); grant("time_sand",2); cd:StartCooldown("brandish",3); hud:OnUpdate(0.2); hud:OnUpdate(0.2); assert(hud.Panel.Enable and #hud.Slots==3); hud:ClickSlot(1); assert(hud.Selector.Enable and #hud.SkillRows==4); hud:ClickSkill(1); assert(not hud.Selector.Enable and cd:GetRemainingCooldown("brandish")==1); hud:OnUpdate(0.2); hud:OnUpdate(0.2); assert(hud.Slots[1].children.Icon.Enable and not hud.Slots[2].children.Icon.Enable); unchangedTurn(); hud:OnEndPlay(); assert(#hud.EventLinks==0 and #hud.Slots==0)''',
    'HUD hides at result / stale run data rejected': '''uiFixture(); grant("red_potion",1); hud:OnUpdate(0.2); hud:OnUpdate(0.2); assert(hud.Panel.Enable); session.BattleResult="DEFEAT"; hud:OnUpdate(0.2); assert(not hud.Panel.Enable and not hud.Selector.Enable); session.BattleResult=""; inv:ResetForRun(2,0); hud:OnUpdate(0.2); assert(not hud.Panel.Enable); hud:OnUpdate(0.2); assert(hud.Panel.Enable and not hud.Slots[1].children.Icon.Enable)''',
}

passed = 0
for name, code in cases.items():
    try:
        lua.execute(code)
        passed += 1
        print('PASS', name)
    except Exception:
        print('FAIL', name)
        raise
print(f'{passed}/{len(cases)} offline cases passed. Maker build/play: NOT RUN.')
