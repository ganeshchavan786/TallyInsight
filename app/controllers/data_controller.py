"""
Data Controller
Handles data query API endpoints
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List

from ..services.database_service import database_service
from ..services.tally_service import tally_service
from ..utils.logger import logger

router = APIRouter()


@router.get("/groups")
async def get_groups(
    parent: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """Get all groups"""
    try:
        await database_service.connect()
        
        query = "SELECT * FROM mst_group"
        params = []
        conditions = []
        
        if parent:
            conditions.append("parent = ?")
            params.append(parent)
        if search:
            conditions.append("name LIKE ?")
            params.append(f"%{search}%")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += f" LIMIT {limit} OFFSET {offset}"
        
        data = await database_service.fetch_all(query, tuple(params))
        total = await database_service.fetch_scalar("SELECT COUNT(*) FROM mst_group")
        
        return {"total": total, "data": data}
    except Exception as e:
        logger.error(f"Failed to get groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledgers")
async def get_ledgers(
    company: Optional[str] = None,
    parent: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=10000, le=50000),
    offset: int = Query(default=0, ge=0)
):
    """Get all ledgers for a company"""
    try:
        await database_service.connect()
        
        query = "SELECT DISTINCT name FROM mst_ledger"
        params = []
        conditions = []
        
        if company:
            conditions.append("_company = ?")
            params.append(company)
        if parent:
            conditions.append("parent = ?")
            params.append(parent)
        if search:
            conditions.append("name LIKE ?")
            params.append(f"%{search}%")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY name"
        query += f" LIMIT {limit} OFFSET {offset}"
        
        data = await database_service.fetch_all(query, tuple(params))
        
        # Return ledgers array for dropdown
        return {"ledgers": [row['name'] for row in data], "total": len(data)}
    except Exception as e:
        logger.error(f"Failed to get ledgers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/stock-items")
async def get_stock_items(
    parent: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """Get all stock items"""
    try:
        await database_service.connect()
        
        query = "SELECT * FROM mst_stock_item"
        params = []
        conditions = []
        
        if parent:
            conditions.append("parent = ?")
            params.append(parent)
        if search:
            conditions.append("name LIKE ?")
            params.append(f"%{search}%")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += f" LIMIT {limit} OFFSET {offset}"
        
        data = await database_service.fetch_all(query, tuple(params))
        total = await database_service.fetch_scalar("SELECT COUNT(*) FROM mst_stock_item")
        
        return {"total": total, "data": data}
    except Exception as e:
        logger.error(f"Failed to get stock items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        counts = await database_service.get_all_table_counts(company=company)
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
