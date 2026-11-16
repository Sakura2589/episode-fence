# Validation record

Date: 2026-11-16. Status: 0.1.0 alpha.

## Executed locally

- Windows, bundled CPython 3.12 runtime.
- `python -m unittest discover -s tests -q`: **40 tests, 39 passed, 1 skipped**.
- The suite includes 300 deterministic randomized audits checked against an independent exhaustive pair oracle, and 100 randomized plans independently checked for residual overlap/group conflicts.
- Tests cover exact half-open and embargo boundaries, contained intervals, complete affected IDs despite evidence caps, source boundary clipping, deterministic plans, transitive group isolation, malformed input, source-length consistency and task-coverage diagnostics.
- Integration tests cover CLI exit codes, preserving source files, refusing existing outputs, demo reproducibility, JSONL/CSV/BOM input, HTML label escaping, and LeRobot v2 metadata import.
- Synthetic demo: **4 affected clips before, 0 after** planning using history=8, future=24. The same policy is used for verification.
- Built a wheel and source distribution. Installed the wheel with no dependencies into an isolated target directory, changed the working directory away from the source, then successfully generated the demo from the installed package. CSS and entry-point code were present.
- Scale smoke check: 100,000 synthetic clips across 1,000 sources, two alternating split labels, future=4; detected 100,000 affected clips with 200 stored witnesses in approximately **1.19 seconds** on this host. Includes fingerprint generation. This is one synthetic run, not a portable speed guarantee. Run `python scripts/benchmark.py` to reproduce the workload.

## Not verified

- The optional LeRobot v3.0 Parquet test was skipped because PyArrow was unavailable. Dependency installation was attempted but the environment's network/proxy access prevented download. v3 importer code is included; actual Parquet execution remains unverified locally.
- Linux, macOS, Python 3.10 and 3.13 were not executed locally. The supplied GitHub Actions workflow configures Linux/Windows 3.10/3.13 tests with PyArrow and wheel installation. No successful remote CI run is claimed.
- HTML generation and escaping passed tests. Visual/browser QA was not completed: the installed Playwright runtime had no browser binary, and the in-app browser rejected local `file:` URLs by policy. No screenshot or responsive-layout verification is claimed.
- No real robot dataset audit, trained policy, policy success rate, benchmark independence guarantee, or user adoption study was performed. The demo and scale workload are synthetic.
- Provenance accuracy, multi-camera alignment, loader read semantics, resampling correctness, and statistical independence are responsibilities of the integrating pipeline.

## Regression repairs made during development

Randomized tests caught an interval-coverage bug: the reverse sweep must be sorted by descending start, not end, to mark contained same-split intervals that share a later neighbour. A dedicated regression test was added. Planning tests caught generator consumption in disjoint-set initialization. A Windows integration test caught an implicit locale-dependent HTML read in the test itself; it now explicitly uses UTF-8.
