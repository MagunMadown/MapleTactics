import os, sys, re
from pathlib import Path
sys.path.insert(0, os.environ['LUPA_PATH'])
from lupa.lua54 import LuaRuntime
source = Path('RootDesk/MyDesk/02_UI/BattleQueueHudComponent.mlua').read_text(encoding='utf-8')
body = re.search(r'handler HandleQuickbarCancelKey\(KeyDownEvent event\)\n(.*?)\n\tend', source, re.S).group(1)
lua = LuaRuntime()
lua.execute('KeyboardKey={Backspace=8}; calls=0; hud={OnClearClicked=function() calls=calls+1 end}')
lua.execute('function cancel(self,event)\n'+body+'\nend')
lua.execute('''
for _,visible in ipairs({false,true}) do
 for _,allowed in ipairs({false,true}) do
  for _,key in ipairs({8,27,32}) do
   calls=0; hud.IsHudContextVisible=visible; hud.CanClearQueue=allowed
   cancel(hud,{key=key})
   assert(calls==((visible and allowed and key==8) and 1 or 0))
  end
 end
end
''')
assert 'ClearButton' not in source and 'ClearClickHandler' not in source
assert 'self.CanClearQueue = uiState.Commands.CanClear' in source
assert '_BattleHudPresenterLogic:RequestClearQueue()' in source
print('PASS: actual cancel handler, 12 visibility/permission/key cases; original clear request retained. Native Maker: NOT RUN.')
