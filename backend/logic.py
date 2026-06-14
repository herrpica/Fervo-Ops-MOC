"""Server-authoritative business rules + serialization, mirroring Fervo_MOC_Form_v2.

Thresholds:
  approval  : max risk score > 8  -> CEO, else VP Operations
  PHA       : max risk score > 12 -> HAZOP, else What-If Analysis
  risk level: >=15 HIGH, >=8 MEDIUM, else LOW
  priority  : VP Operations -> Normal, else High
"""
from datetime import date, datetime
from . import models
from .reference import SIGNOFF_SLA_DAYS, STATES


def log_event(moc, event_type, summary, actor=""):
    """Append an immutable audit record to the MOC's history."""
    moc.audit_events.append(models.AuditEvent(event_type=event_type, summary=summary, actor=actor or ""))


def risk_scores(moc):
    out = []
    for r in moc.risk_items:
        if r.severity and r.likelihood:
            out.append(r.severity * r.likelihood)
        else:
            out.append(0)
    return out


def max_risk(moc):
    s = risk_scores(moc)
    return max(s) if s else 0


def omoc_required(moc):
    return "Y" if any(c.answer == "Y" for c in moc.checklist) else "N"


def flag_type(moc):
    if moc.emergency:
        return "Emergency"
    if moc.temporary:
        return "Temporary"
    return "Standard"


def approval_level(moc):
    return "CEO" if max_risk(moc) > 8 else "VP Operations"


def pha_level(moc):
    return "HAZOP" if max_risk(moc) > 12 else "What-If Analysis"


def risk_level(moc):
    mx = max_risk(moc)
    return "HIGH" if mx >= 15 else ("MEDIUM" if mx >= 8 else "LOW")


def priority(moc):
    return "Normal" if approval_level(moc) == "VP Operations" else "High"


def step_complete(moc, i):
    if i == 0:                                  # checklist confirmed
        return _flag(moc, "step0")
    if i == 1:                                  # change request fields
        return bool(moc.change_name and moc.initiator and moc.date_requested
                    and moc.description and moc.justification)
    if i == 2:                                  # all risk rows scored
        return all(r.severity and r.likelihood for r in moc.risk_items) and len(moc.risk_items) > 0
    if i == 3:
        return _flag(moc, "step3")
    if i == 4:
        return _flag(moc, "step4")
    if i == 5:                                  # endorsements + final approval all granted
        return moc.workflow_state in ("Approved", "Closed")
    if i == 6:                                  # closed out
        return moc.workflow_state == "Closed"
    return False


# steps 0/3/4 are "confirmed" flags stored as a tiny convention: we reuse the MOC's
# updated bookkeeping via the steps_done JSON is overkill, so we infer them from data
# where possible and otherwise treat presence of content as done.
def _flag(moc, which):
    if which == "step0":
        # checklist is "done" once it has been answered (all 10 present)
        return len(moc.checklist) >= 10
    if which == "step3":
        return len(moc.action_items) > 0 or len(moc.impl_reqs) > 0 or moc.status == "Complete"
    if which == "step4":
        return True   # attachments optional; considered reviewed
    return False


def progress(moc):
    return sum(1 for i in range(7) if step_complete(moc, i))


def endorsers(moc):
    return [s for s in moc.stakeholders if s.impacted]


# ===================== Workflow state machine =====================
def required_final_roles(moc):
    return ["VP Operations"] + (["CEO"] if approval_level(moc) == "CEO" else [])


def _final_row(moc, role):
    for a in moc.approvals:
        if a.kind == "final" and (a.role == role or a.role.startswith(role)):
            return a
    return None


def endorsement_summary(moc):
    es = endorsers(moc)
    return {"total": len(es),
            "approved": sum(1 for s in es if s.decision == "Approved"),
            "declined": sum(1 for s in es if s.decision == "Declined"),
            "pending": sum(1 for s in es if s.decision not in ("Approved", "Declined"))}


def all_endorsed(moc):
    es = endorsers(moc)
    return len(es) > 0 and all(s.decision == "Approved" for s in es)


def any_endorsement_declined(moc):
    return any(s.decision == "Declined" for s in endorsers(moc))


def all_final_approved(moc):
    for role in required_final_roles(moc):
        a = _final_row(moc, role)
        if not (a and a.decision == "Approved"):
            return False
    return True


def any_final_declined(moc):
    return any(a.decision == "Declined" for a in moc.approvals if a.kind == "final")


def can_submit(moc):
    return step_complete(moc, 1) and step_complete(moc, 2) and len(endorsers(moc)) > 0


def awaiting(moc):
    """Who the MOC is currently waiting on for action (drives notifications)."""
    out = []
    if moc.workflow_state == "Submitted for Endorsement":
        for s in endorsers(moc):
            if s.decision not in ("Approved", "Declined"):
                out.append({"person": s.endorser_name or "(unassigned)", "email": s.endorser_email or "",
                            "role": "Endorser", "department": s.department})
    elif moc.workflow_state == "Pending Final Approval":
        for role in required_final_roles(moc):
            a = _final_row(moc, role)
            if a and a.decision != "Approved":
                out.append({"person": a.name or "(unassigned)", "email": a.email or "",
                            "role": "Final Approver", "department": a.role})
    return out


def submit(moc, today=None):
    """Draft -> Submitted for Endorsement, or Revision Requested -> resubmit
    (clears ALL endorsement + final decisions; everyone re-endorses)."""
    if moc.workflow_state not in ("Draft", "Revision Requested"):
        raise ValueError("Can only submit from Draft or Revision Requested.")
    if not can_submit(moc):
        raise ValueError("Complete the Change Request, score all risks, and mark at least one impacted department before submitting.")
    for s in endorsers(moc):
        s.decision = "Pending"; s.decision_date = ""; s.decision_comment = ""
    for a in moc.approvals:
        if a.kind == "final":
            a.decision = "Pending"; a.approved = False
    resubmit = moc.workflow_state == "Revision Requested"
    if resubmit:
        moc.revision_count = (moc.revision_count or 0) + 1
    moc.last_decline_by = ""; moc.last_decline_reason = ""
    moc.workflow_state = "Submitted for Endorsement"
    log_event(moc, "resubmitted" if resubmit else "submitted",
              ("Resubmitted for endorsement (rev " + str(moc.revision_count) + "); all endorsers must review again."
               if resubmit else "Submitted for endorsement."), actor=moc.initiator)


def record_endorsement(moc, department, decision, comment="", actor_name="", actor_email="", today=None):
    if moc.workflow_state != "Submitted for Endorsement":
        raise ValueError("MOC is not awaiting endorsement.")
    if decision not in ("Approved", "Declined"):
        raise ValueError("decision must be Approved or Declined")
    s = next((x for x in moc.stakeholders if x.impacted and x.department == department), None)
    if not s:
        raise ValueError("Not an impacted department: " + str(department))
    signer = actor_name or s.endorser_name or department
    now = datetime.utcnow().isoformat(timespec="seconds")
    s.decision = decision; s.decision_comment = comment or ""; s.decision_date = str(today or date.today())
    s.signed_by = signer; s.signed_by_email = actor_email or ""; s.decision_at = now
    log_event(moc, "endorsement",
              s.department + " " + decision + (": " + comment if comment else ""),
              actor=signer)
    if any_endorsement_declined(moc):
        moc.workflow_state = "Revision Requested"
        if decision == "Declined":
            moc.last_decline_by = s.endorser_name or department
            moc.last_decline_reason = comment or ""
            log_event(moc, "endorsement", "Routed back to originator (Revision Requested).")
    elif all_endorsed(moc):
        moc.workflow_state = "Pending Final Approval"
        log_event(moc, "endorsement", "All departments endorsed — advanced to Pending Final Approval.")


def record_final_decision(moc, role, decision, comment="", actor_name="", actor_email="", today=None):
    if moc.workflow_state != "Pending Final Approval":
        raise ValueError("MOC is not awaiting final approval.")
    if decision not in ("Approved", "Declined"):
        raise ValueError("decision must be Approved or Declined")
    a = _final_row(moc, role)
    if not a:
        raise ValueError("No final approver for role: " + str(role))
    signer = actor_name or a.name or a.role
    now = datetime.utcnow().isoformat(timespec="seconds")
    a.decision = decision; a.approved = (decision == "Approved")
    a.decision_comment = comment or ""; a.date = str(today or date.today())
    a.signed_by = signer; a.signed_by_email = actor_email or ""; a.decision_at = now
    log_event(moc, "final_decision",
              a.role + " " + decision + (": " + comment if comment else ""), actor=signer)
    if any_final_declined(moc):
        moc.workflow_state = "Revision Requested"
        moc.last_decline_by = a.name or a.role
        moc.last_decline_reason = comment or ""
        log_event(moc, "final_decision", "Routed back to originator (Revision Requested).")
    elif all_final_approved(moc):
        moc.workflow_state = "Approved"
        log_event(moc, "final_decision", "Final approval granted — MOC Approved.")


def recompute_state(moc):
    """Re-derive the workflow state from the current decisions (used after an undo).
    Never touches Draft or Closed."""
    if moc.workflow_state in ("Draft", "Closed"):
        return
    dec_e = next((s for s in endorsers(moc) if s.decision == "Declined"), None)
    if dec_e:
        moc.workflow_state = "Revision Requested"
        moc.last_decline_by = dec_e.endorser_name or dec_e.department
        moc.last_decline_reason = dec_e.decision_comment or ""
        return
    if not all_endorsed(moc):
        moc.workflow_state = "Submitted for Endorsement"
        moc.last_decline_by = ""; moc.last_decline_reason = ""
        return
    dec_f = next((a for a in moc.approvals if a.kind == "final" and a.decision == "Declined"), None)
    if dec_f:
        moc.workflow_state = "Revision Requested"
        moc.last_decline_by = dec_f.name or dec_f.role
        moc.last_decline_reason = dec_f.decision_comment or ""
        return
    if all_final_approved(moc):
        moc.workflow_state = "Approved"; moc.last_decline_by = ""; moc.last_decline_reason = ""
        return
    moc.workflow_state = "Pending Final Approval"; moc.last_decline_by = ""; moc.last_decline_reason = ""


def _reset_decision(obj):
    obj.decision = "Pending"; obj.decision_comment = ""; obj.signed_by = ""
    obj.signed_by_email = ""; obj.decision_at = ""
    if hasattr(obj, "decision_date"):
        obj.decision_date = ""
    if hasattr(obj, "approved"):
        obj.approved = False


def clear_endorsement(moc, department, actor_name="", actor_email=""):
    if moc.workflow_state in ("Draft", "Closed"):
        raise ValueError("No endorsement to clear in this state.")
    s = next((x for x in moc.stakeholders if x.impacted and x.department == department), None)
    if not s:
        raise ValueError("Not an impacted department: " + str(department))
    if s.decision == "Pending":
        raise ValueError("That endorsement has no decision to clear.")
    prev = s.decision
    _reset_decision(s)
    # the change set has changed -> any recorded final approvals presuppose full
    # endorsement and are now stale, so reset them too.
    for a in moc.approvals:
        if a.kind == "final" and a.decision != "Pending":
            _reset_decision(a)
    log_event(moc, "endorsement",
              "Cleared " + s.department + " endorsement (was " + prev + ").",
              actor=actor_name or "user")
    recompute_state(moc)


def clear_final_decision(moc, role, actor_name="", actor_email=""):
    if moc.workflow_state in ("Draft", "Closed"):
        raise ValueError("No approval to clear in this state.")
    a = _final_row(moc, role)
    if not a:
        raise ValueError("No final approver for role: " + str(role))
    if a.decision == "Pending":
        raise ValueError("That approval has no decision to clear.")
    prev = a.decision
    _reset_decision(a)
    log_event(moc, "final_decision",
              "Cleared " + a.role + " decision (was " + prev + ").", actor=actor_name or "user")
    recompute_state(moc)


def close_moc(moc):
    if moc.workflow_state != "Approved":
        raise ValueError("MOC must be Approved before closing.")
    if not (len(moc.closure_items) > 0 and all(c.complete for c in moc.closure_items) and moc.closure_date):
        raise ValueError("All closure items must be Complete and a Closure Date set.")
    moc.workflow_state = "Closed"; moc.status = "Complete"
    log_event(moc, "closed", "MOC closed on " + str(moc.closure_date) + ".")


def pending_signoffs(moc):
    """People who still owe a sign-off: impacted endorsers without initials, and
    final approvers not yet approved."""
    out = []
    # endorsement approvals are tracked in approvals(kind=endorsement); fall back to stakeholders
    endorsement_by_dept = {a.department: a for a in moc.approvals if a.kind == "endorsement"}
    for s in endorsers(moc):
        a = endorsement_by_dept.get(s.department)
        signed = bool(a and (a.initials or a.date)) if a else False
        if not signed and s.endorser_name:
            out.append({"person": s.endorser_name, "email": s.endorser_email or "",
                        "role": "Endorser", "department": s.department})
    need_ceo = approval_level(moc) == "CEO"
    for a in moc.approvals:
        if a.kind != "final":
            continue
        if a.role.startswith("CEO") and not need_ceo:
            continue
        if a.role == "Site Manager" and not a.name:
            continue
        if not a.approved and a.name:
            out.append({"person": a.name, "email": a.email or "",
                        "role": "Final Approver", "department": a.role})
    return out


def _days_late(due_str, today):
    try:
        d = date.fromisoformat(due_str)
    except Exception:
        return None
    return (today - d).days if d < today else None


def late_action_items(mocs, today=None):
    today = today or date.today()
    out = []
    for m in mocs:
        if m.status == "Complete":
            continue
        for it in m.action_items:
            dl = _days_late(it.due_date, today)
            if dl is not None and it.status != "Complete":
                out.append({"moc": m.change_number, "moc_id": m.id, "kind": "Action",
                            "item": it.description, "assigned_to": it.assigned_to,
                            "due": it.due_date, "days_late": dl})
        for it in m.impl_reqs:
            dl = _days_late(it.due_date, today)
            if dl is not None and it.status != "Complete":
                out.append({"moc": m.change_number, "moc_id": m.id, "kind": "Implementation",
                            "item": it.requirement, "assigned_to": it.assigned_to,
                            "due": it.due_date, "days_late": dl})
    out.sort(key=lambda x: -x["days_late"])
    return out


def late_signoffs(mocs, today=None):
    today = today or date.today()
    out = []
    for m in mocs:
        if m.status == "Complete" or not m.date_requested:
            continue
        try:
            age = (today - date.fromisoformat(m.date_requested)).days
        except Exception:
            continue
        if age < SIGNOFF_SLA_DAYS:
            continue
        for p in awaiting(m):
            if p["person"] and not p["person"].startswith("("):
                out.append({"moc": m.change_number, "moc_id": m.id, "age": age,
                            "state": m.workflow_state, **p})
    out.sort(key=lambda x: -x["age"])
    return out


# ---------- Personal view ("My Work") ----------
def my_view(mocs, email, today=None):
    """Everything relevant to one person (by email): MOCs they initiated or endorse,
    actions assigned to them, and sign-offs the workflow is currently awaiting from them."""
    today = today or date.today()
    email = (email or "").lower()
    my_mocs, my_actions, awaiting_me = [], [], []
    for m in mocs:
        roles = []
        if (m.initiator_email or "").lower() == email:
            roles.append("Initiator")
        endorser_here = any((s.endorser_email or "").lower() == email and s.impacted for s in m.stakeholders)
        if endorser_here:
            roles.append("Endorser")
        if roles:
            d = serialize_moc(m, full=False); d["my_roles"] = roles; my_mocs.append(d)

        # actions / implementation assigned to me
        for it in m.action_items:
            if (it.assigned_email or "").lower() == email:
                dl = _days_late(it.due_date, today)
                my_actions.append({"moc": m.change_number, "moc_id": m.id, "kind": "Action",
                                   "item": it.description, "due": it.due_date, "status": it.status,
                                   "days_late": dl if (dl is not None and it.status != "Complete") else None})
        for it in m.impl_reqs:
            if (it.assigned_email or "").lower() == email:
                dl = _days_late(it.due_date, today)
                my_actions.append({"moc": m.change_number, "moc_id": m.id, "kind": "Implementation",
                                   "item": it.requirement, "due": it.due_date, "status": it.status,
                                   "days_late": dl if (dl is not None and it.status != "Complete") else None})

        # sign-offs awaiting me right now
        if m.workflow_state == "Submitted for Endorsement":
            for s in endorsers(m):
                if (s.endorser_email or "").lower() == email and s.decision not in ("Approved", "Declined"):
                    awaiting_me.append({"moc": m.change_number, "moc_id": m.id, "kind": "Endorsement",
                                        "what": "Endorse (" + s.department + ")", "department": s.department})
        elif m.workflow_state == "Pending Final Approval":
            for a in moc_final_rows(m):
                if (a.email or "").lower() == email and a.decision != "Approved":
                    awaiting_me.append({"moc": m.change_number, "moc_id": m.id, "kind": "Final Approval",
                                        "what": "Final approval (" + a.role + ")", "role": a.role})
    return {"email": email, "my_mocs": my_mocs, "my_actions": my_actions, "awaiting_me": awaiting_me}


def moc_final_rows(moc):
    need_ceo = approval_level(moc) == "CEO"
    rows = []
    for a in moc.approvals:
        if a.kind != "final":
            continue
        if a.role.startswith("CEO") and not need_ceo:
            continue
        rows.append(a)
    return rows


# ---------- Serialization ----------
def serialize_moc(moc, full=True):
    base = {
        "id": moc.id,
        "change_number": moc.change_number,
        "status": moc.status,
        "workflow_state": moc.workflow_state,
        "revision_count": moc.revision_count or 0,
        "last_decline_by": moc.last_decline_by or "",
        "last_decline_reason": moc.last_decline_reason or "",
        "can_submit": can_submit(moc),
        "endorsement_summary": endorsement_summary(moc),
        "awaiting": awaiting(moc),
        "emergency": moc.emergency,
        "temporary": moc.temporary,
        "operating_unit": moc.operating_unit,
        "change_name": moc.change_name,
        "initiator": moc.initiator,
        "initiator_email": moc.initiator_email,
        "date_requested": moc.date_requested,
        "description": moc.description,
        "justification": moc.justification,
        "closure_date": moc.closure_date,
        "updated_at": moc.updated_at.isoformat() if moc.updated_at else None,
        # computed
        "omoc_required": omoc_required(moc),
        "flag_type": flag_type(moc),
        "max_risk": max_risk(moc),
        "approval_level": approval_level(moc),
        "pha_level": pha_level(moc),
        "risk_level": risk_level(moc),
        "priority": priority(moc),
        "progress": progress(moc),
        "steps_complete": [step_complete(moc, i) for i in range(7)],
    }
    if not full:
        return base
    base.update({
        "checklist": [{"idx": c.idx, "category": c.category, "question": c.question,
                       "answer": c.answer} for c in moc.checklist],
        "risk_items": [{"idx": r.idx, "category": r.category, "question": r.question,
                        "severity": r.severity, "likelihood": r.likelihood,
                        "score": (r.severity * r.likelihood) if (r.severity and r.likelihood) else 0}
                       for r in moc.risk_items],
        "stakeholders": [{"idx": s.idx, "department": s.department, "impacted": s.impacted,
                          "endorser_name": s.endorser_name, "endorser_email": s.endorser_email,
                          "notes": s.notes, "decision": s.decision, "decision_date": s.decision_date,
                          "decision_comment": s.decision_comment, "signed_by": s.signed_by,
                          "signed_by_email": s.signed_by_email, "decision_at": s.decision_at}
                         for s in moc.stakeholders],
        "action_items": [{"id": a.id, "seq": a.seq, "type": a.type, "description": a.description,
                          "assigned_to": a.assigned_to, "assigned_email": a.assigned_email,
                          "due_date": a.due_date, "status": a.status, "comments": a.comments}
                         for a in moc.action_items],
        "impl_reqs": [{"id": a.id, "seq": a.seq, "category": a.category, "requirement": a.requirement,
                       "assigned_to": a.assigned_to, "assigned_email": a.assigned_email,
                       "due_date": a.due_date, "status": a.status,
                       "verification": a.verification, "comments": a.comments} for a in moc.impl_reqs],
        "attachments": [{"id": a.id, "seq": a.seq, "description": a.description, "link": a.link}
                        for a in moc.attachments],
        "approvals": [{"id": a.id, "kind": a.kind, "role": a.role, "department": a.department,
                       "name": a.name, "title": a.title, "email": a.email, "date": a.date,
                       "initials": a.initials, "approved": a.approved, "decision": a.decision,
                       "decision_comment": a.decision_comment, "signed_by": a.signed_by,
                       "signed_by_email": a.signed_by_email, "decision_at": a.decision_at,
                       "comments": a.comments}
                      for a in moc.approvals],
        "required_final_roles": required_final_roles(moc),
        "lessons": [{"id": l.id, "seq": l.seq, "category": l.category, "lesson": l.lesson,
                     "action": l.action, "owner": l.owner} for l in moc.lessons],
        "closure_items": [{"idx": c.idx, "question": c.question, "complete": c.complete,
                           "verified_by": c.verified_by, "date": c.date, "comments": c.comments}
                          for c in moc.closure_items],
        "pending_signoffs": pending_signoffs(moc),
        "audit_events": [{"timestamp": ev.timestamp.isoformat() if ev.timestamp else "",
                          "actor": ev.actor, "event_type": ev.event_type, "summary": ev.summary}
                         for ev in sorted(moc.audit_events, key=lambda e: e.id, reverse=True)],
    })
    return base
