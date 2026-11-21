# Beatbot Custom Integration for Home Assistant

Custom Home Assistant integration for **Beatbot** robotic pool cleaners (including **Sora 70**) built on Beatbot's official [`beatbot-cloud`](https://github.com/Beatbot-Robotics/beatbot-cloud-python) OpenAPI v1 SDK (`beatbot-cloud==0.4.4`).

## Features

- **Zero-API-key OAuth2 PKCE login** — authenticates with your standard Beatbot app account using Beatbot's public `home-assistant` OAuth client.
- **Real-time WebSocket push** (`wss://na-iot.beatbot.com/openapi/v1/ha/ws`) with automatic 10-minute REST reconciliation.
- **Vacuum entity** (`vacuum.*`) with dynamic feature flags (`start`, `pause`, `stop`, `return_to_base`) matching your robot's advertised capabilities.
- **Sensors & Binary Sensors:**
  - `sensor.*_status` (detailed Beatbot state: cleaning, diving, emerging, clean_done, docked, charging, etc.)
  - `sensor.*_battery` (%)
  - `sensor.*_error` (with decoded `active_errors` and `raw_error_code` attributes)
  - `binary_sensor.*_online` (stays available even when submerged underwater so you can automate on Wi-Fi disconnect/reconnect)
  - `binary_sensor.*_problem` (active fault indicator)
- **Controls (created dynamically when advertised by your robot):**
  - `select.*_cleaning_mode` (`select.work_mode`)
  - `switch.*_child_lock` & `switch.*_voice_do_not_disturb`
  - `button.*` for every controllable parameterless cloud action advertised by your device
- **Diagnostics:** Full device discovery and capability dump (with OAuth tokens redacted) via **Settings → Devices & Services → Beatbot → Download diagnostics**.

## Installation

1. Copy the `custom_components/beatbot` folder into your Home Assistant `/config/custom_components/beatbot` directory (via Samba Share, Studio Code Server, or Terminal & SSH).
2. **Restart Home Assistant** (HA will automatically install `beatbot-cloud==0.4.4` on startup).
3. Go to **Settings → Devices & Services → Add Integration** and search for **Beatbot**.
4. Sign in with your Beatbot account in the OAuth browser window.

## Note on Future Home Assistant Core Merge

When upstream PR [home-assistant/core#190806](https://github.com/home-assistant/core/pull/190806) merges into Home Assistant Core, you can either keep this custom component (which includes controls beyond Core's initial sensor-only PR) or delete `/config/custom_components/beatbot` and restart to switch to the built-in Core integration.
