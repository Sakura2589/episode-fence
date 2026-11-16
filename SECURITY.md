# Security and data handling

EpisodeFence reads local metadata and writes local reports. It does not execute dataset code, download models, fetch URLs, or upload data.

Treat datasets and Parquet dependencies as untrusted input. Manifests are size bounded; the optional PyArrow importer is not a sandbox for malicious binary files. Use current supported dependencies and only import files appropriate for your environment.

Reports include manifest identifiers and labels without redaction. Review before sharing. HTML escapes user-provided labels and uses no JavaScript or external resources.

For security-sensitive reports, use GitHub's private vulnerability reporting if enabled. Otherwise contact the repository owner privately before posting sensitive details. Do not publish credentials or private dataset contents in public issues.
