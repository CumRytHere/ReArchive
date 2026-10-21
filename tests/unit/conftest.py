"""Hypothesis configuration for the property tests.

The property tests here are *supplemental*: the conformance evidence comes from
the RFC 8785 vectors and the frozen D-015 byte vectors, not from the properties
(a round-trip property cannot establish canonicality -- many non-canonical
encodings round-trip equally well).

Given that, reproducibility is worth more here than exploration. D-013 has CI
compare canonical bytes across three environments, and a randomly-seeded
property test can fail on one leg and pass on the others, which would make a
cross-environment byte difference indistinguishable from a Hypothesis flake.
`derandomize` fixes the seed so a failure means the same thing everywhere.

The trade-off is real and deliberate: this suite no longer explores new inputs
across runs. Raised as a question for the human in docs/STATUS.md.
"""

from __future__ import annotations

from hypothesis import HealthCheck, settings

settings.register_profile(
    "rearchive",
    derandomize=True,
    max_examples=200,
    deadline=None,  # CI runners vary in speed; a timing deadline is not a property
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("rearchive")
