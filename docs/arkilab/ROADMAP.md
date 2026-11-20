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
