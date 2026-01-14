/**
 * ================================================================================
 * TALLY SYNC - ELECTRON PRELOAD SCRIPT
 * ================================================================================
 * Purpose: Preload script for secure context bridge
 * - Exposes safe APIs to renderer process
 * - Handles IPC communication
 * ================================================================================
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to renderer
contextBridge.exposeInMainWorld('electronAPI', {
    // App info
    getVersion: () => process.env.npm_package_version || '1.0.0',
    
    // Window controls
    minimize: () => ipcRenderer.send('window-minimize'),
    maximize: () => ipcRenderer.send('window-maximize'),
    close: () => ipcRenderer.send('window-close'),
    
    // Platform info
    platform: process.platform,
    
    // Check if running in Electron
    isElectron: true,
});

console.log('Preload script loaded');
