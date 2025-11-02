#!/usr/bin/env python3
"""
Playlist Widget dla SID Playera - PyQt5 GUI
Wyświetlanie, edycja i kontrola playlisty
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox, QInputDialog,
    QAbstractButton, QDialog, QProgressBar, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QMimeData, QThread, QObject, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QIcon
from pathlib import Path
from typing import Optional, Dict
import hashlib
import os

from playlist_manager import PlaylistManager, PlaylistEntry
from sid_file_parser import SIDFileParser


def format_artist_name(artist: str) -> str:
    """
    Zmienia format artysty z "Imię Nazwisko (Nick)" na "Nick (Imię Nazwisko)"
    Jeśli brak nawiasów, zwraca oryginalny tekst
    """
    if not artist:
        return artist
    
    # Szukaj ostatniego nawiasu otwierającego i zamykającego
    if "(" in artist and ")" in artist:
        # Znajdź ostatnie nawiasy
        last_open = artist.rfind("(")
        last_close = artist.rfind(")")
        
        if last_open < last_close and last_close == len(artist) - 1:
            # Ekstraktuj Nick z nawiasów
            nick = artist[last_open + 1:last_close].strip()
            # Ekstraktuj Imię Nazwisko przed nawiasami
            name = artist[:last_open].strip()
            
            if nick and name:
                return f"{nick} ({name})"
    
    # Zwróć oryginalny jeśli nie ma nawiasów lub format jest inny
    return artist


def format_tracker_name(tracker: str) -> str:
    """
    Formatuje nazwę trackera: zamienia underscore'y na spacje
    np. "Music_Assembler" -> "Music Assembler"
    """
    if not tracker:
        return tracker
    return tracker.replace("_", " ")


# Import tracker recognition
try:
    from tracker_recognition import get_recognizer
    TRACKER_RECOGNITION_AVAILABLE = True
except ImportError:
    TRACKER_RECOGNITION_AVAILABLE = False


# ===== WORKER THREAD CLASSES =====
class FileAddingWorker(QObject):
    """Worker thread do dodawania plików z folderu bez zacinania GUI"""
    
    # Signals
    progress_updated = pyqtSignal(int, str)  # Emits (count, current_file_name)
    finished = pyqtSignal(int)  # Emits total added count
    error_occurred = pyqtSignal(str)  # Emits error message
    cancelled = pyqtSignal()  # Emits when cancelled
    
    def __init__(self, folder_path: str = None, playlist_manager=None, song_lengths: Dict = None, paths: list = None, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.paths = paths or []  # Support for drag & drop multiple paths
        self.playlist_manager = playlist_manager
        self.song_lengths = song_lengths
        self.is_cancelled = False
    
    def cancel(self):
        """Anuluj przetwarzanie"""
        self.is_cancelled = True
    
    @pyqtSlot()
    def run(self):
        """Główna logika worker thread - przetwarzaj pliki"""
        try:
            from pathlib import Path
            added = 0
            
            # Snapshot of existing file paths to avoid race condition
            existing_files = set(e.file_path for e in self.playlist_manager.entries)
            
            # Zbierz wszystkie pliki .sid do przetworzenia
            all_sid_files = []
            
            # Jeśli folder_path jest podany (Add Folder)
            if self.folder_path:
                all_sid_files.extend(Path(self.folder_path).rglob("*.sid"))
            
            # Jeśli paths są podane (Drag & Drop)
            if self.paths:
                for path_str in self.paths:
                    path = Path(path_str)
                    if path.is_file() and path.suffix.lower() == '.sid':
                        all_sid_files.append(path)
                    elif path.is_dir():
                        all_sid_files.extend(path.rglob("*.sid"))
            
            # Iterate through all .sid files
            for file_path in all_sid_files:
                if self.is_cancelled:
                    self.cancelled.emit()
                    return
                
                file_path_str = str(file_path)
                
                # Check if already in playlist
                if file_path_str in existing_files:
                    continue
                
                try:
                    # Parse SID file to get metadata
                    parser = SIDFileParser(file_path_str)
                    
                    # Get metadata from SID file
                    title = parser.get_name() if parser.is_valid() else file_path.stem
                    author = parser.get_author() if parser.is_valid() else "Unknown"
                    year = parser.get_year_from_released() if parser.is_valid() else ""
                    released = parser.get_released() if parser.is_valid() else ""
                    
                    # Get duration from Songlengths database
                    md5_hash = self._get_file_md5(file_path_str)
                    duration = self.song_lengths.get(md5_hash, 120)
                    
                    # Recognize tracker
                    tracker = self._get_tracker_info(file_path_str)
                    
                    # Add to playlist
                    entry = PlaylistEntry(file_path_str, title, author, duration, year, tracker=tracker, group=released)
                    self.playlist_manager.entries.append(entry)
                    added += 1
                    
                    # Emit progress signal
                    self.progress_updated.emit(added, file_path.name)
                    
                except Exception as e:
                    print(f"[ERROR] Błąd przetwarzania {file_path}: {e}")
                    continue
            
            self.finished.emit(added)
        
        except Exception as e:
            self.error_occurred.emit(f"Błąd podczas dodawania plików: {str(e)}")
    
    def _get_file_md5(self, filepath: str) -> str:
        """Calculate MD5 hash of SID file"""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest().lower()
        except Exception:
            return ""
    
    def _get_tracker_info(self, filepath: str) -> str:
        """Recognize tracker from SID file"""
        if TRACKER_RECOGNITION_AVAILABLE:
            try:
                recognizer = get_recognizer()
                tracker = recognizer.recognize_tracker(filepath, verbose=False)
                result = tracker if tracker != "Unknown" else ""
                return result
            except Exception:
                return ""
        return ""


class FileAddingProgressDialog(QDialog):
    """Dialog pokazujący postęp dodawania plików z przyciskiem CANCEL"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📁 Adding Files to Playlist...")
        self.setGeometry(200, 200, 400, 150)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)  # Ukryj X button
        self.setModal(True)
        
        # UI Layout
        layout = QVBoxLayout()
        
        # Info label
        self.info_label = QLabel("Initializing...")
        layout.addWidget(self.info_label)
        
        # Counter label
        self.counter_label = QLabel("Files added: 0")
        self.counter_label.setStyleSheet("font-weight: bold; color: #888888;")
        layout.addWidget(self.counter_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        layout.addWidget(self.progress_bar)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.cancel_button = QPushButton("❌ CANCEL")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #888888;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #aaaaaab;
            }
        """)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    @pyqtSlot(int, str)
    def update_progress(self, count: int, filename: str):
        """Update progress display"""
        self.counter_label.setText(f"Files added: {count}")
        self.info_label.setText(f"Processing: {filename}")
    
    @pyqtSlot(int)
    def on_finished(self, count: int):
        """Called when adding is finished"""
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.counter_label.setText(f"✅ Completed! Added {count} files")
        self.cancel_button.setText("✓ Close")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #888888;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #aaaaaa;
            }
        """)
    
    @pyqtSlot()
    def on_cancelled(self):
        """Called when operation is cancelled"""
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.counter_label.setText("⏹️ Operation cancelled")
        self.cancel_button.setText("✓ Close")


class PlaylistWidget(QWidget):
    """Widget do zarządzania playlistą"""
    
    # Signals
    song_selected = pyqtSignal(str)  # Emits file path
    song_double_clicked = pyqtSignal(str, int)  # Emits file path and duration (in seconds)
    playlist_changed = pyqtSignal()
    
    def __init__(self, parent=None, songlengths_path: str = "", theme_settings: Dict = None):
        super().__init__(parent)
        # Set flags to be independent window
        from PyQt5.QtCore import Qt
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setObjectName("PlaylistWidget")
        
        self.setWindowTitle("🎵 Playlist")
        
        # --- WINDOW ICON ---
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        icon_path = os.path.join(assets_dir, "sid_ico.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Resize window - teraz mniejsze (ustawiane w sid_player_modern07.py)
        self.setGeometry(100, 100, 820, 450)
        self.setMinimumWidth(500)  # Zapobiega zmniejszeniu poniżej minimalnego rozmiaru
        
        # --- THEME SETTINGS ---
        self.theme_settings = theme_settings if theme_settings else {
            'hue': 210,
            'saturation': 50,
            'brightness': 50,
            'temperature': 50
        }
        
        self.playlist_manager = PlaylistManager("sidplayer_playlist.json")
        self.current_playing_index = -1
        self.songlengths_path = songlengths_path
        self.song_lengths = {}
        self.load_songlengths()
        
        # --- SORT STATE TRACKING ---
        self.sort_state = {
            'title': 'ascending',      # Toggle: ascending -> descending -> ascending...
            'author': 'ascending',
            'year': 'ascending'
        }
        self.sort_buttons = {}  # Store references to sort buttons for updating labels
        
        # Setup UI
        self.setup_ui()
        self.apply_theme()
        self.update_list()
        
        # --- DRAG AND DROP SUPPORT ---
        self.setAcceptDrops(True)
        self.playlist_table.setAcceptDrops(True)
        
        # --- FILE ADDING WORKER THREAD ---
        self.file_adding_thread = None
        self.file_adding_worker = None
        self.file_adding_dialog = None
    
    def load_songlengths(self):
        """Load Songlengths.md5 database"""
        self.song_lengths = {}
        if not self.songlengths_path or not os.path.exists(self.songlengths_path):
            return
        
        try:
            with open(self.songlengths_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(';'):
                        continue
                    
                    if "=" in line:
                        try:
                            md5_hash, time_str = line.split("=", 1)
                            md5_hash = md5_hash.strip().lower()
                            times = time_str.strip().split()
                            if times and ":" in times[0]:
                                min_, sec_ = times[0].split(":")
                                min_ = int(min_)
                                sec_ = float(sec_.split('.')[0])  # Remove milliseconds
                                self.song_lengths[md5_hash] = int(min_ * 60 + sec_)
                        except Exception:
                            pass
        except Exception:
            pass
    
    def get_file_md5(self, filepath: str) -> str:
        """Calculate MD5 hash of SID file"""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest().lower()
        except Exception:
            return ""
    
    def get_song_duration_from_db(self, filepath: str) -> int:
        """Get song duration from Songlengths database"""
        md5_hash = self.get_file_md5(filepath)
        if md5_hash in self.song_lengths:
            return self.song_lengths[md5_hash]
        return 120  # Default fallback
    
    def _get_tracker_info(self, filepath: str) -> str:
        """Recognize tracker from SID file"""
        if TRACKER_RECOGNITION_AVAILABLE:
            try:
                recognizer = get_recognizer()
                tracker = recognizer.recognize_tracker(filepath, verbose=False)
                result = tracker if tracker != "Unknown" else ""
                return result
            except Exception:
                return ""
        return ""
    
    def regenerate_tracker_info_for_all(self):
        """Regenerate tracker info for all playlist entries (useful for old playlists)"""
        if not TRACKER_RECOGNITION_AVAILABLE:
            return 0
        
        count = 0
        for entry in self.playlist_manager.entries:
            if not entry.tracker and os.path.exists(entry.file_path):
                tracker = self._get_tracker_info(entry.file_path)
                if tracker:
                    entry.tracker = tracker
                    count += 1
        
        if count > 0:
            self.update_list()
            print(f"[PLAYLIST] ✅ Regenerated {count} tracker entries")
        
        return count
    
    def setup_ui(self):
        """Configure interface"""
        layout = QVBoxLayout()
        
        # --- TOP BAR ---
        top_layout = QHBoxLayout()
        
        # Add song button
        btn_add = QPushButton("➕ Add Song")
        btn_add.clicked.connect(self.add_song)
        top_layout.addWidget(btn_add)
        
        # Add folder button
        btn_add_folder = QPushButton("📁 Add Folder")
        btn_add_folder.clicked.connect(self.add_folder)
        top_layout.addWidget(btn_add_folder)
        
        # Clear button
        btn_clear = QPushButton("🗑️  Clear")
        btn_clear.clicked.connect(self.clear_playlist)
        top_layout.addWidget(btn_clear)
        
        # Regenerate Trackers button
        btn_regen_trackers = QPushButton("🔄 Refresh Players")
        btn_regen_trackers.clicked.connect(self.on_regenerate_trackers)
        top_layout.addWidget(btn_regen_trackers)
        
        layout.addLayout(top_layout)
        
        # --- SEARCH BAR ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Title or artist...")
        self.search_input.textChanged.connect(self.search_playlist)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # --- SONG TABLE ---
        self.playlist_table = QTableWidget()
        self.playlist_table.setColumnCount(6)
        self.playlist_table.setHorizontalHeaderLabels([
            "Artist", "Title", "Year", "Duration", "Player", "Released"
        ])
        self.playlist_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.playlist_table.itemDoubleClicked.connect(self.on_song_double_clicked)
        # Stylesheet będzie ustawiony w apply_theme()
        self.playlist_table.horizontalHeader().setStretchLastSection(False)
        # Set column widths - DOSTOSUJ TUTAJ jeśli zmienisz rozmiar okna!
        # Okno: 600px → dostępne ~560px (minus scrollbar, padding)
        # Suma kolumn: ~555px
        self.playlist_table.setColumnWidth(0, 176)  # Artist
        self.playlist_table.setColumnWidth(1, 150)  # Title
        self.playlist_table.setColumnWidth(2, 44)   # Year
        self.playlist_table.setColumnWidth(3, 50)   # Duration
        self.playlist_table.setColumnWidth(4, 120)   # Tracker - ZWIĘKSZONA WIDOCZNOŚĆ
        self.playlist_table.setColumnWidth(5, 150)   # Group
        layout.addWidget(self.playlist_table)
        
        # --- BOTTOM BAR ---
        bottom_layout = QHBoxLayout()
        
        # Remove button
        btn_remove = QPushButton("❌ Remove")
        btn_remove.clicked.connect(self.remove_selected)
        bottom_layout.addWidget(btn_remove)
        
        # Sort buttons - with toggle state
        btn_sort_title = QPushButton("⬆️  Sort (Title A-Z)")
        btn_sort_title.clicked.connect(lambda: self.toggle_sort("title"))
        bottom_layout.addWidget(btn_sort_title)
        self.sort_buttons['title'] = btn_sort_title
        
        btn_sort_author = QPushButton("⬆️  Sort (Artist A-Z)")
        btn_sort_author.clicked.connect(lambda: self.toggle_sort("author"))
        bottom_layout.addWidget(btn_sort_author)
        self.sort_buttons['author'] = btn_sort_author
        
        btn_sort_year = QPushButton("🔽 Sort by Year")
        btn_sort_year.clicked.connect(lambda: self.toggle_sort("year"))
        bottom_layout.addWidget(btn_sort_year)
        self.sort_buttons['year'] = btn_sort_year
        
        # Shuffle button
        btn_shuffle = QPushButton("🔀 Shuffle")
        btn_shuffle.clicked.connect(self.shuffle_playlist)
        bottom_layout.addWidget(btn_shuffle)
        
        layout.addLayout(bottom_layout)
        
        # --- INFO BAR ---
        self.info_label = QLabel("ℹ️  No songs")
        self.info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.info_label)
        
        # --- ACTION BAR ---
        action_layout = QHBoxLayout()
        
        btn_save = QPushButton("💾 Save")
        btn_save.clicked.connect(self.save_playlist)
        action_layout.addWidget(btn_save)
        
        btn_load = QPushButton("📂 Load")
        btn_load.clicked.connect(self.load_playlist)
        action_layout.addWidget(btn_load)
        
        layout.addLayout(action_layout)
        
        self.setLayout(layout)
    
    def apply_theme(self):
        """Zastosuj motyw z głównego okna do playlisty"""
        try:
            # Import the theme function
            from theme_settings import apply_theme_to_color
        except ImportError:
            # Fallback jeśli funkcja nie jest dostępna
            return
        
        # Pobierz theme settings
        hue = self.theme_settings.get('hue', 210)
        sat = self.theme_settings.get('saturation', 50)
        bright = self.theme_settings.get('brightness', 50)
        contrast = self.theme_settings.get('contrast', 256)
        temp = self.theme_settings.get('temperature', 256)
        
        # Bazowe kolory (takie same jak w głównym oknie)
        base_bg_dark = (20, 28, 38)
        base_bg_mid = (28, 38, 48)
        base_accent = (70, 110, 140)
        base_text = (180, 200, 216)
        
        # Zastosuj transformacje
        bg_dark = apply_theme_to_color(base_bg_dark, hue, sat, bright, contrast, temp)
        bg_mid = apply_theme_to_color(base_bg_mid, hue, sat, bright, contrast, temp)
        accent = apply_theme_to_color(base_accent, hue, sat, bright, contrast, temp)
        text_color = apply_theme_to_color(base_text, hue, sat, bright, contrast, temp)
        
        # Rozpakowuj kolory
        a_r, a_g, a_b = accent
        t_r, t_g, t_b = text_color
        bg_d_r, bg_d_g, bg_d_b = bg_dark
        bg_m_r, bg_m_g, bg_m_b = bg_mid
        
        # Przechowaj kolory jako atrybuty żeby użyć w add_table_row
        self.bg_mid_color = QColor(int(bg_m_r), int(bg_m_g), int(bg_m_b))
        self.text_color = QColor(int(t_r), int(t_g), int(t_b))
        
        # Ustaw stylesheet dla okna
        window_stylesheet = f"""
        #PlaylistWidget {{
            background-color: rgb({bg_d_r}, {bg_d_g}, {bg_d_b});
        }}
        QWidget {{
            background-color: transparent;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QTableWidget {{
            background-color: rgb({bg_m_r}, {bg_m_g}, {bg_m_b});
            color: rgb({t_r}, {t_g}, {t_b});
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 1px;
            gridline-color: rgba(255, 255, 255, 0.05);
        }}
        QTableView {{
            background-color: rgb({bg_m_r}, {bg_m_g}, {bg_m_b});
            alternate-background-color: rgb({bg_m_r}, {bg_m_g}, {bg_m_b});
        }}
        QTableView::item {{
            padding: 4px;
            background-color: rgb({bg_m_r}, {bg_m_g}, {bg_m_b}) !important;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QTableView::item:selected {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.6) !important;
        }}
        QHeaderView::section {{
            background-color: rgb({bg_d_r}, {bg_d_g}, {bg_d_b});
            color: rgb({t_r}, {t_g}, {t_b});
            padding: 1px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        QTableWidget::corner-button {{
            background-color: rgb({bg_d_r}, {bg_d_g}, {bg_d_b});
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        QLineEdit {{
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 4px;
            padding: 4px 8px;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QLineEdit:focus {{
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 4px;
            padding: 6px 12px;
            color: rgb({t_r}, {t_g}, {t_b});
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.14);
            border-color: rgba(255, 255, 255, 0.2);
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.06);
        }}
        QLabel {{
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QScrollBar:vertical {{
            background-color: rgb({bg_d_r}, {bg_d_g}, {bg_d_b});
            width: 12px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
            border-radius: 6px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.7);
        }}
        QScrollBar:horizontal {{
            background-color: rgb({bg_d_r}, {bg_d_g}, {bg_d_b});
            height: 12px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
            border-radius: 6px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.7);
        }}
        """
        
        self.setStyleSheet(window_stylesheet)
        
        # Apply grayscale style to sort buttons (for arrow emoji)
        gray_color = (140, 140, 140)  # Gray color for sort button arrows
        sort_button_stylesheet = f"""
        #SortButton {{
            color: rgb({gray_color[0]}, {gray_color[1]}, {gray_color[2]}) !important;
        }}
        """
        # Set object names for sort buttons to use the stylesheet
        for field, btn in self.sort_buttons.items():
            btn.setObjectName("SortButton")
        
        self.setStyleSheet(window_stylesheet + sort_button_stylesheet)
        
        # Stylize vertical header (row numbers) separately - PyQt5 bug workaround
        vertical_header_stylesheet = f"""
        QHeaderView::section {{
            background-color: rgb({bg_d_r}, {bg_d_g}, {bg_d_b}) !important;
            color: rgb({t_r}, {t_g}, {t_b}) !important;
            padding: 1px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }}
        """
        self.playlist_table.verticalHeader().setStyleSheet(vertical_header_stylesheet)
        
        # Stylize horizontal header separately
        horizontal_header_stylesheet = f"""
        QHeaderView::section {{
            background-color: rgb({bg_d_r}, {bg_d_g}, {bg_d_b}) !important;
            color: rgb({t_r}, {t_g}, {t_b}) !important;
            padding: 1px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }}
        """
        self.playlist_table.horizontalHeader().setStyleSheet(horizontal_header_stylesheet)
        
        # Stylize corner button (intersection) - find and style directly
        # The corner button is a child QAbstractButton widget in QTableWidget
        corner_button = self.playlist_table.findChild(QAbstractButton)
        if corner_button is not None:
            corner_button_style = f"""
            background-color: rgb({bg_d_r}, {bg_d_g}, {bg_d_b}) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            """
            corner_button.setStyleSheet(corner_button_style)
        
        # Dodatkowo ustaw stylesheets dla info_label
        if hasattr(self, 'info_label'):
            self.info_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.7); font-size: 11px;")
    
    def set_theme_settings(self, new_settings: Dict):
        """Zaktualizuj theme settings i zastosuj je"""
        self.theme_settings = new_settings.copy()
        self.apply_theme()
    
    def add_song(self):
        """Add single song"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SID file",
            "n:\\- Programs\\Thonny\\- MOJE\\sidplayer",
            "SID Files (*.sid);;All Files (*.*)"
        )
        
        if file_path:
            # Parse SID file to get metadata
            parser = SIDFileParser(file_path)
            
            # Get metadata from SID file, or use defaults
            default_title = parser.get_name() if parser.is_valid() else Path(file_path).stem
            default_author = parser.get_author() if parser.is_valid() else "Unknown"
            default_year = parser.get_year_from_released() if parser.is_valid() else ""
            default_released = parser.get_released() if parser.is_valid() else ""
            
            # Allow user to edit title
            title, ok = QInputDialog.getText(
                self, "Edit Title", "Title:", text=default_title
            )
            
            if ok:
                # Allow user to edit author
                author, ok = QInputDialog.getText(
                    self, "Edit Artist", "Artist:", text=default_author
                )
                
                if ok:
                    # Allow user to edit released info
                    released, ok = QInputDialog.getText(
                        self, "Edit Released", "Released:", text=default_released
                    )
                    
                    if ok:
                        # Get duration from Songlengths database
                        duration = self.get_song_duration_from_db(file_path)
                        tracker = self._get_tracker_info(file_path)
                        
                        # Add to playlist with all metadata
                        entry = PlaylistEntry(file_path, title, author, duration, default_year, tracker=tracker, group=released)
                        if not any(e.file_path == file_path for e in self.playlist_manager.entries):
                            self.playlist_manager.entries.append(entry)
                            self.update_list()
                            self.playlist_changed.emit()
                            self._autosave_playlist()  # Auto-save after adding
                        else:
                            QMessageBox.warning(self, "Warning", "Song already in playlist")
                    else:
                        return
    
    def add_folder(self):
        """Add all .sid files from folder using worker thread (non-blocking)"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select folder",
            "n:\\- Programs\\Thonny\\- MOJE\\sidplayer"
        )
        
        if not folder:
            return
        
        # Create progress dialog
        self.file_adding_dialog = FileAddingProgressDialog(self)
        
        # Create worker thread
        self.file_adding_thread = QThread()
        self.file_adding_worker = FileAddingWorker(
            folder, 
            self.playlist_manager, 
            self.song_lengths
        )
        
        # Move worker to thread
        self.file_adding_worker.moveToThread(self.file_adding_thread)
        
        # Connect signals with QueuedConnection to ensure thread-safe execution
        self.file_adding_thread.started.connect(self.file_adding_worker.run, Qt.QueuedConnection)
        self.file_adding_worker.progress_updated.connect(self.file_adding_dialog.update_progress, Qt.QueuedConnection)
        self.file_adding_worker.finished.connect(self._on_files_added_finished, Qt.QueuedConnection)
        self.file_adding_worker.finished.connect(self.file_adding_dialog.on_finished, Qt.QueuedConnection)
        self.file_adding_worker.error_occurred.connect(self._on_file_adding_error, Qt.QueuedConnection)
        self.file_adding_worker.cancelled.connect(self.file_adding_dialog.on_cancelled, Qt.QueuedConnection)
        
        # Cancel button
        self.file_adding_dialog.cancel_button.clicked.connect(self._on_cancel_file_adding)
        
        # Show dialog
        self.file_adding_dialog.show()
        
        # Start thread
        self.file_adding_thread.start()
    
    @pyqtSlot(int)
    def _on_files_added_finished(self, count: int):
        """Called when file adding is finished"""
        self.update_list()
        self.playlist_changed.emit()
        if count > 0:
            self._autosave_playlist()  # Auto-save after adding
        
        # Close dialog after 3 seconds
        from PyQt5.QtCore import QTimer
        if self.file_adding_dialog:
            QTimer.singleShot(3000, lambda: self._close_file_adding_dialog())
    
    @pyqtSlot(str)
    def _on_file_adding_error(self, error_msg: str):
        """Called when error occurs during file adding"""
        if self.file_adding_dialog:
            self.file_adding_dialog.close()
        QMessageBox.critical(self, "Error", error_msg)
    
    @pyqtSlot()
    def _on_cancel_file_adding(self):
        """Cancel file adding operation"""
        if self.file_adding_worker:
            self.file_adding_worker.cancel()
        
        # Close dialog when already finished
        if self.file_adding_dialog and self.file_adding_worker and self.file_adding_worker.is_cancelled:
            self._close_file_adding_dialog()
    
    def _close_file_adding_dialog(self):
        """Close file adding dialog and clean up thread"""
        if self.file_adding_dialog:
            try:
                self.file_adding_dialog.close()
            except:
                pass
        
        # Clean up thread
        if self.file_adding_thread and self.file_adding_thread.isRunning():
            self.file_adding_thread.quit()
            self.file_adding_thread.wait()
        
        self.file_adding_thread = None
        self.file_adding_worker = None
        self.file_adding_dialog = None
    
    def on_regenerate_trackers(self):
        """Regenerate tracker info for all playlist entries"""
        count = self.regenerate_tracker_info_for_all()
        if count > 0:
            QMessageBox.information(self, "✅ Success", f"Regenerated tracker info for {count} songs")
        else:
            QMessageBox.information(self, "ℹ️  Info", "All songs already have tracker info or playlist is empty")
    
    def remove_selected(self):
        """Remove selected songs (supports multiple selection)"""
        selected_rows = self.playlist_table.selectedIndexes()
        
        if not selected_rows:
            return
        
        # Extract unique row indices from selected indexes
        unique_rows = set()
        for index in selected_rows:
            unique_rows.add(index.row())
        
        # Collect actual playlist indices from UserRole data
        indices_to_remove = []
        for row in unique_rows:
            item = self.playlist_table.item(row, 0)
            if item:
                actual_idx = item.data(Qt.UserRole)
                if actual_idx is None:
                    actual_idx = row
            else:
                actual_idx = row
            indices_to_remove.append(actual_idx)
        
        # Remove in reverse order to prevent index shifting
        for actual_idx in sorted(indices_to_remove, reverse=True):
            self.playlist_manager.remove(actual_idx)
        
        self.update_list()
        self.playlist_changed.emit()
        self._autosave_playlist()  # Auto-save after removing
    
    def clear_playlist(self):
        """Clear entire playlist"""
        reply = QMessageBox.question(
            self, "Confirm", "Clear entire playlist?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.playlist_manager.clear()
            self.update_list()
            self.playlist_changed.emit()
            self._autosave_playlist()  # Auto-save after clearing
    
    def search_playlist(self, query: str):
        """Search songs"""
        if not query:
            self.update_list()
            return
        
        results = self.playlist_manager.search(query)
        
        self.playlist_table.setRowCount(0)
        for idx in results:
            entry = self.playlist_manager.entries[idx]
            self.add_table_row(entry, idx, is_highlighted=True)
        
        if not results:
            self.info_label.setText("ℹ️  No matches found")
    
    def toggle_sort(self, field: str):
        """Toggle sort direction for a field (ascending <-> descending)"""
        if field not in self.sort_state:
            return
        
        # Toggle the state
        current_state = self.sort_state[field]
        new_state = 'descending' if current_state == 'ascending' else 'ascending'
        self.sort_state[field] = new_state
        
        # Call the appropriate sort method
        is_reverse = new_state == 'descending'
        
        if field == "title":
            if is_reverse:
                self.playlist_manager.sort_by_title_reverse()
            else:
                self.playlist_manager.sort_by_title()
        elif field == "author":
            if is_reverse:
                self.playlist_manager.sort_by_author_reverse()
            else:
                self.playlist_manager.sort_by_author()
        elif field == "year":
            if is_reverse:
                self.playlist_manager.sort_by_year_reverse()
            else:
                self.playlist_manager.sort_by_year()
        
        # Update button label
        self.update_sort_button_label(field)
        
        self.update_list()
        self.playlist_changed.emit()
    
    def update_sort_button_label(self, field: str):
        """Update sort button label to show current sort direction"""
        if field not in self.sort_buttons:
            return
        
        btn = self.sort_buttons[field]
        state = self.sort_state[field]
        
        if field == "title":
            arrow = "⬆️" if state == "ascending" else "⬇️"
            direction = "A-Z" if state == "ascending" else "Z-A"
            btn.setText(f"{arrow}  Sort (Title {direction})")
        elif field == "author":
            arrow = "⬆️" if state == "ascending" else "⬇️"
            direction = "A-Z" if state == "ascending" else "Z-A"
            btn.setText(f"{arrow}  Sort (Artist {direction})")
        elif field == "year":
            arrow = "🔼" if state == "ascending" else "🔽"
            btn.setText(f"{arrow} Sort by Year")
    
    def shuffle_playlist(self):
        """Shuffle playlist randomly"""
        self.playlist_manager.shuffle()
        self.update_list()
        self.playlist_changed.emit()
    
    def get_sort_state(self):
        """Zwróć aktualny stan sortowania"""
        return self.sort_state.copy()
    
    def set_sort_state(self, sort_state: dict):
        """Ustaw stan sortowania i aktualizuj przyciski"""
        # Zaaktualizuj tylko pola które istnieją w sort_state
        for field, state in sort_state.items():
            if field in self.sort_state:
                self.sort_state[field] = state
        
        # Aktualizuj etykiety przycisków
        for field in self.sort_state.keys():
            self.update_sort_button_label(field)
    
    def save_playlist(self):
        """Save playlist to JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Playlist",
            "sidplayer_playlist.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            if self.playlist_manager.save(file_path):
                QMessageBox.information(self, "Success", "Playlist saved!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save playlist")
    
    def load_playlist(self):
        """Load playlist from JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Playlist",
            ".",
            "JSON Files (*.json)"
        )
        
        if file_path:
            if self.playlist_manager.load(file_path):
                self.update_list()
                self.playlist_changed.emit()
                QMessageBox.information(self, "Success", "Playlist loaded!")
            else:
                QMessageBox.warning(self, "Error", "Failed to load playlist")
    
    def on_selection_changed(self):
        """Handle selection change"""
        current_row = self.playlist_table.currentRow()
        if current_row >= 0:
            # **FIX: Get the actual playlist index from the item data (not the table row index)**
            # This ensures correct song info shows when searching or filtering
            item = self.playlist_table.item(current_row, 0)
            if item:
                actual_idx = item.data(Qt.UserRole)
                if actual_idx is None:
                    actual_idx = current_row
            else:
                actual_idx = current_row
            
            entry = self.playlist_manager.entries[actual_idx]
            self.song_selected.emit(entry.file_path)
    
    def on_song_double_clicked(self, item: QTableWidgetItem):
        """Double-click - play song"""
        row = self.playlist_table.row(item)
        if row >= 0:
            # **FIX: Get the actual playlist index from the item data (not the table row index)**
            # This ensures correct song plays when searching or filtering
            actual_idx = item.data(Qt.UserRole)
            if actual_idx is None:
                # Fallback for compatibility
                actual_idx = row
            
            self.playlist_manager.set_current(actual_idx)
            file_path = self.playlist_manager.entries[actual_idx].file_path
            duration = self.playlist_manager.entries[actual_idx].duration
            self.song_double_clicked.emit(file_path, duration)
            self.current_playing_index = actual_idx
            self.update_list()
            
            # 🎯 HIGHLIGHT: Select row, scroll to center, and bold the selected item
            # After update_list(), find the row that corresponds to current_playing_index
            for row_idx in range(self.playlist_table.rowCount()):
                cell_item = self.playlist_table.item(row_idx, 0)
                if cell_item and cell_item.data(Qt.UserRole) == self.current_playing_index:
                    # Found the correct row
                    self.playlist_table.clearSelection()
                    self.playlist_table.selectRow(row_idx)
                    
                    # Scroll to the row and center it
                    self.playlist_table.scrollToItem(cell_item, QAbstractItemView.PositionAtCenter)
                    break
    
    def add_table_row(self, entry: PlaylistEntry, idx: int, is_highlighted: bool = False):
        """Add row to table"""
        duration_str = f"{entry.duration // 60}:{entry.duration % 60:02d}"
        
        row_position = self.playlist_table.rowCount()
        self.playlist_table.insertRow(row_position)
        
        # Format artist name - zmień format z "Imię Nazwisko (Nick)" na "Nick (Imię Nazwisko)"
        formatted_author = format_artist_name(entry.author)
        # Format tracker name - zamień underscore'y na spacje
        formatted_tracker = format_tracker_name(entry.tracker)
        
        # Create items
        items = [
            (0, formatted_author),
            (1, entry.title),
            (2, entry.year),
            (3, duration_str),
            (4, formatted_tracker),
            (5, entry.group)
        ]
        
        for col, text in items:
            item = QTableWidgetItem(text)
            
            # **IMPORTANT: Store the actual playlist index in the item data**
            # This is used to map table rows back to original playlist entries
            item.setData(Qt.UserRole, idx)
            
            # Ustaw background i text color używając setData z Qt.BackgroundRole
            if hasattr(self, 'bg_mid_color'):
                item.setData(Qt.BackgroundRole, self.bg_mid_color)
            
            if hasattr(self, 'text_color'):
                item.setData(Qt.ForegroundRole, self.text_color)
            
            # Dodatkowo ustaw bezpośrednio (backup)
            if hasattr(self, 'bg_mid_color'):
                item.setBackground(self.bg_mid_color)
            if hasattr(self, 'text_color'):
                item.setForeground(self.text_color)
            
            # Formatting dla highlighted
            if is_highlighted:
                item.setForeground(QColor("#0078d4"))
            
            # Formatting dla currently playing
            if idx == self.current_playing_index:
                font = QFont()
                font.setBold(True)
                font.setPointSize(10)  # Larger font
                item.setFont(font)
                # Bardziej widoczny kolor tekstu
                item.setForeground(QColor("#00ff00"))
                # Wyraźne tło dla aktualnie granego utworu
                item.setBackground(QColor(50, 80, 120))  # Bright blue-ish tint
            
            self.playlist_table.setItem(row_position, col, item)
    
    def update_list(self):
        """Update table view"""
        self.playlist_table.setRowCount(0)
        
        for idx, entry in enumerate(self.playlist_manager.get_all_entries()):
            self.add_table_row(entry, idx)
        
        # Update info
        count = len(self.playlist_manager)
        total_duration = sum(e.duration for e in self.playlist_manager.get_all_entries())
        mins = total_duration // 60
        hours = mins // 60
        mins = mins % 60
        
        if count == 0:
            self.info_label.setText("ℹ️  No songs")
        else:
            self.info_label.setText(
                f"ℹ️  Songs: {count} | Duration: {hours}h {mins}m"
            )
    
    def refresh_playlist(self, playlist_path=None):
        """Refresh/reload playlist from default JSON file or specified path"""
        try:
            # Jeśli ścieżka nie podana, spróbuj domyślną
            if playlist_path is None:
                playlist_path = "sidplayer_playlist.json"
            
            # Przeładuj playlistę z pliku JSON
            if os.path.exists(playlist_path):
                self.playlist_manager.load(playlist_path)
            else:
                # Fallback do domyślnego jeśli podana ścieżka nie istnieje
                if os.path.exists("sidplayer_playlist.json"):
                    self.playlist_manager.load("sidplayer_playlist.json")
            
            # Aktualizuj interfejs
            self.update_list()
            self.playlist_changed.emit()
        except Exception as e:
            pass  # Silent fail - playlist może nie być załadowana jeszcze
    
    def get_next_song(self) -> Optional[PlaylistEntry]:
        """Get next song"""
        return self.playlist_manager.next()
    
    def get_previous_song(self) -> Optional[PlaylistEntry]:
        """Get previous song"""
        return self.playlist_manager.previous()
    
    def get_current_song(self) -> Optional[PlaylistEntry]:
        """Get current song"""
        return self.playlist_manager.get_current()
    
    def set_current_song(self, index: int):
        """Set current song"""
        self.playlist_manager.set_current(index)
        self.current_playing_index = index
        self.update_list()
    
    def set_current_playing_from_filepath(self, file_path: str):
        """
        Set current playing song by file path (cursor follows playback).
        This is called whenever a song starts playing, automatically updating the playlist selection.
        Takes into account the current sort order.
        """
        if not file_path:
            return
        
        # Normalize path for comparison
        file_path = os.path.normpath(file_path)
        
        # Find the index in the currently displayed entries
        current_entries = self.playlist_manager.get_all_entries()
        for idx, entry in enumerate(current_entries):
            if os.path.normpath(entry.file_path) == file_path:
                self.current_playing_index = idx
                # Select the row in the table to follow the playback
                self.playlist_table.setCurrentCell(idx, 0)
                # Scroll to center - keeps song visible in middle of window
                self.playlist_table.scrollToItem(self.playlist_table.item(idx, 0), 
                                                 self.playlist_table.PositionAtCenter)
                # Refresh the display to highlight the current playing song
                self.update_list()
                return
    
    # --- DRAG AND DROP SUPPORT ---
    def dragEnterEvent(self, event):
        """Handle drag enter event - accept drops with files"""
        mime_data = event.mimeData()
        
        # Accept if it contains file URLs
        if mime_data.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """Handle drop event - process dropped files and folders"""
        mime_data = event.mimeData()
        
        if mime_data.hasUrls():
            event.acceptProposedAction()
            
            # Process each dropped item
            paths_to_process = []
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                paths_to_process.append(file_path)
            
            # Handle the dropped items
            self.handle_dropped_items(paths_to_process)
        else:
            event.ignore()
    
    def handle_dropped_items(self, paths: list):
        """
        Process dropped files and folders using worker thread (non-blocking)
        Automatically adds .sid files from files or recursively from folders
        """
        if not paths:
            return
        
        # Create progress dialog
        self.file_adding_dialog = FileAddingProgressDialog(self)
        
        # Create worker thread
        self.file_adding_thread = QThread()
        self.file_adding_worker = FileAddingWorker(
            playlist_manager=self.playlist_manager, 
            song_lengths=self.song_lengths,
            paths=paths  # Pass dropped paths directly
        )
        
        # Move worker to thread
        self.file_adding_worker.moveToThread(self.file_adding_thread)
        
        # Connect signals with QueuedConnection to ensure thread-safe execution
        self.file_adding_thread.started.connect(self.file_adding_worker.run, Qt.QueuedConnection)
        self.file_adding_worker.progress_updated.connect(self.file_adding_dialog.update_progress, Qt.QueuedConnection)
        self.file_adding_worker.finished.connect(self._on_files_added_finished, Qt.QueuedConnection)
        self.file_adding_worker.finished.connect(self.file_adding_dialog.on_finished, Qt.QueuedConnection)
        self.file_adding_worker.error_occurred.connect(self._on_file_adding_error, Qt.QueuedConnection)
        self.file_adding_worker.cancelled.connect(self.file_adding_dialog.on_cancelled, Qt.QueuedConnection)
        
        # Cancel button
        self.file_adding_dialog.cancel_button.clicked.connect(self._on_cancel_file_adding)
        
        # Show dialog
        self.file_adding_dialog.show()
        
        # Start thread
        self.file_adding_thread.start()
    
    def _add_single_file(self, file_path_str: str) -> bool:
        """
        Add a single .sid file to playlist without asking for metadata
        Returns True if added, False if skipped (duplicate)
        """
        # Check if already in playlist
        if any(e.file_path == file_path_str for e in self.playlist_manager.entries):
            return False
        
        try:
            # Parse SID file to get metadata
            parser = SIDFileParser(file_path_str)
            
            # Get metadata from SID file
            title = parser.get_name() if parser.is_valid() else Path(file_path_str).stem
            author = parser.get_author() if parser.is_valid() else "Unknown"
            year = parser.get_year_from_released() if parser.is_valid() else ""
            released = parser.get_released() if parser.is_valid() else ""
            
            # Get duration from Songlengths database
            duration = self.get_song_duration_from_db(file_path_str)
            tracker = self._get_tracker_info(file_path_str)
            
            # Add to playlist
            entry = PlaylistEntry(file_path_str, title, author, duration, year, tracker=tracker, group=released)
            self.playlist_manager.entries.append(entry)
            return True
        
        except Exception as e:
            print(f"Error adding file {file_path_str}: {e}")
            return False
    
    def _autosave_playlist(self):
        """Auto-save playlist after changes (silent, no message)"""
        try:
            self.playlist_manager.save()
        except Exception as e:
            print(f"⚠️  Error auto-saving playlist: {e}")
    
    def closeEvent(self, event):
        """Clean up threads when closing window"""
        self._close_file_adding_dialog()
        super().closeEvent(event)


# --- DEMO STANDALONE ---
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    widget = PlaylistWidget(songlengths_path="Songlengths.md5")
    widget.show()
    
    sys.exit(app.exec_())