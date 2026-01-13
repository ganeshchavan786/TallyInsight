// API Service for Tally Voucher Report

const api = {
    // Base fetch wrapper
    async fetch(endpoint, options = {}) {
        const url = `${CONFIG.API_BASE_URL}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API Error: ${endpoint}`, error);
            throw error;
        }
    },
    
    // Get vouchers with filters
    async getVouchers(params = {}) {
        const queryParams = new URLSearchParams();
        
        if (params.voucher_type) queryParams.append('voucher_type', params.voucher_type);
        if (params.from_date) queryParams.append('from_date', params.from_date);
        if (params.to_date) queryParams.append('to_date', params.to_date);
        if (params.party_name) queryParams.append('party_name', params.party_name);
        if (params.company) queryParams.append('company', params.company);
        if (params.search) queryParams.append('search', params.search);
        if (params.skip !== undefined) queryParams.append('skip', params.skip);
        if (params.limit !== undefined) queryParams.append('limit', params.limit);
        
        const query = queryParams.toString();
        return this.fetch(`/api/data/vouchers${query ? '?' + query : ''}`);
    },
    
    // Get voucher details by GUID
    async getVoucherDetails(guid) {
        return this.fetch(`/api/data/vouchers/${guid}/details`);
    },
    
    // Get voucher summary/stats
    async getVoucherStats(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.from_date) queryParams.append('from_date', params.from_date);
        if (params.to_date) queryParams.append('to_date', params.to_date);
        
        const query = queryParams.toString();
        return this.fetch(`/api/data/vouchers/stats${query ? '?' + query : ''}`);
    },
    
    // Get synced companies
    async getSyncedCompanies() {
        return this.fetch('/api/data/synced-companies');
    },
    
    // Health check
    async healthCheck() {
        return this.fetch('/api/health');
    }
};
