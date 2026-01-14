// ==========================================
// SYNC COMPANIES - Company List Management
// ==========================================

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
