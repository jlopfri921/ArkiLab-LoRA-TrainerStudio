"""Dependency-free, mocked tests for read-only GPU monitoring."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gpu_monitor


class GpuMonitorTests(unittest.TestCase):
    def setUp(self):
        gpu_monitor._cache_value = None
        gpu_monitor._cache_at = 0

    def test_nvidia_smi_unavailable(self):
        with patch.object(gpu_monitor.shutil, "which", return_value=None):
            data = gpu_monitor.get_gpu_metrics()
        self.assertFalse(data["available"])
        self.assertEqual(data["gpus"], [])

    def test_parses_gpu_metrics_and_caches(self):
        result = SimpleNamespace(returncode=0,
            stdout="0, NVIDIA RTX 3090, 24576, 4096, 20480, 45, 67\n")
        with patch.object(gpu_monitor.shutil, "which", return_value="nvidia-smi"):
            with patch.object(gpu_monitor.subprocess, "run", return_value=result) as run:
                first = gpu_monitor.get_gpu_metrics()
                again = gpu_monitor.get_gpu_metrics()
        self.assertTrue(first["available"])
        self.assertEqual(first["gpus"][0]["name"], "NVIDIA RTX 3090")
        self.assertEqual(first["gpus"][0]["vram_used_mib"], 4096)
        self.assertEqual(first["gpus"][0]["utilization_percent"], 45)
        self.assertEqual(first, again)
        run.assert_called_once()
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_handles_unsupported_temperature(self):
        result = SimpleNamespace(returncode=0,
            stdout="0, GPU, 12288, 1024, 11264, N/A, [Not Supported]\n")
        with patch.object(gpu_monitor.shutil, "which", return_value="nvidia-smi"):
            with patch.object(gpu_monitor.subprocess, "run", return_value=result):
                first = gpu_monitor.get_gpu_metrics()
        self.assertTrue(first["available"])
        self.assertIsNone(first["gpus"][0]["utilization_percent"])
        self.assertIsNone(first["gpus"][0]["temperature_c"])

    def test_timeout_does_not_raise(self):
        import subprocess
        with patch.object(gpu_monitor.shutil, "which", return_value="nvidia-smi"):
            with patch.object(gpu_monitor.subprocess, "run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 5)):
                data = gpu_monitor.get_gpu_metrics()
        self.assertFalse(data["available"])


if __name__ == "__main__":
    unittest.main()
