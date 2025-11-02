import sys
import os
import subprocess
import time
import threading
import configparser
import hashlib
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QProgressBar, QGroupBox, QFrame, QCheckBox
)
from PyQt5.QtGui import QFont, QPalette, QColor, QLinearGradient, QIcon
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal

from debug_console import DebugConsoleWidget
from theme_settings import ThemeSettingsWindow, apply_theme_to_color

# ===== IMPORT FROM MODULAR COMPONENTS =====
from utils import format_artist_name, format_tracker_name
from file_manager import FileManager
from sid_player_ui import ClickableProgressBar as UIClickableProgressBar
from ui_theme import UIThemeMixin
from sid_info_manager import SIDInfoMixin
from playback_manager import PlaybackManagerMixin
from windows_api_manager import WindowsAPIManagerMixin


# Note: format_artist_name and format_tracker_name are now imported from utils module


# Import tracker recognition
try:
    from tracker_recognition import get_recognizer
    TRACKER_RECOGNITION_AVAILABLE = True
except ImportError:
    TRACKER_RECOGNITION_AVAILABLE = False

# Import playlist components
try:
    from playlist_widget import PlaylistWidget
    PLAYLIST_AVAILABLE = True
except ImportError:
    PLAYLIST_AVAILABLE = False

try:
    from subprocess import CREATE_NO_WINDOW, CREATE_NEW_CONSOLE
except ImportError:
    CREATE_NO_WINDOW = 0x08000000
    CREATE_NEW_CONSOLE = 0x00000010
try:
    from subprocess import DETACHED_PROCESS
except ImportError:
    DETACHED_PROCESS = 0x00000008


# ClickableProgressBar is now imported from sid_player_ui module
# Create alias for compatibility
ClickableProgressBar = UIClickableProgressBar


class SIDPlayer(WindowsAPIManagerMixin, PlaybackManagerMixin, SIDInfoMixin, UIThemeMixin, QWidget):
    # Signal aby timer był startowany z main thread (nie z daemon thread)
    playback_started_signal = pyqtSignal(int)  # Emituje elapsed time
    song_started_signal = pyqtSignal(str)  # Emituje file path gdy nowy utwór się zaczyna grać
    
    def __init__(self):
        super().__init__()
        self.setObjectName("SIDPlayerRoot")

        # --- PODSTAWOWA INICJALIZACJA ---
        self.sid_file = None
        self.process = None
        self.is_playing = False
        self.loop_enabled = False
        self.playback_started = False  # Flaga czekająca na start playbacku
        self.console_visible = False  # Flaga do pokazywania konsoli sidplayfp
        self.total_duration = 0  # Całkowita długość utworu w sekundach
        
        # --- SONG DURATION MANAGEMENT ---
        self.song_lengths = {}
        self.default_song_duration = 120
        self.current_song_duration = self.default_song_duration
        
        # --- SUBTUNE MANAGEMENT ---
        self.num_subtunes = 1
        self.current_subtune = 1
        self.default_subtune = 1
        self.default_tune_only = False  # Jeśli True, ignoruj subtunes i graj zawsze default
        
        # --- DEBUG CONSOLE ---
        self.debug_console = DebugConsoleWidget(parent=self)
        
        # --- THEME SETTINGS ---
        self.theme_settings = {
            'hue': 210,
            'saturation': 50,
            'brightness': 50,
            'contrast': 256,
            'temperature': 256
        }
        self.theme_window = None  # Referencja do okna theme settings
        self.playlist_window = None  # Referencja do okna playlisty
        
        # --- EXIT CLEANUP ---
        self._cleanup_done = False  # Flaga aby cleanup_on_exit był idempotentny
        
        # --- PLAYLIST MANAGEMENT ---
        self.playlist_file_path = None  # Ścieżka do pliku playlisty
        self.last_playlist_index = -1  # Index ostatnio granego utworu z playlisty
        self.playlist_sort_state = {  # Stan sortowania playlisty
            'title': 'ascending',
            'author': 'ascending',
            'year': 'ascending'
        }
        
        # --- JSIDPLAY2 CHANNEL MUTE STATE ---
        self.jsidplay2_channels_muted = False  # Tracks mute state for PAUSE toggle (False = unmuted, True = muted)

        # --- ŚCIEŻKA DO sidplayfp.exe ---
        if hasattr(sys, 'frozen'):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Helper function to find executables (check tools/ subdirectory first)
        def find_executable(name):
            # Try tools subdirectory first
            tools_path = os.path.join(self.base_dir, "tools", name)
            if os.path.exists(tools_path):
                return tools_path
            # Try base directory as fallback
            path = os.path.join(self.base_dir, name)
            if os.path.exists(path):
                return path
            # Return tools path as default (will error with proper message if not found)
            return tools_path
        
        self.sidplayfp_path = find_executable("sidplayfp.exe")
        self.jsidplay2_path = find_executable("jsidplay2-console.exe")
        self.settings_path = os.path.join(self.base_dir, "settings.ini")
        self.songlengths_path = find_executable("Songlengths.md5")  # Also check tools/
        self.playlist_file_path = os.path.join(self.base_dir, "sidplayer_playlist.json")
        
        # --- AUDIO ENGINE SELECTION ---
        self.audio_engine = "sidplayfp"  # Default engine
        self.available_engines = {
            "sidplayfp": self.sidplayfp_path,
            "jsidplay2": self.jsidplay2_path
        }
        
        # Load song durations database
        self.load_song_lengths()

        if not os.path.exists(self.sidplayfp_path):
            QMessageBox.critical(self, "Fatal Error",
                                 f"Nie znaleziono sidplayfp.exe w:\n{self.sidplayfp_path}\n"
                                 "Umieść go w tym samym katalogu co program.")
            sys.exit(1)

        # --- TIMER ---
        self.time_elapsed = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        
        # --- PLAYBACK SPEED TRACKING ---
        self.playback_speed_multiplier = 1  # 1x lub 8x (dla UI)
        self.arrow_key_net_count = 0  # Śledzi ile arrow keys wysłano: 0=1x, 3=8x
        
        # --- AUTO SEEK TRACKING ---
        self.is_seeking = False  # Flaga czy trwa seek
        self.seek_target_time = 0  # Docelowy czas seek'u w sekundach
        self.seek_block_size = 8  # Rozmiar bloku seek (8 sekund = optymalne dla 16x)
        
        # Podłącz sygnał playback_started do slota który startuje timer z main thread
        self.playback_started_signal.connect(self.on_playback_started)

        # --- UI ---
        self.init_ui()
        
        # --- WINDOW ICON ---
        icon_path = os.path.join(self.base_dir, "assets", "sid_ico.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle("SID Player")
        
        self.apply_modern_theme()
        
        # Initialize status and button styling
        self.update_status_label()
        self.update_button_style()

        self.setFixedSize(380, 760)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)  # ENABLE KEYBOARD FOCUS FOR ARROW KEYS
        
        # Load settings (console_visible state)
        self.load_settings()
        
        # Load last used playlist (after settings are loaded)
        self._load_playlist_on_startup()

        QApplication.instance().aboutToQuit.connect(self.cleanup_on_exit)
        
        # --- WINDOWS API SETUP FOR ARROW KEY SIMULATION ---
        if sys.platform == "win32":
            self.setup_windows_api()
            
    # ===============================================
    #         AUDIO ENGINE MANAGEMENT
    # ===============================================
    def set_audio_engine(self, engine_name):
        """Zmień audio engine (sidplayfp lub jsidplay2)"""
        if engine_name in self.available_engines:
            self.audio_engine = engine_name
            self.debug_console.log(f"[INFO] Audio engine changed to: {engine_name}")
            # Zapisz ustawienie
            self.save_settings()
        else:
            self.debug_console.log(f"[ERROR] Unknown audio engine: {engine_name}")
    
    # ===============================================
    #            SETTINGS (INI FILE)
    # ===============================================
    def load_settings(self):
        """Załaduj ustawienia z settings.ini"""
        try:
            settings = FileManager.load_settings_ini(self.settings_path)
            
            # Load display settings
            if 'display' in settings:
                console_visible_str = settings['display'].get('console_visible', 'False')
                self.console_visible = console_visible_str.lower() in ['true', '1', 'yes']
                print(f"[INFO] Załadowano ustawienia: console_visible={self.console_visible}")
            
            # Load theme settings
            if 'theme' in settings and settings['theme']:
                self.theme_settings.update(settings['theme'])
                print(f"[INFO] Załadowano theme settings: {self.theme_settings}")
            
            # Load playback settings
            if 'playback' in settings:
                last_played = settings['playback'].get('last_played_file', '')
                if last_played and os.path.exists(last_played):
                    self.sid_file = last_played
                    print(f"[INFO] Załadowano ostatni plik: {os.path.basename(last_played)}")
                
                engine = settings['playback'].get('audio_engine', 'sidplayfp')
                if engine in self.available_engines:
                    self.audio_engine = engine
                    print(f"[INFO] Audio engine set to: {self.audio_engine}")
                
                loop_state_str = settings['playback'].get('loop_enabled', 'False')
                loop_state = loop_state_str.lower() in ['true', '1', 'yes']
                self.loop_checkbox.setChecked(loop_state)
                self.loop_enabled = loop_state
                print(f"[INFO] Załadowano stan Loop: {loop_state}")
                
                default_tune_str = settings['playback'].get('default_tune_only', 'False')
                default_tune_state = default_tune_str.lower() in ['true', '1', 'yes']
                self.default_tune_only_checkbox.setChecked(default_tune_state)
                self.default_tune_only = default_tune_state
                print(f"[INFO] Załadowano stan Default Tune Only: {default_tune_state}")
            
            # Load playlist sort settings
            if 'playlist_sort' in settings and settings['playlist_sort']:
                self.playlist_sort_state.update(settings['playlist_sort'])
                print(f"[INFO] Załadowano stan sortowania playlisty: {self.playlist_sort_state}")
            
            # Always apply theme settings after loading
            print(f"[INFO] Applying theme with loaded settings: {self.theme_settings}")
            self.apply_modern_theme()
        except Exception as e:
            print(f"[WARN] Nie udało się załadować settings.ini: {e}")

    def save_settings(self):
        """Zapisz ustawienia do settings.ini"""
        try:
            # Build settings dictionary
            settings = {
                'display': {
                    'console_visible': str(self.console_visible)
                },
                'theme': self.theme_settings.copy(),
                'playback': {
                    'loop_enabled': str(self.loop_enabled),
                    'audio_engine': str(self.audio_engine),
                    'default_tune_only': str(self.default_tune_only)
                },
                'playlist_sort': self.playlist_sort_state.copy()
            }
            
            # Add last played file if available
            if self.sid_file:
                settings['playback']['last_played_file'] = self.sid_file
            
            # Add last playlist index if available
            if self.playlist_window and hasattr(self.playlist_window, 'current_playing_index'):
                settings['playback']['last_playlist_index'] = str(self.playlist_window.current_playing_index)
            
            # Update playlist sort state if window is open
            if self.playlist_window and hasattr(self.playlist_window, 'get_sort_state'):
                sort_state = self.playlist_window.get_sort_state()
                self.playlist_sort_state = sort_state
                settings['playlist_sort'] = sort_state
            
            # Save using FileManager
            success = FileManager.save_settings_ini(self.settings_path, settings)
            if success:
                print(f"[INFO] Zapisano ustawienia: console_visible={self.console_visible}, theme={self.theme_settings}, last_played_file={os.path.basename(self.sid_file) if self.sid_file else 'None'}, loop_enabled={self.loop_enabled}")
        except Exception as e:
            print(f"[WARN] Nie udało się zapisać settings.ini: {e}")
    
    def _load_playlist_on_startup(self):
        """Załaduj ostatnio używaną playlistę przy starcie aplikacji"""
        try:
            if FileManager.file_exists(self.playlist_file_path):
                print(f"[PLAYLIST] ✓ Playlist file exists: {self.playlist_file_path}")
                print("[PLAYLIST] Playlist will be loaded when playlist window is opened")
                
                # Load last playlist index from settings
                self.last_playlist_index = -1
                try:
                    settings = FileManager.load_settings_ini(self.settings_path)
                    if 'playback' in settings:
                        last_index_str = settings['playback'].get('last_playlist_index', '-1')
                        self.last_playlist_index = int(last_index_str)
                        print(f"[PLAYLIST] Loaded last playlist index: {self.last_playlist_index}")
                except Exception as e:
                    print(f"[PLAYLIST] ⚠️  Error loading last playlist index: {e}")
            else:
                print(f"[PLAYLIST] No saved playlist found at: {self.playlist_file_path}")
        except Exception as e:
            print(f"[PLAYLIST] ⚠️  Error during playlist startup check: {e}")
    
    def _save_playlist_on_exit(self):
        """Zapisz aktualną playlistę i ostatnio grany utwór przy wychodzeniu z aplikacji"""
        try:
            if self.playlist_window is not None and hasattr(self.playlist_window, 'playlist_manager'):
                # Zapisz playlistę
                self.playlist_window.playlist_manager.save()
                
                # Zapisz index ostatnio granego utworu
                if hasattr(self.playlist_window, 'current_playing_index'):
                    self.last_playlist_index = self.playlist_window.current_playing_index
                
                print(f"[PLAYLIST] ✓ Playlist saved on exit: {self.playlist_file_path}")
                print(f"[PLAYLIST] ✓ Last playing index saved: {self.last_playlist_index}")
            else:
                print("[PLAYLIST] Playlist window not open, using auto-saved playlist")
        except Exception as e:
            print(f"[PLAYLIST] ⚠️  Error saving playlist on exit: {e}")
    
    def _restore_last_playlist_track(self):
        """Przywróć ostatnio grany utwór - zaznacz go na playliście"""
        try:
            if self.playlist_window is None or not hasattr(self.playlist_window, 'playlist_table'):
                return
            
            if self.last_playlist_index < 0:
                print("[PLAYLIST] No last playlist index to restore")
                return
            
            playlist_table = self.playlist_window.playlist_table
            row_count = playlist_table.rowCount()
            
            if self.last_playlist_index >= row_count:
                print(f"[PLAYLIST] ⚠️  Last index {self.last_playlist_index} out of range (table has {row_count} rows)")
                return
            
            # Zaznacz rząd w tabeli
            playlist_table.selectRow(self.last_playlist_index)
            
            # Przewiń do tego wiersza, aby był widoczny
            playlist_table.scrollToItem(
                playlist_table.item(self.last_playlist_index, 0),
                playlist_table.EnsureVisible
            )
            
            print(f"[PLAYLIST] ✓ Restored last played track at index {self.last_playlist_index}")
            self.debug_console.log(f"[PLAYLIST] ✓ Last played track highlighted: index {self.last_playlist_index}")
        
        except Exception as e:
            print(f"[PLAYLIST] ⚠️  Error restoring last playlist track: {e}")
    
    def _load_playlist_data_async(self):
        """Załaduj dane playlisty ASYNCHRONICZNIE - wywoływane przez QTimer.singleShot
        To odbywa się 50ms PÓŹNIEJ niż show(), więc okno jest już widoczne dla użytkownika"""
        if self.playlist_window is None:
            self.debug_console.log("[PLAYLIST] ⚠️  Playlist window is None, cannot load data")
            return
        
        try:
            # Wymuś załadowanie i odświeżenie danych playlisty
            if hasattr(self.playlist_window, 'refresh_playlist'):
                self.playlist_window.refresh_playlist(self.playlist_file_path)
                self.debug_console.log(f"[PLAYLIST] ✓ Playlist data refreshed from: {self.playlist_file_path}")
            
            # Ustaw stan sortowania playlisty
            if hasattr(self.playlist_window, 'set_sort_state'):
                self.playlist_window.set_sort_state(self.playlist_sort_state)
                self.debug_console.log(f"[PLAYLIST] ✓ Sort state restored: {self.playlist_sort_state}")
            
            # Przywróć ostatnio grany utwór na playliście
            try:
                self._restore_last_playlist_track()
            except Exception as e:
                self.debug_console.log(f"[PLAYLIST] ⚠️  Could not restore track: {e}")

            # Aktualizuj stan przycisków nawigacji playlisty
            try:
                self.update_ui_state()
            except Exception as e:
                self.debug_console.log(f"[PLAYLIST] ⚠️  Could not update UI state: {e}")

            self.debug_console.log("[PLAYLIST] ✓ Playlist data loaded asynchronously")
            
        except Exception as e:
            self.debug_console.log(f"[PLAYLIST] ✗ Error loading playlist data asynchronously: {e}")

    def keyPressEvent(self, event):
        """Obsługa skrótów klawiszowych - CTRL+X pokazuje/ukrywa konsolę, CTRL+L otwiera/zamyka playlistę"""
        try:
            if event.key() == Qt.Key_X and event.modifiers() == Qt.ControlModifier:
                self.toggle_console_visibility()
                return  # Important: prevent event propagation
            elif event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
                # Toggle playlist button (which will trigger toggle_playlist_visibility via toggled signal)
                self.playlist_button.setChecked(not self.playlist_button.isChecked())
            elif event.key() == Qt.Key_P and event.modifiers() == Qt.NoModifier:
                # P: Toggle pause/play
                if self.is_playing:
                    self.pause_playing()
                    self.debug_console.log("[HOTKEY] P: Pause/Play toggled")
                elif self.sid_file:
                    self.start_playing()
                    self.debug_console.log("[HOTKEY] P: Playing started")
            elif event.key() == Qt.Key_B:
                # B: Next song
                self.next_song()
                self.debug_console.log("[HOTKEY] B: Next song")
            elif event.key() == Qt.Key_V:
                # V: Previous song
                self.prev_song()
                self.debug_console.log("[HOTKEY] V: Previous song")
            elif event.key() == Qt.Key_L and event.modifiers() == Qt.NoModifier:
                # L: Loop on/off
                self.loop_enabled = not self.loop_enabled
                if self.loop_enabled:
                    self.loop_checkbox.setText("Loop Song ✓")
                else:
                    self.loop_checkbox.setText("Loop Song")
                # Restart playback if currently playing to apply loop setting
                if self.is_playing:
                    self.stop_sid_file()
                    self.start_playing()
                self.debug_console.log(f"[HOTKEY] L: Loop toggled - {self.loop_enabled}")
            elif event.key() == Qt.Key_Up:
                print(f"[KEY_DEBUG] UP ARROW detected")
                self.send_input_to_sidplay("\x1bOA")  # VT100 format
            elif event.key() == Qt.Key_Down:
                print(f"[KEY_DEBUG] DOWN ARROW detected")
                self.send_input_to_sidplay("\x1bOB")  # VT100 format
            elif event.key() == Qt.Key_Left:
                # Previous subtune - zmniejsz numer i wyślij strzałkę
                print(f"[KEY_DEBUG] LEFT ARROW DETECTED: is_playing={self.is_playing}, current_subtune={self.current_subtune}")
                self.debug_console.log("[KEY] LEFT ARROW pressed")
                self.prev_subtune()  # Already sends escape sequence internally if is_playing
            elif event.key() == Qt.Key_Right:
                # Next subtune - zwiększ numer i wyślij strzałkę
                print(f"[KEY_DEBUG] RIGHT ARROW DETECTED: is_playing={self.is_playing}, current_subtune={self.current_subtune}")
                self.debug_console.log("[KEY] RIGHT ARROW pressed")
                self.next_subtune()  # Already sends escape sequence internally if is_playing
            else:
                super().keyPressEvent(event)
        except Exception as e:
            # Log exception to error file and prevent app crash
            error_message = f"[ERROR] keyPressEvent exception: {type(e).__name__}: {str(e)}"
            print(error_message)
            self._log_error_to_file(error_message)

    def toggle_console_visibility(self):
        """Przełącz widoczność debug consoli - z obsługą wyjątków"""
        try:
            if self.debug_console.isVisible():
                self.debug_console.hide()
                print("[INFO] Debug console: HIDDEN (CTRL+X)")
            else:
                self.debug_console.show()
                print("[INFO] Debug console: VISIBLE (CTRL+X)")
        except Exception as e:
            # Log exception to error file and console
            error_message = f"[ERROR] toggle_console_visibility exception: {type(e).__name__}: {str(e)}"
            print(error_message, file=sys.stderr)
            self._log_error_to_file(error_message)
    
    def _log_error_to_file(self, error_message):
        """Zaloguj błąd do pliku sidplayer_error.txt"""
        try:
            error_file_path = os.path.join(self.base_dir, "sidplayer_error.txt")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(error_file_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {error_message}\n")
        except Exception as log_error:
            print(f"[CRITICAL] Failed to log error: {log_error}", file=sys.stderr)

    def send_input_to_sidplay(self, data):
        try:
            print(f"[SEND_DEBUG] send_input_to_sidplay called with: {repr(data)}")
            print(f"[SEND_DEBUG] self.process={self.process}, stdin={self.process.stdin if self.process else 'N/A'}")
            if self.process is None:
                print(f"[SEND_DEBUG] ERROR: self.process is None!")
                return
            if self.process.stdin is None:
                print(f"[SEND_DEBUG] ERROR: self.process.stdin is None!")
                return
            poll_result = self.process.poll()
            print(f"[SEND_DEBUG] process.poll()={poll_result}")
            if poll_result is not None:
                print(f"[SEND_DEBUG] ERROR: Process already terminated with code {poll_result}")
                return
            
            if isinstance(data, str):
                self.process.stdin.write(data)
            else:
                self.process.stdin.write(data.decode('utf-8'))
            self.process.stdin.flush()
            print(f"[SEND_DEBUG] ✓ Successfully sent: {repr(data)}")
            self.debug_console.log(f"[DEBUG] Sent to stdin: {repr(data)}")
        except Exception as e:
            print(f"[SEND_DEBUG] EXCEPTION: {e}")
            self.debug_console.log(f"[ERROR] send_input_to_sidplay failed: {e}")

    # UI methods (apply_modern_theme, init_ui) are now in UIThemeMixin
    # They are automatically available through inheritance
        
        print(f"[THEME-APPLY] Colors: dark={bg_dark}, mid={bg_mid}, light={bg_light}")
        
        # Aplikuj gradient BEZPOŚREDNIO w CSS (nie przez paletę!)
        self.setStyleSheet(f"""
        #SIDPlayerRoot {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgb{bg_dark},
                stop:0.5 rgb{bg_mid},
                stop:1 rgb{bg_light});
        }}
        QWidget {{
            background: transparent;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            padding: 8px 14px;
            font-size: 10pt;
            font-weight: 500;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton:hover {{ 
            background-color: rgba(255, 255, 255, 0.14);
            border-color: rgba(255, 255, 255, 0.2);
        }}
        QPushButton:pressed {{ 
            background-color: rgba(255, 255, 255, 0.06); 
        }}
        QPushButton:disabled {{
            background-color: rgba(255, 255, 255, 0.03);
            color: rgba({t_r}, {t_g}, {t_b}, 0.3);
            border-color: rgba(255, 255, 255, 0.05);
        }}
        QPushButton#PlayButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border: none;
            color: rgb({t_r}, {t_g}, {t_b});
            font-weight: 600;
        }}
        QPushButton#PauseButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.55);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.65);
            color: rgb({t_r}, {t_g}, {t_b});
            font-weight: 500;
        }}
        QPushButton#PauseButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.65);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.75);
        }}
        QPushButton#PauseButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.45);
        }}
        QPushButton#PauseButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        QPushButton#StopButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#StopButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#StopButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#StopButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        QPushButton#PlayButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.95);
        }}
        QPushButton#PlayButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.75);
        }}
        QPushButton#PlayButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.3);
            color: rgba({t_r}, {t_g}, {t_b}, 0.4);
        }}

        QProgressBar {{
            border: none;
            border-radius: 3px;
            background-color: rgba(255, 255, 255, 0.08);
            height: 6px;
        }}
        QProgressBar::chunk {{
            background-color: rgb({a_r}, {a_g}, {a_b});
            border-radius: 3px;
        }}
        QLabel {{
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QCheckBox {{
            color: rgb({t_r}, {t_g}, {t_b});
            spacing: 8px;
        }}
        /* Loop checkbox: no background under control/text */
        QCheckBox#LoopCheckbox {{
            background-color: transparent;
            border: none;
            padding: 0px;
        }}
        QCheckBox#LoopCheckbox:hover {{
            background-color: transparent;
            border: none;
        }}
        QCheckBox#LoopCheckbox:pressed {{
            background-color: transparent;
            border: none;
        }}
        QCheckBox#LoopCheckbox::indicator:checked {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
        }}
        QCheckBox#LoopCheckbox:disabled {{
            color: rgba({t_r}, {t_g}, {t_b}, {da_chk_text});
            background-color: transparent;
            border: none;
        }}
        QCheckBox#LoopCheckbox::indicator:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_chk_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_chk_border});
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.15);
        }}
        QCheckBox::indicator:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QCheckBox::indicator:checked {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
        }}
        QCheckBox::indicator:checked:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.95);
        }}

        /* Theme button uses accent */
        QPushButton#ThemeButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#ThemeButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#ThemeButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#ThemeButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        /* Playlist button uses accent color like Theme button */
        QPushButton#PlaylistButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#PlaylistButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#PlaylistButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#PlaylistButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        /* Prev/Next Song buttons use accent color like Theme button */
        QPushButton#PrevSongButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#PrevSongButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#PrevSongButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#PrevSongButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        QPushButton#NextSongButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#NextSongButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton#NextSongButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton#NextSongButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        /* Fast Forward button themed baseline (will be overridden by update_button_style) */
        QPushButton#FastForwardButton {{
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton#FastForwardButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        """)

        # Nadpisz style etykiet, aby na pewno reagowały na theme (lokalne QSS)
        self.title_label.setStyleSheet(f"color: rgb({t_r}, {t_g}, {t_b});")
        self.author_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.7);")
        self.year_group_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.7);")
        self.tracker_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.7);")
        self.time_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.95);")
        
        # Style dla kontrolek subtune
        if hasattr(self, 'subtune_label'):
            self.subtune_label.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.7);")
            self.subtune_number.setStyleSheet(f"color: rgba({t_r}, {t_g}, {t_b}, 0.95);")
            
            # Style dla przycisków subtune
            subtune_button_style = f"""
            QPushButton {{
                background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
                border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.4);
                border-radius: 5px;  /* Zmniejszone zaokrąglenie rogów */
                color: rgb({t_r}, {t_g}, {t_b});
                font-weight: bold;
                padding: 0px;
                font-size: 20pt;  /* Większa czcionka w CSS */
                line-height: 1;   /* Lepsze wycentrowanie pionowe */
                text-align: center; /* Wycentrowanie poziome */
            }}
            QPushButton:hover {{
                background-color: rgba({a_r}, {a_g}, {a_b}, 0.3);
                border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.6);
            }}
            QPushButton:pressed {{
                background-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
            }}
            """
            # Apply subtune button style only to subtune arrow buttons
            print(f"[SUBTUNE-STYLE] Applying style to prev_subtune_button, enabled={self.prev_subtune_button.isEnabled()}")
            print(f"[SUBTUNE-STYLE] Applying style to next_subtune_button, enabled={self.next_subtune_button.isEnabled()}")
            self.prev_subtune_button.setStyleSheet(subtune_button_style)
            self.next_subtune_button.setStyleSheet(subtune_button_style)
            print(f"[SUBTUNE-STYLE] ✓ Styles applied successfully")
            # prev_song_button and next_song_button use default button styling

        # Odśwież style progress_bar i loop_checkbox bezpośrednio (force update)
        progress_stylesheet = f"""
        QProgressBar {{
            border: none;
            border-radius: 3px;
            background-color: rgba(255, 255, 255, 0.08);
            height: 6px;
        }}
        QProgressBar::chunk {{
            background-color: rgb({a_r}, {a_g}, {a_b});
            border-radius: 3px;
        }}
        """
        self.progress_bar.setStyleSheet(progress_stylesheet)
        
        loop_stylesheet = f"""
        QCheckBox {{
            color: rgb({t_r}, {t_g}, {t_b});
            spacing: 8px;
            background-color: transparent;
            border: none;
            padding: 0px;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.15);
        }}
        QCheckBox::indicator:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QCheckBox::indicator:checked {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
        }}
        """
        self.loop_checkbox.setStyleSheet(loop_stylesheet)
        
        # Bezpośrednio ustaw stylesheets dla main buttons
        play_button_style = f"""
        QPushButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.85);
            border: none;
            border-radius: 20px;
            padding: 8px 14px;
            font-size: 10pt;
            font-weight: 600;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.95);
        }}
        QPushButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.75);
        }}
        QPushButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        """
        self.play_button.setStyleSheet(play_button_style)
        
        pause_button_style = f"""
        QPushButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.55);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.65);
            border-radius: 20px;
            padding: 8px 14px;
            font-size: 10pt;
            font-weight: 500;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.65);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.75);
        }}
        QPushButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.45);
        }}
        QPushButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        """
        self.pause_button.setStyleSheet(pause_button_style)
        
        stop_button_style = f"""
        QPushButton {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.25);
            border: 1px solid rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-radius: 20px;
            padding: 8px 14px;
            font-size: 10pt;
            font-weight: 500;
            color: rgb({t_r}, {t_g}, {t_b});
        }}
        QPushButton:hover {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.35);
            border-color: rgba({a_r}, {a_g}, {a_b}, 0.5);
        }}
        QPushButton:pressed {{
            background-color: rgba({a_r}, {a_g}, {a_b}, 0.2);
        }}
        QPushButton:disabled {{
            background-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_bg});
            border-color: rgba({a_r}, {a_g}, {a_b}, {da_btn_border});
            color: rgba({t_r}, {t_g}, {t_b}, {da_btn_text});
        }}
        """
        self.stop_button.setStyleSheet(stop_button_style)
        
        # Force refresh UI elements to apply new theme
        self.progress_bar.style().unpolish(self.progress_bar)
        self.progress_bar.style().polish(self.progress_bar)
        self.loop_checkbox.style().unpolish(self.loop_checkbox)
        self.loop_checkbox.style().polish(self.loop_checkbox)
        
        # Force refresh main buttons
        for btn in [self.play_button, self.pause_button, self.stop_button]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        
        # Force refresh root widget and whole tree
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        
        # Odśwież styl przycisku Fast Forward po zmianie motywu
        self.update_button_style()
    # SID info methods moved to sid_info_manager.py (Phase 4 refactoring)
    # load_song_lengths(), calculate_sid_md5(), get_song_duration()
    
    # ----------------------------------------------
    #           DRAG & DROP + METADANE
    # ----------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        try:
            files = [u.toLocalFile() for u in event.mimeData().urls()]
            if files:
                sid_path = files[0]
                if sid_path.lower().endswith(".sid"):
                    self.stop_sid_file()
                    self.sid_file = sid_path
                    self.current_subtune = self.default_subtune  # Reset to default for new file
                    self.save_settings()  # Zapisz ostatnio odtwarzany plik
                    filename = os.path.basename(sid_path)
                    self.status_label.setText("LOADED")
                    self.read_metadata(sid_path)
                    # Pobierz duration dla aktualnego subtune
                    self.current_song_duration = self.get_song_duration(sid_path, self.current_subtune)
                    self.total_duration = self.current_song_duration
                    self.update_time_label()
                    self.update_ui_state()
                    self.start_playing()
                else:
                    QMessageBox.warning(self, "Invalid File", "Proszę przeciągnąć plik .SID.")
        except Exception as e:
            QMessageBox.critical(self, "Drop Error", str(e))

    # ----------------------------------------------
    #              PLAYBACK
    # ----------------------------------------------
    def toggle_loop(self, state):
        """Toggle loop mode."""
        self.loop_enabled = (state == Qt.Checked)
        print(f"[INFO] Loop mode: {'enabled' if self.loop_enabled else 'disabled'}")
        self.debug_console.log(f"[LOOP] Loop checkbox changed! is_playing={self.is_playing}")  # LOG ZMIAN
        # Uaktualnij tekst z symbolem check dla lepszej czytelności
        if self.loop_enabled:
            self.loop_checkbox.setText("Loop Song ✓")
        else:
            self.loop_checkbox.setText("Loop Song")
        
        # Restart playback if currently playing to apply loop setting
        if self.is_playing:
            self.debug_console.log("[LOOP] Restarting playback due to loop change...")  # LOG RESTARTU
            self.stop_sid_file()
            self.start_playing()
    
    def toggle_default_tune_only(self, state):
        """Toggle default tune only mode (ignore subtune navigation)."""
        self.default_tune_only = (state == Qt.Checked)
        mode = "DEFAULT TUNE ONLY" if self.default_tune_only else "ALL SUBTUNES"
        print(f"[INFO] Subtune mode: {mode}")
        self.debug_console.log(f"[SUBTUNE] Subtune mode changed to: {mode}")
        
        # Uaktualnij tekst z symbolem check dla lepszej czytelności
        if self.default_tune_only:
            self.default_tune_only_checkbox.setText("Default tune only ✓")
        else:
            self.default_tune_only_checkbox.setText("Default tune only")
        
        # Jeśli jest włączony i aktualnie gramy, resetuj do default subtune
        if self.is_playing and self.default_tune_only:
            if self.current_subtune != self.default_subtune:
                self.debug_console.log(f"[SUBTUNE] Resetting to default subtune {self.default_subtune}")
                self.current_subtune = self.default_subtune
                self.update_ui_state()
                # Restart playback to apply subtune change
                self.stop_sid_file()
                self.start_playing()
            
    def _on_prev_subtune_clicked(self):
        """Wrapper function to log button click"""
        print(f"[BUTTON_CLICK] ◄ LEFT ARROW BUTTON CLICKED! Button enabled={self.prev_subtune_button.isEnabled()}")
        self.prev_subtune()
    
    def _on_next_subtune_clicked(self):
        """Wrapper function to log button click"""
        print(f"[BUTTON_CLICK] ► RIGHT ARROW BUTTON CLICKED! Button enabled={self.next_subtune_button.isEnabled()}")
        self.next_subtune()



    def toggle_speed(self):
        """Toggle between normal speed (1x) and fast forward (8x)"""
        if self.is_playing:
            # Jeśli aktualnie gra na 1x → przejdź na 8x
            if self.playback_speed_multiplier == 1:
                self.debug_console.log(f"[SPEED] 🚀 Toggling speed: 1x → 8x (Fast Forward)")
                
                # Dla jsidplay2, wysłanie '.' 3x = 1x → 2x → 4x → 8x
                if self.audio_engine == "jsidplay2":
                    speed_success = False
                    
                    # LEVEL 1: Spróbuj wysłać '.' 3x przez STDIN
                    if self.process and self.process.stdin:
                        try:
                            self.debug_console.log("[SPEED] 📋 Level 1: Attempting stdin input (3× '.' for 8x speed)...")
                            # Wysyłaj '.' 3 razy: 1x → 2x → 4x → 8x
                            for i in range(3):
                                self.process.stdin.write(".\n")
                                self.process.stdin.flush()
                                time.sleep(0.05)  # Mały delay między poleceniami
                            self.debug_console.log("[SPEED] ✓ 3× '.' commands sent via stdin - jsidplay2 should now be at 8x")
                            speed_success = True
                        except Exception as e:
                            self.debug_console.log(f"[SPEED] ✗ stdin write failed: {e}")
                    
                    # LEVEL 2: Jeśli stdin nie zadziałał, spróbuj PostMessage API
                    if not speed_success:
                        self.debug_console.log("[SPEED] 📋 Level 2: Attempting PostMessage API (3× '.')...")
                        success = True
                        try:
                            for i in range(3):
                                success = self.send_char_sequence_to_console(['.']) and success
                                time.sleep(0.05)
                        except Exception as e:
                            success = False
                        
                        if success:
                            self.debug_console.log("[SPEED] ✓ 3× '.' keys sent via PostMessage")
                        else:
                            self.debug_console.log("[SPEED] ✗ PostMessage failed - window not found")
                else:
                    # Dla sidplayfp, wysyłaj UP arrows
                    target_state = 3  # 3 = 8x (1x → 2x → 4x → 8x)
                    
                    # Wyślij UP arrows jeśli poniżej 8x
                    if self.arrow_key_net_count < target_state:
                        arrows_to_send = target_state - self.arrow_key_net_count
                        arrow_sequence = "\x1b[A" * arrows_to_send
                        
                        if sys.platform == "win32":
                            for _ in range(arrows_to_send):
                                self.simulate_arrow_key(is_up_arrow=True)
                        else:
                            self.send_input_to_sidplay(arrow_sequence)
                        
                        self.arrow_key_net_count = target_state
                        self.debug_console.log(f"[SPEED] ⬆ Toggle Speed → 8x (sent {arrows_to_send} UP arrows)")
                
                # Update status and button color (dla obu silników)
                self.playback_speed_multiplier = 8
                self.update_status_label()
                self.update_button_style()
            
            # Jeśli aktualnie gra na 8x → przejdź na 1x
            else:
                self.debug_console.log(f"[SPEED] 🔽 Toggling speed: 8x → 1x (Normal Speed)")
                
                # Dla jsidplay2, wysłanie ',' = zmniejsz prędkość
                if self.audio_engine == "jsidplay2":
                    speed_success = False
                    
                    # LEVEL 1: Spróbuj wysłać ',' przez STDIN aby wrócić do 1x
                    if self.process and self.process.stdin:
                        try:
                            self.debug_console.log("[SPEED] 📋 Level 1: Attempting stdin input (',' for 1x speed)...")
                            self.process.stdin.write(",\n")
                            self.process.stdin.flush()
                            self.debug_console.log("[SPEED] ✓ ',' command sent via stdin - jsidplay2 should now be at 1x")
                            speed_success = True
                        except Exception as e:
                            self.debug_console.log(f"[SPEED] ✗ stdin write failed: {e}")
                    
                    # LEVEL 2: Jeśli stdin nie zadziałał, spróbuj PostMessage API
                    if not speed_success:
                        self.debug_console.log("[SPEED] 📋 Level 2: Attempting PostMessage API (',')...")
                        success = self.send_char_sequence_to_console([','])
                        
                        if success:
                            self.debug_console.log("[SPEED] ✓ ',' key sent via PostMessage")
                        else:
                            self.debug_console.log("[SPEED] ✗ PostMessage failed - window not found")
                else:
                    # Dla sidplayfp, wysyłaj DOWN arrows
                    target_state = 0  # 0 = 1x
                    
                    # Wyślij DOWN arrows jeśli powyżej 1x
                    if self.arrow_key_net_count > target_state:
                        arrows_to_send = self.arrow_key_net_count - target_state
                        arrow_sequence = "\x1b[B" * arrows_to_send
                        
                        if sys.platform == "win32":
                            for _ in range(arrows_to_send):
                                self.simulate_arrow_key(is_up_arrow=False)
                        else:
                            self.send_input_to_sidplay(arrow_sequence)
                        
                        self.arrow_key_net_count = target_state
                        self.debug_console.log(f"[SPEED] ⬇ Toggle Speed → 1x (sent {arrows_to_send} DOWN arrows)")
                
                # Update status and button color (dla obu silników)
                self.playback_speed_multiplier = 1
                self.update_status_label()
                self.update_button_style()

    def update_status_label(self):
        """Update status label based on playback state"""
        # Styl bazowy z kolorem z motywu
        if hasattr(self, '_theme_text_rgb'):
            r, g, b = self._theme_text_rgb
            self.status_label.setStyleSheet(f"color: rgba({r}, {g}, {b}, 0.6); letter-spacing: 2px; padding: 8px;")
        else:
            self.status_label.setStyleSheet("color: rgba(180, 200, 216, 0.6); letter-spacing: 2px; padding: 8px;")
        
        if self.is_playing:
            # Playing state
            if self.playback_speed_multiplier == 8:
                self.status_label.setText("FAST FORWARD")
            else:
                self.status_label.setText("PLAYING")
        else:
            # Stopped/Ready state
            if self.sid_file:
                self.status_label.setText("STOPPED")
            else:
                self.status_label.setText("READY")
    
    def update_button_style(self):
        """Update Fast Forward button color based on speed state"""
        if hasattr(self, '_theme_accent_rgb') and hasattr(self, '_theme_text_rgb'):
            ar, ag, ab = self._theme_accent_rgb
            tr, tg, tb = self._theme_text_rgb
        else:
            ar, ag, ab = (70, 110, 140)
            tr, tg, tb = (180, 200, 216)

        # Ujednolicone właściwości dekoracyjne jak STOP; kolor i tekst z motywu.
        if self.playback_speed_multiplier == 8:
            self.fast_forward_button.setStyleSheet(
                f"QPushButton {{ background-color: rgba({ar}, {ag}, {ab}, 0.35); border: 1px solid rgba({ar}, {ag}, {ab}, 0.5); border-radius: 20px; padding: 8px 14px; font-size: 10pt; font-weight: 500; color: rgb({tr}, {tg}, {tb}); }}\nQPushButton:hover {{ background-color: rgba({ar}, {ag}, {ab}, 0.45); border-color: rgba({ar}, {ag}, {ab}, 0.6); }}\nQPushButton:pressed {{ background-color: rgba({ar}, {ag}, {ab}, 0.25); }}"
            )
        else:
            self.fast_forward_button.setStyleSheet(
                f"QPushButton {{ background-color: rgba({ar}, {ag}, {ab}, 0.25); border: 1px solid rgba({ar}, {ag}, {ab}, 0.35); border-radius: 20px; padding: 8px 14px; font-size: 10pt; font-weight: 500; color: rgb({tr}, {tg}, {tb}); }}\nQPushButton:hover {{ background-color: rgba({ar}, {ag}, {ab}, 0.35); border-color: rgba({ar}, {ag}, {ab}, 0.5); }}\nQPushButton:pressed {{ background-color: rgba({ar}, {ag}, {ab}, 0.2); }}"
            )

    def seek_to_time(self, target_time):
        """
        Auto-seek do wskazanego czasu przy użyciu fast forward (16x speed)
        Rozmiar bloku: 8 sekund
        """
        if not self.is_playing:
            self.debug_console.log("[SEEK] ❌ Nie można seek'ować - muzykę nie gra")
            return
        
        if self.is_seeking:
            self.debug_console.log("[SEEK] ⏳ Seek już w trakcie - poczekaj aż się skończy")
            return
        
        time_diff = target_time - self.time_elapsed
        
        # Jeśli jdziemy do tyłu - nie obsługujemy (sidplayfp nie pozwala)
        if time_diff < -1:  # -1 tolerancja
            self.debug_console.log(f"[SEEK] ⚠️ Nie można wrócić do tyłu ({self.time_elapsed}s → {target_time}s)")
            self.debug_console.log("[SEEK] Zatrzymuję muzykę - zagrywam od nowa")
            # Opcja: zatrzymaj i zagrywaj od nowa (zakomentowałem, może to zbyt inwazyjne)
            # self.stop_sid_file()
            # self.start_playing()
            return
        
        # Jeśli już jesteśmy blisko celu - nic nie rób
        if abs(time_diff) <= 1:
            self.debug_console.log(f"[SEEK] ✓ Już blisko celu ({self.time_elapsed}s ≈ {target_time}s)")
            return
        
        self.is_seeking = True
        self.seek_target_time = target_time
        
        # Oblicz liczbę bloków 8s do przeskoczenia
        blocks_to_skip = max(1, int(time_diff / self.seek_block_size))
        blocks_distance = blocks_to_skip * self.seek_block_size
        
        self.debug_console.log(f"[SEEK] 🎯 Inicjowanie seek: {self.time_elapsed}s → {target_time}s")
        self.debug_console.log(f"[SEEK] Dystans: {time_diff:.1f}s = {blocks_to_skip} bloków × {self.seek_block_size}s")
        
        # Uruchom seek w osobnym threadu aby nie zablokować UI
        seek_thread = threading.Thread(target=self._perform_seek, args=(blocks_to_skip,))
        seek_thread.daemon = True
        seek_thread.start()

    def _perform_seek(self, blocks_to_skip):
        """
        Wewnętrzna funkcja seek - uruchamiana w daemon thread
        Przyspieszą grę i czeka na osiągnięcie celu
        """
        try:
            # Przyspiesz na 8x (3 UP arrows)
            self._set_playback_speed_to_8x()
            time.sleep(0.5)  # Krótka przerwa żeby przyspieszenie się ustabilizowało
            
            # Czekaj na osiągnięcie docelowego czasu
            # Każdy blok trwa ~1s przy 8x prędkości (8s / 8 = 1s realnego czasu)
            estimated_seek_time = (blocks_to_skip * self.seek_block_size) / 8
            
            self.debug_console.log(f"[SEEK] ⚡ Przyspieszam na 8x - szacunkowy czas seek: {estimated_seek_time:.1f}s")
            
            # Czekaj z monitoringiem
            wait_iterations = int(estimated_seek_time * 2)  # Sprawdzaj 2x na sekundę
            for i in range(wait_iterations):
                if self.time_elapsed >= self.seek_target_time:
                    self.debug_console.log(f"[SEEK] ✓ Cel osiągnięty! Aktualny czas: {self.time_elapsed}s")
                    break
                time.sleep(0.5)
            
            # Wróć na normalną prędkość (1x)
            self._set_playback_speed_to_1x()
            time.sleep(0.3)
            
            self.debug_console.log(f"[SEEK] ✓ Seek zakończony! Czas: {self.time_elapsed}s / {self.total_duration}s")
            
        except Exception as e:
            self.debug_console.log(f"[SEEK] ❌ Błąd podczas seek: {e}")
        finally:
            self.is_seeking = False

    def _set_playback_speed_to_8x(self):
        """Helper: Ustaw prędkość na 8x (3 UP arrows)"""
        if self.arrow_key_net_count < 3:
            arrows_to_send = 3 - self.arrow_key_net_count
            arrow_sequence = "\x1b[A" * arrows_to_send
            
            if sys.platform == "win32":
                for _ in range(arrows_to_send):
                    self.simulate_arrow_key(is_up_arrow=True)
                    time.sleep(0.1)
            else:
                self.send_input_to_sidplay(arrow_sequence)
            
            self.arrow_key_net_count = 3
            self.playback_speed_multiplier = 8
            self.debug_console.log(f"[SEEK-SPEED] ⬆ Przyspieszam → 8x (wysłano {arrows_to_send} UP arrows)")

    def _set_playback_speed_to_1x(self):
        """Helper: Ustaw prędkość na 1x (resetuj arrow keys)"""
        if self.arrow_key_net_count > 0:
            arrows_to_send = self.arrow_key_net_count
            arrow_sequence = "\x1b[B" * arrows_to_send
            
            if sys.platform == "win32":
                for _ in range(arrows_to_send):
                    self.simulate_arrow_key(is_up_arrow=False)
                    time.sleep(0.1)
            else:
                self.send_input_to_sidplay(arrow_sequence)
            
            self.arrow_key_net_count = 0
            self.playback_speed_multiplier = 1
            self.debug_console.log(f"[SEEK-SPEED] ⬇ Wracam do 1x (wysłano {arrows_to_send} DOWN arrows)")

    def closeEvent(self, event):
        """Obsługa zamknięcia okna - wywołaj cleanup_on_exit()"""
        print("[CLOSE_EVENT] Window close detected - calling cleanup_on_exit()")
        self.cleanup_on_exit()
        event.accept()

    def cleanup_on_exit(self):
        """Ostateczne czyszczenie przy wyjściu aplikacji
        
        Strategia:
        1. Zagraj mutesid.sid (wszystkie instrumenty mają volume=0)
        2. To wycisza całe urządzenie
        3. Czekaj krótko na załadowanie
        4. Potem spokojnie zamknij procesy
        
        Gwarancja: Wywoływana tylko raz (idempotentna)
        """
        # WAŻNE: cleanup_on_exit() może być wywoływana wielokrotnie (closeEvent i aboutToQuit)
        # Zrób to tylko raz!
        if self._cleanup_done:
            print("[EXIT] ⚠️  cleanup_on_exit() called again - already done, skipping")
            return
        
        self._cleanup_done = True
        print("[EXIT] ===== CLEANUP_ON_EXIT STARTED =====")
        
        # Otwórz log file
        log_file = os.path.join(self.base_dir, "exit_debug.log")
        with open(log_file, "w") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ===== CLEANUP ON EXIT START =====\n")
            f.write(f"Current process: {self.process}\n")
            f.write(f"Is playing: {self.is_playing}\n")
            f.write(f"Sid file: {self.sid_file}\n")
            f.flush()
        
        def log(msg):
            print(msg)
            with open(log_file, "a") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
                f.flush()
        
        self.save_settings()  # Zapisz ostatnio odtwarzany plik
        self._save_playlist_on_exit()  # Zapisz playlistę
        log("[EXIT] ✓ Settings and playlist saved")
        
        # Close any open windows (BEFORE audio shutdown, so they don't block exit)
        log("[EXIT] Closing open windows...")
        if self.playlist_window:
            try:
                self.playlist_window.close()
                log("[EXIT] ✓ Playlist window closed")
            except Exception as e:
                log(f"[EXIT] ⚠️  Error closing playlist window: {e}")
        
        if self.theme_window:
            try:
                self.theme_window.close()
                log("[EXIT] ✓ Theme window closed")
            except Exception as e:
                log(f"[EXIT] ⚠️  Error closing theme window: {e}")
        
        # FAZA 2: Graceful shutdown using USB SID Pico menu sequence
        log("[EXIT] FAZA 2: Graceful shutdown of audio engine...")
        if self.audio_engine == "jsidplay2":
            # Use proper USB SID Pico shutdown sequence: 1, 2, 3, q
            success = self.graceful_shutdown_jsidplay2()
            log(f"[EXIT] ✓ FAZA 2: JSidplay2 shutdown {'successful' if success else 'attempted'}")
        else:
            # For sidplayfp, use standard stop
            self.stop_sid_file()
            log("[EXIT] ✓ FAZA 2: sidplayfp stopped")
        
        # FAZA 4: Final cleanup - wait for process to close gracefully, then hard kill if needed
        log(f"[EXIT] FAZA 4: Final check - process={self.process}")
        if self.process:
            try:
                # Give process 2 seconds to close gracefully after shutdown sequence
                log(f"[EXIT] Waiting for process PID={self.process.pid} to close gracefully...")
                try:
                    self.process.wait(timeout=2)
                    log("[EXIT] ✓ Process closed gracefully")
                except subprocess.TimeoutExpired:
                    # Process didn't close - force kill
                    log(f"[EXIT] ⚠️  Process did not close after 2 seconds - force killing PID={self.process.pid}")
                    self.process.kill()
                    log("[EXIT] ✓ Process force-killed")
            except Exception as e:
                log(f"[EXIT] ⚠️  Error during final cleanup: {e}")
        
        log("[EXIT] ✓✓✓ CLEANUP COMPLETE ✓✓✓")
        log(f"[EXIT] Log saved to: {log_file}")

    # ----------------------------------------------
    #               CZAS + METADANE
    # ----------------------------------------------


    def _check_playlist_available_from_file(self):
        """Check if playlist file exists and has more than 1 entry"""
        return FileManager.check_playlist_available(self.playlist_file_path)

    def update_ui_state(self):
        is_loaded = self.sid_file is not None
        print(f"[UPDATE_UI] update_ui_state() called: is_loaded={is_loaded}, is_playing={self.is_playing}, current_subtune={self.current_subtune}, num_subtunes={self.num_subtunes}")
        self.play_button.setEnabled(is_loaded and not self.is_playing)
        self.pause_button.setEnabled(self.is_playing)
        self.stop_button.setEnabled(self.is_playing)
        self.fast_forward_button.setEnabled(self.is_playing)

        # === UPDATE SUBTUNE NUMBER DISPLAY ===
        # This ensures the subtune number updates during auto-advance
        if hasattr(self, 'subtune_number'):
            self.subtune_number.setText(str(self.current_subtune))
            self.debug_console.log(f"[UI_STATE] ✓ Subtune display updated: {self.current_subtune}/{self.num_subtunes}")

        # Update subtune controls
        if hasattr(self, 'prev_subtune_button') and hasattr(self, 'next_subtune_button'):
            # Block if "default tune only" mode is enabled
            if self.default_tune_only:
                prev_enabled = False
                next_enabled = False
            else:
                # Enable prev only if: file loaded AND has multiple subtunes AND not at first subtune
                prev_enabled = is_loaded and self.num_subtunes > 1 and self.current_subtune > 1
                # Enable next only if: file loaded AND has multiple subtunes AND not at last subtune
                next_enabled = is_loaded and self.num_subtunes > 1 and self.current_subtune < self.num_subtunes
            print(f"[BUTTON_STATE] prev_subtune_button: enabled={prev_enabled}, is_loaded={is_loaded}, num_subtunes={self.num_subtunes}, current_subtune={self.current_subtune}, has_multi={self.num_subtunes > 1}, default_tune_only={self.default_tune_only}")
            print(f"[BUTTON_STATE] next_subtune_button: enabled={next_enabled}, is_loaded={is_loaded}, num_subtunes={self.num_subtunes}, current_subtune={self.current_subtune}, has_multi={self.num_subtunes > 1}, default_tune_only={self.default_tune_only}")
            self.prev_subtune_button.setEnabled(prev_enabled)
            self.next_subtune_button.setEnabled(next_enabled)

        # Update playlist navigation controls
        if hasattr(self, 'prev_song_button') and hasattr(self, 'next_song_button'):
            playlist_available = (self.playlist_window is not None and
                                hasattr(self.playlist_window, 'playlist_manager') and
                                len(self.playlist_window.playlist_manager.entries) > 1)
            # Also enable if playlist file exists and has entries (even if window not open)
            if not playlist_available:
                playlist_available = self._check_playlist_available_from_file()
            self.prev_song_button.setEnabled(playlist_available)
            self.next_song_button.setEnabled(playlist_available)

    # SID info methods moved to sid_info_manager.py (Phase 4 refactoring)
    # Including: get_song_length_from_database(), read_metadata()
    
    # ----------------------------------------------
    #           PLAYLIST MANAGEMENT
    # ----------------------------------------------
    
    def toggle_playlist_visibility(self, checked):
        """Toggle playlist window visibility - główna metoda obsługująca przycisk PLAYLIST
        checked: True = pokazać okno, False = ukryć okno (sygnał z toggled przycisku)"""
        
        if not PLAYLIST_AVAILABLE:
            QMessageBox.warning(self, "Playlist Not Available",
                              "PlaylistWidget module is not available.\n"
                              "Please ensure playlist_widget.py is in the sidplayer directory.")
            self.playlist_button.setChecked(False)  # Wyłącz przycisk jeśli błąd
            return
        
        if checked:
            # SHOW WINDOW
            self.open_playlist(show_window=True)
        else:
            # HIDE WINDOW
            if self.playlist_window is not None and self.playlist_window.isVisible():
                self.playlist_window.hide()
                self.debug_console.log("[PLAYLIST] ✓ Playlist window hidden")
    
    def _on_playlist_window_close(self, event):
        """Obsługa zamknięcia okna playlisty (event handler dla closeEvent)
        Synchronizuje stan przycisku ze stanem okna"""
        try:
            # Jeśli przycisk jest zaznaczony (checked), wyłącz go
            if self.playlist_button.isChecked():
                # Blokuj sygnały aby uniknąć nieskończonej rekurencji
                self.playlist_button.blockSignals(True)
                self.playlist_button.setChecked(False)
                self.playlist_button.blockSignals(False)
            
            self.debug_console.log("[PLAYLIST] ✓ Playlist window closed by user, button state synced")
        except Exception as e:
            self.debug_console.log(f"[PLAYLIST] ⚠️  Error in close event handler: {e}")
        
        event.accept()
    
    def open_playlist(self, show_window=True):
        """Otwórz okno managera playlisty"""
        if not PLAYLIST_AVAILABLE:
            QMessageBox.warning(self, "Playlist Not Available",
                              "PlaylistWidget module is not available.\n"
                              "Please ensure playlist_widget.py is in the sidplayer directory.")
            return
        
        try:
            # Jeśli okno już istnieje, po prostu je pokaż
            if self.playlist_window is not None:
                if not self.playlist_window.isVisible():
                    self.playlist_window.show()
                self.playlist_window.raise_()  # Przynieś na front
                self.playlist_window.activateWindow()  # Aktywuj
                self.debug_console.log("[PLAYLIST] ✓ Playlist window shown/brought to front")
                return
            
            # Stwórz nowe okno playlisty z theme settings
            self.playlist_window = PlaylistWidget(
                parent=None, 
                songlengths_path=self.songlengths_path,
                theme_settings=self.theme_settings
            )
            
            # Podłącz sygnały
            self.playlist_window.song_double_clicked.connect(self.play_song_from_playlist)
            self.song_started_signal.connect(self.playlist_window.set_current_playing_from_filepath)  # Cursor Follows Playback
            self.playlist_window.destroyed.connect(self.on_playlist_window_closed)
            
            # 🔴 WAŻNE: Podłączamy closeEvent okna do synchronizacji stanu przycisku
            # Gdy użytkownik zamknie okno krzyżykiem, przycisk się wyłączy (uncheck)
            self.playlist_window.closeEvent = lambda event: self._on_playlist_window_close(event)
            
            # Ustaw rozmiar i pozycję - KOMPAKTNA PLAYLIST
            from PyQt5.QtCore import QRect
            screen = QApplication.primaryScreen().geometry()
            self.playlist_window.setGeometry(
                int(screen.width() * 0.2),   # X pozycja
                int(screen.height() * 0.15), # Y pozycja
                720,  # Szerokość: 600 pikseli (zmiana z 60% -> fixed)
                680   # Wysokość: 450 pikseli (zmiana z 50% -> fixed)
            )
            
            # POKAŻ OKNO NATYCHMIAST (zanim załadujemy dane!)
            if show_window:
                self.playlist_window.show()
                self.playlist_window.raise_()  # Przynieś na front
                self.playlist_window.activateWindow()  # Aktywuj
                self.debug_console.log("[PLAYLIST] ✓ Playlist window made visible (step 1)")
                
                # ⭐ WAŻNE: Zaplanuj ładowanie danych ASYNCHRONICZNIE w Qt event loop
                # To uniemożliwia blokowanie pokazywania okna przez operacje I/O
                # Okno będzie widoczne NATYCHMIAST, a dane załadują się "wkrótce"
                QTimer.singleShot(50, self._load_playlist_data_async)
                return
            
            # Wymuś załadowanie i odświeżenie danych playlisty (tylko jeśli show_window=False)
            if hasattr(self.playlist_window, 'refresh_playlist'):
                self.playlist_window.refresh_playlist(self.playlist_file_path)
                self.debug_console.log(f"[PLAYLIST] ✓ Playlist data refreshed from: {self.playlist_file_path}")
            
            # Ustaw stan sortowania playlisty
            if hasattr(self.playlist_window, 'set_sort_state'):
                self.playlist_window.set_sort_state(self.playlist_sort_state)
                self.debug_console.log(f"[PLAYLIST] ✓ Sort state restored: {self.playlist_sort_state}")
            
            # Przywróć ostatnio grany utwór na playliście
            try:
                self._restore_last_playlist_track()
            except Exception as e:
                self.debug_console.log(f"[PLAYLIST] ⚠️  Could not restore track: {e}")

            # Aktualizuj stan przycisków nawigacji playlisty
            try:
                self.update_ui_state()
            except Exception as e:
                self.debug_console.log(f"[PLAYLIST] ⚠️  Could not update UI state: {e}")

            self.debug_console.log("[PLAYLIST] ✓ Playlist window opened")
            
        except Exception as e:
            self.debug_console.log(f"[PLAYLIST] ✗ Error opening playlist: {e}")
            QMessageBox.critical(self, "Playlist Error", f"Failed to open playlist:\n{e}")
    
    def play_song_from_playlist(self, file_path, duration=None):
        """Obsługa podwójnego kliknięcia na piosenkę w playliście"""
        try:
            if os.path.exists(file_path):
                # Zatrzymaj aktualną piosenkę
                self.stop_sid_file()
                
                # Ustaw nową piosenkę
                self.sid_file = file_path
                self.current_subtune = self.default_subtune  # Reset to default for new file
                self.save_settings()  # Zapisz ostatnio odtwarzany plik
                
                # Załaduj metadane i informacje o piosence
                filename = os.path.basename(file_path)
                self.status_label.setText("LOADED")
                self.read_metadata(file_path)
                
                # Użyj czasu z playlisty, jeśli dostępny; w przeciwnym razie przelicz
                if duration is not None and duration > 0:
                    self.current_song_duration = duration
                    self.debug_console.log(f"[PLAYLIST] ✓ Używam czas z playlisty: {duration}s")
                else:
                    # Fallback: Pobierz duration dla aktualnego subtune
                    self.current_song_duration = self.get_song_duration(file_path, self.current_subtune)
                    self.debug_console.log(f"[PLAYLIST] Fallback - przeliczony czas: {self.current_song_duration}s")
                
                self.total_duration = self.current_song_duration
                self.update_time_label()
                self.update_ui_state()
                
                # Uruchom granie
                self.start_playing()
                self.debug_console.log(f"[PLAYLIST] ▶ Playing: {filename}")
                
                # Emituj sygnał aby playlisty zaktualizowała cursor (Cursor Follows Playback)
                self.song_started_signal.emit(file_path)
            else:
                self.debug_console.log(f"[PLAYLIST] ✗ File not found: {file_path}")
                QMessageBox.warning(self, "File Not Found", f"Could not find: {file_path}")
        except Exception as e:
            self.debug_console.log(f"[PLAYLIST] ✗ Error playing song: {e}")

    def on_playlist_window_closed(self):
        """Obsługa zamknięcia okna playlisty"""
        self.playlist_window = None
        self.update_ui_state()
        self.debug_console.log("[PLAYLIST] Playlist window closed - navigation buttons disabled")

    # ----------------------------------------------
    #           THEME SETTINGS
    # ----------------------------------------------
    def open_theme_settings(self):
        """Otwórz okno ustawień motywu"""
        if self.theme_window is None or not self.theme_window.isVisible():
            self.theme_window = ThemeSettingsWindow(parent=self, initial_settings=self.theme_settings, initial_player=self.audio_engine)
            self.theme_window.theme_changed.connect(self.on_theme_changed)
            self.theme_window.player_engine_changed.connect(self.on_player_engine_changed)
            self.theme_window.show()
            print("[THEME] Theme settings window opened")
        else:
            # Jeśli okno jest już otwarte, przenieś je na wierzch
            self.theme_window.raise_()
            self.theme_window.activateWindow()
    
    def on_theme_changed(self, new_settings):
        """Obsługa zmiany ustawień motywu - live preview"""
        print(f"[THEME-MAIN] ✓ Signal received! New settings: {new_settings}")
        self.theme_settings = new_settings.copy()
        print(f"[THEME-MAIN] Settings updated: {self.theme_settings}")
        
        # Zapisz nowe ustawienia do pliku
        self.save_settings()
        
        # Zastosuj nowy motyw dynamicznie (live preview)
        print("[THEME-MAIN] Calling apply_modern_theme()...")
        self.apply_modern_theme()
        print("[THEME-MAIN] ✓ Theme applied! Check if gradient changed.")
        
        # Zaktualizuj theme playlisty jeśli jest otwarta
        if self.playlist_window is not None and self.playlist_window.isVisible():
            print("[THEME-MAIN] Updating playlist theme...")
            self.playlist_window.set_theme_settings(new_settings)
            print("[THEME-MAIN] ✓ Playlist theme updated!")
    
    def on_player_engine_changed(self, engine_name):
        """Obsługa zmiany wybranego silnika audio"""
        self.debug_console.log(f"[ENGINE] Audio engine changed signal received: {engine_name}")
        self.set_audio_engine(engine_name)
    
    # get_sid_info() moved to sid_info_manager.py (Phase 4 refactoring)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Użyj Fusion style aby lepiej obsługiwać stylesheets (łącznie z corner buttonami w tabelach)
    app.setStyle('Fusion')
    
    player = SIDPlayer()
    player.show()
    
    sys.exit(app.exec_())
