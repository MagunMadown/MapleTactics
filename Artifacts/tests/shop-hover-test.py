"""Actual hover methods: coalesce events before changing native UI layout."""
import os, re, sys
from pathlib import Path
sys.path.insert(0, os.environ.get('LUPA_PATH', ''))
from lupa.lua54 import LuaRuntime
lua = LuaRuntime()
root = Path(__file__).resolve().parents[2]
source = (root/'RootDesk/MyDesk/02_UI/RunShopUIComponent.mlua').read_text(encoding='utf-8-sig')
obj = lua.table()
for match in re.finditer(r'^([ \t]+)method\s+\w+\s+(\w+)\((.*?)\)\n(.*?)^\1end\s*$',source,re.M|re.S):
    _,name,params,body=match.groups()
    if name in {'QueueItemTooltip','UpdateTooltipHover','HideItemTooltip','UpdateTooltipPosition'}:
        args=','.join(p.split()[-1] for p in params.split(',') if p.strip())
        obj[name]=lua.execute('return function(self'+(','+args if args else '')+')\n'+body+'\nend')
lua.globals().ui=obj
lua.execute('''
isvalid=function(x) return x~=nil end
Vector2=function(x,y) return {x=x,y=y} end
local cursor=Vector2(200,400)
_InputService={GetCursorPosition=function() return cursor end}
_UILogic={ScreenWidth=1000,ScreenHeight=800,ScreenToLocalUIPosition=function(_,v) return v end}
local tip={Enable=false}; local row={}; local other={}; local pointer=row; local renders=0
ui._T={}; ui.TooltipIndex=0; ui.TooltipSelling=false; ui.TooltipLeaveRemaining=0
ui.GetEntity=function() return tip end
ui.IsPointerInside=function(_,e) return e==pointer and (e~=tip or tip.Enable) end
ui.ShowItemTooltip=function(self,selling,index)
 renders=renders+1; tip.Enable=true; self.TooltipIndex=index; self.TooltipSelling=selling
 self.TooltipSourceRow=pointer; self.TooltipLeaveRemaining=0.45
end
for i=1,100 do ui:QueueItemTooltip(false,1,row) end
assert(renders==0)
ui:UpdateTooltipHover(0.016); assert(renders==1)
ui:QueueItemTooltip(false,1,row); ui:UpdateTooltipHover(0.06); assert(renders==1)
for i=1,100 do ui:QueueItemTooltip(false,1,row); ui:UpdateTooltipHover(0.016) end
assert(renders==1)
pointer=tip; ui:QueueItemTooltip(false,2,other); ui:UpdateTooltipHover(0.2)
assert(renders==1 and ui._T.PendingTooltip==nil)
pointer=other; ui:QueueItemTooltip(false,2,other); ui:UpdateTooltipHover(0.11)
assert(renders==2)
pointer=tip; ui:UpdateTooltipHover(0.016)
pointer={}; ui:UpdateTooltipHover(0.016)
assert(not tip.Enable,'leaving the description closes it on the next frame')
ui:QueueItemTooltip(false,3,row); ui:HideItemTooltip(); assert(ui._T.PendingTooltip==nil)
tip.Enable=true; tip.Parent={UITransformComponent={}}; tip.UITransformComponent={RectSize=Vector2(300,200)}
ui.TooltipIndex=1; ui._T.TooltipAnchorCursor=Vector2(200,400)
ui:UpdateTooltipPosition()
local first=tip.UITransformComponent.anchoredPosition
assert(first.x==374 and first.y==284)
cursor=Vector2(900,700); ui:UpdateTooltipPosition()
assert(tip.UITransformComponent.anchoredPosition==first,'same item must not follow mouse')
ui.TooltipIndex=2; ui._T.TooltipAnchorCursor=cursor; ui:UpdateTooltipPosition()
assert(tip.UITransformComponent.anchoredPosition.x==726,'right edge must flip to left')
print('PASS hover: event bursts coalesced, stable item renders once, tooltip focus, changed row, close cancellation')
''')
