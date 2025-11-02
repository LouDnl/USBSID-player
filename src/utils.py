"""
Utility functions for SID Player
Helper functions for formatting, string processing, etc.
"""

import os
import hashlib
from typing import Optional


def format_artist_name(artist: str) -> str:
    """
    Zmienia format artysty z "Imię Nazwisko (Nick)" na "Nick (Imię Nazwisko)"
    Jeśli brak nawiasów, zwraca oryginalny tekst
    
    Args:
        artist: Original artist name string
        
    Returns:
        Formatted artist name or original if format doesn't match
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
    
    Args:
        tracker: Tracker name with underscores
        
    Returns:
        Formatted tracker name with spaces
    """
    if not tracker:
        return tracker
    return tracker.replace("_", " ")


def calculate_sid_md5(sid_path: str) -> Optional[str]:
    """
    Oblicza MD5 hash pliku SID
    
    Args:
        sid_path: Path to SID file
        
    Returns:
        MD5 hash string or None if file doesn't exist
    """
    if not os.path.exists(sid_path):
        return None
        
    try:
        with open(sid_path, 'rb') as f:
            md5_hash = hashlib.md5()
            for chunk in iter(lambda: f.read(8192), b''):
                md5_hash.update(chunk)
            return md5_hash.hexdigest().upper()
    except Exception:
        return None


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0


def ensure_directory_exists(directory: str) -> bool:
    """
    Create directory if it doesn't exist
    
    Args:
        directory: Directory path
        
    Returns:
        True if directory exists or was created
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception:
        return False


def get_filename_without_extension(file_path: str) -> str:
    """
    Extract filename without extension
    
    Args:
        file_path: Full file path
        
    Returns:
        Filename without extension
    """
    return os.path.splitext(os.path.basename(file_path))[0]


def get_safe_filename(filename: str) -> str:
    """
    Remove/replace unsafe characters from filename
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    unsafe_chars = '<>:"/\\|?*'
    safe_name = filename
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    return safe_name


# =============================================
#         TIME CONVERSION & FORMATTING
# =============================================

def seconds_to_minsec(seconds: float) -> str:
    """
    Convert seconds to MM:SS format.
    
    Args:
        seconds: Time in seconds (can be float)
        
    Returns:
        Formatted string as "MM:SS"
        
    Example:
        >>> seconds_to_minsec(125)
        '02:05'
        >>> seconds_to_minsec(3661)
        '61:01'  # More than 59 minutes
    """
    if seconds < 0:
        seconds = 0
    
    total_seconds = int(seconds)
    minutes = total_seconds // 60
    secs = total_seconds % 60
    
    return f"{minutes:02d}:{secs:02d}"


def seconds_to_hhmmss(seconds: float) -> str:
    """
    Convert seconds to HH:MM:SS format.
    
    Args:
        seconds: Time in seconds (can be float)
        
    Returns:
        Formatted string as "HH:MM:SS"
        
    Example:
        >>> seconds_to_hhmmss(3661)
        '01:01:01'
        >>> seconds_to_hhmmss(125)
        '00:02:05'
    """
    if seconds < 0:
        seconds = 0
    
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def minsec_to_seconds(minsec_str: str) -> int:
    """
    Convert MM:SS format to seconds.
    
    Args:
        minsec_str: Time string in format "MM:SS"
        
    Returns:
        Total seconds as integer
        
    Example:
        >>> minsec_to_seconds("02:05")
        125
        >>> minsec_to_seconds("1:30")
        90
    """
    try:
        parts = minsec_str.split(':')
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        return 0
    except (ValueError, IndexError):
        return 0


def hhmmss_to_seconds(hhmmss_str: str) -> int:
    """
    Convert HH:MM:SS format to seconds.
    
    Args:
        hhmmss_str: Time string in format "HH:MM:SS"
        
    Returns:
        Total seconds as integer
        
    Example:
        >>> hhmmss_to_seconds("01:02:05")
        3725
        >>> hhmmss_to_seconds("00:00:30")
        30
    """
    try:
        parts = hhmmss_str.split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            # Also support MM:SS format
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        return 0
    except (ValueError, IndexError):
        return 0


# =============================================
#         VALIDATION & CHECKING
# =============================================

def is_valid_time_format(time_str: str) -> bool:
    """
    Check if string is valid time format (MM:SS or HH:MM:SS).
    
    Args:
        time_str: Time string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parts = time_str.split(':')
        if len(parts) not in [2, 3]:
            return False
        
        for part in parts:
            if not part.isdigit() or int(part) < 0:
                return False
        
        # Validate range
        if len(parts) == 2:  # MM:SS
            minutes, seconds = int(parts[0]), int(parts[1])
            return 0 <= minutes and 0 <= seconds <= 59
        else:  # HH:MM:SS
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
            return 0 <= hours and 0 <= minutes <= 59 and 0 <= seconds <= 59
    except (ValueError, IndexError):
        return False


def is_valid_sid_file(file_path: str) -> bool:
    """
    Check if file is a valid SID file (by extension).
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file has .sid extension (case-insensitive)
    """
    return file_path.lower().endswith('.sid')


def validate_percentage(value: int) -> int:
    """
    Ensure value is within 0-100 range.
    
    Args:
        value: Value to validate
        
    Returns:
        Clamped value between 0 and 100
    """
    return max(0, min(100, value))


# =============================================
#         STRING & DATA PROCESSING
# =============================================

def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to max length with suffix.
    
    Args:
        text: String to truncate
        max_length: Maximum length (including suffix)
        suffix: String to append if truncated
        
    Returns:
        Truncated string
        
    Example:
        >>> truncate_string("Hello World", 8)
        'Hello...'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_string(text: str) -> str:
    """
    Clean string by removing leading/trailing whitespace and normalizing spaces.
    
    Args:
        text: String to clean
        
    Returns:
        Cleaned string
    """
    if not text:
        return text
    # Remove multiple spaces
    text = ' '.join(text.split())
    return text.strip()