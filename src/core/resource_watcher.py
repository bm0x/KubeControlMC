import asyncio
import psutil
import time
from typing import Callable, Optional

class ResourceWatcher:
    def __init__(self, callback: Callable[[str], None], threshold_percent=90.0):
        self.running = False
        self.callback = callback
        self.threshold_percent = threshold_percent
        self.server_pid: Optional[int] = None
        self._task = None

    def start(self, pid: int):
        self.server_pid = pid
        self.running = True
        self._task = asyncio.create_task(self._watch_loop())

    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()

    async def _watch_loop(self):
        while self.running:
            try:
                # System Memory
                mem_info = psutil.virtual_memory()
                if mem_info.percent > self.threshold_percent:
                    self.callback(f"[bold red][ALERT] System RAM critical: {mem_info.percent}%[/]")
                    # Trigger optimization logic here (placeholder)
                    self.callback("[yellow]Triggering emergency optimization...[/]")
                
                # Server Process Memory
                if self.server_pid:
                    try:
                        proc = psutil.Process(self.server_pid)
                        proc_mem = proc.memory_info().rss / 1024 / 1024 # MB
                        # self.callback(f"[dim]Server RAM: {proc_mem:.1f} MB[/]")
                    except psutil.NoSuchProcess:
                        self.running = False
                        break
                
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.callback(f"[error]Watcher error: {e}[/]")
                await asyncio.sleep(5)
