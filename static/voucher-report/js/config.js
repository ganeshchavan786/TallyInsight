// Configuration for Tally Voucher Report
// API URL is automatically detected based on current location
const CONFIG = {
    // API Base URL - Auto-detect from current page location
    API_BASE_URL: window.location.origin,
    
    // Default date range (Financial Year)
    DEFAULT_FROM_DATE: '2025-04-01',
    DEFAULT_TO_DATE: '2026-03-31',
    
    // Pagination
    DEFAULT_PAGE_SIZE: 50,
    
    // Date format
    DATE_FORMAT: 'DD-MMM-YYYY',
    
    // Currency
    CURRENCY_SYMBOL: '₹',
    CURRENCY_LOCALE: 'en-IN'
};

// Log API URL for debugging
console.log('Voucher Report API URL:', CONFIG.API_BASE_URL);
