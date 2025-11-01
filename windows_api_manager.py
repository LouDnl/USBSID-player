"""
Windows API Manager Mixin for SID Player
=========================================

This module provides Windows-specific API functions for console window management
and keyboard input simulation. It handles:
- Console window discovery via EnumWindows
- Window visibility control
- Virtual key simulation (arrow keys and character input)
- Cross-platform compatibility fallbacks

Author: Refactored from sid_player_modern07.py
"""

import sys
import os
import time
import ctypes
from ctypes import wintypes


class WindowsAPIManagerMixin:
    """
    Mixin class for Windows API operations.
    
    Provides methods for:
    - Finding and managing console windows
    - Simulating keyboard input to console windows
    - Cross-platform fallbacks for non-Windows systems
    
    Expected to be mixed with a class that has:
    - self.debug_console (for logging)
    - self.process (subprocess instance)
    - self.sid_file (path to currently playing file)
    - self.sidplayfp_path (path to sidplayfp executable)
    """
    
    # ================================================
    #     WINDOWS API HELPER FUNCTIONS
    # ================================================
    
    def _get_engine_hints(self):
        """
        Get search hints for current audio engine.
        Dynamically determines hints based on self.audio_engine value.
        
        Returns:
            list: Search hints for window title matching (e.g., ['jsidplay2', 'Bumper.sid', 'jsidplay2-console.exe'])
        """
        # Get the engine name from self.audio_engine
        engine_name = getattr(self, 'audio_engine', 'sidplayfp')
        
        # Map engine names to executable/hint names
        if engine_name == "jsidplay2":
            engine_hint = 'jsidplay2'
            engine_path = getattr(self, 'jsidplay2_path', '')
        else:
            engine_hint = 'sidplayfp'
            engine_path = getattr(self, 'sidplayfp_path', '')
        
        hints = [
            engine_hint,
            os.path.basename(self.sid_file) if self.sid_file else '',
            os.path.basename(engine_path) if engine_path else ''
        ]
        
        return hints
    
    def setup_windows_api(self):
        """
        Setup Windows API functions for finding console window and sending keys.
        
        Initializes user32.dll functions and their signatures for:
        - EnumWindows: Enumerate all windows
        - GetClassNameW: Get window class name
        - GetWindowTextW: Get window title
        - PostMessageW: Send messages to windows
        - ShowWindow: Control window visibility
        
        Stores references to these functions and WinAPI constants as instance variables.
        """
        try:
            self.user32 = ctypes.WinDLL('user32', use_last_error=True)
            
            # Constants for window messages and virtual keys
            self.WM_KEYDOWN = 0x0100
            self.WM_KEYUP = 0x0101
            self.VK_UP = 0x26
            self.VK_DOWN = 0x28
            self.VK_LEFT = 0x25
            self.VK_RIGHT = 0x27
            
            # API function: GetWindowThreadProcessId
            self.GetWindowThreadProcessId = self.user32.GetWindowThreadProcessId
            self.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
            self.GetWindowThreadProcessId.restype = wintypes.DWORD
            
            # API function: GetClassNameW
            self.GetClassNameW = self.user32.GetClassNameW
            self.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
            self.GetClassNameW.restype = ctypes.c_int
            
            # API function: GetWindowTextW
            self.GetWindowTextW = self.user32.GetWindowTextW
            self.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
            self.GetWindowTextW.restype = ctypes.c_int
            
            # API function: PostMessageW
            self.PostMessageW = self.user32.PostMessageW
            self.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
            self.PostMessageW.restype = wintypes.BOOL
            
            # API function: ShowWindow
            self.ShowWindow = self.user32.ShowWindow
            self.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
            self.ShowWindow.restype = wintypes.BOOL
            
            self.debug_console.log("[WINAPI] Windows API setup completed")
        except Exception as e:
            self.debug_console.log(f"[WINAPI] Failed to setup Windows API: {e}")
    
    def find_console_hwnd_for_sidplay(self, title_hints):
        """
        Search for console window (ConsoleWindowClass) for sidplayfp/jsidplay2.
        
        Uses EnumWindows callback to iterate through all windows and find
        the first ConsoleWindowClass window whose title matches one of the hints.
        
        Args:
            title_hints (list): List of strings to search for in window title
                               (case-insensitive). E.g., ['sidplayfp', 'song.sid']
        
        Returns:
            int: Window handle (HWND) if found, None otherwise
            
        Platform: Windows only - returns None on non-Windows systems
        """
        if sys.platform != "win32":
            return None
            
        matches = []
        all_console_windows = []  # For diagnostics
        
        def enum_callback(hwnd, lParam):
            try:
                buf = ctypes.create_unicode_buffer(256)
                self.GetClassNameW(hwnd, buf, 256)
                if buf.value != 'ConsoleWindowClass':
                    return True
                
                # Found a console window - log it for diagnostics
                tbuf = ctypes.create_unicode_buffer(512)
                self.GetWindowTextW(hwnd, tbuf, 512)
                title = tbuf.value
                all_console_windows.append((hwnd, title))
                
                # Check if title matches any hint
                title_lower = title.lower()
                for hint in title_hints:
                    if hint and hint.lower() in title_lower:
                        matches.append(hwnd)
                        return False  # Stop enumeration
                return True
            except Exception as e:
                self.debug_console.log(f"[WINAPI] Error in enum_callback: {e}")
                return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        enum_proc = EnumWindowsProc(enum_callback)
        
        try:
            self.user32.EnumWindows(enum_proc, 0)
        except Exception as e:
            self.debug_console.log(f"[WINAPI] EnumWindows error: {e}")
        
        # Log diagnostics if no match found
        if not matches and all_console_windows:
            self.debug_console.log(f"[WINAPI] 📊 Found {len(all_console_windows)} console window(s) but NO MATCH:")
            for hwnd, title in all_console_windows:
                self.debug_console.log(f"[WINAPI]   - HWND={hex(hwnd)}: '{title}'")
            self.debug_console.log(f"[WINAPI]   Searching for hints: {[h for h in title_hints if h]}")
        
        return matches[0] if matches else None
    
    def hide_console_window_for_sidplay(self):
        """
        Hide console window for sidplayfp/jsidplay2 after it's found.
        
        Attempts to find and hide the console window completely (no taskbar icon).
        Retries for up to 3 seconds with short intervals to handle delayed window creation.
        
        Returns:
            bool: True if console was hidden, False if not found or error occurred
            
        Platform: Windows only - returns False on non-Windows systems
        """
        if sys.platform != "win32" or not self.sid_file:
            return False
            
        hints = self._get_engine_hints()
        
        # Try for 3 seconds with short intervals (150 attempts * 0.02s)
        for attempt in range(150):
            hwnd = self.find_console_hwnd_for_sidplay(hints)
            if hwnd:
                # Hide window completely (no taskbar icon)
                SW_HIDE = 0
                self.ShowWindow(hwnd, SW_HIDE)
                self.debug_console.log(f"[WINAPI] ✓ Console window hidden: HWND={hwnd} (attempt {attempt+1})")
                # Additional hiding after short delay (sometimes window tries to show again)
                time.sleep(0.05)
                self.ShowWindow(hwnd, SW_HIDE)
                return True
            time.sleep(0.02)  # Short intervals = faster detection
        
        self.debug_console.log("[WINAPI] ⚠ Console window not found for hiding after 3 seconds")
        return False
    
    def simulate_arrow_key(self, is_up_arrow=True):
        """
        Simulate UP or DOWN ARROW key press to console window.
        
        Uses PostMessage to send WM_KEYDOWN and WM_KEYUP messages to the
        console window running sidplayfp/jsidplay2.
        
        Args:
            is_up_arrow (bool): True to simulate UP arrow, False for DOWN arrow
        
        Returns:
            bool: True if key was sent successfully, False if window not found or error
            
        Platform: Windows only - returns False on non-Windows systems
        """
        if sys.platform != "win32" or not self.process or not self.sid_file:
            return False
            
        hints = self._get_engine_hints()
        
        hwnd = self.find_console_hwnd_for_sidplay(hints)
        if not hwnd:
            self.debug_console.log("[WINAPI] Console window not found for key simulation")
            return False
        
        vk_code = self.VK_UP if is_up_arrow else self.VK_DOWN
        scan = 0x48 if is_up_arrow else 0x50  # Scancodes for UP/DOWN arrows
        repeat = 1
        extended = 1
        
        # lParam for key messages
        lparam_down = (repeat & 0xFFFF) | ((scan & 0xFF) << 16) | (extended << 24)
        lparam_up = lparam_down | (1 << 30) | (1 << 31)
        
        try:
            self.PostMessageW(hwnd, self.WM_KEYDOWN, vk_code, lparam_down)
            self.PostMessageW(hwnd, self.WM_KEYUP, vk_code, lparam_up)
            key_name = "UP" if is_up_arrow else "DOWN"
            self.debug_console.log(f"[WINAPI] {key_name} ARROW sent to HWND={hwnd}")
            return True
        except Exception as e:
            self.debug_console.log(f"[WINAPI] PostMessage error: {e}")
            return False
    
    def simulate_arrow_key_left_right(self, is_left=True):
        """
        Simulate LEFT or RIGHT ARROW key press to console window.
        
        Uses PostMessage to send WM_KEYDOWN and WM_KEYUP messages to the
        console window running sidplayfp/jsidplay2.
        
        Args:
            is_left (bool): True to simulate LEFT arrow, False for RIGHT arrow
        
        Returns:
            bool: True if key was sent successfully, False if window not found or error
            
        Platform: Windows only - returns False on non-Windows systems
        """
        if sys.platform != "win32" or not self.process or not self.sid_file:
            return False
            
        hints = self._get_engine_hints()
        
        hwnd = self.find_console_hwnd_for_sidplay(hints)
        if not hwnd:
            self.debug_console.log("[WINAPI] Console window not found for key simulation")
            return False
        
        # Virtual key codes for LEFT/RIGHT ARROW
        vk_code = self.VK_LEFT if is_left else self.VK_RIGHT
        scan = 0x4B if is_left else 0x4D  # Scancodes for LEFT/RIGHT arrows
        repeat = 1
        extended = 1
        
        # lParam for key messages
        lparam_down = (repeat & 0xFFFF) | ((scan & 0xFF) << 16) | (extended << 24)
        lparam_up = lparam_down | (1 << 30) | (1 << 31)
        
        try:
            self.PostMessageW(hwnd, self.WM_KEYDOWN, vk_code, lparam_down)
            self.PostMessageW(hwnd, self.WM_KEYUP, vk_code, lparam_up)
            key_name = "LEFT" if is_left else "RIGHT"
            self.debug_console.log(f"[WINAPI] {key_name} ARROW sent to HWND={hwnd}")
            return True
        except Exception as e:
            self.debug_console.log(f"[WINAPI] PostMessage error: {e}")
            return False
    
    def send_key_to_sidplay(self, key_char):
        """
        Send any single character key to sidplayfp console.
        
        Cross-platform implementation:
        - Windows: Uses PostMessage to send key to console window
        - Other systems: Uses stdin input fallback via send_input_to_sidplay()
        
        Args:
            key_char (str): Single character to send (e.g., 'p' for pause)
        
        Returns:
            bool: True if key was sent successfully, False otherwise
            
        Note:
            Requires self.send_input_to_sidplay() method for non-Windows fallback
        """
        if not self.process or not self.sid_file:
            return False
        
        if sys.platform == "win32":
            # On Windows use PostMessage
            hints = self._get_engine_hints()
            
            hwnd = self.find_console_hwnd_for_sidplay(hints)
            if not hwnd:
                self.debug_console.log(f"[WINAPI] Console window not found for key '{key_char}'")
                return False
            
            # Virtual key codes for letters
            vk_map = {
                'p': 0x50,  # VK_P
                'P': 0x50,  # VK_P (uppercase)
            }
            
            vk_code = vk_map.get(key_char, ord(key_char.upper()))
            scan = 0x19  # Scancode for P
            repeat = 1
            extended = 0
            
            lparam_down = (repeat & 0xFFFF) | ((scan & 0xFF) << 16) | (extended << 24)
            lparam_up = lparam_down | (1 << 30) | (1 << 31)
            
            try:
                self.PostMessageW(hwnd, self.WM_KEYDOWN, vk_code, lparam_down)
                self.PostMessageW(hwnd, self.WM_KEYUP, vk_code, lparam_up)
                self.debug_console.log(f"[WINAPI] Key '{key_char}' sent to HWND={hwnd}")
                return True
            except Exception as e:
                self.debug_console.log(f"[WINAPI] PostMessage error for key '{key_char}': {e}")
                return False
        else:
            # On other systems send to stdin
            self.send_input_to_sidplay(key_char)
            return True
    
    def send_char_sequence_to_console(self, char_list):
        """
        Send sequence of characters to jsidplay2 console (each character + Enter).
        
        Uses STDIN ONLY - PostMessage does NOT work with hidden console windows!
        
        jsidplay2 console is started with SW_HIDE (hidden), so PostMessage API 
        cannot deliver keystrokes. stdin is the ONLY reliable method.
        
        Args:
            char_list (list): List of characters to send
                             (e.g., ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c'] for muting)
        
        Returns:
            bool: True if all characters were sent successfully, False on error
            
        Note:
            Process MUST be created with stdin=subprocess.PIPE for this to work
            Each character is followed by a newline
            Critical timing: 100ms between each character for jsidplay2 to process
        """
        if not self.process or not self.sid_file:
            self.debug_console.log(f"[STDIN] ✗ Cannot send sequence: process={bool(self.process)}, sid_file={bool(self.sid_file)}")
            return False
        
        if self.process.stdin is None:
            self.debug_console.log(f"[STDIN] ✗ Process stdin is None - process may not be created with stdin=PIPE")
            return False
        
        try:
            current_engine = getattr(self, 'audio_engine', 'sidplayfp')
            self.debug_console.log(f"[STDIN] 📤 Sending sequence to ENGINE: {current_engine.upper()}")
            
            # Log exactly what sequence will be sent
            sequence_str = ' + Enter, '.join(char_list) + ' + Enter'
            self.debug_console.log(f"[STDIN] 📝 Will send sequence: {sequence_str}")
            self.debug_console.log(f"[STDIN] ⏱️  Timing: 100ms between each character (critical for JSidplay2)")
            
            # Send each character + Enter with proper timing
            for char in char_list:
                try:
                    # Send character + newline together (fast sequence)
                    self.process.stdin.write(char + '\n')
                    self.process.stdin.flush()
                    self.debug_console.log(f"[STDIN] ✓ Sent '{char}' + Enter")
                    
                    # Wait 100ms for JSidplay2 to process the command
                    time.sleep(0.10)
                    
                except BrokenPipeError:
                    self.debug_console.log(f"[STDIN] ✗ BrokenPipeError - process may have terminated")
                    return False
                except Exception as e:
                    self.debug_console.log(f"[STDIN] ✗ Error sending '{char}': {e}")
                    return False
            
            self.debug_console.log(f"[STDIN] ✓ Entire sequence sent successfully ({len(char_list)} characters)")
            return True
            
        except Exception as e:
            self.debug_console.log(f"[STDIN] ✗ Error in send_char_sequence_to_console: {e}")
            return False