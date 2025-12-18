import asyncio
import os
import re
import requests
import subprocess
import threading
from typing import Callable, Optional

class TunnelManager:
    # GitHub releases URL for playit-agent
    PLAYIT_URL = "https://github.com/playit-cloud/playit-agent/releases/latest/download/playit-linux-amd64"
    # Note: This is for x86_64 Linux. For ARM use playit-linux-aarch64
    
    # Regex to strip ANSI escape codes
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def __init__(self, bin_dir="server_bin"):
        self.bin_dir = bin_dir
        self.agent_path = os.path.join(bin_dir, "playit")
        self.process: Optional[subprocess.Popen] = None
        self.callback = None
        self._reader_thread = None
        self._stop_reading = False

    def set_callback(self, callback):
        self.callback = callback

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text."""
        return self.ANSI_ESCAPE.sub('', text)

    def download_agent(self):
        if os.path.exists(self.agent_path):
            return self.agent_path
        
        if self.callback:
            self.callback("[cyan]Descargando agente Playit.gg...[/cyan]")
        try:
            with requests.get(self.PLAYIT_URL, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(self.agent_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            os.chmod(self.agent_path, 0o755)
            if self.callback:
                self.callback("[green]Agente Playit.gg descargado.[/green]")
            return self.agent_path
        except Exception as e:
            if self.callback:
                self.callback(f"[red]Error descargando playit: {e}[/red]")
            raise e

    def _read_output(self):
        """Thread that reads output from the process."""
        try:
            while not self._stop_reading and self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    continue
                    
                decoded = line.decode('utf-8', errors='replace').strip()
                decoded = self._strip_ansi(decoded)
                
                if not decoded:
                    continue
                
                if self.callback:
                    if "https://" in decoded or "claim" in decoded.lower():
                        self.callback(f"[bold magenta][TUNNEL] {decoded}[/]")
                    elif "error" in decoded.lower() or "failed" in decoded.lower():
                        self.callback(f"[red][TUNNEL] {decoded}[/red]")
                    elif "started" in decoded.lower() or "ready" in decoded.lower() or "running" in decoded.lower():
                        self.callback(f"[green][TUNNEL] {decoded}[/green]")
                    else:
                        self.callback(f"[dim][TUNNEL] {decoded}[/dim]")
        except Exception as e:
            if self.callback and not self._stop_reading:
                self.callback(f"[red][TUNNEL ERROR] {e}[/red]")

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
            # Use subprocess.Popen with line-buffered output
            # Set PYTHONUNBUFFERED and use stdbuf to force line buffering
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            self.process = subprocess.Popen(
                ["stdbuf", "-oL", "-eL", self.agent_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                env=env
            )
            
            if self.callback:
                self.callback(f"[green]Túnel iniciado con PID: {self.process.pid}[/green]")
            
            # Start reader thread
            self._stop_reading = False
            self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self._reader_thread.start()
        
        except FileNotFoundError:
            # stdbuf not available, try without it
            if self.callback:
                self.callback("[yellow]stdbuf no disponible, usando modo básico...[/yellow]")
            try:
                self.process = subprocess.Popen(
                    [self.agent_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1
                )
                if self.callback:
                    self.callback(f"[green]Túnel iniciado con PID: {self.process.pid}[/green]")
                
                self._stop_reading = False
                self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
                self._reader_thread.start()
            except Exception as e:
                if self.callback:
                    self.callback(f"[red]Error al iniciar túnel: {e}[/red]")
        except Exception as e:
            if self.callback:
                self.callback(f"[red]Error al iniciar túnel: {e}[/red]")

    async def stop(self):
        self._stop_reading = True
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception:
                try:
                    self.process.kill()
                except:
                    pass
            self.process = None
            if self.callback:
                self.callback("[yellow]Túnel detenido.[/yellow]")
