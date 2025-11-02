@echo off
echo Simple SID Player Compilation
echo ===========================
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

echo Compiling SID Player with simple spec file...
echo.

REM Run PyInstaller with simple spec file
python -m PyInstaller --noconfirm --clean simple_sidplayer.spec

if %errorlevel% neq 0 (
    echo.
    echo Error: Compilation failed!
    pause
    exit /b 1
)

echo.
echo Compilation completed successfully!
echo.

echo Copying required files to dist directory...
echo.

REM Copy required files and directories
if exist "settings.ini" copy "settings.ini" "dist\" >nul
if exist "sidplayer_playlist.json" copy "sidplayer_playlist.json" "dist\" >nul
if exist "Songlengths.md5" copy "Songlengths.md5" "dist\" >nul
if exist "tools\" xcopy "tools" "dist\tools" /E /I /Y >nul
if exist "assets\" xcopy "assets" "dist\assets" /E /I /Y >nul

echo.
echo All files copied successfully!
echo.
echo Your compiled executable is located at: dist\SIDPlayer.exe
echo.
pause