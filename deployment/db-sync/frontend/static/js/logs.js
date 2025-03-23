/**
 * SQLite-Datenbanksynchronisierung Frontend
 * 
 * JavaScript für die Logs-Seite
 */

document.addEventListener('DOMContentLoaded', function() {
    // Socket.io-Verbindung initialisieren
    const socket = io();
    
    // DOM-Elemente
    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    const clearLogsBtn = document.getElementById('clearLogsBtn');
    const slaveFilter = document.getElementById('slaveFilter');
    const statusFilter = document.getElementById('statusFilter');
    const dateFilter = document.getElementById('dateFilter');
    const limitFilter = document.getElementById('limitFilter');
    const logsTableBody = document.getElementById('logsTableBody');
    const logsPagination = document.getElementById('logsPagination');
    const logsCount = document.getElementById('logsCount');
    
    // Zustandsvariablen
    let currentPage = 1;
    let totalLogs = 0;
    let logsPerPage = parseInt(limitFilter.value);
    let slaves = [];
    
    // Event-Listener
    refreshLogsBtn.addEventListener('click', loadLogs);
    clearLogsBtn.addEventListener('click', confirmClearLogs);
    slaveFilter.addEventListener('change', loadLogs);
    statusFilter.addEventListener('change', loadLogs);
    dateFilter.addEventListener('change', loadLogs);
    limitFilter.addEventListener('change', function() {
        logsPerPage = parseInt(this.value);
        currentPage = 1;
        loadLogs();
    });
    
    // Socket.io Event-Listener für Echtzeit-Updates
    socket.on('log_update', function() {
        loadLogs();
    });
    
    // Initialisierung
    loadSlaves()
        .then(() => loadLogs());
    
    /**
     * Lädt die Liste der Slaves für den Filter
     */
    function loadSlaves() {
        return fetch('/api/slaves')
            .then(response => response.json())
            .then(data => {
                if (data.slaves && data.slaves.length > 0) {
                    slaves = data.slaves;
                    
                    // Slave-Filter aktualisieren
                    slaveFilter.innerHTML = '<option value="all">Alle Slaves</option>';
                    slaves.forEach(slave => {
                        const option = document.createElement('option');
                        option.value = slave.id;
                        option.textContent = slave.name;
                        slaveFilter.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Fehler beim Laden der Slaves:', error);
                showNotification('Fehler beim Laden der Slaves', 'danger');
            });
    }
    
    /**
     * Lädt die Logs basierend auf den aktuellen Filtern
     */
    function loadLogs() {
        // Lade-Anzeige
        logsTableBody.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Wird geladen...</span></div></td></tr>';
        
        // Filter-Parameter erstellen
        const params = new URLSearchParams();
        
        if (slaveFilter.value !== 'all') {
            params.set('slave_id', slaveFilter.value);
        }
        
        // Abhängig vom Datumsfilter das entsprechende Datum berechnen
        if (dateFilter.value !== 'all') {
            const now = new Date();
            let fromDate = new Date();
            
            if (dateFilter.value === 'today') {
                fromDate.setHours(0, 0, 0, 0);
            } else if (dateFilter.value === 'yesterday') {
                fromDate.setDate(fromDate.getDate() - 1);
                fromDate.setHours(0, 0, 0, 0);
            } else if (dateFilter.value === 'last7days') {
                fromDate.setDate(fromDate.getDate() - 7);
            } else if (dateFilter.value === 'last30days') {
                fromDate.setDate(fromDate.getDate() - 30);
            }
            
            params.set('from_date', fromDate.toISOString());
        }
        
        // Berücksichtige Status-Filter
        if (statusFilter.value !== 'all') {
            params.set('status', statusFilter.value);
        }
        
        // Pagination und Limit
        params.set('limit', limitFilter.value);
        params.set('page', currentPage.toString());
        
        // Logs von der API laden
        fetch(`/api/logs?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                updateLogsTable(data.logs || []);
                totalLogs = data.total_count || data.logs.length;
                logsCount.textContent = totalLogs;
                
                // Pagination aktualisieren
                updatePagination();
            })
            .catch(error => {
                console.error('Fehler beim Laden der Logs:', error);
                showNotification('Fehler beim Laden der Logs', 'danger');
                logsTableBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Fehler beim Laden der Logs</td></tr>';
            });
    }
    
    /**
     * Aktualisiert die Logs-Tabelle mit den geladenen Daten
     */
    function updateLogsTable(logs) {
        logsTableBody.innerHTML = '';
        
        if (logs.length === 0) {
            const emptyRow = document.createElement('tr');
            const emptyCell = document.createElement('td');
            emptyCell.colSpan = 6;
            emptyCell.className = 'text-center';
            emptyCell.textContent = 'Keine Logs gefunden';
            emptyRow.appendChild(emptyCell);
            logsTableBody.appendChild(emptyRow);
            return;
        }
        
        logs.forEach(log => {
            const row = document.createElement('tr');
            row.style.cursor = 'pointer';
            row.addEventListener('click', () => showLogDetails(log));
            
            // Zeitstempel
            const timestampCell = document.createElement('td');
            timestampCell.textContent = formatDateTime(log.created_at || log.timestamp);
            row.appendChild(timestampCell);
            
            // Slave
            const slaveCell = document.createElement('td');
            slaveCell.textContent = getSlaveNameById(log.slave_id);
            row.appendChild(slaveCell);
            
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
            messageCell.className = 'text-truncate';
            messageCell.style.maxWidth = '300px';
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
    }
    
    /**
     * Findet den Namen eines Slaves anhand seiner ID
     */
    function getSlaveNameById(slaveId) {
        const slave = slaves.find(s => s.id == slaveId);
        return slave ? slave.name : `Slave ${slaveId}`;
    }
    
    /**
     * Aktualisiert die Paginierung
     */
    function updatePagination() {
        logsPagination.innerHTML = '';
        
        if (totalLogs <= logsPerPage) {
            return;
        }
        
        const pageCount = Math.ceil(totalLogs / logsPerPage);
        
        // Vorherige Seite
        const prevItem = document.createElement('li');
        prevItem.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        
        const prevLink = document.createElement('a');
        prevLink.className = 'page-link';
        prevLink.href = '#';
        prevLink.innerHTML = '&laquo;';
        prevLink.addEventListener('click', function(e) {
            e.preventDefault();
            if (currentPage > 1) {
                currentPage--;
                loadLogs();
            }
        });
        
        prevItem.appendChild(prevLink);
        logsPagination.appendChild(prevItem);
        
        // Seitenzahlen
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(pageCount, startPage + 4);
        
        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const pageItem = document.createElement('li');
            pageItem.className = `page-item ${i === currentPage ? 'active' : ''}`;
            
            const pageLink = document.createElement('a');
            pageLink.className = 'page-link';
            pageLink.href = '#';
            pageLink.textContent = i;
            pageLink.addEventListener('click', function(e) {
                e.preventDefault();
                currentPage = i;
                loadLogs();
            });
            
            pageItem.appendChild(pageLink);
            logsPagination.appendChild(pageItem);
        }
        
        // Nächste Seite
        const nextItem = document.createElement('li');
        nextItem.className = `page-item ${currentPage === pageCount ? 'disabled' : ''}`;
        
        const nextLink = document.createElement('a');
        nextLink.className = 'page-link';
        nextLink.href = '#';
        nextLink.innerHTML = '&raquo;';
        nextLink.addEventListener('click', function(e) {
            e.preventDefault();
            if (currentPage < pageCount) {
                currentPage++;
                loadLogs();
            }
        });
        
        nextItem.appendChild(nextLink);
        logsPagination.appendChild(nextItem);
    }
    
    /**
     * Zeigt die Details eines Logs in einem Modal an
     */
    function showLogDetails(log) {
        // Modal-Elemente aktualisieren
        document.getElementById('logDetailSlave').textContent = getSlaveNameById(log.slave_id);
        document.getElementById('logDetailTimestamp').textContent = formatDateTime(log.created_at || log.timestamp);
        
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
        document.getElementById('logDetailStatus').innerHTML = statusBadge;
        
        document.getElementById('logDetailMessage').textContent = log.message || '-';
        document.getElementById('logDetailChanges').textContent = log.changes_count || '0';
        document.getElementById('logDetailDuration').textContent = `${log.duration ? log.duration.toFixed(2) : '0.00'} Sekunden`;
        
        // Modal anzeigen
        const modal = new bootstrap.Modal(document.getElementById('logDetailsModal'));
        modal.show();
    }
    
    /**
     * Fragt nach Bestätigung zum Löschen der Logs
     */
    function confirmClearLogs() {
        if (confirm('Möchten Sie wirklich alle Logs löschen? Diese Aktion kann nicht rückgängig gemacht werden.')) {
            clearLogs();
        }
    }
    
    /**
     * Löscht alle Logs
     */
    function clearLogs() {
        clearLogsBtn.disabled = true;
        
        fetch('/api/logs/clear', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Logs erfolgreich gelöscht', 'success');
                loadLogs();
            } else {
                showNotification(`Fehler: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Fehler beim Löschen der Logs:', error);
            showNotification('Fehler beim Löschen der Logs', 'danger');
        })
        .finally(() => {
            clearLogsBtn.disabled = false;
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
        if (!dateTimeStr) return 'Nicht angegeben';
        
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