import fitz  # PyMuPDF
from PyQt5.QtGui import QColor

class PDFDocument:
    def __init__(self):
        self.doc = None
        self.annotations = []
        self.page_text_data = []
        
    def open(self, path):
        """Open a PDF document and process its text data"""
        try:
            self.doc = fitz.open(path)
            self.process_text_data()
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return False
            
    def process_text_data(self):
        """Extract text from all pages"""
        if not self.doc:
            return
            
        self.page_text_data = []
        for page in self.doc:
            text = page.get_text()
            self.page_text_data.append(text)
            
    def add_highlight(self, rect, page_num, color):
        """Add a highlight annotation"""
        if not isinstance(rect, fitz.Rect):
            rect = fitz.Rect(rect)
            
        # Add some padding
        rect.x0 -= 1
        rect.x1 += 1
        
        annotation = {
            'type': 'highlight',
            'rect': rect,
            'page': page_num,
            'color': color
        }
        self.annotations.append(annotation)
        
    def remove_annotation(self, index):
        """Remove an annotation by index"""
        if 0 <= index < len(self.annotations):
            try:
                # Get the page number BEFORE removing the annotation
                page_num = self.annotations[index]['page']
                annotation = self.annotations.pop(index)
                
                # Clear any existing highlights on the page
                if self.doc:
                    page = self.doc[page_num]
                    for annot in page.annots():
                        if annot.type[0] == 8:  # Highlight annotation
                            page.delete_annot(annot)
                return True
            except Exception as e:
                print(f"Error removing annotation: {e}")
                # If something went wrong, try to restore the annotation
                if 'annotation' in locals():
                    self.annotations.insert(index, annotation)
                return False
        return False
        
    def apply_highlights(self, page_num):
        """Apply highlights to a specific page"""
        if not self.doc:
            return
            
        page = self.doc[page_num]
        page_highlights = [ann for ann in self.annotations if ann['page'] == page_num]
        
        for highlight in page_highlights:
            if highlight['type'] == 'highlight':
                color = highlight['color']
                rgb = (color.red()/255, color.green()/255, color.blue()/255)
                annot = page.add_highlight_annot(highlight['rect'])
                annot.set_colors(stroke=rgb)
                annot.update()
                
    def save(self, save_path):
        """Save the document with all annotations"""
        if not self.doc:
            return False
            
        try:
            # Apply all annotations
            for annotation in self.annotations:
                if annotation['type'] == 'highlight':
                    page = self.doc[annotation['page']]
                    color = annotation['color']
                    rgb = (color.red()/255, color.green()/255, color.blue()/255)
                    highlight = page.add_highlight_annot(annotation['rect'])
                    highlight.set_colors(stroke=rgb)
                    highlight.update()
            
            # Save with optimization
            self.doc.save(
                save_path,
                garbage=4,
                deflate=True,
                pretty=False
            )
            return True
        except Exception as e:
            print(f"Error saving PDF: {e}")
            return False
            
    def close(self):
        """Close the document"""
        if self.doc:
            self.doc.close()
            self.doc = None
            self.annotations = []
            self.page_text_data = [] 