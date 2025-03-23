"""
Datenbankmanager-Modul für die Verwaltung von SQLite-Datenbankverbindungen.
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple, Union, Any

# Logger einrichten
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Verwaltet Zugriff und Operationen auf SQLite-Datenbanken.
    """
    
    def __init__(self, db_path: str):
        """
        Initialisiert den DatabaseManager.
        
        Args:
            db_path: Pfad zur SQLite-Datenbank
        """
        self.db_path = db_path
        self._validate_db_path()
        
    def _validate_db_path(self) -> None:
        """Überprüft, ob der Datenbankpfad gültig ist."""
        if not self.db_path:
            raise ValueError("Datenbankpfad darf nicht leer sein")
        
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
    @contextmanager
    def get_connection(self) -> sqlite3.Connection:
        """
        Stellt eine Datenbankverbindung als Kontext-Manager bereit.
        
        Returns:
            sqlite3.Connection: Die Datenbankverbindung
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            # Aktiviere Foreign-Key-Constraints
            conn.execute("PRAGMA foreign_keys = ON")
            # Konfiguriere für WAL-Modus
            conn.execute("PRAGMA journal_mode = WAL")
            # Füge Row-Factory hinzu, damit Ergebnisse als Dicts zurückgegeben werden
            conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
            yield conn
            # Explizites Commit, um sicherzustellen, dass Transaktionen abgeschlossen werden
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Datenbankfehler: {e}")
            raise
        finally:
            if conn:
                conn.close()
                
    def get_all_tables(self) -> List[str]:
        """
        Gibt eine Liste aller Tabellen in der Datenbank zurück.
        
        Returns:
            List[str]: Liste der Tabellennamen
        """
        with self.get_connection() as conn:
            query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            result = conn.execute(query).fetchall()
            return [row["name"] for row in result]
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Gibt eine Liste aller Spalten einer Tabelle zurück.
        
        Args:
            table_name: Name der Tabelle
            
        Returns:
            List[str]: Liste der Spaltennamen
        """
        with self.get_connection() as conn:
            query = f"PRAGMA table_info({table_name})"
            result = conn.execute(query).fetchall()
            return [row["name"] for row in result]
    
    def get_table_schema(self, table_name: str) -> str:
        """
        Gibt das Schema (CREATE-Statement) für eine Tabelle zurück.
        
        Args:
            table_name: Name der Tabelle
            
        Returns:
            str: Das CREATE-Statement für die Tabelle
        """
        with self.get_connection() as conn:
            query = f"""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name=?
            """
            result = conn.execute(query, (table_name,)).fetchone()
            if result:
                return result["sql"]
            return ""
    
    def get_table_count(self, table_name: str) -> int:
        """
        Gibt die Anzahl der Datensätze in einer Tabelle zurück.
        
        Args:
            table_name: Name der Tabelle
            
        Returns:
            int: Anzahl der Datensätze
        """
        with self.get_connection() as conn:
            query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = conn.execute(query).fetchone()
            return result["count"]
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Führt eine SQL-Abfrage aus und gibt die Ergebnisse zurück.
        
        Args:
            query: SQL-Abfrage
            params: Parameter für die Abfrage
            
        Returns:
            List[Dict[str, Any]]: Liste der Ergebniszeilen als Dictionaries
        """
        with self.get_connection() as conn:
            result = conn.execute(query, params).fetchall()
            return result
    
    def execute_transaction(self, queries: List[Tuple[str, tuple]]) -> None:
        """
        Führt mehrere SQL-Abfragen als Transaktion aus.
        
        Args:
            queries: Liste von Tupeln (query, params)
        """
        with self.get_connection() as conn:
            try:
                conn.execute("BEGIN TRANSACTION")
                for query, params in queries:
                    conn.execute(query, params)
                conn.execute("COMMIT")
            except sqlite3.Error as e:
                conn.execute("ROLLBACK")
                logger.error(f"Transaktionsfehler: {e}")
                raise
    
    def create_table_if_not_exists(self, table_name: str, schema: str) -> None:
        """
        Erstellt eine Tabelle, falls sie nicht existiert.
        
        Args:
            table_name: Name der Tabelle
            schema: Schema-Definition (CREATE TABLE ...)
        """
        with self.get_connection() as conn:
            conn.execute(schema)
    
    def setup_change_tracking(self) -> None:
        """
        Richtet das Change-Tracking-System in der Datenbank ein.
        Erstellt eine Tabelle zur Verfolgung von Änderungen und Trigger für INSERT, UPDATE, DELETE.
        """
        # Erstelle Change-Tracking-Tabelle
        tracking_table_schema = """
        CREATE TABLE IF NOT EXISTS _sync_tracking (
            id INTEGER PRIMARY KEY,
            table_name TEXT NOT NULL,
            row_id INTEGER NOT NULL,
            operation TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        with self.get_connection() as conn:
            conn.execute(tracking_table_schema)
            
            # Hole alle Tabellen außer System- und Tracking-Tabellen
            tables = self.get_all_tables()
            tables = [t for t in tables if not t.startswith('sqlite_') and t != '_sync_tracking']
            
            # Erstelle Trigger für jede Tabelle
            for table_name in tables:
                # INSERT Trigger
                insert_trigger = f"""
                CREATE TRIGGER IF NOT EXISTS trg_{table_name}_insert AFTER INSERT ON {table_name}
                BEGIN
                    INSERT INTO _sync_tracking (table_name, row_id, operation) 
                    VALUES ('{table_name}', NEW.rowid, 'INSERT');
                END;
                """
                
                # UPDATE Trigger
                update_trigger = f"""
                CREATE TRIGGER IF NOT EXISTS trg_{table_name}_update AFTER UPDATE ON {table_name}
                BEGIN
                    INSERT INTO _sync_tracking (table_name, row_id, operation) 
                    VALUES ('{table_name}', NEW.rowid, 'UPDATE');
                END;
                """
                
                # DELETE Trigger
                delete_trigger = f"""
                CREATE TRIGGER IF NOT EXISTS trg_{table_name}_delete AFTER DELETE ON {table_name}
                BEGIN
                    INSERT INTO _sync_tracking (table_name, row_id, operation) 
                    VALUES ('{table_name}', OLD.rowid, 'DELETE');
                END;
                """
                
                # Führe Trigger-Erstellung aus
                conn.execute(insert_trigger)
                conn.execute(update_trigger)
                conn.execute(delete_trigger)
    
    def get_changes_since(self, timestamp: str, ignored_tables: List[str] = None) -> List[Dict[str, Any]]:
        """
        Gibt Änderungen seit einem bestimmten Zeitpunkt zurück.
        
        Args:
            timestamp: Zeitstempel im Format YYYY-MM-DD HH:MM:SS
            ignored_tables: Liste von Tabellen, die ignoriert werden sollen
            
        Returns:
            List[Dict[str, Any]]: Liste der Änderungen
        """
        if ignored_tables is None:
            ignored_tables = []
            
        placeholder = ','.join(['?'] * len(ignored_tables))
        ignore_clause = f"AND table_name NOT IN ({placeholder})" if ignored_tables else ""
        
        # Zeitzonensicherer Vergleich - SQLite speichert in UTC, konvertiere zur Sicherheit
        # Füge eine kleine Zeitpuffer hinzu (30 Sekunden), um sicherzustellen, dass keine Änderungen verpasst werden
        buffer_time = "30 seconds"
        
        query = f"""
        SELECT id, table_name, row_id, operation, timestamp 
        FROM _sync_tracking 
        WHERE datetime(timestamp) > datetime(?, '-{buffer_time}') {ignore_clause}
        ORDER BY timestamp ASC
        """
        
        logger.debug(f"Suche Änderungen seit {timestamp} (mit {buffer_time} Puffer)")
        
        with self.get_connection() as conn:
            params = [timestamp] + ignored_tables if ignored_tables else [timestamp]
            result = conn.execute(query, params).fetchall()
            
            # Entferne Duplikate (behalte nur die neueste Änderung pro Zeile)
            row_operations = {}
            for change in result:
                key = (change["table_name"], change["row_id"])
                # Wenn der Eintrag neu ist oder neuer als der bisherige
                if key not in row_operations or change["timestamp"] > row_operations[key]["timestamp"]:
                    row_operations[key] = change
            
            # Konvertiere zurück zur Liste und entferne DELETE-Operationen, 
            # wenn die Zeile später wieder eingefügt wurde
            filtered_changes = []
            for key, change in row_operations.items():
                # Wenn eine DELETE-Operation ist, prüfe ob es später wieder eingefügt wurde
                if change["operation"] == "DELETE":
                    table_name, row_id = key
                    # Prüfe mit direkter Abfrage, ob die Zeile existiert
                    row_exists = False
                    try:
                        row_exists_query = f"SELECT 1 FROM {table_name} WHERE rowid = ? LIMIT 1"
                        row_check = conn.execute(row_exists_query, (row_id,)).fetchone()
                        row_exists = row_check is not None
                    except sqlite3.Error:
                        # Tabelle existiert möglicherweise nicht mehr
                        pass
                    
                    if not row_exists:
                        filtered_changes.append(change)
                else:
                    filtered_changes.append(change)
            
            logger.debug(f"Gefunden: {len(result)} Änderungen, nach Filterung: {len(filtered_changes)}")
            return filtered_changes
    
    def backup_database(self, backup_path: str) -> None:
        """
        Erstellt ein Backup der Datenbank.
        
        Args:
            backup_path: Pfad für das Backup
        """
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        source = sqlite3.connect(self.db_path)
        destination = sqlite3.connect(backup_path)
        
        try:
            source.backup(destination)
            logger.info(f"Datenbank-Backup erstellt: {backup_path}")
        except sqlite3.Error as e:
            logger.error(f"Backup-Fehler: {e}")
            raise
        finally:
            source.close()
            destination.close() 