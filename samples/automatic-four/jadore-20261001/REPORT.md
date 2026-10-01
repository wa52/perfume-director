# Actual automatic four-direction ComfyUI run

User requested an automatic trial. Submitted LoadImage -> PerfumeDirectorLoop to the local ComfyUI /prompt endpoint, prompt_id ce70f462-c5a0-4333-a7fb-87e59596a1e3. The node returned job 03a710f9c249435d8da47cb8e1b310f0. Runtime used GLM-4.6V with thinking enabled, the existing authorized product/references, and default maximum three rounds per direction. No human edited any Spec, Critic response, background, typography or product placement in this batch.

Final batch status: PARTIAL. All four directions produced an image; no direction achieved a valid PASS.

- Black/gold: one rendered image. Critic returned pass:true while also returning six changes. Schema validation correctly rejected the contradictory approval (ValueError). No invented score or PASS in the display.
- Cream minimal: V1 rendered/reviewed, the model's patches automatically produced V2. V2 Critic connection closed (RemoteDisconnected). Batch marked ERROR despite keeping the existing files.
- Burgundy editorial: V1 score average 79.3, NEEDS_REVIEW. Invalid/off-canvas Critic patch was rejected; last valid poster preserved.
- Botanical: V1 score average 73.6, NEEDS_REVIEW. Invalid Critic patch was rejected; last valid poster preserved.

Contact sheet uses program-selected versions for completed reviews, and the last generated image for errored reviews. Error images are explicitly unaccepted, not reclassified as successful. Display-manifest.json records hashes and selection provenance. Archived call traces, Specs, all renders and failures allow independent audit. The GUI screenshot shows the actual PARTIAL result and its two previewable directions.

This trial verifies automatic dispatch and real rendering/revision, but exposes unreliable Critic outputs and API interruptions. It does not demonstrate stable professional art direction. Future work should first address these faults, rather than hiding them with manual revisions in an automatic sample.
