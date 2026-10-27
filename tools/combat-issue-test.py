"""Execute production Lua 5.3 damage, ascension and boss summon paths with engine doubles."""
import csv, io, os, re, subprocess, sys
from pathlib import Path
if os.environ.get('LUPA_PATH'): sys.path.insert(0, os.environ['LUPA_PATH'])
from lupa.lua53 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
BASE='48baef800fa2bd8e922a1fc6dc56ea59a02c567d'
COMBAT='RootDesk/MyDesk/01_Combat/'
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute('function log(...) end; function isvalid(x) return x ~= nil and not x.destroyed end')
def load(path,name,selected=None,baseline=False):
    text=(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT).decode('utf-8-sig') if baseline else (ROOT/path).read_text(encoding='utf-8-sig'))
    lua.execute(name+'={_T={}}')
    for key,args,body in re.findall(r'^\tmethod \w+ (\w+)\(([^\n]*)\)\n(.*?)^\tend',text,re.M|re.S):
        if selected is not None and key not in selected: continue
        params=','.join(a.strip().split()[-1] for a in args.split(',') if a.strip())
        lua.execute('function '+name+':'+key+'('+params+')\n'+body+'\nend')
    return lua.globals()[name]
load('RootDesk/MyDesk/04_Roguelike/RunManager/AscensionDifficultyLogic.mlua','_AscensionDifficultyLogic', ['ResolveLevel','GetRules'])
lua.execute('_AscensionDifficultyLogic.MaxLevel=7')
methods=['GetBaseAscensionHpBonus','GetAscensionLevel','ResolveDifficultyStats']
old=load(COMBAT+'Components/Shared/BattleWaveComponent.mlua','oldWave',methods,True)
new=load(COMBAT+'Components/Shared/BattleWaveComponent.mlua','newWave',methods)
rows=list(csv.DictReader(io.StringIO((ROOT/'RootDesk/MyDesk/03_Data/EnemyDefinitions.csv').read_text(encoding='utf-8-sig'))))
checks=0
for row in rows:
    # El Nath was added after this legacy baseline and defines its own ascension bonuses.
    if row["EnemyDefinitionId"].startswith("el_nath_"): continue
    d=dict(row)
    for k in ['MaxHp','BasicAttackDamage','AscensionHpBonus']: d[k]=float(d[k] or 1)
    d['IsBoss']=d['IsBoss'].lower()=='true'
    for hp in [d['MaxHp'],1]:
        for level in range(8):
            d['MaxHp']=hp
            lua.globals().definition=lua.table_from(d)
            lua.globals().difficulty='NORMAL' if level==0 else 'ASCENSION_'+str(level)
            lua.execute("session={PlayerEntity={GetComponent=function() return {RunDifficulty=difficulty} end}}; a=oldWave:ResolveDifficultyStats(session,definition); b=newWave:ResolveDifficultyStats(session,definition); assert(a.MaxHp==b.MaxHp and a.BasicAttackDamage==b.BasicAttackDamage, definition.EnemyDefinitionId)")
            checks+=1
load(COMBAT+'Resolvers/BattleDamageLogic.mlua','damage',['ApplyDamage','ApplyStatusDamage','ReduceFlatDamage'])
load(COMBAT+'Components/Shared/BossSummonComponent.mlua','summon')
lua.execute('''
_AugmentRuntimeLogic={GetConditionalDamageBonus=function() return 0 end}
_TutorialRulesLogic={GetDamageAmount=function(_,s,u,a) return a end}
local function unit(team)
 return {Team=team, CurrentHp=100,MaxHp=100,IsDead=false,PoisonDamage=0,NextAttackBonus=0,ComboAttackBonus=0,DefenseBuffAmount=0,AttackDamageCap=0,FlatDamageReduction=0,BurnDamage=0,BurnTurns=0,
 ShouldBlockHostileStatus=function() return false end,
 ConsumeAttackBuffHit=function() return 0 end, ConsumeVenomBuffHit=function() return 0 end,
 ApplyDamage=function(self,a) local before=self.CurrentHp; self.CurrentHp=math.max(0,before-a); return {Success=true,AppliedAmount=before-self.CurrentHp,HpBefore=before,HpAfter=self.CurrentHp,ReachedZero=self.CurrentHp==0} end}
end
local function entity(u) return {GetComponent=function(_,name) if name=='script.BattleUnitComponent' then return u end end} end
local source=unit('Player'); local target=unit('Enemy')
local src=entity(source); local dst=entity(target)
local session={_T={},StrongHitDamageThreshold=3,FindUnitEntity=function(_,id) if id=='s' then return src elseif id=='t' then return dst end end,
PresentDamageNumber=function() end,PlayAcceptedEnemyImpact=function() end,PlayImpactCameraShake=function() end,RefreshPlayerHpSnapshot=function() end, HandleUnitDiedFromSource=function() end}
for _,reduction in ipairs({0,1,2,0.5}) do
 for _,amount in ipairs({1,2,4}) do
  target.FlatDamageReduction=reduction; target.CurrentHp=100
  local expected=math.max(0,amount-reduction)
  assert(damage:ApplyDamage(session,'s','t',amount,'test').AppliedAmount==expected,'direct reduction')
  assert(damage:ApplyStatusDamage(session,'t',amount,'dead-caster','BURN').AppliedAmount==expected,'status reduction')
 end
end
target.FlatDamageReduction=1; target.DefenseBuffAmount=9
assert(damage:ApplyDamage(session,'s','t',2,'test').AppliedAmount==0,'defense minimum then flat zero')
target.DefenseBuffAmount=0; target.AttackDamageCap=1
assert(damage:ApplyDamage(session,'s','t',9,'test').AppliedAmount==0,'cap before flat')
assert(damage:ApplyStatusDamage(session,'t',9,'dead-caster','POISON').AppliedAmount==8,'status ignores attack cap')
target.AttackDamageCap=0; source.NextAttackBonus=2
session._T.AttackBuffHit={SourceUnitId='s',SkillId='test',FixedFollowup=false}
assert(damage:ApplyDamage(session,'s','t',2,'test').AppliedAmount==3,'first hit bonus')
session._T.AttackBuffHit={SourceUnitId='s',SkillId='test',FixedFollowup=true}
assert(damage:ApplyDamage(session,'s','t',2,'test').AppliedAmount==0,'fixed followup one minus armor')
-- Fire boar applies a one-turn burn after any successful non-fixed hit, outside its CSV effect list.
source.Team='Enemy';source.EnemyDefinitionId='region_04_fire_boar';source.NextAttackBonus=0;target.Team='Player';target.FlatDamageReduction=0;session._T={}
assert(damage:ApplyDamage(session,'s','t',2,'flame').AppliedAmount==2)
assert(target.BurnDamage==1 and target.BurnTurns==1,'fire boar burn')

local boss=unit('Enemy');boss.UnitId='boss';boss.EnemyDefinitionId='ellinia_faust';boss.CellIndex=5;boss.Facing='Left';boss.SpawnOrder=1
local player=unit('Player');player.CellIndex=2;player.Facing='Right'
local bossEntity=entity(boss);local playerEntity=entity(player)
local occupied={[2]=true,[5]=true};local slots=8;local spawned={};local removed={};local failAt=0
local s={BattleResult='',StageTurnNumber=10,CellCount=9,CurrentWave=1,RunSeed=1,StageId='',
 FindUnitEntity=function(_,id) if id=='player_01' then return playerEntity end end,
 IsValidCell=function(_,c) return c>=0 and c<9 end}
s.BoardState={CollectLivingEnemies=function() return {bossEntity} end,UnregisterUnit=function(_,id) removed[id]=true end}
s.WaveRuntime={IsSpawnCellFree=function(_,_,c) return c>=0 and c<9 and not occupied[c] end,GetAvailableSlots=function() return slots end}
s.SpawnWaveEnemy=function(_,id,cell,facing,order,definition)
 if failAt>0 and #spawned+1==failAt then return nil end
 local u=unit('Enemy');u.UnitId=id;u.EnemyDefinitionId=definition.EnemyDefinitionId;u.MaxHp=definition.MaxHp;u._T={};u.MarkDead=function(self) self.IsDead=true end
 local e=entity(u);table.insert(spawned,e);return e
end
_EntityService={Destroy=function(_,e) e.destroyed=true end}
_StageWaveRepositoryLogic={GetEnemySpawnDefinition=function(_,pool) return {Success=true,EnemyDefinitionId=pool,MaxHp=5} end}
local function reset()
 summon.Entity=bossEntity;summon.NextSummonTurn=0;summon.SummonSequence=0;summon.SummonedEnemies={};summon.SummonPoolIds='zombie';summon.LowHpSummonPoolIds='';summon.LowHpRatio=0.5;summon.RequireEmptyBoard=false;summon.SummonCooldownTurns=5;summon._T={};spawned={};removed={};failAt=0;slots=8;occupied={[2]=true,[5]=true};boss.CurrentHp=100;boss.IsDead=false
end
reset()
assert(summon:PrepareSummon(s,0)=='0')
assert(summon:TryPreparedSummon(s,'0').Success)
assert(#summon.SummonedEnemies==1 and summon.NextSummonTurn==15)
assert(not summon:IsSummonAvailable(s),'living summon/cooldown block')
summon:RemoveSummon(s);assert(#summon.SummonedEnemies==0 and spawned[1].destroyed and removed['summon_boss_1'])
s.StageTurnNumber=14;assert(not summon:IsSummonAvailable(s));s.StageTurnNumber=15;assert(summon:IsSummonAvailable(s))
reset();summon:PrepareSummon(s,0);occupied[0]=true
assert(not summon:TryPreparedSummon(s,'0').Success and summon.NextSummonTurn==0,'failed summon no cooldown')
reset();boss.EnemyDefinitionId='region_04_commander_skeleton';summon.RequireEmptyBoard=true;summon.SummonPoolIds='soldier|officer';summon.LowHpSummonPoolIds='soldier|officer|region_04_mummydog'
local cells=summon:PrepareSummon(s,0);assert(#summon._T.preparedSummons==2)
boss.CurrentHp=50;assert(summon:TryPreparedSummon(s,cells).Success and #spawned==2,'frozen roster')
summon:RemoveSummon(s);summon.NextSummonTurn=0;spawned={}
cells=summon:PrepareSummon(s,0);assert(#summon._T.preparedSummons==3)
assert(summon:TryPreparedSummon(s,cells).Success and #spawned==3)
assert(spawned[3]:GetComponent('script.BattleUnitComponent').MaxHp==1,'fragile mummy')
summon:RemoveSummon(s);summon.NextSummonTurn=0;spawned={};failAt=2
cells=summon:PrepareSummon(s,0);assert(not summon:TryPreparedSummon(s,cells).Success)
assert(spawned[1].destroyed and summon.NextSummonTurn==0,'partial spawn rollback')
''')
print('PASS ascension baseline cases='+str(checks)+'; direct/status armor, fixed followup, fire burn; Faust/commander frozen roster, cooldown, cleanup, rollback')

load(COMBAT+'Resolvers/EnemyPlanSnapshotLogic.mlua','plans',['GetEnemySkillOverlayKind','GetEnemyActionOverlayKind','GetEnemyQueueIconRuids','GetEnemyQueueOverlayKinds'])
load('RootDesk/MyDesk/02_UI/EnemyIntentHudComponent.mlua','hud',['GetOverlayLabel'])
lua.execute('''
local definitions={
 melee={Success=true,SkillTags='attack|enemy|melee',EffectSetId='push',HudIconRuid='monster'},
 ranged={Success=true,SkillTags='attack|enemy|ranged',EffectSetId='plain',HudIconRuid='monster'},
 seal={Success=true,SkillTags='enemy|status',EffectSetId='seal',HudIconRuid='10a1f3f2cee742ba864fa6aba18beaaa'},
 pull={Success=true,EffectSetId='pull'},swap={Success=true,EffectSetId='swap'},
 frost={Success=true,EffectSetId='frost'}}
local effects={push={{EffectType='DAMAGE'},{EffectType='PUSH'}},plain={{EffectType='DAMAGE'}},seal={{EffectType='SEAL'}},pull={{EffectType='PULL'}},swap={{EffectType='BOSS_SWAP'}},frost={{EffectType='PUSH'},{EffectType='FROSTBITE'}}}
_SkillDefinitionRepositoryLogic={GetSkillDefinition=function(_,id) return definitions[id] or {Success=false} end,GetEffectSteps=function(_,id) return {Success=true,Steps=effects[id] or {}} end}
assert(plans:GetEnemySkillOverlayKind('melee')=='PUSH')
assert(plans:GetEnemySkillOverlayKind('pull')=='PULL')
assert(plans:GetEnemySkillOverlayKind('seal')=='SEAL')
assert(plans:GetEnemySkillOverlayKind('swap')=='SWAP')
assert(plans:GetEnemySkillOverlayKind('frost')=='FROSTBITE','status priority')
assert(plans:GetEnemyActionOverlayKind('ranged','CAST_INTERRUPTIBLE')=='CAST')
assert(plans:GetEnemyActionOverlayKind('ranged','CHARGE_FORWARD')=='CHARGE')
assert(plans:GetEnemyActionOverlayKind('ranged','TELEGRAPH_TILE')=='TELEGRAPH')
assert(plans:GetEnemyActionOverlayKind('ranged','SUMMON_ENEMIES')=='SUMMON')
assert(plans:GetEnemyActionOverlayKind('ranged','BOSS_JUMP_TELEGRAPH')=='JUMP_UP')
assert(plans:GetEnemyActionOverlayKind('ranged','BOSS_LAND_OPPOSITE')=='JUMP_DOWN')
local snap='1~ATTACK~melee>2~ATTACK~ranged>3~ATTACK~seal'
assert(plans:GetEnemyQueueIconRuids(snap)=='ad4304f4d5654158aca63c8c142d5035|ee74ad8d798c489d957a32cf3c375490|10a1f3f2cee742ba864fa6aba18beaaa')
assert(plans:GetEnemyQueueOverlayKinds(snap)=='PUSH|-|SEAL')
for _,kind in ipairs({'SEAL','PUSH','PULL','SWAP','CHARGE','SUMMON','CAST','TELEGRAPH','DEFENSE_BUFF'}) do assert(hud:GetOverlayLabel(kind)~='',kind) end
assert(plans:GetEnemySkillOverlayKind('missing')=='')
''')
print('PASS enemy icon normalization, effect precedence, command badges, queue alignment, Boogie icon preservation')
