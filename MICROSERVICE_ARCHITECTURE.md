# TallyInsight Microservice Architecture

## 🏗️ Microservice Structure

```
D:\Microservice\TallyInsight\
├── services/                    # Individual microservices
│   ├── tally-service/          # Tally ERP integration
│   ├── analytics-service/       # Data processing
│   ├── report-service/          # Report generation
│   ├── notification-service/    # Alerts & notifications
│   └── dashboard-service/       # Frontend UI
├── shared/                      # Common utilities
│   ├── database/               # Database models
│   ├── utils/                  # Helper functions
│   └── config/                 # Shared configuration
├── gateway/                     # API Gateway
├── infrastructure/              # Docker, K8s configs
└── monitoring/                  # Logging, metrics
```

## 🚀 Services Overview

### 1. Tally Service
- **Port:** 8001
- **Purpose:** Tally ERP XML/TDL communication
- **Endpoints:**
  - `/api/tally/companies`
  - `/api/tally/sync`
  - `/api/tally/health`

### 2. Analytics Service
- **Port:** 8002
- **Purpose:** Data processing and insights
- **Endpoints:**
  - `/api/analytics/summary`
  - `/api/analytics/trends`
  - `/api/analytics/reports`

### 3. Report Service
- **Port:** 8003
- **Purpose:** Dynamic report generation
- **Endpoints:**
  - `/api/reports/generate`
  - `/api/reports/download`
  - `/api/reports/schedule`

### 4. Notification Service
- **Port:** 8004
- **Purpose:** Alerts and notifications
- **Endpoints:**
  - `/api/notifications/send`
  - `/api/notifications/subscribe`
  - `/api/notifications/history`

### 5. Dashboard Service
- **Port:** 8005
- **Purpose:** Frontend UI
- **Endpoints:**
  - `/` - Main dashboard
  - `/static` - Static assets
  - `/api/config` - UI configuration

## 🔧 Technology Stack

- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL/SQLite
- **Cache:** Redis
- **Message Queue:** RabbitMQ
- **Container:** Docker
- **Orchestration:** Docker Compose
- **Monitoring:** Prometheus + Grafana

## 📋 Next Steps

1. **Create individual service folders**
2. **Setup API Gateway**
3. **Configure service discovery**
4. **Implement inter-service communication**
5. **Setup monitoring and logging**
