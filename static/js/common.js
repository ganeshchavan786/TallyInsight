// Common JavaScript Functions

const API_BASE = '';

// Toast Notifications
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    
    setTimeout(() => toast.remove(), 4000);
}

// API Helper
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || 'Request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Check Tally Status (navbar badge)
async function checkTallyStatus() {
    const badge = document.getElementById('tally-status');
    if (!badge) return;
    
    try {
        const data = await apiCall('/api/health');
        const tallyStatus = data.components?.tally;
        const isConnected = tallyStatus?.status === 'healthy';
        
        if (isConnected) {
            badge.className = 'status-badge online';
            badge.innerHTML = '<span class="dot"></span><span>Tally: Connected</span>';
        } else {
            badge.className = 'status-badge offline';
            badge.innerHTML = '<span class="dot"></span><span>Tally: Disconnected</span>';
        }
    } catch (error) {
        badge.className = 'status-badge offline';
        badge.innerHTML = '<span class="dot"></span><span>Tally: Error</span>';
    }
}

// Format Number
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

// Format Date
function formatDate(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { 
        day: '2-digit', 
        month: 'short', 
        year: 'numeric' 
    });
}

// Format Time
function formatTime(dateStr) {
    if (!dateStr) return '--:--';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-IN', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

// Format Duration
function formatDuration(seconds) {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

// ============================================
// MOBILE MENU FUNCTIONALITY
// ============================================

function initMobileMenu() {
    // Create mobile menu elements if not exist
    if (!document.querySelector('.mobile-sidebar')) {
        const mobileHTML = `
            <div class="mobile-nav-overlay" onclick="closeMobileMenu()"></div>
            <div class="mobile-sidebar">
                <div class="mobile-sidebar-header">
                    <div class="navbar-brand">
                        <i class="fas fa-database"></i>
                        <span>TallySync</span>
                    </div>
                    <button class="mobile-sidebar-close" onclick="closeMobileMenu()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <nav class="mobile-sidebar-nav">
                    <a href="/sync.html" class="mobile-nav-link ${location.pathname.includes('sync') ? 'active' : ''}">
                        <i class="fas fa-sync"></i> Sync Settings
                    </a>
                    <a href="/dashboard.html" class="mobile-nav-link ${location.pathname.includes('dashboard') ? 'active' : ''}">
                        <i class="fas fa-chart-bar"></i> Dashboard
                    </a>
                </nav>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', mobileHTML);
    }
    
    // Add hamburger button to navbar if not exist
    const navbar = document.querySelector('.navbar');
    if (navbar && !navbar.querySelector('.hamburger-btn')) {
        const hamburger = document.createElement('button');
        hamburger.className = 'hamburger-btn';
        hamburger.innerHTML = '<i class="fas fa-bars"></i>';
        hamburger.onclick = openMobileMenu;
        navbar.insertBefore(hamburger, navbar.firstChild);
    }
}

function openMobileMenu() {
    document.querySelector('.mobile-nav-overlay')?.classList.add('active');
    document.querySelector('.mobile-sidebar')?.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeMobileMenu() {
    document.querySelector('.mobile-nav-overlay')?.classList.remove('active');
    document.querySelector('.mobile-sidebar')?.classList.remove('active');
    document.body.style.overflow = '';
}

// ============================================
// OFFLINE DETECTION
// ============================================

function initOfflineDetection() {
    // Create offline banner if not exist
    if (!document.querySelector('.offline-banner')) {
        const banner = document.createElement('div');
        banner.className = 'offline-banner';
        banner.innerHTML = '<i class="fas fa-wifi-slash"></i> You are offline. Some features may not work.';
        document.body.insertBefore(banner, document.body.firstChild);
    }
    
    function updateOnlineStatus() {
        const banner = document.querySelector('.offline-banner');
        if (navigator.onLine) {
            banner?.classList.remove('active');
            document.body.classList.remove('offline');
        } else {
            banner?.classList.add('active');
            document.body.classList.add('offline');
        }
    }
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();
}

// ============================================
// PWA INSTALL PROMPT
// ============================================

let deferredPrompt = null;

function initPWAInstall() {
    // Create install banner if not exist
    if (!document.querySelector('.pwa-install-banner')) {
        const banner = document.createElement('div');
        banner.className = 'pwa-install-banner';
        banner.innerHTML = `
            <div class="pwa-install-content">
                <div class="pwa-install-icon">
                    <i class="fas fa-download"></i>
                </div>
                <div class="pwa-install-text">
                    <h4>Install TallySync</h4>
                    <p>Add to home screen for quick access</p>
                </div>
            </div>
            <div class="pwa-install-actions">
                <button class="pwa-install-btn secondary" onclick="dismissPWAInstall()">Not now</button>
                <button class="pwa-install-btn primary" onclick="installPWA()">Install</button>
            </div>
        `;
        document.body.appendChild(banner);
    }
    
    // Listen for install prompt
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        
        // Show install banner after 3 seconds
        setTimeout(() => {
            if (!localStorage.getItem('pwa-install-dismissed')) {
                document.querySelector('.pwa-install-banner')?.classList.add('active');
            }
        }, 3000);
    });
    
    // Hide banner if already installed
    window.addEventListener('appinstalled', () => {
        document.querySelector('.pwa-install-banner')?.classList.remove('active');
        deferredPrompt = null;
    });
}

async function installPWA() {
    if (!deferredPrompt) return;
    
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
        showToast('App installed successfully!', 'success');
    }
    
    deferredPrompt = null;
    document.querySelector('.pwa-install-banner')?.classList.remove('active');
}

function dismissPWAInstall() {
    document.querySelector('.pwa-install-banner')?.classList.remove('active');
    localStorage.setItem('pwa-install-dismissed', 'true');
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

function initKeyboardShortcuts() {
    // Create keyboard hint if not exist
    if (!document.querySelector('.keyboard-shortcuts-hint')) {
        const hint = document.createElement('div');
        hint.className = 'keyboard-shortcuts-hint';
        hint.innerHTML = '<kbd>?</kbd> Keyboard shortcuts';
        document.body.appendChild(hint);
    }
    
    document.addEventListener('keydown', (e) => {
        // Ignore if typing in input
        if (e.target.matches('input, textarea, select')) return;
        
        // Alt + number for navigation
        if (e.altKey) {
            switch (e.key) {
                case '1':
                    e.preventDefault();
                    window.location.href = '/sync.html';
                    break;
                case '2':
                    e.preventDefault();
                    window.location.href = '/dashboard.html';
                    break;
            }
        }
        
        // Ctrl + R for refresh
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            location.reload();
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            closeMobileMenu();
            document.querySelector('.bottom-sheet.active')?.classList.remove('active');
            // Close SweetAlert if open
            if (typeof Swal !== 'undefined') Swal.close();
        }
        
        // ? for shortcuts help
        if (e.key === '?') {
            showKeyboardShortcutsHelp();
        }
    });
}

function showKeyboardShortcutsHelp() {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: 'Keyboard Shortcuts',
            html: `
                <table style="width:100%; text-align:left; font-size:0.9rem;">
                    <tr><td><kbd>Alt</kbd> + <kbd>1</kbd></td><td>Go to Sync</td></tr>
                    <tr><td><kbd>Alt</kbd> + <kbd>2</kbd></td><td>Go to Dashboard</td></tr>
                    <tr><td><kbd>Ctrl</kbd> + <kbd>R</kbd></td><td>Refresh page</td></tr>
                    <tr><td><kbd>Esc</kbd></td><td>Close modals</td></tr>
                    <tr><td><kbd>?</kbd></td><td>Show this help</td></tr>
                </table>
            `,
            icon: 'info',
            confirmButtonColor: '#3b82f6'
        });
    }
}

// ============================================
// STANDALONE MODE DETECTION
// ============================================

function isStandaloneMode() {
    return window.matchMedia('(display-mode: standalone)').matches ||
           window.navigator.standalone === true;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkTallyStatus();
    setInterval(checkTallyStatus, 30000);
    
    // Initialize mobile & PWA features
    initMobileMenu();
    initOfflineDetection();
    initPWAInstall();
    initKeyboardShortcuts();
    
    // Log if running in standalone mode
    if (isStandaloneMode()) {
        console.log('Running in standalone PWA mode');
    }
});
