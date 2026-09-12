import threading
import queue
import time
import pythoncom
import win32com.client
from word_handler import WordHandler

class WordMonitor(threading.Thread):
    def __init__(self, update_queue):
        super().__init__(daemon=True)
        self.update_queue = update_queue
        self.running = True

    def run(self):
        pythoncom.CoInitialize()
        try:
            handler = WordHandler()
            last_position = -1
            while self.running:
                try:
                    start = handler.get_selection_start()
                    if start != last_position:
                        last_position = start
                        para = handler.get_selection_paragraph()
                        info = handler.get_info(para)
                        self.update_queue.put(info)
                except Exception as e:
                    # Robustní ošetření COM chyb
                    print(f"Error in monitor: {e}")
                time.sleep(0.3)
        finally:
            pythoncom.CoUninitialize()

    def stop(self):
        self.running = False
