"""Run: LUPA_PATH=/path/to/lupa python3 Artifacts/tests/new-player-tutorial-test.py.

Executes current mLua bodies with engine services mocked; Maker play is still required.
"""
from pathlib import Path
import re
import runpy

base = runpy.run_path(str(Path(__file__).with_name("union-free-job-token-test.py")))
lua, load = base["lua"], base["load_methods"]
root = base["ROOT"]
profile = "RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.mlua"
tutorial = "RootDesk/MyDesk/00_Core/Lobby/NewPlayerTutorialLogic.mlua"
session = "RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua"
lua.globals().repo.CompleteTutorial = load(profile, {"CompleteTutorial"}).CompleteTutorial
lua.globals().tutorial = load(tutorial, {"IsActive", "IsEntry", "ReleasePlayer", "RequestStart", "Finish", "GetGuideMessage"})
lua.globals().session = load(session, {"TryQueueTile", "ApplyDamage", "FinishEnemyToPlayerTransition", "RequestContinueResult"})
lua.globals()._EnemyTurnExecutionLogic = load(
    "RootDesk/MyDesk/01_Combat/Resolvers/EnemyTurnExecutionLogic.mlua", {"FinishEnemyToPlayerTransition"})
lua.globals()._BattleDamageLogic = load(
    "RootDesk/MyDesk/01_Combat/Resolvers/BattleDamageLogic.mlua", {"ApplyDamage"})
lua.globals().unitDamage = load("RootDesk/MyDesk/01_Combat/Components/Shared/BattleUnitComponent.mlua", {"ApplyDamage"}).ApplyDamage
lua.globals().run = load("RootDesk/MyDesk/04_Roguelike/RunManager/RunManagerLogic.mlua", {"InitializeNewRunOwnedState"})
lua.globals().wave = load("RootDesk/MyDesk/01_Combat/Components/Shared/BattleWaveComponent.mlua", {"SpawnWave"})

# Compile every changed method, not just the paths executed below.
for path in (profile, tutorial, session,
             "RootDesk/MyDesk/01_Combat/Components/Shared/BattleWaveComponent.mlua",
             "RootDesk/MyDesk/01_Combat/Resolvers/BattleGatewayLogic.mlua",
             "RootDesk/MyDesk/04_Roguelike/RunManager/RunManagerLogic.mlua"):
    source = (root / path).read_text(encoding="utf-8-sig")
    names = set(re.findall(r"^\s+method\s+\w+\s+(\w+)\(", source, re.M))
    load(path, names)

lua.execute(r'''
log_warning = log
isvalid = function(value) return value ~= nil and value ~= false end
repo.EnsureProfileLoaded = function(self, user) return self:GetUnionProfile(user) end
_UnionProfileRepositoryLogic = repo
_NewPlayerTutorialLogic = tutorial
tutorial.ActivePlayers = {}
tutorial.ShowEntryStatus = function(self, message, retry) self.Message=message; self.Retry=retry end

-- Old accounts opt out; incomplete new accounts remain incomplete after JSON reload.
local fresh = fixture(300)
assert(fresh.TutorialCompleted == false)
assert(repo:NormalizeProfile(fresh).Profile.TutorialCompleted == false)
fresh.TutorialCompleted = nil
local legacy = repo:NormalizeProfile(fresh)
assert(legacy.Success and legacy.Profile.TutorialCompleted and legacy.NeedsPersistence)
assert(legacy.Profile.UnionPoints == 300 and not legacy.WasMigrated)
fresh.TutorialCompleted = "true"
assert(not repo:NormalizeProfile(fresh).Success)

-- Failed storage writes never mark the cached profile complete; retry is idempotent.
fixture()
local raw = storage.Raw
storage.FailNext = 1000001
assert(not repo:CompleteTutorial(player).Success)
assert(cached().TutorialCompleted == false and storage.Raw == raw)
assert(repo:CompleteTutorial(player).Success)
assert(durable().TutorialCompleted and storage.Writes == 1)
assert(repo:CompleteTutorial(player).Success and storage.Writes == 1)
unlockedLock()

-- Overlapping completion requests share the existing mutation lock.
fixture()
local overlap
storage.BeforeUpdate = function() overlap = repo:CompleteTutorial(player) end
assert(repo:CompleteTutorial(player).Success)
assert(not overlap.Success and overlap.Reason == "PROFILE_MUTATION_IN_PROGRESS")
assert(storage.Writes == 1)

-- Server identity, request binding and save-before-exit are authoritative.
player.PlayerComponent = {UserId="learner"}
tutorial.ActivePlayers.learner = {Player=player, RequestId=9}
assert(tutorial:IsEntry(player, 9) and not tutorial:IsEntry(player, 10))
assert(not tutorial:IsActive({PlayerComponent={UserId="learner"}}))
local exits = 0
local battle = {PlayerEntity=player, EntryRequestId=9, TutorialStep=3, BattleResult="Victory"}
function battle:ForfeitToLobby() exits=exits+1; return {Success=true} end
assert(not tutorial:Finish(battle).Success and exits == 0)
battle.TutorialStep = 4
fixture()
player.PlayerComponent = {UserId="learner"}
battle.PlayerEntity = player
tutorial.ActivePlayers.learner = {Player=player, RequestId=9}
storage.FailNext = 1000001
assert(not tutorial:Finish(battle).Success and exits == 0)
assert(tutorial:Finish(battle).Success and exits == 1 and durable().TutorialCompleted)

-- Registration cannot skip movement or queue several attacks before the enemy-round lesson.
session.TutorialActive=true
session.TutorialStep=1
session.QueuedTileCount=0
assert(not session:TryQueueTile("brandish").Success)
session.TutorialStep=2
assert(not session:TryQueueTile("divine_swing").Success)
session.QueuedTileCount=1
assert(not session:TryQueueTile("brandish").Success)

-- Only the real enemy-to-player transition advances step 3; duplicate callbacks do nothing.
session.TurnState={BattlePhase="PlayerTurn", TurnNumber=5}
session.TutorialStep=3
session:FinishEnemyToPlayerTransition("ATTACK",true,"OK")
assert(session.TutorialStep==3)
session.TurnState.BattlePhase="EnemyTurn"
function session.TurnState:CompleteEnemyTurn() self.BattlePhase="PlayerTurn" end
session.BattleResult=""
session.TurnNumber=5; session.CurrentWave=1
for _, name in ipairs({"PublishTurnStateSnapshot","AdvancePlayerSkillCooldowns","ProcessAugmentTrigger",
                      "EvaluateForcedSpawnAtTurnBoundary","PrepareEnemyIntent"}) do
    session[name]=function() end
end
session:FinishEnemyToPlayerTransition("ATTACK",true,"OK")
assert(session.TutorialStep==4 and session.StageTurnNumber==5)

-- Real damage code keeps the monster alive until the enemy round, then permits the kill.
session._T={}; session.StrongHitDamageThreshold=5
session.PushCollisionAttackId="COLLISION"; session.VenomPoisonAttackId="POISON"
_AugmentRuntimeLogic={GetConditionalDamageBonus=function() return 0 end}
local units={}
for _, id in ipairs({"player_01", "enemy"}) do
    local unit={UnitId=id,Team=id=="enemy" and "Enemy" or "Player",CurrentHp=4,
                NextAttackBonus=0,ComboAttackBonus=0,DefenseBuffAmount=0,AttackDamageCap=0,
                GuardBuffAmount=0,PoisonDamage=0}
    unit.ApplyDamage=unitDamage
    unit.SyncRunHp=function() end
    unit.ConsumeAttackBuffHit=function() return 0 end
    unit.ConsumeVenomBuffHit=function() return 0 end
    unit.Entity={GetComponent=function(self, name) if name=="script.BattleUnitComponent" then return unit end end}
    units[id]=unit
end
session.FindUnitEntity=function(self,id) return units[id].Entity end
for _, name in ipairs({"PresentDamageNumber","PlayAcceptedEnemyImpact","PlayImpactCameraShake","RefreshPlayerHpSnapshot"}) do
    session[name]=function() end
end
local deaths=0
session.HandleUnitDiedFromSource=function() deaths=deaths+1 end
session.TutorialStep=2
assert(session:ApplyDamage("player_01","enemy",99,"brandish").AppliedAmount==3)
assert(units.enemy.CurrentHp==1 and deaths==0 and session.TutorialStep==3)
assert(session:ApplyDamage("player_01","enemy",99,"brandish").AppliedAmount==0)
assert(session:ApplyDamage("enemy","player_01",99,"enemy_basic_attack").AppliedAmount==3)
session.TurnState.BattlePhase="EnemyTurn"
session:FinishEnemyToPlayerTransition("ATTACK",true,"OK")
assert(session:ApplyDamage("player_01","enemy",2,"divine_swing").AppliedAmount==1 and deaths==1)
session.TutorialActive=false
units.enemy.CurrentHp=4
assert(session:ApplyDamage("player_01","enemy",99,"brandish").AppliedAmount==4 and deaths==2)
session.TutorialActive=true

-- Result confirmation retries storage failure instead of advancing to a normal reward/stage.
session.PlayerEntity=player
session.EntryRequestId=9
session.BattleResult="Victory"
session.ResultReady=true
session.IsValidPlayerRequest=function() return true end
session.PublishPlayerCommandResult=function() end
session.ForfeitToLobby=battle.ForfeitToLobby
local incomplete = repo:CloneProfile(cached()); incomplete.TutorialCompleted=false; seed(incomplete)
storage.FailNext=1000001
session:RequestContinueResult()
assert(session.ResultReady and exits==1)
session:RequestContinueResult()
assert(not session.ResultReady and exits==2 and durable().TutorialCompleted)

-- Even if normal content later grows, the tutorial's finite roster is exactly one enemy.
local variants=0
_StageWaveRepositoryLogic={
    GetWaveDefinition=function() return {Success=true,SpawnCount=5,EnemyPoolId="pool",SpawnTriggerMode="CLEAR_ONLY"} end,
    GetEnemySpawnDefinition=function() return {Success=true,EnemyDefinitionId="early_mushroom",MaxHp=4} end,
    GetSpawnVariantIndex=function() variants=variants+1; return 1 end,
    GetSpawnVariantSeed=function() return 1 end,
    GetVariantEnemySpawnDefinition=function() return {Success=true} end,
}
wave.TotalWaves=1; wave.CurrentWave=0; wave.PendingSpawnCount=0
wave.BeginWave=function(self, n) self.CurrentWave=n end
wave.SetWaveTriggerPhaseIndex=function() end
wave.ClearWaveTransitionTimer=function() end
wave.DrainPendingWave=function() end
local spawning={BattleResult="",TutorialActive=true,StageType="NORMAL",StageId="henesys_stage_01",RunSeed=1001,StageTurnNumber=1}
spawning.TurnState={ResetTurnState=function() end}
spawning.ClearPreparedEnemyIntent=function() end
spawning.PublishWaveStateSnapshot=function() end
spawning.TryStartBattle=function() end
wave:SpawnWave(spawning,1)
assert(wave.PendingSpawnCount==1 and #wave.PendingSpawnDefinitions==1 and variants==0)
wave:SpawnWave(spawning,2)
assert(wave.CurrentWave==1)

-- Tutorial run setup resets ordinary owners but never spends departure supplies or starts rewards/history.
local oldProfile=repo.GetUnionProfile
repo.GetUnionProfile=function() return {Success=true,Profile={SkillTree={Unlocked=""}}} end
local captured={Success=true,InventorySlotBonus=0,StartingPotionBonus=1,AugmentRerollBonus=0,StartingRandomRelicBonus=0}
local owner={CaptureForRun=function() return captured end}
local inventory={ResetForRun=function() end,GrantRunReward=function() error("tutorial potion grant") end}
run.GetOrCreateRunUnionEffectState=function() return owner end
run.GetOrCreateRunInventory=function() return inventory end
run.GetOrCreateRunAugmentState=function() return {ResetForRun=function() end} end
_RunShopLogic={ResetPlayerShopState=function() return {Success=true} end}
_UnionRewardServiceLogic={BeginRun=function() error("tutorial reward run") end}
_PremiumBenefitsLogic={GrantRunRelic=function() error("tutorial premium relic") end}
_UnionShopServiceLogic.GrantDepartureSupply=function() error("tutorial supply consumed") end
_RunResultServiceLogic={BeginRun=function() error("tutorial history") end}
assert(run:InitializeNewRunOwnedState(player,{RunSequence=1},{}).Success)
repo.GetUnionProfile=oldProfile

-- First-login dispatch: old users skip, new users bind the prepared request, failures release for retry.
local preparedCount=0
senderUserId="learner"
player.CurrentMap={Name="lobby"}
_UserService={GetUserEntityByUserId=function(self,id) assert(id=="learner"); return player end}
_BattleGatewayLogic={
    ValidateLobbyEntryRequest=function() return {Success=true} end,
    PrepareBattleEntry=function(self,p,stage,character,job) assert(p==player and stage=="henesys_stage_01" and job=="warrior"); preparedCount=preparedCount+1; return {Success=true,RequestId=42} end,
    WatchLobbyEntryTransfer=function() end,
    TransferPreparedLobbyBattleEntry=function() return {Success=true} end,
}
tutorial.ActivePlayers={}
repo.GetUnionProfile=function() return {Success=true,Profile={TutorialCompleted=true}} end
tutorial:RequestStart()
assert(preparedCount==0 and not tutorial:IsActive(player))
repo.GetUnionProfile=function() return {Success=true,Profile={TutorialCompleted=false}} end
tutorial:RequestStart()
assert(preparedCount==1 and tutorial:IsEntry(player,42))
tutorial:RequestStart()
assert(preparedCount==1)
tutorial:ReleasePlayer(player)
repo.GetUnionProfile=function() return {Success=false} end
tutorial:RequestStart()
assert(not tutorial:IsActive(player) and tutorial.Retry and preparedCount==1)
''')
print("PASS tutorial persistence, retries, request ownership, automatic turn progression and single-enemy roster")
