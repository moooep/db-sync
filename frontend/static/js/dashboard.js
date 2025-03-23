// Dashboard-Funktionen
function loadDashboard() {
    console.log('loadDashboard wird ausgeführt');
    // Lade die Liste der Slave-Datenbanken
    loadSlaves();
    
    // Echtzeit-Synchronisation Steuerelemente initialisieren
    initRealtimeSyncControls();
}

function loadSlaves() {
    console.log('loadSlaves wird ausgeführt');
    fetch('/api/slaves')
        .then(response => response.json())
        .then(data => {
            console.log('API-Antwort für Slaves:', data);
            if (data.slaves && Array.isArray(data.slaves)) {
                console.log('Slaves-Array gefunden mit ' + data.slaves.length + ' Einträgen');
                displaySlaves(data.slaves);
            } else if (Array.isArray(data)) {
                console.log('Direkt Array erhalten mit ' + data.length + ' Einträgen');
                displaySlaves(data);
            } else if (data.status === 'success') {
                displaySlaves(data.slaves);
            } else {
                console.error('Fehler beim Laden der Slaves:', data);
                showNotification('Fehler beim Laden der Slaves', 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler beim Laden der Slaves:', error);
            showNotification('Fehler beim Laden der Slaves', 'danger');
        });
}

function displaySlaves(slaves) {
    console.log('displaySlaves wird ausgeführt mit', slaves);
    const container = document.getElementById('slaves-container');
    
    if (!container) {
        console.error('slaves-container nicht gefunden!');
        return;
    }
    
    container.innerHTML = '';

    if (!slaves || slaves.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info">
                    Keine Slave-Datenbanken konfiguriert. Fügen Sie einen Slave hinzu, um zu beginnen.
                </div>
            </div>
        `;
        return;
    }

    slaves.forEach(slave => {
        const card = document.createElement('div');
        card.className = 'col-lg-6 mb-4';
        
        const lastSync = slave.last_sync ? new Date(slave.last_sync).toLocaleString() : 'Nie';
        const statusBadge = slave.status === 'active' ? 
            '<span class="badge bg-success">Online</span>' : 
            '<span class="badge bg-danger">Offline</span>';
        
        card.innerHTML = `
            <div class="card h-100">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">${slave.name}</h5>
                    <div>${statusBadge}</div>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <strong>Pfad:</strong> ${slave.db_path}
                    </div>
                    <div class="mb-3">
                        <strong>Letzte Synchronisation:</strong> ${lastSync}
                    </div>
                    <div class="progress mb-3" style="height: 20px;">
                        <div class="progress-bar" role="progressbar" style="width: ${slave.sync_status?.progress || 0}%;" 
                            aria-valuenow="${slave.sync_status?.progress || 0}" aria-valuemin="0" aria-valuemax="100">
                            ${slave.sync_status?.progress || 0}%
                        </div>
                    </div>
                </div>
                <div class="card-footer d-flex justify-content-between">
                    <div>
                        <button class="btn btn-primary btn-sm me-2 sync-button" data-slave-id="${slave.id}">
                            <i class="bi bi-arrow-repeat"></i> Synchronisieren
                        </button>
                        <button class="btn btn-info btn-sm integrity-button" data-slave-id="${slave.id}">
                            <i class="bi bi-shield-check"></i> Integrität prüfen
                        </button>
                    </div>
                    <div>
                        <button class="btn btn-danger btn-sm delete-button" data-slave-id="${slave.id}">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(card);
    });
    
    // Event-Listener zu den Schaltflächen hinzufügen
    addSlaveButtonListeners();
}

function addSlaveButtonListeners() {
    // Sync-Buttons
    document.querySelectorAll('.sync-button').forEach(button => {
        button.addEventListener('click', function() {
            const slaveId = this.getAttribute('data-slave-id');
            syncSlave(slaveId);
        });
    });
    
    // Integritätsprüfungs-Buttons
    document.querySelectorAll('.integrity-button').forEach(button => {
        button.addEventListener('click', function() {
            const slaveId = this.getAttribute('data-slave-id');
            checkIntegrity(slaveId);
        });
    });
    
    // Lösch-Buttons
    document.querySelectorAll('.delete-button').forEach(button => {
        button.addEventListener('click', function() {
            const slaveId = this.getAttribute('data-slave-id');
            if (confirm('Sind Sie sicher, dass Sie diese Slave-Datenbank entfernen möchten?')) {
                deleteSlave(slaveId);
            }
        });
    });
}

function syncSlave(slaveId) {
    fetch(`/api/slaves/${slaveId}/sync`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ force: true })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification(`Synchronisation für Slave ${slaveId} gestartet: ${data.message}`, 'success');
        } else {
            showNotification(`Fehler bei der Synchronisation für Slave ${slaveId}: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Fehler bei der Synchronisation:', error);
        showNotification(`Fehler bei der Synchronisation für Slave ${slaveId}`, 'danger');
    });
}

function checkIntegrity(slaveId) {
    fetch(`/api/slaves/${slaveId}/integrity`)
        .then(response => response.json())
        .then(data => {
            console.log('Integritätsprüfung Antwort:', data);
            if (data.status === 'success') {
                const modalTitle = `Integritätsprüfung für Slave ${slaveId}`;
                const modalBody = renderIntegrityResult(data);
                showModal(modalTitle, modalBody);
            } else {
                showNotification(`Fehler bei der Integritätsprüfung: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler bei der Integritätsprüfung:', error);
            showNotification('Fehler bei der Integritätsprüfung', 'danger');
        });
}

function renderIntegrityResult(result) {
    console.log('Integritätsprüfung Ergebnis:', result);
    
    let html = `
        <div class="alert ${result.inconsistencies === 0 ? 'alert-success' : 'alert-danger'}">
            <strong>Gesamtergebnis:</strong> ${result.inconsistencies === 0 ? 'Keine Inkonsistenzen gefunden' : `${result.inconsistencies} Inkonsistenzen gefunden`}
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <strong>Master-Datenbank:</strong> ${result.master?.status || 'N/A'}
            </div>
            <div class="col-md-6">
                <strong>Slave-Datenbank:</strong> ${result.slave?.status || 'N/A'}
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <strong>Tabellen:</strong> ${result.tables_count || 'N/A'}
            </div>
            <div class="col-md-6">
                <strong>Zeilen insgesamt:</strong> ${result.rows_count || 'N/A'}
            </div>
        </div>
        <h5>Tabellen-Vergleich:</h5>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Tabelle</th>
                    <th>Master-Zeilen</th>
                    <th>Slave-Zeilen</th>
                    <th>Differenz</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    if (result.details && typeof result.details === 'object') {
        for (const [table, detail] of Object.entries(result.details)) {
            const statusClass = detail.difference === 0 ? 'success' : 'danger';
            
            html += `
                <tr class="table-${statusClass}">
                    <td>${table}</td>
                    <td>${detail.master_count}</td>
                    <td>${detail.slave_count}</td>
                    <td>${detail.difference}</td>
                    <td>${detail.difference === 0 ? 'Übereinstimmend' : 'Unterschiedlich'}</td>
                </tr>
            `;
        }
    } else {
        html += `
            <tr>
                <td colspan="5" class="text-center">Keine Tabellendetails verfügbar</td>
            </tr>
        `;
    }
    
    html += `
            </tbody>
        </table>
    `;
    
    return html;
}

function deleteSlave(slaveId) {
    fetch(`/api/slaves/${slaveId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification('Slave erfolgreich entfernt', 'success');
            loadSlaves();
        } else {
            showNotification(`Fehler beim Entfernen des Slaves: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Fehler beim Entfernen des Slaves:', error);
        showNotification('Fehler beim Entfernen des Slaves', 'danger');
    });
}

function showModal(title, body) {
    const modalId = 'dynamicModal';
    let modal = document.getElementById(modalId);
    
    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"></h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Schließen"></button>
                    </div>
                    <div class="modal-body"></div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Schließen</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    modal.querySelector('.modal-title').textContent = title;
    modal.querySelector('.modal-body').innerHTML = body;
    
    try {
        const bsModal = new bootstrap.Modal(modal);
        
        // Event-Listener für das Entfernen des Backdrops und Aufräumen nach dem Schließen
        modal.addEventListener('hidden.bs.modal', function() {
            // Backdrop manuell entfernen falls vorhanden
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
            
            // Scrolling wieder aktivieren
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }, { once: true }); // Event nur einmal ausführen
        
        bsModal.show();
    } catch (error) {
        console.error('Fehler beim Anzeigen des Modals:', error);
    }
}

function showNotification(message, type = 'info') {
    const toastId = 'notification-toast';
    let toast = document.getElementById(toastId);
    
    if (!toast) {
        // Toast erstellen, wenn es nicht existiert
        toast = document.createElement('div');
        toast.id = toastId;
        toast.className = 'toast position-fixed bottom-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">DB-Sync</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Schließen"></button>
            </div>
            <div class="toast-body"></div>
        `;
        
        document.body.appendChild(toast);
    }
    
    // Toast-Inhalt aktualisieren
    toast.querySelector('.toast-body').textContent = message;
    
    // Toast-Typ festlegen
    toast.className = `toast position-fixed bottom-0 end-0 m-3 text-white bg-${type}`;
    
    // Toast anzeigen
    const bsToast = new bootstrap.Toast(toast, {
        delay: 3000
    });
    bsToast.show();
}

// Echtzeit-Synchronisation Funktionen
function getRealtimeSyncStatus() {
    fetch('/api/realtime-sync/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const statusElement = document.querySelector('#realtime-sync-status, .realtime-sync-status');
                const queueElement = document.querySelector('#realtime-sync-queue, .realtime-sync-queue');
                
                if (statusElement) {
                    statusElement.innerHTML = data.realtime_sync_active ? 
                        '<span class="badge bg-success">Aktiv</span>' : 
                        '<span class="badge bg-secondary">Inaktiv</span>';
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
    // Suche nach Buttons mit bestimmten IDs
    const startButtonById = document.getElementById('start-realtime-sync');
    const stopButtonById = document.getElementById('stop-realtime-sync');
    
    // Suche nach Buttons mit Text "Starten" oder "Stoppen"
    const allButtons = document.querySelectorAll('button');
    const startButtons = Array.from(allButtons).filter(button => 
        button.textContent.trim().includes('Starten'));
    const stopButtons = Array.from(allButtons).filter(button => 
        button.textContent.trim().includes('Stoppen'));
    
    // Aktiviere/deaktiviere Start-Buttons
    if (startButtonById) {
        startButtonById.disabled = isActive;
    }
    
    startButtons.forEach(button => {
        button.disabled = isActive;
    });
    
    // Aktiviere/deaktiviere Stop-Buttons
    if (stopButtonById) {
        stopButtonById.disabled = !isActive;
    }
    
    stopButtons.forEach(button => {
        button.disabled = !isActive;
    });
}

function initRealtimeSyncControls() {
    // Füge Event-Listener zu allen Start- und Stopp-Buttons hinzu
    document.querySelectorAll('button').forEach(button => {
        const buttonText = button.textContent.trim();
        
        if (button.id === 'start-realtime-sync' || buttonText.includes('Starten')) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Start-Button geklickt');
                startRealtimeSync();
            });
        } else if (button.id === 'stop-realtime-sync' || buttonText.includes('Stoppen')) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Stop-Button geklickt');
                stopRealtimeSync();
            });
        }
    });
    
    // Rufe den Status beim Laden der Seite ab
    getRealtimeSyncStatus();
    
    // Aktualisiere den Status regelmäßig (alle 5 Sekunden)
    setInterval(getRealtimeSyncStatus, 5000);
} 