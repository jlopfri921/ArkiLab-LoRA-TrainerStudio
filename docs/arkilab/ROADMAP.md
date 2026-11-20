# Roadmap

| Release | Scope | Acceptance gate |
|---|---|---|
| 0.1 Foundation | branding, docs, safe update | review diff; launch existing UI; update tests |
| 0.2 Workspace | SQLite library, project registry, read-only inventory | index synthetic data; no destructive writes |
| 0.3 Connect | ComfyUI API adapter, workflow validation, explicit submission | mock API tests; real local inference |
| 0.4 Dataset | quality checks, dedup, captions, split | reproducible manifest and non-destructive edits |
| 0.5 Multiview | angle metadata, reference/synthetic distinction | all views individually validated |
| 0.6 Benchmark | paired prompts/seeds, comparable performance | reproducible report and held-out evaluation |
| 0.7 Copilot | Ollama suggestions, logs | user confirmation for mutations |
| 0.8 Hub | HF/Civitai integration | license/token checks and explicit downloads/uploads |
| 0.9 Desktop | portable application/installer | clean Windows/Linux install and rollback |
| 1.0 Stable | documented supported matrix | regression and hardware validation |

## Immediate milestone: 0.3.0-rc.1 — ComfyUI integration candidate

**Status:** scope agreed, candidate **not tagged or released**. The version in `VERSION_ARKILAB` remains `0.2.0-rc.1` until the release gate passes.

**Included in the 0.3 RC (features to stabilize, not a promise every workflow will work):**

- Modern Workspace entry points and the ComfyUI Zone introduction/connection gate, with eight interface languages.
- Local/private ComfyUI connection validation; read-only node and model discovery.
- Workflow library: importing trusted UI/API JSON, indexing local folders, search, favorites, and non-destructive inspection.
- OrkiLab Bridge visual-to-API graph preparation; validation of representative installed-node workflows.
- Generation Studio: explicit review/confirmation, supported parameter editing, job status, best-effort per-node progress, safe cancellation, history and output access.
- Optional, queue-safe ComfyUI model/cache release and per-generation system RAM/VRAM diagnostic snapshots. GPU Manager read-only multi-adapter telemetry and bounded charts.
- Standard-LoRA-loader comparison as an explicitly scoped capability (custom loaders remain unsupported).
- Preserved existing trainer launching and queue; no claim of full trainer-interface modernization in 0.3.

**Exit criteria before changing the version to `0.3.0-rc.1`:**

1. CI passes on Windows and Linux; unit tests include connection/navigation, Bridge parsing, execution safety, RAM/VRAM diagnostics and existing trainer launch routes.
2. Record **actual** Windows + RTX 3090 + ComfyUI Desktop smoke-test evidence: connected/disconnected state, one known-good API graph, one visual graph via Bridge, execution progress, cancellation, history/output links and memory release without interrupting unrelated queue jobs.
3. Check failure states: ComfyUI absent, invalid workflow/sampler, missing custom nodes, unsupported output, failed generation and unauthorized remote access. Imported workflows must never run automatically.
4. Test language switching and page navigation (including Projects and Training Engines) in a real browser, verify no dataset/workflow files are rewritten, and review multi-GPU readings when hardware is available. Single-GPU validation must not be represented as multi-GPU validation.
5. Update README, changelog and acceptance notes with results and known limitations; verify a safe update from the previous release candidate.

**Reported progress (2026-11-21):** user reports that the previously planned real-world ComfyUI/GPU tests have been carried out. Detailed per-scenario PASS/FAIL evidence still needs to be recorded before claiming full certification. Engine-by-engine modernization remains ongoing. Documentation/version planning is being updated here. Packaging and RC tagging follow the exit checks.

**Deferred beyond 0.3 RC:** Dataset Studio (0.4), multiview validation (0.5), broader benchmarking (0.6), Ollama assistant (0.7), Hugging Face/Civitai Hub integration (0.8), production desktop installer (0.9), full trainer modern-view replacement when independently verified, and scheduling or an interactive mesh viewer unless separately accepted.

### 0.3 implementation checkpoints (development, not released)

| Area | Implemented in code | Acceptance still required |
|---|---|---|
| ComfyUI Zone | Separate navigation; read-only model/node inventory and workflow library | Local browser UX and translations |
| Bridge | Installable frontend extension and safe preparation path | ComfyUI Desktop restart and subgraph conversion tests |
| Generation | Graph review, editable inputs, browser presets, explicit execution | Real ComfyUI inference and error-state tests |
| Results | SQLite history, media proxy, images/audio/video playback and downloads | Large-file playback, restarts and 3D viewer |
| LoRA Comparator | Direct workflow discovery, standard-loader weight variants, sequential execution | Full GPU tests, custom loaders, different LoRA files/checkpoints |
| GPU Manager | Read-only local NVIDIA polling and utilization/VRAM alerts | NVIDIA hardware tests, multi-GPU validation, scheduling separately |
| UX/i18n | Modern Workspace/ComfyUI routing and translations | Audit each trainer interface and contextual guidance |

Detailed status: [Workspace feature guide](WORKSPACE_FEATURES.md). Keep the version file unchanged until the corresponding acceptance gates pass.

Dependencies: Foundation -> Workspace -> Connect and Dataset -> Multiview/Benchmark -> Copilot/Hub -> Desktop -> Stable. Prioritize read-only adapters, then writes. No release dates promised. GPU scheduling, plugins, offline mode and migration backups require separate design reviews.
