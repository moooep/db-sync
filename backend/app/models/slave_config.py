"""
Konfiguration und Verwaltung von Slave-Datenbanken.
"""

import os
import sqlite3
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.config.config import MASTER_DB_PATH

# Logger einrichten
logger = logging.getLogger(__name__)

class SlaveConfig:
    """Klasse zur Verwaltung der Slave-Konfiguration."""
    
    def __init__(self, config_db_path: Optional[str] = None):
        """
        Initialisiert die SlaveConfig-Klasse.
        
        Args:
            config_db_path: Pfad zur Konfigurationsdatenbank
        """
        if config_db_path is None:
            # Verwende den gleichen Pfad wie die Master-DB, aber mit anderem Namen
            master_dir = os.path.dirname(MASTER_DB_PATH)
            self.config_db_path = os.path.join(master_dir, 'config.db')
        else:
            self.config_db_path = config_db_path
        
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(self.config_db_path), exist_ok=True)
        
        # Initialisiere die Datenbank, wenn sie nicht existiert
        self._init_db()
    
    def _init_db(self) -> None:
        """
        Initialisiert die Konfigurationsdatenbank, falls sie noch nicht existiert.
        """
        db_exists = os.path.exists(self.config_db_path)
        
        try:
            with sqlite3.connect(self.config_db_path) as conn:
                conn.execute('PRAGMA foreign_keys = ON')
                cursor = conn.cursor()
                
                # Erstelle Tabellen, falls sie nicht existieren
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS slaves (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        db_path TEXT NOT NULL,
                        server_address TEXT,
                        status TEXT DEFAULT 'active',
                        ignored_tables TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sync_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        slave_id INTEGER NOT NULL,
                        slave_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT,
                        changes_count INTEGER DEFAULT 0,
                        duration REAL DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (slave_id) REFERENCES slaves(id) ON DELETE CASCADE
                    )
                ''')
                
                # Füge keine Test-Slaves hinzu, wenn die Datenbank neu erstellt wird
                # Stattdessen protokollieren wir, dass die Datenbank initialisiert wurde
                if not db_exists:
                    logger.info(f"Konfigurationsdatenbank wurde initialisiert: {self.config_db_path}")
                
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Fehler bei der Initialisierung der Konfigurationsdatenbank: {e}")
            raise
    
    def add_slave(self, name: str, db_path: str, server_address: Optional[str] = None, 
                  ignored_tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fügt einen neuen Slave hinzu.
        
        Args:
            name: Name des Slaves
            db_path: Pfad zur Slave-Datenbank
            server_address: Server-Adresse (optional)
            ignored_tables: Liste der ignorierten Tabellen (optional)
            
        Returns:
            Dict mit Status und Nachrichten
        """
        try:
            with sqlite3.connect(self.config_db_path) as conn:
                conn.execute('PRAGMA foreign_keys = ON')
                cursor = conn.cursor()
                
                # Prüfe, ob ein Slave mit diesem Pfad bereits existiert
                cursor.execute('SELECT id FROM slaves WHERE db_path = ?', (db_path,))
                existing_slave = cursor.fetchone()
                
                if existing_slave:
                    return {
                        "status": "error",
                        "message": f"Ein Slave mit dem Pfad '{db_path}' existiert bereits"
                    }
                
                # Konvertiere ignorierte Tabellen in einen String
                ignored_tables_str = ','.join(ignored_tables) if ignored_tables else ''
                
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute('''
                    INSERT INTO slaves (name, db_path, server_address, ignored_tables, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, db_path, server_address, ignored_tables_str, now, now))
                
                slave_id = cursor.lastrowid
                conn.commit()
                
                return {
                    "status": "success",
                    "message": f"Slave '{name}' erfolgreich hinzugefügt",
                    "slave_id": slave_id
                }
        except sqlite3.Error as e:
            logger.error(f"Fehler beim Hinzufügen des Slaves: {e}")
            return {
                "status": "error",
                "message": f"Datenbankfehler: {str(e)}"
            }
    
    def update_slave(self, slave_id: int, name: Optional[str] = None, 
                    db_path: Optional[str] = None, server_address: Optional[str] = None, 
                    status: Optional[str] = None) -> bool:
        """
        Aktualisiert die Konfiguration eines Slaves.
        
        Args:
            slave_id: ID des Slaves
            name: Neuer Name des Slaves (optional)
            db_path: Neuer Pfad zur Slave-Datenbank (optional)
            server_address: Neue Adresse des Slave-Servers (optional)
            status: Neuer Status des Slaves (optional)
            
        Returns:
            bool: True bei Erfolg, False sonst
        """
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if db_path is not None:
            updates.append("db_path = ?")
            params.append(db_path)
        
        if server_address is not None:
            updates.append("server_address = ?")
            params.append(server_address)
        
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        params.append(slave_id)
        
        sql = f"UPDATE slaves SET {', '.join(updates)} WHERE id = ?"
        
        with sqlite3.connect(self.config_db_path) as conn:
            try:
                conn.execute(sql, params)
                return True
            except sqlite3.Error as e:
                logger.error(f"Fehler beim Aktualisieren des Slaves: {e}")
                return False
    
    def delete_slave(self, slave_id: int) -> bool:
        """
        Löscht einen Slave aus der Konfiguration.
        
        Args:
            slave_id: ID des Slaves
            
        Returns:
            bool: True bei Erfolg, False sonst
        """
        with sqlite3.connect(self.config_db_path) as conn:
            try:
                # Durch Foreign-Key-Constraints werden auch verknüpfte Einträge gelöscht
                conn.execute("DELETE FROM slaves WHERE id = ?", (slave_id,))
                return True
            except sqlite3.Error as e:
                logger.error(f"Fehler beim Löschen des Slaves: {e}")
                return False
    
    def get_slave(self, slave_id: int) -> Optional[Dict[str, Any]]:
        """
        Gibt die Konfiguration eines Slaves zurück.
        
        Args:
            slave_id: ID des Slaves
            
        Returns:
            Optional[Dict[str, Any]]: Slave-Konfiguration oder None, wenn nicht gefunden
        """
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM slaves WHERE id = ?", (slave_id,))
            slave = cursor.fetchone()
            
            if not slave:
                return None
            
            # Füge ignorierte Tabellen hinzu
            ignored_tables = conn.execute(
                "SELECT table_name FROM ignored_tables WHERE slave_id = ?", 
                (slave_id,)
            ).fetchall()
            
            slave["ignored_tables"] = [table["table_name"] for table in ignored_tables]
            
            return slave
    
    def get_all_slaves(self) -> List[Dict[str, Any]]:
        """
        Gibt die Konfiguration aller Slaves zurück.
        
        Returns:
            List[Dict[str, Any]]: Liste aller Slave-Konfigurationen
        """
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM slaves ORDER BY name")
            slaves = cursor.fetchall()
            
            # Füge ignorierte Tabellen für jeden Slave hinzu
            for slave in slaves:
                ignored_tables = conn.execute(
                    "SELECT table_name FROM ignored_tables WHERE slave_id = ?", 
                    (slave["id"],)
                ).fetchall()
                
                slave["ignored_tables"] = [table["table_name"] for table in ignored_tables]
            
            return slaves
    
    def update_slave_sync_status(self, slave_id: int, status: str, 
                                last_sync: Optional[str] = None) -> bool:
        """
        Aktualisiert den Synchronisationsstatus eines Slaves.
        
        Args:
            slave_id: ID des Slaves
            status: Neuer Status
            last_sync: Zeitstempel der letzten Synchronisation (optional)
            
        Returns:
            bool: True bei Erfolg, False sonst
        """
        updates = ["status = ?", "updated_at = ?"]
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        params = [status, current_time]
        
        # Wenn ein Zeitstempel für die letzte Synchronisation angegeben wurde,
        # verwenden wir diesen, ansonsten den aktuellen Zeitstempel
        if last_sync is not None:
            updates.append("last_sync = ?")
            params.append(last_sync)
            logger.info(f"update_slave_sync_status: Verwende angegebenen Zeitstempel: {last_sync}")
        else:
            # Nur aktualisieren, wenn Status auf 'active' oder 'syncing' gesetzt wird
            if status in ['active', 'syncing']:
                updates.append("last_sync = ?")
                params.append(current_time)
                logger.info(f"update_slave_sync_status: Verwende aktuellen Zeitstempel: {current_time}")
        
        params.append(slave_id)
        
        sql = f"UPDATE slaves SET {', '.join(updates)} WHERE id = ?"
        logger.info(f"update_slave_sync_status: SQL: {sql}, Params: {params}")
        
        with sqlite3.connect(self.config_db_path) as conn:
            try:
                conn.execute(sql, params)
                return True
            except sqlite3.Error as e:
                logger.error(f"Fehler beim Aktualisieren des Sync-Status: {e}")
                return False
    
    def add_ignored_table(self, slave_id: int, table_name: str) -> bool:
        """
        Fügt eine ignorierte Tabelle für einen Slave hinzu.
        
        Args:
            slave_id: ID des Slaves
            table_name: Name der zu ignorierenden Tabelle
            
        Returns:
            bool: True bei Erfolg, False sonst
        """
        with sqlite3.connect(self.config_db_path) as conn:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO ignored_tables (slave_id, table_name) VALUES (?, ?)",
                    (slave_id, table_name)
                )
                return True
            except sqlite3.Error as e:
                logger.error(f"Fehler beim Hinzufügen der ignorierten Tabelle: {e}")
                return False
    
    def remove_ignored_table(self, slave_id: int, table_name: str) -> bool:
        """
        Entfernt eine ignorierte Tabelle für einen Slave.
        
        Args:
            slave_id: ID des Slaves
            table_name: Name der nicht mehr zu ignorierenden Tabelle
            
        Returns:
            bool: True bei Erfolg, False sonst
        """
        with sqlite3.connect(self.config_db_path) as conn:
            try:
                conn.execute(
                    "DELETE FROM ignored_tables WHERE slave_id = ? AND table_name = ?",
                    (slave_id, table_name)
                )
                return True
            except sqlite3.Error as e:
                logger.error(f"Fehler beim Entfernen der ignorierten Tabelle: {e}")
                return False
    
    def add_sync_log(self, slave_id: int, status: str, message: str = "", 
                    changes_count: int = 0, duration: float = 0.0) -> int:
        """
        Fügt einen Synchronisations-Log-Eintrag hinzu.
        
        Args:
            slave_id: ID des Slaves
            status: Status der Synchronisation
            message: Nachricht zur Synchronisation
            changes_count: Anzahl der Änderungen
            duration: Dauer der Synchronisation in Sekunden
            
        Returns:
            int: ID des Log-Eintrags
        """
        with sqlite3.connect(self.config_db_path) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO sync_logs (slave_id, status, message, changes_count, duration, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (slave_id, status, message, changes_count, duration, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                return cursor.lastrowid
            except sqlite3.Error as e:
                logger.error(f"Fehler beim Hinzufügen des Sync-Logs: {e}")
                return -1
    
    def get_sync_logs(self, slave_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Gibt Synchronisations-Logs zurück.
        
        Args:
            slave_id: ID des Slaves (optional, für Filter nach Slave)
            limit: Maximale Anzahl der Logs
            
        Returns:
            List[Dict[str, Any]]: Liste der Synchronisations-Logs
        """
        if slave_id is not None:
            query = """
            SELECT l.*, s.name as slave_name 
            FROM sync_logs l
            JOIN slaves s ON l.slave_id = s.id
            WHERE l.slave_id = ?
            ORDER BY l.created_at DESC
            LIMIT ?
            """
            params = (slave_id, limit)
        else:
            query = """
            SELECT l.*, s.name as slave_name 
            FROM sync_logs l
            JOIN slaves s ON l.slave_id = s.id
            ORDER BY l.created_at DESC
            LIMIT ?
            """
            params = (limit,)
        
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall() 