#!/bin/bash

# MCSM Universal Installer
# Installs Python dependencies and sets up the environment in a safe location.

INSTALL_DIR="$HOME/mcsm"
REPO_URL="https://github.com/bm0x/KubeControlMC.git"
PYTHON_BIN="python3"

echo -e "\e[32m[KubeControlMC] Iniciando instalador...\e[0m"

# 1. Check Python
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "Python 3 no encontrado. Por favor instálalo."
    exit 1
fi

# 2. Setup Directory
if [ -d "$INSTALL_DIR" ]; then
    echo "Directorio $INSTALL_DIR ya existe. Eliminando versión anterior..."
    rm -rf "$INSTALL_DIR"
fi

echo "Instalando en $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Check if we are running locally (installer next to main.py)
if [ -f "main.py" ]; then
    echo "Detectada instalación local. Copiando archivos..."
    cp -r ./* "$INSTALL_DIR/"
else
    echo "Instalación remota. Clonando repositorio..."
    if command -v git &> /dev/null; then
        git clone "$REPO_URL" "$INSTALL_DIR"
    else
        echo "Error: Git no está instalado y no se encontraron archivos locales."
        exit 1
    fi
fi

# 3. Setup Virtual Environment or Libs
cd "$INSTALL_DIR"
echo "Configurando entorno (Instalando dependencias)..."

# Try to use pip to install to local libs directory
if ! python3 -m pip install --target "$INSTALL_DIR/libs" -r "$INSTALL_DIR/requirements.txt" --break-system-packages 2>/dev/null; then
    echo "Intentando instalación alternativa..."
    python3 -m pip install --user -r "$INSTALL_DIR/requirements.txt" --break-system-packages 2>/dev/null || echo "Advertencia: Algunas dependencias pueden no haberse instalado."
fi

echo "Creando lanzador..."
LAUNCHER="$HOME/.local/bin/kcmc"
mkdir -p "$HOME/.local/bin"

cat <<EOF > "$LAUNCHER"
#!/bin/bash
cd "$INSTALL_DIR"
python3 main.py "\$@"
EOF

chmod +x "$LAUNCHER"

# 4. PATH Handling logic
CURRENT_PATH="$PATH"
BIN_DIR="$HOME/.local/bin"
SHELL_RC=""

if [[ ":$CURRENT_PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "\e[33m[!] Alerta: $BIN_DIR no está en tu PATH.\e[0m"
    
    # Detect shell
    if [[ "$SHELL" == */zsh ]]; then
        SHELL_RC="$HOME/.zshrc"
    elif [[ "$SHELL" == */bash ]]; then
        SHELL_RC="$HOME/.bashrc"
    else
        SHELL_RC="$HOME/.profile"
    fi

    # Auto-fix
    if [ -f "$SHELL_RC" ]; then
        if ! grep -q "$BIN_DIR" "$SHELL_RC"; then
            echo "Añadiendo configuración a $SHELL_RC..."
            echo '' >> "$SHELL_RC"
            echo '# Added by KubeControlMC' >> "$SHELL_RC"
            echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_RC"
            echo "Configuración actualizada."
        fi
    fi
    
    echo -e "\e[31m[IMPORTANTE]\e[0m Para usar el comando inmediatamente, ejecuta:"
    echo -e "    \e[1msource $SHELL_RC\e[0m"
    echo "O cierra y abre tu terminal."
else
    echo -e "\e[32m[OK] Tu PATH ya está configurado correctamente.\e[0m"
fi

echo -e "\e[32m[KubeControlMC] Instalación completada!\e[0m"
echo -e "Puedes mover los archivos del proyecto a: $INSTALL_DIR"
echo -e "Una vez recargada la terminal, ejecuta: \e[1mkcmc\e[0m"
