import asyncio
import os
import requests
import subprocess
from typing import Callable, Optional

class TunnelManager:
    # GitHub releases URL for playit-agent
    PLAYIT_URL = "https://github.com/playit-cloud/playit-agent/releases/latest/download/playit-linux-amd64"
    # Note: This is for x86_64 Linux. For ARM use playit-linux-aarch64

    def __init__(self, bin_dir="server_bin"):
        self.bin_dir = bin_dir
        self.agent_path = os.path.join(bin_dir, "playit")
        self.process: Optional[asyncio.subprocess.Process] = None
        self.callback = None

    def set_callback(self, callback):
        self.callback = callback

    def download_agent(self):
        if os.path.exists(self.agent_path):
            return self.agent_path
        
        self.callback("Downloading Playit.gg agent...")
        try:
            with requests.get(self.PLAYIT_URL, stream=True) as r:
                r.raise_for_status()
                with open(self.agent_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            os.chmod(self.agent_path, 0o755)
            self.callback("Playit agent downloaded.")
            return self.agent_path
        except Exception as e:
            self.callback(f"Error downloading playit: {e}")
            raise e

    async def start(self):
        if self.callback:
            self.callback(f"[dim]Verificando agente en: {self.agent_path}[/dim]")
        
        if not os.path.exists(self.agent_path):
            try:
                self.download_agent()
            except Exception as e:
                if self.callback:
                    self.callback(f"[red]Error descargando agente: {e}[/red]")
                return

        if self.callback:
            self.callback("[cyan]Ejecutando Playit.gg...[/cyan]")
        
        try:
            # Playit runs interactively usually, but we run it to checking output
            self.process = await asyncio.create_subprocess_exec(
                self.agent_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            if self.callback:
                self.callback(f"[green]Túnel iniciado con PID: {self.process.pid}[/green]")
            asyncio.create_task(self._read_stream(self.process.stdout))
            asyncio.create_task(self._read_stream(self.process.stderr, is_error=True))
        
        except Exception as e:
            if self.callback:
                import traceback
                self.callback(f"[red]Error al iniciar túnel: {e}[/red]")

    async def _read_stream(self, stream, is_error=False):
        while True:
            line = await stream.readline()
            if not line:
                break
            try:
                decoded = line.decode('utf-8', errors='replace').strip()
                if not decoded:
                    continue
                    
                # Always show output, but format important lines specially
                if self.callback:
                    if "https://" in decoded or "claim" in decoded.lower():
                        # Important: claim URL or links
                        self.callback(f"[bold magenta][TUNNEL] {decoded}[/]")
                    elif "error" in decoded.lower() or "failed" in decoded.lower():
                        # Errors
                        self.callback(f"[red][TUNNEL] {decoded}[/red]")
                    elif "started" in decoded.lower() or "ready" in decoded.lower() or "connected" in decoded.lower():
                        # Success messages
                        self.callback(f"[green][TUNNEL] {decoded}[/green]")
                    else:
                        # Normal output
                        self.callback(f"[dim][TUNNEL] {decoded}[/dim]")
            except Exception as e:
                if self.callback:
                    self.callback(f"[red][TUNNEL ERROR] {e}[/red]")

    async def stop(self):
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except:
                self.process.kill()
            self.callback("Tunnel stopped.")
