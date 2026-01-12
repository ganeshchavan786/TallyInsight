// Dashboard Page JavaScript

let currentCompany = '';

// Get company from URL parameter
function getCompanyFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('company') || '';
}

// Load Dashboard Data
async function loadDashboard() {
    // Get company from URL
    currentCompany = getCompanyFromUrl();
    
    // Update page title with company name
    if (currentCompany) {
        document.getElementById('page-title').textContent = currentCompany;
        document.getElementById('page-subtitle').textContent = 'Company Dashboard - Synced Data Overview';
        document.title = `${currentCompany} - Dashboard`;
    }
    
    await Promise.all([
        loadStats(),
        loadTableStats()
    ]);
}

// Load Stats
async function loadStats() {
    try {
        let endpoint = '/api/data/counts';
        if (currentCompany) {
            endpoint += `?company=${encodeURIComponent(currentCompany)}`;
        }
        
        const stats = await apiCall(endpoint);
        
        let totalRecords = 0;
        Object.entries(stats).forEach(([key, value]) => {
            if (typeof value === 'number') {
                totalRecords += value;
            }
        });
        
        document.getElementById('total-records').textContent = formatNumber(totalRecords);
        
        // Get companies count (1 if filtered, else total)
        if (currentCompany) {
            document.getElementById('total-companies').textContent = '1';
        } else {
            const companyData = await apiCall('/api/data/synced-companies').catch(() => ({ count: 0 }));
            document.getElementById('total-companies').textContent = companyData.count || 0;
        }
        
        // Get last sync for this company
        if (currentCompany) {
            const syncedCompanies = await apiCall('/api/data/synced-companies').catch(() => ({ companies: [] }));
            const company = syncedCompanies.companies?.find(c => c.company_name === currentCompany);
            if (company?.last_sync_at) {
                document.getElementById('last-sync').textContent = formatTime(company.last_sync_at);
            }
        } else {
            const syncStatus = await apiCall('/api/sync/status').catch(() => ({}));
            if (syncStatus.completed_at) {
                document.getElementById('last-sync').textContent = formatTime(syncStatus.completed_at);
            }
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load Table Stats
async function loadTableStats() {
    try {
        let endpoint = '/api/data/counts';
        if (currentCompany) {
            endpoint += `?company=${encodeURIComponent(currentCompany)}`;
        }
        
        const stats = await apiCall(endpoint);
        
        // All 18 Master Tables
        const masterTables = [
            'mst_group', 'mst_ledger', 'mst_stock_item', 'mst_stock_category',
            'mst_stock_group', 'mst_godown', 'mst_uom', 'mst_vouchertype',
            'mst_cost_category', 'mst_cost_centre', 'mst_currency', 'mst_employee',
            'mst_attendance_type', 'mst_payhead', 'mst_gst_effective_rate',
            'mst_opening_batch_allocation', 'mst_opening_bill_allocation',
            'mst_stockitem_standard_cost', 'mst_stockitem_standard_price'
        ];
        
        // All 14 Transaction Tables
        const transactionTables = [
            'trn_voucher', 'trn_accounting', 'trn_inventory', 'trn_batch',
            'trn_cost_centre', 'trn_cost_category_centre', 'trn_cost_inventory_category_centre',
            'trn_bill', 'trn_bank', 'trn_inventory_accounting',
            'trn_employee', 'trn_payhead', 'trn_attendance', 'trn_closingstock_ledger'
        ];
        
        renderTableGrid('master-tables', masterTables, stats);
        renderTableGrid('transaction-tables', transactionTables, stats);
    } catch (error) {
        console.error('Failed to load table stats:', error);
    }
}

// Render Table Grid
function renderTableGrid(containerId, tables, stats) {
    const container = document.getElementById(containerId);
    
    container.innerHTML = tables.map(table => {
        const count = stats[table] || 0;
        const displayName = table.replace('mst_', '').replace('trn_', '').replace(/_/g, ' ');
        return `
            <div class="table-item">
                <span class="table-name">${displayName}</span>
                <span class="table-count ${count === 0 ? 'zero' : ''}">${formatNumber(count)}</span>
            </div>
        `;
    }).join('');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
});
