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
    if answer == "ano":
        speak("Super, začínám číst Word.")
        return True
    else:
        speak("Word neběží, ukončuji aplikaci.")
        return False

# ---- Použití ----
if not ask_word_running():
    exit()
