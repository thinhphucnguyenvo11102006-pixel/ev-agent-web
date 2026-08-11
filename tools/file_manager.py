"""
E.V. File Manager — File read/write/list operations.
"""

import os
import logging
from pathlib import Path
from typing import Optional
import glob as glob_module

import config

logger = logging.getLogger("ev.tools.file_manager")


def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read the contents of a file."""
    from tools.guardrail import Guardrail
    guardrail = Guardrail()

    check = guardrail.check_file_path(path, write=False)
    if not check.allowed:
        return check.reason

    try:
        resolved = Path(path).resolve()
        if not resolved.exists():
            return f"Error: File not found: {path}"
        if not resolved.is_file():
            return f"Error: Path is not a file: {path}"
        
        # Limit file size to 100KB for safety
        size = resolved.stat().st_size
        if size > 100 * 1024:
            return f"Error: File too large ({size // 1024}KB). Max 100KB."

        content = resolved.read_text(encoding=encoding)
        return content

    except UnicodeDecodeError:
        return f"Error: Cannot read file as {encoding}. It may be a binary file."
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str, mode: str = "write") -> str:
    """Write content to a file."""
    from tools.guardrail import Guardrail
    guardrail = Guardrail()

    check = guardrail.check_file_path(path, write=True)
    if not check.allowed:
        return check.reason

    try:
        resolved = Path(path).resolve()
        
        # Create parent directories if needed
        resolved.parent.mkdir(parents=True, exist_ok=True)

        if mode == "append":
            with open(resolved, "a", encoding="utf-8") as f:
                f.write(content)
            return f"Appended {len(content)} characters to {path}"
        else:
            resolved.write_text(content, encoding="utf-8")
            return f"Written {len(content)} characters to {path}"

    except Exception as e:
        return f"Error writing file: {e}"


def list_files(path: str, pattern: str = "*") -> str:
    """List files and directories in a given path."""
    from tools.guardrail import Guardrail
    guardrail = Guardrail()

    check = guardrail.check_file_path(path, write=False)
    if not check.allowed:
        return check.reason

    try:
        resolved = Path(path).resolve()
        if not resolved.exists():
            return f"Error: Directory not found: {path}"
        if not resolved.is_dir():
            return f"Error: Path is not a directory: {path}"

        entries = []
        for item in sorted(resolved.glob(pattern)):
            if item.is_dir():
                count = sum(1 for _ in item.iterdir()) if item.exists() else 0
                entries.append(f"📁 {item.name}/ ({count} items)")
            else:
                size = item.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size // 1024}KB"
                else:
                    size_str = f"{size // (1024 * 1024)}MB"
                entries.append(f"📄 {item.name} ({size_str})")

        if not entries:
            return f"Directory is empty: {path}"

        return f"Contents of {path}:\n" + "\n".join(entries[:50])  # Limit to 50 entries

    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error listing files: {e}"
