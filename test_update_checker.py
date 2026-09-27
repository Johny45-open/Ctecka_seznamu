"""Testy kontroly aktualizací – bez Wordu, bez GUI, bez internetu (mock).

Pokrytí dle zadání:
1. aktuální == nejnovější
2. aktuální < nejnovější
3. prefix 'v'
4. víceciferné verze (1.9.0 < 1.10.0)
5. neplatná verze
6. chybějící tag_name
7. timeout
8. HTTP chyba
9. neplatný JSON
10. rate limit (HTTP 403)
"""

import io
import json
import socket
import urllib.error

import pytest

import update_checker
from update_checker import (
    InvalidVersionError,
    check_for_updates,
    compare_versions,
    parse_version,
)


def _mock_response(payload: dict):
    """Vytvoří mock context manageru pro urllib.request.urlopen."""
    raw = json.dumps(payload).encode("utf-8")

    class FakeResponse:
        def read(self):
            return raw

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    return FakeResponse()


def _patch_urlopen(monkeypatch, fake):
    """Monkeypatchne update_checker.urllib.request.urlopen.

    fake: FakeResponse | Exception instance k vyhození.
    """
    import urllib.request

    def _fake_urlopen(request, timeout=None):
        if isinstance(fake, Exception):
            raise fake
        return fake

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)


# --- 1. aktuální == nejnovější ---
def test_up_to_date(monkeypatch):
    _patch_urlopen(monkeypatch, _mock_response({"tag_name": "1.0.0", "html_url": "https://example.com/r"}))
    result = check_for_updates(current_version="1.0.0")
    assert result.status == "up_to_date"
    assert result.latest_version == "1.0.0"


# --- 2. aktuální < nejnovější ---
def test_update_available(monkeypatch):
    _patch_urlopen(
        monkeypatch,
        _mock_response({"tag_name": "1.3.0", "html_url": "https://example.com/r/1.3.0", "body": "Novinky"}),
    )
    result = check_for_updates(current_version="1.2.0")
    assert result.status == "update_available"
    assert result.latest_version == "1.3.0"
    assert result.release_url == "https://example.com/r/1.3.0"


# --- 3. prefix 'v' ---
def test_v_prefix_same_version(monkeypatch):
    _patch_urlopen(monkeypatch, _mock_response({"tag_name": "v1.3.0"}))
    result = check_for_updates(current_version="1.3.0")
    assert result.status == "up_to_date"
    assert result.latest_version == "1.3.0"  # zobrazeno bez prefixu


def test_v_prefix_newer(monkeypatch):
    _patch_urlopen(monkeypatch, _mock_response({"tag_name": "v1.4.0"}))
    result = check_for_updates(current_version="1.3.0")
    assert result.status == "update_available"
    assert result.latest_version == "1.4.0"


# --- 4. víceciferné verze ---
def test_multidigit_versions():
    assert compare_versions("1.9.0", "1.10.0") == -1
    assert compare_versions("1.10.0", "1.9.0") == 1
    assert compare_versions("1.10.0", "1.10.0") == 0


def test_multidigit_update_available(monkeypatch):
    _patch_urlopen(monkeypatch, _mock_response({"tag_name": "1.10.0"}))
    result = check_for_updates(current_version="1.9.0")
    assert result.status == "update_available"


# --- 5. neplatná verze ---
def test_invalid_current_version(monkeypatch):
    _patch_urlopen(monkeypatch, _mock_response({"tag_name": "1.2.0"}))
    result = check_for_updates(current_version="nesmysl")
    assert result.status == "error"
    assert result.error_kind == "invalid_version"


def test_invalid_tag_version(monkeypatch):
    _patch_urlopen(monkeypatch, _mock_response({"tag_name": "beta-nesmysl!!!"}))
    result = check_for_updates(current_version="1.0.0")
    assert result.status == "error"
    assert result.error_kind == "invalid_version"


def test_parse_version_rejects_garbage():
    for bad in ["", "   ", "v", "1..2", "1.x.0", "a.b.c", None]:
        with pytest.raises(InvalidVersionError):
            parse_version(bad)


# --- 6. chybějící tag_name ---
def test_missing_tag_name(monkeypatch):
    _patch_urlopen(monkeypatch, _mock_response({"name": "release bez tagu"}))
    result = check_for_updates(current_version="1.0.0")
    assert result.status == "error"
    assert result.error_kind == "invalid_response"


# --- 7. timeout ---
def test_timeout_socket(monkeypatch):
    _patch_urlopen(monkeypatch, socket.timeout("timed out"))
    result = check_for_updates(current_version="1.0.0")
    assert result.status == "error"
    assert result.error_kind == "timeout"


def test_timeout_urlerror(monkeypatch):
    _patch_urlopen(
        monkeypatch, urllib.error.URLError(reason=socket.timeout("timed out"))
    )
    result = check_for_updates(current_version="1.0.0")
    assert result.status == "error"
    assert result.error_kind == "timeout"


# --- 8. HTTP chyba ---
def test_http_error(monkeypatch):
    err = urllib.error.HTTPError(
        url="https://api.github.com/x", code=500, msg="Server Error",
        hdrs={}, fp=io.BytesIO(b"boom"),
    )
    _patch_urlopen(monkeypatch, err)
    result = check_for_updates(current_version="1.0.0")
    assert result.status == "error"
    assert result.error_kind == "http_error"


# --- 9. neplatný JSON ---
def test_invalid_json(monkeypatch):
    import urllib.request

    class FakeBadResponse:
        def read(self):
            return "toto není JSON {{{".encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: FakeBadResponse())
    result = check_for_updates(current_version="1.0.0")
    assert result.status == "error"
    assert result.error_kind == "invalid_response"


# --- 10. rate limit (HTTP 403) ---
def test_rate_limit_403(monkeypatch):
    err = urllib.error.HTTPError(
        url="https://api.github.com/x", code=403, msg="Forbidden",
        hdrs={"X-RateLimit-Remaining": "0"},
        fp=io.BytesIO(b"API rate limit exceeded"),
    )
    _patch_urlopen(monkeypatch, err)
    result = check_for_updates(current_version="1.0.0")
    assert result.status == "error"
    assert result.error_kind == "rate_limit"


# --- doplňkové: výpadek připojení a nikdy nespadne ---
def test_no_connection(monkeypatch):
    _patch_urlopen(
        monkeypatch, urllib.error.URLError(reason=ConnectionRefusedError("refused"))
    )
    result = check_for_updates(current_version="1.0.0")
    assert result.status == "error"
    assert result.error_kind == "no_connection"


def test_unexpected_exception_never_raises(monkeypatch):
    import urllib.request

    def _boom(request, timeout=None):
        raise RuntimeError("neočekávané")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    result = check_for_updates(current_version="1.0.0")  # nesmí vyhodit
    assert result.status == "error"
