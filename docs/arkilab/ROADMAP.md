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

Dependencies: Foundation -> Workspace -> Connect and Dataset -> Multiview/Benchmark -> Copilot/Hub -> Desktop -> Stable. Prioritize read-only adapters, then writes. No release dates promised. GPU scheduling, plugins, offline mode and migration backups require separate design reviews.
