# Clothing subtype qualification

Actual ComfyUI ClothingDirectorLoop with Qwen planning, copy review, rendering and image critique. Each case requests four directions under the existing iteration budget. Creative/copy rejection can stop a case before rendering. Such failures remain visible and are not counted as successful posters.

Execution finished: False. Commercial quality certified: **false**.

| Case | State | Selected posters | Model passes |
|---|---|---:|---:|
| menswear-tshirt | RUNNING | 0 | 0 |
| menswear-shirt | QUEUED | 0 | 0 |
| menswear-knitwear | QUEUED | 0 | 0 |
| menswear-tailoring | QUEUED | 0 | 0 |
| menswear-outerwear | QUEUED | 0 | 0 |
| menswear-trousers | QUEUED | 0 | 0 |
| menswear-activewear | QUEUED | 0 | 0 |
| womenswear-tshirt | QUEUED | 0 | 0 |
| womenswear-shirt | QUEUED | 0 | 0 |
| womenswear-knitwear | QUEUED | 0 | 0 |
| womenswear-tailoring | QUEUED | 0 | 0 |
| womenswear-outerwear | QUEUED | 0 | 0 |
| womenswear-trousers | QUEUED | 0 | 0 |
| womenswear-dress | QUEUED | 0 | 0 |
| womenswear-skirt | QUEUED | 0 | 0 |
| womenswear-activewear | QUEUED | 0 | 0 |

[Actual selected images](gallery.html). [Input contact sheet](../../../assets/products/clothing/subtypes/inputs-contact.jpg).

This is one-fixture coverage, not multi-product stability. The merchandising audience is supplied by the test brief; it does not infer personal gender or certify manufacturer sizing. Garment-specific references fall back explicitly to same-audience references when fewer than three brands match. Reference scarcity can constrain creative quality.

Original RGB, labels, clothing construction and existing wearer photographs are preserved; no wearer is generated. The official Rifo women blazer uses a deterministic matte with unchanged original RGB. Source provenance and preprocessing are in the manifest. PNGimg/StickPNG examples are non-commercial testing fixtures; this run does not grant commercial source rights.

## Input limitations

menswear-tailoring: original supplied wearer photograph retained; jacket complete, source lower legs cropped; tests original_model only
womenswear-tailoring: deterministic matte requires visual edge inspection; no material reconstruction
womenswear-skirt: visible white matte fragments in source; preserved for input-quality regression, not clean production art
womenswear-activewear: source shorter edge below 500 px; enlarged details are not commercial quality evidence
