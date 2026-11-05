# AI Agent Reliability Engineering: companion laboratory and Forms Workbook

Companion toolkit **version 1.0.0** (GitHub tag `v1.0.0`) for *AI Agent Reliability Engineering: Theory and Practices* by Dr. Sri Amit Ray (First edition, 2026; published by Compassionate AI Lab; ISBN 978-81-69641-40-1).

- Book and companion page: https://sriamitray.com/books/ai-agent-reliability/
- Source code: https://github.com/compassionate-ai-lab/ai-agent-reliability

The core laboratory runs offline with Python 3.11 or later and its standard SQLite module. No API keys, accounts, paid calls or network access are needed. All records and cases are synthetic.

## Run it

From this `companion` directory:

```bash
python -m unittest -v test_reliability test_models
python run_experiments.py
python calculations.py
python scorecard.py
python architecture_experiment.py
python capstones.py
```

Expected results:
- 80 passing unit tests (36 core tests in `test_reliability.py`, 44 for `models.py` in `test_models.py`);
- fixture counts minimal 4/10 and guarded 9/10;
- an illustrative scorecard blocked by a critical event;
- the coding baseline fails, and the candidate is accepted;
- research claims with accepted, failed and unresolved labels.

Results are written to `results/`. The reference outputs of this release are in `expected_results/`.

The deterministic fixture counts describe this finite teaching suite; they are not estimates of a live model's reliability. The confidence-card counts are illustrative inputs, separate from the fixture campaign. The seeded propagation experiment measures a supplied synthetic Bernoulli generator, whose graph and structural zeros are known by construction.

## Files

| File | Purpose |
|---|---|
| `flexiagent.py` | Atomic local authority checks, optimistic record versions, durable operation fingerprints and receipts, uncertain-commit reconciliation, checkpoint checksums, local active-memory correction and isolation |
| `models.py` | The models behind every worked example and chart. Regions marked `# [book:name]` are printed verbatim as the book's numbered listings |
| `metrics.py` | Standard-library binomial-tail inversion for exact one-sided fixed-sample bounds |
| `scorecard.py` | Confidence budget across registered constituent groups; unknown groups kept; critical-stratum floors |
| `calculations.py`, `architecture_experiment.py`, `capstones.py`, `run_experiments.py` | The analytical, propagation, transfer and fixture examples |
| `test_reliability.py`, `test_models.py` | The unit tests |
| `Reliability_Lab.ipynb` | Optional notebook that imports the same modules |
| `templates/` | Reusable mission contract, release record and incident record |
| `AI_Agent_Reliability_Engineering_Forms_Workbook_v1.0.0.docx` | Editable Forms Workbook (see its own copyright statement) |
| `MANIFEST.sha256` | SHA-256 of every file in this package |
| `VERSION`, `RELEASE_NOTES.md`, `LICENSE` | Release record and licence |

## Spectral radius (corrected in 1.0.0)

`models.radius_bracket` returns a guaranteed enclosure `lower <= rho(A) <= upper` for a nonnegative matrix:
- it splits reducible matrices into strongly connected blocks;
- it uses Collatz-Wielandt ratios on each block shifted to A + I;
- it stops at a stated tolerance and iteration limit.

`decay_verdict` reports `decays` only when the upper enclosure is below one, and `inconclusive` otherwise. `radius_upper` returns the upper enclosure of the matrix of simultaneous exact upper bounds. In that matrix, `None` is a declared structural zero, and `models.UNKNOWN` marks an unmeasured edge, which is bounded by 1. `calculations.radius` uses the same single implementation.

## Dependencies

The core needs only the Python standard library. One cross-check test uses NumPy when it is installed and is skipped otherwise. The book's figures were produced with NumPy, SciPy, Matplotlib and Pillow; readers do not need them to run the laboratory.

## Licence

The original companion software is released under the MIT License (see `LICENSE`), copyright 2026 Dr. Sri Amit Ray. The book and the Forms Workbook are not covered by the MIT License; they remain © 2026 Dr. Sri Amit Ray, all rights reserved, except as stated in the workbook.

## Cite

Ray, Sri Amit. *AI Agent Reliability Engineering: Theory and Practices*. First edition, Compassionate AI Lab, 2026. ISBN 978-81-69641-40-1.
