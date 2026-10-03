# Commercial V2 beverage pilot — 2026-10-03

This evidence records real Qwen planning, not a finished advertisement or a successful commercial run.

- The initial two-stage plan returned four mostly neutral packshot compositions. It passed structural layout checks but was rejected as creative repetition. `InitialConcepts-rejected.json` preserves that failure.
- The new independent semantic reviewer rejected two successive batches: floor-treatment variants first, then two equivalent decorative-backdrop graphics. `CreativeReview-1.json` and `CreativeReview-2.json` contain its actual evidence and required revisions.
- The third revision received a model semantic approval (`CreativeReview-3.json`, `CreativeGate.json`). Proposed mechanisms: enlarged contour projection, script-derived rings, a hospitality tabletop relationship, and a ground-plane contour trace. Semantic approval is not a renderer feasibility approval: wall projection and raised/table surfaces remain unsupported by the current physical compositor. Do not claim these concepts have been implemented merely because a model approved the prose.
- A preliminary render submission against legacy port 8190 failed HTTP 400: four required background node types were absent. The pilot now defaults to project service 8191 and checks configured node types before submission. No poster from this failed render exists.
- Art Director/layout validation of the revised concepts is in progress. No finished V2 render or commercial approval is recorded in this report yet.

Current tests: 170 passed, including original-product preservation in the external-shadow routine, direction of frontal-light projection, unknown-source-light rejection, immutable source-light patches, missing-evidence vetoes, geometric vetoes and semantic repair before layout. Tests do not establish aesthetic quality.

The V2 gate uses fidelity >=95, physical integration/typography/composition/creative coherence >=88 and brand alignment >=85, plus explicit evidence for all veto checks. Original RGB and alpha are retained; cast/contact shadows are 2D approximations. There is no true material-zone relighting, glass-transmission reconstruction, depth estimation or reconstructed reflection.

The 20-run acceptance target remains untested. Legacy gallery images and existing legacy PASS results are not V2 approvals.
