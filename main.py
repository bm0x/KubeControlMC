import sys
import os

# Add local libs directory to path for portability/restricted envs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

import asyncio  # noqa: E402

def _configure_pi_mode():
    """Activa el modo Raspberry Pi si se pasa --pi o se detecta poca RAM.

    Se establece la variable de entorno ANTES de importar los módulos de la
    app para que pi_profile la lea al cargarse.
    """
    if "--pi" in sys.argv:
        os.environ["KCMC_PI_MODE"] = "1"
        sys.argv.remove("--pi")
        return True
    try:
        from src.core.pi_profile import is_pi_mode
        if is_pi_mode():
            os.environ["KCMC_PI_MODE"] = "1"
            return True
    except ImportError:
        pass
    return False

def main():
    pi_mode = _configure_pi_mode()
    force_gui = "--gui" in sys.argv
    if force_gui:
        sys.argv.remove("--gui")

    # Default to GUI unless --tui/--cli, or Pi mode (headless: TUI)
    if (not force_gui) and ("--tui" in sys.argv or "--cli" in sys.argv or pi_mode):
        if pi_mode and "--tui" not in sys.argv and "--cli" not in sys.argv:
            print("🫐 Modo Raspberry Pi detectado — se inicia TUI por defecto.")
            print("💡 Usa 'kcmc --gui' si tienes escritorio (cuesta más RAM).")
        # UI Mode (Textual) — se importa solo aquí (lazy) para no cargar
        # textual/rich en modo GUI
        from src.tui.app import MCSMApp
        app = MCSMApp()
        app.run()
    else:
        # Launch GUI Mode (Default) — import lazy para que el modo TUI
        # no cargue tkinter/customtkinter/PIL
        try:
            from src.gui.app_gui import KubeControlGUI
            if pi_mode:
                print("🫐 Modo Raspberry Pi detectado.")
            print("🚀 Iniciando modo Gráfico (GUI)...")
            app = KubeControlGUI()
            app.mainloop()
        except ImportError as e:
            print(f"Error al cargar GUI: {e}")
            print("Asegúrate de instalar 'customtkinter'.")
            print("Fallback a TUI...")
            from src.tui.app import MCSMApp
            app = MCSMApp()
            app.run()
        except Exception as e:
            print(f"Crash GUI: {e}")
            print("Fallback a TUI...")
            from src.tui.app import MCSMApp
            app = MCSMApp()
            app.run()

if __name__ == "__main__":
    main()
