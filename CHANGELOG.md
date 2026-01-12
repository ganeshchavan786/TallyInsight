# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v2.6.1] - 2026-01-12

### Fixed
- **Date Parsing Bug**: Fixed `parseTallyDate()` function to correctly handle `YYYY-MM-DD` format
  - Previously, dates like `2025-09-01` were incorrectly parsed as `2001-01-2025`
  - Now correctly returns `YYYY-MM-DD` format dates as-is
- **Date Display**: Fixed `formatDateDisplay()` to properly format `YYYY-MM-DD` dates for display

### Changed
- Removed debug console.log statements from production code

---

## [v2.6.0] - 2026-01-11

### Added
- **Chunked Sync for Large Data**: Transaction data is now synced in 3-month chunks when period > 1 year
  - Prevents Tally timeout errors for large datasets
  - Each chunk is processed sequentially with progress tracking
  
- **Rate Limiting**: Added 2-second delay between chunk processing
  - Reduces load on Tally server
  - Prevents Tally from hanging during large syncs
  
- **Circular Progress Bar**: New visual progress indicator in company cards
  - Shows sync percentage in center of circle
  - Replaces action buttons during sync
  - Works for both new companies and synced companies
  
- **Delete Company Feature**: Users can now delete synced companies
  - Added "Delete Company" option in dropdown menu
  - Deletes all company data from all tables
  - Removes company from `company_config` table
  - New API endpoint: `DELETE /api/data/company/{company_name}`
  
- **Dropdown Auto-close**: Dropdown menus now close automatically when:
  - An option is clicked
  - User clicks outside the dropdown

### Changed
- **Sync Progress UI**: Removed bottom "Sync Progress" card
  - Progress now shown only in circular progress bar within company card
  - Cleaner, less cluttered interface

### Fixed
- **UNIQUE Constraint Errors**: Changed `INSERT` to `INSERT OR REPLACE` in bulk operations
- **Health Check Disconnect**: Removed `disconnect()` call from health check that was closing DB during sync
- **Tally Connection Timeout**: Increased HTTP timeout from 60s to 300s for large data requests

### Technical Details

#### Chunked Sync Implementation
```python
# sync_service.py - _sync_transaction_data()
# Generates 3-month date chunks for periods > 1 year
date_chunks = self._generate_date_chunks(from_date, to_date, chunk_months=3)

# Rate limiting between chunks
await asyncio.sleep(2)  # 2 second delay
```

#### Delete Company API
```python
# DELETE /api/data/company/{company_name}
# Deletes from all tables where _company = company_name
# Also removes from company_config table
```

#### Circular Progress CSS
```css
.circular-progress {
    width: 48px;
    height: 48px;
    /* SVG circle with stroke-dasharray animation */
}
```

---

## [v2.5.0] - 2026-01-10

### Added
- Period storage in `company_config` table (`books_from`, `books_to`)
- Period auto-detection from company name patterns
- Period display in synced company list

### Changed
- Full sync and incremental sync now use stored period
- Improved company card UI with period information

---

## [v2.4.0] - 2026-01-09

### Added
- Incremental sync with GUID+AlterID comparison
- `_diff` table for tracking changes
- `_delete` table for tracking deletions

---

## [v2.3.0] - 2026-01-08

### Added
- Multi-company support with `_company` column
- Company-specific data truncation
- Company configuration table

---

## [v2.2.0] - 2026-01-07

### Added
- Audit trail system
- INSERT/UPDATE/DELETE tracking
- Data recovery capabilities

---

## [v2.1.0] - 2026-01-06

### Added
- Web dashboard for sync management
- Real-time sync progress display
- Tally connection status indicator

---

## [v2.0.0] - 2026-01-05

### Added
- FastAPI backend (migrated from Node.js)
- Async database operations
- Improved error handling

---

## [v1.2.0] - 2026-01-04

### Added
- Transaction tables support
- Date range filtering for sync

---

## [v1.1.0] - 2026-01-03

### Added
- Master tables sync
- Basic CRUD operations

---

## [v1.0.0] - 2026-01-02

### Added
- Initial release
- Basic Tally connection
- SQLite database setup
