# Software Requirements Specification (SRS)
# Tally Database Loader - Desktop Application

**Document Version:** 1.0  
**Date:** 2026-01-14  
**Project:** Electron + Python Hybrid Desktop App

---

## 1. Introduction

### 1.1 Purpose
This document specifies the requirements for converting the existing Tally Database Loader web application into a standalone desktop application using Electron.js as the frontend wrapper and Python FastAPI as the backend service.

### 1.2 Scope
The desktop application will:
- Run as a standalone Windows executable (.exe)
- Bundle Python backend with Electron frontend
- Provide all existing web functionality in a desktop environment
- Auto-start Python server on application launch
- Auto-stop Python server on application close

### 1.3 Definitions

| Term | Definition |
|------|------------|
| **Electron** | Framework for building cross-platform desktop apps with web technologies |
| **FastAPI** | Python web framework for building APIs |
| **PyInstaller** | Tool to convert Python scripts into standalone executables |
| **IPC** | Inter-Process Communication between Electron and Python |

---

## 2. Overall Description

### 2.1 Product Perspective

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DESKTOP APPLICATION ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                    ELECTRON SHELL                           │     │
│  │  ┌──────────────────────────────────────────────────────┐  │     │
│  │  │              Main Process (main.js)                   │  │     │
│  │  │  - Window management                                  │  │     │
│  │  │  - Python process spawning                            │  │     │
│  │  │  - System tray integration                            │  │     │
│  │  │  - Auto-updater                                       │  │     │
│  │  └──────────────────────────────────────────────────────┘  │     │
│  │                          │                                  │     │
│  │                          ▼                                  │     │
│  │  ┌──────────────────────────────────────────────────────┐  │     │
│  │  │            Renderer Process (BrowserWindow)           │  │     │
│  │  │  ┌────────────────────────────────────────────────┐  │  │     │
│  │  │  │         Existing HTML/CSS/JS Frontend          │  │  │     │
│  │  │  │  - sync.html, dashboard.html, audit.html       │  │  │     │
│  │  │  │  - static/js/sync/*.js                         │  │  │     │
│  │  │  │  - static/css/*.css                            │  │  │     │
│  │  │  └────────────────────────────────────────────────┘  │  │     │
│  │  └──────────────────────────────────────────────────────┘  │     │
│  └────────────────────────────────────────────────────────────┘     │
│                              │                                       │
│                              │ HTTP (localhost:8000)                │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                    PYTHON BACKEND (.exe)                    │     │
│  │  ┌──────────────────────────────────────────────────────┐  │     │
│  │  │              FastAPI Server (run.py)                  │  │     │
│  │  │  - Controllers (sync, data, config, health)           │  │     │
│  │  │  - Services (sync, database, tally, xml_builder)      │  │     │
│  │  │  - SQLite Database (tally.db)                         │  │     │
│  │  └──────────────────────────────────────────────────────┘  │     │
│  └────────────────────────────────────────────────────────────┘     │
│                              │                                       │
│                              │ XML over HTTP (port 9000)            │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                    TALLY ERP (External)                     │     │
│  │                    Running on localhost:9000                │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Product Functions

| Function | Description |
|----------|-------------|
| **Application Launch** | Start Electron app, spawn Python backend |
| **Sync Management** | Full sync, incremental sync, delete company |
| **Dashboard** | View synced data, reports, statistics |
| **Tally Configuration** | Configure Tally connection settings |
| **Auto Sync** | Schedule automatic sync at intervals |
| **System Tray** | Minimize to tray, background operation |
| **Auto Update** | Check and install updates automatically |

### 2.3 User Classes

| User Class | Description |
|------------|-------------|
| **End User** | Accountants, business owners using Tally |
| **IT Admin** | Install, configure, maintain the application |

### 2.4 Operating Environment

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10/11 (64-bit) |
| **RAM** | Minimum 4GB, Recommended 8GB |
| **Disk** | 500MB for application + database space |
| **Tally** | Tally ERP 9 or Tally Prime with ODBC enabled |
| **Network** | Localhost access (no internet required for core functions) |

---

## 3. System Features

### 3.1 Application Startup

**Description:** When user launches the application, it should automatically start the Python backend and display the main window.

**Flow:**
```
User clicks .exe
       │
       ▼
┌──────────────────┐
│ Electron Starts  │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Show Splash      │
│ "Starting..."    │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Spawn Python.exe │
│ as child process │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Wait for Python  │
│ to be ready      │
│ (health check)   │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Load Main Window │
│ (sync.html)      │
└──────────────────┘
```

**Requirements:**
- FR-1.1: Application shall start within 10 seconds
- FR-1.2: Splash screen shall show loading progress
- FR-1.3: If Python fails to start, show error dialog
- FR-1.4: Retry Python startup up to 3 times

### 3.2 Application Shutdown

**Description:** When user closes the application, Python backend must be properly terminated.

**Requirements:**
- FR-2.1: Send SIGTERM to Python process on window close
- FR-2.2: Wait up to 5 seconds for graceful shutdown
- FR-2.3: Force kill if Python doesn't respond
- FR-2.4: Clean up temporary files

### 3.3 System Tray Integration

**Description:** Application can minimize to system tray for background operation.

**Requirements:**
- FR-3.1: Minimize to tray on close (configurable)
- FR-3.2: Tray icon with context menu
- FR-3.3: Tray menu options: Open, Sync Now, Exit
- FR-3.4: Notification on sync complete

### 3.4 Window Management

**Requirements:**
- FR-4.1: Remember window size and position
- FR-4.2: Minimum window size: 1024x768
- FR-4.3: Support window maximize/restore
- FR-4.4: Single instance only (prevent multiple windows)

### 3.5 Auto Update

**Description:** Application checks for updates and installs automatically.

**Requirements:**
- FR-5.1: Check for updates on startup
- FR-5.2: Download updates in background
- FR-5.3: Prompt user to restart for update
- FR-5.4: Update server URL configurable

---

## 4. External Interface Requirements

### 4.1 User Interface

| Screen | Description |
|--------|-------------|
| **Splash Screen** | Logo, loading progress, version |
| **Main Window** | Existing sync.html with tabs |
| **System Tray** | Icon with context menu |
| **Settings Dialog** | App settings (minimize to tray, auto-start, etc.) |
| **About Dialog** | Version, credits, license |

### 4.2 Hardware Interfaces

| Interface | Description |
|-----------|-------------|
| **Display** | Minimum 1024x768 resolution |
| **Storage** | Read/write access to app directory |

### 4.3 Software Interfaces

| Interface | Protocol | Description |
|-----------|----------|-------------|
| **Python Backend** | HTTP REST | localhost:8000 |
| **Tally ERP** | XML over HTTP | localhost:9000 |
| **SQLite** | File-based | tally.db |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Requirement |
|--------|-------------|
| **Startup Time** | < 10 seconds |
| **Memory Usage** | < 500MB (Electron + Python) |
| **CPU Usage** | < 5% when idle |

### 5.2 Security

| Requirement | Description |
|-------------|-------------|
| **No External Network** | Core functions work offline |
| **Local Data** | All data stored locally |
| **No Telemetry** | No data sent to external servers |

### 5.3 Reliability

| Requirement | Description |
|-------------|-------------|
| **Crash Recovery** | Auto-restart Python if it crashes |
| **Data Integrity** | SQLite transactions for data safety |
| **Logging** | Log all errors for debugging |

### 5.4 Maintainability

| Requirement | Description |
|-------------|-------------|
| **Modular Code** | Separate Electron and Python codebases |
| **Version Control** | Git for source control |
| **Documentation** | Developer guide for maintenance |

---

## 6. Technology Stack

### 6.1 Electron (Frontend Shell)

| Component | Technology | Version |
|-----------|------------|---------|
| **Framework** | Electron | 28.x |
| **Node.js** | Bundled with Electron | 18.x |
| **Build Tool** | electron-builder | 24.x |
| **Auto Update** | electron-updater | 6.x |

### 6.2 Python (Backend)

| Component | Technology | Version |
|-----------|------------|---------|
| **Framework** | FastAPI | 0.100+ |
| **Server** | Uvicorn | 0.23+ |
| **Database** | SQLite (aiosqlite) | 3.x |
| **Bundler** | PyInstaller | 6.x |

### 6.3 Build Output

| Platform | Output |
|----------|--------|
| **Windows** | TallySync-Setup-1.0.0.exe (installer) |
| **Portable** | TallySync-1.0.0-portable.zip |

---

## 7. Project Structure

```
tally-desktop/
├── electron/                     # Electron app
│   ├── main.js                   # Main process
│   ├── preload.js                # Preload script
│   ├── package.json              # Electron dependencies
│   ├── assets/
│   │   ├── icon.ico              # App icon
│   │   ├── icon.png              # Tray icon
│   │   └── splash.html           # Splash screen
│   └── build/
│       └── installer.nsh         # NSIS installer script
├── python/                       # Python backend (existing)
│   ├── app/                      # FastAPI app
│   ├── static/                   # Frontend files
│   ├── run.py                    # Entry point
│   └── requirements.txt          # Python dependencies
├── dist/                         # Build output
│   ├── TallySync-Setup.exe       # Windows installer
│   └── python-backend.exe        # Bundled Python
└── scripts/
    ├── build-python.bat          # Build Python exe
    ├── build-electron.bat        # Build Electron app
    └── build-all.bat             # Full build
```

---

## 8. Implementation TODO List

### Phase 1: Python Backend Packaging (Day 1-2)

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1.1 | Install PyInstaller | High | Pending |
| 1.2 | Create PyInstaller spec file | High | Pending |
| 1.3 | Bundle static files with Python exe | High | Pending |
| 1.4 | Test Python exe standalone | High | Pending |
| 1.5 | Fix any missing dependencies | Medium | Pending |

### Phase 2: Electron Setup (Day 3-4)

| # | Task | Priority | Status |
|---|------|----------|--------|
| 2.1 | Initialize Electron project | High | Pending |
| 2.2 | Create main.js (main process) | High | Pending |
| 2.3 | Create preload.js | High | Pending |
| 2.4 | Create splash screen | Medium | Pending |
| 2.5 | Implement Python process spawning | High | Pending |
| 2.6 | Implement health check wait | High | Pending |
| 2.7 | Load existing HTML in BrowserWindow | High | Pending |

### Phase 3: Integration (Day 5-6)

| # | Task | Priority | Status |
|---|------|----------|--------|
| 3.1 | Test Electron + Python communication | High | Pending |
| 3.2 | Implement graceful shutdown | High | Pending |
| 3.3 | Add system tray support | Medium | Pending |
| 3.4 | Add window state persistence | Low | Pending |
| 3.5 | Add single instance lock | Medium | Pending |

### Phase 4: Build & Package (Day 7-8)

| # | Task | Priority | Status |
|---|------|----------|--------|
| 4.1 | Configure electron-builder | High | Pending |
| 4.2 | Create Windows installer | High | Pending |
| 4.3 | Add app icon and metadata | Medium | Pending |
| 4.4 | Test installer on clean machine | High | Pending |
| 4.5 | Create portable version | Low | Pending |

### Phase 5: Polish & Release (Day 9-10)

| # | Task | Priority | Status |
|---|------|----------|--------|
| 5.1 | Add auto-update support | Medium | Pending |
| 5.2 | Add about dialog | Low | Pending |
| 5.3 | Add settings dialog | Low | Pending |
| 5.4 | Final testing | High | Pending |
| 5.5 | Create release package | High | Pending |

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Python exe size large** | High | Use UPX compression, exclude unused packages |
| **Antivirus false positive** | Medium | Sign executable, whitelist instructions |
| **Slow startup** | Medium | Optimize Python imports, show splash screen |
| **Port conflict** | Low | Use dynamic port, fallback ports |
| **Tally not running** | Low | Show clear error message with instructions |

---

## 10. Acceptance Criteria

| Criteria | Description |
|----------|-------------|
| **AC-1** | Application starts and shows main window within 10 seconds |
| **AC-2** | All existing web functionality works in desktop app |
| **AC-3** | Application closes cleanly without orphan processes |
| **AC-4** | Installer works on clean Windows 10/11 machine |
| **AC-5** | System tray minimization works correctly |
| **AC-6** | Sync operations complete successfully |

---

## 11. Appendix

### A. Reference Links

- Electron Documentation: https://www.electronjs.org/docs
- PyInstaller Documentation: https://pyinstaller.org/
- electron-builder: https://www.electron.build/

### B. Similar Projects

- VS Code (Electron + Native)
- Postman (Electron + Node.js)
- Discord (Electron)

---

**Document End**

*Next Step: Review SRS and proceed with Phase 1 implementation*
