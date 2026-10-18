#!/usr/bin/env bash
set -e

# Acer Nitro EC Driver Installer for Acer Nitro laptops

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
EC_DRIVER_DIR="$PROJECT_DIR/ec-driver"

echo "=========================================================="
echo "         Acer Nitro Fan Control Driver Setup"
echo "=========================================================="

if [ "$EUID" -ne 0 ]; then
    echo "[!] This installer requires root privileges."
    echo "[*] Elevating with pkexec / sudo..."
    if command -v pkexec >/dev/null 2>&1; then
        exec pkexec "$0" "$@"
    elif command -v sudo >/dev/null 2>&1; then
        exec sudo "$0" "$@"
    else
        echo "[X] Error: sudo or pkexec required to install driver."
        exit 1
    fi
fi

KERNEL_VER="$(uname -r)"
echo "[*] Target kernel: $KERNEL_VER"
echo "[*] Laptop model: $(cat /sys/class/dmi/id/product_name 2>/dev/null || echo 'Unknown')"

# 1. Build kernel module
echo "[*] Building acer-nitro-ec kernel module..."
cd "$EC_DRIVER_DIR"
make clean
make LLVM=

if [ ! -f "acer-nitro-ec.ko" ]; then
    echo "[X] Build failed: acer-nitro-ec.ko not generated!"
    exit 1
fi
echo "[+] Build successful!"

# 2. Install to system updates module path
DEST_DIR="/lib/modules/$KERNEL_VER/updates"
mkdir -p "$DEST_DIR"
cp -f acer-nitro-ec.ko "$DEST_DIR/"
echo "[+] Installed kernel module to $DEST_DIR/acer-nitro-ec.ko"

# 3. Update module dependencies
depmod -a
echo "[+] Module dependencies updated (depmod -a)"

# 4. Configure auto-load on boot
MODULES_LOAD_FILE="/etc/modules-load.d/acer-nitro-ec.conf"
echo "acer_nitro_ec" > "$MODULES_LOAD_FILE"
echo "[+] Configured auto-load on boot: $MODULES_LOAD_FILE"

# 5. Configure udev rules for non-root fan control access
UDEV_RULE_FILE="/etc/udev/rules.d/99-acer-nitro-ec.rules"
cat << 'EOF' > "$UDEV_RULE_FILE"
# Allow unprivileged users to read and set fan speeds on Acer Nitro EC
ACTION=="add|change", SUBSYSTEM=="hwmon", ATTR{name}=="acer_nitro_ec", RUN+="/bin/sh -c 'chmod 0666 /sys%p/pwm* 2>/dev/null || true'"
KERNEL=="hwmon*", ATTRS{name}=="acer_nitro_ec", RUN+="/bin/sh -c 'chmod 0666 /sys%p/pwm* 2>/dev/null || true'"
EOF
udevadm control --reload-rules || true
udevadm trigger || true
echo "[+] Configured udev rules: $UDEV_RULE_FILE"

# 6. Setup DKMS if available
if command -v dkms >/dev/null 2>&1; then
    DKMS_VER="1.0.0"
    DKMS_SRC="/usr/src/acer-nitro-ec-$DKMS_VER"
    echo "[*] Setting up DKMS for automatic rebuilds on kernel updates..."
    mkdir -p "$DKMS_SRC"
    cp "$EC_DRIVER_DIR/acer-nitro-ec.c" "$EC_DRIVER_DIR/Makefile" "$EC_DRIVER_DIR/dkms.conf" "$DKMS_SRC/"
    # Ensure dkms.conf has version filled in
    sed -i "s/@PKGVER@/$DKMS_VER/" "$DKMS_SRC/dkms.conf" || true
    
    # Remove older DKMS module if already registered
    dkms remove -m acer-nitro-ec -v "$DKMS_VER" --all >/dev/null 2>&1 || true
    dkms add -m acer-nitro-ec -v "$DKMS_VER" >/dev/null 2>&1 || true
    dkms build -m acer-nitro-ec -v "$DKMS_VER" >/dev/null 2>&1 || true
    dkms install -m acer-nitro-ec -v "$DKMS_VER" >/dev/null 2>&1 || true
    echo "[+] DKMS package registered and installed!"
fi

# 7. Unload previous version if running
if lsmod | grep -q "acer_nitro_ec"; then
    echo "[*] Unloading active module..."
    modprobe -r acer_nitro_ec || rmmod acer_nitro_ec || true
fi

# 8. Load module
echo "[*] Loading acer_nitro_ec..."
modprobe acer_nitro_ec || insmod "$DEST_DIR/acer-nitro-ec.ko"

# 9. Apply permissions immediately to any active sysfs paths
for hwmon in /sys/class/hwmon/hwmon*; do
    if [ -f "$hwmon/name" ] && [ "$(cat "$hwmon/name" 2>/dev/null)" = "acer_nitro_ec" ]; then
        chmod 0666 "$hwmon"/pwm* 2>/dev/null || true
        echo "[+] Found active hwmon device: $hwmon ($(cat "$hwmon/name"))"
        echo "[+] Permissions set on $hwmon/pwm*"
    fi
done

echo ""
echo "=========================================================="
echo "    [✓] acer-nitro-ec successfully installed & loaded!"
echo "    You can now control CPU/GPU fan speeds and thermals."
echo "=========================================================="
