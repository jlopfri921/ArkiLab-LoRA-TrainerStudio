# OrkiLab 0.4.0 — Dataset Studio: initial scope and acceptance

**Status:** proposed milestone; **no 0.4.0 implementation or release claimed**. Development follows the published 0.3.0-rc.1 and the post-RC Boogu layout fix. The existing 0.3 release tag remains immutable.

## Goal and workflow

**Projects → Dataset Studio → Training Engines → ComfyUI**.

Prepare, inspect and export **image** datasets for LoRA training in one local-first workspace. Video/audio dataset support is a future extension, not part of the first 0.4 acceptance gate.

## Delivery stages

| Stage | Scope | Must pass |
| --- | --- | --- |
| 0.4.0-alpha.1 | Project-linked image library: import by reference, thumbnails, filter/sort, metadata, review and selection | Original files unchanged; empty/broken directories handled, no remote upload |
| 0.4.0-alpha.2 | Duplicates (exact SHA-256 and optional perceptual near-duplicates), dimension/ratio/blur warnings and bounded scan progress | Deterministic results on fixtures, cancellable scans and no hidden deletion |
| 0.4.0-beta.1 | Manual captions, batch edit preview, optional explicit locally executed captioner adapter; non-destructive resize/crop export | Reversible edit history, sidecar validation, consent before model use |
| 0.4.0-rc.1 | Per-trainer export profiles, reproducible dataset manifest, train/validation split and UI integration | Manifest round trip, reproducible split/seed and trainer launch compatibility |
| 0.4.0 | Docs, accessibility/i18n, Windows/Linux CI, real local Windows smoke and no-data-loss update | Release evidence recorded, known limits documented |

## Product requirements

1. **Non-destructive by default.** Import references existing paths, never moves, renames or rewrites source images/captions. Dataset removal removes only library references. Derived versions and exports live in a separate managed destination. A destructive filesystem operation, if ever added, needs a separate design/review.
2. **Local-first and private.** No automatic upload or public sharing; no Hugging Face or Civitai integration as part of this milestone. Future cloud captioning requires an explicit opt-in and clear data transfer disclosure.
3. **Per-project ownership.** Persist image references, sources, collection labels and edit decisions in SQLite under `settings/orkilab`; use migrations, bounded queries and safe path checks.
4. **Useful failure states.** Handle missing/renamed files, unreadable directories, unsupported formats, huge images, truncated content, low disk space and processing cancellation.
5. **Explicit decisions.** Duplicates, quality flags and AI captions are suggestions, not silent edits. Human review precedes any batch application.
6. **Compatibility.** Train/export adapters must describe each engine's folder, resolution/caption conventions; avoid pretending all engines accept the same schema.
7. **Access and safety.** Mutation endpoints are local-only, validate paths and request sizes and reject symlink traversal outside approved roots. No processing at import time until explicitly started.
8. **Languages/accessibility.** New interface strings in all eight supported locales with English fallback; labels, keyboard navigation and no unnecessary long vertical scroll.

## Proposed first implementation PR (alpha.1)

- Dedicated `/workspace/datasets` entry from the main Workspace, with a clear introduction and empty state.
- SQLite-backed collection index scoped to a project, import-by-reference and image-only extension/filter metadata.
- Read-only thumbnail service for approved, indexed files, with size limits and no path traversal.
- Search/sort/filter and manual review states without touching images.
- Synthetic-fixture tests on Windows and Linux proving imports are non-destructive and unauthorized requests are rejected.

**Out of scope for alpha.1:** AI captioning, image generation, automatic training, caption rewrites, cloud sync, multiview, audio/video, marketplace integration and any direct write to the user's dataset folders.

## 0.3.0 stable prerequisite

Before calling 0.3.0 stable, review outstanding ComfyUI custom-node/Bridge failures, browser regressions, history/media persistence, unsupported media types and on-device security; label anything unverified. Boogu's compact-layout change is a post-0.3.0-rc.1 development improvement and is not backdated into that tag.

## Acceptance model

`PASS`: test command/result, commit and environment recorded. `REPORTED PASS`: operator result without retained detailed log. `NOT VERIFIED`: no sufficient evidence; not equal to failure. CI without a GPU **cannot** certify actual end-to-end training. Maintain a separate acceptance record for each 0.4 milestone.
