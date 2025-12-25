#!/bin/bash
set -e

APP_NAME="kubecontrol-mc"
VERSION="1.0.0"
ARCH="amd64"
BUILD_DIR="build_deb"
DIST_DIR="dist"

echo "=== Iniciando Construcción de Paquete DEB ($APP_NAME v$VERSION) ==="

# 1. Setup Virtual Environment
echo "[1/5] Configurando entorno virtual..."
if [ ! -d ".venv" ]; then
    echo "Creando venv..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install Dependencies in VENV
echo "Instalando dependencias en venv..."
pip install --upgrade pip
pip install pyinstaller textual rich customtkinter pillow aiohttp psutil requests

# Verify libraries
python3 -c "import PIL.ImageTk; print('PIL.ImageTk found')" || echo "WARNING: PIL.ImageTk not found in venv!"

# 2. Build Binary
echo "[2/5] Compilando Binario con PyInstaller..."
# Cleanup previous build
rm -rf build "$DIST_DIR"

# Ensure libs are in path
export PYTHONPATH="$(pwd)/libs:$PYTHONPATH"

# Ensure required directories exist (GitHub Actions won't have libs/)
mkdir -p server_bin
mkdir -p libs
mkdir -p assets

# Hidden imports common for TUI/GUI
HIDDEN_IMPORTS="--hidden-import=textual --hidden-import=textual.app --hidden-import=textual.widgets"
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import=customtkinter --hidden-import=rich --hidden-import=PIL --hidden-import=PIL.ImageTk"
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import=aiohttp --hidden-import=asyncio"

# Build ADD_DATA arguments conditionally
ADD_DATA="--add-data src:src --add-data server_bin:server_bin"

# Add assets if icon exists, otherwise create placeholder
if [ ! -f "assets/icon.png" ]; then
    echo "Creating placeholder icon..."
    # Create a minimal 1x1 PNG (placeholder)
    python3 -c "from PIL import Image; img=Image.new('RGBA',(256,256),(50,100,200,255)); img.save('assets/icon.png')"
fi
ADD_DATA="$ADD_DATA --add-data assets:assets"

# Build command (Outputs to dist/kubecontrol-mc directory)
# --noconsole prevents terminal window.
# --paths adds our local libs directory to the search path.
pyinstaller --noconfirm --onedir --noconsole --clean \
    --name "$APP_NAME" \
    --paths "./libs" \
    --paths "." \
    $HIDDEN_IMPORTS \
    --collect-all textual \
    --collect-all customtkinter \
    --collect-all rich \
    $ADD_DATA \
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

# Copy Icon at multiple resolutions for broad compatibility
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/48x48/apps"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$BUILD_DIR/usr/share/pixmaps"

# Resize icon for different sizes (if ImageMagick is available, else just copy)
if command -v convert &> /dev/null; then
    convert assets/icon.png -resize 48x48 "$BUILD_DIR/usr/share/icons/hicolor/48x48/apps/kubecontrol-mc.png"
    convert assets/icon.png -resize 128x128 "$BUILD_DIR/usr/share/icons/hicolor/128x128/apps/kubecontrol-mc.png"
    convert assets/icon.png -resize 256x256 "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps/kubecontrol-mc.png"
else
    cp assets/icon.png "$BUILD_DIR/usr/share/icons/hicolor/48x48/apps/kubecontrol-mc.png"
    cp assets/icon.png "$BUILD_DIR/usr/share/icons/hicolor/128x128/apps/kubecontrol-mc.png"
    cp assets/icon.png "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps/kubecontrol-mc.png"
fi

# Also add to pixmaps as fallback (older DEs)
cp assets/icon.png "$BUILD_DIR/usr/share/pixmaps/kubecontrol-mc.png"

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
Depends: python3-tk, libtk8.6, libc6, python3-pil.imagetk
Recommends: default-jre
Maintainer: KubeControl Team <admin@example.com>
Homepage: https://github.com/bm0x/KubeControlMC
Description: Professional Minecraft Server Manager (GUI)
 Advanced tool to deploy and manage Minecraft servers.
 Includes support for Java, Bedrock, Tunnels, and Discord integration.
 .
 Features:
  - Native GUI (no terminal required)
  - Automatic server downloads (Paper, Folia, Velocity)
  - Tunnel support for easy multiplayer
  - RAM optimization and monitoring
EOF

# Desktop Entry
cat <<EOF > "$BUILD_DIR/usr/share/applications/kubecontrol-mc.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=KubeControl MC
GenericName=Minecraft Server Manager
Comment=Professional Minecraft Server Manager
Exec=/usr/local/bin/kcmc
Icon=kubecontrol-mc
Terminal=false
Categories=Game;
Keywords=minecraft;server;management;
StartupNotify=true
StartupWMClass=kubecontrol-mc
EOF

# Postinst Script (Permissions + Icon Cache)
cat <<EOF > "$BUILD_DIR/DEBIAN/postinst"
#!/bin/bash
set -e

# CRITICAL: Make application directory and all contents writable by any user
# This allows the app to create/modify server files when run by normal users
chmod -R 777 /opt/$APP_NAME
chmod +x /opt/$APP_NAME/$APP_NAME

# Create server_bin directory with full permissions
mkdir -p /opt/$APP_NAME/server_bin
chmod -R 777 /opt/$APP_NAME/server_bin

# Update menu and icon caches
update-desktop-database /usr/share/applications 2>/dev/null || true

# Refresh icon cache (critical for icons to appear)
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi
if command -v update-icon-caches &> /dev/null; then
    update-icon-caches /usr/share/icons/hicolor 2>/dev/null || true
fi

echo "[KubeControl MC] Instalado correctamente."
echo "Busca 'KubeControl' en tu menú de aplicaciones."
EOF
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# 5. Build DEB
echo "[5/5] Empaquetando .deb..."
dpkg-deb --build "$BUILD_DIR" "${APP_NAME}_${VERSION}_${ARCH}.deb"

echo ""
echo "✅ Paquete generado exitosamente: ${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "Instalar con: sudo apt install ./${APP_NAME}_${VERSION}_${ARCH}.deb"
