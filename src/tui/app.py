import asyncio
import os
import sys
import subprocess
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Label, Input, RichLog
from textual.containers import Container, Vertical, Horizontal
from textual.worker import Worker, WorkerState

from src.core.jar_manager import JarManager
from src.core.server_controller import ServerController
from src.core.config_manager import ConfigManager
from src.core.resource_watcher import ResourceWatcher
from src.tui.screens.install import InstallScreen

from src.core.plugin_manager import PluginManager
from src.core.tunnel_manager import TunnelManager

class MCSMApp(App):
    """KubeControlMC - Minecraft Server Manager"""
    TITLE = "KubeControlMC"
    CSS_PATH = "styles/app.tcss"
    # ... previous imports ...
    
    def __init__(self):
        super().__init__()
        # Use absolute path relative to this script's location
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.server_dir = os.path.join(self.base_dir, "server_bin")
        
        self.jar_manager = JarManager(download_dir=self.server_dir)
        self.plugin_manager = PluginManager(plugins_dir=os.path.join(self.server_dir, "plugins"))
        self.tunnel_manager = TunnelManager()
        self.tunnel_manager.set_callback(self.log_write_safe)
        
        self.server_controller = None
        self.resource_watcher = None
        self.current_jar = None
        self.project_type = None

    # ... compose ...
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Label("Estado del Servidor: DESCONOCIDO", id="status-label"),
                RichLog(id="console-log", markup=True, highlight=True),
                Input(placeholder="Escribe un comando...", id="console-input", disabled=True),
                id="console-area"
            ),
            # Extra Tools
            Horizontal(
                Button("Instalar Geyser/Floodgate", id="btn-geyser", variant="default"),
                Button("Iniciar Túnel (Playit)", id="btn-tunnel", variant="default"),
                Button("Abrir Carpeta Server", id="btn-open-root", variant="default"),
                Button("Abrir Plugins", id="btn-open-plugins", variant="default"),
                id="tools-area",
                classes="tools-box"
            ),
            Horizontal(
                Button("Instalar / Actualizar", id="btn-install", variant="primary"),
                Button("Iniciar", id="btn-start", variant="success", disabled=True),
                Button("Detener", id="btn-stop", variant="error", disabled=True),
                Button("Mantenimiento / Reinicio", id="btn-restart", variant="warning", disabled=True),
                Button("Salir App", id="btn-exit", variant="error"),
                id="controls-area"
            ),
            id="main-container"
        )
        yield Footer()

    # ... existing methods ...
    
    def log_write_safe(self, message: str) -> None:
        """Callback suitable for non-async context or threads, schedules update."""
        self.call_from_thread(self.log_write, message)

    def open_folder(self, folder: str):
        """Opens a folder in the system file manager."""
        path = os.path.abspath(folder)
        if not os.path.exists(path):
            os.makedirs(path)
            
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
            self.log_write(f"[blue]Abriendo carpeta:[/blue] {path}")
        except Exception as e:
            self.log_write(f"[red]Error abriendo carpeta: {e}[/red]")

    async def safe_restart(self):
        """Performs a safe restart sequence."""
        if not self.server_controller or not self.server_controller.process:
            self.log_write_safe("[yellow]El servidor no está activo. Iniciando normalmente...[/yellow]")
            await self.start_server()
            return

        self.log_write("[bold orange]ACTIVANDO MODO MANTENIMIENTO...[/bold orange]")
        # 1. Whitelist on
        await self.server_controller.write("whitelist on")
        
        # 2. Kick players
        await self.server_controller.write("kick @a §cServidor en Mantenimiento. Volvemos en unos segundos.")
        
        # 3. Save
        await self.server_controller.write("save-all")
        await asyncio.sleep(2)
        
        # 4. Stop
        await self.stop_server()
        
        self.log_write("[bold orange]Esperando 5 segundos para reiniciar...[/bold orange]")
        await asyncio.sleep(5)
        
        # 5. Start
        await self.start_server()
        
        # 6. Wait for startup (simple delay for now, better would be parsing output)
        # Assuming server takes some time, we can tell user to disable whitelist manually or do it after delay
        # For safety/simplicity, we leave whitelist ON so admin can verify before letting people in.
        self.log_write("[bold green]¡Servidor Reiniciado! La whitelist sigue activa por seguridad.[/bold green]")
        self.log_write("[dim]Escribe 'whitelist off' cuando estés listo.[/dim]")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-install":
            self.open_install_screen()
        elif btn_id == "btn-start":
            await self.start_server()
        elif btn_id == "btn-stop":
            await self.stop_server()
        elif btn_id == "btn-restart":
            await self.safe_restart() # Modified to call safe_restart
        elif btn_id == "btn-geyser":
            self.install_geyser()
        elif btn_id == "btn-tunnel":
            self.toggle_tunnel()
        elif btn_id == "btn-open-root": # Added button handler
            self.open_folder(self.server_dir)
        elif btn_id == "btn-open-plugins": # Added button handler
            self.open_folder(os.path.join(self.server_dir, "plugins"))
        elif btn_id == "btn-exit": # Added button handler
            self.exit()

    def log_write(self, message: str) -> None:
        """Write to the console log widget with Rich markup support."""
        log = self.query_one("#console-log", RichLog)
        log.write(message)

    def on_mount(self) -> None:
        self.log_write("[bold green]Bienvenido a KubeControlMC[/]")
        self.log_write("[italic]Gestor de Servidores Minecraft Avanzado[/italic]")
        self.check_installation()

    def check_installation(self):
        # Simple check: look for any .jar in server_bin
        if not os.path.exists(self.server_dir):
            os.makedirs(self.server_dir)
            
        jars = [f for f in os.listdir(self.server_dir) if f.endswith(".jar")]
        if jars:
            self.current_jar = os.path.join(self.server_dir, jars[0])
            self.log_write(f"[blue]Detectado JAR:[/blue] {jars[0]}")
            self.query_one("#btn-start").disabled = False
            self.query_one("#btn-install").label = "Actualizar/Cambiar"
            self.query_one("#status-label").update("Estado: LISTO PARA INICIAR")
        else:
            self.log_write("[yellow]No se detectó ningún servidor instalado.[/yellow]")
            self.open_install_screen()

    def open_install_screen(self):
        """Opens the install modal. Guards against being called multiple times."""
        # Prevent opening multiple times
        if hasattr(self, '_install_screen_open') and self._install_screen_open:
            self.log_write("[dim]Pantalla de instalación ya abierta.[/dim]")
            return
        
        self._install_screen_open = True
        
        def install_callback(project_type):
            self._install_screen_open = False
            self.log_write(f"[dim]Callback recibido: {project_type} (tipo: {type(project_type).__name__})[/dim]")
            
            # Validate the result
            if project_type and isinstance(project_type, str) and project_type in ("paper", "folia", "velocity"):
                self.install_server(project_type)
            else:
                self.log_write("[yellow]Instalación cancelada o selección inválida.[/yellow]")
        
        self.push_screen(InstallScreen(), install_callback)

    def install_server(self, project: str):
        self.log_write(f"[cyan]Iniciando descarga de {project}...[/cyan]")
        self.project_type = project
        
        # Run in a thread - pass a lambda to ensure method is called correctly
        def do_work():
            return self._do_install_sync()
        
        self.run_worker(do_work, exclusive=True, thread=True)

    def _do_install_sync(self):
        """Synchronous installation worker (runs in thread)."""
        self.call_from_thread(self.log_write, "[dim]Worker iniciado...[/dim]")
        try:
            project = self.project_type
            self.call_from_thread(self.log_write, f"[dim]Buscando versiones para: {project}[/dim]")
            
            version = self.jar_manager.get_latest_version(project)
            if not version:
                raise Exception(f"No se encontraron versiones para '{project}'")
            
            self.call_from_thread(self.log_write, f"Versión más reciente: {version}")
            
            self.call_from_thread(self.log_write, "[dim]Iniciando descarga...[/dim]")
            path = self.jar_manager.download_jar(project, version)
            
            self.current_jar = path
            self.call_from_thread(self.log_write, f"[green]Descarga completada:[/green] {path}")
            
            # Ensure EULA
            self.call_from_thread(self.log_write, "[dim]Configurando EULA...[/dim]")
            ConfigManager.ensure_eula(self.server_dir)
            self.call_from_thread(self.log_write, "EULA aceptado automáticamente.")
            
            return True  # Signal success
            
        except Exception as e:
            import traceback
            self.call_from_thread(self.log_write, f"[bold red]Error en instalación:[/bold red] {e}")
            self.call_from_thread(self.log_write, f"[dim]{traceback.format_exc()}[/dim]")
            return False

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            if self.current_jar:
                self.query_one("#btn-start").disabled = False
                self.query_one("#status-label").update("Estado: INSTALADO")
                self.log_write("[green]¡Instalación lista! Presiona Iniciar.[/green]")

    def install_geyser(self):
        self.log_write("[cyan]Instalando Geyser y Floodgate...[/cyan]")
        def _do_install():
            try:
                g = self.plugin_manager.download_geyser()
                f = self.plugin_manager.download_floodgate()
                self.log_write_safe(f"[green]Instalado:[/green] {os.path.basename(g)}")
                self.log_write_safe(f"[green]Instalado:[/green] {os.path.basename(f)}")
                self.log_write_safe("[bold]Reinicia el servidor para aplicar cambios.[/bold]")
            except Exception as e:
                self.log_write_safe(f"[red]Error instalando plugins: {e}[/red]")
        
        import threading
        threading.Thread(target=_do_install).start()

    def toggle_tunnel(self):
        if self.tunnel_manager.process:
            asyncio.create_task(self.tunnel_manager.stop())
            self.query_one("#btn-tunnel").variant = "default"
            self.query_one("#btn-tunnel").label = "Iniciar Túnel"
        else:
            asyncio.create_task(self.tunnel_manager.start())
            self.query_one("#btn-tunnel").variant = "warning"
            self.query_one("#btn-tunnel").label = "Detener Túnel"


    async def start_server(self):
        if not self.current_jar:
            return

        self.query_one("#btn-start").disabled = True
        self.query_one("#btn-install").disabled = True
        self.query_one("#btn-stop").disabled = False
        self.query_one("#btn-restart").disabled = False
        self.query_one("#console-input").disabled = False
        self.query_one("#status-label").update("Estado: EJECUTANDO")

        self.server_controller = ServerController(self.current_jar)
        self.server_controller.set_callback(self.log_write)
        
        # Resource Watcher
        self.resource_watcher = ResourceWatcher(self.log_write)
        
        await self.server_controller.start()
        
        if self.server_controller.process:
            self.resource_watcher.start(self.server_controller.process.pid)

    async def stop_server(self):
        if self.server_controller:
            self.query_one("#status-label").update("Estado: DETENIENDO...")
            if self.resource_watcher:
                self.resource_watcher.stop()
            
            await self.server_controller.stop()
            
            self.query_one("#btn-start").disabled = False
            self.query_one("#btn-install").disabled = False
            self.query_one("#btn-stop").disabled = True
            self.query_one("#btn-restart").disabled = True
            self.query_one("#console-input").disabled = True
            self.query_one("#status-label").update("Estado: DETENIDO")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.server_controller:
            cmd = event.value
            self.query_one("#console-input").value = ""
            self.log_write(f"[dim]> {cmd}[/dim]")
            await self.server_controller.write(cmd)

