#!/bin/bash

# MCSM Universal Installer
# Installs Python dependencies and sets up the environment in a safe location.

INSTALL_DIR="$HOME/mcsm"
REPO_URL="https://github.com/bm0x/KubeControlMC.git"
PYTHON_BIN="python3"

echo -e "\e[32m[KubeControlMC] Iniciando instalador...\e[0m"

# 1. Check and install dependencies on APT-based systems (Debian/Ubuntu)
if command -v apt-get &> /dev/null; then
    echo "Sistema basado en APT detectado. Verificando dependencias..."
    
    MISSING_DEPS=()
    
    # Check for python3
    if ! command -v python3 &> /dev/null; then
        echo "  - python3: No encontrado"
        MISSING_DEPS+=("python3")
    else
        echo "  - python3: OK"
    fi
    
    # Check for python3-pip (only if python3 is available)
    if command -v python3 &> /dev/null; then
        if ! python3 -m pip --version &> /dev/null; then
            echo "  - python3-pip: No encontrado"
            MISSING_DEPS+=("python3-pip")
        else
            echo "  - python3-pip: OK"
        fi
    else
        echo "  - python3-pip: Pendiente (requiere python3)"
    fi
    
    # Check for git
    if ! command -v git &> /dev/null; then
        echo "  - git: No encontrado"
        MISSING_DEPS+=("git")
    else
        echo "  - git: OK"
    fi
    
    # Install missing dependencies if any
    if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
        echo -e "\e[33mInstalando dependencias faltantes: ${MISSING_DEPS[*]}\e[0m"
        
        # Check if we need sudo (if not running as root)
        if [ "$EUID" -eq 0 ]; then
            # Running as root, no sudo needed
            if apt-get update && apt-get install -y "${MISSING_DEPS[@]}"; then
                echo -e "\e[32mDependencias instaladas correctamente.\e[0m"
            else
                echo -e "\e[31mError: No se pudieron instalar las dependencias automáticamente.\e[0m"
                echo "Por favor instala manualmente: ${MISSING_DEPS[*]}"
            fi
        else
            # Not root, use sudo
            echo "Intentando instalación con privilegios de administrador..."
            if sudo apt-get update && sudo apt-get install -y "${MISSING_DEPS[@]}"; then
                echo -e "\e[32mDependencias instaladas correctamente.\e[0m"
            else
                echo -e "\e[31mError: No se pudieron instalar las dependencias automáticamente.\e[0m"
                echo "Por favor instala manualmente: ${MISSING_DEPS[*]}"
            fi
        fi
    else
        echo -e "\e[32mTodas las dependencias están instaladas.\e[0m"
    fi
fi

# 2. Final check for Python (abort if not found)
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "Python 3 no encontrado. Por favor instálalo."
    exit 1
fi

# 3. Setup Directory
if [ -d "$INSTALL_DIR" ]; then
    echo "Directorio $INSTALL_DIR ya existe."
    
    # PRESERVE SERVER DATA (server_bin)
    if [ -d "$INSTALL_DIR/server_bin" ]; then
        echo -e "\e[33m[!] Detectados datos de servidor. Realizando copia de seguridad de server_bin...\e[0m"
        TEMP_BACKUP="$HOME/mcsm_server_bin_backup_$(date +%s)"
        mv "$INSTALL_DIR/server_bin" "$TEMP_BACKUP"
        echo "Copia guardada en: $TEMP_BACKUP"
        
        echo "Eliminando instalación anterior..."
        rm -rf "$INSTALL_DIR"
        
        # We will restore this after creating the directory
        SHOULD_RESTORE="$TEMP_BACKUP"
    else
        echo "Eliminando versión anterior..."
        rm -rf "$INSTALL_DIR"
    fi
fi

echo "Instalando en $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

if [ ! -z "$SHOULD_RESTORE" ]; then
    echo "Restaurando datos del servidor..."
    mv "$SHOULD_RESTORE" "$INSTALL_DIR/server_bin"
    echo -e "\e[32mDatos restaurados correctamente.\e[0m"
fi

# Check if we are running locally (installer next to main.py)
if [ -f "main.py" ]; then
    echo "Detectada instalación local. Copiando archivos..."
    cp -r ./* "$INSTALL_DIR/"
else
    echo "Instalación remota. Clonando repositorio..."
    if command -v git &> /dev/null; then
        git clone "$REPO_URL" "$INSTALL_DIR"
    else
        echo "Error: Git no está instalado. En sistemas APT, debería haberse instalado automáticamente."
        echo "Por favor ejecuta manualmente: sudo apt-get install git"
        exit 1
    fi
fi

# 4. Setup Virtual Environment or Libs
cd "$INSTALL_DIR" || { echo "Error: No se pudo acceder a $INSTALL_DIR"; exit 1; }
echo "Directorio actual: $(pwd)"

# Find requirements.txt
REQ_FILE=""
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    REQ_FILE="$INSTALL_DIR/requirements.txt"
elif [ -f "requirements.txt" ]; then
    REQ_FILE="$(pwd)/requirements.txt"
else
    # Search for it
    echo "Buscando requirements.txt..."
    REQ_FILE=$(find "$INSTALL_DIR" -name "requirements.txt" -type f 2>/dev/null | head -1)
fi

if [ -z "$REQ_FILE" ] || [ ! -f "$REQ_FILE" ]; then
    echo -e "\e[33m[WARN] No se encontró requirements.txt. Creando uno mínimo...\e[0m"
    cat > "$INSTALL_DIR/requirements.txt" << 'REQS'
textual>=0.40.0
requests
aiohttp
psutil
REQS
    REQ_FILE="$INSTALL_DIR/requirements.txt"
fi

echo "Usando: $REQ_FILE"
echo "Configurando entorno (Instalando dependencias)..."

# Try to use pip to install to local libs directory
if python3 -m pip install --target "$INSTALL_DIR/libs" -r "$REQ_FILE" --break-system-packages 2>/dev/null; then
    echo -e "\e[32mDependencias instaladas correctamente.\e[0m"
else
    echo "Intentando instalación alternativa..."
    python3 -m pip install --user -r "$REQ_FILE" --break-system-packages 2>/dev/null || echo -e "\e[33mAdvertencia: Algunas dependencias pueden no haberse instalado.\e[0m"
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

# 5. PATH Handling logic
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
