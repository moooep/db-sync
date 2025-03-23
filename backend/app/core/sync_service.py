"""
Synchronisationsdienst für SQLite-Datenbanken.
"""

import os
import time
import threading
import logging
import sqlite3
import subprocess
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.app.core.db_manager import DatabaseManager
from backend.app.core.sync_engine import SyncEngine
from backend.app.models.slave_config import SlaveConfig
from backend.app.utils.logger import log_to_db
from backend.config.config import MASTER_DB_PATH, SYNC_INTERVAL, TEMP_DIR

# Logger einrichten
logger = logging.getLogger(__name__)

class SyncService:
    """
    Dienst zur Verwaltung der Synchronisation von Slave-Datenbanken.
    Implementiert einen Hintergrundprozess für regelmäßige Synchronisationen.
    """
    
    def __init__(self, master_db_path: str = MASTER_DB_PATH, sync_interval: int = SYNC_INTERVAL):
        """
        Initialisiert den SyncService.
        
        Args:
            master_db_path: Pfad zur Master-Datenbank
            sync_interval: Intervall für die automatische Synchronisation in Sekunden
        """
        self.master_db_path = master_db_path
        self.sync_interval = sync_interval
        self.slave_config = SlaveConfig()
        self.sync_thread = None
        self.stop_event = threading.Event()
        self.sync_engines = {}  # Cache für SyncEngine-Instanzen
        
        # Überprüfe, ob die Master-Datenbank existiert
        if not os.path.exists(self.master_db_path):
            raise FileNotFoundError(f"Master-Datenbank nicht gefunden: {self.master_db_path}")
        
        # Erstelle das Temp-Verzeichnis, falls es nicht existiert
        os.makedirs(TEMP_DIR, exist_ok=True)
    
    def _get_sync_engine(self, slave_id: int) -> Optional[SyncEngine]:
        """
        Holt oder erstellt eine SyncEngine-Instanz für einen Slave.
        
        Args:
            slave_id: ID des Slaves
            
        Returns:
            Optional[SyncEngine]: SyncEngine-Instanz oder None, wenn der Slave nicht gefunden wird
        """
        # Prüfe Cache
        if slave_id in self.sync_engines:
            return self.sync_engines[slave_id]
        
        # Hole Slave-Konfiguration
        slave = self.slave_config.get_slave(slave_id)
        if not slave:
            logger.error(f"Slave mit ID {slave_id} nicht gefunden")
            return None
        
        # Prüfe, ob die Slave-Datenbank existiert
        if not os.path.exists(os.path.dirname(slave["db_path"])):
            os.makedirs(os.path.dirname(slave["db_path"]), exist_ok=True)
        
        # Erstelle SyncEngine
        try:
            engine = SyncEngine(
                master_db_path=self.master_db_path,
                slave_db_path=slave["db_path"],
                ignored_tables=slave["ignored_tables"]
            )
            self.sync_engines[slave_id] = engine
            return engine
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der SyncEngine für Slave {slave_id}: {e}")
            return None
    
    def _clear_sync_engine_cache(self, slave_id: Optional[int] = None) -> None:
        """
        Löscht den SyncEngine-Cache für einen oder alle Slaves.
        
        Args:
            slave_id: ID des Slaves (optional, None löscht alle)
        """
        if slave_id is not None:
            if slave_id in self.sync_engines:
                del self.sync_engines[slave_id]
        else:
            self.sync_engines.clear()
    
    def sync_slave(self, slave_id: int, initial: bool = False, force: bool = False) -> Dict[str, Any]:
        """
        Synchronisiert einen Slave.
        
        Args:
            slave_id: ID des Slaves
            initial: True für initiale Synchronisation, False für inkrementelle
            force: True für erzwungene vollständige Synchronisation, ignoriert Zeitstempel
            
        Returns:
            Dict[str, Any]: Ergebnis der Synchronisation
        """
        logger.info(f"Starte {'initiale' if initial else 'erzwungene' if force else 'inkrementelle'} Synchronisation für Slave {slave_id}")
        
        # Hole Slave-Konfiguration
        slave = self.slave_config.get_slave(slave_id)
        if not slave:
            error_msg = f"Slave mit ID {slave_id} nicht gefunden"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        # Aktualisiere Slave-Status auf 'syncing'
        self.slave_config.update_slave_sync_status(slave_id, "syncing")
        
        # Hole oder erstelle SyncEngine
        engine = self._get_sync_engine(slave_id)
        if not engine:
            error_msg = f"Konnte keine SyncEngine für Slave {slave_id} erstellen"
            logger.error(error_msg)
            self.slave_config.update_slave_sync_status(slave_id, "error")
            return {"status": "error", "message": error_msg}
        
        # Führe Synchronisation durch
        try:
            if initial:
                result = engine.initial_sync(TEMP_DIR)
            elif force:
                # Bei erzwungener Synchronisation kopiere alle Daten aus den Tabellen direkt
                result = self._force_full_sync(engine, slave["db_path"])
            else:
                result = engine.sync_databases()
            
            # Aktualisiere Slave-Status und Zeitstempel der letzten Synchronisation
            status = "active" if result["status"] == "success" else "error"
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Aktualisiere den Zeitstempel sowohl in der config.db als auch in der slave-DB
            logger.info(f"Aktualisiere last_sync für Slave {slave_id} auf {current_time}")
            
            # In der config.db aktualisieren
            self.slave_config.update_slave_sync_status(
                slave_id, 
                status,
                current_time
            )
            
            # In der slave-DB direkt aktualisieren
            # Unabhängig vom Synchronisationsergebnis zur Vermeidung von Zeitstempelproblemen
            try:
                # Direkter Zugriff auf die Slave-DB mit subprocess - sicherer Weg mit Escapings
                sqlite_cmd = f"""UPDATE _sync_config SET last_sync_timestamp = datetime('now', 'localtime') WHERE id = 1;
                                SELECT last_sync_timestamp FROM _sync_config WHERE id = 1;"""
                cmd = ["sqlite3", slave["db_path"]]
                
                logger.info(f"Führe SQLite-Befehl aus: {cmd} mit Befehl zur Aktualisierung des Zeitstempels")
                proc = subprocess.run(cmd, capture_output=True, text=True, input=sqlite_cmd)
                
                if proc.returncode == 0:
                    updated_timestamp = proc.stdout.strip()
                    logger.info(f"Zeitstempel in der slave-DB für Slave {slave_id} erfolgreich aktualisiert: {updated_timestamp}")
                    
                    # Falls Zeitstempel stark abweichen, synchronisiere sie
                    slave_time = datetime.strptime(updated_timestamp, '%Y-%m-%d %H:%M:%S')
                    config_time = datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')
                    
                    # Wenn die Zeitstempel mehr als 5 Minuten auseinanderliegen
                    if abs((slave_time - config_time).total_seconds()) > 300:
                        logger.warning(f"Zeitstempeldifferenz erkannt: slave={updated_timestamp}, config={current_time}")
                        # Aktualisiere config.db erneut mit dem Zeitstempel aus slave-DB
                        self.slave_config.update_slave_sync_status(slave_id, status, updated_timestamp)
                else:
                    logger.error(f"Fehler beim Aktualisieren des Zeitstempels: {proc.stderr}")
            except Exception as e:
                logger.error(f"Fehler beim Aktualisieren des Zeitstempels in der slave-DB: {e}", exc_info=True)
            
            # Erstelle Log-Eintrag
            self.slave_config.add_sync_log(
                slave_id,
                result["status"],
                result["message"],
                result.get("changes_count", 0),
                result.get("duration", 0)
            )
            
            # Stelle sicher, dass der Slave-Status zu "active" aktualisiert wird, wenn die Synchronisierung erfolgreich war
            if status == "active":
                # Noch einmal explizit den Status auf 'active' setzen, falls er zuvor nicht gesetzt wurde
                self.slave_config.update_slave_sync_status(slave_id, "active")
            
            return result
        except Exception as e:
            error_msg = f"Fehler bei der Synchronisation für Slave {slave_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Aktualisiere Slave-Status auf 'error'
            self.slave_config.update_slave_sync_status(slave_id, "error")
            
            # Erstelle Log-Eintrag
            self.slave_config.add_sync_log(
                slave_id,
                "error",
                error_msg
            )
            
            return {"status": "error", "message": error_msg}
    
    def _force_full_sync(self, engine: SyncEngine, slave_db_path: str) -> Dict[str, Any]:
        """
        Führt eine vollständige Synchronisation aller Tabellen durch, ignoriert Zeitstempel.
        
        Args:
            engine: SyncEngine-Instanz
            slave_db_path: Pfad zur Slave-Datenbank
            
        Returns:
            Dict[str, Any]: Synchronisationsergebnis
        """
        start_time = time.time()
        changes_count = 0
        
        try:
            # Überprüfe Schema-Kompatibilität
            if not engine.verify_schema_compatibility():
                return {"status": "error", "message": "Schema-Inkompatibilität zwischen Master und Slave"}
            
            # Hole alle Tabellen vom Master (außer System- und Sync-Tabellen)
            master_tables = engine.master_db.get_all_tables()
            master_tables = [t for t in master_tables if not t.startswith(('sqlite_', '_sync')) and t not in engine.ignored_tables]
            
            # Für jede Tabelle
            for table in master_tables:
                logger.info(f"Synchronisiere Tabelle {table} vollständig")
                
                try:
                    # Prüfe, ob die Tabelle im Slave existiert
                    with engine.slave_db.get_connection() as slave_conn:
                        table_exists = slave_conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                        ).fetchone()
                        
                        if not table_exists:
                            logger.warning(f"Tabelle {table} existiert nicht im Slave, überspringe.")
                            continue
                    
                    # Konfiguriere Verbindungen für die richtigen Rückgabetypen
                    with engine.master_db.get_connection() as master_conn:
                        # Stelle sicher, dass wir eine Dictionary-artige Rückgabe erhalten
                        master_conn.row_factory = sqlite3.Row
                        
                        # Hole alle IDs vom Master
                        master_ids = set()
                        try:
                            master_query = f"SELECT rowid FROM [{table}]"
                            for row in master_conn.execute(master_query).fetchall():
                                # Zugriff über Index und Name sollte jetzt funktionieren
                                master_ids.add(row[0])  # rowid ist immer an Position 0
                        except Exception as e:
                            logger.error(f"Fehler bei Master-Abfrage für Tabelle {table}: {str(e)}")
                            continue
                    
                    with engine.slave_db.get_connection() as slave_conn:
                        # Stelle sicher, dass wir eine Dictionary-artige Rückgabe erhalten
                        slave_conn.row_factory = sqlite3.Row
                        
                        # Hole alle IDs vom Slave
                        slave_ids = set()
                        try:
                            slave_query = f"SELECT rowid FROM [{table}]"
                            for row in slave_conn.execute(slave_query).fetchall():
                                # Zugriff über Index und Name sollte jetzt funktionieren
                                slave_ids.add(row[0])  # rowid ist immer an Position 0
                        except Exception as e:
                            logger.error(f"Fehler bei Slave-Abfrage für Tabelle {table}: {str(e)}")
                            continue
                    
                    # Fehlende IDs im Slave
                    missing_ids = master_ids - slave_ids
                    # Überflüssige IDs im Slave (in Master gelöscht)
                    extra_ids = slave_ids - master_ids
                    
                    logger.info(f"Tabelle {table}: {len(missing_ids)} fehlende Einträge, {len(extra_ids)} zu löschende Einträge")
                    
                    # Wenn Unterschiede gefunden wurden
                    if missing_ids or extra_ids:
                        # Lösche überflüssige Einträge im Slave
                        if extra_ids and len(extra_ids) > 0:
                            with engine.slave_db.get_connection() as slave_conn:
                                for batch in [list(extra_ids)[i:i+100] for i in range(0, len(extra_ids), 100)]:
                                    if len(batch) > 0:
                                        placeholders = ','.join(['?'] * len(batch))
                                        delete_query = f"DELETE FROM [{table}] WHERE rowid IN ({placeholders})"
                                        slave_conn.execute(delete_query, batch)
                        
                            changes_count += len(extra_ids)
                            logger.info(f"Tabelle {table}: {len(extra_ids)} überflüssige Datensätze gelöscht")
                        
                        # Kopiere fehlende Einträge vom Master zum Slave
                        if missing_ids and len(missing_ids) > 0:
                            with engine.master_db.get_connection() as master_conn:
                                master_conn.row_factory = sqlite3.Row
                                
                                for batch in [list(missing_ids)[i:i+100] for i in range(0, len(missing_ids), 100)]:
                                    if len(batch) > 0:
                                        placeholders = ','.join(['?'] * len(batch))
                                        select_query = f"SELECT * FROM [{table}] WHERE rowid IN ({placeholders})"
                                        rows = master_conn.execute(select_query, batch).fetchall()
                                        
                                        if rows and len(rows) > 0:
                                            # Extrahiere Spalten aus dem ersten Datensatz
                                            try:
                                                # Sichere Extraktion der Spaltennamen
                                                columns = []
                                                for key in rows[0].keys():
                                                    columns.append(key)
                                                
                                                insert_placeholders = ','.join(['?'] * len(columns))
                                                columns_str = ','.join([f"[{col}]" for col in columns])
                                                
                                                # Insert-Statement vorbereiten
                                                insert_sql = f"INSERT INTO [{table}] ({columns_str}) VALUES ({insert_placeholders})"
                                                
                                                # Daten vorbereiten und einfügen
                                                with engine.slave_db.get_connection() as slave_conn:
                                                    for row in rows:
                                                        values = []
                                                        for col in columns:
                                                            try:
                                                                values.append(row[col])
                                                            except (IndexError, KeyError) as e:
                                                                logger.warning(f"Spalte {col} nicht gefunden: {str(e)}")
                                                                values.append(None)
                                                        
                                                        slave_conn.execute(insert_sql, values)
                                                
                                                changes_count += len(rows)
                                                logger.info(f"Tabelle {table}: {len(rows)} fehlende Datensätze kopiert")
                                            except Exception as insert_e:
                                                logger.error(f"Fehler beim Einfügen von Daten in Tabelle {table}: {str(insert_e)}")
                                                continue
                
                    # Aktualisiere bestehende Einträge (die möglicherweise geändert wurden)
                    common_ids = master_ids.intersection(slave_ids)
                    if common_ids and len(common_ids) > 0:
                        # Stichprobenartig einige IDs überprüfen (maximal 20 pro Tabelle)
                        sample_size = min(20, len(common_ids))
                        sample_ids = random.sample(list(common_ids), sample_size)
                        
                        logger.info(f"Überprüfe Stichprobe von {sample_size} existierenden Einträgen in Tabelle {table}")
                        
                        for row_id in sample_ids:
                            # Hole Daten von Master und Slave
                            with engine.master_db.get_connection() as master_conn:
                                master_conn.row_factory = sqlite3.Row
                                master_row = master_conn.execute(f"SELECT * FROM [{table}] WHERE rowid = ?", (row_id,)).fetchone()
                            
                            with engine.slave_db.get_connection() as slave_conn:
                                slave_conn.row_factory = sqlite3.Row
                                slave_row = slave_conn.execute(f"SELECT * FROM [{table}] WHERE rowid = ?", (row_id,)).fetchone()
                            
                            # Vergleiche die Daten
                            if master_row and slave_row:
                                columns = [column for column in master_row.keys()]
                                is_different = False
                                
                                for col in columns:
                                    try:
                                        if master_row[col] != slave_row[col]:
                                            is_different = True
                                            break
                                    except (IndexError, KeyError) as e:
                                        logger.warning(f"Spalte {col} beim Vergleich nicht gefunden: {str(e)}")
                                        is_different = True
                                        break
                                
                                # Wenn Unterschiede gefunden wurden, aktualisiere
                                if is_different:
                                    set_clause = ','.join([f"[{col}] = ?" for col in columns])
                                    try:
                                        values = [master_row[col] for col in columns]
                                        
                                        with engine.slave_db.get_connection() as slave_conn:
                                            slave_conn.execute(f"UPDATE [{table}] SET {set_clause} WHERE rowid = ?", values + [row_id])
                                        
                                        changes_count += 1
                                        logger.info(f"Tabelle {table}: Eintrag mit ID {row_id} aktualisiert")
                                    except Exception as update_e:
                                        logger.error(f"Fehler beim Aktualisieren eines Eintrags in Tabelle {table}: {str(update_e)}")
                except Exception as table_e:
                    logger.error(f"Fehler bei der Synchronisation von Tabelle {table}: {str(table_e)}")
                    # Wir setzen die Synchronisation für andere Tabellen fort
                    continue
            
            # Aktualisiere den Synchronisationszeitstempel
            engine.update_last_sync_timestamp()
            
            # Rückgabe
            duration = time.time() - start_time
            if changes_count > 0:
                return {
                    "status": "success",
                    "message": f"Erzwungene Synchronisation erfolgreich: {changes_count} Änderungen",
                    "duration": duration,
                    "changes_count": changes_count
                }
            else:
                return {
                    "status": "success",
                    "message": "Keine Änderungen seit der letzten Synchronisation",
                    "duration": duration,
                    "changes_count": 0
                }
            
        except Exception as e:
            error_msg = f"Fehler bei der erzwungenen Synchronisation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "message": error_msg,
                "duration": time.time() - start_time,
                "changes_count": changes_count
            }
    
    def _sync_all_slaves(self) -> None:
        """Synchronisiert alle aktiven Slaves."""
        logger.info("Starte Synchronisation aller Slaves")
        
        # Hole alle aktiven Slaves
        slaves = self.slave_config.get_all_slaves()
        active_slaves = [s for s in slaves if s["status"] in ("active", "inactive")]
        
        for slave in active_slaves:
            try:
                # Überspringe Slaves mit Status 'syncing' oder 'error'
                if slave["status"] == "syncing":
                    logger.info(f"Slave {slave['id']} wird bereits synchronisiert, überspringe")
                    continue
                
                # Führe Synchronisation durch
                self.sync_slave(slave["id"])
                
                # Kurze Pause zwischen Synchronisationen
                time.sleep(1)
            except Exception as e:
                logger.error(f"Fehler bei der Synchronisation für Slave {slave['id']}: {e}", exc_info=True)
    
    def _sync_thread_func(self) -> None:
        """Hintergrundprozess für regelmäßige Synchronisationen."""
        logger.info(f"Starte Synchronisations-Thread mit Intervall {self.sync_interval} Sekunden")
        
        while not self.stop_event.is_set():
            try:
                self._sync_all_slaves()
            except Exception as e:
                logger.error(f"Fehler im Synchronisations-Thread: {e}", exc_info=True)
            
            # Warte auf das nächste Intervall oder bis der Thread gestoppt wird
            self.stop_event.wait(self.sync_interval)
    
    def start_sync_thread(self) -> None:
        """Startet den Hintergrundprozess für regelmäßige Synchronisationen."""
        if self.sync_thread and self.sync_thread.is_alive():
            logger.warning("Synchronisations-Thread läuft bereits")
            return
        
        self.stop_event.clear()
        self.sync_thread = threading.Thread(target=self._sync_thread_func, daemon=True)
        self.sync_thread.start()
        logger.info("Synchronisations-Thread gestartet")
    
    def stop_sync_thread(self) -> None:
        """Stoppt den Hintergrundprozess für regelmäßige Synchronisationen."""
        if not self.sync_thread or not self.sync_thread.is_alive():
            logger.warning("Synchronisations-Thread läuft nicht")
            return
        
        logger.info("Stoppe Synchronisations-Thread")
        self.stop_event.set()
        self.sync_thread.join(timeout=10)
        
        if self.sync_thread.is_alive():
            logger.warning("Synchronisations-Thread konnte nicht sauber beendet werden")
        else:
            logger.info("Synchronisations-Thread gestoppt")
            self.sync_thread = None
    
    def get_sync_status(self, slave_id: int) -> Dict[str, Any]:
        """
        Gibt den Synchronisationsstatus eines Slaves zurück.
        
        Args:
            slave_id: ID des Slaves
            
        Returns:
            Dict[str, Any]: Synchronisationsstatus
        """
        # Hole Slave-Konfiguration
        slave = self.slave_config.get_slave(slave_id)
        if not slave:
            return {"status": "error", "message": f"Slave mit ID {slave_id} nicht gefunden"}
        
        # Hole letzte Synchronisationslogs
        logs = self.slave_config.get_sync_logs(slave_id, 5)
        
        return {
            "slave": slave,
            "logs": logs,
            "thread_running": self.sync_thread is not None and self.sync_thread.is_alive()
        }
    
    def get_all_sync_status(self) -> Dict[str, Any]:
        """
        Gibt den Synchronisationsstatus aller Slaves zurück.
        
        Returns:
            Dict[str, Any]: Synchronisationsstatus aller Slaves
        """
        # Hole alle Slaves
        slaves = self.slave_config.get_all_slaves()
        
        # Hole die letzten 5 Logs für jeden Slave
        for slave in slaves:
            slave["logs"] = self.slave_config.get_sync_logs(slave["id"], 5)
        
        return {
            "slaves": slaves,
            "thread_running": self.sync_thread is not None and self.sync_thread.is_alive()
        }
    
    def add_slave(self, name: str, db_path: str, server_address: Optional[str] = None,
                 ignored_tables: List[str] = None) -> Dict[str, Any]:
        """
        Fügt einen neuen Slave hinzu.
        
        Args:
            name: Name des Slaves
            db_path: Pfad zur Slave-Datenbank
            server_address: Adresse des Slave-Servers (optional)
            ignored_tables: Liste von zu ignorierenden Tabellen (optional)
            
        Returns:
            Dict[str, Any]: Ergebnis des Hinzufügens
        """
        try:
            # Füge Slave hinzu
            slave_id = self.slave_config.add_slave(name, db_path, server_address)
            
            # Füge ignorierte Tabellen hinzu
            if ignored_tables:
                # Stelle sicher, dass keine leeren Strings in der Liste sind
                ignored_tables = [t for t in ignored_tables if t and t.strip()]
                for table in ignored_tables:
                    self.slave_config.add_ignored_table(slave_id, table)
            
            return {
                "status": "success",
                "message": f"Slave {name} erfolgreich hinzugefügt",
                "slave_id": slave_id
            }
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Slaves: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Fehler beim Hinzufügen des Slaves: {str(e)}"
            }
    
    def update_slave(self, slave_id: int, name: Optional[str] = None,
                    db_path: Optional[str] = None, server_address: Optional[str] = None,
                    status: Optional[str] = None, ignored_tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Aktualisiert einen Slave.
        
        Args:
            slave_id: ID des Slaves
            name: Neuer Name des Slaves (optional)
            db_path: Neuer Pfad zur Slave-Datenbank (optional)
            server_address: Neue Adresse des Slave-Servers (optional)
            status: Neuer Status des Slaves (optional)
            ignored_tables: Neue Liste von zu ignorierenden Tabellen (optional)
            
        Returns:
            Dict[str, Any]: Ergebnis der Aktualisierung
        """
        try:
            # Hole aktuelle Slave-Konfiguration
            slave = self.slave_config.get_slave(slave_id)
            if not slave:
                return {
                    "status": "error",
                    "message": f"Slave mit ID {slave_id} nicht gefunden"
                }
            
            # Aktualisiere Slave
            self.slave_config.update_slave(
                slave_id, name, db_path, server_address, status
            )
            
            # Aktualisiere ignorierte Tabellen, falls angegeben
            if ignored_tables is not None:
                # Stelle sicher, dass ignorierte Tabellen keine leeren Strings enthalten
                ignored_tables = [t for t in ignored_tables if t and t.strip()]
                
                # Stelle sicher, dass slave["ignored_tables"] eine Liste ist
                current_ignored_tables = slave.get("ignored_tables", []) or []
                
                # Lösche alte ignorierte Tabellen
                for table in current_ignored_tables:
                    self.slave_config.remove_ignored_table(slave_id, table)
                
                # Füge neue ignorierte Tabellen hinzu
                for table in ignored_tables:
                    self.slave_config.add_ignored_table(slave_id, table)
            
            # Lösche SyncEngine-Cache für diesen Slave
            self._clear_sync_engine_cache(slave_id)
            
            return {
                "status": "success",
                "message": f"Slave mit ID {slave_id} erfolgreich aktualisiert"
            }
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Slaves: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Fehler beim Aktualisieren des Slaves: {str(e)}"
            }
    
    def delete_slave(self, slave_id: int) -> Dict[str, Any]:
        """
        Löscht einen Slave.
        
        Args:
            slave_id: ID des Slaves
            
        Returns:
            Dict[str, Any]: Ergebnis des Löschens
        """
        try:
            # Hole aktuelle Slave-Konfiguration
            slave = self.slave_config.get_slave(slave_id)
            if not slave:
                return {
                    "status": "error",
                    "message": f"Slave mit ID {slave_id} nicht gefunden"
                }
            
            # Lösche Slave
            self.slave_config.delete_slave(slave_id)
            
            # Lösche SyncEngine-Cache für diesen Slave
            self._clear_sync_engine_cache(slave_id)
            
            return {
                "status": "success",
                "message": f"Slave mit ID {slave_id} erfolgreich gelöscht"
            }
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Slaves: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Fehler beim Löschen des Slaves: {str(e)}"
            }
    
    def verify_database_integrity(self, slave_id: int) -> Dict[str, Any]:
        """
        Überprüft die Integrität der Datenbanken für einen Slave.
        
        Args:
            slave_id: ID des Slaves
            
        Returns:
            Dict[str, Any]: Ergebnis der Integritätsprüfung
        """
        # Hole SyncEngine
        engine = self._get_sync_engine(slave_id)
        if not engine:
            return {
                "status": "error",
                "message": f"Konnte keine SyncEngine für Slave {slave_id} erstellen"
            }
        
        try:
            return engine.verify_database_integrity()
        except Exception as e:
            logger.error(f"Fehler bei der Integritätsprüfung für Slave {slave_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Fehler bei der Integritätsprüfung: {str(e)}"
            } 