import customtkinter as ctk
import os
import sys
import threading
import asyncio
import signal
from tkinter import StringVar
from PIL import Image

# Ensure sys.path includes our libs if running standalone
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "libs"))

from src.core.server_controller import ServerController
from src.core.jar_manager import JarManager
from src.core.tunnel_manager import TunnelManager

class KubeControlGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Base directory setup ---
        # If running from binary (PyInstaller), sys.executable dir is base? No, sys._MEIPASS for temp, but we want CWD for data
        # Actually logic in main.py usually sets up paths.
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if getattr(sys, 'frozen', False):
            # PyInstaller mode: we might be in temp, but data should be relative to executable or user dir?
            # For now, stick to relative to CWD or executable location
            self.base_dir = os.path.dirname(sys.executable)
        
        self.server_dir = os.path.join(self.base_dir, "server_bin")
        if not os.path.exists(self.server_dir):
            os.makedirs(self.server_dir)

        # --- Window Setup ---
        self.title("KubeControl MC")
        self.geometry("1100x700")
        
        # Load Icon if exists
        icon_path = os.path.join(self.base_dir, "assets", "icon.png")
        if os.path.exists(icon_path):
            # For window icon (tkinter way)
            # iconphoto needs tk image. CTk doesn't have direct set_icon? wm_iconphoto works.
            try:
                img = Image.open(icon_path)
                self.iconphoto(False, ctk.CTkImage(light_image=img, dark_image=img, size=(32,32))._light_image) # Hacky for photoimage
            except Exception:
                pass

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # --- Asyncio Background Loop ---
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.start_async_loop, daemon=True)
        self.loop_thread.start()

        # --- Core Components ---
        self.jar_manager = JarManager(download_dir=self.server_dir)
        self.tunnel_manager = TunnelManager(bin_dir=self.server_dir)
        self.tunnel_manager.set_callback(self.update_tunnel_status_text)
        
        # Server Controller (Lazy init on start check or here?)
        # We need to know which JAR to use.
        self.server_controller = None

        # --- UI Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_main_area()
        
        # Initial status check
        self.check_status_periodic()

    def start_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="KubeControl", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Estado: DETENIDO", text_color="red")
        self.status_label.grid(row=1, column=0, padx=20, pady=10)

        # Tunnel Box
        self.tunnel_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent", border_width=1, border_color="gray")
        self.tunnel_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        self.lbl_tunnel_title = ctk.CTkLabel(self.tunnel_frame, text="Túnel (Red)", font=("Arial", 10, "bold"))
        self.lbl_tunnel_title.pack(pady=(2,0))
        
        self.lbl_java = ctk.CTkLabel(self.tunnel_frame, text="Java: OFF", font=("Arial", 12))
        self.lbl_java.pack(pady=2)
        self.lbl_bedrock = ctk.CTkLabel(self.tunnel_frame, text="Bedrock: OFF", font=("Arial", 12))
        self.lbl_bedrock.pack(pady=2)

        # Controls
        self.lbl_ram = ctk.CTkLabel(self.sidebar_frame, text="Memoria RAM:", anchor="w")
        self.lbl_ram.grid(row=3, column=0, padx=20, pady=(20, 0))
        
        self.ram_var = StringVar(value="4G")
        self.ram_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["2G", "4G", "6G", "8G", "12G", "16G"], variable=self.ram_var)
        self.ram_menu.grid(row=4, column=0, padx=20, pady=10)

        self.btn_start = ctk.CTkButton(self.sidebar_frame, text="▶ Iniciar", fg_color="green", command=self.action_start)
        self.btn_start.grid(row=5, column=0, padx=20, pady=10)

        self.btn_stop = ctk.CTkButton(self.sidebar_frame, text="⏹ Detener", fg_color="red", command=self.action_stop, state="disabled")
        self.btn_stop.grid(row=6, column=0, padx=20, pady=10)
        
        self.btn_restart = ctk.CTkButton(self.sidebar_frame, text="🔄 Reiniciar", fg_color="orange", command=self.action_restart, state="disabled")
        self.btn_restart.grid(row=7, column=0, padx=20, pady=10)

        # Exit
        self.btn_exit = ctk.CTkButton(self.sidebar_frame, text="Salir", fg_color="gray", command=self.action_exit)
        self.btn_exit.grid(row=9, column=0, padx=20, pady=10)

    def setup_main_area(self):
        self.tabview = ctk.CTkTabview(self, width=800)
        self.tabview.grid(row=0, column=1, padx=(10,10), pady=(10,10), sticky="nsew")
        
        self.tab_console = self.tabview.add("Consola")
        self.tab_dash = self.tabview.add("Dashboard")
        
        # -- Console --
        self.console_text = ctk.CTkTextbox(self.tab_console, width=800, height=500, font=("Consolas", 12))
        self.console_text.pack(expand=True, fill="both", padx=10, pady=10)
        self.console_text.configure(state="disabled") # Read only mostly

        self.cmd_entry = ctk.CTkEntry(self.tab_console, placeholder_text="Escribe un comando (/op, /stop...)")
        self.cmd_entry.pack(fill="x", padx=10, pady=(0, 10))
        self.cmd_entry.bind("<Return>", self.send_command)

        # -- Dashboard Info --
        self.lbl_welcome = ctk.CTkLabel(self.tab_dash, text="KubeControl Center", font=("Arial", 24))
        self.lbl_welcome.pack(pady=20)
        
        self.lbl_info = ctk.CTkLabel(self.tab_dash, text=f"Directorio: {self.server_dir}")
        self.lbl_info.pack()

    # --- Logic ---

    def append_console(self, text):
        clean_text = text.replace("[yellow]", "").replace("[/yellow]", "").replace("[dim]", "").replace("[/dim]", "").replace("[red]", "").replace("[/red]", "")
        self.console_text.configure(state="normal")
        self.console_text.insert("end", clean_text + "\n")
        self.console_text.see("end")
        self.console_text.configure(state="disabled")

    def update_tunnel_status_text(self, text):
        # Naive parsing of tunnel output if possible, mostly just logging for now
        # Ideally tunnel manager would expose status flags
        self.append_console(f"[Tunnel] {text}")
        if "Java:" in text:
             # Try to update labels if format matches "Java: IP:PORT"
             pass # Implement better parsing later

    def check_status_periodic(self):
        # Update server status
        if self.server_controller and self.server_controller.process:
            if self.server_controller.process.returncode is None:
                self.status_label.configure(text="Estado: ONLINE", text_color="green")
                self.btn_start.configure(state="disabled")
                self.btn_stop.configure(state="normal")
                self.btn_restart.configure(state="normal")
            else:
                self.status_label.configure(text="Estado: DETENIDO", text_color="red")
                self.btn_start.configure(state="normal")
                self.btn_stop.configure(state="disabled")
                self.btn_restart.configure(state="disabled")
                self.server_controller = None # Reset
        else:
             self.status_label.configure(text="Estado: DETENIDO", text_color="red")
             self.btn_start.configure(state="normal")
             self.btn_stop.configure(state="disabled")
             self.btn_restart.configure(state="disabled")

        self.after(1000, self.check_status_periodic)

    def action_start(self):
        self.append_console("[GUI] Iniciando servidor...")
        
        # 1. Check Jar
        current_jar = self.jar_manager.get_current_jar()
        if not current_jar:
            self.append_console("[GUI] Error: No hay JAR seleccionado. Descargando última versión...")
            # Ideally show a dialog or auto-download. For now auto-download paper in thread
            def download_task():
                self.jar_manager.download_jar("paper", "1.21.1") # Hardcoded for simplicity in Phase 10
                self.after(100, self.action_start) # Retry
            threading.Thread(target=download_task).start()
            return

        # 2. Start
        if not self.server_controller:
            ram = self.ram_var.get()
            self.server_controller = ServerController(current_jar, java_args=[f"-Xms{ram}", f"-Xmx{ram}"])
            self.server_controller.set_callback(lambda msg: self.after(0, self.append_console, msg))
            
        asyncio.run_coroutine_threadsafe(self.server_controller.start(), self.loop)
        
        # 3. Start Tunnel
        asyncio.run_coroutine_threadsafe(self.tunnel_manager.start_tunnel(), self.loop)


    def action_stop(self):
        self.append_console("[GUI] Deteniendo servidor...")
        if self.server_controller:
            asyncio.run_coroutine_threadsafe(self.server_controller.stop(), self.loop)
        
        asyncio.run_coroutine_threadsafe(self.tunnel_manager.stop_tunnel(), self.loop)

    def action_restart(self):
        self.action_stop()
        # Naive restart: wait and start? Better to have a restart method in controller or chain logic
        self.after(5000, self.action_start)

    def action_exit(self):
        self.action_stop()
        self.quit()

    def send_command(self, event):
        cmd = self.cmd_entry.get()
        if cmd and self.server_controller:
            self.cmd_entry.delete(0, "end")
            self.append_console(f"> {cmd}")
            asyncio.run_coroutine_threadsafe(self.server_controller.write(cmd), self.loop)

if __name__ == "__main__":
    app = KubeControlGUI()
    app.mainloop()
