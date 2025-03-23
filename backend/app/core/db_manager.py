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
    
    def __init__(self, db_path: str, check_same_thread: bool = True):
        """
        Initialisiert den DatabaseManager.
        
        Args:
            db_path: Pfad zur SQLite-Datenbank
            check_same_thread: Ob SQLite Thread-Sicherheitsprüfungen durchführen soll
        """
        self.db_path = db_path
        self.check_same_thread = check_same_thread
        
        # Stelle sicher, dass das Verzeichnis existiert
        if not os.path.exists(os.path.dirname(db_path)):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            logger.info(f"Verzeichnis für Datenbank erstellt: {os.path.dirname(db_path)}")
        
        # Stelle sicher, dass die Datenbank existiert oder erstelle sie
        if not os.path.exists(db_path):
            self._create_empty_db()
            logger.info(f"Neue leere Datenbank erstellt: {db_path}")
        
    def _create_empty_db(self):
        """Erstellt eine leere Datenbank-Datei."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Erstelle eine leere Datenbank mit SQLite-Standardkonfiguration
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                
                # Eine leere Tabelle, die wir später nicht verwenden, nur um zu bestätigen, dass die DB erstellt wurde
                conn.execute("CREATE TABLE IF NOT EXISTS _db_info (key TEXT PRIMARY KEY, value TEXT)")
                conn.execute(
                    "INSERT OR REPLACE INTO _db_info (key, value) VALUES (?, ?)",
                    ("creation_date", "CREATE_DATE_PLACEHOLDER")
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Fehler beim Erstellen der leeren Datenbank: {e}")
            raise
        
    @contextmanager
    def get_connection(self) -> sqlite3.Connection:
        """
        Stellt eine Datenbankverbindung als Kontext-Manager bereit.
        
        Returns:
            sqlite3.Connection: Die Datenbankverbindung
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=self.check_same_thread)
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
        """Richtet Tracking-Tabelle und Trigger für Änderungen ein."""
        with self.get_connection() as conn:
            # Erstelle Tracking-Tabelle
            conn.execute('''
            CREATE TABLE IF NOT EXISTS _sync_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                row_id INTEGER NOT NULL,
                operation TEXT NOT NULL,
                changed_columns TEXT,
                old_values TEXT,
                new_values TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Erstelle Index
            conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_sync_tracking_timestamp
            ON _sync_tracking (timestamp)
            ''')
            
            # Erstelle Tabelle für verarbeitete Änderungen
            conn.execute('''
            CREATE TABLE IF NOT EXISTS _sync_processed_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                change_id INTEGER NOT NULL,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (change_id) REFERENCES _sync_tracking(id) ON DELETE CASCADE
            )
            ''')
            
            # Migriere _sync_tracking-Tabelle, wenn sie bereits existiert aber die Spalten fehlen
            self._migrate_sync_tracking_table(conn)
            
            system_tables = ['_sync_tracking', '_sync_processed_changes', 'sqlite_sequence', '_db_info']
            # Hole alle Tabellen, die nicht zu den Systemtabellen gehören
            all_tables = self.get_all_tables()
            tables = [table for table in all_tables if table not in system_tables]
            
            for table_name in tables:
                if table_name.startswith('sqlite_') or table_name in system_tables:
                    continue
                
                # Hole Spaltennamen für die Tabelle
                columns = self.get_table_columns(table_name)
                if not columns:
                    continue
                
                column_list = ','.join(columns)
                
                # Funktion zum Erstellen von JSON-Objekten als Text
                # Verwende eine robustere Methode zur JSON-Erzeugung, die keine json_object-Funktion erfordert
                json_builder = lambda col_prefix: (
                    f"'{{' || " +
                    " || ',' || ".join([
                        f"'\"' || '{col}' || '\":' || CASE WHEN {col_prefix}.{col} IS NULL THEN 'null' " +
                        f"WHEN typeof({col_prefix}.{col}) IN ('integer', 'real') THEN {col_prefix}.{col} " +
                        f"ELSE '\"' || replace(replace({col_prefix}.{col}, '\\', '\\\\'), '\"', '\\\"') || '\"' END"
                        for col in columns
                    ]) +
                    " || '}}'"
                )
                
                # INSERT Trigger - mit Erfassung der neuen Werte
                insert_trigger = f"""
                CREATE TRIGGER IF NOT EXISTS trg_{table_name}_insert AFTER INSERT ON {table_name}
                BEGIN
                    INSERT INTO _sync_tracking (
                        table_name, 
                        row_id, 
                        operation,
                        changed_columns,
                        old_values,
                        new_values
                    ) 
                    VALUES (
                        '{table_name}', 
                        NEW.rowid, 
                        'INSERT',
                        '{column_list}',
                        NULL,
                        {json_builder('NEW')}
                    );
                END;
                """
                
                # UPDATE Trigger - mit Erfassung der alten und neuen Werte
                # Nur triggern, wenn sich tatsächlich etwas geändert hat
                update_trigger = f"""
                CREATE TRIGGER IF NOT EXISTS trg_{table_name}_update AFTER UPDATE ON {table_name}
                WHEN {' OR '.join([f"OLD.{column_name} IS NOT NEW.{column_name}" for column_name in columns])}
                BEGIN
                    INSERT INTO _sync_tracking (
                        table_name, 
                        row_id, 
                        operation,
                        changed_columns,
                        old_values,
                        new_values
                    ) 
                    VALUES (
                        '{table_name}', 
                        NEW.rowid, 
                        'UPDATE',
                        (SELECT json_group_array(column_name) FROM (
                            {' UNION ALL '.join([f"SELECT '{column_name}' as column_name FROM (SELECT 1) WHERE OLD.{column_name} IS NOT NEW.{column_name}" for column_name in columns])}
                        )),
                        {json_builder('OLD')},
                        {json_builder('NEW')}
                    );
                END;
                """
                
                # DELETE Trigger - speichert die alten Werte
                delete_trigger = f"""
                CREATE TRIGGER IF NOT EXISTS trg_{table_name}_delete AFTER DELETE ON {table_name}
                BEGIN
                    INSERT INTO _sync_tracking (
                        table_name, 
                        row_id, 
                        operation,
                        changed_columns,
                        old_values,
                        new_values
                    ) 
                    VALUES (
                        '{table_name}', 
                        OLD.rowid, 
                        'DELETE',
                        '{column_list}',
                        {json_builder('OLD')},
                        NULL
                    );
                END;
                """
                
                # Führe Trigger-Erstellung aus
                try:
                    conn.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_insert")
                    conn.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_update")
                    conn.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_delete")
                    
                    conn.execute(insert_trigger)
                    conn.execute(update_trigger)
                    conn.execute(delete_trigger)
                    logger.info(f"Trigger für Tabelle {table_name} erfolgreich erstellt")
                except sqlite3.Error as e:
                    logger.error(f"Fehler beim Erstellen der Trigger für Tabelle {table_name}: {e}")
    
    def _migrate_sync_tracking_table(self, conn: sqlite3.Connection) -> None:
        """
        Migriert die _sync_tracking-Tabelle, um sicherzustellen, dass alle erforderlichen Spalten vorhanden sind.
        """
        try:
            cursor = conn.cursor()
            # Prüfe, ob die Tabelle existiert
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_sync_tracking'")
            if not cursor.fetchone():
                # Tabelle existiert nicht, keine Migration nötig
                return
                
            # Prüfe, welche Spalten vorhanden sind
            cursor.execute("PRAGMA table_info(_sync_tracking)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Überprüfe fehlende Spalten und füge sie hinzu
            missing_columns = []
            if "changed_columns" not in column_names:
                missing_columns.append("changed_columns TEXT")
            if "old_values" not in column_names:
                missing_columns.append("old_values TEXT")
            if "new_values" not in column_names:
                missing_columns.append("new_values TEXT")
            
            # Spaltenname könnte variieren (row_id vs record_id)
            if "row_id" not in column_names and "record_id" in column_names:
                # Wir müssen die record_id-Spalte in row_id umbenennen
                # Da SQLite keine direkte RENAME COLUMN unterstützt, müssen wir eine neue Tabelle erstellen
                # und die Daten migrieren
                logger.info("Migration von _sync_tracking: record_id wird in row_id umbenannt")
                cursor.execute('''
                CREATE TABLE _sync_tracking_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    row_id INTEGER NOT NULL,
                    operation TEXT NOT NULL,
                    changed_columns TEXT,
                    old_values TEXT,
                    new_values TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0
                )
                ''')
                
                # Kopiere Daten und benenne record_id in row_id um
                cursor.execute('''
                INSERT INTO _sync_tracking_new (id, table_name, row_id, operation, timestamp, processed)
                SELECT id, table_name, record_id, operation, timestamp, processed FROM _sync_tracking
                ''')
                
                # Lösche alte Tabelle und benenne neue Tabelle um
                cursor.execute("DROP TABLE _sync_tracking")
                cursor.execute("ALTER TABLE _sync_tracking_new RENAME TO _sync_tracking")
                
                # Neuer Index für die umbenannte Tabelle
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sync_tracking_timestamp
                ON _sync_tracking (timestamp)
                ''')
                
                logger.info("Migration von record_id zu row_id erfolgreich abgeschlossen")
            else:
                # Füge einzelne fehlende Spalten hinzu
                for column_def in missing_columns:
                    column_name = column_def.split()[0]
                    logger.info(f"Migration von _sync_tracking: Füge {column_name}-Spalte hinzu")
                    try:
                        cursor.execute(f"ALTER TABLE _sync_tracking ADD COLUMN {column_def}")
                        logger.info(f"Migration {column_name} erfolgreich")
                    except sqlite3.Error as e:
                        logger.error(f"Fehler beim Hinzufügen der Spalte {column_name}: {e}")
            
            conn.commit()
            logger.info("_sync_tracking Tabellen-Migration abgeschlossen")
        except sqlite3.Error as e:
            logger.error(f"Fehler bei der _sync_tracking Migration: {e}")
            conn.rollback()
    
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
        
        # Zeitzonensicherer Vergleich
        buffer_time = "30 seconds"
        
        query = f"""
        SELECT * FROM _sync_tracking 
        WHERE datetime(timestamp) > datetime(?, '-{buffer_time}')
        {ignore_clause}
        ORDER BY timestamp ASC
        """
        
        params = (timestamp,) + tuple(ignored_tables)
        
        with self.get_connection() as conn:
            try:
                result = conn.execute(query, params).fetchall()
                logger.info(f"Gefundene Änderungen seit {timestamp}: {len(result)}")
                return result
            except sqlite3.Error as e:
                logger.error(f"Fehler beim Abrufen der Änderungen: {e}")
                return []
    
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
    
    def get_unprocessed_changes(self, conn, limit=100):
        """
        Holt unverarbeitete Änderungen aus der Tracking-Tabelle.
        
        Args:
            conn: Datenbankverbindung
            limit: Maximale Anzahl von Änderungen
            
        Returns:
            List[Dict]: Liste von Änderungen
        """
        # Prüfe, ob die Tabelle existiert, und erstelle sie, falls nicht
        conn.execute('''
        CREATE TABLE IF NOT EXISTS _sync_processed_changes (
            id INTEGER PRIMARY KEY,
            change_id INTEGER NOT NULL,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Abfrage für unverarbeitete Änderungen
        query = '''
        SELECT id, table_name, row_id as record_id, operation, timestamp
        FROM _sync_tracking
        WHERE id NOT IN (SELECT change_id FROM _sync_processed_changes)
        ORDER BY id ASC
        LIMIT ?
        '''
        
        result = conn.execute(query, (limit,)).fetchall()
        return result
    
    def mark_changes_as_processed(self, conn, change_ids):
        """
        Markiert Änderungen als verarbeitet.
        
        Args:
            conn: Datenbankverbindung
            change_ids: Liste von Änderungs-IDs
        """
        if not change_ids:
            return
        
        # Erstelle die Tabelle, falls sie nicht existiert
        conn.execute('''
        CREATE TABLE IF NOT EXISTS _sync_processed_changes (
            id INTEGER PRIMARY KEY,
            change_id INTEGER NOT NULL,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Füge die verarbeiteten Änderungen hinzu
        for change_id in change_ids:
            conn.execute(
                "INSERT INTO _sync_processed_changes (change_id) VALUES (?)",
                (change_id,)
            ) 