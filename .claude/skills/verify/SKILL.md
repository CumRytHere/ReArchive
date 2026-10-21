---
name: verify
description: Run the project's verification and show the generated report. Use whenever results are about to be reported. Usage /verify [fast|gate-A].
argument-hint: "[fast | gate-A]"
---

Run, depending on "$ARGUMENTS":
- empty → `python3 tools/verify.py`
- `fast` → `python3 tools/verify.py --fast`
- `gate-A` → `python3 tools/verify.py --gate A`

Then reply with the markdown report exactly as printed (do not retype or summarise numbers), followed by one line:
"Report <id>: <verdict>". If the verdict is FAIL, list the failing checks with the last line of each check's output.
Never describe results from an earlier report as current; if in doubt run
`python3 tools/verify.py --check-report reports/verify/latest.json`.
