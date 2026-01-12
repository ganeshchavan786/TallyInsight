# Database Configuration Guide

## Supported Databases

Tally FastAPI Database Loader supports multiple databases:

| Database | Use Case | Status |
|----------|----------|--------|
| **SQLite** | Local development, single-user | ✅ Default |
| **SQL Server** | Enterprise, Windows environments | ✅ Supported |
| **PostgreSQL** | Cloud, Linux production | ✅ Supported |
| **MySQL** | Web applications, shared hosting | ✅ Supported |
| **MongoDB** | NoSQL, document storage | ✅ Supported |

---

## Quick Setup

### 1. SQLite (Default - Zero Configuration)

SQLite is the default database. No setup required.

```yaml
# config.yaml
database:
  type: sqlite
  path: ./tally.db
```

**Pros:**
- Zero configuration
- No server required
- Single file database
- Perfect for development

**Cons:**
- Not suitable for high-traffic
- Limited concurrent writes

---

### 2. SQL Server (Enterprise/Windows)

#### Prerequisites

**Windows:**
1. Download and install [ODBC Driver 17 for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
2. Install Python driver:
   ```bash
   pip install pyodbc
   ```

**Linux (Ubuntu/Debian):**
```bash
# Add Microsoft repository
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

# Install ODBC driver
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17

# Install Python driver
pip install pyodbc
```

#### Configuration

```yaml
# config.yaml
database:
  type: sqlserver
  host: localhost
  port: 1433
  database: TallyDB
  username: sa
  password: YourPassword123
  driver: "ODBC Driver 17 for SQL Server"
```

#### Connection String Examples

```yaml
# Local SQL Server
database:
  type: sqlserver
  host: localhost
  database: TallyDB
  username: sa
  password: Password123

# SQL Server with Windows Authentication
database:
  type: sqlserver
  host: localhost
  database: TallyDB
  trusted_connection: true

# Azure SQL Database
database:
  type: sqlserver
  host: yourserver.database.windows.net
  database: TallyDB
  username: admin
  password: Password123
```

---

### 3. PostgreSQL (Cloud/Linux)

#### Prerequisites

**Windows:**
1. Download and install [PostgreSQL](https://www.postgresql.org/download/windows/)
2. Install Python driver:
   ```bash
   pip install asyncpg
   ```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# Install Python driver
pip install asyncpg
```

**Docker:**
```bash
docker run -d \
  --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=tallydb \
  -p 5432:5432 \
  postgres:15
```

#### Configuration

```yaml
# config.yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  database: tallydb
  username: postgres
  password: password
```

#### Connection String Examples

```yaml
# Local PostgreSQL
database:
  type: postgresql
  host: localhost
  database: tallydb
  username: postgres
  password: password

# AWS RDS PostgreSQL
database:
  type: postgresql
  host: mydb.xxxxx.us-east-1.rds.amazonaws.com
  port: 5432
  database: tallydb
  username: admin
  password: password

# Heroku PostgreSQL
database:
  type: postgresql
  url: postgres://user:pass@host:5432/dbname
```

---

### 4. MySQL (Web Applications)

#### Prerequisites

**Windows:**
1. Download and install [MySQL](https://dev.mysql.com/downloads/installer/)
2. Install Python driver:
   ```bash
   pip install aiomysql
   ```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install mysql-server

# Install Python driver
pip install aiomysql
```

**Docker:**
```bash
docker run -d \
  --name mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=tallydb \
  -p 3306:3306 \
  mysql:8
```

#### Configuration

```yaml
# config.yaml
database:
  type: mysql
  host: localhost
  port: 3306
  database: tallydb
  username: root
  password: password
```

---

### 5. MongoDB (NoSQL/Document Store)

#### Prerequisites

**Windows:**
1. Download and install [MongoDB Community Server](https://www.mongodb.com/try/download/community)
2. Install Python driver:
   ```bash
   pip install motor
   ```

**Linux:**
```bash
# Ubuntu/Debian
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod

# Install Python driver
pip install motor
```

**Docker:**
```bash
docker run -d \
  --name mongodb \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password \
  -p 27017:27017 \
  mongo:6
```

#### Configuration

```yaml
# config.yaml
database:
  type: mongodb
  host: localhost
  port: 27017
  database: tallydb
  username: admin        # optional
  password: password     # optional
```

#### Connection String Examples

```yaml
# Local MongoDB (no auth)
database:
  type: mongodb
  host: localhost
  database: tallydb

# MongoDB with authentication
database:
  type: mongodb
  host: localhost
  database: tallydb
  username: admin
  password: password

# MongoDB Atlas (Cloud)
database:
  type: mongodb
  url: mongodb+srv://user:pass@cluster.mongodb.net/tallydb

# MongoDB Replica Set
database:
  type: mongodb
  url: mongodb://host1:27017,host2:27017,host3:27017/tallydb?replicaSet=rs0
```

---

## Database Selection Guide

| Scenario | Recommended Database |
|----------|---------------------|
| Local development | SQLite |
| Single user/small team | SQLite |
| Enterprise/Corporate | SQL Server |
| Cloud deployment | PostgreSQL |
| Windows environment | SQL Server or SQLite |
| Linux environment | PostgreSQL |
| Shared hosting | MySQL |
| High traffic | PostgreSQL or SQL Server |
| Document-based queries | MongoDB |
| Flexible schema | MongoDB |

---

## Switching Databases

### Step 1: Install Required Driver

```bash
# SQLite (built-in, no install needed)

# SQL Server
pip install pyodbc

# PostgreSQL
pip install asyncpg

# MySQL
pip install aiomysql

# MongoDB
pip install motor
```

### Step 2: Update config.yaml

```yaml
# Change database type
database:
  type: postgresql  # sqlite, sqlserver, postgresql, mysql, mongodb
  host: localhost
  port: 5432
  database: tallydb
  username: postgres
  password: password
```

### Step 3: Create Database

```sql
-- SQL Server
CREATE DATABASE TallyDB;

-- PostgreSQL
CREATE DATABASE tallydb;

-- MySQL
CREATE DATABASE tallydb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

For MongoDB, database is created automatically.

### Step 4: Run Application

```bash
python run.py
```

Tables/Collections will be created automatically on first run.

---

## Environment Variables

You can also use environment variables:

```bash
# Windows (PowerShell)
$env:DATABASE_TYPE = "postgresql"
$env:DATABASE_HOST = "localhost"
$env:DATABASE_PORT = "5432"
$env:DATABASE_NAME = "tallydb"
$env:DATABASE_USER = "postgres"
$env:DATABASE_PASSWORD = "password"

# Linux/Mac
export DATABASE_TYPE=postgresql
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_NAME=tallydb
export DATABASE_USER=postgres
export DATABASE_PASSWORD=password
```

---

## Connection Pooling

For production databases, connection pooling is automatically configured:

| Setting | Default | Description |
|---------|---------|-------------|
| `pool_size` | 10 | Number of connections to keep |
| `max_overflow` | 20 | Extra connections when pool is full |
| `pool_recycle` | 300 | Recycle connections after 5 minutes |
| `pool_pre_ping` | true | Check connection before use |

Custom pool settings:

```yaml
database:
  type: postgresql
  host: localhost
  database: tallydb
  pool_size: 20
  max_overflow: 30
  pool_recycle: 600
```

---

## Data Migration

### Export from SQLite

```bash
python -m app.tools.export --format json --output backup.json
```

### Import to New Database

```bash
# Update config.yaml to new database first
python -m app.tools.import --input backup.json
```

---

## Troubleshooting

### SQLite

**Error:** `database is locked`
- Solution: Close other connections or enable WAL mode

### SQL Server

**Error:** `Can't find ODBC driver`
- Solution: Install ODBC Driver 17 for SQL Server

**Error:** `Login failed`
- Solution: Check username/password and SQL Server authentication mode

### PostgreSQL

**Error:** `connection refused`
- Solution: Check if PostgreSQL is running: `sudo systemctl status postgresql`

**Error:** `password authentication failed`
- Solution: Check pg_hba.conf and password

### MySQL

**Error:** `Access denied`
- Solution: Check username/password and user privileges

### MongoDB

**Error:** `connection refused`
- Solution: Check if MongoDB is running: `sudo systemctl status mongod`

**Error:** `Authentication failed`
- Solution: Check username/password and authSource

---

## Platform-Specific Notes

### Windows

- SQLite: Works out of the box
- SQL Server: Install ODBC Driver from Microsoft
- PostgreSQL: Use installer from postgresql.org
- MySQL: Use MySQL Installer
- MongoDB: Use MSI installer from mongodb.com

### Linux (Ubuntu/Debian)

- SQLite: Built into Python
- SQL Server: Install msodbcsql17 package
- PostgreSQL: `apt-get install postgresql`
- MySQL: `apt-get install mysql-server`
- MongoDB: Add MongoDB repo and install

### macOS

- SQLite: Built into Python
- SQL Server: Install via Homebrew: `brew install msodbcsql17`
- PostgreSQL: `brew install postgresql`
- MySQL: `brew install mysql`
- MongoDB: `brew install mongodb-community`

### Docker

All databases can be run in Docker containers. See examples above.

---

## Best Practices

1. **Development:** Use SQLite for simplicity
2. **Testing:** Use SQLite with in-memory database
3. **Staging:** Use same database as production
4. **Production:** Use SQL Server, PostgreSQL, or MySQL with proper backups
5. **Always:** Keep config.yaml out of version control (use .env or environment variables)

---

*Last Updated: January 2026*
