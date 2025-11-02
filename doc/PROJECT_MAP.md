# SID Player - Project Map 🗺️

## 📋 Struktura Plików

```
sidplayer/
├── sid_player_modern07.py        [MAIN APP] - Główna klasa SIDPlayer
├── playback_manager.py           [MIXINS] - PlaybackManagerMixin (odtwarzanie)
├── sid_info_manager.py           [MIXINS] - SIDInfoMixin (info o plikach)
├── windows_api_manager.py        [MIXINS] - WindowsAPIManagerMixin (Windows API)
├── ui_theme.py                   [MIXINS] - UIThemeMixin (wygląd)
├── sid_player_ui.py              [UI] - ClickableProgressBar
├── debug_console.py              [UI] - DebugConsoleWidget
├── theme_settings.py             [UI] - ThemeSettingsWindow
├── playlist_widget.py            [UI] - PlaylistWidget
├── file_manager.py               [IO] - FileManager (INI, JSON, Playlist)
├── utils.py                      [UTILS] - Funkcje pomocnicze
├── tracker_recognition.py        [UTILS] - TrackerRecognizer
├── sid_file_parser.py            [UTILS] - Parser SID files
└── tools/
    ├── sidplayfp.exe             [BINARY] - Odtwarzacz C64
    ├── jsidplay2-console.exe     [BINARY] - Alternatywny odtwarzacz
    └── Songlengths.md5           [DB] - Baza duracii piosenek
```

---

## 🎯 Główne Metody do Pamiętania

### **playback_manager.py** - Logika Odtwarzania
Wszystkie metody powiązane z odtwarzaniem, pauzowaniem, przesuwaniem czasem

| Linia | Metoda | Opis |
|-------|--------|------|
| 30 | `prev_subtune()` | Poprzednia piosenka/subtune |
| 89 | `next_subtune()` | Następna piosenka/subtune |
| 148 | `prev_song()` | Poprzednia piosenka w playliście |
| 178 | `next_song()` | Następna piosenka w playliście |
| **208** | `start_playing()` | START odtwarzania (uruchamia sidplayfp) |
| 362 | `pause_playing()` | PAUZA odtwarzania |
| 429 | `stop_sid_file()` | STOP odtwarzania |
| **540** | `update_time()` ⚠️ | **GŁÓWNA PĘTLA TIMERA** - update co 100ms |
| **600** | `update_time_label()` | Wyświetl czas (mm:ss / mm:ss) |
| 609 | `on_playback_started()` | Slot po starcie playbacku |
| 617 | `monitor_playback_start()` | Monitor thread dla playback detection |
| 731 | `get_jsidplay2_mute_sequence()` | Sekwencja wyciszenia kanałów |
| 746 | `mute_all_jsidplay2_channels()` | Wycisz wszystkie kanały |
| 787 | `unmute_all_jsidplay2_channels()` | Odwycisz wszystkie kanały |
| 828 | `ensure_muted_before_navigation()` | Wycisz przed navigacją |
| 871 | `reset_mute_state_on_new_playback()` | Reset mute state |

**WAŻNE LOGIKA:**
- Linia **555-598**: Auto-advance/Loop logika gdy piosenka się skończy
  - **566-584**: Auto-advance do następnego subtune
  - **586-592**: Auto-play następna piosenka z playlisty

---

### **sid_info_manager.py** - Informacje o Plikach
Metody do odczytywania metadanych i duracii

| Linia | Metoda | Opis |
|-------|--------|------|
| 34 | `scale_title_font()` | Skalowanie fontu tytułu |
| 52 | `load_song_lengths()` | Załaduj Songlengths.md5 do pamięci |
| 95 | `calculate_sid_md5()` | Oblicz MD5 pliku SID |
| **106** | `get_song_duration()` | **Pobierz duration dla subtune** |
| 154 | `get_song_length_from_database()` | Szukaj w DB po MD5 |
| 210 | `read_metadata()` | Wczytaj metadata z SID |
| 324 | `get_sid_info()` | Pobierz pełne info o pliku |

**WAŻNE:**
- `get_song_duration()` - **to ta metoda która pobiera duration z Songlengths.md5!**

---

### **debug_console.py** - Konsola Debugowania

| Linia | Metoda | Opis |
|-------|--------|------|
| 18 | `__init__()` | Inicjalizacja |
| 23 | `init_ui()` | Zbuduj UI |
| 67 | `log()` | Wyślij log |
| 71 | `add_text()` | Dodaj tekst |
| 81 | `clear_console()` | Wyczyść konsole |
| 86 | `copy_all()` | Kopiuj wszystko |

---

### **sid_player_ui.py** - Komponenty UI

| Linia | Metoda | Opis |
|-------|--------|------|
| 19 | `ClickableProgressBar.__init__()` | Progress bar |
| 31 | `mousePressEvent()` | Klikanie na pasek |
| 48 | `mouseMoveEvent()` | Przesuwanie paska |

---

### **file_manager.py** - Zarządzanie Plikami (Static Methods)

| Linia | Metoda | Opis |
|-------|--------|------|
| 29 | `load_settings_ini()` | Załaduj settings.ini |
| 83 | `save_settings_ini()` | Zapisz settings.ini |
| 126 | `load_json()` | Załaduj JSON |
| 147 | `save_json()` | Zapisz JSON |
| 172 | `check_playlist_available()` | Sprawdź playlistę |
| 195 | `load_playlist()` | Załaduj playlistę |
| 208 | `save_playlist()` | Zapisz playlistę |
| 226 | `file_exists()` | Sprawdź czy plik istnieje |
| 231 | `directory_exists()` | Sprawdź czy folder istnieje |
| 236 | `ensure_directory()` | Stwórz folder jeśli nie istnieje |
| 254 | `get_file_info()` | Pobierz info o pliku |

---

### **theme_settings.py** - Ustawienia Tematu

| Linia | Metoda | Opis |
|-------|--------|------|
| 22 | `ThemeSettingsWindow.__init__()` | Inicjalizacja okna |
| 46 | `init_ui()` | Zbuduj UI |
| 157 | `create_slider_with_label()` | Stwórz slider |
| 212 | `on_slider_changed()` | Slider zmieniony |
| 227 | `on_player_changed()` | Player engine zmieniony |
| 239 | `reset_to_defaults()` | Reset do default |
| 248 | `apply_and_close()` | Zastosuj i zamknij |
| 267 | `apply_window_theme()` | Zastosuj theme |
| 344 | `get_settings()` | Pobierz ustawienia |

---

### **playlist_widget.py** - Widget Playlisty

| Linia | Metoda | Opis |
|-------|--------|------|
| 76 | `__init__()` | Inicjalizacja |
| 119 | `load_songlengths()` | Załaduj duracii |
| 147 | `get_file_md5()` | Oblicz MD5 |
| 155 | `get_song_duration_from_db()` | Pobierz duration |
| 162 | `_get_tracker_info()` | Pobierz info o trackerze |
| 174 | `regenerate_tracker_info_for_all()` | Regeneruj tracker info |
| 193 | `setup_ui()` | Zbuduj UI |
| 305 | `apply_theme()` | Zastosuj theme |
| 492 | `add_song()` | Dodaj piosenkę |
| 545 | `add_folder()` | Dodaj folder |
| 589 | `on_regenerate_trackers()` | Regeneruj trackery |
| 597 | `remove_selected()` | Usuń wybraną |
| 606 | `clear_playlist()` | Wyczyść playlistę |
| 619 | `search_playlist()` | Szukaj w playliście |
| 635 | `toggle_sort()` | Zmień sortowanie |
| 670 | `update_sort_button_label()` | Update label |
| 690 | `shuffle_playlist()` | Losuj playlistę |
| 696 | `get_sort_state()` | Pobierz stan sortowania |

---

### **windows_api_manager.py** - Windows API

| Linia | Metoda | Opis |
|-------|--------|------|
| 42 | `_get_engine_hints()` | Get engine title hints |
| 69 | `setup_windows_api()` | Inicjalizacja Windows API |
| 122 | `find_console_hwnd_for_sidplay()` | Znajdź handle okna |
| 185 | `hide_console_window_for_sidplay()` | Ukryj okno konsoli |
| 219 | `simulate_arrow_key()` | Symuluj arrow key (UP/DOWN) |
| 263 | `simulate_arrow_key_left_right()` | Symuluj arrow key (LEFT/RIGHT) |
| 308 | `send_key_to_sidplay()` | Wyślij klawisz |
| 364 | `send_char_sequence_to_console()` | Wyślij sekwencję znaków |

---

### **utils.py** - Funkcje Pomocnicze (Module Functions)

| Linia | Funkcja | Opis |
|-------|---------|------|
| 11 | `format_artist_name()` | Format artysty |
| 44 | `format_tracker_name()` | Format trackera |
| 60 | `calculate_sid_md5()` | Oblicz MD5 |
| 83 | `get_file_size_mb()` | Rozmiar pliku |
| 100 | `ensure_directory_exists()` | Ensure folder |
| 117 | `get_filename_without_extension()` | Nazwa bez ext |
| 130 | `get_safe_filename()` | Safe filename |
| 151 | `seconds_to_minsec()` | Sekundy -> mm:ss |
| 177 | `seconds_to_hhmmss()` | Sekundy -> hh:mm:ss |
| 204 | `minsec_to_seconds()` | mm:ss -> sekundy |
| 231 | `hhmmss_to_seconds()` | hh:mm:ss -> sekundy |
| 268 | `is_valid_time_format()` | Sprawdź format czasu |
| 298 | `is_valid_sid_file()` | Sprawdź czy SID |
| 311 | `validate_percentage()` | Validuj percentage |
| 328 | `truncate_string()` | Skrój string |
| 349 | `clean_string()` | Czyść string |

---

### **tracker_recognition.py** - Rozpoznawanie Trackera

| Linia | Funkcja | Opis |
|-------|---------|------|
| 413 | `get_recognizer()` | Pobierz recognizer |
| 421 | `recognize_tracker()` | Rozpoznaj tracker |

---

## 🔑 Kluczowe Zmienne w SIDPlayer

```python
# Playback state
self.is_playing          # Czy gramy
self.loop_enabled        # Loop włączony
self.current_subtune     # Obecny subtune (1-N)
self.num_subtunes        # Ile subtunes
self.total_duration      # Duration obecnego subtune (sekundy)
self.time_elapsed        # Upłynęły czas (sekundy)

# Timer
self.timer               # QTimer dla update_time()
self.time_elapsed        # Licznik czasu

# Process
self.process             # Subprocess sidplayfp
self.sid_file            # Ścieżka do SID file

# UI
self.time_label          # Label pokazujący czas
self.progress_bar        # Progress bar
self.debug_console       # Debug konsola
```

---

## 🐛 Najczęstsze Miejsca Bugów

| Bug | Plik | Linia | Opis |
|-----|------|-------|------|
| Auto-advance nie pokazuje czasu | playback_manager.py | 540-600 | `update_time()` logika |
| Duracii nie się ładują | sid_info_manager.py | 52-106 | `load_song_lengths()` i `get_song_duration()` |
| Konsola nie się pojawia | debug_console.py | 18-92 | DebugConsoleWidget |
| Wyciszenie nie działa | playback_manager.py | 731-871 | JSIDPLAY2 mute logika |
| Settings nie się zachowują | file_manager.py | 29-125 | INI save/load |
| Progress bar nie się updatuje | playback_manager.py | 540-560 | `setValue()` calls |

---

## 📝 Jak Raportować Bug

**Zamiast:**
> "Nie działa auto-advance"

**Powiedz:**
> "Auto-advance w playback_manager.py, linia 566-584, po zmierzeniu się subtune 2, nie pokazuje czasu docelowego dla subtune 3"

---

## 🎯 Quick Navigation

Aby szybko znaleźć problem:

1. **Nie gra dźwięk?** → `playback_manager.py:208` `start_playing()`
2. **Czas się nie updatuje?** → `playback_manager.py:540` `update_time()`
3. **Duracii źle?** → `sid_info_manager.py:106` `get_song_duration()`
4. **Konsola pusta?** → `debug_console.py:67` `log()`
5. **Settings nie się zapisują?** → `file_manager.py:83` `save_settings_ini()`
6. **Progress bar nie rusza?** → `playback_manager.py:550-552` progress calculation
7. **Subtune nie zmienia się?** → `playback_manager.py:89` `next_subtune()`

---

**Ostatnia aktualizacja:** 2024  
**Główne klasy:** SIDPlayer, PlaybackManagerMixin, SIDInfoMixin, FileManager  
**Główne loop:** `update_time()` co 100ms (QTimer)