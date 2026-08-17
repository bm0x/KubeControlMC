import os
import re
import platform
import subprocess
import shutil
import sys
import threading
import pty
import select
from typing import Callable, Optional

from src.core import http_client


class TunnelManager:
    # Pinned release that ships the SELF-CONTAINED playit agent (no IPC socket/daemon).
    # Since playit became a `playitd` daemon + CLI service (sockets under /run/playit),
    # the "latest" release no longer works when launched standalone by a normal user
    # (error: "IPC Error: Failed to bind to socket: No such file or directory").
    # v0.15.0 is still the build playit.gg links for manual Linux installs.
    PLAYIT_LEGACY_TAG = "v0.15.0"
    PLAYIT_AMD64_URL = f"https://github.com/playit-cloud/playit-agent/releases/download/{PLAYIT_LEGACY_TAG}/playit-linux-amd64"
    PLAYIT_AARCH64_URL = f"https://github.com/playit-cloud/playit-agent/releases/download/{PLAYIT_LEGACY_TAG}/playit-linux-aarch64"

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
        self._on_crash = None
        self._intentional_stop = False

    def set_callback(self, callback):
        self.callback = callback

    def set_crash_callback(self, callback):
        self._on_crash = callback

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text."""
        return self.ANSI_ESCAPE.sub('', text)

    def _read_pty_output(self):
        """Thread that reads output from the PTY master."""
        buffer = ""
        try:
            while not self._stop_reading and self._master_fd is not None:
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
                        data = os.read(self._master_fd, 1024)  # Read smaller chunks
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

                        # Escape brackets to prevent Rich markup errors
                        safe_line = line.replace("[", "\\[").replace("]", "\\]")

                        if self.callback:
                            if "https://" in line or "claim" in line.lower():
                                self.callback(f"[bold magenta]\\[TUNNEL] {safe_line}[/]")
                            elif "error" in line.lower() or "failed" in line.lower():
                                self.callback(f"[red]\\[TUNNEL] {safe_line}[/red]")
                            elif "started" in line.lower() or "ready" in line.lower() or "running" in line.lower():
                                self.callback(f"[green]\\[TUNNEL] {safe_line}[/green]")
                            else:
                                self.callback(f"[dim]\\[TUNNEL] {safe_line}[/dim]")
                except OSError:
                    # PTY closed
                    break

        except Exception as e:
            if self.callback and not self._stop_reading:
                self.callback(f"[red][TUNNEL ERROR] {e}[/red]")
        finally:
            # Notify crash handler only on unexpected exits (not intentional stops)
            if not self._intentional_stop and self._on_crash and not self._stop_reading:
                self._on_crash()

    async def start(self):
        self._intentional_stop = False

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

            # Set TERM to xterm to avoid complex cursor movements if possible
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
        self._intentional_stop = True
        self._stop_reading = True

        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
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
                except Exception:
                    pass
            self.process = None
            if self.callback:
                self.callback("[yellow]Túnel detenido.[/yellow]")

    def _is_playitd(self, bin_path: str) -> bool:
        """Detect the new 'playitd' daemon binary (needs systemd / IPC sockets).

        The legacy self-contained agent answers 'version'/'playit --version' with a
        plain version string, while the daemon identifies itself as 'playitd'.
        """
        try:
            out = subprocess.run(
                [bin_path, "--version"],
                capture_output=True,
                timeout=8
            )
            text = (out.stdout + out.stderr).decode("utf-8", errors="replace").lower()
            return "playitd" in text
        except Exception:
            # Can't inspect the binary; treat unknown as valid.
            return False

    def download_agent(self):
        # If a cached binary exists, keep it as long as it's the self-contained
        # (legacy) agent. The new playitd daemon MUST be replaced, otherwise it
        # fails to bind its socket at /run/playit for non-root users.
        if os.path.exists(self.agent_path):
            if not self._is_playitd(self.agent_path):
                return self.agent_path
            if self.callback:
                self.callback(
                    "[yellow]El binario guardado es 'playitd' (nuevo daemon de playit.gg) que "
                    "requiere un socket en /run/playit y no funciona en modo standalone. "
                    "Descargando el agente compatible...[/yellow]"
                )

        if self.callback:
            self.callback("[cyan]Descargando agente Playit.gg...[/cyan]")

        # macOS only: prefer an already-installed playit binary on the system.
        if sys.platform == "darwin":
            installed = self._find_playit_binary()
            if installed:
                try:
                    os.makedirs(os.path.dirname(self.agent_path), exist_ok=True)
                    shutil.copy(installed, self.agent_path)
                    os.chmod(self.agent_path, 0o755)
                    if self.callback:
                        self.callback(f"[green]Agente Playit.gg detectado en: {installed}[/green]")
                    return self.agent_path
                except Exception as e:
                    if self.callback:
                        self.callback(f"[yellow]No se pudo copiar playit desde {installed}: {e}[/yellow]")

        # Linux: download the self-contained agent (pinned version for non-service installs).
        if sys.platform.startswith("linux"):
            machine = platform.machine().lower()
            if machine in ("aarch64", "arm64"):
                url = self.PLAYIT_AARCH64_URL
            else:
                url = self.PLAYIT_AMD64_URL
            try:
                http_client.download(url, self.agent_path, timeout=120)
                os.chmod(self.agent_path, 0o755)
                if self.callback:
                    self.callback("[green]Agente Playit.gg descargado.[/green]")
                return self.agent_path
            except Exception as e:
                if self.callback:
                    self.callback(f"[red]Error descargando playit: {e}[/red]")
                raise e

        # macOS and other platforms: no official GitHub binary.
        if self.callback:
            self.callback(
                "[orange3]Playit.gg no publica binarios oficiales para macOS. "
                "Descárgalo desde https://playit.gg/download/macos e instálalo en el "
                "PATH (p.ej. /usr/local/bin/playit), o ejecuta: brew install playit[/orange3]"
            )
        raise FileNotFoundError("No se encontró el binario de playit para esta plataforma")

    def _find_playit_binary(self):
        """Locate an existing playit binary in common locations or on PATH."""
        if self.callback:
            self.callback("[dim]Buscando playit instalado en el sistema...[/dim]")
        candidates = [
            os.path.join(os.path.expanduser("~"), ".local", "bin", "playit"),
            "/usr/local/bin/playit",
            "/opt/homebrew/bin/playit",
            "/usr/bin/playit",
        ]
        found = shutil.which("playit")
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        if found and os.path.isfile(found) and os.access(found, os.X_OK):
            return found
        return None

    def reset_config(self):
        """Performs a full reset: Deletes config AND the binary to force update."""
        files_to_remove = [
            os.path.join(self.bin_dir, "playit.toml"),
            "playit.toml",
            self.agent_path  # Delete the binary itself
        ]

        deleted_any = False
        for f in files_to_remove:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    deleted_any = True
                except OSError:
                    pass

        if self.callback:
            if deleted_any:
                self.callback("[green]Agente y configuración eliminados. Se descargará la última versión.[/green]")
            else:
                self.callback("[dim]Nada que limpiar (Agente/Config no encontrados).[/dim]")

        return deleted_any