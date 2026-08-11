"""
E.V. Python Executor — Sandboxed Python code execution.
"""

import subprocess
import sys
import os
import logging
from pathlib import Path

import config

logger = logging.getLogger("ev.tools.python_executor")


def execute_python(code: str) -> str:
    """
    Execute Python code in a subprocess.
    Returns stdout + stderr output.
    """
    from tools.guardrail import Guardrail
    guardrail = Guardrail()

    # Safety check
    check = guardrail.check_python_code(code)
    if not check.allowed:
        return check.reason

    # Write code to temp file
    tmp_dir = config.DATA_DIR / "temp"
    tmp_dir.mkdir(exist_ok=True)

    tmp_file = tmp_dir / "ev_exec.py"
    tmp_file.write_text(code, encoding="utf-8")

    # Use python.exe instead of pythonw.exe to guarantee stdout/stderr capture
    python_bin = sys.executable
    if "pythonw.exe" in python_bin.lower():
        python_bin = python_bin.lower().replace("pythonw.exe", "python.exe")

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            [python_bin, str(tmp_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=config.TOOL_EXECUTION_TIMEOUT,
            cwd=str(config.PROJECT_ROOT),
            env=env,
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[STDERR]: {result.stderr}"
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"

        return output.strip() or "Code executed successfully (no output)."

    except subprocess.TimeoutExpired:
        return f"Error: Code execution timed out after {config.TOOL_EXECUTION_TIMEOUT} seconds."
    except Exception as e:
        return f"Error executing Python code: {e}"
    finally:
        try:
            tmp_file.unlink(missing_ok=True)
        except Exception:
            pass
