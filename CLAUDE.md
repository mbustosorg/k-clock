# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

k-clock is a Raspberry Pi voice-controlled LED clock. It listens for the wake word "hey clock" (via Picovoice Porcupine), then processes intents (via Picovoice Rhino) to control a Pixelblaze LED controller over the local network. It also adjusts brightness on a 15-minute schedule based on time of day, and fetches moon phase data from python-weather.

## Running

The app runs as a systemd service (`k-clock_service.service`) on a Raspberry Pi. The service calls `startup.sh`, which activates a virtualenv and runs:

```sh
python3 k-clock.py \
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

The local development virtualenv is at `/Users/mauricio/Documents/development/projects/k-clock-venv`. The Pixelblaze is reachable from the development machine but requires a 10s enumeration timeout (`Pixelblaze.EnumerateAddresses(timeout=10000)`). The production code uses a 5s timeout.

## Architecture

All logic is in a single file: `k-clock.py`.

**Flow:**
1. `main()` parses CLI args, then calls `asyncio.run(listen_and_process(...))`
2. `listen_and_process()` initializes Porcupine (wake word) and Rhino (intent), discovers the Pixelblaze named `"k-clock"` on the LAN via `Pixelblaze.EnumerateAddresses(timeout=5000)`, builds on/off playlists via `on_and_off_playlists()`, sets the sequencer to the `on_list`, and enters the main loop
3. Main loop: reads PCM audio from `PvRecorder`, feeds it to Porcupine every frame; every 15 minutes adjusts Pixelblaze brightness using a cosine curve (dim at night, brighter during the day)
4. On wake word detection: switches active pattern to `"C wake word"`, then listens for Rhino intent for up to 5 seconds; on timeout restores the previous pattern and resumes the sequencer

**Pattern naming convention:**
- Patterns prefixed with `C ` (e.g. `C Clock Fire`) are the clock-on variants
- Patterns prefixed with `C- ` (e.g. `C- Clock Fire`) are the clock-off variants
- `on_and_off_playlists()` builds two playlist item lists by pairing these variants

**Supported intents (defined in the `.rhn` Rhino context):**
- `setPattern` with slot `pattern`:
  - `time` → `pb.setActivePatternByName('Clock')`
  - `moon phase` → fetches moon phase from Oakland weather via `python_weather`, sets pattern to `moon phase`, sets `sliderMoonIndex` control to `moon_phase_index / 8.0`, waits 5s, then restores previous pattern + resumes sequencer
  - `clock on` → switches sequencer playlist to `play_list['on_list']` and calls `pb.playSequencer()`
  - `clock off` → switches sequencer playlist to `play_list['off_list']` and calls `pb.playSequencer()`

**Moon phase mapping** (`MOON_PHASES` dict, indices 0–7):
`NEW_MOON`, `WAXING_CRESCENT`, `FIRST_QUARTER`, `WAXING_GIBBOUS`, `FULL_MOON`, `WANING_GIBBOUS`, `LAST_QUARTER`, `WANING_CRESCENT`

**Utility functions** (not called from the main loop — used for one-off device maintenance):
- `save_pattern_code(pb, pattern_name)` — downloads a single pattern's source to a `.js` file
- `migrate_clock_patterns(pb)` — downloads all `Clock*` patterns, replaces their clock scaffold section with the one from `Clock Scroll Out`, saves to `migration/`
- `upload_patterns_from_directory(pb)` — uploads all `.js` files from `migration/` back to the device
- `build_pattern_file_cache(pb)` — reads `.c` files from the device for patterns prefixed `C `

**Logs** rotate to `k-clock.log` (40KB, 5 backups) in the working directory.

## Key files

- `k-clock.py` — entire application
- `startup.sh` — launch script (activates venv at `/home/mauricio/.virtualenvs/k-clock`, passes Picovoice access key and `.ppn`/`.rhn` model paths; uses `--audio_device_index 3`)
- `k-clock_service.service` — systemd unit file
- `*.ppn` — Porcupine wake word model (Raspberry Pi, not committed)
- `*.rhn` — Rhino intent context model (Raspberry Pi, not committed)