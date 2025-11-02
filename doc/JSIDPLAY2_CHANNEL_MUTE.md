# JSidplay2 Channel Muting Feature

## Overview

This document describes the implementation of audio channel muting functionality for the JSidplay2 audio engine in the SID Player application.

## Feature Description

### What It Does

When using JSidplay2 as the audio engine, the application now automatically mutes all 12 audio channels during specific playback events to prevent audio glitches and provide smoother transitions:

1. **PAUSE Button (Toggle)**:
   - **1st Press**: Mutes all channels
   - **2nd Press**: Unmutes all channels (resumes playback)
   - Tracks mute state to correctly toggle between mute/unmute

2. **STOP Button**:
   - Automatically mutes all channels before stopping playback

3. **NEXT SONG Button**:
   - Automatically mutes all channels before navigating to the next song

4. **PREV SONG Button**:
   - Automatically mutes all channels before navigating to the previous song

5. **New Playback**:
   - Resets mute state when starting a new song (assumes unmuted at start)

## Implementation Details

### Channel Sequence

JSidplay2 has 12 audio channels that can be individually muted/unmuted by sending key commands:

```
Channels 1-9:   Send '1', '2', '3', '4', '5', '6', '7', '8', '9' (one key per channel)
Channels 10-12: Send 'a', 'b', 'c' (hexadecimal notation)
```

Each key press **TOGGLES** the mute state for that channel:
- First press → Mute that channel
- Second press → Unmute that channel
- And so on...

### Mute Sequence

To mute all channels, send this exact sequence to the JSidplay2 console:
```
1, Enter
2, Enter
3, Enter
4, Enter
5, Enter
6, Enter
7, Enter
8, Enter
9, Enter
a, Enter
b, Enter
c, Enter
```

To unmute all channels, send the same sequence again (toggle behavior).

### State Tracking

The implementation tracks mute state with a boolean flag:

```python
self.jsidplay2_channels_muted = False  # False = unmuted, True = muted
```

This ensures proper toggle behavior for the PAUSE button and prevents redundant mute operations.

## Code Changes

### Files Modified

1. **`playback_manager.py`** - Added mute management methods and integrated into playback flow:
   - `get_jsidplay2_mute_sequence()` - Returns the channel sequence
   - `mute_all_jsidplay2_channels()` - Mutes all channels
   - `unmute_all_jsidplay2_channels()` - Unmutes all channels
   - `ensure_muted_before_navigation()` - Mutes before navigation operations
   - `reset_mute_state_on_new_playback()` - Resets state for new songs
   - Modified `pause_playing()` - Added toggle mute/unmute
   - Modified `stop_sid_file()` - Added pre-stop mute
   - Modified `next_song()` - Added pre-navigation mute
   - Modified `prev_song()` - Added pre-navigation mute
   - Modified `start_playing()` - Added mute state reset

2. **`sid_player_modern07.py`** - Added state variable initialization:
   - Added `self.jsidplay2_channels_muted` initialization in `__init__`

### Usage of Existing Methods

The implementation uses existing infrastructure:

- **`send_char_sequence_to_console()`** (from `windows_api_manager.py`):
  - Sends character sequences to the JSidplay2 console window
  - Each character is followed by an Enter key press
  - Works on Windows using PostMessage API
  - Handles window detection automatically

- **Logging** (from debug console):
  - All operations are logged with prefixes like `[MUTE]`
  - Makes troubleshooting easy

## Behavior

### JSidplay2 Only

The mute functionality is **only active** when using the JSidplay2 audio engine:

```python
if self.audio_engine == "jsidplay2":
    # Mute operations execute
else:
    # For sidplayfp: no-op (returns False or True without action)
```

### No Blocking

If mute operations fail (e.g., console window not found), they never block playback operations:

```python
# In ensure_muted_before_navigation():
success = self.send_char_sequence_to_console(mute_seq)
# Always returns True, regardless of success
return True  # Don't block navigation
```

### Logging Examples

When you press PAUSE with JSidplay2:

```
[PAUSE] ⏸ jsidplay2: Timer stopped (PAUSED)
[MUTE] 🔇 Muting all JSidplay2 channels: 1, 2, 3, 4, 5, 6, 7, 8, 9, a, b, c
[WINAPI] 🔍 Searching for jsidplay2 console window...
[WINAPI] ✓ Console window FOUND: HWND=0x...
[MUTE] ✓ All channels muted successfully
[PAUSE] ✓ 'p' command sent via stdin to jsidplay2
```

When you press PAUSE again to resume:

```
[PAUSE] ▶ jsidplay2: Timer started (RESUMED)
[MUTE] 🔊 Unmuting all JSidplay2 channels: 1, 2, 3, 4, 5, 6, 7, 8, 9, a, b, c
[WINAPI] ✓ Console window FOUND: HWND=0x...
[MUTE] ✓ All channels unmuted successfully
[PAUSE] ✓ 'p' command sent via stdin to jsidplay2
```

## Testing

### Test Case 1: PAUSE Toggle
1. Load a SID file
2. Select JSidplay2 from engine dropdown
3. Press PLAY
4. Press PAUSE (watch debug console for mute sequence)
5. Press PAUSE again (watch for unmute sequence)
6. Verify no audio glitches occur

### Test Case 2: STOP
1. Start playing with JSidplay2
2. Press STOP (watch for pre-stop mute)
3. Verify clean stop with no audio artifacts

### Test Case 3: Navigation (NEXT/PREV)
1. Play from playlist with JSidplay2
2. Press NEXT SONG (watch for pre-navigation mute)
3. Verify smooth transition to next song
4. Repeat with PREV SONG

### Test Case 4: New Playback
1. Play a song with JSidplay2 and pause it (channels muted)
2. Press PLAY to resume from same file
3. Verify mute state resets properly
4. Switch to different file and PLAY
5. Verify mute state resets for new song

## Debug Information

### Log Messages

| Message | Meaning | Status |
|---------|---------|--------|
| `🔇 Muting all JSidplay2 channels` | Sending mute sequence | ℹ️ Informational |
| `✓ All channels muted successfully` | Mute completed | ✅ Success |
| `ℹ️  Channels already muted` | Skipping redundant mute | ℹ️ Informational |
| `✗ Failed to mute channels` | Send failed (window not found) | ⚠️ Warning |
| `🔊 Unmuting all JSidplay2 channels` | Sending unmute sequence | ℹ️ Informational |
| `✓ All channels unmuted successfully` | Unmute completed | ✅ Success |
| `🔄 Mute state reset` | Reset for new playback | ℹ️ Informational |

### If Muting Doesn't Work

1. **Check Debug Console** for error messages
2. **Verify JSidplay2 is selected** (not sidplayfp)
3. **Check console window** is visible (muting requires window to be found)
4. **Run diagnostic** to verify console window detection:
   - Open Debug Console (CTRL+X)
   - Look for `[WINAPI] ✓ Console window FOUND`

## Technical Notes

### Why This Works

JSidplay2 console accepts key input when it has focus or via PostMessage API:
- Each key press toggles the mute state for that channel
- Sending 1-c in sequence toggles all 12 channels simultaneously
- The "unmute" sequence is identical to the "mute" sequence (toggle behavior)

### Why It's Needed

Without channel muting:
- Audio may "click" or "pop" when transitioning between songs
- Glitches can occur if timing is off
- User experience is degraded during rapid navigation

With channel muting:
- Clean, click-free transitions
- Smoother playback experience
- Professional-quality audio handling

### Timing

The mute sequence sends each character with a short delay:
- Each character: Send key down → key up
- Between characters: 100ms delay (via `time.sleep(0.1)`)
- Ensures JSidplay2 has time to process each key

This is handled automatically by `send_char_sequence_to_console()`.

## Compatibility

### Engines

- **JSidplay2**: ✅ Full mute support
- **Sidplayfp**: ✅ Compatible (methods return False but don't break functionality)

### Platforms

- **Windows**: ✅ Full support (uses PostMessage API)
- **Linux/Mac**: ⚠️ Limited support (stdin fallback in `send_char_sequence_to_console`)

## Future Improvements

1. **Selective channel muting**: Allow user to mute specific channels (not all 12)
2. **Mute profiles**: Save/load custom mute configurations
3. **Performance metrics**: Track mute timing impact on audio quality
4. **Configuration**: Add settings to enable/disable mute per operation

## References

- JSidplay2 Console Documentation: See `JSIDPLAY2_QUICK_REFERENCE.md`
- Windows API Implementation: See `windows_api_manager.py`
- Playback Manager: See `playback_manager.py`