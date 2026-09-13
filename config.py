import json
import os

CONFIG_FILE = "config.json"

def load_config():
    default_config = {
        "rate": 150,
        "volume": 1.0,
        "reporting_mode": False,
        "silent_mode": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                # Zajistit, aby konfigurační soubor obsahoval všechna potřebná pole
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception:
            pass
    return default_config

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)
