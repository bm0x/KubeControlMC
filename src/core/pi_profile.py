"""Perfil de rendimiento dinámico para hardware ARM / Raspberry Pi.

Detección inteligente del dispositivo al arrancar:
  - Raspberry Pi real (modelo exacto vía /proc/device-tree/model)
  - Cualquier ARM (aarch64/armv7) con poca RAM
  - Cualquier dispositivo con < 1.5 GB de RAM

Ajusta dinámicamente: techo de RAM para el servidor, opciones del selector,
flags JVM (SerialGC para heaps <= 1G, G1GC tuneado para heaps mayores) y
preset de optimización de configuraciones.

Se puede forzar con la variable KCMC_PI_MODE=1 o el flag `--pi`.
"""

import os
import platform

PI_MODE_ENV = "KCMC_PI_MODE"
LOW_MEMORY_THRESHOLD_MB = 1536


# ---------------------------------------------------------------------------
# Detección de hardware
# ---------------------------------------------------------------------------

def get_hardware_model() -> str:
    """Modelo exacto del dispositivo (ej: 'Raspberry Pi 3 Model B Plus Rev 1.3')."""
    try:
        with open("/proc/device-tree/model", "rb") as f:
            model = f.read().rstrip(b"\0").decode("utf-8", errors="replace").strip()
            if model:
                return model
    except OSError:
        pass
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Hardware"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def is_raspberry_pi() -> bool:
    """True si el dispositivo es una Raspberry Pi (Linux)."""
    if not sys_platform_is_linux():
        return False
    return "raspberry pi" in get_hardware_model().lower()


def _is_arm() -> bool:
    machine = platform.machine().lower()
    return machine in ("aarch64", "arm64", "armv6l", "armv7l", "armv8l") or "arm" in machine


def sys_platform_is_linux() -> bool:
    return platform.system().lower() in ("linux",)


def is_pi_mode() -> bool:
    """Modo optimizado: forzado, Raspberry Pi, ARM con poca RAM o < 1.5 GB totales.

    Nota: Apple Silicon (aarch64 en macOS) NO entra en modo Pi.
    """
    if os.environ.get(PI_MODE_ENV) == "1":
        return True
    if is_raspberry_pi():
        return True
    total = get_total_ram_mb()
    if sys_platform_is_linux() and _is_arm() and 0 < total < 2048:
        return True
    return 0 < total < LOW_MEMORY_THRESHOLD_MB


# ---------------------------------------------------------------------------
# Memoria
# ---------------------------------------------------------------------------

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


def _ram_cap_mb() -> int:
    """Techo de RAM para el servidor según el hardware detectado.

    Pi 3B+/1GB  -> 768 MB   (deja ~140 MB al sistema)
    Pi 4/2GB    -> 1.5 GB
    Pi 4/4GB    -> 3 GB
    Pi 5/8GB    -> 6 GB
    Otros       -> 75% de la RAM total
    """
    total = get_total_ram_mb()
    if is_raspberry_pi():
        if total <= 1024:
            return 768
        if total <= 2048:
            return 1536
        if total <= 4096:
            return 3072
        return min(total - 1024, 6144)
    return max(int(total * 0.75), 0)


def get_recommended_server_ram() -> str:
    """RAM recomendada: ~75% de la RAM libre, múltiplos de 64 MB, con techo por hardware."""
    total = get_total_ram_mb()
    avail = get_available_ram_mb() or total
    if not avail:
        return "512M"

    cap = _ram_cap_mb()
    target = int(avail * 0.75)
    target = (target // 64) * 64
    target = max(256, min(target, cap))

    if target >= 1024:
        return f"{target // 1024}G" if target % 1024 == 0 else f"{target}M"
    return f"{target}M"


def _ram_mb(value: str) -> int:
    """Convierte '512M'/'1G' a MB."""
    v = value.strip().upper()
    if v.endswith("G"):
        return int(v[:-1]) * 1024
    if v.endswith("M"):
        return int(v[:-1])
    return int(v)


def get_ram_options() -> list:
    """Opciones del selector de RAM, dinámicas según el hardware.

    Escritorio: 1G - 32G. En modo Pi: escalones desde 256M hasta el techo.
    """
    if not is_pi_mode():
        return ["1G", "2G", "4G", "6G", "8G", "12G", "16G", "24G", "32G"]

    cap = _ram_cap_mb()
    steps = []
    for v in (256, 512, 768, 1024, 1536, 2048, 3072, 4096, 6144, 8192):
        if v <= cap:
            steps.append(f"{v}M" if v % 1024 else f"{v // 1024}G")
    return steps or ["256M"]


def get_default_ram() -> str:
    """RAM por defecto para el selector: la recomendada, ajustada a una opción válida."""
    if not is_pi_mode():
        return "4G"
    recommended = _ram_mb(get_recommended_server_ram())
    options = get_ram_options()
    best = options[0]
    for opt in options:
        if _ram_mb(opt) <= recommended:
            best = opt
    # Prefiere la opción más cercana por arriba si hay margen (<96 MB)
    for opt in options:
        if _ram_mb(opt) >= recommended and _ram_mb(opt) - recommended < 96:
            best = opt
    return best


# ---------------------------------------------------------------------------
# JVM
# ---------------------------------------------------------------------------

def get_java_args(ram: str) -> list:
    """Args JVM óptimos según el heap asignado.

    <= 1G : SerialGC (mejor para 1-2 núcleos y poca RAM, Pi 3B+)
    >  1G : G1GC tuneado para pausas bajas (Pi 4/5 con más RAM)
    """
    args = [f"-Xms{ram}", f"-Xmx{ram}"]

    if not is_pi_mode():
        args.append("-Dfile.encoding=UTF-8")
        return args

    if _ram_mb(ram) <= 1024:
        args += [
            "-XX:+UseSerialGC",
            "-XX:MaxMetaspaceSize=128M",
        ]
    else:
        args += [
            "-XX:+UseG1GC",
            "-XX:G1NewSizePercent=30",
            "-XX:G1MaxNewSizePercent=40",
            "-XX:G1HeapRegionSize=8M",
            "-XX:G1ReservePercent=20",
            "-XX:MaxGCPauseMillis=50",
            "-XX:MaxMetaspaceSize=256M",
        ]
    args += [
        "-XX:+DisableExplicitGC",
        "-Dfile.encoding=UTF-8",
    ]
    return args


def get_optimization_preset() -> str:
    """Preset de optimización: 'pi' en modo Pi, 'aggressive' en escritorio."""
    return "pi" if is_pi_mode() else "aggressive"


# ---------------------------------------------------------------------------
# Diagnóstico
# ---------------------------------------------------------------------------

def get_diagnostics() -> list:
    """Resumen legible del hardware y la configuración recomendada (para el log de bienvenida)."""
    lines = []
    if is_pi_mode():
        model = get_hardware_model() or "Dispositivo ARM"
        lines.append(f"[bold orange]Modo optimizado: {model}[/bold orange]")
        lines.append(f"[dim]RAM total: {get_total_ram_mb()} MB | libre: {get_available_ram_mb()} MB[/dim]")
        lines.append(f"[dim]RAM recomendada para el servidor: {get_recommended_server_ram()}[/dim]")
        lines.append(f"[dim]Opciones de RAM: {', '.join(get_ram_options())}[/dim]")
    return lines