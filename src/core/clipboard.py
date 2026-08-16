"""Portapapeles sin dependencias externas (sin pyperclip).

Soporta macOS (pbcopy), Windows (clip) y Linux (wl-copy para Wayland,
xclip/xsel para X11). Devuelve False si no hay ninguna herramienta
disponible, para que el llamador decida qué hacer.
"""

import subprocess
import sys


def _run(cmd: list, text: str) -> bool:
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        proc.communicate(text.encode())
        return proc.returncode == 0
    except (OSError, FileNotFoundError):
        return False


def copy_text(text: str) -> bool:
    """Copia texto al portapapeles. True si se pudo copiar."""
    if sys.platform == "darwin":
        return _run(["pbcopy"], text)
    if sys.platform == "win32":
        return _run(["clip"], text)
    # Linux: Wayland primero (wl-copy), luego X11
    for tool, args in (("wl-copy", []),
                       ("xclip", ["-selection", "clipboard"]),
                       ("xsel", ["--clipboard", "--input"])):
        if _run([tool] + args, text):
            return True
    return False