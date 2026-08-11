"""
E.V. Guardrail — Safety checks before tool execution.
Prevents dangerous commands and enforces boundaries.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

import config

logger = logging.getLogger("ev.tools.guardrail")


class GuardrailResult:
    """Result of a guardrail check."""
    
    def __init__(self, allowed: bool, reason: str = "", requires_confirmation: bool = False):
        self.allowed = allowed
        self.reason = reason
        self.requires_confirmation = requires_confirmation


class Guardrail:
    """
    Safety guardrail for tool execution.
    
    Checks:
    - Dangerous command blacklist
    - File system boundaries
    - Rate limiting
    - Confirmation for sensitive operations
    """

    def __init__(self):
        self.dangerous_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in [
                r"rm\s+-rf\s+/",
                r"format\s+[a-z]:",
                r"del\s+/[sf]\s+/[sq]",
                r"shutdown\s+/[sr]",
                r"rmdir\s+/s\s+/q",
                r"reg\s+delete",
                r"bcdedit",
                r"diskpart",
                r":\s*format",
                r"Remove-Item\s+-Recurse\s+-Force\s+[/\\]",
                r"Stop-Computer",
                r"Restart-Computer",
                r"Clear-Disk",
            ]
        ]

        self.sensitive_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in [
                r"del\s+",
                r"Remove-Item",
                r"rmdir",
                r"taskkill",
                r"Stop-Process",
                r"Set-ExecutionPolicy",
                r"net\s+user",
                r"net\s+localgroup",
                r"reg\s+add",
                r"schtasks\s+/create",
            ]
        ]

        self._call_counts: Dict[str, int] = {}
        self._max_calls_per_minute = 30

    def check_shell_command(self, command: str) -> GuardrailResult:
        """Check if a shell command is safe to execute."""
        # Check dangerous patterns (block immediately)
        for pattern in self.dangerous_patterns:
            if pattern.search(command):
                return GuardrailResult(
                    allowed=False,
                    reason=f"🚫 Blocked: This command matches a dangerous pattern and could damage the system."
                )

        # Check sensitive patterns (require confirmation)
        for pattern in self.sensitive_patterns:
            if pattern.search(command):
                return GuardrailResult(
                    allowed=True,
                    reason=f"⚠️ This command is potentially destructive. Please confirm.",
                    requires_confirmation=True,
                )

        return GuardrailResult(allowed=True)

    def check_file_path(self, path: str, write: bool = False) -> GuardrailResult:
        """Check if file access is within allowed boundaries."""
        from pathlib import Path

        try:
            resolved = Path(path).resolve()
        except Exception:
            return GuardrailResult(
                allowed=False,
                reason=f"Invalid file path: {path}"
            )

        # System-critical paths that should never be modified
        protected_paths = [
            "C:\\Windows",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
        ]

        if write:
            for protected in protected_paths:
                if str(resolved).lower().startswith(protected.lower()):
                    return GuardrailResult(
                        allowed=False,
                        reason=f"🚫 Cannot write to protected system directory: {protected}"
                    )

        return GuardrailResult(allowed=True)

    def check_python_code(self, code: str) -> GuardrailResult:
        """Check if Python code is safe to execute."""
        dangerous_imports = [
            "subprocess", "shutil.rmtree", "os.system",
            "ctypes", "winreg",
        ]

        dangerous_calls = [
            "os.remove", "os.rmdir", "os.unlink",
            "shutil.rmtree", "os.system",
        ]

        for imp in dangerous_imports:
            if imp in code:
                return GuardrailResult(
                    allowed=True,
                    reason=f"⚠️ Code uses '{imp}' which can be dangerous.",
                    requires_confirmation=True,
                )

        for call in dangerous_calls:
            if call in code:
                return GuardrailResult(
                    allowed=True,
                    reason=f"⚠️ Code calls '{call}' which can modify the system.",
                    requires_confirmation=True,
                )

        return GuardrailResult(allowed=True)

    def check_rate_limit(self, tool_name: str) -> GuardrailResult:
        """Simple rate limiting to prevent infinite loops."""
        import time
        current_minute = int(time.time()) // 60
        key = f"{tool_name}_{current_minute}"

        self._call_counts[key] = self._call_counts.get(key, 0) + 1

        if self._call_counts[key] > self._max_calls_per_minute:
            return GuardrailResult(
                allowed=False,
                reason=f"🚫 Rate limit exceeded for tool '{tool_name}'. Max {self._max_calls_per_minute} calls/minute."
            )

        # Cleanup old entries
        old_keys = [k for k in self._call_counts if not k.endswith(str(current_minute))]
        for k in old_keys:
            del self._call_counts[k]

        return GuardrailResult(allowed=True)
