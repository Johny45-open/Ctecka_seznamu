import pygame
from gtts import gTTS
import io
import speech_recognition as sr

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

# ---- Hlasový vstup ----
def listen_yes_no():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        speak("Běží Word? Odpověz ano nebo ne.")  # hlas + výpis
        audio = r.listen(source)
    try:
        text = r.recognize_google(audio, language="cs-CZ")
        print(f"Rozpoznáno: {text}")  # debug do příkazovky
        if "ano" in text.lower():
            return True
        return False
    except:
        return False

# ---- Použití ----
if not listen_yes_no():
    speak("Word neběží, ukončuji aplikaci.")
    exit()
else:
    speak("Super, začínám číst Word.")
