# Contributing

A useful first contribution is a small, sanitized manifest demonstrating a real split mistake or a false positive. Include the loader's actual history/future offsets, padding behavior and source identity rules.

Run `python -m unittest discover -s tests -v`. Install optional PyArrow to include v3.0 import tests. Core functionality must continue to work with the standard library.

For algorithm changes, extend the independent all-pairs oracle or randomized tests. Preserve half-open interval semantics and complete affected-clip detection. Do not silently reinterpret unknown format versions.

Good first improvements:
- documented export recipes for real data preparation pipelines;
- visual accessibility and keyboard checks for reports;
- task-stratified planning with explicit infeasibility handling;
- an adapter for timestamp-based manifests with stated units.

Open a focused issue or pull request with reproduction steps, expected behavior, and relevant test results. Never include private recordings, credentials, or identifying session labels.
