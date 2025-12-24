# 🧊 KubeControlMC

![Main View](https://via.placeholder.com/800x400?text=KubeControl+Dashboard+GUI)
[![Build DEB Package](https://github.com/bm0x/KubeControlMC/actions/workflows/build_deb.yml/badge.svg)](https://github.com/bm0x/KubeControlMC/actions/workflows/build_deb.yml)

**Tu Servidor de Minecraft, Simplificado y Potente (Aplicación de Escritorio).**

KubeControlMC es la herramienta definitiva para crear y administrar servidores de Minecraft sin dolores de cabeza. Ahora disponible como una **Aplicación Nativa** para Linux.

## ✨ Características Desktop First

*   **🖥️ Interfaz Gráfica (GUI)**: Olvídate de la terminal. Usa botones, menús y ventanas reales con Modo Oscuro nativo.
*   **📦 Instalación Nativa**: Se instala como cualquier programa (`.deb`), con su propio icono en el menú de aplicaciones.
*   **🚀 Rendimiento Extremo**: Elige entre **PaperMC** (Estable) o **Folia** (Velocidad absurda) con un clic.
*   **🤝 Túnel Automático**: Juega con amigos sin abrir puertos. Enlace público seguro integrado.
*   **🧠 IA de Recursos**: Un guardián silencioso optimiza la RAM de tu servidor en tiempo real.
*   **⚡ Optimizador de FPS**: Configuraciones agresivas de rendimiento aplicadas automáticamente.

---

## 📥 Instalación

### Opción A (Recomendada): Paquete DEB
Descarga el último release desde la pestaña "Actions" o "Releases" e instálalo:

```bash
sudo apt install ./kubecontrol-mc_1.0.0_amd64.deb
```

Luego búscalo en tu menú de aplicaciones como **"KubeControl MC"**.

### Opción B: Script de Instalación Rápida
Si prefieres instalar desde la fuente:
```bash
curl -sL https://raw.githubusercontent.com/bm0x/KubeControlMC/main/install.sh | bash
```

---

## 🎮 Cómo Usar

### Modo Escritorio (GUI)
Simplemente haz clic en el icono **KubeControl** en tu menú.
Todo se gestiona visualmente:
1.  **Dashboard**: Inicia/Detiene el servidor y ve el estado.
2.  **Consola**: Ve los logs en tiempo real y envía comandos.
3.  **Config**: Ajusta la RAM y versiones.

### Modo Terminal (TUI)
¿Eres un usuario avanzado o usas un servidor sin monitor?
```bash
kcmc --tui
```
Esto abrirá la interfaz clásica de terminal ligera.

### Compilación Manual
Si quieres generar tu propio instalador `.deb`:
```bash
./build_deb.sh
```

---

## ❓ Preguntas Frecuentes

**¿Funciona en Windows?**
Actualmente es nativo para Linux (Debian, Ubuntu, Elementary, Mint). Estamos trabajando en la versión `.exe`.

**¿Dónde están mis archivos?**
Todo se guarda en `/opt/kubecontrol-mc` (binarios) y los datos del servidor suelen estar en tu directorio de ejecución o `~/mcsm`.

---

**KubeControlMC** - *Construye mundos, no configuraciones.*
