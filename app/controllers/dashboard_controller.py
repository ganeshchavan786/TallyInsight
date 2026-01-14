"""
Dashboard Controller
Handles dashboard API endpoints (Counts, Companies, Query)

================================================================================
DEVELOPER NOTES
================================================================================
File: dashboard_controller.py
Purpose: Handle dashboard statistics and company management
Prefix: /api/data

BUSINESS LOGIC:
---------------
1. Counts API (/counts):
   - Returns row counts for all tables (master + transaction)
   - Used in: Dashboard page to show data overview
   - Parameter: company_name (required for filtering)
   
2. Synced Companies API (/synced-companies):
   - Returns list of companies synced to database
   - Source: sync_companies table
   - Shows: company_name, last_sync_at, sync_count, books_from, books_to
   
3. Companies API (/companies):
   - Returns company details from database
   - Used in: Company selection dropdown
   
4. Delete Company API (DELETE /company/{name}):
   - Deletes all data for a company from all tables
   - Cascades: master tables, transaction tables, sync_companies
   - WARNING: Irreversible operation!
   
5. Query API (POST /query):
   - Executes custom SQL query (SELECT only)
   - Used in: Debug/admin tools
   - Security: Only SELECT queries allowed

DASHBOARD METRICS:
------------------
Master Tables: mst_group, mst_ledger, mst_vouchertype, mst_stock_item, etc.
Transaction Tables: trn_voucher, trn_accounting, trn_inventory, trn_bill, etc.

IMPORTANT:
----------
- company_name parameter is REQUIRED for counts API
- Delete operation removes data from ALL tables for that company
- Query API is for debugging only, not for production use

DEPENDENCIES:
-------------
- sync_companies: Tracks synced company metadata
- All mst_* and trn_* tables for counts
================================================================================
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ..services.database_service import database_service
from ..services.tally_service import tally_service
from ..utils.logger import logger

router = APIRouter()


@router.post("/query")
async def execute_query(query_request: dict):
    """Execute custom SQL query (SELECT only)"""
    query = query_request.get("query", "")
    
    # Security: Only allow SELECT queries
    if not query.strip().upper().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    
    try:
        await database_service.connect()
        data = await database_service.fetch_all(query)
        
        return {
            "columns": list(data[0].keys()) if data else [],
            "data": data,
            "row_count": len(data)
        }
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/counts")
async def get_table_counts(company: Optional[str] = None):
    """Get row counts for all tables, optionally filtered by company"""
    try:
        await database_service.connect()
        counts = await database_service.get_all_table_counts(company_name=company)
        return counts
    except Exception as e:
        logger.error(f"Failed to get counts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/synced-companies")
async def get_synced_companies():
    """Get list of synced companies from company_config table"""
    try:
        await database_service.connect()
        companies = await database_service.get_synced_companies()
        return {"companies": companies, "count": len(companies)}
    except Exception as e:
        logger.error(f"Failed to get synced companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies")
async def get_tally_companies():
    """Get list of all open companies from Tally with current company indicator"""
    try:
        # Get open companies from Tally
        open_companies = await tally_service.get_open_companies()
        logger.info(f"Open companies from Tally: {open_companies}")
        
        # Get current company info
        current_company_info = await tally_service.get_company_info()
        current_company_name = current_company_info.get("name", "")
        logger.info(f"Current company: {current_company_name}")
        
        # Mark current company in the list
        for company in open_companies:
            company["is_current"] = company.get("name", "") == current_company_name
        
        return {
            "companies": open_companies,
            "current_company": current_company_name,
            "count": len(open_companies)
        }
    except Exception as e:
        logger.error(f"Failed to get Tally companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/company/{company_name}")
async def delete_company(company_name: str):
    """Delete all data for a specific company from the database"""
    try:
        await database_service.connect()
        deleted_count = await database_service.delete_company_data(company_name)
        logger.info(f"Deleted company '{company_name}': {deleted_count} rows removed")
        return {
            "success": True,
            "message": f"Company '{company_name}' deleted successfully",
            "deleted_rows": deleted_count
        }
    except Exception as e:
        logger.error(f"Failed to delete company '{company_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
