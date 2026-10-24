"use strict";
const path=require("node:path");
const {UIBuilder}=require("../../.agents/skills/msw-ui-system/scripts/msw_ui_builder.cjs");
const root=path.resolve(__dirname,"../..");
const file=path.join(root,"ui/RunRelicInventoryUI.ui");
const b=UIBuilder.read(file);
b.empty("ContentHud",{anchor:"top-left",pos:[32,-176],rect_size:[568,328],enable:false});
b.upsertComponent("ContentHud","MOD.Core.CanvasGroupComponent",{GroupAlpha:1,BlocksRaycasts:false,Interactable:false});
b.text("ContentHud/Title","유물 상태",{anchor:"top-left",pos:[0,0],rect_size:[568,22],size:18,bold:true,color:"#D8E8F4",alignment:3});
const icons=["24f6b7a6e22c426b9d27f197ecb3f4d1","38b6acb253d94d2abc5c1dfbde19b4f5","d3b052a8877a4460bb801c4aebea442c","a372f621f1f84561ad046d8b68964ad2","thumbnail://b86fe397c76642988d4a5f6ef3f3ee40","thumbnail://d458879e2e2949f2bb2e915ff67fbc64"];
// ponytail: 24 slots cover the current per-job catalog; grow this grid and the client binding bound together if needed.
for(let index=0;index<24;index++){
 const slot="ContentHud/Slot"+(index+1);
 b.panel(slot,{anchor:"top-left",pos:[(index%6)*96,-24-Math.floor(index/6)*76],rect_size:[88,72],color:{r:0.10,g:0.14,b:0.21,a:0.90},raycast:false,enable:false});
 b.sprite(slot+"/Icon",{anchor:"top-center",pos:[0,-4],rect_size:[36,36],image_ruid:icons[index%icons.length],sprite_type:0,color:"#FFFFFF",alpha:1,raycast:false});
 b.patchComponent(slot+"/Icon","MOD.Core.SpriteGUIRendererComponent",{PreserveSprite:1});
 b.text(slot+"/State","",{anchor:"bottom-center",pos:[0,4],rect_size:[88,24],size:18,color:"#D9E3F5",bold:true});
}
b.write(file);
console.log("Orbis relic feedback HUD: 24 passive slots; existing inventory preserved.");
