"""
Modell für die Konfiguration von Slave-Datenbanken.
"""

import os
import json
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.app.core.db_manager import DatabaseManager
from backend.config.config import CONFIG_DB_PATH

class SlaveConfig:
    """
    Klasse zur Verwaltung der Konfiguration von Slave-Datenbanken.
    """
    
    def __init__(self, config_db_path: str = CONFIG_DB_PATH):
        """
        Initialisiert die SlaveConfig-Klasse.
        
        Args:
            config_db_path: Pfad zur Konfigurations-Datenbank
        """
        self.db_manager = DatabaseManager(config_db_path)
        self._create_config_tables()
    
    def _create_config_tables(self) -> None:
        """Erstellt die notwendigen Konfigurationstabellen."""
        # Tabelle für Slave-Datenbanken
        slaves_schema = """
        CREATE TABLE IF NOT EXISTS slaves (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            db_path TEXT NOT NULL,
            server_address TEXT,
            last_sync DATETIME,
            status TEXT DEFAULT 'inactive',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # Tabelle für ignorierte Tabellen
        ignored_tables_schema = """
        CREATE TABLE IF NOT EXISTS ignored_tables (
            id INTEGER PRIMARY KEY,
            slave_id INTEGER,
            table_name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (slave_id) REFERENCES slaves(id) ON DELETE CASCADE,
            UNIQUE(slave_id, table_name)
        )
        """
        
        # Tabelle für Synchronisations-Logs
        sync_logs_schema = """
        CREATE TABLE IF NOT EXISTS sync_logs (
            id INTEGER PRIMARY KEY,
            slave_id INTEGER,
            status TEXT NOT NULL,
            message TEXT,
            changes_count INTEGER DEFAULT 0,
            duration REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (slave_id) REFERENCES slaves(id) ON DELETE CASCADE
        )
        """
        
        self.db_manager.create_table_if_not_exists("slaves", slaves_schema)
        self.db_manager.create_table_if_not_exists("ignored_tables", ignored_tables_schema)
        self.db_manager.create_table_if_not_exists("sync_logs", sync_logs_schema)
    
    def add_slave(self, name: str, db_path: str, server_address: Optional[str] = None) -> int:
        """
        Fügt einen neuen Slave zur Konfiguration hinzu.
        
        Args:
            name: Name des Slaves
            db_path: Pfad zur Slave-Datenbank
            server_address: Adresse des Slave-Servers (optional)
            
        Returns:
            int: ID des neuen Slaves
        """
        with self.db_manager.get_connection() as conn:
            try:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                result = conn.execute(
                    """
                    INSERT INTO slaves (name, db_path, server_address, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (name, db_path, server_address, now, now)
                )
                return result.lastrowid
            except Exception as e:
                raise ValueError(f"Fehler beim Hinzufügen des Slaves: {e}")
    
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
        
        with self.db_manager.get_connection() as conn:
            try:
                conn.execute(sql, params)
                return True
            except Exception as e:
                raise ValueError(f"Fehler beim Aktualisieren des Slaves: {e}")
    
    def delete_slave(self, slave_id: int) -> bool:
        """
        Löscht einen Slave aus der Konfiguration.
        
        Args:
            slave_id: ID des Slaves
            
        Returns:
            bool: True bei Erfolg, False sonst
        """
        with self.db_manager.get_connection() as conn:
            try:
                # Durch Foreign-Key-Constraints werden auch verknüpfte Einträge gelöscht
                conn.execute("DELETE FROM slaves WHERE id = ?", (slave_id,))
                return True
            except Exception as e:
                raise ValueError(f"Fehler beim Löschen des Slaves: {e}")
    
    def get_slave(self, slave_id: int) -> Optional[Dict[str, Any]]:
        """
        Gibt die Konfiguration eines Slaves zurück.
        
        Args:
            slave_id: ID des Slaves
            
        Returns:
            Optional[Dict[str, Any]]: Slave-Konfiguration oder None, wenn nicht gefunden
        """
        with self.db_manager.get_connection() as conn:
            slave = conn.execute("SELECT * FROM slaves WHERE id = ?", (slave_id,)).fetchone()
            
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
        with sqlite3.connect(self.db_manager.db_path) as conn:
            # Aktiviere Row-Factory, um die Ergebnisse als Dict zu erhalten
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM slaves ORDER BY name")
            slave_rows = cursor.fetchall()
            
            # Konvertiere SQLite-Rows in echte Python-Dictionaries
            slaves = []
            for row in slave_rows:
                slave = dict(row)
                
                # Wenn die ignorierte Tabellen als String gespeichert wurden, konvertiere sie in eine Liste
                if 'ignored_tables' in slave and slave['ignored_tables']:
                    slave['ignored_tables'] = slave['ignored_tables'].split(',')
                else:
                    slave['ignored_tables'] = []
                
                slaves.append(slave)
            
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
            print(f"update_slave_sync_status: Verwende angegebenen Zeitstempel: {last_sync}")
        else:
            # Nur aktualisieren, wenn Status auf 'active' oder 'syncing' gesetzt wird
            if status in ['active', 'syncing']:
                updates.append("last_sync = ?")
                params.append(current_time)
                print(f"update_slave_sync_status: Verwende aktuellen Zeitstempel: {current_time}")
        
        params.append(slave_id)
        
        sql = f"UPDATE slaves SET {', '.join(updates)} WHERE id = ?"
        print(f"update_slave_sync_status: SQL: {sql}, Params: {params}")
        
        with self.db_manager.get_connection() as conn:
            try:
                conn.execute(sql, params)
                return True
            except Exception as e:
                raise ValueError(f"Fehler beim Aktualisieren des Sync-Status: {e}")
    
    def add_ignored_table(self, slave_id: int, table_name: str) -> bool:
        """
        Fügt eine ignorierte Tabelle für einen Slave hinzu.
        
        Args:
            slave_id: ID des Slaves
            table_name: Name der zu ignorierenden Tabelle
            
        Returns:
            bool: True bei Erfolg, False sonst
        """
        with self.db_manager.get_connection() as conn:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO ignored_tables (slave_id, table_name) VALUES (?, ?)",
                    (slave_id, table_name)
                )
                return True
            except Exception as e:
                raise ValueError(f"Fehler beim Hinzufügen der ignorierten Tabelle: {e}")
    
    def remove_ignored_table(self, slave_id: int, table_name: str) -> bool:
        """
        Entfernt eine ignorierte Tabelle für einen Slave.
        
        Args:
            slave_id: ID des Slaves
            table_name: Name der nicht mehr zu ignorierenden Tabelle
            
        Returns:
            bool: True bei Erfolg, False sonst
        """
        with self.db_manager.get_connection() as conn:
            try:
                conn.execute(
                    "DELETE FROM ignored_tables WHERE slave_id = ? AND table_name = ?",
                    (slave_id, table_name)
                )
                return True
            except Exception as e:
                raise ValueError(f"Fehler beim Entfernen der ignorierten Tabelle: {e}")
    
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
        with self.db_manager.get_connection() as conn:
            try:
                result = conn.execute(
                    """
                    INSERT INTO sync_logs (slave_id, status, message, changes_count, duration, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (slave_id, status, message, changes_count, duration, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                return result.lastrowid
            except Exception as e:
                raise ValueError(f"Fehler beim Hinzufügen des Sync-Logs: {e}")
    
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
        
        with self.db_manager.get_connection() as conn:
            return conn.execute(query, params).fetchall() 