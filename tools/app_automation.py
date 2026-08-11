"""
E.V. App Automation — Enhanced OS & App Automation using pyautogui, webbrowser & pyperclip.
Supports opening apps, opening web URLs, playing media on YouTube/Spotify, Vietnamese Unicode typing, and window/system control.
"""

import subprocess
import logging
import urllib.parse
import webbrowser
import time

logger = logging.getLogger("ev.tools.app_automation")


def automate_app(action: str, target: str, value: str = "") -> str:
    """
    Perform automation actions on the desktop or browser.
    
    Args:
        action: "open_app", "open_url", "play_media", "close_app", "type_text", "press_key", "click", "move_mouse", "minimize", "maximize", "set_volume"
        target: App name, URL, media platform ('youtube', 'spotify'), key name, or coordinates
        value: Query/song name for media, search query, text content, volume level
    """
    try:
        clean_action = action.strip().lower()
        clean_target = target.strip()
        clean_value = value.strip() if value else ""

        if clean_action in ("open_url", "web"):
            return _open_url(clean_target)
        elif clean_action in ("play_media", "play_music", "play_video", "search_media"):
            return _play_media(clean_target, clean_value)
        elif clean_action == "open_app":
            # Auto-route URLs or YouTube/Spotify search queries
            if clean_target.startswith(("http://", "https://", "www.")) or (("." in clean_target) and "/" in clean_target):
                return _open_url(clean_target)
            elif clean_target.lower() in ("youtube", "spotify") and clean_value:
                return _play_media(clean_target, clean_value)
            elif clean_target.lower() in ("chrome", "edge", "browser") and clean_value:
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(clean_value)}"
                webbrowser.open(search_url)
                return f"Searched Google in {clean_target} for: {clean_value}"
            else:
                return _open_app(clean_target)
        elif clean_action == "close_app":
            return _close_app(clean_target)
        elif clean_action == "type_text":
            return _type_text(clean_target)
        elif clean_action == "press_key":
            return _press_key(clean_target)
        elif clean_action == "click":
            return _click(clean_target)
        elif clean_action == "move_mouse":
            return _move_mouse(clean_target)
        elif clean_action == "minimize":
            return _window_action("minimize")
        elif clean_action == "maximize":
            return _window_action("maximize")
        elif clean_action == "set_volume":
            return _set_volume(clean_target)
        else:
            return f"Unknown action: {action}. Available: open_app, open_url, play_media, close_app, type_text, press_key, click, move_mouse, minimize, maximize, set_volume"

    except ImportError as ie:
        return f"Error: Missing required package ({ie}). Please install dependencies."
    except Exception as e:
        logger.error(f"Error performing automation action={action}, target={target}: {e}", exc_info=True)
        return f"Error performing automation: {e}"


def _open_url(url: str) -> str:
    """Open a website URL in default web browser."""
    try:
        full_url = url
        if not full_url.startswith(("http://", "https://")):
            full_url = "https://" + full_url
        webbrowser.open(full_url)
        return f"Opened web URL: {full_url}"
    except Exception as e:
        return f"Error opening URL {url}: {e}"


def _play_media(platform: str, query: str = "") -> str:
    """
    Search and play music or videos on YouTube, Spotify, or Web.
    """
    try:
        platform_lower = platform.lower().strip()
        
        # If no query provided but platform itself contains a query (e.g. target="lofi chill", platform="youtube")
        if not query and platform_lower not in ("youtube", "spotify", "music", "video"):
            query = platform
            platform_lower = "youtube"

        encoded_query = urllib.parse.quote(query) if query else ""

        if "spotify" in platform_lower:
            if query:
                # Open Spotify web search (works natively in browser or redirects to app)
                url = f"https://open.spotify.com/search/{encoded_query}"
                webbrowser.open(url)
                return f"Opening Spotify and searching for: '{query}'"
            else:
                return _open_app("spotify")

        else:
            # Default to YouTube for videos/music
            if query:
                url = f"https://www.youtube.com/results?search_query={encoded_query}"
                webbrowser.open(url)
                return f"Opened YouTube search for: '{query}'"
            else:
                webbrowser.open("https://www.youtube.com")
                return "Opened YouTube"

    except Exception as e:
        return f"Error playing media on {platform}: {e}"


def _open_app(app_name: str) -> str:
    """Open an application by name or executable."""
    try:
        app_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "spotify": "spotify.exe",
            "code": "code.exe",
            "vscode": "code.exe",
            "task manager": "taskmgr.exe",
            "settings": "ms-settings:",
        }

        app_clean = app_name.lower().strip()
        exe = app_map.get(app_clean, app_name)

        if exe.startswith("ms-"):
            subprocess.Popen(["start", exe], shell=True)
        else:
            try:
                subprocess.Popen(exe, shell=True)
            except Exception:
                # Fallback to start command for Windows
                subprocess.Popen(f"start {exe}", shell=True)

        return f"Opened application: {app_name}"
    except Exception as e:
        return f"Error opening {app_name}: {e}"


def _close_app(app_name: str) -> str:
    """Close an application by name."""
    try:
        result = subprocess.run(
            ["taskkill", "/IM", f"{app_name}.exe", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return f"Closed application: {app_name}"
        return f"Could not close {app_name}: {result.stderr}"
    except Exception as e:
        return f"Error closing {app_name}: {e}"


def _type_text(text: str) -> str:
    """
    Type text using pyperclip (clipboard paste) for full Unicode/Vietnamese support.
    """
    import pyautogui
    import pyperclip

    try:
        # Copy text to clipboard and paste to support full Unicode (Vietnamese accents)
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        return f"Typed: {text[:50]}"
    except Exception as e:
        # Fallback to pyautogui.typewrite if clipboard fails
        pyautogui.typewrite(text, interval=0.02)
        return f"Typed (ASCII fallback): {text[:50]}"


def _press_key(key: str) -> str:
    """Press a key or key combination (including media keys)."""
    import pyautogui

    key_clean = key.strip().lower()
    
    # Media key aliases
    media_map = {
        "play": "playpause",
        "pause": "playpause",
        "playpause": "playpause",
        "next": "nexttrack",
        "nexttrack": "nexttrack",
        "previous": "prevtrack",
        "prevtrack": "prevtrack",
        "volumeup": "volumeup",
        "volumedown": "volumedown",
        "mute": "volumemute",
    }

    if key_clean in media_map:
        pyautogui.press(media_map[key_clean])
        return f"Pressed media key: {media_map[key_clean]}"

    # Handle combinations like "ctrl+c" or "win+d"
    if "+" in key_clean:
        keys = [k.strip() for k in key_clean.split("+")]
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(key_clean)

    return f"Pressed key: {key}"


def _click(coords: str) -> str:
    """Click at coordinates (x,y) or target location like 'center'."""
    import pyautogui

    try:
        clean_target = coords.strip().lower()
        if clean_target in ("center", "middle"):
            sw, sh = pyautogui.size()
            x, y = sw // 2, sh // 2
        else:
            parts = coords.replace("(", "").replace(")", "").split(",")
            x, y = int(parts[0].strip()), int(parts[1].strip())

        pyautogui.click(x, y)
        return f"Clicked at ({x}, {y})"
    except (ValueError, IndexError):
        return f"Error: Invalid coordinates '{coords}'. Expected format: 'x,y' or 'center'"


def _move_mouse(coords: str) -> str:
    """Move mouse to coordinates."""
    import pyautogui

    try:
        parts = coords.replace("(", "").replace(")", "").split(",")
        x, y = int(parts[0].strip()), int(parts[1].strip())
        pyautogui.moveTo(x, y)
        return f"Mouse moved to ({x}, {y})"
    except (ValueError, IndexError):
        return f"Error: Invalid coordinates '{coords}'."


def _window_action(action: str) -> str:
    """Minimize or maximize the active window."""
    import pyautogui

    if action == "minimize":
        pyautogui.hotkey("win", "down")
        return "Window minimized"
    elif action == "maximize":
        pyautogui.hotkey("win", "up")
        return "Window maximized"
    return f"Unknown window action: {action}"


def _set_volume(level: str) -> str:
    """Set system volume (0-100)."""
    try:
        vol = int(level)
        vol = max(0, min(100, vol))

        # Use PowerShell to set volume
        ps_script = f"""
        $vol = {vol / 100}
        $obj = New-Object -ComObject WScript.Shell
        1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
        $steps = [math]::Round({vol} / 2)
        1..$steps | ForEach-Object {{ $obj.SendKeys([char]175) }}
        """

        subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True
        )

        return f"Volume set to {vol}%"
    except ValueError:
        return f"Error: Invalid volume level '{level}'. Expected a number 0-100."
