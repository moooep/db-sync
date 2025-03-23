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

def run_app():
    """Führt die Anwendung aus."""
    # Überprüfe, ob Eventlet bereits geladen ist, anstatt es erneut zu patchen
    eventlet_available = False
    try:
        import eventlet
        eventlet_available = True
        logger.info("Eventlet wurde geladen und ist verfügbar")
        # Prüfe auf socket-monkey_patch
        if hasattr(eventlet, 'monkey_patch') and hasattr(eventlet, 'is_monkey_patched'):
            logger.info(f"Socket monkey-patched: {eventlet.is_monkey_patched('socket')}")
            logger.info(f"Thread monkey-patched: {eventlet.is_monkey_patched('thread')}")
        else:
            logger.warning("Eventlet ist geladen, aber monkey_patch-Funktionen konnten nicht verifiziert werden")
    except ImportError:
        logger.warning("Eventlet nicht installiert oder nicht verfügbar")

    app = create_app()
    
    # Starte den Sync-Thread, wenn ein sync_service existiert
    if hasattr(app, 'sync_service') and app.sync_service is not None:
        try:
            app.sync_service.start_sync_thread()
            app.sync_service.start_realtime_sync()
            logger.info("Synchronisations-Threads und Echtzeit-Synchronisation aktiviert")
        except Exception as e:
            logger.error(f"Fehler beim Starten der Synchronisations-Threads: {e}", exc_info=True)
    else:
        logger.warning("SyncService nicht verfügbar, Synchronisations-Threads werden nicht gestartet")
        
    # Starte den Server
    host = os.environ.get('FLASK_HOST', WEB_HOST)
    port = int(os.environ.get('FLASK_PORT', WEB_PORT))
    debug = os.environ.get('FLASK_DEBUG', str(DEBUG)).lower() == 'true'
    
    logger.info(f"Starte Server auf {host}:{port} (Debug: {debug})")
    
    if eventlet_available:
        try:
            # Explizit Socket erstellen
            sock = None
            try:
                import socket
                # Diese Optionen können helfen, das "Address already in use"-Problem zu vermeiden
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # Versuche zuerst den regulären Socket zu verwenden
                sock.bind((host, port))
                sock.listen(128)  # Backlog für verbindende Clients
                logger.info(f"Socket erfolgreich konfiguriert und gebunden an {host}:{port}")
            except (socket.error, AttributeError) as socket_err:
                logger.error(f"Socket-Fehler: {socket_err}")
                sock = None
                
            if sock:
                # Verwende den explizit erstellten Socket
                logger.info(f"WSGI-Server-Start mit explizitem Socket")
                # Prüfe, ob die debug-Option unterstützt wird
                try:
                    eventlet.wsgi.server(sock, app, log_output=True, debug=debug)
                except TypeError:
                    # Ältere Versionen unterstützen debug nicht
                    logger.info("Fallback auf Eventlet wsgi.server ohne debug-Option")
                    eventlet.wsgi.server(sock, app, log_output=True)
            else:
                # Fallback auf Eventlet-eigene Socket-Erstellung
                logger.warning("Fallback auf Eventlet listen()")
                try:
                    sock = eventlet.listen((host, port))
                    eventlet.wsgi.server(sock, app, log_output=True)
                except (TypeError, AttributeError) as e:
                    logger.error(f"Fehler beim Eventlet listen: {e}")
                    # Letzter Versuch mit Standard-API
                    logger.info("Letzter Versuch mit Standard-Eventlet-API")
                    if hasattr(eventlet, 'serve'):
                        eventlet.serve(eventlet.listen((host, port)), app)
                    else:
                        # Wirklich letzte Möglichkeit
                        logger.warning("Eventlet API scheint sehr alt zu sein, versuche direkte Socket-Übergabe")
                        from eventlet import wsgi
                        wsgi.server(sock, app)
        except Exception as e:
            logger.error(f"Fehler beim Starten des Eventlet-Servers: {e}", exc_info=True)
            # Fallback auf Flask im Fehlerfall
            logger.info(f"Fallback auf Flask-Server auf {host}:{port}")
            try:
                app.run(host=host, port=port, debug=debug, use_reloader=False)
            except Exception as run_err:
                logger.error(f"Fehler beim Starten des Flask-Servers: {run_err}", exc_info=True)
    else:
        logger.info(f"Starte Server mit Flask auf {host}:{port} (Debug: {debug})")
        app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == '__main__':
    run_app() 