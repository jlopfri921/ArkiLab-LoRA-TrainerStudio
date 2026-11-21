"""Native local folder selector used by Dataset Studio.

The browser cannot expose absolute paths from <input webkitdirectory>; the
launcher therefore asks its own desktop OS to select a folder. This endpoint
is deliberately restricted to loopback requests.
"""
import os
import subprocess
import sys
import threading
from pathlib import Path

from flask import jsonify, request

_DIALOG_LOCK = threading.Lock()
_TIMEOUT_SECONDS = 120
_DIALOG_SCRIPT = r"""
import sys
try:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askdirectory(parent=root, mustexist=True, title="OrkiLab - Select image folder")
    if path:
        print(path)
    root.destroy()
except Exception as error:
    print(type(error).__name__ + ": " + str(error), file=sys.stderr)
    sys.exit(2)
"""


def select_folder():
    """Select only an existing local folder; never import/mutate by browsing."""
    if not _DIALOG_LOCK.acquire(blocking=False):
        return {"error": "A folder dialog is already open"}, 409
    try:
        if sys.platform != "win32" and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return {"error": "No desktop session available. Paste an absolute local folder path instead."}, 422
        try:
            child = subprocess.run(
                [sys.executable, "-c", _DIALOG_SCRIPT],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"error": "Native folder dialog unavailable or timed out. Paste a folder path instead."}, 503
        if child.returncode:
            return {"error": "The native folder selector could not open. Paste a folder path instead."}, 503
        selected = child.stdout.strip()
        if not selected:
            return {"cancelled": True}, 200
        path = Path(selected).expanduser()
        if not path.is_absolute() or not path.is_dir() or path.is_symlink():
            return {"error": "The selected folder is unavailable"}, 400
        return {"folder": str(path.resolve()), "cancelled": False}, 200
    finally:
        _DIALOG_LOCK.release()


def register(app, local, valid_origin):
    @app.post("/api/workspace/datasets/browse-folder")
    def browse_dataset_folder():
        if not local() or not valid_origin():
            return jsonify(error="Folder selection is available only on the launcher computer"), 403
        if request.content_length is not None and request.content_length > 1024:
            return jsonify(error="Invalid request size"), 413
        result, status = select_folder()
        return jsonify(result), status
