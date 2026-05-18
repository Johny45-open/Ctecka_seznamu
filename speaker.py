import ctypes
import win32com.client
from accessible_output2.outputs.auto import Auto

class Speaker:
    def __init__(self):
        self.is_screen_reader = self._check_screen_reader()
        if self.is_screen_reader:
            self.engine = Auto()
        else:
            self.engine = win32com.client.Dispatch("SAPI.SpVoice")
            self.rate = 0
            self.volume = 100

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
            flags = 1
            if interrupt:
                flags = 3
            self.engine.Speak(text, flags)

    def is_speaking(self):
        if self.is_screen_reader:
            return False
        # 1 = SVSFPending, 2 = SVSFIsSpeaking
        state = self.engine.Status.RunningState
        print(f"Debug: SAPI RunningState = {state}")
        return state != 0

    def wait_for_speech_to_finish(self):
        if not self.is_screen_reader:
            import time
            time.sleep(0.3)
            # Pokud se to zasekává, zkusíme bezpečný limit čekání 5 sekund
            max_wait = 50 
            while self.is_speaking() and max_wait > 0:
                time.sleep(0.1)
                max_wait -= 1
            print("Debug: Čekání na hlas ukončeno.")

    def set_rate(self, rate):
        if not self.is_screen_reader:
            sapi_rate = min(10, max(-10, (rate - 150) // 10))
            print(f"Debug: Nastavuji SAPI Rate na {sapi_rate} (z původních {rate})")
            self.engine.Rate = sapi_rate

    def set_volume(self, volume):
        if not self.is_screen_reader:
            vol = int(max(0, min(100, volume * 100)))
            print(f"Debug: Nastavuji SAPI Volume na {vol} (z původních {volume})")
            self.engine.Volume = vol
