#!/usr/bin/env python3
"""
Playlist Manager dla SID Playera
Obsługa dodawania, usuwania, ładowania playlisty z JSON
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
import hashlib


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


class PlaylistEntry:
    """Jedna piosenka w playliście"""
    def __init__(self, file_path: str, title: str = "", author: str = "", duration: int = 120, 
                 year: str = "", tracker: str = "", group: str = ""):
        self.file_path = file_path
        self.title = title or Path(file_path).stem
        self.author = author or "Unknown"
        self.duration = duration  # w sekundach
        self.year = year or ""
        self.tracker = tracker or ""
        self.group = group or ""
        self.file_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Oblicz hash pliku do identyfikacji duplikatów"""
        if os.path.exists(self.file_path):
            return hashlib.md5(self.file_path.encode()).hexdigest()[:8]
        return "unknown"
    
    def to_dict(self) -> Dict:
        """Konwertuj do dict (do JSON)"""
        return {
            "file_path": self.file_path,
            "title": self.title,
            "author": self.author,
            "duration": self.duration,
            "year": self.year,
            "tracker": self.tracker,
            "group": self.group
        }
    
    def __repr__(self) -> str:
        return f"🎵 {self.title} - {self.author} ({self.duration}s)"


class PlaylistManager:
    """Zarządzanie playlistą"""
    def __init__(self, playlist_file: str = "playlist.json"):
        self.playlist_file = playlist_file
        self.entries: List[PlaylistEntry] = []
        self.current_index = -1
        
        # Załaduj istniejącą playlistę
        if os.path.exists(playlist_file):
            self.load(playlist_file)
    
    def add(self, file_path: str, title: str = "", author: str = "", duration: int = 120) -> bool:
        """
        Dodaj piosenkę do playlisty
        Zwraca True jeśli się powiodło
        """
        if not os.path.exists(file_path):
            print(f"❌ Plik nie istnieje: {file_path}")
            return False
        
        # Sprawdź duplikaty
        if any(e.file_path == file_path for e in self.entries):
            print(f"⚠️  Piosenka już jest na liście: {file_path}")
            return False
        
        entry = PlaylistEntry(file_path, title, author, duration)
        self.entries.append(entry)
        print(f"✅ Dodana: {entry}")
        return True
    
    def add_multiple(self, directory: str, pattern: str = "*.sid") -> int:
        """
        Dodaj wszystkie pliki z folderu
        Zwraca liczbę dodanych plików
        """
        if not os.path.isdir(directory):
            print(f"❌ Folder nie istnieje: {directory}")
            return 0
        
        added = 0
        for file_path in Path(directory).glob(pattern):
            if self.add(str(file_path)):
                added += 1
        
        print(f"✅ Dodano {added} piosenek z {directory}")
        return added
    
    def remove(self, index: int) -> bool:
        """Usuń piosenkę z playlisty"""
        if 0 <= index < len(self.entries):
            entry = self.entries.pop(index)
            print(f"🗑️  Usunięta: {entry}")
            
            # Aktualizuj current_index jeśli trzeba
            if self.current_index >= len(self.entries):
                self.current_index = len(self.entries) - 1
            
            return True
        
        print(f"❌ Błędny indeks: {index}")
        return False
    
    def clear(self) -> None:
        """Wyczyść całą playlistę"""
        self.entries.clear()
        self.current_index = -1
        print("🗑️  Playlista wyczyszczona")
    
    def move(self, from_index: int, to_index: int) -> bool:
        """Przenieś piosenkę na inną pozycję"""
        if not (0 <= from_index < len(self.entries) and 0 <= to_index < len(self.entries)):
            return False
        
        entry = self.entries.pop(from_index)
        self.entries.insert(to_index, entry)
        print(f"↔️  Przeniesiono: {entry}")
        return True
    
    def shuffle(self) -> None:
        """Losowo przetasuj playlistę"""
        import random
        random.shuffle(self.entries)
        print("🔀 Playlista przetasowana")
    
    def sort_by_title(self) -> None:
        """Posortuj po tytułach"""
        self.entries.sort(key=lambda x: x.title.lower())
        print("⬆️  Posortowana po tytułach")
    
    def sort_by_author(self) -> None:
        """Posortuj po autorach (używając sformatowanego formatu Nick(Name)), wtórnie po tytułach"""
        self.entries.sort(key=lambda x: (format_artist_name(x.author).lower(), x.title.lower()))
        print("⬆️  Posortowana po autorach (wtórnie po tytułach)")
    
    def sort_by_year(self) -> None:
        """Posortuj po roku"""
        self.entries.sort(key=lambda x: int(x.year) if x.year and x.year.isdigit() else 0)
        print("⬆️  Posortowana po roku")
    
    def sort_by_title_reverse(self) -> None:
        """Posortuj po tytułach (odwrotnie)"""
        self.entries.sort(key=lambda x: x.title.lower(), reverse=True)
        print("⬇️  Posortowana po tytułach (odwrotnie)")
    
    def sort_by_author_reverse(self) -> None:
        """Posortuj po autorach (odwrotnie) (używając sformatowanego formatu Nick(Name)), wtórnie po tytułach"""
        self.entries.sort(key=lambda x: (format_artist_name(x.author).lower(), x.title.lower()), reverse=True)
        print("⬇️  Posortowana po autorach (odwrotnie) (wtórnie po tytułach)")
    
    def sort_by_year_reverse(self) -> None:
        """Posortuj po roku (odwrotnie)"""
        self.entries.sort(key=lambda x: int(x.year) if x.year and x.year.isdigit() else 0, reverse=True)
        print("⬇️  Posortowana po roku (odwrotnie)")
    
    def get_current(self) -> Optional[PlaylistEntry]:
        """Pobierz aktualną piosenkę"""
        if -1 < self.current_index < len(self.entries):
            return self.entries[self.current_index]
        return None
    
    def next(self) -> Optional[PlaylistEntry]:
        """Przejdź do następnej piosenki"""
        if len(self.entries) == 0:
            return None
        
        self.current_index = (self.current_index + 1) % len(self.entries)
        return self.get_current()
    
    def previous(self) -> Optional[PlaylistEntry]:
        """Przejdź do poprzedniej piosenki"""
        if len(self.entries) == 0:
            return None
        
        self.current_index = (self.current_index - 1) % len(self.entries)
        return self.get_current()
    
    def set_current(self, index: int) -> Optional[PlaylistEntry]:
        """Ustaw aktualną piosenkę"""
        if 0 <= index < len(self.entries):
            self.current_index = index
            return self.get_current()
        return None
    
    def save(self, filename: Optional[str] = None) -> bool:
        """Zapisz playlistę do JSON"""
        filepath = filename or self.playlist_file
        
        try:
            data = {
                "version": "1.0",
                "entries": [e.to_dict() for e in self.entries],
                "current_index": self.current_index
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Zapisana playlista: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Błąd przy zapisywaniu: {e}")
            return False
    
    def load(self, filename: str) -> bool:
        """Załaduj playlistę z JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.entries.clear()
            for entry_data in data.get('entries', []):
                entry = PlaylistEntry(
                    entry_data['file_path'],
                    entry_data.get('title', ''),
                    entry_data.get('author', ''),
                    entry_data.get('duration', 120),
                    entry_data.get('year', ''),
                    entry_data.get('tracker', ''),
                    entry_data.get('group', '')
                )
                self.entries.append(entry)
            
            self.current_index = data.get('current_index', -1)
            print(f"📂 Załadowana playlista: {filename} ({len(self.entries)} piosenek)")
            return True
        except Exception as e:
            print(f"❌ Błąd przy ładowaniu: {e}")
            return False
    
    def search(self, query: str) -> List[int]:
        """
        Szukaj piosenek po tytule lub autorze
        Zwraca indeksy pasujących piosenek
        """
        query = query.lower()
        results = []
        
        for i, entry in enumerate(self.entries):
            if query in entry.title.lower() or query in entry.author.lower():
                results.append(i)
        
        return results
    
    def get_length_formatted(self, index: int = None) -> str:
        """Pobierz sformatowany czas"""
        if index is None:
            entry = self.get_current()
        else:
            entry = self.entries[index] if 0 <= index < len(self.entries) else None
        
        if not entry:
            return "N/A"
        
        mins = entry.duration // 60
        secs = entry.duration % 60
        return f"{mins}:{secs:02d}"
    
    def get_all_entries(self) -> List[PlaylistEntry]:
        """Pobierz wszystkie wpisy"""
        return self.entries.copy()
    
    def __len__(self) -> int:
        """Liczba piosenek na liście"""
        return len(self.entries)
    
    def __repr__(self) -> str:
        return f"Playlista ({len(self.entries)} piosenek, aktualna: {self.current_index})"


# --- TESTY ---
if __name__ == "__main__":
    print("=" * 60)
    print("🎵 Playlist Manager - Test")
    print("=" * 60)
    
    # Utwórz manager
    pm = PlaylistManager("test_playlist.json")
    
    # Dodaj kilka piosenek
    print("\n1️⃣  Dodawanie piosenek...")
    pm.add("n:\\- Programs\\Thonny\\- MOJE\\sidplayer\\example.sid", "Example", "Unknown", 120)
    pm.add("n:\\- Programs\\Thonny\\- MOJE\\sidplayer\\Are_You_Satisfied.sid", "Are You Satisfied", "Unknown", 180)
    pm.add("n:\\- Programs\\Thonny\\- MOJE\\sidplayer\\Bassliner.sid", "Bassliner", "Unknown", 150)
    
    # Lub dodaj folder
    print("\n2️⃣  Dodawanie folderu...")
    pm.add_multiple("n:\\- Programs\\Thonny\\- MOJE\\sidplayer\\Metal", "*.sid")
    
    # Wyświetl playlistę
    print(f"\n3️⃣  Playlista ma {len(pm)} piosenek")
    for i, entry in enumerate(pm.get_all_entries()[:5]):  # Pierwsze 5
        print(f"   {i}: {entry}")
    
    # Posortuj
    print("\n4️⃣  Sortowanie...")
    pm.sort_by_title()
    
    # Szukaj
    print("\n5️⃣  Szukanie 'Bassliner'...")
    results = pm.search("bassliner")
    for idx in results:
        print(f"   Znaleziono: {pm.entries[idx]}")
    
    # Nawigacja
    print("\n6️⃣  Nawigacja...")
    pm.set_current(0)
    print(f"   Aktualna: {pm.get_current()}")
    pm.next()
    print(f"   Następna: {pm.get_current()}")
    pm.previous()
    print(f"   Poprzednia: {pm.get_current()}")
    
    # Zapisz
    print("\n7️⃣  Zapisywanie...")
    pm.save("test_playlist.json")
    
    # Załaduj
    print("\n8️⃣  Ładowanie...")
    pm2 = PlaylistManager("test_playlist.json")
    print(f"   Załadowana: {pm2}")
    
    print("\n" + "=" * 60)
    print("✅ Test zakończony")
    print("=" * 60)