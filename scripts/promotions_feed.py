"""Read-only, centrally editable OrkiLab promotions. No telemetry or third-party scripts."""
import json
import threading
import time
import urllib.request
from urllib.parse import urlparse

from flask import jsonify

FEED_URL = ("https://raw.githubusercontent.com/jlopfri921/"
            "OrkiLab-LoRA-TrainerStudio/main/GUI/promotions.json")
ALLOWED_REPOS = {"/jlopfri921/OrkiLab-LoRA-TrainerStudio", "/jlopfri921/orkicad-ai"}
CACHE_SECONDS = 6 * 3600
MAX_BYTES = 16384
_cached = {"until": 0, "items": []}
_lock = threading.Lock()


def _text(value, length):
    return value[:length].strip() if isinstance(value, str) else ""


def _validate(payload):
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Unsupported promotions manifest")
    if not isinstance(payload.get("items"), list):
        raise ValueError("Invalid promotions list")
    accepted = []
    for item in payload["items"][:8]:
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        url = item.get("url")
        if not isinstance(url, str):
            continue
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if (parsed.scheme != "https" or parsed.username or parsed.password
                or parsed.port not in (None, 443)
                or host != "github.com" or parsed.path.rstrip("/").lower() not in {p.lower() for p in ALLOWED_REPOS}
                or parsed.query or parsed.fragment):
            continue
        titles = item.get("title") if isinstance(item.get("title"), dict) else {}
        descriptions = item.get("description") if isinstance(item.get("description"), dict) else {}
        title = {str(k)[:8]: _text(v, 90) for k, v in titles.items() if _text(v, 90)}
        description = {str(k)[:8]: _text(v, 180) for k, v in descriptions.items() if _text(v, 180)}
        if not title.get("en") and not title.get("es"):
            continue
        accepted.append({"id": _text(item.get("id"), 40), "title": title,
                         "description": description, "url": url})
    return accepted


def register(app):
    @app.get("/api/workspace/promotions")
    def promotions():
        # The server fetches one fixed owner-controlled file, never a client URL.
        # No client identifiers are forwarded to the remote source.
        now = time.monotonic()
        with _lock:
            if now >= _cached["until"]:
                try:
                    req = urllib.request.Request(
                        FEED_URL, headers={"User-Agent": "OrkiLab-Promotions/1.0",
                                           "Accept": "application/json"})
                    with urllib.request.urlopen(req, timeout=3) as response:
                        if response.status != 200:
                            raise ValueError("Promotion fetch failed")
                        raw = response.read(MAX_BYTES + 1)
                        if len(raw) > MAX_BYTES:
                            raise ValueError("Promotion manifest too large")
                    _cached["items"] = _validate(json.loads(raw.decode("utf-8")))
                    _cached["until"] = time.monotonic() + CACHE_SECONDS
                except (OSError, ValueError, UnicodeError, TypeError):
                    # Keep last known-good promotions; retry later, without blocking UI.
                    _cached["until"] = time.monotonic() + 600
            items = list(_cached["items"])
        response = jsonify({"items": items})
        response.headers["Cache-Control"] = "private, max-age=300"
        return response
