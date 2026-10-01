"""Actual server routing and authorization for the shared reward map."""
import os,re,sys
from pathlib import Path
sys.path.insert(0,os.environ.get('LUPA_PATH',''))
from lupa.lua54 import LuaRuntime
lua=LuaRuntime(); root=Path(__file__).resolve().parents[2]
def method(path,name):
    text=(root/path).read_text(encoding='utf-8-sig')
    m=re.search(r'^([ \t]+)method\s+\w+\s+'+name+r'\((.*?)\)\n(.*?)^\1end\s*$',text,re.M|re.S)
    args=','.join(p.split()[-1] for p in m[2].split(',') if p.strip())
    return lua.execute('return function(self,'+args+')\n'+m[3]+'\nend')
base='RootDesk/MyDesk/04_Roguelike/'
lua.globals().route=method(base+'RunManager/StageTransitionManagerLogic.mlua','DetermineIntermediateMap')
lua.globals().upgrade=method(base+'SkillStage/UpgradeSkillStageLogic.mlua','BuildUpgradeState')
lua.globals().newOffer=method(base+'SkillStage/NewSkillStageChoiceComponent.mlua','ResolveOffer')
lua.execute('''
isvalid=function(v) return v~=nil end
local run={RunSequence=1,LastBattleRecordKey='battle1',RewardSelectionContext=''}
local player={CurrentMap={Name='new_skill_stage'},GetComponent=function() return run end}
local rolls=0
local manager={ChooseRewardKind=function() rolls=rolls+1; return 'UPGRADE' end}
assert(route(manager,player,'stage')=='new_skill_stage')
assert(run.RewardSelectionContext=='1:battle1|UPGRADE')
assert(route(manager,player,'stage')=='new_skill_stage' and rolls==1)
assert(newOffer({},player,1).Reason=='WRONG_REWARD_KIND')
run.LastBattleRecordKey='battle2'
manager.ChooseRewardKind=function() rolls=rolls+1; return 'NEW' end
assert(route(manager,player,'stage')=='new_skill_stage' and rolls==2)
assert(run.RewardSelectionContext=='1:battle2|NEW')
assert(upgrade({},player).Reason=='WRONG_REWARD_KIND')
run.RunSequence=2
assert(route(manager,player,'stage')=='new_skill_stage' and rolls==3)
assert(run.RewardSelectionContext=='2:battle2|NEW')
print('PASS shared reward: one destination, one roll per battle, new-run isolation, cross-kind requests rejected')
''')
