# Validation record

Updated: 2026-11-17. Status: 0.1.0 alpha.

## Executed locally

- Windows, bundled CPython 3.12 runtime.
- `python -m unittest discover -s tests -q`: **40 tests, 39 passed, 1 skipped**.
- The suite includes 300 deterministic randomized audits checked against an independent exhaustive pair oracle, and 100 randomized plans independently checked for residual overlap/group conflicts.
- Tests cover exact half-open and embargo boundaries, contained intervals, complete affected IDs despite evidence caps, source boundary clipping, deterministic plans, transitive group isolation, malformed input, source-length consistency and task-coverage diagnostics.
- Integration tests cover CLI exit codes, preserving source files, refusing existing outputs, demo reproducibility, JSONL/CSV/BOM input, HTML label escaping, and LeRobot v2 metadata import.
- Synthetic demo: **4 affected clips before, 0 after** planning using history=8, future=24. The same policy is used for verification.
- Built a wheel and source distribution. Installed the wheel with no dependencies into an isolated target directory, changed the working directory away from the source, then successfully generated the demo from the installed package. CSS and entry-point code were present.
- Scale smoke check: 100,000 synthetic clips across 1,000 sources, two alternating split labels, future=4; detected 100,000 affected clips with 200 stored witnesses in approximately **1.19 seconds** on this host. Includes fingerprint generation. This is one synthetic run, not a portable speed guarantee. Run `python scripts/benchmark.py` to reproduce the workload.

## Verified on GitHub Actions

The [initial CI run](https://github.com/Sakura2589/episode-fence/actions/runs/43999510393) passed all four jobs: Ubuntu and Windows with Python 3.10 and 3.13. Each job passed all 40 tests with no test skips, built the distributions, installed the wheel into an isolated environment outside the source checkout, and successfully generated the demo.

This includes the LeRobot v3.0 sharded Parquet metadata test with PyArrow, which could not run in the local environment. The test covers synthetic metadata import, episode lengths and task labels; it is not a real-world dataset validation claim.

The tested commit is `27ef97b53e4fc69cdd8a3c0da0dcdb2ddf5075f3`. The subsequent documentation-only commit updates this record; implementation, tests, and workflow are unchanged. The run includes a downloadable distribution artifact.

## Not verified

- Local execution of the LeRobot v3.0 Parquet test remains unverified because PyArrow was unavailable there. Its hosted Windows/Linux execution is verified above.
- macOS was not tested. Windows/Linux with Python 3.10 and 3.13 were verified on GitHub Actions as described above.
- HTML generation and escaping passed tests. Visual/browser QA was not completed: the installed Playwright runtime had no browser binary, and the in-app browser rejected local `file:` URLs by policy. No screenshot or responsive-layout verification is claimed.
- No real robot dataset audit, trained policy, policy success rate, benchmark independence guarantee, or user adoption study was performed. The demo and scale workload are synthetic.
- Provenance accuracy, multi-camera alignment, loader read semantics, resampling correctness, and statistical independence are responsibilities of the integrating pipeline.

## Regression repairs made during development

Randomized tests caught an interval-coverage bug: the reverse sweep must be sorted by descending start, not end, to mark contained same-split intervals that share a later neighbour. A dedicated regression test was added. Planning tests caught generator consumption in disjoint-set initialization. A Windows integration test caught an implicit locale-dependent HTML read in the test itself; it now explicitly uses UTF-8.
