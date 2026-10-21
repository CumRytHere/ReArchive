"""ReArchive benchmark — generator, hidden truth, oracle and scoring.

This package is deliberately separate from :mod:`rearchive` (D-012). It must
never import the product, so that truth values can never be computed with the
same code that is under test.
"""

__version__ = "0.1.0"
