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

    def count_subitems(self, paragraph, list_end):
        if paragraph.Range.ListFormat.ListType == 0:
            return 0
        level = paragraph.Range.ListFormat.ListLevelNumber
        count = 0
        current = paragraph.Next()
        while current is not None and current.Range.Start < list_end:
            if current.Range.ListFormat.ListType != 0:
                p_level = current.Range.ListFormat.ListLevelNumber
                if p_level > level:
                    count += 1
            current = current.Next()
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
            
            # Počítání v rámci tohoto rozsahu
            siblings_count = 0
            index = 0
            
            # Procházení pouze v rámci rozsahu seznamu
            current = paragraph
            # Najdeme začátek bloku pro počítání sourozenců
            while current.Previous() is not None and current.Previous().Range.Start >= start_range:
                current = current.Previous()
            
            # Nyní procházíme od začátku
            while current is not None and current.Range.End <= end_range:
                if current.Range.ListFormat.ListType != 0 and current.Range.ListFormat.ListLevelNumber == level:
                    siblings_count += 1
                    if current.Range.Start <= paragraph.Range.Start:
                        index += 1
                current = current.Next()
            
            subitems_count = self.count_subitems(paragraph, end_range)
            return {"text": text, "level": level, "index": index, "siblings_count": siblings_count, "subitems_count": subitems_count, "type": "seznam"}
        else:
            return {"text": text, "type": "text"}

    def get_selection_paragraph(self):
        return self.word.Selection.Paragraphs(1)

    def get_selection_start(self):
        return self.word.Selection.Start

    def move_to_next_list_item(self):
        # Pokusí se přesunout kurzor na další položku seznamu
        current = self.get_selection_paragraph()
        nxt = current.Next()
        while nxt is not None:
            if nxt.Range.ListFormat.ListType != 0:
                nxt.Range.Select()
                return True
            nxt = nxt.Next()
        return False

    def move_to_previous_list_item(self):
        # Pokusí se přesunout kurzor na předchozí položku seznamu
        current = self.get_selection_paragraph()
        prev = current.Previous()
        while prev is not None:
            if prev.Range.ListFormat.ListType != 0:
                prev.Range.Select()
                return True
            prev = prev.Previous()
        return False

    def move_to_parent_list_item(self):
        # Skok na nadřazenou položku
        current = self.get_selection_paragraph()
        level = current.Range.ListFormat.ListLevelNumber
        if level <= 1:
            return False
        
        prev = current.Previous()
        while prev is not None:
            if prev.Range.ListFormat.ListType != 0:
                prev_level = prev.Range.ListFormat.ListLevelNumber
                if prev_level < level:
                    prev.Range.Select()
                    return True
            prev = prev.Previous()
        return False

    def move_to_start_of_list(self):
        # Skok na začátek aktuálního bloku seznamu
        current = self.get_selection_paragraph()
        start_range, end_range = self.get_list_range(current)
        
        # Najít první položku v rozsahu
        para = self.doc.Paragraphs(1) # Toto je neefektivní, ale v COM nemáme snadný přístup k odstavci podle start pozice bez iterace
        # Lepší přístup:
        rng = self.doc.Range(start_range, start_range)
        rng.Paragraphs(1).Range.Select()
        return True

    def move_to_end_of_list(self):
        # Skok na konec aktuálního bloku seznamu
        current = self.get_selection_paragraph()
        start_range, end_range = self.get_list_range(current)
        
        rng = self.doc.Range(end_range, end_range)
        rng.Paragraphs(1).Range.Select()
        return True

    def get_hierarchy_path(self, paragraph):
        # Vrací cestu k položce v hierarchii, např. "Instalace > Ovladače > USB"
        path = []
        current = paragraph
        current_level = current.Range.ListFormat.ListLevelNumber
        
        while current is not None and current_level > 0:
            text = current.Range.Text.strip()
            path.insert(0, text)
            
            # Najít nadřazenou položku
            found_parent = False
            prev = current.Previous()
            while prev is not None:
                if prev.Range.ListFormat.ListType != 0:
                    prev_level = prev.Range.ListFormat.ListLevelNumber
                    if prev_level < current_level:
                        current = prev
                        current_level = prev_level
                        found_parent = True
                        break
                prev = prev.Previous()
            
            if not found_parent:
                break
                
        return " > ".join(path)
