import asyncio
import os
from typing import Callable, Optional

from src.core import pi_profile


class ResourceWatcher:
    """Monitor de recursos basado únicamente en la stdlib (/proc).

    Lee /proc/meminfo y /proc/<pid>/status directamente, sin psutil,
    para minimizar la huella de memoria en la Raspberry Pi.
    """

    def __init__(self, callback: Callable[[str], None], threshold_percent: Optional[float] = None,
                 interval: float = 10.0):
        self.running = False
        self.callback = callback
        # Umbral adaptado: 85% en modo Pi (poca RAM), 90% en escritorio
        self.threshold_percent = threshold_percent or (85.0 if pi_profile.is_pi_mode() else 90.0)
        self.interval = interval
        self.server_pid: Optional[int] = None
        self._task = None
        self._mem_alerted = False
        self._rss_alerted = False

    def start(self, pid: int):
        self.server_pid = pid
        self.running = True
        self._task = asyncio.create_task(self._watch_loop())

    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()

    @staticmethod
    def _mem_percent() -> Optional[float]:
        """Porcentaje de RAM en uso. None si no se puede leer."""
        total = avail = None
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        avail = int(line.split()[1])
                    if total and avail:
                        break
        except OSError:
            return None
        if not total or not avail:
            return None
        return 100.0 * (total - avail) / total

    @staticmethod
    def _proc_rss_mb(pid: int) -> Optional[int]:
        """RSS (MB) del proceso. None si el proceso no existe."""
        try:
            with open(f"/proc/{pid}/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) // 1024
        except OSError:
            return None
        return None

    async def _watch_loop(self):
        while self.running:
            try:
                # System Memory (con histéresis: alerta solo al cruzar el umbral)
                mem = self._mem_percent()
                if mem is not None:
                    if mem > self.threshold_percent and not self._mem_alerted:
                        self._mem_alerted = True
                        self.callback(f"[bold red][ALERT] System RAM critical: {mem:.0f}%[/]")
                        self.callback("[yellow]Triggering emergency optimization...[/]")
                    elif mem <= self.threshold_percent - 5:
                        self._mem_alerted = False

                # Server Process Memory
                if self.server_pid:
                    rss = self._proc_rss_mb(self.server_pid)
                    if rss is None:
                        # Process is gone: stop watching
                        self.running = False
                        break
                    if rss > 1024 and not self._rss_alerted:
                        self._rss_alerted = True
                        self.callback(f"[yellow][WARN] Server RAM: {rss} MB[/]")
                    elif rss <= 900:
                        self._rss_alerted = False

                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.callback(f"[error]Watcher error: {e}[/]")
                await asyncio.sleep(self.interval)