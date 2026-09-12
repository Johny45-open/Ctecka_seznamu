print("Starting test")
import win32com.client
print("Imported win32com")
try:
    word = win32com.client.Dispatch("Word.Application")
    print("Word dispatched")
    word.Quit()
    print("Word quit")
except Exception as e:
    print(f"Error: {e}")
