#!/usr/bin/env python3
"""
E.V. Agent — Native Desktop Application Entry Point
Launches Flask backend server and opens a native desktop application window via Google Chrome App Mode (Edge fallback).
Keeps backend process alive for the duration of the desktop app session.
"""

import sys
import os
import time
import threading
import logging
import subprocess
import urllib.request
import webbrowser
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

LOG_FILE = PROJECT_ROOT / "desktop_launch.log"

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
root_logger.addHandler(file_handler)

logger = logging.getLogger("ev.desktop")

import config
from server import app


def is_server_running() -> bool:
    """Check if Flask server is responding with HTTP 200 on port 5000."""
    try:
        url = f"http://{config.WEB_HOST}:{config.WEB_PORT}/"
        req = urllib.request.urlopen(url, timeout=1.5)
        return req.status == 200
    except Exception:
        return False


def run_flask():
    """Run Flask backend server in background thread."""
    logger.info(f"Starting Flask backend on http://{config.WEB_HOST}:{config.WEB_PORT}")
    try:
        app.run(
            host=config.WEB_HOST,
            port=config.WEB_PORT,
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        logger.error(f"Flask server error: {e}")


def launch_native_app_window(url: str):
    """Launch native desktop window using Chrome App Mode (with Edge fallback). Returns Process handle."""
    logger.info(f"Launching Native Chrome App Mode for {url}")
    profile_dir = str(PROJECT_ROOT / "data" / "chrome_profile")
    os.makedirs(profile_dir, exist_ok=True)

    # 1. Google Chrome App Mode
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "chrome.exe"
    ]

    for chrome in chrome_paths:
        try:
            cmd = [
                chrome,
                f"--app={url}",
                "--window-size=1080,760"
            ]
            proc = subprocess.Popen(cmd)
            if proc.poll() is None:
                logger.info(f"Successfully launched Chrome App Mode via {chrome}")
                return proc
        except Exception as e:
            logger.debug(f"Failed to launch {chrome}: {e}")

    # 2. Edge App Mode Fallback
    edge_paths = [
        "msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]

    for edge in edge_paths:
        try:
            cmd = [edge, f"--app={url}", "--window-size=1080,760"]
            proc = subprocess.Popen(cmd)
            if proc.poll() is None:
                logger.info(f"Successfully launched Edge App Mode via {edge}")
                return proc
        except Exception as e:
            logger.debug(f"Failed to launch {edge}: {e}")

    # 3. Standard browser fallback
    logger.warning("App Mode launch failed. Opening default browser...")
    webbrowser.open(url)
    return None


def main():
    """Main entry point."""
    logger.info("=== E.V. Agent Desktop Launcher Started ===")

    errors = config.validate_config()
    if errors:
        for e in errors:
            logger.error(f"Config error: {e}")
        sys.exit(1)

    # Start Flask server if not running
    if not is_server_running():
        server_thread = threading.Thread(target=run_flask, daemon=True)
        server_thread.start()

        # Wait up to 30s until root page returns HTTP 200 OK
        start_t = time.time()
        ready = False
        while time.time() - start_t < 30:
            if is_server_running():
                ready = True
                break
            time.sleep(0.3)

        if not ready:
            logger.error("Flask server failed to start within 30 seconds.")
            sys.exit(1)

    url = f"http://{config.WEB_HOST}:{config.WEB_PORT}"
    proc = launch_native_app_window(url)

    # Keep Python main process alive so Flask server daemon thread never dies!
    try:
        logger.info("Desktop window launched. Keeping Flask server alive...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Exiting E.V. Agent Desktop.")


if __name__ == "__main__":
    main()

