/**
 * SQLite-Datenbanksynchronisierung Frontend
 * 
 * Hauptskript für die Weboberfläche
 */

document.addEventListener('DOMContentLoaded', function() {
    // Socket.io-Verbindung initialisieren
    const socket = io();
    
    // Elemente cachen
    const slavesList = document.getElementById('slavesList');
    const syncStatusText = document.getElementById('syncStatusText');
    const syncStatus = document.getElementById('syncStatus');
    const refreshBtn = document.getElementById('refreshBtn');
    const syncAllBtn = document.getElementById('syncAllBtn');
    const saveSlaveBtn = document.getElementById('saveSlaveBtn');
    const loadTablesBtn = document.getElementById('loadTablesBtn');
    
    // Status-Farben
    const statusColors = {
        'active': 'success',
        'inactive': 'secondary',
        'syncing': 'primary',
        'error': 'danger'
    };
    
    // Status-Texte
    const statusTexts = {
        'active': 'Aktiv',
        'inactive': 'Inaktiv',
        'syncing': 'Synchronisierung läuft',
        'error': 'Fehler'
    };
    
    // Daten laden
    function loadDashboard() {
        fetchSyncStatus();
        fetchSlaves();
    }
    
    // Status abrufen
    function fetchSyncStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                updateSyncStatus(data);
            })
            .catch(error => {
                console.error('Fehler beim Abrufen des Status:', error);
                syncStatusText.innerText = 'Fehler beim Laden des Status.';
                syncStatus.className = 'alert alert-danger';
            });
    }
    
    // Slave-Liste abrufen
    function fetchSlaves() {
        fetch('/api/slaves')
            .then(response => response.json())
            .then(data => {
                updateSlavesList(data.slaves);
            })
            .catch(error => {
                console.error('Fehler beim Abrufen der Slaves:', error);
                slavesList.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center">
                            Fehler beim Laden der Slave-Datenbanken. Bitte versuchen Sie es später erneut.
                        </td>
                    </tr>
                `;
            });
    }
    
    // Status aktualisieren
    function updateSyncStatus(data) {
        if (data.thread_running) {
            syncStatusText.innerText = 'Synchronisationsdienst läuft.';
            syncStatus.className = 'alert alert-success';
        } else {
            syncStatusText.innerText = 'Synchronisationsdienst ist gestoppt.';
            syncStatus.className = 'alert alert-warning';
        }
    }
    
    // Slave-Liste aktualisieren
    function updateSlavesList(slaves) {
        if (!slaves || slaves.length === 0) {
            slavesList.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">
                        Keine Slave-Datenbanken konfiguriert. Fügen Sie einen Slave hinzu, um zu beginnen.
                    </td>
                </tr>
            `;
            return;
        }
        
        let html = '';
        slaves.forEach(slave => {
            const statusClass = statusColors[slave.status] || 'secondary';
            const statusText = statusTexts[slave.status] || 'Unbekannt';
            const lastSync = slave.last_sync ? new Date(slave.last_sync).toLocaleString() : 'Nie';
            
            html += `
                <tr>
                    <td>${slave.name}</td>
                    <td><span class="text-truncate d-inline-block" style="max-width: 200px;" title="${slave.db_path}">${slave.db_path}</span></td>
                    <td>${slave.server_address || 'Lokal'}</td>
                    <td><span class="badge bg-${statusClass}">${statusText}</span></td>
                    <td>${lastSync}</td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-primary sync-slave" data-id="${slave.id}">
                                <i class="bi bi-arrow-repeat"></i>
                            </button>
                            <a href="/slaves/${slave.id}" class="btn btn-info">
                                <i class="bi bi-info-circle"></i>
                            </a>
                            <button class="btn btn-danger delete-slave" data-id="${slave.id}" data-name="${slave.name}">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        slavesList.innerHTML = html;
        
        // Event-Listener für Slave-Aktionen hinzufügen
        document.querySelectorAll('.sync-slave').forEach(button => {
            button.addEventListener('click', function() {
                const slaveId = this.getAttribute('data-id');
                syncSlave(slaveId);
            });
        });
        
        document.querySelectorAll('.delete-slave').forEach(button => {
            button.addEventListener('click', function() {
                const slaveId = this.getAttribute('data-id');
                const slaveName = this.getAttribute('data-name');
                confirmDeleteSlave(slaveId, slaveName);
            });
        });
    }
    
    // Slave synchronisieren
    function syncSlave(slaveId) {
        const button = document.querySelector(`.sync-slave[data-id="${slaveId}"]`);
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        }
        
        fetch(`/api/slaves/${slaveId}/sync`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ initial: false })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Synchronisation gestartet', 'success');
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
            
            // Aktualisiere nach kurzer Verzögerung
            setTimeout(() => {
                loadDashboard();
            }, 1000);
        })
        .catch(error => {
            console.error('Fehler bei der Synchronisation:', error);
            showNotification('Fehler bei der Synchronisation', 'danger');
            loadDashboard();
        });
    }
    
    // Slave löschen bestätigen
    function confirmDeleteSlave(slaveId, slaveName) {
        if (confirm(`Möchten Sie den Slave "${slaveName}" wirklich löschen?`)) {
            deleteSlave(slaveId);
        }
    }
    
    // Slave löschen
    function deleteSlave(slaveId) {
        fetch(`/api/slaves/${slaveId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Slave erfolgreich gelöscht', 'success');
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
            loadDashboard();
        })
        .catch(error => {
            console.error('Fehler beim Löschen des Slaves:', error);
            showNotification('Fehler beim Löschen des Slaves', 'danger');
        });
    }
    
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
    
    // Tabellen laden
    function loadAvailableTables() {
        console.log('Debug: loadAvailableTables in main.js wird ausgeführt');
        const tablesContainer = document.getElementById('availableTablesContainer');
        const tablesList = document.getElementById('availableTables');
        
        if (!tablesContainer || !tablesList) {
            console.error('Debug: Container-Elemente für Tabellen nicht gefunden!');
            return;
        }
        
        loadTablesBtn.disabled = true;
        loadTablesBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Lade...';
        
        fetch('/api/tables')
            .then(response => {
                console.log('Debug: API Response Status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Debug: Erhaltene Tabellendaten:', data);
                
                if (data.tables && Array.isArray(data.tables) && data.tables.length > 0) {
                    let html = '';
                    data.tables.forEach(table => {
                        html += `
                            <div class="form-check">
                                <input class="form-check-input table-checkbox" type="checkbox" value="${table}" id="table-${table}">
                                <label class="form-check-label" for="table-${table}">
                                    ${table}
                                </label>
                            </div>
                        `;
                    });
                    tablesList.innerHTML = html;
                    tablesContainer.classList.remove('d-none');
                    
                    // Event-Listener für Checkboxen
                    document.querySelectorAll('.table-checkbox').forEach(checkbox => {
                        checkbox.addEventListener('change', updateIgnoredTablesInput);
                    });
                    
                    console.log('Debug: Tabellen erfolgreich angezeigt, Anzahl:', data.tables.length);
                } else if (data.status === 'error') {
                    console.error('Debug: API-Fehler beim Laden der Tabellen:', data.message);
                    tablesList.innerHTML = `<p class="text-danger">Fehler: ${data.message || 'Unbekannter Fehler beim Laden der Tabellen.'}</p>`;
                    tablesContainer.classList.remove('d-none');
                } else {
                    console.log('Debug: Keine Tabellen in der Antwort gefunden');
                    tablesList.innerHTML = '<p>Keine Tabellen gefunden.</p>';
                    tablesContainer.classList.remove('d-none');
                }
            })
            .catch(error => {
                console.error('Debug: Fetch-Fehler beim Laden der Tabellen:', error);
                tablesList.innerHTML = `<p class="text-danger">Fehler beim Laden der Tabellen: ${error.message}</p>`;
                tablesContainer.classList.remove('d-none');
            })
            .finally(() => {
                loadTablesBtn.disabled = false;
                loadTablesBtn.innerHTML = 'Verfügbare Tabellen laden';
            });
    }
    
    // Ignorierte Tabellen aktualisieren
    function updateIgnoredTablesInput() {
        const ignoredTablesInput = document.getElementById('ignoredTables');
        const checkedTables = Array.from(document.querySelectorAll('.table-checkbox:checked'))
            .map(checkbox => checkbox.value);
        
        ignoredTablesInput.value = checkedTables.join(',');
    }
    
    // Neuen Slave speichern
    function saveNewSlave() {
        const nameInput = document.getElementById('slaveName');
        const dbPathInput = document.getElementById('dbPath');
        const serverAddressInput = document.getElementById('serverAddress');
        const ignoredTablesInput = document.getElementById('ignoredTables');
        
        if (!nameInput.value || !dbPathInput.value) {
            showNotification('Bitte füllen Sie alle Pflichtfelder aus', 'warning');
            return;
        }
        
        const slaveData = {
            name: nameInput.value,
            db_path: dbPathInput.value,
            server_address: serverAddressInput.value,
            ignored_tables: ignoredTablesInput.value ? ignoredTablesInput.value.split(',') : []
        };
        
        saveSlaveBtn.disabled = true;
        saveSlaveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Speichere...';
        
        fetch('/api/slaves', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(slaveData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Slave erfolgreich hinzugefügt', 'success');
                
                // Modal schließen und Formular zurücksetzen
                const modal = bootstrap.Modal.getInstance(document.getElementById('addSlaveModal'));
                modal.hide();
                
                document.getElementById('addSlaveForm').reset();
                document.getElementById('availableTables').innerHTML = '';
                document.getElementById('availableTablesContainer').classList.add('d-none');
                
                // Dashboard aktualisieren
                loadDashboard();
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler beim Hinzufügen des Slaves:', error);
            showNotification('Fehler beim Hinzufügen des Slaves', 'danger');
        })
        .finally(() => {
            saveSlaveBtn.disabled = false;
            saveSlaveBtn.innerHTML = 'Speichern';
        });
    }
    
    // Event-Listener hinzufügen
    refreshBtn.addEventListener('click', loadDashboard);
    
    syncAllBtn.addEventListener('click', function() {
        fetch('/api/sync/start', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Synchronisation aller Slaves gestartet', 'success');
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
            setTimeout(loadDashboard, 1000);
        })
        .catch(error => {
            console.error('Fehler beim Starten der Synchronisation:', error);
            showNotification('Fehler beim Starten der Synchronisation', 'danger');
        });
    });
    
    loadTablesBtn.addEventListener('click', loadAvailableTables);
    
    saveSlaveBtn.addEventListener('click', saveNewSlave);
    
    // Socket.io-Events
    socket.on('sync_update', function(data) {
        loadDashboard();
    });
    
    // Initialen Ladeprozess starten
    loadDashboard();

    // Funktionen für die Echtzeit-Synchronisation
    function getRealtimeSyncStatus() {
        fetch('/api/realtime-sync/status')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const statusElement = document.getElementById('realtime-sync-status');
                    const queueElement = document.getElementById('realtime-sync-queue');
                    
                    if (statusElement) {
                        statusElement.innerHTML = data.realtime_sync_active ? 
                            '<span class="badge bg-success">Aktiv</span>' : 
                            '<span class="badge bg-danger">Inaktiv</span>';
                    }
                    
                    if (queueElement) {
                        queueElement.textContent = data.queue_size;
                    }
                    
                    // Aktualisiere die Schaltflächen
                    toggleRealtimeSyncButtons(data.realtime_sync_active);
                }
            })
            .catch(error => console.error('Fehler beim Abrufen des Echtzeit-Synchronisationsstatus:', error));
    }

    function startRealtimeSync() {
        fetch('/api/realtime-sync/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Echtzeit-Synchronisation gestartet', 'success');
                getRealtimeSyncStatus();
            } else {
                showNotification('Fehler: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler beim Starten der Echtzeit-Synchronisation:', error);
            showNotification('Fehler beim Starten der Echtzeit-Synchronisation', 'danger');
        });
    }

    function stopRealtimeSync() {
        fetch('/api/realtime-sync/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Echtzeit-Synchronisation gestoppt', 'success');
                getRealtimeSyncStatus();
            } else {
                showNotification('Fehler: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler beim Stoppen der Echtzeit-Synchronisation:', error);
            showNotification('Fehler beim Stoppen der Echtzeit-Synchronisation', 'danger');
        });
    }

    function toggleRealtimeSyncButtons(isActive) {
        const startButton = document.getElementById('start-realtime-sync');
        const stopButton = document.getElementById('stop-realtime-sync');
        
        if (startButton && stopButton) {
            startButton.disabled = isActive;
            stopButton.disabled = !isActive;
        }
    }

    // Initialisiere die Echtzeit-Synchronisationssteuerung auf der Hauptseite
    function initRealtimeSyncControls() {
        // Originale Implementierung für die bekannten IDs
        const startButton = document.getElementById('start-realtime-sync');
        const stopButton = document.getElementById('stop-realtime-sync');
        
        if (startButton) {
            startButton.addEventListener('click', startRealtimeSync);
        }
        
        if (stopButton) {
            stopButton.addEventListener('click', stopRealtimeSync);
        }
        
        // Zusätzliche Implementierung für Buttons mit Text "Starten" und "Stoppen"
        document.querySelectorAll('button').forEach(button => {
            const buttonText = button.textContent.trim();
            if (buttonText === 'Starten') {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('Start-Button geklickt (Text-basiert)');
                    startRealtimeSync();
                });
            } else if (buttonText.includes('Starten')) {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('Start-Button geklickt (enthält "Starten")');
                    startRealtimeSync();
                });
            } else if (buttonText === 'Stoppen') {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('Stop-Button geklickt (Text-basiert)');
                    stopRealtimeSync();
                });
            } else if (buttonText.includes('Stoppen')) {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('Stop-Button geklickt (enthält "Stoppen")');
                    stopRealtimeSync();
                });
            }
        });
        
        // Rufe den Status beim Laden der Seite ab
        getRealtimeSyncStatus();
        
        // Aktualisiere den Status regelmäßig (alle 5 Sekunden)
        setInterval(getRealtimeSyncStatus, 5000);
    }
    
    // Initialisiere die Bedienelemente
    initRealtimeSyncControls();
    
    // Modal zum Hinzufügen eines neuen Slaves
    const addSlaveForm = document.getElementById('addSlaveForm');
    if (addSlaveForm) {
        addSlaveForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(addSlaveForm);
            const slaveData = {
                name: formData.get('slaveName'),
                db_path: formData.get('slavePath'),
                server: formData.get('slaveServer') || null
            };
            
            fetch('/api/slaves', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(slaveData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification('Slave erfolgreich hinzugefügt', 'success');
                    addSlaveForm.reset();
                    bootstrap.Modal.getInstance(document.getElementById('addSlaveModal')).hide();
                    loadSlaves();
                } else {
                    showNotification('Fehler beim Hinzufügen des Slaves: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Fehler beim Hinzufügen des Slaves:', error);
                showNotification('Fehler beim Hinzufügen des Slaves', 'danger');
            });
        });
    }
}); 