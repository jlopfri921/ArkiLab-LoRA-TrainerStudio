"""Read-only GPU telemetry for the OrkiLab Workspace.

Uses NVIDIA's local nvidia-smi if available. Never starts/stops processes.
"""
import csv
import io
import math
import shutil
import subprocess
import time
import threading

_FIELDS = ("index", "name", "memory.total", "memory.used", "memory.free", "utilization.gpu", "temperature.gpu")
_CACHE_SECONDS = 3.0
_cache_lock = threading.Lock()
_cache_value = None
_cache_at = 0.0


def _num(value):
    value = value.strip()
    if value.lower() in ("n/a", "[not supported]", ""):
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) and number >= 0 else None


def get_gpu_metrics():
    global _cache_value, _cache_at
    with _cache_lock:
        now = time.monotonic()
        if _cache_value is not None and now - _cache_at < _CACHE_SECONDS:
            return _cache_value
        exe = shutil.which("nvidia-smi")
        if not exe:
            result = {"available": False, "reason": "NVIDIA monitoring tool not found", "gpus": []}
        else:
            try:
                completed = subprocess.run(
                    [exe, "--query-gpu=" + ",".join(_FIELDS), "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=5, check=False, shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if completed.returncode != 0 or len(completed.stdout) > 20000:
                    raise ValueError("GPU metrics not available")
                rows = list(csv.reader(io.StringIO(completed.stdout)))
                gpus = []
                for row in rows[:16]:
                    if len(row) != len(_FIELDS):
                        continue
                    index = _num(row[0])
                    if index is None or not index.is_integer():
                        continue
                    total, used, free, load, temp = map(_num, row[2:])
                    gpus.append({
                        "index": int(index),
                        "name": row[1].strip()[:150],
                        "vram_total_mib": total,
                        "vram_used_mib": used,
                        "vram_free_mib": free,
                        "utilization_percent": load,
                        "temperature_c": temp,
                    })
                result = {"available": bool(gpus), "reason": None if gpus else "GPU metrics not available", "gpus": gpus}
            except (OSError, ValueError, subprocess.TimeoutExpired):
                result = {"available": False, "reason": "GPU metrics not available", "gpus": []}
        _cache_value = result
        _cache_at = now
        return result
