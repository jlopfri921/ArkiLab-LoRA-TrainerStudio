# ComfyUI integration — proposed contract

Existing export: Send to Models copies LoRA to selected models/loras folder; export path shared across trainers, metadata embedded. Preserve it. New adapter must run in ArkiLab environment, not install into ComfyUI.

Config: default http://127.0.0.1:8188; explicit opt-in for LAN URL. Read-only health/inventory candidates: GET /system_stats, /object_info, /queue, /history/{prompt_id}. Validate exact node class and model names before generating API-format workflow. Submit only on explicit user action via POST /prompt; track prompt_id, use /ws or polling; retrieve output only through supported endpoints. Confirm against actual ComfyUI version before implementation. No arbitrary URL fetching from untrusted workflows.

Define registry: architecture, variant, loader class, compatible LoRA format, model/text encoder/VAE requirements. Distinguish GGUF and native loaders, do not guess compatibility from file extensions. Initial target FLUX.3 and Qwen 2.1 with native models. Store templates per architecture and test with mocked object_info. Keep file copy atomic and reject collisions by default. Prefer separate GPU scheduling or user confirmation when training is active.

Acceptance: mock tests for missing model/node, unreachable endpoint, invalid workflow, failed job, duplicate filenames, cancellation handling; live smoke run on local machine. Never expose unauthenticated ComfyUI publicly.
