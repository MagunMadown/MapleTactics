"use strict";
const fs = require("node:fs");
const path = require("node:path");
const api = require("../../.agents/skills/msw-search/scripts/msw_resource_api.cjs");
const packs = {
  star_pixie: "mob/3230200.img", lunar_pixie: "mob/4230106.img", luster_pixie: "mob/5120000.img",
  nependeath: "mob/4230105.img", dark_nependeath: "mob/4130102.img",
  jr_cellion: "mob/3210200.img", jr_lioner: "mob/3210201.img", jr_grupin: "mob/3210202.img",
  cellion: "mob/5120001.img", lioner: "mob/5120002.img", grupin: "mob/5120003.img",
  jr_lucida: "mob/6230401.img", lucida: "mob/7130000.img",
  papa_pixie: "mob/9300039.img", eliza: "mob/8220000.img"
};
async function main() {
  const cachedPath = path.join(__dirname, "resources.json");
  const cached = fs.existsSync(cachedPath) ? JSON.parse(fs.readFileSync(cachedPath, "utf8")) : {};
  const resources = cached.resources || Object.fromEntries(await Promise.all(Object.entries(packs).map(async ([key, id]) => [key, await api.getResource(id)])));
  const scenery = cached.scenery ? Object.entries(cached.scenery) : await Promise.all([
    ["orbis", "오르비스", ["resource_pack"], ["background", "object"]],
    ["garden", "오르비스 공원", ["resource_pack"], ["object", "background"]],
    ["cloud", "구름 공원", ["resource_pack"], ["background", "object"]],
    ["bgm", "Orbis", ["bgm"], ["background"]],
    ["orbis_sprite", "오르비스", ["sprite", "animationclip"], ["object", "background"]],
    ["garden_sprite", "Orbis garden pillar", ["sprite"], ["object", "background"]],
    ["cloud_sprite", "Orbis clouds sky", ["sprite"], ["background", "object"]],
    ["floor_sprite", "Orbis white stone platform", ["sprite"], ["object", "background", "foothold"]]
  ].map(async ([key, query, resourceTypeFilter, categoryFilter]) => [key, await api.searchResources(query, {resourceTypeFilter, categoryFilter, topK: 3})]));
  const details = cached.details || Object.fromEntries(await Promise.all([
    "e58e17b0848641aba9a586e61817df67", "ba762b7c46ab4530b77e5da44c7264b2", "32e0794950034037afc51f1a22ee97ed",
    "c5b77d0a8b8b4bbebee53da0edf83c17", "a65e163fa850426fb06b28547cee6816", "3722f86d44974182982b8079ce18326f",
    "2f6c7232b6344389a0d39a8f2d0909cb", "3b0debccd6cc41d092572b6ccf9b5b8d", "3413251c390346e7acce30580c562ff7"
  ].map(async id => [id, await api.getResource(id)])));
  const manifest = {source: "MSW resource API", retrievedAt: new Date().toISOString(), resources, scenery: Object.fromEntries(scenery), details};
  fs.writeFileSync(path.join(__dirname, "resources.json"), JSON.stringify(manifest, null, 2) + "\n");
  if (process.argv.includes("--previews")) {
    fs.mkdirSync(path.join(__dirname, "previews"), {recursive: true});
    await Promise.all(Object.values(details).map(async resource => {
      const response = await fetch(resource.payload.thumbnail);
      if (!response.ok) throw Error("Preview download: " + response.status);
      fs.writeFileSync(path.join(__dirname, "previews", resource.id + ".png"), Buffer.from(await response.arrayBuffer()));
    }));
  }
  for (const [key, resource] of Object.entries(resources)) console.log(JSON.stringify({key, id: resource.id, actions: resource.payload?.elements?.filter(e => e.type === "animationclip").map(e => e.rel_path)}));
  for (const [key, result] of scenery) console.log(JSON.stringify({key, results: result.results?.map(r => ({id: r.id, names: r.names, type: r.type, payload: r.type === "resource_pack" ? undefined : r.payload}))}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
