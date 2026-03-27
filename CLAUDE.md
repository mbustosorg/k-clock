# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

k-clock is a Raspberry Pi voice-controlled LED clock. It listens for the wake word "hey clock" (via Picovoice Porcupine), then processes intents (via Picovoice Rhino) to control a Pixelblaze LED controller over the local network. It also adjusts brightness on a 15-minute schedule based on time of day, and fetches moon phase data from python-weather.

## Running

The app runs as a systemd service (`k-clock_service.service`) on a Raspberry Pi. The service calls `startup.sh`, which activates a virtualenv and runs:

```sh
python3 -m k-clock \
  --access_key <PICOVOICE_KEY> \
  --keyword_paths hey-clock_en_raspberry-pi_v4_0_0.ppn \
  --context_path k-clock-pattern_en_raspberry-pi_v4_0_0.rhn
```

To manage the service on the Pi:
```sh
sudo systemctl start k-clock
sudo systemctl stop k-clock
sudo systemctl status k-clock
journalctl -u k-clock -f
```

To run directly (for development):
```sh
python3 k-clock.py --access_key <KEY> --keyword_paths <path>.ppn --context_path <path>.rhn
```

Useful flags:
- `--show_audio_devices` — list available audio input devices
- `--show_inference_devices` — list available Porcupine inference devices
- `--audio_device_index <n>` — select audio device (default: -1)
- `--sensitivities <float>` — wake word sensitivity, 0.0–1.0 (default: 0.5)

## Dependencies

Install with:
```sh
pip install -r requirements.txt
```

The `pixelblaze-client` package source is available locally at:
`/Users/mauricio/.pyenv/versions/3.11.0rc2/lib/python3.11/site-packages/pixelblaze/pixelblaze.py`

The local development virtualenv is at `/Users/mauricio/Documents/development/projects/k-clock-venv`. The Pixelblaze is reachable from the development machine but requires a 10s enumeration timeout (`Pixelblaze.EnumerateAddresses(timeout=10000)`).


## Architecture

All logic is in a single file: `k-clock.py`.

**Flow:**
1. `main()` parses CLI args, then calls `asyncio.run(listen_and_process(...))`
2. `listen_and_process()` initializes Porcupine (wake word) and Rhino (intent), discovers the Pixelblaze named `"k-clock"` on the LAN via `Pixelblaze.EnumerateAddresses()`, and enters the main loop
3. Main loop: reads PCM audio from `PvRecorder`, feeds it to Porcupine every frame; every 15 minutes adjusts Pixelblaze brightness using a cosine curve (dim at night, brighter during the day)
4. On wake word detection: sets `wakeMode: 1` variable on the active Pixelblaze pattern, then listens for Rhino intent for up to 5 seconds; on timeout or completion sets `wakeMode: 0`

**Supported intents (defined in the `.rhn` Rhino context):**
- `setPattern` with slot `pattern`:
  - `time` → `pb.setActivePatternByName('Clock')`
  - `moon phase` → fetches moon phase from Oakland weather via `python_weather`, sets pattern to `moon phase` with `moonIndex` variable, then restores previous pattern after 5s
  - `random` → picks from `pattern_names_list`
  - `clock on` → sets `clockOn: 1` on active pattern, then calls `ensure_pattern_variables(pb, 1)` to sync all Clock patterns
  - `clock off` → sets `clockOn: 0` on active pattern, then calls `ensure_pattern_variables(pb, 0)` to sync all Clock patterns
- `nextPattern` with slot `player`:
  - `continue` → restores previous pattern + `pb.playSequencer()`
  - `pause` → restores previous pattern + `pb.pauseSequencer()`

**Pixelblaze patterns used:** `Clock Fire`, `Clock honeycomb`, `Clock`, `coronal mass ejection`, `spiral twirls 2D`, `pulse 2D`, `perlin fire wind`, `Coral Plasma`, `moon phase`

**Logs** rotate to `k-clock.log` (40KB, 5 backups) in the working directory.

## Key files

- `k-clock.py` — entire application
- `startup.sh` — launch script (activates venv at `/home/mauricio/.virtualenvs/k-clock`, passes Picovoice access key and `.ppn`/`.rhn` model paths; uses `--audio_device_index 3`)
- `k-clock_service.service` — systemd unit file
- `*.ppn` — Porcupine wake word model (Raspberry Pi, not committed)
- `*.rhn` — Rhino intent context model (Raspberry Pi, not committed)