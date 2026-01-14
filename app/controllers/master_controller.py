"""
Master Controller
Handles master data API endpoints (Groups, Ledgers, Stock Items)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ..services.database_service import database_service
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
        
        query = "SELECT * FROM mst_ledger"
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
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM mst_ledger"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        total = await database_service.fetch_scalar(count_query, tuple(params))
        
        # Return both formats - data for dashboard, ledgers for dropdown
        return {
            "total": total,
            "data": data,
            "ledgers": [row['name'] for row in data]
        }
    except Exception as e:
        logger.error(f"Failed to get ledgers: {e}")
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
