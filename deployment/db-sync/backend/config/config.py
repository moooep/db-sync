"""
Konfigurationsdatei für SQLite-Datenbanksynchronisierung.
"""

import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env-Datei
load_dotenv()

# Pfad zur Anwendungskonfiguration (SQLite-Datenbank)
CONFIG_DB_PATH = os.getenv('CONFIG_DB_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'config.db'))

# Master-Datenbank-Konfiguration
MASTER_DB_PATH = os.getenv('MASTER_DB_PATH', '')
MASTER_SERVER = os.getenv('MASTER_SERVER', 'localhost')

# Webserver-Konfiguration
WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
WEB_PORT = int(os.getenv('WEB_PORT', '5000'))
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

# Synchronisationskonfiguration
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', '60'))  # Sekunden
IGNORED_TABLES = os.getenv('IGNORED_TABLES', '').split(',') if os.getenv('IGNORED_TABLES') else []
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '10485760'))  # 10MB in Bytes

# Logging-Konfiguration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs', 'db_sync.log'))

# Pfad für temporäre Dateien
TEMP_DIR = os.getenv('TEMP_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'temp'))

# Erstelle Verzeichnisse, falls sie nicht existieren
os.makedirs(os.path.dirname(CONFIG_DB_PATH), exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True) 