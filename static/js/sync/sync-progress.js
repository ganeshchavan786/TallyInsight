// ==========================================
// SYNC PROGRESS - Progress UI & Status Updates
// ==========================================
/*
================================================================================
DEVELOPER NOTES
================================================================================
File: sync-progress.js
Purpose: Handle sync progress UI and real-time status updates

FUNCTIONS:
----------
1. showSyncProgress(companyName) - Initialize progress tracking
2. hideSyncProgress() - Clear interval and hide progress
3. updateSyncStatus() - Poll /api/sync/status every 1 second
4. showCircularProgress(companyName) - Show circular progress indicator
5. hideCircularProgress() - Hide all progress indicators
6. updateCircularProgress(companyName, percent) - Update progress percentage

SYNC STATUS FLOW:
-----------------
1. User clicks Sync button
2. showCircularProgress() shows spinner on that company
3. setInterval calls updateSyncStatus() every 1 second
4. updateSyncStatus() calls /api/sync/status API
5. API returns: {status, progress, current_table, company}
6. updateCircularProgress() updates the percentage
7. When status='completed' or 'error', hideSyncProgress() clears interval

CIRCULAR PROGRESS:
------------------
- SVG circle with stroke-dashoffset animation
- Circumference = 2 * PI * radius = 125.66
- Offset = circumference - (percent/100 * circumference)

DEPENDENCIES:
-------------
- Uses: apiCall() (from common.js)
- Uses: syncInterval (from sync-core.js)
- Uses: loadCompanies(), loadSyncedCompanies() (from sync-companies.js)
================================================================================
*/

// Show Sync Progress (now only updates hidden elements for status tracking)
function showSyncProgress(companyName) {
    // Hidden elements for status tracking only
    const progressTitle = document.getElementById('progress-title');
    if (progressTitle) progressTitle.textContent = `Syncing ${companyName}...`;
}

// Hide Sync Progress
function hideSyncProgress() {
    if (syncInterval) {
        clearInterval(syncInterval);
        syncInterval = null;
    }
}

// Update Sync Status
async function updateSyncStatus() {
    try {
        const status = await apiCall('/api/sync/status');
        
        if (status.status === 'idle' || status.status === 'completed') {
            hideSyncProgress();
            hideCircularProgress();
            
            if (status.status === 'completed') {
                showToast('Sync completed successfully!', 'success');
                loadCompanies();
                loadSyncedCompanies();
            }
            return;
        }
        
        if (status.status === 'error') {
            hideSyncProgress();
            hideCircularProgress();
            showToast(`Sync error: ${status.error || 'Unknown error'}`, 'error');
            return;
        }
        
        // Update progress
        const percent = status.progress || 0;
        updateCircularProgress(status.current_company, percent);
        
        // Update hidden elements
        const progressPercent = document.getElementById('progress-percent');
        const currentTable = document.getElementById('current-table');
        const rowsProcessed = document.getElementById('rows-processed');
        
        if (progressPercent) progressPercent.textContent = `${percent}%`;
        if (currentTable) currentTable.textContent = status.current_table || '';
        if (rowsProcessed) rowsProcessed.textContent = status.rows_processed || '';
        
    } catch (error) {
        console.error('Status check failed:', error);
    }
}

// Show Circular Progress for a company
function showCircularProgress(companyName) {
    const companyId = companyName.replace(/[^a-zA-Z0-9]/g, '_');
    
    // Try synced company progress
    let progress = document.getElementById(`progress-${companyId}`);
    if (progress) {
        progress.style.display = 'flex';
        return;
    }
    
    // Try new company progress
    progress = document.getElementById(`new-progress-${companyId}`);
    if (progress) {
        progress.style.display = 'flex';
    }
}

// Hide all circular progress indicators
function hideCircularProgress() {
    document.querySelectorAll('.circular-progress').forEach(p => {
        p.style.display = 'none';
        const text = p.querySelector('.progress-text');
        if (text) text.textContent = '0%';
        const bar = p.querySelector('.progress-bar');
        if (bar) bar.style.strokeDashoffset = '125.66';
    });
}

// Update Circular Progress
function updateCircularProgress(companyName, percent) {
    if (!companyName) return;
    
    const companyId = companyName.replace(/[^a-zA-Z0-9]/g, '_');
    
    // Try both progress elements
    let progress = document.getElementById(`progress-${companyId}`) || 
                   document.getElementById(`new-progress-${companyId}`);
    
    if (progress) {
        // Ensure progress is visible
        progress.style.display = 'flex';
        
        const text = progress.querySelector('.progress-text');
        const bar = progress.querySelector('.progress-bar');
        
        if (text) text.textContent = `${Math.round(percent)}%`;
        if (bar) {
            // Circle circumference = 2 * PI * r = 2 * 3.14159 * 20 = 125.66
            const circumference = 125.66;
            const offset = circumference - (percent / 100) * circumference;
            bar.style.strokeDashoffset = offset;
        }
    }
}
