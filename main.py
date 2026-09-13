import time
import keyboard
import queue
import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu, QDialog
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
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


class SettingsSignal(QObject):
    """Pomocný objekt pro thread-safe otevření nastavení z keyboard hotkey vlákna."""
    open_requested = pyqtSignal()


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


def build_announcement(info, cfg):
    """Sestaví hlášku podle aktuální konfigurace announce_*.

    Respektuje:
      announce_list_type, announce_level, announce_index, announce_subitems
    """
    parts = [f"Položka: {info['text']}"]
    if cfg.get("announce_level", True):
        parts.append(f"Úroveň: {info['level']}")
    if cfg.get("announce_index", True):
        parts.append(f"Pořadí: {info['index']} z {info['siblings_count']}")
    if cfg.get("announce_subitems", True):
        parts.append(f"Podpoložek: {info['subitems_count']}")
    return ", ".join(parts)


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

    # Aktuální runtime konfigurace držená v proměnné cfg (uzavřená v closure)
    # poll_queue a další callbacky čtou vždy aktuální cfg

    def apply_config(new_cfg):
        """Okamžitě aplikuje novou konfiguraci na běžící aplikaci."""
        nonlocal cfg
        cfg = new_cfg
        # Hlas – pouze pokud neběží odečítač
        try:
            speaker.set_rate(new_cfg["rate"])
            speaker.set_volume(new_cfg["volume"])
            # hlasový výstup – pokus o přepnutí SAPI hlasu
            voice_id = new_cfg.get("voice_id")
            if voice_id and not speaker.is_screen_reader:
                old_id = speaker.get_current_voice_id()
                if voice_id != old_id:
                    ok = speaker.set_voice(voice_id)
                    if not ok:
                        # Informovat uživatele že změna vyžaduje restart nebo selhala
                        m = QMessageBox()
                        m.setWindowTitle("Změna hlasu")
                        m.setText("Nepodařilo se přepnout hlas za běhu.")
                        m.setInformativeText("Zkuste restartovat aplikaci. Pokud problém přetrvává, vyberte jiný hlas v Nastavení.")
                        m.setIcon(QMessageBox.Icon.Warning)
                        m.setAccessibleName("Dialog informace o hlasu")
                        m.exec()
        except Exception as e:
            logger.debug("apply_config hlas selhal: %s", e)

    def show_settings_dialog(first_run: bool = False) -> bool:
        """Společná cesta pro prvotní i běžné Nastavení.

        Vrací True pokud uživatel potvrdil (uloženo), False pokud zrušil.
        Nemění config před potvrzením.
        """
        # Načti vždy aktuální hodnoty (first_run = výchozí, jinak uložené)
        current = config.load_config() if not first_run else config.get_default_config()
        # Pokud už existuje soubor a first_run=False, first_run parametr ignoruje soubor,
        # použije se aktuální uložená konfigurace. Pro first_run chceme výchozí.
        if first_run is False:
            current = config.load_config()
        else:
            # first_run: pokud soubor existuje (neměl by), přesto respektuj soubor?
            # Spec: při prvním spuštění načti výchozí hodnoty
            current = config.get_default_config()
            # ale pokud už soubor existuje, first_run se nevolá

        try:
            voices = speaker.list_voices() if speaker else []
        except Exception:
            voices = []

        dialog = SettingsDialog(
            current,
            first_run=first_run,
            available_voices=voices,
            is_screen_reader=speaker.is_screen_reader if speaker else False,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_cfg = dialog.get_config()
            config.save_config(new_cfg)
            apply_config(new_cfg)
            return True
        return False

    # Prvotní spuštění – zobrazit dialog, pokud neexistuje soubor
    if not os.path.exists(config.CONFIG_FILE):
        confirmed = show_settings_dialog(first_run=True)
        if not confirmed:
            sys.exit(0)
        # cfg už aktualizován v apply_config
    else:
        # Aplikuj hlas z existující konfigurace
        apply_config(cfg)

    # ---- Otevření nastavení za běhu – thread-safe signál ----
    settings_signal = SettingsSignal()

    def open_settings():
        if show_settings_dialog(first_run=False):
            speak("Nastavení bylo aktualizováno.")
        else:
            # Zrušeno – zachovat původní hodnoty, pouze potvrdit
            speak("Nastavení beze změny.")

    settings_signal.open_requested.connect(open_settings)

    def request_open_settings():
        # Voláno z keyboard vlákna – přepošli do GUI vlákna
        settings_signal.open_requested.emit()

    # Klávesová zkratka – primární Ctrl+Shift+Q (nekoliduje s Wordem)
    # Ctrl+Shift+S ponechána jako alias pro zpětnou kompatibilitu
    # Obě snadno dostupné, vhodné pro screen reader (levá ruka, ne Word).
    keyboard.add_hotkey("ctrl+shift+q", request_open_settings)
    keyboard.add_hotkey("ctrl+shift+s", request_open_settings)

    # ---- Systémová oznamovací oblast – druhý způsob otevření Nastavení ----
    tray = None
    try:
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray = QSystemTrayIcon(parent=app)
            # Zkusit ikonu aplikace, fallback na standardní
            icon = QIcon.fromTheme("preferences-system")
            if icon.isNull():
                icon = app.style().standardIcon(app.style().StandardPixmap.SP_ComputerIcon)
            tray.setIcon(icon)
            tray.setToolTip("Čtečka seznamů – Nastavení: Ctrl+Shift+Q")
            tray.setAccessibleName("Oznamovací oblast Čtečka seznamů")
            tray.setAccessibleDescription("Nabízí otevření Nastavení a ukončení aplikace. Klávesová zkratka Ctrl Shift Q.")

            menu = QMenu()
            act_settings = QAction("Nastavení…  (Ctrl+Shift+Q)", menu)
            act_settings.setAccessibleText("Otevřít Nastavení. Klávesová zkratka Ctrl Shift Q.")
            act_settings.triggered.connect(open_settings)
            menu.addAction(act_settings)

            menu.addSeparator()

            act_quit = QAction("Ukončit", menu)
            act_quit.triggered.connect(app.quit)
            menu.addAction(act_quit)

            tray.setContextMenu(menu)
            tray.show()
            # Dvojklik na ikonu také otevře nastavení
            tray.activated.connect(lambda reason: open_settings() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    except Exception as e:
        logger.debug("Tray init selhal: %s", e)
        tray = None

    # ---- Detekce Wordu – programově bez ptaní, pak GUI dialog ----
    while not word.try_connect():
        should_retry = show_word_error_dialog()
        if not should_retry:
            try:
                speak("Ukončuji aplikaci.")
                speaker.wait_for_speech_to_finish()
            except Exception:
                pass
            sys.exit(0)

    # ---- Ostatní nastavení – už řízeno přes cfg, toggle aktualizuje cfg ----
    def toggle_silent_mode():
        new_cfg = config.load_config()
        new_cfg["silent_mode"] = not new_cfg.get("silent_mode", True)
        config.save_config(new_cfg)
        apply_config(new_cfg)
        status = "zapnutý" if new_cfg["silent_mode"] else "vypnutý"
        speak(f"Režim mlčení při psaní je nyní {status}")

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

    speak("Nyní sleduji Word. Přesuň kurzor. Nastavení otevřete klávesovou zkratkou Ctrl Shift Q nebo z oznamovací oblasti.")

    def cleanup():
        try:
            monitor.stop()
        except Exception:
            pass
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        try:
            if tray is not None:
                tray.hide()
        except Exception:
            pass

    app.aboutToQuit.connect(cleanup)

    def poll_queue():
        nonlocal last_nonlist_text, last_info
        try:
            info = update_queue.get_nowait()
        except queue.Empty:
            return

        typing = check_typing()
        silent_mode_enabled = cfg.get("silent_mode", True)
        only_lists = cfg.get("reporting_mode", False)
        if info:
            if info["type"] == "seznam":
                if not last_info or info["text"] != last_info["text"] or info["level"] != last_info["level"] or info["index"] != last_info["index"]:
                    if not (silent_mode_enabled and typing):
                        msg = build_announcement(info, cfg)
                        speak(msg, interrupt=True)
                        last_info = info
            else:
                if info["text"] != last_nonlist_text and not only_lists:
                    # Respektovat announce_list_type – pokud vypnuto, nehlásit "Mimo seznam:"
                    if cfg.get("announce_list_type", True):
                        speak(f"Mimo seznam: {info['text']}", interrupt=True)
                    else:
                        speak(info["text"], interrupt=True)
                    last_nonlist_text = info["text"]
                    last_info = None

    timer = QTimer()
    timer.timeout.connect(poll_queue)
    timer.start(100)

    exit_code = app.exec()
    cleanup()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
