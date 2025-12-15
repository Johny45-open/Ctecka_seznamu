import win32com.client
import time
import pygame
from gtts import gTTS
import io

# ---- Hlasový výstup ----
pygame.init()
def speak(text):
    print(text)  # vypíše do příkazovky
    tts = gTTS(text=text, lang='cs')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    pygame.mixer.music.load(fp, "mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

# ---- Dotaz na uživatele ----
def ask_word_running():
    speak("Běží Word? Odpověz ano nebo ne.")
    answer = input("Zadej odpověď (ano/ne): ").strip().lower()
    if answer.startswith("a"):
        speak("Super, začínám číst Word.")
        return True
    else:
        speak("Word neběží, ukončuji aplikaci.")
        return False

if not ask_word_running():
    exit()

# ---- Dotaz na typ hlášení ----
speak("Chceš hlásit jen seznamy, nebo i normální text?")
speak("Zadej 1 pro seznamy, 2 pro seznamy a mimo seznam.")
mode = input("Zadej 1 nebo 2: ").strip()
only_lists = mode == "1"

# ---- Připojení k Wordu ----
word = win32com.client.Dispatch("Word.Application")
if word.Documents.Count == 0:
    word.Documents.Add()
doc = word.ActiveDocument
last_position = -1
last_in_list = False  # pamatujeme si, jestli jsme byli v seznamu

# ---- Funkce pro počítání podpoložek ----
def count_subitems(paragraph):
    if paragraph.Range.ListFormat.ListType == 0:
        return 0
    level = paragraph.Range.ListFormat.ListLevelNumber
    start = paragraph.Range.Start
    end = paragraph.Range.End
    count = 0
    for p in doc.Paragraphs:
        if p.Range.ListFormat.ListType != 0:
            p_level = p.Range.ListFormat.ListLevelNumber
            p_start = p.Range.Start
            if start < p_start < end and p_level > level:
                count += 1
    return count

# ---- Funkce pro získání informací o odstavci ----
def get_info(paragraph):
    text = paragraph.Range.Text.strip()
    if paragraph.Range.ListFormat.ListType != 0:  # seznam
        level = paragraph.Range.ListFormat.ListLevelNumber
        siblings_count = sum(
            1 for p in doc.Paragraphs
            if p.Range.ListFormat.ListType !=0 and p.Range.ListFormat.ListLevelNumber==level
        )
        index = sum(
            1 for p in doc.Paragraphs
            if p.Range.ListFormat.ListType!=0 and p.Range.ListFormat.ListLevelNumber==level and p.Range.Start<=paragraph.Range.Start
        )
        subitems_count = count_subitems(paragraph)
        return {"text": text, "level": level, "index": index, "siblings_count": siblings_count, "subitems_count": subitems_count, "type": "seznam"}
    else:
        return {"text": text, "type": "text"}

# ---- Sledování Wordu ----
speak("Nyní sleduji Word. Přesuň kurzor do seznamu nebo textu.")
try:
    while True:
        sel = word.Selection
        start = sel.Start
        if start != last_position:
            last_position = start
            para = sel.Paragraphs(1)
            info = get_info(para)

            if info["type"] == "seznam":
                last_in_list = True
                speak(f"Položka seznamu: '{info['text']}', Úroveň: {info['level']}, Pořadí: {info['index']} z {info['siblings_count']}, Podpoložek: {info['subitems_count']}")
            else:
                if last_in_list and not only_lists:  # vyšel z seznamu
                    speak(f"Mimo seznam: '{info['text']}'")
                last_in_list = False  # teď jsme mimo seznam

        time.sleep(0.5)
except KeyboardInterrupt:
    speak("Ukončuji sledování Wordu.")
