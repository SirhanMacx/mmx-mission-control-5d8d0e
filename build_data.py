#!/usr/bin/env python3
"""Build data/days.json (one entry per instructional day) for Mr. Mac's Mission Control.

Source of truth: Unified_Daily_Calendar_2026-27.csv (178 instructional days).
Enriched with: Global 9R V2 lesson folders (Build_Manifest topic match), AP Psych
day-by-day pacing, day-type classification, materials lists, classroom posts, ENL notes.
"""
import csv, json, os, re, glob, sys
from datetime import datetime, date

ROOT = "/Volumes/CURRICULA/Curriculum_Agent_Workspace_2026_2027/06_Generated_Curricula"
CSV = f"{ROOT}/_Maccarello_Year_Plan_2026-27/Unified_Daily_Calendar_2026-27.csv"
G9R = f"{ROOT}/Global_9R_V2"
OUT = os.path.join(os.path.dirname(__file__), "data", "days.json")

# ---- G9R unit folders -> friendly names + lesson folders indexed by date ----
G9R_UNITS = {}          # unit_num -> {name, slug_folder}
G9R_LESSON_BY_DATE = {} # 'YYYY-MM-DD' -> {folder, slug, unit_num, unit_name, topic}

def load_g9r():
    for ufolder in sorted(glob.glob(f"{G9R}/Unit_*")):
        base = os.path.basename(ufolder)
        m = re.match(r"Unit_(\d+)_(.+)", base)
        if not m:
            continue
        unum = int(m.group(1))
        uname = m.group(2).replace("_", " ")
        G9R_UNITS[unum] = {"name": uname, "folder": base}
        for lf in glob.glob(f"{ufolder}/Lesson_*"):
            lb = os.path.basename(lf)
            lm = re.match(r"Lesson_(\d+)_(\d{4}-\d{2}-\d{2})_(.+)", lb)
            if not lm:
                continue
            lno, ldate, lslug = lm.groups()
            topic = None
            bm = os.path.join(lf, "Build_Manifest.json")
            if os.path.exists(bm):
                try:
                    topic = json.load(open(bm)).get("topic")
                except Exception:
                    pass
            # First lesson dated on a day wins; keep if not already set
            if ldate not in G9R_LESSON_BY_DATE:
                G9R_LESSON_BY_DATE[ldate] = {
                    "folder": lb, "slug": lslug.replace("_", " "),
                    "lesson_no": int(lno), "unit_num": unum,
                    "unit_name": uname, "topic": topic,
                    "path": os.path.join(ufolder, lb),
                }

# ---- day-type classification ----
def classify(text, assess_flag, exam_window=""):
    t = (text or "").lower()
    ew = (exam_window or "").lower()
    if not t:
        return "content"
    if "last day" in t or "close out" in t or "goodbye" in t:
        return "closeout"
    if "mock" in t or "mock final" in t:
        return "mock"
    if "ap psychology exam" in t or "regents exam" in t or "★" in t or "regents" in ew:
        return "exam"
    if "eie final" in t or ("eie" in t and "final" in t):
        return "eie"
    if "unit" in t and "test" in t:
        return "test"
    if re.search(r"\btest\b", t):
        return "test"
    if "quiz" in t:
        return "quiz"
    if "crq" in t:
        return "crq"
    if "eie" in t or "enduring issue" in t:
        return "eie"
    if "project" in t or "capstone" in t or "symposium" in t or "presentation" in t or "poster" in t:
        return "project"
    if "review" in t or "marathon" in t or "catch-up" in t or "catch up" in t:
        return "review"
    if "launch" in t or "what is history" in t or "course launch" in t:
        return "launch"
    if assess_flag.strip().upper() == "Y":
        # Friday practice etc. that's graded -> treat as quiz-ish
        if "friday" in t or "practice" in t:
            return "quiz"
        return "quiz"
    return "content"

DAYTYPE_LABEL = {
    "content":"Content","quiz":"Quiz","test":"Test","crq":"CRQ","eie":"EIE",
    "mock":"Mock","project":"Project","review":"Review","exam":"Exam",
    "launch":"Launch","closeout":"Close-Out",
}

# ---- materials per prep+daytype ----
def ap_materials(title, dtype):
    if dtype == "quiz":
        return ["Weekly Quiz (Assessment_Bank)", "Answer key", "Scantron / response sheet"]
    if dtype == "test":
        return ["Unit Test: 50 MCQ + AAQ + EBQ", "Test answer key", "Scantron / blue book"]
    if dtype == "mock":
        return ["Full Mock AP Exam (timed)", "Scoring guide", "Bubble sheet + FRQ packet"]
    if dtype == "exam":
        return ["College Board AP Exam (no teacher materials — proctor only)"]
    if dtype == "project":
        return ["Project / Capstone packet", "Rubric", "Peer-review checklist"]
    if dtype == "review":
        return ["Review deck", "Practice MCQ set", "Misconception tracker"]
    # content / launch
    return ["Teacher_Slides.pptx", "Student_Handout (guided notes)", "Teacher_Key", "Vocab sheet"]

def g9r_materials(rec, dtype):
    if dtype == "test":
        return ["Unit Exam (Unit_NN_Exam.docx)", "Exam Key", "Scantron"]
    if dtype == "crq":
        return ["Unit CRQ packet (2 CRQs · 40 pts)", "CRQ Key + rubric"]
    if dtype == "eie":
        return ["EIE essay prompt + NYS rubric", "EIE Key / exemplar", "Lined paper"]
    if dtype == "mock":
        return ["Mock Regents (full)", "Scoring key", "Answer sheets"]
    if dtype == "project":
        return ["Year-End Project packet", "Rubric", "Presentation slot sheet"]
    if dtype == "review":
        return ["Review deck", "Past-Regents MCQ set", "CRQ practice"]
    if rec:
        return ["Teacher_Slides.pptx", "Student_Handout.docx (guided notes)",
                "Teacher_Key.docx", "Key Terms / vocab sheet"]
    return ["Teacher_Slides.pptx", "Student_Handout.docx", "Teacher_Key.docx"]

# ---- student_do / teacher_do ----
def student_do(prep, title, dtype):
    if dtype == "quiz":
        return "Take the weekly quiz, then self-correct using the review key."
    if dtype == "test":
        return "Complete the unit test independently; bring a pen and your review sheet."
    if dtype == "mock":
        return "Sit the full timed mock under exam conditions; pace yourself across sections."
    if dtype == "exam":
        return "Report on time with ID and pencils; this is the official exam."
    if dtype == "crq":
        return "Analyze the documents and write both constructed-response answers."
    if dtype == "eie":
        return "Plan, draft, and write the Enduring Issues essay to the NYS rubric."
    if dtype == "project":
        return "Work on your project deliverable and prep for presentation day."
    if dtype == "review":
        return "Drill weak spots, work practice items, and ask targeted questions."
    if dtype == "launch":
        return "Set up notebooks, review the syllabus, and complete the opening activity."
    if dtype == "closeout":
        return "Wrap up, reflect on the year, and submit any remaining work."
    return f"Complete the guided notes and exit ticket for: {title}."

def teacher_do(prep, title, dtype, enl=False):
    enl_tag = " Pull the ENL slice-first parallel and the EN-pinyin-中文-ES vocab sheet." if enl else ""
    if dtype == "quiz":
        return "Print the quiz + key; after, log misses into the weak-topics tracker." + enl_tag
    if dtype == "test":
        return "Print test + key and scantrons; proctor, then grade against the key." + enl_tag
    if dtype == "mock":
        return "Set up timed conditions; proctor the full mock and prep the scoring guide." + enl_tag
    if dtype == "exam":
        return "Confirm proctor logistics and room; no instruction — official exam day."
    if dtype == "crq":
        return "Print CRQ packet + rubric; model evidence use, then circulate." + enl_tag
    if dtype == "eie":
        return "Print the prompt + NYS rubric; time the essay and collect for grading." + enl_tag
    if dtype == "project":
        return "Have packets/rubrics ready; conference with groups and track progress." + enl_tag
    if dtype == "review":
        return "Open the review deck; target the misconceptions from the last assessment." + enl_tag
    if dtype == "launch":
        return "Print the launch handout; set classroom norms and run the hook." + enl_tag
    return f"Prep slides + handout + key for '{title}'; lead notes, then release to practice.{enl_tag}"

# ---- Google Classroom posts (hand-tuned templates by day-type) ----
def aim_of(title):
    t = re.sub(r"^(Unit\s+[\d.]+\s+|U\d+\s+L\d+:\s*)", "", title or "").strip()
    return t or title

def classroom_post(prep, title, dtype, unit_label):
    aim = aim_of(title)
    arcade = "Mr. Mac's Review Arcade course page"
    world = "the 3D Review World"
    if dtype == "content" or dtype == "launch":
        return (f"Today: {aim}. Goal: build the core ideas in your guided notes. "
                f"Handout is attached — finish your notes and exit ticket before you leave. "
                f"Bring questions to our review day.")
    if dtype == "quiz":
        return (f"Quiz today: {aim}. You need a pen and your notes from this week. "
                f"Warm up first on the {arcade} — same skills, no pressure.")
    if dtype == "test":
        return (f"{unit_label} test today. Bring a pen. This covers everything from the unit. "
                f"Review tools: {arcade} and {world}. You've got this.")
    if dtype == "crq":
        return (f"CRQ practice today: {aim}. We'll read the documents together, then you write. "
                f"Remember: cite the document, explain it, connect it to the question.")
    if dtype == "eie":
        if "final" in (title or "").lower():
            return (f"Enduring Issues Essay — the real one. Bring your planning sheet and a pen. "
                    f"Choose your issue, build your throughline, and write to the rubric. "
                    f"This counts. Final review tools are posted.")
        return (f"Enduring Issues today: {aim}. Plan first, then draft to the NYS rubric. "
                f"Use your evidence from across the units.")
    if dtype == "mock":
        return (f"Mock exam today: {aim}. Full timing, real conditions. "
                f"Treat it like the real thing — it shows you exactly what to fix before exam day.")
    if dtype == "exam":
        return (f"{aim}. Report on time with ID and #2 pencils. No phones. "
                f"You are ready — trust your prep.")
    if dtype == "project":
        return (f"Project work today: {aim}. Check the rubric, hit your milestone for the day, "
                f"and come ready to present when it's your turn.")
    if dtype == "review":
        return (f"Review day: {aim}. We target the spots that tripped people up last time. "
                f"Bring your missed questions. Practice live on the {arcade}.")
    if dtype == "closeout":
        return (f"Last one: {aim}. Bring anything outstanding, and let's close the year well. "
                f"Thank you for a great year.")
    return f"Today: {aim}. Handout attached."

def enl_note(title, dtype):
    base = ("ENL parallel runs in lockstep with 9R. Hand out the EN-pinyin-中文-ES vocab "
            "sheet up front; teach slice-first (one chunk at a time, model before release).")
    if dtype == "test":
        return base + " For the test: same content, scaffolded prompts + word bank + extended time."
    if dtype == "crq" or dtype == "eie":
        return base + " For writing: sentence frames + the multilingual glossary; grade content, not grammar."
    if dtype == "review":
        return base + " Review in the home-language glossary first, then English."
    return base + f" Today's anchor terms come from: {aim_of(title)}."

# ---- key date markers ----
KEY_EVENTS = {
    "2026-09-01": "First student day",
    "2027-05-03": "G9R Mock Final #1",
    "2027-05-18": "G9R Mock Final #2",
    "2027-06-03": "EIE FINAL (Enduring Issues Essay)",
    "2027-06-25": "Last day of school",
}

def main():
    load_g9r()
    rows = list(csv.DictReader(open(CSV)))
    days = []
    mismatches = []
    g9r_match_total = 0
    g9r_match_hit = 0
    for r in rows:
        if r["status"] != "instructional":
            continue
        d = r["date"]
        dow = r["day"]
        # AP Psych
        ap_title = (r["AP_Psych_x3"] or "").strip()
        ap_assess = r.get("AP_assessment","")
        ap_type = classify(ap_title, ap_assess, r.get("exam_window",""))
        # find AP unit label
        ap_unit = ""
        mu = re.match(r"Unit\s+(\d+)", ap_title)
        if mu:
            ap_unit = f"AP Psych U{mu.group(1)}"
        ap = {
            "title": ap_title or "—",
            "unit": ap_unit,
            "day_type": ap_type,
            "day_type_label": DAYTYPE_LABEL[ap_type],
            "materials": ap_materials(ap_title, ap_type),
            "student_do": student_do("ap", ap_title, ap_type),
            "teacher_do": teacher_do("ap", ap_title, ap_type),
            "classroom_post": classroom_post("ap", ap_title, ap_type, ap_unit or "Unit"),
            "links": {
                "arcade": "AP Psychology — Review Arcade",
                "world": "AP Psych 3D World (Brain / Memory)",
                "folder": f"{ROOT}/AP_Psychology_Synthesis_2026-27/",
            },
        }
        # Global 9R + ENL
        g_title = (r["Global_9_9R_and_ENL"] or "").strip()
        g_assess = r.get("G9_assessment","")
        g_type = classify(g_title, g_assess, r.get("exam_window",""))
        rec = G9R_LESSON_BY_DATE.get(d)
        g_unit_label = ""
        lesson_no = None
        folder_path = f"{G9R}/"
        topic = None
        if rec:
            g9r_match_total += 1
            g_unit_label = f"G9R U{rec['unit_num']:02d} — {rec['unit_name']}"
            lesson_no = rec["lesson_no"]
            folder_path = rec["path"]
            topic = rec["topic"]
            # validate title token overlap: does the calendar title share words with folder slug?
            cal = re.sub(r"^U\d+\s+L\d+:\s*", "", g_title).lower()
            slug = rec["slug"].lower()
            cal_words = set(re.findall(r"[a-z]{4,}", cal))
            slug_words = set(re.findall(r"[a-z]{4,}", slug))
            if cal_words and (cal_words & slug_words):
                g9r_match_hit += 1
            else:
                mismatches.append({"date": d, "calendar": g_title, "folder_slug": rec["slug"]})
        else:
            mu = re.match(r"U(\d+)", g_title)
            if mu:
                g_unit_label = f"G9R U{int(mu.group(1)):02d}"
        g9 = {
            "title": g_title or "—",
            "unit": g_unit_label,
            "lesson_no": lesson_no,
            "topic": topic,
            "day_type": g_type,
            "day_type_label": DAYTYPE_LABEL[g_type],
            "materials": g9r_materials(rec, g_type),
            "student_do": student_do("g9", g_title, g_type),
            "teacher_do": teacher_do("g9", g_title, g_type, enl=True),
            "classroom_post": classroom_post("g9", g_title, g_type, g_unit_label or "Unit"),
            "enl_note": enl_note(g_title, g_type),
            "links": {
                "arcade": "Global History — Review Arcade",
                "world": "Global 9 3D World (Silk Road / River Valleys)",
                "folder": folder_path,
            },
        }
        days.append({
            "date": d,
            "day_of_week": dow,
            "marking_period": r.get("marking_period",""),
            "key_event": KEY_EVENTS.get(d),
            "exam_window": r.get("exam_window",""),
            "ap_psych": ap,
            "global9": g9,
        })
    # ---------- VALIDATION GATE ----------
    print("="*60)
    print("DATA VALIDATION GATE")
    print("="*60)
    n = len(days)
    print(f"[1] instructional day count: {n}  (expect 178)  -> {'PASS' if n==178 else 'FAIL'}")

    # contiguity: no Sat/Sun, dates strictly increasing
    bad_weekend = [x['date'] for x in days if x['day_of_week'] in ('Saturday','Sunday')]
    print(f"[2] weekend days in set: {len(bad_weekend)} (expect 0) -> {'PASS' if not bad_weekend else 'FAIL'} {bad_weekend[:5]}")
    dts = [datetime.strptime(x['date'],'%Y-%m-%d').date() for x in days]
    increasing = all(dts[i] < dts[i+1] for i in range(len(dts)-1))
    print(f"[3] dates strictly increasing: {'PASS' if increasing else 'FAIL'}")

    # both prep columns filled every day
    empty_ap = [x['date'] for x in days if x['ap_psych']['title'] in ('','—')]
    empty_g9 = [x['date'] for x in days if x['global9']['title'] in ('','—')]
    print(f"[4] AP empty: {len(empty_ap)} | G9 empty: {len(empty_g9)} (expect 0/0) -> "
          f"{'PASS' if not empty_ap and not empty_g9 else 'FAIL'}")
    if empty_ap: print("    AP empty dates:", empty_ap)
    if empty_g9: print("    G9 empty dates:", empty_g9)

    # key dates land correctly
    present = {x['date'] for x in days}
    print("[5] key dates present:")
    for kd, lbl in KEY_EVENTS.items():
        ok = kd in present
        print(f"    {kd}  {lbl:38s} -> {'PASS' if ok else 'FAIL'}")
    # EIE final must be classified eie
    eie = next((x for x in days if x['date']=='2027-06-03'), None)
    eie_ok = eie and eie['global9']['day_type']=='eie'
    print(f"    2027-06-03 G9 classified as EIE -> {'PASS' if eie_ok else 'FAIL'} "
          f"({eie['global9']['day_type'] if eie else 'missing'})")

    # AP exam window check (~May 12 2027)
    apx = [x['date'] for x in days if x['ap_psych']['day_type']=='exam' or 'ap exam' in x['ap_psych']['title'].lower()]
    print(f"[6] AP-exam-type days: {apx[:3]}")

    # G9R title match rate
    rate = (g9r_match_hit/g9r_match_total*100) if g9r_match_total else 0
    print(f"[7] G9R title↔folder match: {g9r_match_hit}/{g9r_match_total} = {rate:.1f}% (gate >=95%) -> "
          f"{'PASS' if rate>=95 else 'WARN'}")
    if mismatches:
        print(f"    mismatch log ({len(mismatches)}):")
        for m in mismatches[:25]:
            print(f"      {m['date']}: cal='{m['calendar']}' vs folder='{m['folder_slug']}'")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meta = {
        "generated": datetime.now().isoformat(),
        "instructional_days": n,
        "first_day": days[0]['date'], "last_day": days[-1]['date'],
        "key_events": KEY_EVENTS,
        "g9r_match_rate": round(rate,1),
        "units_g9r": {str(k): v["name"] for k,v in sorted(G9R_UNITS.items())},
    }
    json.dump({"meta": meta, "days": days}, open(OUT,"w"), indent=1, ensure_ascii=False)
    print("="*60)
    print(f"WROTE {OUT}  ({os.path.getsize(OUT)//1024} KB, {n} days)")

if __name__ == "__main__":
    main()
