'use strict';
// Shared knowledge contains locations only. Progress and availability stay in worlds.
const SharedKnown=(()=>{
 const kinds=['resources','bases','cysts','landmarks'];
 const blank=()=>Object.fromEntries(kinds.map(k=>[k,[]]));
 function clean(kind,v){
  if(!v||!Number.isFinite(v.x)||!Number.isFinite(v.y)||Math.abs(v.x)>1e7||Math.abs(v.y)>1e7)return null;
  if(kind==='resources')return typeof v.type==='string'&&v.type.length<=100?{type:v.type,x:v.x,y:v.y}:null;
  if(kind==='bases')return typeof v.id==='string'&&typeof v.name==='string'?{id:v.id,name:v.name,x:v.x,y:v.y}:null;
  if(kind==='cysts')return typeof v.key==='string'?{key:v.key,x:v.x,y:v.y}:null;
  if(kind==='landmarks')return typeof v.id==='string'&&typeof v.name==='string'&&v.kind!=='abandoned_base'?{id:v.id,name:v.name,kind:typeof v.kind==='string'?v.kind:'',x:v.x,y:v.y}:null;
  return null;
 }
 function index(items){const buckets=new Map();for(const r of items){const x=Math.floor(r.x/100),y=Math.floor(r.y/100),key=r.type+'|'+x+'|'+y;if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(r)}return buckets}
 function near(buckets,r){const x=Math.floor(r.x/100),y=Math.floor(r.y/100);for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)for(const v of buckets.get(r.type+'|'+(x+dx)+'|'+(y+dy))||[])if(Math.hypot(v.x-r.x,v.y-r.y)<=100)return true;return false}
 function addBucket(buckets,r){const key=r.type+'|'+Math.floor(r.x/100)+'|'+Math.floor(r.y/100);if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(r)}
 function merge(previous,worlds){
  const out=blank(), ids={bases:new Set(),cysts:new Set(),landmarks:new Set()}, buckets=index([]);
  for(const source of [previous,...worlds.filter(w=>w&&w.mapVersion===2&&!w.image)])for(const kind of kinds)for(const value of Array.isArray(source?.[kind])?source[kind]:[]){
   const v=clean(kind,value);if(!v)continue;
   if(kind==='resources'){if(near(buckets,v))continue;addBucket(buckets,v)}else{const id=kind==='cysts'?v.key:v.id;if(ids[kind].has(id))continue;ids[kind].add(id)}
   out[kind].push(v);
  }
  return out;
 }
 function undiscovered(shared,world,kind){
  const known=(world?.[kind]||[]).map(v=>clean(kind,v)).filter(Boolean);
  if(kind==='resources'){const buckets=index(known);return (shared?.resources||[]).filter(v=>!near(buckets,v))}
  const key=kind==='cysts'?'key':'id',ids=new Set(known.map(v=>v[key]));return (shared?.[kind]||[]).filter(v=>!ids.has(v[key]));
 }
 return {merge,undiscovered};
})();
if(typeof module!=='undefined')module.exports=SharedKnown;
