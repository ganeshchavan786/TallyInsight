let selectedType = 'receivable';
let selectedCompany = '';
let allData = [];

document.addEventListener('DOMContentLoaded', () => {
    initFromUrl();
    loadCompanies();
    setupSubmenuListeners();
    loadOutstanding();
});

function initFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const type = params.get('type');
    if (type === 'receivable' || type === 'payable') {
        selectedType = type;
        updateActiveSubmenu();
    }
}

function updateActiveSubmenu() {
    document.querySelectorAll('.submenu-link').forEach(link => {
        link.classList.remove('active');
        if (link.dataset.type === selectedType) {
            link.classList.add('active');
        }
    });
    document.getElementById('pageTitle').textContent = 
        selectedType === 'receivable' ? 'Receivable Outstanding' : 'Payable Outstanding';
}

function setupSubmenuListeners() {
    document.querySelectorAll('.submenu-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const type = link.dataset.type;
            if (type) {
                selectedType = type;
                updateActiveSubmenu();
                loadOutstanding();
                history.pushState({}, '', `?type=${type}`);
            }
        });
    });
}

function toggleSubmenu(event) {
    event.preventDefault();
    const navItem = event.currentTarget.parentElement;
    const submenu = navItem.querySelector('.submenu');
    navItem.classList.toggle('open');
    submenu.classList.toggle('show');
}

async function loadCompanies() {
    try {
        const data = await api.getSyncedCompanies();
        const select = document.getElementById('companySelect');
        if (data.companies && data.companies.length > 0) {
            data.companies.forEach(company => {
                const option = document.createElement('option');
                option.value = company.name;
                option.textContent = company.name;
                select.appendChild(option);
            });
            selectedCompany = data.companies[0].name;
            select.value = selectedCompany;
            document.getElementById('currentCompany').textContent = selectedCompany;
        }
    } catch (error) {
        console.error('Failed to load companies:', error);
    }
}

function changeCompany() {
    const select = document.getElementById('companySelect');
    selectedCompany = select.value;
    document.getElementById('currentCompany').textContent = selectedCompany || 'All Companies';
    loadOutstanding();
}

async function loadOutstanding() {
    showLoading();
    try {
        const data = await api.getOutstanding({
            type: selectedType,
            company: selectedCompany
        });
        allData = data.data || [];
        renderTable();
        updateStats();
    } catch (error) {
        console.error('Failed to load outstanding:', error);
        showError('Failed to load data');
    }
}

function renderTable() {
    const tbody = document.getElementById('tableBody');
    if (allData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No data found</td></tr>';
        return;
    }
    tbody.innerHTML = allData.map(row => `
        <tr>
            <td>${row.ledger_name || row.party_name || '-'}</td>
            <td class="text-right">${formatAmount(row.opening || 0)}</td>
            <td class="text-right">${formatAmount(row.debit || 0)}</td>
            <td class="text-right">${formatAmount(row.credit || 0)}</td>
            <td class="text-right ${row.closing >= 0 ? 'amount-positive' : 'amount-negative'}">${formatAmount(row.closing || 0)}</td>
        </tr>
    `).join('');
    document.getElementById('recordCount').textContent = `${allData.length} records`;
}

function updateStats() {
    const total = allData.reduce((sum, row) => sum + (row.closing || 0), 0);
    document.getElementById('totalAmount').textContent = formatCurrency(Math.abs(total));
    document.getElementById('totalParties').textContent = allData.length;
}

function formatAmount(value) {
    return new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
}

function formatCurrency(value) {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2 }).format(value);
}

function showLoading() {
    document.getElementById('tableBody').innerHTML = '<tr><td colspan="5" class="loading-cell"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
}

function showError(msg) {
    document.getElementById('tableBody').innerHTML = `<tr><td colspan="5" class="loading-cell">${msg}</td></tr>`;
}

function filterTable() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const filtered = allData.filter(row => 
        (row.ledger_name || row.party_name || '').toLowerCase().includes(search)
    );
    const tbody = document.getElementById('tableBody');
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No matching records</td></tr>';
        return;
    }
    tbody.innerHTML = filtered.map(row => `
        <tr>
            <td>${row.ledger_name || row.party_name || '-'}</td>
            <td class="text-right">${formatAmount(row.opening || 0)}</td>
            <td class="text-right">${formatAmount(row.debit || 0)}</td>
            <td class="text-right">${formatAmount(row.credit || 0)}</td>
            <td class="text-right ${row.closing >= 0 ? 'amount-positive' : 'amount-negative'}">${formatAmount(row.closing || 0)}</td>
        </tr>
    `).join('');
    document.getElementById('recordCount').textContent = `${filtered.length} records`;
}

function exportData() {
    alert('Export feature coming soon');
}
