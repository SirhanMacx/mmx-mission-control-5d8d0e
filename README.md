# Mr. Mac's Mission Control — 2026-27

A private-ish, 3D, interactive teacher-prep dashboard for the 2026-27 school year.
Day-by-day, per-prep: what you and your students should be doing, what to print/open,
and a ready-to-paste Google Classroom post — across all three preps:

- **AP Psychology ×3 sections**
- **Global History 9R**
- **Global 9 ENL** (runs in lockstep with 9R; ENL parallels noted per day)

## Open it

1. Go to the Pages URL for this repo.
2. Enter the passcode: **`macs-mission-2027`**
3. You're in for the browser session (sessionStorage).

## What's inside

- **The Year Road** — a three.js scene: a winding low-poly road through the school year,
  with landmarks for each Global 9R unit and the big events (mocks, EIE final, AP exam,
  last day). Click a landmark or drag the scrubber to jump the date.
- **Day panel** — two prep cards side by side: title, unit/lesson, day-type chip,
  materials checklist (copy file names), Students / You lines, the Google Classroom post
  in a copy box, the ENL parallel, and quick links.
- **Today** button, prev/next arrows, week strip (Mon–Fri, colored by day-type),
  month mini-calendar, search, and a **Print week** view (clean print CSS).
- **Prep-status checkboxes** (printed / posted / graded) per day, saved in localStorage.

## Privacy — read this honestly

GitHub's free tier cannot serve Pages from a *private* repo, so this is a **public** repo
with an **unguessable name** plus:

- a **passcode gate** (SHA-256 of the passcode is compared in JS; only the hash is in the
  code, never the plaintext),
- `<meta name="robots" content="noindex,nofollow">` on every page and a `robots.txt`
  that disallows all crawlers,
- **zero student data** anywhere — there is none in the source data, and it stays that way.
  Only "Maccarello" appears.

**This is obscurity + a passcode, NOT encryption.** Anyone who has both this exact URL and
the passcode can read the dashboard. The hash gate stops casual snooping and the noindex
keeps it out of search engines — that's the whole security model. Don't put anything
sensitive (especially student data) in here.

## Data

`data/days.json` — one entry per instructional day (178 total), built from:

- the Unified Daily Calendar 2026-27 (the 178-day spine),
- Global 9R V2 lesson folders / Build_Manifest topics,
- the AP Psychology day-by-day pacing + assessment cadence.

Regenerate with `build_data.py` (reads the curriculum workspace on disk). The build runs a
validation gate: exactly 178 instructional days, no weekends, both prep columns filled every
day, all key dates present, and a Global 9R title↔folder match check.

Built with Claude Code.
