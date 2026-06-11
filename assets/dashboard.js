// Mission Control dashboard — the 2D workhorse + glue to the 3D Year Road.
import { initRoad } from "./road3d.js";

// gate guard
if (sessionStorage.getItem("mmx_auth") !== "1") location.replace("index.html");

const DT = {
  content:"#4d9dff", quiz:"#ffc34d", test:"#ff5a6e", crq:"#c98bff", eie:"#ff4d9d",
  mock:"#ff8a3d", project:"#3ddc84", review:"#28e0d4", exam:"#ff2e5b",
  launch:"#8b7dff", closeout:"#8ea0c4",
};
const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

let DAYS = [], META = {}, idx = 0, road = null;
let calMonth = 0, calYear = 0;          // month-cursor for mini calendar
const byDate = {};

const $ = s => document.querySelector(s);

fetch("data/days.json").then(r=>r.json()).then(j=>{
  DAYS = j.days; META = j.meta;
  DAYS.forEach((d,i)=>{ d._i=i; byDate[d.date]=d; });
  // restore last index or pick "today"/next school day
  const saved = +localStorage.getItem("mmx_idx");
  idx = (saved>=0 && saved<DAYS.length) ? saved : pickToday();
  road = initRoad(DAYS, jumpTo);
  $("#heroSub").textContent = `${META.instructional_days} instructional days · ${road.markerCount} landmarks · click or scrub to jump`;
  wireUI();
  render();
});

function pickToday(){
  const t = new Date().toISOString().slice(0,10);
  for (let i=0;i<DAYS.length;i++) if (DAYS[i].date>=t) return i;
  return 0;
}

function jumpTo(i){ idx = Math.max(0, Math.min(DAYS.length-1, i)); render(); }

function statusKey(date, prep, field){ return `mmx_st_${date}_${prep}_${field}`; }

function render(){
  const d = DAYS[idx];
  localStorage.setItem("mmx_idx", idx);
  // daybar
  const dt = new Date(d.date+"T12:00:00");
  $("#dDate").textContent = `${MONTHS[dt.getMonth()].slice(0,3)} ${dt.getDate()}, ${dt.getFullYear()}`;
  $("#dDow").textContent = d.day_of_week;
  $("#dMp").textContent = `Day ${idx+1} / ${DAYS.length}`;
  const kev = $("#dKev");
  if (d.key_event){ kev.style.display=""; kev.textContent = "★ "+d.key_event; }
  else kev.style.display="none";
  // cards
  $("#cards").innerHTML = card(d, "ap", "AP Psychology ×3", d.ap_psych) + card(d, "g9", "Global 9R + ENL", d.global9);
  wireCards(d);
  // 3D + scrub
  $("#scrub").value = idx;
  $("#scrubPos").textContent = `Day ${idx+1} / ${DAYS.length}`;
  if (road) road.setCam(idx);
  renderWeek();
  // sync calendar cursor to selected day
  calMonth = dt.getMonth(); calYear = dt.getFullYear();
  renderCal();
}

function chip(dtype, label){
  const c = DT[dtype]||"#8ea0c4";
  return `<span class="chip" style="background:${c}22;color:${c};border:1px solid ${c}55">
    <span class="d" style="background:${c}"></span>${label}</span>`;
}

function card(day, prep, name, p){
  const unit = p.unit ? `<div class="unit">${esc(p.unit)}${p.lesson_no?` · Lesson ${p.lesson_no}`:""}</div>` : "";
  const mats = p.materials.map(m=>
    `<li>${esc(m)}<span class="copy" data-copy="${esc(m)}">copy</span></li>`).join("");
  const enl = (prep==="g9" && p.enl_note) ? `<div class="enl"><b>ENL parallel:</b> ${esc(p.enl_note)}</div>` : "";
  const links = p.links ? `<div class="qlinks">
      <a>${esc(p.links.arcade)}</a><a>${esc(p.links.world)}</a>
      <span class="pathchip" data-copy="${esc(p.links.folder)}" title="copy folder path">📁 copy curriculum path</span>
    </div>` : "";
  const st = ["printed","posted","graded"].map(f=>{
    const k = statusKey(day.date, prep, f);
    const on = localStorage.getItem(k)==="1" ? "checked":"";
    return `<label><input type="checkbox" data-st="${k}" ${on}>${f}</label>`;
  }).join("");
  return `<div class="card ${prep}">
    <div class="ph"><span class="prep">${name}</span>${chip(p.day_type, p.day_type_label)}</div>
    ${unit}
    <h3>${esc(p.title)}</h3>
    <div class="sect"><div class="lbl">Materials — print / open</div><ul class="materials">${mats}</ul></div>
    <div class="sect"><div class="lbl">Students</div><p>${esc(p.student_do)}</p></div>
    <div class="sect"><div class="lbl">You</div><p>${esc(p.teacher_do)}</p></div>
    <div class="sect"><div class="lbl">Google Classroom post</div>
      <div class="post-box"><button class="copybtn" data-postcopy>Copy</button>${esc(p.classroom_post)}</div>
    </div>
    ${enl}
    ${links}
    <div class="status">${st}</div>
  </div>`;
}

function wireCards(day){
  document.querySelectorAll("[data-copy]").forEach(el=>
    el.onclick = ()=>copy(el.getAttribute("data-copy"), "Copied"));
  document.querySelectorAll("[data-postcopy]").forEach(btn=>btn.onclick=()=>{
    const box = btn.parentElement;
    copy(box.textContent.replace(/^Copy/,"").trim(), "Classroom post copied");
    box.classList.add("copied"); btn.textContent="Copied ✓";
    setTimeout(()=>{box.classList.remove("copied"); btn.textContent="Copy";},1600);
  });
  document.querySelectorAll("[data-st]").forEach(cb=>cb.onchange=()=>{
    localStorage.setItem(cb.getAttribute("data-st"), cb.checked?"1":"0");
  });
}

function renderWeek(){
  // Mon–Fri of the selected week
  const sel = new Date(DAYS[idx].date+"T12:00:00");
  const monday = new Date(sel); monday.setDate(sel.getDate() - ((sel.getDay()+6)%7));
  let html="";
  for (let k=0;k<5;k++){
    const dd = new Date(monday); dd.setDate(monday.getDate()+k);
    const ds = dd.toISOString().slice(0,10);
    const rec = byDate[ds];
    const isSel = rec && rec._i===idx;
    if (rec){
      const ac=DT[rec.ap_psych.day_type], gc=DT[rec.global9.day_type];
      html += `<div class="wd ${isSel?'sel':''}" data-i="${rec._i}">
        <div class="wdh">${["MON","TUE","WED","THU","FRI"][k]}</div>
        <div class="wdn">${dd.getDate()}</div>
        <div class="bars">
          <div class="bar" style="background:${ac}" title="AP: ${rec.ap_psych.day_type_label}"></div>
          <div class="bar" style="background:${gc}" title="G9: ${rec.global9.day_type_label}"></div>
        </div>
        ${rec.key_event?`<div class="ev">★ ${esc(rec.key_event.split('(')[0].trim())}</div>`:""}
      </div>`;
    } else {
      html += `<div class="wd" style="opacity:.4;cursor:default">
        <div class="wdh">${["MON","TUE","WED","THU","FRI"][k]}</div>
        <div class="wdn">${dd.getDate()}</div>
        <div class="wdh" style="margin-top:8px">no school</div></div>`;
    }
  }
  $("#weekstrip").innerHTML = html;
  document.querySelectorAll("#weekstrip .wd[data-i]").forEach(el=>
    el.onclick=()=>jumpTo(+el.getAttribute("data-i")));
  // legend
  const keys = [["content","Content"],["quiz","Quiz"],["test","Test"],["crq","CRQ"],["eie","EIE"],
    ["mock","Mock"],["project","Project"],["review","Review"],["exam","Exam"],["launch","Launch"]];
  $("#legend2").innerHTML = keys.map(([k,l])=>
    `<span class="lg"><span class="dot" style="background:${DT[k]}"></span>${l}</span>`).join("");
}

function renderCal(){
  const first = new Date(calYear, calMonth, 1);
  const startDow = (first.getDay()+6)%7;           // Mon=0
  const dim = new Date(calYear, calMonth+1, 0).getDate();
  let cells="";
  for (let i=0;i<startDow;i++) cells+=`<td><div class="cell off"></div></td>`;
  for (let d=1; d<=dim; d++){
    const ds = `${calYear}-${String(calMonth+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
    const rec = byDate[ds];
    if (rec){
      const sel = rec._i===idx ? "sel":"";
      const kev = rec.key_event ? "kev":"";
      const pip = DT[rec.global9.day_type];
      cells += `<td><div class="cell school ${sel} ${kev}" data-i="${rec._i}">${d}
        <span class="pip" style="background:${pip}"></span></div></td>`;
    } else {
      cells += `<td><div class="cell off">${d}</div></td>`;
    }
    if ((startDow+d)%7===0) cells+="</tr><tr>";
  }
  $("#cal").innerHTML = `
    <div class="calhead">
      <button id="calPrev">‹</button>
      <span class="m">${MONTHS[calMonth]} ${calYear}</span>
      <button id="calNext">›</button>
    </div>
    <table><thead><tr>${["M","T","W","T","F","S","S"].map(x=>`<th>${x}</th>`).join("")}</tr></thead>
    <tbody><tr>${cells}</tr></tbody></table>`;
  $("#calPrev").onclick=()=>{calMonth--; if(calMonth<0){calMonth=11;calYear--;} renderCal();};
  $("#calNext").onclick=()=>{calMonth++; if(calMonth>11){calMonth=0;calYear++;} renderCal();};
  document.querySelectorAll("#cal .cell.school").forEach(el=>
    el.onclick=()=>jumpTo(+el.getAttribute("data-i")));
}

function wireUI(){
  $("#prevDay").onclick=()=>jumpTo(idx-1);
  $("#nextDay").onclick=()=>jumpTo(idx+1);
  $("#todayBtn").onclick=()=>jumpTo(pickToday());
  $("#scrub").oninput=e=>{ idx=+e.target.value; render(); };
  $("#printWeekBtn").onclick=printWeek;
  document.addEventListener("keydown",e=>{
    if (e.target.tagName==="INPUT") return;
    if (e.key==="ArrowLeft") jumpTo(idx-1);
    if (e.key==="ArrowRight") jumpTo(idx+1);
  });
  // search
  const si=$("#search"), sr=$("#searchRes");
  si.oninput=()=>{
    const q=si.value.trim().toLowerCase();
    if (q.length<2){ sr.classList.remove("open"); return; }
    const hits=[];
    for (const d of DAYS){
      const hay=(d.ap_psych.title+" "+d.global9.title+" "+(d.global9.topic||"")+" "+
                 (d.key_event||"")+" "+d.ap_psych.day_type+" "+d.global9.day_type).toLowerCase();
      if (hay.includes(q)){
        const which = d.global9.title.toLowerCase().includes(q)||((d.global9.topic||"").toLowerCase().includes(q)) ? d.global9.title : d.ap_psych.title;
        hits.push({i:d._i, date:d.date, t:which});
      }
      if (hits.length>=40) break;
    }
    sr.innerHTML = hits.length ? hits.map(h=>
      `<div class="sr" data-i="${h.i}"><span class="d">${h.date}</span> — ${esc(h.t)}</div>`).join("")
      : `<div class="sr">No matches</div>`;
    sr.classList.add("open");
    sr.querySelectorAll(".sr[data-i]").forEach(el=>el.onclick=()=>{
      jumpTo(+el.getAttribute("data-i")); sr.classList.remove("open"); si.value="";
    });
  };
  document.addEventListener("click",e=>{ if(!e.target.closest(".search")) sr.classList.remove("open"); });
}

function printWeek(){
  const sel=new Date(DAYS[idx].date+"T12:00:00");
  const monday=new Date(sel); monday.setDate(sel.getDate()-((sel.getDay()+6)%7));
  let rows="";
  for (let k=0;k<5;k++){
    const dd=new Date(monday); dd.setDate(monday.getDate()+k);
    const ds=dd.toISOString().slice(0,10); const rec=byDate[ds];
    const hdr=`${["Monday","Tuesday","Wednesday","Thursday","Friday"][k]} · ${MONTHS[dd.getMonth()]} ${dd.getDate()}`;
    if (!rec){ rows+=`<div class="pw-day"><h2>${hdr} — no school</h2></div>`; continue; }
    rows += `<div class="pw-day"><h2>${hdr}${rec.key_event?` ★ ${esc(rec.key_event)}`:""}</h2>
      ${pwPrep("AP Psychology ×3", rec.ap_psych)}
      ${pwPrep("Global 9R + ENL", rec.global9)}</div>`;
  }
  $("#pwSheet").innerHTML = `<h1>Week Plan — Mr. Mac · 2026-27</h1>
    <p class="pwsub">Week of ${MONTHS[monday.getMonth()]} ${monday.getDate()}, ${monday.getFullYear()}</p>${rows}`;
  window.print();
}
function pwPrep(name,p){
  return `<div class="pw-prep">
    <div class="pn">${name} — [${p.day_type_label}]</div>
    <div class="pt">${esc(p.title)}${p.unit?` · ${esc(p.unit)}`:""}</div>
    <div class="pm">Materials: ${p.materials.map(esc).join(" · ")}</div>
    <div class="pm">You: ${esc(p.teacher_do)}</div>
    <div class="pc">Post: ${esc(p.classroom_post)}</div>
  </div>`;
}

function copy(text, msg){
  navigator.clipboard?.writeText(text).then(()=>toast(msg||"Copied")).catch(()=>toast("Copy failed"));
}
function toast(m){
  const t=$("#toast"); t.textContent=m; t.classList.add("show");
  clearTimeout(t._tm); t._tm=setTimeout(()=>t.classList.remove("show"),1500);
}
function esc(s){ return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
