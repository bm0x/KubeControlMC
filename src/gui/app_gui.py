import customtkinter as ctk
import os
import sys
import threading
import asyncio
import subprocess
import re
from tkinter import StringVar, END, messagebox
from tkinter import ttk
from PIL import Image

# Ensure sys.path includes our libs if running standalone
base_check = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists(os.path.join(base_check, "libs")):
    sys.path.insert(0, os.path.join(base_check, "libs"))

from src.core.server_controller import ServerController
from src.core.jar_manager import JarManager
from src.core.tunnel_manager import TunnelManager
from src.core.player_manager import PlayerManager
from src.core.plugin_manager import PluginManager
from src.core.config_manager import ConfigManager


class KubeControlGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Base directory setup ---
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        self.server_dir = os.path.join(self.base_dir, "server_bin")
        if not os.path.exists(self.server_dir):
            os.makedirs(self.server_dir)

        # --- Window Setup ---
        self.title("KubeControl MC")
        self.geometry("1200x750")
        
        # Load Icon
        icon_path = os.path.join(self.base_dir, "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                self.iconphoto(False, ctk.CTkImage(light_image=img, dark_image=img, size=(32,32))._light_image)
            except Exception:
                pass

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # --- Asyncio Background Loop ---
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._start_async_loop, daemon=True)
        self.loop_thread.start()

        # --- Core Components ---
        self.jar_manager = JarManager(download_dir=self.server_dir)
        self.plugin_manager = PluginManager(plugins_dir=os.path.join(self.server_dir, "plugins"))
        self.tunnel_manager = TunnelManager(bin_dir=self.server_dir)
        self.tunnel_manager.set_callback(self._tunnel_callback)
        self.player_manager = PlayerManager(server_path=self.server_dir)
        
        self.server_controller = None
        self.current_jar = None
        self.tunnel_retry_count = 0

        # --- UI Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._setup_sidebar()
        self._setup_main_area()
        
        # Initial status check loop
        self._check_status_periodic()

    def _start_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    # ========== SIDEBAR ==========
    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(15, weight=1)

        # Logo
        self.logo = ctk.CTkLabel(self.sidebar, text="KubeControl", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        self.subtitle = ctk.CTkLabel(self.sidebar, text="Minecraft Server Manager", font=ctk.CTkFont(size=10), text_color="gray")
        self.subtitle.grid(row=1, column=0, padx=20, pady=(0, 10))

        # Status
        self.status_label = ctk.CTkLabel(self.sidebar, text="● DETENIDO", text_color="red", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.grid(row=2, column=0, padx=20, pady=10)

        # Tunnel Box
        self.tunnel_frame = ctk.CTkFrame(self.sidebar, fg_color=("gray85", "gray20"), corner_radius=8)
        self.tunnel_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.tunnel_frame, text="Túnel de Red", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5,2))
        self.lbl_java = ctk.CTkLabel(self.tunnel_frame, text="Java: OFF", font=ctk.CTkFont(size=10))
        self.lbl_java.pack(pady=2)
        self.lbl_bedrock = ctk.CTkLabel(self.tunnel_frame, text="Bedrock: OFF", font=ctk.CTkFont(size=10))
        self.lbl_bedrock.pack(pady=(2,5))

        # RAM Select
        ctk.CTkLabel(self.sidebar, text="Memoria RAM:", anchor="w").grid(row=4, column=0, padx=20, pady=(15, 0))
        self.ram_var = StringVar(value="4G")
        self.ram_menu = ctk.CTkOptionMenu(self.sidebar, values=["2G", "4G", "6G", "8G", "12G", "16G", "24G", "32G"], variable=self.ram_var)
        self.ram_menu.grid(row=5, column=0, padx=20, pady=5)

        # Control Buttons
        self.btn_start = ctk.CTkButton(self.sidebar, text="▶ Iniciar", fg_color="green", hover_color="darkgreen", command=self.action_start)
        self.btn_start.grid(row=6, column=0, padx=20, pady=5)

        self.btn_stop = ctk.CTkButton(self.sidebar, text="⏹ Detener", fg_color="red", hover_color="darkred", command=self.action_stop, state="disabled")
        self.btn_stop.grid(row=7, column=0, padx=20, pady=5)
        
        self.btn_restart = ctk.CTkButton(self.sidebar, text="🔄 Reiniciar", fg_color="orange", hover_color="darkorange", command=self.action_restart, state="disabled")
        self.btn_restart.grid(row=8, column=0, padx=20, pady=5)

        # Tunnel
        self.btn_tunnel = ctk.CTkButton(self.sidebar, text="🌐 Iniciar Túnel", fg_color=("gray70", "gray30"), command=self.action_tunnel)
        self.btn_tunnel.grid(row=9, column=0, padx=20, pady=(15,5))

        # Exit
        self.btn_exit = ctk.CTkButton(self.sidebar, text="Salir", fg_color="gray", hover_color="gray40", command=self.action_exit)
        self.btn_exit.grid(row=16, column=0, padx=20, pady=10)

    # ========== MAIN AREA (TABS) ==========
    def _setup_main_area(self):
        self.tabview = ctk.CTkTabview(self, width=900)
        self.tabview.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Create Tabs
        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_console = self.tabview.add("Consola")
        self.tab_system = self.tabview.add("Sistema")

        self._setup_tab_dashboard()
        self._setup_tab_console()
        self._setup_tab_system()

    def _setup_tab_dashboard(self):
        # Left: Info | Right: Player List
        self.tab_dashboard.grid_columnconfigure(0, weight=1)
        self.tab_dashboard.grid_columnconfigure(1, weight=2)
        self.tab_dashboard.grid_rowconfigure(0, weight=1)

        # Left Panel
        left_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(left_frame, text="Estado del Servidor", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.info_frame = ctk.CTkFrame(left_frame)
        self.info_frame.pack(fill="x", padx=10, pady=5)
        
        self.lbl_jar = ctk.CTkLabel(self.info_frame, text="JAR: No seleccionado", anchor="w")
        self.lbl_jar.pack(fill="x", padx=10, pady=2)
        
        self.lbl_ram_info = ctk.CTkLabel(self.info_frame, text="RAM: --", anchor="w")
        self.lbl_ram_info.pack(fill="x", padx=10, pady=2)
        
        self.lbl_players_count = ctk.CTkLabel(self.info_frame, text="Jugadores: 0", anchor="w")
        self.lbl_players_count.pack(fill="x", padx=10, pady=2)

        # Right Panel: Player List
        right_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(right_frame, text="Jugadores en Línea", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Using ttk.Treeview for table (better for data)
        self.player_tree = ttk.Treeview(right_frame, columns=("name", "discord", "balance"), show="headings", height=15)
        self.player_tree.heading("name", text="Nombre")
        self.player_tree.heading("discord", text="Discord")
        self.player_tree.heading("balance", text="Balance")
        self.player_tree.column("name", width=150)
        self.player_tree.column("discord", width=120)
        self.player_tree.column("balance", width=80)
        self.player_tree.pack(fill="both", expand=True, padx=10)

        # Moderation Buttons
        mod_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        mod_frame.pack(fill="x", pady=10)
        
        self.btn_kick = ctk.CTkButton(mod_frame, text="🦵 Kick", fg_color="orange", command=self.action_kick, state="disabled", width=100)
        self.btn_kick.pack(side="left", padx=5)
        
        self.btn_ban = ctk.CTkButton(mod_frame, text="🔨 Ban", fg_color="red", command=self.action_ban, state="disabled", width=100)
        self.btn_ban.pack(side="left", padx=5)

        self.player_tree.bind("<<TreeviewSelect>>", self._on_player_select)

    def _setup_tab_console(self):
        self.tab_console.grid_rowconfigure(0, weight=1)
        self.tab_console.grid_columnconfigure(0, weight=1)

        # Console Log
        self.console_text = ctk.CTkTextbox(self.tab_console, font=("Consolas", 12), state="disabled")
        self.console_text.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Command Input
        self.cmd_entry = ctk.CTkEntry(self.tab_console, placeholder_text="Escribe un comando (/op, /gamemode, ...)...")
        self.cmd_entry.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")
        self.cmd_entry.bind("<Return>", self._send_command)

    def _setup_tab_system(self):
        self.tab_system.grid_columnconfigure(0, weight=3)
        self.tab_system.grid_columnconfigure(1, weight=1)
        self.tab_system.grid_rowconfigure(0, weight=1)

        # Left: System Log
        log_frame = ctk.CTkFrame(self.tab_system, fg_color="transparent")
        log_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(log_frame, text="Logs del Sistema", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        self.system_log = ctk.CTkTextbox(log_frame, font=("Consolas", 11), state="disabled")
        self.system_log.pack(fill="both", expand=True, padx=5, pady=5)

        # Right: Tools Sidebar
        tools_frame = ctk.CTkFrame(self.tab_system, fg_color=("gray90", "gray17"))
        tools_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(tools_frame, text="Herramientas", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)

        btn_cfg = {"width": 180, "height": 32}
        
        ctk.CTkButton(tools_frame, text="📦 Instalar/Actualizar", command=self.action_install, **btn_cfg).pack(pady=3)
        ctk.CTkButton(tools_frame, text="⚙️ Configuración", command=self.action_config, **btn_cfg).pack(pady=3)
        ctk.CTkButton(tools_frame, text="⚡ Optimizar", fg_color="orange", command=self.action_optimize, **btn_cfg).pack(pady=3)
        ctk.CTkButton(tools_frame, text="🔗 Geyser/Floodgate", command=self.action_geyser, **btn_cfg).pack(pady=3)
        
        ctk.CTkLabel(tools_frame, text="───── Túnel ─────", text_color="gray").pack(pady=5)
        ctk.CTkButton(tools_frame, text="♻️ Reinstalar Túnel", fg_color="gray", command=self.action_reset_tunnel, **btn_cfg).pack(pady=3)

        ctk.CTkLabel(tools_frame, text="───── Archivos ─────", text_color="gray").pack(pady=5)
        ctk.CTkButton(tools_frame, text="📂 Carpeta Server", command=lambda: self.open_folder(self.server_dir), **btn_cfg).pack(pady=3)
        ctk.CTkButton(tools_frame, text="📂 Plugins", command=lambda: self.open_folder(os.path.join(self.server_dir, "plugins")), **btn_cfg).pack(pady=3)
        ctk.CTkButton(tools_frame, text="📋 Copiar Logs", command=self.action_copy_logs, **btn_cfg).pack(pady=3)

        ctk.CTkLabel(tools_frame, text="───── App ─────", text_color="gray").pack(pady=5)
        ctk.CTkButton(tools_frame, text="🔄 Actualizar App", fg_color="teal", command=self.action_update_app, **btn_cfg).pack(pady=3)

    # ========== LOGGING ==========
    def _strip_markup(self, text):
        """Remove Rich console markup AND ANSI escape codes from text."""
        # 1. Strip ANSI escape codes (like \x1b[8m, \x1b[0m, etc)
        ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
        text = ansi_pattern.sub('', text)
        
        # 2. Strip Rich markup tags like [bold], [dim], [/], [cyan], etc.
        rich_pattern = re.compile(r'\[/?[a-zA-Z0-9_ ]*\]')
        text = rich_pattern.sub('', text)
        
        # 3. Clean any remaining weird characters (like standalone "8" from escape codes)
        text = re.sub(r'(?<!\d)8(?!\d)', '', text)  # Remove standalone "8" not part of numbers
        
        return text.strip()

    def log_console(self, text):
        """Append text to console tab."""
        clean_text = self._strip_markup(text)
        self.console_text.configure(state="normal")
        self.console_text.insert(END, clean_text + "\n")
        self.console_text.see(END)
        self.console_text.configure(state="disabled")

    def log_system(self, text):
        """Append text to system log."""
        clean_text = self._strip_markup(text)
        self.system_log.configure(state="normal")
        self.system_log.insert(END, clean_text + "\n")
        self.system_log.see(END)
        self.system_log.configure(state="disabled")

    def _tunnel_callback(self, message):
        """Handle tunnel messages."""
        self.after(0, lambda: self._process_tunnel_message(message))

    def _process_tunnel_message(self, message):
        self.log_system(f"[Tunnel] {message}")
        
        # Parse tunnel IPs
        if "=>" in message and ("ply.gg" in message or "tunnel" in message.lower()):
            try:
                parts = message.split("=>")
                if len(parts) >= 2:
                    public_addr = parts[0].strip().split()[-1]
                    local_addr = parts[1].strip()
                    
                    if ":25565" in local_addr:
                        self.lbl_java.configure(text=f"Java: {public_addr}", text_color="green")
                    elif ":19132" in local_addr:
                        self.lbl_bedrock.configure(text=f"Bedrock: {public_addr}", text_color="green")
            except:
                pass

    # ========== STATUS CHECK ==========
    def _check_status_periodic(self):
        if self.server_controller and self.server_controller.process:
            if self.server_controller.process.returncode is None:
                self.status_label.configure(text="● ONLINE", text_color="green")
                self.btn_start.configure(state="disabled")
                self.btn_stop.configure(state="normal")
                self.btn_restart.configure(state="normal")
            else:
                self._set_stopped_state()
        else:
            self._set_stopped_state()

        # Update JAR info
        jar = self.jar_manager.get_current_jar()
        if jar:
            self.lbl_jar.configure(text=f"JAR: {os.path.basename(jar)}")
            self.current_jar = jar
        
        self.lbl_ram_info.configure(text=f"RAM: {self.ram_var.get()}")
        
        self.after(1000, self._check_status_periodic)

    def _set_stopped_state(self):
        self.status_label.configure(text="● DETENIDO", text_color="red")
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_restart.configure(state="disabled")
        self.server_controller = None

    # ========== ACTIONS ==========
    def action_start(self):
        self.log_console("Iniciando servidor...")
        
        if not self.current_jar:
            self._show_install_dialog()
            return

        # Ensure EULA is accepted
        self.log_console("Configurando EULA...")
        ConfigManager.ensure_eula(self.server_dir)
        self.log_console("EULA aceptado automáticamente.")

        ram = self.ram_var.get()
        self.server_controller = ServerController(self.current_jar, java_args=[f"-Xms{ram}", f"-Xmx{ram}"])
        self.server_controller.set_callback(lambda msg: self.after(0, self.log_console, msg))
        
        asyncio.run_coroutine_threadsafe(self.server_controller.start(), self.loop)

    def _show_install_dialog(self):
        """Show dialog to select and download a server JAR."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Instalar Servidor")
        dialog.geometry("400x350")
        dialog.transient(self)
        
        # Fix for empty dialog - wait for window to be ready
        dialog.after(100, dialog.lift)
        dialog.after(100, dialog.focus_force)
        
        # Main container frame
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="Selecciona el tipo de servidor:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0,15))
        
        server_type = StringVar(value="paper")
        
        ctk.CTkRadioButton(main_frame, text="Paper (Recomendado - Estable)", variable=server_type, value="paper").pack(anchor="w", pady=5)
        ctk.CTkRadioButton(main_frame, text="Folia (Experimental - Multihilo)", variable=server_type, value="folia").pack(anchor="w", pady=5)
        ctk.CTkRadioButton(main_frame, text="Velocity (Proxy)", variable=server_type, value="velocity").pack(anchor="w", pady=5)
        
        ctk.CTkLabel(main_frame, text="Versión de Minecraft:").pack(pady=(20,5))
        version_var = StringVar(value="1.21.4")
        version_entry = ctk.CTkEntry(main_frame, textvariable=version_var, width=150)
        version_entry.pack()
        
        def do_install():
            stype = server_type.get()
            version = version_var.get()
            dialog.destroy()
            self.log_system(f"Descargando {stype} {version}...")
            
            def download_task():
                try:
                    jar_path = self.jar_manager.download_jar(stype, version)
                    self.after(0, lambda: self.log_system(f"JAR descargado: {os.path.basename(jar_path)}"))
                    self.current_jar = jar_path
                except Exception as e:
                    self.after(0, lambda: self.log_system(f"ERROR: {e}"))
            
            threading.Thread(target=download_task, daemon=True).start()
        
        ctk.CTkButton(main_frame, text="Descargar e Instalar", fg_color="green", hover_color="darkgreen", command=do_install, width=200).pack(pady=25)

    def action_stop(self):
        self.log_console("[GUI] Deteniendo servidor...")
        if self.server_controller:
            asyncio.run_coroutine_threadsafe(self.server_controller.stop(), self.loop)

    def action_restart(self):
        self.action_stop()
        self.after(5000, self.action_start)

    def action_tunnel(self):
        """Show tunnel configuration dialog and start tunnel."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Configurar Túnel")
        dialog.geometry("450x300")
        dialog.transient(self)
        dialog.after(100, dialog.lift)
        dialog.after(100, dialog.focus_force)
        
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="Túnel Playit.gg", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0,15))
        ctk.CTkLabel(main_frame, text="Playit.gg permite que jugadores se conecten\na tu servidor sin necesidad de abrir puertos.", text_color="gray").pack(pady=5)
        
        # Status
        self.tunnel_status_label = ctk.CTkLabel(main_frame, text="Estado: Desconectado", text_color="orange")
        self.tunnel_status_label.pack(pady=10)
        
        def start_tunnel():
            dialog.destroy()
            self.log_system("Iniciando túnel Playit.gg...")
            asyncio.run_coroutine_threadsafe(self.tunnel_manager.start(), self.loop)
        
        def stop_tunnel():
            self.log_system("Deteniendo túnel...")
            asyncio.run_coroutine_threadsafe(self.tunnel_manager.stop(), self.loop)
            dialog.destroy()
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="▶ Iniciar Túnel", fg_color="green", command=start_tunnel, width=150).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="⏹ Detener", fg_color="red", command=stop_tunnel, width=150).pack(side="left", padx=5)
        
        ctk.CTkLabel(main_frame, text="La primera vez deberás vincular tu cuenta\nen el enlace que aparecerá en los logs.", text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(10,0))

    def action_reset_tunnel(self):
        """Reinstall tunnel binary."""
        self.log_system("Reinstalando agente de túnel...")
        
        def reset_task():
            # Stop tunnel first
            asyncio.run_coroutine_threadsafe(self.tunnel_manager.stop(), self.loop).result()
            
            # Delete the binary
            playit_path = os.path.join(self.server_dir, "playit")
            if os.path.exists(playit_path):
                os.remove(playit_path)
                self.after(0, lambda: self.log_system("Agente eliminado."))
            
            # Trigger re-download on next start
            self.after(0, lambda: self.log_system("Reinstalación lista. Inicia el túnel para descargar el agente nuevo."))
        
        threading.Thread(target=reset_task, daemon=True).start()

    def action_exit(self):
        self.action_stop()
        asyncio.run_coroutine_threadsafe(self.tunnel_manager.stop(), self.loop)
        self.after(1000, self.quit)

    def action_install(self):
        self._show_install_dialog()

    def action_config(self):
        """Open server.properties editor dialog."""
        props_path = os.path.join(self.server_dir, "server.properties")
        if not os.path.exists(props_path):
            self.log_system("No existe server.properties. Inicia el servidor primero.")
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Configuración del Servidor")
        dialog.geometry("600x500")
        dialog.transient(self)
        dialog.after(100, dialog.lift)
        dialog.after(100, dialog.focus_force)
        
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(main_frame, text="server.properties", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0,10))
        
        # Scrollable frame for properties
        scroll_frame = ctk.CTkScrollableFrame(main_frame, height=350)
        scroll_frame.pack(fill="both", expand=True)
        
        # Load properties
        props = ConfigManager.get_all_properties(self.server_dir)
        entries = {}
        
        # Important properties first
        important = ["server-port", "motd", "max-players", "gamemode", "difficulty", "pvp", "online-mode",
                     "view-distance", "simulation-distance", "spawn-protection", "allow-flight"]
        
        for key in important:
            if key in props:
                row = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=key, width=200, anchor="w").pack(side="left", padx=5)
                entry = ctk.CTkEntry(row, width=200)
                entry.insert(0, props[key])
                entry.pack(side="right", padx=5)
                entries[key] = entry
        
        # Add separator
        ctk.CTkLabel(scroll_frame, text="─── Otras Opciones ───", text_color="gray").pack(pady=10)
        
        # Other properties
        for key, val in props.items():
            if key not in important:
                row = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=key, width=200, anchor="w").pack(side="left", padx=5)
                entry = ctk.CTkEntry(row, width=200)
                entry.insert(0, val)
                entry.pack(side="right", padx=5)
                entries[key] = entry
        
        def save_config():
            new_props = {k: e.get() for k, e in entries.items()}
            ConfigManager.save_all_properties(self.server_dir, new_props)
            self.log_system("Configuración guardada. Reinicia el servidor para aplicar cambios.")
            dialog.destroy()
        
        ctk.CTkButton(main_frame, text="Guardar", fg_color="green", command=save_config).pack(pady=15)

    def action_optimize(self):
        """Apply optimization settings to server."""
        self.log_system("Aplicando optimizaciones...")
        changes = ConfigManager.apply_aggressive_optimization(self.server_dir)
        for change in changes:
            self.log_system(f"  • {change}")
        self.log_system("Optimización completada. Reinicia el servidor para aplicar.")

    def action_geyser(self):
        """Show Geyser/Floodgate installation dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Instalar Geyser/Floodgate")
        dialog.geometry("450x350")
        dialog.transient(self)
        dialog.after(100, dialog.lift)
        dialog.after(100, dialog.focus_force)
        
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="Geyser & Floodgate", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0,10))
        ctk.CTkLabel(main_frame, text="Geyser permite que jugadores de Bedrock\nse conecten a tu servidor Java.", text_color="gray").pack(pady=5)
        ctk.CTkLabel(main_frame, text="Floodgate permite autenticación sin\ncuenta Java (usando cuenta Xbox).", text_color="gray").pack(pady=5)
        
        # Checkboxes
        install_geyser = ctk.BooleanVar(value=True)
        install_floodgate = ctk.BooleanVar(value=True)
        
        ctk.CTkCheckBox(main_frame, text="Instalar Geyser", variable=install_geyser).pack(pady=5, anchor="w")
        ctk.CTkCheckBox(main_frame, text="Instalar Floodgate", variable=install_floodgate).pack(pady=5, anchor="w")
        
        progress_label = ctk.CTkLabel(main_frame, text="", text_color="gray")
        progress_label.pack(pady=10)
        
        def do_install():
            dialog.destroy()
            
            def install_task():
                try:
                    if install_geyser.get():
                        self.after(0, lambda: self.log_system("Descargando Geyser-Spigot.jar..."))
                        path = self.plugin_manager.download_geyser()
                        self.after(0, lambda: self.log_system(f"Geyser instalado: {os.path.basename(path)}"))
                    
                    if install_floodgate.get():
                        self.after(0, lambda: self.log_system("Descargando Floodgate-Spigot.jar..."))
                        path = self.plugin_manager.download_floodgate()
                        self.after(0, lambda: self.log_system(f"Floodgate instalado: {os.path.basename(path)}"))
                    
                    self.after(0, lambda: self.log_system("Instalación completada. Reinicia el servidor para activar los plugins."))
                except Exception as e:
                    self.after(0, lambda: self.log_system(f"Error instalando: {e}"))
            
            threading.Thread(target=install_task, daemon=True).start()
        
        ctk.CTkButton(main_frame, text="Instalar Seleccionados", fg_color="green", command=do_install, width=200).pack(pady=20)
        ctk.CTkLabel(main_frame, text="Nota: Requiere reiniciar el servidor\npara activar los plugins.", text_color="gray", font=ctk.CTkFont(size=11)).pack()

    def action_copy_logs(self):
        try:
            import pyperclip
            text = self.console_text.get("1.0", END)
            pyperclip.copy(text)
            self.log_system("Logs copiados al portapapeles.")
        except:
            # Fallback: use xclip
            try:
                text = self.console_text.get("1.0", END)
                process = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                process.communicate(text.encode())
                self.log_system("Logs copiados al portapapeles.")
            except:
                self.log_system("Error copiando logs.")

    def action_update_app(self):
        if self.server_controller and self.server_controller.process and self.server_controller.process.returncode is None:
            self.log_system("Detén el servidor antes de actualizar.")
            return
        self.log_system("Buscando actualizaciones...")
        # TODO: Implement git pull or similar

    def open_folder(self, path):
        """Open folder in system file manager (not code editor)."""
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            # Try common file managers first, then fallback to xdg-open
            file_managers = ["io.elementary.files", "pantheon-files", "nautilus", "dolphin", "thunar", "nemo", "pcmanfm", "caja"]
            opened = False
            for fm in file_managers:
                try:
                    result = subprocess.run(["which", fm], capture_output=True)
                    if result.returncode == 0:
                        subprocess.Popen([fm, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                        opened = True
                        break
                except:
                    continue
            
            if not opened:
                # Fallback to gio open (preferred on GNOME/Elementary) or xdg-open
                try:
                    subprocess.Popen(["gio", "open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                except:
                    subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            
            self.log_system(f"Abriendo: {path}")
        except Exception as e:
            self.log_system(f"Error abriendo carpeta: {e}")

    def _send_command(self, event):
        cmd = self.cmd_entry.get()
        if cmd and self.server_controller:
            self.cmd_entry.delete(0, END)
            self.log_console(f"> {cmd}")
            asyncio.run_coroutine_threadsafe(self.server_controller.write(cmd), self.loop)

    def _on_player_select(self, event):
        selection = self.player_tree.selection()
        if selection:
            self.btn_kick.configure(state="normal")
            self.btn_ban.configure(state="normal")
        else:
            self.btn_kick.configure(state="disabled")
            self.btn_ban.configure(state="disabled")

    def action_kick(self):
        selection = self.player_tree.selection()
        if selection and self.server_controller:
            player = self.player_tree.item(selection[0])["values"][0]
            asyncio.run_coroutine_threadsafe(self.server_controller.write(f"kick {player}"), self.loop)
            self.log_console(f"[MOD] Kicked: {player}")

    def action_ban(self):
        selection = self.player_tree.selection()
        if selection and self.server_controller:
            player = self.player_tree.item(selection[0])["values"][0]
            asyncio.run_coroutine_threadsafe(self.server_controller.write(f"ban {player}"), self.loop)
            self.log_console(f"[MOD] Banned: {player}")


if __name__ == "__main__":
    app = KubeControlGUI()
    app.mainloop()
