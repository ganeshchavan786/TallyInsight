# TallyInsight

<p align="center">
  <img src="static/assets/logo.png" alt="TallyInsight Logo" width="120">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/Tally-ERP%209%20%7C%20Prime-red.svg" alt="Tally">
  <img src="https://img.shields.io/badge/Version-2.0.0-purple.svg" alt="Version">
</p>

<h3 align="center">🚀 Tally ERP Business Intelligence & Real-Time Data Sync Platform</h3>

<p align="center">
  <strong>Open-source solution to sync Tally ERP data with smart incremental sync, complete audit trail, and multi-database support.</strong>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [How It Works](#-how-it-works)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [API Reference](#-api-reference)
- [Database Schema](#-database-schema)
- [Configuration](#-configuration)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**TallyInsight** is a powerful, open-source platform that bridges Tally ERP with modern databases and applications. It provides:

- **Real-time data synchronization** from Tally ERP 9/Prime
- **Smart incremental sync** using AlterID-based change detection
- **Complete audit trail** with data recovery capabilities
- **Modern web dashboard** for monitoring and management
- **REST API** for building custom integrations

> Perfect for building dashboards, reports, mobile apps, and integrations with Tally ERP data.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **Full Sync** | Complete data extraction from Tally (Masters + Transactions) |
| ⚡ **Incremental Sync** | Smart AlterID-based diff - only sync changes (10-60 seconds) |
| 🏢 **Multi-Company** | Sync multiple companies simultaneously |
| 📝 **Audit Trail** | Track all INSERT/UPDATE/DELETE with full data recovery |
| 🔌 **REST API** | Complete API for data access and management |
| 📊 **Web Dashboard** | Built-in modern dashboard with real-time progress |
| 🛡️ **Auto Sync** | Scheduled automatic incremental sync (configurable interval) |
| 🗄️ **Multi-Database** | Support for SQLite, PostgreSQL, MySQL, SQL Server, MongoDB |
| 📱 **PWA Support** | Progressive Web App with offline capabilities |
| 🖥️ **Desktop App** | Electron-based standalone application |

---

## 🔄 How It Works

### Incremental Sync Flow

TallyInsight uses Tally's **AlterID** system to detect changes efficiently:

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Compare AlterID                                     │
│  ─────────────────────────────────────────────────────────── │
│  Database: last_alter_id = 102237                           │
│  Tally:    current_alter_id = 102240                        │
│  Result:   102240 > 102237 → 3 Changes detected!            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Fetch ONLY changed records                          │
│  ─────────────────────────────────────────────────────────── │
│  Query: WHERE AlterID > 102237                              │
│  Result: Only 3 changed records fetched                     │
│  (NOT all 3812 ledgers - only changed ones!)                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: UPSERT (Insert OR Update)                           │
│  ─────────────────────────────────────────────────────────── │
│  - New record? → INSERT                                      │
│  - Existing record (same GUID)? → UPDATE                    │
│  - Record deleted in Tally? → DELETE from DB                │
│  ✅ All changes logged to Audit Trail                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Save new AlterID                                    │
│  ─────────────────────────────────────────────────────────── │
│  last_alter_id = 102240 (for next sync)                     │
└─────────────────────────────────────────────────────────────┘
```

### Full Sync vs Incremental Sync

| Aspect | Full Sync | Incremental Sync |
|--------|-----------|------------------|
| **What it does** | Deletes all data, fetches everything fresh | Fetches only changed records |
| **Time** | 5-15 minutes | 10-60 seconds |
| **When to use** | First sync, data corruption recovery | Regular updates |
| **Data Safety** | Replaces all data | Preserves existing data |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Tally ERP 9 or Tally Prime (with ODBC enabled)
- pip (Python package manager)

### 1. Clone Repository

```bash
git clone https://github.com/ganeshchavan786/TallyInsight.git
cd TallyInsight
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Enable Tally ODBC Server

In Tally ERP 9/Prime:
1. Go to **Gateway of Tally** → **F12: Configure** → **Advanced Configuration**
2. Set **Enable ODBC Server** to **Yes**
3. Set **Port** to **9000**

### 4. Run Server

```bash
python run.py
```

### 5. Open Dashboard

```
http://localhost:8000
```

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Tally ERP     │────▶│  TallyInsight   │────▶│   Database      │
│   (Port 9000)   │ XML │  FastAPI Server │ SQL │  (Multi-DB)     │
│                 │ TDL │  (Port 8000)    │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │   Web    │ │  Mobile  │ │ Desktop  │
              │Dashboard │ │   PWA    │ │   App    │
              └──────────┘ └──────────┘ └──────────┘
```

### Core Services

| Service | Description |
|---------|-------------|
| **Tally Service** | XML/TDL communication with Tally ERP |
| **Sync Service** | Full & Incremental sync orchestration |
| **Database Service** | Multi-database abstraction layer |
| **Audit Service** | Change tracking and recovery |
| **XML Builder** | Dynamic TDL query generation |

### Supported Databases

| Database | Status | Adapter |
|----------|--------|---------|
| SQLite | ✅ Production Ready | `sqlite_adapter.py` |
| PostgreSQL | ✅ Production Ready | `postgresql_adapter.py` |
| MySQL | ✅ Production Ready | `mysql_adapter.py` |
| SQL Server | ✅ Production Ready | `sqlserver_adapter.py` |
| MongoDB | ✅ Production Ready | `mongodb_adapter.py` |

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

**Response:**
```json
{
  "status": "started",
  "message": "Incremental sync started for My Company"
}
```

### Data Access

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/data/groups` | GET | Get all account groups |
| `/api/data/ledgers` | GET | Get all ledgers |
| `/api/data/vouchers` | GET | Get vouchers with filters |
| `/api/data/stock-items` | GET | Get stock items |
| `/api/data/synced-companies` | GET | Get synced companies |
| `/api/data/counts` | GET | Get table record counts |

### Audit Trail

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/audit/stats` | GET | Get audit statistics |
| `/api/audit/history` | GET | Get audit history |
| `/api/audit/deleted` | GET | Get deleted records |
| `/api/audit/restore/{id}` | POST | Restore deleted record |

**Example: Get Audit Stats**
```bash
curl "http://localhost:8000/api/audit/stats"
```

**Response:**
```json
{
  "by_action": {"DELETE": 5, "INSERT": 100, "UPDATE": 50},
  "by_table": {"mst_ledger": 80, "mst_stock_item": 75},
  "pending_deleted_records": 5
}
```

### Health Check

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Full health check |
| `/api/health/tally` | GET | Tally connection status |

---

## 🗄️ Database Schema

### Master Tables

| Table | Description | Key Fields |
|-------|-------------|------------|
| `mst_group` | Account Groups | guid, name, parent |
| `mst_ledger` | Ledger Accounts | guid, name, parent, opening_balance |
| `mst_stock_group` | Stock Groups | guid, name, parent |
| `mst_stock_item` | Stock Items | guid, name, parent, uom |
| `mst_stock_category` | Stock Categories | guid, name, parent |
| `mst_godown` | Godowns/Warehouses | guid, name, parent |
| `mst_vouchertype` | Voucher Types | guid, name, parent |
| `mst_cost_category` | Cost Categories | guid, name |
| `mst_cost_centre` | Cost Centres | guid, name, parent |
| `mst_employee` | Employees | guid, name |
| `mst_uom` | Units of Measure | guid, name |

### Transaction Tables

| Table | Description | Key Fields |
|-------|-------------|------------|
| `trn_voucher` | All Vouchers | guid, date, voucher_type, voucher_number |
| `trn_accounting` | Accounting Entries | guid, ledger, amount |
| `trn_inventory` | Inventory Entries | guid, item, quantity, rate |
| `trn_bill` | Bill-wise Details | guid, ledger, name, amount |
| `trn_batch` | Batch Details | guid, item, name, quantity |
| `trn_bank` | Bank Allocations | guid, ledger, instrument_number |

### System Tables

| Table | Description |
|-------|-------------|
| `company_config` | Company sync configuration |
| `audit_log` | All change logs (INSERT/UPDATE/DELETE) |
| `sync_history` | Sync session history |
| `_diff` | Temporary diff comparison table |
| `_delete` | Temporary delete tracking table |

---

## ⚙️ Configuration

### config.yaml

```yaml
# Tally Connection
tally:
  server: localhost
  port: 9000
  timeout: 30

# Database Configuration
database:
  type: sqlite          # sqlite, postgresql, mysql, sqlserver, mongodb
  path: "./tally.db"    # For SQLite
  # host: localhost     # For other databases
  # port: 5432
  # name: tallyinsight
  # user: admin
  # password: secret

# API Server
api:
  host: "0.0.0.0"
  port: 8000
  debug: false

# Logging
logging:
  level: INFO
  file: "./logs/app.log"
```

### Auto Sync Configuration

Auto sync interval can be configured in the web dashboard:
- **5 minutes** (default)
- **10 minutes**
- **15 minutes**
- **30 minutes**
- **60 minutes**

---

## 📁 Project Structure

```
TallyInsight/
├── app/
│   ├── controllers/           # API endpoint handlers
│   │   ├── sync_controller.py
│   │   ├── data_controller.py
│   │   ├── audit_controller.py
│   │   └── health_controller.py
│   ├── services/              # Business logic
│   │   ├── sync_service.py    # Sync orchestration
│   │   ├── tally_service.py   # Tally communication
│   │   ├── audit_service.py   # Audit trail
│   │   ├── xml_builder.py     # TDL query builder
│   │   └── database/          # Database adapters
│   │       ├── base.py
│   │       ├── sqlite_adapter.py
│   │       ├── postgresql_adapter.py
│   │       ├── mysql_adapter.py
│   │       ├── sqlserver_adapter.py
│   │       └── mongodb_adapter.py
│   ├── models/                # Pydantic models
│   └── config.py              # Configuration
├── static/                    # Web dashboard
│   ├── css/
│   ├── js/
│   └── assets/
├── logs/                      # Log files
├── config.yaml                # Configuration file
├── requirements.txt           # Python dependencies
├── run.py                     # Entry point
└── README.md
```

---

## 🔧 Troubleshooting

### Tally Connection Failed
1. Ensure Tally is running with ODBC enabled
2. Check port 9000 is not blocked
3. Verify Tally server address in config.yaml

### Sync Stuck at 0%
1. Check Tally connection status
2. Verify company is open in Tally
3. Check logs for errors

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

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024-2026 Ganesh Chavan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Tally Solutions](https://tallysolutions.com/) - ERP software
- [SQLite](https://sqlite.org/) - Lightweight database

---

## 📞 Support

- 📧 Email: ganeshchavan786@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/ganeshchavan786/TallyInsight/issues)
- 📖 Docs: [API Documentation](http://localhost:8000/docs)

---

<p align="center">
  <strong>Made with ❤️ for the Tally community</strong>
</p>

<p align="center">
  ⭐ Star this repo if you find it useful!
</p>
