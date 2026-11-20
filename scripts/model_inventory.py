"""Bounded, read-only inventory; never loads model weights."""
import os
import time
from pathlib import Path, PurePosixPath
from collections import Counter

EXTENSIONS = {".safetensors", ".ckpt", ".gguf", ".pt", ".pth", ".bin", ".onnx"}
CATEGORIES = {"checkpoints": "Checkpoint", "diffusion_models": "Diffusion model",
              "unet": "Diffusion model", "loras": "LoRA", "vae": "VAE",
              "clip": "Text encoder", "text_encoders": "Text encoder",
              "controlnet": "ControlNet", "embeddings": "Embedding",
              "upscale_models": "Upscaler", "audio_encoders": "Audio encoder",
              "clip_vision": "Vision encoder"}
LIMIT = 3000

def category(name, fallback="Weights"):
    parts = PurePosixPath(name.replace("\\", "/")).parts
    return next((CATEGORIES[p.lower()] for p in parts[:-1] if p.lower() in CATEGORIES), fallback)

def scan_local(root, source, fallback="Weights", limit=LIMIT):
    rows = []
    deadline = time.monotonic() + 3
    scanned = 0
    errors = []
    root = Path(root)
    try:
        if not root.is_dir():
            return rows, "Folder unavailable"
        for current, dirs, files in os.walk(root, followlinks=False, onerror=errors.append):
            dirs[:] = [d for d in dirs if not d.startswith(".") and not Path(current, d).is_symlink()
                       and not getattr(Path(current, d), "is_junction", lambda: False)()]
            for name in files:
                scanned += 1
                if scanned > 30000 or len(rows) >= limit or time.monotonic() > deadline:
                    return rows, "Inventory limit reached"
                p = Path(current, name)
                if p.suffix.lower() not in EXTENSIONS or p.is_symlink():
                    continue
                try:
                    relative = p.relative_to(root).as_posix()
                    rows.append({"source": source, "name": relative, "category": category(relative, fallback),
                                 "format": p.suffix.lower()[1:], "bytes": p.stat().st_size})
                except OSError:
                    continue
            if time.monotonic() > deadline:
                return rows, "Inventory limit reached"
    except OSError:
        return rows, "Folder unavailable"
    return rows, "Some folders could not be read" if errors else ""

def scan_comfy(url, get_json):
    rows = []
    # Discover categories first; use only fixed, known API paths.
    folders = get_json(url, "/models")
    if not isinstance(folders, list):
        raise ValueError("Invalid model inventory")
    warnings = []
    seen = set()
    for folder, kind in CATEGORIES.items():
        if folder not in folders:
            continue
        try:
            names = get_json(url, "/models/" + folder)
            if not isinstance(names, list):
                raise ValueError()
        except (OSError, ValueError):
            warnings.append("Some ComfyUI categories could not be read")
            continue
        for name in names:
            if not isinstance(name, str) or len(name) > 1024:
                continue
            key = (kind, name)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"source": "ComfyUI", "name": name, "category": kind,
                         "format": PurePosixPath(name).suffix.lower()[1:], "bytes": None})
            if len(rows) >= LIMIT:
                return rows, "Inventory limit reached"
    return rows, warnings[0] if warnings else ""

def inventory(base, config, get_json):
    rows, warnings = [], []
    roots = [(base / "Models", "OrkiLab", "Weights"),
             (base / "Outputs", "OrkiLab outputs", "Training output")]
    if config["model_folder"]:
        shared = Path(os.path.expanduser(config["model_folder"]))
        if shared.is_absolute():
            roots.append((shared, "Shared folder", "Weights"))
        else:
            warnings.append({"source": "Shared folder", "message": "Use an absolute model folder path"})
    for root, source, kind in roots:
        found, warning = scan_local(root, source, kind)
        rows.extend(found)
        if warning:
            warnings.append({"source": source, "message": warning})
    if config["mode"] != "native":
        try:
            found, warning = scan_comfy(config["url"], get_json)
            rows.extend(found)
            if warning:
                warnings.append({"source": "ComfyUI", "message": warning})
        except (OSError, ValueError):
            warnings.append({"source": "ComfyUI", "message": "Could not read ComfyUI models"})
    counts = Counter(PurePosixPath(r["name"].replace("\\", "/")).name.casefold() for r in rows)
    for row in rows:
        row["same_name"] = counts[PurePosixPath(row["name"].replace("\\", "/")).name.casefold()] > 1
    return {"models": sorted(rows, key=lambda r: (r["source"], r["name"].casefold())), "warnings": warnings}
