#!/usr/bin/env python3
"""Push-to-talk voice transcription for Linux/Wayland."""

import subprocess
import sys
import os
import signal
import time
import numpy as np
import sounddevice as sd
from pathlib import Path
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
CHANNELS = 1
MODEL_SIZE = "base"
DEVICE = "pulse"

STATE_DIR = Path("/tmp/voice-input")
STATE_DIR.mkdir(exist_ok=True)
PID_FILE = STATE_DIR / "record.pid"
TRANSCRIBE_LOCK = STATE_DIR / "transcribe.lock"
AUDIO_FILE = STATE_DIR / "recording.npy"
LOG_FILE = STATE_DIR / "debug.log"


def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


def notify(message, urgency="normal"):
    subprocess.run(
        ["notify-send", "-u", urgency, "-t", "1500", "Voice Input", message],
        capture_output=True,
    )


def do_record():
    PID_FILE.write_text(str(os.getpid()))
    audio_chunks = []
    recording = True

    def callback(indata, frames, time_info, status):
        if recording:
            audio_chunks.append(indata.copy())

    def stop_handler(signum, frame):
        nonlocal recording
        recording = False

    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)
    notify("🎤 Recording...")

    try:
        with sd.InputStream(
            device=DEVICE,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.float32,
            callback=callback,
        ):
            while recording:
                sd.sleep(100)
    except Exception as e:
        log(f"Recording error: {e}")
        notify(f"Recording error: {e}", "critical")
        return
    finally:
        PID_FILE.unlink(missing_ok=True)

    if audio_chunks:
        audio = np.concatenate(audio_chunks, axis=0)
        np.save(AUDIO_FILE, audio)
        log(f"Recorded {len(audio) / SAMPLE_RATE:.1f}s")


def transcribe():
    if not AUDIO_FILE.exists():
        notify("No recording found", "critical")
        return

    TRANSCRIBE_LOCK.write_text(str(os.getpid()))
    try:
        notify("⏳ Transcribing...")
        audio = np.load(AUDIO_FILE).flatten().astype(np.float32)
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio, beam_size=5, language="en")
        text = " ".join(seg.text for seg in segments).strip()
        AUDIO_FILE.unlink(missing_ok=True)

        if text:
            subprocess.run(
                ["wl-copy", text],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            notify(f"✓ {text[:50]}{'...' if len(text) > 50 else ''}")
            log(f"Transcribed: {text}")
        else:
            notify("No speech detected")
    finally:
        TRANSCRIBE_LOCK.unlink(missing_ok=True)


def start_recording():
    script_path = Path(__file__).resolve()
    with (
        open(STATE_DIR / "stdout.log", "w") as out,
        open(STATE_DIR / "stderr.log", "w") as err,
    ):
        subprocess.Popen(
            [sys.executable, str(script_path), "--record"],
            start_new_session=True,
            stdout=out,
            stderr=err,
        )
    time.sleep(0.2)


def stop_recording():
    if not PID_FILE.exists():
        return

    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.1)
            if not PID_FILE.exists():
                break
    except ProcessLookupError:
        pass

    PID_FILE.unlink(missing_ok=True)
    transcribe()


def is_process_alive(pid_file):
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        pid_file.unlink(missing_ok=True)
        return False


def main():
    if "--record" in sys.argv:
        do_record()
        return

    LOG_FILE.write_text("")

    if is_process_alive(TRANSCRIBE_LOCK):
        return

    if is_process_alive(PID_FILE):
        stop_recording()
    else:
        start_recording()


if __name__ == "__main__":
    main()
