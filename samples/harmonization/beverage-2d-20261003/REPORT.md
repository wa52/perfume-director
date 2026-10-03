# Six actual 2D optimization rounds — beverage pilot

Same original transparent bottle, 1080×1440 PosterSpec, clean source background and original typography in every round. The illumination guide is the actual previous Mage-Flow ComfyUI output from material-edit trial 2. No new model generation is claimed for these rounds.

| Round | Controlled change | Preference | Release |
|---|---|---|---|
| 1 | Source RGBA, linear-light composition, edge RGB repair, bounded smooth guide | B | NEEDS_REVIEW: base corners |
| 2 | Actual bottom-contour contact core | B | NEEDS_REVIEW: source-edge remnant; incomplete first review retained |
| 3 | Manual warm-spill edge cleanup | B | NEEDS_REVIEW |
| 4 | Optional measured 0.55px alpha-boundary refinement | B | NEEDS_REVIEW: minor neck halo |
| 5 | Manual neck light wrap and slightly stronger contact | B | NEEDS_REVIEW |
| 6 | Protect foam/liquid/base as well as cap/label; compare 0/0.12/0.24 additive reflection guidance | B | NEEDS_REVIEW |

Rounds 1–5 compare guide strength A=0, B=0.35, C=0.65. Round 6 keeps diffuse strength 0.35 and compares reflection strength A=0, B=0.12, C=0.24. These are compositor variants, not four advertising concepts. All per-round reviews and their disagreements are preserved.

An independent review, without previous scores/preferences, compared X=v4/B, Y=v6/B and Z=baseline. Its first response contained empty problem objects for rejected candidates, so it was rejected and retained as `IndependentReview-attempt-1.json`. The complete replacement preferred X and gave X fidelity 97, physical integration 91, edges 90, with no blocking integration problems. Y also met that review's integration thresholds but did not win the preference. [Actual independent response](IndependentReview.json), [validated integration gate](IndependentGate.json).

`selected-scene.png` and `selected-poster.png` are actual v4/B outputs. The latter restores the unchanged original demo typography, which has **not** been commercially approved. No commercial PASS: earlier per-round review still reports a minor neck halo. [Selection records](Selection.json) preserve aggregate `NEEDS_REVIEW` rather than discarding disagreement to claim success.

Some visual-model root-cause claims conflict with deterministic evidence: the implementation does not rotate the product, apply an extra source resample, or omit candidate shadows. Its source contour is unchanged by default; round 4 onward explicitly records optional alpha repair. Scores for identical baselines also vary. Therefore model scoring is comparative evidence, not a calibrated physical measurement; unsupported root causes are not executed as automatic repairs.

Original full-resolution PNGs remain in local ignored runs. This folder includes selected full PNGs, enlarged detail panels, comparison JPEGs and per-candidate JPEG previews. `ImageManifest.json` separately records original PNG and exported JPEG hashes. Private API endpoint/configuration/request traces were not exported.

The actual ComfyUI `Product2DHarmonize` class was invoked with original source/background/guide tensors and the saved recipe. Both scene and poster match selected CLI outputs byte-for-byte in RGB: [verification](NodeVerification.json). Frontend/server import remains unverified; busy services were not restarted. The node never grants commercial PASS.

Tests cover linear compositing, edge/color cleanup, source lettering retention, bounded guide/reflection fields, contour contacts without raised-gap shadows, optional alpha refinement, light-wrap limits, malformed/empty-evidence review rejection, actual node IMAGE outputs and batch/NaN rejection. These are implementation checks, not claims that all categories or repeated random runs are commercially stable.

Final validation: all 193 repository tests passed, including stale/mismatched guide rejection and transparent-image preprocessing before vision calls.
