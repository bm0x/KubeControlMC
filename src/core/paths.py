"""Resolución de directorios de datos escribibles (server_bin, configs).

En desarrollo los datos viven junto al código; en el paquete compilado
(PyInstaller onedir) /opt/kubecontrol-mc es propiedad de root, así que se
cae a ~/mcsm cuando el directorio del binario no es escribible.
"""

import os
import sys


def base_dir() -> str:
    if getattr(sys, "frozen", False):
        candidate = os.path.dirname(sys.executable)
    else:
        candidate = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    if os.access(candidate, os.W_OK):
        return candidate
    home = os.path.expanduser("~")
    mcsm = os.path.join(home, "mcsm")
    try:
        os.makedirs(mcsm, exist_ok=True)
        return mcsm
    except OSError:
        return candidate