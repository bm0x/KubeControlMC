"""Perfil de rendimiento para hardware de bajos recursos (Raspberry Pi).

Detección automática de poca memoria (<= 1.5 GB), cálculo seguro de la RAM
recomendada para el servidor y flags JVM optimizados para la Pi 3B+.

Se puede forzar el modo con la variable de entorno KCMC_PI_MODE=1 o con el
flag `--pi` al lanzar la aplicación (lo gestiona main.py).
"""

import os

PI_MODE_ENV = "KCMC_PI_MODE"
LOW_MEMORY_THRESHOLD_MB = 1536


def is_pi_mode() -> bool:
    """True si se forzó el modo Pi o si el sistema tiene poca RAM."""
    return os.environ.get(PI_MODE_ENV) == "1" or get_total_ram_mb() < LOW_MEMORY_THRESHOLD_MB


def get_total_ram_mb() -> int:
    """RAM total en MB usando /proc/meminfo (Linux) o sysconf (macOS). 0 si no se puede."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    try:
        return (os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) // (1024 * 1024)
    except (ValueError, OSError):
        return 0


def get_available_ram_mb() -> int:
    """RAM libre disponible en MB (MemAvailable). 0 si no se puede leer."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def get_recommended_server_ram() -> str:
    """RAM recomendada (en MB) para el servidor de Minecraft.

    En modo Pi usa ~75% de la RAM libre, redondeada a múltiplos de 64 MB,
    limitada al rango [256M, 768M]. Nunca supera la RAM del sistema.
    """
    total = get_total_ram_mb()
    avail = get_available_ram_mb() or total
    if not avail:
        return "512M"

    target = int(avail * 0.75)
    target = (target // 64) * 64
    target = max(256, min(target, total - 128 if total > 256 else 512))

    if target >= 1024:
        return "1G"
    return f"{target}M"


def get_ram_options() -> list:
    """Opciones del selector de RAM según el perfil detectado."""
    if not is_pi_mode():
        return ["1G", "2G", "4G", "6G", "8G", "12G", "16G", "24G", "32G"]
    # Pi 3B+: nunca ofrecer más de 1G
    return ["256M", "512M", "768M", "1G"]


def _ram_mb(value: str) -> int:
    """Convierte '512M'/'1G' a MB."""
    v = value.strip().upper()
    if v.endswith("G"):
        return int(v[:-1]) * 1024
    if v.endswith("M"):
        return int(v[:-1])
    return int(v)


def get_default_ram() -> str:
    """RAM por defecto para el selector (la recomendada en modo Pi).

    Se ajusta hacia abajo a la opción disponible más cercana para que el
    valor sea siempre válido en el selector.
    """
    if not is_pi_mode():
        return "4G"
    recommended = _ram_mb(get_recommended_server_ram())
    options = get_ram_options()
    best = options[0]
    for opt in options:
        if _ram_mb(opt) <= recommended:
            best = opt
    # Prefiere la opción más cercana por arriba si hay margen (>32MB)
    for opt in options:
        if _ram_mb(opt) >= recommended and _ram_mb(opt) - recommended < 96:
            best = opt
    return best


def get_java_args(ram: str) -> list:
    """Args JVM para el servidor. En modo Pi usa SerialGC (ideal < 2 GB)."""
    args = [f"-Xms{ram}", f"-Xmx{ram}"]
    if is_pi_mode():
        args += [
            "-XX:+UseSerialGC",
            "-XX:MaxMetaspaceSize=128M",
            "-XX:+DisableExplicitGC",
            "-Dfile.encoding=UTF-8",
        ]
    return args


def get_optimization_preset() -> str:
    """Nombre del preset de optimización a usar ('pi' o 'aggressive')."""
    return "pi" if is_pi_mode() else "aggressive"
