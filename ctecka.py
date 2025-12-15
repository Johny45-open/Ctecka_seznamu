# pip install pywinauto
# NVDA musí běžet, jinak hlásí jen, že není spuštěná

from pywinauto import Desktop
import nvdaControllerClient
import psutil
import time

def nvda_running():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'nvda' in proc.info['name'].lower():
            return True
    return False

def get_focused_list_item():
    window = Desktop(backend="uia").get_active()
    try:
        focused_elem = window.child_window(control_type="ListItem", has_focus=True)
        if focused_elem.exists():
            return focused_elem
    except:
        return None
    return None

def get_item_level(item):
    level = 0
    parent = item.parent()
    while parent:
        level += 1
        parent = parent.parent()
    return level

while True:
    if nvda_running():
        item = get_focused_list_item()
        if item:
            text = item.window_text()
            level = get_item_level(item)
            message = f"Položka: {text}, úroveň: {level}"
            nvdaControllerClient.speakText(message)
    else:
        print("NVDA není spuštěná.")
    time.sleep(2)  # kontrola každé 2 sekundy
