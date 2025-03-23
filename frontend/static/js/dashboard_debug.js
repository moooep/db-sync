// Debug-Funktionen für die Buttons im Dashboard

// Funktionen für die Echtzeit-Synchronisation
function debug_startRealtimeSync() {
    console.log('Debug: Starte Echtzeit-Synchronisation');
    
    fetch('/api/realtime-sync/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Antwort vom Server:', data);
        if (data.status === 'success') {
            alert('Echtzeit-Synchronisation gestartet');
        } else {
            alert('Fehler: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Fehler beim Starten der Echtzeit-Synchronisation:', error);
        alert('Fehler beim Starten der Echtzeit-Synchronisation');
    });
}

function debug_stopRealtimeSync() {
    console.log('Debug: Stoppe Echtzeit-Synchronisation');
    
    fetch('/api/realtime-sync/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Antwort vom Server:', data);
        if (data.status === 'success') {
            alert('Echtzeit-Synchronisation gestoppt');
        } else {
            alert('Fehler: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Fehler beim Stoppen der Echtzeit-Synchronisation:', error);
        alert('Fehler beim Stoppen der Echtzeit-Synchronisation');
    });
}

// Funktion für das Speichern eines neuen Slaves
function debug_saveNewSlave() {
    console.log('Debug: Speichere neuen Slave');
    
    const nameInput = document.getElementById('slaveName') || document.querySelector('[name="slaveName"]');
    const dbPathInput = document.getElementById('dbPath') || document.querySelector('[name="dbPath"]') || document.querySelector('[name="slavePath"]');
    const serverAddressInput = document.getElementById('serverAddress') || document.querySelector('[name="serverAddress"]') || document.querySelector('[name="slaveServer"]');
    const ignoredTablesInput = document.getElementById('ignoredTables') || document.querySelector('[name="ignoredTables"]');
    
    if (!nameInput || !dbPathInput) {
        alert('Konnte die Formularfelder nicht finden');
        console.error('Konnte die Formularfelder nicht finden');
        return;
    }
    
    if (!nameInput.value || !dbPathInput.value) {
        alert('Bitte füllen Sie alle Pflichtfelder aus');
        return;
    }
    
    const slaveData = {
        name: nameInput.value,
        db_path: dbPathInput.value,
        server_address: serverAddressInput ? serverAddressInput.value : null,
        ignored_tables: ignoredTablesInput && ignoredTablesInput.value ? 
            ignoredTablesInput.value.split(',') : []
    };
    
    console.log('Slave-Daten:', slaveData);
    
    fetch('/api/slaves', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(slaveData)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Antwort vom Server:', data);
        if (data.status === 'success') {
            alert('Slave erfolgreich hinzugefügt');
            
            // Formular zurücksetzen
            if (nameInput) nameInput.value = '';
            if (dbPathInput) dbPathInput.value = '';
            if (serverAddressInput) serverAddressInput.value = '';
            if (ignoredTablesInput) ignoredTablesInput.value = '';
            
            // Seite neu laden
            window.location.reload();
        } else {
            alert('Fehler: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Fehler beim Hinzufügen des Slaves:', error);
        alert('Fehler beim Hinzufügen des Slaves');
    });
}

// Debug-Funktion zum manuellen Laden der Slaves
function debug_loadSlaves() {
    console.log('Debug: Slaves werden geladen...');
    
    fetch('/api/slaves')
        .then(response => response.json())
        .then(data => {
            console.log('Debug: API-Antwort für Slaves:', data);
            
            // Prüfen, ob Slaves-Array direkt verfügbar ist
            if (data.slaves && Array.isArray(data.slaves)) {
                console.log('Debug: Slaves-Array gefunden mit ' + data.slaves.length + ' Einträgen');
                debug_displaySlaves(data.slaves);
            } else if (Array.isArray(data)) {
                // Alternativ: API gibt direkt ein Array zurück
                console.log('Debug: Direkt Array erhalten mit ' + data.length + ' Einträgen');
                debug_displaySlaves(data);
            } else {
                console.error('Debug: Unerwartetes Antwortformat:', data);
                alert('Fehler beim Laden der Slaves: Unerwartetes Antwortformat');
            }
        })
        .catch(error => {
            console.error('Debug: Fetch-Fehler beim Laden der Slaves:', error);
            alert('Fehler beim Laden der Slaves: ' + error.message);
        });
}

// Debug-Funktion zum Anzeigen der Slaves
function debug_displaySlaves(slaves) {
    console.log('Debug: Slaves werden angezeigt:', slaves);
    
    const container = document.getElementById('slaves-container');
    
    if (!container) {
        console.error('Debug: slaves-container nicht gefunden!');
        alert('Fehler: slaves-container Element wurde nicht gefunden!');
        return;
    }
    
    console.log('Debug: Container gefunden, HTML wird generiert');
    container.innerHTML = '';

    if (slaves.length === 0) {
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
        console.log('Debug: Slave-Karte wird erstellt für:', slave);
        const card = document.createElement('div');
        card.className = 'col-lg-6 mb-4';
        
        const lastSync = slave.last_sync ? new Date(slave.last_sync).toLocaleString() : 'Nie';
        const statusBadge = (slave.status === 'active' || slave.is_online) ? 
            '<span class="badge bg-success">Aktiv</span>' : 
            '<span class="badge bg-danger">Inaktiv</span>';
        
        card.innerHTML = `
            <div class="card h-100">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">${slave.name}</h5>
                    <div>${statusBadge}</div>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <strong>ID:</strong> ${slave.id}
                    </div>
                    <div class="mb-3">
                        <strong>Pfad:</strong> ${slave.db_path}
                    </div>
                    <div class="mb-3">
                        <strong>Letzte Synchronisation:</strong> ${lastSync}
                    </div>
                </div>
                <div class="card-footer d-flex justify-content-between">
                    <div>
                        <button class="btn btn-primary btn-sm me-2 sync-button" data-slave-id="${slave.id}">
                            <i class="bi bi-arrow-repeat"></i> Synchronisieren
                        </button>
                        <button class="btn btn-info btn-sm integrity-button" data-slave-id="${slave.id}">
                            <i class="bi bi-shield-check"></i> Integrität
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
}

// Debug-Funktion zum Laden des Dashboards
function debug_initDashboard() {
    console.log('Debug: Dashboard wird initialisiert...');
    
    // Container anzeigen
    const container = document.getElementById('slaves-container');
    console.log('Debug: slaves-container Element:', container);
    
    // Slaves laden
    debug_loadSlaves();
}

// Bei Seitenladung die Event-Listener hinzufügen
document.addEventListener('DOMContentLoaded', function() {
    console.log('Debug: DOMContentLoaded-Event ausgelöst');
});

// Füge direkte Event-Listener hinzu
window.addEventListener('load', function() {
    console.log('Debug: Event-Listener werden hinzugefügt');
    
    // Buttons für die Echtzeit-Synchronisation
    const startButtons = document.querySelectorAll('button');
    startButtons.forEach(button => {
        const text = button.textContent.trim();
        if (text.includes('Starten')) {
            console.log('Debug: Start-Button gefunden:', button);
            button.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                debug_startRealtimeSync();
                return false;
            };
        } else if (text.includes('Stoppen')) {
            console.log('Debug: Stop-Button gefunden:', button);
            button.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                debug_stopRealtimeSync();
                return false;
            };
        } else if (text.includes('Speicher')) {
            console.log('Debug: Speichern-Button gefunden:', button);
            button.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                debug_saveNewSlave();
                return false;
            };
        }
    });
});

// Debug-Funktion für die Integritätsprüfung
function debug_checkIntegrity(slaveId) {
    console.log('Debug: Integritätsprüfung für Slave', slaveId);
    
    fetch(`/api/slaves/${slaveId}/integrity`)
        .then(response => response.json())
        .then(data => {
            console.log('Debug: Integritätsprüfung Antwort:', data);
            
            if (data.status === 'success') {
                console.log('Debug: Integritätsprüfung erfolgreich');
                
                // Die Daten sind direkt im Hauptobjekt, nicht in data.result
                try {
                    const modalTitle = `Integritätsprüfung für Slave ${slaveId}`;
                    // Übergebe das data-Objekt direkt an die Render-Funktion
                    const modalBody = debug_renderIntegrityResult(data);
                    console.log('Debug: Modal-Body generiert');
                    showModal(modalTitle, modalBody);
                } catch (error) {
                    console.error('Debug: Fehler beim Rendern des Ergebnisses:', error);
                    alert('Fehler beim Rendern des Ergebnisses: ' + error.message);
                }
            } else {
                console.error('Debug: Fehler bei der Integritätsprüfung:', data.message);
                alert('Fehler bei der Integritätsprüfung: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Debug: Fetch-Fehler bei der Integritätsprüfung:', error);
            alert('Fehler bei der Integritätsprüfung: ' + error.message);
        });
}

// Debug-Version der renderIntegrityResult-Funktion
function debug_renderIntegrityResult(result) {
    console.log('Debug: Rendere Integritätsergebnis:', result);
    
    // Einfacheres HTML für Debugging-Zwecke
    let html = `
        <div class="p-3">
            <h4>Rohdaten der Integritätsprüfung:</h4>
            <pre style="background-color: #f5f5f5; padding: 15px; overflow: auto; max-height: 400px;">${JSON.stringify(result, null, 2)}</pre>
            
            <h4>Interpretierte Daten:</h4>
    `;
    
    // Gesamtstatus
    if (result.inconsistencies !== undefined) {
        html += `
            <div class="alert ${result.inconsistencies === 0 ? 'alert-success' : 'alert-danger'}">
                <strong>Gesamtergebnis:</strong> ${result.inconsistencies === 0 ? 'Keine Inkonsistenzen gefunden' : `${result.inconsistencies} Inkonsistenzen gefunden`}
            </div>
        `;
    }
    
    // Master/Slave Status
    if (result.master && result.slave) {
        html += `
            <div class="row mb-3">
                <div class="col-md-6">
                    <strong>Master-Datenbank:</strong> ${result.master.status || 'Status nicht verfügbar'}
                </div>
                <div class="col-md-6">
                    <strong>Slave-Datenbank:</strong> ${result.slave.status || 'Status nicht verfügbar'}
                </div>
            </div>
        `;
    }
    
    // Zähler für Tabellen und Zeilen
    if (result.tables_count !== undefined || result.rows_count !== undefined) {
        html += `
            <div class="row mb-3">
                <div class="col-md-6">
                    <strong>Tabellen:</strong> ${result.tables_count || 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Zeilen insgesamt:</strong> ${result.rows_count || 'N/A'}
                </div>
            </div>
        `;
    }
    
    // Tabellen-Vergleich
    if (result.details && typeof result.details === 'object') {
        html += `
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
        
        try {
            for (const [table, detail] of Object.entries(result.details)) {
                const statusClass = detail.difference === 0 ? 'success' : 'danger';
                
                html += `
                    <tr class="table-${statusClass}">
                        <td>${table}</td>
                        <td>${detail.master_count !== undefined ? detail.master_count : 'N/A'}</td>
                        <td>${detail.slave_count !== undefined ? detail.slave_count : 'N/A'}</td>
                        <td>${detail.difference !== undefined ? detail.difference : 'N/A'}</td>
                        <td>${detail.difference === 0 ? 'Übereinstimmend' : 'Unterschiedlich'}</td>
                    </tr>
                `;
            }
        } catch (error) {
            console.error('Debug: Fehler beim Rendern der Tabellen:', error);
            html += `
                <tr>
                    <td colspan="5">Fehler beim Rendern der Tabellen: ${error.message}</td>
                </tr>
            `;
        }
        
        html += `
                </tbody>
            </table>
        `;
    }
    
    html += `</div>`;
    
    console.log('Debug: HTML-Ausgabe generiert');
    return html;
}

// Bei Seitenladung Event-Listener für Integritäts-Buttons hinzufügen
window.addEventListener('load', function() {
    console.log('Debug: Event-Listener für Integritäts-Buttons werden hinzugefügt');
    
    setTimeout(function() {
        document.querySelectorAll('.integrity-button').forEach(button => {
            console.log('Debug: Integritäts-Button gefunden:', button);
            const slaveId = button.getAttribute('data-slave-id');
            if (slaveId) {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Debug: Integritäts-Button geklickt für Slave', slaveId);
                    debug_checkIntegrity(slaveId);
                    return false;
                });
            }
        });
    }, 1000); // Verzögerung, um sicherzustellen, dass die Buttons geladen sind
});

// Funktion zum Anzeigen des Modals (Kopie aus dashboard.js, falls nicht global definiert)
function showModal(title, body) {
    console.log('Debug: Modal wird angezeigt:', title);
    
    const modalId = 'dynamicModal';
    let modal = document.getElementById(modalId);
    
    if (!modal) {
        // Modal erstellen, wenn es nicht existiert
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
        console.log('Debug: Neues Modal erstellt');
    }
    
    // Modal-Inhalte aktualisieren
    modal.querySelector('.modal-title').textContent = title;
    modal.querySelector('.modal-body').innerHTML = body;
    
    // Modal anzeigen
    try {
        const bsModal = new bootstrap.Modal(modal);
        
        // Event-Listener für das Entfernen des Backdrops und Aufräumen nach dem Schließen
        modal.addEventListener('hidden.bs.modal', function() {
            console.log('Debug: Modal wurde geschlossen');
            
            // Backdrop manuell entfernen falls vorhanden
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                console.log('Debug: Entferne Modal-Backdrop');
                backdrop.remove();
            }
            
            // Scrolling wieder aktivieren
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
            
            // Optionales Aufräumen - Modal aus dem DOM entfernen wenn nicht mehr benötigt
            // modal.remove();
        }, { once: true }); // Event nur einmal ausführen
        
        bsModal.show();
        console.log('Debug: Modal angezeigt');
    } catch (error) {
        console.error('Debug: Fehler beim Anzeigen des Modals:', error);
        alert('Fehler beim Anzeigen des Modals: ' + error.message);
    }
}

// Debug-Funktion für das Laden verfügbarer Tabellen
function debug_loadAvailableTables() {
    console.log('Debug: Lade verfügbare Tabellen...');
    
    const tablesContainer = document.getElementById('availableTablesContainer');
    const tablesList = document.getElementById('availableTables');
    
    if (!tablesContainer || !tablesList) {
        console.error('Debug: Container-Elemente für Tabellen nicht gefunden!');
        alert('Fehler: Container-Elemente für Tabellen nicht gefunden!');
        return;
    }
    
    // Visuelles Feedback, dass die Aktion läuft
    const loadTablesBtn = document.querySelector('#loadTablesBtn');
    if (loadTablesBtn) {
        loadTablesBtn.disabled = true;
        loadTablesBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Lade...';
    }
    
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
                    checkbox.addEventListener('change', debug_updateIgnoredTablesInput);
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
            if (loadTablesBtn) {
                loadTablesBtn.disabled = false;
                loadTablesBtn.innerHTML = 'Verfügbare Tabellen laden';
            }
        });
}

// Debug-Funktion für das Aktualisieren der ignorierten Tabellen
function debug_updateIgnoredTablesInput() {
    console.log('Debug: Aktualisiere ignorierte Tabellen...');
    
    const ignoredTablesInput = document.getElementById('ignoredTables');
    if (!ignoredTablesInput) {
        console.error('Debug: ignoredTables Input nicht gefunden!');
        return;
    }
    
    const checkedTables = Array.from(document.querySelectorAll('.table-checkbox:checked'))
        .map(checkbox => checkbox.value);
    
    console.log('Debug: Ausgewählte Tabellen:', checkedTables);
    ignoredTablesInput.value = checkedTables.join(',');
}

// Event-Listener für den "Verfügbare Tabellen laden" Button hinzufügen
window.addEventListener('load', function() {
    console.log('Debug: Füge Event-Listener für loadTablesBtn hinzu');
    setTimeout(function() {
        const loadTablesBtn = document.getElementById('loadTablesBtn');
        if (loadTablesBtn) {
            console.log('Debug: loadTablesBtn gefunden, füge Event-Listener hinzu');
            loadTablesBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Debug: loadTablesBtn wurde geklickt!');
                debug_loadAvailableTables();
                return false;
            });
        } else {
            console.error('Debug: loadTablesBtn nicht gefunden!');
        }
    }, 1000); // Verzögerung, um sicherzustellen, dass das DOM vollständig geladen ist
});

// Event-Listener für den "Speichern" Button hinzufügen
window.addEventListener('load', function() {
    console.log('Debug: Füge Event-Listener für saveSlaveBtn hinzu');
    setTimeout(function() {
        const saveSlaveBtn = document.getElementById('saveSlaveBtn');
        if (saveSlaveBtn) {
            console.log('Debug: saveSlaveBtn gefunden, füge Event-Listener hinzu');
            saveSlaveBtn.addEventListener('click', function(e) {
                console.log('Debug: saveSlaveBtn wurde geklickt!');
                
                // Die originale Funktion debug_saveNewSlave() verwenden
                debug_saveNewSlave();
            });
        } else {
            console.error('Debug: saveSlaveBtn nicht gefunden!');
        }
    }, 1000); // Verzögerung, um sicherzustellen, dass das DOM vollständig geladen ist
}); 