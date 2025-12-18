import asyncio
import subprocess
import os
from typing import Callable, Optional

class ServerController:
    def __init__(self, jar_path: str, java_args: list[str] = None):
        self.jar_path = jar_path
        # Get the directory containing the JAR file - this is where we'll run the server
        self.working_dir = os.path.dirname(os.path.abspath(jar_path))
        self.java_args = java_args or ["-Xms1G", "-Xmx2G"]
        self.process: Optional[asyncio.subprocess.Process] = None
        self.output_callback: Optional[Callable[[str], None]] = None

    def set_callback(self, callback: Callable[[str], None]):
        self.output_callback = callback

    def cleanup_zombie_processes(self):
        """Kill any existing Java processes using the same server directory and remove session.lock."""
        session_lock = os.path.join(self.working_dir, "world", "session.lock")
        
        # Try to find and kill Java processes running in our working directory
        try:
            # Use lsof to find processes with session.lock open
            result = subprocess.run(
                ["lsof", "-t", session_lock],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        if self.output_callback:
                            self.output_callback(f"[yellow]Terminando proceso zombie (PID: {pid})...[/yellow]")
                        os.kill(int(pid), 9)  # SIGKILL
                    except (ProcessLookupError, ValueError):
                        pass
        except FileNotFoundError:
            # lsof not available, try alternative approach
            pass
        
        # Also try to find Java processes with our JAR in their command line
        try:
            jar_name = os.path.basename(self.jar_path)
            result = subprocess.run(
                ["pgrep", "-f", jar_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        if self.output_callback:
                            self.output_callback(f"[yellow]Terminando servidor anterior (PID: {pid})...[/yellow]")
                        os.kill(int(pid), 9)
                    except (ProcessLookupError, ValueError):
                        pass
        except FileNotFoundError:
            pass
        
        # Remove session.lock if exists
        if os.path.exists(session_lock):
            try:
                os.remove(session_lock)
                if self.output_callback:
                    self.output_callback("[dim]session.lock eliminado.[/dim]")
            except Exception as e:
                if self.output_callback:
                    self.output_callback(f"[yellow]No se pudo eliminar session.lock: {e}[/yellow]")

    async def start(self):
        if self.process and self.process.returncode is None:
            if self.output_callback:
                self.output_callback("Server is already running.")
            return

        # Clean up any zombie processes before starting
        self.cleanup_zombie_processes()

        cmd = ["java"] + self.java_args + ["-jar", self.jar_path, "nogui"]
        
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
