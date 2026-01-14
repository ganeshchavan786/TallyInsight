/**
 * ================================================================================
 * TALLY SYNC - ELECTRON MAIN PROCESS
 * ================================================================================
 * Purpose: Main process for Electron app
 * - Spawns Python backend as child process
 * - Creates main browser window
 * - Handles app lifecycle (startup, shutdown)
 * - System tray integration
 * ================================================================================
 */

const electron = require('electron');
const app = electron.app;
const BrowserWindow = electron.BrowserWindow;
const Tray = electron.Tray;
const Menu = electron.Menu;
const dialog = electron.dialog;
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

// Keep references to prevent garbage collection
let mainWindow = null;
let tray = null;
let pythonProcess = null;
let isQuitting = false;

// Check if running in development or production
const isDev = !app.isPackaged;

// Configuration
const CONFIG = {
    pythonExe: isDev 
        ? path.join(__dirname, '..', 'dist', 'TallySync.exe')
        : path.join(process.resourcesPath, 'backend', 'TallySync.exe'),
    backendUrl: 'http://127.0.0.1:8000',
    healthCheckUrl: 'http://127.0.0.1:8000/api/health',
    startupTimeout: 60000, // 60 seconds
    healthCheckInterval: 2000, // 2 seconds
};

/**
 * Start Python backend process
 */
function startPythonBackend() {
    return new Promise((resolve, reject) => {
        console.log('Starting Python backend...');
        console.log('Python exe path:', CONFIG.pythonExe);

        // Check if exe exists
        const fs = require('fs');
        if (!fs.existsSync(CONFIG.pythonExe)) {
            reject(new Error(`Python backend not found: ${CONFIG.pythonExe}`));
            return;
        }

        // Spawn Python process
        pythonProcess = spawn(CONFIG.pythonExe, [], {
            cwd: path.dirname(CONFIG.pythonExe),
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
        });

        pythonProcess.stdout.on('data', (data) => {
            console.log(`[Python] ${data.toString().trim()}`);
        });

        pythonProcess.stderr.on('data', (data) => {
            console.error(`[Python Error] ${data.toString().trim()}`);
        });

        pythonProcess.on('error', (err) => {
            console.error('Failed to start Python backend:', err);
            reject(err);
        });

        pythonProcess.on('exit', (code) => {
            console.log(`Python backend exited with code ${code}`);
            pythonProcess = null;
            
            if (!isQuitting) {
                // Unexpected exit - show error
                dialog.showErrorBox('Backend Error', 
                    'Python backend stopped unexpectedly. The application will close.');
                app.quit();
            }
        });

        // Wait for backend to be ready
        waitForBackend(CONFIG.startupTimeout)
            .then(() => {
                console.log('Python backend is ready!');
                resolve();
            })
            .catch((err) => {
                console.error('Backend startup timeout:', err);
                stopPythonBackend();
                reject(err);
            });
    });
}

/**
 * Wait for backend to respond to health check
 */
function waitForBackend(timeout) {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();
        
        const checkHealth = () => {
            http.get(CONFIG.healthCheckUrl, (res) => {
                if (res.statusCode === 200) {
                    resolve();
                } else {
                    retry();
                }
            }).on('error', () => {
                retry();
            });
        };

        const retry = () => {
            if (Date.now() - startTime > timeout) {
                reject(new Error('Backend startup timeout'));
            } else {
                setTimeout(checkHealth, CONFIG.healthCheckInterval);
            }
        };

        checkHealth();
    });
}

/**
 * Stop Python backend process
 */
function stopPythonBackend() {
    if (pythonProcess) {
        console.log('Stopping Python backend...');
        pythonProcess.kill('SIGTERM');
        
        // Force kill after 5 seconds
        setTimeout(() => {
            if (pythonProcess) {
                pythonProcess.kill('SIGKILL');
            }
        }, 5000);
    }
}

/**
 * Create main application window
 */
function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        minWidth: 1024,
        minHeight: 768,
        title: 'TallySync',
        icon: path.join(__dirname, 'assets', 'icon.ico'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
        show: false, // Don't show until ready
    });

    // Load the app from Python backend
    mainWindow.loadURL(`${CONFIG.backendUrl}/sync.html`);

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // Handle window close - minimize to tray instead
    mainWindow.on('close', (event) => {
        if (!isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Open DevTools in development
    // mainWindow.webContents.openDevTools();
}

/**
 * Create system tray icon
 */
function createTray() {
    const iconPath = path.join(__dirname, 'assets', 'icon.png');
    
    // Use default icon if custom not found
    const fs = require('fs');
    if (!fs.existsSync(iconPath)) {
        console.log('Tray icon not found, skipping tray creation');
        return;
    }

    tray = new Tray(iconPath);
    
    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Open TallySync',
            click: () => {
                if (mainWindow) {
                    mainWindow.show();
                }
            }
        },
        { type: 'separator' },
        {
            label: 'Sync Now',
            click: () => {
                if (mainWindow) {
                    mainWindow.show();
                    mainWindow.webContents.executeJavaScript('loadCompanies(); loadSyncedCompanies();');
                }
            }
        },
        { type: 'separator' },
        {
            label: 'Exit',
            click: () => {
                isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setToolTip('TallySync - Tally Database Loader');
    tray.setContextMenu(contextMenu);

    tray.on('double-click', () => {
        if (mainWindow) {
            mainWindow.show();
        }
    });
}

/**
 * App ready event
 */
app.whenReady().then(async () => {
    try {
        // Start Python backend first
        await startPythonBackend();
        
        // Create window and tray
        createMainWindow();
        createTray();
        
    } catch (error) {
        console.error('Startup error:', error);
        dialog.showErrorBox('Startup Error', 
            `Failed to start TallySync:\n\n${error.message}\n\nPlease check if another instance is already running.`);
        app.quit();
    }
});

/**
 * Handle all windows closed
 */
app.on('window-all-closed', () => {
    // On macOS, keep app running in menu bar
    if (process.platform !== 'darwin') {
        // Don't quit - keep running in tray
    }
});

/**
 * Handle app activation (macOS)
 */
app.on('activate', () => {
    if (mainWindow === null) {
        createMainWindow();
    } else {
        mainWindow.show();
    }
});

/**
 * Handle app quit
 */
app.on('before-quit', () => {
    isQuitting = true;
});

app.on('quit', () => {
    stopPythonBackend();
});

/**
 * Prevent multiple instances
 */
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        // Focus existing window
        if (mainWindow) {
            if (mainWindow.isMinimized()) {
                mainWindow.restore();
            }
            mainWindow.show();
            mainWindow.focus();
        }
    });
}
