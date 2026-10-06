"""Actual upgrade UI entry method; offline lifecycle and delayed-response checks."""
import os, re, sys
from pathlib import Path
sys.path.insert(0, os.environ.get('LUPA_PATH', ''))
from lupa.lua54 import LuaRuntime
root = Path(__file__).resolve().parents[2]
source = (root/'RootDesk/MyDesk/04_Roguelike/SkillStage/UpgradeSkillStageUIComponent.mlua').read_text(encoding='utf-8-sig')
body = re.search(r'\tmethod void OnUpdate\(number delta\)\n(.*?)^\tend', source, re.M|re.S).group(1)
lua = LuaRuntime()
lua.globals().update = lua.execute('return function(self,delta)\n'+body+'\nend')
lua.execute('''
isvalid=function(v) return v~=nil and not v.destroyed end
log=function() end; log_error=function() end
local requests,raises=0,0
_UpgradeSkillStageLogic={RequestUpgradeState=function() requests=requests+1 end}
_GameUIPolishLogic={BringUIGroupToFront=function() raises=raises+1 end,ShowToast=function() end}
_UILayerLogic={PushWindow=function() raises=raises+1 end,PopWindow=function() end}
local run={RunSequence=1,LastBattleRecordKey='clear',RewardSelectionContext='1:clear|UPGRADE'}
_UserService={LocalPlayer={CurrentMap={Name='new_skill_stage'},GetComponent=function() return run end}}
local ui={_T={},ActiveMapName='battle',UpgradeContextName='UPGRADE',PanelEntity={Enable=false},
 Entity={Parent={}},StatusText={},ApplyLocked=false,AnimateHiddenGlow=function() end}
ui.ResetSelection=function() error('interrupted initialization') end
assert(pcall(update,ui,0.1))
assert(ui.ActiveMapName=='battle','failed initialization must remain retryable')
ui.ResetSelection=function(self) self._T.UpgradeStateReady=false end
update(ui,3)
assert(ui.PanelEntity.Enable and ui.Entity.Parent.Enable and raises==1 and requests==1)
for i=1,20 do update(ui,1) end
assert(requests==4,'read retries must be bounded')
ui._T.UpgradeStateReady=true
update(ui,10); assert(requests==4)
_UserService.LocalPlayer.CurrentMap={Name='battle'}
update(ui,0.1); assert(not ui.PanelEntity.Enable)
_UserService.LocalPlayer.CurrentMap={Name='new_skill_stage'}
update(ui,0.1); assert(requests==5 and raises==2)
run.RewardSelectionContext='1:clear|NEW'
update(ui,0.1); assert(not ui.PanelEntity.Enable and requests==5)
run.RewardSelectionContext=''
update(ui,0.1); assert(not ui.PanelEntity.Enable and requests==5)
run.RewardSelectionContext='1:clear|UPGRADE'
update(ui,0.1); assert(ui.PanelEntity.Enable and requests==6)
print('PASS upgrade entry: interrupted setup recovery, visibility, bounded retry, ready state, re-entry')
''')
