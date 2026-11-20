"""Expose editable scalar inputs without modifying the saved workflow."""
import copy
import math

def editable_fields(graph, schemas):
    fields = []
    for ident, node in graph.items():
        schema = schemas[node["class_type"]].get("input", {})
        descriptors = {**schema.get("required", {}), **schema.get("optional", {})}
        for name, value in node["inputs"].items():
            desc = descriptors.get(name)
            if not isinstance(desc, list) or not desc:
                continue
            typ = desc[0]
            opts = desc[1] if len(desc) > 1 and isinstance(desc[1], dict) else {}
            if opts.get("forceInput") or opts.get("defaultInput"):
                continue
            if isinstance(typ, list):
                if not typ or len(typ) > 5000 or any(type(x) not in (str,int,float,bool) for x in typ) or value not in typ:
                    continue
                kind = "choice"
            elif typ == "STRING" and isinstance(value,str):
                kind = "text"
            elif typ == "INT" and type(value) is int and abs(value) <= 9007199254740991:
                kind = "integer"
            elif typ == "FLOAT" and type(value) in (int,float) and math.isfinite(value):
                kind = "number"
            elif typ == "BOOLEAN" and type(value) is bool:
                kind = "boolean"
            else:
                continue
            field = {"node":ident,"class_type":node["class_type"],"name":name,"kind":kind,"value":value}
            if kind == "choice":
                field["choices"] = typ
            if kind in ("integer","number"):
                for key in ("min","max","step"):
                    val = opts.get(key)
                    if type(val) in (int,float) and math.isfinite(val) and abs(val) <= 9007199254740991:
                        field[key] = val
            if isinstance(opts.get("tooltip"),str):
                field["help"] = opts["tooltip"][:500]
            fields.append(field)
            if len(fields) >= 300:
                return fields
    return fields

def apply_edits(graph, fields, edits):
    if not isinstance(edits,list) or len(edits)>300:
        raise ValueError("Invalid parameter changes")
    allowed = {(f["node"],f["name"]):f for f in fields}
    result = copy.deepcopy(graph)
    seen = set()
    for edit in edits:
        if not isinstance(edit,dict) or not isinstance(edit.get("node"),str) or not isinstance(edit.get("name"),str) or "value" not in edit:
            raise ValueError("Invalid parameter change")
        key = (edit["node"],edit["name"])
        f = allowed.get(key)
        if not f or key in seen:
            raise ValueError("Parameter is not editable")
        seen.add(key)
        v = edit["value"]
        kind = f["kind"]
        ok = (kind=="choice" and any(type(v) is type(x) and v==x for x in f["choices"]) or
              kind=="text" and isinstance(v,str) and len(v)<=100000 or
              kind=="integer" and type(v) is int and abs(v)<=9007199254740991 or
              kind=="number" and type(v) in (int,float) and math.isfinite(v) or
              kind=="boolean" and type(v) is bool)
        if not ok:
            raise ValueError("Invalid value: "+f["name"])
        if kind in ("integer","number") and (("min" in f and v<f["min"]) or ("max" in f and v>f["max"])):
            raise ValueError("Value out of range: "+f["name"])
        result[key[0]]["inputs"][key[1]] = v
    return result
