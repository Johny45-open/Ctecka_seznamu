"""Kontrola aktualizací přes GitHub Releases API.

Čistý modul bez závislosti na Qt/GUI – síť, parsování a porovnání verzí.
GUI vrstva řeší pouze prezentaci výsledku (update_dialog.py),
spouštění na pozadí řeší update_worker.py (QThread).

Endpoint: https://api.github.com/repos/Johny45-open/Ctecka_seznamu/releases/latest
Pouze stdlib (urllib), timeout 8 s.
"""

import json
import logging
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional, Tuple

from version import APP_VERSION, GITHUB_LATEST_RELEASE_URL

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 8  # sekund, dle zadání ~5-10 s

# Uživatelsky přívětivé hlášky (čeština, bez technických detailů navíc)
MSG_NO_CONNECTION = "Nelze se připojit k internetu."
MSG_TIMEOUT = "Připojení vypršelo (timeout)."
MSG_UNAVAILABLE = "Server aktualizací není momentálně dostupný."
MSG_RATE_LIMIT = "Server aktualizací není momentálně dostupný (limit GitHub API). Zkuste to později."
MSG_INVALID_RESPONSE = "Odpověď serveru je neplatná."


class InvalidVersionError(ValueError):
    """Neplatný formát verze."""


def parse_version(value: str) -> Tuple[int, ...]:
    """Převede 'v1.2.3' / '1.2.3' na (1, 2, 3). Podporuje víceciferné části.

    Raises:
        InvalidVersionError: prázdný řetězec, chybějící čísla, nečíselné části.
    """
    if value is None:
        raise InvalidVersionError("Verze je None")
    s = str(value).strip()
    if not s:
        raise InvalidVersionError("Prázdná verze")
    # Prefix v/V (např. tag_name = v1.4.0)
    if s[:1] in ("v", "V"):
        s = s[1:].strip()
    if not s:
        raise InvalidVersionError(f"Neplatná verze: {value!r}")
    parts = s.split(".")
    numbers = []
    for part in parts:
        part = part.strip()
        if not part.isdigit():
            raise InvalidVersionError(f"Neplatná verze: {value!r}")
        numbers.append(int(part))
    if not numbers:
        raise InvalidVersionError(f"Neplatná verze: {value!r}")
    return tuple(numbers)


def compare_versions(a: str, b: str) -> int:
    """Porovná dvě verze numericky. Vrací -1 / 0 / 1 (a < b, a == b, a > b).

    Kratší verze se doplní nulami: 1.2 == 1.2.0.
    """
    ta = parse_version(a)
    tb = parse_version(b)
    length = max(len(ta), len(tb))
    ta += (0,) * (length - len(ta))
    tb += (0,) * (length - len(tb))
    if ta < tb:
        return -1
    if ta > tb:
        return 1
    return 0


def normalize_version(value: str) -> str:
    """Vrátí verzi bez prefixu 'v' pro zobrazení (v1.4.0 -> 1.4.0)."""
    s = str(value).strip()
    if s[:1] in ("v", "V"):
        return s[1:].strip()
    return s


@dataclass
class UpdateCheckResult:
    """Výsledek kontroly. status: 'update_available' | 'up_to_date' | 'error'."""

    status: str
    current_version: str
    latest_version: Optional[str] = None
    release_url: Optional[str] = None
    release_notes: Optional[str] = None
    error_kind: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.status == "error"

    @property
    def has_update(self) -> bool:
        return self.status == "update_available"


def _is_rate_limit(http_error: urllib.error.HTTPError) -> bool:
    """Detekuje GitHub rate limit: 403/429 + hlavičky nebo text chyby."""
    code = getattr(http_error, "code", None)
    if code not in (403, 429):
        return False
    try:
        headers = http_error.headers or {}
        remaining = headers.get("X-RateLimit-Remaining", "")
        if str(remaining).strip() == "0":
            return True
    except Exception:
        pass
    try:
        body = http_error.read().decode("utf-8", errors="replace")
        if "rate limit" in body.lower():
            return True
    except Exception:
        pass
    # I bez potvrzení v těle považujeme 403/429 od GitHub API za limit/nedostupnost
    return True


def _fetch_latest_release(
    url: str = GITHUB_LATEST_RELEASE_URL, timeout: int = REQUEST_TIMEOUT
) -> dict:
    """Stáhne JSON nejnovějšího releasu. Vyhazuje zpracovatelné výjimky."""
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Ctecka-seznamu-update-checker",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def check_for_updates(
    current_version: Optional[str] = None,
    url: str = GITHUB_LATEST_RELEASE_URL,
    timeout: int = REQUEST_TIMEOUT,
) -> UpdateCheckResult:
    """Hlavní vstup: ověří nejnovější stabilní release. Nikdy nevyhazuje.

    Vrací vždy UpdateCheckResult (chyba = status 'error', aplikace nesmí spadnout).
    """
    current = current_version if current_version is not None else APP_VERSION
    try:
        current_norm = normalize_version(current)
        parse_version(current)  # validace aktuální verze
    except InvalidVersionError:
        logger.debug("Neplatná aktuální verze: %r", current)
        return UpdateCheckResult(
            status="error",
            current_version=str(current),
            error_kind="invalid_version",
            error_message=MSG_INVALID_RESPONSE,
        )

    try:
        data = _fetch_latest_release(url=url, timeout=timeout)
    except (socket.timeout, TimeoutError):
        return UpdateCheckResult(
            status="error", current_version=current_norm,
            error_kind="timeout", error_message=MSG_TIMEOUT,
        )
    except urllib.error.HTTPError as e:
        logger.debug("GitHub API HTTP chyba: %s", e)
        if _is_rate_limit(e):
            return UpdateCheckResult(
                status="error", current_version=current_norm,
                error_kind="rate_limit", error_message=MSG_RATE_LIMIT,
            )
        return UpdateCheckResult(
            status="error", current_version=current_norm,
            error_kind="http_error", error_message=MSG_UNAVAILABLE,
        )
    except urllib.error.URLError as e:
        # URLError obaluje i timeouty (reason je socket.timeout) a DNS/výpadky
        reason = getattr(e, "reason", None)
        logger.debug("GitHub API URLError: %s", e)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return UpdateCheckResult(
                status="error", current_version=current_norm,
                error_kind="timeout", error_message=MSG_TIMEOUT,
            )
        # TimeoutError se může objevit i jako string reason; TimeoutError je podtřída OSError
        if isinstance(reason, OSError) and "timed out" in str(reason).lower():
            return UpdateCheckResult(
                status="error", current_version=current_norm,
                error_kind="timeout", error_message=MSG_TIMEOUT,
            )
        # DNS / refused / no route – typicky výpadek internetu
        return UpdateCheckResult(
            status="error", current_version=current_norm,
            error_kind="no_connection", error_message=MSG_NO_CONNECTION,
        )
    except TimeoutError:
        return UpdateCheckResult(
            status="error", current_version=current_norm,
            error_kind="timeout", error_message=MSG_TIMEOUT,
        )
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
        logger.debug("Neplatný JSON z GitHub API: %s", e)
        return UpdateCheckResult(
            status="error", current_version=current_norm,
            error_kind="invalid_response", error_message=MSG_INVALID_RESPONSE,
        )
    except OSError as e:
        # Obecný síťový pád (např. socket.error) – nerozbít aplikaci
        logger.debug("Síťová chyba: %s", e)
        return UpdateCheckResult(
            status="error", current_version=current_norm,
            error_kind="no_connection", error_message=MSG_NO_CONNECTION,
        )
    except Exception as e:  # poslední záchrana – kontrola nesmí shodit aplikaci
        logger.debug("Neočekávaná chyba kontroly aktualizací: %s", e)
        return UpdateCheckResult(
            status="error", current_version=current_norm,
            error_kind="unavailable", error_message=MSG_UNAVAILABLE,
        )

    # --- Parsování release ---
    tag = data.get("tag_name") if isinstance(data, dict) else None
    if not tag:
        logger.debug("Chybějící tag_name v odpovědi: %r", data)
        return UpdateCheckResult(
            status="error", current_version=current_norm,
            error_kind="invalid_response", error_message=MSG_INVALID_RESPONSE,
        )
    try:
        cmp = compare_versions(current, tag)
    except InvalidVersionError:
        logger.debug("Neplatná verze v tag_name: %r", tag)
        return UpdateCheckResult(
            status="error", current_version=current_norm,
            error_kind="invalid_version", error_message=MSG_INVALID_RESPONSE,
        )

    latest_norm = normalize_version(tag)
    release_url = data.get("html_url") if isinstance(data, dict) else None
    release_notes = data.get("body") if isinstance(data, dict) else None

    if cmp < 0:
        return UpdateCheckResult(
            status="update_available",
            current_version=current_norm,
            latest_version=latest_norm,
            release_url=release_url,
            release_notes=release_notes,
        )
    return UpdateCheckResult(
        status="up_to_date",
        current_version=current_norm,
        latest_version=latest_norm,
        release_url=release_url,
        release_notes=release_notes,
    )
