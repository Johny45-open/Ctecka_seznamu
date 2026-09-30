import json
import os
import shutil

APP_DIR_NAME = "Ctecka_seznamu"
LEGACY_CONFIG_FILE = "config.json"


def _get_appdata_dir():
    """Vrátí %APPDATA%\\Ctecka_seznamu, s fallbackem na ~ na ne-Windows."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, APP_DIR_NAME)
    return os.path.join(os.path.expanduser("~"), "." + APP_DIR_NAME)


CONFIG_DIR = _get_appdata_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

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


def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def migrate_legacy_config():
    """Nedestruktivní migrace ./config.json -> %APPDATA% (kopie, starý nemazat).

    Provede se jen pokud nový config neexistuje a starý ano.
    """
    try:
        if os.path.exists(CONFIG_FILE):
            return False
        if not os.path.exists(LEGACY_CONFIG_FILE):
            return False
        ensure_config_dir()
        shutil.copy2(LEGACY_CONFIG_FILE, CONFIG_FILE)
        return True
    except Exception:
        return False


def load_config():
    default_config = get_default_config()
    migrate_legacy_config()
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
    ensure_config_dir()
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_FILE)
