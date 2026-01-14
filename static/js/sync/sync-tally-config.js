// ==========================================
// SYNC TALLY CONFIG - Tally Configuration Tab Functions
// ==========================================
/*
================================================================================
DEVELOPER NOTES
================================================================================
File: sync-tally-config.js
Purpose: Handle Tally Configuration tab (connection settings)

FUNCTIONS:
----------
1. loadTallyConfig() - Load Tally host/port from /api/config
2. checkTallyConnectionStatus() - Check and display connection status
3. saveTallyConfig() - Save config and auto-test connection
4. testTallyConnection() - Manual test with SweetAlert feedback

TALLY CONNECTION:
-----------------
- Default: localhost:9000
- Tally must be running with ODBC server enabled
- Port 9000 is Tally's default XML/ODBC port

UI ELEMENTS:
------------
- Host input: Tally server address (usually localhost)
- Port input: Tally port (usually 9000)
- Save button: Saves config and tests connection
- Test Connection button: Tests without saving
- Connection Status: Shows connected/disconnected with details

STATUS DISPLAY:
---------------
Connected: Green checkmark, shows server/port/current company
Disconnected: Red X, shows error message
Checking: Spinner animation

ERROR HANDLING:
---------------
- Connection failed: SweetAlert with troubleshooting checklist
- Success: SweetAlert with green confirmation

API ENDPOINTS:
--------------
- GET /api/config - Get current configuration
- PUT /api/config - Update configuration
- POST /api/config/tally/test - Test Tally connection
- GET /api/health - Get health status including Tally

DEPENDENCIES:
-------------
- Uses: apiCall(), showToast() (from common.js)
- Uses: Swal (SweetAlert2 library)
================================================================================
*/

// Load Tally Config from API
async function loadTallyConfig() {
    try {
        const config = await apiCall('/api/config');
        
        document.getElementById('tally-host').value = config.tally?.server || 'localhost';
        document.getElementById('tally-port').value = config.tally?.port || 9000;
        
        // Check connection status
        checkTallyConnectionStatus();
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

// Check Tally Connection Status
async function checkTallyConnectionStatus() {
    const statusIcon = document.querySelector('#connection-status .status-icon');
    const statusText = document.getElementById('conn-status-text');
    const statusDetail = document.getElementById('conn-status-detail');
    const connectionDetails = document.getElementById('connection-details');
    
    statusIcon.className = 'status-icon checking';
    statusIcon.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    statusText.textContent = 'Checking connection...';
    statusDetail.textContent = 'Please wait';
    
    try {
        const health = await apiCall('/api/health');
        const tallyStatus = health.components?.tally;
        const isConnected = tallyStatus?.status === 'healthy';
        
        if (isConnected) {
            statusIcon.className = 'status-icon connected';
            statusIcon.innerHTML = '<i class="fas fa-check"></i>';
            statusText.textContent = 'Connected';
            statusDetail.textContent = tallyStatus.message || 'Tally is running and accessible';
            connectionDetails.style.display = 'block';
            
            document.getElementById('detail-server').textContent = tallyStatus.server || 'localhost';
            document.getElementById('detail-port').textContent = tallyStatus.port || '9000';
            
            // Get current company from companies API
            try {
                const companies = await apiCall('/api/data/companies');
                document.getElementById('detail-company').textContent = companies.current_company || 'N/A';
            } catch {
                document.getElementById('detail-company').textContent = 'N/A';
            }
        } else {
            statusIcon.className = 'status-icon disconnected';
            statusIcon.innerHTML = '<i class="fas fa-times"></i>';
            statusText.textContent = 'Disconnected';
            statusDetail.textContent = tallyStatus?.message || 'Cannot connect to Tally';
            connectionDetails.style.display = 'none';
        }
    } catch (error) {
        statusIcon.className = 'status-icon disconnected';
        statusIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        statusText.textContent = 'Error';
        statusDetail.textContent = error.message;
        connectionDetails.style.display = 'none';
    }
}

// Save Tally Config and Test Connection
async function saveTallyConfig() {
    const host = document.getElementById('tally-host').value;
    const port = document.getElementById('tally-port').value;
    
    if (!host || !port) {
        showToast('Please fill all fields', 'error');
        return;
    }
    
    try {
        // Step 1: Save config
        await apiCall('/api/config', {
            method: 'PUT',
            body: JSON.stringify({ 
                tally: { 
                    server: host, 
                    port: parseInt(port) 
                } 
            })
        });
        showToast('Configuration saved, testing connection...', 'info');
        
        // Step 2: Auto test connection
        const result = await apiCall('/api/config/tally/test', { method: 'POST' });
        
        if (result.connected) {
            showToast('Connection successful!', 'success');
        } else {
            showToast('Connection failed: ' + (result.error || 'Tally not responding'), 'error');
        }
        
        // Step 3: Update status display
        checkTallyConnectionStatus();
    } catch (error) {
        showToast(`Save failed: ${error.message}`, 'error');
    }
}

// Test Tally Connection
async function testTallyConnection() {
    showToast('Testing connection...', 'info');
    
    try {
        const result = await apiCall('/api/config/tally/test', { method: 'POST' });
        
        if (result.connected) {
            showToast('Connection successful!', 'success');
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'success',
                    title: '<strong style="color: #28a745;">Connected!</strong>',
                    html: '<p style="font-size: 16px;"><strong>Tally is running</strong> and accessible.</p>',
                    confirmButtonColor: '#28a745',
                    confirmButtonText: 'OK'
                });
            }
        } else {
            showToast('Connection failed: ' + (result.error || 'Unknown error'), 'error');
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'error',
                    title: '<strong style="color: #dc3545;">Connection Failed</strong>',
                    html: '<p style="font-size: 16px;"><strong style="color: #721c24;">Unable to connect to Tally.</strong></p><p>Please check:</p><ul style="text-align: left;"><li>Tally is <strong>running</strong></li><li>Tally port is <strong>9000</strong></li><li>Tally has companies <strong>open</strong></li></ul>',
                    confirmButtonColor: '#dc3545',
                    confirmButtonText: 'OK'
                });
            }
        }
        
        checkTallyConnectionStatus();
    } catch (error) {
        showToast(`Connection test failed: ${error.message}`, 'error');
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: '<strong style="color: #dc3545;">Connection Failed</strong>',
                html: '<p style="font-size: 16px;"><strong style="color: #721c24;">Unable to connect to Tally.</strong></p><p>Error: ' + error.message + '</p><p>Please check:</p><ul style="text-align: left;"><li>Tally is <strong>running</strong></li><li>Tally port is <strong>9000</strong></li><li>Tally has companies <strong>open</strong></li></ul>',
                confirmButtonColor: '#dc3545',
                confirmButtonText: 'OK'
            });
        }
    }
}
