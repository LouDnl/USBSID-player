@echo off
echo Quick SID Player Compilation
echo ===========================
echo.

python quick_compile.py

if %errorlevel% equ 0 (
    echo.
    echo Compilation completed successfully!
    echo Find your executable in the dist folder.
) else (
    echo.
    echo Compilation failed!
)

echo.
pause