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
    
    # Prüfe Eventlet-Version und passe die Parameter entsprechend an
    try:
        eventlet_version = eventlet.__version__
        print(f"Erkannte Eventlet-Version: {eventlet_version}")
        
        # Ältere Versionen von Eventlet unterstützen das ssl-Argument nicht
        if hasattr(eventlet, 'monkey_patch'):
            # Versuche zuerst ohne ssl-Argument
            try:
                eventlet.monkey_patch(thread=True, os=True, time=True, socket=True, select=True)
                print("Eventlet Monkey-Patching ohne ssl-Argument erfolgreich durchgeführt")
            except TypeError as e:
                print(f"Fehler beim ersten Patch-Versuch: {e}")
                # Reduziere auf die minimal notwendigen Argumente
                eventlet.monkey_patch()
                print("Eventlet Monkey-Patching mit Standardargumenten durchgeführt")
        else:
            print("Eventlet hat keine monkey_patch-Funktion, überspringe Patching")
    except (ImportError, AttributeError) as e:
        print(f"Eventlet-Version konnte nicht ermittelt werden: {e}")
        # Versuche trotzdem zu patchen ohne ssl
        eventlet.monkey_patch(thread=True, os=True, time=True, socket=True, select=True)
    
    # Überprüfe, ob das Patching tatsächlich funktioniert hat
    if hasattr(eventlet, 'is_monkey_patched'):
        patches = {
            'socket': eventlet.is_monkey_patched('socket'),
            'thread': eventlet.is_monkey_patched('thread'),
            'time': eventlet.is_monkey_patched('time'),
            'select': eventlet.is_monkey_patched('select')
        }
        print(f"Monkey-Patching-Status: {patches}")
        
        # Wichtig zu prüfen
        if not patches.get('socket', False) or not patches.get('thread', False):
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