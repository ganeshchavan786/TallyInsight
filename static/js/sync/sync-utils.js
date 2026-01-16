// ==========================================
// SYNC UTILS - Date/Period Utilities & Navigation Helpers
// ==========================================
/*
================================================================================
DEVELOPER NOTES
================================================================================
File: sync-utils.js
Purpose: Utility functions for date formatting, period extraction, navigation

FUNCTIONS:
----------
1. formatDateTimeShort(dateStr) - Format: "11 Jan 12:39 pm"
2. formatDateDisplay(dateStr) - Format: "1 Apr 2025"
3. formatDate(dateStr) - Format: "YYYY-MM-DD" for API
4. parseTallyDate(dateStr) - Parse Tally date formats
5. extractPeriodFromName(name) - Extract FY from company name
6. goToCompanyDashboard(name) - Navigate to dashboard.html
7. goToCompanyAudit(name) - Navigate to audit.html
8. toggleDropdown(id) - Toggle dropdown menu
9. closeAllDropdowns() - Close all open dropdowns
10. editPeriod(name) - Show period edit modal
11. savePeriod(name) - Save edited period

BUSINESS LOGIC:
---------------
- Company names often contain financial year (e.g., "MATOSHRI 18-24")
- extractPeriodFromName() parses this to get Apr 2018 - Mar 2024
- Tally dates come in formats: "1-Apr-25", "2025-04-01", "1-Apr-2025"
- parseTallyDate() converts all formats to YYYY-MM-DD

DEPENDENCIES:
-------------
- Uses global: companyPeriods (from sync-core.js)
- Uses: showToast() (from common.js)
================================================================================
*/

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

// Extract period from company name pattern like "MATOSHRI ENTERPRISES 18-24" or "Company 25-26"
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

// Format date for API
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toISOString().split('T')[0];
}

// Edit Period for a company (pencil button)
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
