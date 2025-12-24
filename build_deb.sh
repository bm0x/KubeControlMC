#!/bin/bash
set -e

APP_NAME="kubecontrol-mc"
VERSION="1.0.0"
ARCH="amd64"
BUILD_DIR="build_deb"
DIST_DIR="dist"

echo "=== Iniciando Construcción de Paquete DEB ($APP_NAME v$VERSION) ==="

# 1. Install PyInstaller
echo "[1/5] Verificando PyInstaller..."
if ! command -v pyinstaller &> /dev/null; then
    echo "Instalando PyInstaller..."
    pip install pyinstaller --break-system-packages || pip install pyinstaller
fi

# 2. Build Binary
echo "[2/5] Compilando Binario con PyInstaller..."
# Cleanup previous build
rm -rf build "$DIST_DIR"

# Ensure libs are in path
export PYTHONPATH="$(pwd)/libs:$PYTHONPATH"

# Ensure server_bin exists (needed for --add-data)
mkdir -p server_bin

# Hidden imports common for TUI/GUI
HIDDEN_IMPORTS="--hidden-import=textual --hidden-import=customtkinter --hidden-import=rich --hidden-import=PIL"

# Build command (Outputs to dist/kubecontrol-mc directory)
# --noconsole prevents terminal window.
# --icon sets the window icon (for Windows/some Linux DEs).
pyinstaller --noconfirm --onedir --noconsole --clean \
    --name "$APP_NAME" \
    $HIDDEN_IMPORTS \
    --collect-all textual \
    --collect-all customtkinter \
    --add-data "src:src" \
    --add-data "assets:assets" \
    --add-data "server_bin:server_bin" \
    main.py

echo "[OK] Compilación completada."

# 3. Create DEB Structure
echo "[3/5] Creando estructura del paquete DEB..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/local/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$BUILD_DIR/opt"

# Move compiled binary to /opt/kubecontrol-mc
cp -r "$DIST_DIR/$APP_NAME" "$BUILD_DIR/opt/$APP_NAME"
# Copy Icon
cp assets/icon.png "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps/kubecontrol-mc.png"

# Create Symlink script (wrapper to run from /opt)
WRAPPER="$BUILD_DIR/usr/local/bin/kcmc"
cat <<EOF > "$WRAPPER"
#!/bin/bash
export TERM=xterm-256color
/opt/$APP_NAME/$APP_NAME "\$@"
EOF
chmod 755 "$WRAPPER"

# 4. Metadata Files
echo "[4/5] Generando metadatos..."

# Control File
cat <<EOF > "$BUILD_DIR/DEBIAN/control"
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: KubeControl Team <admin@example.com>
Description: Gestor de Servidores Minecraft (TUI/GUI)
 Herramienta avanzada para desplegar y gestionar servidores de Minecraft.
 Incluye soporte para Java, Bedrock, Túneles y Discord.
EOF

# Desktop Entry
cat <<EOF > "$BUILD_DIR/usr/share/applications/kubecontrol.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=KubeControl MC
Comment=Gestor de Servidores Minecraft Profesional
Exec=/usr/local/bin/kcmc
Icon=kubecontrol-mc
Terminal=false
Categories=Utility;Game;System;
StartupNotify=true
EOF

# Postinst Script (Permissions)
cat <<EOF > "$BUILD_DIR/DEBIAN/postinst"
#!/bin/bash
set -e
# Fix permissions in /opt
chmod -R 755 /opt/$APP_NAME
chmod +x /opt/$APP_NAME/$APP_NAME
# Update menu
update-desktop-database /usr/share/applications || true
echo "KubeControl MC instalado correctamente."
EOF
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# 5. Build DEB
echo "[5/5] Empaquetando .deb..."
dpkg-deb --build "$BUILD_DIR" "${APP_NAME}_${VERSION}_${ARCH}.deb"

echo ""
echo "✅ Paquete generado exitosamente: ${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "Instalar con: sudo apt install ./${APP_NAME}_${VERSION}_${ARCH}.deb"
