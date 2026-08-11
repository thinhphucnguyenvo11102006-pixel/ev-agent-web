"""
E.V. Vision — Screenshot capture and image analysis.
"""

import base64
import subprocess
import logging
from pathlib import Path
from datetime import datetime

import config

logger = logging.getLogger("ev.tools.vision")


def take_screenshot(target: str = "full_screen") -> str:
    """
    Take a screenshot and save it.
    Returns the path to the saved image.
    """
    try:
        screenshot_dir = config.DATA_DIR / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = screenshot_dir / filename

        # Method 1: Pillow ImageGrab
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            if img:
                img.save(str(filepath))
                return f"Screenshot saved: {filepath}"
        except Exception:
            pass

        # Method 2: mss
        try:
            import mss
            with mss.MSS() as sct:
                monitor = sct.monitors[1] if target == "active_window" else sct.monitors[0]
                screenshot = sct.grab(monitor)

                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                img.save(str(filepath))
                return f"Screenshot saved: {filepath}"
        except Exception:
            pass

        # Method 3: PowerShell GDI Graphics capture (100% reliable on Windows)
        ps_script = f"""
        Add-Type -AssemblyName System.Drawing
        Add-Type -AssemblyName System.Windows.Forms
        $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
        $graphics = [System.Drawing.Graphics]::FromImage($bmp)
        $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
        $bmp.Save('{str(filepath)}', [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bmp.Dispose()
        """
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True
        )

        if filepath.exists():
            return f"Screenshot saved: {filepath}"
        else:
            return f"Error taking screenshot via PowerShell: {result.stderr}"

    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return f"Error taking screenshot: {e}"


async def analyze_image(image_path: str, question: str = "") -> str:
    """
    Analyze an image using Vision-capable LLM (OpenRouter / Gemini / OpenAI).
    """
    try:
        path = Path(image_path).resolve()
        if not path.exists():
            return f"Error: Image not found: {image_path}"

        import io
        from PIL import Image

        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((1024, 1024))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            image_data = base64.b64encode(buf.getvalue()).decode("utf-8")

        mime_type = "image/jpeg"

        from openai import AsyncOpenAI

        # Check available API keys (OpenRouter primary)
        extra_headers = None
        if config.OPENROUTER_API_KEY:
            api_key = config.OPENROUTER_API_KEY
            base_url = config.OPENROUTER_BASE_URL
            model = config.OPENROUTER_MODEL
            extra_headers = {"HTTP-Referer": "https://github.com/ev-agent", "X-Title": "E.V. Agent"}
        elif config.GEMINI_API_KEY:
            api_key = config.GEMINI_API_KEY
            base_url = config.GEMINI_BASE_URL
            model = config.GEMINI_MODEL
        elif config.GROQ_API_KEY:
            api_key = config.GROQ_API_KEY
            base_url = config.GROQ_BASE_URL
            model = "llama-3.2-11b-vision-preview"
        else:
            api_key = config.DEEPSEEK_API_KEY
            base_url = config.DEEPSEEK_BASE_URL
            model = config.DEEPSEEK_MODEL

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=extra_headers,
            timeout=20.0,
        )

        prompt = question or "Describe this image concisely. If there is text, read key parts."

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=512,
        )

        return response.choices[0].message.content or "No analysis available."

    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return f"Error analyzing image: {e}"
