#!/usr/bin/env node
// Checks that Balance Studio's vocabulary catalog (#vocabCatalog in
// tools/balance-studio.html) still covers every closed value the game code
// accepts and the CSVs use: skill effect types, effect conditions / target
// selectors / targeting types / cost types, MOVE_SELF modes, DAMAGE modes,
// utility effect types, enemy pattern actions / conditions / CELL_FREE
// selectors, skill augment kinds, and relic special effects (the page's
// RELIC_SPECIAL_EFFECTS list, checked against RelicDefinitionRepositoryLogic).
//
//   node tools/check-balance-vocab.cjs          # report, exit 1 if the catalog is missing something
//
// Run it after adding a new effect / action / mode to the game, then add the
// reported values to #vocabCatalog (label + what Value / ParameterA / ParameterB
// mean for it, transcribed from the code). Zero dependencies.
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const HTML = path.join(ROOT, "tools/balance-studio.html");
const DATA = path.join(ROOT, "RootDesk/MyDesk/03_Data");
const COMBAT = path.join(ROOT, "RootDesk/MyDesk/01_Combat");

const read = (p) => (fs.existsSync(p) ? fs.readFileSync(p, "utf8") : "");
const html = read(HTML);
const m = html.match(/<script type="application\/json" id="vocabCatalog">([\s\S]*?)<\/script>/);
if (!m) {
  console.error("#vocabCatalog not found in tools/balance-studio.html");
  process.exit(2);
}
const VOCAB = JSON.parse(m[1]);

// Same extraction the page does on load (scanVocabFromCode), plus the
// executors in 01_Combat that the page can't see from 03_Data.
function methodBody(text, name) {
  const start = text.search(new RegExp(`method\\s+\\w+\\s+${name}\\s*\\(`));
  if (start === -1) return "";
  const rest = text.slice(start + 1);
  const end = rest.search(/\n\s*(@ExecSpace|method\s)/);
  return end === -1 ? rest : rest.slice(0, end);
}
const literals = (text, re) => [...text.matchAll(re)].map((x) => x[1]);
const cv = read(path.join(DATA, "Repositories/ContentValidatorLogic.mlua"));
const pv = read(path.join(DATA, "Repositories/EnemyPatternContentValidatorLogic.mlua"));
const buff = read(path.join(COMBAT, "Skills/EffectExecutors/BuffEffectExecutorLogic.mlua"));
const move = read(path.join(COMBAT, "Skills/EffectExecutors/MoveSelfEffectExecutorLogic.mlua"));
const session = read(path.join(COMBAT, "Components/Shared/BattleSessionComponent.mlua"));
const router = read(path.join(COMBAT, "Resolvers/EffectRouterLogic.mlua"));
const augmentValidator = read(path.join(DATA, "Repositories/AugmentContentValidatorLogic.mlua"));
const relicRepo = read(path.join(DATA, "Repositories/RelicDefinitionRepositoryLogic.mlua"));
const skillBody = methodBody(cv, "ValidateSkillBundle");
const lit = /"([A-Z0-9_]+)"/g;

const fromCode = {
  effectType: [
    ...literals(skillBody, /EffectType\s*[~=]=\s*"([A-Z0-9_]+)"/g),
    ...literals(methodBody(buff, "IsBuffEffectType"), lit),
    ...literals(methodBody(buff, "GetBuffStat"), /effectType\s*==\s*"([A-Z0-9_]+)"/g),
    ...literals(methodBody(move, "IsMoveEffectType"), lit),
    ...literals(methodBody(session, "IsCombatModifierEffect"), lit),
    ...literals(router, /EffectType\s*==\s*"([A-Z0-9_]+)"/g),
  ],
  utilityEffectType: literals(methodBody(cv, "ValidateUtilityEffect"), /EffectType\s*[~=]=\s*"([A-Z0-9_]+)"/g),
  effectCondition: literals(skillBody, /condition\s*[~=]=\s*"([A-Z0-9_]+)"/g),
  costType: literals(skillBody, /CostType\s*[~=]=\s*"([A-Z0-9_]+)"/g),
  targetingType: literals(methodBody(cv, "IsSupportedSkillTargetingType"), lit),
  targetSelector: literals(methodBody(cv, "IsSupportedEffectTargetSelector"), lit),
  damageMode: literals(skillBody, /ParameterA\s*[~=]=\s*"([A-Z0-9_]+)"/g),
  moveMode: literals(methodBody(move, "IsSupportedMoveMode"), lit),
  patternAction: literals(methodBody(pv, "IsSupportedAction"), lit),
  patternCondition: literals(methodBody(pv, "IsSupportedCondition"), lit),
  cellSelector: literals(methodBody(pv, "IsSupportedCellSelector"), lit),
  augmentModifier: literals(methodBody(augmentValidator, "IsSkillModifierValid"), /kind\s*==\s*"([A-Z0-9_]+)"/g),
  relicSpecial: literals(methodBody(relicRepo, "DescribeSpecialEffect"), /^\s*([A-Z0-9_]+)\s*=\s*"/gm),
};

function csvColumn(file, col) {
  const text = read(path.join(DATA, file)).replace(/^﻿/, "");
  if (!text) return [];
  const lines = text.split(/\r?\n/).filter(Boolean);
  const header = lines[0].split(",");
  const i = header.indexOf(col);
  if (i === -1) return [];
  // Closed-vocabulary cells never contain commas or quotes, so a plain split is enough here.
  return lines.slice(1).map((l) => (l.split(",")[i] || "").trim());
}
const skillTables = fs.readdirSync(DATA).filter((f) => /SkillDefinitions\.csv$/.test(f) && f !== "UtilitySkillDefinitions.csv");
const fromData = {
  augmentHidden: csvColumn("AugmentEffects.csv", "ParamC"),
  augmentTrigger: csvColumn("AugmentEffects.csv", "TriggerType"),
  augmentCondition: csvColumn("AugmentEffects.csv", "ConditionType"),
  augmentEffect: csvColumn("AugmentEffects.csv", "EffectType"),
  augmentTarget: csvColumn("AugmentEffects.csv", "TargetType"),
  augmentModifier: csvColumn("AugmentEffects.csv", "ParamA"),
  effectType: csvColumn("SkillEffectSteps.csv", "EffectType"),
  utilityEffectType: csvColumn("UtilitySkillEffectSteps.csv", "EffectType"),
  effectCondition: csvColumn("SkillEffectSteps.csv", "ConditionId"),
  targetSelector: [...csvColumn("SkillEffectSteps.csv", "TargetSelector"), ...csvColumn("UtilitySkillEffectSteps.csv", "TargetSelector")],
  targetingType: [...skillTables, "UtilitySkillDefinitions.csv"].flatMap((f) => csvColumn(f, "TargetingType")),
  costType: [...skillTables, "UtilitySkillDefinitions.csv"].flatMap((f) => csvColumn(f, "CostType")),
  patternAction: csvColumn("EnemyPatternSteps.csv", "ActionType"),
  patternCondition: csvColumn("EnemyPatternSteps.csv", "ConditionType"),
  relicSpecial: csvColumn("RelicDefinitions.csv", "SpecialEffectType"),
};
// Relic special effects live in a JS constant on the page, not in #vocabCatalog.
const relicList = html.match(/const RELIC_SPECIAL_EFFECTS = \[([\s\S]*?)\];/);
const relicCatalog = relicList ? literals(relicList[1], /\["([A-Z0-9_]+)",/g) : [];

const S = VOCAB.skill, P = VOCAB.enemyPattern;
const catalog = {
  augmentHidden: Object.keys(VOCAB.augment.hiddenMarker),
  augmentTrigger: Object.keys(VOCAB.augment.triggerTypes),
  augmentCondition: Object.keys(VOCAB.augment.conditionTypes),
  augmentEffect: Object.keys(VOCAB.augment.effectTypes),
  augmentTarget: Object.keys(VOCAB.augment.targetTypes),
  augmentModifier: Object.keys(VOCAB.augment.modifiers),
  effectType: Object.keys(S.effects),
  utilityEffectType: Object.keys(S.utilityEffects),
  effectCondition: Object.keys(S.conditions),
  costType: Object.keys(S.costTypes),
  targetingType: Object.keys(S.targetingTypes),
  targetSelector: Object.keys(S.targetSelectors),
  damageMode: Object.keys(S.effects.DAMAGE.paramA.options).filter(Boolean),
  moveMode: Object.keys(S.effects.MOVE_SELF.paramA.options),
  patternAction: Object.keys(P.actions),
  patternCondition: Object.keys(P.conditions),
  cellSelector: Object.keys(P.conditions.CELL_FREE.paramA.options),
  relicSpecial: relicCatalog,
};
const TITLES = {
  augmentHidden: "AugmentEffects.ParamC", augmentTrigger: "AugmentEffects.TriggerType", augmentCondition: "AugmentEffects.ConditionType",
  augmentEffect: "AugmentEffects.EffectType", augmentTarget: "AugmentEffects.TargetType", augmentModifier: "AugmentEffects.ParamA",
  effectType: "SkillEffectSteps.EffectType", utilityEffectType: "UtilitySkillEffectSteps.EffectType",
  effectCondition: "SkillEffectSteps.ConditionId", costType: "*SkillDefinitions.CostType",
  targetingType: "*SkillDefinitions.TargetingType", targetSelector: "*EffectSteps.TargetSelector",
  damageMode: "DAMAGE ParameterA", moveMode: "MOVE_SELF ParameterA",
  patternAction: "EnemyPatternSteps.ActionType", patternCondition: "EnemyPatternSteps.ConditionType",
  cellSelector: "CELL_FREE ParamA", relicSpecial: "RelicDefinitions.SpecialEffectType",
};

let missing = 0;
console.log(`Balance Studio vocab catalog: ${VOCAB.catalogVersion}\n`);
for (const kind of Object.keys(catalog)) {
  const known = new Set(catalog[kind]);
  const code = new Set((fromCode[kind] || []).filter((v) => v));
  const data = new Set((fromData[kind] || []).filter((v) => v));
  const gaps = [...new Set([...code, ...data])].filter((v) => !known.has(v));
  const unseen = [...known].filter((v) => v && !code.has(v) && !data.has(v));
  const status = gaps.length ? "MISSING" : "ok";
  console.log(`${status.padEnd(7)} ${TITLES[kind].padEnd(38)} catalog ${known.size}, code ${code.size}, data ${data.size}`);
  gaps.forEach((v) => {
    missing++;
    const where = kind === "relicSpecial" ? "RELIC_SPECIAL_EFFECTS" : "#vocabCatalog";
    console.log(`        + ${v}  (${[code.has(v) && "game code", data.has(v) && "CSV"].filter(Boolean).join(" + ")}) — add to ${where}`);
  });
  if (unseen.length && code.size) console.log(`        · in catalog but not found in code/data (removed?): ${unseen.join(", ")}`);
}
console.log(missing ? `\n${missing} value(s) missing from the catalog. They still appear in the tool's selects as "카탈로그 미등록", but without descriptions or checks.` : "\nCatalog covers everything the code and data use.");
process.exit(missing ? 1 : 0);
