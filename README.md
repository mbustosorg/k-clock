# k-clock

A voice-controlled LED clock running on a Raspberry Pi. Say "hey clock" to wake it, then speak a command to change patterns, show the moon phase, or toggle the clock display. LED animations are driven by a [Pixelblaze](https://electromage.com/pixelblaze) controller over the local network.

## Hardware

- Raspberry Pi (any model with audio input)
- Pixelblaze LED controller named `k-clock` on the local network
- USB microphone or audio input device

## How it works

1. The Pi continuously listens for the wake word **"hey clock"** (via [Picovoice Porcupine](https://picovoice.ai/platform/porcupine/))
2. On detection, the active pattern switches to `C wake word` to signal the clock is listening
3. You have 5 seconds to speak a command, which is parsed by [Picovoice Rhino](https://picovoice.ai/platform/rhino/)
4. The command controls the Pixelblaze over WebSocket
5. Every 15 minutes, brightness is adjusted automatically on a cosine curve (dim at night, brighter during the day)

## Voice commands

| Phrase                      | Action |
|-----------------------------|---|
| "set pattern to moon phase" | Fetch today's moon phase, display it for 5s, then return |
| "set pattern to clock on"   | Switch sequencer to clock-on playlist (`C ` patterns) |
| "set pattern to clock off"  | Switch sequencer to clock-off playlist (`C- ` patterns) |

## Pixelblaze pattern naming convention

Patterns come in pairs:
- `C <name>` — clock-on variant (clock overlay visible)
- `C- <name>` — clock-off variant (background only)

On startup, the sequencer playlist is built from the `C ` variants. The "clock off" command swaps to the paired `C- ` variants without leaving the sequencer.

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

## Files

```
k-clock.py               # Entire application (single file)
startup.sh               # Launch script for the Pi (activates venv, passes args)
k-clock_service.service  # systemd unit file
requirements.txt         # Python dependencies
```

## Logs

Rotating log file at `k-clock.log` in the working directory (40 KB, 5 backups).