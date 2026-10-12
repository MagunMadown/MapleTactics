"""Exercise the battle UI read model and session facade with offline Lua mocks."""
import os
from pathlib import Path
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime
from battle_refactor_fixture import wire_logic_owners

ROOT = Path(__file__).resolve().parents[2]
SESSION = ROOT / "RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua"
LOGIC = ROOT / "RootDesk/MyDesk/01_Combat/Resolvers/BattleUiStateLogic.mlua"
PATTERN = re.compile(r"^\tmethod\s+\w+\s+(\w+)\(([^)]*)\)\n(.*?)^\tend$", re.M | re.S)
lua = LuaRuntime(unpack_returned_tuples=True)
wire_logic_owners(lua)


def load(source, names):
    methods = lua.table()
    for name, parameters, body in PATTERN.findall(source):
        if name in names:
            args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
            methods[name] = lua.eval("function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend")
    assert set(methods.keys()) == set(names)
    return methods


source = SESSION.read_text(encoding="utf-8-sig")
lua.globals().Session = load(source, {"GetBattleUiState", "ParseEnemyPlanSnapshot", "IsPlayerSealed", "GetPlayerStatusUnit"})
lua.globals()._BattleUiStateLogic = load(LOGIC.read_text(encoding="utf-8-sig"), {"Build", "ParseEnemyPlanSnapshot", "DecodeEnemyPlanField", "ResolvePlayerActionState"})
defaults = lua.table()
for kind, name, value in re.findall(r"property\s+(string|number|integer|boolean)\s+(\w+)\s*=\s*([^\n]+)", source):
    defaults[name] = lua.eval(value)
lua.globals().sessionDefaults = defaults
lua.execute(r'''
function isvalid(value) return value ~= nil and value.Valid ~= false end
local logic = _BattleUiStateLogic
setmetatable(logic, {__index=function(_, name) error('unexpected logic state: '..name) end})
_RunManagerLogic = {GetLocalRunStatsSnapshot=function() return {Revision=2, RunSequence=3} end}
function fixture()
    local session = setmetatable({}, {__index=Session})
    for name, value in pairs(sessionDefaults) do session[name]=value end
    function session:IsClient() return true end
    session.ContentValidationState='VALID'
    session.StageId='stage_a'
    session.SelectedJobRevision=10
    session.JobMechanicRevision=11
    session.SkillTargetRevision=12
    session.ContentValidationRevision=13
    session.EnemyPlanRevision=15
    session.UnionRewardRevision=17
    session.AugmentRuntimeRevision=9
    local turn = {BattlePhase='PlayerTurn', IsActionProcessing=false, QueuedActionType='',
        QueuedTileIds='', QueuedTileCount=0, TileQueueCapacity=3, BaseQueueCapacity=3,
        QueueCapacityBonus=0, QueueCapacityMin=1, QueueCapacityMax=10,
        ExecutingTileIds='', ExecutingTileIndex=0, QueueCapacityModifierSnapshot='',
        StateRevision=4, QueueCapacityRevision=5, QueueOrderRevision=6,
        CommandResultRevision=7, LastCommandType='', LastCommandSuccess=true,
        LastCommandReason='OK', TurnNumber=1}
    local wave = {CurrentWave=14, TotalWaves=20, WaveState='ACTIVE', ForceSpawnPending=false}
    local parts = {['script.BattleTurnComponent']=turn, ['script.BattleWaveComponent']=wave,
        ['script.BattleDropComponent']={PendingDropSnapshot='drop', PendingDropCount=2, DropRevision=8}}
    local children={}
    local map={GetComponent=function(_,name) return parts[name] end,
        GetChildByName=function(_,name) return children[name] end}
    session.Entity=map
    local playerParts={['script.BattleUnitComponent']={SealTurns=0, FrostbiteTurns=0,
        ConfuseTurns=0, BurnDamage=0, BurnTurns=0},
        ['script.SkillRuntimeStateComponent']={CooldownSnapshot='cooldowns', CooldownRevision=18},
        ['script.PlayerRunInventoryComponent']={RunConsumableSnapshot='consumables',
            RunCurrencySnapshot='currency', RunSkillSnapshot='skills', InventoryRevision=19,
            HealCharges=2, HealUnlimited=false, SkillInventoryRevision=20, ConsumableCapacity=4},
        ['script.PlayerRunAugmentComponent']={OwnedAugmentSnapshot='augments', AugmentRevision=21}}
    local player={CurrentMap=map, GetComponent=function(_,name) return playerParts[name] end}
    _UserService={LocalPlayer=player}
    session.PlayerEntity=player
    return session, turn, wave, parts, children, playerParts
end
function case(name, check)
    check()
    print('PASS '..name)
end
function equal(left, right)
    assert(type(left)==type(right))
    if type(left)~='table' then assert(left==right); return end
    for key,value in pairs(left) do equal(value,right[key]) end
    for key in pairs(right) do assert(left[key]~=nil) end
end
function plan(fields)
    return table.concat(fields, ',')
end
function legacy(state, order)
    return {'enemy', tostring(order or 1), state or 'TRACKING', '1','2','DOUBLE_STRIKE',
        'ATTACK','skill_a','1','2','pattern_a','3','4','1~ATTACK~skill_a>2~ATTACK~skill_b'}
end

case('session facade returns the same DTO and parser result as the read model', function()
    local session=fixture()
    equal(session:GetBattleUiState(), logic:Build(session))
    equal(session:ParseEnemyPlanSnapshot(plan(legacy())), logic:ParseEnemyPlanSnapshot(plan(legacy())))
end)
case('missing turn or wave returns BATTLE_STATE_MISSING; child state is preferred', function()
    local session,turn,wave,parts,children=fixture()
    parts['script.BattleTurnComponent']=nil
    assert(logic:Build(session).Reason=='BATTLE_STATE_MISSING')
    children.BattleTurnState={GetComponent=function() return turn end}
    assert(logic:Build(session).Success)
    parts['script.BattleWaveComponent']=nil
    assert(logic:Build(session).Reason=='BATTLE_STATE_MISSING')
    children.BattleWaveState={GetComponent=function() return wave end}
    assert(logic:Build(session).Wave.Current==14)
    local childTurn={}
    for k,v in pairs(turn) do childTurn[k]=v end
    childTurn.TurnNumber=42
    children.BattleTurnState.GetComponent=function() return childTurn end
    assert(logic:Build(session).TurnNumber==42)
end)
case('idle, queued, processing and enemy-turn action states preserve command gates', function()
    local session,turn=fixture()
    local state=logic:Build(session)
    assert(state.PlayerActionState=='READY' and state.Commands.CanMove and state.Commands.CanTurn)
    assert(state.Commands.CanQueue and not state.Commands.CanExecute and not state.Commands.CanRemove)
    turn.QueuedTileIds='skill_a|skill_b'; turn.QueuedTileCount=2
    state=logic:Build(session)
    assert(state.PlayerActionState=='PREPARING_ATTACK' and state.Commands.CanExecute and state.Commands.CanReorder)
    assert(state.PlayerQueue.Items[2].SkillId=='skill_b' and state.PlayerQueue.RemainingSlots==1)
    turn.QueuedTileCount=3
    assert(not logic:Build(session).Commands.CanQueue)
    turn.IsActionProcessing=true
    for action,expected in pairs({MOVE='MOVING',TURN='TURNING'}) do
        turn.QueuedActionType=action; state=logic:Build(session)
        assert(state.PlayerActionState==expected and not state.Commands.CanMove and not state.Commands.CanExecute)
    end
    turn.QueuedActionType=''; turn.ExecutingTileIds='skill_a'
    assert(logic:Build(session).PlayerActionState=='EXECUTING_ATTACK')
    turn.ExecutingTileIds=''; assert(logic:Build(session).PlayerActionState=='LOCKED')
    turn.IsActionProcessing=false; turn.BattlePhase='EnemyTurn'
    state=logic:Build(session)
    assert(state.PlayerActionState=='WAITING_ENEMY_TURN' and not state.Commands.CanTurn)
    session.BattleResult='WIN'; assert(logic:Build(session).PlayerActionState=='LOCKED')
    session.BattleResult=''; session.ContentValidationState='INVALID'
    assert(logic:Build(session).PlayerActionState=='LOCKED' and not logic:Build(session).Commands.CanQueue)
end)
case('sealed and frostbitten statuses gate only their existing commands', function()
    local session,turn,_,_,_,playerParts=fixture()
    turn.QueuedTileIds='skill_a|skill_b'; turn.QueuedTileCount=2
    local unit=playerParts['script.BattleUnitComponent']
    unit.SealTurns=2; unit.FrostbiteTurns=1; unit.ConfuseTurns=3; unit.BurnDamage=7; unit.BurnTurns=4
    local state=logic:Build(session)
    assert(state.PlayerSealed and state.PlayerFrostbitten and state.PlayerConfused)
    assert(state.PlayerBurnDamage==7 and state.PlayerBurnTurns==4)
    assert(not state.Commands.CanMove and not state.Commands.CanQueue and not state.Commands.CanExecute)
    assert(state.Commands.CanTurn and state.Commands.CanClear and state.Commands.CanRemove and state.Commands.CanReorder)
    playerParts['script.BattleUnitComponent']=nil
    assert(not logic:Build(session).PlayerSealed)
end)
case('legacy plans decode empty fields, sort spawn order and keep inserted queue slots', function()
    local fields=legacy('TRACKING',2); fields[6]='-'; fields[11]='-'
    local earlier=legacy('INSERTING',1)
    local plans=logic:ParseEnemyPlanSnapshot(plan(fields)..'#'..plan(earlier)..'#bad,entry')
    assert(#plans==2 and plans[1].SpawnOrder==1)
    assert(plans[1].QueuedTileIds=='' and not plans[1].IsQueueReady)
    assert(plans[2].TraitIds=='' and plans[2].PatternId=='')
    assert(plans[2].QueuedTileIds=='skill_a|skill_b' and plans[2].IsQueueReady)
    assert(plans[2].BossPhaseId=='' and plans[2].LandingCell==-1 and plans[2].CastState=='NONE')
    assert(logic:DecodeEnemyPlanField(nil)=='' and logic:DecodeEnemyPlanField('-')=='')
    assert(logic:DecodeEnemyPlanField('enemy%20name')=='enemy%20name')
end)
case('full plans preserve boss, telegraph, queue icon and interrupted cast fields', function()
    local fields=legacy('ATTACK_READY')
    for i,value in ipairs({'phase_a','2','5','3','3','RANGE_READY','ATTACK','2|3','-1',
        'Enemy A','A|B','icon_a|icon_b','LANDING','5','9','red|blue','INTERRUPTED',
        'cast_a','4','3','1|0','ATTACK|MOVE'}) do fields[14+i]=value end
    local result=logic:ParseEnemyPlanSnapshot(plan(fields))[1]
    assert(result.BossPhaseId=='phase_a' and result.BossPhaseIndex==2 and result.BossPhaseRevision==5)
    assert(result.QueueTurnsRequired==3 and result.QueueTurnsElapsed==3 and result.ReadinessReason=='RANGE_READY')
    assert(result.TargetCells=='2|3' and result.NextCommandDirection==-1 and result.EntityName=='Enemy A')
    assert(result.QueuedTileNames=='A|B' and result.QueuedIconRuids=='icon_a|icon_b')
    assert(result.QueuedIconBackgroundColors=='red|blue' and result.QueuedSpecialFlags=='1|0')
    assert(result.QueuedOverlayKinds=='ATTACK|MOVE' and result.TelegraphKind=='LANDING')
    assert(result.LandingCell==5 and result.DeferredUntilTurn==9 and result.IsCastInterrupted and result.IsAttackReady)
    assert(result.CastingSkillId=='cast_a' and result.InterruptHitsRequired==4 and result.InterruptHitsReceived==3)
    fields[3]='INSERTING'; fields[19]='0'
    result=logic:ParseEnemyPlanSnapshot(plan(fields))[1]
    assert(result.QueuedTileNames=='' and result.QueuedIconRuids=='' and result.QueuedOverlayKinds=='')
end)
case('boss summon and opposite jump preview retain their display-only queue entries', function()
    local fields=legacy('PREPARED'); fields[7]='SUMMON_ENEMIES'; fields[8]='-'
    local result=logic:ParseEnemyPlanSnapshot(plan(fields))[1]
    assert(result.QueuedTileIds=='boss_summon' and result.QueuedTileNames=='몬스터 소환')
    assert(result.QueuedSpecialFlags=='1' and result.QueuedOverlayKinds=='WARNING')
    fields[7]='BOSS_JUMP_TELEGRAPH'; fields[8]='jump_a'
    assert(logic:ParseEnemyPlanSnapshot(plan(fields))[1].QueuedOverlayKinds=='JUMP_UP')
    fields[7]='BOSS_LAND_OPPOSITE'
    assert(logic:ParseEnemyPlanSnapshot(plan(fields))[1].QueuedOverlayKinds=='JUMP_DOWN')
end)
case('prepared intent component overrides compatibility fields without duplicating a real plan', function()
    local session,_,_,parts=fixture()
    session.PreparedEnemyIntentState='PREPARED'; session.PreparedEnemyId='compat_enemy'; session.PreparedEnemyTileId='compat_skill'
    local state=logic:Build(session)
    assert(#state.EnemyIntents==1 and state.EnemyIntents[1].UnitId=='compat_enemy')
    parts['script.EnemyIntentComponent']={IntentState='TRACKING',EnemyId='component_enemy',PatternId='pattern',
        StepIndex=1,ActionType='ATTACK',TileId='component_skill',TelegraphTurnsRemaining=0,
        Direction=1,PreparedTurn=2,IntentReason='READY',IntentRevision=16}
    state=logic:Build(session)
    assert(state.EnemyIntents[1].UnitId=='component_enemy' and state.EnemyIntents[1].Revision==16)
    session.EnemyPlanSnapshot=plan(legacy())
    state=logic:Build(session)
    assert(#state.EnemyIntents==1 and state.EnemyIntents[1].UnitId=='enemy')
end)
case('synchronized run, queue and drop data retain their revision key positions', function()
    local session=fixture()
    local state=logic:Build(session)
    assert(state.RevisionKey=='2:3:4:5:6:7:18:19:21:9:8:10:11:12:13:14:15:0:EMPTY::::17::false:')
    assert(state.CooldownSnapshot=='cooldowns' and state.CooldownRevision==18)
    assert(state.RunInventory.CurrencySnapshot=='currency' and state.RunInventory.ConsumableSnapshot=='consumables')
    assert(state.RunInventory.SkillSnapshot=='skills' and state.RunInventory.SkillRevision==20)
    assert(state.RunInventory.Revision==19 and state.RunInventory.HealCharges==2 and state.RunInventory.ConsumableCapacity==4)
    assert(state.RunAugments.OwnedSnapshot=='augments' and state.RunAugments.Revision==21)
    assert(state.Drops.PendingSnapshot=='drop' and state.Drops.PendingCount==2 and state.Drops.Revision==8)
    assert(state.PlayerQueue.QueueOrderRevision==6 and state.LastCommand.Revision==7)
end)
case('absent local player and optional inventory state use existing defaults', function()
    local session,_,_,parts=fixture()
    _UserService.LocalPlayer=nil; parts['script.BattleDropComponent']=nil
    local state=logic:Build(session)
    assert(state.Success and state.CooldownSnapshot=='' and state.CooldownRevision==0)
    assert(state.RunInventory.HealCharges==-1 and state.RunInventory.Revision==0)
    assert(state.RunAugments.OwnedSnapshot=='' and state.Drops.PendingCount==0)
end)
case('alternating sessions and mutated DTOs cannot share read-model state', function()
    local first=fixture()
    local second,turn=fixture(); second.StageId='stage_b'; turn.TurnNumber=22
    local firstDto=first:GetBattleUiState(); local secondDto=second:GetBattleUiState()
    assert(firstDto.Stage.StageId=='stage_a' and secondDto.Stage.StageId=='stage_b')
    secondDto.Stage.StageId='mutated'; secondDto.PlayerQueue.Items[1]={SkillId='fake'}
    assert(first:GetBattleUiState().Stage.StageId=='stage_a')
    local fresh=second:GetBattleUiState()
    assert(fresh.Stage.StageId=='stage_b' and fresh.TurnNumber==22 and #fresh.PlayerQueue.Items==0)
    assert(rawget(logic,'Entity')==nil and rawget(logic,'session')==nil)
end)
''')
