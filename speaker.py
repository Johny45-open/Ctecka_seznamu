import ctypes
import win32com.client
from accessible_output2.outputs.auto import Auto

class Speaker:
    def __init__(self):
        self.is_screen_reader = self._check_screen_reader()
        if self.is_screen_reader:
            self.engine = Auto()
        else:
            # Použijeme nativní SAPI rozhraní pro maximální stabilitu na Windows
            self.engine = win32com.client.Dispatch("SAPI.SpVoice")
            self.rate = 0  # Výchozí rychlost SAPI je 0
            self.volume = 100 # Hlasitost 0-100

    def _check_screen_reader(self):
        val = ctypes.c_uint(0)
        if ctypes.windll.user32.SystemParametersInfoW(70, 0, ctypes.byref(val), 0):
            return val.value != 0
        return False

    def speak(self, text, interrupt=False):
        print(f"Hlas: {text}")
        if self.is_screen_reader:
            self.engine.speak(text)
        else:
            # SAPI.SpVoiceflags 1 (SVSFlagsAsync) zajistí, že hlas nebude blokovat program
            flags = 1
            if interrupt:
                # 3 = SVSFPurgeBeforeSpeak | SVSFlagsAsync
                flags = 3
            self.engine.Speak(text, flags)

    def set_rate(self, rate):
        if not self.is_screen_reader:
            # Přepočet z 150 (pyttsx3) na SAPI rozsah (-10 až 10)
            # Rychlost cca 150 v pyttsx3 odpovídá zhruba 0 v SAPI
            sapi_rate = min(10, max(-10, (rate - 150) // 10))
            self.engine.Rate = sapi_rate

    def set_volume(self, volume):
        if not self.is_screen_reader:
            self.engine.Volume = int(volume * 100)
