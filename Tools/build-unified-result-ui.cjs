const path = require('path');
const repo = process.argv[2] || path.resolve(__dirname, '..');
const { UIBuilder } = require(repo+'/.agents/skills/msw-ui-system/scripts/msw_ui_builder.cjs');
const file = repo+'/ui/BattleQueueHUD.ui';
const b = UIBuilder.load(file);
const root = 'ResultPanel';
const sprite = 'MOD.Core.SpriteGUIRendererComponent';
const text = 'MOD.Core.TextGUIRendererComponent';
const c = (r,g,bl,a=1)=>({r:r/255,g:g/255,b:bl/255,a});
const white = c(245,250,249), muted=c(191,210,213), mint=c(159,240,219);
const flat = '1705e3c5b2c146ac9a699f96fb067408';
// Reuse the project's sliced UI skin (also used by RunShopUI).
const skin = '2860136c06ab075439721c027de365af';
function panel(name,x,y,w,h,color) {
  b.panel(root+'/'+name,{pos:[x,y],rect_size:[w,h],color,image_ruid:flat,raycast:false});
}
function label(name,value,x,y,w,h,size=24,color=white) {
  b.text(root+'/'+name,value,{pos:[x,y],rect_size:[w,h],size,color,alignment:3});
}
function patchText(name,x,y,w,h,size,color=white) {
  b.patch(root+'/'+name,{pos:[x,y],rect_size:[w,h]});
  b.patchComponent(root+'/'+name,text,{FontSize:size,FontColor:color,OutlineWidth:0,Underlay:false,HorizontalAlignment:1});
}
b.panel('ResultBackdrop',{anchor:'stretch',rect_size:[0,0],image_ruid:flat,color:c(4,12,17,0.24),raycast:true,enable:false});
b.patch('ResultBackdrop',{display_order:99});
b.patch(root,{pos:[0,0],rect_size:[1280,860],enable:false,display_order:100});
b.patchComponent(root,sprite,{ImageRUID:{DataId:skin},Type:1,Color:c(22,39,45,1),RaycastTarget:true,Outline:true,OutlineColor:c(130,167,172),OutlineWidth:2,DropShadow:true,DropShadowColor:c(0,8,12,.25),DropShadowDistance:5});
// An opaque inset prevents the source skin's own transparency from revealing scenery.
b.panel(root+'/BodyFill',{anchor:'stretch',rect_size:[-16,-16],image_ruid:flat,sprite_type:0,color:c(22,39,45,1),raycast:false});
// Preserve existing title, panel and continue-button bindings.
patchText('ResultText',0,340,1168,88,68);
b.patch(root+'/StageName',{enable:false});
b.patch(root+'/Divider',{pos:[0,270],rect_size:[1168,2]});
b.patchComponent(root+'/Divider',sprite,{ImageRUID:{DataId:flat},Type:0,Color:c(59,82,87)});
label('RewardsTitle','획득 보상',-324,217,520,40,32);
label('RewardsEmpty','획득한 보상이 없습니다',0,132,1008,52,26,muted);
for(let i=1;i<=8;i++) {
  const x=-396+((i-1)%3)*396, y=132;
  panel('Reward'+i,x,y,376,128,c(39,62,70,1));
  b.patchComponent(root+'/Reward'+i,sprite,{ImageRUID:{DataId:skin},Type:1,Outline:true,OutlineColor:c(63,88,97),OutlineWidth:1});
  b.patch(root+'/Reward'+i,{enable:false});
  b.sprite(root+'/Reward'+i+'/Icon',{pos:[-128,0],rect_size:[64,64],image_ruid:flat,sprite_type:0,color:c(255,255,255),preserve_aspect:false});
  b.text(root+'/Reward'+i+'/Name','',{pos:[48,24],rect_size:[232,40],size:30,color:white,alignment:3});
  b.text(root+'/Reward'+i+'/Amount','',{pos:[48,-24],rect_size:[232,48],size:40,color:mint,bold:true,alignment:3});
}
label('RewardPages','',324,217,520,32,20,muted);
b.patchComponent(root+'/RewardPages',text,{HorizontalAlignment:4});
label('RelicsTitle','유물을 하나 선택하세요',0,18,1168,42,32);
label('RelicsEmpty','선택 가능한 유물이 없습니다',0,-146,1008,60,25,muted);
for(let i=1;i<=3;i++) {
  const p=root+'/Relic'+i;
  b.button(p,'',{pos:[(i-2)*396,-137],rect_size:[376,258],image_ruid:skin,bg_color:c(30,47,52)});
  b.patchComponent(p,sprite,{Outline:true,OutlineColor:c(64,89,94),OutlineWidth:1});
  b.sprite(p+'/Icon',{pos:[-93,3],rect_size:[164,180],image_ruid:flat,sprite_type:0,color:c(255,255,255),preserve_aspect:true});
  b.text(p+'/Kind','유물',{pos:[88,38],rect_size:[172,30],size:22,color:muted,alignment:3});
  b.text(p+'/Name','',{pos:[88,-10],rect_size:[172,68],size:28,color:white,bold:true,alignment:3});
  b.text(p+'/Effect','',{pos:[0,-104],rect_size:[332,32],size:20,color:muted,alignment:3});
  b.text(p+'/Selected','✓',{pos:[152,98],rect_size:[38,38],size:28,color:c(18,53,49),alignment:4,enable:false});
  b.patchComponent(p+'/Selected',sprite,{ImageRUID:{DataId:skin},Type:1,Color:mint});
}
panel('FooterDivider',0,-305,1168,2,c(68,97,104));
b.patch(root+'/Summary',{enable:false});
panel('FooterStats',-310,-363,548,60,c(0,0,0,0));
b.text(root+'/FooterStats/TurnLabel','소요 턴',{pos:[-225,0],rect_size:[96,42],size:24,color:muted,alignment:3});
b.text(root+'/FooterStats/TurnValue','0',{pos:[-113,0],rect_size:[100,48],size:36,color:white,bold:true,alignment:3});
b.panel(root+'/FooterStats/Separator',{pos:[-50,0],rect_size:[1,44],image_ruid:flat,color:c(65,93,100),raycast:false});
b.text(root+'/FooterStats/KillLabel','처치 수',{pos:[33,0],rect_size:[100,42],size:24,color:muted,alignment:3});
b.text(root+'/FooterStats/KillValue','0',{pos:[145,0],rect_size:[100,48],size:36,color:white,bold:true,alignment:3});
patchText('UnionRewardText',-250,122,440,45,27,mint);
patchText('UnionRewardBreakdownText',-240,77,460,38,20,muted);
b.patch(root+'/BtnReset',{pos:[408,-363],rect_size:[352,72]});
b.patchComponent(root+'/BtnReset',sprite,{ImageRUID:{DataId:skin},Type:1,Color:white});
b.patchComponent(root+'/BtnReset',text,{Text:'모험 계속',FontSize:28,FontColor:c(20,37,42),OutlineWidth:0,HorizontalAlignment:2,Underlay:false,Padding:{left:8,right:60,top:0,bottom:0}});
b.text(root+'/BtnReset/KeyBadge','E',{pos:[136,0],rect_size:[46,46],size:28,color:white,alignment:4});
b.patchComponent(root+'/BtnReset/KeyBadge',sprite,{ImageRUID:{DataId:skin},Type:1,Color:c(24,43,49)});
label('Status','',-130,-285,740,22,16,mint);
b.sprite(root+'/RewardDragArea',{pos:[0,132],rect_size:[1168,128],alpha:0,raycast:true,enable:false});
b.upsertComponent(root+'/RewardDragArea','MOD.Core.UITouchReceiveComponent');
// Screen UI ignores renderer OrderInLayer; order the panel's siblings instead.
const panelPath = b.find(root).path;
const bodyPath = b.find(root+'/BodyFill').path;
const children = b.listEntities().filter(e => e.path.startsWith(panelPath+'/') && !e.path.slice(panelPath.length+1).includes('/'));
const content = children.filter(e => e.path !== bodyPath).sort((a,bEntry) => b.find(a.path).jsonString.displayOrder - b.find(bEntry.path).jsonString.displayOrder);
b.patch(bodyPath,{display_order:0});
content.forEach((entity,index) => b.patch(entity.path,{display_order:index+1}));
b.write(file);
