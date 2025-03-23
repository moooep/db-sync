# DB-Sync

DB-Sync ist eine Anwendung zur Synchronisation von SQLite-Datenbanken zwischen einem Master und mehreren Slaves. Es bietet eine Web-Oberfläche zur Verwaltung der Synchronisation und ermöglicht die automatische und manuelle Synchronisation von Änderungen.

## Funktionen

- **Master-Slave-Synchronisation**: Automatische Synchronisation von Änderungen vom Master zu Slaves
- **Web-Interface**: Benutzerfreundliche Oberfläche zur Verwaltung der Synchronisation
- **Echtzeit-Überwachung**: Überwachung des Synchronisationsstatus und der Aktivitäten
- **Integritätsprüfung**: Überprüfung der Datenintegrität zwischen Master und Slaves
- **Konfigurierbare Synchronisationsintervalle**: Anpassbare Zeitintervalle für die automatische Synchronisation
- **Detaillierte Protokollierung**: Umfassende Protokollierung aller Synchronisationsaktivitäten

## Anforderungen

- Python 3.8 oder höher
- SQLite 3.x
- Flask
- Flask-SocketIO
- Python-dotenv

## Installation

### Entwicklungsumgebung

1. Repository klonen:
   ```
   git clone https://github.com/moooep/db-sync.git
   cd db-sync
   ```

2. Virtuelle Umgebung erstellen und aktivieren:
   ```
   python -m venv venv
   source venv/bin/activate  # Unter Windows: venv\Scripts\activate
   ```

3. Abhängigkeiten installieren:
   ```
   pip install -r requirements.txt
   ```

4. Umgebungsvariablen konfigurieren:
   - Kopiere `.env.example` zu `.env`
   - Passe die Variablen nach Bedarf an (insbesondere `MASTER_DB_PATH`)

5. Anwendung starten:
   ```
   python backend/run.py
   ```

### Produktionsumgebung

Für die Produktionsumgebung empfehlen wir die Verwendung des Installationsskripts:

1. Übertragen Sie das Installationspaket auf den Server
2. Führen Sie das Installationsskript aus:
   ```
   ./install.sh
   ```

Detaillierte Installationsanweisungen finden Sie in der [INSTALLATIONSANLEITUNG.txt](deployment/INSTALLATIONSANLEITUNG.txt).

## Verwendung

Nach dem Start ist die Anwendung unter `http://localhost:5002` (oder dem konfigurierten Port) verfügbar.

### Hauptfunktionen:

- **Dashboard**: Übersicht über alle Slave-Datenbanken und ihren Synchronisationsstatus
- **Slave-Details**: Detaillierte Informationen zu einzelnen Slave-Datenbanken
- **Manuelle Synchronisation**: Manuelles Auslösen der Synchronisation für einzelne Slaves
- **Integritätsprüfung**: Überprüfung der Datenintegrität zwischen Master und Slaves
- **Protokollansicht**: Einsicht in alle Synchronisationsaktivitäten

## Projektstruktur

```
db-sync/
├── backend/               # Backend-Code
│   ├── app/               # Hauptanwendungscode
│   │   ├── api/           # API-Endpunkte
│   │   ├── core/          # Kernfunktionalität
│   │   ├── models/        # Datenmodelle
│   │   └── utils/         # Hilfsfunktionen
│   └── config/            # Konfigurationen
├── frontend/              # Frontend-Code
│   ├── static/            # Statische Dateien (CSS, JS)
│   └── templates/         # HTML-Templates
├── data/                  # Datenbankdateien
├── deployment/            # Deployment-Skripte und -Konfigurationen
└── logs/                  # Protokolldateien
```

## Entwicklung

### Beitrag

1. Fork des Repositories
2. Feature-Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Änderungen committen (`git commit -m 'Add some AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request erstellen

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe die [LICENSE](LICENSE) Datei für Details. 