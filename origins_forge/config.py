import json
from pathlib import Path
from typing import Dict, Any

APP_NAME = "Origins Intelligent Dev Tool"
CURRENT_VERSION = "0.2.4"
MANIFEST_URL = "https://gist.github.com/Htet-2aung/8a8a85c1f45979e1215f2a30bcfb9475/raw/template.json"
VERSION_URL = "https://raw.githubusercontent.com/Htet-2aung/origins-forge/main/version.txt"
REPO_NAME = "Htet-2aung/origins-forge"

HOME_DIR = Path.home()
PROJECTS_DIR = HOME_DIR / "origins-projects"
CONFIG_DIR = HOME_DIR / ".origins"
CACHE_DIR = CONFIG_DIR / "cache"
MANIFEST_FILE = CONFIG_DIR / "templates.json"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Ensure base directories exist
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def load_config() -> Dict[str, Any]:
    """Load configuration from the JSON file."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}

def save_config(key: str, value: Any) -> None:
    """Save a key-value pair to the configuration file."""
    config = load_config()
    config[key] = value
    CONFIG_FILE.write_text(json.dumps(config, indent=4))