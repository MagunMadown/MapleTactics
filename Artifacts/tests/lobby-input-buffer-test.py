import os,re,sys
from pathlib import Path
sys.path.insert(0,os.environ.get('LUPA_PATH',''))
from lupa.lua54 import LuaRuntime
lua=LuaRuntime(); obj=lua.table()
source=(Path(__file__).resolve().parents[2]/'RootDesk/MyDesk/00_Core/LobbyGridMovementComponent.mlua').read_text(encoding='utf-8-sig')
for m in re.finditer(r'^([ \t]+)method\s+\w+\s+(\w+)\((.*?)\)\n(.*?)^\1end\s*$',source,re.M|re.S):
    _,name,params,body=m.groups()
    if name in {'TryLobbyMove','UpdateBufferedMove'}:
        args=','.join(p.split()[-1] for p in params.split(',') if p.strip())
        obj[name]=lua.execute('return function(self,'+args+')\n'+body+'\nend')
lua.globals().ui=obj
lua.execute('''
Vector2=function(x,y) return {x=x,y=y} end
local busy=true; local blocked=false; local requests=0
_PlayerGridMovementLogic={HasLocalMove=function() return busy end,GetProfile=function() return {} end,
 BeginLocalMove=function() busy=true; return 1 end}
local modal={IsOpen=function() return blocked end,IsInputBlocked=function() return blocked end}
_SkillTreeUILogic=modal; _LobbyCharacterSelectionLogic=modal; _LobbyCodexLogic=modal
_UnionSystemUILogic=modal; _GameSettingsLogic=modal
ui._T={moveContext=1}; ui.Entity={}; ui.CellSize=1
ui.GetStepTargetX=function(_,x,d) return x+d end
ui.RequestMove=function(_,d) requests=requests+1; assert(d==-1) end
local player={TransformComponent={WorldPosition={x=0,y=0}}}
ui:TryLobbyMove(player,1); ui:TryLobbyMove(player,-1)
ui:UpdateBufferedMove(player,0.1); assert(requests==0)
busy=false; ui:UpdateBufferedMove(player,0.1); assert(requests==1)
ui:UpdateBufferedMove(player,0.1); assert(requests==1)
ui:TryLobbyMove(player,1); blocked=true; ui:UpdateBufferedMove(player,0.1)
assert(ui._T.BufferedDirection==nil)
blocked=false; ui:TryLobbyMove(player,1); busy=false; ui:UpdateBufferedMove(player,0.7)
assert(requests==1 and ui._T.BufferedDirection==nil)
print('PASS lobby input: latest direction retained, one dispatch after response, modal and expiry cancel')
''')
