import win32com.client
import time
from accessible_output2.outputs.auto import Auto

# ---- Hlasový výstup ----
speech = Auto()

def speak(text):
    print(text)  # pro kontrolu v příkazovce
    speech.speak(text)

# ---- Dotaz na uživatele, jestli běží Word ----
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

# ---- Připojení k Wordu ----
word = win32com.client.Dispatch("Word.Application")
if word.Documents.Count == 0:
    word.Documents.Add()
doc = word.ActiveDocument
last_position = -1
last_in_list = False  # pamatujeme si, jestli jsme byli v seznamu

# ---- Funkce pro analýzu dokumentu ----
def analyze_document(doc):
    list_count = 0
    text_count = 0
    for para in doc.Paragraphs:
        if para.Range.ListFormat.ListType != 0:
            list_count += 1
        elif para.Range.Text.strip():  # ignorujeme prázdné odstavce
            text_count += 1

    if list_count == 0 and text_count == 0:
        doc_type = "prázdný"
    elif list_count == 0:
        doc_type = "jen normální text"
    elif text_count == 0:
        doc_type = "jen seznamy"
    else:
        doc_type = "kombinace seznamů a normálního textu"
    
    return doc_type, list_count, text_count

# ---- Hlášení názvu a typu dokumentu ----
speak(f"Otevřený dokument se jmenuje: {doc.Name}")
doc_type, list_count, text_count = analyze_document(doc)
speak(f"Dokument obsahuje {doc_type}. Seznamů: {list_count}, normálních odstavců: {text_count}")

# ---- Dotaz na typ hlášení ----
if list_count > 0:
    speak("Chceš hlásit jen seznamy, nebo i normální text?")
    speak("Zadej 1 pro seznamy, 2 pro seznamy a mimo seznam.")
    mode = input("Zadej 1 nebo 2: ").strip()
    only_lists = mode == "1"
else:
    speak("V dokumentu nejsou žádné seznamy, hlásit budu jen normální text.")
    only_lists = False

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
    if not text:  # přeskočíme prázdné odstavce
        return None
    if paragraph.Range.ListFormat.ListType != 0:  # seznam
        level = paragraph.Range.ListFormat.ListLevelNumber
        siblings_count = sum(
            1 for p in doc.Paragraphs
            if p.Range.ListFormat.ListType !=0 and p.Range.ListFormat.ListLevelNumber==level
        )
        index = sum(
            1 for p in doc.Paragraphs
            if p.Range.ListFormat.ListType !=0 and p.Range.ListFormat.ListLevelNumber==level and p.Range.Start<=paragraph.Range.Start
        )
        subitems_count = count_subitems(paragraph)
        return {"text": text, "level": level, "index": index, "siblings_count": siblings_count, "subitems_count": subitems_count, "type": "seznam"}
    else:
        return {"text": text, "type": "text"}

# ---- Sledování Wordu ----
speak("Nyní sleduji Word. Přesuň kurzor do seznamu nebo textu.")
last_nonlist_text = ""  # pamatujeme si poslední text mimo seznam
try:
    while True:
        sel = word.Selection
        start = sel.Start
        if start != last_position:
            last_position = start
            para = sel.Paragraphs(1)
            info = get_info(para)
            if info is None:
                continue  # přeskočíme prázdný odstavec

            if info["type"] == "seznam":
                last_in_list = True
                speak(f"Položka seznamu: {info['text']}, Úroveň: {info['level']}, Pořadí: {info['index']} z {info['siblings_count']}, Podpoložek: {info['subitems_count']}")
            else:
                if info["text"] != last_nonlist_text and not only_lists:
                    speak(f"Mimo seznam: {info['text']}")
                    last_nonlist_text = info["text"]
                last_in_list = False

        time.sleep(0.3)  # zrychlené čekání, Auto je rychlejší
except KeyboardInterrupt:
    speak("Ukončuji sledování Wordu.")
