"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const base=path.join(__dirname,"../RootDesk/MyDesk");
const entry=fs.readFileSync(path.join(base,"01_Combat/Components/Shared/BattleEntryStateComponent.mlua"),"utf8");
const hub=fs.readFileSync(path.join(base,"05_Test/BattleTestHubLogic.mlua"),"utf8");
const run=fs.readFileSync(path.join(base,"04_Roguelike/RunManager/RunManagerLogic.mlua"),"utf8");
function method(source,name){
  const found=source.match(new RegExp("\\tmethod [^\\n]* "+name+"\\([^\\n]*\\)([\\s\\S]*?)\\n\\tend"));
  assert.ok(found,"method missing: "+name);return found[0];
}
// These are source-boundary guards, not an emulation of MSW execution; Maker covers runtime behavior.
test("test job access grant is server-only, Maker-only and issued in the test hub",()=>{
  assert.match(entry,/\n\tproperty integer PrototypeTestJobAccessRequestId = 0/);
  assert.doesNotMatch(entry,/@Sync property integer PrototypeTestJobAccessRequestId/);
  assert.match(entry,/@ExecSpace\("ServerOnly"\)\s+method table MarkPrototypeTest/);
  const mark=method(entry,"MarkPrototypeTest");
  for(const gate of ['self.EntryState ~= "PREPARED"','requestId ~= self.RequestId','Environment:IsMakerPlay()',
    'self.EntryMode == "NEW_RUN"','self.Entity.CurrentMap.Name == _BattleTestHubLogic.TestHubMapId'])assert.ok(mark.includes(gate),gate);
  assert.ok(mark.indexOf('Environment:IsMakerPlay()')<mark.indexOf('self.PrototypeTestJobAccessRequestId = requestId'));
});
test("all entry lifecycle boundaries clear the request-scoped job access grant",()=>{
  for(const name of ["Prepare","MarkStarted","Cancel","ResetToIdle"])
    assert.ok(method(entry,name).includes("self.PrototypeTestJobAccessRequestId = 0"),name);
});
test("job bypass requires matching claimed request, job, transfer and destination",()=>{
  assert.match(hub,/@ExecSpace\("ServerOnly"\)\s+method boolean CanBypassJobLock/);
  const check=method(hub,"CanBypassJobLock");
  for(const gate of ['Environment:IsMakerPlay() == false','entry.EntryState ~= "INITIALIZING"','entry.EntryMode ~= "NEW_RUN"',
    'entry.PrototypeTestEntry ~= true','entry.JobId ~= jobId','entry.RequestId <= 0',
    'entry.PrototypeTestJobAccessRequestId ~= entry.RequestId','entry.LastTransferRequestId ~= entry.RequestId',
    'route.Success == true and route.MapId == playerEntity.CurrentMap.Name'])assert.ok(check.includes(gate),gate);
});
test("ordinary job checks stay authoritative and only JOB_LOCKED can be bypassed",()=>{
  const selection=method(run,"ApplyJobSelection"),start=method(hub,"StartStageWithLoadout");
  assert.ok(selection.includes('_UnionShopServiceLogic:CanSelectJob(playerEntity, resolvedJobId)'));
  assert.ok(selection.includes('jobAccess.Reason ~= "JOB_LOCKED" or _BattleTestHubLogic:CanBypassJobLock(playerEntity, resolvedJobId) == false'));
  assert.ok(start.includes('Environment:IsMakerPlay() == false or jobAccess.Reason ~= "JOB_LOCKED"'));
  assert.ok(start.indexOf('_UnionShopServiceLogic:CanSelectJob')<start.indexOf('_BattleGatewayLogic:PrepareBattleEntry'));
});
