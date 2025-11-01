"""
File Manager for SID Player
Extracted from sid_player_modern07.py (Phase 1 refactoring)

This module handles all file I/O operations:
- INI settings file management (load/save configuration)
- Playlist file management (load/save/check availability)
- JSON operations
- File validation and checking

The FileManager class provides static methods for easy access
without needing to instantiate the class.
"""

import os
import json
import configparser
from typing import Optional, Dict, Any, List


class FileManager:
    """Static file management utilities for SID Player"""
    
    # ============================================
    #         INI SETTINGS FILE MANAGEMENT
    # ============================================
    
    @staticmethod
    def load_settings_ini(settings_path: str) -> Dict[str, Any]:
        """
        Load settings from INI file.
        
        Args:
            settings_path: Path to settings.ini file
            
        Returns:
            Dictionary with loaded settings, empty dict if file doesn't exist
            
        Example:
            settings = FileManager.load_settings_ini("settings.ini")
            console_visible = settings.get('display', {}).get('console_visible', False)
        """
        settings = {
            'display': {},
            'theme': {},
            'playback': {},
            'playlist_sort': {}
        }
        
        if not os.path.exists(settings_path):
            return settings
        
        try:
            config = configparser.ConfigParser()
            config.read(settings_path)
            
            # Load display settings
            if config.has_section('display'):
                settings['display'] = dict(config.items('display'))
            
            # Load theme settings
            if config.has_section('theme'):
                for key, value in config.items('theme'):
                    try:
                        settings['theme'][key] = int(value)
                    except ValueError:
                        settings['theme'][key] = value
            
            # Load playback settings
            if config.has_section('playback'):
                settings['playback'] = dict(config.items('playback'))
            
            # Load playlist sort settings
            if config.has_section('playlist_sort'):
                settings['playlist_sort'] = dict(config.items('playlist_sort'))
                
        except Exception as e:
            print(f"[FILE_MANAGER] ⚠️  Error loading settings.ini: {e}")
        
        return settings
    
    @staticmethod
    def save_settings_ini(settings_path: str, settings: Dict[str, Any]) -> bool:
        """
        Save settings to INI file.
        
        Args:
            settings_path: Path to settings.ini file
            settings: Dictionary with settings to save
            
        Returns:
            True if successful, False otherwise
            
        Example:
            settings = {
                'display': {'console_visible': 'False'},
                'theme': {'hue': '210', 'saturation': '50'},
                'playback': {'audio_engine': 'sidplayfp'},
                'playlist_sort': {'title': 'ascending'}
            }
            success = FileManager.save_settings_ini("settings.ini", settings)
        """
        try:
            config = configparser.ConfigParser()
            
            for section, values in settings.items():
                if values and isinstance(values, dict):
                    if not config.has_section(section):
                        config.add_section(section)
                    for key, value in values.items():
                        config.set(section, key, str(value))
            
            with open(settings_path, 'w') as f:
                config.write(f)
            
            return True
        except Exception as e:
            print(f"[FILE_MANAGER] ⚠️  Error saving settings.ini: {e}")
            return False
    
    # ============================================
    #         JSON FILE MANAGEMENT
    # ============================================
    
    @staticmethod
    def load_json(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON as dictionary, or None if file doesn't exist or is invalid
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[FILE_MANAGER] ⚠️  Error loading JSON {file_path}: {e}")
            return None
    
    @staticmethod
    def save_json(file_path: str, data: Dict[str, Any]) -> bool:
        """
        Save data to JSON file.
        
        Args:
            file_path: Path to JSON file
            data: Data to save as dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[FILE_MANAGER] ⚠️  Error saving JSON {file_path}: {e}")
            return False
    
    # ============================================
    #         PLAYLIST FILE MANAGEMENT
    # ============================================
    
    @staticmethod
    def check_playlist_available(playlist_path: str) -> bool:
        """
        Check if playlist file exists and has entries.
        
        Args:
            playlist_path: Path to playlist JSON file
            
        Returns:
            True if playlist file exists and has more than 1 entry
        """
        if not os.path.exists(playlist_path):
            return False
        
        try:
            data = FileManager.load_json(playlist_path)
            if data and 'entries' in data and isinstance(data['entries'], list):
                return len(data['entries']) > 1
        except Exception as e:
            print(f"[FILE_MANAGER] ⚠️  Error checking playlist: {e}")
        
        return False
    
    @staticmethod
    def load_playlist(playlist_path: str) -> Optional[Dict[str, Any]]:
        """
        Load playlist from JSON file.
        
        Args:
            playlist_path: Path to playlist JSON file
            
        Returns:
            Playlist dictionary with 'entries' key, or None if file doesn't exist
        """
        return FileManager.load_json(playlist_path)
    
    @staticmethod
    def save_playlist(playlist_path: str, playlist_data: Dict[str, Any]) -> bool:
        """
        Save playlist to JSON file.
        
        Args:
            playlist_path: Path to playlist JSON file
            playlist_data: Playlist dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        return FileManager.save_json(playlist_path, playlist_data)
    
    # ============================================
    #         FILE VALIDATION
    # ============================================
    
    @staticmethod
    def file_exists(file_path: str) -> bool:
        """Check if file exists"""
        return os.path.exists(file_path) and os.path.isfile(file_path)
    
    @staticmethod
    def directory_exists(dir_path: str) -> bool:
        """Check if directory exists"""
        return os.path.exists(dir_path) and os.path.isdir(dir_path)
    
    @staticmethod
    def ensure_directory(dir_path: str) -> bool:
        """
        Ensure directory exists, create if necessary.
        
        Args:
            dir_path: Path to directory
            
        Returns:
            True if directory exists or was created, False otherwise
        """
        try:
            os.makedirs(dir_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"[FILE_MANAGER] ⚠️  Error creating directory {dir_path}: {e}")
            return False
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """
        Get file information (size, exists, name).
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file info
        """
        info = {
            'exists': False,
            'size': 0,
            'size_mb': 0.0,
            'name': os.path.basename(file_path),
            'dir': os.path.dirname(file_path)
        }
        
        if os.path.exists(file_path):
            info['exists'] = True
            size_bytes = os.path.getsize(file_path)
            info['size'] = size_bytes
            info['size_mb'] = size_bytes / (1024 * 1024)
        
        return info


# Alias for backward compatibility (if used as a module-level class)
__all__ = ['FileManager']