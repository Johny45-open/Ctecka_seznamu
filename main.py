import time
import keyboard
import queue
from speaker import Speaker
from word_handler import WordHandler
from worker import WordMonitor
import config

# Inicializace
speaker = Speaker()
word = WordHandler()
update_queue = queue.Queue()

# Pokud neběží čtečka, načteme konfiguraci
if not speaker.is_screen_reader:
    cfg = config.load_config()
    speaker.set_rate(cfg["rate"])
    speaker.set_volume(cfg["volume"])
    
    print(f"Aktuální nastavení: Rychlost={cfg['rate']}, Hlasitost={cfg['volume']}")
    zmenit = input("Chceš změnit nastavení hlasu? (ano/ne): ").strip().lower()
    if zmenit.startswith("a"):
        try:
            rate = int(input("Zadej rychlost hlasu (výchozí 150): ") or cfg["rate"])
            volume = float(input("Zadej hlasitost (0.0 až 1.0, výchozí 1.0): ") or cfg["volume"])
            speaker.set_rate(rate)
            speaker.set_volume(volume)
            config.save_config(rate, volume)
        except ValueError:
            print("Neplatný vstup, použiji staré hodnoty.")

def speak(text, interrupt=False):
    speaker.speak(text, interrupt)

# ---- Start aplikace ----
speak("Běží Word? Odpověz ano nebo ne.")
answer = input("Zadej odpověď (ano/ne): ").strip().lower()
if not answer.startswith("a"):
    speak("Word neběží, ukončuji aplikaci.")
    speaker.wait_for_speech_to_finish()
    exit()

# ---- Režim mlčení ----
silent_mode_enabled = True

def toggle_silent_mode():
    global silent_mode_enabled
    silent_mode_enabled = not silent_mode_enabled
    status = "zapnutý" if silent_mode_enabled else "vypnutý"
    speak(f"Režim mlčení při psaní je nyní {status}")

keyboard.add_hotkey("ctrl+shift+m", toggle_silent_mode)

# ---- Navigace a hierarchie ----
def navigate_next():
    if word.move_to_next_list_item():
        speak("Další položka")
    else:
        speak("Konec seznamu")

def navigate_prev():
    if word.move_to_previous_list_item():
        speak("Předchozí položka")
    else:
        speak("Začátek seznamu")

def navigate_parent():
    if word.move_to_parent_list_item():
        speak("Nadřazená položka")
    else:
        speak("Žádná nadřazená položka")

def navigate_start():
    word.move_to_start_of_list()
    speak("Začátek seznamu")

def navigate_end():
    word.move_to_end_of_list()
    speak("Konec seznamu")

def announce_hierarchy():
    para = word.get_selection_paragraph()
    path = word.get_hierarchy_path(para)
    speak(f"Cesta: {path}")

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
    exit()

speak(f"Otevřený dokument se jmenuje: {word.doc.Name}")
speak(f"Dokument obsahuje {doc_type}. Seznamů: {list_count}, normálních odstavců: {text_count}")

# ---- Typ hlášení ----
if list_count > 0:
    speak("Chceš hlásit jen seznamy, nebo i normální text?")
    mode = input("Zadej 1 pro seznamy, 2 pro seznamy a mimo seznam: ").strip()
    only_lists = mode == "1"
else:
    only_lists = False

# ---- Funkce pro check psaní ----
def check_typing():
    for key in "abcdefghijklmnopqrstuvwxyz0123456789":
        if keyboard.is_pressed(key):
            return True
    return False

# ---- Hlavní smyčka ----
monitor = WordMonitor(update_queue)
monitor.start()

last_nonlist_text = ""
last_info = None  # Cache pro poslední ohlášenou položku

speak("Nyní sleduji Word. Přesuň kurzor.")
try:
    while True:
        try:
            info = update_queue.get(timeout=0.1)
            typing = check_typing()
            
            if info:
                if info["type"] == "seznam":
                    # Kontrola, zda se změnily relevantní údaje
                    if not last_info or info["text"] != last_info["text"] or info["level"] != last_info["level"] or info["index"] != last_info["index"]:
                        if not (silent_mode_enabled and typing):
                            msg = f"Položka: {info['text']}, Úroveň: {info['level']}, Pořadí: {info['index']} z {info['siblings_count']}, Podpoložek: {info['subitems_count']}"
                            speak(msg, interrupt=True)
                            last_info = info
                else:
                    if info["text"] != last_nonlist_text and not only_lists:
                        speak(f"Mimo seznam: {info['text']}", interrupt=True)
                        last_nonlist_text = info["text"]
                        last_info = None # Reset při přechodu mimo seznam
        except queue.Empty:
            pass
        
        time.sleep(0.1)
except KeyboardInterrupt:
    monitor.stop()
    speak("Ukončuji sledování Wordu a zavírám aplikaci.")
    speaker.wait_for_speech_to_finish()
