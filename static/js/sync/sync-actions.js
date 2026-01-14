// ==========================================
// SYNC ACTIONS - All Sync Operations
// ==========================================
/*
================================================================================
DEVELOPER NOTES
================================================================================
File: sync-actions.js
Purpose: Handle all sync operations (Full, Incremental, Delete)

FUNCTIONS:
----------
1. syncCompanyFull(name) - Full sync for SYNCED company (with confirmation)
2. incrementalSyncCompany(name) - Incremental sync (changes only)
3. resyncCompany(name) - Re-sync all data (alias for full sync)
4. deleteCompany(name) - Delete company from database
5. syncCompany(name) - Sync NEW company (first time)
6. startSync(type) - Batch sync for selected companies

SYNC TYPES:
-----------
FULL SYNC:
- Deletes ALL existing data for company
- Fetches fresh data from Tally
- Use when: Data corruption, major changes, first sync

INCREMENTAL SYNC:
- Compares alter_id with last sync
- Only fetches changed/new records
- Use when: Regular updates, faster sync

BUSINESS LOGIC:
---------------
- Full sync shows warning confirmation (data will be deleted)
- Period (from_date, to_date) passed to API for filtering
- After sync starts, polling begins via syncInterval
- On completion, both company lists are refreshed

API ENDPOINTS:
--------------
- POST /api/sync/full?company=X&from_date=Y&to_date=Z
- POST /api/sync/incremental?company=X&from_date=Y&to_date=Z
- DELETE /api/data/company/{name}

DEPENDENCIES:
-------------
- Uses: apiCall(), showToast() (from common.js)
- Uses: companyPeriods, syncInterval (from sync-core.js)
- Uses: showSyncProgress(), showCircularProgress() (from sync-progress.js)
- Uses: window.syncedCompaniesData (set by sync-companies.js)
================================================================================
*/

// Full Sync for synced company
async function syncCompanyFull(companyName) {
    // Get stored period for this company
    const companyData = window.syncedCompaniesData?.[companyName] || {};
    const fromDate = companyData.books_from || '';
    const toDate = companyData.books_to || '';
    
    const periodInfo = fromDate ? `\nPeriod: ${formatDateDisplay(fromDate)} to ${formatDateDisplay(toDate)}` : '\nPeriod: Auto-detect from Tally';
    
    if (!confirm(`⚠️ Full Sync for ${companyName}\n\nWarning: Existing data will be DELETED and fresh data will be synced from Tally.${periodInfo}\n\nMake sure "${companyName}" is selected in Tally before proceeding.\n\nAre you sure you want to continue?`)) return;
    
    showToast(`Starting Full Sync for ${companyName}...`, 'info');
    showSyncProgress(companyName);
    showCircularProgress(companyName);
    
    try {
        // Use stored period or let backend auto-detect
        let endpoint = `/api/sync/full?company=${encodeURIComponent(companyName)}`;
        if (fromDate && toDate) {
            endpoint += `&from_date=${fromDate}&to_date=${toDate}`;
        }
        
        await apiCall(endpoint, { method: 'POST' });
        showToast('Full Sync started!', 'success');
        syncInterval = setInterval(updateSyncStatus, 1000);
    } catch (error) {
        showToast(`Sync failed: ${error.message}`, 'error');
        hideSyncProgress();
    }
}

// Incremental Sync for synced company
async function incrementalSyncCompany(companyName) {
    // Get stored period for this company
    const companyData = window.syncedCompaniesData?.[companyName];
    const fromDate = companyData?.books_from || '';
    const toDate = companyData?.books_to || '';
    
    let periodInfo = 'Auto-detect from Tally';
    if (fromDate && toDate) {
        periodInfo = `${formatDate(fromDate)} to ${formatDate(toDate)}`;
    }
    
    showToast(`Starting Incremental Sync for ${companyName}...`, 'info');
    showSyncProgress(companyName);
    showCircularProgress(companyName);
    
    try {
        let url = `/api/sync/incremental?company=${encodeURIComponent(companyName)}`;
        if (fromDate) url += `&from_date=${fromDate}`;
        if (toDate) url += `&to_date=${toDate}`;
        
        await apiCall(url, { method: 'POST' });
        showToast('Incremental Sync started!', 'success');
        syncInterval = setInterval(updateSyncStatus, 1000);
    } catch (error) {
        showToast(`Sync failed: ${error.message}`, 'error');
        hideSyncProgress();
    }
}

// Re-sync all data for company
async function resyncCompany(companyName) {
    // Get stored period for this company
    const companyData = window.syncedCompaniesData?.[companyName];
    const fromDate = companyData?.books_from || '';
    const toDate = companyData?.books_to || '';
    
    let periodInfo = 'Auto-detect from Tally';
    if (fromDate && toDate) {
        periodInfo = `${formatDate(fromDate)} to ${formatDate(toDate)}`;
    }
    
    if (!confirm(`Re-sync ALL data for ${companyName}?\n\nThis will delete existing data and sync fresh.\nPeriod: ${periodInfo}\n\nMake sure "${companyName}" is selected in Tally.`)) return;
    
    showToast(`Re-syncing ${companyName}...`, 'info');
    showSyncProgress(companyName);
    showCircularProgress(companyName);
    
    try {
        let url = `/api/sync/full?company=${encodeURIComponent(companyName)}`;
        if (fromDate) url += `&from_date=${fromDate}`;
        if (toDate) url += `&to_date=${toDate}`;
        
        await apiCall(url, { method: 'POST' });
        showToast('Re-sync started!', 'success');
        syncInterval = setInterval(updateSyncStatus, 1000);
    } catch (error) {
        showToast(`Re-sync failed: ${error.message}`, 'error');
        hideSyncProgress();
    }
}

// Delete Company
async function deleteCompany(companyName) {
    if (!confirm(`⚠️ Delete "${companyName}"?\n\nThis will permanently delete ALL synced data for this company from the database.\n\nThis action cannot be undone.\n\nAre you sure?`)) return;
    
    try {
        await apiCall(`/api/data/company/${encodeURIComponent(companyName)}`, { method: 'DELETE' });
        showToast(`Company "${companyName}" deleted successfully`, 'success');
        loadSyncedCompanies();
        loadCompanies();
    } catch (error) {
        showToast(`Delete failed: ${error.message}`, 'error');
    }
}

// Sync single company (Full Sync for NEW company)
async function syncCompany(companyName) {
    const period = companyPeriods[companyName];
    showCircularProgress(companyName);
    
    try {
        let endpoint = `/api/sync/full?company=${encodeURIComponent(companyName)}`;
        if (period) {
            endpoint += `&from_date=${period.from}&to_date=${period.to}`;
        }
        
        await apiCall(endpoint, { method: 'POST' });
        showToast(`Full sync started for ${companyName}`, 'success');
        
        // Start polling for status
        syncInterval = setInterval(updateSyncStatus, 1000);
    } catch (error) {
        showToast(`Sync failed: ${error.message}`, 'error');
        hideCircularProgress();
    }
}

// Start Sync for selected companies
async function startSync(type) {
    if (selectedCompanies.length === 0) {
        showToast('Please select at least one company', 'warning');
        return;
    }
    
    try {
        for (const company of selectedCompanies) {
            showCircularProgress(company);
            const period = companyPeriods[company];
            let endpoint = `/api/sync/full?company=${encodeURIComponent(company)}`;
            if (period) {
                endpoint += `&from_date=${period.from}&to_date=${period.to}`;
            }
            
            await apiCall(endpoint, { method: 'POST' });
            showToast(`Full sync started for ${company}`, 'success');
        }
        
        // Start polling for status
        syncInterval = setInterval(updateSyncStatus, 1000);
    } catch (error) {
        showToast(`Sync failed: ${error.message}`, 'error');
        hideCircularProgress();
    }
}
