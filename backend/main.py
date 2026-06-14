"""FastAPI application for the Fervo OMOC system.

Serves a REST API (under /api) backed by a relational SQLite database, and the
build-free React front end (static files). For Azure, set DATABASE_URL to an
Azure SQL / PostgreSQL connection string and put Entra ID auth in front — no
changes to the model or routes are required.
"""
import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Body, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, SessionLocal
from . import models
from .logic import (serialize_moc, late_action_items, late_signoffs, log_event, my_view,
                    submit as wf_submit, record_endorsement, record_final_decision, close_moc,
                    clear_endorsement, clear_final_decision)
from .reference import (CHECKLIST_QUESTIONS, RISK_QUESTIONS, DEPARTMENTS,
                        CLOSURE_QUESTIONS, SIGNOFF_SLA_DAYS)
from .seed import seed_if_empty

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

app = FastAPI(title="Fervo OMOC API", version="1.0.0")


@app.middleware("http")
async def no_cache_static(request: Request, call_next):
    """Serve the HTML/JS/CSS with no-cache so users always get the latest build
    (avoids stale-asset issues during active development)."""
    resp = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


# ---------------- Reference ----------------
@app.get("/api/reference")
def reference(db: Session = Depends(get_db)):
    return {
        "checklist_questions": [{"category": c, "question": q} for c, q in CHECKLIST_QUESTIONS],
        "risk_questions": [{"category": c, "question": q} for c, q in RISK_QUESTIONS],
        "departments": DEPARTMENTS,
        "closure_questions": CLOSURE_QUESTIONS,
        "severity": ["", "1 – Slight", "2 – Minor", "3 – Moderate", "4 – Major", "5 – Critical"],
        "likelihood": ["", "1 – Rare", "2 – Unlikely", "3 – Possible", "4 – Probable", "5 – Almost Certain"],
        "action_status": ["Not Started", "In Progress", "Complete", "Blocked"],
        "signoff_sla_days": SIGNOFF_SLA_DAYS,
        "people": [{"name": p.name, "email": p.email, "department": p.department, "role": p.role}
                   for p in db.query(models.Person).order_by(models.Person.name).all()],
    }


@app.get("/api/people")
def people(db: Session = Depends(get_db)):
    return [{"name": p.name, "email": p.email, "department": p.department, "role": p.role}
            for p in db.query(models.Person).order_by(models.Person.name).all()]


@app.get("/api/my")
def my(email: str, db: Session = Depends(get_db)):
    return my_view(db.query(models.MOC).all(), email)


# ---------------- Dashboard ----------------
@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    mocs = db.query(models.MOC).all()
    active = [m for m in mocs if m.status != "Complete"]
    complete = [m for m in mocs if m.status == "Complete"]
    return {
        "active_count": len(active),
        "complete_count": len(complete),
        "late_action_items": late_action_items(mocs),
        "late_signoffs": late_signoffs(mocs),
        "active": [serialize_moc(m, full=False) for m in active],
        "complete": [serialize_moc(m, full=False) for m in complete],
    }


# ---------------- MOC CRUD ----------------
@app.get("/api/mocs")
def list_mocs(db: Session = Depends(get_db)):
    return [serialize_moc(m, full=False) for m in db.query(models.MOC).all()]


@app.get("/api/mocs/{moc_id}")
def get_moc(moc_id: int, db: Session = Depends(get_db)):
    m = db.get(models.MOC, moc_id)
    if not m:
        raise HTTPException(404, "MOC not found")
    return serialize_moc(m, full=True)


@app.post("/api/mocs")
def create_moc(db: Session = Depends(get_db)):
    year = datetime.utcnow().year
    n = db.query(models.MOC).count() + 1
    m = models.MOC(change_number=f"MOC-{year}-{n:03d}", status="Active")
    for i, (cat, q) in enumerate(CHECKLIST_QUESTIONS):
        m.checklist.append(models.ChecklistItem(idx=i, category=cat, question=q, answer="N"))
    for i, (cat, q) in enumerate(RISK_QUESTIONS):
        m.risk_items.append(models.RiskItem(idx=i, category=cat, question=q))
    for i, dept in enumerate(DEPARTMENTS):
        m.stakeholders.append(models.Stakeholder(idx=i, department=dept, impacted=False))
    m.approvals.append(models.Approval(kind="initiation", role="Initiator"))
    m.approvals.append(models.Approval(kind="initiation", role="MOC Coordinator"))
    m.approvals.append(models.Approval(kind="final", role="VP Operations"))
    m.approvals.append(models.Approval(kind="final", role="CEO (if required)"))
    m.approvals.append(models.Approval(kind="final", role="Site Manager"))
    for i, q in enumerate(CLOSURE_QUESTIONS):
        m.closure_items.append(models.ClosureItem(idx=i, question=q))
    db.add(m)
    db.flush()
    log_event(m, "created", "MOC created (" + m.change_number + ").")
    db.commit()
    db.refresh(m)
    return serialize_moc(m, full=True)


@app.put("/api/mocs/{moc_id}")
def update_moc(moc_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    m = db.get(models.MOC, moc_id)
    if not m:
        raise HTTPException(404, "MOC not found")

    # CONTENT LOCK: the change itself is only editable while Draft or Revision Requested.
    # Once submitted/approved it is locked (so endorsers/approvers always see the version
    # they signed). Closure fields are editable only while Approved (to complete closeout).
    content_unlocked = m.workflow_state in ("Draft", "Revision Requested")
    closure_unlocked = m.workflow_state == "Approved"
    content_applied = False
    closure_applied = False

    if not (content_unlocked or closure_unlocked):
        # Locked state (Submitted for Endorsement / Pending Final Approval / Closed):
        # ignore content edits; only workflow action endpoints change a locked MOC.
        return serialize_moc(m, full=True)

    # ----- content fields (Draft / Revision Requested only) -----
    if content_unlocked:
        for f in ["change_name", "initiator", "initiator_email", "date_requested", "description",
                  "justification", "operating_unit"]:
            if f in payload and payload[f] != getattr(m, f):
                setattr(m, f, payload[f]); content_applied = True
        for f in ["emergency", "temporary"]:
            if f in payload and bool(payload[f]) != getattr(m, f):
                setattr(m, f, bool(payload[f])); content_applied = True

    # closure_date editable while Approved (closeout) or while content is unlocked
    if "closure_date" in payload and (closure_unlocked or content_unlocked):
        if payload["closure_date"] != m.closure_date:
            m.closure_date = payload["closure_date"]; closure_applied = True

    # fixed-index children: update in place by idx (content -> only when unlocked)
    if content_unlocked and "checklist" in payload:
        content_applied = True
        by_idx = {c.idx: c for c in m.checklist}
        for row in payload["checklist"]:
            it = by_idx.get(row.get("idx"))
            if it:
                it.answer = row.get("answer", it.answer)
    if content_unlocked and "risk_items" in payload:
        content_applied = True
        by_idx = {r.idx: r for r in m.risk_items}
        for row in payload["risk_items"]:
            it = by_idx.get(row.get("idx"))
            if it:
                it.severity = row.get("severity") or None
                it.likelihood = row.get("likelihood") or None
    if content_unlocked and "stakeholders" in payload:
        content_applied = True
        by_idx = {s.idx: s for s in m.stakeholders}
        for row in payload["stakeholders"]:
            it = by_idx.get(row.get("idx"))
            if it:
                it.impacted = bool(row.get("impacted"))
                it.endorser_name = row.get("endorser_name", "")
                it.endorser_email = row.get("endorser_email", "")
                it.notes = row.get("notes", "")
                # decision is managed by the /endorse action, not content edits
    if (content_unlocked or closure_unlocked) and "closure_items" in payload:
        closure_applied = True
        by_idx = {c.idx: c for c in m.closure_items}
        for row in payload["closure_items"]:
            it = by_idx.get(row.get("idx"))
            if it:
                it.complete = bool(row.get("complete"))
                it.verified_by = row.get("verified_by", "")
                it.date = row.get("date", "")
                it.comments = row.get("comments", "")

    # variable children: replace wholesale (content -> only when unlocked)
    if content_unlocked and "action_items" in payload:
        content_applied = True
        m.action_items.clear()
        for j, a in enumerate(payload["action_items"], start=1):
            m.action_items.append(models.ActionItem(
                seq=j, type=a.get("type", ""), description=a.get("description", ""),
                assigned_to=a.get("assigned_to", ""), assigned_email=a.get("assigned_email", ""),
                due_date=a.get("due_date", ""), status=a.get("status", "Not Started"),
                comments=a.get("comments", "")))
    if content_unlocked and "impl_reqs" in payload:
        content_applied = True
        m.impl_reqs.clear()
        for j, a in enumerate(payload["impl_reqs"], start=1):
            m.impl_reqs.append(models.ImplReq(
                seq=j, category=a.get("category", ""), requirement=a.get("requirement", ""),
                assigned_to=a.get("assigned_to", ""), assigned_email=a.get("assigned_email", ""),
                due_date=a.get("due_date", ""), status=a.get("status", "Not Started"),
                verification=a.get("verification", ""), comments=a.get("comments", "")))
    if content_unlocked and "attachments" in payload:
        content_applied = True
        m.attachments.clear()
        for j, a in enumerate(payload["attachments"], start=1):
            m.attachments.append(models.Attachment(
                seq=j, description=a.get("description", ""), link=a.get("link", "")))
    if (content_unlocked or closure_unlocked) and "lessons" in payload:
        closure_applied = True
        m.lessons.clear()
        for j, a in enumerate(payload["lessons"], start=1):
            m.lessons.append(models.Lesson(
                seq=j, category=a.get("category", ""), lesson=a.get("lesson", ""),
                action=a.get("action", ""), owner=a.get("owner", "")))
    if content_unlocked and "approvals" in payload:
        m.approvals.clear()
        for a in payload["approvals"]:
            m.approvals.append(models.Approval(
                kind=a.get("kind", "final"), role=a.get("role", ""),
                department=a.get("department", ""), name=a.get("name", ""),
                title=a.get("title", ""), email=a.get("email", ""), date=a.get("date", ""),
                initials=a.get("initials", ""), approved=bool(a.get("approved")),
                decision=a.get("decision", "Pending"), decision_comment=a.get("decision_comment", ""),
                comments=a.get("comments", "")))

    if content_applied:
        log_event(m, "edited", "Change content edited (state: " + m.workflow_state + ").")
    elif closure_applied:
        log_event(m, "edited", "Closure information updated.")

    db.commit()
    db.refresh(m)
    return serialize_moc(m, full=True)


@app.delete("/api/mocs/{moc_id}")
def delete_moc(moc_id: int, db: Session = Depends(get_db)):
    m = db.get(models.MOC, moc_id)
    if not m:
        raise HTTPException(404, "MOC not found")
    db.delete(m)
    db.commit()
    return {"deleted": moc_id}


# ---------------- Workflow actions (state machine) ----------------
def _moc_or_404(db, moc_id):
    m = db.get(models.MOC, moc_id)
    if not m:
        raise HTTPException(404, "MOC not found")
    return m


@app.post("/api/mocs/{moc_id}/submit")
def submit_for_endorsement(moc_id: int, db: Session = Depends(get_db)):
    """Draft -> Submitted for Endorsement, or resubmit from Revision Requested
    (clears all endorsement + final decisions; everyone re-endorses)."""
    m = _moc_or_404(db, moc_id)
    try:
        wf_submit(m)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit(); db.refresh(m)
    return serialize_moc(m, full=True)


@app.post("/api/mocs/{moc_id}/endorse")
def endorse(moc_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Record an endorser's Approve/Decline. A decline routes the MOC back to the
    originator (Revision Requested); all-approved advances to Pending Final Approval."""
    m = _moc_or_404(db, moc_id)
    try:
        record_endorsement(m, payload.get("department"), payload.get("decision"), payload.get("comment", ""),
                           actor_name=payload.get("actor_name", ""), actor_email=payload.get("actor_email", ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit(); db.refresh(m)
    return serialize_moc(m, full=True)


@app.post("/api/mocs/{moc_id}/final-decision")
def final_decision(moc_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Record a final approver's Approve/Decline. Decline -> Revision Requested;
    all required approvers approved -> Approved."""
    m = _moc_or_404(db, moc_id)
    try:
        record_final_decision(m, payload.get("role"), payload.get("decision"), payload.get("comment", ""),
                              actor_name=payload.get("actor_name", ""), actor_email=payload.get("actor_email", ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit(); db.refresh(m)
    return serialize_moc(m, full=True)


@app.post("/api/mocs/{moc_id}/clear-signoff")
def clear_signoff(moc_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Undo a recorded endorsement or final approval (back to Pending) and roll the
    workflow state back accordingly. The undo is recorded in the audit log."""
    m = _moc_or_404(db, moc_id)
    try:
        if payload.get("kind") == "final":
            clear_final_decision(m, payload.get("role"), payload.get("actor_name", ""), payload.get("actor_email", ""))
        else:
            clear_endorsement(m, payload.get("department"), payload.get("actor_name", ""), payload.get("actor_email", ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit(); db.refresh(m)
    return serialize_moc(m, full=True)


@app.post("/api/mocs/{moc_id}/close")
def close(moc_id: int, db: Session = Depends(get_db)):
    m = _moc_or_404(db, moc_id)
    try:
        close_moc(m)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit(); db.refresh(m)
    return serialize_moc(m, full=True)


# ---------------- Static front end ----------------
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
