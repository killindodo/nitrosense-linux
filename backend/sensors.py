"""
Hardware sensor reader for Acer Nitro laptops.
Dynamically discovers and monitors CPU, discrete GPU, integrated GPU,
and Embedded Controller (EC) fan RPM and PWM states.

Privacy & Security:
- 100% local, offline monitoring with zero telemetry.
- No network queries, no IP/MAC reading, and no hardware serial/UUID collection.
- All hardware paths and model strings are detected dynamically without hardcoding.
"""

import os
import re
import glob
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


def _read_str(path: str) -> Optional[str]:
    """Safely reads a single line from a sysfs or procfs entry."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _read_int(path: str) -> Optional[int]:
    """Safely reads an integer from a sysfs entry."""
    val = _read_str(path)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            return None
    return None


def get_system_model() -> str:
    """
    Dynamically identifies the laptop model without hardcoding.
    Returns e.g. 'Acer Nitro AN515-42' or 'Acer Nitro Series'.
    """
    vendor = _read_str("/sys/class/dmi/id/sys_vendor") or ""
    product = _read_str("/sys/class/dmi/id/product_name") or ""

    if vendor and product:
        # Avoid duplicate vendor name if product already includes it
        if vendor.lower() in product.lower():
            return product
        return f"{vendor} {product}"
    elif product:
        return product
    return "Acer Nitro Series"


def get_cpu_model_name() -> str:
    """
    Dynamically reads CPU model name from /proc/cpuinfo.
    Cleans up redundant marketing suffixes.
    """
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    raw = line.split(":", 1)[1].strip()
                    clean = raw
                    for noise in [
                        " with Radeon Vega Mobile Gfx",
                        " with Radeon Graphics",
                        " Processor",
                        " CPU",
                    ]:
                        clean = clean.replace(noise, "")
                    return clean
    except Exception:
        pass
    return "Processor"


def get_gpu_descriptions() -> Dict[str, str]:
    """
    Dynamically extracts concise GPU names from lspci.
    Returns mapping of PCI slot (e.g. '0000:01:00.0') to clean GPU name.
    """
    gpu_names: Dict[str, str] = {}
    try:
        out = subprocess.check_output(["lspci"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if "controller:" in line and any(k in line for k in ["VGA", "3D", "Display"]):
                slot_id = line.split()[0]
                if not slot_id.startswith("0000:"):
                    slot_id = f"0000:{slot_id}"
                desc = line.split("controller:", 1)[1].strip()
                # Remove common vendor prefixes
                desc = re.sub(
                    r"^(Advanced Micro Devices, Inc\. \[AMD/ATI\]|NVIDIA Corporation|Intel Corporation)\s*",
                    "",
                    desc,
                )
                desc = re.sub(r"\s*\(rev\s+[0-9a-fA-F]+\)\s*$", "", desc)

                # Prefer text inside brackets if available
                bracket_match = re.search(r"\[(.*?)\]", desc)
                if bracket_match:
                    name_candidate = bracket_match.group(1)
                    if "/" in name_candidate:
                        # Extract first variant or concise family
                        name_candidate = name_candidate.split("/")[0].strip()
                    gpu_names[slot_id] = name_candidate
                else:
                    gpu_names[slot_id] = desc
    except Exception:
        pass
    return gpu_names


@dataclass
class ThermalSnapshot:
    # System / Laptop Model
    system_model: str = "Acer Nitro"

    # CPU
    cpu_temp: Optional[float] = None
    cpu_label: str = "CPU Core"

    # Discrete GPU
    dgpu_temp: Optional[float] = None
    dgpu_power_w: Optional[float] = None
    dgpu_sclk_mhz: Optional[int] = None
    dgpu_mclk_mhz: Optional[int] = None
    dgpu_active: bool = False
    dgpu_name: str = "Discrete GPU"

    # Integrated GPU
    igpu_temp: Optional[float] = None
    igpu_name: str = "Integrated GPU"

    # Fans (via acer-nitro-ec)
    ec_available: bool = False
    ec_writable: bool = False
    ec_path: Optional[str] = None

    cpu_fan_rpm: int = 0
    gpu_fan_rpm: int = 0

    cpu_fan_pct: int = 0
    gpu_fan_pct: int = 0

    # 0 = Turbo, 1 = Manual, 2 = Auto
    cpu_fan_mode: int = 2
    gpu_fan_mode: int = 2


class SensorMonitor:
    def __init__(self):
        self.system_model = get_system_model()
        self.cpu_name = get_cpu_model_name()

        self.cpu_hwmon: Optional[str] = None
        self.dgpu_hwmon: Optional[str] = None
        self.igpu_hwmon: Optional[str] = None
        self.ec_hwmon: Optional[str] = None

        self.dgpu_name: str = "Discrete GPU"
        self.igpu_name: str = "Integrated GPU"

        self.rescan_devices()

    def rescan_devices(self):
        """Dynamically scans sysfs and hwmon to map sensors without hardcoding."""
        self.cpu_hwmon = None
        self.dgpu_hwmon = None
        self.igpu_hwmon = None
        self.ec_hwmon = None

        # 1. Fetch GPU hardware labels
        gpu_labels = get_gpu_descriptions()

        # 2. Inspect all PCI display controllers
        pci_gpus: Dict[str, Dict[str, Any]] = {}
        for dev_path in sorted(glob.glob("/sys/bus/pci/devices/*")):
            class_path = os.path.join(dev_path, "class")
            if not os.path.exists(class_path):
                continue
            pci_class = _read_str(class_path) or ""
            # VGA (0x0300), 3D (0x0302), Display (0x0380)
            if pci_class.startswith(("0x0300", "0x0302", "0x0380")):
                slot = os.path.basename(dev_path)
                boot_vga_path = os.path.join(dev_path, "boot_vga")
                is_boot = (_read_str(boot_vga_path) == "1") if os.path.exists(boot_vga_path) else False

                hw_subdirs = glob.glob(os.path.join(dev_path, "hwmon", "hwmon*"))
                hw_dir = hw_subdirs[0] if hw_subdirs else None

                pci_gpus[dev_path] = {
                    "slot": slot,
                    "boot_vga": is_boot,
                    "hwmon": hw_dir,
                    "name": gpu_labels.get(slot, "GPU"),
                }

        # Assign discrete vs integrated based on boot_vga and controller type
        for dev_path, info in pci_gpus.items():
            if info["boot_vga"]:
                self.igpu_hwmon = info["hwmon"]
                self.igpu_name = info["name"] or "Integrated GPU"
            else:
                self.dgpu_hwmon = info["hwmon"]
                self.dgpu_name = info["name"] or "Discrete GPU"

        # 3. Discover all hwmon nodes (CPU, EC, and fallback GPU)
        for hwmon in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
            name = _read_str(os.path.join(hwmon, "name"))
            if not name:
                continue

            # CPU thermals: k10temp, coretemp, zenpower, cpu_thermal
            if name in ("k10temp", "coretemp", "zenpower", "cpu_thermal"):
                self.cpu_hwmon = hwmon
            elif name == "acer_nitro_ec":
                self.ec_hwmon = hwmon
            elif name in ("amdgpu", "nouveau", "nvidia"):
                # If hwmon not linked via PCI subpath, match via device link
                dev_link = os.path.realpath(os.path.join(hwmon, "device"))
                if dev_link in pci_gpus:
                    if pci_gpus[dev_link]["boot_vga"]:
                        self.igpu_hwmon = hwmon
                    else:
                        self.dgpu_hwmon = hwmon
                elif not self.dgpu_hwmon:
                    self.dgpu_hwmon = hwmon
                elif not self.igpu_hwmon:
                    self.igpu_hwmon = hwmon

    def poll(self) -> ThermalSnapshot:
        """Reads real-time thermal & fan metrics without hardcoded values."""
        if not self.ec_hwmon or not os.path.exists(self.ec_hwmon):
            self.rescan_devices()

        snap = ThermalSnapshot(
            system_model=self.system_model,
            cpu_label=self.cpu_name,
            dgpu_name=self.dgpu_name,
            igpu_name=self.igpu_name,
        )

        # 1. CPU Temperature
        if self.cpu_hwmon:
            # Check temp1_input (Tctl or Core package)
            raw = _read_int(os.path.join(self.cpu_hwmon, "temp1_input"))
            if raw and raw > 0:
                snap.cpu_temp = raw / 1000.0

        # 2. Discrete GPU
        if self.dgpu_hwmon:
            raw_temp = _read_int(os.path.join(self.dgpu_hwmon, "temp1_input"))
            raw_pwr = _read_int(os.path.join(self.dgpu_hwmon, "power1_input"))
            raw_sclk = _read_int(os.path.join(self.dgpu_hwmon, "freq1_input"))
            raw_mclk = _read_int(os.path.join(self.dgpu_hwmon, "freq2_input"))

            if raw_temp and raw_temp > 0:
                snap.dgpu_temp = raw_temp / 1000.0
                snap.dgpu_active = True
            else:
                snap.dgpu_temp = None
                snap.dgpu_active = False

            if raw_pwr and raw_pwr > 0:
                snap.dgpu_power_w = raw_pwr / 1_000_000.0

            if raw_sclk and raw_sclk > 0:
                snap.dgpu_sclk_mhz = int(raw_sclk / 1_000_000.0)

            if raw_mclk and raw_mclk > 0:
                snap.dgpu_mclk_mhz = int(raw_mclk / 1_000_000.0)

        # 3. Integrated GPU
        if self.igpu_hwmon:
            raw_temp = _read_int(os.path.join(self.igpu_hwmon, "temp1_input"))
            if raw_temp and raw_temp > 0:
                snap.igpu_temp = raw_temp / 1000.0

        # 4. Embedded Controller (Fans & Modes)
        if self.ec_hwmon and os.path.exists(self.ec_hwmon):
            snap.ec_available = True
            snap.ec_path = self.ec_hwmon
            snap.ec_writable = os.access(os.path.join(self.ec_hwmon, "pwm1"), os.W_OK)

            # Fan RPMs
            cpu_rpm = _read_int(os.path.join(self.ec_hwmon, "fan1_input"))
            gpu_rpm = _read_int(os.path.join(self.ec_hwmon, "fan2_input"))
            if cpu_rpm is not None:
                snap.cpu_fan_rpm = max(0, cpu_rpm)
            if gpu_rpm is not None:
                snap.gpu_fan_rpm = max(0, gpu_rpm)

            # Fan PWM (0-255 -> 0-100%)
            cpu_pwm = _read_int(os.path.join(self.ec_hwmon, "pwm1"))
            gpu_pwm = _read_int(os.path.join(self.ec_hwmon, "pwm2"))
            if cpu_pwm is not None:
                snap.cpu_fan_pct = int(round(cpu_pwm * 100 / 255.0))
            if gpu_pwm is not None:
                snap.gpu_fan_pct = int(round(gpu_pwm * 100 / 255.0))

            # Modes (0=Turbo, 1=Manual, 2=Auto)
            cpu_mode = _read_int(os.path.join(self.ec_hwmon, "pwm1_enable"))
            gpu_mode = _read_int(os.path.join(self.ec_hwmon, "pwm2_enable"))
            if cpu_mode is not None:
                snap.cpu_fan_mode = cpu_mode
            if gpu_mode is not None:
                snap.gpu_fan_mode = gpu_mode

            # Fallback for CPU temp if CPU hwmon not read
            if snap.cpu_temp is None:
                ec_cpu = _read_int(os.path.join(self.ec_hwmon, "temp1_input"))
                if ec_cpu and ec_cpu > 0:
                    snap.cpu_temp = ec_cpu / 1000.0

            # Fallback for GPU temp if discrete GPU sleeping
            if snap.dgpu_temp is None:
                ec_gpu = _read_int(os.path.join(self.ec_hwmon, "temp2_input"))
                if ec_gpu and ec_gpu > 0:
                    snap.dgpu_temp = ec_gpu / 1000.0

        return snap
