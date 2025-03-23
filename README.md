# DB-Sync

Eine Python-Anwendung zur Synchronisation von SQLite-Datenbanken zwischen Master und Slaves.

## Funktionen

- Master-Slave-Datenbankreplikation
- Echtzeit-Synchronisation
- Integrität prüfen
- Ausschließen von Tabellen aus der Synchronisation
- Webbasiertes Dashboard zur Überwachung und Steuerung

## Installation

1. Repository klonen:
   ```
   git clone https://github.com/yourusername/db-sync.git
   cd db-sync
   ```

2. Virtuelle Umgebung erstellen und Abhängigkeiten installieren:
   ```
   python -m venv venv
   source venv/bin/activate  # Unter Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Server starten:
   ```
   PYTHONPATH=. python backend/run.py
   ```

4. Im Browser öffnen:
   ```
   http://localhost:5002
   ```

## Konfiguration

### Slave-Datenbank hinzufügen

1. Klicken Sie auf "Slave hinzufügen"
2. Geben Sie einen Namen und den Pfad zur Slave-Datenbank ein
3. Wählen Sie optional zu ignorierende Tabellen aus
4. Klicken Sie auf "Speichern"

### Echtzeit-Synchronisation

1. Klicken Sie auf "Starten" im Abschnitt Echtzeit-Synchronisation
2. Die Änderungen werden automatisch von der Master-Datenbank zu den Slave-Datenbanken synchronisiert

## Entwicklung

### Projektstruktur

```
db-sync/
├── backend/          # Python-Backend
│   ├── app/          # Flask-Anwendung
│   └── run.py        # Startskript
├── data/             # Datenbank-Dateien
├── frontend/         # Frontend-Dateien
│   ├── static/       # Statische Ressourcen
│   └── templates/    # HTML-Templates
└── requirements.txt  # Python-Abhängigkeiten
```

## Lizenz

MIT 