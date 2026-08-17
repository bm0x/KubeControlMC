import asyncio
import os
from typing import Callable, Optional

from src.core import pi_profile


class ServerController:
    def __init__(self, jar_path: str, java_args: list = None):
        self.jar_path = jar_path
        # Get the directory containing the JAR file - this is where we'll run the server
        self.working_dir = os.path.dirname(os.path.abspath(jar_path))
        self.java_args = java_args or ["-Xms1G", "-Xmx2G"]
        self.process: Optional[asyncio.subprocess.Process] = None
        self.output_callback: Optional[Callable[[str], None]] = None

    def set_callback(self, callback: Callable[[str], None]):
        self.output_callback = callback

    @staticmethod
    def _find_java_pids(jar_name: str) -> list:
        """Find Java PIDs running our JAR by scanning /proc (stdlib only).

        No depende de lsof/pgrep (no instalados por defecto en Debian mínimo).
        """
        pids = []
        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                try:
                    with open(f"/proc/{entry}/cmdline", "rb") as f:
                        cmdline = f.read().replace(b"\0", b" ").decode("utf-8", errors="replace")
                    if "java" in cmdline and jar_name in cmdline and "nogui" in cmdline:
                        pids.append(int(entry))
                except OSError:
                    continue
        except OSError:
            pass
        return pids

    def cleanup_zombie_processes(self):
        """Kill any existing Java processes using the same server JAR and remove session.lock."""
        session_lock = os.path.join(self.working_dir, "world", "session.lock")
        jar_name = os.path.basename(self.jar_path)

        for pid in self._find_java_pids(jar_name):
            try:
                if self.output_callback:
                    self.output_callback(f"[yellow]Terminando servidor anterior (PID: {pid})...[/yellow]")
                os.kill(int(pid), 9)  # SIGKILL
            except (ProcessLookupError, ValueError, PermissionError):
                pass

        # Remove session.lock if exists
        if os.path.exists(session_lock):
            try:
                os.remove(session_lock)
                if self.output_callback:
                    self.output_callback("[dim]session.lock eliminado.[/dim]")
            except Exception as e:
                if self.output_callback:
                    self.output_callback(f"[yellow]No se pudo eliminar session.lock: {str(e).replace('[', '\\\\[').replace(']', '\\\\]')}[/yellow]")

    async def start(self):
        if self.process and self.process.returncode is None:
            if self.output_callback:
                self.output_callback("Server is already running.")
            return

        # Clean up any zombie processes before starting
        self.cleanup_zombie_processes()

        # En modo Pi añade flags JVM optimizados si no vienen ya incluidos
        args = list(self.java_args)
        gc_flags = ("-XX:+UseSerialGC", "-XX:+UseG1GC", "-XX:+UseZGC", "-XX:+UseShenandoahGC")
        if pi_profile.is_pi_mode() and not any(flag in " ".join(args) for flag in gc_flags):
            xmx = next((a.split("=")[1] for a in args if a.startswith("-Xmx")), "512M")
            args = pi_profile.get_java_args(xmx)

        cmd = ["java"] + args + ["-jar", self.jar_path, "nogui"]

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir  # Run server in the JAR's directory
            )

            # Start monitoring output
            asyncio.create_task(self._read_stream(self.process.stdout))
            asyncio.create_task(self._read_stream(self.process.stderr, is_error=True))

            if self.output_callback:
                self.output_callback(f"Server started with PID: {self.process.pid}")

        except Exception as e:
            if self.output_callback:
                self.output_callback(f"Failed to start server: {e}")

    async def _read_stream(self, stream, is_error=False):
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode('utf-8', errors='replace').strip()
            if self.output_callback:
                prefix = "[ERR] " if is_error else ""
                self.output_callback(f"{prefix}{decoded}")

    async def write(self, command: str):
        if self.process and self.process.stdin:
            self.process.stdin.write(f"{command}\n".encode())
            await self.process.stdin.drain()
        else:
            if self.output_callback:
                self.output_callback("Server not running.")

    async def stop(self):
        if self.process and self.process.returncode is None:
            await self.write("stop")
            try:
                await asyncio.wait_for(self.process.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                if self.output_callback:
                    self.output_callback("Server stop timed out, killing process...")
                self.process.kill()
            if self.output_callback:
                self.output_callback("Server stopped.")