/* Shared staged trainer layout. Never writes trainer values or invokes training actions. */
(() => {
"use strict";
const tr=k=>typeof t==="function"?t(k):k;
function init(){
 const grid=document.querySelector(".main-grid"),sidebar=grid?.querySelector(".sidebar"),monitor=grid?.querySelector(".console-container");
 if(!grid||!sidebar||!monitor)return;
 const panels=Array.from(sidebar.querySelectorAll(".panel"));
 const terminal=document.getElementById("terminal"),dataset=document.getElementById("ds-grid"),gallery=document.getElementById("gallery");
 const datasetSection=dataset?.parentElement, gallerySection=gallery?.parentElement;
 const consoleTitle=terminal?.previousElementSibling;
 if(panels.length!==5||!terminal||!datasetSection||!gallerySection||!consoleTitle||datasetSection.parentElement!==monitor||gallerySection.parentElement!==monitor)return;
 // Exact control IDs identify stages, independent of translated headings.
 const find=id=>document.getElementById(id)?.closest(".panel");
 const cache=find("precache_cache_dir"),training=find("train_total_steps"),exportPanel=find("export_final_name"),preview=find("train_preview_every");
 const token=panels.find(p=>![cache,training,exportPanel,preview].includes(p));
 if(new Set([cache,training,exportPanel,preview,token]).size!==5||![cache,training,exportPanel,preview,token].every(Boolean))return;
 const nav=document.createElement("nav");nav.className="orki-tools orki-pilot-nav no-i18n";nav.setAttribute("aria-label",tr("Training navigation"));
 const localized=[];
 const mk=(tag,txt)=>{const e=document.createElement(tag);e.textContent=tr(txt);localized.push([e,txt]);return e;};
 document.addEventListener("orkilab:language-changed",()=>{for(const [e,key] of localized)e.textContent=tr(key);nav.setAttribute("aria-label",tr("Training navigation"));});
 const btn=(label,action)=>{const b=mk("button",label);b.type="button";b.addEventListener("click",action);return b;};
 const stages=[["Project and pre-cache",[cache]],["Dataset",[]],["Training",[training]],["Previews",[preview]],["Export",[exportPanel]],["Logs",[]],["Credentials",[token]]];
 const advancedIds=["train_lr_scheduler","train_warmup_steps","train_lr_cycles","train_lora_alpha","train_use_rslora","train_use_loraplus","train_use_dora","train_dora_normfix","train_compute_precision","train_lora_targets","train_precision","train_grad_accum","train_save_every","train_seed","train_use_lokr","train_lokr_factor"];
 const advanced=new Set(advancedIds.map(id=>document.getElementById(id)?.closest(".form-group")).filter(Boolean));
 // A shared container may also contain a basic setting; never conceal that container.
 for(const group of advanced){if(Array.from(group.querySelectorAll("input,select,textarea")).some(e=>e.id&&!advancedIds.includes(e.id)))advanced.delete(group);}
 const engine=document.body.dataset.orkiEngine||"sdxl";
 const preference="orkilab."+engine+".mode";
 let stage="Training",mode="Expert";
 try{const saved=localStorage.getItem(preference);if(saved==="Basic"||saved==="Expert")mode=saved;}catch{}
 const buttons=new Map(), modes=new Map();
 const hide=(e,on)=>{if(e)e.dataset.orkiStageHidden=on?"1":"0";};
 function render(){
   const selected=stages.find(x=>x[0]===stage)[1]; const only=stage==="Dataset"||stage==="Logs";
   grid.classList.toggle("orki-monitor-only",only);
   for(const p of panels){hide(p,!selected.includes(p));if(selected.includes(p)&&p.classList.contains("collapsed"))p.querySelector(".panel-title[onclick]")?.click();}
   // Keep the actual status and console visible in every stage.
   hide(datasetSection,stage!=="Dataset");hide(gallerySection,stage!=="Previews");
   for(const group of advanced)group.dataset.orkiBasicHidden=mode==="Basic"?"1":"0";
   for(const [k,b] of buttons)b.setAttribute("aria-pressed",String(k===stage));
   for(const [k,b] of modes)b.setAttribute("aria-pressed",String(k===mode));
 }
 nav.append(mk("strong","Training navigation"));
 for(const [label] of stages){const b=btn(label,()=>{stage=label;render();});buttons.set(label,b);nav.append(b);}
 const row=document.createElement("div");row.className="orki-mode-row";
 for(const label of ["Basic","Expert"]){const b=btn(label,()=>{mode=label;try{localStorage.setItem(preference,mode);}catch{}render();});modes.set(label,b);row.append(b);}
 nav.append(row,mk("p","Basic mode hides advanced parameters without changing their values. Review Expert before training."));
 const classic=btn("Classic layout",()=>{
   document.body.classList.remove("orki-pilot");grid.classList.remove("orki-monitor-only");nav.hidden=true;nav.style.display="none";
   for(const p of panels)delete p.dataset.orkiStageHidden;
   for(const p of [datasetSection,gallerySection])delete p.dataset.orkiStageHidden;
   for(const p of advanced)delete p.dataset.orkiBasicHidden;
   restore.hidden=false;
 });
 nav.append(classic);
 const restore=btn("Modern layout",()=>{restore.hidden=true;nav.hidden=false;nav.style.display="";document.body.classList.add("orki-pilot");render();});
 restore.hidden=true;grid.before(restore);grid.prepend(nav);document.body.classList.add("orki-pilot");render();
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();
