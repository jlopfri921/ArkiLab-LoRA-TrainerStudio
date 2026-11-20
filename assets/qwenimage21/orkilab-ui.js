/* Shared enhancements, deliberately independent of trainer/API logic. */
(() => {
"use strict";
const text=(key)=>typeof t==="function"?t(key):key;
const node=(tag,content,className)=>{const el=document.createElement(tag);if(content!==undefined)el.textContent=content;if(className)el.className=className;return el;};
const localized=[];
const button=(name,fn)=>{const b=node("button",text(name),"no-i18n");b.type="button";b.addEventListener("click",fn);localized.push(()=>b.textContent=text(name));return b;};
document.addEventListener("orkilab:language-changed",()=>{for(const refresh of localized)refresh();});
const topics=[
[/^HF Token|Hugging Face Token/i,"Authentication token for gated Hugging Face models. Only enter your own token; never share it."],
[/Project Name/i,"Identifies the training run. Use a distinct name for each project."],
[/Trigger Word/i,"A distinctive word used in captions and generation prompts to invoke the concept learned by the LoRA."],
[/Dataset Path|Dataset reference|Folder with the images/i,"Location or reference for the training samples. Select the intended dataset; this field does not create training images."],
[/Cache Folder|Pre.Cache Settings/i,"Pre-cache computes and stores latents or embeddings before training to avoid repeating expensive calculations."],
[/Total Steps/i,"Number of optimizer updates to perform. More steps may improve learning but can also overfit."],
[/Learning Rate/i,"Size of each optimizer update. Too high can destabilize training; too low can make learning slow."],
[/LR Scheduler/i,"Controls how the learning rate evolves over the training run."],
[/Warmup Steps/i,"Initial updates during which the learning rate gradually increases when the selected scheduler supports warmup."],
[/LoRA Rank|LoRA Rank \(R\)/i,"Capacity of the adapter matrices. Higher rank may learn more detail but increases memory use and file size."],
[/LoRA Alpha/i,"Scaling parameter for the adapter. Its effect depends on rank and the selected LoRA method."],
[/Batch Size/i,"Number of samples processed per forward/backward batch. Larger batches generally require more memory."],
[/Grad Accum/i,"Number of batches accumulated before an optimizer update. This can increase effective batch size without increasing the batch itself."],
[/Save Every/i,"Interval between saved checkpoints, usually measured in training steps. More frequent saves use more disk space."],
[/Seed/i,"Random seed for reproducibility. Random mode selects a different seed when supported."],
[/Preview Every/i,"Interval between sample previews. Previews help monitor progress but take time and memory."],
[/Preview Steps/i,"Number of generation steps used for a preview; not the number of training updates."],
[/LoRA Targets/i,"Selects the model layers adapted by LoRA. Supported targets vary by engine."],
[/Final LoRA Filename/i,"Name of the exported adapter file. Choose a unique name to avoid confusion with other projects."],
[/UI LoRA Folder/i,"Destination folder for compatible LoRA weights, such as the LoRA directory of ComfyUI."],
[/Resolution/i,"Controls the size or pixel area of samples, depending on the trainer. Higher resolution generally costs more memory."],
[/Caption Mode/i,"Determines how descriptions are selected or formatted for training. Captions should describe the relevant variation."],
[/Block Swap|Resident Blocks/i,"Moves model blocks between GPU and system memory. This can reduce VRAM usage at the cost of speed."],
[/Precision|Quantization|Compute$/i,"Controls numerical representation or computation precision. Lower precision can save memory; compatibility varies by GPU and engine."],
[/Notes$/i,"Optional project notes. They are stored as metadata and do not change training parameters."],
[/Category$/i,"Groups the project by media type; the selected engine still determines training capabilities."],
[/Engine$/i,"Selects the model family for this project. Creating workspace metadata does not launch training."]
];
function openHelp(label,desc){let dialog=document.getElementById("orki-help-dialog");if(!dialog){dialog=node("dialog",undefined,"orki-help-dialog no-i18n");dialog.id="orki-help-dialog";dialog.setAttribute("aria-labelledby","orki-help-heading");const h=node("h2");h.id="orki-help-heading";const p=node("p");p.id="orki-help-content";dialog.append(h,p,button("Close",()=>dialog.close()));document.body.append(dialog);}dialog.querySelector("h2").textContent=label;dialog.querySelector("p").textContent=text(desc);if(!dialog.open)dialog.showModal();}
function labelKey(label){return (typeof I18N!=="undefined" ? Array.from(label.childNodes).map(n=>n.nodeType===3?(I18N.original.get(n)||n.nodeValue):n.textContent).join(" "):label.textContent).trim().replace(/\s+/g," ").replace(/:$/,"");}
function attachHelp(){for(const group of document.querySelectorAll(".form-group,.field,#create>label")){const label=group.matches("label")?group:group.querySelector(":scope > label");if(!label||group.dataset.orkiHelp)continue;const key=labelKey(label);const control=group.querySelector("input,select,textarea");const hint=label.dataset.i18ntitle||label.getAttribute("title")||group.dataset.i18ntitle||group.getAttribute("title")||control?.dataset.i18ntitle||control?.getAttribute("title")||topics.find(([rx])=>rx.test(key))?.[1];if(!hint)continue;group.dataset.orkiHelp="1";if(!label.title)label.title=text(hint);if(group===label){const h=node("small",text(hint),"no-i18n");h.style.color="#a7bad2";group.append(h);localized.push(()=>h.textContent=text(hint));continue;}group.classList.add("orki-help-group");const b=node("button","?","orki-help-button no-i18n");b.type="button";b.title=text("Help")+": "+label.textContent.trim();b.setAttribute("aria-label",b.title);localized.push(()=>{b.title=text("Help")+": "+label.textContent.trim();b.setAttribute("aria-label",b.title);});b.addEventListener("click",()=>openHelp(label.textContent.trim(),hint));group.append(b);}}
function sections(){const headers=Array.from(document.querySelectorAll(".panel-title[onclick]"));if(!headers.length)return;const bar=node("div",undefined,"orki-tools");bar.setAttribute("role","navigation");bar.setAttribute("aria-label",text("Section navigation"));const heading=node("strong",text("Section navigation"),"no-i18n");bar.append(heading);localized.push(()=>{heading.textContent=text("Section navigation");bar.setAttribute("aria-label",text("Section navigation"));});const input=node("input");input.type="search";input.className="no-i18n";const refreshSearch=()=>{input.placeholder=text("Search sections");input.setAttribute("aria-label",input.placeholder);};refreshSearch();localized.push(refreshSearch);bar.append(input);const collapsible=h=>h.closest(".panel");const set=(h,on)=>{const p=collapsible(h);if(p&&p.classList.contains("collapsed")===on)h.click();};bar.append(button("Expand all",()=>headers.forEach(h=>set(h,true))),button("Collapse all",()=>headers.forEach(h=>set(h,false))));const links=node("div",undefined,"orki-section-links");const items=headers.map(h=>{const title=h.querySelector("span:not(.toggle-icon)")||h;const name=labelKey(title).replace(/[▼▲]/g,"").trim();const b=button(name,()=>{set(h,true);h.scrollIntoView({block:"start",behavior:"auto"});});links.append(b);return b;});bar.append(links);input.addEventListener("input",()=>{const q=input.value.trim().toLocaleLowerCase();for(const b of items)b.hidden=!b.textContent.toLocaleLowerCase().includes(q);});const grid=document.querySelector(".main-grid");if(grid)grid.before(bar);}
function addLanguage(){if(document.querySelector("#ui-lang,#workspace-language,#orki-language"))return;const host=document.querySelector("header,.wrap>.top,.wrap");if(!host||typeof I18N==="undefined")return;const wrap=node("div",undefined,"orki-tools no-i18n");const label=node("label",text("Language"));const sel=node("select");sel.id="orki-language";label.htmlFor=sel.id;for(const [code,name] of I18N.languages)sel.add(new Option(name,code));sel.value=I18N.lang;wrap.append(label,sel);host.append(wrap);sel.addEventListener("change",async()=>{sel.disabled=true;try{const r=await fetch("/api/i18n",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({language:sel.value})});if(!r.ok)throw Error();await I18N.load(sel.value);label.textContent=text("Language");wrap.title="";}catch(e){sel.value=I18N.lang;wrap.title=text("Language update failed");}finally{sel.disabled=false;}});}
function init(){sections();attachHelp();addLanguage();}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();
