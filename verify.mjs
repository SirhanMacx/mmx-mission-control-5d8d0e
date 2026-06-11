import { chromium } from "/Volumes/CURRICULA/00_ACTIVE_CURRENT_PROJECTS/Review_Arcade/mr-macs-review-arcade-live/node_modules/playwright-core/index.mjs";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";

const ROOT = process.argv[2] || "/tmp/mmx_mc";
const BASE = process.argv[3]; // if provided, test live URL instead of local server
const SHOTS = "/tmp/mmx_shots";
const MIME = {".html":"text/html",".js":"text/javascript",".css":"text/css",".json":"application/json",".txt":"text/plain"};

let server, base = BASE;
if (!BASE){
  server = http.createServer((req,res)=>{
    let p = decodeURIComponent(req.url.split("?")[0]); if (p==="/") p="/index.html";
    const fp = path.join(ROOT, p);
    if (!fp.startsWith(ROOT) || !fs.existsSync(fp)){ res.writeHead(404); return res.end("404"); }
    res.writeHead(200,{"Content-Type":MIME[path.extname(fp)]||"application/octet-stream"});
    res.end(fs.readFileSync(fp));
  });
  await new Promise(r=>server.listen(0,r));
  base = `http://localhost:${server.address().port}`;
}

const fails=[], errs=[];
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport:{width:1280,height:900} });
const page = await ctx.newPage();
page.on("console", m=>{ if(m.type()==="error") errs.push(m.text()); });
page.on("pageerror", e=>errs.push("PAGEERROR: "+e.message));
const ok=(c,m)=>{ console.log((c?"PASS":"FAIL")+" — "+m); if(!c) fails.push(m); };

// 1. index IS the dashboard — no gate
await page.goto(base+"/index.html",{waitUntil:"networkidle"});
ok((await page.title()).includes("Mission Control"), "index page title");
ok(await page.$('meta[content="noindex,nofollow"]')!==null, "index has noindex meta");
ok(await page.$("#gate")===null && await page.$("#pc")===null, "no passcode gate on index");
ok(page.url().includes("index.html"), "no redirect away from index");
ok(await page.$("#road3d")!==null, "index renders the dashboard (Year Road canvas present)");
await page.waitForTimeout(2500); // let three.js + data load
await page.screenshot({path:SHOTS+"/01_index_dashboard.png"});

// 2. dashboard.html still works for old bookmarks
const page2 = await ctx.newPage();
page2.on("console", m=>{ if(m.type()==="error") errs.push("dash: "+m.text()); });
page2.on("pageerror", e=>errs.push("dash PAGEERROR: "+e.message));
await page2.goto(base+"/dashboard.html",{waitUntil:"networkidle"});
ok(await page2.$("#road3d")!==null, "dashboard.html still serves the dashboard");
ok(page2.url().includes("dashboard.html"), "dashboard.html does not bounce to a gate");
await page2.waitForTimeout(1500);
await page2.screenshot({path:SHOTS+"/02_dashboard.png"});
await page2.close();

// 4. Year Road renders (canvas has non-trivial pixels)
const canvasOk = await page.evaluate(()=>{
  const c=document.getElementById("road3d"); if(!c) return false;
  return c.width>0 && c.height>0;
});
ok(canvasOk, "Year Road canvas sized");
const heroSub = await page.textContent("#heroSub");
ok(/178 instructional days/.test(heroSub) && /landmarks/.test(heroSub), "hero shows 178 days + landmarks: "+heroSub);

// 5. spot-check dates via search + scrub
async function jumpToDate(dateStr){
  // use the scrub by computing index: search box is simpler
  await page.fill("#search", dateStr);
  await page.waitForTimeout(250);
  const sel = await page.$(`.search-res .sr[data-i]`);
  // search matches title text, not date; instead drive via evaluate on the module isn't exposed.
  // Use scrub: find index by querying rendered week? Simplest: set scrub by date through global.
}
// Drive jumps deterministically by setting the range input to the day index (compute from data).
const data = await page.evaluate(async ()=>{
  const r = await fetch("data/days.json"); const j = await r.json();
  return j.days.map(d=>({date:d.date, ap:d.ap_psych.title, apT:d.ap_psych.day_type,
    g9:d.global9.title, g9T:d.global9.day_type,
    enl:d.enl?d.enl.title:"", enlT:d.enl?d.enl.day_type:"", kev:d.key_event}));
});
function idxOf(date){ return data.findIndex(d=>d.date===date); }
async function gotoIdx(i){
  await page.$eval("#scrub",(el,v)=>{el.value=v; el.dispatchEvent(new Event("input"));}, i);
  await page.waitForTimeout(500);
}

// Sep 1 = first day / launch
await gotoIdx(idxOf("2026-09-01"));
let dDate = await page.textContent("#dDate");
ok(/Sep 1, 2026/.test(dDate), "Sep 1 selected: "+dDate);
ok((await page.textContent("#dKev")).includes("First student day"), "Sep 1 key event shown");
await page.screenshot({path:SHOTS+"/03_sep1.png"});

// an October Thursday quiz day — find one in data
const octQuiz = data.find(d=>d.date.startsWith("2026-10") && (d.apT==="quiz"||d.g9T==="quiz") && new Date(d.date+"T12:00").getDay()===4);
await gotoIdx(idxOf(octQuiz.date));
const chips = await page.$$eval(".chip",els=>els.map(e=>e.textContent.trim().toLowerCase()));
ok(chips.some(c=>c.includes("quiz")||c.includes("test")||c.includes("content")), "Oct Thursday shows a day-type chip: "+octQuiz.date+" "+chips.join("/"));
await page.screenshot({path:SHOTS+"/04_oct_thursday.png"});

// EIE Jun 3 2027
await gotoIdx(idxOf("2027-06-03"));
ok((await page.textContent("#dKev")).includes("EIE"), "Jun 3 EIE key event");
const g9chip = await page.$$eval(".card.g9 .chip",els=>els.map(e=>e.textContent.trim()));
ok(g9chip.join(" ").toUpperCase().includes("EIE"), "Jun 3 G9 chip = EIE: "+g9chip.join(","));
await page.screenshot({path:SHOTS+"/05_eie_jun3.png"});

// AP exam week (May 12 2027)
await gotoIdx(idxOf("2027-05-12"));
const apchip = await page.$$eval(".card.ap .chip",els=>els.map(e=>e.textContent.trim()));
ok(apchip.join(" ").toUpperCase().includes("EXAM"), "May 12 AP chip = Exam: "+apchip.join(","));
await page.screenshot({path:SHOTS+"/06_apexam.png"});

// last day Jun 25
await gotoIdx(idxOf("2027-06-25"));
ok((await page.textContent("#dKev")).includes("Last day"), "Jun 25 last day key event");
await page.screenshot({path:SHOTS+"/07_lastday.png"});

// 5b. ENL SPLIT PROOFS — ENL is a separate course, not lockstep with 9R
// three cards render
const nCards = await page.$$eval(".cards .card", e=>e.length);
ok(nCards===3, "day panel renders THREE prep cards (AP | 9R | ENL): "+nCards);
ok(await page.$(".card.enl")!==null, "ENL card present with its own class/accent");

// Sep 3 2026: ENL = Geography vocab while 9R = its own lesson (the proof of the split)
await gotoIdx(idxOf("2026-09-03"));
const sep3enl = await page.$eval(".card.enl h3", e=>e.textContent);
const sep3g9  = await page.$eval(".card.g9 h3",  e=>e.textContent);
ok(/Geography/i.test(sep3enl), "Sep 3 ENL = Geography & Vocabulary: '"+sep3enl+"'");
ok(/World Map from Memory/i.test(sep3g9), "Sep 3 9R = its own lesson: '"+sep3g9+"'");
ok(sep3enl.trim()!==sep3g9.trim(), "Sep 3 ENL ≠ 9R (not lockstep)");
await page.screenshot({path:SHOTS+"/09_sep3_split.png"});

// an October day: ENL in RVC while 9R is elsewhere
await gotoIdx(idxOf("2026-10-05"));
const oct5enl = await page.$eval(".card.enl h3", e=>e.textContent);
const oct5unit = await page.$eval(".card.enl .unit", e=>e.textContent);
const oct5g9 = await page.$eval(".card.g9 h3", e=>e.textContent);
ok(/Hammurabi/i.test(oct5enl) && /River Valley/i.test(oct5unit),
   "Oct 5 ENL in RVC (Hammurabi): '"+oct5enl+"' / "+oct5unit);
ok(!/Hammurabi/i.test(oct5g9), "Oct 5 9R on a different lesson: '"+oct5g9+"'");
await page.screenshot({path:SHOTS+"/10_oct5_rvc.png"});

// Jun 22 2027: ENL Time Travel presentations
await gotoIdx(idxOf("2027-06-22"));
const jun22enl = await page.$eval(".card.enl h3", e=>e.textContent);
ok(/Time Travel presentations/i.test(jun22enl), "Jun 22 ENL = Time Travel presentations: '"+jun22enl+"'");
await page.screenshot({path:SHOTS+"/11_jun22_timetravel.png"});

// no lockstep copy anywhere in the UI
const bodyText = await page.evaluate(()=>document.body.innerText);
ok(!/lockstep/i.test(bodyText), "no 'lockstep' copy in the UI");

// 6. copy box present
const hasPost = await page.$(".post-box .copybtn");
ok(hasPost!==null, "Classroom post copy box present");
const matCopy = await page.$(".materials .copy");
ok(matCopy!==null, "materials copy buttons present");

// 7. search works (Hammurabi-ish term)
await page.fill("#search","mock");
await page.waitForTimeout(300);
const srCount = await page.$$eval(".search-res .sr[data-i]",e=>e.length).catch(()=>0);
ok(srCount>0, "search 'mock' returns results: "+srCount);
await page.fill("#search","");

// 8. week strip + calendar present
ok(await page.$$eval("#weekstrip .wd",e=>e.length)>=5, "week strip has 5 cells");
ok(await page.$("#cal table")!==null, "calendar renders");

// 9. checkboxes persist
const cb = await page.$('.status input[type=checkbox]');
await cb.check();
ok(await cb.isChecked(), "status checkbox toggles");

// 10. print week view builds (emulate print media)
await page.evaluate(()=>document.getElementById("printWeekBtn").click());
await page.waitForTimeout(300);
const pwHtml = await page.$eval("#pwSheet",e=>e.innerHTML);
ok(pwHtml.includes("Week Plan") && pwHtml.includes("Post:"), "print week sheet built with posts");
await page.emulateMedia({media:"print"});
await page.screenshot({path:SHOTS+"/08_print_week.png", fullPage:true});
await page.emulateMedia({media:"screen"});

// console errors
ok(errs.length===0, "0 console errors"+(errs.length?": "+JSON.stringify(errs.slice(0,5)):""));

console.log("\n==== RESULT ====");
console.log(fails.length? `FAILED (${fails.length}): \n - `+fails.join("\n - ") : "ALL PASS");
console.log("console errors:", errs.length);
await browser.close();
if (server) server.close();
process.exit(fails.length?1:0);
