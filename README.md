# Tally FastAPI Database Loader

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/Tally-ERP%209%20%7C%20Prime-red.svg" alt="Tally">
</p>

**A powerful, open-source Python solution to sync Tally ERP data to SQLite database with real-time incremental sync, audit trail, and multi-company support.**

> 🚀 Perfect for building dashboards, reports, mobile apps, and integrations with Tally ERP 9/Prime data.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **Full Sync** | Complete data extraction from Tally (Masters + Transactions) |
| ⚡ **Incremental Sync** | Smart GUID+AlterID based diff - only sync changes |
| 🏢 **Multi-Company** | Sync multiple companies simultaneously |
| 📝 **Audit Trail** | Track all INSERT/UPDATE/DELETE with full data recovery |
| 🔌 **REST API** | Complete API for data access and management |
| 📊 **Web Dashboard** | Built-in dashboard for monitoring |
| 🛡️ **Error Recovery** | Automatic retry with circuit breaker pattern |
| 📁 **SQLite Database** | Lightweight, portable, zero-config database |

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Tally ERP     │────▶│  FastAPI Server │────▶│  SQLite DB      │
│   (Port 9000)   │ XML │  (Port 8000)    │ SQL │  (tally.db)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Your App       │
                        │  Dashboard/API  │
                        └─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Tally ERP 9 or Tally Prime (running with ODBC/XML enabled)
- pip (Python package manager)

### 1. Clone Repository

```bash
git clone https://github.com/ganeshchavan786/tally-fastapi.git
cd tally-fastapi
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Tally Connection

Edit `config.yaml`:

```yaml
tally:
  server: localhost
  port: 9000
  from_date: "2025-04-01"
  to_date: "2026-03-31"

database:
  path: "./tally.db"

api:
  host: "0.0.0.0"
  port: 8000
```

### 4. Enable Tally ODBC Server

In Tally ERP 9/Prime:
1. Go to **Gateway of Tally** → **F12: Configure** → **Advanced Configuration**
2. Set **Enable ODBC Server** to **Yes**
3. Set **Port** to **9000**

---

## 📅 Company Period Auto-Detection

The system automatically detects and stores company period (books_from/books_to) from Tally:

### Flow:
1. **First Sync**: Period auto-detected from Tally's `BOOKSFROM` field
2. **Stored**: Period saved in `company_config` table
3. **Re-Sync**: Uses stored period for subsequent syncs
4. **Override**: Can manually specify `from_date` and `to_date` in API

### API Parameters:
```
POST /api/sync/full?company=CompanyName&from_date=2019-04-01&to_date=2026-03-31
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `company` | Company name to sync | Active company in Tally |
| `from_date` | Start date (YYYY-MM-DD) | Auto-detect from Tally |
| `to_date` | End date (YYYY-MM-DD) | Current financial year end |

### company_config Table:
```sql
CREATE TABLE company_config (
    company_name TEXT NOT NULL UNIQUE,
    company_guid TEXT,
    books_from TEXT,      -- Stored period start
    books_to TEXT,        -- Stored period end
    last_sync_at TEXT,
    sync_count INTEGER
);
```

### 5. Run Server

```bash
python run.py
```

Server starts at: **http://localhost:8000**

---

## 📖 API Reference

### Sync Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sync/full` | POST | Start full sync (all data) |
| `/api/sync/incremental` | POST | Sync only changes (fast) |
| `/api/sync/status` | GET | Get current sync status |
| `/api/sync/cancel` | POST | Cancel running sync |

**Example: Start Incremental Sync**
```bash
curl -X POST "http://localhost:8000/api/sync/incremental?company=My%20Company"
```

### Data Access

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/data/groups` | GET | Get all account groups |
| `/api/data/ledgers` | GET | Get all ledgers |
| `/api/data/vouchers` | GET | Get vouchers with filters |
| `/api/data/stock-items` | GET | Get stock items |
| `/api/data/companies` | GET | Get synced companies |
| `/api/data/stats` | GET | Get database statistics |
| `/api/data/query` | POST | Execute custom SQL query |

**Example: Get Ledgers**
```bash
curl "http://localhost:8000/api/data/ledgers?company=My%20Company&limit=100"
```

### Audit Trail

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/audit/stats` | GET | Get audit statistics |
| `/api/audit/history` | GET | Get audit history with filters |
| `/api/audit/deleted` | GET | Get deleted records |
| `/api/audit/restore/{id}` | POST | Restore a deleted record |
| `/api/audit/sessions` | GET | Get sync sessions |
| `/api/audit/record/{table}/{guid}` | GET | Get record history |

**Example: Get Audit Stats**
```bash
curl "http://localhost:8000/api/audit/stats"
```

**Response:**
```json
{
  "by_action": {"DELETE": 1702, "INSERT": 2, "UPDATE": 5},
  "by_table": {"mst_ledger": 500, "mst_stock_item": 1200},
  "pending_deleted_records": 1702
}
```

### Health & Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Full health check |
| `/api/health/tally` | GET | Tally connection status |
| `/api/health/database` | GET | Database status |

### Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config` | GET | Get current configuration |
| `/api/config/reload` | POST | Reload configuration |

### Debug & Logs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/debug/enable` | POST | Enable debug mode |
| `/api/debug/disable` | POST | Disable debug mode |
| `/api/logs` | GET | Get recent logs |
| `/api/logs/download` | GET | Download log file |

---

## 🔄 Sync Modes

### Full Sync
Extracts all data from Tally. Use for initial setup or complete refresh.

```bash
curl -X POST "http://localhost:8000/api/sync/full?company=My%20Company"
```

### Incremental Sync
Only syncs changes since last sync using GUID+AlterID comparison.

```bash
curl -X POST "http://localhost:8000/api/sync/incremental?company=My%20Company"
```

**How Incremental Sync Works:**
1. Fetches current GUID list from Tally
2. Compares with database GUIDs
3. Detects: **New records** (INSERT), **Modified records** (UPDATE), **Deleted records** (DELETE)
4. Logs all changes to audit trail
5. Updates database

---

## 📝 Audit Trail

The audit trail feature tracks all data changes during sync operations.

### Features
- **Complete Change Tracking** - INSERT, UPDATE, DELETE operations logged
- **Deleted Records Recovery** - Full data stored for recovery
- **Session Grouping** - Changes grouped by sync session
- **Record History** - View complete history of any record

### Example: View Deleted Records
```bash
curl "http://localhost:8000/api/audit/deleted?limit=10"
```

### Example: Restore Deleted Record
```bash
curl -X POST "http://localhost:8000/api/audit/restore/42"
```

📚 **Full Documentation:** [docs/AUDIT_TRAIL.md](docs/AUDIT_TRAIL.md)

---

## 🗄️ Database Schema

### Master Tables
| Table | Description |
|-------|-------------|
| `mst_group` | Account Groups |
| `mst_ledger` | Ledger Accounts |
| `mst_stock_group` | Stock Groups |
| `mst_stock_item` | Stock Items |
| `mst_stock_category` | Stock Categories |
| `mst_godown` | Godowns/Warehouses |
| `mst_unit` | Units of Measure |
| `mst_vouchertype` | Voucher Types |
| `mst_cost_category` | Cost Categories |
| `mst_cost_centre` | Cost Centres |
| `mst_currency` | Currencies |
| `mst_employee` | Employees |

### Transaction Tables
| Table | Description |
|-------|-------------|
| `trn_voucher` | All Vouchers |
| `trn_accounting` | Accounting Entries |
| `trn_inventory` | Inventory Entries |
| `trn_cost_centre` | Cost Centre Allocations |
| `trn_bill` | Bill-wise Details |
| `trn_batch` | Batch Details |

### Audit Tables
| Table | Description |
|-------|-------------|
| `audit_log` | All change logs |
| `deleted_records` | Deleted records for recovery |

---

## 📁 Project Structure

```
tally-fastapi/
├── app/
│   ├── controllers/          # API endpoint handlers
│   │   ├── sync_controller.py
│   │   ├── data_controller.py
│   │   ├── audit_controller.py
│   │   ├── health_controller.py
│   │   └── ...
│   ├── services/             # Business logic
│   │   ├── sync_service.py
│   │   ├── tally_service.py
│   │   ├── database_service.py
│   │   ├── audit_service.py
│   │   └── ...
│   ├── models/               # Pydantic models
│   ├── utils/                # Helpers, logger
│   └── main.py               # FastAPI app
├── docs/                     # Documentation
│   └── AUDIT_TRAIL.md
├── static/                   # Web dashboard assets
├── logs/                     # Log files
├── config.yaml               # Configuration
├── database-structure-incremental.sql  # DB schema
├── requirements.txt          # Python dependencies
└── run.py                    # Entry point
```

---

## ⚙️ Configuration

### config.yaml

```yaml
# Tally Connection
tally:
  server: localhost
  port: 9000
  timeout: 30
  from_date: "2025-04-01"
  to_date: "2026-03-31"

# Database
database:
  path: "./tally.db"

# API Server
api:
  host: "0.0.0.0"
  port: 8000
  debug: false

# Logging
logging:
  level: INFO
  file: "./logs/app.log"
  max_size: 10485760  # 10MB
  backup_count: 5
  console: true
  colorize: true

# Sync Settings
sync:
  batch_size: 1000
  parallel_tables: false
```

---

## 🧪 Testing

### Run Audit Trail Test
```bash
python test_audit_trail.py
```

### Test Sync
```bash
python test_sync.py
```

---

## 📊 Web Dashboard

Access the built-in dashboard at: **http://localhost:8000**

Features:
- Real-time sync status
- Database statistics
- Company overview
- Audit trail viewer

---

## 🔧 Troubleshooting

### Tally Connection Failed
1. Ensure Tally is running with ODBC Server enabled
2. Check port 9000 is not blocked by firewall
3. Verify `config.yaml` settings

### Sync Returns 0 Rows
1. Ensure correct company is open in Tally
2. Check date range in `config.yaml`
3. Enable debug mode for detailed logs

### Database Locked
1. Close any SQLite browser tools
2. Restart the server

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Tally Solutions](https://tallysolutions.com/) - ERP software
- [SQLite](https://sqlite.org/) - Lightweight database

---

## 📞 Support

- 📧 Email: ganeshchavan786@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/ganeshchavan786/tally-fastapi/issues)
- 📖 Docs: [API Documentation](http://localhost:8000/docs)

---

<p align="center">
  Made with ❤️ for the Tally community
</p>
