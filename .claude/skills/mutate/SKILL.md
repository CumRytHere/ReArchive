---
name: mutate
description: Mutation-test one product module against chosen tests and propose the missing tests. Usage /mutate <src file> [test paths...].
argument-hint: "<src/rearchive/...py> [tests/unit/test_x.py ...]"
disable-model-invocation: true
---

1. Parse "$ARGUMENTS": the first word is the module; the rest are test paths. If no test paths are given, find the
   test files that import the module (Grep) and use those.
2. `python3 tools/mutate.py --list <module>` to see the sites; if more than 200, narrow with `--function`.
3. `python3 tools/mutate.py <module> --tests <tests> --json reports/mutate/<module-stem>.json`.
4. For each survivor: classify gap / equivalent / unreachable (see the test-skeptic agent), and for gaps write the
   test you propose — inputs and exact assertion — in the reply. Do not add the tests unless the owner says so.
5. Confirm `git status --porcelain -- src/` shows nothing left behind.
