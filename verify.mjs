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

// 1. gate page loads
await page.goto(base+"/index.html",{waitUntil:"networkidle"});
ok(await page.title()==="Mission Control", "gate page title");
ok(await page.$('meta[content="noindex,nofollow"]')!==null, "gate has noindex meta");
await page.screenshot({path:SHOTS+"/01_gate.png"});

// 2. wrong passcode rejected
await page.fill("#pc","wrong-code"); await page.click("button[type=submit]");
await page.waitForTimeout(300);
ok((await page.textContent("#err")).includes("Wrong"), "wrong passcode rejected");
ok(page.url().includes("index.html")||page.url().endsWith("/"), "wrong passcode stays on gate");

// 3. correct passcode enters
await page.fill("#pc","macs-mission-2027"); await page.click("button[type=submit]");
await page.waitForURL(/dashboard\.html/,{timeout:5000}).catch(()=>{});
ok(page.url().includes("dashboard.html"), "correct passcode enters dashboard");
await page.waitForTimeout(2500); // let three.js + data load
await page.screenshot({path:SHOTS+"/02_dashboard.png"});

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
    g9:d.global9.title, g9T:d.global9.day_type, kev:d.key_event}));
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
