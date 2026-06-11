#!/usr/bin/env python3
"""Build data/days.json (one entry per instructional day) for Mr. Mac's Mission Control.

Source of truth: Unified_Daily_Calendar_2026-27_v2.csv (178 instructional days,
three preps: AP Psych x3 / Global 9R / Global 9 ENL) + the ENL course's own
calendar (Global_9_ENL_V2/00_Project_Charter/CALENDAR_2026-27_ENL.csv).

NOTE (2026-06-11): Global 9 ENL is a SEPARATE, slower, vocabulary-first course
on Jon's real 25-26 model — NOT in lockstep with 9R. Each day now carries a
real `enl` object (own unit/lesson/day-type/posts), replacing the old
"[ENL: scaffolded]" note on the shared 9R lesson.
"""
import csv, json, os, re, glob, sys
from datetime import datetime, date

ROOT = "/Volumes/CURRICULA/Curriculum_Agent_Workspace_2026_2027/06_Generated_Curricula"
CSV = f"{ROOT}/_Maccarello_Year_Plan_2026-27/Unified_Daily_Calendar_2026-27_v2.csv"
G9R = f"{ROOT}/Global_9R_V2"
ENL_CSV = f"{ROOT}/Global_9_ENL_V2/00_Project_Charter/CALENDAR_2026-27_ENL.csv"
ENL_DIR = f"{ROOT}/Global_9_ENL_V2"
OUT = os.path.join(os.path.dirname(__file__), "data", "days.json")

# ---- G9R unit folders -> friendly names + lesson folders indexed by date ----
G9R_UNITS = {}          # unit_num -> {name, slug_folder}
G9R_LESSON_BY_DATE = {} # 'YYYY-MM-DD' -> {folder, slug, unit_num, unit_name, topic}
ENL_BY_DATE = {}        # 'YYYY-MM-DD' -> real ENL day object (filled in main)

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
    "vocab":"Vocab","buffer":"Buffer",   # ENL-specific day types
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

# =====================================================================
# Global 9 ENL — the REAL course (separate, slower, vocabulary-first).
# Source: Global_9_ENL_V2/00_Project_Charter/CALENDAR_2026-27_ENL.csv
# =====================================================================
ENL_UNIT_TAG = {
    "Intro": "ENL Intro",
    "U1 Geography": "ENL U1 — Geography & Vocabulary",
    "U2 Paleo-Neo": "ENL U2 — Paleo-Neo",
    "U3 River Valley Civilizations": "ENL U3 — River Valley Civilizations",
    "EI thread": "ENL — Enduring Issues thread",
    "U4 Classical": "ENL U4 — Classical (Greece · Rome · Han)",
    "U5 Post-Classical": "ENL U5 — Post-Classical",
    "U6 Renaissance": "ENL U6 — Renaissance",
    "U7 Age of Exploration": "ENL U7 — Age of Exploration",
    "U8 Final / EI / Time Travel": "ENL U8 — Final / Time Travel",
}
ENL_UNIT_FOLDER = {
    "Intro": "00_Intro", "U1 Geography": "01_Geography", "U2 Paleo-Neo": "02_Paleo_Neo",
    "U3 River Valley Civilizations": "03_RVC", "EI thread": "EI_Thread",
    "U4 Classical": "04_Classical", "U5 Post-Classical": "05_Post_Classical",
    "U6 Renaissance": "06_Renaissance", "U7 Age of Exploration": "07_Exploration",
    "U8 Final / EI / Time Travel": "08_Final",
}
ENL_PROJECT_WORDS = ("instagram", "poster", "newspaper", "crime scene", "artist",
                     "aztec dictionary", "time travel", "adventure awaits",
                     "hero or villain", "presentations", "project")

def enl_classify(slot, fil):
    t = (slot or "").lower()
    f = (fil or "").lower()
    if f.startswith("gap (buffer") or t.startswith("buffer"):
        return "buffer"
    if "final exam" in t:
        return "exam"
    if any(w in t for w in ENL_PROJECT_WORDS):
        return "project"
    if "test" in t or "exam" in t or "assessment" in t:
        return "test"
    if "quiz" in t:
        return "quiz"
    if "crq" in t:
        return "crq"
    if "enduring issue" in t or t.startswith("ei ") or "ei final" in t or "ei document" in t or "identifying an enduring" in t:
        return "eie"
    if "review" in t or "catch-up" in t:
        return "review"
    if "vocab" in t:
        return "vocab"
    if "course launch" in t:
        return "launch"
    return "content"

def enl_vocab_hint(slot):
    """Pull the key words named in the lesson slot, e.g. '(desert/mountain/ocean/island)'."""
    m = re.search(r"\(([^)]+)\)", slot or "")
    if m:
        inner = m.group(1)
        if not re.search(r"^\s*(MODS|mods|work day|intro)", inner):
            words = re.split(r"[/,+·]| and ", inner)
            words = [w.strip() for w in words if w.strip() and len(w.strip()) > 2][:4]
            if words:
                return ", ".join(words)
    return None

def enl_materials(fil, dtype):
    if dtype == "buffer":
        return ["No new materials — recycle vocab do-nows, review sheets, _Vocab_Supplements glossaries"]
    files = [p.strip() for p in re.split(r"\s\+\s", fil or "") if p.strip()]
    files = [re.sub(r"^GAP \(new:\s*", "", x).rstrip(")") for x in files]
    mats = files if files else ["See unit _UNIT_PLAN.md for the day's file"]
    mats.append("[Template] student copy — push/print one per class")
    return mats

def enl_student_do(slot, dtype):
    if dtype == "vocab":
        return ("Define each word with the Britannica dictionary, translate it into YOUR "
                "first language, then write sentences using the new words.")
    if dtype == "test":
        return "Take the unit test. Read each question slowly. Use the word bank when given."
    if dtype == "quiz":
        return "Take the short quiz. You practiced these words — trust your review sheet."
    if dtype == "exam":
        return "Final exam: 20 multiple choice + the Enduring Issues essay. Use your sentence starters."
    if dtype == "review":
        return "Finish the fill-in-the-blank review sheet with the word bank, then study it."
    if dtype == "project":
        return f"Work on the project: {slot}. Follow the directions step by step (Step 1, Step 2, Step 3)."
    if dtype == "eie":
        return "Practice Enduring Issues: find the issue in the documents and use the sentence starters to write."
    if dtype == "crq":
        return "Read the documents, then answer the CRQ questions. Restate the question in your answer."
    if dtype == "buffer":
        return "Catch-up day: finish old work, practice vocabulary, extra reading time."
    if dtype == "launch":
        return "Meet the class, review the course outline, and complete the about-you activity."
    return f"Complete today's reading/notes and the Step 1 / Step 2 / Step 3 tasks: {slot}."

def enl_teacher_do(slot, dtype):
    if dtype == "vocab":
        return ("Print the vocab table (Vocabulary | Translate | Definition); model one entry; "
                "students translate into their own L1. Optional multilingual glossary in _Vocab_Supplements.")
    if dtype in ("test", "quiz"):
        return "Print test + key. Read directions aloud slowly; allow the review sheet where your policy says so."
    if dtype == "exam":
        return "Print the ENL Final (20 MC + EI documents). Proctor; grade content, not grammar, on the essay."
    if dtype == "review":
        return "Print the review sheet (+ key). Fill in the first blanks together, then release."
    if dtype == "project":
        return f"Print/post project directions; model an exemplar; conference table-by-table. ({slot})"
    if dtype == "eie":
        return "Teach from the EI scaffold: what makes an issue 'enduring', then guided document work."
    if dtype == "crq":
        return "Model restate-the-question, then guided CRQ writing with sentence frames."
    if dtype == "buffer":
        return "No new prep. Recycle vocab do-nows / review sheets; re-teach what the last exit work showed."
    return "Prep the deck + Student Copy blank (or the glossed reading). Pre-teach 2-3 hard words, then Step tasks."

def enl_classroom_post(slot, dtype, vocab_hint):
    vocab = f" Key words today: {vocab_hint}." if vocab_hint else ""
    if dtype == "vocab":
        return (f"New vocabulary today: {slot}.{vocab} Use the Britannica dictionary. "
                "Write the meaning in English AND translate each word into YOUR language. "
                "Then write your sentences. Ask for help in any language.")
    if dtype == "test":
        return (f"Test today: {slot}. Bring a pencil. Read every question slowly. "
                "You studied the review sheet — you are ready.")
    if dtype == "quiz":
        return (f"Short quiz today: {slot}. It is just like the review sheet. Take your time.")
    if dtype == "exam":
        return ("Final exam today: 20 questions + the Enduring Issues essay. "
                "Use your sentence starters. Take your time. You worked hard all year — you are ready.")
    if dtype == "review":
        return (f"Review day: {slot}.{vocab} Finish the fill-in-the-blank sheet. "
                "Use the word bank. Study it tonight.")
    if dtype == "project":
        return (f"Project time: {slot}. Read the directions step by step. "
                "It is OK to ask questions — in English or your language. Be creative!")
    if dtype == "eie":
        return ("Enduring Issues today. An enduring issue = a big problem that lasts a long time "
                "and affects many people. Look at the documents, find the issue, and use the "
                "sentence starters to write about it.")
    if dtype == "crq":
        return (f"Writing practice today: {slot}. Read the documents. Restate the question, "
                "then answer with evidence. Use your sentence starters.")
    if dtype == "buffer":
        return ("Catch-up day. Finish any old work. Practice your vocabulary words. "
                "Extra reading time. Ask me for help with anything.")
    if dtype == "launch":
        return ("Welcome to Global History 9! Today we meet each other and learn how the class works. "
                "You can use your home language to help you learn — that is a strength.")
    return (f"Today we learn: {slot}.{vocab} Read slowly, use the word list, and do "
            "Step 1, Step 2, Step 3. Ask for help in any language.")

def load_enl():
    """date -> real ENL day object."""
    out = {}
    for r in csv.DictReader(open(ENL_CSV)):
        unit = r["ENL_unit"].strip()
        slot = r["ENL_lesson_slot"].strip()
        fil = r["ENL_file_or_GAP"].strip()
        dtype = enl_classify(slot, fil)
        vocab = enl_vocab_hint(slot)
        folder = ENL_UNIT_FOLDER.get(unit, "")
        out[r["date"]] = {
            "title": slot,
            "unit": ENL_UNIT_TAG.get(unit, unit),
            "file_label": fil if not fil.startswith("GAP (buffer") else "buffer day — recycle materials",
            "day_type": dtype,
            "day_type_label": DAYTYPE_LABEL[dtype],
            "materials": enl_materials(fil, dtype),
            "student_do": enl_student_do(slot, dtype),
            "teacher_do": enl_teacher_do(slot, dtype),
            "classroom_post": enl_classroom_post(slot, dtype, vocab),
            "links": {
                "arcade": "Global History — Review Arcade (+ EN/pinyin/中文/ES glossary panel)",
                "world": "Global 9 3D World (Silk Road / River Valleys)",
                "folder": f"{ENL_DIR}/{folder}/" if folder else f"{ENL_DIR}/",
            },
        }
    return out

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
    global ENL_BY_DATE
    ENL_BY_DATE = load_enl()
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
        # Global 9R (its own prep — ENL is separate, below)
        g_title = (r["Global_9R"] or "").strip()
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
            "teacher_do": teacher_do("g9", g_title, g_type),
            "classroom_post": classroom_post("g9", g_title, g_type, g_unit_label or "Unit"),
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
            "enl": ENL_BY_DATE.get(d),
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

    # ENL coverage: every instructional day has a real ENL object; split-proof days
    enl_missing = [x['date'] for x in days if not x.get('enl')]
    print(f"[8] ENL real-course coverage: {n-len(enl_missing)}/{n} (expect {n}/{n}) -> "
          f"{'PASS' if not enl_missing else 'FAIL'} {enl_missing[:5]}")
    sep3 = next((x for x in days if x['date']=='2026-09-03'), None)
    if sep3:
        s_ok = ('Geography' in sep3['enl']['unit'] and sep3['enl']['title'] != sep3['global9']['title'])
        print(f"    Sep 3 split proof: ENL='{sep3['enl']['title'][:50]}' vs 9R='{sep3['global9']['title'][:40]}' -> "
              f"{'PASS' if s_ok else 'FAIL'}")
    jun22 = next((x for x in days if x['date']=='2027-06-22'), None)
    if jun22:
        tt_ok = 'Time Travel' in jun22['enl']['title']
        print(f"    Jun 22 ENL Time Travel presentations -> {'PASS' if tt_ok else 'FAIL'} ('{jun22['enl']['title']}')")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meta = {
        "generated": datetime.now().isoformat(),
        "instructional_days": n,
        "first_day": days[0]['date'], "last_day": days[-1]['date'],
        "key_events": KEY_EVENTS,
        "g9r_match_rate": round(rate,1),
        "units_g9r": {str(k): v["name"] for k,v in sorted(G9R_UNITS.items())},
        "enl_model": ("separate vocabulary-first course (Jon's real 25-26 model) — "
                      "NOT lockstep with 9R; source Global_9_ENL_V2/CALENDAR_2026-27_ENL.csv"),
        "units_enl": list(ENL_UNIT_TAG.values()),
    }
    json.dump({"meta": meta, "days": days}, open(OUT,"w"), indent=1, ensure_ascii=False)
    print("="*60)
    print(f"WROTE {OUT}  ({os.path.getsize(OUT)//1024} KB, {n} days)")

if __name__ == "__main__":
    main()
