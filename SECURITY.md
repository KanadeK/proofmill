# Security policy

## Supported versions

Security fixes are applied to the latest tagged release.

## Report a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not attach an
unpublished manuscript, password, font file, or proprietary PDF to a public issue.

Include:

- ProofMill version and operating system;
- the smallest synthetic PDF that reproduces the issue;
- whether the issue affects parsing, report privacy, path handling, or package integrity;
- the expected and actual behavior.

## Data handling

ProofMill makes no network requests and does not execute PDF JavaScript, attachments, or
embedded content. Reports omit manuscript text by default. A PDF parser is still a complex
attack surface: inspect untrusted PDFs in a disposable account or container, keep
dependencies updated, and never run the CLI with elevated privileges.

Release assets include `SHA256SUMS`; verify the downloaded wheel before installation.

