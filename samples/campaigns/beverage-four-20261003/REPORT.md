# Four complete beverage poster studies

Guided creative experiment: Codex art-directed four advertising ideas, ComfyUI generated the scenes, deterministic typography/product compositing produced final PNGs, and Qwen performed three real whole-poster reviews against the original product and three Design KB references. This is not an independent autonomous commercial acceptance run.

Four final PNGs are 810x1080: ice / diner / motion / sculpture. The same official cropped 180x650 source product is kept at native resolution, original labels retained; no raw generated bottle is used. Source provenance is in ../../harmonization/beverage-clean-20261003/SourceProvenance.json. White-baked glass transmission and small packshot resolution remain limitations.

Actual execution: 7 Z-Image scene generations (4 initial, ice and motion replacements, 1 diner replacement), plus 1 Mage background-only edit to remove foreground cup/menu. Source product was excluded from that edit. A blurred distant condiment remains. Three paid Qwen reviews were actually completed. No independent stability statistics claimed.

Final Qwen preference: motion, accepted as a creative study under all six score thresholds and no reported problems. Ice/diner/sculpture remain NEEDS_REVIEW for grounding, stray prop/readability or spatial coherence. Overall commercial_release_allowed remains false. Model scores are subjective assessments, not proof of commercial craft. Raw review JSON and earlier review records are retained.

Manual visual refinements: reject the initial ice scene's oversized drinking glass; reject generated nonsense lettering and white framing in the first motion scene; adjust diner typography contrast to the actual background; increase photo contact strength; align sculpture subtitle; move diner product 50px deeper into the counter and edit its scene. Some fixes did not resolve the underlying photographed integration gap.

Verification.json records actual PNG size, font glyph support, text bounds and no text/product collisions. ImageManifest.json hashes all public PNGs. Private API request traces are excluded. Running Comfy services were not restarted.

Reproduce a NEW initial directed experiment with existing private configuration and running ComfyUI 8191:

```powershell
& '<your-comfy-python>' campaign_four.py --output runs/campaign-four/<new-directory>
& '<your-comfy-python>' campaign_four.py --output runs/campaign-four/<new-directory> --review-only
```

The initial script deliberately supplies guided concepts. Saved final PosterSpecs and RenderParameters include subsequent manual art-direction decisions. Use saved background PNGs to reproduce final selected composites; do not claim a stochastic re-generation reproduces them exactly. This script is separate from the existing dynamic Director workflow.
