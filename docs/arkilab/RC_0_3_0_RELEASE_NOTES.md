# OrkiLab v0.3.0-rc.1 — prerelease notes (publication draft)

> **Not published.** Copy/adapt this document to the GitHub prerelease only after the final release acceptance gates pass, the release PR is merged and a verified tag `v0.3.0-rc.1` points to the exact release commit. Do not label this as a stable release.

## Summary

The 0.3 release candidate focuses on the modern Workspace, the ComfyUI Zone and more controlled real-world generation workflows. The supported path is **local and operator-confirmed**; not every ComfyUI custom node, trainer or LoRA model is guaranteed to work.

## What is included

- Guided ComfyUI connection/onboarding, workflow exploration and inspection, and optional OrkiLab Bridge preparation for trusted visual graphs.
- Generation Studio: explicit submission, progress where supplied by ComfyUI, cancellation isolation, result preview/history and safe paths for supported outputs.
- Read-only GPU telemetry with RAM/VRAM monitoring and optional release of ComfyUI model/cache resources.
- Modern trainer navigation, contextual assistance and compact configuration panels; existing training engines are retained.
- English and other locales in the new Workspace; locale completeness and fallback across all legacy trainer inputs are not independently certified.
- The existing LoRA Comparator **remains experimental and unverified**, with no compatibility guarantee or required acceptance for this RC.

## Acceptance evidence and limitations

- **GitHub Actions:** Python 3.13 GPU-free RC validation and foundation checks completed successfully on **Windows and Ubuntu** at the PR #42 candidate commit `52b4a98f3089c26ce8201cf37d0f25dd1f7a55a4` (runs `44847212885`, `44847212900`). After editing release documentation, rerun checks on the current PR SHA and final merge SHA.
- **Windows local UI:** operator supplied a screenshot-free console transcript `3/3 OK` for `sdxl`, `wan22`, `yue2` using the project virtualenv, and reported that the full trainer UI smoke suite and unit tests passed. Browser smoke tests simulate training actions rather than performing GPU training.
- **ComfyUI real-world operator reports:** generated image found in history; cancellation did not affect other jobs; RAM/VRAM checked before/after releasing models; correct disconnected state; invalid workflow handled; safe update retained data. These are operator **reported successes** and not complete per-case instrumented verification.
- **Not independently covered by the above:** unauthorized/remote access controls, every invalid custom-node scenario, all audio/video/mesh previews and persistence cases, every GPU telemetry sensor, multi-GPU physical validation, the two-strength LoRA Comparator, end-to-end training on every engine, and a cross-platform installer/rollback run.
- Exact workflow percentage and immediate interruption are dependent on ComfyUI's reported progress and queue status.
- Local-first behavior and model compatibility depend on ComfyUI Desktop, optional custom nodes and the installed model set. Only import workflows and install dependencies from trusted sources.

Detailed acceptance: [0.3 readiness register](RC_0_3_0_READINESS.md) and [GPU/Generation matrix](GPU_GENERATION_ACCEPTANCE.md).

## Install or update (Windows; non-destructive)

1. Before updating, back up datasets, user settings, workflows, projects and generated outputs. Do not delete or reset them.
2. From the repository directory, inspect `git status --short`, `git branch --show-current` and `git remote -v`. If local changes are present, preserve them and resolve safely instead of forcing a reset or cleaning ignored data.
3. After this prerelease has been published, use the tagged `v0.3.0-rc.1` source or the official repository instructions. Do not deploy a pending PR as an official release.
4. Use the existing project's virtualenv for checks: `.\venv\Scripts\python.exe -m unittest discover -s tests -v` and `.\venv\Scripts\python.exe tools\smoke_test_ui.py --only sdxl,wan22,yue2`.
5. If needed, reinstall the OrkiLab Bridge from ComfyUI Zone and restart ComfyUI Desktop. Verify connection before running a trusted workflow.
6. If a regression appears, stop unsafe jobs, preserve logs and user data, then return the code to the previously working tagged version; avoid resetting or overwriting settings, datasets, projects or outputs.

## Publication checklist for maintainers

- [ ] Complete the remaining mandatory security and integrity checks, and record honest limitations.
- [ ] Verify Windows and Ubuntu Actions checks on the **current PR head SHA** and **merged main SHA**.
- [ ] Verify `VERSION_ARKILAB`, `GUI/launcher.json`, README badge and changelog consistently show `0.3.0-rc.1`.
- [ ] Merge release candidate PR after acceptance.
- [ ] Create annotated tag `v0.3.0-rc.1` **on the verified merge SHA**, push the tag without rewriting history.
- [ ] Publish GitHub **Pre-release** (not Latest/stable), link these notes and acceptance docs; verify displayed tag and SHA.
- [ ] Keep the prior release available for rollback.
