"""
SID Player UI Components
Contains UI widgets, layout initialization, and styling
"""

from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtCore import pyqtSignal, Qt
from typing import Optional, Callable


class ClickableProgressBar(QProgressBar):
    """
    Progress bar który reaguje na klikanie - emituje procent i czas docelowy
    Pozwala na szybkie przeskakiwanie do wybranego miejsca w utworze
    """
    # Signal emitting target time in seconds when clicked
    seek_requested = pyqtSignal(int)
    
    def __init__(self, parent=None, total_duration_callback: Optional[Callable] = None):
        """
        Initialize clickable progress bar
        
        Args:
            parent: Parent widget
            total_duration_callback: Callback function returning total duration in seconds
        """
        super().__init__(parent)
        self.total_duration_callback = total_duration_callback
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event):
        """
        Obsługa kliknięcia na pasek - oblicz docelowy czas i emituj sygnał
        Allows user to seek by clicking on progress bar
        """
        if self.maximum() > 0:
            # Oblicz procent na podstawie pozycji X myszki
            click_percent = (event.x() / self.width()) * 100
            self.setValue(int(click_percent))
            
            # Oblicz docelowy czas w sekundach
            if self.total_duration_callback:
                total_duration = self.total_duration_callback()
                if total_duration > 0:
                    target_time = int((click_percent / 100) * total_duration)
                    self.seek_requested.emit(target_time)
    
    def mouseMoveEvent(self, event):
        """Show tooltip with time when hovering over progress bar"""
        try:
            if self.maximum() > 0 and self.total_duration_callback:
                hover_percent = (event.x() / self.width()) * 100
                total_duration = self.total_duration_callback()
                if total_duration > 0:
                    hover_time = int((hover_percent / 100) * total_duration)
                    minutes = hover_time // 60
                    seconds = hover_time % 60
                    self.setToolTip(f"{minutes}:{seconds:02d}")
        except Exception:
            pass


def create_progress_bar_with_seek(parent=None, duration_callback=None):
    """
    Factory function to create a clickable progress bar
    
    Args:
        parent: Parent widget
        duration_callback: Callback returning total duration
        
    Returns:
        ClickableProgressBar instance
    """
    return ClickableProgressBar(parent, duration_callback)