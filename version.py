"""Jediný zdroj pravdy pro verzi aplikace.

GitHub Releases je prázdný (ověřeno: /releases/latest -> 404, /releases -> []),
proto výchozí verze 1.0.0. Po prvním vydaném releasu synchronizovat ručně.
"""

APP_NAME = "Čtečka seznamů"
APP_VERSION = "1.1.0"
GITHUB_REPO = "Johny45-open/Ctecka_seznamu"
GITHUB_LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Build-time diagnostika (commit + čas buildu).
# Soubor _build_info.py generuje build.ps1; v dev prostředí chybí -> fallback.
try:
    from _build_info import BUILD_COMMIT, BUILD_TIME  # type: ignore
except Exception:
    BUILD_COMMIT = "dev"
    BUILD_TIME = "unknown"


def get_version_string():
    """Jednořádková identifikace buildu pro --version a logy (nemění UX)."""
    return f"{APP_NAME} {APP_VERSION} (commit {BUILD_COMMIT}, build {BUILD_TIME})"
