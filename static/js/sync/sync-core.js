// ==========================================
// SYNC CORE - Global Variables, Tab Switching, Initialize
// ==========================================

// Global Variables
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
        // Update UI to show saved interval
        const radioBtn = document.querySelector(`input[name="sync-interval"][value="${syncIntervalMinutes}"]`);
        if (radioBtn) radioBtn.checked = true;
    }
    
    // Load auto sync setting
    const autoSyncEnabled = localStorage.getItem('autoSyncEnabled') === 'true';
    const autoSyncToggle = document.getElementById('auto-sync-toggle');
    if (autoSyncToggle) {
        autoSyncToggle.checked = autoSyncEnabled;
        updateAutoSyncStatus(autoSyncEnabled);
        if (autoSyncEnabled) {
            startAutoSync();
        }
    }
});
