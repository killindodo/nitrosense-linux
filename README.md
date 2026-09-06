# NitroSense Linux

A dedicated, native Linux GUI and Embedded Controller (EC) kernel driver for **Acer Nitro 5 (AN515-42 and compatible AN515 series)** laptops.

**Developer**: [killindodo](https://github.com/killindodo)  
**Repository**: [https://github.com/killindodo/nitrosense-linux](https://github.com/killindodo/nitrosense-linux)

![NitroSense Linux](assets/icon.png)

---

## Why I Built This

On Acer Nitro laptops, the cooling fans are **not connected to standard CPU or GPU PWM headers**. Instead, both fans are routed exclusively through the proprietary **ITE Embedded Controller (EC)** on the motherboard.

Because of this architecture:
1. Standard Linux utilities like `lm-sensors`, `fancontrol`, `CoolerControl`, or `GreenWithEnvy` cannot detect or control the fans.
2. Generic fan apps like `nbfc` often have broken, missing, or untested profiles for AMD-based Nitro laptops (AN515-42).
3. The existing open-source driver (`acer-nitro-ec`) had omitted the `AN515-42` from its DMI whitelist, causing it to refuse to load.

I built this project to provide a reliable, native solution for Linux users with Acer Nitro laptops:
- **Added native DMI support** for `Nitro AN515-42` (with manual override options) into the `acer-nitro-ec` Linux hwmon kernel driver.
- **Fixed the kernel module build system** to compile cleanly with GCC on standard Linux/Debian/Ubuntu/Kali kernels.
- **Exposed the fans** directly via standard Linux `/sys/class/hwmon/` sysfs nodes.
- **Built a modern PyQt6 GUI** that matches the look, feel, and functionality of Windows NitroSense, featuring real-time dials, rolling thermal history, Auto/Turbo/Manual fan modes, and system tray integration.

---

## Features

- **Real-Time Thermals & Metrics**:
  - AMD Ryzen CPU temperature (direct `k10temp` diode and EC diode).
  - Discrete AMD Radeon RX 560X temperature, wattage (`PPT`), core and memory clock speeds.
  - Integrated AMD Radeon Vega iGPU temperature.
- **Fan Control Modes**:
  - ⚡ **Auto**: Default firmware/BIOS thermal management.
  - 🔥 **Max / Turbo**: 100% maximum fan speed for gaming, video rendering, or heavy builds.
  - ⚙️ **Custom**: Interactive sliders (20%–100% CPU floor, 0%–100% GPU) with optional fan synchronization.
  - 📈 **Smart Dynamic Curve**: Automatic software-driven fan curve based on real-time temperatures.
- **Safety Protections**:
  - **Thermal Safety Floor**: Automatically increases fan speed if temperatures exceed 82°C.
  - **Auto-Recovery on Exit**: Restores fans to firmware Auto mode whenever the application closes.
- **System Tray Integration**:
  - Runs in the background with live temperature and RPM readouts in the tray tooltip, plus right-click preset controls.
- **Passwordless Fan Management**:
  - Automated udev rules grant user-level access to the sysfs fan controls without requiring `sudo` after initial setup.

---

## Installation & Setup

### Prerequisites

Ensure Python 3, PyQt6, and kernel build headers are installed:

```bash
# Debian / Ubuntu / Kali
sudo apt update
sudo apt install python3 python3-pyqt6 build-essential dkms linux-headers-$(uname -r)
```

### 1. Clone the Repository

```bash
git clone https://github.com/killindodo/nitrosense-linux.git
cd nitrosense-linux
```

### 2. Activate the Kernel Driver (One-Time)

Run the automated installer script:

```bash
sudo ./scripts/install_driver.sh
```

This script:
1. Compiles the `acer-nitro-ec` kernel module.
2. Installs it into `/lib/modules/$(uname -r)/updates/`.
3. Registers it with **DKMS** so it automatically rebuilds across kernel updates.
4. Configures `/etc/modules-load.d/acer-nitro-ec.conf` to load automatically on boot.
5. Installs `/etc/udev/rules.d/99-acer-nitro-ec.rules` so you can control fan speeds without root.

### 3. Desktop Integration (Optional)

To add NitroSense to your application launcher, desktop, and system PATH:

```bash
./install_desktop.sh
```

---

## Usage

Launch NitroSense from your application menu or terminal:

```bash
nitrosense
```

To launch minimized directly to the system tray on startup:

```bash
nitrosense --tray
```

---

## EC Register Architecture (AN515-42)

| Parameter | EC Register | Description |
| :--- | :--- | :--- |
| **CPU Fan Mode** | `0x22` | Auto (`0x04`), Turbo (`0x08`), Manual (`0x0C`) |
| **CPU Fan Speed** | `0x37` | PWM duty cycle (0–100%) |
| **CPU Fan RPM** | `0x13` (Low), `0x14` (High) | 16-bit integer RPM |
| **GPU Fan Mode** | `0x21` | Auto (`0x10`), Turbo (`0x20`), Manual (`0x30`) |
| **GPU Fan Speed** | `0x3A` | PWM duty cycle (0–100%) |
| **GPU Fan RPM** | `0x15` (Low), `0x16` (High) | 16-bit integer RPM |

---

## Author

**killindodo**
- GitHub: [@killindodo](https://github.com/killindodo)
- Repository: [https://github.com/killindodo/nitrosense-linux](https://github.com/killindodo/nitrosense-linux)

---

## License

GPL-2.0 / MIT
