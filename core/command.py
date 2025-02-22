from abc import ABC, abstractmethod
from typing import List, Dict, Any
from PyQt5.QtGui import QColor
import fitz
import json

class Command(ABC):
    @abstractmethod
    def execute(self):
        pass
        
    @abstractmethod
    def undo(self):
        pass
        
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert command to a serializable dictionary"""
        pass
        
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any], pdf_doc):
        """Create command instance from dictionary"""
        pass

class HighlightCommand(Command):
    def __init__(self, pdf_doc, rects: List[fitz.Rect], page_num: int, color: QColor):
        self.pdf_doc = pdf_doc
        self.rects = rects  # Now a list of rectangles
        self.page_num = page_num
        self.color = color
        self.annotation_indices = []  # List of indices for all annotations
        self.removed_annotations = []  # Store removed annotations for redo
        
    def execute(self):
        """Add the highlight annotations"""
        if self.removed_annotations:
            # Restore removed annotations
            for idx, annotation in zip(self.annotation_indices, self.removed_annotations):
                if idx is not None and idx <= len(self.pdf_doc.annotations):
                    self.pdf_doc.annotations.insert(idx, annotation)
                else:
                    self.pdf_doc.annotations.append(annotation)
                    idx = len(self.pdf_doc.annotations) - 1
            self.removed_annotations = []
        else:
            # Add new highlights
            for rect in self.rects:
                self.pdf_doc.add_highlight(rect, self.page_num, self.color)
                self.annotation_indices.append(len(self.pdf_doc.annotations) - 1)
        return True
        
    def undo(self):
        """Remove all highlight annotations"""
        if not self.annotation_indices:
            return False
            
        # Remove annotations in reverse order to maintain correct indices
        self.removed_annotations = []
        for idx in reversed(self.annotation_indices):
            if 0 <= idx < len(self.pdf_doc.annotations):
                self.removed_annotations.insert(0, self.pdf_doc.annotations[idx])
                if not self.pdf_doc.remove_annotation(idx):
                    return False
        return True
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert command to a serializable dictionary"""
        return {
            'type': 'highlight',
            'rects': [{
                'x0': rect.x0,
                'y0': rect.y0,
                'x1': rect.x1,
                'y1': rect.y1
            } for rect in self.rects],
            'page_num': self.page_num,
            'color': {
                'r': self.color.red(),
                'g': self.color.green(),
                'b': self.color.blue(),
                'a': self.color.alpha()
            },
            'annotation_indices': self.annotation_indices
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any], pdf_doc):
        """Create command instance from dictionary"""
        rects = [fitz.Rect(
            rect_dict['x0'],
            rect_dict['y0'],
            rect_dict['x1'],
            rect_dict['y1']
        ) for rect_dict in data['rects']]
        
        color = QColor(
            data['color']['r'],
            data['color']['g'],
            data['color']['b'],
            data['color']['a']
        )
        command = cls(pdf_doc, rects, data['page_num'], color)
        command.annotation_indices = data.get('annotation_indices', [])
        return command

class CommandHistory:
    def __init__(self, max_stack_size: int = 100):
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_stack_size = max_stack_size
        
    def will_lose_redo_history(self) -> bool:
        """Check if executing a new command now would clear redo history"""
        return len(self.redo_stack) > 0
        
    def execute(self, command: Command) -> bool:
        """Execute a new command and add it to history"""
        if command.execute():
            self.undo_stack.append(command)
            # If we exceed max size, remove oldest command
            if len(self.undo_stack) > self.max_stack_size:
                self.undo_stack.pop(0)
            # Clear redo stack as we're creating a new history branch
            if self.redo_stack:
                print("Note: Cleared redo history as new action was performed")
            self.redo_stack.clear()
            return True
        return False
        
    def undo(self) -> bool:
        """Undo the last command"""
        if not self.undo_stack:
            return False
            
        command = self.undo_stack.pop()
        if command.undo():
            self.redo_stack.append(command)
            # If we exceed max size, remove oldest command
            if len(self.redo_stack) > self.max_stack_size:
                self.redo_stack.pop(0)
            return True
        return False
        
    def redo(self) -> bool:
        """Redo the last undone command"""
        if not self.redo_stack:
            return False
            
        command = self.redo_stack.pop()
        if command.execute():
            self.undo_stack.append(command)
            # If we exceed max size, remove oldest command
            if len(self.undo_stack) > self.max_stack_size:
                self.undo_stack.pop(0)
            return True
        return False
        
    def clear(self):
        """Clear all command history"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert command history to a serializable dictionary"""
        return {
            'undo_stack': [cmd.to_dict() for cmd in self.undo_stack],
            'redo_stack': [cmd.to_dict() for cmd in self.redo_stack],
            'max_stack_size': self.max_stack_size
        }
        
    def load_from_dict(self, data: Dict[str, Any], pdf_doc):
        """Load command history from dictionary"""
        self.clear()
        self.max_stack_size = data.get('max_stack_size', 100)
        
        # Reconstruct undo stack
        for cmd_data in data.get('undo_stack', []):
            if cmd_data['type'] == 'highlight':
                command = HighlightCommand.from_dict(cmd_data, pdf_doc)
                self.undo_stack.append(command)
                
        # Reconstruct redo stack
        for cmd_data in data.get('redo_stack', []):
            if cmd_data['type'] == 'highlight':
                command = HighlightCommand.from_dict(cmd_data, pdf_doc)
                self.redo_stack.append(command) 