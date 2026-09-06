"""
Hardware sensor reader for Acer Nitro 5 (AN515-42 and compatible models).
Reads CPU, dGPU (RX 560X), iGPU (Vega) temperatures, power, clocks,
and Embedded Controller (EC) fan RPM and PWM states.
"""

import os
import glob
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


@dataclass
class ThermalSnapshot:
    # CPU
    cpu_temp: Optional[float] = None
    cpu_label: str = "AMD Ryzen"
    
    # Discrete GPU (RX 560X)
    dgpu_temp: Optional[float] = None
    dgpu_power_w: Optional[float] = None
    dgpu_sclk_mhz: Optional[int] = None
    dgpu_mclk_mhz: Optional[int] = None
    dgpu_active: bool = False
    dgpu_name: str = "Radeon RX 560X"
    
    # Integrated GPU (Vega)
    igpu_temp: Optional[float] = None
    igpu_name: str = "Radeon Vega"
    
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


def _read_str(path: str) -> Optional[str]:
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _read_int(path: str) -> Optional[int]:
    val = _read_str(path)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            return None
    return None


class SensorMonitor:
    def __init__(self):
        self.k10temp_hwmon: Optional[str] = None
        self.dgpu_hwmon: Optional[str] = None
        self.igpu_hwmon: Optional[str] = None
        self.ec_hwmon: Optional[str] = None
        self.rescan_devices()

    def rescan_devices(self):
        """Discovers hwmon nodes for CPU, GPUs, and EC."""
        self.k10temp_hwmon = None
        self.dgpu_hwmon = None
        self.igpu_hwmon = None
        self.ec_hwmon = None

        for hwmon in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
            name = _read_str(os.path.join(hwmon, "name"))
            if not name:
                continue

            if name in ("k10temp", "coretemp", "zenpower"):
                self.k10temp_hwmon = hwmon
            elif name == "acer_nitro_ec":
                self.ec_hwmon = hwmon
            elif name == "amdgpu":
                device_link = os.path.realpath(os.path.join(hwmon, "device"))
                # Discrete GPU (RX 560X) is PCI 01:00.0 on AN515-42
                if "0000:01:00.0" in device_link:
                    self.dgpu_hwmon = hwmon
                elif "0000:04:00.0" in device_link:
                    self.igpu_hwmon = hwmon
                elif not self.dgpu_hwmon:
                    self.dgpu_hwmon = hwmon
                elif not self.igpu_hwmon:
                    self.igpu_hwmon = hwmon

    def poll(self) -> ThermalSnapshot:
        """Reads real-time thermal & fan metrics."""
        # Periodically check if EC driver appeared
        if not self.ec_hwmon or not os.path.exists(self.ec_hwmon):
            self.rescan_devices()

        snap = ThermalSnapshot()

        # 1. CPU Temperature (k10temp)
        if self.k10temp_hwmon:
            # Prefer Tctl (temp1)
            raw = _read_int(os.path.join(self.k10temp_hwmon, "temp1_input"))
            if raw and raw > 0:
                snap.cpu_temp = raw / 1000.0

        # 2. Discrete GPU (RX 560X)
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

        # 3. Integrated GPU (Vega)
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

            # Fallback for CPU temp if k10temp not available
            if snap.cpu_temp is None:
                ec_cpu_temp = _read_int(os.path.join(self.ec_hwmon, "temp1_input"))
                if ec_cpu_temp and ec_cpu_temp > 0:
                    snap.cpu_temp = ec_cpu_temp / 1000.0

            # Fallback for GPU temp if amdgpu asleep
            if snap.dgpu_temp is None:
                ec_gpu_temp = _read_int(os.path.join(self.ec_hwmon, "temp2_input"))
                if ec_gpu_temp and ec_gpu_temp > 0:
                    snap.dgpu_temp = ec_gpu_temp / 1000.0

        return snap
