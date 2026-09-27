import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "rate": 150,
    "volume": 1.0,
    "reporting_mode": False,
    "silent_mode": True,
    "announce_level": True,
    "announce_index": True,
    "announce_subitems": True,
    "announce_list_type": True,
    "voice_id": None,
    "auto_check_updates": True,
    "last_update_check": None,
}


def get_default_config():
    """Vrátí kopii výchozích hodnot (bez reference na originál)."""
    return dict(DEFAULT_CONFIG)


def load_config():
    default_config = get_default_config()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Zajistit, aby konfigurační soubor obsahoval všechna potřebná pole (migrace)
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception:
            pass
    return default_config


def save_config(config_data):
    # Atomický zápis aby pád nepoškodil soubor
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_FILE)
