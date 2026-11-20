"""Conservative conversion of ordinary ComfyUI visual graphs.

Only known built-in widget layouts are converted. Unknown frontend behavior,
subgraphs, bypasses and custom widgets require an API export from ComfyUI.
"""
from urllib.parse import quote

# Explicit frontend widget order, including seed control widgets.
LAYOUTS = {
    "CheckpointLoaderSimple": ("ckpt_name",),
    "CLIPTextEncode": ("text",),
    "EmptyLatentImage": ("width", "height", "batch_size"),
    "KSampler": ("seed", None, "steps", "cfg", "sampler_name", "scheduler", "denoise"),
    "VAEDecode": (),
    "VAEEncode": (),
    "SaveImage": ("filename_prefix",),
    "PreviewImage": (),
    "LoraLoader": ("lora_name", "strength_model", "strength_clip"),
    "LoraLoaderModelOnly": ("lora_name", "strength_model"),
    "VAELoader": ("vae_name",),
    "CLIPSetLastLayer": ("stop_at_clip_layer",),
    "LoadImage": ("image", None),
}

def node_schema(url, kind, get_json):
    for prefix in ("/object_info/", "/api/object_info/"):
        try:
            data = get_json(url, prefix + quote(kind, safe=""), max_bytes=8_000_000, timeout=20)
            if isinstance(data, dict) and isinstance(data.get(kind), dict):
                return data[kind]
        except (OSError, ValueError):
            pass
    raise ValueError("Node metadata unavailable: " + kind)

def validate_prompt(prompt, schema):
    for ident, node in prompt.items():
        kind = node["class_type"]
        spec = schema[kind]
        fields = spec.get("input", {})
        required = fields.get("required", {})
        optional = fields.get("optional", {})
        for name in required:
            if name not in node["inputs"]:
                raise ValueError(f"{kind} #{ident}: missing input {name}")
        for name, value in node["inputs"].items():
            descriptor = required.get(name, optional.get(name))
            if not isinstance(descriptor, list) or not descriptor:
                raise ValueError(f"{kind} #{ident}: unknown input {name}")
            typ = descriptor[0]
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and type(value[1]) is int:
                upstream = prompt.get(value[0])
                if upstream is None:
                    raise ValueError(f"{kind} #{ident}: invalid link {name}")
                outputs = schema[upstream["class_type"]].get("output", [])
                if not 0 <= value[1] < len(outputs):
                    raise ValueError(f"{kind} #{ident}: invalid output slot")
                if isinstance(typ, str) and typ not in ("*", outputs[value[1]]):
                    raise ValueError(f"{kind} #{ident}: incompatible link {name}")
                continue
            if isinstance(typ, list) and value not in typ:
                raise ValueError(f"{kind} #{ident}: unavailable option {name}: {value}")
            if typ == "INT" and type(value) is not int:
                raise ValueError(f"{kind} #{ident}: invalid integer {name}")
            if typ == "FLOAT" and type(value) not in (int, float):
                raise ValueError(f"{kind} #{ident}: invalid number {name}")
            if typ == "STRING" and not isinstance(value, str):
                raise ValueError(f"{kind} #{ident}: invalid text {name}")
            if typ == "BOOLEAN" and type(value) is not bool:
                raise ValueError(f"{kind} #{ident}: invalid boolean {name}")
            if isinstance(typ, str) and typ not in ("INT","FLOAT","STRING","BOOLEAN","*"):
                raise ValueError(f"{kind} #{ident}: input {name} requires a link")
            opts = descriptor[1] if len(descriptor) > 1 and isinstance(descriptor[1], dict) else {}
            if type(value) in (int,float) and (("min" in opts and value < opts["min"]) or ("max" in opts and value > opts["max"])):
                raise ValueError(f"{kind} #{ident}: out of range {name}")
    if not any(schema[n["class_type"]].get("output_node") for n in prompt.values()):
        raise ValueError("No executable output node")
    visiting, done = set(), set()
    def visit(ident):
        if ident in visiting:
            raise ValueError("Workflow contains a cycle")
        if ident in done:
            return
        visiting.add(ident)
        for v in prompt[ident]["inputs"].values():
            if isinstance(v,list) and len(v)==2 and isinstance(v[0],str):
                visit(v[0])
        visiting.remove(ident)
        done.add(ident)
    for ident in prompt:
        visit(ident)

def convert_visual(graph, url, get_json):
    nodes = graph.get("nodes")
    links = graph.get("links")
    if not isinstance(nodes,list) or not isinstance(links,list):
        raise ValueError("Unsupported visual graph structure")
    definitions = graph.get("definitions") or {}
    if not isinstance(definitions, dict):
        raise ValueError("Unsupported workflow definitions")
    subgraphs = definitions.get("subgraphs") or []
    if not isinstance(subgraphs, list):
        raise ValueError("Unsupported subgraph definitions")
    subgraph_ids = {str(item.get("id")) for item in subgraphs if isinstance(item, dict)}
    used = [n for n in nodes if str(n.get("type")) in subgraph_ids]
    if used:
        names = {str(item.get("id")): str(item.get("name") or item.get("id")) for item in subgraphs if isinstance(item, dict)}
        raise ValueError("Subgraphs require ComfyUI API export: " + ", ".join(names[str(n.get("type"))] for n in used)[:300])
    if any(value for key, value in definitions.items() if key != "subgraphs"):
        raise ValueError("Unsupported workflow definitions")
    link_map = {}
    for link in links:
        if not isinstance(link,list) or len(link)<6 or type(link[2]) is not int or type(link[4]) is not int:
            raise ValueError("Unsupported link format")
        if str(link[0]) in link_map:
            raise ValueError("Duplicate link ID")
        link_map[str(link[0])] = (str(link[1]),link[2],str(link[3]),link[4])
    prompt, schemas = {}, {}
    for n in nodes:
        kind = n.get("type")
        if kind in ("Note","MarkdownNote") and not n.get("inputs") and not n.get("outputs"):
            continue
        if n.get("mode",0) != 0 or kind not in LAYOUTS:
            raise ValueError(f"Unsupported visual node: {kind}. Export API format in ComfyUI.")
        ident = str(n.get("id"))
        if ident in prompt or ident=="None":
            raise ValueError("Invalid node ID")
        if kind not in schemas:
            schemas[kind] = node_schema(url,kind,get_json)
        widgets = n.get("widgets_values",[])
        layout = LAYOUTS[kind]
        if not isinstance(widgets,list) or len(widgets)!=len(layout):
            raise ValueError(f"{kind}: unsupported widget layout")
        inputs = {name: value for name,value in zip(layout,widgets) if name is not None}
        for i, slot in enumerate(n.get("inputs",[])):
            if not isinstance(slot,dict) or not isinstance(slot.get("name"),str):
                raise ValueError("Invalid input slot")
            if slot.get("link") is None:
                continue
            link = link_map.get(str(slot["link"]))
            if not link or link[2:] != (ident,i):
                raise ValueError("Invalid visual link")
            inputs[slot["name"]] = [link[0],link[1]]
        prompt[ident] = {"class_type":kind,"inputs":inputs}
    validate_prompt(prompt,schemas)
    return prompt
