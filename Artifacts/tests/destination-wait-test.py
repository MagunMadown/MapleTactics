"""Actual server wait methods: delayed availability and stale-run cancellation."""
import os, re, sys
from pathlib import Path
sys.path.insert(0, os.environ.get('LUPA_PATH', ''))
from lupa.lua54 import LuaRuntime
lua=LuaRuntime()
root=Path(__file__).resolve().parents[2]
source=(root/'RootDesk/MyDesk/02_UI/MapTeleportManager.mlua').read_text(encoding='utf-8-sig')
obj=lua.table()
for m in re.finditer(r'^([ \t]+)method\s+\w+\s+(\w+)\((.*?)\)\n(.*?)^\1end\s*$',source,re.M|re.S):
    _,name,params,body=m.groups()
    if name in {'WaitForDestination','IsPendingTransferCurrent','ConsumePendingTransfer'}:
        args=','.join(p.split()[-1] for p in params.split(',') if p.strip())
        obj[name]=lua.execute('return function(self,'+args+')\n'+body+'\nend')
lua.globals().nav=obj
lua.execute('''
isvalid=function(v) return v~=nil end
local callbacks={}; local available=false; local moved=0; local failed=0
_EntityService={GetEntityByPath=function() if available then return {MapComponent={}} end end}
_TimerService={SetTimerOnce=function(_,fn) table.insert(callbacks,fn); return #callbacks end}
nav.TeleportPlayer=function() moved=moved+1 end
nav.NotifyUnavailableDestination=function() failed=failed+1 end
local function setup()
 callbacks={}; available=false
 local map={}; local run={RunSequence=1}
 local player={CurrentMap=map,GetComponent=function() return run end}
 local p={UserId='u',PlayerEntity=player,SourceMap=map,RunSequence=1,TimerId=0}
 nav.PendingTransfers={u=p}
 return p,player,run
end
local p=setup(); nav:WaitForDestination(p,'reward',{},'VICTORY',20)
assert(moved==0 and #callbacks==1)
available=true; callbacks[1](); callbacks[1]()
assert(moved==1 and nav.PendingTransfers.u==nil,'only one dispatch when map appears')
p=setup(); nav:WaitForDestination(p,'reward',{},'VICTORY',20)
for i=1,20 do callbacks[i]() end
assert(failed==1 and moved==1 and #callbacks==20 and nav.PendingTransfers.u==nil)
local player,run
p,player,run=setup(); nav:WaitForDestination(p,'reward',{},'VICTORY',20)
run.RunSequence=2; available=true; callbacks[1](); assert(moved==1)
p,player=setup(); nav:WaitForDestination(p,'reward',{},'VICTORY',20)
player.CurrentMap={}; available=true; callbacks[1](); assert(moved==1)
p=setup(); nav:WaitForDestination(p,'reward',{},'VICTORY',20)
local replacement={}; nav.PendingTransfers.u=replacement
available=true; callbacks[1](); assert(moved==1 and nav.PendingTransfers.u==replacement)
print('PASS destination wait: delayed readiness, one dispatch, bounded timeout, new run/map/request cancellation')
''')
