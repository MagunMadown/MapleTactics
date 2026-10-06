import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.environ['LUPA_PATH'])
from lupa.lua54 import LuaRuntime

root = Path(__file__).resolve().parents[2]
source = (root / 'RootDesk/MyDesk/02_UI/BattleQueueHudComponent.mlua').read_text(encoding='utf-8-sig')
settings_source = (root / 'RootDesk/MyDesk/00_Core/GameSettingsLogic.mlua').read_text(encoding='utf-8-sig')
body = re.search(r'handler HandleQuickbarCancelKey\(KeyDownEvent event\)\n(.*?)\n\tend', source, re.S).group(1)
lua = LuaRuntime()
lua.execute('''
log=function() end
_UnionCoinShopLogic={IsOpen=false}
_GameSettingsLogic={_T={KeyEnums={}},Bindings={}}
for code=1,400 do _GameSettingsLogic._T.KeyEnums[code]=code end
function _GameSettingsLogic:EnsureCatalogCache() end
_UILayerLogic={HasBlockingWindow=function() return _GameSettingsLogic.IsWindowOpen or _GameSettingsLogic.IsMenuOpen or _UnionCoinShopLogic.IsOpen end}
_BattleHudPresenterLogic={GetBattleSession=function() return nil end}
hud={_T={},GetSlotSkillId=function(_,slot) return tostring(slot) end,OnClearClicked=function() calls=calls+1 end,
     RequestSlotSkill=function(_,slot,execute)
         assert(execute==false); slotCalls[#slotCalls+1]=slot
     end}
function reset()
    calls=0; slotCalls={}
    hud.IsHudContextVisible=true; hud.CanClearQueue=true; hud.IsMapTransferPending=false
    _GameSettingsLogic.IsWindowOpen=false; _GameSettingsLogic.IsCapturingKey=false
    _GameSettingsLogic.IsMenuOpen=false; _UnionCoinShopLogic.IsOpen=false
    _GameSettingsLogic:ApplyDefaultBindings()
end
''')
for name in ('GetActionCatalog', 'ApplyDefaultBindings', 'IsActionKey', 'IsInputBlocked'):
    match = re.search(r'\tmethod\s+\w+\s+' + name + r'\((.*?)\)\n(.*?)\n\tend', settings_source, re.S)
    params, method_body = match.groups()
    args = ','.join(param.strip().split()[-1] for param in params.split(',') if param.strip())
    lua.execute('function _GameSettingsLogic:' + name + '(' + args + ')\n' + method_body + '\nend')
lua.execute('_GameSettingsLogic._T.Actions=_GameSettingsLogic:GetActionCatalog()')
lua.execute('function cancel(self,event)\n'+body+'\nend')
lua.execute('''
caseCount=0
-- Preserve all 12 original visibility, permission and default-cancel cases.
for _,visible in ipairs({false,true}) do
 for _,allowed in ipairs({false,true}) do
  for _,key in ipairs({8,27,32}) do
   reset(); hud.IsHudContextVisible=visible; hud.CanClearQueue=allowed
   cancel(hud,{key=key})
   assert(calls==((visible and allowed and key==8) and 1 or 0))
   assert(#slotCalls==0); caseCount=caseCount+1
  end
 end
end
-- Every input gate blocks both cancellation and slot dispatch.
for gate=1,6 do
 for _,key in ipairs({8,49,257}) do
  reset()
  if gate==1 then _GameSettingsLogic.IsWindowOpen=true
  elseif gate==2 then _GameSettingsLogic.IsCapturingKey=true
  elseif gate==3 then _GameSettingsLogic.IsMenuOpen=true
  elseif gate==4 then _UnionCoinShopLogic.IsOpen=true
  elseif gate==5 then hud.IsMapTransferPending=true
  else hud.IsHudContextVisible=false end
  cancel(hud,{key=key})
  assert(calls==0 and #slotCalls==0); caseCount=caseCount+1
 end
end
-- Both authored bindings of all six slots use the existing registration path.
for slot=1,6 do
 for _,key in ipairs({48+slot,256+slot}) do
  reset(); hud.CanClearQueue=false
  cancel(hud,{key=key})
  assert(calls==0 and #slotCalls==1 and slotCalls[1]==slot); caseCount=caseCount+1
 end
end
-- Rebinding cancellation removes the old key and respects both new bindings.
for _,key in ipairs({8,99,13,27,0}) do
 reset(); _GameSettingsLogic.Bindings.CLEAR_QUEUE={99,13}
 cancel(hud,{key=key})
 assert(calls==((key==99 or key==13) and 1 or 0) and #slotCalls==0)
 caseCount=caseCount+1
end
-- Reassigned slot keys likewise replace the original row and numpad keys.
for _,key in ipairs({54,262,122,9}) do
 reset(); _GameSettingsLogic.Bindings.SLOT_6={122,9}
 cancel(hud,{key=key})
 local expected=(key==122 or key==9) and 1 or 0
 assert(calls==0 and #slotCalls==expected)
 if expected==1 then assert(slotCalls[1]==6) end
 caseCount=caseCount+1
end
''')
assert 'ClearButton' not in source and 'ClearClickHandler' not in source
assert 'self.CanClearQueue = uiState.Commands.CanClear' in source
assert '_BattleHudPresenterLogic:RequestClearQueue()' in source
assert lua.globals().caseCount == 51
print('PASS: actual quickbar handler and settings methods, 51 cases (12 original + input gates/map transfer + slots + rebindings); original clear request retained. Native Maker: NOT RUN.')
