"""Cliente HTTP minimalista basado únicamente en la stdlib.

Reemplaza a `requests`/`aiohttp` para reducir drásticamente la huella de
memoria y el tiempo de arranque en hardware de bajos recursos (Pi 3B+).
Incluye reintentos con backoff, ideal para redes WiFi inestables.
"""

import json
import os
import time
import urllib.error
import urllib.request

USER_AGENT = "KubeControlMC/1.0 (https://github.com/bm0x/KubeControlMC)"


class HTTPError(Exception):
    """Error de red o respuesta HTTP no satisfactoria."""


def _open(url: str, timeout: float, retries: int, headers: dict):
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, OSError) as e:
            last_error = e
            if attempt < retries:
                time.sleep(min(1.0 * (2 ** attempt), 4.0))
    raise HTTPError(str(last_error)) from last_error


def get_json(url: str, timeout: float = 30, retries: int = 2) -> dict:
    """GET y parsea JSON con timeout y reintentos."""
    data = _open(url, timeout, retries, {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPError(f"JSON inválido desde {url}: {e}") from e


def download(url: str, dest: str, timeout: float = 60, retries: int = 2,
             chunk_size: int = 65536) -> str:
    """Descarga en streaming a `dest`. Borra el archivo parcial si falla."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
            return dest
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, OSError) as e:
            last_error = e
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass
            if attempt < retries:
                time.sleep(min(1.0 * (2 ** attempt), 4.0))
    raise HTTPError(f"Descarga fallida: {last_error}") from last_error