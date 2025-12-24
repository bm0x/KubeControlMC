import sys
import os

# Add local libs directory to path for portability/restricted envs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

import asyncio
from src.tui.app import MCSMApp

def main():
    # Default to GUI unless --tui or --cli is specified
    if "--tui" in sys.argv or "--cli" in sys.argv:
         # UI Mode (Textual)
        app = MCSMApp()
        app.run()
    else:
        # Launch GUI Mode (Default)
        try:
            from src.gui.app_gui import KubeControlGUI
            print("🚀 Iniciando modo Gráfico (GUI)...")
            app = KubeControlGUI()
            app.mainloop()
        except ImportError as e:
            print(f"Error al cargar GUI: {e}")
            print("Asegúrate de instalar 'customtkinter'.")
            print("Fallback a TUI...")
            app = MCSMApp()
            app.run()
        except Exception as e:
            print(f"Crash GUI: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
