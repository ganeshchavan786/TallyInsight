// Main Application JavaScript for Tally Voucher Report

// State
let allVouchers = [];
let filteredVouchers = [];
let currentPage = 1;
let pageSize = CONFIG.DEFAULT_PAGE_SIZE;
let sortColumn = 'date';
let sortDirection = 'desc';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeDates();
    loadCompanyInfo();
    loadVouchers();
    setupEventListeners();
});

// Setup Event Listeners
function setupEventListeners() {
    // Global search
    const searchInput = document.getElementById('globalSearch');
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            filterVouchers();
        }, 300);
    });
    
    // Navigation links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.dataset.view;
            setActiveNav(link);
            filterByType(view);
        });
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

// Initialize Dates
function initializeDates() {
    document.getElementById('fromDate').value = CONFIG.DEFAULT_FROM_DATE;
    document.getElementById('toDate').value = CONFIG.DEFAULT_TO_DATE;
}

// Load Company Info
async function loadCompanyInfo() {
    try {
        const data = await api.getSyncedCompanies();
        if (data.companies && data.companies.length > 0) {
            document.getElementById('currentCompany').textContent = data.companies[0].company_name;
        }
    } catch (error) {
        console.error('Failed to load company info:', error);
    }
}

// Load Vouchers
async function loadVouchers() {
    showLoading();
    
    try {
        const fromDate = document.getElementById('fromDate').value;
        const toDate = document.getElementById('toDate').value;
        const voucherType = document.getElementById('voucherType').value;
        
        // Fetch all vouchers (paginated from API)
        allVouchers = await fetchAllVouchers({
            from_date: fromDate,
            to_date: toDate,
            voucher_type: voucherType
        });
        
        filterVouchers();
        updateStats();
        showToast('Vouchers loaded successfully', 'success');
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
                <td colspan="7" class="loading-cell">
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
                <td class="sticky-col">${formatDate(v.date)}</td>
                <td><span class="voucher-type-tag ${typeClass}">${v.voucher_type}</span></td>
                <td>${v.voucher_number || '-'}</td>
                <td>${v.party_name || '-'}</td>
                <td class="text-right ${amount >= 0 ? 'amount-positive' : 'amount-negative'}">
                    ${formatCurrency(Math.abs(amount))}
                </td>
                <td><span class="narration-text" title="${escapeHtml(v.narration || '')}">${truncate(v.narration, 40)}</span></td>
                <td class="sticky-col-right">
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
            <td colspan="7" class="loading-cell">
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
            <td colspan="7" class="loading-cell">
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
