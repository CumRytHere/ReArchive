---
name: decide
description: Draft a decision proposal when work hits a design question no ratified decision answers, then stop. Usage /decide <short topic>.
argument-hint: "<topic, e.g. 'segment boundary encoding'>"
---

A design gap has appeared: "$ARGUMENTS". Do not implement an answer. Draft one for the owner.

1. Check it really is a gap: grep docs/DECISIONS.md and docs/PROJECT_SPEC.md for the topic. If a ratified decision
   answers it, quote it and continue the increment instead.
2. Write `docs/proposals/<next free D-number>-<slug>.md` with this structure:
   - Status: PROPOSED (date). Gap found while working on increment <n>; what is blocked.
   - Question, in one sentence.
   - Options (2–3). For each: what it means concretely, what it costs now, what it costs later, which tests and
     acceptance tests it affects, whether it changes any hash (hash-affecting = higher bar).
   - Recommendation and the deciding reason.
   - Ready-to-paste decision text, following DECISIONS.md conventions: heading `## D-NNN Title (changes §X)`
     naming a PROJECT_SPEC section, never another decision; relationships to earlier decisions stated in the body.
   - A `decision-constants due=<increment>` block for every value the code must match (D-028).
3. Add an open question to docs/STATUS.md: `- **Q-NN** (blocks <increment>): <question> → docs/proposals/<file>`.
4. Stop and tell the owner what is blocked and what can continue without the decision.
Never write the proposal's content into code, tests, vectors or golden files before the owner ratifies it (D-028 §3).
