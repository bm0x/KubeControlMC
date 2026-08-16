# 🧊 KubeControlMC

<div align="center">

[![Build DEB Package](https://github.com/bm0x/KubeControlMC/actions/workflows/build_deb.yml/badge.svg)](https://github.com/bm0x/KubeControlMC/actions/workflows/build_deb.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-green.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)]()

**Gestión Profesional de Servidores Minecraft · Interfaz TUI Moderna · Túneles Automáticos**

</div>

---

## 📋 Descripción

**KubeControlMC** es una herramienta de gestión completa para servidores de Minecraft, diseñada para simplificar la administración sin sacrificar el control avanzado. Disponible como aplicación nativa para **Linux y macOS** con interfaz TUI (Terminal User Interface) y GUI moderna.

### ¿Por qué KubeControlMC?

- 🚀 **Instalación en un clic** de Paper, Folia o Velocity
- 🔧 **Gestión automática** de plugins y configuraciones
- 🌐 **Túneles integrados** con Playit.gg (sin abrir puertos)
- 📊 **Monitoreo en tiempo real** de recursos y jugadores
- 🛡️ **Sanitización inteligente** de estructura de directorios

---

## ✨ Características

### 🖥️ Interfaz TUI Profesional
- Dashboard con estado del servidor en tiempo real
- Consola de servidor con logs coloreados
- Panel de administración de jugadores (kick/ban)
- Selector de RAM configurable (2G - 32G)

### 📦 Gestión de Servidor
- Descarga automática de **PaperMC**, **Folia** y **Velocity**
- Instalación de **Geyser + Floodgate** para soporte Bedrock
- Editor de `server.properties` integrado
- Optimización agresiva de configuraciones para bajo rendimiento

### 🔧 Sanitización de Directorios
- **Detección automática** de plugins mal ubicados
- **Escaneo profundo** de subdirectorios
- **Movimiento forzado** a carpeta `plugins/`
- **Limpieza de residuos** después de mover

### 🌐 Túneles Automáticos
- Integración nativa con **Playit.gg**
- Soporte para Java (TCP) y Bedrock (UDP)
- Reconexión automática con backoff exponencial
- Copiado automático de IP al portapapeles

### 🛡️ Preservación de Datos
- **El directorio `server_bin` NUNCA se modifica** durante reinstalaciones
- Actualizaciones de aplicación sin pérdida de mundos ni configuraciones
- Compatible con actualizaciones DEB (`apt upgrade`)

---

## 📥 Instalación

### Opción A: Paquete DEB (Recomendada)

Descarga el último release desde [Releases](https://github.com/bm0x/KubeControlMC/releases):

```bash
sudo apt install ./kubecontrol-mc_1.0.0_amd64.deb
```

Después, busca **"KubeControl MC"** en tu menú de aplicaciones.

### Opción B: Script de Instalación

```bash
curl -sL https://raw.githubusercontent.com/bm0x/KubeControlMC/main/install.sh | bash
```

### Opción C: Desde Código Fuente

```bash
git clone https://github.com/bm0x/KubeControlMC.git
cd KubeControlMC
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./launcher.sh            # GUI (modo gráfico)
./launcher.sh --tui      # Interfaz de terminal
```

### Opción D: macOS

1. Instala **Python 3.10+** (desde [python.org](https://www.python.org/downloads/)) y **Java 17+** (`brew install --cask temurin@17`).
2. Clona y configura el entorno:

```bash
git clone https://github.com/bm0x/KubeControlMC.git
cd KubeControlMC
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./launcher.sh            # Abre la GUI (ventana nativa)
./launcher.sh --tui      # Modo terminal
```

> Nota sobre túneles: Playit.gg solo publica binarios oficiales para Linux/Windows. En macOS descarga la app desde https://playit.gg/download/macos o instálala en el PATH (`brew install playit` o `/usr/local/bin/playit`) y KubeControlMC la detectará automáticamente.

### Opción E: Raspberry Pi 3B+ (Ultra-Optimizado) 🫐

Diseñado para la Pi 3B+ (1 GB RAM): el **núcleo es 100% stdlib** (sin `requests`/`psutil`/`aiohttp`/`pyperclip`) y se detecta automáticamente poca memoria:

```bash
git clone https://github.com/bm0x/KubeControlMC.git
cd KubeControlMC
python3 -m venv .venv
.venv/bin/pip install -r requirements-pi.txt   # solo Textual (~30MB)
./launcher.sh --tui --pi                        # TUI en modo Pi
```

O instala el paquete **`kubecontrol-mc_*_arm64.deb`** desde [Releases](https://github.com/bm0x/KubeControlMC/releases) (publicado automáticamente por las Actions) y lanza `kcmc --tui --pi`.

Cuando se detecta modo Pi automáticamente:

| Ajuste | Valor en Pi |
|--------|-------------|
| Selector RAM | 256M – 1G (nunca más de 1G), por defecto la recomendada |
| JVM | `-XX:+UseSerialGC`, `-XX:MaxMetaspaceSize=128M`, sin `DisableExplicitGC` |
| Consola TUI | `max_lines=300`, sin `ReprHighlighter` (ahorra CPU) |
| Sincronización | Cada 15s (menos carga) |
| `⚡ Optimizar` | Perfil Pi: view-distance=3, sim-distance=2, spawn limits reducidos |
| Monitor de RAM | Alerta al 85%, lee `/proc` directamente |

> **Nota**: con ~905 MB de RAM, usa **PaperMC** y el botón **⚡ Optimizar** antes de iniciar. Con Geyser/Floodgate activos la RAM del servidor sube considerablemente.

---

## 🎮 Uso

### Iniciar la Aplicación

```bash
# Desde menú de aplicaciones
KubeControl MC

# Desde terminal
kcmc
```

### Navegación

| Pestaña | Descripción |
|---------|-------------|
| **Dashboard** | Estado del servidor, controles de inicio/parada, lista de jugadores |
| **Consola Server** | Logs en tiempo real, entrada de comandos |
| **Sistema** | Herramientas, configuración, actualizaciones |

### Comandos de Servidor

Desde la pestaña "Consola Server", escribe comandos directamente:

```
/op NombreJugador
/whitelist add NombreJugador
/stop
```

---

## 🔧 Herramientas del Sistema

| Botón | Función |
|-------|---------|
| **Instalar/Actualizar** | Descargar Paper, Folia o Velocity |
| **⚙️ Configuración** | Editor de server.properties |
| **⚡ Optimizar** | Aplicar configuraciones de bajo consumo |
| **🔧 Reparar Estructura** | Sanitización de directorios |
| **Geyser/Floodgate** | Instalar soporte para Bedrock |
| **Iniciar Túnel** | Activar túnel Playit.gg |
| **📂 Carpeta Server** | Abrir directorio del servidor |
| **🔄 Actualizar App** | Actualizar desde GitHub |

---

## 📁 Estructura de Directorios

```
/opt/kubecontrol-mc/           # Instalación de la aplicación
├── kubecontrol-mc             # Binario ejecutable
├── src/                       # Código fuente
└── server_bin/                # ⚠️ DATOS DEL SERVIDOR (NUNCA SE MODIFICA)
    ├── paper-*.jar            # JAR del servidor
    ├── eula.txt
    ├── server.properties
    ├── plugins/               # Todos los plugins aquí
    │   ├── *.jar
    │   └── [configs]/
    ├── world/
    ├── world_nether/
    └── logs/
```

> ⚠️ **Importante**: El directorio `server_bin` es preservado durante actualizaciones. Tus mundos y configuraciones están seguros.

---

## 🤝 Integración con KubeControlPlugin

Para estadísticas avanzadas y sincronización con Discord, instala [KubeControlPlugin](https://github.com/bm0x/KubeControlPlugin) en tu servidor.

---

## 📋 Requisitos

- **Sistema Operativo**: Linux (Debian, Ubuntu, Elementary OS, Linux Mint) y macOS (11+)
- **Python**: 3.10+
- **Java**: 17+ (para el servidor Minecraft)
- **RAM**: Mínimo 2GB libres para el servidor (en Raspberry Pi 3B+ usa el modo Pi: 512M recomendado)

---

## 🛠️ Desarrollo

### Compilar Paquete DEB

```bash
./build_deb.sh
```

### Ejecutar Tests

```bash
python -m pytest
```

---

## ❓ FAQ

**¿Funciona en Windows?**
> Actualmente es nativo para Linux y macOS. Versión Windows en desarrollo.

**¿Dónde están mis mundos?**
> En `/opt/kubecontrol-mc/server_bin/world/` (o `~/mcsm/server_bin/` si usaste el script).

**¿Cómo hago backup?**
> Copia la carpeta `server_bin/` completa. Nunca se modifica durante actualizaciones.

**¿Puedo usar mods de Forge/Fabric?**
> Actualmente soporta Paper, Folia y Velocity. Forge/Fabric en desarrollo.

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.

---

<div align="center">

**KubeControlMC** · *Construye mundos, no configuraciones.*

[Reportar Bug](https://github.com/bm0x/KubeControlMC/issues) · [Solicitar Feature](https://github.com/bm0x/KubeControlMC/issues)

</div>
