import json
import os

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"rate": 150, "volume": 1.0}

def save_config(rate, volume):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"rate": rate, "volume": volume}, f)
