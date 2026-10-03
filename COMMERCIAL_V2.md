# Commercial V2: bottled-beverage pilot

This is an opt-in engineering pilot, not a commercial-quality release.

The existing four-direction workflow remains compatible. V2 first asks the vision model for an evidence-qualified brand analysis and four advertising propositions without coordinates. An independent semantic-review call rejects collapsed or impossible ideas before layout, with at most two creative repairs. A separate Art Director call executes accepted IDs as layouts. V2 removes mandatory palette, serif/sans and above/below/beside quotas; those quotas measured layout variety rather than advertising concepts. Unique mechanism strings are only a structural check. Semantic review is still model judgment, and the final images need direct comparison.

## Run

Use the configured vision key in the environment; never place it in a command or tracked file.

The pilot defaults to project ComfyUI port 8191. Override with `--comfy-url` only for a service containing the configured background workflow's nodes. It does not restart existing services.

```powershell
python commercial_pilot.py plan --config config.local.json
python commercial_pilot.py render --config config.local.json --plan-dir "<printed absolute plan directory>" --direction 1
```

Planning writes `CreativeConcepts.json`, `BrandAnalysis.json`, four validated `Concepts.json` specs, references and the source identity hash under ignored `runs/commercial-pilot/`. It generates no poster. Render checks the saved product hash, runs the selected direction through ComfyUI scene generation, the V2 Pillow compositor and the vision Critic, and saves a per-version `CommercialGate.json`. Repeat directions 2–4 to inspect the whole campaign. `poster.py four --commercial-v2` also supports an explicitly configured bottled beverage/perfume category.

## Current physical integration

Original product RGB and alpha are preserved through aspect-preserving resize and translation. There are no generated replacements for labels, logos or silhouette. An integration plan declares observed source key-light direction, floor material and bounded cast-shadow parameters. A floor shadow is projected from the original alpha, in the opposite horizontal direction to an observed left/right key light, alongside the existing contact shadow and dense contact core. Graphic presentations do not get a floor cast shadow. Unknown illumination disables directional shadowing rather than guessing.

This is a 2D approximation. It does **not** estimate scene depth, material zones, real color temperature, camera perspective or glass transmission. It does **not** relight the original packshot, reconstruct reflections or guarantee plausible contact. The scene must accommodate the observed source photograph. Each shadow still needs visual review. A later physically informed integration renderer is required to remove these limitations.

Scene generation stays in ComfyUI. The opt-in V2 CPU compositor runs in the calling worker so a busy service with an older node cannot silently omit the new shadow layer. Installation copies `commercial.py` with the node on the next safe service deployment; running legacy jobs are not restarted.

## Commercial Gate

Product fidelity >=95; physical integration, typography, composition and creative coherence >=88; brand alignment >=85. Every explicit check must contain a true boolean and nonempty visual evidence: logo, shape, grounding, clean edges, consistent lighting, uncropped and noncolliding text, fonts, and brand spelling. Missing or uncertain evidence vetoes approval. Outstanding critique or changes and deterministic unsafe geometry also veto approval. A high average cannot override a failed item.

The Critic receives the observed brand evidence and is asked for root cause, affected layer and repair strategy. Actual execution remains the validated patch whitelist: scene prompts, layout, typography, contact shadows and bounded cast-shadow values. Source illumination is immutable. Unsupported material relighting is not treated as a completed repair.

Model checks are not independent physical measurements or human commercial certification. Existing legacy PASS records are not automatically V2 approvals. The proposed 20-run targets (16 physically correct, 12 social-ad ready, four campaign candidates) remain **unmeasured**; no stability rate is claimed here. Brand/scene fusion, semantic diversity, typography intentions and expert-review calibration require further real-image work.

After a numeric/check gate passes, a separate final Art Director sees the actual poster, original product and references without the first Critic's numerical scores. It classifies the work as `draft`, `social_ad` or `campaign_candidate`; unresolved problems veto acceptance. V2 defaults to target `campaign_candidate`; an explicit `commercial_target: social_ad` accepts either higher tier. Unavailable or malformed final review is a veto. A real test exposed a 90.6-score numeric PASS that this final reviewer classified as a generic `draft`; its original approval and corrective release decision are both preserved in the [pilot report](samples/commercial-v2/beverage-20261003/REPORT.md).

V2 allows guarded typography-family/layout corrections while preserving the advertising proposition; legacy strict serif/sans and title-position locks remain unchanged outside V2. This avoids protecting a poorly chosen prototype font from brand-alignment repairs.
