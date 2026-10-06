// Static contract checks only. Maker build/play remains required for native rendering and RPCs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const read = p => fs.readFileSync(path.join(root, p), 'utf8');
const dataRoot = 'RootDesk/MyDesk/03_Data/';

function parseCsv(text) {
  text = text.replace(/^\uFEFF/, '');
  const records = []; let record = [], cell = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') { cell += '"'; i++; }
      else quoted = !quoted;
    } else if (ch === ',' && !quoted) { record.push(cell); cell = ''; }
    else if (ch === '\n' && !quoted) { record.push(cell.replace(/\r$/, '')); records.push(record); record = []; cell = ''; }
    else cell += ch;
  }
  assert.equal(quoted, false, 'Unterminated CSV quote');
  if (cell || record.length) { record.push(cell); records.push(record); }
  const headers = records.shift();
  assert.equal(new Set(headers).size, headers.length, 'Duplicate columns');
  return records.map(values => {
    assert.equal(values.length, headers.length, 'CSV column count');
    return Object.fromEntries(headers.map((h, i) => [h, values[i]]));
  });
}

const rows = parseCsv(read(dataRoot + 'DamageSkinDefinitions.csv'));
const ids = new Set();
const tweens = new Set(['Default', 'Volcano', 'Blade', 'DefaultMini', 'VolcanoMini', 'BladeMini']);
const ranges = { OffsetX: [-10, 10], OffsetY: [-10, 10], Scale: [0.1, 5], PlayRate: [0.1, 5], Alpha: [0.1, 1] };
for (const row of rows) {
  assert.equal(row.SchemaVersion, '1');
  assert.match(row.SkinId, /^[a-z][a-z0-9_]*$/);
  assert.ok(!ids.has(row.SkinId), 'Duplicate SkinId'); ids.add(row.SkinId);
  assert.ok(row.DisplayName.trim());
  assert.match(row.ResourceRuid, /^[a-fA-F0-9]{32}$/);
  assert.ok(tweens.has(row.TweenType));
  for (const [field, [min, max]] of Object.entries(ranges)) {
    assert.notEqual(row[field].trim(), '');
    const value = Number(row[field]);
    assert.ok(Number.isFinite(value) && value >= min && value <= max, field);
  }
}
assert.ok(ids.has('maple_default') && ids.has('maple_taken'));
const wrapper = JSON.parse(read(dataRoot + 'DamageSkinDefinitions.userdataset'));
assert.equal(wrapper.EntryKey, 'userdataset://' + wrapper.ContentProto.Json.id);
assert.equal(wrapper.ContentProto.Json.name, 'DamageSkinDefinitions');
assert.equal(wrapper.ContentProto.Json.serveronly, false);

const session = read('RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua');
const presentation = read('RootDesk/MyDesk/01_Combat/Components/Shared/BattleUnitPresentationComponent.mlua');
const damageExecutor = read('RootDesk/MyDesk/01_Combat/Skills/EffectExecutors/DamageEffectExecutorLogic.mlua');
const repository = read(dataRoot + 'Repositories/DamageSkinDefinitionRepositoryLogic.mlua');
const attack = session.slice(session.indexOf('method table ApplyDamage('), session.indexOf('method void PresentDamageNumber('));
const status = session.slice(session.indexOf('method table ApplyStatusDamage('));
assert.match(attack, /table\.insert\(batch\.Damages, damageResult\.AppliedAmount\)/);
assert.match(attack, /batch\.HitCount = batch\.HitCount \+ 1/);
assert.match(attack, /self:PresentDamageNumber\(sourceEntity, targetEntity, damageResult\.AppliedAmount\)/);
assert.ok(attack.lastIndexOf('self:FlushDamageNumberBatch(batch)') < attack.indexOf('self:HandleUnitDiedFromSource('), 'Flush lethal batch before death handling');
assert.match(attack, /if sourcePresentation ~= nil and playImpact then/);
assert.match(attack, /if targetPresentation ~= nil and playImpact then/);
assert.match(attack, /Flash = self\.HitFlashDuration, SkipMotion = batch ~= nil/);
assert.match(session, /if batch == nil or batch\.HitCount <= 1 then self:PlayActiveHitEffect\(targetUnitId\) end/);
assert.match(status, /if result.Success and result.AppliedAmount > 0 then\s+self:PresentDamageNumber/);
assert.ok(status.indexOf('self:PresentDamageNumber(') < status.indexOf('self:HandleUnitDiedFromSource('), 'Status number before death handling');
assert.match(presentation, /@ExecSpace\("Client"\)\s+method void PlayDamageNumbers/);
assert.match(presentation, /@ExecSpace\("ServerOnly"\)\s+method table SetDamageSkin/);
assert.equal((presentation.match(/_DamageSkinService:Play\(/g) || []).length, 1);
assert.ok(presentation.includes('localPlayer.CurrentMap ~= self.Entity.CurrentMap'));
assert.match(damageExecutor, /battleSession\._T\.damageNumberBatch = batch/);
assert.match(damageExecutor, /battleSession:FlushDamageNumberBatch\(batch\)/);
assert.match(damageExecutor, /battleSession\._T\.damageNumberBatch = previousBatch/);
assert.match(session, /self:PresentDamageNumbers\(self:FindUnitEntity\(batch\.SourceUnitId\), self:FindUnitEntity\(batch\.TargetUnitId\), amounts, 0\.08\)/);
assert.match(session, /presentation:PlayDamageNumbers\(target\.UnitId, appliedAmounts, skinId, playerTarget, delayPerAttack\)/);
assert.match(presentation, /_DamageSkinService:Play\(self\.Entity, definition\.ResourceRuid, math\.max\(0, delayPerAttack\), damages/);
assert.match(presentation, /if skipHitMotion == false and self\.DeathMotionActive == false/);
assert.ok(repository.includes('DUPLICATE_DAMAGE_SKIN_ID'));
assert.ok(repository.includes('DAMAGE_SKIN_DEFAULT_MISSING'));
assert.ok(repository.includes('value ~= value'));
assert.ok(repository.includes('self._T.catalog = nil'));
console.log(`PASS: ${rows.length} skin rows, dataset metadata, multi-hit batching, lethal/status dispatch boundaries, RPC/guard/static validation contracts`);
console.log('NOT RUN: Maker compilation, native resource loading, visual placement, lethal/transition playback.');
