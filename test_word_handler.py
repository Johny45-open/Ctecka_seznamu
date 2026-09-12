import win32com.client
import os

try:
    word = win32com.client.Dispatch("Word.Application")
    doc = word.Documents.Add()
    # Insert some list items
    for i in range(3):
        para = doc.Paragraphs.Add()
        para.Range.Text = f"Položka {i+1}"
        para.Range.ListFormat.ApplyNumberDefault()
    
    # Test WordHandler locally
    from word_handler import WordHandler
    wh = WordHandler()
    
    # Find the second paragraph
    para2 = doc.Paragraphs(2)
    info = wh.get_info(para2)
    print(f"Info: {info}")
    
    doc.Close(SaveChanges=0)
    word.Quit()
    print("Test passed")
except Exception as e:
    print(f"Test failed: {e}")
