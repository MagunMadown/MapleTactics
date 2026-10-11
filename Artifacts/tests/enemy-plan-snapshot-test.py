"""Exercise server enemy HUD publication, client decoding, and hover request guards."""
import os
from pathlib import Path
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
COMBAT = ROOT / "RootDesk/MyDesk/01_Combat"
SESSION = COMBAT / "Components/Shared/BattleSessionComponent.mlua"
LOGIC = COMBAT / "Resolvers/EnemyPlanSnapshotLogic.mlua"
PATTERN = re.compile(r"^\tmethod\s+\w+\s+(\w+)\(([^)]*)\)\n(.*?)^\tend$", re.M | re.S)
lua = LuaRuntime(unpack_returned_tuples=True)


def load(path, names=None):
    methods = lua.table()
    for name, parameters, body in PATTERN.findall(path.read_text(encoding="utf-8-sig")):
        if names is None or name in names:
            args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
            methods[name] = lua.eval("function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend")
    if names is not None:
        assert set(methods.keys()) == set(names)
    return methods


lua.globals().Session = load(SESSION, {"PublishEnemyPlanSnapshot", "RequestEnemySkillHover"})
lua.globals()._EnemyPlanSnapshotLogic = load(LOGIC)
lua.globals()._EnemyTelegraphLogic = load(COMBAT / "Resolvers/EnemyTelegraphLogic.mlua")
lua.globals().Parser = load(COMBAT / "Resolvers/BattleUiStateLogic.mlua", {"ParseEnemyPlanSnapshot", "DecodeEnemyPlanField"})
# Optional migration check against the actual pre-extraction source, never a copied implementation.
if os.environ.get("ORIGINAL_SESSION"):
    names = set(lua.globals()._EnemyPlanSnapshotLogic.keys()) - {"BuildSnapshot", "BuildEnemySkillHover"}
    lua.globals().Original = load(Path(os.environ["ORIGINAL_SESSION"]), names | {
        "PublishEnemyPlanSnapshot", "IsEnemySpecialSkill", "BuildBossLandingTelegraph",
        "BuildChargeTelegraph", "BuildSkillAreaTelegraph"})

lua.execute(r'''
function isvalid(value) return value ~= nil and value.Valid ~= false end
function log(_) end
_UtilLogic = {ElapsedSeconds=10}
local logic = _EnemyPlanSnapshotLogic
setmetatable(logic, {__index=function(_, name) error('unexpected shared state: '..name) end})
local definitions, effects = {}, {}
_SkillDefinitionRepositoryLogic = {
    GetSkillDefinition=function(_, id) return definitions[id] or {Success=false} end,
    GetEffectSteps=function(_, id) return effects[id] or {Success=false} end
}
_SkillCodexProvider={DescribeRange=function() return '전방 2칸' end}
_BuffEffectExecutorLogic={FormatNumber=function(_, n) return tostring(n) end,
    DescribeEffectSteps=function(_, steps) return '기타: '..steps[1].EffectType end}
_DamageEffectExecutorLogic={ResolveDamageAmount=function(_, unit, step) return unit.AttackPower * step.Value end}
_SkillTargetResolverLogic={SerializeIntegers=function(_, cells) return table.concat(cells,'|') end,
    Resolve=function() return {Success=true,TargetCellIndices={2,3}} end}
function skill(id, kinds, tags)
    local definition={Success=true, SkillId=id, DisplayName=id..' 이름', EffectSetId=id,
        HudIconRuid=id..'_icon', HudIconBackgroundColor='#123456FF', SkillTags=tags or '',
        CooldownTurns=2, Range=2, TargetingType='FIRST_ENEMY_FORWARD', TargetOffsets='1|2'}
    definitions[id]=definition
    local steps={}
    for _, kind in ipairs(kinds or {'DAMAGE'}) do
        table.insert(steps, {EffectType=kind, Value=3, ParameterA='2'})
    end
    effects[id]={Success=true, Steps=steps}
    return definition, steps
end
skill('plain'); skill('burn', {'DAMAGE','IGNITE'}, 'telegraph')
function fixture()
    local current={Success=true, ActionType='EXECUTE_TILE', TileId='plain', Direction=1,
        TelegraphTurnsRemaining=2, PatternId='pattern_a', StepIndex=3}
    local plan={PlanState='TRACKING', CurrentActionIndex=1, PlannedActionCount=2,
        TraitIds='trait_a', PlanRevision=7, PlannedActionSnapshot='1~EXECUTE_TILE~plain>2~TELEGRAPH_TILE~burn',
        QueueTurnsRequired=2, QueueTurnsElapsed=2, QueueSkillsIndividually=false,
        ReadinessReason='RANGE_READY', NextCommandType='ATTACK', NextCommandDirection=1,
        TargetCellSnapshot='old', DeferredUntilTurn=4, CastState='NONE', CastingSkillId='',
        InterruptHitsRequired=2, InterruptHitsReceived=0, GetCurrentAction=function() return current end}
    local unit={UnitId='enemy_a', SpawnOrder=2, EnemyPatternId='fallback', Facing='Right',
        IsDead=false, Team='Enemy', AttackPower=5, CellIndex=1, IsBoss=false}
    local parts={['script.BattleUnitComponent']=unit, ['script.EnemyActionPlanComponent']=plan}
    local enemy={Name='Enemy A', GetComponent=function(_, name) return parts[name] end}
    local enemies={enemy}
    local session=setmetatable({CellCount=6, BoardState={CollectLivingEnemies=function() return enemies end,
        FindAtCell=function() return nil end},
        EnemyPlanSnapshot='before', EnemyPlanCount=99, EnemyPlanRevision=8, _T={}}, {__index=Session})
    function session:IsValidCell(cell) return cell>=0 and cell<self.CellCount end
    function session:IsValidPlayerRequest(id) return id=='owner' end
    function session:FindUnitEntity(id) return id==unit.UnitId and enemy or nil end
    function session:ReceiveEnemySkillHover(key, requestId, text, cells, id)
        self.Response={Key=key, RequestId=requestId, Text=text, Cells=cells, UserId=id}
    end
    return session, plan, current, unit, parts, enemies
end
function publish(session)
    local previous=session.EnemyPlanRevision
    session:PublishEnemyPlanSnapshot('TEST')
    assert(session.EnemyPlanRevision==previous+1)
    if Original ~= nil then
        local baseline=setmetatable({}, {__index=Original})
        for key,value in pairs(session) do baseline[key]=value end
        Original.PublishEnemyPlanSnapshot(baseline, 'PARITY')
        assert(baseline.EnemyPlanSnapshot==session.EnemyPlanSnapshot, 'snapshot changed during extraction')
        assert(baseline.EnemyPlanCount==session.EnemyPlanCount)
    end
    return Parser:ParseEnemyPlanSnapshot(session.EnemyPlanSnapshot)[1]
end
function case(name, check) check(); print('PASS '..name) end

case('builder reads state while session owns publication and revision', function()
    local session,plan=fixture()
    local result=logic:BuildSnapshot(session)
    assert(result.Count==1 and session.EnemyPlanSnapshot=='before' and session.EnemyPlanRevision==8)
    assert(plan.TargetCellSnapshot=='old' and plan.PlanRevision==7)
    local dto=publish(session)
    assert(session.EnemyPlanCount==1 and session.EnemyPlanSnapshot==result.Snapshot)
    assert(dto.UnitId=='enemy_a' and dto.PatternId=='pattern_a' and dto.Revision==7)
    assert(dto.EntityName=='Enemy A' and dto.TargetCells=='2|3' and dto.TelegraphKind=='')
    assert(dto.QueuedTileNames=='plain 이름|burn 이름' and dto.QueuedIconRuids=='plain_icon|burn_icon')
    assert(dto.QueuedIconBackgroundColors=='123456FF|123456FF' and dto.QueuedOverlayKinds=='-|IGNITE')
    assert(dto.QueuedSpecialFlags=='0|1' and dto.DeferredUntilTurn==4)
    local count=0
    for _ in string.gmatch(session.EnemyPlanSnapshot, '([^,]+)') do count=count+1 end
    assert(count==36)
end)
case('empty board and missing or empty plans publish an empty snapshot', function()
    local session,plan,_,_,parts,enemies=fixture()
    session.BoardState=nil; assert(publish(session)==nil and session.EnemyPlanCount==0)
    session=fixture(); session.BoardState.CollectLivingEnemies=function() return {} end
    assert(publish(session)==nil)
    session,plan,_,_,parts,enemies=fixture(); plan.PlanState='EMPTY'; assert(publish(session)==nil)
    plan.PlanState='TRACKING'; parts['script.BattleUnitComponent']=nil; assert(publish(session)==nil)
end)
case('queue visibility keeps partially inserted slots and preparation timing', function()
    local session,plan=fixture()
    plan.PlanState='INSERTING'; plan.QueueSkillsIndividually=true
    assert(logic:BuildSnapshot(session).Snapshot:find('plain 이름|burn 이름',1,true))
    plan.QueueSkillsIndividually=false
    assert(not logic:BuildSnapshot(session).Snapshot:find('plain 이름',1,true))
    plan.PlanState='PREPARED'; plan.QueueTurnsElapsed=1; assert(publish(session).QueuedTileNames=='')
    plan.QueueTurnsElapsed=2; assert(publish(session).QueuedTileNames=='plain 이름|burn 이름')
end)
case('ready area, committed charge and interrupted cast warnings retain their cells', function()
    local session,plan,current=fixture(); plan.PlanState='ATTACK_READY'
    assert(publish(session).TelegraphKind=='SKILL_AREA')
    current.ActionType='CHARGE_FORWARD'; plan.TargetCellSnapshot='1|2|3'
    local dto=publish(session); assert(dto.TargetCells=='1|2|3' and dto.TelegraphKind=='CHARGE_LINE')
    plan.CastState='INTERRUPTED'; plan.CastingSkillId='plain'; plan.InterruptHitsReceived=2
    dto=publish(session)
    assert(dto.TargetCells=='' and dto.TelegraphKind=='' and dto.LandingCell==-1 and dto.IsCastInterrupted)
    assert(dto.QueuedIconRuids=='plain_icon|burn_icon' and plan.TargetCellSnapshot=='1|2|3')
end)
case('boss landing, summon preview and prepared direction use existing rule helpers', function()
    local session,plan,current,unit,parts=fixture(); plan.PlanState='PREPARED'; unit.IsBoss=true
    parts['script.BossPhaseStateComponent']={PhaseId='rage', PhaseIndex=2, PhaseRevision=9}
    current.ActionType='BOSS_LAND_OPPOSITE'
    local dto=publish(session)
    assert(dto.TargetCells=='5|4|3' and dto.LandingCell==5 and dto.TelegraphKind=='BOSS_LANDING')
    assert(dto.BossPhaseId=='rage' and dto.BossPhaseRevision==9 and dto.QueuedOverlayKinds=='JUMP_DOWN')
    current.ActionType='SUMMON_ENEMIES'
    parts['script.FaustSummonComponent']={SummonDisplayName='소환', SummonIconRuid='summon_icon'}
    dto=publish(session); assert(dto.QueuedTileNames=='소환' and dto.QueuedIconRuids=='summon_icon')
    current.ActionType='MOVE_TOWARD'; current.Direction=-1
    assert(publish(session).CommandType=='TURN_TO_PLAYER')
end)
case('unknown skill placeholders, colors and semantic badge priorities remain aligned', function()
    local actions='bad>1~MOVE~->2~EXECUTE_TILE~missing>3~TELEGRAPH_TILE~plain'
    assert(logic:GetEnemyQueueDisplayNames(actions)=='missing|plain 이름')
    assert(logic:GetEnemyQueueIconRuids(actions)=='-|plain_icon')
    definitions.plain.HudIconBackgroundColor='invalid'
    assert(logic:GetEnemyQueueIconBackgroundColors(actions)=='-|-')
    assert(logic:GetEnemyQueueSpecialFlags(actions)=='0|1' and logic:GetEnemyQueueOverlayKinds(actions)=='-|WARNING')
    definitions.plain.HudIconBackgroundColor='#123456FF'
    for _, kind in ipairs({'FROSTBITE','CONFUSE','POISON_MIST','POISON','STUN','ATTACK_BUFF','HEAL'}) do
        skill(kind,{kind}); assert(logic:GetEnemySkillOverlayKind(kind)==kind)
    end
    skill('priority',{'HEAL','FROSTBITE','BURN'}); assert(logic:GetEnemySkillOverlayKind('priority')=='IGNITE')
    skill('future',{'NEW_EFFECT'}); assert(logic:GetEnemySkillOverlayKind('future')=='WARNING')
    skill('area',{'DAMAGE'},'area'); assert(logic:GetEnemySkillOverlayKind('area')=='IMPACT')
    assert(logic:GetEnemyActionOverlayKind('missing','BOSS_JUMP_TELEGRAPH')=='JUMP_UP')
end)
case('tooltip preserves resolved damage, statuses, cooldown and special classification', function()
    local _,_,_,unit=fixture()
    local definition,steps=skill('tooltip',{'DAMAGE','IGNITE','FROSTBITE','CONFUSE','SEAL','POISON_MIST','PUSH','PULL','TURN_TARGET','HEAL'},'telegraph')
    local text=logic:BuildEnemySkillHoverText(unit,definition,steps)
    for _, phrase in ipairs({'[특수 공격]','전방 2칸','예고 후 발동','재사용 대기: 2턴','피해: 15','화상','동상','혼란','봉인','독안개','3칸 밀치기','3칸 끌어오기','방향을 뒤집음','기타: HEAL'}) do
        assert(text:find(phrase,1,true), phrase)
    end
    assert(not logic:BuildEnemySkillHoverText(unit,definitions.plain,effects.plain.Steps):find('[특수 공격]',1,true))
end)
case('boss landing clips and deduplicates offsets and preserves a pending airborne destination', function()
    local session,_,_,unit=fixture(); unit.IsBoss=true
    local definition=skill('landing'); definition.TargetOffsets='1|2|2|-1|99'
    local result=_EnemyTelegraphLogic:BuildBossLandingTelegraph(session,unit,'landing')
    assert(result.LandingCell==5 and result.TargetCells=='5|4|3')
    unit.IsAirborne=true; unit.PendingLandingCell=0
    result=_EnemyTelegraphLogic:BuildBossLandingTelegraph(session,unit,'landing')
    assert(result.LandingCell==0 and result.TargetCells=='0|1|2')
    unit.IsBoss=false; assert(not _EnemyTelegraphLogic:BuildBossLandingTelegraph(session,unit,'landing').Success)
end)
case('charge uses facing fallback and stops on the first occupied cell', function()
    local session,_,_,unit=fixture(); definitions.plain.Range=5
    local blocker={GetComponent=function() return {Team='Enemy',IsDead=false} end}
    session.BoardState.FindAtCell=function(_,cell) return cell==3 and blocker or nil end
    local result=_EnemyTelegraphLogic:BuildChargeTelegraph(session,unit,0,'plain')
    assert(result.TargetCells=='2|3' and result.TelegraphKind=='CHARGE_LINE')
    unit.Team='Player'; assert(_EnemyTelegraphLogic:BuildChargeTelegraph(session,unit,1,'plain').TargetCells=='2|3')
    blocker.GetComponent=function() return {Team='Player',IsDead=false} end
    assert(_EnemyTelegraphLogic:BuildChargeTelegraph(session,unit,1,'plain').TargetCells=='2')
    unit.Facing='Left'; assert(_EnemyTelegraphLogic:BuildChargeTelegraph(session,unit,0,'plain').TargetCells=='0')
    unit.IsDead=true; assert(not _EnemyTelegraphLogic:BuildChargeTelegraph(session,unit,1,'plain').Success)
    definitions.plain.Range=2
end)
case('area warning shows full potential reach and delegates other targeting to the shared resolver', function()
    local session,_,_,unit=fixture(); unit.CellIndex=4
    assert(_EnemyTelegraphLogic:BuildSkillAreaTelegraph(session,unit,'plain').TargetCells=='5')
    unit.Facing='Left'; assert(_EnemyTelegraphLogic:BuildSkillAreaTelegraph(session,unit,'plain').TargetCells=='3|2')
    local definition=skill('offsets'); definition.TargetingType='RANGE_OFFSETS'
    local result=_EnemyTelegraphLogic:BuildSkillAreaTelegraph(session,unit,'offsets')
    assert(result.TargetCells=='2|3' and result.TelegraphKind=='SKILL_AREA')
    assert(not _EnemyTelegraphLogic:BuildSkillAreaTelegraph(session,unit,'missing').Success)
end)
case('hover RPC retains owner, living enemy, definition and throttle checks', function()
    local session,_,_,unit=fixture()
    _SkillTargetResolverLogic.Resolve=function(_, s, id)
        assert(s==session and id=='enemy_a'); return {Success=true,TargetCellIndices={2,3}} end
    senderUserId='stranger'; session:RequestEnemySkillHover('enemy_a','plain',1); assert(session.Response==nil)
    senderUserId='owner'; session:RequestEnemySkillHover('enemy_a','plain',2)
    assert(session.Response.RequestId==2 and session.Response.Key=='enemy_a:plain' and session.Response.UserId=='owner')
    assert(session.Response.Cells[2]==3)
    session:RequestEnemySkillHover('enemy_a','plain',3); assert(session.Response.RequestId==2)
    _UtilLogic.ElapsedSeconds=11; session.Response=nil; unit.IsDead=true
    session:RequestEnemySkillHover('enemy_a','plain',4); assert(session.Response==nil)
    _UtilLogic.ElapsedSeconds=12; unit.IsDead=false
    session:RequestEnemySkillHover('enemy_a','missing',5); assert(session.Response==nil)
end)
case('alternating sessions do not retain board or plan state on the global logic', function()
    local first=fixture(); local second,plan,current,unit=fixture()
    unit.UnitId='enemy_b'; unit.SpawnOrder=1; current.ActionType='CHARGE_FORWARD'; plan.TargetCellSnapshot='4'
    local firstBefore=logic:BuildSnapshot(first).Snapshot
    assert(publish(second).UnitId=='enemy_b' and publish(first).UnitId=='enemy_a')
    assert(logic:BuildSnapshot(first).Snapshot==firstBefore and rawget(logic,'session')==nil)
end)
''')
