import time
import keyboard
import queue
import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer
from speaker import Speaker
from word_handler import WordHandler
from worker import WordMonitor
import config
from settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)

# Globální reference nastavené v main() – přístupné pro hotkey callbacky
speaker: Speaker | None = None
word: WordHandler | None = None
update_queue: queue.Queue | None = None


def speak(text, interrupt=False):
    if speaker is not None:
        speaker.speak(text, interrupt)


def check_typing():
    for key in "abcdefghijklmnopqrstuvwxyz0123456789":
        if keyboard.is_pressed(key):
            return True
    return False


def navigate_next():
    if word is None:
        return
    if word.move_to_next_list_item():
        speak("Další položka")
    else:
        speak("Konec seznamu")


def navigate_prev():
    if word is None:
        return
    if word.move_to_previous_list_item():
        speak("Předchozí položka")
    else:
        speak("Začátek seznamu")


def navigate_parent():
    if word is None:
        return
    if word.move_to_parent_list_item():
        speak("Nadřazená položka")
    else:
        speak("Žádná nadřazená položka")


def navigate_start():
    if word is None:
        return
    word.move_to_start_of_list()
    speak("Začátek seznamu")


def navigate_end():
    if word is None:
        return
    word.move_to_end_of_list()
    speak("Konec seznamu")


def announce_hierarchy():
    if word is None:
        return
    para = word.get_selection_paragraph()
    path = word.get_hierarchy_path(para)
    speak(f"Cesta: {path}")


def show_word_error_dialog(parent=None):
    """Přístupný PyQt6 dialog pro nedostupný Word.

    Vrací True pro 'Zkusit znovu', False pro 'Ukončit aplikaci'.
    Splňuje: název okna, Tab navigace, pojmenované controls, NVDA.
    """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle("Microsoft Word není dostupný")
    msg_box.setText("Microsoft Word nebyl nalezen nebo není dostupný.")
    msg_box.setInformativeText(
        "Zkontrolujte, zda je Microsoft Word spuštěný a obsahuje otevřený dokument.\n"
        "Chcete to zkusit znovu, nebo aplikaci ukončit?"
    )
    msg_box.setIcon(QMessageBox.Icon.Warning)
    # Přístupnost
    msg_box.setAccessibleName("Dialog chyby připojení k Wordu")
    msg_box.setAccessibleDescription(
        "Microsoft Word není dostupný. Vyberte Zkusit znovu pro opakování připojení nebo Ukončit aplikaci."
    )

    retry_button = msg_box.addButton("Zkusit znovu", QMessageBox.ButtonRole.AcceptRole)
    retry_button.setAccessibleName("Zkusit znovu")
    retry_button.setAccessibleDescription("Zkusí se znovu připojit k Microsoft Wordu")

    exit_button = msg_box.addButton("Ukončit aplikaci", QMessageBox.ButtonRole.RejectRole)
    exit_button.setAccessibleName("Ukončit aplikaci")
    exit_button.setAccessibleDescription("Ukončí aplikaci Čtečka seznamů")

    msg_box.setDefaultButton(retry_button)
    msg_box.setEscapeButton(exit_button)

    msg_box.exec()
    return msg_box.clickedButton() == retry_button


def show_empty_document_dialog(parent=None):
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle("Prázdný dokument")
    msg_box.setText("Dokument neobsahuje žádný text.")
    msg_box.setInformativeText("Aplikace bude ukončena.")
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setAccessibleName("Dialog prázdný dokument")
    msg_box.setAccessibleDescription("Dokument je prázdný. Aplikace bude ukončena.")
    ok_btn = msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
    ok_btn.setAccessibleName("OK")
    ok_btn.setAccessibleDescription("Potvrdit a ukončit aplikaci")
    msg_box.setDefaultButton(ok_btn)
    msg_box.exec()


def main():
    global speaker, word, update_queue

    # ---- Konfigurace a QApplication ----
    cfg = config.load_config()

    app = QApplication(sys.argv)
    app.setApplicationName("Čtečka seznamů pro Word")

    # Inicializace Speaker a WordHandler až po QApplication (žádný side-effect při importu)
    speaker = Speaker()
    word = WordHandler(auto_connect=False)
    update_queue = queue.Queue()

    # Prvotní spuštění - zobrazit dialog, pokud neexistuje soubor
    if not os.path.exists(config.CONFIG_FILE):
        dialog = SettingsDialog(cfg)
        if dialog.exec():
            cfg = dialog.get_config()
            config.save_config(cfg)
        else:
            sys.exit(0)

    speaker.set_rate(cfg["rate"])
    speaker.set_volume(cfg["volume"])

    # ---- Otevření nastavení za běhu ----
    def open_settings():
        dialog = SettingsDialog(config.load_config())
        if dialog.exec():
            new_cfg = dialog.get_config()
            config.save_config(new_cfg)
            speaker.set_rate(new_cfg["rate"])
            speaker.set_volume(new_cfg["volume"])
            speak("Nastavení bylo aktualizováno.")

    keyboard.add_hotkey("ctrl+shift+s", open_settings)

    # ---- Detekce Wordu – programově bez ptaní, pak GUI dialog ----
    # Nejprve zkusit připojit programově
    while not word.try_connect():
        # Word není dostupný -> přístupný dialog
        should_retry = show_word_error_dialog()
        if not should_retry:
            # Ukončení bez pádu, korektně počkat na hlas
            try:
                speak("Ukončuji aplikaci.")
                speaker.wait_for_speech_to_finish()
            except Exception:
                pass
            sys.exit(0)
        # jinak pokračuje smyčka a zkusí znovu

    # ---- Ostatní nastavení ----
    silent_mode_enabled = cfg["silent_mode"]
    only_lists = cfg["reporting_mode"]

    def toggle_silent_mode():
        nonlocal silent_mode_enabled
        silent_mode_enabled = not silent_mode_enabled
        status = "zapnutý" if silent_mode_enabled else "vypnutý"
        speak(f"Režim mlčení při psaní je nyní {status}")
        new_cfg = config.load_config()
        new_cfg["silent_mode"] = silent_mode_enabled
        config.save_config(new_cfg)

    keyboard.add_hotkey("ctrl+shift+m", toggle_silent_mode)

    keyboard.add_hotkey("alt+shift+right", navigate_next)
    keyboard.add_hotkey("alt+shift+left", navigate_prev)
    keyboard.add_hotkey("alt+shift+up", navigate_parent)
    keyboard.add_hotkey("alt+shift+home", navigate_start)
    keyboard.add_hotkey("alt+shift+end", navigate_end)
    keyboard.add_hotkey("alt+shift+c", announce_hierarchy)

    # ---- Inicializace dokumentu ----
    doc_type, list_count, text_count = word.analyze_document()
    if doc_type == "prázdný":
        speak("Dokument neobsahuje žádný text. Ukončuji aplikaci.")
        speaker.wait_for_speech_to_finish()
        show_empty_document_dialog()
        sys.exit(0)

    speak(f"Otevřený dokument se jmenuje: {word.doc.Name}")
    speak(f"Dokument obsahuje {doc_type}. Seznamů: {list_count}, normálních odstavců: {text_count}")

    # ---- Sledování Wordu – integrace s Qt event loopem ----
    monitor = WordMonitor(update_queue)
    monitor.start()

    last_nonlist_text = ""
    last_info = None

    speak("Nyní sleduji Word. Přesuň kurzor.")

    # Ukončení: zajistit korektní cleanup při zavření aplikace
    def cleanup():
        try:
            monitor.stop()
        except Exception:
            pass
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

    app.aboutToQuit.connect(cleanup)

    # QTimer místo blokující while True – umožňuje app.exec() a GUI dialogy
    def poll_queue():
        nonlocal last_nonlist_text, last_info
        try:
            info = update_queue.get_nowait()
        except queue.Empty:
            return

        typing = check_typing()
        if info:
            if info["type"] == "seznam":
                if not last_info or info["text"] != last_info["text"] or info["level"] != last_info["level"] or info["index"] != last_info["index"]:
                    if not (silent_mode_enabled and typing):
                        msg = f"Položka: {info['text']}, Úroveň: {info['level']}, Pořadí: {info['index']} z {info['siblings_count']}, Podpoložek: {info['subitems_count']}"
                        speak(msg, interrupt=True)
                        last_info = info
            else:
                if info["text"] != last_nonlist_text and not only_lists:
                    speak(f"Mimo seznam: {info['text']}", interrupt=True)
                    last_nonlist_text = info["text"]
                    last_info = None

    timer = QTimer()
    timer.timeout.connect(poll_queue)
    timer.start(100)

    # Spuštění Qt event loopu – aplikace je nyní GUI, ne konzolová
    exit_code = app.exec()
    # Fallback cleanup pokud aboutToQuit nebyl zavolán
    cleanup()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
