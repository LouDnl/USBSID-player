#!/usr/bin/env python3
"""
SID PLAYER - MODULAR VERSION
Main entry point for the SID Player application

This is the cleaned-up, modular entry point.
All business logic is separated into modular components.
"""

import sys
import os
import traceback

# Ensure the script's directory is in the path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from PyQt5.QtWidgets import QApplication, QMessageBox
from sid_player_modern07 import SIDPlayer

try:
    import qdarktheme
    QDARKTHEME_AVAILABLE = True
except ImportError:
    QDARKTHEME_AVAILABLE = False
    print("[WARN] qdarktheme not available, using default theme")


def main():
    """Initialize and run the SID Player application"""
    try:
        # Create Qt Application instance
        app = QApplication(sys.argv)

        # Apply dark theme if available
        if QDARKTHEME_AVAILABLE:
            try:
                qdarktheme.setup_theme("dark")
                print("[INFO] Dark theme applied successfully")
            except Exception as e:
                print(f"[WARN] Could not apply dark theme: {e}")

        # Use Fusion style for better stylesheet support
        app.setStyle('Fusion')

        # Create and show the main window
        print("[INFO] Creating SID Player window...")
        player = SIDPlayer()
        print("[INFO] Showing SID Player window...")
        player.show()
        print("[INFO] SID Player started successfully")

        # Start the event loop
        sys.exit(app.exec_())
    
    except Exception as e:
        # Try to show error in GUI if possible
        try:
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)
            error_msg = f"Fatal Error:\n\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            QMessageBox.critical(None, "SID Player - Fatal Error", error_msg)
        except:
            # If GUI fails, print to console
            print(f"\n[FATAL ERROR] {str(e)}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
