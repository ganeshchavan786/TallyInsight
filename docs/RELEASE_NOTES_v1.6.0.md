# Release Notes - v1.6.0

## Ledger Report Feature

### Overview
Tally-style Ledger Report with Transactions and Bill-wise views, searchable ledger dropdown, and professional UI.

---

## New Features

### 1. Ledger Report Menu
- New "Ledger" menu item in sidebar
- Searchable ledger dropdown with 6000+ ledgers
- Date range filters (From Date, To Date)
- Auto-load on ledger selection

### 2. Transactions Tab
- Shows all transactions for selected ledger
- Running balance calculation
- Opening Balance row
- Closing Balance row with totals
- Columns: Date, Particulars, Voucher Type, Voucher No., Debit, Credit, Balance

### 3. Bill-wise Tab (Pending Bills)
- Tally-style 2-row format per bill
- Row 1: Bill details (Date, Ref No., Opening Amount, Pending Amount, Due Date, Overdue Days)
- Row 2: Opening Balance sub-row
- Sub Total row
- On Account row (calculated from Bills Total - Ledger Opening Balance)
- Cr/Dr suffix on amounts like Tally

---

## Database Tables Used

### 1. mst_ledger
- Stores ledger master data
- Fields: `name`, `parent`, `opening_balance`, `closing_balance`, `_company`
- Used for: Ledger dropdown, Opening Balance calculation

### 2. mst_opening_bill_allocation
- Stores opening bill allocations
- Fields: `ledger`, `name` (bill_no), `bill_date`, `opening_balance`, `bill_credit_period`, `_company`
- Used for: Opening bills in Bill-wise report

### 3. trn_voucher
- Stores voucher transactions
- Fields: `guid`, `date`, `voucher_type`, `voucher_number`, `_company`
- Used for: Transaction dates, voucher types

### 4. trn_accounting
- Stores accounting entries
- Fields: `guid`, `ledger`, `amount`, `_company`
- Used for: Debit/Credit amounts in Transactions

### 5. trn_bill
- Stores bill allocations in transactions
- Fields: `guid`, `ledger`, `name` (bill_no), `billtype`, `amount`, `bill_credit_period`, `_company`
- Used for: Transaction bills in Bill-wise report

---

## API Endpoints

### GET /api/data/ledgers
**Purpose:** Get list of ledgers for dropdown

**Parameters:**
- `company` (optional): Filter by company name

**Query:**
```sql
SELECT DISTINCT name FROM mst_ledger 
WHERE _company = ? 
ORDER BY name
```

**Response:**
```json
{
  "ledgers": ["Ledger 1", "Ledger 2", ...],
  "total": 3812
}
```

---

### GET /api/data/ledger-report
**Purpose:** Get ledger transactions with running balance

**Parameters:**
- `ledger` (required): Ledger name
- `company` (optional): Company name
- `from_date` (optional): Start date (YYYY-MM-DD)
- `to_date` (optional): End date (YYYY-MM-DD)

**Query Logic:**
1. Get opening balance from `mst_ledger`
2. Get transactions from `trn_accounting` joined with `trn_voucher`
3. Calculate running balance

**Response:**
```json
{
  "ledger": "Gyankaar Technologies Private Limited",
  "opening_balance": 36464.0,
  "closing_balance": 36464.0,
  "total_debit": 0,
  "total_credit": 0,
  "transactions": [...]
}
```

---

### GET /api/data/ledger-billwise
**Purpose:** Get pending bills for a ledger (Tally-style)

**Parameters:**
- `ledger` (required): Ledger name
- `company` (optional): Company name
- `from_date` (optional): Start date
- `to_date` (optional): End date

**Query Logic:**
```sql
WITH all_bills AS (
    -- Opening bill allocations
    SELECT name as bill_no, bill_date, opening_balance as amount, 'Opening' as source
    FROM mst_opening_bill_allocation
    WHERE ledger = ? AND name != ''
    
    UNION ALL
    
    -- Transaction bills
    SELECT b.name as bill_no, v.date as bill_date,
           CASE WHEN billtype = 'New Ref' THEN ABS(amount)
                WHEN billtype = 'Agst Ref' THEN -ABS(amount)
           END as amount,
           v.voucher_type as source
    FROM trn_bill b
    JOIN trn_voucher v ON b.guid = v.guid
    WHERE b.ledger = ? AND billtype IN ('New Ref', 'Agst Ref')
)
SELECT bill_no, MIN(bill_date), SUM(amount) as pending_amount, ...
FROM all_bills
GROUP BY bill_no
HAVING pending_amount != 0
ORDER BY bill_date
```

**On Account Calculation:**
```
On Account = Bills Sub Total - Ledger Opening Balance
Example: 76,464 Cr - 36,464 Cr = 40,000 Dr
```

**Response:**
```json
{
  "ledger": "Gyankaar Technologies Private Limited",
  "bills": [
    {"bill_no": "PB/2022-23/CP04", "bill_date": "2022-05-31", "opening_amount": 2800, "pending_amount": 2800, ...},
    ...
  ],
  "on_account": 40000,
  "total_bills": 3
}
```

---

## Frontend Files

### 1. static/voucher-report/index.html
- Added Ledger menu item in sidebar
- Added ledgerSection with:
  - Searchable input with dropdown
  - Date filters
  - Stats cards (Opening Balance, Total Debit, Total Credit, Closing Balance)
  - Tabs (Transactions, Bill-wise)
  - Data table

### 2. static/voucher-report/js/app.js
- `showLedgerView()` - Switch to ledger view
- `loadLedgerList()` - Load ledgers for dropdown
- `filterLedgerDropdown()` - Filter ledgers on type
- `selectLedger()` - Select ledger and auto-load
- `loadLedgerReport()` - Load transactions
- `renderLedgerReport()` - Render transactions table
- `switchLedgerTab()` - Switch between tabs
- `loadLedgerBillwise()` - Load bill-wise data
- `renderLedgerBillwise()` - Render bill-wise table with 2-row format

### 3. static/voucher-report/css/style.css
- Custom dropdown styling
- Compact Ledger section styling
- Fixed table column widths
- Source badge styling

---

## UI Features

1. **Searchable Dropdown** - Type to filter 6000+ ledgers
2. **Auto-load** - Report loads automatically on ledger selection
3. **Date Change Reload** - Report reloads when dates change
4. **Company Switch** - Ledger list reloads on company change
5. **2-Row Bill Format** - Like Tally's Pending Bills view
6. **Cr/Dr Suffix** - Amounts show Cr/Dr like Tally
7. **On Account Row** - Calculated from Bills Total - Opening Balance
8. **Compact UI** - Smaller fonts, tighter spacing

---

## Summary

| Feature | Status |
|---------|--------|
| Ledger dropdown with search | ✅ |
| Transactions tab | ✅ |
| Bill-wise tab | ✅ |
| On Account calculation | ✅ |
| 2-row bill format | ✅ |
| Cr/Dr display | ✅ |
| Company switch support | ✅ |
| Compact UI | ✅ |

---

**Release Date:** 13-Jan-2026
**Version:** v1.6.0
