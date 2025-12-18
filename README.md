# 🧊 KubeControlMC

**Tu Servidor de Minecraft, Simplificado y Potente.**

KubeControlMC es la herramienta definitiva para crear y administrar servidores de Minecraft sin dolores de cabeza. Diseñada para jugadores, no para ingenieros, pero con la potencia que los expertos desean.

![KubeControlMC Preview](https://via.placeholder.com/800x400?text=KubeControlMC+Dashboard)

## ✨ ¿Por qué KubeControlMC?

*   **🚀 Rendimiento Extremo**: Elige entre **PaperMC** (Estable) o **Folia** (Velocidad absurda) con un solo clic.
*   **🤝 Juega con Todos**: Invita a tus amigos de consola (PlayStation, Xbox, Switch) y celular gracias a la integración automática de **Geyser**.
*   **🌍 Sin Puertos Probemáticos**: Olvídate de abrir puertos en tu router. Crea un enlace público seguro en segundos.
*   **🧠 Inteligencia Artificial (IA) de Recursos**: Un guardián silencioso optimiza la RAM de tu servidor en tiempo real para eliminar el lag.
*   **🛡️ Modo Mantenimiento Seguro**: Reinicia y guarda tu mundo sin riesgo de corrupción ni pérdida de objetos.

---

## 📥 Instalación (En 1 paso)

Copia y pega este comando en tu terminal de Linux. El asistente se encargará de todo.

```bash
curl -sL https://raw.githubusercontent.com/bm0x/KubeControlMC/main/install.sh | bash
```

> **Nota**: El instalador descargará las dependencias necesarias y creará el comando `kcmc` en tu sistema.

---

## 🎮 Cómo Usar

Una vez instalado, no necesitas navegar a ninguna carpeta extraña. Simplemente abre tu terminal en cualquier lugar y escribe:

```bash
kcmc
```

### Primeros Pasos
1.  **Selecciona tu Núcleo**: Al abrirlo por primera vez, elige si quieres estabilidad (Paper) o rendimiento (Folia).
2.  **Enciende**: Pulsa el botón `Iniciar`.
3.  **Comparte**: Si quieres jugar con amigos, pulsa `Iniciar Túnel` y pásales el enlace.

---

## ❓ Preguntas Frecuentes

**¿El comando `kcmc` no funciona?**
Es probable que tu sistema no esté leyendo la carpeta de programas locales. Ejecuta esto y prueba de nuevo:
```bash
export PATH=$PATH:$HOME/.local/bin
```
*(Para hacerlo permanente, añade esa línea al final de tu archivo `.bashrc` o `.zshrc`)*.

**¿Dónde están mis archivos?**
Todo está guardado de forma segura en `~/mcsm` en tu carpeta personal. Puedes abrir esa carpeta directamente desde la aplicación pulsando "Abrir Carpeta Server".

---

**KubeControlMC** - *Construye mundos, no configuraciones.*
