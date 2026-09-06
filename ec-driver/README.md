# acer-nitro-ec

Linux kernel module (hwmon driver) that exposes Embedded Controller (EC) fan
control and temperature sensors via the standard hwmon sysfs interface for
Acer Nitro AN515/AN517 laptops.

## Supported models

- AN515-44, AN515-46, AN515-54, AN515-55, AN515-56, AN515-57, AN515-58
- AN517-55

## Features

- CPU and GPU fan speed readout (RPM)
- PWM duty-cycle control (0–255)
- Fan mode selection: Turbo / Manual / Auto
- Temperature readings: CPU, GPU, System

## Requirements

- Linux kernel headers for the running kernel
- `make`
- LLVM toolchain (`clang`, `llvm-ar`, …) — required by default for
  LLVM-built kernels such as CachyOS; can be disabled with `LLVM=0`

## Build & install

```bash
# Build (LLVM=1 is the default)
make

# Build without LLVM (GCC kernels)
make LLVM=0

# Install to the running kernel's module tree
sudo make install
```

## DKMS (auto-rebuild on kernel updates)

```bash
# Set the version in dkms.conf
VERSION=1.0.0

# Copy sources and register
sudo cp -r . /usr/src/acer-nitro-ec-$VERSION
sudo sed -i "s/@PKGVER@/$VERSION/" /usr/src/acer-nitro-ec-$VERSION/dkms.conf
sudo dkms add    acer-nitro-ec/$VERSION
sudo dkms build  acer-nitro-ec/$VERSION
sudo dkms install acer-nitro-ec/$VERSION
```

## Sysfs interface

After loading, the following files are available under
`/sys/class/hwmon/hwmonX/` (find the right `hwmonX` with
`grep -l acer_nitro_ec /sys/class/hwmon/*/name`):

| File          | Access | Description                                   |
| ------------- | ------ | --------------------------------------------- |
| `fan1_input`  | r      | CPU fan speed (RPM)                           |
| `fan2_input`  | r      | GPU fan speed (RPM)                           |
| `pwm1`        | rw     | CPU fan duty cycle (0–255)                    |
| `pwm2`        | rw     | GPU fan duty cycle (0–255)                    |
| `pwm1_enable` | rw     | CPU fan mode: `0`=Turbo, `1`=Manual, `2`=Auto |
| `pwm2_enable` | rw     | GPU fan mode: `0`=Turbo, `1`=Manual, `2`=Auto |
| `temp1_input` | r      | CPU temperature (m°C)                         |
| `temp2_input` | r      | GPU temperature (m°C)                         |
| `temp3_input` | r      | System temperature (m°C)                      |

Example — set CPU fan to manual at ~50% and read current speed:

```bash
HWMON=/sys/class/hwmon/$(grep -l acer_nitro_ec /sys/class/hwmon/*/name | cut -d/ -f5)
echo 1   | sudo tee $HWMON/pwm1_enable   # manual mode
echo 128 | sudo tee $HWMON/pwm1          # ~50% duty cycle
cat $HWMON/fan1_input                    # current RPM
```

## Debug / logging

```bash
# Enable verbose logging at load time
sudo modprobe acer-nitro-ec debug=1

# Or enable dynamic_debug at runtime (no reload needed)
echo "module acer_nitro_ec +p" | sudo tee /sys/kernel/debug/dynamic_debug/control

# Watch kernel messages
sudo dmesg -w | grep acer-nitro-ec
```

## Credits

EC register maps reverse-engineered from the
[Linux-NitroSense](https://github.com/JafarAkhondali/linux-nitroshark) project.
