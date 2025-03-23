/**
 * SQLite-Datenbanksynchronisierung Frontend
 * 
 * Konfigurationsskript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Socket.io-Verbindung initialisieren
    const socket = io();
    
    // Formulare abrufen
    const masterConfigForm = document.getElementById('masterConfigForm');
    const advancedConfigForm = document.getElementById('advancedConfigForm');
    const tableExclusionsForm = document.getElementById('tableExclusionsForm');
    
    // Buttons für Aktionen
    const loadSystemTablesBtn = document.getElementById('loadSystemTablesBtn');
    const optimizeDbBtn = document.getElementById('optimizeDbBtn');
    const checkIntegrityBtn = document.getElementById('checkIntegrityBtn');
    const resetLogDbBtn = document.getElementById('resetLogDbBtn');
    const forceFullSyncBtn = document.getElementById('forceFullSyncBtn');
    
    // Konfiguration laden
    function loadConfig() {
        // Master-Konfiguration abrufen
        fetch('/api/config/master')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const config = data.config;
                    document.getElementById('masterDbPath').value = config.db_path || '';
                    document.getElementById('syncInterval').value = config.sync_interval || 60;
                    document.getElementById('maxSyncThreads').value = config.max_sync_threads || 3;
                    document.getElementById('autoStartSync').checked = config.auto_start_sync !== false;
                } else {
                    showNotification(`Fehler beim Laden der Konfiguration: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Fehler beim Laden der Master-Konfiguration:', error);
                showNotification('Fehler beim Laden der Master-Konfiguration', 'danger');
            });
        
        // Erweiterte Einstellungen abrufen
        fetch('/api/config/advanced')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const config = data.config;
                    document.getElementById('logLevel').value = config.log_level || 'INFO';
                    document.getElementById('logRetention').value = config.log_retention || 30;
                    document.getElementById('tempDir').value = config.temp_dir || '';
                    document.getElementById('enableChangeDetection').checked = config.enable_change_detection !== false;
                    document.getElementById('validateAfterSync').checked = config.validate_after_sync === true;
                } else {
                    showNotification(`Fehler beim Laden der erweiterten Einstellungen: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Fehler beim Laden der erweiterten Einstellungen:', error);
                showNotification('Fehler beim Laden der erweiterten Einstellungen', 'danger');
            });
        
        // Globale Tabellen-Ausschlüsse abrufen
        fetch('/api/config/excluded_tables')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const excludedTables = data.excluded_tables || [];
                    document.getElementById('globalExcludedTables').value = excludedTables.join('\n');
                } else {
                    showNotification(`Fehler beim Laden der Tabellen-Ausschlüsse: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Fehler beim Laden der Tabellen-Ausschlüsse:', error);
                showNotification('Fehler beim Laden der Tabellen-Ausschlüsse', 'danger');
            });
    }
    
    // Master-Konfiguration speichern
    masterConfigForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const config = {
            db_path: document.getElementById('masterDbPath').value,
            sync_interval: parseInt(document.getElementById('syncInterval').value),
            max_sync_threads: parseInt(document.getElementById('maxSyncThreads').value),
            auto_start_sync: document.getElementById('autoStartSync').checked
        };
        
        saveMasterConfig(config);
    });
    
    // Erweiterte Einstellungen speichern
    advancedConfigForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const config = {
            log_level: document.getElementById('logLevel').value,
            log_retention: parseInt(document.getElementById('logRetention').value),
            temp_dir: document.getElementById('tempDir').value,
            enable_change_detection: document.getElementById('enableChangeDetection').checked,
            validate_after_sync: document.getElementById('validateAfterSync').checked
        };
        
        saveAdvancedConfig(config);
    });
    
    // Globale Tabellen-Ausschlüsse speichern
    tableExclusionsForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const excludedTablesText = document.getElementById('globalExcludedTables').value;
        const excludedTables = excludedTablesText
            .split('\n')
            .map(table => table.trim())
            .filter(table => table.length > 0);
        
        saveExcludedTables(excludedTables);
    });
    
    // Master-Konfiguration speichern
    function saveMasterConfig(config) {
        fetch('/api/config/master', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Master-Konfiguration erfolgreich gespeichert', 'success');
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler beim Speichern der Master-Konfiguration:', error);
            showNotification('Fehler beim Speichern der Master-Konfiguration', 'danger');
        });
    }
    
    // Erweiterte Einstellungen speichern
    function saveAdvancedConfig(config) {
        fetch('/api/config/advanced', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Erweiterte Einstellungen erfolgreich gespeichert', 'success');
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler beim Speichern der erweiterten Einstellungen:', error);
            showNotification('Fehler beim Speichern der erweiterten Einstellungen', 'danger');
        });
    }
    
    // Globale Tabellen-Ausschlüsse speichern
    function saveExcludedTables(excludedTables) {
        fetch('/api/config/excluded_tables', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ excluded_tables: excludedTables })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Tabellen-Ausschlüsse erfolgreich gespeichert', 'success');
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler beim Speichern der Tabellen-Ausschlüsse:', error);
            showNotification('Fehler beim Speichern der Tabellen-Ausschlüsse', 'danger');
        });
    }
    
    // System-Tabellen laden
    loadSystemTablesBtn.addEventListener('click', function() {
        const systemTablesContainer = document.getElementById('systemTablesContainer');
        const systemTablesElement = document.getElementById('systemTables');
        
        systemTablesElement.innerHTML = '<p>Wird geladen...</p>';
        systemTablesContainer.classList.remove('d-none');
        
        fetch('/api/tables/system')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.tables && data.tables.length > 0) {
                    let html = '';
                    data.tables.forEach(table => {
                        html += `
                            <div class="form-check">
                                <input class="form-check-input system-table-checkbox" type="checkbox" value="${table}" id="system-table-${table}">
                                <label class="form-check-label" for="system-table-${table}">
                                    ${table}
                                </label>
                            </div>
                        `;
                    });
                    systemTablesElement.innerHTML = html;
                    
                    // Event-Handler für Checkboxen
                    document.querySelectorAll('.system-table-checkbox').forEach(checkbox => {
                        checkbox.addEventListener('change', function() {
                            if (this.checked) {
                                addTableToExclusions(this.value);
                            } else {
                                removeTableFromExclusions(this.value);
                            }
                        });
                    });
                    
                    // Aktuell ausgewählte Tabellen markieren
                    const currentExclusions = document.getElementById('globalExcludedTables').value
                        .split('\n')
                        .map(table => table.trim())
                        .filter(table => table.length > 0);
                    
                    currentExclusions.forEach(table => {
                        const checkbox = document.getElementById(`system-table-${table}`);
                        if (checkbox) {
                            checkbox.checked = true;
                        }
                    });
                } else {
                    systemTablesElement.innerHTML = '<p>Keine System-Tabellen gefunden.</p>';
                }
            })
            .catch(error => {
                console.error('Fehler beim Laden der System-Tabellen:', error);
                systemTablesElement.innerHTML = '<p class="text-danger">Fehler beim Laden der System-Tabellen.</p>';
            });
    });
    
    // Tabelle zu Ausschlüssen hinzufügen
    function addTableToExclusions(table) {
        const excludedTablesElement = document.getElementById('globalExcludedTables');
        const currentExclusions = excludedTablesElement.value
            .split('\n')
            .map(t => t.trim())
            .filter(t => t.length > 0);
        
        if (!currentExclusions.includes(table)) {
            currentExclusions.push(table);
            excludedTablesElement.value = currentExclusions.join('\n');
        }
    }
    
    // Tabelle aus Ausschlüssen entfernen
    function removeTableFromExclusions(table) {
        const excludedTablesElement = document.getElementById('globalExcludedTables');
        const currentExclusions = excludedTablesElement.value
            .split('\n')
            .map(t => t.trim())
            .filter(t => t.length > 0 && t !== table);
        
        excludedTablesElement.value = currentExclusions.join('\n');
    }
    
    // Datenbanken optimieren
    optimizeDbBtn.addEventListener('click', function() {
        if (confirm('Möchten Sie wirklich alle Datenbanken optimieren? Dies kann einige Zeit dauern.')) {
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Optimiere...';
            
            fetch('/api/maintenance/optimize', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification('Datenbanken wurden erfolgreich optimiert', 'success');
                } else {
                    showNotification(`Fehler: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Fehler bei der Optimierung der Datenbanken:', error);
                showNotification('Fehler bei der Optimierung der Datenbanken', 'danger');
            })
            .finally(() => {
                this.disabled = false;
                this.innerHTML = '<i class="bi bi-speedometer"></i> Datenbanken optimieren';
            });
        }
    });
    
    // Integrität prüfen
    checkIntegrityBtn.addEventListener('click', function() {
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Prüfe...';
        
        fetch('/api/maintenance/check_integrity', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                if (data.all_ok) {
                    showNotification('Alle Datenbanken haben die Integritätsprüfung bestanden', 'success');
                } else {
                    const errorCount = data.errors ? data.errors.length : 0;
                    showNotification(`Integritätsprüfung abgeschlossen: ${errorCount} Fehler gefunden. Siehe Logs für Details.`, 'warning');
                }
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler bei der Integritätsprüfung:', error);
            showNotification('Fehler bei der Integritätsprüfung', 'danger');
        })
        .finally(() => {
            this.disabled = false;
            this.innerHTML = '<i class="bi bi-shield-check"></i> Integrität prüfen';
        });
    });
    
    // Log-Datenbank zurücksetzen
    resetLogDbBtn.addEventListener('click', function() {
        if (confirm('Möchten Sie wirklich alle Logs löschen? Diese Aktion kann nicht rückgängig gemacht werden!')) {
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Lösche...';
            
            fetch('/api/logs/reset', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification('Log-Datenbank wurde erfolgreich zurückgesetzt', 'success');
                } else {
                    showNotification(`Fehler: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Fehler beim Zurücksetzen der Log-Datenbank:', error);
                showNotification('Fehler beim Zurücksetzen der Log-Datenbank', 'danger');
            })
            .finally(() => {
                this.disabled = false;
                this.innerHTML = '<i class="bi bi-trash"></i> Log-Datenbank zurücksetzen';
            });
        }
    });
    
    // Vollständige Neusynchronisation erzwingen
    forceFullSyncBtn.addEventListener('click', function() {
        if (confirm('Möchten Sie wirklich eine vollständige Neusynchronisation aller Slaves erzwingen? Dies kann je nach Datenbankgröße einige Zeit dauern.')) {
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Synchronisiere...';
            
            fetch('/api/sync/force_full', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification('Vollständige Neusynchronisation wurde gestartet', 'success');
                } else {
                    showNotification(`Fehler: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Fehler beim Starten der vollständigen Neusynchronisation:', error);
                showNotification('Fehler beim Starten der vollständigen Neusynchronisation', 'danger');
            })
            .finally(() => {
                this.disabled = false;
                this.innerHTML = '<i class="bi bi-arrow-repeat"></i> Vollständige Neusynchronisation erzwingen';
            });
        }
    });
    
    // Notification anzeigen
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} notification-toast`;
        notification.innerHTML = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
    
    // Socket.io-Events
    socket.on('config_update', function(data) {
        loadConfig();
    });
    
    // Initialen Ladeprozess starten
    loadConfig();
}); 