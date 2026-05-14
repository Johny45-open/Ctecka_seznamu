import ctypes
import pyttsx3
import threading
import queue
from accessible_output2.outputs.auto import Auto

class Speaker:
    def __init__(self):
        self.is_screen_reader = self._check_screen_reader()
        if self.is_screen_reader:
            self.engine = Auto()
        else:
            self.queue = queue.Queue()
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
            self.worker_thread = threading.Thread(target=self._run_engine, daemon=True)
            self.worker_thread.start()

    def _run_engine(self):
        while True:
            text, interrupt = self.queue.get()
            if interrupt:
                self.engine.stop()
            self.engine.say(text)
            self.engine.runAndWait()
            self.queue.task_done()

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
            # Vyprázdnění fronty při přerušení
            if interrupt:
                while not self.queue.empty():
                    try:
                        self.queue.get_nowait()
                        self.queue.task_done()
                    except queue.Empty:
                        break
            self.queue.put((text, interrupt))

    def set_rate(self, rate):
        if not self.is_screen_reader:
            self.engine.setProperty('rate', rate)

    def set_volume(self, volume):
        if not self.is_screen_reader:
            self.engine.setProperty('volume', volume)
