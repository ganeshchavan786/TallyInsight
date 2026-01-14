"""
Ledger Controller
Handles ledger report API endpoints (Ledger Report, Ledger Billwise)

================================================================================
DEVELOPER NOTES
================================================================================
File: ledger_controller.py
Purpose: Handle ledger statement and bill-wise report queries
Prefix: /api/data

BUSINESS LOGIC:
---------------
1. Ledger Report (/ledger-report):
   - Shows ledger statement like Tally's Ledger Vouchers
   - Columns: date, voucher_type, voucher_no, particulars, debit, credit, balance
   - Running balance calculated: opening + cumulative transactions
   - Used in: Ledger statement page
   
2. Ledger Bill-wise (/ledger-billwise):
   - Shows pending bills for a specific ledger (party)
   - Columns: bill_name, bill_date, voucher_type, opening, pending
   - On Account = Bills Total - Ledger Opening Balance
   - Used in: Bill-wise tab in Voucher Report page

CALCULATION FORMULAS:
---------------------
- Running Balance = Opening Balance + SUM(Debit) - SUM(Credit)
- On Account = Total of all bills - Ledger's opening balance
- Pending = Original bill amount - Payments received

TALLY CONCEPTS:
---------------
- Ledger Statement: Chronological list of all transactions
- Bill-wise: Tracks individual invoices and their payments
- On Account: Amount not allocated to any specific bill

IMPORTANT:
----------
- Debit = Positive amount (we receive/asset increases)
- Credit = Negative amount (we pay/liability increases)
- For Sundry Debtors: Debit = Sales, Credit = Receipt
- For Sundry Creditors: Credit = Purchase, Debit = Payment

DEPENDENCIES:
-------------
- mst_ledger: Ledger master with opening balance
- trn_accounting: Transaction entries
- trn_bill: Bill allocations
- trn_voucher: Voucher headers for date/type
================================================================================
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ..services.database_service import database_service
from ..utils.logger import logger

router = APIRouter()


@router.get("/ledger-report")
async def get_ledger_report(
    ledger: str = Query(..., description="Ledger name"),
    company: Optional[str] = None,
    from_date: Optional[str] = Query(default=None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(default=None, description="To date (YYYY-MM-DD)")
):
    """Get ledger report with transactions like Tally"""
    try:
        await database_service.connect()
        
        # Get opening balance from ledger master
        opening_query = """
            SELECT opening_balance 
            FROM mst_ledger 
            WHERE name = ?
        """
        opening_params = [ledger]
        if company:
            opening_query += " AND _company = ?"
            opening_params.append(company)
        
        opening_result = await database_service.fetch_all(opening_query, tuple(opening_params))
        opening_balance = opening_result[0]['opening_balance'] if opening_result else 0
        
        # Get transactions from trn_accounting
        txn_query = """
            SELECT 
                v.date,
                v.voucher_type,
                v.voucher_number as voucher_no,
                a.amount,
                CASE WHEN a.amount > 0 THEN a.amount ELSE 0 END as debit,
                CASE WHEN a.amount < 0 THEN ABS(a.amount) ELSE 0 END as credit,
                v.narration,
                v.party_name as particulars
            FROM trn_accounting a
            JOIN trn_voucher v ON a.guid = v.guid
            WHERE a.ledger = ?
        """
        params = [ledger]
        
        if company:
            txn_query += " AND a._company = ?"
            params.append(company)
        
        if from_date:
            txn_query += " AND v.date >= ?"
            params.append(from_date)
        
        if to_date:
            txn_query += " AND v.date <= ?"
            params.append(to_date)
        
        txn_query += " ORDER BY v.date, v.voucher_number"
        
        transactions = await database_service.fetch_all(txn_query, tuple(params))
        
        # Calculate totals
        total_debit = sum(t['debit'] or 0 for t in transactions)
        total_credit = sum(t['credit'] or 0 for t in transactions)
        closing_balance = opening_balance + total_debit - total_credit
        
        return {
            "ledger": ledger,
            "opening_balance": opening_balance or 0,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "closing_balance": closing_balance,
            "transactions": [dict(t) for t in transactions]
        }
    except Exception as e:
        logger.error(f"Failed to get ledger report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger-billwise")
async def get_ledger_billwise(
    ledger: str = Query(..., description="Ledger name"),
    company: Optional[str] = None,
    from_date: Optional[str] = Query(default=None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(default=None, description="To date (YYYY-MM-DD)")
):
    """Get pending bills for a specific ledger like Tally's Pending Bills view"""
    try:
        await database_service.connect()
        
        ref_date_sql = f"'{to_date}'" if to_date else "date('now')"
        
        query = f"""
            WITH all_bills AS (
                -- Opening bill allocations
                SELECT 
                    o.name as bill_no,
                    o.bill_date,
                    CASE WHEN o.bill_credit_period > 0 THEN o.bill_credit_period ELSE 1 END as bill_credit_period,
                    o.opening_balance as amount,
                    o.opening_balance as opening_amount,
                    'Opening' as source,
                    o._company
                FROM mst_opening_bill_allocation o
                WHERE o.ledger = ? AND o.name != ''
                
                UNION ALL
                
                -- Transaction bills
                SELECT 
                    b.name as bill_no,
                    v.date as bill_date,
                    CASE WHEN b.bill_credit_period > 0 THEN b.bill_credit_period ELSE 1 END as bill_credit_period,
                    CASE 
                        WHEN b.billtype = 'New Ref' THEN ABS(b.amount)
                        WHEN b.billtype = 'Agst Ref' THEN -ABS(b.amount)
                        ELSE 0 
                    END as amount,
                    CASE WHEN b.billtype = 'New Ref' THEN ABS(b.amount) ELSE 0 END as opening_amount,
                    v.voucher_type as source,
                    b._company
                FROM trn_bill b
                JOIN trn_voucher v ON b.guid = v.guid
                WHERE b.ledger = ? AND b.name != '' AND b.billtype IN ('New Ref', 'Agst Ref')
            )
            SELECT 
                bill_no,
                MIN(bill_date) as bill_date,
                date(MIN(bill_date), '+' || MAX(bill_credit_period) || ' days') as due_date,
                SUM(opening_amount) as opening_amount,
                SUM(amount) as pending_amount,
                CAST(julianday({ref_date_sql}) - julianday(date(MIN(bill_date), '+' || MAX(bill_credit_period) || ' days')) AS INTEGER) as overdue_days,
                GROUP_CONCAT(DISTINCT source) as source
            FROM all_bills
            WHERE 1=1
        """
        params = [ledger, ledger]
        
        if company:
            query += " AND _company = ?"
            params.append(company)
        
        query += " GROUP BY bill_no HAVING pending_amount != 0 ORDER BY bill_date"
        
        bills = await database_service.fetch_all(query, tuple(params))
        
        # Calculate bills sub total
        bills_total = sum(b['pending_amount'] or 0 for b in bills)
        
        # Get ledger opening balance
        ledger_query = "SELECT opening_balance FROM mst_ledger WHERE name = ?"
        ledger_params = [ledger]
        if company:
            ledger_query += " AND _company = ?"
            ledger_params.append(company)
        
        ledger_result = await database_service.fetch_all(ledger_query, tuple(ledger_params))
        ledger_opening = ledger_result[0]['opening_balance'] if ledger_result else 0
        
        # On Account = Bills Total - Ledger Opening Balance
        # If bills_total = 76,464 Cr and ledger_opening = 36,464 Cr
        # Then on_account = 76,464 - 36,464 = 40,000 (Dr because it reduces the balance)
        on_account = bills_total - (ledger_opening or 0)
        on_account_date = None  # Will be set from opening bill allocation if exists
        
        return {
            "ledger": ledger,
            "bills": [dict(b) for b in bills],
            "on_account": on_account,
            "on_account_date": on_account_date,
            "total_bills": len(bills)
        }
    except Exception as e:
        logger.error(f"Failed to get ledger billwise: {e}")
        raise HTTPException(status_code=500, detail=str(e))
