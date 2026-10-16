"""HUD dirty-check regressions; Python + lupa (optional LUPA_PATH)."""
import os, re, sys, json
from pathlib import Path
if os.environ.get("LUPA_PATH"): sys.path.insert(0,os.environ["LUPA_PATH"])
from lupa.lua53 import LuaRuntime
root=Path(__file__).resolve().parents[1]
text=(root/"RootDesk/MyDesk/02_UI/BattleHudPresenterLogic.mlua").read_text(encoding="utf-8-sig")
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute("hud={_T={},PendingLocalCommand='',CurrentState={Success=true}}; _UtilLogic={ServerElapsedSeconds=0}; function isvalid(x) return x~=nil end")
for key,args,body in re.findall(r"^\tmethod \w+ (\w+)\(([^\n]*)\)\n(.*?)^\tend",text,re.M|re.S):
    if key not in ["GetHudComponent","HasHudGroupChanged","HaveHudInputsChanged","RefreshState"]:continue
    names=",".join(a.strip().split()[-1] for a in args.split(",") if a.strip())
    lua.execute("function hud:"+key+"("+names+")\n"+body+"\nend")
lua.execute("""
  components={}
  map={GetChildByName=function() return nil end,GetComponent=function(self,name) return components[name] end}
  player={CurrentMap=map,GetComponent=function(self,name) return components[name] end}
  _UserService={LocalPlayer=player}
  session={Entity=map}
  function session:GetPlayerStatusUnit() return components["script.BattleUnitComponent"] end
  function hud:GetBattleSession() return session end
  local names={"BattleTurnComponent","BattleWaveComponent","EnemyIntentComponent","SkillRuntimeStateComponent",
    "PlayerRunInventoryComponent","PlayerRunAugmentComponent","BattleDropComponent","PlayerRunUnionEffectComponent",
    "PlayerRunStateComponent","BattleUnitComponent","PlayerRunCombatStatsComponent"}
  for _,name in ipairs(names) do components["script."..name]={} end
  stats=components["script.PlayerRunCombatStatsComponent"]
  stats.FinalElapsedSeconds=0; stats.IsRunning=true; stats.RunStartTime=0
  assert(hud:HaveHudInputsChanged(session), "initial context")
  assert(not hud:HaveHudInputsChanged(session), "stable context")
  for group,fields in pairs(hud._T.HudInputFields) do
    local component=hud._T.HudInputs[group].Component
    for _,field in ipairs(fields) do
      local before=component[field]
      if group=="Stats" and field=="IsRunning" then component[field]=false
      elseif group=="Stats" then component[field]=1
      else component[field]="changed" end
      assert(hud:HaveHudInputsChanged(session),group.."."..field)
      assert(not hud:HaveHudInputsChanged(session),"stable "..group.."."..field)
      component[field]=before
      assert(hud:HaveHudInputsChanged(session),"restore "..group.."."..field)
    end
  end
  _UtilLogic.ServerElapsedSeconds=0.99
  assert(not hud:HaveHudInputsChanged(session),"same display second")
  _UtilLogic.ServerElapsedSeconds=1
  assert(hud:HaveHudInputsChanged(session),"elapsed display tick")
  assert(not hud:HaveHudInputsChanged(session))
  session.EntryRequestId=2; assert(hud:HaveHudInputsChanged(session),"entry")
  session.HudContextRevision=2; assert(hud:HaveHudInputsChanged(session),"context")
  hud.PendingLocalCommand="MOVE"; assert(hud:HaveHudInputsChanged(session),"pending command")
  hud.PendingLocalCommand=""; assert(hud:HaveHudInputsChanged(session))
  local prior=components["script.EnemyIntentComponent"]
  components["script.EnemyIntentComponent"]={}
  assert(hud:HaveHudInputsChanged(session),"component replacement")
  components["script.EnemyIntentComponent"]=nil
  assert(hud:HaveHudInputsChanged(session),"component removal")
  components["script.EnemyIntentComponent"]=prior
  assert(hud:HaveHudInputsChanged(session),"component restoration")
  hud._T.HudInputs=nil
  assert(hud:HaveHudInputsChanged(session),"unavailable context reset")
  builds=0
  function session:GetBattleUiState() builds=builds+1; error("BUILD_REQUESTED") end
  for i=1,1000 do hud:RefreshState(false) end
  assert(builds==0,"unchanged refresh must skip DTO building")
  session.EnemyPlanSnapshot="late payload"
  local ok,reason=pcall(function() hud:RefreshState(false) end)
  assert(not ok and string.find(reason,"BUILD_REQUESTED"),"payload before revision must invalidate")
  assert(builds==1)
  local ok2=pcall(function() hud:RefreshState(true) end)
  assert(not ok2 and builds==2,"force must bypass dirty check")
""")
ui=(root/"RootDesk/MyDesk/01_Combat/Resolvers/BattleUiStateLogic.mlua").read_text(encoding="utf-8-sig")
build=re.search(r"\tmethod table Build\([^\n]*\)\n(.*?)^\tend",ui,re.M|re.S).group(1)
watch=lua.globals().hud._T.HudInputFields
for variable,group in [("session","Session"),("turnState","Turn"),("waveState","Wave"),("intentState","Intent"),
                       ("runtimeState","Runtime"),("runInventory","Inventory"),("runAugments","Augments"),
                       ("dropRuntime","Drops"),("statusUnit","Status")]:
    used=set(re.findall(r"\b"+variable+r"\.(\w+)",build))-{"Entity","_T"}
    covered=set(watch[group].values())
    assert used<=covered,(group,used-covered)
print(json.dumps({"status":"PASS","watched_fields":sum(len(v) for _,v in watch.items()),"unchanged_refreshes":1000,"unchanged_DTO_builds":0,"context_payload_time_force_checks":"PASS"}))
