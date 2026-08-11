#!/usr/bin/env python3
"""
E.V. Agent — Background Wake Word Listener
Continuously monitors background audio for trigger phrases ("EV", "Hey EV", "EV ơi", "Mở EV").
Automatically launches or focuses E.V. Agent when spoken.
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Safe stdout/stderr fallback
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# File logging
LOG_FILE = PROJECT_ROOT / "wake_word.log"
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [ev.wake_word] %(levelname)s: %(message)s"))
root_logger.addHandler(file_handler)

logger = logging.getLogger("ev.wake_word")

import speech_recognition as sr

# Expanded list of supported wake words and pronunciations (including single word "EV")
WAKE_WORDS = [
    # Single word triggers
    "ev", "e.v.", "e v", "y vi", "i vi", "eve", "ee vee", "ê vi", "ê-vi", "ế vế", "ê vây",
    # Phrase triggers
    "hey ev", "hey e v", "hey e.v.", "ev ơi", "e v ơi", "hey assistant",
    "mở ev", "mở e v", "bật ev", "bật e v", "hello ev", "ơi ev"
]


def is_ev_running() -> bool:
    """Check if E.V. Agent desktop/web server is active on port 5000."""
    try:
        import urllib.request
        req = urllib.request.urlopen("http://127.0.0.1:5000/api/status", timeout=1)
        return req.status == 200
    except Exception:
        return False


def launch_ev():
    """Launch E.V. Agent silently via VBScript."""
    vbs_path = PROJECT_ROOT / "run_app.vbs"
    logger.info(f"Triggering E.V. Agent via {vbs_path}")
    subprocess.Popen(f'wscript.exe "{vbs_path}"', shell=True)


def listen_loop():
    """Continuous background listener loop."""
    logger.info("=== Wake Word Listener Started ===")
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    try:
        mic = sr.Microphone()
    except Exception as e:
        logger.error(f"Cannot initialize microphone: {e}")
        return

    logger.info("🎙️ E.V. Wake Word Listener active. Say 'EV' or 'Hey EV' to launch!")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    while True:
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=4, phrase_time_limit=4)

            # Recognize speech
            text = ""
            try:
                # Try Vietnamese recognition first
                text = recognizer.recognize_google(audio, language="vi-VN").lower()
            except Exception:
                try:
                    # Fallback to English
                    text = recognizer.recognize_google(audio, language="en-US").lower()
                except Exception:
                    pass

            if text:
                logger.info(f"Heard audio: '{text}'")

            # Check if any wake word or single word "ev" matches
            words_list = text.strip().split()
            matched = any(w in text for w in WAKE_WORDS) or any(w in words_list for w in ["ev", "e.v.", "eve", "i-vi"])

            if matched:
                logger.info(f"✨ Wake word detected in '{text}'!")

                if not is_ev_running():
                    logger.info("E.V. Agent is not running. Launching E.V. Agent now...")
                    launch_ev()
                else:
                    logger.info("E.V. Agent is already running.")

                # Cooldown to avoid duplicate triggers
                time.sleep(3)

        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            logger.error(f"Listener loop error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    listen_loop()
