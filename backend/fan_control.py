"""
Fan speed and mode controller for Acer Nitro 5.
Interacts with the acer-nitro-ec sysfs interface to switch between
Auto, Max/Turbo, Manual (Custom), and Smart Curve modes.
Includes hardware safety limits and auto-recovery on exit.
"""

import os
import atexit
from typing import Optional, Tuple


class FanMode:
    TURBO = 0       # 0 in hwmon: forced max speed (Nitro Turbo)
    MANUAL = 1      # 1 in hwmon: user-specified pwm value
    AUTO = 2        # 2 in hwmon: default firmware EC curve
    SMART_CURVE = 3 # Software-managed dynamic curve


# Default fan curve: (temp_c, fan_pct)
DEFAULT_CURVE = [
    (40, 20),
    (50, 35),
    (60, 50),
    (70, 70),
    (80, 85),
    (85, 100),
]


class FanController:
    def __init__(self, ec_hwmon_path: Optional[str] = None):
        self.ec_path = ec_hwmon_path
        self.active_mode = FanMode.AUTO
        self.target_cpu_pct = 50
        self.target_gpu_pct = 50
        self.synced = True
        self.curve = list(DEFAULT_CURVE)

        # Register safety shutdown
        atexit.register(self.safety_reset)

    def set_hwmon_path(self, path: Optional[str]):
        self.ec_path = path

    def is_ready(self) -> bool:
        if not self.ec_path or not os.path.exists(self.ec_path):
            return False
        return os.access(os.path.join(self.ec_path, "pwm1"), os.W_OK)

    def _write_sysfs(self, filename: str, val: int) -> bool:
        if not self.ec_path:
            return False
        filepath = os.path.join(self.ec_path, filename)
        try:
            with open(filepath, "w") as f:
                f.write(str(val))
            return True
        except Exception as e:
            return False

    def set_mode(self, mode: int) -> bool:
        """Sets fan control mode (Auto, Turbo, Manual, or Smart Curve)."""
        self.active_mode = mode
        if not self.is_ready():
            return False

        if mode == FanMode.AUTO:
            ok1 = self._write_sysfs("pwm1_enable", 2)
            ok2 = self._write_sysfs("pwm2_enable", 2)
            return ok1 and ok2
        elif mode == FanMode.TURBO:
            ok1 = self._write_sysfs("pwm1_enable", 0)
            ok2 = self._write_sysfs("pwm2_enable", 0)
            return ok1 and ok2
        elif mode in (FanMode.MANUAL, FanMode.SMART_CURVE):
            # Set to manual mode
            self._write_sysfs("pwm1_enable", 1)
            self._write_sysfs("pwm2_enable", 1)
            return self.apply_speeds(self.target_cpu_pct, self.target_gpu_pct)

        return False

    def apply_speeds(self, cpu_pct: int, gpu_pct: int) -> bool:
        """Sets target fan percentage (0-100%). Enforces safety limits."""
        # Hardware limits: keep CPU fan >= 20% to prevent thermal runaway
        self.target_cpu_pct = max(20, min(100, cpu_pct))
        self.target_gpu_pct = max(0, min(100, gpu_pct))

        if not self.is_ready() or self.active_mode not in (FanMode.MANUAL, FanMode.SMART_CURVE):
            return False

        # Scale 0-100% -> 0-255
        raw_cpu = int(round(self.target_cpu_pct * 255 / 100.0))
        raw_gpu = int(round(self.target_gpu_pct * 255 / 100.0))

        ok1 = self._write_sysfs("pwm1", raw_cpu)
        ok2 = self._write_sysfs("pwm2", raw_gpu)
        return ok1 and ok2

    def evaluate_smart_curve(self, max_temp: float) -> int:
        """Computes target fan speed % from thermal curve."""
        if max_temp <= self.curve[0][0]:
            return self.curve[0][1]
        if max_temp >= self.curve[-1][0]:
            return self.curve[-1][1]

        for i in range(len(self.curve) - 1):
            t1, s1 = self.curve[i]
            t2, s2 = self.curve[i + 1]
            if t1 <= max_temp <= t2:
                fraction = (max_temp - t1) / float(t2 - t1)
                return int(round(s1 + fraction * (s2 - s1)))

        return 50

    def tick_safety_and_curve(self, cpu_temp: Optional[float], gpu_temp: Optional[float]):
        """Called on periodic sensor updates to handle smart curves and safety."""
        valid_temps = [t for t in (cpu_temp, gpu_temp) if t is not None and t > 0]
        if not valid_temps:
            return

        peak_temp = max(valid_temps)

        # Thermal Emergency Override: If temp > 88°C, force Turbo
        if peak_temp >= 88.0:
            if self.active_mode != FanMode.TURBO:
                self.set_mode(FanMode.TURBO)
            return

        # Smart curve update
        if self.active_mode == FanMode.SMART_CURVE:
            speed = self.evaluate_smart_curve(peak_temp)
            self.apply_speeds(speed, speed)
        elif self.active_mode == FanMode.MANUAL:
            # Safety floor if temp > 80°C in manual mode
            if peak_temp >= 82.0 and self.target_cpu_pct < 70:
                self.apply_speeds(max(70, self.target_cpu_pct), max(70, self.target_gpu_pct))

    def safety_reset(self):
        """Always restore firmware Auto mode when the application exits."""
        if self.ec_path and os.path.exists(self.ec_path):
            try:
                self._write_sysfs("pwm1_enable", 2)
                self._write_sysfs("pwm2_enable", 2)
            except Exception:
                pass
