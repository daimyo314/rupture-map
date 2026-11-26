/* Translate replicated values into presentation state without guessing missing data. */
(function(root){
 'use strict';
 function display(wave){
  const visual=wave?.visuals,fade=Number.isInteger(visual?.fadeout)&&visual.fadeout>=0&&visual.fadeout<=3?visual.fadeout:null;
  const grow=Number.isInteger(visual?.growback)&&visual.growback>=0&&visual.growback<=3?visual.growback:null;
  const water=typeof visual?.water_evaporated==='boolean'?visual.water_evaporated:null;
  const phase=Number.isInteger(wave?.phase)?wave.phase:null;
  return {fade,grow,water,moon:grow===null?null:grow===1,phase,phaseName:({0:'Normal',1:'Rupture',2:'Rupture',3:'Regrowth',4:'Stable'})[phase]||'Unknown',growColor:grow===null?'unknown':grow===0?(fade===null?'unknown':fade>0?'black':'dark-green'):['','purple','light-green','green'][grow]};
 }
 const api={display};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.Forecast=api;
})(typeof globalThis!=='undefined'?globalThis:this);
