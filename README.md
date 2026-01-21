# 🧊 KubeControlMC

<div align="center">

[![Build DEB Package](https://github.com/bm0x/KubeControlMC/actions/workflows/build_deb.yml/badge.svg)](https://github.com/bm0x/KubeControlMC/actions/workflows/build_deb.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)]()

**Gestión Profesional de Servidores Minecraft · Interfaz TUI Moderna · Túneles Automáticos**

</div>

---

## 📋 Descripción

**KubeControlMC** es una herramienta de gestión completa para servidores de Minecraft, diseñada para simplificar la administración sin sacrificar el control avanzado. Disponible como aplicación nativa para Linux con interfaz TUI (Terminal User Interface) moderna.

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
pip install -r requirements.txt
python main.py
```

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

- **Sistema Operativo**: Linux (Debian, Ubuntu, Elementary OS, Linux Mint)
- **Python**: 3.10+
- **Java**: 17+ (para el servidor Minecraft)
- **RAM**: Mínimo 2GB libres para el servidor

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
> Actualmente es nativo para Linux. Versión Windows en desarrollo.

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
