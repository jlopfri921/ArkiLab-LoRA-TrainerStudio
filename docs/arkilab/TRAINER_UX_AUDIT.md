# Trainer UX consolidation — setting finder pilot

## Scope

The existing staged trainer interface already provides Basic/Expert modes and panel navigation. This change adds an in-place setting finder and a basic-first presentation to the **shared** `orkilab-pilot.js` and stylesheet. No trainer settings, IDs, default values, API calls or training scripts are replaced.

- New users start in **Basic** presentation; an existing saved Basic/Expert choice is respected. Expert controls are never deleted and training parameter values are not modified. The navigation announces how many advanced controls are hidden in the current stage.
- Enter at least two characters to filter existing labeled controls; at most eight matches are displayed.
- Choose a match to switch to its current stage, enable Expert mode temporarily, scroll to and focus the original control.
- The search is client-side and never writes input values or submits a training job.
- A clear empty-results message is displayed when nothing matches; labels are read from the current DOM so changes of UI language remain searchable.
- It works with any trainer whose DOM passes the shared pilot's safety checks; unsupported trainer structures continue to fall back to their original interface.

## Validation

Automated static coverage: `python -m unittest tests.test_trainer_setting_finder tests.test_workspace_navigation`.

Manual test on the installed app is still required, including an actual local restart. Verify:

1. Navigate Dashboard → Projects → Training engines → GPU Manager and use contextual help in every section.
2. Open SDXL from the Workspace. Search `Learning Rate` and `Rank`, select an existing field and confirm it receives focus in Expert mode.
3. Verify first-run Basic mode, restart with a saved Expert preference, switch Basic/Expert and check defaults remain unchanged and submit a *non-running* configuration review; avoid starting training for this UX test.
4. Repeat on a video and image trainer with different options, and at narrow screen widths.
5. Confirm GPU monitoring and training jobs are unaffected.

Do not delete classic views until field-by-field audits, accessible interactions, runtime browser testing, translation checks and backend parity are complete.

## Individual trainer audit — first pass (SDXL / FLUX.1 / Qwen-Image 2.1)

This pass inspects the real HTML control IDs, keeping original forms, input values, event handlers and backend behavior. The shared modern presentation continues to use a safe fallback if panels are unfamiliar.

| Trainer | Identified training controls | Essential (examples) | Additional Expert-only controls | Notes |
| --- | ---: | --- | --- | --- |
| SDXL | 33 IDs in the reviewed prefix families | Steps, learning rate, rank, batch size, pre-cache and previews | Shared scheduler, LoRA variations, precision, accumulation, checkpoint and seed settings | Keeps original SDXL forms |
| FLUX.1 | 39 IDs in the reviewed prefix families | Steps, LR, rank, batch size, **automatic VRAM profile** | Resident blocks, block-swap storage, RAM limit and guidance, on top of shared advanced fields | No VRAM value is modified by switching modes |
| Qwen-Image 2.1 | 37 IDs in the reviewed prefix families | Steps, LR, rank, batch size, pre-cache and turbo toggle | Turbo strength (plus shared Expert controls) | Preserve model-specific options and their IDs |

Counts are HTML ID observations, **not** a claim that all controls have passed live training validation. The next pass should include Krea, Z-Image, other FLUX engines, video and audio engines. The new Expert classification only changes visibility. Required, hidden or conditionally displayed fields must still be checked per trainer in browser before classic views can be removed.
