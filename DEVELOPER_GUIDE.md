# Tally FastAPI Database Loader - Developer Guide

**Version:** v1.8.1  
**Last Updated:** 2026-01-14

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Data Flow](#data-flow)
3. [File Structure](#file-structure)
4. [Controllers (API Layer)](#controllers-api-layer)
5. [Frontend JavaScript Modules](#frontend-javascript-modules)
6. [Core Services](#core-services)
7. [Sync Logic](#sync-logic)
8. [API Endpoints](#api-endpoints)
9. [Database Schema](#database-schema)
10. [Configuration Files](#configuration-files)
11. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TALLY FASTAPI LOADER                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐             │
│  │   FastAPI    │────▶│   Services   │────▶│   Database   │             │
│  │  Controllers │     │              │     │   (SQLite)   │             │
│  └──────────────┘     └──────────────┘     └──────────────┘             │
│         │                    │                                           │
│         │                    ▼                                           │
│         │             ┌──────────────┐                                   │
│         │             │    Tally     │                                   │
│         │             │   Gateway    │                                   │
│         │             │  (Port 9000) │                                   │
│         │             └──────────────┘                                   │
│         │                    │                                           │
│         ▼                    ▼                                           │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │                    XML Builder                            │           │
│  │  (Generates TDL XML requests from YAML config)           │           │
│  └──────────────────────────────────────────────────────────┘           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Components:

| Component | File | Purpose |
|-----------|------|---------|
| **Controllers** | `app/controllers/*.py` | API endpoints (REST) - Separated by domain |
| **Sync Service** | `app/services/sync_service.py` | Main sync orchestration |
| **Database Service** | `app/services/database_service.py` | SQLite operations |
| **Tally Service** | `app/services/tally_service.py` | Tally HTTP communication |
| **XML Builder** | `app/services/xml_builder.py` | TDL XML generation |
| **Queue Service** | `app/services/sync_queue_service.py` | Multi-company queue |
| **Frontend JS** | `static/js/sync/*.js` | Modular JavaScript (7 files) |

---

## Data Flow

### Full Sync Flow:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FULL SYNC FLOW                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. API Request                                                          │
│     POST /api/sync/full?company=CompanyName                             │
│                    │                                                     │
│                    ▼                                                     │
│  2. Verify Tally Connection                                             │
│     - Check if Tally is accessible                                      │
│     - Verify company exists and has data                                │
│                    │                                                     │
│                    ▼                                                     │
│  3. Truncate Company Data                                               │
│     - DELETE FROM table WHERE _company = 'CompanyName'                  │
│     - Only deletes data for specified company                           │
│                    │                                                     │
│                    ▼                                                     │
│  4. Sync Master Tables (19 tables)                                      │
│     For each table in tally-export-config.yaml:                         │
│     a. Build XML request from YAML config                               │
│     b. Send to Tally Gateway (localhost:9000)                           │
│     c. Parse XML response                                               │
│     d. Bulk insert into SQLite                                          │
│                    │                                                     │
│                    ▼                                                     │
│  5. Sync Transaction Tables (13 tables)                                 │
│     Same process as master tables                                       │
│                    │                                                     │
│                    ▼                                                     │
│  6. Update company_config Table                                         │
│     - Save company GUID, AlterID                                        │
│     - Update last_sync_at, sync_count                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Incremental Sync Flow (Node.js Style):

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      INCREMENTAL SYNC FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Get Last AlterID from Database                                      │
│     SELECT last_alter_id_master FROM company_config                     │
│     WHERE company_name = 'CompanyName'                                  │
│                    │                                                     │
│                    ▼                                                     │
│  2. Get Current AlterID from Tally                                      │
│     - Request company info from Tally                                   │
│     - Extract current AlterID                                           │
│                    │                                                     │
│                    ▼                                                     │
│  3. Compare AlterIDs                                                    │
│     IF current_alterid == last_alterid:                                 │
│        → No changes, skip sync                                          │
│     ELSE:                                                               │
│        → Changes detected, continue                                     │
│                    │                                                     │
│                    ▼                                                     │
│  4. Process Diff for Primary Tables                                     │
│     For each PRIMARY table:                                             │
│     ┌─────────────────────────────────────────────────────────┐        │
│     │ a. Truncate _diff and _delete tables                     │        │
│     │                                                          │        │
│     │ b. Fetch GUID + AlterID from Tally into _diff            │        │
│     │    (All current records)                                 │        │
│     │                                                          │        │
│     │ c. Find DELETED records:                                 │        │
│     │    INSERT INTO _delete                                   │        │
│     │    SELECT guid FROM main_table                           │        │
│     │    WHERE guid NOT IN (SELECT guid FROM _diff)            │        │
│     │                                                          │        │
│     │ d. Find MODIFIED records:                                │        │
│     │    INSERT INTO _delete                                   │        │
│     │    SELECT t.guid FROM main_table t                       │        │
│     │    JOIN _diff d ON d.guid = t.guid                       │        │
│     │    WHERE d.alterid <> t.alterid                          │        │
│     │                                                          │        │
│     │ e. Delete from main table:                               │        │
│     │    DELETE FROM main_table                                │        │
│     │    WHERE guid IN (SELECT guid FROM _delete)              │        │
│     │                                                          │        │
│     │ f. Cascade delete related tables                         │        │
│     └─────────────────────────────────────────────────────────┘        │
│                    │                                                     │
│                    ▼                                                     │
│  5. Import Changed Records                                              │
│     For each table:                                                     │
│     - Add filter: $AlterID > last_alterid                              │
│     - Fetch only new/modified records                                   │
│     - Upsert into database                                              │
│                    │                                                     │
│                    ▼                                                     │
│  6. Update company_config                                               │
│     - Save new AlterID values                                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Multi-Company Queue Flow:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MULTI-COMPANY QUEUE FLOW                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Add Companies to Queue                                              │
│     POST /api/sync/queue                                                │
│     Body: {"companies": ["Company1", "Company2"], "sync_type": "full"}  │
│                    │                                                     │
│                    ▼                                                     │
│  2. Start Queue Processing                                              │
│     POST /api/sync/queue/start                                          │
│                    │                                                     │
│                    ▼                                                     │
│  3. Process Each Company Sequentially                                   │
│     ┌─────────────────────────────────────────────────────────┐        │
│     │  FOR each company in queue:                              │        │
│     │    - Set config.tally.company = company_name             │        │
│     │    - Run full_sync() or incremental_sync()               │        │
│     │    - Update queue status                                 │        │
│     │    - Continue to next company                            │        │
│     └─────────────────────────────────────────────────────────┘        │
│                    │                                                     │
│                    ▼                                                     │
│  4. Queue Complete                                                      │
│     All companies synced, status updated                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
tally-fastapi/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry point, router registration
│   ├── config.py                    # Configuration loader
│   ├── controllers/                 # ⭐ API Controllers (Separated by domain)
│   │   ├── __init__.py              # Exports all routers
│   │   ├── sync_controller.py       # /api/sync/* - Sync operations
│   │   ├── master_controller.py     # /api/data/* - Groups, Ledgers, Stock
│   │   ├── voucher_controller.py    # /api/data/* - Vouchers
│   │   ├── outstanding_controller.py # /api/data/* - Outstanding reports
│   │   ├── ledger_controller.py     # /api/data/* - Ledger reports
│   │   ├── dashboard_controller.py  # /api/data/* - Dashboard, counts
│   │   ├── config_controller.py     # /api/config/* - Tally configuration
│   │   ├── health_controller.py     # /api/health/* - Health checks
│   │   ├── audit_controller.py      # /api/audit/* - Audit trail
│   │   ├── log_controller.py        # /api/logs/* - Log viewing
│   │   └── debug_controller.py      # /api/debug/* - Debug tools
│   ├── services/
│   │   ├── __init__.py
│   │   ├── sync_service.py          # ⭐ Main sync orchestration
│   │   ├── sync_queue_service.py    # Multi-company queue
│   │   ├── database_service.py      # SQLite operations
│   │   ├── tally_service.py         # Tally HTTP client
│   │   └── xml_builder.py           # TDL XML generator
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                # Logging configuration
│       └── decorators.py            # Utility decorators
├── static/                          # ⭐ Frontend Assets
│   ├── css/
│   │   ├── common.css               # Shared styles
│   │   └── sync.css                 # Sync page styles
│   ├── js/
│   │   ├── common.js                # Shared utilities (apiCall, showToast)
│   │   ├── sync/                    # ⭐ Sync page modules (7 files)
│   │   │   ├── sync-utils.js        # Date/period utilities
│   │   │   ├── sync-core.js         # Global vars, init
│   │   │   ├── sync-companies.js    # Company list management
│   │   │   ├── sync-progress.js     # Progress UI
│   │   │   ├── sync-actions.js      # Sync operations
│   │   │   ├── sync-schedule.js     # Auto sync schedule
│   │   │   └── sync-tally-config.js # Tally configuration
│   │   ├── dashboard.js             # Dashboard page
│   │   └── audit.js                 # Audit page
│   ├── sync.html                    # Sync settings page
│   ├── dashboard.html               # Company dashboard
│   └── audit.html                   # Audit trail page
├── data/
│   └── tally.db                     # SQLite database
├── logs/                            # Application logs
├── config.yaml                      # App configuration
├── tally-export-config.yaml         # Full sync table/field config
├── tally-export-config-incremental.yaml  # Incremental sync config
├── database-structure.sql           # Full sync DB schema
├── database-structure-incremental.sql    # Incremental sync schema
├── run.py                           # Server startup script
├── DEVELOPER_GUIDE.md               # This file
└── TECHNICAL_DOCUMENTATION.md       # Detailed technical docs
```

---

## Controllers (API Layer)

Controllers are separated by domain for better maintainability (v1.7.0+).

### Controller Overview:

| Controller | Prefix | Purpose |
|------------|--------|---------|
| `sync_controller.py` | `/api/sync` | Sync operations (full, incremental) |
| `master_controller.py` | `/api/data` | Groups, Ledgers, Stock Items |
| `voucher_controller.py` | `/api/data` | Vouchers, Voucher Details |
| `outstanding_controller.py` | `/api/data` | Outstanding reports (Receivable/Payable) |
| `ledger_controller.py` | `/api/data` | Ledger reports, Bill-wise |
| `dashboard_controller.py` | `/api/data` | Dashboard counts, Company management |
| `config_controller.py` | `/api/config` | Tally configuration |
| `health_controller.py` | `/api/health` | Health checks |
| `audit_controller.py` | `/api/audit` | Audit trail |

### Adding a New Controller:

1. Create file in `app/controllers/`
2. Define router: `router = APIRouter()`
3. Add endpoints with decorators
4. Export in `__init__.py`
5. Register in `main.py`

```python
# Example: app/controllers/my_controller.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint():
    return {"message": "Hello"}
```

```python
# In main.py
from .controllers.my_controller import router as my_router
app.include_router(my_router, prefix="/api/my", tags=["My"])
```

---

## Frontend JavaScript Modules

JavaScript is modularized for the sync page (v1.8.0+).

### Module Overview:

| File | Purpose | Key Functions |
|------|---------|---------------|
| `sync-utils.js` | Utilities | `formatDateDisplay()`, `parseTallyDate()`, `extractPeriodFromName()` |
| `sync-core.js` | Global state | `switchTab()`, `toggleCompany()`, global variables |
| `sync-companies.js` | Company lists | `loadCompanies()`, `loadSyncedCompanies()` |
| `sync-progress.js` | Progress UI | `showCircularProgress()`, `updateSyncStatus()` |
| `sync-actions.js` | Sync operations | `syncCompanyFull()`, `incrementalSyncCompany()`, `deleteCompany()` |
| `sync-schedule.js` | Auto sync | `startAutoSync()`, `stopAutoSync()`, `setSyncInterval()` |
| `sync-tally-config.js` | Tally config | `loadTallyConfig()`, `testTallyConnection()` |

### Script Loading Order (in sync.html):

```html
<script src="/static/js/common.js"></script>
<script src="/static/js/sync/sync-utils.js"></script>
<script src="/static/js/sync/sync-core.js"></script>
<script src="/static/js/sync/sync-companies.js"></script>
<script src="/static/js/sync/sync-progress.js"></script>
<script src="/static/js/sync/sync-actions.js"></script>
<script src="/static/js/sync/sync-schedule.js"></script>
<script src="/static/js/sync/sync-tally-config.js"></script>
```

### Global Variables (sync-core.js):

```javascript
let selectedCompanies = [];      // Selected for batch sync
let syncInterval = null;         // Status polling interval
let companyPeriods = {};         // {companyName: {from, to}}
let autoSyncTimer = null;        // Auto sync timer
let syncIntervalMinutes = 60;    // Default 1 hour
```

### Adding a New JS Module:

1. Create file in `static/js/sync/`
2. Add developer notes at top
3. Add script tag in `sync.html` (order matters!)
4. Use global variables from `sync-core.js`
5. Use `apiCall()` from `common.js` for API requests

---

## Core Services

### 1. SyncService (`sync_service.py`)

**Purpose:** Orchestrates the entire sync process.

**Key Methods:**

```python
class SyncService:
    async def full_sync(company: str) -> Dict:
        """
        Full synchronization - replaces all data for a company.
        
        Flow:
        1. Verify Tally connection (prevent data loss)
        2. Truncate company data
        3. Sync master tables
        4. Sync transaction tables
        5. Update company_config
        """
    
    async def incremental_sync(company: str) -> Dict:
        """
        Incremental sync - only changed records.
        
        Flow:
        1. Get last AlterID from DB
        2. Get current AlterID from Tally
        3. If different → process diff
        4. Import changed records
        5. Update company_config
        """
    
    async def _process_diff_for_primary_tables(data_type: str, last_alterid: int):
        """
        Node.js style diff processing.
        
        Uses _diff and _delete tables to:
        - Find deleted records (GUID not in Tally)
        - Find modified records (AlterID changed)
        - Delete old versions before importing new
        """
    
    async def _import_changed_records(data_type: str, last_alterid: int):
        """
        Import only records with AlterID > last_alterid.
        Uses $AlterID filter in Tally XML request.
        """
```

### 2. DatabaseService (`database_service.py`)

**Purpose:** All SQLite database operations.

**Key Methods:**

```python
class DatabaseService:
    async def connect() -> None:
        """Connect to SQLite database."""
    
    async def create_tables(incremental: bool) -> None:
        """
        Create tables from SQL schema file.
        - Full sync: database-structure.sql
        - Incremental: database-structure-incremental.sql
        """
    
    async def bulk_insert(table_name: str, rows: List[Dict], company_name: str) -> int:
        """
        Bulk insert rows into table.
        - Auto-adds _company column
        - Auto-creates missing columns (from YAML config)
        """
    
    async def _ensure_columns_exist(table_name: str, columns: List[str]) -> None:
        """
        Auto-add missing columns to table.
        Prevents schema mismatch errors when YAML has new fields.
        """
    
    async def truncate_all_tables(company: str) -> None:
        """
        Delete data only for specified company.
        DELETE FROM table WHERE _company = 'company_name'
        """
    
    async def update_company_config(...) -> None:
        """
        Update company_config table with:
        - company_guid, company_alterid
        - last_alter_id_master, last_alter_id_transaction
        - last_sync_at, sync_count
        """
```

### 3. TallyService (`tally_service.py`)

**Purpose:** HTTP communication with Tally Gateway.

**Key Methods:**

```python
class TallyService:
    async def send_xml(xml_request: str) -> str:
        """
        Send XML request to Tally Gateway.
        - URL: http://localhost:9000
        - Method: POST
        - Content-Type: text/xml
        - Encoding: UTF-16
        """
    
    async def check_connection() -> bool:
        """Check if Tally is accessible."""
    
    async def get_open_companies() -> List[Dict]:
        """Get list of all open companies in Tally."""
    
    async def get_company_info() -> Dict:
        """
        Get current company info including:
        - name, guid, alter_id
        - books_from, books_to
        """
```

### 4. XMLBuilder (`xml_builder.py`)

**Purpose:** Generate TDL XML requests from YAML config.

**Key Methods:**

```python
class XMLBuilder:
    def reload_config(incremental: bool) -> None:
        """
        Load YAML config file.
        - Full: tally-export-config.yaml
        - Incremental: tally-export-config-incremental.yaml
        """
    
    def build_export_request(table_config: Dict) -> str:
        """
        Build TDL XML request for a table.
        
        Structure:
        <ENVELOPE>
          <HEADER>...</HEADER>
          <BODY>
            <DESC>
              <TDL>
                <TDLMESSAGE>
                  <REPORT>...</REPORT>
                  <FORM>...</FORM>
                  <PART>...</PART>
                  <LINE>...</LINE>
                  <FIELD>...</FIELD>
                  <FETCH>...</FETCH>
                  <FILTER>...</FILTER>
                </TDLMESSAGE>
              </TDL>
            </DESC>
          </BODY>
        </ENVELOPE>
        """
    
    def get_master_tables() -> List[Dict]:
        """Get list of master table configs."""
    
    def get_transaction_tables() -> List[Dict]:
        """Get list of transaction table configs."""
```

---

## API Endpoints

### Sync Endpoints (`/api/sync/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/sync/full` | Start full sync (delete + fresh sync) |
| `POST` | `/api/sync/incremental` | Start incremental sync (changes only) |
| `GET` | `/api/sync/status` | Get current sync status |
| `POST` | `/api/sync/cancel` | Cancel running sync |
| `GET` | `/api/sync/history` | Get sync history |
| `POST` | `/api/sync/queue` | Add companies to queue |
| `POST` | `/api/sync/queue/start` | Start queue processing |
| `GET` | `/api/sync/queue/status` | Get queue status |
| `DELETE` | `/api/sync/queue` | Clear queue |

### Master Data Endpoints (`/api/data/` - master_controller.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/data/groups` | Get all account groups |
| `GET` | `/api/data/ledgers` | Get ledgers with pagination |
| `GET` | `/api/data/stock-items` | Get all stock items |

### Voucher Endpoints (`/api/data/` - voucher_controller.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/data/vouchers` | Get vouchers with filters |
| `GET` | `/api/data/vouchers/{guid}/details` | Get voucher details |

### Outstanding Endpoints (`/api/data/` - outstanding_controller.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/data/outstanding` | Receivable/Payable summary |
| `GET` | `/api/data/outstanding/billwise` | Bill-wise outstanding |
| `GET` | `/api/data/outstanding/ledgerwise` | Ledger-wise outstanding |
| `GET` | `/api/data/outstanding/ageing` | Ageing analysis (0-30, 30-60, etc.) |
| `GET` | `/api/data/outstanding/group` | Group-wise outstanding |

### Ledger Report Endpoints (`/api/data/` - ledger_controller.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/data/ledger-report` | Ledger statement with running balance |
| `GET` | `/api/data/ledger-billwise` | Bill-wise details for a ledger |

### Dashboard Endpoints (`/api/data/` - dashboard_controller.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/data/counts` | Table row counts for dashboard |
| `GET` | `/api/data/synced-companies` | List synced companies |
| `GET` | `/api/data/companies` | Company details |
| `DELETE` | `/api/data/company/{name}` | Delete company data |
| `POST` | `/api/data/query` | Execute custom SQL query |

### Config Endpoints (`/api/config/` - config_controller.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/config` | Get current configuration |
| `PUT` | `/api/config` | Update configuration |
| `POST` | `/api/config/tally/test` | Test Tally connection |

### Health Endpoints (`/api/health/` - health_controller.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Overall health status |
| `GET` | `/api/health/tally` | Tally connection status |

### Audit Endpoints (`/api/audit/` - audit_controller.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/audit/changes` | Audit trail records |
| `GET` | `/api/audit/summary` | Insert/Update/Delete counts |
| `GET` | `/api/audit/pending` | Pending restore items |

---

## Database Schema

### Key Tables:

```sql
-- Company configuration (per-company sync metadata)
CREATE TABLE company_config (
    id INTEGER PRIMARY KEY,
    company_name TEXT UNIQUE,      -- Company name
    company_guid TEXT,             -- Tally GUID
    company_alterid INTEGER,       -- Company AlterID
    last_alter_id_master INTEGER,  -- Last synced master AlterID
    last_alter_id_transaction INTEGER,  -- Last synced transaction AlterID
    last_sync_at TEXT,             -- Last sync timestamp
    last_sync_type TEXT,           -- 'full' or 'incremental'
    sync_count INTEGER             -- Total sync count
);

-- Diff table (for incremental sync)
CREATE TABLE _diff (
    guid TEXT PRIMARY KEY,
    alterid TEXT
);

-- Delete tracking table
CREATE TABLE _delete (
    guid TEXT PRIMARY KEY
);

-- All data tables have _company column
-- Example: mst_ledger
CREATE TABLE mst_ledger (
    guid VARCHAR(64) PRIMARY KEY,
    name NVARCHAR(1024),
    parent NVARCHAR(1024),
    ...
    _company TEXT DEFAULT ''  -- Multi-company support
);
```

### Multi-Company Support:

Every data table has `_company` column:
- Full sync: `DELETE FROM table WHERE _company = 'CompanyName'`
- Queries: `SELECT * FROM table WHERE _company = 'CompanyName'`

---

## Configuration Files

### 1. `config.yaml` - App Configuration

```yaml
tally:
  server: localhost
  port: 9000
  company: ""  # Empty = active company in Tally

database:
  path: ./tally.db

sync:
  mode: full  # 'full' or 'incremental'
  batch_size: 1000

api:
  host: 0.0.0.0
  port: 8000
```

### 2. `tally-export-config.yaml` - Table/Field Config

```yaml
master:
  - name: mst_ledger           # Table name in database
    collection: Ledger         # Tally collection name
    nature: Primary            # Primary or Derived
    fields:
      - name: guid             # Column name in database
        field: Guid            # Tally field/formula
        type: text             # text, number, amount, logical, date
      - name: name
        field: Name
        type: text
    filters:                   # Optional Tally filters
      - NOT $IsCancelled
    cascade_delete:            # For incremental sync
      - table: related_table
        field: ledger_guid

transaction:
  - name: trn_voucher
    collection: Voucher
    ...
```

### Field Types:

| Type | Description | Example |
|------|-------------|---------|
| `text` | String value | Name, GUID |
| `number` | Integer/decimal | Quantity, AlterID |
| `amount` | Currency value | Amount, Balance |
| `logical` | Boolean (Yes/No) | IsActive |
| `date` | Date value | VoucherDate |

---

## Troubleshooting

### Common Issues:

#### 1. Schema Mismatch Error
```
Error: table X has no column named Y
```

**Cause:** YAML config has field not in SQL schema.

**Solution:** 
- Auto-column creation handles this automatically
- Or manually add column to database-structure.sql

#### 2. Tally Connection Error
```
Error: Tally connection failed
```

**Cause:** Tally not running or wrong port.

**Solution:**
- Ensure Tally is running
- Check config.yaml port (default: 9000)
- Enable Tally Gateway Server in Tally

#### 3. Zero Rows Imported
```
Full sync completed. Total rows: 0
```

**Cause:** Company not active in Tally or wrong company name.

**Solution:**
- Open the company in Tally
- Verify company name matches exactly

#### 4. Incremental Sync Not Detecting Changes

**Cause:** AlterID not changing or filter issue.

**Solution:**
- Check company_config table for last_alter_id values
- Verify Tally is returning AlterID in company info

---

## Best Practices

1. **Always use Full Sync first** before Incremental Sync
2. **Keep YAML and SQL files in sync** when adding new fields
3. **Use queue for multi-company sync** instead of parallel requests
4. **Check logs** in case of issues
5. **Backup tally.db** before major changes
6. **Add developer notes** to new files (see existing files for format)
7. **Follow controller separation** - don't add unrelated endpoints to same controller

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.8.1 | 2026-01-14 | Add technical documentation and developer notes |
| v1.8.0 | 2026-01-14 | Split sync.js into 7 modular files |
| v1.7.1 | 2026-01-14 | Add SweetAlert for Tally errors |
| v1.7.0 | 2026-01-14 | Split data_controller into 5 controllers |
| v1.6.1 | 2026-01-11 | Fix Dashboard API issues |
| v1.6.0 | 2026-01-10 | Ledger Bill-wise report |

---

## Related Documentation

- **TECHNICAL_DOCUMENTATION.md** - Detailed technical reference
- **README.md** - Quick start guide
- **API Docs** - http://localhost:8000/docs (Swagger UI)

---

## Contact

For issues or questions, check the logs or create a GitHub issue.
