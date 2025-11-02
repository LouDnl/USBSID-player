# SID Player Compilation Instructions

This document provides instructions on how to compile the SID Player application into a standalone executable using PyInstaller.

## Prerequisites

1. Python 3.7 or later installed on your system
2. All required Python packages installed (see requirements.txt)
3. PyInstaller package installed

## Method 1: Using the Batch File (Windows)

The easiest way to compile the application on Windows is to use the provided batch file:

1. Navigate to the `sidplayer` directory
2. Double-click on `compile.bat` or run it from the command prompt:
   ```
   compile.bat
   ```

The batch file will automatically:
- Check for Python installation
- Install PyInstaller if not already installed
- Compile the application using the spec file
- Copy all required files to the dist directory

## Method 2: Using the Python Script

You can also run the Python compilation script directly:

1. Navigate to the `sidplayer` directory
2. Run the compilation script:
   ```
   python compile_sidplayer.py
   ```

## Method 3: Manual PyInstaller Command

If you prefer to run PyInstaller manually, you can use the following command from the `sidplayer` directory:

```
pyinstaller sidplayer.spec
```

Or use a direct command:
```
pyinstaller --name=SIDPlayer --windowed --onefile --icon=assets/sid_ico.ico --add-data "tools;tools" --add-data "assets;assets" --hidden-import=PyQt5.sip --hidden-import=PyQt5.QtCore --hidden-import=PyQt5.QtGui --hidden-import=PyQt5.QtWidgets --hidden-import=configparser --hidden-import=ctypes --hidden-import=ctypes.wintypes --clean --noconfirm main.py
```

## Output

After successful compilation:
- The executable will be located in the `dist` folder as `SIDPlayer.exe`
- All required files and directories will be copied to the `dist` folder

## Running the Compiled Application

1. Navigate to the `dist` folder
2. Double-click on `SIDPlayer.exe` to run the application

Note: The application requires the following files to run properly:
- `tools/sidplayfp.exe` - The SID playback engine
- `tools/jsidplay2-console.exe` - Alternative playback engine
- `Songlengths.md5` - Song duration database
- `assets/` directory - Contains icons and other assets

These files are automatically copied to the dist folder during compilation.

## Troubleshooting

If you encounter any issues during compilation:

1. Make sure all Python dependencies are installed:
   ```
   pip install -r ../requirements.txt
   ```

2. Ensure PyInstaller is installed:
   ```
   pip install PyInstaller
   ```

3. Check that all required files exist in their expected locations:
   - `main.py` (entry point)
   - `tools/sidplayfp.exe`
   - `assets/sid_ico.ico`
   - `Songlengths.md5`

4. If you get import errors, try adding more hidden imports to the spec file or command line.

## Additional Notes

- The compiled executable is completely standalone and does not require Python to be installed on the target machine
- The application will maintain all functionality of the original Python script
- File paths are handled automatically by PyInstaller's resource system