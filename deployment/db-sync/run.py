#!/usr/bin/env python3
"""
Startskript für die Anwendung.
"""

import os
import sys
from backend.app.app import run_app

# Stelle sicher, dass das aktuelle Verzeichnis im Python-Pfad ist
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == '__main__':
    run_app() 