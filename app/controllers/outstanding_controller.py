"""
Outstanding Controller
Handles outstanding report API endpoints (Receivable/Payable, Billwise, Ledgerwise, Ageing)

================================================================================
DEVELOPER NOTES
================================================================================
File: outstanding_controller.py
Purpose: Handle outstanding/dues report queries
Prefix: /api/data

BUSINESS LOGIC:
---------------
1. Outstanding Summary (/outstanding):
   - type=receivable: Sundry Debtors with positive balance (customers owe us)
   - type=payable: Sundry Creditors with positive balance (we owe suppliers)
   - Calculates: total_amount, count of parties
   
2. Bill-wise Outstanding (/outstanding/billwise):
   - Shows individual pending bills
   - Source: trn_bill table (bill allocations)
   - Columns: bill_name, bill_date, opening, pending
   
3. Ledger-wise Outstanding (/outstanding/ledgerwise):
   - Groups outstanding by ledger (party)
   - Shows: ledger_name, total_pending, bill_count
   
4. Ageing Report (/outstanding/ageing):
   - Buckets: 0-30, 30-60, 60-90, 90+ days
   - Calculated from bill_date vs current_date
   
5. Group Outstanding (/outstanding/group):
   - Groups by parent group (e.g., all Sundry Debtors)

TALLY CONCEPTS:
---------------
- Sundry Debtors: Customers who owe money (Receivable)
- Sundry Creditors: Suppliers we owe money (Payable)
- Bill: Invoice reference for tracking payments
- Opening: Original bill amount
- Pending: Remaining unpaid amount

IMPORTANT:
----------
- Positive pending = amount due
- Negative pending = advance payment
- Bill matching done via bill_name in trn_bill

DEPENDENCIES:
-------------
- trn_bill: Bill allocations from vouchers
- mst_ledger: Ledger master for party details
================================================================================
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ..services.database_service import database_service
from ..utils.logger import logger

router = APIRouter()


@router.get("/outstanding")
async def get_outstanding(
    type: str = Query(default="receivable", description="receivable or payable"),
    company: Optional[str] = None
):
    """Get outstanding receivable or payable data - uses pre-computed summary table"""
    try:
        await database_service.connect()
        
        parent_group = "Sundry Debtors" if type == "receivable" else "Sundry Creditors"
        
        # Use pre-computed summary table for fast queries
        query = """
            SELECT ledger_name, opening_balance as opening, debit, credit, closing
            FROM ledger_balance_summary
            WHERE parent = ?
        """
        params = [parent_group]
        
        if company:
            query += " AND _company = ?"
            params.append(company)
        
        query += " ORDER BY ledger_name"
        
        data = await database_service.fetch_all(query, tuple(params))
        
        # Calculate totals
        total_opening = sum(row.get('opening', 0) or 0 for row in data)
        total_debit = sum(row.get('debit', 0) or 0 for row in data)
        total_credit = sum(row.get('credit', 0) or 0 for row in data)
        total_closing = sum(row.get('closing', 0) or 0 for row in data)
        
        return {
            "type": type,
            "data": data,
            "count": len(data),
            "totals": {
                "opening": total_opening,
                "debit": total_debit,
                "credit": total_credit,
                "closing": total_closing
            }
        }
    except Exception as e:
        logger.error(f"Failed to get outstanding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outstanding/billwise")
async def get_billwise_outstanding(
    type: str = Query(default="receivable", description="receivable or payable"),
    company: Optional[str] = None,
    from_date: Optional[str] = Query(default=None, description="Period start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(default=None, description="Period end date (YYYY-MM-DD)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=10, le=100, description="Items per page")
):
    """Get bill-wise outstanding with pagination - includes opening bill allocations
    
    Receivable = Debit balance (positive pending) from Sundry Debtors + Sundry Creditors
    Payable = Credit balance (negative pending) from Sundry Debtors + Sundry Creditors
    
    Overdue days = Today - Due Date
    Due Date = Bill Date + Credit Period (default 1 day if no credit period)
    """
    try:
        await database_service.connect()
        
        # Use to_date as reference date for overdue calculation, default to today
        ref_date = to_date if to_date else "date('now')"
        ref_date_sql = f"'{to_date}'" if to_date else "date('now')"
        
        # Include both Sundry Debtors and Sundry Creditors
        # Filter by balance type: Receivable = Debit (positive), Payable = Credit (negative)
        base_query = f"""
            WITH all_bills AS (
                -- Opening bill allocations from both Debtors and Creditors
                -- For Creditors: positive = Cr (Payable), negative = Dr (Receivable) - reverse sign
                -- For Debtors: positive = Dr (Receivable), negative = Cr (Payable) - keep sign
                SELECT 
                    o.ledger as party_name,
                    o.name as bill_no,
                    o.bill_date,
                    CASE WHEN o.bill_credit_period > 0 THEN o.bill_credit_period ELSE 1 END as bill_credit_period,
                    CASE WHEN l.parent = 'Sundry Creditors' THEN -o.opening_balance ELSE o.opening_balance END as amount,
                    'Opening' as source,
                    o._company
                FROM mst_opening_bill_allocation o
                JOIN mst_ledger l ON o.ledger = l.name AND o._company = l._company
                WHERE l.parent IN ('Sundry Debtors', 'Sundry Creditors') AND o.name != ''
                
                UNION ALL
                
                -- Transaction bills (New Ref and Agst Ref) from both Debtors and Creditors
                SELECT 
                    b.ledger as party_name,
                    b.name as bill_no,
                    v.date as bill_date,
                    CASE WHEN b.bill_credit_period > 0 THEN b.bill_credit_period ELSE 1 END as bill_credit_period,
                    CASE 
                        WHEN b.billtype = 'New Ref' THEN ABS(b.amount)
                        WHEN b.billtype = 'Agst Ref' THEN -ABS(b.amount)
                        ELSE 0 
                    END as amount,
                    v.voucher_type as source,
                    b._company
                FROM trn_bill b
                JOIN trn_voucher v ON b.guid = v.guid
                JOIN mst_ledger l ON b.ledger = l.name AND b._company = l._company
                WHERE l.parent IN ('Sundry Debtors', 'Sundry Creditors') AND b.name != '' AND b.billtype IN ('New Ref', 'Agst Ref')
            )
            SELECT 
                party_name,
                bill_no,
                MIN(bill_date) as bill_date,
                MAX(bill_credit_period) as bill_credit_period,
                date(MIN(bill_date), '+' || MAX(bill_credit_period) || ' days') as due_date,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as bill_amount,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as paid_amount,
                SUM(amount) as pending_amount,
                CAST(julianday({ref_date_sql}) - julianday(date(MIN(bill_date), '+' || MAX(bill_credit_period) || ' days')) AS INTEGER) as overdue_days,
                GROUP_CONCAT(DISTINCT source) as source
            FROM all_bills
            WHERE 1=1
        """
        params = []
        
        if company:
            base_query += " AND _company = ?"
            params.append(company)
        
        # Filter by balance type: Receivable = positive (Debit), Payable = negative (Credit)
        if type == "receivable":
            base_query += """
                GROUP BY party_name, bill_no
                HAVING pending_amount > 0
            """
        else:
            base_query += """
                GROUP BY party_name, bill_no
                HAVING pending_amount < 0
            """
        
        # Count query for total records
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) sub"
        count_result = await database_service.fetch_all(count_query, tuple(params))
        total_count = count_result[0]['total'] if count_result else 0
        
        # Totals query (sum of all, not just current page)
        totals_query = f"""
            SELECT 
                SUM(bill_amount) as total_bill,
                SUM(paid_amount) as total_paid,
                SUM(pending_amount) as total_pending
            FROM ({base_query}) sub
        """
        totals_result = await database_service.fetch_all(totals_query, tuple(params))
        totals = totals_result[0] if totals_result else {}
        
        # Paginated data query
        offset = (page - 1) * page_size
        data_query = f"{base_query} ORDER BY overdue_days DESC, party_name LIMIT ? OFFSET ?"
        data_params = list(params) + [page_size, offset]
        
        data = await database_service.fetch_all(data_query, tuple(data_params))
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "type": type,
            "report_type": "billwise",
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "totals": {
                "bill_amount": totals.get('total_bill', 0) or 0,
                "paid_amount": totals.get('total_paid', 0) or 0,
                "pending_amount": totals.get('total_pending', 0) or 0
            }
        }
    except Exception as e:
        logger.error(f"Failed to get billwise outstanding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outstanding/ledgerwise")
async def get_ledgerwise_outstanding(
    type: str = Query(default="receivable", description="receivable or payable"),
    company: Optional[str] = None,
    from_date: Optional[str] = Query(default=None, description="Period start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(default=None, description="Period end date (YYYY-MM-DD)")
):
    """Get ledger-wise outstanding - bills grouped by party with subtotals like Tally"""
    try:
        await database_service.connect()
        
        ref_date_sql = f"'{to_date}'" if to_date else "date('now')"
        
        base_query = f"""
            WITH all_bills AS (
                -- For Creditors: positive = Cr (Payable), negative = Dr (Receivable) - reverse sign
                SELECT 
                    o.ledger as party_name,
                    o.name as bill_no,
                    o.bill_date,
                    CASE WHEN o.bill_credit_period > 0 THEN o.bill_credit_period ELSE 1 END as bill_credit_period,
                    CASE WHEN l.parent = 'Sundry Creditors' THEN -o.opening_balance ELSE o.opening_balance END as amount,
                    'Opening' as source,
                    o._company
                FROM mst_opening_bill_allocation o
                JOIN mst_ledger l ON o.ledger = l.name AND o._company = l._company
                WHERE l.parent IN ('Sundry Debtors', 'Sundry Creditors') AND o.name != ''
                
                UNION ALL
                
                SELECT 
                    b.ledger as party_name,
                    b.name as bill_no,
                    v.date as bill_date,
                    CASE WHEN b.bill_credit_period > 0 THEN b.bill_credit_period ELSE 1 END as bill_credit_period,
                    CASE 
                        WHEN b.billtype = 'New Ref' THEN ABS(b.amount)
                        WHEN b.billtype = 'Agst Ref' THEN -ABS(b.amount)
                        ELSE 0 
                    END as amount,
                    v.voucher_type as source,
                    b._company
                FROM trn_bill b
                JOIN trn_voucher v ON b.guid = v.guid
                JOIN mst_ledger l ON b.ledger = l.name AND b._company = l._company
                WHERE l.parent IN ('Sundry Debtors', 'Sundry Creditors') AND b.name != '' AND b.billtype IN ('New Ref', 'Agst Ref')
            )
            SELECT 
                party_name,
                bill_no,
                MIN(bill_date) as bill_date,
                date(MIN(bill_date), '+' || MAX(bill_credit_period) || ' days') as due_date,
                SUM(amount) as pending_amount,
                CAST(julianday({ref_date_sql}) - julianday(date(MIN(bill_date), '+' || MAX(bill_credit_period) || ' days')) AS INTEGER) as overdue_days,
                GROUP_CONCAT(DISTINCT source) as source
            FROM all_bills
            WHERE 1=1
        """
        params = []
        
        if company:
            base_query += " AND _company = ?"
            params.append(company)
        
        # Filter by balance type
        if type == "receivable":
            base_query += " GROUP BY party_name, bill_no HAVING pending_amount > 0"
        else:
            base_query += " GROUP BY party_name, bill_no HAVING pending_amount < 0"
        
        base_query += " ORDER BY party_name, bill_date"
        
        bills = await database_service.fetch_all(base_query, tuple(params))
        
        # Group bills by party with subtotals
        ledger_data = []
        current_party = None
        party_bills = []
        party_total = 0
        grand_total = 0
        
        for bill in bills:
            if current_party != bill['party_name']:
                # Save previous party data
                if current_party and party_bills:
                    ledger_data.append({
                        "party_name": current_party,
                        "bills": party_bills,
                        "party_total": party_total
                    })
                    grand_total += party_total
                
                # Start new party
                current_party = bill['party_name']
                party_bills = []
                party_total = 0
            
            party_bills.append({
                "bill_no": bill['bill_no'],
                "bill_date": bill['bill_date'],
                "due_date": bill['due_date'],
                "pending_amount": bill['pending_amount'],
                "overdue_days": bill['overdue_days'],
                "source": bill['source']
            })
            party_total += bill['pending_amount'] or 0
        
        # Add last party
        if current_party and party_bills:
            ledger_data.append({
                "party_name": current_party,
                "bills": party_bills,
                "party_total": party_total
            })
            grand_total += party_total
        
        return {
            "type": type,
            "report_type": "ledgerwise",
            "data": ledger_data,
            "totals": {
                "party_count": len(ledger_data),
                "bill_count": len(bills),
                "grand_total": grand_total
            }
        }
    except Exception as e:
        logger.error(f"Failed to get ledgerwise outstanding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outstanding/ageing")
async def get_ageing_analysis(
    type: str = Query(default="receivable", description="receivable or payable"),
    company: Optional[str] = None
):
    """Get ageing analysis - 0-30, 30-60, 60-90, 90+ days"""
    try:
        await database_service.connect()
        
        parent_group = "Sundry Debtors" if type == "receivable" else "Sundry Creditors"
        
        # Query to get bill-wise data with age buckets
        query = """
            SELECT 
                b.ledger as party_name,
                SUM(CASE WHEN b.billtype = 'New Ref' THEN ABS(b.amount) ELSE 0 END) - 
                SUM(CASE WHEN b.billtype = 'Agst Ref' THEN ABS(b.amount) ELSE 0 END) as pending_amount,
                CAST(julianday('now') - julianday(MIN(v.date)) AS INTEGER) as days_old
            FROM trn_bill b
            JOIN trn_voucher v ON b.guid = v.guid
            JOIN mst_ledger l ON b.ledger = l.name
            WHERE l.parent = ? AND b.name != '' AND b.billtype IN ('New Ref', 'Agst Ref')
        """
        params = [parent_group]
        
        if company:
            query += " AND b._company = ?"
            params.append(company)
        
        query += """
            GROUP BY b.ledger, b.name
            HAVING pending_amount > 0
        """
        
        bills = await database_service.fetch_all(query, tuple(params))
        
        # Aggregate by party with age buckets
        party_ageing = {}
        for bill in bills:
            party = bill['party_name']
            amount = bill['pending_amount'] or 0
            days = bill['days_old'] or 0
            
            if party not in party_ageing:
                party_ageing[party] = {'party_name': party, 'days_0_30': 0, 'days_30_60': 0, 'days_60_90': 0, 'days_90_plus': 0, 'total': 0}
            
            if days <= 30:
                party_ageing[party]['days_0_30'] += amount
            elif days <= 60:
                party_ageing[party]['days_30_60'] += amount
            elif days <= 90:
                party_ageing[party]['days_60_90'] += amount
            else:
                party_ageing[party]['days_90_plus'] += amount
            
            party_ageing[party]['total'] += amount
        
        data = list(party_ageing.values())
        data.sort(key=lambda x: x['total'], reverse=True)
        
        # Calculate totals
        totals = {
            'days_0_30': sum(p['days_0_30'] for p in data),
            'days_30_60': sum(p['days_30_60'] for p in data),
            'days_60_90': sum(p['days_60_90'] for p in data),
            'days_90_plus': sum(p['days_90_plus'] for p in data),
            'total': sum(p['total'] for p in data)
        }
        
        return {
            "type": type,
            "report_type": "ageing",
            "data": data,
            "count": len(data),
            "totals": totals
        }
    except Exception as e:
        logger.error(f"Failed to get ageing analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outstanding/group")
async def get_group_outstanding(
    type: str = Query(default="receivable", description="receivable or payable"),
    company: Optional[str] = None
):
    """Get group outstanding - Sundry Debtors/Creditors group total"""
    try:
        await database_service.connect()
        
        parent_group = "Sundry Debtors" if type == "receivable" else "Sundry Creditors"
        
        # Query to get group summary
        query = """
            SELECT 
                ? as group_name,
                COUNT(DISTINCT l.name) as party_count,
                SUM(l.opening_balance) as opening,
                SUM(COALESCE((SELECT SUM(CASE WHEN a.amount > 0 THEN a.amount ELSE 0 END) FROM trn_accounting a WHERE a.ledger = l.name), 0)) as debit,
                SUM(COALESCE((SELECT SUM(CASE WHEN a.amount < 0 THEN ABS(a.amount) ELSE 0 END) FROM trn_accounting a WHERE a.ledger = l.name), 0)) as credit,
                SUM(l.opening_balance) + SUM(COALESCE((SELECT SUM(a.amount) FROM trn_accounting a WHERE a.ledger = l.name), 0)) as closing
            FROM mst_ledger l
            WHERE l.parent = ?
        """
        params = [parent_group, parent_group]
        
        if company:
            query += " AND l._company = ?"
            params.append(company)
        
        data = await database_service.fetch_all(query, tuple(params))
        
        return {
            "type": type,
            "report_type": "group",
            "data": data[0] if data else {},
            "group_name": parent_group
        }
    except Exception as e:
        logger.error(f"Failed to get group outstanding: {e}")
        raise HTTPException(status_code=500, detail=str(e))
