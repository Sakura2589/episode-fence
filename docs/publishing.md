# Release handoff

The local repository and distributions are ready for review. No remote repository or release has been created from this environment. Browser access to GitHub's repository creation page was blocked by an administrator-enforced origin policy, and the connected GitHub tools do not expose repository creation.

Proposed repository name: `episode-fence`

Description:

> Catch temporal leakage in robot learning splits. Exact source-frame evidence, action-window checks, and verified split manifests. No GPU or model API.

Suggested topics: `robotics`, `lerobot`, `imitation-learning`, `dataset`, `data-quality`, `data-leakage`, `machine-learning`, `python`.

Create an empty public repository in the intended account (without an extra README, license or gitignore), then connect and push this local repository. Use the actual URL returned by GitHub. Do not force-push over an existing repository.

Before announcing:

1. Let the supplied CI run, including optional PyArrow tests on Windows and Linux.
2. Open the before/after HTML reports at desktop and phone widths; local browser QA was blocked here.
3. Attach the wheel, source ZIP and SHA256SUMS.txt to a v0.1.0 alpha release.
4. Use the exact synthetic example and limitations from the README. Avoid claims about policy success, real-world adoption or guaranteed stars.
5. Seek a small number of real manifest examples and integration feedback before expanding scope. See research.zh-CN.md.

No community messages, promotional issues, or social posts have been sent.
