"use strict";
// Run after Maker imports 200080200 into the new tower map and saves it.
const fs = require("node:fs");
const path = require("node:path");
const {MapBuilder} = require("../../.agents/skills/msw-general/scripts/map/msw_map_builder.cjs");
const root=path.resolve(__dirname,"../.."), id="orbis_tower_battle";
const file=path.join(root,"map",id+".map");
const source=MapBuilder.read(path.join(root,"map/orbis_guardian_battle.map"));
const map=MapBuilder.read(file);
if (map.getTileMapMode()!==0 || source.getTileMapMode()!==0) throw Error("Expected MapleTile maps");
const nativeBackground=map.component("Background","MOD.Core.BackgroundComponent");
if (nativeBackground.Type!==1 || nativeBackground.TemplateRUID!=="1089d1a3ea414480b5ca8a09d5f6e93f") throw Error("Import original Orbis Tower 20F before adapting");
const nativeSnapshot=path.join(__dirname,"tower-import-provenance.json");
if (!fs.existsSync(nativeSnapshot)) fs.writeFileSync(nativeSnapshot,JSON.stringify({sourceMapId:"200080200",sourceMapName:"Orbis Tower <20th Floor>",background:nativeBackground,originalMapInfo:map.getMapInfo(),nativeScenery:map.listEntities().filter(e=>/^foothold-|^MapObject/.test(e.name)).map(e=>({name:e.name,ruid:map.component(e.path,"MOD.Core.SpriteRendererComponent")?.SpriteRUID,position:map.component(e.path,"MOD.Core.TransformComponent")?.Position}))},null,2)+"\n");
for (const e of map.listEntities()) {
  if (/^monster-|^npc-|^Portal|^Ladder|^Rope/.test(e.name)) map.remove(e.path);
  else if (e.name==="SpawnLocation") {if (map.find(e.path)) map.remove(e.path);}
  else if (/^foothold-/.test(e.name)) {
    const t=map.component(e.path,"MOD.Core.TransformComponent");
    // Keep only distant background ornaments; the board has one physical floor.
    if (t.Position.y<2.2) map.remove(e.path);
    else {
      if (map.component(e.path,"MOD.Core.CustomFootholdComponent")) map.removeComponent(e.path,"MOD.Core.CustomFootholdComponent");
      map.patchComponent(e.path,"MOD.Core.SpriteRendererComponent",{SortingLayer:"MapLayer0",OrderInLayer:0});
    }
  } else if (/^MapObject/.test(e.name)) map.patchComponent(e.path,"MOD.Core.SpriteRendererComponent",{SortingLayer:"MapLayer0",OrderInLayer:0});
  else if (e.componentNames.includes("MOD.Core.TileMapComponent")) {
    // Imported vertical wall/floor tiles stay intact, hidden behind the adapted arena.
    // Do not paint or rewrite any native tile arrays.
    map.patchComponent(e.path,"MOD.Core.TileMapComponent",{Color:{r:1,g:1,b:1,a:0},SortingLayer:"MapLayer0"});
  }
}
for (const name of ["BattleScenery/CloudBank","BattleScenery/Pillar1","BattleScenery/Pillar2","BattleScenery/Pillar3","BattleScenery/Pillar4"]) if (map.find(name)) map.remove(name);
for (const name of ["BattleBoardState","BattleTurnState","BattleWaveState","BattleCameraAnchor","SpawnLocation"]) {
  const e=source.find(name).jsonString;
  map.entity(name,e["@components"],{modelId:e.modelId||"mapempty"});
}
for (const name of ["BattlePlatforms","BattleScenery","MapleMapLayer"]) map.upsertComponent(name,"MOD.Core.MapLayerComponent",source.component(name,"MOD.Core.MapLayerComponent"));
map.patchComponent(id,"script.BattleSessionComponent",{AutoStartPrototypeBattle:false,CellCount:7,CellStartX:-3.36,CellSpacing:1.12,UnitY:-.05,PlayerStartCell:3,QueueCapacity:3});
// Reuse the proven flat ground chain and bind its owner to this map's tile entity.
const owner=map.find("TileMap").id;
const ground=source.getFootholds().map(f=>({...f,OwnerId:owner}));
map.patchComponent(id,"MOD.Core.FootholdComponent",{FootholdsByLayer:{1:ground}});
map.patch("SpawnLocation",{pos:[0,.05,0]}).patchComponent("SpawnLocation","MOD.Core.SpriteRendererComponent",{Color:{r:1,g:1,b:1,a:0}});
for (let i=1;i<=9;i++) map.patch("BattlePlatforms/BattleCell"+i,{enable:false});
map.write(file);
console.log(JSON.stringify({map:id,...map.getMapInfo(),originalMapId:"200080200",background:nativeBackground.TemplateRUID}));
