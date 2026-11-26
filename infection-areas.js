'use strict';
// Observed locations form connected groups, not measured infection boundaries.
const InfectionAreas=(()=>{
 const LINK=2500, SPACING=500, CLEAR=600, MAX_POINTS=2000;
 const near=(a,b,limit)=>Math.hypot(a.x-b.x,a.y-b.y)<=limit;
 function observe(areas,point){
  if(!Array.isArray(areas)||!Number.isFinite(point.x)||!Number.isFinite(point.y))return false;
  const matches=areas.filter(a=>!a.cleared&&a.points.some(p=>near(p,point,LINK)));
  if(!matches.length){if(areas.reduce((n,a)=>n+a.points.length,0)>=MAX_POINTS)return false;areas.push({id:crypto.randomUUID(),points:[{x:point.x,y:point.y}],cleared:false});return true}
  const target=matches[0];let changed=false;
  for(const other of matches.slice(1)){target.points.push(...other.points);areas.splice(areas.indexOf(other),1);changed=true}
  if(!target.points.some(p=>near(p,point,SPACING))&&areas.reduce((n,a)=>n+a.points.length,0)<MAX_POINTS){target.points.push({x:point.x,y:point.y});changed=true}
  return changed;
 }
 function clearNearby(areas,point){let changed=false;for(const a of areas){if(!a.cleared&&a.points.some(p=>near(p,point,CLEAR))){a.cleared=true;changed=true}}return changed}
 function nearby(areas,point){return areas.some(a=>!a.cleared&&a.points.some(p=>near(p,point,CLEAR)))}
 function valid(a){return typeof a?.id==='string'&&Array.isArray(a.points)&&a.points.length>0&&a.points.length<=MAX_POINTS&&a.points.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)&&Math.abs(p.x)<1e7&&Math.abs(p.y)<1e7)&&typeof a.cleared==='boolean'}
 return {observe,clearNearby,nearby,valid,LINK};
})();
if(typeof module!=='undefined')module.exports=InfectionAreas;
