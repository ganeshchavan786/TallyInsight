// ==========================================
// SYNC PROGRESS - Progress UI & Status Updates
// ==========================================

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
        updateCircularProgress(status.company, percent);
        
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
        if (bar) bar.style.strokeDashoffset = '126';
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
