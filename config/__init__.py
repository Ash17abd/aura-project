import json, os
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "api_keys.json"

def get_config() -> dict:
    cfg = {}
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    # Environment variables take precedence over config file
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        cfg["gemini_api_key"] = gemini_key

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        cfg["openai_api_key"] = openai_key

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        cfg["anthropic_api_key"] = anthropic_key

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        cfg["openrouter_api_key"] = openrouter_key

    return cfg

def get_os() -> str:
    """Returns: 'windows' | 'mac' | 'linux'"""
    return os.getenv("OS_SYSTEM", get_config().get("os_system", "windows")).lower()

def is_windows() -> bool: return get_os() == "windows"
def is_mac()     -> bool: return get_os() == "mac"
def is_linux()   -> bool: return get_os() == "linux"