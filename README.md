# Mr. Mac's Mission Control — 2026-27

A private-ish, 3D, interactive teacher-prep dashboard for the 2026-27 school year.
Day-by-day, per-prep: what you and your students should be doing, what to print/open,
and a ready-to-paste Google Classroom post — across all three preps:

- **AP Psychology ×3 sections**
- **Global History 9R**
- **Global 9 ENL** — a **separate, slower, vocabulary-first course** on Jon's real model
  (its own 8-unit sequence, MODS tests, and signature projects; **not** in lockstep with 9R)

## Open it

Go to the Pages URL for this repo — the dashboard loads directly (no gate).
`index.html` and `dashboard.html` are the same dashboard, so old bookmarks to
either page keep working.

## What's inside

- **The Year Road** — a three.js scene: a winding low-poly road through the school year,
  with landmarks for each Global 9R unit and the big events (mocks, EIE final, AP exam,
  last day). Click a landmark or drag the scrubber to jump the date.
- **Day panel** — **three prep cards** (AP Psych · Global 9R · Global 9 ENL, the ENL card
  with its own amber accent): title, unit/lesson, day-type chip, materials checklist
  (copy file names), Students / You lines, the Google Classroom post in a copy box
  (ENL posts written in simple English with the day's key vocab named), and quick links.
- **Today** button, prev/next arrows, week strip (Mon–Fri, colored by day-type),
  month mini-calendar, search, and a **Print week** view (clean print CSS).
- **Prep-status checkboxes** (printed / posted / graded) per day, saved in localStorage.

## Privacy — read this honestly

GitHub's free tier cannot serve Pages from a *private* repo, so this is a **public** repo
with an **unguessable name** plus:

- an **unlisted URL** — the repo name is random and the site is never linked publicly,
- `<meta name="robots" content="noindex,nofollow">` on every page and a `robots.txt`
  that disallows all crawlers,
- **zero student data** anywhere — there is none in the source data, and it stays that way.
  Only "Maccarello" appears.

**This is obscurity, NOT encryption.** Anyone who has this exact URL can read the
dashboard. The unlisted URL plus noindex keeps it out of search engines — that's the
whole security model. Don't put anything sensitive (especially student data) in here.

## Data

`data/days.json` — one entry per instructional day (178 total), built from:

- the Unified Daily Calendar 2026-27 **v2** (the 178-day spine, three prep columns),
- Global 9R V2 lesson folders / Build_Manifest topics,
- the **real ENL course calendar** (`Global_9_ENL_V2/00_Project_Charter/CALENDAR_2026-27_ENL.csv`),
- the AP Psychology day-by-day pacing + assessment cadence.

Regenerate with `build_data.py` (reads the curriculum workspace on disk). The build runs a
validation gate: exactly 178 instructional days, no weekends, all three prep columns filled
every day, all key dates present, a Global 9R title↔folder match check, and ENL split proofs
(e.g. Sep 3 2026 must show ENL = Geography & Vocabulary while 9R runs its own lesson).

Built with Claude Code.
