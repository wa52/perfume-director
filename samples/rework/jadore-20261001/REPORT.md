# J’adore redesign: human guided, real ComfyUI + live Critic

The previous GUI 75→86 PASS was judged weak by the user. This revision replaces the busy dark setting with a warm ivory studio, enlarges the visible bottle to 850/1440 pixels, uses measured serif typography, and refines contact shadow and centering.

The independent Director returned an invalid spec (empty price size 0, missing decoration layer), recorded in Director-call-rejected.json; it was not rendered. Codex supplied the valid V1 spec. Both posters were rendered through the real local ComfyUI; V2 reuses the V1 generated background. V2 centering and shadow changes were human guided, not autonomous Critic patches.

The first Critic connection failed, recorded without inventing an outcome. A non-thinking retry and the V2 review used the authorized GLM-4.6V API. Seven-dimension averages were 67.1 and 75.0; both failed. Critic falsely claims bbox overlap and confuses a floor transition with a tabletop. Review-consistency.json records the geometry contradiction and patch validation. These scores are not evidence of aesthetic improvement. The final status is NEEDS_REVIEW, with V2 selected by human review.

New program rules require seven finite dimension scores, average >=85, every dimension >=80, no unresolved problems; original reported_score is retained. Invalid patches preserve the last reviewable poster instead of losing the run. Later reviews receive previous image/critique and computed overlap booleans. This helps audit the model; it does not guarantee correct aesthetic judgments.

Reproduce V2 in the project environment:

```powershell
python guided_render.py --spec samples/rework/jadore-20261001/v2/PosterSpec.json --product samples/rework/jadore-20261001/product.png --background samples/rework/jadore-20261001/v1/background.png --output runs/reproduction/jadore-rework.png
```
