# Beatbot for Home Assistant

HACS-compatible Home Assistant custom integration for **Beatbot** robotic pool cleaners (including the **Beatbot Sora 70**), built on Beatbot's official [`beatbot-cloud`](https://github.com/Beatbot-Robotics/beatbot-cloud-python) OpenAPI v1 SDK (`beatbot-cloud==0.4.4`).

## Features

- **OAuth2 PKCE login (no API key required):** Sign in with your standard Beatbot app account using Beatbot's public `home-assistant` OAuth2 client.
- **Real-time WebSocket push + REST reconciliation:** Receives instant `properties_changed` and online/offline events from Beatbot Cloud with a 10-minute reconciliation poll.
- **Pool-friendly availability:** Status, battery, error, and online connectivity entities remain available while the robot is submerged underwater (when Wi-Fi naturally disconnects).
- **Entities created:**
  - `vacuum.*` — Modern `StateVacuumEntity` (`VacuumActivity`) with dynamic `start`, `pause`, `stop`, and `return_to_base` support based on your robot's advertised capabilities.
  - `sensor.*_status` — Detailed semantic status (`cleaning`, `diving`, `emerge`, `clean_done`, `charging`, `dock`, etc.).
  - `sensor.*_battery` — Battery percentage (`%`).
  - `sensor.*_error` — Active error enum plus `active_errors` and `raw_error_code` attributes.
  - `binary_sensor.*_online` & `binary_sensor.*_problem` — Connectivity and active fault indicators.
  - `select.*_cleaning_mode` — Dynamically populated from your robot's advertised `work_mode_options`.
  - `switch.*_child_lock` & `switch.*_voice_do_not_disturb` — Created when advertised by the device.
  - `button.*` — Dynamically exposes every controllable parameterless cloud action advertised by your robot.
- **Diagnostics:** Full device/capability dump (OAuth tokens redacted) via **Settings → Devices & Services → Beatbot → Download diagnostics**.

## Installation

### Option 1: HACS / Home Assistant Marketplace (Custom Repository)

1. Open **HACS** (or **Marketplace**) in Home Assistant.
2. Open the menu (**⋮**) → **Custom repositories**.
3. Add this repository URL with category **Integration**.
4. Search for **Beatbot**, install it, and **restart Home Assistant**.

### Option 2: Manual Installation

1. Copy `custom_components/beatbot` into `/config/custom_components/beatbot` on your Home Assistant server.
2. **Restart Home Assistant** (HA installs `beatbot-cloud==0.4.4` automatically on startup).

## Setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Beatbot**.
3. Sign in with your Beatbot mobile app account in the OAuth browser window.
