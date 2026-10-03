# 2D product integration — opt-in, source-preserving branch

This branch improves controlled photographic product composites. It does not claim best possible 2D quality, measured physical material reconstruction, commercial approval or multi-category stability. The first evaluated case is the existing Coca-Cola bottle and clean linen scene.

## Run

```powershell
python optimize_2d.py --contour-contact --refine-alpha --spill-zones samples/harmonization/beverage-2d-20261003/SpillZones.json --review
```

Run from the repository with the configured vision key in the environment. `--review` uses the configured paid vision API; omit it to produce `UNREVIEWED` outputs. The command creates a unique ignored `runs/harmonization/<id>/` directory. It saves the original compositor, three candidates, original-resolution posters, enlarged details, metrics and actual review. Explicit `--output` refuses to replace an existing directory. `--review-only --output <existing-directory>` reviews existing images and checks the product identity hash; previous review is retained.

The default `ground_top=0.72` belongs to this packaged bottle/scene experiment, not arbitrary backgrounds. The source key-light direction comes from the PosterSpec. New products need their own transparent source, spec, background and reviewed identity/material regions. Generate a fresh matching baseline/guide with `relight_pilot.py` first. The 2D compositor verifies that the lossless guide baseline matches the actual source, background and spec; a different product's guide or a stale placement is rejected. Current CLI defaults deliberately reuse the prior real ComfyUI trial instead of claiming new model executions.

## What changed

- Preserve original product texture and draw campaign typography separately at 1080×1440 output resolution. Guide images supply a bounded smooth illumination field; their product RGB, labels and scene geometry are not copied.
- Composite RGBA in linear light. Clean partially transparent edge RGB with nearby opaque foreground colors without changing alpha by default.
- Rebuild ground-plane shadow and contact core from the actual source silhouette. The core follows the lowest support contour instead of a single ellipse; raised gaps do not manufacture contact. Cast direction follows the observed source light, with bounded length restricted to the declared ground plane.
- Optional manual warm-spill cleanup is confined to reviewed contour regions; it is not an automatic material detector or a global brand recolor.
- Optional 0.55px alpha refinement smooths the boundary and records changed alpha pixels. It can shrink boundary alpha and therefore is **not** exact silhouette identity. Original core RGB and alpha are retained by this operation.
- Optional bounded environment color wrap affects only reviewed contour strips. Optional additive neutral reflection guidance excludes protected regions and is capped; it can still create implausible material appearance. Protected regions must include cap, lettering, liquid/foam structure and other identity-critical material details. The reflection trial did not win the final preference and is not enabled automatically.
- Transparent source images sent to the Director/Critic are now flattened on a neutral matte before JPEG encoding, rather than exposing hidden original-background RGB.

## ComfyUI

The new `Product2DHarmonize` node returns actual `poster` and `scene` IMAGE outputs plus `audit_json`. Connect IMAGE outputs to SaveImage. An audit string is not the finished image. It requires a declared photographic ground plane in `parameters_json`; source-only operation needs no guide. Optional guide inputs require manually reviewed `identity_zones`. The packaged selected parameters belong only to this bottle/scene.

Import `workflows/harmonization-2d.ui.json` after a safe installation through `start_comfy.ps1`; the API equivalent is `workflows/harmonization-2d.api.json`. Select/upload these four files in LoadImage:

1. `assets/products/categories/beverage.png`
2. `samples/relighting/beverage-20261003/source-background.png`
3. `samples/relighting/beverage-20261003/trial-2/before.png`
4. `samples/relighting/beverage-20261003/trial-2/raw-material-edit.png`

Installation copies `harmonization.py` alongside the node. This work did not restart busy ComfyUI services, replace the default four-direction loop, or verify frontend import in the running server. The actual node class was executed with real ComfyUI-format tensors: both IMAGE outputs match the selected CLI PNGs with **zero RGB error**. Batch/mask/NaN rejection is tested. All node outputs remain `UNREVIEWED`; the regular commercial gate is not bypassed.

## Evidence

See [six controlled rounds](samples/harmonization/beverage-2d-20261003/gallery.html) and [report](samples/harmonization/beverage-2d-20261003/REPORT.md). Six rounds contain 18 processed candidates from the same source and previously executed model guide, not 18 independent generations or a measured stability rate. Independent integration review preferred v4/B; earlier review still reported a minor neck halo, so the aggregate release stays `NEEDS_REVIEW` and commercial release is false. A good integration score does not evaluate brand concept or typography.
