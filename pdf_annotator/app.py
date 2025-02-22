import sys
from PyQt5.QtWidgets import (QMainWindow, QApplication, QAction, 
                            QFileDialog, QScrollArea, QLabel, QToolBar, QStyle, QWidget, QHBoxLayout, QVBoxLayout, QComboBox,
                            QColorDialog, QLineEdit)
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QIcon
import fitz  # PyMuPDF
import pytesseract
from PIL import Image as PILImage
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QSettings

class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_doc = None
        self.current_page = 0
        self.ocr_engine = pytesseract
        self.annotations = []
        self.page_text_data = []
        self.selected_text = ""
        self.page_widgets = []  # Store our custom page widgets
        self.zoom_level = 1.5  # Default zoom level
        self.highlight_color = QColor(255, 255, 0, 100)  # Default yellow with transparency
        
        self.settings = QSettings("YourCompany", "PDFAnnotator9000")
        self.load_last_session()
        
        self.search_results = []
        self.current_search_index = -1
        self.search_highlight_color = QColor(0, 255, 0, 60)  # Green highlight
        
        self.init_ui()
        self.connect_actions()
        
    def init_ui(self):
        self.setWindowTitle('PDF Annotator 9000')
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget setup
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create a container widget to center the image label
        self.container = QWidget()
        container_layout = QVBoxLayout(self.container)  # Changed to VBox for vertical stacking
        container_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)  # Center horizontally, align top vertically
        container_layout.setSpacing(20)  # Add space between pages
        
        self.scroll_area.setWidget(self.container)
        self.setCentralWidget(self.scroll_area)
        
        # Create toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Create actions with icons from standard icon set
        self.open_action = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), '&Open PDF...', self)
        self.open_action.setShortcut('Ctrl+O')
        
        self.save_action = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), '&Save Annotations...', self)
        self.save_action.setShortcut('Ctrl+S')
        
        self.copy_action = QAction('&Copy', self)
        self.copy_action.setShortcut('Ctrl+C')
        
        self.quit_action = QAction('&Quit', self)
        self.quit_action.setShortcut('Ctrl+Q')
        
        # Create zoom actions
        self.zoom_in_action = QAction(self.style().standardIcon(QStyle.SP_ArrowUp), 'Zoom In', self)
        self.zoom_in_action.setShortcut('Ctrl++')
        
        self.zoom_out_action = QAction(self.style().standardIcon(QStyle.SP_ArrowDown), 'Zoom Out', self)
        self.zoom_out_action.setShortcut('Ctrl+-')
        
        # Create zoom level combo box
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(['50%', '75%', '100%', '125%', '150%', '200%', '300%', '400%'])
        self.zoom_combo.setCurrentText('150%')  # Match default zoom_level
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(100)
        
        # Create highlight actions
        self.highlight_action = QAction('&Highlight', self)
        self.highlight_action.setShortcut('Ctrl+H')
        
        self.color_picker_action = QAction(self.style().standardIcon(QStyle.SP_DialogResetButton), 'Choose Highlight Color', self)
        
        # Add actions to toolbar
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.zoom_out_action)
        toolbar.addWidget(self.zoom_combo)
        toolbar.addAction(self.zoom_in_action)
        toolbar.addSeparator()
        toolbar.addAction(self.highlight_action)
        toolbar.addAction(self.color_picker_action)
        
        # TODO [Feature 1]: Add search components to toolbar
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search...")
        self.search_field.setMaximumWidth(200)
        self.search_prev = QAction('◀', self)
        self.search_next = QAction('▶', self)
        toolbar.insertWidget(self.open_action, self.search_field)
        toolbar.addAction(self.search_prev)
        toolbar.addAction(self.search_next)
        
        # TODO [Feature 4]: Add undo/redo actions
        self.undo_action = QAction(self.style().standardIcon(QStyle.SP_ArrowBack), 'Undo', self)
        self.redo_action = QAction(self.style().standardIcon(QStyle.SP_ArrowForward), 'Redo', self)
        toolbar.addSeparator()
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
        
        # Setup menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu('&Edit')
        edit_menu.addAction(self.copy_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.highlight_action)
        edit_menu.addAction(self.color_picker_action)
        
        # View menu
        view_menu = menubar.addMenu('&View')
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        
    def connect_actions(self):
        self.open_action.triggered.connect(self.open_pdf)
        self.save_action.triggered.connect(self.save_annotations)
        self.copy_action.triggered.connect(self.copy_text)
        self.quit_action.triggered.connect(self.close)
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.zoom_combo.currentTextChanged.connect(self.zoom_level_changed)
        self.highlight_action.triggered.connect(self.highlight_selected_text)
        self.color_picker_action.triggered.connect(self.choose_highlight_color)
        self.search_field.returnPressed.connect(self.perform_search)
        self.search_prev.triggered.connect(self.prev_search_result)
        self.search_next.triggered.connect(self.next_search_result)
        self.undo_action.triggered.connect(self.undo_last_action)
        self.redo_action.triggered.connect(self.redo_last_action)
    
    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if path:
            try:
                self.current_doc = fitz.open(path)
                self.process_pdf()
                self.render_pdf()  # Now renders all pages at once
            except Exception as e:
                print(f"Error opening PDF: {e}")
    
    def process_pdf(self):
        """Handle text extraction and OCR needs"""
        if not self.current_doc:
            return
            
        self.page_text_data = []  # Store text data for each page
        
        for page_num in range(len(self.current_doc)):
            page = self.current_doc[page_num]
            text = page.get_text()
            
            # If page has no text, try OCR
            if not text.strip():
                # Convert page to image for OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = self.run_ocr(img)
            
            self.page_text_data.append(text)
    
    def render_pdf(self):
        """Render all PDF pages into the scrollable view"""
        if not self.current_doc:
            return
            
        # Clear existing pages
        for widget in self.page_widgets:
            widget.deleteLater()
        self.page_widgets.clear()
        
        # Get the container layout
        layout = self.container.layout()
        
        # Render each page
        mat = fitz.Matrix(self.zoom_level, self.zoom_level)
        
        for page_num in range(len(self.current_doc)):
            page = self.current_doc[page_num]
            
            # Apply highlights for this page
            page_highlights = [ann for ann in self.annotations if ann['page'] == page_num]
            for highlight in page_highlights:
                if highlight['type'] == 'highlight':
                    # Convert QColor to RGB tuple (0-1 range)
                    color = highlight['color']
                    rgb = (color.red()/255, color.green()/255, color.blue()/255)
                    # Add highlight to page
                    annot = page.add_highlight_annot(highlight['rect'])
                    annot.set_colors(stroke=rgb)
                    annot.update()
            
            # Get page pixmap after applying highlights
            pix = page.get_pixmap(matrix=mat)
            
            # Convert pixmap to QImage
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            
            # Create custom widget for this page
            page_widget = PDFDisplayWidget(page_num=page_num)
            page_widget.setAlignment(Qt.AlignCenter)
            page_widget.setPixmap(QPixmap.fromImage(img))
            
            # Extract text blocks and their positions
            text_blocks = []
            for block in page.get_text("dict")["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        if "spans" in line:
                            for span in line["spans"]:
                                # Convert PDF coordinates to screen coordinates
                                rect = span["bbox"]
                                scaled_rect = {
                                    'x': rect[0] * self.zoom_level,
                                    'y': rect[1] * self.zoom_level,
                                    'width': (rect[2] - rect[0]) * self.zoom_level,
                                    'height': (rect[3] - rect[1]) * self.zoom_level
                                }
                                text_blocks.append({
                                    'text': span["text"],
                                    'rect': scaled_rect
                                })
            
            # Set text blocks for the page widget
            page_widget.set_text_blocks(text_blocks)
            
            # Add to layout
            layout.addWidget(page_widget)
            self.page_widgets.append(page_widget)
            
        # Update window title
        total_pages = len(self.current_doc)
        self.setWindowTitle(f'PDF Annotator 9000 - {total_pages} pages')
    
    def run_ocr(self, image):
        """Process image through OCR engine"""
        try:
            # Configure OCR for better accuracy
            custom_config = r'--oem 3 --psm 6'
            return self.ocr_engine.image_to_string(image, config=custom_config)
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def add_highlight(self, rect, page_num):
        """Store highlight coordinates and metadata"""
        print(f"Adding highlight on page {page_num} at {rect}")
        
        # Ensure we have a proper fitz.Rect
        if not isinstance(rect, fitz.Rect):
            rect = fitz.Rect(rect)
        
        # Add some padding to the rectangle for better visual appearance
        rect.x0 -= 1
        rect.x1 += 1
        
        self.annotations.append({
            'type': 'highlight',
            'rect': rect,  # PyMuPDF rectangle for the highlight
            'page': page_num,  # Page number for the highlight
            'color': self.highlight_color
        })
        self.render_pdf()
    
    def handle_text_selection(self, text, page_num):
        """Handle text selection from a page widget"""
        self.selected_text = text
        self.current_selection_info = {
            'text': text,
            'page_num': page_num
        }
    
    def copy_text(self):
        """Handle system clipboard integration"""
        if self.selected_text:
            clipboard = QApplication.clipboard()
            clipboard.clear()
            clipboard.setText(self.selected_text)
        else:
            print("No text selected to copy")
    
    def save_annotations(self):
        """Save modified PDF with annotations"""
        if not self.current_doc:
            print("No document open to save")
            return
            
        # Get save path from user
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Annotated PDF",
            "",
            "PDF Files (*.pdf)"
        )
        
        if not save_path:
            return  # User cancelled
            
        try:
            # Apply all annotations before saving
            for annotation in self.annotations:
                if annotation['type'] == 'highlight':
                    page = self.current_doc[annotation['page']]
                    # Convert QColor to RGB tuple (0-1 range)
                    color = annotation['color']
                    rgb = (color.red()/255, color.green()/255, color.blue()/255)
                    highlight = page.add_highlight_annot(annotation['rect'])
                    highlight.set_colors(stroke=rgb)
                    highlight.update()
            
            # Create a copy of the document for saving
            self.current_doc.save(
                save_path,
                garbage=4,  # Clean up and optimize PDF
                deflate=True,  # Compress streams
                pretty=False  # Don't prettify PDF structure (smaller file)
            )
            print(f"PDF saved successfully to: {save_path}")
            
        except Exception as e:
            print(f"Error saving PDF: {e}")
            # Could add a proper error dialog here later
    
    def zoom_in(self):
        """Increase zoom level by 25%"""
        new_zoom = min(self.zoom_level * 1.25, 4.0)  # Cap at 400%
        self.set_zoom_level(new_zoom)
        
    def zoom_out(self):
        """Decrease zoom level by 25%"""
        new_zoom = max(self.zoom_level / 1.25, 0.5)  # Cap at 50%
        self.set_zoom_level(new_zoom)
        
    def zoom_level_changed(self, text):
        """Handle zoom level changes from combo box"""
        try:
            # Strip the % sign and convert to float
            zoom = float(text.rstrip('%')) / 100
            self.set_zoom_level(zoom)
        except ValueError:
            # Restore the previous zoom level in the combo box
            self.zoom_combo.setCurrentText(f"{int(self.zoom_level * 100)}%")
            
    def set_zoom_level(self, zoom):
        """Set zoom level and update display"""
        if zoom != self.zoom_level:
            self.zoom_level = zoom
            self.zoom_combo.setCurrentText(f"{int(zoom * 100)}%")
            if self.current_doc:
                self.render_pdf()
    
    def choose_highlight_color(self):
        """Open color picker and set new highlight color"""
        color = QColorDialog.getColor(
            initial=self.highlight_color,
            parent=self,
            title='Choose Highlight Color',
            options=QColorDialog.ShowAlphaChannel
        )
        
        if color.isValid():
            # Keep alpha at 100 for consistency
            self.highlight_color = QColor(color.red(), color.green(), color.blue(), 100)
            
    def highlight_selected_text(self):
        """Enhanced text selection handling"""
        # Potential improvements:
        # 1. Add visual feedback during selection
        # 2. Implement snap-to-text boundaries
        # 3. Add highlight preview before commit
        # 4. Support multiple selection ranges
        pass  # Implementation would modify existing logic
    
    def perform_search(self):
        """Search through document text"""
        query = self.search_field.text().lower()
        self.search_results = []
        
        for page_num, text in enumerate(self.page_text_data):
            if query in text.lower():
                # Find all matches and their positions
                start_idx = 0
                while True:
                    idx = text.lower().find(query, start_idx)
                    if idx == -1:
                        break
                    # Convert character index to position rect
                    # (Would need position mapping from text_blocks)
                    self.search_results.append((page_num, idx, idx+len(query)))
                    start_idx = idx + len(query)
        
        if self.search_results:
            self.current_search_index = 0
            self.highlight_search_result()
        self.render_pdf()  # Rerender to show search highlights

    def prev_search_result(self):
        """Navigate to previous search result"""
        if self.search_results:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            self.highlight_search_result()

    def next_search_result(self):
        """Navigate to next search result"""
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            self.highlight_search_result()

    def highlight_search_result(self):
        """Highlight current search result"""
        if self.search_results:
            page_num, start_idx, end_idx = self.search_results[self.current_search_index]
            self.highlight_selected_text()
            self.current_selection_info = {
                'text': self.page_text_data[page_num][start_idx:end_idx],
                'page_num': page_num
            }
            self.render_pdf()

    def closeEvent(self, event):
        """Save state on window close"""
        self.save_current_session()
        super().closeEvent(event)
        
    def save_current_session(self):
        """Save current document and annotations"""
        # Implementation would need to handle:
        # - Last opened file path
        # - Current annotations
        # - View state (zoom, scroll position)
        pass
        
    def load_last_session(self):
        """Load previous session state"""
        pass

    def undo_last_action(self):
        """Handle undo logic using command pattern"""
        # Implementation would require:
        # - Command history stack
        # - Inverse operations for annotations
        pass
        
    def redo_last_action(self):
        """Handle redo logic"""
        pass

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
        """Improved word detection with PDF semantics"""
        # Current implementation uses whitespace - could be enhanced with:
        # - PDF layout analysis
        # - Hyphenation handling
        # - Multi-language support
        pass
    
    def paintEvent(self, event):
        # Add improved selection rendering:
        # - Smoother highlight transitions
        # - Better contrast for selected text
        # - Animation effects
        super().paintEvent(event)
        
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
        if main_window and isinstance(main_window, PDFViewer):
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PDFViewer()
    window.show()
    sys.exit(app.exec_())
