import os
import re
import requests
import subprocess
import threading
import pty
import select
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
        self._master_fd = None

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

    def _read_pty_output(self):
        """Thread that reads output from the PTY master."""
        buffer = ""
        try:
            while not self._stop_reading and self._master_fd is not None:
                # Use select to avoid blocking forever
                try:
                    ready, _, _ = select.select([self._master_fd], [], [], 0.1)
                    if not ready:
                        # If we have data in buffer containing a URL but no newline arrived for a while,
                        # imply a line break to ensure it gets shown (e.g. prompts)
                        if buffer and ("https://" in buffer or "claim" in buffer.lower()):
                             buffer += "\n"
                        else:
                            continue
                    
                    if ready:
                        data = os.read(self._master_fd, 1024) # Read smaller chunks
                        if not data:
                            break
                        
                        decoded = data.decode('utf-8', errors='replace')
                        # Normalize carriage returns to newlines to handle progress bars/prompts
                        decoded = decoded.replace('\r\n', '\n').replace('\r', '\n')
                        buffer += decoded
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = self._strip_ansi(line).strip()
                        
                        if not line:
                            continue
                        
                        if self.callback:
                            if "https://" in line or "claim" in line.lower():
                                self.callback(f"[bold magenta][TUNNEL] {line}[/]")
                            elif "error" in line.lower() or "failed" in line.lower():
                                self.callback(f"[red][TUNNEL] {line}[/red]")
                            elif "started" in line.lower() or "ready" in line.lower() or "running" in line.lower():
                                self.callback(f"[green][TUNNEL] {line}[/green]")
                            else:
                                self.callback(f"[dim][TUNNEL] {line}[/dim]")
                except OSError:
                    # PTY closed
                    break
                    
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
            self.callback("[cyan]Ejecutando Playit.gg con PTY...[/cyan]")
        
        try:
            # Create a pseudo-terminal to capture ALL output (including direct TTY writes)
            master_fd, slave_fd = pty.openpty()
            self._master_fd = master_fd
            
            # Set TERM to dumb or xterm to avoid complex cursor movements if possible
            env = os.environ.copy()
            env["TERM"] = "xterm"
            
            self.process = subprocess.Popen(
                [self.agent_path],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env=env
            )
            
            # Close slave in parent process
            os.close(slave_fd)
            
            if self.callback:
                self.callback(f"[green]Túnel iniciado con PID: {self.process.pid}[/green]")
            
            # Start reader thread
            self._stop_reading = False
            self._reader_thread = threading.Thread(target=self._read_pty_output, daemon=True)
            self._reader_thread.start()
        
        except Exception as e:
            if self.callback:
                self.callback(f"[red]Error al iniciar túnel: {e}[/red]")

    async def stop(self):
        self._stop_reading = True
        
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except:
                pass
            self._master_fd = None
        
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
