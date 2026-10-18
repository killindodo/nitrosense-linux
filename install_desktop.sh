#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_EXEC="$SCRIPT_DIR/nitro_sense.py"
ICON_PATH="$SCRIPT_DIR/assets/icon.png"

echo "[*] Setting up NitroSense Linux desktop integration..."

# 1. Symlink to ~/.local/bin
mkdir -p "$HOME/.local/bin"
ln -sf "$APP_EXEC" "$HOME/.local/bin/nitrosense"
echo "[+] Created CLI shortcut: ~/.local/bin/nitrosense"

# 2. Desktop launcher
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
cat << EOF > "$DESKTOP_DIR/nitrosense.desktop"
[Desktop Entry]
Name=NitroSense
Comment=Monitor thermals and control fans on Acer Nitro laptops (Made with ❤️ by killindodo)
Exec=$APP_EXEC
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=System;HardwareSettings;Utility;
Keywords=acer;nitro;fan;thermal;cooling;gpu;cpu;nitrosense;
StartupNotify=true
EOF

chmod +x "$DESKTOP_DIR/nitrosense.desktop"
echo "[+] Created desktop entry: $DESKTOP_DIR/nitrosense.desktop"

# 3. Optional desktop shortcut
if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_DIR/nitrosense.desktop" "$HOME/Desktop/"
    chmod +x "$HOME/Desktop/nitrosense.desktop"
    echo "[+] Created Desktop shortcut on ~/Desktop"
fi

echo "[✓] Desktop integration complete! You can now launch NitroSense from your application menu or by running 'nitrosense' in the terminal."
