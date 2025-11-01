"""
Debug Console Widget - shows sidplayfp output in real-time
Separate module for easy integration/removal
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt5.QtGui import QFont, QTextCursor, QColor
from PyQt5.QtCore import Qt, pyqtSignal
from datetime import datetime


class DebugConsoleWidget(QWidget):
    """Okno debuggera do wyświetlania outputu sidplayfp"""
    
    # Signal emitted when text needs to be added to console
    append_text = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.append_text.connect(self.add_text)  # Connect signal to slot
        
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Title
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier New", 9))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #44cc44;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_console)
        clear_btn.setMaximumWidth(80)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        copy_btn = QPushButton("Copy All")
        copy_btn.clicked.connect(self.copy_all)
        copy_btn.setMaximumWidth(80)
        button_layout.addWidget(copy_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setWindowTitle("SID Player - Debug Console [CTRL+X to toggle]")
        self.setGeometry(100, 100, 600, 400)
        
        self.log(f"[DEBUG] Console initialized at {datetime.now().strftime('%H:%M:%S')}")
    
    def log(self, message):
        """Add message to console (can be called from any thread via signal)"""
        self.append_text.emit(message)
    
    def add_text(self, text):
        """Add text to console (slot connected to signal)"""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + "\n")
        
        # Auto-scroll to bottom
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
    
    def clear_console(self):
        """Clear console"""
        self.text_edit.clear()
        self.log("[DEBUG] Console cleared")
    
    def copy_all(self):
        """Copy all text to clipboard"""
        self.text_edit.selectAll()
        self.text_edit.copy()
        self.log("[DEBUG] All text copied to clipboard")
    
    def closeEvent(self, event):
        """Handle close event"""
        # Don't close, just hide
        self.hide()
        event.ignore()