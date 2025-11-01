"""
Playback Manager - Manages SID file playback, subtune navigation, and timing
Part of Phase 3 refactoring: Playback Controls
"""

import subprocess
import threading
import time
import os
from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QMessageBox

try:
    from subprocess import CREATE_NO_WINDOW, CREATE_NEW_CONSOLE
except ImportError:
    CREATE_NO_WINDOW = 0x08000000
    CREATE_NEW_CONSOLE = 0x00000010

try:
    from subprocess import DETACHED_PROCESS
except ImportError:
    DETACHED_PROCESS = 0x00000008

import sys


class PlaybackManagerMixin:
    """Mixin class for SIDPlayer handling playback control and timing"""
    
    def prev_subtune(self):
        """Przełącz na poprzedni subtune"""
        print(f"[SUBTUNE_DEBUG] prev_subtune() called: current={self.current_subtune}, max={self.num_subtunes}, is_playing={self.is_playing}")
        self.debug_console.log(f"[SUBTUNE] prev_subtune() called: current={self.current_subtune}, max={self.num_subtunes}")
        if self.current_subtune > 1:
            self.current_subtune -= 1
            print(f"[SUBTUNE_DEBUG] Decreased to {self.current_subtune}")
            self.subtune_number.setText(str(self.current_subtune))
            
            # Update duration for new subtune from Songlengths database
            if self.sid_file:
                self.total_duration = self.get_song_duration(self.sid_file, self.current_subtune)
                self.current_song_duration = self.total_duration
                self.debug_console.log(f"[SUBTUNE] Duration updated for subtune {self.current_subtune}: {self.total_duration}s")
            
            # Reset licznika czasu
            self.time_elapsed = 0
            self.update_time_label()
            self.debug_console.log(f"[SUBTUNE] ◄ Previous: {self.current_subtune}/{self.num_subtunes}")
            # Refresh button states after changing subtune
            self.update_ui_state()

            if self.is_playing:
                if self.audio_engine == "jsidplay2":
                    # jsidplay2 nie obsługuje arrow keys - trzeba zrestartować playback
                    print(f"[SUBTUNE_DEBUG] Playing jsidplay2 - restarting with new subtune")
                    self.debug_console.log(f"[SUBTUNE] jsidplay2 detected - restarting playback with new subtune")
                    self.stop_sid_file()
                    self.start_playing()
                else:
                    # Dla sidplayfp wyślij LEFT arrow za pomocą PostMessage
                    print(f"[SUBTUNE_DEBUG] Playing - sending LEFT arrow to sidplayfp")
                    success = self.simulate_arrow_key_left_right(is_left=True)
                    if success:
                        self.debug_console.log(f"[SUBTUNE] ◄ LEFT arrow sent successfully")
                    else:
                        self.debug_console.log(f"[SUBTUNE] ◄ Failed to send LEFT arrow")
            else:
                # Jeśli nie odtwarza, zatrzymaj i uruchom ponownie z nowym subtune
                print(f"[SUBTUNE_DEBUG] Not playing, restarting...")
                self.stop_sid_file()
                self.start_playing()
        else:
            print(f"[SUBTUNE_DEBUG] Already at minimum, cannot go previous")
            self.debug_console.log(f"[SUBTUNE] ◄ Cannot go previous (already at min: {self.current_subtune})")

    def next_subtune(self):
        """Przełącz na następny subtune"""
        print(f"[SUBTUNE_DEBUG] next_subtune() called: current={self.current_subtune}, max={self.num_subtunes}, is_playing={self.is_playing}")
        self.debug_console.log(f"[SUBTUNE] next_subtune() called: current={self.current_subtune}, max={self.num_subtunes}")
        if self.current_subtune < self.num_subtunes:
            self.current_subtune += 1
            print(f"[SUBTUNE_DEBUG] Increased to {self.current_subtune}")
            self.subtune_number.setText(str(self.current_subtune))
            
            # Update duration for new subtune from Songlengths database
            if self.sid_file:
                self.total_duration = self.get_song_duration(self.sid_file, self.current_subtune)
                self.current_song_duration = self.total_duration
                self.debug_console.log(f"[SUBTUNE] Duration updated for subtune {self.current_subtune}: {self.total_duration}s")
            
            # Reset licznika czasu
            self.time_elapsed = 0
            self.update_time_label()
            self.debug_console.log(f"[SUBTUNE] ► Next: {self.current_subtune}/{self.num_subtunes}")
            # Refresh button states after changing subtune
            self.update_ui_state()

            if self.is_playing:
                if self.audio_engine == "jsidplay2":
                    # jsidplay2 nie obsługuje arrow keys - trzeba zrestartować playback
                    print(f"[SUBTUNE_DEBUG] Playing jsidplay2 - restarting with new subtune")
                    self.debug_console.log(f"[SUBTUNE] jsidplay2 detected - restarting playback with new subtune")
                    self.stop_sid_file()
                    self.start_playing()
                else:
                    # Dla sidplayfp wyślij RIGHT arrow za pomocą PostMessage
                    print(f"[SUBTUNE_DEBUG] Playing - sending RIGHT arrow to sidplayfp")
                    success = self.simulate_arrow_key_left_right(is_left=False)
                    if success:
                        self.debug_console.log(f"[SUBTUNE] ► RIGHT arrow sent successfully")
                    else:
                        self.debug_console.log(f"[SUBTUNE] ► Failed to send RIGHT arrow")
            else:
                # Jeśli nie odtwarza, zatrzymaj i uruchom ponownie z nowym subtune
                print(f"[SUBTUNE_DEBUG] Not playing, restarting...")
                self.stop_sid_file()
                self.start_playing()
        else:
            print(f"[SUBTUNE_DEBUG] Already at maximum, cannot go next")
            self.debug_console.log(f"[SUBTUNE] ► Cannot go next (already at max: {self.current_subtune})")

    def prev_song(self):
        """Przejdź do poprzedniej piosenki w playliście"""
        if (self.playlist_window is not None and
            hasattr(self.playlist_window, 'get_previous_song')):
            prev_entry = self.playlist_window.get_previous_song()
            if prev_entry:
                self.debug_console.log(f"[PLAYLIST] Previous song: {prev_entry.title}")
                self.play_song_from_playlist(prev_entry.file_path, prev_entry.duration)
            else:
                self.debug_console.log("[PLAYLIST] No previous song available")
        elif self._check_playlist_available_from_file():
            # Playlist file exists but window not open - open it first (hidden for auto operations)
            self.debug_console.log("[PLAYLIST] Opening playlist window for previous song")
            self.open_playlist(show_window=False)
            # After opening, try again
            if (self.playlist_window is not None and
                hasattr(self.playlist_window, 'get_previous_song')):
                prev_entry = self.playlist_window.get_previous_song()
                if prev_entry:
                    self.debug_console.log(f"[PLAYLIST] Previous song: {prev_entry.title}")
                    self.play_song_from_playlist(prev_entry.file_path, prev_entry.duration)
                else:
                    self.debug_console.log("[PLAYLIST] No previous song available")

    def next_song(self):
        """Przejdź do następnej piosenki w playliście"""
        if (self.playlist_window is not None and
            hasattr(self.playlist_window, 'get_next_song')):
            next_entry = self.playlist_window.get_next_song()
            if next_entry:
                self.debug_console.log(f"[PLAYLIST] Next song: {next_entry.title}")
                self.play_song_from_playlist(next_entry.file_path, next_entry.duration)
            else:
                self.debug_console.log("[PLAYLIST] No next song available")
        elif self._check_playlist_available_from_file():
            # Playlist file exists but window not open - open it first (hidden for auto operations)
            self.debug_console.log("[PLAYLIST] Opening playlist window for next song")
            self.open_playlist(show_window=False)
            # After opening, try again
            if (self.playlist_window is not None and
                hasattr(self.playlist_window, 'get_next_song')):
                next_entry = self.playlist_window.get_next_song()
                if next_entry:
                    self.debug_console.log(f"[PLAYLIST] Next song: {next_entry.title}")
                    self.play_song_from_playlist(next_entry.file_path, next_entry.duration)
                else:
                    self.debug_console.log("[PLAYLIST] No next song available")

    def start_playing(self):
        """Start playback of the selected SID file with chosen audio engine and subtune"""
        if not self.sid_file:
            QMessageBox.warning(self, "Warning", "Najpierw przeciągnij plik .SID.")
            return

        # Jeśli metadane nie są jeszcze wczytane (załadowany z settings), wczytaj je teraz
        if self.title_label.text() in ["DROP A SID FILE", "UNKNOWN TITLE"]:
            self.read_metadata(self.sid_file)
            self.current_song_duration = self.get_song_duration(self.sid_file)
            self.total_duration = self.current_song_duration
            self.update_time_label()

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1)
            except Exception:
                pass
            self.process = None

        self.time_elapsed = 0
        # NIE resetuj self.total_duration - jest już ustawiony w dropEvent()
        # self.total_duration powinno pozostać ustawione, by timer mógł pokazać prawidłowy czas
        self.playback_started = False  # Resetuj flagę
        self.is_playing = True
        self.playback_speed_multiplier = 1  # Reset speed to 1x
        self.arrow_key_net_count = 0  # Reset arrow key count
        self.debug_console.log("[START] start_playing() called")  # LOG STARTOWANIA
        self.update_status_label()  # Update status with proper styling
        self.update_button_style()  # Update button to default style
        self.update_ui_state()
        self.update_time_label()

        # Przygotowanie komendy
        # WAŻNE: W interactive mode sidplayfp chce prostych flag!
        # Użyj wybranego audio engine
        engine_executable = self.available_engines.get(self.audio_engine, self.sidplayfp_path)
        
        # SPRAWDZENIE: Czy plik silnika audio istnieje?
        if not os.path.exists(engine_executable):
            engine_name = self.audio_engine if self.audio_engine in self.available_engines else "default"
            self.debug_console.log(f"[ERROR] Engine executable not found: {engine_executable}")
            self.is_playing = False
            self.update_ui_state()
            QMessageBox.critical(
                self, 
                "Audio Engine Not Found", 
                f"Engine '{engine_name}' not found at:\n{engine_executable}\n\n"
                f"Available engines in directory:\n"
                f"- sidplayfp.exe\n"
                f"- jsidplay2-console.exe"
            )
            return
        
        # Upewnij się że ścieżka ma prawidłowe backslashe na Windowsie
        sid_path = os.path.normpath(str(self.sid_file))
        
        # DEBUG: wyświetl jaką wartość mamy
        self.debug_console.log(f"[DEBUG] self.current_song_duration = {self.current_song_duration}s")
        
        # Buduj komendę w zależności od wybranego engine'a
        if self.audio_engine == "jsidplay2":
            # jsidplay2-console wymaga parametrów w tej kolejności:
            # jsidplay2-console.exe --engine USBSID --usbSidAudio 1 [--tune N] file.sid
            # Note: --tune parameter may or may not be supported, depending on jsidplay2 version
            command = [engine_executable]
            command.append("--engine")
            command.append("USBSID")
            command.append("--usbSidAudio")
            command.append("1")
            # Spróbuj dodać parametr --tune jeśli jest dostępny
            # (some versions of jsidplay2 support it, others don't)
            if self.current_subtune > 1:
                command.append("--tune")
                command.append(str(self.current_subtune))
            command.append(sid_path)
            self.debug_console.log(f"[INFO] jsidplay2: Playing with USBSID engine, subtune {self.current_subtune}/{self.num_subtunes}")
        else:
            # sidplayfp wymaga formatu: sidplayfp.exe -s<subtune> [-ol | -t<time>] file.sid
            command = [engine_executable]
            
            # Dodaj parametr subtune
            command.append(f"-s{self.current_subtune}")
            self.debug_console.log(f"[INFO] sidplayfp: Playing subtune {self.current_subtune}/{self.num_subtunes}")
            
            # Dodaj looping lub czas odtwarzania
            if self.loop_enabled:
                command.append("-ol")  # Looping mode
            else:
                # Bez loopingu - określ czas utworu
                # Sidplayfp wymaga formatu: -t[mins:]secs[.milli]
                # ZAWSZE używamy M:SS format z separatorem ':' (bez wiodących zer dla minut!)
                # Przykład: -t0:42, -t1:30, -t2:15
                minutes = self.current_song_duration // 60
                seconds = self.current_song_duration % 60
                time_arg = f"{minutes}:{seconds:02d}"
                self.debug_console.log(f"[DEBUG] time_arg = '{time_arg}'")
                # Sidplayfp wymaga -t BEZPOŚREDNIO z wartością bez spacji: -t0:42
                command.append(f"-t{time_arg}")
            
            command.append(sid_path)
        
        self.debug_console.log(f"[INFO] Uruchamianie: {' '.join(command)}")

        try:
            # Uruchomienie silnika audio - konsola jest tworzona ale od razu ukryta, stdin dostępny dla arrow keys
            creationflags = 0
            startupinfo = None
            
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags = 1  # STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE - okno startuje jako ukryte
                creationflags = CREATE_NEW_CONSOLE
            
            self.debug_console.log(f"[INFO] 🎯 Starting {self.audio_engine} engine: {command[0]}")
            
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                startupinfo=startupinfo,
                creationflags=creationflags,
                universal_newlines=True,
                bufsize=1  # Line-buffered - ważne dla stdin
            )
            self.debug_console.log(f"[INFO] ✓ Process created: PID={self.process.pid}, engine={self.audio_engine}")
            self.debug_console.log(f"[INFO] ⏳ Waiting for {self.audio_engine} to start playback...")
            
            # Uruchom thread do ukrycia konsoli (zaraz po starcie)
            hide_thread = threading.Thread(target=self.hide_console_window_for_sidplay, daemon=True)
            hide_thread.start()
            
            # Uruchom thread do monitorowania startu playbacku
            monitor_thread = threading.Thread(target=self.monitor_playback_start, daemon=True)
            monitor_thread.start()
            
        except FileNotFoundError:
            engine_name = self.audio_engine if self.audio_engine in self.available_engines else "unknown"
            QMessageBox.critical(
                self, 
                "Audio Engine Error", 
                f"Engine '{engine_name}' executable not found:\n{engine_executable}"
            )
            self.is_playing = False
            self.update_ui_state()
        except Exception as e:
            QMessageBox.critical(self, "Runtime Error", str(e))
            self.is_playing = False
            self.update_ui_state()

    def pause_playing(self):
        """Pause/Resume playback - obsługuje zarówno jsidplay2 jak i sidplayfp"""
        if self.is_playing:
            if self.audio_engine == "jsidplay2":
                # Dla jsidplay2: zarządzaj timerem ORAZ wysyłaj 'p' do procesu
                if self.timer.isActive():
                    # Timer jest aktywny = muzykę odtwarzana, wciśnięto PAUSE → zatrzymaj
                    self.timer.stop()
                    self.debug_console.log("[PAUSE] ⏸ jsidplay2: Timer stopped (PAUSED)")
                else:
                    # Timer jest nieaktywny = muzykę na pauzie, wciśnięto PAUSE → wznów
                    self.timer.start(1000)  # Wznów licznik
                    self.debug_console.log("[PAUSE] ▶ jsidplay2: Timer started (RESUMED)")
                
                pause_success = False
                
                # LEVEL 1: Spróbuj wysłać 'p' przez STDIN (najskuteczniejsze!)
                if self.process and self.process.stdin:
                    try:
                        self.debug_console.log("[PAUSE] 📋 Level 1: Attempting stdin input...")
                        self.process.stdin.write("p\n")
                        self.process.stdin.flush()
                        self.debug_console.log("[PAUSE] ✓ 'p' command sent via stdin to jsidplay2")
                        pause_success = True
                    except Exception as e:
                        self.debug_console.log(f"[PAUSE] ✗ stdin write failed: {e}")
                
                # LEVEL 2: Jeśli stdin nie zadziałał, spróbuj PostMessage API
                if not pause_success:
                    self.debug_console.log("[PAUSE] 📋 Level 2: Attempting PostMessage API...")
                    success = self.send_char_sequence_to_console(['p'])
                    
                    if success:
                        self.debug_console.log("[PAUSE] ✓ 'p' key sent via PostMessage to jsidplay2")
                    else:
                        self.debug_console.log("[PAUSE] ✗ PostMessage failed - window not found")
            else:
                # Dla sidplayfp: zarządzaj timerem i wysyłaj 'p' poprzez key simulation
                if self.timer.isActive():
                    # Timer jest aktywny = muzykę odtwarzana, wciśnięto PAUSE → zatrzymaj
                    self.timer.stop()
                    self.debug_console.log("[PAUSE] ⏸ sidplayfp: Timer stopped (PAUSED)")
                    
                    # Wysłanie 'p' przez key simulation (PostMessage)
                    success = self.send_key_to_sidplay('p')
                    if success:
                        self.debug_console.log("[PAUSE] ✓ 'p' key sent via PostMessage to sidplayfp")
                    else:
                        self.debug_console.log("[PAUSE] ✗ Failed to send 'p' key to sidplayfp")
                else:
                    # Timer jest nieaktywny = muzykę na pauzie, wciśnięto PAUSE → wznów
                    self.timer.start(1000)  # Wznów licznik
                    self.debug_console.log("[PAUSE] ▶ sidplayfp: Timer started (RESUMED)")
                    
                    # Wysłanie 'p' przez key simulation (PostMessage)
                    success = self.send_key_to_sidplay('p')
                    if success:
                        self.debug_console.log("[PAUSE] ✓ 'p' key sent via PostMessage to sidplayfp")
                    else:
                        self.debug_console.log("[PAUSE] ✗ Failed to send 'p' key to sidplayfp")
    
    def stop_sid_file(self):
        """Zatrzymaj playback - dla jsidplay2 wyślij 'q', dla sidplayfp używaj terminate"""
        if self.process:
            try:
                # Dla jsidplay2, spróbuj graceful shutdown przez wysłanie 'q'
                if self.audio_engine == "jsidplay2":
                    self.debug_console.log("[STOP] 🎵 jsidplay2 detected - attempting graceful shutdown")
                    
                    graceful_success = False
                    
                    # LEVEL 1: Spróbuj wysłać 'q' przez STDIN (najskuteczniejsze!)
                    if self.process.stdin:
                        try:
                            self.debug_console.log("[STOP] 📋 Level 1: Attempting stdin input...")
                            self.process.stdin.write("q\n")
                            self.process.stdin.flush()
                            self.debug_console.log("[STOP] ✓ 'q' command sent via stdin - this should terminate jsidplay2 AND java.exe")
                            graceful_success = True
                        except Exception as e:
                            self.debug_console.log(f"[STOP] ✗ stdin write failed: {e}")
                    
                    # LEVEL 2: Jeśli stdin nie zadziałał, spróbuj PostMessage API
                    if not graceful_success:
                        self.debug_console.log("[STOP] 📋 Level 2: Attempting PostMessage API...")
                        success = self.send_char_sequence_to_console(['q'])
                        
                        if success:
                            self.debug_console.log("[STOP] ✓ 'q' key sequence sent via PostMessage")
                            graceful_success = True
                        else:
                            self.debug_console.log("[STOP] ✗ PostMessage failed - console window may not be found")
                    
                    # LEVEL 3: Czekaj na graceful shutdown lub fallback
                    if graceful_success:
                        try:
                            self.process.wait(timeout=2)
                            self.debug_console.log("[STOP] ✓ jsidplay2 process closed gracefully (including java.exe)")
                        except subprocess.TimeoutExpired:
                            self.debug_console.log("[STOP] ⚠ Timeout: graceful shutdown took too long - forcing kill")
                            self.process.kill()
                            try:
                                self.process.wait(timeout=1)
                            except:
                                pass
                            self.debug_console.log("[STOP] ✓ Process force-killed")
                    else:
                        # Fallback: terminate
                        self.debug_console.log("[STOP] 📋 Level 3: Attempting terminate() fallback...")
                        try:
                            self.process.terminate()
                            self.process.wait(timeout=2)
                            self.debug_console.log("[STOP] ✓ Fallback terminate() executed")
                        except subprocess.TimeoutExpired:
                            self.debug_console.log("[STOP] ⚠ Timeout: process did not terminate - forcing kill")
                            self.process.kill()
                            try:
                                self.process.wait(timeout=1)
                            except:
                                pass
                            self.debug_console.log("[STOP] ✓ Process force-killed")
                        except Exception as e:
                            self.debug_console.log(f"[STOP] ✗ Fallback terminate() failed: {e}")
                else:
                    # Dla sidplayfp, używaj stdin + terminate
                    self.debug_console.log("[STOP] 🎵 sidplayfp detected - using stdin method")
                    
                    graceful_success = False
                    if self.process.stdin:
                        try:
                            self.process.stdin.write("q\n")
                            self.process.stdin.flush()
                            self.debug_console.log("[STOP] ✓ 'q' command sent via stdin to sidplayfp")
                            graceful_success = True
                        except Exception as e:
                            self.debug_console.log(f"[STOP] ✗ stdin write failed: {e}")
                    
                    # Czekaj max 2 sekundy
                    try:
                        self.process.wait(timeout=2)
                        self.debug_console.log("[STOP] ✓ sidplayfp process closed gracefully")
                    except subprocess.TimeoutExpired:
                        # Jeśli nie umiera, zrób hard kill
                        self.debug_console.log("[STOP] ⚠ Timeout: process did not close after 2 seconds - forcing kill")
                        self.process.kill()
                        try:
                            self.process.wait(timeout=1)
                        except:
                            pass
                        self.debug_console.log("[STOP] ✓ Process force-killed")
            except Exception as e:
                self.debug_console.log(f"[STOP] ✗ Error during graceful shutdown: {e}")
            finally:
                self.process = None

        self.timer.stop()
        self.is_playing = False
        self.time_elapsed = 0
        self.total_duration = 0  # Resetuj całkowity czas
        self.playback_speed_multiplier = 1  # Resetuj mnożnik prędkości
        self.arrow_key_net_count = 0  # Resetuj licznik arrow keys
        self.is_seeking = False  # Resetuj flagę seek'u
        self.update_status_label()  # Update status with proper styling
        self.update_button_style()  # Reset button to default style
        self.update_time_label()
        self.update_ui_state()
        self.progress_bar.setValue(0)

    def update_time(self):
        """Update time display - sidplayfp zarządza końcem odtwarzania."""
        # Inkrementuj czas uwzględniając aktualną prędkość
        self.time_elapsed += self.playback_speed_multiplier
        self.update_time_label()
        
        # Aktualizuj pasek postępu
        if self.total_duration > 0:
            progress = int((self.time_elapsed / self.total_duration) * 100)
            if progress > 100:
                progress = progress % 100
            self.progress_bar.setValue(progress)
            
            # Sprawdź czy muzyka się skończyła
            if self.time_elapsed >= self.total_duration:
                if self.loop_enabled:
                    # Loop jest włączony - resetuj licznik ale nie stop
                    self.time_elapsed = 0
                    self.progress_bar.setValue(0)
                    self.update_time_label()
                    self.debug_console.log(f"[LOOP] ✓ Song ended, looping... (resetting timer)")
                else:
                    # Loop jest wyłączony - sprawdź czy jest następna piosenka w playliście
                    if self._check_playlist_available_from_file():
                        self.debug_console.log(f"[PLAYBACK] ✓ Song ended, auto-advancing to next song")
                        self.next_song()
                    else:
                        # Brak playlisty - zatrzymaj muzykę
                        self.debug_console.log(f"[PLAYBACK] ✓ Song ended, stopping playback")
                        self.timer.stop()
                        self.stop_sid_file()  # Wyślij sygnał STOP
    
    def update_time(self):
        """Callback wywołany co sekundę przez timer - aktualizuje czas i progress"""
        if self.is_playing:
            self.time_elapsed += 1
            
            # Aktualizuj label czasowy
            self.update_time_label()
            
            # Aktualizuj progress bar
            if self.total_duration > 0:
                progress = int((self.time_elapsed / self.total_duration) * 100)
                progress = min(progress, 100)  # Nie przechodzę powyżej 100%
                self.progress_bar.setValue(progress)
            
            # Sprawdzenie czy utwór się skończył
            if self.total_duration > 0 and self.time_elapsed >= self.total_duration:
                # Utwór się skończył
                if self.loop_enabled:
                    # Loop włączony - resetuj timer
                    self.time_elapsed = 0
                    self.progress_bar.setValue(0)
                    self.update_time_label()
                    self.debug_console.log(f"[LOOP] ✓ Song ended, looping... (resetting timer)")
                else:
                    # Loop jest wyłączony - sprawdź czy jest następna piosenka w playliście
                    if self._check_playlist_available_from_file():
                        self.timer.stop()
                        self.next_song()
                    else:
                        # Brak playlisty - zatrzymaj muzykę
                        self.debug_console.log(f"[PLAYBACK] ✓ Song ended, stopping playback")
                        self.timer.stop()
                        self.stop_sid_file()  # Wyślij sygnał STOP
            
    def update_time_label(self):
        """Wyświetl elapsed time i total duration w formacie mm:ss / mm:ss"""
        elapsed = QTime(0, 0).addSecs(self.time_elapsed).toString("mm:ss")
        if self.total_duration > 0:
            total = QTime(0, 0).addSecs(self.total_duration).toString("mm:ss")
            self.time_label.setText(f"{elapsed} / {total}")
        else:
            self.time_label.setText(elapsed)

    def on_playback_started(self, elapsed_time):
        """Slot wywoływany z daemon thread poprzez sygnał - startuje timer w main thread"""
        self.time_elapsed = elapsed_time
        self.playback_started = True
        msg = f"[INFO] ✓ Timer started from main thread at {elapsed_time}s"
        self.debug_console.log(msg)
        self.timer.start(1000)  # 1000ms = 1 sekunda

    def monitor_playback_start(self):
        """Monitor audio engine output to detect when playback actually starts."""
        try:
            self.debug_console.log(f"[MONITOR] monitor_playback_start() thread started for {self.audio_engine}")
            timeout_counter = 0
            max_timeout = 100  # 10 sekund
            playback_detected = False
            last_log_line = ""  # Aby nie drukować tych samych linii w pętli
            
            # Różne sygnatury "Playing" dla różnych engines
            is_jsidplay2 = self.audio_engine == "jsidplay2"
            
            while self.process and self.process.poll() is None and self.is_playing:
                try:
                    # Czytaj linię w trybie binarnym i zdekoduj
                    line = self.process.stdout.readline()
                    
                    if not line:
                        timeout_counter += 1
                        if timeout_counter > max_timeout:
                            if not playback_detected:
                                msg = f"[WARN] Timeout: nie otrzymano odpowiedzi od {self.audio_engine} w ciągu 10 sekund"
                                self.debug_console.log(msg)
                                msg2 = "[INFO] ⏱️ Emitting signal to start timer from main thread (timeout)..."
                                self.debug_console.log(msg2)
                                # Emit signal - timer będzie startowany z main thread
                                self.playback_started_signal.emit(0)
                            break
                        time.sleep(0.01)
                        continue
                    
                    timeout_counter = 0  # Reset timeout
                    # Dekoduj bytes do string
                    try:
                        line = line.decode('utf-8', errors='ignore').strip()
                    except:
                        line = str(line).strip()
                    
                    if line:
                        # Filtruj komunikaty w zależności od engine'a
                        should_log = True
                        
                        if is_jsidplay2:
                            # jsidplay2 ma inne komunikaty - ignoruj powtarzające się
                            # Przykład output: "tune 1/1" itp.
                            if "tune" in line and line == last_log_line:
                                should_log = False
                        else:
                            # sidplayfp - ignoruj linijki które tylko powtarzają "Playing, press ESC to stop..."
                            if line.startswith("Playing, press ESC to stop"):
                                should_log = False
                        
                        if should_log and line != last_log_line:
                            engine_label = "JSIDPLAY2" if is_jsidplay2 else "SIDPLAYFP"
                            self.debug_console.log(f"[{engine_label}] {line}")
                            last_log_line = line
                            
                            # Fallback: parsuj Song Length z outputu jeśli potrzeba
                            if "Song Length" in line and self.total_duration == 0:
                                try:
                                    # Ekstrahuj czas (mm:ss.xx format)
                                    parts = line.split(":")
                                    if len(parts) >= 2:
                                        mins = int(parts[1].strip())
                                        secs_str = parts[2].split("|")[0].strip()
                                        secs = float(secs_str)
                                        self.total_duration = mins * 60 + int(secs)
                                        self.debug_console.log(f"[INFO] ✓ Song Length fallback: {self.total_duration}s")
                                        self.update_time_label()
                                except Exception as e:
                                    self.debug_console.log(f"[WARN] Nie udało się sparsować Song Length: {e}")
                        
                        # Czekaj na sygnał że muzyka się odtwarza
                        # Dla obu engines - jeśli otrzymaliśmy jakieś output z muzyką, to znaczy że się gra
                        playback_markers = ["Playing", "tune", "Playback"]  # Różne markery dla różnych engines
                        if not playback_detected and any(marker in line for marker in playback_markers):
                            playback_detected = True
                            msg = f"[INFO] ✓ Playback detected ({self.audio_engine})! Starting timer immediately..."
                            self.debug_console.log(msg)
                            # Emit signal - timer będzie startowany z main thread
                            self.playback_started_signal.emit(0)
                            self.debug_console.log("[MONITOR] Signal emitted! Continuing to monitor...")
                        
                except Exception as e:
                    msg = f"[WARN] Błąd czytania stdout: {e}"
                    self.debug_console.log(msg)
                    break
                    
        except Exception as e:
            msg = f"[ERROR] Monitor thread error: {e}"
            self.debug_console.log(msg)
        finally:
            self.debug_console.log("[MONITOR] monitor_playback_start() thread FINISHED")