import win32com.client

class WordHandler:
    def __init__(self):
        self.word = win32com.client.Dispatch("Word.Application")
        if self.word.Documents.Count == 0:
            self.word.Documents.Add()
        self.doc = self.word.ActiveDocument

    def analyze_document(self):
        list_count = 0
        text_count = 0
        for para in self.doc.Paragraphs:
            if para.Range.ListFormat.ListType != 0:
                list_count += 1
            elif para.Range.Text.strip():
                text_count += 1
        
        if list_count == 0 and text_count == 0:
            doc_type = "prázdný"
        elif list_count == 0:
            doc_type = "jen normální text"
        elif text_count == 0:
            doc_type = "jen seznamy"
        else:
            doc_type = "kombinace seznamů a normálního textu"
        
        return doc_type, list_count, text_count

    def count_subitems(self, paragraph):
        if paragraph.Range.ListFormat.ListType == 0:
            return 0
        level = paragraph.Range.ListFormat.ListLevelNumber
        start = paragraph.Range.Start
        end = paragraph.Range.End
        count = 0
        for p in self.doc.Paragraphs:
            if p.Range.ListFormat.ListType != 0:
                p_level = p.Range.ListFormat.ListLevelNumber
                p_start = p.Range.Start
                if start < p_start < end and p_level > level:
                    count += 1
        return count

    def get_info(self, paragraph):
        text = paragraph.Range.Text.strip()
        if not text:
            return None
        if paragraph.Range.ListFormat.ListType != 0:
            level = paragraph.Range.ListFormat.ListLevelNumber
            siblings_count = sum(
                1 for p in self.doc.Paragraphs
                if p.Range.ListFormat.ListType !=0 and p.Range.ListFormat.ListLevelNumber==level
            )
            index = sum(
                1 for p in self.doc.Paragraphs
                if p.Range.ListFormat.ListType !=0 and p.Range.ListFormat.ListLevelNumber==level and p.Range.Start<=paragraph.Range.Start
            )
            subitems_count = self.count_subitems(paragraph)
            return {"text": text, "level": level, "index": index, "siblings_count": siblings_count, "subitems_count": subitems_count, "type": "seznam"}
        else:
            return {"text": text, "type": "text"}

    def get_selection_paragraph(self):
        return self.word.Selection.Paragraphs(1)

    def get_selection_start(self):
        return self.word.Selection.Start
