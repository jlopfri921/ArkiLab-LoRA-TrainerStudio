"""Discover ComfyUI node metadata without loading or executing workflows."""
import re

MAX_NODES = 5000

def discover(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid ComfyUI node inventory")
    rows = []
    for key, item in data.items():
        if not isinstance(key, str) or not isinstance(item, dict):
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
    return {"nodes": sorted(rows, key=lambda x: x["name"].casefold()),
            "truncated": len(data) > len(rows)}

def fetch_nodes(url, get_json):
    return discover(get_json(url, "/object_info", max_bytes=96_000_000, timeout=60))
