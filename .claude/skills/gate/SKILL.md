---
name: gate
description: Run the human-owned acceptance gate and summarise which tests pass and fail. Read-only; never edits files.
disable-model-invocation: true
---

1. Run `uv run pytest -q -m acceptance -rA` and keep the full output.
2. Produce a table: test name · pass/fail · one-line reason for each failure (quote the assertion message).
3. Group failures by the increment in docs/STATUS.md that should fix them.
4. Do not edit, create or delete any file. Do not suggest changing tests in tests/acceptance/; if one looks wrong, say why and leave the decision to the human.
