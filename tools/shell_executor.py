"""
E.V. Shell Executor — PowerShell/CMD command execution with UTF-8 encoding support.
"""

import subprocess
import os
import logging

import config

logger = logging.getLogger("ev.tools.shell_executor")


def execute_shell(command: str, shell: str = "powershell") -> str:
    """
    Execute a shell command via PowerShell or CMD.
    Returns stdout + stderr output.
    """
    from tools.guardrail import Guardrail
    guardrail = Guardrail()

    # Safety check
    check = guardrail.check_shell_command(command)
    if not check.allowed:
        return check.reason

    # Rate limit check
    rate_check = guardrail.check_rate_limit("execute_shell")
    if not rate_check.allowed:
        return rate_check.reason

    if check.requires_confirmation:
        logger.warning(f"Sensitive command detected: {command}")
        warning = f"⚠️ Warning: {check.reason}\n"
    else:
        warning = ""

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        if shell.lower() == "powershell":
            utf8_cmd = f"$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; {command}"
            cmd = ["powershell", "-NoProfile", "-Command", utf8_cmd]
        else:
            cmd = ["cmd", "/c", command]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=config.TOOL_EXECUTION_TIMEOUT,
            cwd=str(config.PROJECT_ROOT),
            env=env,
        )

        output = warning
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[STDERR]: {result.stderr}"
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"

        return output.strip() or "Command executed successfully (no output)."

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {config.TOOL_EXECUTION_TIMEOUT} seconds."
    except Exception as e:
        return f"Error executing command: {e}"
