"""
Voucher Controller
Handles voucher API endpoints (Vouchers, Voucher Details)

================================================================================
DEVELOPER NOTES
================================================================================
File: voucher_controller.py
Purpose: Handle voucher transaction queries
Prefix: /api/data

BUSINESS LOGIC:
---------------
1. Vouchers API (/vouchers):
   - Returns vouchers from trn_voucher table
   - Filters: voucher_type, date range, company
   - Used in: Voucher list, Transaction reports
   
2. Voucher Details API (/vouchers/{guid}/details):
   - Returns single voucher with all line items
   - Joins: trn_accounting (ledger entries), trn_inventory (stock entries)
   - Used in: Voucher detail popup/page

TALLY VOUCHER TYPES:
--------------------
- Sales, Purchase, Receipt, Payment, Journal
- Contra, Credit Note, Debit Note
- Stock Journal, Physical Stock, etc.

IMPORTANT:
----------
- GUID is unique identifier for each voucher
- Date format: YYYY-MM-DD
- Amount: Positive for debit, Negative for credit

DEPENDENCIES:
-------------
- trn_voucher: Voucher headers
- trn_accounting: Accounting entries (ledger-wise)
- trn_inventory: Inventory entries (item-wise)
================================================================================
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ..services.database_service import database_service
from ..utils.logger import logger

router = APIRouter()


@router.get("/vouchers")
async def get_vouchers(
    voucher_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    company: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """Get vouchers with filters and calculated amounts"""
    try:
        await database_service.connect()
        
        # Query with amount calculated from trn_accounting (debit side = negative amounts, take first one)
        query = """
            SELECT v.*, 
                   COALESCE((SELECT ABS(a.amount) FROM trn_accounting a WHERE a.guid = v.guid AND a.amount < 0 LIMIT 1), 0) as amount
            FROM trn_voucher v
        """
        params = []
        conditions = []
        
        if company:
            conditions.append("v._company = ?")
            params.append(company)
        if voucher_type:
            conditions.append("v.voucher_type = ?")
            params.append(voucher_type)
        if from_date:
            conditions.append("v.date >= ?")
            params.append(from_date)
        if to_date:
            conditions.append("v.date <= ?")
            params.append(to_date)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += f" ORDER BY v.date DESC LIMIT {limit} OFFSET {offset}"
        
        data = await database_service.fetch_all(query, tuple(params))
        
        # Get total count with same filters
        count_query = "SELECT COUNT(*) FROM trn_voucher v"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        total = await database_service.fetch_scalar(count_query, tuple(params))
        
        return {"total": total, "data": data}
    except Exception as e:
        logger.error(f"Failed to get vouchers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vouchers/{guid}/details")
async def get_voucher_details(guid: str):
    """Get voucher details including accounting entries, inventory, bills, and bank details"""
    try:
        await database_service.connect()
        
        # Get voucher header
        voucher = await database_service.fetch_one(
            "SELECT * FROM trn_voucher WHERE guid = ?", (guid,)
        )
        
        if not voucher:
            raise HTTPException(status_code=404, detail="Voucher not found")
        
        # Get accounting entries (DISTINCT to avoid duplicates)
        entries = await database_service.fetch_all(
            "SELECT DISTINCT guid, ledger, amount, amount_forex, currency FROM trn_accounting WHERE guid = ?", (guid,)
        )
        
        # Get inventory items (DISTINCT to avoid duplicates)
        inventory = await database_service.fetch_all(
            "SELECT DISTINCT guid, item, quantity, rate, amount, godown FROM trn_inventory WHERE guid = ?", (guid,)
        )
        
        # Get bill allocations (DISTINCT to avoid duplicates)
        bills = await database_service.fetch_all(
            "SELECT DISTINCT guid, ledger, name, amount, billtype FROM trn_bill WHERE guid = ?", (guid,)
        )
        
        # Get bank details (DISTINCT to avoid duplicates)
        bank = await database_service.fetch_all(
            "SELECT DISTINCT * FROM trn_bank WHERE guid = ?", (guid,)
        )
        
        # Calculate totals
        total_dr = sum(abs(float(e.get('amount', 0))) for e in entries if float(e.get('amount', 0)) < 0)
        total_cr = sum(float(e.get('amount', 0)) for e in entries if float(e.get('amount', 0)) >= 0)
        
        return {
            "voucher": voucher,
            "entries": entries,
            "inventory": inventory,
            "bills": bills,
            "bank": bank,
            "total_dr": total_dr,
            "total_cr": total_cr
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get voucher details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
