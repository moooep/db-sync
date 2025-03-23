"""
Logger-Konfiguration für die SQLite-Datenbanksynchronisierung.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

from backend.config.config import LOG_LEVEL, LOG_FILE

def setup_logger(name: str, log_file: Optional[str] = None, level: Optional[str] = None) -> logging.Logger:
    """
    Richtet einen Logger mit Datei- und Konsolenhandler ein.
    
    Args:
        name: Name des Loggers
        log_file: Pfad zur Log-Datei, verwendet LOG_FILE aus der Konfiguration falls None
        level: Log-Level, verwendet LOG_LEVEL aus der Konfiguration falls None
        
    Returns:
        logging.Logger: Der konfigurierte Logger
    """
    if log_file is None:
        log_file = LOG_FILE
        
    if level is None:
        level = LOG_LEVEL
    
    # Erstelle Verzeichnis für Log-Datei, falls nicht vorhanden
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Bestimme das Log-Level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Erstelle Logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    
    # Verhindere doppelte Handler
    if logger.handlers:
        return logger
    
    # Datei-Handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(numeric_level)
    logger.addHandler(file_handler)
    
    # Konsolen-Handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(numeric_level)
    logger.addHandler(console_handler)
    
    return logger

def log_to_db(db_manager, event_type: str, message: str, details: Optional[str] = None) -> None:
    """
    Schreibt ein Log-Event in die Datenbank.
    
    Args:
        db_manager: Datenbankmanager-Instanz
        event_type: Typ des Events (z.B. 'sync', 'error', 'info')
        message: Kurze Beschreibung des Events
        details: Detaillierte Informationen zum Event
    """
    log_schema = """
    CREATE TABLE IF NOT EXISTS _sync_logs (
        id INTEGER PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        event_type TEXT NOT NULL,
        message TEXT NOT NULL,
        details TEXT
    )
    """
    
    try:
        db_manager.create_table_if_not_exists("_sync_logs", log_schema)
        
        with db_manager.get_connection() as conn:
            conn.execute(
                "INSERT INTO _sync_logs (event_type, message, details) VALUES (?, ?, ?)",
                (event_type, message, details)
            )
    except Exception as e:
        # Falls DB-Logging fehlschlägt, logge auf die Konsole
        logging.error(f"Fehler beim Schreiben des DB-Logs: {e}")

def get_db_logs(db_manager, limit: int = 100, event_type: Optional[str] = None) -> list:
    """
    Holt Log-Einträge aus der Datenbank.
    
    Args:
        db_manager: Datenbankmanager-Instanz
        limit: Maximale Anzahl der zurückzugebenden Logs
        event_type: Optionaler Filter für den Event-Typ
        
    Returns:
        list: Liste der Log-Einträge
    """
    try:
        if event_type:
            query = """
            SELECT * FROM _sync_logs 
            WHERE event_type = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """
            params = (event_type, limit)
        else:
            query = """
            SELECT * FROM _sync_logs 
            ORDER BY timestamp DESC 
            LIMIT ?
            """
            params = (limit,)
            
        return db_manager.execute_query(query, params)
    except Exception as e:
        logging.error(f"Fehler beim Abrufen der DB-Logs: {e}")
        return []

# Erstelle den Standard-Logger
logger = setup_logger('db_sync') 