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
# Optional metrics are isolated: older GPUs may lack individual sensors.
_EXTRA_FIELDS = ("index", "uuid", "pci.bus_id", "driver_version", "pstate",
                 "utilization.memory", "power.draw", "power.limit", "fan.speed",
                 "clocks.current.graphics", "clocks.current.memory")
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
                if gpus:
                    # Fetch extra telemetry separately so older drivers never
                    # lose the basic VRAM/load/temperature overview.
                    try:
                        extra = subprocess.run(
                            [exe, "--query-gpu=" + ",".join(_EXTRA_FIELDS),
                             "--format=csv,noheader,nounits"],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=5, check=False, shell=False,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                        if extra.returncode == 0 and len(extra.stdout) <= 20000:
                            by_index = {gpu["index"]: gpu for gpu in gpus}
                            names = {
                                "uuid": "uuid", "pci.bus_id": "pci_bus_id",
                                "driver_version": "driver_version", "pstate": "performance_state",
                                "utilization.memory": "memory_utilization_percent",
                                "power.draw": "power_draw_w", "power.limit": "power_limit_w",
                                "fan.speed": "fan_percent",
                                "clocks.current.graphics": "graphics_clock_mhz",
                                "clocks.current.memory": "memory_clock_mhz",
                            }
                            for values in list(csv.reader(io.StringIO(extra.stdout)))[:16]:
                                if len(values) != len(_EXTRA_FIELDS):
                                    continue
                                idx = _num(values[0])
                                if idx is None or not idx.is_integer() or int(idx) not in by_index:
                                    continue
                                gpu = by_index[int(idx)]
                                for label, val in zip(_EXTRA_FIELDS[1:], values[1:]):
                                    key = names[label]
                                    gpu[key] = val.strip()[:100] if label in (
                                        "uuid", "pci.bus_id", "driver_version", "pstate"
                                    ) else _num(val)
                    except (OSError, ValueError, subprocess.TimeoutExpired):
                        pass
                result = {"available": bool(gpus), "reason": None if gpus else "GPU metrics not available", "gpus": gpus}
            except (OSError, ValueError, subprocess.TimeoutExpired):
                result = {"available": False, "reason": "GPU metrics not available", "gpus": []}
        _cache_value = result
        _cache_at = now
        return result
