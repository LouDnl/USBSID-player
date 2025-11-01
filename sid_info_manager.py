"""
SID Player SID Info Manager Mixin
Extracted from sid_player_modern07.py (Phase 4 refactoring)

This module contains the SIDInfoMixin class which provides:
- load_song_lengths(): Load songlengths database
- calculate_sid_md5(): Calculate MD5 hash of SID file
- get_song_duration(): Get song duration from database or fallback
- read_metadata(): Read SID file metadata
- get_sid_info(): Parse SID header information
- scale_title_font(): Scale title font based on text length

The mixin is designed to be inherited by the SIDPlayer class to separate
SID metadata parsing concerns from the main playback logic.
"""

import os
import hashlib
from PyQt5.QtGui import QFont

# Imports for tracker recognition and utilities
try:
    from tracker_recognition import get_recognizer
    TRACKER_RECOGNITION_AVAILABLE = True
except ImportError:
    TRACKER_RECOGNITION_AVAILABLE = False

from utils import format_artist_name, format_tracker_name


class SIDInfoMixin:
    """Mixin providing SID file information and metadata parsing methods for SID Player"""
    
    def scale_title_font(self, text):
        """Skaluj font tytułu na podstawie liczby znaków"""
        char_count = len(text)
        
        if char_count <= 15:
            font_size = 32
        elif char_count <= 25:
            font_size = 26
        elif char_count <= 35:
            font_size = 20
        elif char_count <= 45:
            font_size = 16
        else:
            font_size = 12
        
        font = QFont("Arial", font_size, QFont.Bold)
        self.title_label.setFont(font)

    def load_song_lengths(self):
        """Odczytuje plik Songlengths.md5 z katalogu sidplayer (format MD5).
        Przechowuje WSZYSTKIE czasy dla każdego subtune'a jako listę."""
        self.song_lengths = {}
        if not os.path.exists(self.songlengths_path):
            self.debug_console.log(f"[WARN] Songlengths.md5 not found: {self.songlengths_path}")
            return

        try:
            with open(self.songlengths_path, "r", encoding="latin-1") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("\ufeff"):
                        line = line.replace("\ufeff", "")
                    
                    if not line or line.startswith(";") or line.startswith("#"):
                        continue
                    
                    if "=" in line:
                        try:
                            md5_hash, time_str = line.split("=", 1)
                            md5_hash = md5_hash.strip().lower()
                            times = time_str.strip().split()
                            
                            # Parse ALL times for all subtunes
                            durations = []
                            for time_part in times:
                                if ":" in time_part:
                                    try:
                                        min_, sec_ = map(int, time_part.split(":"))
                                        durations.append(min_ * 60 + sec_)
                                    except:
                                        pass
                            
                            # Store as list of durations for each subtune
                            if durations:
                                self.song_lengths[md5_hash] = durations
                        except Exception:
                            pass
            self.debug_console.log(f"[INFO] Załadowano {len(self.song_lengths)} wpisów z Songlengths.md5 (z długościami dla każdego subtune'a)")
        except Exception as e:
            self.debug_console.log(f"[ERROR] Nie udało się odczytać Songlengths.md5: {e}")

    def calculate_sid_md5(self, sid_path):
        """Oblicza MD5 hash pliku SID."""
        try:
            with open(sid_path, "rb") as f:
                file_data = f.read()
                md5_hash = hashlib.md5(file_data).hexdigest().lower()
                return md5_hash
        except Exception as e:
            self.debug_console.log(f"[ERROR] Nie udało się obliczyć MD5: {e}")
            return None

    def get_song_duration(self, sid_path, subtune_number=None):
        """Zwraca czas utworu z Songlengths.md5 na podstawie MD5 hash i numeru subtune'a.
        
        Args:
            sid_path: ścieżka do pliku SID
            subtune_number: numer subtune'a (1-based), jeśli None zwraca czas dla aktualnego
        
        Fallback do default jeśli brak w bazie.
        """
        if not sid_path:
            return self.default_song_duration

        try:
            # Jeśli nie podano numeru subtune'a, użyj aktualnego
            if subtune_number is None:
                subtune_number = self.current_subtune

            md5_hash = self.calculate_sid_md5(sid_path)
            if not md5_hash:
                self.debug_console.log(f"[INFO] Nie udało się obliczyć MD5 dla: {sid_path}")
                return self.default_song_duration

            durations_list = self.song_lengths.get(md5_hash, None)
            
            if durations_list is not None:
                # Jeśli to lista (nowy format), weź czas dla konkretnego subtune'a
                if isinstance(durations_list, list):
                    if 1 <= subtune_number <= len(durations_list):
                        duration = durations_list[subtune_number - 1]  # 1-based index -> 0-based
                        self.debug_console.log(f"[INFO] ✓ Czas z Songlengths.md5: {duration}s dla subtune {subtune_number} z {len(durations_list)}")
                        return duration
                    else:
                        # Jeśli subtune poza zakresem, weź ostatni dostępny
                        duration = durations_list[-1]
                        self.debug_console.log(f"[INFO] ⚠ Subtune {subtune_number} poza zakresem, używam ostatni: {duration}s")
                        return duration
                else:
                    # Stary format - pojedyncza liczba (dla zgodności wstecznej)
                    self.debug_console.log(f"[INFO] ✓ Czas z Songlengths.md5: {durations_list}s (stary format)")
                    return durations_list
            else:
                self.debug_console.log(f"[INFO] Brak wpisu w Songlengths.md5 dla MD5: {md5_hash} - używam default: {self.default_song_duration}s")
                return self.default_song_duration

        except Exception as e:
            self.debug_console.log(f"[ERROR] Błąd w get_song_duration: {e}")
            return self.default_song_duration

    def get_song_length_from_database(self, sid_path):
        """Pobierz czas piosenki z bazy Songlengths.md5 / Songlengths.txt"""
        try:
            # Oblicz MD5 pliku SID
            md5_hash = hashlib.md5()
            with open(sid_path, "rb") as f:
                md5_hash.update(f.read())
            file_md5 = md5_hash.hexdigest().lower()
            self.debug_console.log(f"[INFO] MD5 pliku: {file_md5}")
            
            # Szukaj w Songlengths.md5
            songlengths_path = os.path.join(os.path.dirname(self.sidplayfp_path), "Songlengths.md5")
            
            if not os.path.exists(songlengths_path):
                self.debug_console.log(f"[WARN] Songlengths.md5 nie znaleziony: {songlengths_path}")
                return None
            
            # Czytaj plik - szukaj linii z naszym MD5
            with open(songlengths_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    
                    # Pomiń komentarze i puste linie
                    if not line or line.startswith(";"):
                        continue
                    
                    # Format: MD5=mm:ss[.milliseconds]
                    if "=" in line:
                        stored_md5, time_str = line.split("=", 1)
                        stored_md5 = stored_md5.strip().lower()
                        
                        if stored_md5 == file_md5:
                            # Znaleziono! Parsuj czas
                            # Format: 1:23, 1:23.456, etc.
                            try:
                                parts = time_str.strip().split(":")
                                if len(parts) >= 2:
                                    minutes = int(parts[0])
                                    # Segundy mogą mieć część dziesiętną
                                    seconds_part = parts[1].split(".")
                                    seconds = int(seconds_part[0])
                                    
                                    total_seconds = minutes * 60 + seconds
                                    self.debug_console.log(f"[INFO] ✓ Song Length z bazy: {time_str} = {total_seconds}s")
                                    return total_seconds
                            except (ValueError, IndexError) as e:
                                self.debug_console.log(f"[WARN] Błąd parsowania czasu '{time_str}': {e}")
                                continue
            
            self.debug_console.log(f"[INFO] Plik nie znaleziony w Songlengths.md5")
            return None
            
        except Exception as e:
            self.debug_console.log(f"[WARN] Błąd odczytu Songlengths.md5: {e}")
            return None

    def read_metadata(self, path):
        """Czytaj metadane z pliku SID i czasami z bazy Songlengths.md5"""
        try:
            # Najpierw czytaj z nagłówka SID
            with open(path, "rb") as f:
                data = f.read()
                title = data[0x16:0x36].decode("latin1", errors="ignore").strip("\0 ")
                author = data[0x36:0x56].decode("latin1", errors="ignore").strip("\0 ")
                released = data[0x56:0x76].decode("latin1", errors="ignore").strip("\0 ")
                group = ""  # W PSID nie ma pola "group", to w metadanych sidplayfp
                
                # Czytaj liczbę subtunes (offset 0x0E) i default subtune (offset 0x10)
                self.num_subtunes = int.from_bytes(data[0x0E:0x10], 'big')
                self.default_subtune = int.from_bytes(data[0x10:0x12], 'big')
                self.current_subtune = self.default_subtune
                
                print(f"[METADATA_DEBUG] Loaded: num_subtunes={self.num_subtunes}, default_subtune={self.default_subtune}, current_subtune={self.current_subtune}")
                self.debug_console.log(f"[INFO] SID contains {self.num_subtunes} subtune(s), default: {self.default_subtune}")
                
                # Aktualizuj UI dla subtunes
                if hasattr(self, 'subtune_label'):
                    self.subtune_label.setText(f"{self.num_subtunes} subtunes")
                    self.subtune_number.setText(str(self.current_subtune))

            title_text = title.upper() if title else "UNKNOWN TITLE"
            self.title_label.setText(title_text)
            self.scale_title_font(title_text)
            
            # Ustaw Artist - zastosuj formatowanie
            formatted_author = format_artist_name(author) if author else "Unknown Artist"
            self.author_label.setText(formatted_author)
            
            # Utwórz tekst dla year_group_label: rok, group i tracker
            year_text = ""
            if released and released != "-":
                year_text = released
            if group:
                if year_text:
                    year_text += f" [{group}]"
                else:
                    year_text = group
            
            # Przygotuj tracker info (będzie dodany później po rozpoznaniu)
            tracker_info = ""
            
            # Pokaż/ukryj year_group_label w zależności od zawartości
            if year_text or tracker_info:
                final_text = year_text
                if tracker_info:
                    if final_text:
                        final_text += f" • {tracker_info}"
                    else:
                        final_text = tracker_info
                
                self.year_group_label.setText(final_text)
                self.year_group_label.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
                self.year_group_label.show()
            else:
                self.year_group_label.setMaximumHeight(0)
                self.year_group_label.hide()
            
            # Rozpoznaj tracker i dodaj do year_group_label
            if TRACKER_RECOGNITION_AVAILABLE:
                try:
                    recognizer = get_recognizer()
                    tracker_name = recognizer.recognize_tracker(path, verbose=False)
                    if tracker_name != "Unknown":
                        tracker_info = format_tracker_name(tracker_name)
                        self.debug_console.log(f"[TRACKER] ✓ Rozpoznano: {tracker_info}")
                        
                        # Dodaj tracker info do year_group_label
                        current_text = self.year_group_label.text()
                        if current_text:
                            final_text = f"{current_text} • {tracker_info}"
                        else:
                            final_text = tracker_info
                        
                        self.year_group_label.setText(final_text)
                        self.year_group_label.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
                        self.year_group_label.show()
                    
                    # Ukryj osobny tracker_label (dane teraz w year_group_label)
                    self.tracker_label.setMaximumHeight(0)
                    self.tracker_label.hide()
                except Exception as e:
                    self.debug_console.log(f"[TRACKER] Błąd rozpoznawania: {e}")
                    self.tracker_label.setMaximumHeight(0)
                    self.tracker_label.hide()
            else:
                self.tracker_label.setMaximumHeight(0)
                self.tracker_label.hide()
            
            # Pobierz Song Length - najpierw z bazy Songlengths.md5, potem fallback do nagłówka SID
            song_length_from_db = self.get_song_length_from_database(path)
            if song_length_from_db is not None:
                self.total_duration = song_length_from_db
                self.update_time_label()
            else:
                # Fallback: czytaj z nagłówka SID
                self.get_sid_info(path)

        except Exception as e:
            self.debug_console.log(f"[ERROR] Failed to read metadata: {e}")
            self.title_label.setText("UNKNOWN TITLE")
            self.scale_title_font("UNKNOWN TITLE")
            self.author_label.setText("Unknown Artist")
            self.year_group_label.setMaximumHeight(0)
            self.year_group_label.hide()
            self.debug_console.log(f"[WARN] Error reading metadata: {e}")

    def get_sid_info(self, path):
        """Pobierz informacje o SID (łącznie z Song Length) bezpośrednio z pliku"""
        try:
            with open(path, "rb") as f:
                data = f.read()
                
                # Sprawdź nagłówek SID
                header = data[0:4].decode("ascii", errors="ignore")
                if header not in ["PSID", "RSID"]:
                    self.debug_console.log(f"[WARN] Nieznany format SID: {header}")
                    return
                
                # Czytaj wersję nagłówka
                version = int.from_bytes(data[4:6], 'big')
                self.debug_console.log(f"[INFO] SID Header: {header} v{version}")
                
                # Dla PSID v3/v4 i RSID v3/v4 Song Length jest na offset 0x76-0x7A (w milliseconds)
                if version >= 3:
                    try:
                        song_length_ms = int.from_bytes(data[0x76:0x7A], 'big')
                        if song_length_ms > 0:
                            self.total_duration = song_length_ms // 1000  # Convert ms to seconds
                            self.debug_console.log(f"[INFO] ✓ Total duration from SID: {self.total_duration}s ({song_length_ms}ms)")
                            self.update_time_label()
                            return
                        else:
                            self.debug_console.log(f"[INFO] Song Length = 0 (looping enabled)")
                            self.total_duration = 0
                            self.update_time_label()
                            return
                    except Exception as e:
                        self.debug_console.log(f"[WARN] Błąd czytania Song Length z v{version}: {e}")
                
                # Dla v1/v2 Song Length nie jest dostępne w headrze
                self.debug_console.log(f"[INFO] PSID v{version} - Song Length niedostępny (format nie zawiera tej info)")
                self.total_duration = 0
                self.update_time_label()
                
        except Exception as e:
            self.debug_console.log(f"[WARN] Błąd pobierania Song Length z pliku SID: {e}")