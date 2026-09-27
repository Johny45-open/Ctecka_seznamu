"""Jediný zdroj pravdy pro verzi aplikace.

GitHub Releases je prázdný (ověřeno: /releases/latest -> 404, /releases -> []),
proto výchozí verze 1.0.0. Po prvním vydaném releasu synchronizovat ručně.
"""

APP_NAME = "Čtečka seznamů"
APP_VERSION = "1.0.0"
GITHUB_REPO = "Johny45-open/Ctecka_seznamu"
GITHUB_LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
