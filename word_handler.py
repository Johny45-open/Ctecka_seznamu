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

    def get_list_range(self, paragraph):
        # Najde rozsah bloku seznamu podle ListTemplateID a zachování úrovně
        start = paragraph.Range.Start
        end = paragraph.Range.End
        
        # Získání informací o aktuálním odstavci
        level = paragraph.Range.ListFormat.ListLevelNumber
        try:
            template_id = paragraph.Range.ListFormat.ListTemplate.ListTemplateID
        except:
            template_id = None
        
        # Hledání nahoru
        current = paragraph
        while current.Previous() is not None:
            prev = current.Previous()
            prev_level = prev.Range.ListFormat.ListLevelNumber
            try:
                prev_template = prev.Range.ListFormat.ListTemplate.ListTemplateID
            except:
                prev_template = None
            
            # Blok pokračuje, pokud je stejná šablona a úroveň je stejná nebo vyšší
            if prev.Range.ListFormat.ListType != 0 and prev_template == template_id and prev_level >= level:
                current = prev
                start = current.Range.Start
                # Pokud jsme našli vyšší úroveň, tohle je začátek bloku pro tuto úroveň
                if prev_level < level:
                    break
            else:
                break
            
        # Hledání dolů
        current = paragraph
        while current.Next() is not None:
            nxt = current.Next()
            next_level = nxt.Range.ListFormat.ListLevelNumber
            try:
                next_template = nxt.Range.ListFormat.ListTemplate.ListTemplateID
            except:
                next_template = None
                
            # Blok pokračuje, pokud je stejná šablona a úroveň je stejná nebo vyšší
            if nxt.Range.ListFormat.ListType != 0 and next_template == template_id and next_level >= level:
                current = nxt
                end = current.Range.End
                # Pokud narazíme na úroveň nižší než je naše, seznam pro tuto úroveň končí
                if next_level < level:
                    break
            else:
                break
            
        return start, end

    def get_info(self, paragraph):
        text = paragraph.Range.Text.strip()
        if not text:
            return None
        if paragraph.Range.ListFormat.ListType != 0:
            level = paragraph.Range.ListFormat.ListLevelNumber
            start_range, end_range = self.get_list_range(paragraph)
            
            # Diagnostika
            print(f"DEBUG: Rozsah {start_range}-{end_range}, Odstavec {paragraph.Range.Start}-{paragraph.Range.End}")
            
            # Počítání v rámci tohoto rozsahu
            siblings_count = 0
            index = 0
            
            for p in self.doc.Paragraphs:
                if p.Range.Start >= start_range and p.Range.End <= end_range and \
                   p.Range.ListFormat.ListType != 0 and \
                   p.Range.ListFormat.ListLevelNumber == level:
                    siblings_count += 1
                    if p.Range.Start <= paragraph.Range.Start:
                        index += 1
            
            subitems_count = self.count_subitems(paragraph)
            return {"text": text, "level": level, "index": index, "siblings_count": siblings_count, "subitems_count": subitems_count, "type": "seznam"}
        else:
            return {"text": text, "type": "text"}

    def get_selection_paragraph(self):
        return self.word.Selection.Paragraphs(1)

    def get_selection_start(self):
        return self.word.Selection.Start
