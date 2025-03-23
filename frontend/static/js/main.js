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
        const tablesContainer = document.getElementById('availableTablesContainer');
        const tablesList = document.getElementById('availableTables');
        
        loadTablesBtn.disabled = true;
        loadTablesBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Lade...';
        
        fetch('/api/tables')
            .then(response => response.json())
            .then(data => {
                if (data.tables && data.tables.length > 0) {
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
                } else {
                    tablesList.innerHTML = '<p>Keine Tabellen gefunden.</p>';
                    tablesContainer.classList.remove('d-none');
                }
            })
            .catch(error => {
                console.error('Fehler beim Laden der Tabellen:', error);
                tablesList.innerHTML = '<p class="text-danger">Fehler beim Laden der Tabellen.</p>';
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
}); 