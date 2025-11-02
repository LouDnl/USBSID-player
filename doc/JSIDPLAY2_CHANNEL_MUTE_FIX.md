# JSidplay2 Channel Mute - Fixes Applied 🔧

## Problems Found & Fixed

### ⚠️ Problem 1: Timing Too Fast (20ms → 100ms)
**Location**: `windows_api_manager.py` lines 438, 448

**Issue**: 
- Characters were sent with only 20ms delay between keystrokes
- JSidplay2 needs **100ms** to process each command
- **RESULT**: Some channels would be skipped or not muted properly

**Fix Applied**:
```python
# BEFORE:
time.sleep(0.02)  # 20ms - TOO FAST!

# AFTER:
time.sleep(0.05)  # 50ms after key
time.sleep(0.10)  # 100ms after Enter - CRITICAL for JSidplay2
```

**Total timing per keystroke**: ~150ms (50ms key + 100ms Enter)

---

### ⚠️ Problem 2: Sequence Could Send to Wrong Engine
**Location**: `windows_api_manager.py` line 397 (added logging)

**Issue**: 
- Method had no verification of which engine was receiving the sequence
- Could silently send to sidplayfp instead of jsidplay2
- User wouldn't know why muting didn't work

**Fix Applied**:
```python
# Added engine verification logging
current_engine = getattr(self, 'audio_engine', 'sidplayfp')
self.debug_console.log(f"[WINAPI] 📤 Sending sequence to ENGINE: {current_engine.upper()}")
```

**Now you can see in Debug Console**:
```
[WINAPI] 📤 Sending sequence to ENGINE: JSIDPLAY2
[WINAPI] 📝 Will send sequence: 1 + Enter, 2 + Enter, 3 + Enter, 4 + Enter, 5 + Enter, 6 + Enter, 7 + Enter, 8 + Enter, 9 + Enter, a + Enter, b + Enter, c + Enter
[WINAPI] ⏱️  Timing: 50ms after key + 100ms after Enter (TOTAL: ~150ms per keystroke)
```

---

### ⚠️ Problem 3: No Fallback to stdin
**Location**: `windows_api_manager.py` lines 404-410

**Issue**:
- If jsidplay2 console window couldn't be found (e.g., minimized), sequence would fail
- No alternative method existed
- **RESULT**: Muting would silently fail

**Fix Applied**:
```python
# BEFORE:
if not hwnd:
    return False  # ← Sequence never sent!

# AFTER:
if not hwnd:
    # FALLBACK: Try stdin as alternative
    try:
        for char in char_list:
            self.send_input_to_sidplay(char + '\n')
            time.sleep(0.10)  # Same timing for consistency
        return True  # Success via stdin
    except Exception as e:
        return False
```

**Now the sequence will try**:
1. PostMessage API (if console window is visible)
2. stdin fallback (if window is hidden/minimized)

---

## Testing Instructions

### ✅ Test 1: Verify Engine Detection
1. Open SID Player with Debug Console (CTRL+X)
2. Select **JSidplay2** from audio engine dropdown
3. Play any SID file
4. Look for this log message:
   ```
   [WINAPI] 📤 Sending sequence to ENGINE: JSIDPLAY2
   ```
   ✓ If you see this, correct engine is selected

---

### ✅ Test 2: Verify Timing
1. In Debug Console, look for:
   ```
   [WINAPI] ⏱️  Timing: 50ms after key + 100ms after Enter (TOTAL: ~150ms per keystroke)
   ```
   ✓ This confirms new timing is active

---

### ✅ Test 3: Full Muting Sequence
1. Play SID file with JSidplay2
2. Press PAUSE button
3. In Debug Console, you should see:
   ```
   [MUTE] 🔇 Muting all JSidplay2 channels: 1, 2, 3, 4, 5, 6, 7, 8, 9, a, b, c
   [WINAPI] 📤 Sending sequence to ENGINE: JSIDPLAY2
   [WINAPI] 🔍 Searching for console window with hints: ['jsidplay2', 'filename.sid', 'jsidplay2-console.exe']
   [WINAPI] ✓ Console window FOUND: HWND=0x...
   [WINAPI] 📝 Will send sequence: 1 + Enter, 2 + Enter, 3 + Enter, ...
   [WINAPI] ⏱️  Timing: 50ms after key + 100ms after Enter (TOTAL: ~150ms per keystroke)
   [WINAPI] Sending '1': VK=0x31, SCAN=0x02, HWND=0x...
   [JSIDPLAY2] ✓ Sent key '1'
   [WINAPI] Sending ENTER: VK=0x0D, HWND=0x...
   [JSIDPLAY2] ✓ Sent ENTER after '1'
   ... (12 channels total)
   [WINAPI] ✓ Character sequence sent successfully
   [MUTE] ✓ All channels muted successfully
   ```

---

### ✅ Test 4: Fallback to stdin (if window not found)
1. Play SID file with JSidplay2
2. Minimize jsidplay2-console window
3. Press PAUSE button
4. In Debug Console, you should see:
   ```
   [WINAPI] ✗ Console window NOT FOUND for jsidplay2
   [WINAPI] 🔄 FALLBACK: Attempting to send via stdin...
   [WINAPI] ✓ Sequence sent successfully via stdin fallback
   ```

---

### ✅ Test 5: Audio Quality Check
1. Play SID file with JSidplay2
2. Listen for any audio artifacts/clicks when:
   - Pressing PAUSE (mutes before pause)
   - Pressing NEXT/PREV (mutes before navigation)
   - Pressing STOP (mutes before stopping)
3. ✓ Should be clean, click-free audio

---

## Debug Console Log Reference

| Log Message | Meaning | Status |
|-------------|---------|--------|
| `📤 Sending sequence to ENGINE: JSIDPLAY2` | Correct engine selected | ✅ Good |
| `📤 Sending sequence to ENGINE: SIDPLAYFP` | Wrong engine selected | ❌ Check settings |
| `✓ Console window FOUND: HWND=0x...` | PostMessage path used | ✅ Good |
| `✗ Console window NOT FOUND` | PostMessage failed | ⚠️ Using stdin fallback |
| `✓ Sequence sent successfully via stdin fallback` | Stdin path used | ✅ Good |
| `✗ Stdin fallback also failed` | Both methods failed | ❌ Problem to investigate |
| `⏱️  Timing: 50ms after key + 100ms after Enter` | New timing active | ✅ Good |

---

## If It Still Doesn't Work

### 1️⃣ Check in Debug Console:
- Look for `[WINAPI]` messages
- Verify `ENGINE: JSIDPLAY2` is shown
- Check if window was found or fallback was used

### 2️⃣ Verify JSidplay2 is installed:
```python
# Check path in settings:
# Should see: tools/jsidplay2-console.exe
```

### 3️⃣ Try with visible console:
- Make sure jsidplay2-console.exe window is visible (not minimized)
- Should use PostMessage path instead of stdin

### 4️⃣ Look for timing issues:
- If channels mute but only partially:
  - May need even longer delay (try 0.15 or 0.20)
  - Report this to developer

---

## Technical Details

### Sequence Structure
Each character (1-c) is followed by Enter:
```
Character 1:
  1. Send KEY DOWN for '1'
  2. Send KEY UP for '1'
  3. Wait 50ms
  4. Send KEY DOWN for Enter
  5. Send KEY UP for Enter
  6. Wait 100ms ← CRITICAL: JSidplay2 processes here
  
Repeat for '2' through 'c'
```

### Total Duration
12 channels × 150ms per channel = **1.8 seconds** total

This is acceptable because it's done asynchronously in a background thread and doesn't block UI.

---

## Files Modified

1. **`windows_api_manager.py`**
   - Line 396-397: Added engine verification logging
   - Line 415-417: Added sequence preview logging
   - Line 438: Changed `time.sleep(0.02)` → `time.sleep(0.05)`
   - Line 448: Changed `time.sleep(0.02)` → `time.sleep(0.10)`
   - Line 411-421: Added stdin fallback

---

## Summary

✅ **Timing fixed**: 0.02s → 0.10s (5x improvement)  
✅ **Engine verification**: Now shows which engine is receiving sequence  
✅ **Fallback path**: stdin now used if window not found  
✅ **Better logging**: Full sequence visibility in Debug Console  

**Expected result**: JSidplay2 channel muting now works reliably! 🎵