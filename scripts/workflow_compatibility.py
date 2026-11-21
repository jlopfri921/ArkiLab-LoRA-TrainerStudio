"""Conservative model-family hints for project-scoped ComfyUI LoRA comparison.

A filename or node name is *not* proof of model compatibility. Positive
classification is only a hint; ComfyUI API validation and real inference are
still required. Missing evidence stays unknown rather than becoming a match.
"""
import re

FAMILIES = {
    "flux3klein": ("FLUX.3 Image Klein", (r"flux[._ -]?3(?:[._ -]?(?:image|klein))?", r"flux3klein")),
    "flux2klein": ("FLUX.2 Klein", (r"flux[._ -]?2(?:[._ -]?klein)?", r"flux2klein")),
    "sdxl": ("SDXL", (r"sdxl", r"stable[._ -]?diffusion[._ -]?xl", r"pony[._ -]?diffusion", r"illustrious", r"noobai")),
    "qwenimage21": ("Qwen-Image 2.1", (r"qwen[._ -]?image[._ -]?2[._ -]?1", r"qwenimage21")),
    "qwenimage": ("Qwen-Image", (r"qwen[._ -]?image",)),
    "krea2": ("Krea 2", (r"krea[._ -]?2",)),
    "zimage": ("Z-Image", (r"z[._ -]?image",)),
    "ideogram4": ("Ideogram 4", (r"ideogram[._ -]?4",)),
    "ernieimage": ("ERNIE-Image", (r"ernie[._ -]?image",)),
    "mossimage": ("MOSS-Image", (r"moss[._ -]?image",)),
    "anima": ("Anima", (r"(?:^|[^a-z])anima(?:[^a-z]|$)",)),
}
# In exact-value comparisons, the shorter generic family must not win over
# the more specific name, e.g. Qwen-Image 2.1 versus Qwen-Image.
FAMILY_ORDER = ("flux3klein", "flux2klein", "qwenimage21", "sdxl",
                "krea2", "zimage", "ideogram4", "ernieimage",
                "mossimage", "anima", "qwenimage")
NODE_LOADER = {"LoraLoader", "LoraLoaderModelOnly"}

def family_from_engine(engine):
    if not isinstance(engine, str):
        return None
    name = engine.lower().replace("-", "").replace("_", "")
    if name.startswith("flux3klein"):
        return "flux3klein"
    if name.startswith("flux2klein"):
        return "flux2klein"
    if name.startswith("qwenimage21"):
        return "qwenimage21"
    for family in FAMILY_ORDER:
        if family.replace("_", "") in name:
            return family
    return None

def detect_family(model_references=(), node_types=()):
    """Use model references and distinctive custom loader types, never workflow title."""
    references = [s for s in model_references if isinstance(s, str)]
    custom_nodes = [s for s in node_types if isinstance(s, str) and
                    (s.lower().endswith(("loader", "modelloader")) or "flux3klein" in s.lower())]
    found = set()
    for name in references + custom_nodes:
        for family in FAMILY_ORDER:
            if any(re.search(pattern, name, flags=re.I) for pattern in FAMILIES[family][1]):
                found.add(family)
                break
    # An SDXL LoRA reference alone says nothing about the base model: callers
    # must only pass actual model-loading references, not lora_name values.
    return sorted(found)

def model_evidence(graph):
    if not isinstance(graph, dict):
        return [], [], False
    ui = isinstance(graph.get("nodes"), list)
    nodes = graph["nodes"] if ui else list(graph.values())
    model_refs, classes = [], []
    standard_loader = False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = node.get("type" if ui else "class_type", "")
        if not isinstance(kind, str):
            continue
        classes.append(kind)
        standard_loader = standard_loader or kind in NODE_LOADER
        if ui:
            if "loader" not in kind.lower() and "checkpoint" not in kind.lower():
                continue
            values = node.get("widgets_values", [])
            if not isinstance(values, list):
                continue
            model_refs.extend(s for s in values if isinstance(s, str) and
                              s.lower().endswith((".safetensors",".ckpt",".gguf",".pt",".pth")))
        else:
            inputs = node.get("inputs", {})
            if not isinstance(inputs, dict):
                continue
            for name, value in inputs.items():
                if (isinstance(value,str) and isinstance(name,str) and
                        name.lower() not in ("lora_name", "lycoris_name") and
                        ("model" in name.lower() or "unet" in name.lower()
                         or "ckpt" in name.lower() or "diffusion" in name.lower())
                        and value.lower().endswith((".safetensors",".ckpt",".gguf",".pt",".pth"))):
                    model_refs.append(value)
    return model_refs, classes, standard_loader

def assess_workflow(graph, category, engine):
    expected = family_from_engine(engine)
    refs, nodes, supported = model_evidence(graph)
    families = detect_family(refs, nodes)
    if category not in ("image", "other"):
        return {"status":"incompatible", "reason":"non_image", "expected":expected,
                "detected":families, "standard_loader":supported}
    if not supported:
        return {"status":"incompatible", "reason":"no_loader", "expected":expected,
                "detected":families, "standard_loader":False}
    if expected is None:
        return {"status":"unverified", "reason":"unknown_project_family", "expected":None,
                "detected":families, "standard_loader":True}
    if len(families)>1:
        return {"status":"unverified", "reason":"mixed_models", "expected":expected,
                "detected":families, "standard_loader":True}
    if families and families[0]!=expected:
        return {"status":"incompatible", "reason":"different_family", "expected":expected,
                "detected":families, "standard_loader":True}
    if not families:
        return {"status":"unverified", "reason":"unknown_family", "expected":expected,
                "detected":[], "standard_loader":True}
    return {"status":"candidate", "reason":"family_hint", "expected":expected,
            "detected":families, "standard_loader":True}
