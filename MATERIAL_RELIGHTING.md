# Experimental material / lighting branch

This branch tests material appearance editing with real ComfyUI execution. It is opt-in and does not replace the commercial renderer or mark a poster commercial-ready.

## Run the packaged bottle experiment

Use the project's Python environment with Pillow and NumPy. ComfyUI must expose `TextEncodeMageFlowEdit` and these installed models:

- `diffusion_models/mage_flow_edit_turbo_int8_convrot.safetensors`
- `text_encoders/qwen3vl_4b_bf16.safetensors`
- `vae/mage_flow_vae_bf16.safetensors`

```powershell
python relight_pilot.py --config config.local.json --comfy-url http://127.0.0.1:8191
python relight_pilot.py --config config.local.json --comfy-url http://127.0.0.1:8191 --seed 20261004 --review
```

`--review` sends the actual experiment images to the configured vision provider and can incur API costs. Set the configured API key in the environment; never put it in tracked files. Without review the result stays `UNREVIEWED`; failed review stays `REVIEW_FAILED`; rejected review stays `REJECTED`. Even an accepted appearance experiment only becomes `PROTOTYPE_ONLY`, never commercial PASS.

Outputs appear under the printed absolute `runs/relighting/<id>/` directory: original composite, product/identity/editable masks, raw edit, exact-label restored edit, source-texture lighting transfer, source hash, actual API graph, metrics and optional visual review. Typography is deliberately excluded so the model cannot redraw campaign text.

`--spec`, `--background`, `--product`, `--zones` select another controlled experiment. `--prompt` overrides the editing instruction. Product coordinates come from the validated PosterSpec. The default zones belong to this bottle only: **replace them for another product**. Zones are normalized to the cropped product, not canvas coordinates; empty/invalid protection and unobservable background illumination are rejected.

## ComfyUI graph

`workflows/material-relight-mage.api.json` is the executed graph. `workflows/material-relight-mage.ui.json` is the frontend import counterpart (manual frontend import validation remains pending). Load a composite photograph in LoadImage before running. The graph saves raw AI output only; it does not run Python protection or the commercial gate. Use the CLI for the complete protected experiment and optional review.

The CPU text encoder and 576×768 output were tested locally on 8GB VRAM. Other workloads and machines can still change memory availability and runtime.

## Actual evidence and limits

See [two trials and actual Qwen reviews](samples/relighting/beverage-20261003/REPORT.md) and [gallery](samples/relighting/beverage-20261003/gallery.html).

Exact pixel restoration protects original labels but can create lighting seams. Smooth illumination transfer retains original source texture while allowing brightness changes; it does not preserve exact label RGB. Neither method reconstructs measured normals, material zones, refraction, light temperature or physically accurate specular response. Remaining wall-shadow/grounding issues must be resolved and repeated trials must be reviewed before automatically enabling this branch in the commercial loop.
