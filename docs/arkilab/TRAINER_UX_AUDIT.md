# Trainer UX consolidation — setting finder pilot

## Scope

The existing staged trainer interface already provides Basic/Expert modes and panel navigation. This change adds an in-place setting finder to the **shared** `orkilab-pilot.js` and stylesheet. No trainer settings, IDs, default values, API calls or training scripts are replaced.

- Enter at least two characters to filter existing labeled controls; at most eight matches are displayed.
- Choose a match to switch to its current stage, enable Expert mode temporarily, scroll to and focus the original control.
- The search is client-side and never writes input values or submits a training job.
- The UI remains usable if no matching controls are found; translated headings and labels are reused where possible.
- It works with any trainer whose DOM passes the shared pilot's safety checks; unsupported trainer structures continue to fall back to their original interface.

## Validation

Automated static coverage: `python -m unittest tests.test_trainer_setting_finder tests.test_workspace_navigation`.

Manual test on the installed app is still required, including an actual local restart. Verify:

1. Navigate Dashboard → Projects → Training engines → GPU Manager and use contextual help in every section.
2. Open SDXL from the Workspace. Search `Learning Rate` and `Rank`, select an existing field and confirm it receives focus in Expert mode.
3. Switch Basic/Expert, check defaults remain unchanged and submit a *non-running* configuration review; avoid starting training for this UX test.
4. Repeat on a video and image trainer with different options, and at narrow screen widths.
5. Confirm GPU monitoring and training jobs are unaffected.

Do not delete classic views until field-by-field audits, accessible interactions, runtime browser testing, translation checks and backend parity are complete.
