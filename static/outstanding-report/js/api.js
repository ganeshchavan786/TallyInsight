const api = {
    async getSyncedCompanies() {
        const response = await fetch(`${CONFIG.API_BASE}/synced-companies`);
        return response.json();
    },
    
    async getOutstanding(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.type) queryParams.append('type', params.type);
        if (params.company) queryParams.append('company', params.company);
        const url = `${CONFIG.API_BASE}/outstanding?${queryParams}`;
        const response = await fetch(url);
        return response.json();
    }
};
