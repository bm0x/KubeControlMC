#!/bin/bash

# MCSM Universal Installer
# Installs Python dependencies and sets up the environment in a safe location.

INSTALL_DIR="$HOME/mcsm"
REPO_URL="https://github.com/bm0x/KubeControlMC.git" # Actualizar con tu usuario real
PYTHON_BIN="python3"

echo -e "\e[32m[KubeControlMC] Iniciando instalador...\e[0m"

# 1. Check Python
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "Python 3 no encontrado. Por favor instálalo."
    exit 1
fi

# 2. Setup Directory
if [ -d "$INSTALL_DIR" ]; then
    echo "Directorio $INSTALL_DIR ya existe. Actualizando..."
    # In a real scenario, valid git logic here. For now, we assume this script stays with the files.
else
    echo "Creando directorio en $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    # Copy current files to install dir (Simulation of git clone)
    # cp -r ./* "$INSTALL_DIR"
fi

# 3. Setup Virtual Environment or Libs
echo "Configurando entorno (Instalando dependencias)..."

# Try to use pip to install to local libs directory
if ! python3 -m pip install --target "$INSTALL_DIR/libs" -r requirements.txt --break-system-packages; then
    echo "Error instalando dependencias con pip. Intentando '--user' fallback..."
    python3 -m pip install --user -r requirements.txt --break-system-packages
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

echo -e "\e[32m[KubeControlMC] Instalación completada!\e[0m"
echo -e "Puedes mover los archivos del proyecto a: $INSTALL_DIR"
echo -e "Y ejecutar 'kcmc' (asegúrate de que ~/.local/bin está en tu PATH) o 'python3 main.py' en la carpeta."
