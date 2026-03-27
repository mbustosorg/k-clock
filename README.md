# k-clock

A voice-controlled LED clock running on a Raspberry Pi. Say "hey clock" to wake it, then speak a command to change patterns, show the moon phase, or toggle the clock display. LED animations are driven by a [Pixelblaze](https://electromage.com/pixelblaze) controller over the local network.

## Hardware

- Raspberry Pi (any model with audio input)
- Pixelblaze LED controller named `k-clock` on the local network
- USB microphone or audio input device

## How it works

1. The Pi continuously listens for the wake word **"hey clock"** (via [Picovoice Porcupine](https://picovoice.ai/platform/porcupine/))
2. On detection, the active pattern enters wake mode — the border LEDs pulse to signal the clock is listening
3. You have 5 seconds to speak a command, which is parsed by [Picovoice Rhino](https://picovoice.ai/platform/rhino/)
4. The command controls the Pixelblaze over WebSocket
5. Every 15 minutes, brightness is adjusted automatically on a cosine curve (dim at night, brighter during the day)

## Voice commands

| Phrase | Action |
|---|---|
| "show the time" | Switch to the `Clock` pattern |
| "show the moon phase" | Fetch today's moon phase, display it for 5s, then return |
| "random pattern" | Pick a random pattern from the playlist |
| "clock on" | Enable the clock overlay on all Clock patterns |
| "clock off" | Disable the clock overlay, trigger scroll-out on all Clock patterns |
| "continue" | Resume the pattern sequencer |
| "pause" | Pause the pattern sequencer |

## Setup

### Dependencies

Requires Python 3.11+ and a [Picovoice access key](https://console.picovoice.ai/).

```sh
pip install -r requirements.txt
```

### Picovoice models

Two model files are required (not committed — generate from the Picovoice Console):

- `hey-clock_en_raspberry-pi_v4_0_0.ppn` — Porcupine wake word model
- `k-clock-pattern_en_raspberry-pi_v4_0_0.rhn` — Rhino intent context model

### Running directly

```sh
python3 k-clock.py \
  --access_key <PICOVOICE_KEY> \
  --keyword_paths hey-clock_en_raspberry-pi_v4_0_0.ppn \
  --context_path k-clock-pattern_en_raspberry-pi_v4_0_0.rhn
```

Useful flags:

| Flag | Description |
|---|---|
| `--show_audio_devices` | List available audio input devices |
| `--show_inference_devices` | List available Porcupine inference devices |
| `--audio_device_index <n>` | Select audio device (default: -1) |
| `--sensitivities <float>` | Wake word sensitivity 0.0–1.0 (default: 0.5) |

### Running as a systemd service

```sh
sudo systemctl start k-clock
sudo systemctl stop k-clock
sudo systemctl status k-clock
journalctl -u k-clock -f
```

The service unit is defined in `k-clock_service.service`. It calls `startup.sh`, which activates the virtualenv and passes the access key and model paths.

## Pixelblaze patterns

The `migration/` directory contains JavaScript pattern files for the Pixelblaze. Each pattern uses a shared clock scaffold that provides:

- **Clock display** — 4-digit 12-hour clock with scrolling digit transitions
- **Wake mode** — border LEDs (top row, bottom row, left/right edges) cycle saturation on a 500ms pulse while listening
- **Scroll out / scroll in** — digits animate off-screen and back when the clock is toggled
- **Pluggable background** — each pattern supplies its own `beforeRenderBackground` / `renderBackground` functions; the scaffold calls them automatically

### Pattern list

| Pattern | Background |
|---|---|
| Clock | Solid color |
| Clock Color Cube | 3D color cube animation |
| Clock Color Cube & Twinkles | Color cube with twinkle overlay |
| Clock Fire | Fire simulation |
| Clock Flower | Flower/petal animation |
| Clock Honeycomb | Honeycomb grid |
| Clock Honeycomb Transform | Transformed honeycomb |
| Clock Scroll Out | Cube fire (template / reference) |
| Clock Sun rays through trees | Radial sun ray effect |
| Clock color twinkles | Color twinkle field |
| Clock lissajou | Lissajous figure |
| Clock meatballs | Metaball blobs |
| Clock Coronal Ejection | Coronal mass ejection plasma |
| Clock spotlights / rotation 3D | 3D rotating spotlights |
| Clock wake word | Wake word visualizer |
| moon phase | Moon phase display |

## Files

```
k-clock.py               # Entire application (single file)
startup.sh               # Launch script for the Pi (activates venv, passes args)
k-clock_service.service  # systemd unit file
requirements.txt         # Python dependencies
migration/               # Pixelblaze JS pattern files
```

## Logs

Rotating log file at `k-clock.log` in the working directory (40 KB, 5 backups).