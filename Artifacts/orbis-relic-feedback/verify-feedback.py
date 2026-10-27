"""Execute production relic projection + client HUD methods with native JSON/UI boundaries doubled.
Set ORBIS_LUA_PATH to a lupa installation. Maker compilation/rendering are a separate check.
"""
import json,runpy
from pathlib import Path
ns=runpy.run_path(str(Path(__file__).resolve().parents[1]/'orbis-content/verify-relics.py'))
lua,load=ns['lua'],ns['load']
load('RunRelicInventoryUILogic')
lua.execute('''
feedbackChecks={}
feedbackLogs={}
function log(value) table.insert(feedbackLogs,value) end
function DataRef(value) return {DataId=value} end
local R=_ContentRelicTriggerLogic
local o,i,u,run,rt,p=relicFixture()
for _,id in ipairs({'orbis_star_fragment','orbis_moon_fragment','orbis_sun_fragment','orbis_stone_fragment','orbis_papa_crown','orbis_eliza_feather'}) do
 local d=o.Definitions[id];assert(i:GrantRelicFrom(id,'feedback:'..id,d.AcquisitionType,d.AcquisitionSourceId).Success)
end
local session={StageId='orbis_stage_16',EntryRequestId=101,SkillTestMode=false}
_UserService={LocalPlayer=p}
local epilogue=false
_UILayerLogic={IsEpilogueActive=function() return epilogue end}
local ui=setmetatable({ContentHud={Enable=false},ContentSlots={},ContentItems={},ContentPulses={},ContentFlashes={},ContentBattleKey='',LastContentSnapshot='',IsOpen=false},{__index=_RunRelicInventoryUILogic})
for n=1,6 do
 ui.ContentSlots[n]={Root={Enable=false,SpriteGUIRendererComponent={}},Icon={SpriteGUIRendererComponent={}},Label={TextGUIRendererComponent={}},Signature=''}
end
local function frame(delta) ui:UpdateContentHud(delta or 0,run,o,session) end
local function item(id)
 for _,row in ipairs(ui.ContentItems)do if row.RelicId==id then return row end end
end
local function slot(id)
 for n,row in ipairs(ui.ContentItems)do if row.RelicId==id then return ui.ContentSlots[n] end end
 error('missing slot '..id)
end
local function check(label,condition) assert(condition,label);table.insert(feedbackChecks,label) end
local function context(index,count)
 return {SourceUnitId='player_01',SkillId='slash',BattleSession={TurnState={ExecutingTileIndex=index,ExecutingTileIds=count,GetTileIdCount=function(_,ids)return ids end}}}
end
frame()
check('six owned relics only; matching run/battle key',ui.ContentHud.Enable and #ui.ContentItems==6 and ui.ContentBattleKey==o.ActiveBattleKey)
check('initial display does not replay old receipts',next(ui.ContentFlashes)==nil)
check('icons retain authoritative original RUID',slot('orbis_papa_crown').Icon.SpriteGUIRendererComponent.ImageRUID.DataId=='thumbnail://b86fe397c76642988d4a5f6ef3f3ee40')
R:Turned(o);frame()
check('moon charge highlights and is ready',item('orbis_moon_fragment').Ready and slot('orbis_moon_fragment').Label.TextGUIRendererComponent.Text=='충전')
local pulse=item('orbis_moon_fragment').Pulse
frame(0.4);R:Turned(o);frame()
check('repeat turn neither stacks nor restarts highlight',item('orbis_moon_fragment').Pulse==pulse and ui.ContentFlashes.orbis_moon_fragment<1)
frame(1)
check('highlight expires to charged state',slot('orbis_moon_fragment').Label.TextGUIRendererComponent.Text=='충전 완료' and ui.ContentFlashes.orbis_moon_fragment==nil)
local miss=context(1,1);R:SkillStarted(o,miss,true);frame()
check('attack miss still consumes moon readiness',not item('orbis_moon_fragment').Ready and slot('orbis_moon_fragment').Label.TextGUIRendererComponent.Text=='전환 대기')
R:Turned(o)
rt.cooldowns.slash=3
rt.ReduceCooldown=function(self,id,n) local before=self.cooldowns[id] or 0;self.cooldowns[id]=math.max(0,before-n);return {AppliedAmount=before-self.cooldowns[id]} end
local hit=context(1,1);R:SkillStarted(o,hit,true);R:DirectHit(o,hit,'enemy1',1);frame()
check('moon reports actual cooldown refund',rt.cooldowns.slash==2 and slot('orbis_moon_fragment').Label.TextGUIRendererComponent.Text=='쿨 -1')
local count=item('orbis_moon_fragment').Pulse
R:DirectHit(o,hit,'enemy1',1);frame()
check('multi-hit does not duplicate moon receipt',item('orbis_moon_fragment').Pulse==count)
frame(2)
R:PlayerActionStarted(o);R:PlayerActionCompleted(o);frame()
check('stone shows first consumed stationary action',slot('orbis_stone_fragment').Label.TextGUIRendererComponent.Text=='1/2' and not item('orbis_stone_fragment').Ready)
R:PlayerActionStarted(o);R:PlayerActionCompleted(o);frame(2)
check('stone ready remains after highlight expiry',slot('orbis_stone_fragment').Label.TextGUIRendererComponent.Text=='방어 준비' and item('orbis_stone_fragment').Ready)
u:ApplyCellChange(4);frame()
check('moving preserves an earned guard',item('orbis_stone_fragment').Ready)
R:IncomingDirectDamage(o,1);frame()
check('stone reports actual reduction and clears readiness',slot('orbis_stone_fragment').Label.TextGUIRendererComponent.Text=='피해 -1' and not item('orbis_stone_fragment').Ready)
frame(2)
check('spent stone settles to zero progress',slot('orbis_stone_fragment').Label.TextGUIRendererComponent.Text=='0/2')
o.ContentRelicState.Stone=true;R:IncomingDirectDamage(o,0.5);frame()
check('fractional blocked damage retains its actual amount',slot('orbis_stone_fragment').Label.TextGUIRendererComponent.Text=='피해 -0.5')
for n=1,3 do check('ice status blocked '..n,u:ApplyHostileStatus('FROSTBITE',1,0,'ice'..n).Reason=='RELIC_STATUS_IMMUNE') end
frame()
check('three coalesced block receipts retain the latest highlight',item('orbis_eliza_feather').Pulse==3 and slot('orbis_eliza_feather').Label.TextGUIRendererComponent.Text=='상태 차단')
frame(2)
check('feather shows the live immunity window',slot('orbis_eliza_feather').Label.TextGUIRendererComponent.Text=='면역 중' and item('orbis_eliza_feather').Ready)
R:PlayerActionStarted(o);R:PlayerActionCompleted(o);frame()
check('consumed action expires immunity',slot('orbis_eliza_feather').Label.TextGUIRendererComponent.Text=='사용 완료' and not item('orbis_eliza_feather').Ready)
R:QueueStarted(o);local last=context(2,2);R:SkillStarted(o,last,true)
check('finisher bonus remains exactly once',R:FinisherBonus(o,last)==1 and R:FinisherBonus(o,last)==0)
frame()
check('finisher emits a single bonus receipt',item('orbis_star_fragment').Pulse==1 and slot('orbis_star_fragment').Label.TextGUIRendererComponent.Text=='피해 +1')
u.CurrentHp=u.MaxHp;local full=context(1,2);R:SkillStarted(o,full,true);R:DirectHit(o,full,'a',1);R:DirectHit(o,full,'b',1);frame()
check('full HP does not claim healing occurred',item('orbis_sun_fragment').Pulse==0)
R:QueueEnded(o);R:QueueStarted(o);u.CurrentHp=5
local area=context(1,2);R:SkillStarted(o,area,true);R:DirectHit(o,area,'a',1);R:DirectHit(o,area,'b',1);frame()
check('actual sun healing is shown once and carried into run HP',item('orbis_sun_fragment').Pulse==1 and u.CurrentHp==6 and run.RunCurrentHp==6 and slot('orbis_sun_fragment').Label.TextGUIRendererComponent.Text=='회복 +1')
R:WaveStarted(o,1,true);R:WaveStarted(o,2,false);frame()
check('first wave/forced wave emit no recovery receipt',item('orbis_papa_crown').Pulse==0)
R:WaveStarted(o,2,true);R:WaveStarted(o,2,true);frame()
check('crown clear transition heals once',item('orbis_papa_crown').Pulse==1 and u.CurrentHp==7 and slot('orbis_papa_crown').Label.TextGUIRendererComponent.Text=='회복 +1')
-- A final hit and EndBattleEffects may arrive together in one sync update.
frame(2);R:QueueEnded(o);R:QueueStarted(o);u.CurrentHp=5
local lethal=context(1,2);R:SkillStarted(o,lethal,true);R:DirectHit(o,lethal,'last1',1);R:DirectHit(o,lethal,'last2',1);o:EndBattleEffects();frame()
check('final-hit receipt survives result settlement',ui.ContentFlashes.orbis_sun_fragment~=nil and slot('orbis_sun_fragment').Label.TextGUIRendererComponent.Text=='회복 +1')
frame(2)
check('ended battle has no false ready states',slot('orbis_moon_fragment').Label.TextGUIRendererComponent.Text=='전투 종료' and not item('orbis_moon_fragment').Ready)
o:BeginBattle('orbis_stage_16',101);frame()
check('same encounter reinit preserves spent feather without replay',item('orbis_eliza_feather').StateText=='사용 완료' and next(ui.ContentFlashes)==nil)
o:BeginBattle('orbis_stage_16',102);frame()
check('out-of-order new battle snapshot hides stale display',not ui.ContentHud.Enable and ui.ContentBattleKey=='')
session.EntryRequestId=102;frame()
check('new encounter resets readiness and receipts',item('orbis_eliza_feather').StateText=='차단 준비' and item('orbis_eliza_feather').Pulse==0 and next(ui.ContentFlashes)==nil)
R:Turned(o);frame();ui.IsOpen=true;frame()
check('inventory overlay suppresses the compact HUD',not ui.ContentHud.Enable)
ui.IsOpen=false;frame();check('closing inventory restores current readiness',ui.ContentHud.Enable and item('orbis_moon_fragment').Ready)
session.SkillTestMode=true;frame();check('skill-test context hides and resets receipts',not ui.ContentHud.Enable and next(ui.ContentPulses)==nil)
session.SkillTestMode=false;frame();check('return to same encounter never replays an old pulse',ui.ContentHud.Enable and next(ui.ContentFlashes)==nil)
epilogue=true;frame();check('epilogue hides the HUD',not ui.ContentHud.Enable);epilogue=false
session=nil;frame();check('lobby/map transfer hides the HUD',not ui.ContentHud.Enable)
session={StageId='orbis_stage_16',EntryRequestId=102,SkillTestMode=false};run.RunSequence=2;frame()
check('new run cannot render previous run state',not ui.ContentHud.Enable)
run.RunSequence=1;frame();i.RunItemSnapshot=i:SetSnapshotAmount(i.RunItemSnapshot,'orbis_moon_fragment',0);o:Recalculate();frame()
check('selling removes the card and its readiness',item('orbis_moon_fragment')==nil and #ui.ContentItems==5)
-- A free queue/turn-state update cannot rebuild the inventory or invoke combat itself.
check('presentation never writes combat state',o.ContentRelicState.Moon==false and u.CurrentHp==6)
''')
checks=ns['from_lua'](lua.globals().feedbackChecks)
logs=ns['from_lua'](lua.globals().feedbackLogs)
report={'result':'PASS','assertions':len(checks),'checks':checks,'evidence':logs,
 'scope':'Production Lua trigger/projection and client HUD methods; JSON/UI/player boundaries doubled.',
 'maker':'NOT RUN: Maker MCP tools unavailable. Native compilation/rendering/input remain pending.'}
Path(__file__).with_name('lua-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'result':'PASS','assertions':len(checks),'maker':report['maker']},ensure_ascii=False))
