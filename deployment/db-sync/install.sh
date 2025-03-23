#!/bin/bash

# DB-Sync Installation Skript
echo "=== DB-Sync Installation ==="
echo "Dieses Skript installiert die DB-Sync Anwendung auf Ihrem Server."

# Verzeichnis prüfen
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
  echo "Fehler: Verzeichnisstruktur ist ungültig. Bitte stellen Sie sicher, dass Sie das Skript im Hauptverzeichnis von db-sync ausführen."
  exit 1
fi

# Python prüfen
if ! command -v python3 &> /dev/null; then
  echo "Python3 ist nicht installiert. Installation wird gestartet..."
  if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
  elif command -v yum &> /dev/null; then
    sudo yum install -y python3 python3-pip
  else
    echo "Fehler: Ihr Betriebssystem wird nicht erkannt. Bitte installieren Sie Python 3.8+ manuell."
    exit 1
  fi
else
  echo "Python3 ist bereits installiert."
fi

# Virtuelle Umgebung erstellen
echo "Erstelle virtuelle Python-Umgebung..."
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
echo "Installiere Abhängigkeiten..."
pip install --upgrade pip
pip install -r requirements.txt

# .env-Datei anpassen
echo "Konfiguriere .env-Datei..."
# Absoluten Pfad zum aktuellen Verzeichnis ermitteln
CURRENT_DIR=$(pwd)
# Pfad zur Master-DB in .env ändern
sed -i "s|MASTER_DB_PATH=.*|MASTER_DB_PATH=$CURRENT_DIR/data/master.db|g" .env

# Systemd Service erstellen
echo "Erstelle Systemd-Service..."
cat > db-sync.service << EOF
[Unit]
Description=DB-Sync Service
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
ExecStart=$CURRENT_DIR/venv/bin/python backend/run.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "Installiere Systemd-Service..."
sudo mv db-sync.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable db-sync.service

echo "Starte DB-Sync Service..."
sudo systemctl start db-sync.service

echo "=== Installation abgeschlossen ==="
echo "DB-Sync wurde installiert und gestartet."
echo "Die Weboberfläche ist nun verfügbar unter: http://$(hostname -I | awk '{print $1}'):5002"
echo "Um den Service zu verwalten, verwenden Sie:"
echo "  sudo systemctl status db-sync.service"
echo "  sudo systemctl restart db-sync.service"
echo "  sudo systemctl stop db-sync.service"
echo "Die Logs können Sie mit dem folgenden Befehl einsehen:"
echo "  sudo journalctl -u db-sync.service -f" 