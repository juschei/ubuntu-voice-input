# Local Voice Input

Push-to-talk voice transcription for Linux/Wayland and PulseAudio. Records audio, transcribes with Whisper, copies to clipboard.

## Requirements

- Python 3.10+
- PulseAudio
- `wl-copy` (wl-clipboard)
- `notify-send` (libnotify)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install faster-whisper sounddevice numpy
```

## Usage

```bash
./run.sh  # Toggle recording on/off
```

Run once to start recording, again to stop and transcribe. Text is copied to clipboard.

### Ubuntu Keyboard Shortcut

1. Open Settings > Keyboard > Keyboard Shortcuts > Custom Shortcuts
2. Click "Add Shortcut"
3. Name: `Voice Input`
4. Command: `/full/path/to/run.sh`
5. Set your preferred shortcut (e.g. `CTRL+ALT+Y`)

## Configuration

Edit constants in `voice_input.py`:

- `MODEL_SIZE` - Whisper model: `tiny`, `base`, `small`, `medium`, `large-v3` (default: `base`)
- `DEVICE` - Audio device (default: pulse)
