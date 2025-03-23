/**
 * SQLite-Datenbanksynchronisierung Frontend
 * 
 * JavaScript für die Slave-Detail-Seite
 */

document.addEventListener('DOMContentLoaded', function() {
    // Socket.io-Verbindung initialisieren
    const socket = io();
    
    // DOM-Elemente
    const slaveTitle = document.getElementById('slaveTitle');
    const slaveLoadingAlert = document.getElementById('slaveLoadingAlert');
    const slaveDetails = document.getElementById('slaveDetails');
    const refreshBtn = document.getElementById('refreshBtn');
    const syncSlaveBtn = document.getElementById('syncSlaveBtn');
    const initialSyncBtn = document.getElementById('initialSyncBtn');
    const checkIntegrityBtn = document.getElementById('checkIntegrityBtn');
    const deleteSlaveBtn = document.getElementById('deleteSlaveBtn');
    const saveSlaveBtn = document.getElementById('saveSlaveBtn');
    const loadTablesBtn = document.getElementById('loadTablesBtn');
    
    // Slave-Daten laden
    loadSlaveDetails();
    
    // Event-Listener
    refreshBtn.addEventListener('click', loadSlaveDetails);
    syncSlaveBtn.addEventListener('click', syncSlave);
    initialSyncBtn.addEventListener('click', initialSyncSlave);
    checkIntegrityBtn.addEventListener('click', checkIntegrity);
    deleteSlaveBtn.addEventListener('click', confirmDeleteSlave);
    saveSlaveBtn.addEventListener('click', saveSlaveChanges);
    loadTablesBtn.addEventListener('click', loadAvailableTables);
    
    // Socket.io Event-Listener für Echtzeit-Updates
    socket.on('sync_update', function(data) {
        if (data.slave_id === slaveId) {
            loadSlaveDetails();
        }
    });
    
    /**
     * Lädt die Details des Slaves von der API
     */
    function loadSlaveDetails() {
        slaveLoadingAlert.classList.remove('d-none');
        slaveDetails.classList.add('d-none');
        
        fetch(`/api/slaves/${slaveId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Slave nicht gefunden');
                }
                return response.json();
            })
            .then(data => {
                console.log('Slave-Daten erhalten:', JSON.stringify(data));
                updateSlaveDetails(data);
                loadSlaveLogs();
            })
            .catch(error => {
                console.error('Fehler beim Laden der Slave-Details:', error);
                showNotification(`Fehler: ${error.message}`, 'danger');
            });
    }
    
    /**
     * Aktualisiert die Anzeige mit den Slave-Details
     */
    function updateSlaveDetails(data) {
        // Überprüfen, ob die Slave-Daten im erwarteten Format vorhanden sind
        if (!data || !data.slave) {
            console.error('Fehlerhafte Datenstruktur:', data);
            slaveTitle.innerHTML = `<i class="bi bi-hdd-network"></i> Unbekannter Slave`;
            slaveLoadingAlert.classList.add('d-none');
            slaveDetails.classList.remove('d-none');
            return;
        }
        
        const slave = data.slave;
        
        slaveTitle.innerHTML = `<i class="bi bi-hdd-network"></i> ${slave.name || 'Unbekannter Slave'}`;
        
        // Allgemeine Informationen aktualisieren
        document.getElementById('slaveName').textContent = slave.name || 'Nicht angegeben';
        document.getElementById('slaveDbPath').textContent = slave.db_path || 'Nicht angegeben';
        document.getElementById('slaveServerAddress').textContent = slave.server_address || 'Nicht angegeben';
        
        // Status mit entsprechendem Badge anzeigen
        const statusElement = document.getElementById('slaveStatus');
        const status = slave.status || 'inactive';
        let statusBadge = '';
        
        if (status === 'active') {
            statusBadge = '<span class="badge bg-success">Aktiv</span>';
        } else if (status === 'inactive') {
            statusBadge = '<span class="badge bg-secondary">Inaktiv</span>';
        } else if (status === 'error') {
            statusBadge = '<span class="badge bg-danger">Fehler</span>';
        } else if (status === 'syncing') {
            statusBadge = '<span class="badge bg-primary">Synchronisierung läuft</span>';
        }
        
        statusElement.innerHTML = statusBadge;
        
        // Zeitstempel formatieren
        document.getElementById('slaveLastSync').textContent = 
            slave.last_sync ? formatDateTime(slave.last_sync) : 'Keine Synchronisation';
        document.getElementById('slaveCreatedAt').textContent = 
            slave.created_at ? formatDateTime(slave.created_at) : 'Unbekannt';
        
        // Ignorierte Tabellen anzeigen
        const ignoredTablesElement = document.getElementById('slaveIgnoredTables');
        if (slave.ignored_tables && slave.ignored_tables.length > 0) {
            const tablesList = document.createElement('ul');
            tablesList.className = 'list-group';
            
            slave.ignored_tables.forEach(table => {
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                listItem.textContent = table;
                tablesList.appendChild(listItem);
            });
            
            ignoredTablesElement.innerHTML = '';
            ignoredTablesElement.appendChild(tablesList);
        } else {
            ignoredTablesElement.innerHTML = '<p>Keine Tabellen ignoriert</p>';
        }
        
        // Modal-Felder für die Bearbeitung vorausfüllen
        document.getElementById('editSlaveName').value = slave.name || '';
        document.getElementById('editDbPath').value = slave.db_path || '';
        document.getElementById('editServerAddress').value = slave.server_address || '';
        document.getElementById('editStatus').value = slave.status || 'inactive';
        document.getElementById('editIgnoredTables').value = slave.ignored_tables ? slave.ignored_tables.join(', ') : '';
        
        // Lade-Anzeige ausblenden und Details anzeigen
        slaveLoadingAlert.classList.add('d-none');
        slaveDetails.classList.remove('d-none');
    }
    
    /**
     * Lädt die Logs des Slaves
     */
    function loadSlaveLogs() {
        fetch(`/api/logs?slave_id=${slaveId}&limit=5`)
            .then(response => response.json())
            .then(data => {
                const logsTableBody = document.getElementById('syncLogsTableBody');
                logsTableBody.innerHTML = '';
                
                if (data.logs && data.logs.length > 0) {
                    data.logs.forEach(log => {
                        const row = document.createElement('tr');
                        
                        // Zeitstempel
                        const timestampCell = document.createElement('td');
                        timestampCell.textContent = formatDateTime(log.created_at || log.timestamp);
                        row.appendChild(timestampCell);
                        
                        // Status
                        const statusCell = document.createElement('td');
                        let statusBadge = '';
                        if (log.status === 'success') {
                            statusBadge = '<span class="badge bg-success">Erfolg</span>';
                        } else if (log.status === 'error') {
                            statusBadge = '<span class="badge bg-danger">Fehler</span>';
                        } else if (log.status === 'warning') {
                            statusBadge = '<span class="badge bg-warning text-dark">Warnung</span>';
                        } else {
                            statusBadge = `<span class="badge bg-secondary">${log.status}</span>`;
                        }
                        statusCell.innerHTML = statusBadge;
                        row.appendChild(statusCell);
                        
                        // Nachricht
                        const messageCell = document.createElement('td');
                        messageCell.textContent = log.message;
                        row.appendChild(messageCell);
                        
                        // Änderungen
                        const changesCell = document.createElement('td');
                        changesCell.textContent = log.changes_count || 0;
                        row.appendChild(changesCell);
                        
                        // Dauer
                        const durationCell = document.createElement('td');
                        durationCell.textContent = log.duration ? log.duration.toFixed(2) : '0.00';
                        row.appendChild(durationCell);
                        
                        logsTableBody.appendChild(row);
                    });
                } else {
                    const emptyRow = document.createElement('tr');
                    const emptyCell = document.createElement('td');
                    emptyCell.colSpan = 5;
                    emptyCell.className = 'text-center';
                    emptyCell.textContent = 'Keine Logs vorhanden';
                    emptyRow.appendChild(emptyCell);
                    logsTableBody.appendChild(emptyRow);
                }
            })
            .catch(error => {
                console.error('Fehler beim Laden der Logs:', error);
                showNotification('Fehler beim Laden der Logs', 'danger');
            });
    }
    
    /**
     * Startet die Synchronisation des Slaves
     */
    function syncSlave() {
        syncSlaveBtn.disabled = true;
        syncSlaveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Synchronisiere...';
        
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
                showNotification(data.message || 'Synchronisation gestartet', 'success');
                // Verzögerung, um die Daten nach der Synchronisation zu laden
                setTimeout(loadSlaveDetails, 2000);
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler bei der Synchronisation:', error);
            showNotification('Fehler bei der Synchronisation', 'danger');
        })
        .finally(() => {
            syncSlaveBtn.disabled = false;
            syncSlaveBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Jetzt synchronisieren';
        });
    }
    
    /**
     * Startet die vollständige Synchronisation des Slaves
     */
    function initialSyncSlave() {
        if (confirm('Möchten Sie wirklich eine vollständige Synchronisation durchführen? Dies kann je nach Datenbankgröße längere Zeit dauern.')) {
            initialSyncBtn.disabled = true;
            initialSyncBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Vollständige Synchronisation...';
            
            fetch(`/api/slaves/${slaveId}/sync`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ initial: true })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification(data.message || 'Vollständige Synchronisation gestartet', 'success');
                    // Verzögerung, um die Daten nach der Synchronisation zu laden
                    setTimeout(loadSlaveDetails, 2000);
                } else {
                    showNotification(`Fehler: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Fehler bei der vollständigen Synchronisation:', error);
                showNotification('Fehler bei der vollständigen Synchronisation', 'danger');
            })
            .finally(() => {
                initialSyncBtn.disabled = false;
                initialSyncBtn.innerHTML = '<i class="bi bi-lightning-charge"></i> Vollständige Synchronisation';
            });
        }
    }
    
    /**
     * Überprüft die Datenbankintegrität des Slaves
     */
    function checkIntegrity() {
        checkIntegrityBtn.disabled = true;
        checkIntegrityBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Prüfe...';
        
        fetch(`/api/slaves/${slaveId}/integrity`)
            .then(response => response.json())
            .then(data => {
                // Modal mit den Integritätsprüfungsergebnissen anzeigen
                const integrityResults = document.getElementById('integrityResults');
                if (data.status === 'success') {
                    let resultsHtml = '<div class="alert alert-success"><i class="bi bi-check-circle"></i> Integritätsprüfung erfolgreich</div>';
                    
                    resultsHtml += '<h6 class="mt-3">Details:</h6>';
                    resultsHtml += '<ul class="list-group mb-3">';
                    
                    if (data.tables_count !== undefined) {
                        resultsHtml += `<li class="list-group-item d-flex justify-content-between align-items-center">
                            Anzahl der überprüften Tabellen
                            <span class="badge bg-primary rounded-pill">${data.tables_count}</span>
                        </li>`;
                    }
                    
                    if (data.rows_count !== undefined) {
                        resultsHtml += `<li class="list-group-item d-flex justify-content-between align-items-center">
                            Gesamtzahl der Datensätze
                            <span class="badge bg-primary rounded-pill">${data.rows_count}</span>
                        </li>`;
                    }
                    
                    if (data.inconsistencies !== undefined) {
                        resultsHtml += `<li class="list-group-item d-flex justify-content-between align-items-center">
                            Gefundene Inkonsistenzen
                            <span class="badge bg-${data.inconsistencies > 0 ? 'danger' : 'success'} rounded-pill">${data.inconsistencies}</span>
                        </li>`;
                    }
                    
                    resultsHtml += '</ul>';
                    
                    if (data.details) {
                        resultsHtml += '<h6>Tabellen-Details:</h6>';
                        resultsHtml += '<table class="table table-sm table-striped">';
                        resultsHtml += '<thead><tr><th>Tabelle</th><th>Master-Datensätze</th><th>Slave-Datensätze</th><th>Differenz</th></tr></thead>';
                        resultsHtml += '<tbody>';
                        
                        for (const table in data.details) {
                            const detail = data.details[table];
                            const diff = detail.master_count - detail.slave_count;
                            const diffClass = diff === 0 ? 'success' : (diff > 0 ? 'warning' : 'danger');
                            
                            resultsHtml += `<tr>
                                <td>${table}</td>
                                <td>${detail.master_count}</td>
                                <td>${detail.slave_count}</td>
                                <td><span class="badge bg-${diffClass}">${diff}</span></td>
                            </tr>`;
                        }
                        
                        resultsHtml += '</tbody></table>';
                    }
                    
                    integrityResults.innerHTML = resultsHtml;
                } else {
                    integrityResults.innerHTML = `<div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle"></i> 
                        Fehler bei der Integritätsprüfung: ${data.message || 'Unbekannter Fehler'}
                    </div>`;
                }
                
                // Modal anzeigen
                const integrityModal = new bootstrap.Modal(document.getElementById('integrityResultsModal'));
                integrityModal.show();
            })
            .catch(error => {
                console.error('Fehler bei der Integritätsprüfung:', error);
                showNotification('Fehler bei der Integritätsprüfung', 'danger');
            })
            .finally(() => {
                checkIntegrityBtn.disabled = false;
                checkIntegrityBtn.innerHTML = '<i class="bi bi-shield-check"></i> Integrität prüfen';
            });
    }
    
    /**
     * Zeigt eine Bestätigungsdialog zum Löschen des Slaves an
     */
    function confirmDeleteSlave() {
        if (confirm(`Möchten Sie den Slave "${document.getElementById('slaveName').textContent}" wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.`)) {
            deleteSlave();
        }
    }
    
    /**
     * Löscht den Slave
     */
    function deleteSlave() {
        deleteSlaveBtn.disabled = true;
        deleteSlaveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Lösche...';
        
        fetch(`/api/slaves/${slaveId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification(data.message || 'Slave erfolgreich gelöscht', 'success');
                // Zurück zum Dashboard nach kurzer Verzögerung
                setTimeout(() => {
                    window.location.href = '/';
                }, 1500);
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
                deleteSlaveBtn.disabled = false;
                deleteSlaveBtn.innerHTML = '<i class="bi bi-trash"></i> Slave löschen';
            }
        })
        .catch(error => {
            console.error('Fehler beim Löschen des Slaves:', error);
            showNotification('Fehler beim Löschen des Slaves', 'danger');
            deleteSlaveBtn.disabled = false;
            deleteSlaveBtn.innerHTML = '<i class="bi bi-trash"></i> Slave löschen';
        });
    }
    
    /**
     * Lädt die verfügbaren Tabellen für das Ausschlussformular
     */
    function loadAvailableTables() {
        loadTablesBtn.disabled = true;
        loadTablesBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Lade Tabellen...';
        
        fetch('/api/tables')
            .then(response => response.json())
            .then(data => {
                const availableTables = document.getElementById('availableTables');
                availableTables.innerHTML = '';
                
                if (data.tables && data.tables.length > 0) {
                    // Array der aktuell ignorierten Tabellen
                    const currentIgnored = document.getElementById('editIgnoredTables').value
                        .split(',')
                        .map(t => t.trim())
                        .filter(t => t);
                    
                    // Checkboxen für jede Tabelle erstellen
                    data.tables.forEach(table => {
                        const isChecked = currentIgnored.includes(table);
                        
                        const div = document.createElement('div');
                        div.className = 'form-check';
                        
                        const input = document.createElement('input');
                        input.className = 'form-check-input table-checkbox';
                        input.type = 'checkbox';
                        input.id = `table-${table}`;
                        input.value = table;
                        input.checked = isChecked;
                        input.addEventListener('change', updateIgnoredTablesInput);
                        
                        const label = document.createElement('label');
                        label.className = 'form-check-label';
                        label.htmlFor = `table-${table}`;
                        label.textContent = table;
                        
                        div.appendChild(input);
                        div.appendChild(label);
                        availableTables.appendChild(div);
                    });
                    
                    // Container anzeigen
                    document.getElementById('availableTablesContainer').classList.remove('d-none');
                } else {
                    availableTables.innerHTML = '<p>Keine Tabellen verfügbar</p>';
                }
            })
            .catch(error => {
                console.error('Fehler beim Laden der Tabellen:', error);
                showNotification('Fehler beim Laden der Tabellen', 'danger');
            })
            .finally(() => {
                loadTablesBtn.disabled = false;
                loadTablesBtn.innerHTML = 'Verfügbare Tabellen laden';
            });
    }
    
    /**
     * Aktualisiert das Eingabefeld für ignorierte Tabellen basierend auf den Checkboxen
     */
    function updateIgnoredTablesInput() {
        const checkboxes = document.querySelectorAll('.table-checkbox:checked');
        const ignoredTables = Array.from(checkboxes).map(cb => cb.value);
        document.getElementById('editIgnoredTables').value = ignoredTables.join(', ');
    }
    
    /**
     * Speichert die Änderungen am Slave
     */
    function saveSlaveChanges() {
        saveSlaveBtn.disabled = true;
        saveSlaveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Speichere...';
        
        // Daten aus dem Formular sammeln
        const name = document.getElementById('editSlaveName').value;
        const dbPath = document.getElementById('editDbPath').value;
        const serverAddress = document.getElementById('editServerAddress').value;
        const status = document.getElementById('editStatus').value;
        const ignoredTablesStr = document.getElementById('editIgnoredTables').value;
        
        // Ignorierte Tabellen in ein Array umwandeln
        const ignoredTables = ignoredTablesStr
            .split(',')
            .map(t => t.trim())
            .filter(t => t);
        
        // Daten an die API senden
        fetch(`/api/slaves/${slaveId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                db_path: dbPath,
                server_address: serverAddress,
                status,
                ignored_tables: ignoredTables
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification(data.message || 'Slave erfolgreich aktualisiert', 'success');
                
                // Modal schließen
                const modal = bootstrap.Modal.getInstance(document.getElementById('editSlaveModal'));
                modal.hide();
                
                // Daten neu laden
                loadSlaveDetails();
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler beim Speichern der Änderungen:', error);
            showNotification('Fehler beim Speichern der Änderungen', 'danger');
        })
        .finally(() => {
            saveSlaveBtn.disabled = false;
            saveSlaveBtn.innerHTML = 'Speichern';
        });
    }
    
    /**
     * Zeigt eine Benachrichtigung an
     */
    function showNotification(message, type = 'info') {
        // Toast-Container erstellen, falls nicht vorhanden
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Toast-Element erstellen
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.className = `toast bg-${type} text-white`;
        toast.id = toastId;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // Toast-Inhalt
        toast.innerHTML = `
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">Benachrichtigung</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Schließen"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        // Toast zum Container hinzufügen
        toastContainer.appendChild(toast);
        
        // Toast initialisieren und anzeigen
        const toastInstance = new bootstrap.Toast(toast);
        toastInstance.show();
        
        // Toast nach 5 Sekunden entfernen
        setTimeout(() => {
            if (document.getElementById(toastId)) {
                toastInstance.hide();
                setTimeout(() => {
                    if (document.getElementById(toastId)) {
                        document.getElementById(toastId).remove();
                    }
                }, 500);
            }
        }, 5000);
    }

    /**
     * Formatiert einen Zeitstempel korrekt für die Anzeige
     * Unterstützt sowohl ISO 8601 als auch SQLite-Zeitstempel (YYYY-MM-DD HH:MM:SS)
     */
    function formatDateTime(dateTimeStr) {
        try {
            // Wenn das Format bereits YYYY-MM-DD HH:MM:SS ist
            if (dateTimeStr.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)) {
                // Konvertiere es zu einem ISO 8601 Format, das vom Date-Konstruktor besser verarbeitet wird
                const [datePart, timePart] = dateTimeStr.split(' ');
                dateTimeStr = `${datePart}T${timePart}`;
            }
            
            const date = new Date(dateTimeStr);
            
            // Überprüfen, ob das Datum gültig ist
            if (isNaN(date.getTime())) {
                console.error('Ungültiges Datum:', dateTimeStr);
                return dateTimeStr; // Gib den Original-String zurück
            }
            
            return date.toLocaleString('de-DE');
        } catch (error) {
            console.error('Fehler beim Formatieren des Datums:', error);
            return dateTimeStr; // Gib den Original-String zurück
        }
    }
}); 