@echo off
echo SID Player Compilation Script
echo ============================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or later and try again
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install PyInstaller
    if %errorlevel% neq 0 (
        echo Error: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo Compiling SID Player with PyInstaller...
echo.

REM Run PyInstaller with our spec file and --noupx flag to avoid DLL issues
python -m PyInstaller --noupx sidplayer.spec

if %errorlevel% neq 0 (
    echo.
    echo Error: Compilation failed!
    echo Trying alternative compilation method...
    echo.
    
    REM Try direct compilation without spec file
    echo Attempting direct compilation...
    python -m PyInstaller --name=SIDPlayer --windowed --onefile --clean --noconfirm --noupx --hidden-import=PyQt5.sip --hidden-import=PyQt5.QtCore --hidden-import=PyQt5.QtGui --hidden-import=PyQt5.QtWidgets --hidden-import=PyQt5.Qt --hidden-import=configparser --hidden-import=ctypes --hidden-import=ctypes.wintypes main.py
    
    if %errorlevel% neq 0 (
        echo.
        echo Error: Direct compilation also failed!
        pause
        exit /b 1
    )
)

echo.
echo Compilation completed successfully!
echo.

echo Copying additional files to dist directory...
echo.

REM Copy additional required files
if exist "settings.ini" copy "settings.ini" "dist\" >nul
if exist "sidplayer_playlist.json" copy "sidplayer_playlist.json" "dist\" >nul
if exist "Songlengths.md5" copy "Songlengths.md5" "dist\" >nul

REM Copy tools directory
if exist "tools\" (
    echo Copying tools directory...
    xcopy "tools" "dist\tools" /E /I /Y >nul
)

REM Copy assets directory
if exist "assets\" (
    echo Copying assets directory...
    xcopy "assets" "dist\assets" /E /I /Y >nul
)

echo.
echo All files copied successfully!
echo.
echo Your compiled executable is located at: dist\SIDPlayer.exe
echo.
echo To run the application, double-click on SIDPlayer.exe in the dist folder
echo.
pause