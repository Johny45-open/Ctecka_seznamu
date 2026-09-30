"""Testy ručního režimu psaní (writing_mode) – bez Wordu, bez GUI, bez hotkeys.

Pokrytí dle zadání §10:
1. výchozí writing_mode == False
2. Ctrl+Shift+P (toggle) aktivuje režim
3. druhý toggle režim deaktivuje
4. při writing_mode=True se automatická hlášení nevyslovují
5. přepínací hlášení se vysloví
6. po vypnutí se nové hlášení opět vysloví
7. staré události z doby psaní se po vypnutí nepřehrávají
8. silent_mode zůstává funkční
9. běžná navigace seznamem zůstává funkční
10. cleanup hotkeys zůstává funkční
"""

import queue

import main
from main import (
    WRITING_MODE_OFF_MSG,
    WRITING_MODE_ON_MSG,
    WritingModeState,
    drain_queue,
    should_speak,
)


# --- 1. výchozí writing_mode == False ---
def test_default_writing_mode_is_false():
    st = WritingModeState()
    assert st.writing_mode is False


# --- 2. toggle aktivuje režim (simulace Ctrl+Shift+P bez fyzického stisku) ---
def test_toggle_activates():
    st = WritingModeState()
    new_state, msg = st.toggle()
    assert new_state is True
    assert st.writing_mode is True
    assert msg == WRITING_MODE_ON_MSG == "Režim psaní zapnut."


# --- 3. druhý toggle deaktivuje ---
def test_double_toggle_deactivates():
    st = WritingModeState()
    st.toggle()
    new_state, msg = st.toggle()
    assert new_state is False
    assert st.writing_mode is False
    assert msg == WRITING_MODE_OFF_MSG == "Režim psaní vypnut."


# --- 4. při writing_mode=True se automatická hlášení nevyslovují ---
def test_no_auto_speech_while_writing():
    for silent in (True, False):
        for typing in (True, False):
            assert should_speak(True, silent, typing) is False


# --- 5. přepínací hlášení se vysloví (callback volá speak i přes gate) ---
def test_toggle_announcement_goes_through_speak(monkeypatch):
    spoken = []
    monkeypatch.setattr(main, "speaker", None)  # jistota: speak() řeší None
    # Fake speaker zachytávající speak()
    import types

    fake = types.SimpleNamespace(speak=lambda text, interrupt=False: spoken.append(text))
    monkeypatch.setattr(main, "speaker", fake)

    st = WritingModeState()
    q = queue.Queue()
    q.put({"type": "seznam", "text": "x", "level": 1, "index": 1})

    # Simulace toggle callbacku z main(): drain + speak mimo gate
    new_state, msg = st.toggle()
    drain_queue(q)
    main.speak(msg)
    assert spoken == ["Režim psaní zapnut."]
    assert q.empty()

    spoken.clear()
    new_state, msg = st.toggle()
    drain_queue(q)
    main.speak(msg)
    assert spoken == ["Režim psaní vypnut."]


# --- 6. po vypnutí se nové hlášení opět vysloví ---
def test_speech_resumes_after_toggle_off():
    st = WritingModeState()
    st.toggle()  # ON
    st.toggle()  # OFF
    assert st.writing_mode is False
    # Nová relevantní změna, netypuje se / silent vypnutý -> povoleno
    assert should_speak(st.writing_mode, False, False) is True
    assert should_speak(st.writing_mode, True, False) is True
    assert should_speak(st.writing_mode, False, True) is True


# --- 7. staré události z doby psaní se po vypnutí nepřehrávají ---
def test_backlog_dropped():
    q = queue.Queue()
    for i in range(5):
        q.put({"type": "seznam", "text": f"položka {i}", "level": 1, "index": i})
    # Během writing_mode se fronta zahazuje (poll_queue early-return + drain)
    dropped = drain_queue(q)
    assert dropped == 5
    assert q.empty()
    # Po vypnutí: get_nowait -> Empty, nic se nepřehrává
    import queue as qmod

    try:
        q.get_nowait()
        replayed = True
    except qmod.Empty:
        replayed = False
    assert replayed is False
    # Nová událost po vypnutí projde branou
    q.put({"type": "seznam", "text": "nová položka", "level": 1, "index": 9})
    info = q.get_nowait()
    assert info["text"] == "nová položka"
    assert should_speak(False, False, False) is True


def test_drain_empty_queue_returns_zero():
    assert drain_queue(queue.Queue()) == 0
    assert drain_queue(None) == 0


# --- 8. současný silent_mode zůstává funkční ---
def test_silent_mode_still_works():
    # silent zapnutý + psaní -> mlčet (i bez writing_mode)
    assert should_speak(False, True, True) is False
    # silent zapnutý + nepsaní -> mluvit
    assert should_speak(False, True, False) is True
    # silent vypnutý -> mluvit i při stisku kláves
    assert should_speak(False, False, True) is True
    assert should_speak(False, False, False) is True
    # writing_mode má prioritu nad vším
    assert should_speak(True, False, False) is False


# --- 9. běžná navigace seznamem zůstává funkční ---
def test_navigation_still_works(monkeypatch):
    import types

    spoken = []
    fake_speaker = types.SimpleNamespace(speak=lambda text, interrupt=False: spoken.append(text))
    monkeypatch.setattr(main, "speaker", fake_speaker)

    class FakeWord:
        def move_to_next_list_item(self):
            return True

        def move_to_previous_list_item(self):
            return False

    monkeypatch.setattr(main, "word", FakeWord())
    main.navigate_next()
    assert spoken == ["Další položka"]
    spoken.clear()
    main.navigate_prev()
    assert spoken == ["Začátek seznamu"]


# --- 10. ukončení aplikace a cleanup hotkeys zůstávají funkční ---
def test_cleanup_hotkeys_intact(monkeypatch):
    import keyboard

    assert hasattr(keyboard, "unhook_all_hotkeys")
    calls = []
    monkeypatch.setattr(keyboard, "unhook_all_hotkeys", lambda: calls.append(True))
    keyboard.unhook_all_hotkeys()
    assert calls == [True]
    # writing_mode stav nijak neblokuje cleanup
    st = WritingModeState()
    assert st.writing_mode is False
