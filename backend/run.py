#!/usr/bin/env python3
"""
Einstiegspunkt für die Anwendung.
"""

import os
import sys

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Führe Eventlet-Monkey-Patching vor allen anderen Imports durch
print("Initialisiere Eventlet...")
try:
    import eventlet
    eventlet.monkey_patch(thread=True, os=True, time=True, socket=True, select=True, ssl=True)
    print("Eventlet Monkey-Patching erfolgreich durchgeführt")
    
    # Überprüfe, ob das Patching tatsächlich funktioniert hat
    if hasattr(eventlet, 'is_monkey_patched'):
        patches = {
            'socket': eventlet.is_monkey_patched('socket'),
            'thread': eventlet.is_monkey_patched('thread'),
            'time': eventlet.is_monkey_patched('time'),
            'select': eventlet.is_monkey_patched('select'),
            'ssl': eventlet.is_monkey_patched('ssl')
        }
        print(f"Monkey-Patching-Status: {patches}")
        
        # Wichtig zu prüfen
        if not patches['socket'] or not patches['thread']:
            print("WARNUNG: Kritische Module wurden nicht gepacht!")
    else:
        print("is_monkey_patched nicht verfügbar, kann Patch-Status nicht verifizieren")
except ImportError:
    print("Warnung: Eventlet nicht installiert!")

from backend.config.config import MASTER_DB_PATH
print(f"MASTER_DB_PATH: {MASTER_DB_PATH}")

# Prüfe die Eventlet-Version
try:
    print(f"Eventlet-Version: {eventlet.__version__}")
except (ImportError, AttributeError):
    print("Eventlet-Version kann nicht ermittelt werden")

from backend.app.app import run_app

if __name__ == "__main__":
    run_app() 