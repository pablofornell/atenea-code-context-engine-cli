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
    """Returns the configuration file path (~/.atenea/conf.json)."""
    return get_config_dir() / "conf.json"

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


def get_api_key() -> str | None:
    """
    Resolves the API key following this precedence:
    1. Environment variable ATENEA_API_KEY
    2. Config file api_key
    3. None (no authentication)
    """
    env_key = os.environ.get("ATENEA_API_KEY")
    if env_key:
        return env_key

    config = load_config()
    return config.get("api_key")


def get_verify_ssl() -> bool:
    """
    Resolves SSL certificate verification following this precedence:
    1. Environment variable ATENEA_VERIFY_SSL ("false" disables verification)
    2. Config file verify_ssl
    3. True (verification enabled by default)

    Set to False only when using a self-signed certificate (public IP deployment).
    """
    env_val = os.environ.get("ATENEA_VERIFY_SSL")
    if env_val is not None:
        return env_val.lower() not in ("false", "0", "no")

    config = load_config()
    return config.get("verify_ssl", True)


def get_ca_cert() -> str | None:
    """
    Resolves a custom CA certificate path following this precedence:
    1. Environment variable ATENEA_CA_CERT
    2. Config file ca_cert
    3. None (use system CAs)

    Use this to trust Caddy's self-signed root CA without disabling verification.
    Export it with:
      docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
    """
    env_cert = os.environ.get("ATENEA_CA_CERT")
    if env_cert:
        return env_cert

    config = load_config()
    return config.get("ca_cert")
