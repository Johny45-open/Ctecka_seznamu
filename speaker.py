import ctypes
import pyttsx3
from accessible_output2.outputs.auto import Auto

class Speaker:
    def __init__(self):
        self.is_screen_reader = self._check_screen_reader()
        if self.is_screen_reader:
            self.engine = Auto()
        else:
            self.engine = pyttsx3.init()
            # Výchozí nastavení, lze v budoucnu měnit
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)

    def _check_screen_reader(self):
        # SPI_GETSCREENREADER = 70
        val = ctypes.c_uint(0)
        if ctypes.windll.user32.SystemParametersInfoW(70, 0, ctypes.byref(val), 0):
            return val.value != 0
        return False

    def speak(self, text, interrupt=False):
        print(f"Hlas: {text}")
        if self.is_screen_reader:
            self.engine.speak(text)
        else:
            if interrupt:
                self.engine.stop()
            self.engine.say(text)
            self.engine.runAndWait()

    def set_rate(self, rate):
        if not self.is_screen_reader:
            self.engine.setProperty('rate', rate)

    def set_volume(self, volume):
        if not self.is_screen_reader:
            self.engine.setProperty('volume', volume)
