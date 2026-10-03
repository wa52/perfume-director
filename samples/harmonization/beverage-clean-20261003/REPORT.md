# Replacement source / actual 2D rerun

The earlier beverage source was rejected for visible original-background remnants. Historical outputs remain intact and have a correction notice.

Replacement: [Coca-Cola Austria official product page](https://www.coca-cola.com/at/de/brands/coca-cola). Full asset URL and hashes in SourceProvenance.json. Original JPEG 750x750, cropped product 180x650. Border-connected near-white pixels only were masked; source RGB was retained. No invented brand/product pixels. Source remains limited by baked white-background glass transmission, pale fine edges and resolution. This is a test asset, not an approved delivery packshot.

Actual fresh ComfyUI Mage trial: 4304f1fc3381, seed 2026100307. The raw edit altered printed lettering; it is a lighting guide only, never the output product. Then three real 1080x1440 CPU composites used the new source: A gain strength 0, B .35, C .65. No old bottle spill zones or neck wrap regions were reused. Ground boundary .72; new bottle remains at native 650px height with the same product base y=1152. Old/new comparison is the same scene, height constraint and base; these are different packshots, not pixel-identical products.

Qwen preferred A: fidelity 97, edges 86, light 93, grounding 90. All versions NEEDS_REVIEW. Remaining pale base fringe and uneven contact shadow prevent acceptance. Do not claim independent repeated stability or commercial approval. Typography is retained demo typography, not reviewed campaign design.

Open gallery.html for source checks, old/new controlled comparison and fresh three-candidate review. Exact selected settings in SelectedParameters.json, audit in Metrics.json. All image hashes in ImageManifest.json. No private API traces exported.

Optional Comfy import: workflow.ui.json requires the Product2DHarmonize node installed and loaded, as documented in HARMONIZATION_2D.md. Pick product.png, source-background.png, guide-before.png and guide-raw-material-edit.png from this directory. The node implementation was tested earlier; this new UI graph has not been manually executed inside the running browser. Actual above trial ran through relight_pilot.py and optimize_2d.py. No service restart was performed.
