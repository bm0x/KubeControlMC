import asyncio
import os
import sys
import subprocess
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Label, Input, RichLog, Select, TabbedContent, TabPane, DataTable
from textual.containers import Container, Vertical, Horizontal
from textual.worker import Worker, WorkerState

from src.core.jar_manager import JarManager
from src.core.server_controller import ServerController
from src.core.player_manager import PlayerManager
from src.core.config_manager import ConfigManager
from src.core.resource_watcher import ResourceWatcher
from src.tui.screens.install import InstallScreen
from src.tui.screens.properties_editor import PropertiesEditorScreen

from src.core.plugin_manager import PluginManager
from src.core.tunnel_manager import TunnelManager

class MCSMApp(App):
    """KubeControlMC - Minecraft Server Manager"""
    TITLE = "KubeControlMC"
    CSS_PATH = "styles/app.tcss"
    
    def __init__(self):
        super().__init__()
        # Use absolute path relative to this script's location
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.server_dir = os.path.join(self.base_dir, "server_bin")
        
        self.jar_manager = JarManager(download_dir=self.server_dir)
        self.plugin_manager = PluginManager(plugins_dir=os.path.join(self.server_dir, "plugins"))
        self.tunnel_manager = TunnelManager(bin_dir=self.server_dir)
        self.tunnel_manager.set_callback(self.tunnel_callback_universal)
        self.tunnel_manager.set_crash_callback(self.on_tunnel_crash)
        
        self.tunnel_retry_count = 0
        
        self.server_controller = None
        self.resource_watcher = None
        self.player_manager = PlayerManager()
        self.current_jar = None
        self.project_type = None
    def compose(self) -> ComposeResult:
        yield Header()
        
        with TabbedContent(initial="tab-dashboard"):
            
            # --- TAB 1: DASHBOARD ---
            with TabPane("Dashboard", id="tab-dashboard"):
                yield Horizontal(
                    # Left: Status and Controls
                    Vertical(
                        Label("Estado del Servidor: DESCONOCIDO", id="status-label"),
                        # Tunnel Status (Dual Box)
                        Vertical(
                            Label("Java: Inactivo", id="tunnel-java"),
                            Label("Bedrock: Inactivo", id="tunnel-bedrock"),
                            id="tunnel-box"
                        ),
                        
                        # Controls
                        Label("Panel de Control", classes="section-title"),
                        Horizontal(
                             Select.from_values(
                                ["2G", "4G", "6G", "8G", "12G", "16G", "24G", "32G"],
                                value="4G",
                                id="ram-select",
                                allow_blank=False
                            ),
                             id="ram-area"
                        ),
                        Button("▶ Iniciar", id="btn-start", variant="success", disabled=True, classes="dash-btn"),
                        Button("⏹ Detener", id="btn-stop", variant="error", disabled=True, classes="dash-btn"),
                        Button("🔄 Reiniciar/Mant.", id="btn-restart", variant="warning", disabled=True, classes="dash-btn"),
                        
                        id="dashboard-left"
                    ),
                    
                    # Right: Player List
                    Vertical(
                        Label("[bold]Jugadores en Línea[/bold]", id="players-title"),
                        DataTable(id="player-list"),
                        id="dashboard-right"
                    ),
                    id="dashboard-container"
                )

            # --- TAB 2: CONSOLA SERVIDOR ---
            with TabPane("Consola Server", id="tab-console"):
                yield Vertical(
                    RichLog(id="server-log", markup=True, highlight=True, auto_scroll=True),
                    Input(placeholder="Comando de servidor (ej: /op, /stop)...", id="console-input", disabled=True),
                    id="server-console-area"
                )

            # --- TAB 3: SISTEMA Y HERRAMIENTAS ---
            with TabPane("Sistema", id="tab-system"):
                yield Horizontal(
                    # Left Panel: Logs
                    Vertical(
                        Label("[bold]Logs del Sistema & Túnel[/bold]"),
                        RichLog(id="system-log", markup=True, highlight=True, auto_scroll=True),
                        id="system-left-panel"
                    ),
                    # Right Sidebar: Tools
                    Vertical(
                        Label("[bold]Control & Herramientas[/bold]", classes="sidebar-header"),
                        Button("Instalar / Actualizar", id="btn-install", variant="primary", classes="sidebar-btn"),
                        Button("⚙️ Configuración", id="btn-config", variant="default", classes="sidebar-btn"),
                        Button("⚡ Optimizar", id="btn-optimize", variant="warning", classes="sidebar-btn"),
                        Button("Geyser/Floodgate", id="btn-geyser", variant="default", classes="sidebar-btn"),
                        Button("Iniciar Túnel", id="btn-tunnel", variant="default", classes="sidebar-btn"),
                        
                        Label("[dim]Archivos[/dim]", classes="sidebar-divider"),
                        Button("📂 Carpeta Server", id="btn-open-root", variant="default", classes="sidebar-btn"),
                        Button("📂 Plugins", id="btn-open-plugins", variant="default", classes="sidebar-btn"),
                        Button("📋 Copiar Logs", id="btn-copy-logs", variant="default", classes="sidebar-btn"),
                        
                        Label("[dim]App[/dim]", classes="sidebar-divider"),
                        Button("🔄 Actualizar App", id="btn-update-app", variant="warning", classes="sidebar-btn"),
                        Button("Salir", id="btn-exit", variant="error", classes="sidebar-btn"),
                        
                        id="system-sidebar"
                    ),
                    id="system-area"
                )
        
        yield Footer()

    # ... existing methods ...
    
    def on_tunnel_message(self, message: str) -> None:
        """Handle messages specifically from the tunnel manager."""
        clean_msg = message.replace("[TUNNEL]", "").strip()
        
        tunnel_box = self.query_one("#tunnel-box")
        lbl_java = self.query_one("#tunnel-java")
        lbl_bedrock = self.query_one("#tunnel-bedrock")
        
        if "https://" in message or "claim" in message.lower():
            # Link de Claim
            tunnel_box.display = True
            lbl_java.update(clean_msg) 
            lbl_java.styles.background = "magenta"
            lbl_bedrock.update("Esperando configuración...")
            self.log_write_universal(message)
            
        elif "=>" in message and (("ply.gg" in message) or ("tunnel" in message.lower())):
             # EXTRACT ADDRESS
             try:
                 parts = clean_msg.split("=>")
                 if len(parts) >= 2:
                     public_addr = parts[0].strip()
                     local_addr = parts[1].strip() # e.g. 127.0.0.1:25565
                     
                     if " " in public_addr:
                         public_addr = public_addr.split(" ")[-1]
                     
                     tunnel_box.display = True
                     
                     # Logic to distinguish Java vs Bedrock by LOCAL port
                     if ":25565" in local_addr:
                         lbl_java.update(f"Java: [bold]{public_addr}[/bold] (Copiado)")
                         lbl_java.styles.background = "green"
                         # Auto-copy Java IP
                         try:
                             process = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                             process.communicate(public_addr.encode())
                             self.log_write_universal(f"[green]IP Java copiada: {public_addr}[/green]")
                         except:
                             pass
                             
                     elif ":19132" in local_addr:
                         lbl_bedrock.update(f"Bedrock: [bold]{public_addr}[/bold]")
                         lbl_bedrock.styles.background = "green"
                     
                     else:
                         # Fallback if port is different or unknown
                         self.log_write_universal(f"[yellow]Túnel detectado en puerto no estándar: {local_addr}[/yellow]")
                         if "udp" in message.lower():
                             lbl_bedrock.update(f"Bedrock/UDP: [bold]{public_addr}[/bold]")
                             lbl_bedrock.styles.background = "green"
                         else:
                             lbl_java.update(f"Java/TCP: [bold]{public_addr}[/bold]")
                             lbl_java.styles.background = "green"
             except:
                 pass

        elif "tunnel running" in message.lower():
            tunnel_box.display = True
            # Don't overwrite if we already have specific info
            pass
        
        elif "stopped" in message.lower() or "detenido" in message.lower():
            tunnel_box.display = False
            lbl_java.update("Java: Inactivo")
            lbl_bedrock.update("Bedrock: Inactivo")
            lbl_java.styles.background = "secondary"
            lbl_bedrock.styles.background = "secondary"
        
        elif "error" in message.lower() or "failed" in message.lower():
             self.log_write_universal(message)
        
        # Log filtering
        if "error" in message.lower() or "claim" in message.lower() or "started" in message.lower() or "=>" in message:
            pass 
        else:
             pass

    def log_write_safe(self, message: str) -> None:
        """Callback for NON-async thread context only (uses call_from_thread)."""
        self.call_from_thread(self.log_write, message)

    def log_write_universal(self, message: str) -> None:
        """Smart callback that works from both async context and threads."""
        import threading
        if threading.current_thread() is threading.main_thread():
            try:
                self.log_write(message)
            except Exception:
                self.call_later(lambda: self.log_write(message))
        else:
            self.call_from_thread(self.log_write, message) 
            
    def tunnel_callback_universal(self, message: str):
        import threading
        if threading.current_thread() is threading.main_thread():
            self.on_tunnel_message(message)
        else:
            self.call_from_thread(self.on_tunnel_message, message)

    def on_tunnel_crash(self):
        self.call_from_thread(self._handle_crash_logic)

    async def _restart_tunnel_task(self):
         """Async task to actually restart the tunnel."""
         try:
             # Ensure clean stop first
             await self.tunnel_manager.stop()
             # Start again
             await self.tunnel_manager.start()
         except Exception as e:
             self.log_write_universal(f"[red]Error reiniciando túnel: {e}[/red]")

    def _handle_crash_logic(self):
        """UI logic for crash handling (Main Thread)."""
        self.tunnel_retry_count += 1
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s... max 60s
        delay = min(1.0 * (2 ** (self.tunnel_retry_count - 1)), 60)
        
        self.log_write_universal(f"[bold red]⚠️  Túnel interrumpido. Reintento #{self.tunnel_retry_count} en {int(delay)}s[/bold red]")
        
        tunnel_box = self.query_one("#tunnel-box")
        lbl_java = self.query_one("#tunnel-java")
        lbl_bedrock = self.query_one("#tunnel-bedrock")
        
        tunnel_box.display = True
        lbl_java.update(f"⚠️ Reintentando... ({int(delay)}s)")
        lbl_java.styles.background = "warning"
        lbl_bedrock.update(f"Intento #{self.tunnel_retry_count}")
        lbl_bedrock.styles.background = "error"
        
        self.set_timer(delay, self._restart_tunnel_task)

    def open_folder(self, folder: str):
        """Opens a folder in the system file manager (not code editor)."""
        path = os.path.abspath(folder)
        if not os.path.exists(path):
            os.makedirs(path)
            
        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", path])
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                # Try common file managers first, then fallback to xdg-open
                # io.elementary.files = Elementary OS, nautilus = GNOME, etc.
                file_managers = ["io.elementary.files", "pantheon-files", "nautilus", "dolphin", "thunar", "nemo", "pcmanfm", "caja"]
                opened = False
                for fm in file_managers:
                    try:
                        result = subprocess.run(["which", fm], capture_output=True)
                        if result.returncode == 0:
                            subprocess.Popen(
                                [fm, path],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                start_new_session=True
                            )
                            opened = True
                            break
                    except:
                        continue
                
                if not opened:
                    # Fallback to gio open or xdg-open
                    try:
                        subprocess.Popen(
                            ["gio", "open", path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                    except:
                        subprocess.Popen(
                            ["xdg-open", path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
            
            self.log_write(f"[blue]Abriendo carpeta:[/blue] {path}")
        except Exception as e:
            self.log_write(f"[red]Error abriendo carpeta: {e}[/red]")

    def copy_logs_to_clipboard(self):
        """Copy all log content to system clipboard."""
        try:
            # Determine which log is more relevant or copy server log by default
            log_widget = self.query_one("#server-log", RichLog)
            # Extract plain text from RichLog
            # RichLog.lines contains Strip objects with Segment children
            lines = []
            for strip in log_widget.lines:
                # Each Strip has segments, extract text from each
                line_text = ""
                if hasattr(strip, '_segments'):
                    for segment in strip._segments:
                        if hasattr(segment, 'text'):
                            line_text += segment.text
                elif hasattr(strip, 'plain'):
                    line_text = strip.plain
                else:
                    # Fallback: try to get text representation
                    try:
                        line_text = strip.text if hasattr(strip, 'text') else ""
                    except:
                        pass
                lines.append(line_text)
            
            log_text = "\n".join(lines)
            
            # Copy to clipboard using xclip or xsel
            try:
                process = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                process.communicate(log_text.encode())
            except FileNotFoundError:
                try:
                    process = subprocess.Popen(["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE)
                    process.communicate(log_text.encode())
                except FileNotFoundError:
                    # Fallback: save to a temp file
                    temp_file = "/tmp/kcmc_logs.txt"
                    with open(temp_file, "w") as f:
                        f.write(log_text)
                    self.log_write(f"[yellow]Logs guardados en:[/yellow] {temp_file}")
                    return
            
            self.log_write("[green]Logs del servidor copiados al portapapeles.[/green]")
        except Exception as e:
            self.log_write(f"[red]Error copiando logs: {e}[/red]")

    def update_app(self):
        """Update the application from GitHub and restart."""
        # Check active process - SAFE UPDATE
        if self.server_controller and self.server_controller.process and self.server_controller.process.returncode is None:
            self.log_write("[bold red]⛔ IMPOSIBLE ACTUALIZAR: SERVIDOR ACTIVO[/bold red]")
            self.log_write("[yellow]Por favor, detén el servidor antes de actualizar para garantizar la seguridad de tus datos.[/yellow]")
            return

        self.log_write("[cyan]🔄 Buscando actualizaciones...[/cyan]")
        
        def _do_update():
            try:
                # Run git pull in the base directory
                result = subprocess.run(
                    ["git", "pull", "origin", "main"],
                    cwd=self.base_dir,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if "Already up to date" in output or "Ya está actualizado" in output:
                        self.call_from_thread(self.log_write, "[green]✓ Ya tienes la última versión.[/green]")
                    else:
                        self.call_from_thread(self.log_write, f"[green]✓ Actualización descargada:[/green]\n{output}")
                        self.call_from_thread(self.log_write, "[bold yellow]⚠ Reiniciando aplicación en 3 segundos...[/bold yellow]")
                        
                        # Schedule restart
                        import time
                        time.sleep(3)
                        
                        # Restart by executing the launcher again
                        self.call_from_thread(self._restart_app)
                else:
                    self.call_from_thread(self.log_write, f"[red]Error en git pull: {result.stderr}[/red]")
                    
            except FileNotFoundError:
                self.call_from_thread(self.log_write, "[red]Git no está instalado. No se puede actualizar.[/red]")
            except Exception as e:
                self.call_from_thread(self.log_write, f"[red]Error actualizando: {e}[/red]")
        
        import threading
        threading.Thread(target=_do_update).start()

    def _restart_app(self):
        """Restart the application."""
        self.log_write("[dim]Reiniciando...[/dim]")
        # Exit current app and restart via launcher
        python = sys.executable
        os.execl(python, python, os.path.join(self.base_dir, "main.py"))

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

    def optimize_server_config(self):
        self.log_write("[cyan]Aplicando optimizaciones agresivas (Low-End PC)...[/cyan]")
        try:
            changes = ConfigManager.apply_aggressive_optimization(self.server_dir)
            if changes:
                for change in changes:
                    self.log_write(f"[green]✓ {change}[/green]")
                self.log_write("[bold yellow]Reinicia el servidor para aplicar cambios.[/bold yellow]")
            else:
                self.log_write("[dim]No se aplicaron cambios o archivos no encontrados.[/dim]")
        except Exception as e:
            self.log_write(f"[red]Error optimizando: {e}[/red]")

    def open_properties_editor(self):
        """Opens the properties editor modal."""
        if not os.path.exists(os.path.join(self.server_dir, "server.properties")):
            self.log_write("[yellow]No se encontró server.properties. Inicia el servidor al menos una vez.[/yellow]")
            return

        def editor_callback(result):
            if result:
                self.log_write("[green]✓ Configuración guardada correctamente.[/green]")
                if self.server_controller and self.server_controller.process:
                    self.log_write("[bold yellow]Algunos cambios requieren reiniciar el servidor.[/bold yellow]")
            elif result is False:
                 pass # Canceled or error handled inside
        
        self.push_screen(PropertiesEditorScreen(self.server_dir), editor_callback)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-install":
            self.open_install_screen()
        elif btn_id == "btn-config":
            self.open_properties_editor()
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
        elif btn_id == "btn-optimize":
            self.optimize_server_config()
        elif btn_id == "btn-open-root": # Added button handler
            self.open_folder(self.server_dir)
        elif btn_id == "btn-open-plugins": # Added button handler
            self.open_folder(os.path.join(self.server_dir, "plugins"))
        elif btn_id == "btn-copy-logs":
            self.copy_logs_to_clipboard()
        elif btn_id == "btn-update-app":
            self.update_app()
        elif btn_id == "btn-exit": # Added button handler
            self.exit()

    def log_write(self, message: str) -> None:
        """Write to the SYSTEM log widget."""
        try:
            log = self.query_one("#system-log", RichLog)
            log.write(message)
        except:
            pass
            
    def log_server(self, message: str) -> None:
        """Write to the SERVER CONSOLE log widget."""
        try:
            log = self.query_one("#server-log", RichLog)
            log.write(message)
            
            # Parse for Players
            if self.player_manager:
                try:
                    if self.player_manager.parse_log(message):
                        self.call_from_thread(self.update_player_list)
                except Exception:
                    pass
        except:
            pass

    def update_player_list(self):
        """Refreshes the player DataTable."""
        try:
            table = self.query_one("#player-list", DataTable)
            table.clear()
            
            players = self.player_manager.get_players()
            
            # Title update
            try:
                self.query_one("#players-title").update(f"[bold]Jugadores en Línea ({len(players)})[/bold]")
            except: 
                pass

            if not players:
                return
                
            for player, data in players.items():
                rank = data.get("rank", "User")
                # Style rank
                rank_styled = f"[bold red]{rank}[/]" if rank == "OP" else f"[dim]{rank}[/]"
                
                table.add_row(
                    player,
                    rank_styled, 
                    data.get("ping", "?")
                )
        except Exception:
             pass

    def on_mount(self) -> None:
        self.log_write("[bold green]Bienvenido a KubeControlMC[/]")
        self.log_write("[italic]Gestor de Servidores Minecraft Avanzado[/italic]")
        
        # Init Player Table
        try:
            table = self.query_one("#player-list", DataTable)
            table.add_columns("Jugador", "Rango", "Ping")
            table.cursor_type = "row"
        except:
            pass
            
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
        self.log_write("[dim]Toggle tunnel llamado...[/dim]")
        try:
            if self.tunnel_manager.process:
                self.log_write("[cyan]Deteniendo túnel...[/cyan]")
                asyncio.create_task(self.tunnel_manager.stop())
                self.query_one("#btn-tunnel").variant = "default"
                self.query_one("#btn-tunnel").label = "Iniciar Túnel"
            else:
                self.log_write("[cyan]Iniciando túnel Playit.gg...[/cyan]")
                asyncio.create_task(self.tunnel_manager.start())
                self.query_one("#btn-tunnel").variant = "warning"
                self.query_one("#btn-tunnel").label = "Detener Túnel"
        except Exception as e:
            self.log_write(f"[red]Error en toggle_tunnel: {e}[/red]")


    async def start_server(self):
        if not self.current_jar:
            return

        self.query_one("#btn-start").disabled = True
        self.query_one("#btn-install").disabled = True
        self.query_one("#btn-stop").disabled = False
        self.query_one("#btn-restart").disabled = False
        self.query_one("#console-input").disabled = False
        
        # Disable RAM selector
        ram_select = self.query_one("#ram-select")
        ram_select.disabled = True
        
        # Get RAM Value
        ram_val = ram_select.value
        # If blank for some reason, default to 4G
        if not ram_val:
            ram_val = "4G"
            
        self.query_one("#status-label").update(f"Estado: EJECUTANDO ({ram_val} RAM)")

        # Prepare arguments
        java_args = [f"-Xms{ram_val}", f"-Xmx{ram_val}"]
        self.log_write(f"[dim]Iniciando servidor con memoria: {ram_val}[/dim]") # System log
        
        # Initialize Controller
        self.server_controller = ServerController(self.current_jar, java_args=java_args)
        # Redirect Server Output to Console Tab
        self.server_controller.set_callback(self.log_server)
        
        # Resource Watcher - Write stats to System Log
        self.resource_watcher = ResourceWatcher(self.log_write)
        
        # Switch to Console Tab automatically? Optional
        # self.query_one(TabbedContent).active = "tab-console" 
        
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
            self.query_one("#ram-select").disabled = False # Re-enable RAM selector
            self.query_one("#status-label").update("Estado: DETENIDO")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.server_controller:
            cmd = event.value
            self.query_one("#console-input").value = ""
            self.log_server(f"[dim]> {cmd}[/dim]")
            await self.server_controller.write(cmd)

