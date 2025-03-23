#!/usr/bin/env python3
import os
import sys

# Füge das Stammverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Jetzt kann das backend-Modul gefunden werden
from backend.app.app import run_app

if __name__ == '__main__':
    run_app() 