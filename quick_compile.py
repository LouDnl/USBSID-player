#!/usr/bin/env python3
"""
Quick compilation script for SID Player
"""

import subprocess
import sys
import os

def main():
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyInstaller"])
    
    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    
    print("Compiling SID Player...")
    
    # First try with spec file
    try:
        print("Attempting compilation with spec file...")
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--noupx",  # Disable UPX to avoid DLL issues
            "sidplayer.spec"
        ])
        print("\nCompilation successful!")
        print("Executable created in dist/SIDPlayer.exe")
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"\nCompilation with spec file failed with error code {e.returncode}")
        print("Trying alternative compilation method...")
        
        # Try direct compilation without spec file
        try:
            print("Attempting direct compilation...")
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--name=SIDPlayer",
                "--windowed",
                "--onefile",
                "--clean",
                "--noconfirm",
                "--noupx",  # Disable UPX to avoid DLL issues
                "--hidden-import=PyQt5.sip",
                "--hidden-import=PyQt5.QtCore",
                "--hidden-import=PyQt5.QtGui",
                "--hidden-import=PyQt5.QtWidgets",
                "--hidden-import=PyQt5.Qt",
                "--hidden-import=configparser",
                "--hidden-import=ctypes",
                "--hidden-import=ctypes.wintypes",
                "main.py"
            ]
            
            # Add icon if it exists
            icon_path = os.path.join(current_dir, "assets", "sid_ico.ico")
            if os.path.exists(icon_path):
                cmd.extend(["--icon", icon_path])
            
            # Add data directories
            tools_path = os.path.join(current_dir, "tools")
            if os.path.exists(tools_path):
                cmd.extend(["--add-data", f"{tools_path}{os.pathsep}tools"])
                
            assets_path = os.path.join(current_dir, "assets")
            if os.path.exists(assets_path):
                cmd.extend(["--add-data", f"{assets_path}{os.pathsep}assets"])
            
            subprocess.check_call(cmd)
            print("\nCompilation successful!")
            print("Executable created in dist/SIDPlayer.exe")
            return 0
            
        except subprocess.CalledProcessError as e2:
            print(f"\nDirect compilation also failed with error code {e2.returncode}")
            return 1
        except Exception as e2:
            print(f"\nUnexpected error during direct compilation: {e2}")
            return 1
            
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())