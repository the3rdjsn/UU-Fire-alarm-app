═══════════════════════════════════════════════════════════════════
  UOFU FIRE ALARM MANAGEMENT SYSTEM
  University of Utah — Facilities Management
═══════════════════════════════════════════════════════════════════

QUICK START
───────────
Mac/Linux:
  1. Open Terminal in this folder
  2. Run:  bash run.sh
  3. Browser opens at http://localhost:8501

Windows:
  1. Double-click run.bat
  2. Browser opens at http://localhost:8501

FIRST RUN ONLY — needs internet to install packages (takes ~30 sec)
After that it runs fully offline.

REQUIREMENTS
────────────
Python 3.9 or newer — download at python.org if needed.
The run script installs everything else automatically.

DATA FILES NEEDED (place in same folder as app.py)
───────────────────────────────────────────────────
The app reads from these JSON files on first run to seed the database.
If fire_alarm.db already exists, these are not needed.

  buildings_clean.json  — 164 buildings
  schedule_clean.json   — 151 inspection entries
  device_rows.json      — 31,740 FocalPoint device points

These are located in /tmp/ on the build machine. Copy them here
if running on a new machine.

DATABASE
────────
All data is stored in fire_alarm.db (SQLite) in this folder.
Back it up to keep your inspection history. That's the only file
you need to preserve between updates.

PAGES
─────
Dashboard        — Live stats, monthly progress chart, upcoming inspections
Schedule         — Full 2026 calendar, update status with dropdown, saves instantly
Buildings        — All 164 buildings, searchable/filterable, full detail view
New Inspection   — Auto-populates from building DB, save reports to history
Inspection History — All saved reports, expandable, deleteable
Device Inventory — 31,740 FocalPoint points, searchable/filterable

PDF EXPORT
──────────
On the New Inspection page, after filling out the form use
File → Print (Ctrl+P / Cmd+P) → Save as PDF in your browser.
The page is formatted cleanly for letter-size printing.

UPDATING STATUS (fixes the overdue issue from before)
──────────────────────────────────────────────────────
On the Schedule page, expand any row, change the Status dropdown
to "Complete" and click Save. The dashboard updates immediately.
Overdue is calculated live against today's date — once you mark
something Complete it will never show as overdue again.
