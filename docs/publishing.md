# Release checklist

Repository: [Sakura2589/episode-fence](https://github.com/Sakura2589/episode-fence).

The source is maintained on `main`. Publishing source does not automatically create a tagged release or publish a package to PyPI.

Description:

> Catch temporal leakage in robot learning splits. Exact source-frame evidence, action-window checks, and verified split manifests. No GPU or model API.

Suggested topics: `robotics`, `lerobot`, `imitation-learning`, `dataset`, `data-quality`, `data-leakage`, `machine-learning`, `python`.

Review the changes and push commits to the repository through the normal Git workflow. Do not force-push over shared history.

Before announcing:

1. Let the supplied CI run, including optional PyArrow tests on Windows and Linux.
2. Open the before/after HTML reports at desktop and phone widths; local browser QA was blocked here.
3. Attach the wheel, source ZIP and SHA256SUMS.txt to a v0.1.0 alpha release.
4. Use the exact synthetic example and limitations from the README. Avoid claims about policy success, real-world adoption or guaranteed stars.
5. Seek a small number of real manifest examples and integration feedback before expanding scope. See research.zh-CN.md.

No community messages, promotional issues, or social posts have been sent.
