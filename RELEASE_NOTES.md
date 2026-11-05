# Release notes: companion toolkit v1.0.0

Book: *AI Agent Reliability Engineering: Theory and Practices*, Dr. Sri Amit Ray, First edition, 2026. Published by Compassionate AI Lab. ISBN 978-81-69641-40-1.

Release: version 1.0.0, GitHub tag `v1.0.0`. This is the release printed in the book. A later corrected release will carry a new version number, and this one stays available unchanged.

## Source identity
- Built from the V7 development package (`AI_Agent_Reliability_Engineering_V7_Companion.zip`, 70 tests) plus the final correction pass of 5 November 2026 (book production V8).
- The modules in this archive are the ones printed as the book's numbered listings, regions `# [book:name]`.

## Corrected in 1.0.0
- **Spectral radius (Chapter 16, Listing 16.1).** Before 1.0.0, the routine returned the last normalisation factor after 4,000 power steps. That is an estimate, not a bound. It returned about 0.9995 for a matrix whose radius is exactly 1, and `radius_upper` returned about 0.99937 for a bound matrix with radius 1, which wrongly suggested decay. The new routine works as follows:
  - `models.radius_bracket` gives a guaranteed enclosure. It splits reducible matrices into strongly connected blocks and runs Collatz-Wielandt ratios on A + I. It has a stated tolerance and iteration limit, and an allowance for rounding.
  - `decay_verdict` returns `decays`, `grows` or `inconclusive`. `spectral_radius` is the midpoint estimate.
  - `radius_upper` now returns the upper enclosure. `upper_matrix` keeps unmeasured edges as `UNKNOWN`, bounded by 1. Only declared structural zeros (`None`) are 0.
  - Inputs are validated: the matrix must be square, nonempty, finite and nonnegative, and edge counts must be valid.
  - `calculations.radius` and `architecture_experiment.py` now use the same single implementation. The propagation campaign also records a verdict.
- Teaching values are unchanged: 0.5302, 1.0604, 0.5223 (estimate), 0.5909 (upper enclosure), 1.1225 (cycle).

## Tests and outputs
- 78 unit tests: 36 in `test_reliability.py` and 42 in `test_models.py`. All pass.
- New radius tests cover:
  - the two review counterexamples;
  - zero and diagonal matrices, asymmetric cycles, reducible and nearly critical matrices;
  - unknown edges and invalid inputs;
  - a cross-check against NumPy's eigenvalue solver, skipped when NumPy is absent.
- All five documented scripts run, and the 3 notebook code cells execute. The reference outputs are in `companion/expected_results/`.

## Inventory
- `companion/`: the code, tests, notebook, README, `templates/` and `expected_results/`.
- `AI_Agent_Reliability_Engineering_Forms_Workbook_v1.0.0.docx`: the editable Forms Workbook (mission contract, sampling and confidence plan, reliability card, release decision record, incident and remediation record).
- `LICENSE`: MIT, for the companion software only.
- `VERSION`, `RELEASE_NOTES.md`, `README.md`, and `MANIFEST.sha256` (per-file digests).

## Dependencies
Python 3.11 or later with the standard library and `sqlite3`. NumPy is optional; it is used by one cross-check test only.

## Checksum
The SHA-256 of the ZIP file is published outside the archive: in `AI_Agent_Reliability_Engineering_Companion_v1.0.0.zip.sha256`, in Appendix A of the book, and on the companion page https://sriamitray.com/books/ai-agent-reliability/.
