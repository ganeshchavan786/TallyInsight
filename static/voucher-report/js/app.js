// Main Application JavaScript for Tally Voucher Report

// State
let allVouchers = [];
let filteredVouchers = [];
let currentPage = 1;
let pageSize = CONFIG.DEFAULT_PAGE_SIZE;
let sortColumn = 'date';
let sortDirection = 'desc';
let selectedCompany = '';
let selectedVoucherType = 'Sales'; // Default to Sales
let currentView = 'voucher'; // 'voucher' or 'outstanding'
let outstandingData = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeDates();
    loadCompanies();
    setupEventListeners();
    setupSubmenuListeners();
});

// Setup Event Listeners
function setupEventListeners() {
    // Global search - works for both vouchers and outstanding
    const searchInput = document.getElementById('globalSearch');
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            if (currentView === 'outstanding') {
                filterOutstandingTable();
            } else {
                filterVouchers();
            }
        }, 300);
    });
    
    // Table header sorting
    document.querySelectorAll('.data-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.dataset.sort;
            if (sortColumn === column) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortColumn = column;
                sortDirection = 'asc';
            }
            sortVouchers();
            renderVouchers();
        });
    });
}

// Setup Submenu Listeners
function setupSubmenuListeners() {
    // Voucher type links
    document.querySelectorAll('.submenu-link[data-type]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const type = link.dataset.type;
            
            // Update active state
            document.querySelectorAll('.submenu-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Switch to voucher view
            showVoucherView();
            
            // Update voucher type filter
            selectedVoucherType = type;
            document.getElementById('voucherType').value = type;
            
            // Reload with filter
            loadVouchers();
        });
    });
    
    // Outstanding links
    document.querySelectorAll('.submenu-link[data-outstanding]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const type = link.dataset.outstanding;
            
            // Update active state
            document.querySelectorAll('.submenu-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Switch to outstanding view
            showOutstandingView(type);
        });
    });
}

// Toggle Submenu
function toggleSubmenu(event) {
    event.preventDefault();
    const navItem = event.currentTarget.parentElement;
    const submenu = navItem.querySelector('.submenu');
    
    navItem.classList.toggle('open');
    submenu.classList.toggle('show');
}

// Initialize Dates
function initializeDates() {
    document.getElementById('fromDate').value = CONFIG.DEFAULT_FROM_DATE;
    document.getElementById('toDate').value = CONFIG.DEFAULT_TO_DATE;
}

// Load Companies for dropdown
async function loadCompanies() {
    try {
        const data = await api.getSyncedCompanies();
        const select = document.getElementById('companySelect');
        const footer = document.getElementById('currentCompany');
        
        if (data.companies && data.companies.length > 0) {
            // Populate dropdown
            data.companies.forEach(c => {
                const option = document.createElement('option');
                option.value = c.company_name;
                option.textContent = c.company_name;
                select.appendChild(option);
            });
            
            // Set first company as default
            selectedCompany = data.companies[0].company_name;
            select.value = selectedCompany;
            footer.textContent = selectedCompany;
            
            // Set default voucher type in dropdown
            document.getElementById('voucherType').value = selectedVoucherType;
            
            // Load vouchers for selected company
            loadVouchers();
        } else {
            footer.textContent = 'No companies synced';
            showToast('No companies found. Please sync data first.', 'warning');
        }
    } catch (error) {
        console.error('Failed to load companies:', error);
        showToast('Failed to load companies', 'error');
    }
}

// Change Company
async function changeCompany() {
    const select = document.getElementById('companySelect');
    selectedCompany = select.value;
    document.getElementById('currentCompany').textContent = selectedCompany || 'All Companies';
    
    // Reload based on current view
    if (currentView === 'outstanding') {
        const activeLink = document.querySelector('.submenu-link[data-outstanding].active');
        const type = activeLink ? activeLink.dataset.outstanding : 'receivable';
        loadOutstandingData(type);
    } else if (currentView === 'ledger') {
        // Clear current selection first
        allLedgers = [];
        document.getElementById('ledgerSearchInput').value = '';
        document.getElementById('ledgerDropdown').style.display = 'none';
        document.getElementById('ledgerTableBody').innerHTML = '<tr><td colspan="7" class="loading-cell">Select a ledger to view transactions</td></tr>';
        // Reload ledger list for new company
        await loadLedgerList();
        showToast(`Loaded ${allLedgers.length} ledgers for ${selectedCompany}`, 'success');
    } else {
        loadVouchers();
    }
}

// Load Vouchers
async function loadVouchers() {
    showLoading();
    
    try {
        const fromDate = document.getElementById('fromDate').value;
        const toDate = document.getElementById('toDate').value;
        const voucherType = document.getElementById('voucherType').value || selectedVoucherType;
        
        // Fetch all vouchers (paginated from API)
        allVouchers = await fetchAllVouchers({
            from_date: fromDate,
            to_date: toDate,
            voucher_type: voucherType,
            company: selectedCompany
        });
        
        filterVouchers();
        updateStats();
        showToast(`Loaded ${allVouchers.length} vouchers`, 'success');
    } catch (error) {
        console.error('Failed to load vouchers:', error);
        showToast('Failed to load vouchers: ' + error.message, 'error');
        showEmptyState();
    }
}

// Fetch all vouchers with pagination
async function fetchAllVouchers(params) {
    const BATCH_SIZE = 1000;
    let skip = 0;
    let allItems = [];
    let hasMore = true;
    
    while (hasMore) {
        const response = await api.getVouchers({
            ...params,
            skip: skip,
            limit: BATCH_SIZE
        });
        
        const vouchers = response?.vouchers || response?.data || [];
        allItems.push(...vouchers);
        
        if (vouchers.length < BATCH_SIZE) {
            hasMore = false;
        } else {
            skip += BATCH_SIZE;
        }
    }
    
    return allItems;
}

// Filter Vouchers
function filterVouchers() {
    const searchTerm = document.getElementById('globalSearch').value.toLowerCase();
    const partyFilter = document.getElementById('partyFilter').value.toLowerCase();
    const fromDate = new Date(document.getElementById('fromDate').value);
    const toDate = new Date(document.getElementById('toDate').value);
    
    filteredVouchers = allVouchers.filter(v => {
        // Date filter
        const vDate = new Date(v.date);
        if (vDate < fromDate || vDate > toDate) return false;
        
        // Party filter
        if (partyFilter && !v.party_name?.toLowerCase().includes(partyFilter)) return false;
        
        // Global search
        if (searchTerm) {
            const searchFields = [
                v.voucher_number,
                v.party_name,
                v.narration,
                v.voucher_type,
                v.reference_number
            ].filter(Boolean).join(' ').toLowerCase();
            
            if (!searchFields.includes(searchTerm)) return false;
        }
        
        return true;
    });
    
    sortVouchers();
    currentPage = 1;
    renderVouchers();
    updateVoucherCount();
}

// Sort Vouchers
function sortVouchers() {
    filteredVouchers.sort((a, b) => {
        let aVal = a[sortColumn];
        let bVal = b[sortColumn];
        
        // Handle dates
        if (sortColumn === 'date') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        }
        
        // Handle amounts
        if (sortColumn === 'amount') {
            aVal = parseFloat(aVal) || 0;
            bVal = parseFloat(bVal) || 0;
        }
        
        // Handle strings
        if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal?.toLowerCase() || '';
        }
        
        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
}

// Render Vouchers
function renderVouchers() {
    const tbody = document.getElementById('vouchersTableBody');
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const pageVouchers = filteredVouchers.slice(start, end);
    
    if (pageVouchers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="loading-cell">
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>No vouchers found</p>
                        <p style="font-size: 0.875rem;">Try adjusting your filters</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = pageVouchers.map(v => {
        const typeClass = v.voucher_type?.toLowerCase().replace(/\s+/g, '-') || 'other';
        const amount = calculateVoucherAmount(v);
        
        return `
            <tr>
                <td>${formatDate(v.date)}</td>
                <td><span class="voucher-type-tag ${typeClass}">${v.voucher_type}</span></td>
                <td>${v.voucher_number || '-'}</td>
                <td>${v.party_name || '-'}</td>
                <td class="text-right">${formatCurrency(amount)}</td>
                <td class="text-center">
                    <button class="action-btn" onclick="viewVoucher('${v.guid}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    renderPagination();
    updateShowingInfo();
}

// Calculate voucher amount from accounting entries
function calculateVoucherAmount(voucher) {
    // If voucher has pre-calculated amount, use it
    if (voucher.amount !== undefined) {
        return parseFloat(voucher.amount) || 0;
    }
    
    // Otherwise return 0 (will be calculated when viewing details)
    return 0;
}

// Render Pagination
function renderPagination() {
    const totalPages = Math.ceil(filteredVouchers.length / pageSize);
    const pagination = document.getElementById('pagination');
    
    let html = '';
    
    // Previous button
    html += `<button ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">
        <i class="fas fa-chevron-left"></i>
    </button>`;
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        html += `<button onclick="goToPage(1)">1</button>`;
        if (startPage > 2) html += `<button disabled>...</button>`;
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += `<button disabled>...</button>`;
        html += `<button onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }
    
    // Next button
    html += `<button ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">
        <i class="fas fa-chevron-right"></i>
    </button>`;
    
    pagination.innerHTML = html;
}

// Go to page
function goToPage(page) {
    currentPage = page;
    renderVouchers();
    document.querySelector('.table-container').scrollTop = 0;
}

// Update showing info
function updateShowingInfo() {
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, filteredVouchers.length);
    
    document.getElementById('showingFrom').textContent = filteredVouchers.length > 0 ? start : 0;
    document.getElementById('showingTo').textContent = end;
    document.getElementById('totalRecords').textContent = filteredVouchers.length;
}

// Update voucher count badge
function updateVoucherCount() {
    document.getElementById('voucherCount').textContent = `${filteredVouchers.length} vouchers`;
}

// Update Stats
function updateStats() {
    let sales = 0, purchase = 0, payment = 0, receipt = 0;
    
    allVouchers.forEach(v => {
        const type = v.voucher_type?.toLowerCase() || '';
        const amount = Math.abs(parseFloat(v.amount) || 0);
        
        if (type.includes('sales')) sales += amount;
        else if (type.includes('purchase')) purchase += amount;
        else if (type.includes('payment')) payment += amount;
        else if (type.includes('receipt')) receipt += amount;
    });
    
    document.getElementById('totalSales').textContent = formatCurrency(sales);
    document.getElementById('totalPurchase').textContent = formatCurrency(purchase);
    document.getElementById('totalPayment').textContent = formatCurrency(payment);
    document.getElementById('totalReceipt').textContent = formatCurrency(receipt);
}

// View Voucher Details
async function viewVoucher(guid) {
    try {
        const data = await api.getVoucherDetails(guid);
        showVoucherModal(data);
    } catch (error) {
        console.error('Failed to load voucher details:', error);
        showToast('Failed to load voucher details', 'error');
    }
}

// Show Voucher Modal
function showVoucherModal(data) {
    const voucher = data.voucher || data;
    const entries = data.entries || data.accounting || [];
    const inventory = data.inventory || [];
    const bills = data.bills || [];
    const bank = data.bank || [];
    
    // Set header info
    document.getElementById('modalVoucherType').textContent = voucher.voucher_type;
    document.getElementById('modalVoucherNumber').textContent = voucher.voucher_number;
    document.getElementById('modalDate').textContent = formatDate(voucher.date);
    document.getElementById('modalParty').textContent = voucher.party_name || '-';
    document.getElementById('modalRefNo').textContent = voucher.reference_number || '-';
    document.getElementById('modalRefDate').textContent = voucher.reference_date ? formatDate(voucher.reference_date) : '-';
    document.getElementById('modalNarration').textContent = voucher.narration || '-';
    
    // Render ledger entries
    let totalDebit = 0, totalCredit = 0;
    const ledgerHtml = entries.map(e => {
        const amount = parseFloat(e.amount) || 0;
        const debit = amount < 0 ? Math.abs(amount) : 0;
        const credit = amount >= 0 ? amount : 0;
        totalDebit += debit;
        totalCredit += credit;
        
        return `
            <tr>
                <td>${e.ledger}</td>
                <td class="text-right">${debit > 0 ? formatCurrency(debit) : '-'}</td>
                <td class="text-right">${credit > 0 ? formatCurrency(credit) : '-'}</td>
            </tr>
        `;
    }).join('');
    
    document.getElementById('ledgerEntries').innerHTML = ledgerHtml || '<tr><td colspan="3" style="text-align:center;color:#9ca3af;padding:2rem;">No entries</td></tr>';
    document.getElementById('totalDebit').textContent = formatCurrency(totalDebit);
    document.getElementById('totalCredit').textContent = formatCurrency(totalCredit);
    
    // Render inventory items
    const inventoryHtml = inventory.map(i => `
        <tr>
            <td>${i.item || i.stock_item}</td>
            <td class="text-right">${i.quantity}</td>
            <td class="text-right">${formatCurrency(i.rate)}</td>
            <td class="text-right">${formatCurrency(i.amount)}</td>
            <td>${i.godown || '-'}</td>
        </tr>
    `).join('');
    document.getElementById('inventoryItems').innerHTML = inventoryHtml || '<tr><td colspan="5" style="text-align:center;color:#9ca3af;padding:2rem;">No items</td></tr>';
    document.getElementById('itemCount').textContent = inventory.length;
    
    // Render bills
    const billsHtml = bills.map(b => `
        <tr>
            <td>${b.name || b.bill_name}</td>
            <td>${b.billtype || b.bill_type || '-'}</td>
            <td class="text-right">${formatCurrency(b.amount)}</td>
        </tr>
    `).join('');
    document.getElementById('billAllocations').innerHTML = billsHtml || '<tr><td colspan="3" style="text-align:center;color:#9ca3af;padding:2rem;">No bills</td></tr>';
    document.getElementById('billCount').textContent = bills.length;
    
    // Render bank details
    const bankHtml = bank.map(b => `
        <tr>
            <td>${b.transaction_type || '-'}</td>
            <td>${b.instrument_number || '-'}</td>
            <td>${b.instrument_date ? formatDate(b.instrument_date) : '-'}</td>
            <td>${b.bank_name || '-'}</td>
            <td class="text-right">${b.amount ? formatCurrency(b.amount) : '-'}</td>
        </tr>
    `).join('');
    document.getElementById('bankDetails').innerHTML = bankHtml || '<tr><td colspan="5" style="text-align:center;color:#9ca3af;padding:2rem;">No bank details</td></tr>';
    document.getElementById('bankCount').textContent = bank.length;
    
    // Show first tab
    showModalTab('ledger');
    
    // Show modal
    document.getElementById('voucherModal').classList.add('active');
}

// Show Modal Tab
function showModalTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    
    document.getElementById(tabName + 'Tab').classList.add('active');
    document.querySelector(`.tab-btn[onclick*="${tabName}"]`)?.classList.add('active');
}

// Close Modal
function closeModal() {
    document.getElementById('voucherModal').classList.remove('active');
}

// Filter Actions
function applyFilters() {
    loadVouchers();
}

function resetFilters() {
    document.getElementById('fromDate').value = CONFIG.DEFAULT_FROM_DATE;
    document.getElementById('toDate').value = CONFIG.DEFAULT_TO_DATE;
    document.getElementById('voucherType').value = '';
    document.getElementById('partyFilter').value = '';
    document.getElementById('globalSearch').value = '';
    
    // Reset quick filter buttons
    document.querySelectorAll('.quick-filters .btn-chip').forEach(b => b.classList.remove('active'));
    document.querySelector('.quick-filters .btn-chip:last-child')?.classList.add('active');
    
    loadVouchers();
}

function setQuickFilter(period) {
    const today = new Date();
    let fromDate, toDate;
    
    switch (period) {
        case 'today':
            fromDate = toDate = today.toISOString().split('T')[0];
            break;
        case 'week':
            const weekStart = new Date(today);
            weekStart.setDate(today.getDate() - today.getDay());
            fromDate = weekStart.toISOString().split('T')[0];
            toDate = today.toISOString().split('T')[0];
            break;
        case 'month':
            fromDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
            toDate = today.toISOString().split('T')[0];
            break;
        case 'year':
        default:
            fromDate = CONFIG.DEFAULT_FROM_DATE;
            toDate = CONFIG.DEFAULT_TO_DATE;
    }
    
    document.getElementById('fromDate').value = fromDate;
    document.getElementById('toDate').value = toDate;
    
    // Update active button
    document.querySelectorAll('.quick-filters .btn-chip').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    
    filterVouchers();
}

function filterByType(type) {
    const typeSelect = document.getElementById('voucherType');
    
    if (type === 'vouchers') {
        typeSelect.value = '';
    } else {
        typeSelect.value = type.charAt(0).toUpperCase() + type.slice(1);
    }
    
    filterVouchers();
}

function setActiveNav(link) {
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
}

// Toggle Filters
function toggleFilters() {
    const body = document.getElementById('filtersBody');
    const icon = document.getElementById('filterToggleIcon');
    
    body.style.display = body.style.display === 'none' ? 'block' : 'none';
    icon.classList.toggle('fa-chevron-down');
    icon.classList.toggle('fa-chevron-up');
}

// Change Page Size
function changePageSize() {
    pageSize = parseInt(document.getElementById('pageSize').value);
    currentPage = 1;
    renderVouchers();
}

// Refresh Data
function refreshData() {
    loadVouchers();
}

// Export to Excel
function exportToExcel() {
    showToast('Export feature coming soon', 'info');
}

// Print Report
function printReport() {
    window.print();
}

// Print Voucher
function printVoucher() {
    showToast('Print voucher feature coming soon', 'info');
}

// Utility Functions
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    
    const day = date.getDate().toString().padStart(2, '0');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    
    return `${day}-${month}-${year}`;
}

function formatCurrency(amount) {
    const num = parseFloat(amount) || 0;
    return CONFIG.CURRENCY_SYMBOL + num.toLocaleString(CONFIG.CURRENCY_LOCALE, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function truncate(str, length) {
    if (!str) return '-';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#039;');
}

function showLoading() {
    document.getElementById('vouchersTableBody').innerHTML = `
        <tr>
            <td colspan="6" class="loading-cell">
                <div class="loader">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Loading vouchers...</span>
                </div>
            </td>
        </tr>
    `;
}

function showEmptyState() {
    document.getElementById('vouchersTableBody').innerHTML = `
        <tr>
            <td colspan="6" class="loading-cell">
                <div class="empty-state">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Failed to load vouchers</p>
                    <p style="font-size: 0.875rem;">Check your connection and try again</p>
                </div>
            </td>
        </tr>
    `;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Close modal on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
});

// ========== Outstanding Functions ==========
function showVoucherView() {
    currentView = 'voucher';
    
    // Reset search placeholder for vouchers
    const searchInput = document.getElementById('globalSearch');
    searchInput.placeholder = 'Search vouchers, party, narration...';
    
    document.querySelector('.stats-grid').style.display = 'grid';
    document.querySelector('.filters-card').style.display = 'block';
    document.querySelector('.table-card').style.display = 'block';
    document.getElementById('outstandingSection').style.display = 'none';
}

async function showOutstandingView(type) {
    currentView = 'outstanding';
    currentPartyType = type;
    currentReportType = 'ledger';
    billwisePage = 1;
    
    // Clear and update search placeholder
    const searchInput = document.getElementById('globalSearch');
    searchInput.value = '';
    searchInput.placeholder = 'Search party name, bill no...';
    
    document.querySelector('.stats-grid').style.display = 'none';
    document.querySelector('.filters-card').style.display = 'none';
    document.querySelector('.table-card').style.display = 'none';
    document.getElementById('outstandingSection').style.display = 'block';
    
    // Reset tabs to Ledger
    document.querySelectorAll('.report-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.report === 'ledger');
    });
    
    const title = type === 'receivable' ? 'Receivable' : 'Payable';
    document.getElementById('outstandingLabel').textContent = `${title} Outstanding`;
    
    // Initialize period dates (fast - no API call)
    await initOutstandingPeriod();
    
    await switchOutstandingReport('ledger');
}

async function loadOutstandingData(type) {
    const tbody = document.getElementById('outstandingTableBody');
    tbody.innerHTML = '<tr><td colspan="5" class="loading-cell"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
    try {
        const response = await fetch(`/api/data/outstanding?type=${type}&company=${encodeURIComponent(selectedCompany)}`);
        const data = await response.json();
        outstandingData = data.data || [];
        renderOutstandingTable();
        updateOutstandingStats();
        showToast(`Loaded ${outstandingData.length} parties`, 'success');
    } catch (error) {
        console.error('Failed to load outstanding:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">Failed to load data</td></tr>';
    }
}

function renderOutstandingTable() {
    const tbody = document.getElementById('outstandingTableBody');
    if (outstandingData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No data found</td></tr>';
        return;
    }
    tbody.innerHTML = outstandingData.map(row => `
        <tr>
            <td>${row.ledger_name || '-'}</td>
            <td class="text-right">${formatCurrency(row.opening || 0)}</td>
            <td class="text-right">${formatCurrency(row.debit || 0)}</td>
            <td class="text-right">${formatCurrency(row.credit || 0)}</td>
            <td class="text-right" style="color: ${row.closing >= 0 ? '#16a34a' : '#dc2626'}; font-weight: 500;">${formatCurrency(row.closing || 0)}</td>
        </tr>
    `).join('');
    document.getElementById('outstandingCount').textContent = `${outstandingData.length} records`;
}

function updateOutstandingStats() {
    const total = outstandingData.reduce((sum, row) => sum + (row.closing || 0), 0);
    document.getElementById('outstandingTotal').textContent = formatCurrency(Math.abs(total));
    document.getElementById('outstandingParties').textContent = outstandingData.length;
}

// Current outstanding report type and party type
let currentReportType = 'ledger';
let currentPartyType = 'receivable';
let billwisePage = 1;
let billwisePageSize = 50;
let outstandingFromDate = '';
let outstandingToDate = '';

// Initialize period dates - use today as default (fast, no API call)
async function initOutstandingPeriod() {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    
    // Set to_date to today
    outstandingToDate = todayStr;
    document.getElementById('outstandingToDate').value = todayStr;
    
    // Set from_date to start of financial year (April 1)
    const year = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
    outstandingFromDate = `${year}-04-01`;
    document.getElementById('outstandingFromDate').value = outstandingFromDate;
}

// Period change handler
function onPeriodChange() {
    // Just update the values, don't auto-reload
}

// Apply period filter
async function applyPeriodFilter() {
    outstandingFromDate = document.getElementById('outstandingFromDate').value;
    outstandingToDate = document.getElementById('outstandingToDate').value;
    billwisePage = 1; // Reset to first page
    await switchOutstandingReport(currentReportType);
    showToast('Period filter applied', 'success');
}

// Reset period filter
async function resetPeriodFilter() {
    await initOutstandingPeriod();
    billwisePage = 1;
    await switchOutstandingReport(currentReportType);
    showToast('Period reset to default', 'info');
}

// Switch Outstanding Report Type
async function switchOutstandingReport(reportType) {
    currentReportType = reportType;
    
    // Clear search input when switching reports
    const searchInput = document.getElementById('outstandingSearch');
    if (searchInput) searchInput.value = '';
    
    // Update tab active state
    document.querySelectorAll('.report-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.report === reportType);
    });
    
    // Load data based on report type
    const tbody = document.getElementById('outstandingTableBody');
    tbody.innerHTML = '<tr><td colspan="7" class="loading-cell"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
    
    try {
        // Build period params
        let periodParams = '';
        if (outstandingFromDate) periodParams += `&from_date=${outstandingFromDate}`;
        if (outstandingToDate) periodParams += `&to_date=${outstandingToDate}`;
        
        let url = '';
        if (reportType === 'ledger') {
            url = `/api/data/outstanding?type=${currentPartyType}&company=${encodeURIComponent(selectedCompany)}${periodParams}`;
        } else if (reportType === 'billwise') {
            url = `/api/data/outstanding/billwise?type=${currentPartyType}&company=${encodeURIComponent(selectedCompany)}&page=${billwisePage}&page_size=${billwisePageSize}${periodParams}`;
        } else if (reportType === 'ledgerwise') {
            url = `/api/data/outstanding/ledgerwise?type=${currentPartyType}&company=${encodeURIComponent(selectedCompany)}${periodParams}`;
        } else if (reportType === 'ageing') {
            url = `/api/data/outstanding/ageing?type=${currentPartyType}&company=${encodeURIComponent(selectedCompany)}${periodParams}`;
        } else if (reportType === 'group') {
            url = `/api/data/outstanding/group?type=${currentPartyType}&company=${encodeURIComponent(selectedCompany)}${periodParams}`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        renderOutstandingByType(reportType, result);
        showToast(`Loaded ${reportType} report`, 'success');
    } catch (error) {
        console.error('Failed to load report:', error);
        tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Failed to load data</td></tr>';
    }
}

// Render Outstanding based on report type
function renderOutstandingByType(reportType, result) {
    const thead = document.getElementById('outstandingTableHead');
    const tbody = document.getElementById('outstandingTableBody');
    const title = currentPartyType === 'receivable' ? 'Receivable' : 'Payable';
    
    if (reportType === 'ledger') {
        document.getElementById('outstandingTitle').textContent = `${title} - Ledger Outstanding`;
        thead.innerHTML = `<tr><th>Party Name</th><th class="text-right">Opening</th><th class="text-right">Debit</th><th class="text-right">Credit</th><th class="text-right">Closing</th></tr>`;
        
        const data = result.data || [];
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No data found</td></tr>';
            return;
        }
        tbody.innerHTML = data.map(row => `
            <tr>
                <td>${row.ledger_name || '-'}</td>
                <td class="text-right">${formatCurrency(row.opening || 0)}</td>
                <td class="text-right">${formatCurrency(row.debit || 0)}</td>
                <td class="text-right">${formatCurrency(row.credit || 0)}</td>
                <td class="text-right" style="color: ${(row.closing || 0) >= 0 ? '#16a34a' : '#dc2626'}; font-weight: 500;">${formatCurrency(row.closing || 0)}</td>
            </tr>
        `).join('');
        document.getElementById('outstandingCount').textContent = `${data.length} records`;
        document.getElementById('outstandingTotal').textContent = formatCurrency(Math.abs(result.totals?.closing || 0));
        document.getElementById('outstandingParties').textContent = data.length;
        
    } else if (reportType === 'billwise') {
        document.getElementById('outstandingTitle').textContent = `${title} - Bill-wise Outstanding`;
        thead.innerHTML = `<tr><th>Party Name</th><th>Bill No.</th><th>Bill Date</th><th>Due Date</th><th class="text-right">Pending</th><th class="text-right">Overdue Days</th></tr>`;
        
        const data = result.data || [];
        const pagination = result.pagination || {};
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">No data found</td></tr>';
            return;
        }
        tbody.innerHTML = data.map(row => {
            const sourceLabel = row.source === 'Opening' ? 
                '<span class="source-badge opening">Opening</span>' : 
                (row.source ? `<span class="source-badge">${row.source}</span>` : '');
            return `<tr>
                <td>${row.party_name || '-'}</td>
                <td><div style="display: flex; flex-direction: column;"><span>${row.bill_no || '-'}</span>${sourceLabel}</div></td>
                <td>${row.bill_date || '-'}</td>
                <td>${row.due_date || '-'}</td>
                <td class="text-right" style="color: #dc2626; font-weight: 500;">${formatCurrency(row.pending_amount || 0)}</td>
                <td class="text-right">${row.overdue_days || 0}</td>
            </tr>`;
        }).join('');
        
        // Show pagination info
        const pageInfo = pagination.total_count ? 
            `Page ${pagination.page} of ${pagination.total_pages} (${pagination.total_count} bills)` : 
            `${data.length} bills`;
        document.getElementById('outstandingCount').textContent = pageInfo;
        document.getElementById('outstandingTotal').textContent = formatCurrency(result.totals?.pending_amount || 0);
        document.getElementById('outstandingParties').textContent = pagination.total_count || data.length;
        
        // Render pagination controls
        renderBillwisePagination(pagination);
        
    } else if (reportType === 'ledgerwise') {
        document.getElementById('outstandingTitle').textContent = `${title} - Ledger-wise Outstanding`;
        thead.innerHTML = `<tr><th>Date</th><th>Bill No.</th><th class="text-right">Pending</th><th>Due Date</th><th class="text-right">Overdue</th></tr>`;
        
        const data = result.data || [];
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No data found</td></tr>';
            return;
        }
        
        // Render grouped by party with subtotals (Tally-like format)
        let html = '';
        data.forEach(party => {
            // Party header row
            html += `<tr style="background: var(--primary-light); font-weight: 600;">
                <td colspan="5" style="padding: 0.75rem 1rem; color: var(--primary-dark);">
                    <i class="fas fa-user" style="margin-right: 0.5rem;"></i>${party.party_name}
                </td>
            </tr>`;
            
            // Bill rows
            party.bills.forEach(bill => {
                const sourceLabel = bill.source === 'Opening' ? 
                    '<span class="source-badge opening">Opening</span>' : 
                    (bill.source ? `<span class="source-badge">${bill.source}</span>` : '');
                html += `<tr>
                    <td style="padding-left: 2rem;"><div style="display: flex; flex-direction: column;"><span>${bill.bill_date || '-'}</span>${sourceLabel}</div></td>
                    <td>${bill.bill_no || '-'}</td>
                    <td class="text-right">${formatCurrency(bill.pending_amount || 0)}</td>
                    <td>${bill.due_date || '-'}</td>
                    <td class="text-right">${bill.overdue_days || 0}</td>
                </tr>`;
            });
            
            // Party subtotal row
            html += `<tr style="background: var(--gray-100); font-weight: 500;">
                <td colspan="2" style="text-align: right; padding-right: 1rem;">Subtotal:</td>
                <td class="text-right" style="color: #dc2626;">${formatCurrency(party.party_total || 0)}</td>
                <td colspan="2"></td>
            </tr>`;
        });
        
        tbody.innerHTML = html;
        document.getElementById('outstandingCount').textContent = `${result.totals?.party_count || 0} parties, ${result.totals?.bill_count || 0} bills`;
        document.getElementById('outstandingTotal').textContent = formatCurrency(result.totals?.grand_total || 0);
        document.getElementById('outstandingParties').textContent = result.totals?.party_count || 0;
        
    } else if (reportType === 'ageing') {
        document.getElementById('outstandingTitle').textContent = `${title} - Ageing Analysis`;
        thead.innerHTML = `<tr><th>Party Name</th><th class="text-right">0-30 Days</th><th class="text-right">30-60 Days</th><th class="text-right">60-90 Days</th><th class="text-right">90+ Days</th><th class="text-right">Total</th></tr>`;
        
        const data = result.data || [];
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">No data found</td></tr>';
            return;
        }
        tbody.innerHTML = data.map(row => `
            <tr>
                <td>${row.party_name || '-'}</td>
                <td class="text-right">${formatCurrency(row.days_0_30 || 0)}</td>
                <td class="text-right">${formatCurrency(row.days_30_60 || 0)}</td>
                <td class="text-right">${formatCurrency(row.days_60_90 || 0)}</td>
                <td class="text-right" style="color: #dc2626;">${formatCurrency(row.days_90_plus || 0)}</td>
                <td class="text-right" style="font-weight: 500;">${formatCurrency(row.total || 0)}</td>
            </tr>
        `).join('');
        document.getElementById('outstandingCount').textContent = `${data.length} parties`;
        document.getElementById('outstandingTotal').textContent = formatCurrency(result.totals?.total || 0);
        document.getElementById('outstandingParties').textContent = data.length;
        
    } else if (reportType === 'group') {
        document.getElementById('outstandingTitle').textContent = `${title} - Group Summary`;
        thead.innerHTML = `<tr><th>Group</th><th class="text-right">Parties</th><th class="text-right">Opening</th><th class="text-right">Debit</th><th class="text-right">Credit</th><th class="text-right">Closing</th></tr>`;
        
        const data = result.data || {};
        tbody.innerHTML = `
            <tr style="font-weight: 500; background: var(--gray-50);">
                <td>${result.group_name || '-'}</td>
                <td class="text-right">${data.party_count || 0}</td>
                <td class="text-right">${formatCurrency(data.opening || 0)}</td>
                <td class="text-right">${formatCurrency(data.debit || 0)}</td>
                <td class="text-right">${formatCurrency(data.credit || 0)}</td>
                <td class="text-right" style="color: ${(data.closing || 0) >= 0 ? '#16a34a' : '#dc2626'};">${formatCurrency(data.closing || 0)}</td>
            </tr>
        `;
        document.getElementById('outstandingCount').textContent = '1 group';
        document.getElementById('outstandingTotal').textContent = formatCurrency(Math.abs(data.closing || 0));
        document.getElementById('outstandingParties').textContent = data.party_count || 0;
    }
}

// Render billwise pagination controls
function renderBillwisePagination(pagination) {
    if (!pagination || !pagination.total_pages || pagination.total_pages <= 1) {
        return;
    }
    
    const container = document.getElementById('outstandingTableBody').parentElement.parentElement;
    let paginationDiv = container.querySelector('.billwise-pagination');
    
    if (!paginationDiv) {
        paginationDiv = document.createElement('div');
        paginationDiv.className = 'billwise-pagination';
        paginationDiv.style.cssText = 'display: flex; justify-content: center; gap: 0.5rem; padding: 1rem; border-top: 1px solid var(--gray-200);';
        container.appendChild(paginationDiv);
    }
    
    let html = '';
    
    // Previous button
    html += `<button ${pagination.page === 1 ? 'disabled' : ''} onclick="goToBillwisePage(${pagination.page - 1})" style="padding: 0.5rem 1rem; border: 1px solid var(--gray-300); border-radius: 4px; background: white; cursor: pointer;">
        <i class="fas fa-chevron-left"></i> Prev
    </button>`;
    
    // Page info
    html += `<span style="padding: 0.5rem 1rem; background: var(--gray-100); border-radius: 4px;">
        Page ${pagination.page} of ${pagination.total_pages}
    </span>`;
    
    // Next button
    html += `<button ${pagination.page >= pagination.total_pages ? 'disabled' : ''} onclick="goToBillwisePage(${pagination.page + 1})" style="padding: 0.5rem 1rem; border: 1px solid var(--gray-300); border-radius: 4px; background: white; cursor: pointer;">
        Next <i class="fas fa-chevron-right"></i>
    </button>`;
    
    paginationDiv.innerHTML = html;
}

// Go to specific billwise page
async function goToBillwisePage(page) {
    billwisePage = page;
    await switchOutstandingReport('billwise');
}

// Filter Outstanding table by search term (client-side filtering)
function filterOutstandingTable() {
    // Use global search box
    const searchTerm = document.getElementById('globalSearch').value.toLowerCase().trim();
    const tbody = document.getElementById('outstandingTableBody');
    const rows = tbody.querySelectorAll('tr');
    
    let visibleCount = 0;
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (!searchTerm || text.includes(searchTerm)) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // Update count
    const countEl = document.getElementById('outstandingCount');
    if (countEl) {
        const totalCount = rows.length;
        if (searchTerm) {
            countEl.textContent = `${visibleCount} of ${totalCount} records`;
        }
    }
}

// ========== Ledger Report Functions ==========
let selectedLedger = '';

async function showLedgerView() {
    currentView = 'ledger';
    
    // Update search placeholder
    const searchInput = document.getElementById('globalSearch');
    searchInput.value = '';
    searchInput.placeholder = 'Search ledger transactions...';
    
    // Hide other sections
    document.querySelector('.stats-grid').style.display = 'none';
    document.querySelector('.filters-card').style.display = 'none';
    document.querySelector('.table-card').style.display = 'none';
    document.getElementById('outstandingSection').style.display = 'none';
    document.getElementById('ledgerSection').style.display = 'block';
    
    // Initialize dates
    initLedgerDates();
    
    // Load ledger list and wait for it
    await loadLedgerList();
    showToast(`Loaded ${allLedgers.length} ledgers`, 'success');
}

function initLedgerDates() {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    
    // Set to_date to today
    document.getElementById('ledgerToDate').value = todayStr;
    
    // Set from_date to start of financial year (April 1)
    const year = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
    document.getElementById('ledgerFromDate').value = `${year}-04-01`;
}

let allLedgers = [];

async function loadLedgerList() {
    try {
        const response = await fetch(`/api/data/ledgers?company=${encodeURIComponent(selectedCompany)}`);
        const result = await response.json();
        
        // Handle different response formats
        allLedgers = (result.ledgers || result.data || result || []).map(l => l.name || l);
        console.log(`Loaded ${allLedgers.length} ledgers`);
    } catch (error) {
        console.error('Failed to load ledgers:', error);
        showToast('Failed to load ledger list', 'error');
    }
}

function showLedgerDropdown() {
    filterLedgerDropdown();
}

function filterLedgerDropdown() {
    const input = document.getElementById('ledgerSearchInput');
    const dropdown = document.getElementById('ledgerDropdown');
    const searchTerm = input.value.toLowerCase().trim();
    
    // Filter ledgers
    const filtered = searchTerm ? 
        allLedgers.filter(l => l.toLowerCase().includes(searchTerm)).slice(0, 50) : 
        allLedgers.slice(0, 50);
    
    if (filtered.length === 0) {
        dropdown.innerHTML = '<div style="padding: 0.75rem; color: var(--gray-500);">No ledgers found</div>';
    } else {
        dropdown.innerHTML = filtered.map(name => 
            `<div class="dropdown-item" onclick="selectLedger('${name.replace(/'/g, "\\'")}')" style="padding: 0.5rem 0.75rem; cursor: pointer; border-bottom: 1px solid var(--gray-100);" onmouseover="this.style.background='var(--gray-100)'" onmouseout="this.style.background='white'">${name}</div>`
        ).join('');
    }
    
    dropdown.style.display = 'block';
}

function selectLedger(name) {
    document.getElementById('ledgerSearchInput').value = name;
    document.getElementById('ledgerDropdown').style.display = 'none';
    // Auto-load report when ledger is selected
    loadLedgerReport();
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('ledgerDropdown');
    const input = document.getElementById('ledgerSearchInput');
    if (dropdown && input && !dropdown.contains(e.target) && e.target !== input) {
        dropdown.style.display = 'none';
    }
});

// Reload ledger report if a ledger is already selected (for date changes)
function reloadLedgerIfSelected() {
    const ledgerName = document.getElementById('ledgerSearchInput').value;
    if (ledgerName && allLedgers.includes(ledgerName)) {
        loadLedgerReport();
    }
}

async function loadLedgerReport() {
    const ledgerName = document.getElementById('ledgerSearchInput').value;
    if (!ledgerName) {
        showToast('Please select a ledger', 'warning');
        return;
    }
    
    selectedLedger = ledgerName;
    const fromDate = document.getElementById('ledgerFromDate').value;
    const toDate = document.getElementById('ledgerToDate').value;
    
    const tbody = document.getElementById('ledgerTableBody');
    tbody.innerHTML = '<tr><td colspan="7" class="loading-cell"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
    
    try {
        let url = `/api/data/ledger-report?ledger=${encodeURIComponent(ledgerName)}&company=${encodeURIComponent(selectedCompany)}`;
        if (fromDate) url += `&from_date=${fromDate}`;
        if (toDate) url += `&to_date=${toDate}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        renderLedgerReport(result);
        showToast(`Loaded ${ledgerName}`, 'success');
    } catch (error) {
        console.error('Failed to load ledger report:', error);
        tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Failed to load data</td></tr>';
        showToast('Failed to load ledger report', 'error');
    }
}

function renderLedgerReport(result) {
    const tbody = document.getElementById('ledgerTableBody');
    const transactions = result.transactions || [];
    
    // Update title
    document.getElementById('ledgerTitle').textContent = `${selectedLedger} - Transactions`;
    document.getElementById('ledgerCount').textContent = `${transactions.length} entries`;
    
    // Update summary
    document.getElementById('ledgerOpeningBal').textContent = formatCurrency(result.opening_balance || 0);
    document.getElementById('ledgerDebit').textContent = formatCurrency(result.total_debit || 0);
    document.getElementById('ledgerCredit').textContent = formatCurrency(result.total_credit || 0);
    document.getElementById('ledgerClosingBal').textContent = formatCurrency(result.closing_balance || 0);
    
    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">No transactions found</td></tr>';
        return;
    }
    
    // Render transactions with running balance
    let runningBalance = result.opening_balance || 0;
    let html = '';
    
    // Opening balance row
    html += `<tr style="background: var(--gray-100); font-weight: 500;">
        <td colspan="4">Opening Balance</td>
        <td class="text-right"></td>
        <td class="text-right"></td>
        <td class="text-right">${formatCurrency(runningBalance)}</td>
    </tr>`;
    
    transactions.forEach(txn => {
        const debit = txn.debit || 0;
        const credit = txn.credit || 0;
        runningBalance += debit - credit;
        
        html += `<tr>
            <td>${txn.date || '-'}</td>
            <td>${txn.particulars || '-'}</td>
            <td><span class="source-badge">${txn.voucher_type || '-'}</span></td>
            <td>${txn.voucher_no || '-'}</td>
            <td class="text-right">${debit > 0 ? formatCurrency(debit) : ''}</td>
            <td class="text-right">${credit > 0 ? formatCurrency(credit) : ''}</td>
            <td class="text-right" style="font-weight: 500;">${formatCurrency(runningBalance)}</td>
        </tr>`;
    });
    
    // Closing balance row
    html += `<tr style="background: var(--primary-light); font-weight: 600;">
        <td colspan="4" style="color: var(--primary-dark);">Closing Balance</td>
        <td class="text-right" style="color: var(--primary-dark);">${formatCurrency(result.total_debit || 0)}</td>
        <td class="text-right" style="color: var(--primary-dark);">${formatCurrency(result.total_credit || 0)}</td>
        <td class="text-right" style="color: var(--primary-dark);">${formatCurrency(result.closing_balance || 0)}</td>
    </tr>`;
    
    tbody.innerHTML = html;
}

// Ledger Report Tab Switching
let currentLedgerTab = 'transactions';

function switchLedgerTab(tabType) {
    currentLedgerTab = tabType;
    
    // Update tab buttons
    document.querySelectorAll('[data-ledger-tab]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.ledgerTab === tabType);
    });
    
    // Load data based on tab
    const ledgerName = document.getElementById('ledgerSearchInput').value;
    if (!ledgerName) {
        showToast('Please select a ledger first', 'warning');
        return;
    }
    
    if (tabType === 'transactions') {
        loadLedgerReport();
    } else if (tabType === 'billwise') {
        loadLedgerBillwise();
    }
}

async function loadLedgerBillwise() {
    const ledgerName = document.getElementById('ledgerSearchInput').value;
    if (!ledgerName) return;
    
    const fromDate = document.getElementById('ledgerFromDate').value;
    const toDate = document.getElementById('ledgerToDate').value;
    
    const tbody = document.getElementById('ledgerTableBody');
    const thead = document.getElementById('ledgerTableHead');
    tbody.innerHTML = '<tr><td colspan="7" class="loading-cell"><i class="fas fa-spinner fa-spin"></i> Loading bills...</td></tr>';
    
    try {
        let url = `/api/data/ledger-billwise?ledger=${encodeURIComponent(ledgerName)}&company=${encodeURIComponent(selectedCompany)}`;
        if (fromDate) url += `&from_date=${fromDate}`;
        if (toDate) url += `&to_date=${toDate}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        renderLedgerBillwise(result);
    } catch (error) {
        console.error('Failed to load ledger billwise:', error);
        tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Failed to load bills</td></tr>';
        showToast('Failed to load bills', 'error');
    }
}

function renderLedgerBillwise(result) {
    const tbody = document.getElementById('ledgerTableBody');
    const thead = document.getElementById('ledgerTableHead');
    const bills = result.bills || [];
    
    // Update header
    thead.innerHTML = `<tr>
        <th style="width: 100px;">Date</th>
        <th style="width: 180px;">Ref. No.</th>
        <th class="text-right" style="width: 140px;">Opening Amount</th>
        <th class="text-right" style="width: 140px;">Pending Amount</th>
        <th style="width: 100px;">Due Date</th>
        <th class="text-right" style="width: 80px;">Overdue</th>
    </tr>`;
    
    document.getElementById('ledgerTitle').textContent = `${selectedLedger} - Pending Bills`;
    document.getElementById('ledgerCount').textContent = `${bills.length} bills`;
    
    if (bills.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">No pending bills found</td></tr>';
        return;
    }
    
    let html = '';
    let totalOpening = 0;
    let totalPending = 0;
    
    bills.forEach(bill => {
        const opening = bill.opening_amount || 0;
        const pending = bill.pending_amount || 0;
        totalOpening += Math.abs(opening);
        totalPending += pending;
        
        // Opening Amount with Cr/Dr like Tally
        const openingDisplay = opening > 0 ? `${formatCurrency(opening)} Cr` : (opening < 0 ? `${formatCurrency(Math.abs(opening))} Dr` : '-');
        // Pending Amount with Cr/Dr like Tally
        const pendingDisplay = pending > 0 ? `${formatCurrency(pending)} Cr` : `${formatCurrency(Math.abs(pending))} Dr`;
        
        // Row 1: Main bill row
        html += `<tr>
            <td>${bill.bill_date || '-'}</td>
            <td>${bill.bill_no || '-'}</td>
            <td class="text-right">${openingDisplay}</td>
            <td class="text-right" style="color: ${pending > 0 ? '#dc2626' : '#16a34a'}; font-weight: 500;">${pendingDisplay}</td>
            <td>${bill.due_date || '-'}</td>
            <td class="text-right">${bill.overdue_days || 0}</td>
        </tr>`;
        
        // Row 2: Opening Balance sub-row (like Tally)
        const sourceText = bill.source === 'Opening' ? 'Opening Balance' : (bill.source || 'Transaction');
        const openingAmountCrDr = opening > 0 ? `${formatCurrency(opening)} Cr` : (opening < 0 ? `${formatCurrency(Math.abs(opening))} Dr` : '');
        html += `<tr style="color: var(--gray-500); font-size: 0.85rem;">
            <td style="padding-left: 1rem;">${bill.bill_date || '-'}</td>
            <td style="padding-left: 1rem;">${sourceText}</td>
            <td class="text-right">${openingAmountCrDr}</td>
            <td colspan="3"></td>
        </tr>`;
    });
    
    // Sub Total row
    const totalOpeningDisplay = totalOpening > 0 ? `${formatCurrency(totalOpening)} Cr` : '-';
    const totalPendingDisplay = totalPending > 0 ? `${formatCurrency(totalPending)} Cr` : `${formatCurrency(Math.abs(totalPending))} Dr`;
    html += `<tr style="background: var(--gray-100); font-weight: 600;">
        <td colspan="2" style="text-align: right;">Sub Total:</td>
        <td class="text-right">${totalOpeningDisplay}</td>
        <td class="text-right" style="color: ${totalPending > 0 ? '#dc2626' : '#16a34a'};">${totalPendingDisplay}</td>
        <td colspan="2"></td>
    </tr>`;
    
    // On Account row if exists (like Tally - 2 rows)
    if (result.on_account && result.on_account !== 0) {
        const onAccountDisplay = result.on_account > 0 ? `${formatCurrency(result.on_account)} Dr` : `${formatCurrency(Math.abs(result.on_account))} Cr`;
        // Row 1: On Account main row
        html += `<tr>
            <td>${result.on_account_date || '-'}</td>
            <td>On Account</td>
            <td class="text-right">${onAccountDisplay}</td>
            <td class="text-right" style="color: ${result.on_account > 0 ? '#16a34a' : '#dc2626'}; font-weight: 500;">${onAccountDisplay}</td>
            <td colspan="2"></td>
        </tr>`;
        // Row 2: Opening Balance sub-row
        html += `<tr style="color: var(--gray-500); font-size: 0.85rem;">
            <td style="padding-left: 1rem;">${result.on_account_date || '-'}</td>
            <td style="padding-left: 1rem;">Opening Balance</td>
            <td class="text-right">${onAccountDisplay}</td>
            <td colspan="3"></td>
        </tr>`;
    }
    
    tbody.innerHTML = html;
}
