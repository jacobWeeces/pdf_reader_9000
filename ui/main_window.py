from email.mime import application
from PyQt5.QtWidgets import (QMainWindow, QAction, QFileDialog, QScrollArea, 
                            QToolBar, QStyle, QWidget, QVBoxLayout, QComboBox,
                            QColorDialog, QLineEdit, QApplication, QMessageBox, QCheckBox)
from PyQt5.QtGui import QImage, QPixmap, QColor
from PyQt5.QtCore import Qt, QSettings
import fitz
import json
import os

from core.pdf_document import PDFDocument
from core.command import CommandHistory, HighlightCommand
from ui.pdf_display_widget import PDFDisplayWidget
from utils.ocr_handler import OCRHandler

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pdf_doc = PDFDocument()
        self.ocr = OCRHandler()
        self.selected_text = ""
        self.page_widgets = []  # Store our custom page widgets
        self.zoom_level = 1.5  # Default zoom level
        self.highlight_color = QColor(255, 255, 0, 100)  # Default yellow with transparency
        
        self.settings = QSettings("YourCompany", "PDFAnnotator9000")
        
        self.search_results = []
        self.current_search_index = -1
        self.search_highlight_color = QColor(0, 255, 0, 60)  # Green highlight
        
        # Initialize command history
        self.command_history = CommandHistory()
        
        # First create UI
        self.init_ui()
        self.connect_actions()
        
        # Then load saved session
        self.load_last_session()
        
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
        
        # Create toolbar with object name
        toolbar = QToolBar("Main Toolbar")  # Added name in constructor
        toolbar.setObjectName("mainToolbar")  # Set object name for state saving
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
        
        # Create zoom combo box
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(['50%', '75%', '100%', '125%', '150%', '200%', '300%', '400%'])
        self.zoom_combo.setCurrentText('150%')  # Match default zoom_level
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(100)
        
        # Create highlight actions
        self.highlight_action = QAction('&Highlight', self)
        self.highlight_action.setShortcut('Ctrl+H')
        
        self.color_picker_action = QAction(self.style().standardIcon(QStyle.SP_DialogResetButton), 'Choose Highlight Color', self)
        
        # Add search field
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search...")
        self.search_field.setMaximumWidth(200)
        
        # Add undo/redo actions with shortcuts
        self.undo_action = QAction(self.style().standardIcon(QStyle.SP_ArrowBack), '&Undo', self)
        self.undo_action.setShortcut('Ctrl+Z')
        self.undo_action.setEnabled(False)  # Start disabled
        
        self.redo_action = QAction(self.style().standardIcon(QStyle.SP_ArrowForward), '&Redo', self)
        self.redo_action.setShortcut('Ctrl+Y')  # Windows standard
        self.redo_action.setEnabled(False)  # Start disabled
        
        # Add actions to toolbar
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addWidget(self.zoom_combo)
        toolbar.addSeparator()
        toolbar.addAction(self.highlight_action)
        toolbar.addAction(self.color_picker_action)
        toolbar.addSeparator()
        toolbar.insertWidget(self.open_action, self.search_field)
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
        edit_menu.addSeparator()
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        
        # View menu
        view_menu = menubar.addMenu('&View')
        
    def connect_actions(self):
        self.open_action.triggered.connect(self.open_pdf)
        self.save_action.triggered.connect(self.save_annotations)
        self.copy_action.triggered.connect(self.copy_text)
        self.quit_action.triggered.connect(self.close)
        self.zoom_combo.currentTextChanged.connect(self.zoom_level_changed)
        self.highlight_action.triggered.connect(self.highlight_selected_text)
        self.color_picker_action.triggered.connect(self.choose_highlight_color)
        self.search_field.returnPressed.connect(self.perform_search)
        
        # Connect undo/redo actions
        self.undo_action.triggered.connect(self.undo_last_action)
        self.redo_action.triggered.connect(self.redo_last_action)
    
    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if path:
            if self.pdf_doc.open(path):
                # Clear command history when opening new document
                self.command_history.clear()
                self.update_undo_redo_actions()
                self.render_pdf()
    
    def render_pdf(self):
        """Render all PDF pages into the scrollable view"""
        if not self.pdf_doc.doc:
            return
            
        # Clear existing pages
        for widget in self.page_widgets:
            widget.deleteLater()
        self.page_widgets.clear()
        
        # Get the container layout
        layout = self.container.layout()
        
        # Render each page
        mat = fitz.Matrix(self.zoom_level, self.zoom_level)
        
        for page_num in range(len(self.pdf_doc.doc)):
            page = self.pdf_doc.doc[page_num]
            
            # Apply highlights for this page
            self.pdf_doc.apply_highlights(page_num)
            
            # Get page pixmap
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
                                # Apply zoom and ensure coordinates are within widget bounds
                                scaled_rect = {
                                    'x': max(0, rect[0] * self.zoom_level),
                                    'y': max(0, rect[1] * self.zoom_level),
                                    'width': max(1, (rect[2] - rect[0]) * self.zoom_level),
                                    'height': max(1, (rect[3] - rect[1]) * self.zoom_level)
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
        total_pages = len(self.pdf_doc.doc)
        self.setWindowTitle(f'PDF Annotator 9000 - {total_pages} pages')
    
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
            clipboard = QApplication.clipboard()  # Fixed clipboard access
            clipboard.clear()
            clipboard.setText(self.selected_text)
    
    def save_annotations(self):
        """Save modified PDF with annotations"""
        if not self.pdf_doc.doc:
            return
            
        # Get save path from user
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Annotated PDF",
            "",
            "PDF Files (*.pdf)"
        )
        
        if save_path:
            self.pdf_doc.save(save_path)
    
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
            if self.pdf_doc.doc:
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
        """Create a highlight annotation from the current text selection"""
        # Check if we have a selection
        if not hasattr(self, 'current_selection_info') or not self.current_selection_info:
            return
            
        # Get the current page widget
        page_num = self.current_selection_info['page_num']
        if page_num >= len(self.page_widgets):
            return
            
        page_widget = self.page_widgets[page_num]
        
        # Check if we have valid selection indices
        if page_widget.selection_start is None or page_widget.selection_end is None:
            # No active selection, try to use the current_selection_info to find text
            text = self.current_selection_info['text']
            if not text:
                return
                
            # Find the text in the page's text blocks
            text_found = False
            for i, block in enumerate(page_widget.text_blocks):
                if block['text'] == text[0]:  # Found potential start
                    # Check if the following characters match
                    matches = True
                    for j, char in enumerate(text[1:], 1):
                        if i + j >= len(page_widget.text_blocks) or page_widget.text_blocks[i + j]['text'] != char:
                            matches = False
                            break
                    
                    if matches:
                        # Found the text, set selection indices
                        page_widget.selection_start = i
                        page_widget.selection_end = i + len(text) - 1
                        text_found = True
                        break
            
            if not text_found:
                return
        
        # Get selection indices
        start_idx = min(page_widget.selection_start, page_widget.selection_end)
        end_idx = max(page_widget.selection_start, page_widget.selection_end)
        
        # Get the rectangles for the selected text
        selected_rects = []
        current_line = []
        current_y = None
        
        # Group characters by line
        for i in range(start_idx, end_idx + 1):
            if i >= len(page_widget.text_blocks):
                break
                
            rect = page_widget.text_blocks[i]['rect']
            y = int(rect['y'])
            
            # If this is a new line or the first character
            if current_y is None or abs(y - current_y) > rect['height'] * 0.5:
                # Add the previous line if it exists
                if current_line:
                    # Create a single rectangle for the line
                    x_start = min(r['x'] for r in current_line)
                    x_end = max(r['x'] + r['width'] for r in current_line)
                    selected_rects.append(fitz.Rect(
                        x_start / self.zoom_level,
                        current_line[0]['y'] / self.zoom_level,
                        x_end / self.zoom_level,
                        (current_line[0]['y'] + current_line[0]['height']) / self.zoom_level
                    ))
                # Start a new line
                current_line = [rect]
                current_y = y
            else:
                # Add to current line
                current_line.append(rect)
        
        # Add the last line
        if current_line:
            x_start = min(r['x'] for r in current_line)
            x_end = max(r['x'] + r['width'] for r in current_line)
            selected_rects.append(fitz.Rect(
                x_start / self.zoom_level,
                current_line[0]['y'] / self.zoom_level,
                x_end / self.zoom_level,
                (current_line[0]['y'] + current_line[0]['height']) / self.zoom_level
            ))
        
        # Create a single command for all rectangles
        if selected_rects:
            # Check if we'll lose redo history and if we should show the warning
            if (self.command_history.will_lose_redo_history() and 
                not self.settings.value("hide_redo_warning", False, type=bool)):
                # Create message box with checkbox
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle('Warning')
                msg_box.setText('Creating a new highlight here will clear your redo history.')
                msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg_box.setDefaultButton(QMessageBox.No)
                
                # Add checkbox
                checkbox = QCheckBox("Don't show this warning again")
                msg_box.setCheckBox(checkbox)
                
                reply = msg_box.exec_()
                
                # Save checkbox state if user clicked Yes
                if reply == QMessageBox.Yes and checkbox.isChecked():
                    self.settings.setValue("hide_redo_warning", True)
                    self.settings.sync()
                
                if reply == QMessageBox.No:
                    return
                    
            command = HighlightCommand(self.pdf_doc, selected_rects, page_num, self.highlight_color)
            self.command_history.execute(command)
        
        # Clear the selection after highlighting
        page_widget.selection_start = None
        page_widget.selection_end = None
        page_widget.update()
        
        # Update undo/redo action states
        self.update_undo_redo_actions()
        
        # Rerender to show highlights
        self.render_pdf()
    
    def perform_search(self):
        """Search through document text"""
        query = self.search_field.text().lower()
        self.search_results = []
        
        for page_num, text in enumerate(self.pdf_doc.page_text_data):
            if query in text.lower():
                # Find all matches and their positions
                start_idx = 0
                while True:
                    idx = text.lower().find(query, start_idx)
                    if idx == -1:
                        break
                    self.search_results.append((page_num, idx, idx+len(query)))
                    start_idx = idx + len(query)
        
        if self.search_results:
            self.current_search_index = 0
            self.highlight_search_result()
        self.render_pdf()  # Rerender to show search highlights

    def highlight_search_result(self):
        """Highlight current search result"""
        if self.search_results:
            page_num, start_idx, end_idx = self.search_results[self.current_search_index]
            self.highlight_selected_text()
            self.current_selection_info = {
                'text': self.pdf_doc.page_text_data[page_num][start_idx:end_idx],
                'page_num': page_num
            }
            self.render_pdf()

    def closeEvent(self, event):
        """Save state on window close"""
        self.save_current_session()
        super().closeEvent(event)
        
    def save_current_session(self):
        """Save current document and annotations"""
        try:
            # Save window geometry and state
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())
            
            # Save zoom level if it exists
            if hasattr(self, 'zoom_level'):
                self.settings.setValue("zoom_level", self.zoom_level)
            
            # Save scroll position if scroll_area still exists
            if hasattr(self, 'scroll_area') and not self.scroll_area.isHidden():
                try:
                    scroll_pos = self.scroll_area.verticalScrollBar().value()
                    self.settings.setValue("scroll_position", scroll_pos)
                except Exception as e:
                    print(f"Warning: Could not save scroll position: {e}")
            
            # Save current file path if a document is open
            if hasattr(self, 'pdf_doc') and self.pdf_doc.doc:
                current_path = self.pdf_doc.doc.name
                if current_path and os.path.exists(current_path):
                    self.settings.setValue("last_file", current_path)
                    
                    # Save annotations and command history
                    try:
                        # Save annotations
                        annotations_data = []
                        for ann in self.pdf_doc.annotations:
                            color = ann['color']
                            color_dict = {
                                'r': color.red(),
                                'g': color.green(),
                                'b': color.blue(),
                                'a': color.alpha()
                            }
                            
                            rect = ann['rect']
                            rect_dict = {
                                'x0': rect.x0,
                                'y0': rect.y0,
                                'x1': rect.x1,
                                'y1': rect.y1
                            }
                            
                            ann_dict = {
                                'type': ann['type'],
                                'page': ann['page'],
                                'color': color_dict,
                                'rect': rect_dict
                            }
                            annotations_data.append(ann_dict)
                        
                        self.settings.setValue("annotations", json.dumps(annotations_data))
                        
                        # Save command history
                        command_history = self.command_history.to_dict()
                        self.settings.setValue("command_history", json.dumps(command_history))
                        
                    except Exception as e:
                        print(f"Warning: Could not save annotations or history: {e}")
        except Exception as e:
            print(f"Warning: Error saving session: {e}")
            try:
                self.settings.sync()
            except:
                pass

    def load_last_session(self):
        """Load previous session state"""
        try:
            # Restore window geometry and state if they exist
            if self.settings.contains("geometry"):
                self.restoreGeometry(self.settings.value("geometry"))
            if self.settings.contains("windowState"):
                self.restoreState(self.settings.value("windowState"))
            
            # Restore zoom level if zoom_combo exists
            if hasattr(self, 'zoom_combo') and self.settings.contains("zoom_level"):
                try:
                    self.zoom_level = float(self.settings.value("zoom_level"))
                    self.zoom_combo.setCurrentText(f"{int(self.zoom_level * 100)}%")
                except (ValueError, TypeError) as e:
                    print(f"Error restoring zoom level: {e}")
                    self.zoom_level = 1.5  # Reset to default if invalid
            
            # Restore last opened file
            if self.settings.contains("last_file"):
                last_file = self.settings.value("last_file")
                if os.path.exists(last_file):
                    if self.pdf_doc.open(last_file):
                        # Restore annotations
                        if self.settings.contains("annotations"):
                            try:
                                annotations_data = json.loads(self.settings.value("annotations"))
                                for ann_dict in annotations_data:
                                    # Reconstruct QColor
                                    color_dict = ann_dict['color']
                                    color = QColor(
                                        color_dict['r'],
                                        color_dict['g'],
                                        color_dict['b'],
                                        color_dict['a']
                                    )
                                    
                                    # Reconstruct fitz.Rect
                                    rect_dict = ann_dict['rect']
                                    rect = fitz.Rect(
                                        rect_dict['x0'],
                                        rect_dict['y0'],
                                        rect_dict['x1'],
                                        rect_dict['y1']
                                    )
                                    
                                    # Add annotation
                                    self.pdf_doc.add_highlight(rect, ann_dict['page'], color)
                            except Exception as e:
                                print(f"Error restoring annotations: {e}")
                                
                        # Restore command history
                        if self.settings.contains("command_history"):
                            try:
                                command_history = json.loads(self.settings.value("command_history"))
                                self.command_history.load_from_dict(command_history, self.pdf_doc)
                                # Update UI state for undo/redo buttons
                                self.update_undo_redo_actions()
                            except Exception as e:
                                print(f"Error restoring command history: {e}")
                        
                        # Render the document
                        self.render_pdf()
                        
                        # Restore scroll position if scroll_area exists
                        if hasattr(self, 'scroll_area') and self.settings.contains("scroll_position"):
                            try:
                                scroll_pos = int(self.settings.value("scroll_position"))
                                self.scroll_area.verticalScrollBar().setValue(scroll_pos)
                            except (ValueError, TypeError) as e:
                                print(f"Error restoring scroll position: {e}")
        except Exception as e:
            print(f"Error loading session: {e}")
            self.zoom_level = 1.5

    def undo_last_action(self):
        """Handle undo logic"""
        if self.command_history.undo():
            print("Undid last action")  # Debug print
            self.update_undo_redo_actions()
            # Force a complete rerender to show changes
            if self.pdf_doc.doc:
                self.render_pdf()
        
    def redo_last_action(self):
        """Handle redo logic"""
        if self.command_history.redo():
            print("Redid last action")  # Debug print
            self.update_undo_redo_actions()
            # Force a complete rerender to show changes
            if self.pdf_doc.doc:
                self.render_pdf()
            
    def update_undo_redo_actions(self):
        """Update the enabled state of undo/redo actions"""
        can_undo = len(self.command_history.undo_stack) > 0
        can_redo = len(self.command_history.redo_stack) > 0
        
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)
        print(f"Updated action states - Can undo: {can_undo}, Can redo: {can_redo}")  # Debug print 