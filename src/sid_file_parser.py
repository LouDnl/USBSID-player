#!/usr/bin/env python3
"""
Parser pliku SID - odczytuje metadane z plików .sid
Based on SID file format specification (PSID v1-v4)
"""

import struct
import os
from typing import Optional, Tuple


class SIDFileParser:
    """Odczytuje metadane z pliku SID"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.valid = False
        self.magic = ""
        self.version = 0
        self.name = ""
        self.author = ""
        self.released = ""
        self.songs = 1
        self.start_song = 1
        
        if os.path.exists(filepath):
            self._parse()
    
    def _parse(self):
        """Parsuj plik SID"""
        try:
            with open(self.filepath, 'rb') as f:
                # Odczytaj magic ID (4 bajty)
                magic_bytes = f.read(4)
                self.magic = magic_bytes.decode('ascii', errors='ignore')
                
                if self.magic not in ('PSID', 'RSID'):
                    return
                
                # Odczytaj version (WORD = 2 bajty, big endian)
                version_bytes = f.read(2)
                self.version = struct.unpack('>H', version_bytes)[0]
                
                # Data offset (WORD)
                data_offset_bytes = f.read(2)
                data_offset = struct.unpack('>H', data_offset_bytes)[0]
                
                # Load address (WORD)
                load_addr_bytes = f.read(2)
                
                # Init address (WORD)
                init_addr_bytes = f.read(2)
                
                # Play address (WORD)
                play_addr_bytes = f.read(2)
                
                # Songs (WORD) - liczba subtun
                songs_bytes = f.read(2)
                self.songs = struct.unpack('>H', songs_bytes)[0]
                
                # Start song (WORD)
                start_song_bytes = f.read(2)
                self.start_song = struct.unpack('>H', start_song_bytes)[0]
                
                # Speed (LONGWORD = 4 bajty)
                speed_bytes = f.read(4)
                
                # Name (32 bajty) - offset +16 od początku
                name_bytes = f.read(32)
                self.name = self._extract_string(name_bytes)
                
                # Author (32 bajty) - offset +36
                author_bytes = f.read(32)
                self.author = self._extract_string(author_bytes)
                
                # Released (32 bajty) - offset +56
                released_bytes = f.read(32)
                self.released = self._extract_string(released_bytes)
                
                self.valid = True
                
        except Exception as e:
            print(f"[SIDParser] Error parsing {self.filepath}: {e}")
            self.valid = False
    
    @staticmethod
    def _extract_string(byte_data: bytes) -> str:
        """Wyciągnij string z danych, usuwając null terminatory"""
        # Dekoduj jako Windows-1252 (Extended ASCII)
        try:
            text = byte_data.decode('windows-1252', errors='ignore')
            # Usuń trailing null bytes i whitespace
            return text.rstrip('\x00').strip()
        except Exception:
            return ""
    
    def get_name(self) -> str:
        """Zwróć nazwę piosenki (title)"""
        return self.name if self.name else os.path.splitext(os.path.basename(self.filepath))[0]
    
    def get_author(self) -> str:
        """Zwróć autora"""
        return self.author if self.author else "Unknown"
    
    def get_released(self) -> str:
        """Zwróć rok/wydanie"""
        return self.released.strip() if self.released else ""
    
    def get_songs_count(self) -> int:
        """Zwróć liczbę subtun"""
        return self.songs if self.songs > 0 else 1
    
    def get_year_from_released(self) -> str:
        """Wyciągnij rok z pola 'released' - zwyczajnie szuka 4-cyfrowego liczby"""
        if not self.released:
            return ""
        
        # Szukaj 4-cyfrowego roku
        released = self.released.strip()
        for word in released.split():
            if word.isdigit() and len(word) == 4:
                year = int(word)
                if 1980 <= year <= 2100:  # Rozsądny zakres
                    return word
        
        return ""
    
    def is_valid(self) -> bool:
        """Czy plik SID został prawidłowo sparsowany"""
        return self.valid
    
    def __repr__(self) -> str:
        return f"SIDFile({self.get_name()}/{self.get_author()}/{self.get_year_from_released()})"


def read_sid_metadata(filepath: str) -> dict:
    """Convenience function - odczytaj metadane z pliku SID"""
    parser = SIDFileParser(filepath)
    
    if not parser.is_valid():
        return {
            'title': os.path.splitext(os.path.basename(filepath))[0],
            'author': 'Unknown',
            'year': '',
            'songs': 1
        }
    
    return {
        'title': parser.get_name(),
        'author': parser.get_author(),
        'year': parser.get_year_from_released(),
        'songs': parser.get_songs_count()
    }


# --- TESTY ---
if __name__ == "__main__":
    print("=" * 70)
    print("🎵 SID File Parser - Test")
    print("=" * 70)
    
    # Testuj na dostępnych plikach SID
    test_files = [
        "n:\\- Programs\\Thonny\\- MOJE\\sidplayer\\Are_You_Satisfied.sid",
        "n:\\- Programs\\Thonny\\- MOJE\\sidplayer\\Bassliner.sid",
    ]
    
    for filepath in test_files:
        if os.path.exists(filepath):
            print(f"\n📄 {os.path.basename(filepath)}")
            parser = SIDFileParser(filepath)
            
            if parser.is_valid():
                print(f"   ✅ Valid SID file")
                print(f"   Title:    {parser.get_name()}")
                print(f"   Author:   {parser.get_author()}")
                print(f"   Released: {parser.get_released()}")
                print(f"   Year:     {parser.get_year_from_released()}")
                print(f"   Songs:    {parser.get_songs_count()}")
            else:
                print(f"   ❌ Failed to parse")
        else:
            print(f"\n⚠️  {filepath} - not found")
    
    print("\n" + "=" * 70)
    print("✅ Test completed")
    print("=" * 70)