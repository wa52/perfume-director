# Real automatic campaign regression

Product: official Coca-Cola Austria source; provenance is retained in ../../harmonization/beverage-clean-20261003/SourceProvenance.json.
Qwen generated and independently reviewed four creative propositions and four distinct copies. Art Director chose coordinates and scene plans. Local ComfyUI generated scenes. Critic reviewed source, final image and three selected references, proposing bounded repairs. No human words, coordinates or pixel edits were supplied.

Four-direction execution used at most two rounds. It predates the new product_silhouette executor. An optional separately identified regression uses the upgraded executor and at most three rounds. These are capability regressions, not a 20-run stability or commercial acceptance test.

| Direction | Status | Selected score | Versions |
|---|---|---:|---|
| concept-1 | NEEDS_REVIEW | 76.3 | 73.3 → 76.3 |
| concept-2 | NEEDS_REVIEW | 85.4 | 83.3 → 85.4 |
| concept-3 | NEEDS_REVIEW | 82.3 | 78.6 → 82.3 |
| concept-4 | NEEDS_REVIEW | 90.0 | 90.0 |
| silhouette-regression | NEEDS_REVIEW | 78.9 | 77.4 → 74.6 → 78.9 |
| final-review-regression | NEEDS_REVIEW | 85.9 | 80.0 → 82.6 → 85.9 |
| final-veto-resume | NEEDS_REVIEW | 81.7 | 81.7 → 83.4 |

All gate failures are retained in summary.json and each CommercialGate.json. No image is certified for commercial release. Source is only 180×650; preserving its pixels does not create high-resolution professional source photography. Private API call traces and endpoint configuration are excluded.

Open gallery.html for complete V1/V2 comparisons, PosterSpec and Critic evidence.

## Final veto repair replay

`final-veto-repair/PreviousCommercialArtDirector.json` is the actual independent rejection of the original concept-4. The first automatic repair tried to change locked logo.text; the second conflicted with graphic-mode shadow constraints. Both proposals were atomically rejected. Their recorded validation errors were sent back to the model; its third proposal passed validation. `CommercialRepair.json` contains the accepted edits, never an approval. The program applied them, rendered again and reviewed two versions. Direct visual selection retained V1 despite V2's higher numeric score; neither passed. This saved-veto replay verifies the new feedback path rather than a fresh end-to-end four-direction stability run.

The separate fresh `final-review-regression` did not reach a Commercial Art Director approval; do not present it as evidence of commercial acceptance. All seven recorded executions remain NEEDS_REVIEW.
