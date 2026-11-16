# Use an audit in CI

Keep the manifest and policy under review. Run the same read-window policy used by the data loader.

```yaml
- run: python -m pip install .
- name: Audit split boundaries
  run: python -m episode_fence audit dataset/clips.jsonl --history 8 --future 24 --embargo 4 --format markdown -o split-review.md
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: split-review
    path: split-review.md
```

Exit codes: **0** no declared conflicts, **1** conflicts, **2** invalid input or an I/O error. A single split can return 0 with a warning; it does not establish a held-out evaluation. The report is written before a conflict exit.

Do not allow arbitrary manifest or policy replacement to stand in for independent review. A report only covers supplied source IDs, coordinates and policy.

The project's CI tests the tool itself. Synthetic conflict fixtures intentionally return 1; test code asserts that value.
