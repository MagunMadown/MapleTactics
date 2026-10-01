"""Execute real scroll methods; unchanged tooltips must not emit layout events."""
import os
import re
import sys
from pathlib import Path
sys.path.insert(0, os.environ.get('LUPA_PATH', ''))
from lupa.lua54 import LuaRuntime

root = Path(__file__).resolve().parents[2]
lua = LuaRuntime()
source = (root / 'RootDesk/MyDesk/02_UI/ScrollableTextComponent.mlua').read_text(encoding='utf-8-sig')
methods = lua.table()
for match in re.finditer(r'^([ \t]+)method\s+\w+\s+(\w+)\((.*?)\)\n(.*?)^\1end\s*$', source, re.M | re.S):
    _, name, params, body = match.groups()
    if name in {'RefreshText', 'GetContentWidth'}:
        args = ','.join(p.split()[-1] for p in params.split(',') if p.strip())
        methods[name] = lua.execute('return function(self' + (',' + args if args else '') + ')\n' + body + '\nend')
lua.globals().scroll = methods
lua.execute('''
isvalid=function(v) return v~=nil end
Vector2=function(x,y) return {x=x,y=y} end
log=function() end
LayoutGroupType={Vertical=1}; ScrollBarVisibility={Hide=0,AutoHide=1}
VerticalScrollBarDirection={TopToBottom=1}; UITransformAxis={Horizontal=0,Vertical=1}
TextOverflowMode={Overflow=1}; TextVerticalAlignmentOption={Top=1}
local events,measures=0,0
local layout={ScrollBarThickness=14,SetScrollNormalizedPosition=function() events=events+1 end,
 ResetScrollPosition=function() events=events+1 end}
local text={Text='description',Font='font',FontSize=20,FontStyle=0,IsRichText=false,
 GetLocalizedText=function(self) return self.Text end}
local body={UITransformComponent={},TextGUIRendererComponent={GetPreferredHeight=function() measures=measures+1; return 200 end}}
scroll.Entity={TextGUIRendererComponent=text,ScrollLayoutGroupComponent=layout,
 UITransformComponent={RectSize=Vector2(300,100)},GetChildByName=function() return body end,Path='tooltip'}
scroll.HideScrollBar=false
scroll:RefreshText()
assert(events==2 and measures==1)
for i=1,100 do scroll:RefreshText() end
assert(events==2 and measures==1,'unchanged tooltip must not reset scrolling or remeasure')
text.Text='another item'; scroll:RefreshText()
assert(events==4 and measures==2)
print('PASS unchanged tooltip: no scroll events or measurements; changed item refreshes')
''')
