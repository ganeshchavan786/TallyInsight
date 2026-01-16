// ==========================================
// SYNC SCHEDULE - Auto Sync Schedule Functions
// ==========================================
/*
================================================================================
DEVELOPER NOTES
================================================================================
File: sync-schedule.js
Purpose: Handle auto sync scheduling (Sync Options tab)

FUNCTIONS:
----------
1. setSyncInterval(minutes) - Set sync interval (5/15/30/60 min)
2. saveScheduleSettings() - Save settings to localStorage
3. loadScheduleSettings() - Load settings from localStorage
4. updateAutoSyncStatus(enabled) - Update UI status text
5. startAutoSync() - Start auto sync timer
6. stopAutoSync() - Stop auto sync timer
7. toggleAutoSync() - Toggle auto sync on/off

AUTO SYNC FLOW:
---------------
1. User selects interval (5/15/30/60 minutes)
2. User enables Auto Sync toggle
3. saveScheduleSettings() saves to localStorage
4. startAutoSync() creates setInterval with selected interval
5. On each interval: Runs incremental sync for ALL synced companies
6. User can disable anytime with toggle

STORAGE:
--------
- localStorage.syncIntervalMinutes: Selected interval
- localStorage.autoSyncEnabled: true/false

BUSINESS LOGIC:
---------------
- Auto sync runs INCREMENTAL sync (not full) to minimize load
- Syncs ALL companies in sync_companies table
- Continues running even after page refresh (if enabled)

DEPENDENCIES:
-------------
- Uses: apiCall(), showToast() (from common.js)
- Uses: syncIntervalMinutes, autoSyncTimer (from sync-core.js)
- Uses: updateSyncStatus() (from sync-progress.js)
================================================================================
*/

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
    
    // For testing: Use 5 minutes (300000ms) regardless of UI selection
    // TODO: Remove this override after testing
    const intervalMs = 5 * 60 * 1000; // 5 minutes for testing
    // const intervalMs = syncIntervalMinutes * 60 * 1000;
    
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
