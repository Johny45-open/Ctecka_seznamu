import ctypes
import logging
import win32com.client
from accessible_output2.outputs.auto import Auto

logger = logging.getLogger(__name__)

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
        logger.debug("Hlas: %s", text)
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
        logger.debug("SAPI RunningState = %s", state)
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
            logger.debug("Čekání na hlas ukončeno.")

    def set_rate(self, rate):
        if not self.is_screen_reader:
            sapi_rate = min(10, max(-10, (rate - 150) // 10))
            logger.debug("Nastavuji SAPI Rate na %s (z původních %s)", sapi_rate, rate)
            self.engine.Rate = sapi_rate

    def set_volume(self, volume):
        if not self.is_screen_reader:
            vol = int(max(0, min(100, volume * 100)))
            logger.debug("Nastavuji SAPI Volume na %s (z původních %s)", vol, volume)
            self.engine.Volume = vol

    def list_voices(self):
        """Vrátí list[(voice_id, voice_name)] pro SAPI, prázdný pokud běží odečítač."""
        if self.is_screen_reader:
            return []
        try:
            voices = []
            for v in self.engine.GetVoices():
                try:
                    vid = v.Id
                    vname = v.GetDescription()
                    voices.append((vid, vname))
                except Exception:
                    continue
            return voices
        except Exception as e:
            logger.debug("list_voices selhal: %s", e)
            return []

    def set_voice(self, voice_id):
        """Nastaví SAPI hlas podle Id. Vrací True pokud úspěšně, False jinak.
        Vyžaduje SAPI engine (ne screen reader)."""
        if self.is_screen_reader or not voice_id:
            return False
        try:
            for v in self.engine.GetVoices():
                if v.Id == voice_id:
                    self.engine.Voice = v
                    logger.debug("Nastaven SAPI hlas na %s", voice_id)
                    return True
            logger.debug("Hlas %s nenalezen", voice_id)
            return False
        except Exception as e:
            logger.debug("set_voice selhal: %s", e)
            return False

    def get_current_voice_id(self):
        if self.is_screen_reader:
            return None
        try:
            return self.engine.Voice.Id
        except Exception:
            return None
