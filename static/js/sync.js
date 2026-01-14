// Sync Page JavaScript

let selectedCompanies = [];
let syncInterval = null;
let companyPeriods = {}; // Store period for each company
let autoSyncTimer = null;
let syncIntervalMinutes = 60; // Default 1 hour

// Tab Switching
function switchTab(tabName) {
    // Remove active from all tabs
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    // Activate selected tab
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // Load tab-specific data
    if (tabName === 'tally-config') {
        loadTallyConfig();
    }
}

// Load Synced Companies - Show already synced companies with Dashboard/Audit links
async function loadSyncedCompanies() {
    const list = document.getElementById('synced-company-list');
    if (!list) return;
    
    list.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
    
    try {
        const syncedCompanies = await apiCall('/api/data/synced-companies');
        
        if (!syncedCompanies.companies || syncedCompanies.companies.length === 0) {
            list.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>No synced companies yet</p><p class="text-muted">Sync a company to see it here</p></div>';
            return;
        }
        
        // Store synced companies data globally for sync functions
        window.syncedCompaniesData = {};
        
        list.innerHTML = syncedCompanies.companies.map(company => {
            const lastSync = company.last_sync_at ? formatDateTimeShort(company.last_sync_at) : 'Never';
            const syncCount = company.sync_count || 0;
            const companyId = company.company_name.replace(/[^a-zA-Z0-9]/g, '_');
            const booksFrom = company.books_from || '';
            const booksTo = company.books_to || '';
            
            // Store period for sync functions
            window.syncedCompaniesData[company.company_name] = {
                books_from: booksFrom,
                books_to: booksTo
            };
            
            return `
                <div class="synced-company-item" id="synced-${companyId}" onclick="goToCompanyDashboard('${company.company_name}')">
                    <div class="synced-company-info">
                        <div class="synced-company-name">${company.company_name}</div>
                        <div class="synced-company-meta">
                            <span><i class="fas fa-sync"></i> ${syncCount} syncs</span>
                            <span><i class="fas fa-clock"></i> ${lastSync}</span>
                            ${booksFrom ? `<span><i class="fas fa-calendar"></i> ${formatDateDisplay(booksFrom)} - ${formatDateDisplay(booksTo)}</span>` : ''}
                        </div>
                    </div>
                    <div class="synced-company-actions">
                        <div class="circular-progress" id="progress-${companyId}" style="display: none;" onclick="event.stopPropagation();">
                            <svg viewBox="0 0 44 44">
                                <circle class="progress-bg" cx="22" cy="22" r="20"></circle>
                                <circle class="progress-bar" cx="22" cy="22" r="20"></circle>
                            </svg>
                            <span class="progress-text">0%</span>
                        </div>
                        <button class="btn btn-sm btn-outline" onclick="event.stopPropagation(); goToCompanyDashboard('${company.company_name}')" title="Dashboard">
                            <i class="fas fa-chart-bar"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="event.stopPropagation(); goToCompanyAudit('${company.company_name}')" title="Audit">
                            <i class="fas fa-history"></i>
                        </button>
                        <button class="btn btn-sm btn-success" onclick="event.stopPropagation(); syncCompanyFull('${company.company_name}')" title="Full Sync">
                            <i class="fas fa-sync"></i>
                        </button>
                        <div class="dropdown" onclick="event.stopPropagation();">
                            <button class="btn btn-sm btn-outline dropdown-toggle" onclick="toggleDropdown('${companyId}')">
                                <i class="fas fa-ellipsis-v"></i>
                            </button>
                            <div class="dropdown-menu" id="dropdown-${companyId}">
                                <a class="dropdown-item" onclick="closeAllDropdowns(); incrementalSyncCompany('${company.company_name}')">
                                    <i class="fas fa-bolt"></i> Incremental Sync
                                </a>
                                <a class="dropdown-item" onclick="closeAllDropdowns(); resyncCompany('${company.company_name}')">
                                    <i class="fas fa-redo"></i> Re-sync All Data
                                </a>
                                <div class="dropdown-divider"></div>
                                <a class="dropdown-item text-danger" onclick="closeAllDropdowns(); deleteCompany('${company.company_name}')">
                                    <i class="fas fa-trash"></i> Delete Company
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        list.innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Error: ${error.message}</p></div>`;
    }
}

// Format date time short
function formatDateTimeShort(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) + ' ' + 
           date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

// Go to Company Dashboard
function goToCompanyDashboard(companyName) {
    window.location.href = `dashboard.html?company=${encodeURIComponent(companyName)}`;
}

// Go to Company Audit
function goToCompanyAudit(companyName) {
    window.location.href = `audit.html?company=${encodeURIComponent(companyName)}`;
}

// Toggle Dropdown Menu
function toggleDropdown(companyId) {
    const dropdown = document.getElementById(`dropdown-${companyId}`);
    // Close all other dropdowns
    document.querySelectorAll('.dropdown-menu.show').forEach(d => {
        if (d.id !== `dropdown-${companyId}`) d.classList.remove('show');
    });
    dropdown.classList.toggle('show');
}

// Close all dropdowns
function closeAllDropdowns() {
    document.querySelectorAll('.dropdown-menu.show').forEach(d => d.classList.remove('show'));
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown')) {
        closeAllDropdowns();
    }
});

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

// Load Companies - Show all companies from Tally with sync status
async function loadCompanies() {
    const list = document.getElementById('company-list');
    list.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
    
    try {
        const data = await apiCall('/api/companies');
        
        // Get synced companies from database (correct endpoint)
        const syncedCompanies = await apiCall('/api/data/synced-companies').catch(() => ({ companies: [] }));
        const syncedNames = (syncedCompanies.companies || []).map(c => c.company_name || c.name || c);
        
        if (!data.companies || data.companies.length === 0) {
            list.innerHTML = '<div class="empty-state"><i class="fas fa-building"></i><p>No companies found in Tally. Make sure Tally is running.</p></div>';
            // Show SweetAlert for Tally not running
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'warning',
                    title: '<strong style="color: #dc3545;">Tally Not Connected</strong>',
                    html: '<p style="font-size: 16px;"><strong style="color: #856404;">No companies found in Tally.</strong></p><p>Make sure <strong>Tally is running</strong> and has companies open.</p>',
                    confirmButtonColor: '#3085d6',
                    confirmButtonText: 'OK'
                });
            }
            return;
        }
        
        // Filter out synced companies - only show NEW companies
        const newCompanies = data.companies.filter(c => !syncedNames.includes(c.name));
        
        if (newCompanies.length === 0) {
            list.innerHTML = '<div class="empty-state"><i class="fas fa-check-circle"></i><p>All companies are already synced!</p><p class="text-muted">Go to Dashboard to view synced data</p></div>';
            return;
        }
        
        list.innerHTML = newCompanies.map(company => {
            // Extract period from company name or use Tally data
            const extractedPeriod = extractPeriodFromName(company.name);
            const fromDate = parseTallyDate(company.books_from) || extractedPeriod.from || '2025-04-01';
            const toDate = parseTallyDate(company.books_to) || extractedPeriod.to || '2026-03-31';
            companyPeriods[company.name] = { from: fromDate, to: toDate };
            const companyId = company.name.replace(/[^a-zA-Z0-9]/g, '_');
            
            return `
                <div class="company-item new-company" id="new-${companyId}" data-company="${company.name}">
                    <div class="company-info">
                        <div class="company-name-row">
                            <span class="company-name">${company.name}</span>
                            <span class="not-synced-badge">New</span>
                        </div>
                        <div class="company-period">
                            <span class="period-display" id="period-${companyId}">
                                ${formatDateDisplay(fromDate)} - ${formatDateDisplay(toDate)}
                            </span>
                        </div>
                    </div>
                    <div class="company-actions">
                        <div class="circular-progress" id="new-progress-${companyId}" style="display: none;">
                            <svg viewBox="0 0 44 44">
                                <circle class="progress-bg" cx="22" cy="22" r="20"></circle>
                                <circle class="progress-bar" cx="22" cy="22" r="20"></circle>
                            </svg>
                            <span class="progress-text">0%</span>
                        </div>
                        <button class="btn btn-sm btn-outline" onclick="editPeriod('${company.name}')" title="Edit Period">
                            <i class="fas fa-pencil-alt"></i>
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="syncCompany('${company.name}')" title="Full Sync">
                            <i class="fas fa-sync"></i> Sync
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        list.innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Error: ${error.message}</p></div>`;
        // Show SweetAlert for connection error
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: '<strong style="color: #dc3545;">Tally Connection Failed</strong>',
                html: '<p style="font-size: 16px;"><strong style="color: #721c24;">Unable to connect to Tally.</strong></p><p>Please check:</p><ul style="text-align: left;"><li>Tally is <strong>running</strong></li><li>Tally port is <strong>9000</strong></li><li>Tally has companies <strong>open</strong></li></ul>',
                confirmButtonColor: '#dc3545',
                confirmButtonText: 'OK'
            });
        }
    }
}

// Extract period from company name pattern like "MATOSHRI ENTERPRISES 18-24" or "Company 25-26"
// DEVELOPER NOTE: Many Tally companies have financial year in name (e.g., "18-24" means Apr 2018 to Mar 2024)
function extractPeriodFromName(companyName) {
    // Pattern: Look for YY-YY at end of name (e.g., "18-24", "25-26")
    const yearPattern = /(\d{2})-(\d{2})$/;
    const match = companyName.match(yearPattern);
    
    if (match) {
        const startYear = parseInt(match[1]);
        const endYear = parseInt(match[2]);
        
        // Convert 2-digit year to 4-digit (18 -> 2018, 25 -> 2025)
        const fullStartYear = startYear > 50 ? 1900 + startYear : 2000 + startYear;
        const fullEndYear = endYear > 50 ? 1900 + endYear : 2000 + endYear;
        
        // Financial year: Apr 1 to Mar 31
        return {
            from: `${fullStartYear}-04-01`,
            to: `${fullEndYear}-03-31`
        };
    }
    
    // Pattern: Look for "(from 1-Sep-25)" style
    const fromPattern = /\(from\s+(\d{1,2})-([A-Za-z]{3})-(\d{2})\)/i;
    const fromMatch = companyName.match(fromPattern);
    
    if (fromMatch) {
        const day = fromMatch[1].padStart(2, '0');
        const monthStr = fromMatch[2];
        const year = parseInt(fromMatch[3]) > 50 ? 1900 + parseInt(fromMatch[3]) : 2000 + parseInt(fromMatch[3]);
        
        const months = { 'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
                         'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12' };
        const month = months[monthStr.charAt(0).toUpperCase() + monthStr.slice(1).toLowerCase()] || '04';
        
        return {
            from: `${year}-${month}-${day}`,
            to: `${year + 1}-03-31`
        };
    }
    
    return { from: null, to: null };
}

// Parse Tally date format (e.g., "1-Apr-18 to 31-Mar-26" or "1-Apr-2025" or "2025-09-01")
function parseTallyDate(dateStr) {
    if (!dateStr) return null;
    
    // Already in YYYY-MM-DD format - return as is
    if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
        return dateStr;
    }
    
    // Handle format like "1-Apr-25 to 31-Mar-26" - extract just the date part
    const cleanDate = dateStr.split(' to ')[0].trim();
    
    // Parse formats: "1-Apr-25", "01-Apr-2025", "1-Apr-2025"
    const parts = cleanDate.split('-');
    if (parts.length !== 3) return null;
    
    const day = parts[0].padStart(2, '0');
    const monthStr = parts[1];
    const yearStr = parts[2];
    
    const months = { 'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
                     'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12' };
    
    const month = months[monthStr] || '01';
    const year = yearStr.length === 2 ? (parseInt(yearStr) > 50 ? '19' + yearStr : '20' + yearStr) : yearStr;
    
    return `${year}-${month}-${day}`;
}

// Format date for display
function formatDateDisplay(dateStr) {
    if (!dateStr) return '--';
    
    // Handle YYYY-MM-DD format
    if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
        const [year, month, day] = dateStr.split('-');
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${parseInt(day)} ${months[parseInt(month) - 1]} ${year}`;
    }
    
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

// Toggle Company Selection
function toggleCompany(name) {
    const items = document.querySelectorAll('.company-item');
    items.forEach(item => {
        if (item.querySelector('.company-name').textContent === name) {
            item.classList.toggle('selected');
            if (item.classList.contains('selected')) {
                if (!selectedCompanies.includes(name)) selectedCompanies.push(name);
            } else {
                selectedCompanies = selectedCompanies.filter(c => c !== name);
            }
        }
    });
}

// Refresh Companies
function refreshCompanies() {
    loadCompanies();
}

// Edit Period for a company (Task 2 - pencil button)
function editPeriod(companyName) {
    const period = companyPeriods[companyName] || { from: '2025-04-01', to: new Date().toISOString().split('T')[0] };
    
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <h3>Edit Period - ${companyName}</h3>
                <button class="btn-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="date-input">
                    <label>From Date</label>
                    <input type="date" id="edit-from-date" value="${period.from}">
                </div>
                <div class="date-input">
                    <label>To Date</label>
                    <input type="date" id="edit-to-date" value="${period.to}">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                <button class="btn btn-primary" onclick="savePeriod('${companyName}')">Save</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

// Save Period
function savePeriod(companyName) {
    const fromDate = document.getElementById('edit-from-date').value;
    const toDate = document.getElementById('edit-to-date').value;
    
    companyPeriods[companyName] = { from: fromDate, to: toDate };
    
    // Update display
    const safeId = companyName.replace(/[^a-zA-Z0-9]/g, '_');
    const periodDisplay = document.getElementById(`period-${safeId}`);
    if (periodDisplay) {
        periodDisplay.textContent = `${formatDateDisplay(fromDate)} - ${formatDateDisplay(toDate)}`;
    }
    
    document.querySelector('.modal-overlay').remove();
    showToast('Period updated', 'success');
}

// Sync single company (Task 3 - Full Sync)
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

// Update Sync Status
async function updateSyncStatus() {
    try {
        const status = await apiCall('/api/sync/status');
        
        const progressFill = document.getElementById('progress-fill');
        const progressPercent = document.getElementById('progress-percent');
        const progressTitle = document.getElementById('progress-title');
        const currentTable = document.getElementById('current-table');
        const rowsProcessed = document.getElementById('rows-processed');
        
        // Round progress to whole number
        const progress = Math.round(status.progress || 0);
        
        // Update main progress card
        if (progressFill) progressFill.style.width = `${progress}%`;
        if (progressPercent) progressPercent.textContent = `${progress}%`;
        if (progressTitle) progressTitle.textContent = `Syncing ${status.current_company || ''}`;
        if (currentTable) currentTable.textContent = status.current_table || 'Processing...';
        if (rowsProcessed) rowsProcessed.textContent = `${formatNumber(status.rows_processed || 0)} rows`;
        
        // Update circular progress in company card
        if (status.current_company) {
            updateCircularProgress(status.current_company, progress);
        }
        
        // Stop polling if sync is not running (idle, completed, failed, cancelled)
        if (status.status !== 'running') {
            clearInterval(syncInterval);
            syncInterval = null;
            
            if (status.status === 'completed') {
                showToast('Sync completed successfully!', 'success');
                if (progressPercent) progressPercent.textContent = '100%';
                if (progressFill) progressFill.style.width = '100%';
                if (status.current_company) {
                    updateCircularProgress(status.current_company, 100);
                }
                setTimeout(() => {
                    hideSyncProgress();
                    hideCircularProgress();
                    loadCompanies();
                    loadSyncedCompanies();
                }, 2000);
            } else if (status.status === 'failed') {
                showToast(`Sync failed: ${status.error_message}`, 'error');
                setTimeout(() => {
                    hideSyncProgress();
                    hideCircularProgress();
                }, 2000);
            } else if (status.status === 'idle') {
                // Sync already finished or never started - just stop polling
                hideSyncProgress();
                hideCircularProgress();
            }
        }
    } catch (error) {
        console.error('Status check failed:', error);
    }
}

// Show circular progress in company card
function showCircularProgress(companyName) {
    const companyId = companyName.replace(/[^a-zA-Z0-9]/g, '_');
    
    // Try synced company card
    const syncedCard = document.getElementById(`synced-${companyId}`);
    if (syncedCard) {
        syncedCard.classList.add('syncing');
        const progress = document.getElementById(`progress-${companyId}`);
        if (progress) {
            progress.style.display = 'flex';
            // Hide buttons
            syncedCard.querySelectorAll('.synced-company-actions .btn, .synced-company-actions .dropdown').forEach(el => {
                el.style.display = 'none';
            });
        }
    }
    
    // Try new company card
    const newCard = document.getElementById(`new-${companyId}`);
    if (newCard) {
        newCard.classList.add('syncing');
        const progress = document.getElementById(`new-progress-${companyId}`);
        if (progress) {
            progress.style.display = 'flex';
            // Hide buttons
            newCard.querySelectorAll('.company-actions .btn').forEach(el => {
                el.style.display = 'none';
            });
        }
    }
}

// Update circular progress value
function updateCircularProgress(companyName, percent) {
    const companyId = companyName.replace(/[^a-zA-Z0-9]/g, '_');
    
    // Calculate stroke-dashoffset (126 is circumference of circle with r=20)
    const circumference = 126;
    const offset = circumference - (percent / 100) * circumference;
    
    // Update synced company progress
    const syncedProgress = document.getElementById(`progress-${companyId}`);
    if (syncedProgress) {
        const bar = syncedProgress.querySelector('.progress-bar');
        const text = syncedProgress.querySelector('.progress-text');
        if (bar) bar.style.strokeDashoffset = offset;
        if (text) text.textContent = `${percent}%`;
    }
    
    // Update new company progress
    const newProgress = document.getElementById(`new-progress-${companyId}`);
    if (newProgress) {
        const bar = newProgress.querySelector('.progress-bar');
        const text = newProgress.querySelector('.progress-text');
        if (bar) bar.style.strokeDashoffset = offset;
        if (text) text.textContent = `${percent}%`;
    }
}

// Hide all circular progress indicators
function hideCircularProgress() {
    // Reset synced company cards
    document.querySelectorAll('.synced-company-item.syncing').forEach(card => {
        card.classList.remove('syncing');
        card.querySelectorAll('.circular-progress').forEach(p => p.style.display = 'none');
        card.querySelectorAll('.synced-company-actions .btn, .synced-company-actions .dropdown').forEach(el => {
            el.style.display = '';
        });
    });
    
    // Reset new company cards
    document.querySelectorAll('.company-item.syncing').forEach(card => {
        card.classList.remove('syncing');
        card.querySelectorAll('.circular-progress').forEach(p => p.style.display = 'none');
        card.querySelectorAll('.company-actions .btn').forEach(el => {
            el.style.display = '';
        });
    });
}

// Cancel Sync
async function cancelSync() {
    try {
        await apiCall('/api/sync/cancel', { method: 'POST' });
        showToast('Sync cancelled', 'warning');
        clearInterval(syncInterval);
        syncInterval = null;
        hideCircularProgress();
    } catch (error) {
        showToast(`Cancel failed: ${error.message}`, 'error');
    }
}

// ==========================================
// TAB 2: SYNC OPTIONS FUNCTIONS
// ==========================================

// Set Sync Interval
function setSyncInterval(minutes) {
    syncIntervalMinutes = minutes;
    showToast(`Sync interval set to ${minutes} minutes`, 'success');
}

// Toggle Auto Sync
function toggleAutoSync() {
    const toggle = document.getElementById('auto-sync-toggle');
    const label = document.getElementById('auto-sync-label');
    const scheduleInfo = document.getElementById('schedule-info');
    
    if (toggle.checked) {
        label.textContent = 'Auto Sync: ON';
        scheduleInfo.style.display = 'flex';
        startAutoSync();
    } else {
        label.textContent = 'Auto Sync: OFF';
        scheduleInfo.style.display = 'none';
        stopAutoSync();
    }
}

// Start Auto Sync Timer
function startAutoSync() {
    if (autoSyncTimer) clearInterval(autoSyncTimer);
    
    updateNextSyncTime();
    
    autoSyncTimer = setInterval(() => {
        runAutoIncrementalSync();
        updateNextSyncTime();
    }, syncIntervalMinutes * 60 * 1000);
    
    showToast(`Auto sync enabled - every ${syncIntervalMinutes} minutes`, 'success');
}

// Stop Auto Sync
function stopAutoSync() {
    if (autoSyncTimer) {
        clearInterval(autoSyncTimer);
        autoSyncTimer = null;
    }
    showToast('Auto sync disabled', 'warning');
}

// Update Next Sync Time Display
function updateNextSyncTime() {
    const nextSyncEl = document.getElementById('next-sync-time');
    if (nextSyncEl) {
        nextSyncEl.textContent = `${syncIntervalMinutes} minutes`;
    }
}

// Run Auto Incremental Sync
async function runAutoIncrementalSync() {
    try {
        const lastSyncEl = document.getElementById('last-sync-time');
        await apiCall('/api/sync/incremental', { method: 'POST' });
        if (lastSyncEl) {
            lastSyncEl.textContent = new Date().toLocaleTimeString();
        }
    } catch (error) {
        console.error('Auto sync failed:', error);
    }
}

// Save Schedule Settings
function saveScheduleSettings() {
    localStorage.setItem('syncIntervalMinutes', syncIntervalMinutes);
    localStorage.setItem('autoSyncEnabled', document.getElementById('auto-sync-toggle').checked);
    showToast('Schedule settings saved', 'success');
}

// ==========================================
// TAB 3: TALLY CONFIGURATION FUNCTIONS
// ==========================================

// Load Tally Config from API
async function loadTallyConfig() {
    try {
        const config = await apiCall('/api/config');
        
        document.getElementById('tally-host').value = config.tally?.server || 'localhost';
        document.getElementById('tally-port').value = config.tally?.port || 9000;
        
        // Check connection status
        checkTallyConnectionStatus();
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

// Check Tally Connection Status
async function checkTallyConnectionStatus() {
    const statusIcon = document.querySelector('#connection-status .status-icon');
    const statusText = document.getElementById('conn-status-text');
    const statusDetail = document.getElementById('conn-status-detail');
    const connectionDetails = document.getElementById('connection-details');
    
    statusIcon.className = 'status-icon checking';
    statusIcon.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    statusText.textContent = 'Checking connection...';
    statusDetail.textContent = 'Please wait';
    
    try {
        const health = await apiCall('/api/health');
        const tallyStatus = health.components?.tally;
        const isConnected = tallyStatus?.status === 'healthy';
        
        if (isConnected) {
            statusIcon.className = 'status-icon connected';
            statusIcon.innerHTML = '<i class="fas fa-check"></i>';
            statusText.textContent = 'Connected';
            statusDetail.textContent = tallyStatus.message || 'Tally is running and accessible';
            connectionDetails.style.display = 'block';
            
            document.getElementById('detail-server').textContent = tallyStatus.server || 'localhost';
            document.getElementById('detail-port').textContent = tallyStatus.port || '9000';
            
            // Get current company from companies API
            try {
                const companies = await apiCall('/api/data/companies');
                document.getElementById('detail-company').textContent = companies.current_company || 'N/A';
            } catch {
                document.getElementById('detail-company').textContent = 'N/A';
            }
        } else {
            statusIcon.className = 'status-icon disconnected';
            statusIcon.innerHTML = '<i class="fas fa-times"></i>';
            statusText.textContent = 'Disconnected';
            statusDetail.textContent = tallyStatus?.message || 'Cannot connect to Tally';
            connectionDetails.style.display = 'none';
        }
    } catch (error) {
        statusIcon.className = 'status-icon disconnected';
        statusIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        statusText.textContent = 'Error';
        statusDetail.textContent = error.message;
        connectionDetails.style.display = 'none';
    }
}

// Save Tally Config and Test Connection
async function saveTallyConfig() {
    const host = document.getElementById('tally-host').value;
    const port = document.getElementById('tally-port').value;
    
    if (!host || !port) {
        showToast('Please fill all fields', 'error');
        return;
    }
    
    try {
        // Step 1: Save config
        await apiCall('/api/config', {
            method: 'PUT',
            body: JSON.stringify({ 
                tally: { 
                    server: host, 
                    port: parseInt(port) 
                } 
            })
        });
        showToast('Configuration saved, testing connection...', 'info');
        
        // Step 2: Auto test connection
        const result = await apiCall('/api/config/tally/test', { method: 'POST' });
        
        if (result.connected) {
            showToast('Connection successful!', 'success');
        } else {
            showToast('Connection failed: ' + (result.error || 'Tally not responding'), 'error');
        }
        
        // Step 3: Update status display
        checkTallyConnectionStatus();
    } catch (error) {
        showToast(`Save failed: ${error.message}`, 'error');
    }
}

// Test Tally Connection
async function testTallyConnection() {
    showToast('Testing connection...', 'info');
    
    try {
        const result = await apiCall('/api/config/tally/test', { method: 'POST' });
        
        if (result.connected) {
            showToast('Connection successful!', 'success');
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'success',
                    title: '<strong style="color: #28a745;">Connected!</strong>',
                    html: '<p style="font-size: 16px;"><strong>Tally is running</strong> and accessible.</p>',
                    confirmButtonColor: '#28a745',
                    confirmButtonText: 'OK'
                });
            }
        } else {
            showToast('Connection failed: ' + (result.error || 'Unknown error'), 'error');
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'error',
                    title: '<strong style="color: #dc3545;">Connection Failed</strong>',
                    html: '<p style="font-size: 16px;"><strong style="color: #721c24;">Unable to connect to Tally.</strong></p><p>Please check:</p><ul style="text-align: left;"><li>Tally is <strong>running</strong></li><li>Tally port is <strong>9000</strong></li><li>Tally has companies <strong>open</strong></li></ul>',
                    confirmButtonColor: '#dc3545',
                    confirmButtonText: 'OK'
                });
            }
        }
        
        checkTallyConnectionStatus();
    } catch (error) {
        showToast(`Connection test failed: ${error.message}`, 'error');
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: '<strong style="color: #dc3545;">Connection Failed</strong>',
                html: '<p style="font-size: 16px;"><strong style="color: #721c24;">Unable to connect to Tally.</strong></p><p>Error: ' + error.message + '</p><p>Please check:</p><ul style="text-align: left;"><li>Tally is <strong>running</strong></li><li>Tally port is <strong>9000</strong></li><li>Tally has companies <strong>open</strong></li></ul>',
                confirmButtonColor: '#dc3545',
                confirmButtonText: 'OK'
            });
        }
    }
}

// ==========================================
// INITIALIZE
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    loadCompanies();
    loadSyncedCompanies();
    
    // Load saved settings
    const savedInterval = localStorage.getItem('syncIntervalMinutes');
    if (savedInterval) {
        syncIntervalMinutes = parseInt(savedInterval);
        const radio = document.querySelector(`input[name="sync-interval"][value="${savedInterval}"]`);
        if (radio) radio.checked = true;
    }
    
    const autoSyncEnabled = localStorage.getItem('autoSyncEnabled') === 'true';
    if (autoSyncEnabled) {
        document.getElementById('auto-sync-toggle').checked = true;
        toggleAutoSync();
    }
});
