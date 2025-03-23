"""
Konfigurationsdatei für SQLite-Datenbanksynchronisierung.
"""

import os
import configparser
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env-Datei
load_dotenv()

# Bestimme den Pfad zur Konfigurationsdatei
CONFIG_FILE = os.environ.get('CONFIG_FILE', 'config.ini')
CONFIG_SAMPLE_FILE = 'config-sample.ini'

# Erstelle Konfigurationsobjekt
config = configparser.ConfigParser()

# Versuche, die Konfigurationsdatei zu lesen
if os.path.exists(CONFIG_FILE):
    config.read(CONFIG_FILE)
elif os.path.exists(CONFIG_SAMPLE_FILE):
    config.read(CONFIG_SAMPLE_FILE)
    print(f"Konfigurationsdatei {CONFIG_FILE} nicht gefunden, verwende {CONFIG_SAMPLE_FILE}")
else:
    print(f"Weder {CONFIG_FILE} noch {CONFIG_SAMPLE_FILE} gefunden, verwende Standardwerte")

# Datenbankeinstellungen
DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
os.makedirs(DEFAULT_DB_DIR, exist_ok=True)

MASTER_DB_PATH = os.environ.get('MASTER_DB_PATH') or config.get('database', 'master_db_path', fallback=os.path.join(DEFAULT_DB_DIR, 'master.db'))
print(f"MASTER_DB_PATH: {MASTER_DB_PATH}")

# Stellen sicher, dass der Ordner für die Master-DB existiert
os.makedirs(os.path.dirname(os.path.abspath(MASTER_DB_PATH)), exist_ok=True)

# Webserver-Einstellungen
WEB_HOST = os.environ.get('WEB_HOST') or config.get('server', 'host', fallback='0.0.0.0')
WEB_PORT = int(os.environ.get('WEB_PORT') or config.get('server', 'port', fallback='5000'))
DEBUG = os.environ.get('DEBUG') or config.getboolean('server', 'debug', fallback=False)

# Synchronisierungseinstellungen
SYNC_INTERVAL = int(os.environ.get('SYNC_INTERVAL') or config.get('sync', 'check_interval', fallback='60'))
IGNORED_TABLES = os.environ.get('IGNORED_TABLES', '').split(',') if os.environ.get('IGNORED_TABLES') else []

# Logging-Einstellungen
LOG_LEVEL = os.environ.get('LOG_LEVEL') or config.get('logging', 'level', fallback='INFO')
LOG_TO_FILE = os.environ.get('LOG_TO_FILE') or config.getboolean('logging', 'log_to_file', fallback=True)
LOG_FILE = os.environ.get('LOG_FILE') or config.get('logging', 'log_file', fallback='logs/db-sync.log')

# Temporäres Verzeichnis
TEMP_DIR = os.environ.get('TEMP_DIR') or config.get('sync', 'temp_dir', fallback='temp')

# Pfad für temporäre Dateien
TEMP_DIR = os.path.join(TEMP_DIR, 'temp')
os.makedirs(TEMP_DIR, exist_ok=True) 