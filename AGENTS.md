# AGENTS.md

## Repo Structure

This repo (`jonjon1123/dotty-stackchan`) is a fork of `BrettKinny/dotty-stackchan`. It
contains a single git submodule at `firmware/` pointing to `jonjon1123/dotty-firmware`.

> **Note:** This is a fork. The primary reference docs are in `README-UPDATED.md`,
> not the original `README.md` from upstream.

### Fork Chain

```
m5stack/StackChan          (original upstream)
       │
BrettKinny/StackChan       (dotty fork — firmware customizations)
       │
jonjon1123/dotty-firmware   (your firmware fork — submodule source)
```

```
BrettKinny/dotty-stackchan  (server-side stack fork)
       │
jonjon1123/dotty-stackchan  (this repo)
```

### Remote Layout

**This repo** (`jonjon1123/dotty-stackchan`):

| Remote   | URL                                                   | Purpose                        |
|----------|-------------------------------------------------------|--------------------------------|
| `origin` | `https://github.com/jonjon1123/dotty-stackchan.git`   | Your fork (push target)        |
| `upstream` | `https://github.com/BrettKinny/dotty-stackchan.git` | Pulls from the dotty stack fork |

**Submodule** (`firmware/` — `jonjon1123/dotty-firmware`):

| Remote     | URL                                                 | Purpose                              |
|------------|-----------------------------------------------------|--------------------------------------|
| `origin`   | `https://github.com/jonjon1123/dotty-firmware.git`  | Your firmware fork (push target)     |
| `fork`     | `https://github.com/BrettKinny/StackChan.git`       | Pulls from the BrettKinny fork       |
| `upstream` | `https://github.com/m5stack/StackChan.git`          | Pulls from the original m5stack repo |

### Submodule Configuration

`.gitmodules` in the parent repo pins the submodule to:
- **URL:** `https://github.com/jonjon1123/dotty-firmware.git`
- **Branch:** `dotty`

The local `.git/config` must match `.gitmodules`. If they drift (e.g. after cloning),
run:

```bash
git submodule sync
```

## Workflow: Pulling Updates Into the Submodule

All commands below are run from the `firmware/` directory.

### Pull from BrettKinny/StackChan (fork updates)

```bash
cd firmware
git fetch fork
git merge fork/dotty
```

### Pull from m5stack/StackChan (upstream updates)

```bash
cd firmware
git fetch upstream
git merge upstream/main
```

### Push updated submodule to your fork

```bash
cd firmware
git push origin dotty
```

### Update the submodule pointer in the parent repo

After pushing the submodule, update the parent repo to point at the new commit:

```bash
cd ..
git add firmware
git commit -m "chore: update firmware submodule"
git push origin main
```

## Workflow: Pulling Updates Into the Parent Repo

```bash
git fetch upstream
git merge upstream/main
git push origin main
```

## Quick Reference

| Task                              | Command                                                  |
|-----------------------------------|----------------------------------------------------------|
| Sync submodule URL after clone    | `git submodule sync`                                     |
| Init submodule after fresh clone  | `git submodule update --init`                            |
| Update submodule to latest remote | `cd firmware && git pull origin dotty`                   |
| Check submodule status            | `git submodule status`                                   |
| List submodule remotes            | `git -C firmware remote -v`                              |

## Firmware

### Repository Structure

```
firmware/
├── app/              # Flutter mobile app (DO NOT MODIFY)
├── firmware/         # ESP-IDF firmware (PRIMARY WORK AREA)
│   ├── main/         # Main component source code
│   │   ├── hal/      # Hardware Abstraction Layer
│   │   ├── stackchan/ # Core StackChan logic (avatar, motion, modifiers)
│   │   ├── apps/     # Mooncake app modules
│   │   ├── assets/   # Fonts, sound effects, binary assets
│   │   └── main.cpp  # Entry point (app_main)
│   ├── tests/        # Host-side unit tests
│   ├── patches/      # Patches applied to dependencies
│   ├── xiaozhi-esp32/ # Cloned dependency (DO NOT MODIFY)
│   ├── components/   # Cloned dependencies (DO NOT MODIFY)
│   └── managed_components/ # ESP-IDF managed deps (DO NOT MODIFY)
├── remote/           # Remote controller firmware (DO NOT MODIFY)
└── server/           # Go backend server (DO NOT MODIFY)
```

### Do NOT Modify

These directories are either upstream code, cloned dependencies, or build artifacts. Changes here will be overwritten or break the sync with upstream:

- `app/` - Upstream StackChan mobile app
- `server/` - Upstream StackChan server
- `remote/` - Upstream StackChan remote controller
- `firmware/xiaozhi-esp32/` - Cloned from `78/xiaozhi-esp32` (v2.2.4), patched at build time
- `firmware/components/` - Cloned dependencies (mooncake, smooth_ui_toolkit, ArduinoJson, esp-now)
- `firmware/managed_components/` - ESP-IDF component manager dependencies
- `firmware/build/` - Build output
- `firmware/sdkconfig` - Generated config (git-ignored, derived from `sdkconfig.defaults`)
- `firmware/sdkconfig.old` - Previous config (git-ignored)

### Safe to Modify

Only modify files within these directories:

- `firmware/main/hal/` - Hardware abstraction layer (HAL singleton, board bridge, drivers)
- `firmware/main/stackchan/` - Core StackChan logic (avatar, motion, modifiers, animations)
- `firmware/main/apps/` - Mooncake application modules
- `firmware/main/assets/` - Custom fonts, sound effects, asset binaries
- `firmware/main/main.cpp` - Entry point
- `firmware/main/Kconfig.projbuild` - Build configuration options
- `firmware/main/idf_component.yml` - ESP-IDF component dependencies
- `firmware/main/CMakeLists.txt` - Build rules
- `firmware/CMakeLists.txt` - Top-level CMake config
- `firmware/sdkconfig.defaults` - Default SDK configuration
- `firmware/partitions.csv` - Partition table
- `firmware/tests/` - Host-side unit tests
- `firmware/patches/` - Patches for cloned dependencies
- `firmware/fetch_repos.py` - Dependency fetching script
- `firmware/repos.json` - Dependency repository definitions
- `firmware/.clang-format` - Code formatting rules

### Architecture

#### HAL (Hardware Abstraction Layer)

The `Hal` class (`firmware/main/hal/hal.h`) is a **singleton** accessed via `GetHAL()`. It provides a unified API for all hardware interactions. Application code never talks to drivers directly.

Key domains: System, Display (LVGL), BLE, WiFi/Network, IMU, Servos, RGB LEDs, WebSocket, ESP-NOW, RTC, OTA, Audio.

The `hal_bridge` namespace (`firmware/main/hal/board/hal_bridge.h`) bridges the StackChan HAL with the xiaozhi-esp32 board SDK.

#### StackChan Core

- `StackChan` class (`firmware/main/stackchan/stackchan.h`) - Main robot controller
- `Modifiable` / `Modifier` pattern (`firmware/main/stackchan/modifiable.h`) - Plugin system for behaviors
- Avatar, Motion, and NeonLight subsystems

#### App Framework

Uses the **Mooncake** framework. Apps are installed in `main.cpp` via `GetMooncake().installApp()`. The firmware runs StackChan apps first, then transitions to xiaozhi-esp32 AI agent mode.

#### xiaozhi-esp32 Integration

The xiaozhi-esp32 code is cloned into `firmware/xiaozhi-esp32/` and referenced directly via CMake. Its source files are compiled as part of the main component. A patch file (`firmware/patches/xiaozhi-esp32.patch`) is applied during `fetch_repos.py`.

### Build Commands

#### ESP-IDF Environment Setup

**Before running any `idf.py` commands**, the ESP-IDF toolchain environment must be sourced. The ESP-IDF framework installs to platform-specific default locations. If multiple ESP-IDF versions are installed, the folder name may include a version suffix (e.g., `Espressif-v5.5.4`).

| Platform | Default Install Location |
|----------|------------------------|
| **Windows** | `C:\Espressif` or `C:\Espressif-vX.Y.Z` |
| **macOS** | `~/Espressif` or `~/Espressif-vX.Y.Z` |
| **Linux** | `~/esp` or `~/esp/esp-idf` |

Each installation includes an export script that sets up environment variables (toolchain paths, IDF paths, etc.) for the current shell session:

| Platform | Export Script |
|----------|---------------|
| **Windows (PowerShell)** | `<install_dir>/frameworks/esp-idf-vX.Y.Z/export.ps1` |
| **Windows (CMD)** | `<install_dir>/frameworks/esp-idf-vX.Y.Z/export.bat` |
| **macOS / Linux** | `<install_dir>/frameworks/esp-idf-vX.Y.Z/export.sh` |

**Example (Windows PowerShell):**
```powershell
& "C:\Espressif-v5.5.4\frameworks\esp-idf-v5.5.4\export.ps1"
```

**Example (macOS / Linux):**
```bash
source ~/esp/esp-idf/export.sh
```

Once the environment is sourced, the following commands are available from the `firmware/` directory:

```bash
# Fetch/update all cloned dependencies
python3 ./fetch_repos.py

# Configure (first time or after sdkconfig changes)
idf.py menuconfig

# Build
idf.py build

# Flash to device
idf.py flash

# Monitor serial output
idf.py monitor
```