"""
Hauptanwendung für die SQLite-Datenbanksynchronisierung.
"""

import os
import logging
from flask import Flask, render_template, send_from_directory, redirect, url_for
from flask_socketio import SocketIO

from backend.app.api.routes import api_bp
from backend.app.core.sync_service import SyncService
from backend.app.utils.logger import setup_logger
from backend.config.config import WEB_HOST, WEB_PORT, DEBUG, MASTER_DB_PATH

# Logger einrichten
logger = setup_logger('app')

def create_app(test_config=None):
    """
    Erstellt und konfiguriert die Flask-Anwendung.
    
    Args:
        test_config: Testkonfiguration (optional)
        
    Returns:
        Flask: Die Flask-Anwendung
    """
    # Erstelle und konfiguriere die App
    app = Flask(
        __name__,
        static_folder='../../frontend/static',
        template_folder='../../frontend/templates'
    )
    
    # Konfiguration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key'),
        DEBUG=DEBUG
    )
    
    if test_config is None:
        # Lade die Instanzkonfiguration, falls sie existiert
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Lade die Testkonfiguration, falls sie übergeben wurde
        app.config.from_mapping(test_config)
    
    # Initialisiere SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    app.socketio = socketio
    
    # Initialisiere SyncService
    try:
        if MASTER_DB_PATH:
            logger.info(f"Initialisiere SyncService mit Master-DB: {MASTER_DB_PATH}")
            sync_service = SyncService(MASTER_DB_PATH)
            app.sync_service = sync_service
            logger.info("SyncService erfolgreich initialisiert")
        else:
            logger.warning("MASTER_DB_PATH nicht konfiguriert, SyncService wird nicht initialisiert")
            # Erstelle einen Dummy-SyncService, um Fehler zu vermeiden
            app.sync_service = None
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung des SyncService: {e}", exc_info=True)
        # Erstelle einen Dummy-SyncService, um Fehler zu vermeiden
        app.sync_service = None
    
    # Registriere Blueprints
    app.register_blueprint(api_bp)
    
    # Route für die Startseite
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # Route für Slave-Details
    @app.route('/slaves/<int:slave_id>')
    def slave_detail(slave_id):
        return render_template('slave_detail.html', slave_id=slave_id)
    
    # Route für Konfigurationsseite
    @app.route('/config')
    def config():
        return render_template('config.html')
    
    # Route für Logs
    @app.route('/logs')
    def logs():
        return render_template('logs.html')
    
    # Route für Favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, '../../frontend/static'),
            'favicon.ico', mimetype='image/vnd.microsoft.icon'
        )
    
    # Fehlerbehandlung
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500
    
    return app

def run_app(config_path=None, host=WEB_HOST, port=WEB_PORT, debug=DEBUG):
    """Flask-Anwendung ausführen."""
    app = create_app(config_path)
    
    # Starte Synchronisations-Thread, wenn vorhanden
    if hasattr(app, 'sync_service') and app.sync_service is not None:
        try:
            app.sync_service.start_sync_thread()
            app.sync_service.start_realtime_sync()
            logger.info("Echtzeit-Synchronisation aktiviert")
        except Exception as e:
            logger.error(f"Fehler beim Starten der Synchronisations-Threads: {e}", exc_info=True)
    else:
        logger.warning("SyncService nicht verfügbar, Synchronisations-Threads werden nicht gestartet")
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_app() 