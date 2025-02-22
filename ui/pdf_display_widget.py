from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import Qt

class PDFDisplayWidget(QLabel):
    """Custom widget for handling PDF page display and text selection"""
    def __init__(self, parent=None, page_num=0):
        super().__init__(parent)
        self.page_num = page_num
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
        self.text_blocks = []  # Will store character-level text positions
        self.selected_chars = set()  # Track selected character indices
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        self.setCursor(Qt.IBeamCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            # Find the closest character to the click position
            char_idx = self.find_nearest_char(pos)
            if char_idx is not None:
                if event.modifiers() == Qt.ShiftModifier and self.selection_start is not None:
                    # Extend selection
                    self.selection_end = char_idx
                else:
                    # Start new selection
                    self.selection_start = char_idx
                    self.selection_end = char_idx
                self.is_selecting = True
                self.update_selection()
            
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            char_idx = self.find_nearest_char(pos)
            if char_idx is not None:
                # Find word boundaries
                word_start, word_end = self.find_word_boundaries(char_idx)
                self.selection_start = word_start
                self.selection_end = word_end
                self.update_selection()
    
    def mouseMoveEvent(self, event):
        if self.is_selecting:
            pos = event.pos()
            char_idx = self.find_nearest_char(pos)
            if char_idx is not None:
                self.selection_end = char_idx
                self.update_selection()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_selecting = False
    
    def find_nearest_char(self, pos):
        """Find the character index closest to the given position"""
        if not self.text_blocks:
            return None
            
        min_dist = float('inf')
        nearest_idx = None
        
        for idx, block in enumerate(self.text_blocks):
            rect = block['rect']
            # Check if position is within the vertical bounds of this line
            if pos.y() >= rect['y'] and pos.y() <= rect['y'] + rect['height']:
                # Calculate horizontal distance to character
                char_center_x = rect['x'] + rect['width'] / 2
                dist = abs(pos.x() - char_center_x)
                if dist < min_dist:
                    min_dist = dist
                    nearest_idx = idx
                    
        return nearest_idx
    
    def find_word_boundaries(self, char_idx):
        """Find word boundaries around the given character index"""
        if char_idx is None or not self.text_blocks:
            return None, None
            
        # Find start of word
        start = char_idx
        while start > 0 and not self.text_blocks[start-1]['text'].isspace():
            start -= 1
            
        # Find end of word
        end = char_idx
        while end < len(self.text_blocks)-1 and not self.text_blocks[end+1]['text'].isspace():
            end += 1
            
        return start, end
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self.selection_start is not None and self.selection_end is not None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set selection highlight color
            highlight_color = QColor(0, 120, 215, 128)  # Semi-transparent blue
            painter.setBrush(highlight_color)
            painter.setPen(Qt.NoPen)
            
            # Get selection range
            start_idx = min(self.selection_start, self.selection_end)
            end_idx = max(self.selection_start, self.selection_end)
            
            # Group characters by line (using y-coordinate)
            current_line = []
            current_y = None
            
            # Process all selected characters
            for i in range(start_idx, end_idx + 1):
                if i >= len(self.text_blocks):
                    break
                    
                rect = self.text_blocks[i]['rect']
                y = int(rect['y'])
                
                # If this is a new line or the first character
                if current_y is None or abs(y - current_y) > rect['height'] * 0.5:
                    # Draw the previous line if it exists
                    if current_line:
                        self._draw_line_highlight(painter, current_line)
                    # Start a new line
                    current_line = [rect]
                    current_y = y
                else:
                    # Add to current line
                    current_line.append(rect)
            
            # Draw the last line
            if current_line:
                self._draw_line_highlight(painter, current_line)
            
            painter.end()
    
    def _draw_line_highlight(self, painter, line_rects):
        """Draw a continuous highlight for a line of text"""
        if not line_rects:
            return
            
        # Find the bounds of the entire line
        x_start = min(rect['x'] for rect in line_rects)
        x_end = max(rect['x'] + rect['width'] for rect in line_rects)
        y = line_rects[0]['y']
        height = line_rects[0]['height']
        
        # Draw a single rectangle for the entire line
        painter.drawRect(
            int(x_start),
            int(y),
            int(x_end - x_start),
            int(height)
        )
    
    def update_selection(self):
        """Update the selected text based on character selection"""
        if self.selection_start is None or self.selection_end is None:
            return
            
        # Update visual selection
        self.update()
        
        # Get selected text
        start_idx = min(self.selection_start, self.selection_end)
        end_idx = max(self.selection_start, self.selection_end)
        selected_text = ''.join(self.text_blocks[i]['text'] for i in range(start_idx, end_idx + 1))
        
        # Get the main window instance and update selection
        main_window = self.window()
        if main_window:
            main_window.handle_text_selection(selected_text, self.page_num)
    
    def set_text_blocks(self, blocks):
        """Set text block data from PyMuPDF"""
        # Convert blocks to character-level positions
        char_blocks = []
        for block in blocks:
            text = block['text']
            if not text:
                continue
                
            # Calculate width per character (approximately)
            char_width = block['rect']['width'] / len(text)
            
            # Create a block for each character
            for i, char in enumerate(text):
                char_x = block['rect']['x'] + (i * char_width)
                char_block = {
                    'text': char,
                    'rect': {
                        'x': char_x,
                        'y': block['rect']['y'],
                        'width': char_width,
                        'height': block['rect']['height']
                    }
                }
                char_blocks.append(char_block)
        
        self.text_blocks = char_blocks 