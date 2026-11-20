"""Read-only ComfyUI connection, configured on the launcher host."""
import ipaddress
import json
import os
import tempfile
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler
from flask import jsonify, request

DEFAULT = "http://127.0.0.1:8188"

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def validate_url(value):
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError("Invalid ComfyUI address")
    try:
        u = urlsplit(value.strip())
        host = u.hostname
        ip = ipaddress.ip_address("127.0.0.1" if host == "localhost" else host or "")
        port = u.port or (443 if u.scheme == "https" else 80)
        allowed = any(ip in ipaddress.ip_network(n) for n in (
            "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
            "100.64.0.0/10", "::1/128", "fc00::/7"))
        if (u.scheme not in ("http", "https") or not allowed or u.username is not None
                or u.password is not None or u.path not in ("", "/") or u.query or u.fragment
                or not 1 <= port <= 65535 or "%" in u.netloc):
            raise ValueError()
        address = "[" + str(ip) + "]" if ip.version == 6 else str(ip)
        return f"{u.scheme}://{address}:{port}"
    except (ValueError, TypeError):
        raise ValueError("Use a local or private IP address and port")

def get_json(base, path):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(base + path, timeout=4) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Response too large")
    return json.loads(raw)

def probe(base):
    stats = get_json(base, "/system_stats")
    if not isinstance(stats, dict) or not isinstance(stats.get("system"), dict) or not isinstance(stats.get("devices"), list):
        raise ValueError("Not a ComfyUI response")
    system = stats["system"]
    return {"connected": True, "version": str(system.get("comfyui_version", ""))[:100],
            "devices": [str(d.get("name", ""))[:200] for d in stats["devices"][:16] if isinstance(d, dict)]}

def register(app, base):
    file = base / "settings" / "orkilab" / "comfyui.json"

    def load():
        try:
            return validate_url(json.loads(file.read_text(encoding="utf-8"))["url"])
        except (OSError, ValueError, KeyError, TypeError):
            return DEFAULT

    @app.route("/api/workspace/comfyui", methods=["GET", "POST"])
    def comfyui_settings():
        if request.method == "GET":
            return jsonify(url=load())
        if request.remote_addr not in ("127.0.0.1", "::1"):
            return jsonify(error="Configure ComfyUI on the launcher PC"), 403
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 1024:
            return jsonify(error="Invalid request"), 400
        body = request.get_json(silent=True)
        try:
            url = validate_url(body.get("url") if isinstance(body, dict) else None)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=file.parent, delete=False) as tmp:
            json.dump({"url": url}, tmp)
            name = tmp.name
        try:
            os.replace(name, file)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return jsonify(url=url)

    @app.post("/api/workspace/comfyui/check")
    def comfyui_check():
        if request.remote_addr not in ("127.0.0.1", "::1"):
            return jsonify(error="Configure ComfyUI on the launcher PC"), 403
        if request.mimetype != "application/json" or not 0 < (request.content_length or 0) <= 1024:
            return jsonify(error="Invalid request"), 400
        try:
            return jsonify(probe(load()))
        except (OSError, ValueError):
            return jsonify(connected=False, error="Could not connect to ComfyUI"), 502
