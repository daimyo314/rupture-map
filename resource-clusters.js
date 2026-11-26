/* Group same-type world positions using a screen-space grid. Stored data is unchanged. */
(function(root){
 'use strict';
 const MIN_SCALE=.1, MAX_SCALE=20, SCREEN_CELL=48, WORLD_PER_MAP_PIXEL=500;
 function clampScale(scale){return Math.max(MIN_SCALE,Math.min(MAX_SCALE,scale))}
 function group(items,scale){
  scale=clampScale(scale);
  const cell=SCREEN_CELL*WORLD_PER_MAP_PIXEL/scale*(1-scale/MAX_SCALE), groups=new Map(), result=[];
  for(const item of items){
   if(!Number.isFinite(item.x)||!Number.isFinite(item.y)||typeof item.type!=='string')continue;
   if(cell<=0){result.push({type:item.type,x:item.x,y:item.y,items:[item]});continue}
   const key=JSON.stringify([item.type,Math.floor((item.x+480000)/cell),Math.floor((item.y+380000)/cell)]);
   let g=groups.get(key);if(!g){g={type:item.type,x:0,y:0,items:[]};groups.set(key,g)}g.items.push(item);g.x+=item.x;g.y+=item.y;
  }
  for(const g of groups.values()){g.x/=g.items.length;g.y/=g.items.length;result.push(g)}
  return result;
 }
 const api={MIN_SCALE,MAX_SCALE,clampScale,group};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else root.ResourceClusters=api;
})(typeof globalThis!=='undefined'?globalThis:this);
