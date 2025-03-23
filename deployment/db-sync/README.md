# DB-Sync

DB-Sync ist eine Anwendung zur Synchronisation von SQLite-Datenbanken. Sie ermöglicht die Überwachung und Synchronisation von Änderungen zwischen einer Master-Datenbank und mehreren Slave-Datenbanken.

## Installation

### Voraussetzungen

- Linux-Server (Ubuntu/Debian oder CentOS/RHEL empfohlen)
- Python 3.8 oder höher
- sudo-Rechte für die Installation des Systemdienstes

### Automatische Installation

1. Entpacken Sie die Anwendung in ein Verzeichnis Ihrer Wahl:
   ```
   unzip db-sync.zip -d /opt/
   cd /opt/db-sync
   ```

2. Führen Sie das Installationsskript aus:
   ```
   ./install.sh
   ```

Das Skript führt folgende Schritte aus:
- Installation erforderlicher Abhängigkeiten
- Einrichtung einer Python-Umgebung
- Konfiguration der Anwendung
- Einrichtung und Start des Systemdienstes

### Manuelle Installation

Falls die automatische Installation nicht funktioniert, können Sie die folgenden Schritte manuell durchführen:

1. Python-Paketabhängigkeiten installieren:
   ```
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip python3-venv
   ```

2. Virtuelle Umgebung erstellen und aktivieren:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Abhängigkeiten installieren:
   ```
   pip install -r requirements.txt
   ```

4. Umgebungsvariablen in der .env-Datei anpassen (wichtig: MASTER_DB_PATH anpassen)

5. Anwendung starten:
   ```
   python run.py
   ```

## Konfiguration

Die Konfiguration erfolgt über die `.env`-Datei im Hauptverzeichnis. Wichtige Einstellungen:

- `MASTER_DB_PATH`: Pfad zur Master-Datenbank
- `WEB_PORT`: Port für die Weboberfläche (Standard: 5002)
- `SYNC_INTERVAL`: Synchronisationsintervall in Sekunden
- `LOG_LEVEL`: Protokollierungsstufe (DEBUG, INFO, WARNING, ERROR)

## Verwendung

Nach der Installation ist die Weboberfläche unter http://[Server-IP]:5002 erreichbar.

### Funktionen

- Dashboard zur Überwachung der Synchronisation
- Manuelle Synchronisation einzelner Slave-Datenbanken
- Integritätsprüfung zwischen Master- und Slave-Datenbanken
- Protokollierung aller Synchronisationsaktivitäten

### Systemdienst verwalten

```
# Status überprüfen
sudo systemctl status db-sync.service

# Dienst neustarten
sudo systemctl restart db-sync.service

# Dienst stoppen
sudo systemctl stop db-sync.service

# Logs anzeigen
sudo journalctl -u db-sync.service -f
```

## Fehlerbehebung

Sollten Probleme auftreten, überprüfen Sie bitte:

1. Die Logs des Systemdienstes:
   ```
   sudo journalctl -u db-sync.service -f
   ```

2. Anwendungslogs im Verzeichnis `logs/`

3. Verbindung zur Master-Datenbank und korrekte Pfadangabe in der `.env`-Datei

## Support

Bei Fragen oder Problemen wenden Sie sich bitte an den Support unter support@example.com. 