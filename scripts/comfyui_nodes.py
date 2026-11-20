"""Discover ComfyUI node metadata without loading or executing workflows."""
import re
from http.client import HTTPException
from urllib.error import HTTPError

MAX_NODES = 5000

def discover(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid ComfyUI node inventory")
    rows = []
    for key, item in data.items():
        if not isinstance(key, str) or not isinstance(item, dict) or not any(k in item for k in ("input", "output", "display_name", "name")):
            continue
        module = str(item.get("python_module") or "")[:300]
        outputs = item.get("output", [])
        outputs = [str(x)[:80] for x in outputs[:32]] if isinstance(outputs, list) else []
        group = str(item.get("category") or "")[:200]
        name = str(item.get("display_name") or key)[:200]
        hint = " ".join([key, name, group, *outputs]).lower()
        tags = []
        for tag, pattern in (
            ("Image", r"\bimage\b|image"),
            ("Video", r"video|animatediff|\bframes\b"),
            ("Audio", r"audio|waveform|music|speech"),
            ("3D", r"\b3d\b|mesh|pointcloud|point_cloud"),
            ("LoRA", r"lora|lycoris"),
            ("Conditioning", r"conditioning|controlnet"),
            ("Sampling", r"sampler|sampling"),
        ):
            if re.search(pattern, hint):
                tags.append(tag)
        origin = "Custom" if module.startswith("custom_nodes.") else (
            "Built-in" if module == "nodes" or module.startswith("comfy_extras.") else "Unknown")
        rows.append({"id": key[:300], "name": name, "category": group, "module": module,
                     "origin": origin, "outputs": outputs, "tags": tags})
        if len(rows) >= MAX_NODES:
            break
    if not rows:
        raise ValueError("ComfyUI returned no valid node definitions")
    return {"nodes": sorted(rows, key=lambda x: x["name"].casefold()),
            "truncated": len(data) > len(rows)}

def fetch_nodes(url, get_json):
    failures = []
    for path in ("/object_info", "/api/object_info"):
        try:
            result = discover(get_json(url, path, max_bytes=96_000_000, timeout=60))
            result["endpoint"] = path
            return result
        except (OSError, ValueError, HTTPException) as exc:
            failures.append(f"{path}: {exc}"[:350])
    raise ValueError(" | ".join(failures))
