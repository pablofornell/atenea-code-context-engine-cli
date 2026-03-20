import os
import json
from pathlib import Path
from typing import Any, Dict

from .utils import get_project_root

DEFAULT_CONFIG = {
    "server_url": "http://localhost:8080"
}

def get_config_dir() -> Path:
    """Returns the configuration directory path (.atenea inside project root)."""
    project_root = get_project_root()
    config_dir = Path(project_root) / ".atenea"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_config_path() -> Path:
    """Returns the configuration file path (~/.atenea/config.json)."""
    return get_config_dir() / "config.json"

def load_config() -> Dict[str, Any]:
    """Loads the configuration from the JSON file, creating it if it doesn't exist."""
    config_path = get_config_path()
    
    if not config_path.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            # Ensure all default keys are present
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> None:
    """Saves the configuration to the JSON file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

def get_server_url() -> str:
    """
    Resolves the server URL following this precedence:
    1. Environment variable ATENEA_SERVER
    2. Config file server_url
    3. Default http://localhost:8080
    """
    env_url = os.environ.get("ATENEA_SERVER")
    if env_url:
        return env_url
    
    config = load_config()
    return config.get("server_url", DEFAULT_CONFIG["server_url"])
