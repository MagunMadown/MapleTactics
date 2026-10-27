"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { UIBuilder } = require("../.agents/skills/msw-ui-system/scripts/msw_ui_builder.cjs");

const repoRoot = path.resolve(__dirname, "..");
const authoredPaths = new Set();
const externalPaths = new Set(["/ui/DefaultGroup"]); // Engine-owned default UI group.

function filesUnder(directory, extension) {
  const result = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) result.push(...filesUnder(full, extension));
    else if (entry.name.endsWith(extension)) result.push(full);
  }
  return result;
}

for (const file of filesUnder(path.join(repoRoot, "ui"), ".ui")) {
  const originalLog = console.log;
  let builder;
  try {
    console.log = () => {};
    builder = UIBuilder.read(file);
  } finally {
    console.log = originalLog;
  }
  for (const entity of builder.listEntities()) authoredPaths.add(entity.path);
}

const missing = [];
const literalPath = /_EntityService:GetEntityByPath\(\s*(["'])(\/ui\/[^"']+)\1\s*\)/g;
for (const file of filesUnder(path.join(repoRoot, "RootDesk", "MyDesk"), ".mlua")) {
  const source = fs.readFileSync(file, "utf8");
  let match;
  while ((match = literalPath.exec(source)) !== null) {
    const uiPath = match[2];
    const engineOwned = [...externalPaths].some(rootPath => uiPath === rootPath || uiPath.startsWith(rootPath + "/"));
    if (authoredPaths.has(uiPath) || engineOwned) continue;
    const line = source.slice(0, match.index).split("\n").length;
    missing.push(`${path.relative(repoRoot, file)}:${line} -> ${uiPath}`);
  }
}

if (missing.length > 0) {
  console.error("UI path contract failed. Missing authored entities:");
  for (const item of missing) console.error(`- ${item}`);
  process.exitCode = 1;
} else {
  console.log(`UI path contract OK (${authoredPaths.size} authored entities checked)`);
}
