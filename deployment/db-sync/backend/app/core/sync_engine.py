"""
Synchronisations-Engine für SQLite-Datenbanken.
"""

import os
import time
import datetime
import hashlib
import logging
import sqlite3
import threading
import random
from typing import Dict, List, Optional, Tuple, Any

from backend.app.core.db_manager import DatabaseManager
from backend.config.config import CHUNK_SIZE

# Logger einrichten
logger = logging.getLogger(__name__)

class SyncEngine:
    """
    Engine zur Synchronisation von SQLite-Datenbanken im Master-Slave-Modus.
    """
    
    def __init__(self, master_db_path: str, slave_db_path: str, ignored_tables: List[str] = None):
        """
        Initialisiert die Synchronisations-Engine.
        
        Args:
            master_db_path: Pfad zur Master-Datenbank
            slave_db_path: Pfad zur Slave-Datenbank
            ignored_tables: Liste von Tabellen, die ignoriert werden sollen
        """
        self.master_db = DatabaseManager(master_db_path)
        self.slave_db = DatabaseManager(slave_db_path)
        self.ignored_tables = ignored_tables or []
        self.sync_lock = threading.Lock()
        self._setup_databases()
        
    def _setup_databases(self) -> None:
        """Richtet die Datenbanken für die Synchronisation ein."""
        try:
            # Stelle sicher, dass die Master-Datenbank Change-Tracking hat
            self.master_db.setup_change_tracking()
            
            # Erstelle Konfigurationstabelle in Slave-DB, falls nicht vorhanden
            sync_config_schema = """
            CREATE TABLE IF NOT EXISTS _sync_config (
                id INTEGER PRIMARY KEY,
                last_sync_timestamp TEXT NOT NULL,
                master_db_path TEXT NOT NULL
            )
            """
            self.slave_db.create_table_if_not_exists("_sync_config", sync_config_schema)
            
            # Initialisiere die Konfiguration, falls nicht vorhanden
            with self.slave_db.get_connection() as conn:
                config = conn.execute("SELECT * FROM _sync_config").fetchone()
                if not config:
                    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    conn.execute(
                        "INSERT INTO _sync_config (last_sync_timestamp, master_db_path) VALUES (?, ?)",
                        (now, self.master_db.db_path)
                    )
        except Exception as e:
            logger.error(f"Fehler beim Einrichten der Datenbanken: {e}")
            raise
            
    def get_last_sync_timestamp(self) -> str:
        """
        Gibt den Zeitstempel der letzten Synchronisation zurück.
        
        Returns:
            str: Zeitstempel im Format YYYY-MM-DD HH:MM:SS
        """
        with self.slave_db.get_connection() as conn:
            result = conn.execute("SELECT last_sync_timestamp FROM _sync_config").fetchone()
            return result["last_sync_timestamp"] if result else "1970-01-01 00:00:00"
    
    def update_last_sync_timestamp(self) -> None:
        """Aktualisiert den Zeitstempel der letzten Synchronisation."""
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Aktualisiere last_sync_timestamp in der Slave-DB auf {now}")
        try:
            # Direkte Verbindung zur SQLite-Datenbank öffnen
            conn = sqlite3.connect(self.slave_db.db_path)
            try:
                # Zuerst den aktuellen Wert abfragen
                cursor = conn.cursor()
                cursor.execute("SELECT last_sync_timestamp FROM _sync_config")
                current = cursor.fetchone()
                logger.info(f"Aktueller Wert in _sync_config: {current}")
                
                # Update durchführen
                cursor.execute(
                    "UPDATE _sync_config SET last_sync_timestamp = ?",
                    (now,)
                )
                
                # Commit sicherstellen
                conn.commit()
                
                # Prüfen, ob Update erfolgreich war
                cursor.execute("SELECT last_sync_timestamp FROM _sync_config")
                after = cursor.fetchone()
                logger.info(f"Neuer Wert in _sync_config nach Update: {after}")
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Zeitstempels: {e}", exc_info=True)
    
    def verify_schema_compatibility(self) -> bool:
        """
        Überprüft, ob die Schemata von Master und Slave kompatibel sind.
        
        Returns:
            bool: True, wenn kompatibel, sonst False
        """
        # Hole alle Tabellen vom Master außer System- und Sync-Tabellen
        master_tables = self.master_db.get_all_tables()
        master_tables = [t for t in master_tables if not t.startswith(('sqlite_', '_sync'))]
        
        # Hole alle Tabellen vom Slave außer System- und Sync-Tabellen
        slave_tables = self.slave_db.get_all_tables()
        slave_tables = [t for t in slave_tables if not t.startswith(('sqlite_', '_sync'))]
        
        # Überprüfe, ob alle erforderlichen Tabellen im Slave vorhanden sind
        required_tables = [t for t in master_tables if t not in self.ignored_tables]
        missing_tables = [t for t in required_tables if t not in slave_tables]
        
        if missing_tables:
            logger.warning(f"Fehlende Tabellen im Slave: {missing_tables}")
            self._create_missing_tables(missing_tables)
        
        # Überprüfe, ob Spalten übereinstimmen
        for table in required_tables:
            if table in slave_tables:
                master_columns = set(self.master_db.get_table_columns(table))
                slave_columns = set(self.slave_db.get_table_columns(table))
                
                if master_columns != slave_columns:
                    logger.warning(f"Unterschiedliche Spalten in Tabelle {table}")
                    return False
        
        return True
    
    def _create_missing_tables(self, missing_tables: List[str]) -> None:
        """
        Erstellt fehlende Tabellen im Slave basierend auf dem Master-Schema.
        
        Args:
            missing_tables: Liste der fehlenden Tabellen
        """
        for table in missing_tables:
            # Hole Schema vom Master
            schema = self.master_db.get_table_schema(table)
            if schema:
                # Erstelle Tabelle im Slave
                try:
                    with self.slave_db.get_connection() as conn:
                        conn.execute(schema)
                    logger.info(f"Tabelle {table} im Slave erstellt")
                except sqlite3.Error as e:
                    logger.error(f"Fehler beim Erstellen der Tabelle {table}: {e}")
    
    def sync_databases(self) -> Dict[str, Any]:
        """
        Synchronisiert die Datenbanken.
        Überprüft die Schema-Kompatibilität und wendet Änderungen an.
        
        Returns:
            Dict[str, Any]: Synchronisationsergebnis
        """
        start_time = time.time()
        
        try:
            # Überprüfe Schema-Kompatibilität
            if not self.verify_schema_compatibility():
                return {"status": "error", "message": "Schema-Inkompatibilität zwischen Master und Slave"}
            
            # Verbesserte Änderungserkennung
            # Statt nur Zeitstempel zu vergleichen, ermittle Änderungen durch direkten Vergleich
            master_tables = self.master_db.get_all_tables()
            master_tables = [t for t in master_tables if not t.startswith(('sqlite_', '_sync')) and t not in self.ignored_tables]
            
            changes = []
            
            # Überprüfe zuerst _sync_tracking-Änderungen (traditioneller Ansatz)
            last_sync = self.get_last_sync_timestamp()
            tracking_changes = self.master_db.get_changes_since(last_sync, self.ignored_tables)
            changes.extend(tracking_changes)
            
            # Falls keine Änderungen im Tracking gefunden wurden, überprüfe Tabellen auf fehlende Daten
            if len(changes) == 0:
                logger.info("Keine Änderungen durch Tracking gefunden, überprüfe Tabellen direkt")
                with self.master_db.get_connection() as master_conn, self.slave_db.get_connection() as slave_conn:
                    # Konfiguriere Verbindungen für die richtigen Rückgabetypen
                    master_conn.row_factory = sqlite3.Row
                    slave_conn.row_factory = sqlite3.Row
                    
                    for table in master_tables:
                        # Prüfe, ob die Tabelle im Slave existiert
                        table_exists = slave_conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                        ).fetchone()
                        
                        if not table_exists:
                            logger.warning(f"Tabelle {table} existiert nicht im Slave, überspringe.")
                            continue
                            
                        # Vergleiche Zeilenanzahl der Tabellen
                        try:
                            master_count_result = master_conn.execute(f"SELECT COUNT(*) as count FROM [{table}]").fetchone()
                            master_count = master_count_result["count"] if master_count_result else 0
                            
                            slave_count_result = slave_conn.execute(f"SELECT COUNT(*) as count FROM [{table}]").fetchone()
                            slave_count = slave_count_result["count"] if slave_count_result else 0
                            
                            if master_count != slave_count:
                                logger.info(f"Differenz in Tabellenanzahl gefunden: {table} (Master: {master_count}, Slave: {slave_count})")
                                
                                # Finde IDs, die im Slave fehlen
                                try:
                                    master_ids = set(row[0] for row in master_conn.execute(f"SELECT rowid FROM [{table}]").fetchall())
                                    slave_ids = set(row[0] for row in slave_conn.execute(f"SELECT rowid FROM [{table}]").fetchall())
                                    
                                    missing_ids = master_ids - slave_ids
                                    extra_ids = slave_ids - master_ids
                                    
                                    logger.info(f"Tabelle {table}: {len(missing_ids)} fehlende Einträge, {len(extra_ids)} überflüssige Einträge")
                                    
                                    # Füge Änderungen für fehlende IDs hinzu
                                    for row_id in missing_ids:
                                        changes.append({
                                            "table_name": table,
                                            "row_id": row_id,
                                            "operation": "INSERT"
                                        })
                                        
                                    # Füge Änderungen für überflüssige IDs hinzu
                                    for row_id in extra_ids:
                                        changes.append({
                                            "table_name": table,
                                            "row_id": row_id,
                                            "operation": "DELETE"
                                        })
                                except Exception as id_e:
                                    logger.error(f"Fehler beim Vergleich der IDs für Tabelle {table}: {str(id_e)}")
                                    continue
                            else:
                                # Auch wenn die Anzahl gleich ist, prüfe stichprobenartig auf Unterschiede
                                try:
                                    # Hole alle IDs
                                    master_ids = set(row[0] for row in master_conn.execute(f"SELECT rowid FROM [{table}]").fetchall())
                                    slave_ids = set(row[0] for row in slave_conn.execute(f"SELECT rowid FROM [{table}]").fetchall())
                                    
                                    # Finde gemeinsame IDs
                                    common_ids = master_ids.intersection(slave_ids)
                                    
                                    # Stichprobenartig einige IDs überprüfen (maximal 5 pro Tabelle)
                                    if common_ids:
                                        sample_size = min(5, len(common_ids))
                                        sample_ids = random.sample(list(common_ids), sample_size)
                                        
                                        for row_id in sample_ids:
                                            # Hole Daten von Master und Slave
                                            master_row = master_conn.execute(f"SELECT * FROM [{table}] WHERE rowid = ?", (row_id,)).fetchone()
                                            slave_row = slave_conn.execute(f"SELECT * FROM [{table}] WHERE rowid = ?", (row_id,)).fetchone()
                                            
                                            # Vergleiche die Daten
                                            if master_row and slave_row:
                                                try:
                                                    columns = [column for column in master_row.keys()]
                                                    for col in columns:
                                                        if master_row[col] != slave_row[col]:
                                                            # Füge Änderung hinzu
                                                            changes.append({
                                                                "table_name": table,
                                                                "row_id": row_id,
                                                                "operation": "UPDATE"
                                                            })
                                                            logger.info(f"Unterschied in Tabelle {table}, ID {row_id}, Spalte {col} gefunden")
                                                            break
                                                except Exception as compare_e:
                                                    logger.error(f"Fehler beim Vergleich der Daten für Tabelle {table}, ID {row_id}: {str(compare_e)}")
                                                    continue
                                except Exception as sample_e:
                                    logger.error(f"Fehler bei der Stichprobenprüfung für Tabelle {table}: {str(sample_e)}")
                                    continue
                        except Exception as count_e:
                            logger.error(f"Fehler beim Zählen der Einträge für Tabelle {table}: {str(count_e)}")
                            continue
            
            changes_count = len(changes)
            logger.info(f"{changes_count} Änderungen gefunden")
            
            if changes_count > 0:
                # Wende Änderungen an
                self._apply_changes(changes)
                
                # Aktualisiere Zeitstempel der letzten Synchronisation
                self.update_last_sync_timestamp()
                
                return {
                    "status": "success",
                    "message": f"Synchronisation erfolgreich: {changes_count} Änderungen",
                    "changes_count": changes_count,
                    "duration": time.time() - start_time
                }
            else:
                # Aktualisiere Zeitstempel der letzten Synchronisation
                self.update_last_sync_timestamp()
                
                return {
                    "status": "success",
                    "message": "Keine Änderungen seit der letzten Synchronisation",
                    "changes_count": 0,
                    "duration": time.time() - start_time
                }
                
        except Exception as e:
            error_msg = f"Fehler bei der Synchronisation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error", 
                "message": error_msg,
                "duration": time.time() - start_time
            }
    
    def _apply_changes(self, changes: List[Dict[str, Any]]) -> None:
        """
        Wendet Änderungen auf die Slave-Datenbank an.
        
        Args:
            changes: Liste der anzuwendenden Änderungen
        """
        with self.slave_db.get_connection() as slave_conn:
            try:
                slave_conn.execute("BEGIN TRANSACTION")
                
                for change in changes:
                    table_name = change["table_name"]
                    row_id = change["row_id"]
                    operation = change["operation"]
                    
                    if operation in ("INSERT", "UPDATE"):
                        # Hole aktuellen Datensatz vom Master
                        with self.master_db.get_connection() as master_conn:
                            row_data = master_conn.execute(
                                f"SELECT * FROM {table_name} WHERE rowid = ?", 
                                (row_id,)
                            ).fetchone()
                        
                        if row_data:
                            columns = self.master_db.get_table_columns(table_name)
                            
                            # Konstruiere SQL-Anweisung
                            if operation == "INSERT" or not self._row_exists(slave_conn, table_name, row_id):
                                # INSERT
                                placeholders = ','.join(['?'] * len(columns))
                                columns_str = ','.join(columns)
                                values = [row_data[col] for col in columns]
                                
                                sql = f"INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                                slave_conn.execute(sql, values)
                            else:
                                # UPDATE
                                set_clause = ','.join([f"{col} = ?" for col in columns])
                                values = [row_data[col] for col in columns]
                                
                                sql = f"UPDATE {table_name} SET {set_clause} WHERE rowid = ?"
                                slave_conn.execute(sql, values + [row_id])
                    
                    elif operation == "DELETE":
                        # DELETE
                        if self._row_exists(slave_conn, table_name, row_id):
                            sql = f"DELETE FROM {table_name} WHERE rowid = ?"
                            slave_conn.execute(sql, (row_id,))
                
                slave_conn.execute("COMMIT")
                logger.info(f"{len(changes)} Änderungen erfolgreich angewendet")
                
            except Exception as e:
                slave_conn.execute("ROLLBACK")
                logger.error(f"Fehler beim Anwenden der Änderungen: {e}")
                raise
    
    def _row_exists(self, conn: sqlite3.Connection, table_name: str, row_id: int) -> bool:
        """
        Überprüft, ob eine Zeile in einer Tabelle existiert.
        
        Args:
            conn: Datenbankverbindung
            table_name: Name der Tabelle
            row_id: ID der Zeile
            
        Returns:
            bool: True, wenn die Zeile existiert, sonst False
        """
        query = f"SELECT 1 FROM {table_name} WHERE rowid = ? LIMIT 1"
        result = conn.execute(query, (row_id,)).fetchone()
        return result is not None
    
    def initial_sync(self, temp_dir: str = None) -> Dict[str, Any]:
        """
        Führt eine initiale vollständige Synchronisation der Datenbanken durch.
        
        Args:
            temp_dir: Verzeichnis für temporäre Dateien
            
        Returns:
            Dict[str, Any]: Synchronisationsergebnis
        """
        # Verhindere parallele Synchronisierung
        if not self.sync_lock.acquire(blocking=False):
            return {"status": "running", "message": "Eine Synchronisation läuft bereits"}
        
        start_time = time.time()
        status = "success"
        message = "Initiale Synchronisation erfolgreich"
        
        try:
            # Erstelle temporäres Verzeichnis, falls nicht angegeben
            if not temp_dir:
                temp_dir = os.path.join(os.path.dirname(self.slave_db.db_path), "temp")
                os.makedirs(temp_dir, exist_ok=True)
            
            temp_db_path = os.path.join(temp_dir, "temp_master.db")
            
            # Erstelle eine Kopie der Master-DB
            with self.master_db.get_connection() as master_conn:
                # Führe WAL-Checkpoint durch
                master_conn.execute("PRAGMA wal_checkpoint(FULL)")
            
            self.master_db.backup_database(temp_db_path)
            
            # Hole Tabellenliste vom Master und sortiere sie nach Abhängigkeiten
            master_tables = self.master_db.get_all_tables()
            master_tables = [t for t in master_tables if not t.startswith(('sqlite_', '_sync')) 
                            and t not in self.ignored_tables]
            
            # Versuche, Tabellen nach Abhängigkeiten zu sortieren
            # Standardtabellen, die weniger wahrscheinlich Fremdschlüssel haben, zuerst
            # (Dies ist eine Heuristik und kann je nach Datenbankdesign angepasst werden)
            prioritized_tables = []
            standard_tables = []
            relation_tables = []
            
            # Klassifiziere Tabellen nach Namenskonventionen
            for table in master_tables:
                if table.lower() in ['kategorien', 'categories', 'types', 'typen', 'status', 'settings', 'einstellungen']:
                    # Diese Tabellen enthalten oft Grunddaten und haben weniger Abhängigkeiten
                    prioritized_tables.append(table)
                elif '_' in table or any(table.lower().endswith(s) for s in ['_relation', '_mapping', '_map', '_link']):
                    # Diese Tabellen sind oft Beziehungstabellen und sollten zuletzt synchronisiert werden
                    relation_tables.append(table)
                else:
                    # Alle anderen Tabellen
                    standard_tables.append(table)
            
            # Sortiere Tabellen in der Reihenfolge: Prioritätstabellen -> Standardtabellen -> Beziehungstabellen
            sorted_tables = prioritized_tables + standard_tables + relation_tables
            logger.info(f"Tabellen für die Synchronisation sortiert: {sorted_tables}")
            
            # Kopiere alle Tabellen
            with sqlite3.connect(temp_db_path) as source_conn, self.slave_db.get_connection() as slave_conn:
                # Konfiguriere Verbindungen
                source_conn.row_factory = sqlite3.Row
                
                # Deaktiviere Fremdschlüsselprüfungen während der Synchronisation
                slave_conn.execute("PRAGMA foreign_keys = OFF")
                slave_conn.execute("BEGIN TRANSACTION")
                
                try:
                    for table in sorted_tables:
                        # Prüfe, ob die Tabelle im Slave existiert
                        table_exists = slave_conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                        ).fetchone()
                        
                        if not table_exists:
                            logger.warning(f"Tabelle {table} existiert nicht im Slave, überspringe.")
                            continue

                        # Lösche vorhandene Daten in der Slave-Tabelle
                        slave_conn.execute(f"DELETE FROM [{table}]")
                        
                        # Kopiere Daten von Master zu Slave
                        for batch in self._get_data_in_batches(source_conn, table, 1000):
                            if not batch or len(batch) == 0:
                                continue
                            
                            # Stelle sicher, dass wir die Spalten als Liste erhalten
                            columns = []
                            try:
                                for key in batch[0].keys():
                                    columns.append(key)
                                    
                                if not columns:
                                    logger.warning(f"Keine Spalten in Tabelle {table} gefunden, überspringe.")
                                    continue
                                    
                                placeholders = ','.join(['?'] * len(columns))
                                columns_str = ','.join([f"[{column}]" for column in columns])
                                
                                insert_sql = f"INSERT INTO [{table}] ({columns_str}) VALUES ({placeholders})"
                                
                                # Daten vorbereiten und einfügen
                                batch_data = []
                                for row in batch:
                                    # Stelle sicher, dass wir die Werte robust extrahieren
                                    values = []
                                    for column in columns:
                                        try:
                                            # Versuche zuerst über den Namen
                                            values.append(row[column])
                                        except (IndexError, KeyError) as e:
                                            # Falls das nicht funktioniert, setze NULL
                                            logger.warning(f"Spalte {column} in Tabelle {table} nicht gefunden: {str(e)}. Verwende NULL.")
                                            values.append(None)
                                            
                                    batch_data.append(values)
                                
                                # Führe den Batch-Insert durch
                                try:
                                    slave_conn.executemany(insert_sql, batch_data)
                                except sqlite3.IntegrityError as e:
                                    logger.error(f"Integritätsfehler beim Einfügen in Tabelle {table}: {str(e)}")
                                    # Versuche es mit einzelnen Einfügungen, um Fehler zu isolieren
                                    for i, values in enumerate(batch_data):
                                        try:
                                            slave_conn.execute(insert_sql, values)
                                        except sqlite3.IntegrityError as row_e:
                                            logger.error(f"Konnte Zeile {i} nicht einfügen: {str(row_e)}")
                            except Exception as e:
                                logger.error(f"Fehler beim Verarbeiten der Tabelle {table}: {str(e)}")
                                continue
                    
                    # Aktualisiere den Synchronisationszeitstempel
                    self.update_last_sync_timestamp()
                    
                    # Aktiviere Fremdschlüsselprüfungen wieder
                    slave_conn.execute("PRAGMA foreign_keys = ON")
                    slave_conn.execute("COMMIT")
                except Exception as e:
                    slave_conn.execute("ROLLBACK")
                    status = "error"
                    message = f"Fehler bei der initialen Synchronisation: {str(e)}"
                    logger.error(message, exc_info=True)
                    raise
            
            # Lösche temporäre Dateien
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
            
        except Exception as e:
            status = "error"
            message = f"Fehler bei der initialen Synchronisation: {str(e)}"
            logger.error(message, exc_info=True)
        finally:
            self.sync_lock.release()
        
        duration = time.time() - start_time
        
        return {
            "status": status,
            "message": message,
            "duration": duration
        }
    
    def _get_data_in_batches(self, conn: sqlite3.Connection, table: str, batch_size: int):
        """
        Generator zum Abrufen von Daten in Batches.
        
        Args:
            conn: Datenbankverbindung
            table: Name der Tabelle
            batch_size: Größe eines Batches
            
        Yields:
            List[sqlite3.Row]: Ein Batch von Datensätzen
        """
        offset = 0
        while True:
            rows = conn.execute(
                f"SELECT * FROM {table} LIMIT ? OFFSET ?", 
                (batch_size, offset)
            ).fetchall()
            
            if not rows:
                break
                
            yield rows
            
            if len(rows) < batch_size:
                break
                
            offset += batch_size
    
    def verify_database_integrity(self) -> Dict[str, Any]:
        """
        Überprüft die Integrität beider Datenbanken.
        
        Returns:
            Dict[str, Any]: Ergebnis der Integritätsprüfung
        """
        import sqlite3
        import os
        
        result = {
            "status": "success",
            "master": {"status": "unknown", "message": ""},
            "slave": {"status": "unknown", "message": ""},
            "tables_count": 0,
            "rows_count": 0,
            "inconsistencies": 0,
            "details": {}
        }
        
        master_path = self.master_db.db_path
        slave_path = self.slave_db.db_path
        
        # Überprüfe, ob die Dateien existieren
        if not os.path.exists(master_path):
            result["master"]["status"] = "error"
            result["master"]["message"] = f"Datenbankdatei nicht gefunden: {master_path}"
            result["status"] = "error"
            return result
            
        if not os.path.exists(slave_path):
            result["slave"]["status"] = "error"
            result["slave"]["message"] = f"Datenbankdatei nicht gefunden: {slave_path}"
            result["status"] = "error"
            return result
        
        # Direkte Verbindung zu SQLite-Datenbanken
        try:
            master_conn = sqlite3.connect(master_path)
            master_conn.row_factory = sqlite3.Row
            
            # Überprüfe Master-Datenbank-Integrität
            integrity_result = master_conn.execute("PRAGMA integrity_check").fetchone()
            if integrity_result and integrity_result[0] == "ok":
                result["master"]["status"] = "ok"
                result["master"]["message"] = "ok"
            else:
                result["master"]["status"] = "error"
                result["master"]["message"] = "Integritätsprüfung fehlgeschlagen"
                
            # Hole alle Tabellen außer den System- und Sync-Tabellen
            tables = master_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_sync_%'"
            ).fetchall()
            
            tables = [table[0] for table in tables]
            result["tables_count"] = len(tables)
            
            # Slave-Verbindung
            slave_conn = sqlite3.connect(slave_path)
            slave_conn.row_factory = sqlite3.Row
            
            # Überprüfe Slave-Datenbank-Integrität
            integrity_result = slave_conn.execute("PRAGMA integrity_check").fetchone()
            if integrity_result and integrity_result[0] == "ok":
                result["slave"]["status"] = "ok"
                result["slave"]["message"] = "ok"
            else:
                result["slave"]["status"] = "error"
                result["slave"]["message"] = "Integritätsprüfung fehlgeschlagen"
            
            total_inconsistencies = 0
            total_rows = 0
            
            # Vergleiche Datensätze für jede Tabelle
            for table in tables:
                try:
                    master_count = master_conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
                    
                    # Prüfe ob die Tabelle im Slave existiert
                    table_exists = slave_conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                    ).fetchone()
                    
                    slave_count = 0
                    if table_exists:
                        slave_count = slave_conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
                    
                    # Berechne Unterschiede
                    diff = master_count - slave_count
                    total_inconsistencies += abs(diff)
                    total_rows += master_count
                    
                    # Speichere Details für diese Tabelle
                    result["details"][table] = {
                        "master_count": master_count,
                        "slave_count": slave_count,
                        "difference": diff
                    }
                except Exception as e:
                    # Fehler für diese spezifische Tabelle
                    result["details"][table] = {
                        "error": f"Fehler bei Tabelle {table}: {str(e)}",
                        "master_count": 0,
                        "slave_count": 0,
                        "difference": 0
                    }
            
            result["rows_count"] = total_rows
            result["inconsistencies"] = total_inconsistencies
            
            # Verbindungen schließen
            master_conn.close()
            slave_conn.close()
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Fehler bei der Integritätsprüfung: {str(e)}"
            
            # Versuche Verbindungen zu schließen, falls sie existieren
            try:
                if 'master_conn' in locals():
                    master_conn.close()
                if 'slave_conn' in locals():
                    slave_conn.close()
            except:
                pass
        
        return result 