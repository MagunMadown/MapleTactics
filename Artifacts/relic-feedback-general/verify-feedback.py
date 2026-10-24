"""Run shared stateful-relic feedback through production Lua. Engine UI/player boundaries are doubles."""
import json,runpy,re
from pathlib import Path
ns=runpy.run_path(str(Path(__file__).resolve().parents[1]/'orbis-content/verify-relics.py'))
lua,load=ns['lua'],ns['load']
load('RunRelicInventoryUILogic');load('SkillRuntimeStateComponent')
root=Path(__file__).resolve().parents[2]
for name in ['RunRelicFeedbackLogic','ContentRelicTriggerLogic','PlayerRunRelicEffectComponent','RunRelicInventoryUILogic']:
    source=next((root/'RootDesk/MyDesk').rglob(name+'.mlua')).read_text(encoding='utf-8-sig')
    converted=[]
    for line in source.splitlines():
        stripped=line.strip()
        if stripped.startswith('@') or stripped.startswith('property '): continue
        if re.match(r'^script \w+ extends \w+$',stripped): converted.append('do');continue
        match=re.match(r'^(?:method \w+|handler) (\w+)\((.*)\)$',stripped)
        if match:
            args=','.join(a.strip().split()[-1] for a in match[2].split(',') if a.strip())
            converted.append('local function '+match[1]+'('+args+')');continue
        converted.append(line)
    valid,error=lua.eval('function(source) local f,e=load(source);return f~=nil,e end')('\n'.join(converted))
    assert valid,(name,error)
lua.execute('''
checks={};feedbackLogs={}
function log(value) table.insert(feedbackLogs,value) end
function DataRef(value) return {DataId=value} end
local F=_RunRelicFeedbackLogic
local function check(label,condition) assert(condition,label);table.insert(checks,label) end
local function fixture(job,ids)
 local o,i,u,r,rt,p=relicFixture(job)
 p.Name='feedback-test';rt.Entity=p;rt.RemainingCooldowns={};rt.CooldownSnapshot='';rt.CooldownRevision=0
 rt.ReduceCooldown=nil;setmetatable(rt,{__index=_SkillRuntimeStateComponent})
 local session={StageId='orbis_stage_16',EntryRequestId=101,TurnNumber=0,SkillTestMode=false}
 p.CurrentMap={GetComponent=function(_,name) if name=='script.BattleSessionComponent' then return session end end}
 for _,id in ipairs(ids or {}) do assert(i:GrantRelic(id,'feedback:'..id).Success,id) end
 local ui=setmetatable({ContentHud={Enable=false},ContentSlots={},ContentItems={},ContentPulses={},ContentFlashes={},ContentBattleKey='',LastContentSnapshot='',IsOpen=false},{__index=_RunRelicInventoryUILogic})
 for n=1,24 do ui.ContentSlots[n]={Root={Enable=false,SpriteGUIRendererComponent={}},Icon={SpriteGUIRendererComponent={}},Label={TextGUIRendererComponent={}},Signature=''} end
 _UserService={LocalPlayer=p};_UILayerLogic={IsEpilogueActive=function() return false end}
 local c={o=o,i=i,u=u,r=r,rt=rt,p=p,s=session,ui=ui}
 function c:frame(delta) ui:UpdateContentHud(delta or 0,r,o,session) end
 function c:item(id) for _,v in ipairs(ui.ContentItems) do if v.RelicId==id then return v end end end
 function c:slot(id) for n,v in ipairs(ui.ContentItems) do if v.RelicId==id then return ui.ContentSlots[n] end end end
 function c:text(id) return self:slot(id).Label.TextGUIRendererComponent.Text end
 function c:legacy(id) i.RunItemSnapshot=i:SetSnapshotAmount(i.RunItemSnapshot,id,1);o:Recalculate() end
 function c:nextBattle() o:EndBattleEffects();session.EntryRequestId=session.EntryRequestId+1;o:BeginBattle(session.StageId,session.EntryRequestId);self:frame() end
 c:frame();return c
end
local c=fixture('warrior',{'pot_lid','rainbow_rice_cake','icarus_cape','half_earrings','soft_shoes','power_medal','work_gloves'})
check('stateful effects displayed and constant stat relic excluded',#c.ui.ContentItems==6 and c:item('work_gloves')==nil)
check('first guard and finite charges start ready',c:item('pot_lid').Ready and c:text('rainbow_rice_cake')=='방어 3회')
check('first guard prevents damage before finite guard',c.o:ResolveIncomingDamage(8,10)==0 and c.o.RemainingUses.rainbow_rice_cake==3)
c:frame();check('first guard highlights once and clears readiness',c:text('pot_lid')=='피해 무효' and not c:item('pot_lid').Ready)
c:frame(2);check('first guard settles to used',c:text('pot_lid')=='사용 완료')
for n=2,0,-1 do
 check('finite guard consumes actual charge '..n,c.o:ResolveIncomingDamage(8,10)==0 and c.o.RemainingUses.rainbow_rice_cake==n)
 c:frame();if n>0 then c:frame(2);check('finite charge label '..n,c:text('rainbow_rice_cake')=='방어 '..n..'회') end
end
check('final guard is removed from inventory but its receipt remains',c.i:GetSnapshotAmount(c.i.RunItemSnapshot,'rainbow_rice_cake')==0 and c:item('rainbow_rice_cake').Transient and c:text('rainbow_rice_cake')=='방어 소진')
c:frame(2);check('depleted card hides when its highlight ends',not c:slot('rainbow_rice_cake').Root.Enable)
c.o:Recalculate();c:frame();check('recalculation cannot replay depleted receipt',not c:slot('rainbow_rice_cake').Root.Enable)
c:nextBattle();check('depleted finite guard cannot refill next battle',c:item('rainbow_rice_cake')==nil and c.o.RemainingUses.rainbow_rice_cake==0)
check('new-battle first guard still takes precedence',c.o:ResolveIncomingDamage(1,5)==0)
c:legacy('von_leon_war_belt');check('legacy survival preserves gameplay damage',c.o:ResolveIncomingDamage(20,5)==4);c:frame()
check('survival receipt matches one-HP protection',c:text('von_leon_war_belt')=='체력 1' and not c:item('von_leon_war_belt').Ready)
local pulse=c:item('von_leon_war_belt').Pulse;c.o:ResolveIncomingDamage(20,5);c:frame();check('spent survival cannot emit a second receipt',c:item('von_leon_war_belt').Pulse==pulse)

c=fixture('mage',{'icarus_cape'});c.rt.RemainingCooldowns.slash=3;c.o:OnSkillCompleted('slash');c:frame()
check('first completed skill reports actual cooldown reduction',c.rt:GetRemainingCooldown('slash')==2 and c:text('icarus_cape')=='쿨 -1' and not c:item('icarus_cape').Ready)
c.o:OnSkillCompleted('slash');c:frame();check('first skill cannot trigger twice',c:item('icarus_cape').Pulse==1 and c.rt:GetRemainingCooldown('slash')==2)
c=fixture('mage',{'icarus_cape'});c.o:OnSkillCompleted('slash');c:frame();check('zero cooldown consumes first-use state without false refund',c:item('icarus_cape').Pulse==0 and c:text('icarus_cape')=='사용 완료')

c=fixture('warrior',{'soft_shoes','half_earrings','power_medal'});c.u.CurrentHp=4;c.rt.RemainingCooldowns={slash=3,other=1}
c.o:OnEnemyKilled('one');c:frame()
check('first kill healing reports the actual floor-25-percent heal',c.u.CurrentHp==6 and c.r.RunCurrentHp==6 and c:text('soft_shoes')=='회복 +2')
check('first kill cooldown uses actual runtime reduction',c.rt:GetRemainingCooldown('slash')==2 and c.rt:GetRemainingCooldown('other')==0 and c:text('half_earrings')=='쿨 감소')
check('power medal shows one gained stack',c:text('power_medal')=='공격 +1')
c.o:OnEnemyKilled('one');c:frame();check('duplicate kill cannot repeat receipts',c:item('soft_shoes').Pulse==1 and c:item('half_earrings').Pulse==1 and c:item('power_medal').Pulse==1)
for _,id in ipairs({'two','three','four'})do c.o:OnEnemyKilled(id) end;c:frame()
check('power medal caps at three without false extra pulse',c.o.BattleKillAttackBonus==3 and c:item('power_medal').Pulse==3 and c:text('power_medal')=='공격 +3')
c:nextBattle();check('new battle resets stacks and first-kill readiness',c:text('power_medal')=='공격 +0' and c:item('soft_shoes').Ready and c:item('half_earrings').Ready and next(c.ui.ContentFlashes)==nil)
c=fixture('warrior',{'soft_shoes','half_earrings'});c.u.CurrentHp=c.u.MaxHp;c.o:OnEnemyKilled('full');c:frame()
check('full HP and empty cooldowns produce no false application flash',c:item('soft_shoes').Pulse==0 and c:item('half_earrings').Pulse==0 and not c:item('soft_shoes').Ready)

c=fixture('warrior',{});c:legacy('romeo_pendant');c.o:OnEnemyKilled('a');c:frame();check('run-wide three-kill progress shows one',c:text('romeo_pendant')=='1/3')
c.o:OnEnemyKilled('b');c:nextBattle();check('three-kill progress survives battle transitions',c:text('romeo_pendant')=='2/3')
c.o:OnEnemyKilled('c');c:frame();check('third kill heals once and reports actual amount',c.u.CurrentHp==6 and c:text('romeo_pendant')=='회복 +1' and c.o.KillHealProgress==0)
c:frame(2);check('three-kill progress returns to zero after flash',c:text('romeo_pendant')=='0/3')

c=fixture('archer',{'bronze_arrow'});c.s.TurnNumber=10;c.rt.RemainingCooldowns.slash=4;c.o:OnSkillKill('slash',10);c:frame()
check('bronze arrow resets the actual skill and shows five-turn wait',c.rt:GetRemainingCooldown('slash')==0 and c:item('bronze_arrow').StateText=='대기 5턴' and c:text('bronze_arrow')=='쿨 초기화')
c.rt.RemainingCooldowns.slash=3;c.o:OnSkillKill('slash',11);c:frame();check('internal cooldown rejection does not replay reset',c.rt:GetRemainingCooldown('slash')==3 and c:item('bronze_arrow').Pulse==1)
c.s.TurnNumber=14;c.o:OnUpdate(0.06);c:frame(2);check('existing owner update refreshes internal wait without gameplay mutations',c:text('bronze_arrow')=='대기 1턴' and c.o.EffectReadyTurns.KILL_SKILL_RESET_INTERVAL==15)
local count=0;local publish=F.Publish;F.Publish=function(self,owner)count=count+1;return publish(self,owner)end
F:UpdateClock(c.o);F:UpdateClock(c.o);check('unchanged turn performs no display publication',count==0)
c.s.TurnNumber=15;F:UpdateClock(c.o);c:frame();check('deadline becomes ready with one publication',count==1 and c:item('bronze_arrow').Ready and c:text('bronze_arrow')=='준비 완료');F.Publish=publish
c.rt.RemainingCooldowns={};c.o:OnSkillKill('slash',15);c:frame();check('zero cooldown does not consume reset availability',c:item('bronze_arrow').Ready and c:item('bronze_arrow').Pulse==1)

c=fixture('archer',{'breeze_feather'});c.s.TurnNumber=10;check('breeze grants the existing free-load effect',c.o:OnSkillLoaded('slash',10,false));c:frame();check('breeze shows actual activation and wait',c:text('breeze_feather')=='무료 장전' and c:item('breeze_feather').StateText=='대기 5턴')
c=fixture('archer',{'breeze_feather'});c.s.TurnNumber=10;check('naturally free load preserves relic charge',not c.o:OnSkillLoaded('slash',10,true));c:frame();check('natural free load has no relic pulse',c:item('breeze_feather').Ready and c:item('breeze_feather').Pulse==0)

c=fixture('mage',{'platinum_book'});c.s.TurnNumber=10;c.o:OnSkillLoaded('slash',10,false);c:frame()
check('platinum displays a reserved loaded effect',c:text('platinum_book')=='장전 예약' and c.o.LoadedCooldownReductions.slash==3)
c.o:CancelLoadedSkill('slash');c:frame(2);check('cancelled loaded skill reveals remaining internal wait',c:text('platinum_book')=='대기 3턴' and next(c.o.LoadedCooldownReductions)==nil)
c.s.TurnNumber=13;F:UpdateClock(c.o);c.o:OnSkillLoaded('slash',13,false);c:frame()
check('platinum reservation preserves existing reduction amount',c.o:ConsumeLoadedCooldownReduction('slash')==3);c:frame()
check('consumed reservation has its own accurate use receipt',c:text('platinum_book')=='예약 사용' and c:item('platinum_book').StateText=='대기 3턴')
local prior=c:item('platinum_book').Pulse;check('same loaded reservation cannot consume twice',c.o:ConsumeLoadedCooldownReduction('slash')==0);c:frame();check('repeat consume has no duplicate use pulse',c:item('platinum_book').Pulse==prior)
c.i.RunItemSnapshot=c.i:SetSnapshotAmount(c.i.RunItemSnapshot,'platinum_book',0);c.o:Recalculate();c:frame();check('sale removes all readiness and current highlight',not c.ui.ContentHud.Enable and c:item('platinum_book')==nil)

c=fixture('pirate',{'wrist_band'});c.s.TurnNumber=4;check('repeat relic consumes availability once',c.o:ConsumeReadyEffect('REPEAT_SKILL_INTERVAL',4));c:frame()
check('repeat display reports activation and four-turn wait',c:text('wrist_band')=='추가 시전' and c:item('wrist_band').StateText=='대기 4턴')
check('repeat availability cannot stack',not c.o:ConsumeReadyEffect('REPEAT_SKILL_INTERVAL',4));c:frame();check('duplicate repeat request has no pulse',c:item('wrist_band').Pulse==1)
c.s.TurnNumber=8;F:UpdateClock(c.o);c:frame(2);check('repeat deadline becomes ready',c:text('wrist_band')=='준비 완료' and c:item('wrist_band').Ready)

c=fixture('warrior',{'rainbow_rice_cake'});for n=1,3 do c.o:ResolveIncomingDamage(1,10) end;c:frame()
check('only depleted relic retains a visible final flash',c.ui.ContentHud.Enable and c:text('rainbow_rice_cake')=='방어 소진')
c:frame(2);check('only depleted relic leaves no empty HUD title',not c.ui.ContentHud.Enable)
c=fixture('mage',{'icarus_cape'});c.rt.RemainingCooldowns.slash=2;c.o:OnSkillCompleted('slash');c:frame();c:frame(2)
c:legacy('ice_knight_earring');c:frame();check('new relic sharing an already-triggered effect does not replay its receipt',next(c.ui.ContentFlashes)==nil and not c:item('ice_knight_earring').Ready)
for _,id in ipairs({'icarus_cape','ice_knight_earring'})do c.i.RunItemSnapshot=c.i:SetSnapshotAmount(c.i.RunItemSnapshot,id,0) end;c.o:Recalculate();c:frame()
c:legacy('icarus_cape');c:frame();check('selling and reacquiring cannot replay an old shared-effect receipt',next(c.ui.ContentFlashes)==nil)

for _,job in ipairs({'warrior','mage','archer','thief','pirate'})do
 c=fixture(job,{})
 for id in pairs(c.o.Definitions)do c.i.RunItemSnapshot=c.i:SetSnapshotAmount(c.i.RunItemSnapshot,id,1) end
 c.o:Recalculate();c:frame()
 check('all eligible stateful relics fit the authored HUD for '..job,#c.ui.ContentItems<=24 and #c.ui.ContentItems>6 and c.ui.ContentSlots[7].Root.Enable)
 for _,item in ipairs(c.ui.ContentItems)do check('display honors job restriction '..job..':'..item.RelicId,c.o:IsJobAllowed(item.RelicId)) end
end
''')
checks=ns['from_lua'](lua.globals().checks)
report={'result':'PASS','assertions':len(checks),'checks':checks,'evidence':ns['from_lua'](lua.globals().feedbackLogs),
 'scope':'Production Lua relic owner/projector/cooldown/client display methods with native UI/player boundaries doubled.',
 'maker':'NOT RUN: Maker execution MCP tools unavailable; native compilation/rendering/input remain pending.'}
Path(__file__).with_name('lua-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'result':'PASS','assertions':len(checks),'maker':report['maker']},ensure_ascii=False))
