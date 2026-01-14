// ==========================================
// SYNC SCHEDULE - Auto Sync Schedule Functions
// ==========================================

// Set Sync Interval
function setSyncInterval(minutes) {
    syncIntervalMinutes = minutes;
    localStorage.setItem('syncIntervalMinutes', minutes);
    showToast(`Sync interval set to ${minutes} minutes`, 'success');
}

// Save Schedule Settings
async function saveScheduleSettings() {
    const autoSyncEnabled = document.getElementById('auto-sync-toggle')?.checked || false;
    
    localStorage.setItem('autoSyncEnabled', autoSyncEnabled);
    localStorage.setItem('syncIntervalMinutes', syncIntervalMinutes);
    
    if (autoSyncEnabled) {
        startAutoSync();
    } else {
        stopAutoSync();
    }
    
    updateAutoSyncStatus(autoSyncEnabled);
    showToast('Schedule settings saved', 'success');
}

// Load Schedule Settings
function loadScheduleSettings() {
    const savedInterval = localStorage.getItem('syncIntervalMinutes');
    if (savedInterval) {
        syncIntervalMinutes = parseInt(savedInterval);
        const radioBtn = document.querySelector(`input[name="sync-interval"][value="${syncIntervalMinutes}"]`);
        if (radioBtn) radioBtn.checked = true;
    }
    
    const autoSyncEnabled = localStorage.getItem('autoSyncEnabled') === 'true';
    const autoSyncToggle = document.getElementById('auto-sync-toggle');
    if (autoSyncToggle) {
        autoSyncToggle.checked = autoSyncEnabled;
    }
    
    updateAutoSyncStatus(autoSyncEnabled);
}

// Update Auto Sync Status Display
function updateAutoSyncStatus(enabled) {
    const statusText = document.getElementById('auto-sync-status');
    if (statusText) {
        statusText.textContent = enabled ? 'Auto Sync: ON' : 'Auto Sync: OFF';
        statusText.className = enabled ? 'auto-sync-on' : 'auto-sync-off';
    }
}

// Start Auto Sync
function startAutoSync() {
    if (autoSyncTimer) {
        clearInterval(autoSyncTimer);
    }
    
    const intervalMs = syncIntervalMinutes * 60 * 1000;
    
    autoSyncTimer = setInterval(async () => {
        console.log('Auto sync triggered');
        
        // Get all synced companies and run incremental sync
        try {
            const syncedCompanies = await apiCall('/api/data/synced-companies');
            
            if (syncedCompanies.companies && syncedCompanies.companies.length > 0) {
                for (const company of syncedCompanies.companies) {
                    const companyName = company.company_name;
                    const fromDate = company.books_from || '';
                    const toDate = company.books_to || '';
                    
                    let url = `/api/sync/incremental?company=${encodeURIComponent(companyName)}`;
                    if (fromDate) url += `&from_date=${fromDate}`;
                    if (toDate) url += `&to_date=${toDate}`;
                    
                    await apiCall(url, { method: 'POST' });
                    showToast(`Auto sync started for ${companyName}`, 'info');
                }
                
                // Start status polling
                syncInterval = setInterval(updateSyncStatus, 1000);
            }
        } catch (error) {
            console.error('Auto sync failed:', error);
            showToast(`Auto sync failed: ${error.message}`, 'error');
        }
    }, intervalMs);
    
    console.log(`Auto sync started with interval: ${syncIntervalMinutes} minutes`);
}

// Stop Auto Sync
function stopAutoSync() {
    if (autoSyncTimer) {
        clearInterval(autoSyncTimer);
        autoSyncTimer = null;
        console.log('Auto sync stopped');
    }
}

// Toggle Auto Sync
function toggleAutoSync() {
    const autoSyncToggle = document.getElementById('auto-sync-toggle');
    const enabled = autoSyncToggle?.checked || false;
    
    localStorage.setItem('autoSyncEnabled', enabled);
    updateAutoSyncStatus(enabled);
    
    if (enabled) {
        startAutoSync();
        showToast('Auto sync enabled', 'success');
    } else {
        stopAutoSync();
        showToast('Auto sync disabled', 'info');
    }
}
