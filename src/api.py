"""
FastAPI web layer — exposes the ERP Integration Hub as a real HTTP API.

This is the layer a frontend dashboard, another internal system, or
(in Shibaura's real environment) other enterprise systems would call.
Every endpoint here is a thin wrapper around the business logic already
built and tested in erp_workflow.py, connectors.py, security_monitor.py,
and genai_assistant.py — the API layer's job is only routing and
request/response shaping, never business logic itself.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import database as db
from connectors import sync_all_peripheral_systems
from erp_workflow import WorkflowEngine, WorkflowError
from genai_assistant import daily_ops_briefing, summarize_security_events
from security_monitor import SecurityMonitor

app = FastAPI(
    title="ERP Integration Hub",
    description="Cloud ERP core + peripheral system integration + security monitoring + GenAI ops assistant",
    version="1.0.0",
)

# In-memory workflow engine for this running instance. Requisition
# state lives here; persisted snapshots go to SQLite via database.py.
engine = WorkflowEngine()


# -----------------------------------------------------------------
# Request/response schemas
# -----------------------------------------------------------------

class CreateRequisitionRequest(BaseModel):
    requester: str
    department: str
    item_description: str
    quantity: int
    unit_cost: float


class ApproveRequest(BaseModel):
    approver: str


# -----------------------------------------------------------------
# Requisition workflow endpoints
# -----------------------------------------------------------------

@app.post("/requisitions")
def create_requisition(body: CreateRequisitionRequest):
    req = engine.create_requisition(
        body.requester, body.department, body.item_description,
        body.quantity, body.unit_cost,
    )
    conn = db.get_connection()
    db.save_requisition(conn, req)
    conn.close()
    return req


@app.post("/requisitions/{requisition_id}/submit")
def submit_requisition(requisition_id: str):
    try:
        req = engine.submit_for_approval(requisition_id)
    except WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))
    conn = db.get_connection()
    db.save_requisition(conn, req)
    conn.close()
    return req


@app.post("/requisitions/{requisition_id}/approve")
def approve_requisition(requisition_id: str, body: ApproveRequest):
    try:
        req = engine.approve_requisition(requisition_id, body.approver)
    except WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))
    conn = db.get_connection()
    db.save_requisition(conn, req)
    conn.close()
    return req


@app.post("/requisitions/{requisition_id}/reject")
def reject_requisition(requisition_id: str, body: ApproveRequest):
    try:
        req = engine.reject_requisition(requisition_id, body.approver)
    except WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))
    conn = db.get_connection()
    db.save_requisition(conn, req)
    conn.close()
    return req


@app.post("/requisitions/{requisition_id}/procure")
def procure_requisition(requisition_id: str):
    try:
        txn = engine.mark_procured(requisition_id)
    except WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))
    conn = db.get_connection()
    req = engine.requisitions[requisition_id]
    db.save_requisition(conn, req)
    db.save_transactions(conn, [txn])
    conn.close()
    return txn


@app.get("/requisitions")
def list_requisitions(status: Optional[str] = None):
    reqs = engine.list_requisitions()
    if status:
        reqs = [r for r in reqs if r.status.value == status]
    return reqs


# -----------------------------------------------------------------
# Peripheral systems + security + GenAI endpoints
# -----------------------------------------------------------------

@app.post("/sync-peripheral-systems")
def sync_peripheral_systems():
    peripheral_txns = sync_all_peripheral_systems()
    all_txns = engine.transactions + peripheral_txns
    events = SecurityMonitor().scan(all_txns)

    conn = db.get_connection()
    db.save_transactions(conn, peripheral_txns)
    db.save_security_events(conn, events)
    conn.close()

    return {
        "synced_transactions": len(peripheral_txns),
        "security_events_found": len(events),
        "events": events,
    }


@app.get("/security-events")
def list_security_events():
    conn = db.get_connection()
    events = db.query(conn, "SELECT * FROM security_events ORDER BY id DESC")
    conn.close()
    return events


@app.get("/briefing")
def get_daily_briefing():
    conn = db.get_connection()
    txn_rows = db.query(conn, "SELECT * FROM transactions")
    event_rows = db.query(conn, "SELECT * FROM security_events")
    conn.close()

    # Reconstruct lightweight objects for the summarizer, which expects
    # attribute access (.severity, .amount, etc.) rather than dicts.
    from types import SimpleNamespace
    txns = [SimpleNamespace(**{**r, "source": SimpleNamespace(value=r["source"])}) for r in txn_rows]
    events = [SimpleNamespace(**r) for r in event_rows]

    return {"briefing": daily_ops_briefing(txns, events)}


@app.get("/")
def root():
    return {
        "service": "ERP Integration Hub",
        "status": "running",
        "docs": "/docs",
    }