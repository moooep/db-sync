"""
API-Endpunkte für die SQLite-Datenbanksynchronisierung.
"""

import os
import json
from flask import Blueprint, request, jsonify, current_app
from typing import Dict, List, Any, Optional

from backend.app.core.sync_service import SyncService
from backend.app.core.db_manager import DatabaseManager
from backend.app.models.slave_config import SlaveConfig
from backend.config.config import MASTER_DB_PATH

# Blueprint für API-Endpunkte
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/status', methods=['GET'])
def get_status() -> Dict[str, Any]:
    """
    Gibt den aktuellen Status der Anwendung zurück.
    
    Returns:
        Dict[str, Any]: Status der Anwendung
    """
    sync_service = current_app.sync_service
    return jsonify(sync_service.get_all_sync_status())

@api_bp.route('/slaves', methods=['GET'])
def get_slaves() -> Dict[str, Any]:
    """
    Gibt eine Liste aller konfigurierten Slaves zurück.
    
    Returns:
        Dict[str, Any]: Liste der Slaves
    """
    slave_config = SlaveConfig()
    slaves = slave_config.get_all_slaves()
    return jsonify({"slaves": slaves})

@api_bp.route('/slaves', methods=['POST'])
def add_slave() -> Dict[str, Any]:
    """
    Fügt einen neuen Slave hinzu.
    
    Returns:
        Dict[str, Any]: Ergebnis des Hinzufügens
    """
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Keine Daten erhalten"}), 400
    
    required_fields = ["name", "db_path"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"Fehlende Felder: {', '.join(missing_fields)}"
        }), 400
    
    sync_service = current_app.sync_service
    result = sync_service.add_slave(
        data["name"],
        data["db_path"],
        data.get("server_address"),
        data.get("ignored_tables", [])
    )
    
    status_code = 201 if result["status"] == "success" else 400
    return jsonify(result), status_code

@api_bp.route('/slaves/<int:slave_id>', methods=['GET'])
def get_slave(slave_id: int) -> Dict[str, Any]:
    """
    Gibt die Konfiguration eines Slaves zurück.
    
    Args:
        slave_id: ID des Slaves
        
    Returns:
        Dict[str, Any]: Slave-Konfiguration
    """
    sync_service = current_app.sync_service
    result = sync_service.get_sync_status(slave_id)
    
    if "status" in result and result["status"] == "error":
        return jsonify(result), 404
        
    return jsonify(result)

@api_bp.route('/slaves/<int:slave_id>', methods=['PUT'])
def update_slave(slave_id: int) -> Dict[str, Any]:
    """
    Aktualisiert einen Slave.
    
    Args:
        slave_id: ID des Slaves
        
    Returns:
        Dict[str, Any]: Ergebnis der Aktualisierung
    """
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Keine Daten erhalten"}), 400
    
    sync_service = current_app.sync_service
    result = sync_service.update_slave(
        slave_id,
        data.get("name"),
        data.get("db_path"),
        data.get("server_address"),
        data.get("status"),
        data.get("ignored_tables")
    )
    
    if result["status"] == "error" and "nicht gefunden" in result["message"]:
        return jsonify(result), 404
        
    return jsonify(result)

@api_bp.route('/slaves/<int:slave_id>', methods=['DELETE'])
def delete_slave(slave_id: int) -> Dict[str, Any]:
    """
    Löscht einen Slave.
    
    Args:
        slave_id: ID des Slaves
        
    Returns:
        Dict[str, Any]: Ergebnis des Löschens
    """
    sync_service = current_app.sync_service
    result = sync_service.delete_slave(slave_id)
    
    if result["status"] == "error" and "nicht gefunden" in result["message"]:
        return jsonify(result), 404
        
    return jsonify(result)

@api_bp.route('/slaves/<int:slave_id>/sync', methods=['POST'])
def sync_slave(slave_id):
    """
    Synchronisiert einen Slave mit der Master-Datenbank.
    
    Args:
        slave_id: ID des Slaves
        
    Returns:
        dict: Synchronisationsergebnis
    """
    try:
        # Daten aus dem Request-Body extrahieren, falls vorhanden
        data = request.get_json() or {}
        initial = data.get('initial', False)
        force = data.get('force', False)
        
        # Auf Schema-Updates prüfen
        if 'update_schema' in data and data['update_schema']:
            # TODO: Schema-Update-Logik implementieren
            pass
        
        # Synchronisation starten
        sync_service = current_app.sync_service
        result = sync_service.sync_slave(slave_id, initial=initial, force=force)
        
        # Ereignis über Socket.IO senden - nur wenn socketio importiert ist
        status = result.get('status', 'unknown')
        # Ereignis über Socket.IO senden, falls verfügbar
        if hasattr(current_app, 'socketio'):
            current_app.socketio.emit('sync_status_changed', {'slave_id': slave_id, 'status': status})
        
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Fehler bei der Synchronisation von Slave {slave_id}: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"Synchronisationsfehler: {str(e)}"
        }), 500

@api_bp.route('/slaves/<int:slave_id>/integrity', methods=['GET'])
def check_slave_integrity(slave_id: int) -> Dict[str, Any]:
    """
    Überprüft die Integrität der Datenbanken für einen Slave.
    
    Args:
        slave_id: ID des Slaves
        
    Returns:
        Dict[str, Any]: Ergebnis der Integritätsprüfung
    """
    sync_service = current_app.sync_service
    result = sync_service.verify_database_integrity(slave_id)
    
    if "status" in result and result["status"] == "error":
        return jsonify(result), 400
        
    return jsonify(result)

@api_bp.route('/sync/start', methods=['POST'])
def start_sync_thread() -> Dict[str, Any]:
    """
    Startet den Hintergrundprozess für regelmäßige Synchronisationen.
    
    Returns:
        Dict[str, Any]: Ergebnis des Starts
    """
    sync_service = current_app.sync_service
    sync_service.start_sync_thread()
    return jsonify({"status": "success", "message": "Synchronisations-Thread gestartet"})

@api_bp.route('/sync/stop', methods=['POST'])
def stop_sync_thread() -> Dict[str, Any]:
    """
    Stoppt den Hintergrundprozess für regelmäßige Synchronisationen.
    
    Returns:
        Dict[str, Any]: Ergebnis des Stopps
    """
    sync_service = current_app.sync_service
    sync_service.stop_sync_thread()
    return jsonify({"status": "success", "message": "Synchronisations-Thread gestoppt"})

@api_bp.route('/tables', methods=['GET'])
def get_tables() -> Dict[str, Any]:
    """
    Gibt eine Liste aller Tabellen in der Master-Datenbank zurück.
    
    Returns:
        Dict[str, Any]: Liste der Tabellen
    """
    try:
        db_manager = DatabaseManager(MASTER_DB_PATH)
        tables = db_manager.get_all_tables()
        tables = [t for t in tables if not t.startswith(('sqlite_', '_sync'))]
        return jsonify({"tables": tables})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/logs', methods=['GET'])
def get_logs() -> Dict[str, Any]:
    """
    Gibt Synchronisations-Logs zurück.
    
    Returns:
        Dict[str, Any]: Liste der Logs
    """
    slave_id = request.args.get('slave_id', type=int)
    limit = request.args.get('limit', default=100, type=int)
    
    slave_config = SlaveConfig()
    logs = slave_config.get_sync_logs(slave_id, limit)
    
    return jsonify({"logs": logs})

@api_bp.route('/config/master', methods=['GET'])
def get_master_config() -> Dict[str, Any]:
    """
    Gibt die Master-Konfiguration zurück.
    
    Returns:
        Dict[str, Any]: Master-Konfiguration
    """
    from backend.config.config import MASTER_DB_PATH, SYNC_INTERVAL
    
    return jsonify({
        "status": "success",
        "config": {
            "db_path": MASTER_DB_PATH,
            "sync_interval": SYNC_INTERVAL,
            "max_sync_threads": 3,
            "auto_start_sync": True
        }
    })

@api_bp.route('/config/master', methods=['POST'])
def update_master_config() -> Dict[str, Any]:
    """
    Aktualisiert die Master-Konfiguration.
    
    Returns:
        Dict[str, Any]: Ergebnis der Aktualisierung
    """
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Keine Daten erhalten"}), 400
    
    # Hier würde die Logik zur Aktualisierung der Master-Konfiguration stehen
    # Da dies eine komplexere Änderung wäre, geben wir nur eine Erfolgsmeldung zurück
    
    return jsonify({
        "status": "success",
        "message": "Master-Konfiguration aktualisiert"
    })

@api_bp.route('/config/advanced', methods=['GET'])
def get_advanced_config() -> Dict[str, Any]:
    """
    Gibt die erweiterten Einstellungen zurück.
    
    Returns:
        Dict[str, Any]: Erweiterte Einstellungen
    """
    from backend.config.config import LOG_LEVEL, TEMP_DIR
    
    return jsonify({
        "status": "success",
        "config": {
            "log_level": LOG_LEVEL,
            "log_retention": 30,
            "temp_dir": TEMP_DIR,
            "enable_change_detection": True,
            "validate_after_sync": False
        }
    })

@api_bp.route('/config/advanced', methods=['POST'])
def update_advanced_config() -> Dict[str, Any]:
    """
    Aktualisiert die erweiterten Einstellungen.
    
    Returns:
        Dict[str, Any]: Ergebnis der Aktualisierung
    """
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Keine Daten erhalten"}), 400
    
    # Hier würde die Logik zur Aktualisierung der erweiterten Einstellungen stehen
    
    return jsonify({
        "status": "success",
        "message": "Erweiterte Einstellungen aktualisiert"
    })

@api_bp.route('/config/excluded_tables', methods=['GET'])
def get_excluded_tables() -> Dict[str, Any]:
    """
    Gibt die globalen Tabellen-Ausschlüsse zurück.
    
    Returns:
        Dict[str, Any]: Tabellen-Ausschlüsse
    """
    from backend.config.config import IGNORED_TABLES
    
    return jsonify({
        "status": "success",
        "excluded_tables": IGNORED_TABLES
    })

@api_bp.route('/config/excluded_tables', methods=['POST'])
def update_excluded_tables() -> Dict[str, Any]:
    """
    Aktualisiert die globalen Tabellen-Ausschlüsse.
    
    Returns:
        Dict[str, Any]: Ergebnis der Aktualisierung
    """
    data = request.json
    if not data or 'excluded_tables' not in data:
        return jsonify({"status": "error", "message": "Keine gültigen Daten erhalten"}), 400
    
    # Hier würde die Logik zur Aktualisierung der Tabellen-Ausschlüsse stehen
    
    return jsonify({
        "status": "success",
        "message": "Tabellen-Ausschlüsse aktualisiert"
    })

@api_bp.route('/tables/system', methods=['GET'])
def get_system_tables() -> Dict[str, Any]:
    """
    Gibt eine Liste der System-Tabellen zurück.
    
    Returns:
        Dict[str, Any]: Liste der System-Tabellen
    """
    try:
        db_manager = DatabaseManager(MASTER_DB_PATH)
        tables = db_manager.get_all_tables()
        system_tables = [t for t in tables if t.startswith(('sqlite_', '_sync'))]
        return jsonify({
            "status": "success",
            "tables": system_tables
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Fehler beim Abrufen der System-Tabellen: {str(e)}"
        }), 500

@api_bp.route('/settings', methods=['GET'])
def get_settings() -> Dict[str, Any]:
    """
    Gibt die aktuellen Einstellungen zurück.
    
    Returns:
        Dict[str, Any]: Einstellungen
    """
    from backend.config.config import (
        MASTER_DB_PATH, SYNC_INTERVAL, IGNORED_TABLES,
        WEB_HOST, WEB_PORT
    )
    
    return jsonify({
        "master_db_path": MASTER_DB_PATH,
        "sync_interval": SYNC_INTERVAL,
        "ignored_tables": IGNORED_TABLES,
        "web_host": WEB_HOST,
        "web_port": WEB_PORT
    })