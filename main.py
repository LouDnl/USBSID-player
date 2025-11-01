#!/usr/bin/env python3
"""
SID PLAYER - MODULAR VERSION
Main entry point for the SID Player application

This is the cleaned-up, modular entry point.
All business logic is separated into modular components.
"""

import sys
from PyQt5.QtWidgets import QApplication
from sid_player_modern07 import SIDPlayer


def main():
    """Initialize and run the SID Player application"""
    # Create Qt Application instance
    app = QApplication(sys.argv)
    
    # Use Fusion style for better stylesheet support
    app.setStyle('Fusion')
    
    # Create and show the main window
    player = SIDPlayer()
    player.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()