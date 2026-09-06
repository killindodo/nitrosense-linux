#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "    Acer Nitro 5 EC Driver Uninstaller"
echo "=========================================================="

if [ "$EUID" -ne 0 ]; then
    echo "[!] This script requires root privileges."
    if command -v pkexec >/dev/null 2>&1; then
        exec pkexec "$0" "$@"
    elif command -v sudo >/dev/null 2>&1; then
        exec sudo "$0" "$@"
    else
        echo "[X] Error: sudo or pkexec required."
        exit 1
    fi
fi

KERNEL_VER="$(uname -r)"

echo "[*] Unloading kernel module..."
modprobe -r acer_nitro_ec 2>/dev/null || rmmod acer_nitro_ec 2>/dev/null || true

echo "[*] Removing installed files..."
rm -f "/lib/modules/$KERNEL_VER/updates/acer-nitro-ec.ko"
rm -f "/etc/modules-load.d/acer-nitro-ec.conf"
rm -f "/etc/udev/rules.d/99-acer-nitro-ec.rules"

if command -v dkms >/dev/null 2>&1; then
    echo "[*] Removing from DKMS..."
    dkms remove -m acer-nitro-ec -v 1.0.0 --all 2>/dev/null || true
    rm -rf /usr/src/acer-nitro-ec-1.0.0
fi

depmod -a
udevadm control --reload-rules || true

echo "[✓] acer-nitro-ec driver uninstalled successfully."
