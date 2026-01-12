# Developer Notes - Tally Database Loader

## Company Period Auto-Detection

### Overview
The sync page automatically extracts financial year period from company names when Tally API doesn't provide `books_from` and `books_to` data.

### How It Works

#### 1. Company Name Pattern: `YY-YY` (e.g., "18-24")
Many Tally companies include financial year in their name:
- `MATOSHRI ENTERPRISES 18-24` → Apr 2018 to Mar 2024
- `Vrushali Infotech Pvt Ltd. 25-26` → Apr 2025 to Mar 2026

**Logic:**
```javascript
// Pattern: /(\d{2})-(\d{2})$/
// "18-24" → from: 2018-04-01, to: 2024-03-31
```

#### 2. Company Name Pattern: `(from D-Mon-YY)` 
Some companies have start date in name:
- `Test23131131313131sdfd - (from 1-Sep-25)` → Sep 2025 to Mar 2026

**Logic:**
```javascript
// Pattern: /\(from\s+(\d{1,2})-([A-Za-z]{3})-(\d{2})\)/i
// "(from 1-Sep-25)" → from: 2025-09-01, to: 2026-03-31
```

#### 3. Fallback: Default Period
If no pattern matches:
- Default From: `2025-04-01`
- Default To: `2026-03-31`

### Code Location
- **Frontend:** `static/js/sync.js` - `extractPeriodFromName()` function
- **Backend:** `app/services/tally_service.py` - `_parse_company_list_with_period()`

### Tally API Limitation

**Issue:** Tally's "List of Companies" collection doesn't always return `BOOKSFROM` data.

**Expected XML Response:**
```xml
<COMPANY NAME="CompanyName">
    <BOOKSFROM>20180401</BOOKSFROM>
    <STARTINGFROM>20180401</STARTINGFROM>
    <COMPANYNUMBER>100001</COMPANYNUMBER>
</COMPANY>
```

**Actual Response:** Often returns empty `BOOKSFROM` field.

**Workaround:** Extract period from company name pattern.

### Future Improvement
To get accurate period from Tally, use TDL report with company-specific query:
```xml
<FIELD NAME="FldBooksFrom">
    <SET>$BooksFrom</SET>
</FIELD>
```

This requires selecting each company individually and querying its info.

---

## Sync Page Features

### 1. Synced Companies Hidden
- Only NEW (unsynced) companies shown in list
- Synced companies checked via `/api/data/synced-companies` endpoint

### 2. Per-Company Actions
Each company row has:
- **Checkbox** - Select for batch sync
- **Period Display** - Auto-extracted or editable
- **Pencil Button** - Edit period manually
- **Sync Button** - Full sync for that company

### 3. Period Edit Modal
Users can manually edit period via pencil button:
- Opens modal with From/To date inputs
- Saves to `companyPeriods` object
- Updates display immediately

---

## API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `/api/companies` | Get companies from Tally |
| `/api/data/synced-companies` | Get synced companies from DB |
| `/api/sync/full` | Start full sync |
| `/api/sync/status` | Get sync progress |

---

## File Structure

```
static/
├── sync.html          # Sync page HTML
├── dashboard.html     # Dashboard page
├── audit.html         # Audit trail page
├── css/
│   ├── common.css     # Shared styles (light theme)
│   ├── sync.css       # Sync page styles
│   ├── dashboard.css  # Dashboard styles
│   └── audit.css      # Audit page styles
└── js/
    ├── common.js      # Shared functions (API, toast, etc.)
    ├── sync.js        # Sync page logic
    ├── dashboard.js   # Dashboard logic
    └── audit.js       # Audit page logic
```

---

## Known Issues

1. **Tally Period Not Returned:** Tally API doesn't return `books_from` in collection request
2. **Company Name Parsing:** Only works for standard naming patterns

---

## v2.6.0+ New Features

### 1. Chunked Sync for Large Data (v2.6.0)

**Problem:** Tally hangs/times out when syncing transaction data for periods > 1 year.

**Solution:** Break sync into 3-month chunks with rate limiting.

**Implementation:**
```python
# sync_service.py

def _generate_date_chunks(self, from_date, to_date, chunk_months=3):
    """Generate date chunks for large period sync"""
    chunks = []
    current = from_date
    while current < to_date:
        chunk_end = min(current + relativedelta(months=chunk_months), to_date)
        chunks.append((current, chunk_end))
        current = chunk_end
    return chunks

async def _sync_transaction_data(self, parallel=False):
    # For periods > 1 year, use chunked sync
    date_chunks = self._generate_date_chunks(from_date, to_date, chunk_months=3)
    
    for chunk_idx, (chunk_start, chunk_end) in enumerate(date_chunks):
        # Sync each chunk
        await self._extract_table_data_with_dates(table, chunk_start, chunk_end)
        
        # Rate limiting: 2 sec delay between chunks
        if chunk_idx < len(date_chunks) - 1:
            await asyncio.sleep(2)
```

**Benefits:**
- Prevents Tally timeout
- Reduces memory usage
- Progress tracking per chunk
- Tally gets breathing room between chunks

---

### 2. Circular Progress Bar (v2.6.0)

**Location:** Company cards (both new and synced)

**HTML Structure:**
```html
<div class="circular-progress" id="progress-{companyId}">
    <svg viewBox="0 0 44 44">
        <circle class="progress-bg" cx="22" cy="22" r="20"></circle>
        <circle class="progress-bar" cx="22" cy="22" r="20"></circle>
    </svg>
    <span class="progress-text">0%</span>
</div>
```

**CSS Animation:**
```css
.circular-progress .progress-bar {
    stroke-dasharray: 126;  /* 2 * PI * r (r=20) */
    stroke-dashoffset: 126; /* Start at 0% */
    transition: stroke-dashoffset 0.3s ease;
}
```

**JavaScript Update:**
```javascript
function updateCircularProgress(companyName, percent) {
    const circumference = 126;
    const offset = circumference - (percent / 100) * circumference;
    progressBar.style.strokeDashoffset = offset;
    progressText.textContent = `${percent}%`;
}
```

---

### 3. Delete Company Feature (v2.6.0)

**Frontend:**
```javascript
async function deleteCompany(companyName) {
    if (!confirm(`Delete "${companyName}"?`)) return;
    await apiCall(`/api/data/company/${encodeURIComponent(companyName)}`, { method: 'DELETE' });
    loadSyncedCompanies();
    loadCompanies();
}
```

**Backend API:**
```python
@router.delete("/company/{company_name}")
async def delete_company(company_name: str):
    deleted_count = await database_service.delete_company_data(company_name)
    return {"success": True, "deleted_rows": deleted_count}
```

**Database Service:**
```python
async def delete_company_data(self, company_name: str) -> int:
    total_deleted = 0
    for table in ALL_TABLES:
        # Delete where _company = company_name
        await conn.execute(f"DELETE FROM {table} WHERE _company = ?", (company_name,))
    # Also delete from company_config
    await conn.execute("DELETE FROM company_config WHERE company_name = ?", (company_name,))
    return total_deleted
```

---

### 4. Date Parsing Fix (v2.6.1)

**Problem:** `parseTallyDate()` was incorrectly parsing `YYYY-MM-DD` format.

**Example Bug:**
- Input: `2025-09-01`
- Old Output: `2001-01-2025` (wrong!)
- New Output: `2025-09-01` (correct)

**Fix:**
```javascript
function parseTallyDate(dateStr) {
    if (!dateStr) return null;
    
    // Already in YYYY-MM-DD format - return as is
    if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
        return dateStr;
    }
    
    // Handle "1-Apr-25" format...
}
```

---

### 5. Dropdown Auto-close (v2.6.0)

**Implementation:**
```javascript
function closeAllDropdowns() {
    document.querySelectorAll('.dropdown-menu.show').forEach(d => d.classList.remove('show'));
}

// Close on option click
<a class="dropdown-item" onclick="closeAllDropdowns(); doAction()">

// Close on outside click
document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown')) {
        closeAllDropdowns();
    }
});
```

---

## API Endpoints (Updated)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/data/companies` | GET | Get companies from Tally |
| `/api/data/synced-companies` | GET | Get synced companies from DB |
| `/api/data/company/{name}` | DELETE | **NEW** Delete company data |
| `/api/sync/full` | POST | Start full sync |
| `/api/sync/incremental` | POST | Start incremental sync |
| `/api/sync/status` | GET | Get sync progress |
| `/api/sync/cancel` | POST | Cancel running sync |

---

## Contributing
When adding new features:
1. Follow existing code style
2. Add developer notes for complex logic
3. Test with multiple company name formats
4. Update CHANGELOG.md with changes
