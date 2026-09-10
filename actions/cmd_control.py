"""
actions/cmd_control.py — Safe system command and process executor for AURA.

Executes shell commands, opens files, launches applications, and manages system tasks.
"""

from __future__ import annotations

import os
import sys
import subprocess
import shlex
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("cmd_control")

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def cmd_control(
    parameters: Optional[Dict[str, Any]] = None,
    player: Optional[Any] = None,
    speak: Optional[Any] = None,
) -> str:
    """
    Execute a system task or command line instruction.
    
    Parameters:
        task: string (required) - natural language task or shell command (e.g. 'open report.txt in notepad', 'dir', 'ipconfig')
        visible: boolean (optional) - whether to run visibly in a console window
        cwd: string (optional) - working directory
        timeout: int (optional) - command timeout in seconds (default: 30)
    """
    params = parameters or {}
    task = str(params.get("task", "")).strip()
    visible = bool(params.get("visible", False))
    timeout = int(params.get("timeout", 30))
    cwd = params.get("cwd") or str(Path.home())

    if not task:
        return "No task or command specified for cmd_control."

    if player and hasattr(player, "write_log"):
        player.write_log(f"[cmd] {task[:60]}")

    # Check for direct file opening requests (e.g., 'open filename.txt with notepad')
    desktop = Path.home() / "Desktop"
    downloads = Path.home() / "Downloads"
    documents = Path.home() / "Documents"

    # Match simple open commands
    open_match = False
    task_lower = task.lower()
    
    # 1. Direct file launch / open with notepad / default app
    if "notepad" in task_lower:
        # Extract potential filename
        for word in task.split():
            clean_word = word.strip("'\"")
            if "." in clean_word and not clean_word.endswith(".exe"):
                for search_dir in [desktop, downloads, documents, Path.cwd()]:
                    candidate = search_dir / clean_word
                    if candidate.exists():
                        try:
                            if sys.platform == "win32":
                                subprocess.Popen(["notepad.exe", str(candidate)])
                            else:
                                subprocess.Popen(["nano", str(candidate)])
                            return f"Opened {candidate.name} in Notepad."
                        except Exception as e:
                            return f"Failed to open {candidate.name} in Notepad: {e}"

    # 2. Check if task mentions opening a specific existing file
    for search_dir in [desktop, downloads, documents, Path.cwd()]:
        for word in task.split():
            clean_word = word.strip("'\"")
            if "." in clean_word:
                candidate = search_dir / clean_word
                if candidate.exists() and ("open" in task_lower or "launch" in task_lower or "view" in task_lower):
                    try:
                        if sys.platform == "win32":
                            os.startfile(str(candidate))
                        elif sys.platform == "darwin":
                            subprocess.Popen(["open", str(candidate)])
                        else:
                            subprocess.Popen(["xdg-open", str(candidate)])
                        return f"Opened file: {candidate.name}"
                    except Exception as e:
                        return f"Failed to open file: {e}"

    # 3. Execute as command in shell
    try:
        if sys.platform == "win32":
            shell_cmd = task
            creationflags = subprocess.CREATE_NEW_CONSOLE if visible else 0
            res = subprocess.run(
                shell_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                creationflags=creationflags,
                errors="replace",
            )
        else:
            res = subprocess.run(
                task,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                errors="replace",
            )

        stdout = (res.stdout or "").strip()
        stderr = (res.stderr or "").strip()

        if res.returncode == 0:
            if stdout:
                return stdout[:2000]
            return f"Command executed successfully: {task}"
        else:
            err_msg = stderr or stdout or f"Exit code {res.returncode}"
            return f"Command error ({res.returncode}): {err_msg[:1000]}"

    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds."
    except Exception as e:
        return f"cmd_control execution failed: {e}"
