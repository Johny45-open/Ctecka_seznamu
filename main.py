import time
import keyboard
from speaker import Speaker
from word_handler import WordHandler

# Inicializace
speaker = Speaker()
word = WordHandler()

def speak(text, interrupt=False):
    speaker.speak(text, interrupt)

# ---- Start aplikace ----
speak("Běží Word? Odpověz ano nebo ne.")
answer = input("Zadej odpověď (ano/ne): ").strip().lower()
if not answer.startswith("a"):
    speak("Word neběží, ukončuji aplikaci.")
    exit()

# ---- Režim mlčení ----
silent_mode_enabled = True

def toggle_silent_mode():
    global silent_mode_enabled
    silent_mode_enabled = not silent_mode_enabled
    status = "zapnutý" if silent_mode_enabled else "vypnutý"
    speak(f"Režim mlčení při psaní je nyní {status}")

keyboard.add_hotkey("ctrl+shift+m", toggle_silent_mode)

# ---- Inicializace dokumentu ----
speak(f"Otevřený dokument se jmenuje: {word.doc.Name}")
doc_type, list_count, text_count = word.analyze_document()
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
last_position = -1
last_nonlist_text = ""

speak("Nyní sleduji Word. Přesuň kurzor.")
try:
    while True:
        start = word.get_selection_start()
        typing = check_typing()
        
        if start != last_position:
            last_position = start
            para = word.get_selection_paragraph()
            info = word.get_info(para)
            
            if info:
                if info["type"] == "seznam":
                    if not (silent_mode_enabled and typing):
                        msg = f"Položka seznamu: {info['text']}, Úroveň: {info['level']}, Pořadí: {info['index']} z {info['siblings_count']}, Podpoložek: {info['subitems_count']}"
                        speak(msg, interrupt=True)
                else:
                    if info["text"] != last_nonlist_text and not only_lists:
                        speak(f"Mimo seznam: {info['text']}", interrupt=True)
                        last_nonlist_text = info["text"]
        
        time.sleep(0.3)
except KeyboardInterrupt:
    speak("Ukončuji sledování Wordu.")
