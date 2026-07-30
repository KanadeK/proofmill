# Research trail

Research snapshot: `2026-07-30`

## Selection criteria

The project was chosen only after checking that the surrounding portfolio did not already
contain a self-publishing or print-PDF preflight tool. Candidate ideas were filtered for:

- a repeated, concrete failure with observable input and output;
- useful behavior without cloud accounts or proprietary APIs;
- an honest implementation possible with synthetic test data;
- a gap between expensive production software and simple online calculators;
- a searchable problem statement that can attract contributors beyond software engineers.

ProofMill is a publishing-production tool rather than another source-code dashboard,
generic repository scanner, or UI-only local-first demo.

## Primary requirements evidence

Amazon's current guidance explicitly documents:

- exact trim, bleed, and page-count-dependent margin math;
- one-page cover wraps and paper/ink-specific spine formulas;
- minimum 300 DPI and recommended maximum 600 DPI;
- embedded fonts and the limitations of some font licenses;
- annotations, comments, bookmarks, transparency, layers, metadata, and crop marks as
  common failure surfaces;
- 0.75 point minimum line thickness and spine text restrictions.

Sources:

- [Paperback submission guidelines](https://kdp.amazon.com/en_US/help/topic/G201857950)
- [Trim size, bleed, and margins](https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6)
- [Paperback fonts](https://kdp.amazon.com/en_US/help/topic/G202145450)
- [Book image guidance](https://kdp.amazon.com/en_US/help/topic/G202169030)
- [Formatting issue repairs](https://kdp.amazon.com/en_US/help/topic/G201834260)

## Demand evidence

Community reports span years and remain current in 2026:

- [a June 2026 discussion](https://www.reddit.com/r/selfpublishing/comments/1u24u59/identifying_the_exact_math_behind_kdp_and/)
  describes authors losing time to cryptic layout rejections and asks for exact preflight
  math;
- [bleed and safe-area confusion](https://www.reddit.com/r/selfpublish/comments/le21or/kdp_set_to_bleed_but_keeps_showing_margins_any/)
  shows how bleed and live-text margins are easily conflated;
- [font embedding failures](https://www.reddit.com/r/selfpublish/comments/q9drcx/embedded_fonts/)
  show that a visually correct cover can still be rejected.

These discussions are treated as demand evidence, not as normative rules. Only primary
platform documentation defines the built-in thresholds.

## Competitor scan

Search results show active hosted tools such as:

- [KDPPreflight](https://kdppreflight.com/about)
- [Univers Studio's KDP checker](https://www.univers.studio/kdp-preflight/)
- [commercial print validation](https://www.manu2print.com/)

Their existence validates the workflow. ProofMill's differentiation is not a claim that no
other checker exists. It is:

- source-visible rules and parser code;
- a CLI suitable for local automation and CI;
- deterministic JSON evidence and release assets;
- no upload, account, analytics, or manuscript text in reports;
- committed positive and negative PDFs;
- a contribution contract for adding sourced checks.

## Rejected directions

- A hosted upload UI was rejected because it would add privacy and operations risk without
  improving the scanner.
- Automatic PDF repair was rejected for the first release because destructive transforms
  can silently alter fonts, image quality, transparency, and color.
- PDF/X and ICC certification were deferred because partial checks would imply stronger
  print guarantees than the implementation can support.
- Proprietary previewer emulation was rejected because it cannot be reproduced or tested
  openly.

