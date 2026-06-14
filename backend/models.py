"""Relational data model for the OMOC application.

One MOC has many of each child entity (checklist answers, risk items, stakeholders,
action items, implementation requirements, attachments, approvals, lessons, closure
items). All children cascade-delete with their parent MOC.
"""
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Text, Boolean, DateTime,
                        ForeignKey)
from sqlalchemy.orm import relationship
from .database import Base


class MOC(Base):
    __tablename__ = "mocs"
    id = Column(Integer, primary_key=True)
    change_number = Column(String, unique=True, nullable=False)
    status = Column(String, default="Active")          # Active | Complete (dashboard grouping)
    workflow_state = Column(String, default="Draft")   # see logic.STATES
    revision_count = Column(Integer, default=0)
    last_decline_by = Column(String, default="")
    last_decline_reason = Column(Text, default="")
    emergency = Column(Boolean, default=False)
    temporary = Column(Boolean, default=False)
    operating_unit = Column(String, default="Fervo Project Site")
    change_name = Column(String, default="")
    initiator = Column(String, default="")
    initiator_email = Column(String, default="")        # identity key for "My MOCs"
    date_requested = Column(String, default="")         # ISO date string yyyy-mm-dd
    description = Column(Text, default="")
    justification = Column(Text, default="")
    closure_date = Column(String, default="")
    is_seed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    checklist = relationship("ChecklistItem", back_populates="moc",
                             cascade="all, delete-orphan", order_by="ChecklistItem.idx")
    risk_items = relationship("RiskItem", back_populates="moc",
                              cascade="all, delete-orphan", order_by="RiskItem.idx")
    stakeholders = relationship("Stakeholder", back_populates="moc",
                                cascade="all, delete-orphan", order_by="Stakeholder.idx")
    action_items = relationship("ActionItem", back_populates="moc",
                                cascade="all, delete-orphan", order_by="ActionItem.seq")
    impl_reqs = relationship("ImplReq", back_populates="moc",
                             cascade="all, delete-orphan", order_by="ImplReq.seq")
    attachments = relationship("Attachment", back_populates="moc",
                               cascade="all, delete-orphan", order_by="Attachment.seq")
    approvals = relationship("Approval", back_populates="moc",
                             cascade="all, delete-orphan", order_by="Approval.id")
    lessons = relationship("Lesson", back_populates="moc",
                           cascade="all, delete-orphan", order_by="Lesson.seq")
    closure_items = relationship("ClosureItem", back_populates="moc",
                                 cascade="all, delete-orphan", order_by="ClosureItem.idx")
    audit_events = relationship("AuditEvent", back_populates="moc",
                                cascade="all, delete-orphan", order_by="AuditEvent.id")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    idx = Column(Integer)
    category = Column(String)
    question = Column(Text)
    answer = Column(String, default="N")               # Y | N
    moc = relationship("MOC", back_populates="checklist")


class RiskItem(Base):
    __tablename__ = "risk_items"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    idx = Column(Integer)
    category = Column(String)
    question = Column(Text)
    severity = Column(Integer, nullable=True)          # 1-5
    likelihood = Column(Integer, nullable=True)        # 1-5
    moc = relationship("MOC", back_populates="risk_items")


class Stakeholder(Base):
    __tablename__ = "stakeholders"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    idx = Column(Integer)
    department = Column(String)
    impacted = Column(Boolean, default=False)
    endorser_name = Column(String, default="")
    endorser_email = Column(String, default="")
    notes = Column(Text, default="")
    decision = Column(String, default="Pending")        # Pending | Approved | Declined
    decision_date = Column(String, default="")
    decision_comment = Column(Text, default="")
    signed_by = Column(String, default="")              # who actually recorded the decision
    signed_by_email = Column(String, default="")        # their identity (Entra UPN once auth is live)
    decision_at = Column(String, default="")            # full ISO timestamp of the sign-off
    moc = relationship("MOC", back_populates="stakeholders")


class ActionItem(Base):
    __tablename__ = "action_items"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    seq = Column(Integer)
    type = Column(String, default="")
    description = Column(Text, default="")
    assigned_to = Column(String, default="")
    assigned_email = Column(String, default="")        # identity key for "My Actions"
    due_date = Column(String, default="")
    status = Column(String, default="Not Started")
    comments = Column(Text, default="")
    moc = relationship("MOC", back_populates="action_items")


class ImplReq(Base):
    __tablename__ = "impl_reqs"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    seq = Column(Integer)
    category = Column(String, default="")
    requirement = Column(Text, default="")
    assigned_to = Column(String, default="")
    assigned_email = Column(String, default="")        # identity key for "My Actions"
    due_date = Column(String, default="")
    status = Column(String, default="Not Started")
    verification = Column(String, default="")
    comments = Column(Text, default="")
    moc = relationship("MOC", back_populates="impl_reqs")


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    seq = Column(Integer)
    description = Column(Text, default="")
    link = Column(Text, default="")
    moc = relationship("MOC", back_populates="attachments")


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    kind = Column(String)                  # initiation | endorsement | final
    role = Column(String, default="")
    department = Column(String, default="")
    name = Column(String, default="")
    title = Column(String, default="")
    email = Column(String, default="")
    date = Column(String, default="")
    initials = Column(String, default="")
    approved = Column(Boolean, default=False)
    decision = Column(String, default="Pending")        # Pending | Approved | Declined (final approvers)
    decision_comment = Column(Text, default="")
    signed_by = Column(String, default="")              # who actually recorded the decision
    signed_by_email = Column(String, default="")        # their identity (Entra UPN once auth is live)
    decision_at = Column(String, default="")            # full ISO timestamp of the approval
    comments = Column(Text, default="")
    moc = relationship("MOC", back_populates="approvals")


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    seq = Column(Integer)
    category = Column(String, default="")
    lesson = Column(Text, default="")
    action = Column(Text, default="")
    owner = Column(String, default="")
    moc = relationship("MOC", back_populates="lessons")


class ClosureItem(Base):
    __tablename__ = "closure_items"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    idx = Column(Integer)
    question = Column(Text)
    complete = Column(Boolean, default=False)
    verified_by = Column(String, default="")
    date = Column(String, default="")
    comments = Column(Text, default="")
    moc = relationship("MOC", back_populates="closure_items")


class Person(Base):
    """People directory — the identity source for initiators, endorsers, approvers, and
    action assignees. `email` is the match key (and becomes the Entra ID UPN later)."""
    __tablename__ = "people"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    department = Column(String, default="")
    role = Column(String, default="")


class AuditEvent(Base):
    """Append-only history of everything that happens to a MOC: creation, content
    edits, submissions, endorsement/approval decisions, and closure. `actor` is a
    placeholder until Entra ID is wired, after which it carries the signed-in user."""
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True)
    moc_id = Column(Integer, ForeignKey("mocs.id", ondelete="CASCADE"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    actor = Column(String, default="")
    event_type = Column(String)        # created | edited | submitted | resubmitted | endorsement | final_decision | closed
    summary = Column(Text, default="")
    moc = relationship("MOC", back_populates="audit_events")
