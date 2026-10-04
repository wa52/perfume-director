# Unified director workflow acceptance

All 23 complete ComfyUI director entry workflows now use `commercial-v2-aligned-20261003`. The job manager enforces dynamic four-concept planning, independently reviewed concept-specific copy, Commercial V2 checks, and final target `campaign_candidate` regardless of old saved configuration flags. Exact user-approved text remains locked. Existing iteration budgets and configured provider are preserved.

The [workflow catalog](workflows/QUALITY_ALIGNMENT.json) covers all 29 workflow JSON files. Six are rendering components (background, compositing, 2D harmonization or experimental relighting), not independent commercial director loops. They execute the requested layer; the parent director loop owns acceptance. No component is labelled commercially certified merely because it renders.

Shared minimum scores are Product Fidelity 95, Physical Integration 88, Typography 88, Composition 88, Brand Alignment 85 and Creative Coherence 88. All eleven evidence-based commercial checks are mandatory. A final independent commercial art review must meet the same campaign-candidate target without unresolved problems. Refused edits are never silently applied. These are identical acceptance rules, not a claim that every category has already produced equally good images.

Category-specific geometry and fidelity constraints remain necessary: horizontal shoes are not evaluated as tall bottles; flat-lay watches are not made upright; hanging clothing is not assigned an invented floor shadow. Menswear/womenswear garment subtypes share the same gate, but full visual qualification requires correct input products for each subtype.

UI defaults are aligned with the dynamic path. The perfume entry no longer requests one fixed warm-white style for all four proposals. Beverage uses the corrected official source, with provenance and source-resolution limitation retained. Clothing subtype workflows with no matching sample no longer load a T-shirt or dress as if it were a suit, trousers or activewear; upload a matching cutout before running those entries. Existing user-uploaded images are not overwritten by startup example setup.

## Verification

219 repository tests pass. Contract tests cover all category/subtype configurations and classify every workflow against its actual node graph. Job tests verify that the enforced profile reaches the worker and the saved job state. These checks validate policy routing, not commercial visual quality.

The initial perfume/watch qualification exposed a common copy retry failure: the writer was never told the numerical title/subtitle limits, and repeated subtitles over 96 characters. Limits and actual measured rejection lengths are now included in both generation and retry feedback, with rejection records retained. Language follows the user's brief unless explicitly requested otherwise. Creative generation/review now receive the same category/source constraints and actual renderer capabilities, excluding duplicate photographs, macro crop plates or arbitrary repeated typography that the renderer cannot execute.

The next batch rejected superficially different geometry around an isolated packshot. Investigation found that Design KB references were selected only after creative generation, so the Creative Director could not actually see them. References are now selected first, and three different-brand images plus their analyses are supplied to creative generation and independent diversity review. Only creative generation uses temperature 0.8; factual identity reading and independent reviews preserve their configured settings. Diversity vetoes remain mandatory and no four preset genres are imposed. All 29 workflows also passed a live registered-interface check; this is recorded separately from image qualification.

Fresh real-node qualification uses seven representative products, four automatic directions per category, with the configured five-round maximum per direction. Inputs: [alignment-products.json](assets/products/alignment-products.json). The skincare fixture is lipstick rather than a skincare pump/jar; the watch fixture does not validate jewellery; T-shirt and dress do not validate every clothing subtype. The corrected beverage source is only 180×650. Reference and source coverage limits must remain visible in the report.

Run or resume the same qualification without duplicate submissions:

```powershell
python run_category_matrix.py --comfy-url http://127.0.0.1:8191 --tag commercial-alignment-qualification-20261004 --manifest assets/products/alignment-products.json --categories perfume watches footwear beverage skincare menswear womenswear
```

The runner exports actual selected PNGs, previews, PosterSpec, Critic, Commercial Gate, independent art review and accepted commercial repair records when available. RUNNING/ERROR/NEEDS_REVIEW are retained. See [the current qualification gallery](samples/categories/commercial-alignment-qualification-20261004/gallery.html) and [the initial failed batch](samples/categories/commercial-alignment-20261003/gallery.html); a job finishing or shared code passing tests does not certify commercial image quality. The catalog intentionally keeps `commercial_visual_quality_verified:false` until separate commercial qualification supports changing it.

When independent concept review rejects diversity after three attempts, a schema-valid proposal may be rendered as a held draft for diagnosis. The rejection remains a collective veto: every resulting image is NEEDS_REVIEW regardless of score. Malformed proposals and unavailable reviews cannot use this path. Consumer-facing copy is now required; explanations of layout belong only in the rationale, and subtitles may be empty.

The earlier reference-aware watch batch completed four selections with zero commercial passes. It is preserved separately from the current seven-category qualification, which has now finished: six categories completed four selections each, menswear failed before rendering, and none of the 24 selections passed the commercial gate. All 29 saved workflows have passed real node-registration checks on the reloaded service. Source policy alignment is complete; commercial approval and subtype coverage remain separate acceptance criteria. The new 16-case clothing test is recorded independently.
