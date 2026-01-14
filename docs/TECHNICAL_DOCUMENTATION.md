# Tally Database Loader - Technical Documentation

## Project Overview

**Purpose**: Sync data from Tally ERP 9/Prime to SQLite database via REST APIs. Provides web UI for sync management, dashboard, and reports.

**Version**: v1.8.0

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+ with FastAPI |
| Database | SQLite (aiosqlite for async) |
| Frontend | Vanilla JavaScript, HTML5, CSS3 |
| Tally Integration | XML over HTTP (port 9000) |
| UI Library | SweetAlert2 for alerts |

---

## Project Structure

```
tally-fastapi/
├── app/                          # Backend Application
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Configuration management
│   ├── controllers/              # API Controllers (MVC Pattern)
│   │   ├── __init__.py
│   │   ├── sync_controller.py    # Sync operations
│   │   ├── master_controller.py  # Master data APIs
│   │   ├── voucher_controller.py # Voucher APIs
│   │   ├── outstanding_controller.py # Outstanding reports
│   │   ├── ledger_controller.py  # Ledger reports
│   │   ├── dashboard_controller.py # Dashboard APIs
│   │   ├── config_controller.py  # Configuration APIs
│   │   ├── health_controller.py  # Health check APIs
│   │   ├── audit_controller.py   # Audit trail APIs
│   │   ├── log_controller.py     # Log viewing APIs
│   │   └── debug_controller.py   # Debug tools
│   ├── services/                 # Business Logic Layer
│   │   ├── database/
│   │   │   ├── factory.py        # Database service factory
│   │   │   └── sqlite_adapter.py # SQLite implementation
│   │   ├── tally_service.py      # Tally XML communication
│   │   └── sync_service.py       # Sync orchestration
│   └── utils/
│       └── logger.py             # Logging utilities
├── static/                       # Frontend Assets
│   ├── css/
│   │   ├── common.css            # Shared styles
│   │   └── sync.css              # Sync page styles
│   ├── js/
│   │   ├── common.js             # Shared utilities
│   │   ├── sync/                 # Sync page modules
│   │   │   ├── sync-utils.js
│   │   │   ├── sync-core.js
│   │   │   ├── sync-companies.js
│   │   │   ├── sync-progress.js
│   │   │   ├── sync-actions.js
│   │   │   ├── sync-schedule.js
│   │   │   └── sync-tally-config.js
│   │   ├── dashboard.js
│   │   └── audit.js
│   ├── sync.html                 # Sync settings page
│   ├── dashboard.html            # Company dashboard
│   └── audit.html                # Audit trail page
├── data/
│   └── tally.db                  # SQLite database
├── logs/                         # Application logs
├── run.py                        # Server startup script
├── config.yaml                   # Configuration file
└── requirements.txt              # Python dependencies
```

---

## Backend Architecture

### Controllers (app/controllers/)

#### 1. sync_controller.py
**Prefix**: `/api/sync`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/full` | POST | Full sync - deletes existing data and syncs fresh |
| `/incremental` | POST | Incremental sync - only syncs changes |
| `/status` | GET | Get current sync status |
| `/queue` | GET | Get sync queue status |

**Business Logic**:
- Full sync: DELETE all company data → Fetch from Tally → INSERT
- Incremental sync: Compare alter_id → Fetch only changed records

---

#### 2. master_controller.py
**Prefix**: `/api/data`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/groups` | GET | Get all account groups |
| `/ledgers` | GET | Get all ledgers with pagination |
| `/stock-items` | GET | Get all stock items |

**Query Parameters**:
- `company` - Filter by company name
- `limit` - Pagination limit
- `offset` - Pagination offset

---

#### 3. voucher_controller.py
**Prefix**: `/api/data`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/vouchers` | GET | Get vouchers with filters |
| `/vouchers/{guid}/details` | GET | Get voucher details with line items |

**Query Parameters**:
- `company` - Company name
- `voucher_type` - Filter by type (Sales, Purchase, etc.)
- `from_date`, `to_date` - Date range filter

---

#### 4. outstanding_controller.py
**Prefix**: `/api/data`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/outstanding` | GET | Receivable/Payable summary |
| `/outstanding/billwise` | GET | Bill-wise outstanding |
| `/outstanding/ledgerwise` | GET | Ledger-wise outstanding |
| `/outstanding/ageing` | GET | Ageing analysis |
| `/outstanding/group` | GET | Group-wise outstanding |

**Business Logic**:
- Receivable: Sundry Debtors with positive balance
- Payable: Sundry Creditors with positive balance
- Ageing buckets: 0-30, 30-60, 60-90, 90+ days

---

#### 5. ledger_controller.py
**Prefix**: `/api/data`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ledger-report` | GET | Ledger statement with running balance |
| `/ledger-billwise` | GET | Bill-wise details for a ledger |

**Business Logic**:
- Running balance calculated from opening + transactions
- On Account = Bills Total - Ledger Opening Balance

---

#### 6. dashboard_controller.py
**Prefix**: `/api/data`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/counts` | GET | Table row counts for dashboard |
| `/synced-companies` | GET | List of synced companies |
| `/companies` | GET | Company details |
| `/company/{name}` | DELETE | Delete company data |
| `/query` | POST | Execute custom SQL query |

---

### Services (app/services/)

#### database/factory.py
**Purpose**: Factory pattern for database service instantiation
```python
def get_database_service() -> SQLiteDatabaseService:
    return SQLiteDatabaseService(db_path)
```

#### database/sqlite_adapter.py
**Purpose**: SQLite database operations
- Async operations using aiosqlite
- CRUD operations for all tables
- Query builders for reports

#### tally_service.py
**Purpose**: Tally XML communication
- Send XML requests to Tally
- Parse XML responses
- Handle connection errors

#### sync_service.py
**Purpose**: Sync orchestration
- Coordinate full/incremental sync
- Track sync progress
- Handle errors and rollback

---

## Frontend Architecture

### JavaScript Modules (static/js/sync/)

#### 1. sync-utils.js
**Purpose**: Utility functions

| Function | Description |
|----------|-------------|
| `formatDateTimeShort(dateStr)` | Format: "11 Jan 12:39 pm" |
| `formatDateDisplay(dateStr)` | Format: "1 Apr 2025" |
| `parseTallyDate(dateStr)` | Parse Tally date formats |
| `extractPeriodFromName(name)` | Extract FY from name (e.g., "18-24") |
| `editPeriod(companyName)` | Show period edit modal |

---

#### 2. sync-core.js
**Purpose**: Global state and initialization

| Variable | Description |
|----------|-------------|
| `selectedCompanies` | Array of selected companies |
| `syncInterval` | Status polling interval ID |
| `companyPeriods` | Period for each company |
| `syncIntervalMinutes` | Auto sync interval (default 60) |

---

#### 3. sync-companies.js
**Purpose**: Company list management

| Function | Description |
|----------|-------------|
| `loadCompanies()` | Load Tally companies (left panel) |
| `loadSyncedCompanies()` | Load synced companies (right panel) |

**Business Logic**:
- Left panel: New companies from Tally (not synced)
- Right panel: Already synced companies with actions

---

#### 4. sync-progress.js
**Purpose**: Progress UI

| Function | Description |
|----------|-------------|
| `showCircularProgress(name)` | Show circular progress indicator |
| `updateCircularProgress(name, %)` | Update progress percentage |
| `updateSyncStatus()` | Poll `/api/sync/status` every 1 second |

---

#### 5. sync-actions.js
**Purpose**: Sync operations

| Function | Description |
|----------|-------------|
| `syncCompany(name)` | Sync new company |
| `syncCompanyFull(name)` | Full sync for synced company |
| `incrementalSyncCompany(name)` | Incremental sync |
| `deleteCompany(name)` | Delete company from database |

---

#### 6. sync-schedule.js
**Purpose**: Auto sync scheduling

| Function | Description |
|----------|-------------|
| `setSyncInterval(minutes)` | Set interval (5/15/30/60 min) |
| `startAutoSync()` | Start auto sync timer |
| `stopAutoSync()` | Stop auto sync |

---

#### 7. sync-tally-config.js
**Purpose**: Tally configuration

| Function | Description |
|----------|-------------|
| `loadTallyConfig()` | Load host/port from API |
| `testTallyConnection()` | Test connection with SweetAlert |
| `saveTallyConfig()` | Save and test connection |

---

## Database Schema

### Master Tables

| Table | Description |
|-------|-------------|
| `mst_group` | Account groups |
| `mst_ledger` | Ledger accounts |
| `mst_vouchertype` | Voucher types |
| `mst_stock_item` | Stock items |
| `mst_stock_group` | Stock groups |
| `mst_uom` | Units of measure |
| `mst_godown` | Godowns/Warehouses |
| `mst_cost_centre` | Cost centres |
| `mst_gst_effective_rate` | GST rates |

### Transaction Tables

| Table | Description |
|-------|-------------|
| `trn_voucher` | Voucher headers |
| `trn_accounting` | Accounting entries |
| `trn_inventory` | Inventory entries |
| `trn_bill` | Bill allocations |
| `trn_bank` | Bank transactions |
| `trn_batch` | Batch allocations |

### Sync Tables

| Table | Description |
|-------|-------------|
| `sync_companies` | Synced company metadata |

---

## API Response Formats

### Success Response
```json
{
    "success": true,
    "data": [...],
    "total": 100,
    "message": "Success"
}
```

### Error Response
```json
{
    "success": false,
    "error": "Error message",
    "detail": "Detailed error info"
}
```

---

## Configuration (config.yaml)

```yaml
tally:
  server: localhost
  port: 9000

database:
  path: data/tally.db

logging:
  level: INFO
  file: logs/app.log
```

---

## Running the Application

### Development
```bash
python run.py
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Access URLs
- **Sync Page**: http://localhost:8000/sync.html
- **Dashboard**: http://localhost:8000/dashboard.html
- **API Docs**: http://localhost:8000/docs

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.8.0 | 2026-01-14 | Split sync.js into 7 modular files |
| v1.7.1 | 2026-01-14 | Add SweetAlert for Tally errors |
| v1.7.0 | 2026-01-14 | Split data_controller into 5 controllers |
| v1.6.1 | 2026-01-11 | Fix Dashboard API issues |
| v1.6.0 | 2026-01-10 | Ledger Bill-wise report |

---

## Developer Notes

### Adding New API Endpoint
1. Create function in appropriate controller
2. Add route decorator with path and method
3. Implement business logic
4. Return proper response format
5. Test with `/docs` Swagger UI

### Adding New JS Module
1. Create file in `static/js/sync/`
2. Add script tag in `sync.html` (order matters!)
3. Use global variables from `sync-core.js`
4. Call `apiCall()` from `common.js` for API requests

### Common Issues
1. **Tally not connecting**: Check port 9000, Tally running
2. **API returning empty**: Check company parameter
3. **Progress not updating**: Check `syncInterval` is set

---

*Last Updated: 2026-01-14*
