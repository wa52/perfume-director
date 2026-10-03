# Material and relighting pilot — actual local trials

Two Mage-Flow-Edit-Turbo int8 executions completed on the local RTX 5060 Laptop 8GB using project ComfyUI port 8191, 576×768, four Euler/simple steps, CFG 1, CPU text encoder. Both trials were reviewed by the configured Qwen vision API with actual before/edit/protected images and original product. The second review also included the source-texture illumination variant.

See [the visual comparison](gallery.html), [trial 1 review](trial-1/VisualReview.json) and [trial 2 review](trial-2/VisualReview.json). Trial 1's illumination-transfer variant was computed afterward and was **not** included in its original review.

## Findings

| Variant | Result | Remaining problem |
|---|---|---|
| Raw instruction edit | Rejected in both trials | Labels and liquid/headspace drift; inconsistent shadows despite explicit preservation prompts |
| Exact label/cap/boundary restoration | Rejected in both trials | Label pixels identical to the resized source composite, but seams and edge-light mismatch remain |
| Source-texture smooth illumination transfer | Second reviewer accepted as appearance prototype only | Faint wall-shadow ghost, original reflection response, weak grounding; brightness can change label pixels |

The raw model demonstrably changes glass appearance and illumination. It does not preserve product identity reliably. Exact restoration achieves zero RGB error over 14,045 protected pixels but does not achieve coherent material response. The conservative transfer copies no generated product RGB and retains original lettering/detail while multiplying by a bounded smooth illumination field. It preserves more identity but cannot synthesize accurate new reflections or glass transmission. Its background estimate excludes the foreground before blur to avoid turning glass highlights into a background halo.

No commercial PASS, physical material accuracy, stability rate or production integration is claimed. `PROTOTYPE_ONLY` means the reviewer accepted at least one protected appearance experiment; the actual review still contains unresolved problems. The commercial workflow's gate remains unchanged and this branch does not replace its renderer automatically.

Manual bottle-specific cap/label bands are recorded in `IdentityZones.json`. They must be reviewed and replaced for a different product. The immutable source product hash and masks are recorded per trial. The source background and PosterSpec are included so the experiment does not depend on ignored run directories.

The API graph was actually executed. The separate UI graph is provided for import but its frontend import has not yet been manually verified. Direct UI execution produces **raw, unapproved output only**; protection and review are performed by `relight_pilot.py`.

Validation: all 179 repository unit tests passed, including exact protected pixels, geometry mismatch rejection, bounded background transfer, source-lettering retention and prevention of foreground-highlight leakage. These tests verify implementation invariants, not aesthetic quality. No 20-run repeatability claim is made.

Model reference: [Microsoft Mage-Flow documentation](https://github.com/microsoft/Mage/blob/main/mage_flow/README.md). The implementation is instruction-based appearance editing plus 2D transfer, not PBR or inverse material reconstruction.
