#!/usr/bin/env python3
"""
PyInstaller compilation script for SID Player
This script will create a standalone executable for the SID Player application.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def compile_sidplayer():
    """Compile the SID Player application using PyInstaller"""
    
    # Get the current directory (where this script is located)
    current_dir = Path(__file__).parent.absolute()
    print(f"Working directory: {current_dir}")
    
    # Define paths
    source_dir = current_dir / "src" 
    main_script = source_dir / "main.py"
    tools_dir = source_dir / "players"
    assets_dir = source_dir / "assets"
    config_dir = source_dir / "config"
    playlists_dir = source_dir / "playlists"
    
    # Verify required files exist
    if not main_script.exists():
        print(f"Error: Main script not found at {main_script}")
        return False
        
    if not tools_dir.exists():
        print(f"Error: Tools directory not found at {tools_dir}")
        return False
        
    if not assets_dir.exists():
        print(f"Warning: Assets directory not found at {assets_dir}")
        
    # Create dist and build directories if they don't exist
    dist_dir = current_dir / "dist"
    build_dir = current_dir / "build"
    dist_dir.mkdir(exist_ok=True)
    build_dir.mkdir(exist_ok=True)
    
    # Try to fix PyQt5 DLL issues by ensuring we have the right version
    try:
        import PyQt5
        pyqt5_path = os.path.dirname(PyQt5.__file__)
        qt5_path = os.path.join(pyqt5_path, 'Qt5')
        qt5_bin_path = os.path.join(qt5_path, 'bin')
        
        if os.path.exists(qt5_bin_path):
            print(f"Found PyQt5 Qt5 binaries at: {qt5_bin_path}")
        else:
            print("Warning: PyQt5 Qt5 binaries not found in expected location")
    except ImportError:
        print("Error: PyQt5 not installed")
        return False
    
    # PyInstaller command with fixes for DLL issues
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=SIDPlayer",
        "--windowed",  # No console window
        "--onefile",   # Single executable file
        f"--icon={assets_dir / 'sid_ico.ico'}" if (assets_dir / 'sid_ico.ico').exists() else None,
        "--add-data", f"{tools_dir}{os.pathsep}players",
        "--add-data", f"{assets_dir}{os.pathsep}assets" if assets_dir.exists() else None,
        "--add-data", f"{config_dir}{os.pathsep}config" if config_dir.exists() else None,
        "--add-data", f"{playlists_dir}{os.pathsep}playlists" if playlists_dir.exists() else None,
        "--hidden-import=PyQt5.sip",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.Qt",
        "--hidden-import=configparser",
        "--hidden-import=ctypes",
        "--hidden-import=ctypes.wintypes",
        "--clean",
        "--noconfirm",
        # Add flag to avoid UPX compression issues with DLLs
        "--noupx",
        str(main_script)
    ]
    
    # Remove None values from cmd
    cmd = [arg for arg in cmd if arg is not None]
    
    print("Running PyInstaller with command:")
    print(" ".join(cmd))
    print("\n" + "="*50)
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, cwd=current_dir, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print("="*50)
        print("Compilation completed successfully!")
        print(f"Executable location: {dist_dir / 'SIDPlayer.exe'}")
        return True
        
    except subprocess.CalledProcessError as e:
        print("Error during compilation:")
        print(f"Return code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        
        # Try alternative approach without onefile
        print("\nTrying alternative compilation approach (directory mode)...")
        return compile_sidplayer_directory_mode()
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def compile_sidplayer_directory_mode():
    """Compile as a directory instead of single file to avoid DLL issues"""
    
    # Get the current directory (where this script is located)
    current_dir = Path(__file__).parent.absolute()
    print(f"Working directory: {current_dir}")
    
    # Define paths
    main_script = current_dir / "main.py"
    tools_dir = current_dir / "tools"
    assets_dir = current_dir / "assets"
    
    # PyInstaller command without --onefile
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=SIDPlayer",
        "--windowed",  # No console window
        f"--icon={assets_dir / 'sid_ico.ico'}" if (assets_dir / 'sid_ico.ico').exists() else None,
        "--add-data", f"{tools_dir}{os.pathsep}tools",
        "--add-data", f"{assets_dir}{os.pathsep}assets" if assets_dir.exists() else None,
        "--hidden-import=PyQt5.sip",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.Qt",
        "--hidden-import=configparser",
        "--hidden-import=ctypes",
        "--hidden-import=ctypes.wintypes",
        "--clean",
        "--noconfirm",
        "--noupx",
        str(main_script)
    ]
    
    # Remove None values from cmd
    cmd = [arg for arg in cmd if arg is not None]
    
    print("Running PyInstaller in directory mode with command:")
    print(" ".join(cmd))
    print("\n" + "="*50)
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, cwd=current_dir, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print("="*50)
        print("Compilation completed successfully!")
        print(f"Executable location: {current_dir / 'dist' / 'SIDPlayer' / 'SIDPlayer(.exe)'}")
        return True
        
    except subprocess.CalledProcessError as e:
        print("Error during compilation:")
        print(f"Return code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def copy_additional_files():
    """Copy additional required files to the dist directory"""
    current_dir = Path(__file__).parent.absolute()
    dist_dir = current_dir / "dist"
    
    if not dist_dir.exists():
        print("Dist directory not found!")
        return False
    
    # Files to copy
    files_to_copy = [
        "settings.ini",
        "sidplayer_playlist.json",
        "Songlengths.md5"
    ]
    
    # Copy files if they exist
    for file_name in files_to_copy:
        source_file = current_dir / file_name
        if source_file.exists():
            dest_file = dist_dir / file_name
            try:
                shutil.copy2(source_file, dest_file)
                print(f"Copied {file_name} to dist directory")
            except Exception as e:
                print(f"Warning: Could not copy {file_name}: {e}")
        else:
            print(f"Warning: {file_name} not found, skipping")
    
    # Copy tools directory
    source_tools = current_dir / "tools"
    dest_tools = dist_dir / "tools"
    if source_tools.exists():
        try:
            if dest_tools.exists():
                shutil.rmtree(dest_tools)
            shutil.copytree(source_tools, dest_tools)
            print("Copied tools directory to dist directory")
        except Exception as e:
            print(f"Warning: Could not copy tools directory: {e}")
    else:
        print("Warning: tools directory not found")
    
    # Copy assets directory
    source_assets = current_dir / "assets"
    dest_assets = dist_dir / "assets"
    if source_assets.exists():
        try:
            if dest_assets.exists():
                shutil.rmtree(dest_assets)
            shutil.copytree(source_assets, dest_assets)
            print("Copied assets directory to dist directory")
        except Exception as e:
            print(f"Warning: Could not copy assets directory: {e}")
    else:
        print("Warning: assets directory not found")
    
    return True

if __name__ == "__main__":
    print("SID Player Compilation Script")
    print("="*30)
    
    # Install PyInstaller if not available
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyInstaller"])
    
    # Compile the application
    success = compile_sidplayer()
    
    if success:
        # Copy additional files
        copy_additional_files()
        print("\nCompilation and file copying completed!")
        print("You can find the executable in the 'dist' folder.")
    else:
        print("\nCompilation failed!")
        sys.exit(1)
