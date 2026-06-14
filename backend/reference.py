"""Reference data for OMOC forms — checklist questions, risk questions, departments,
closure questions. Mirrors Fervo_MOC_Form_v2. In production these become admin-managed
reference tables; kept here as constants for the prototype."""

CHECKLIST_QUESTIONS = [
    ("Process Chemistry and Technology", "Are you changing, substituting, or introducing new process chemicals?"),
    ("Process Chemistry and Technology", "Are you modifying or implementing new process technology?"),
    ("Equipment or Facilities", "Are you installing, removing, replacing (not in kind), or modifying process equipment or gathering system equipment?"),
    ("Equipment or Facilities", "Are you making any physical changes to facilities that affect a covered process?"),
    ("Equipment or Facilities", "Are you making any changes that impact the steady state operation of the subsurface process?"),
    ("Procedures", "Are you updating, rewriting, or creating new operating procedures?"),
    ("Control Systems", "Are you modifying control system parameters, logic, alarms, or instrumentation settings?"),
    ("Safety Systems", "Are you altering safety systems, interlocks, or protections that impact process safety?"),
    ("Operating Envelopes", "Are you modifying defined safe operating limits or system envelopes?"),
    ("Risk, Compliance, and Organizational Impact", "Does this change potentially impact personnel safety, environmental compliance, facility integrity, or regulatory requirements?"),
]

RISK_QUESTIONS = [
    ("Safety, Health & Environmental", "Could the change significantly affect employee or public safety?"),
    ("Safety, Health & Environmental", "Could the change alter or bypass a safety system or protective control?"),
    ("Safety, Health & Environmental", "Could the change have a material environmental impact?"),
    ("Compliance & Regulatory", "Does the change affect permit requirements or regulatory limits?"),
    ("Compliance & Regulatory", "Does this change create or increase the risk of non-compliance?"),
    ("Technical & Operational", "Does the change modify core process conditions?"),
    ("Technical & Operational", "Will new equipment or control logic be added or removed?"),
    ("Organizational & Cross-Team", "Will the change affect more than one team or department?"),
    ("Organizational & Cross-Team", "Will the change require training or procedural updates?"),
    ("Financial", "What is the financial impact if this change does not occur?"),
]

DEPARTMENTS = [
    "Process Engineering", "Electrical Engineering", "Mechanical Engineering",
    "Instrumentation and Controls Engineering", "Turbomachinery Engineering",
    "Safety and Environmental", "Mechanical Planner", "Civil and Structural Engineering",
    "Drafting and Modeling", "Operations", "Reservoir Engineering", "Production Engineering",
]

CLOSURE_QUESTIONS = [
    "Have all action items been completed?",
    "Have all implementation requirements been verified per their specified verification methods?",
    "Have all affected operating procedures been updated and approved?",
    "Have all affected P&IDs, drawings, and technical documents been updated?",
    "Has required training been completed and documented for all affected personnel?",
    "Have all affected safety systems, interlocks, and protections been tested and verified?",
    "Has the change been communicated to all affected stakeholders?",
    "Have all endorsers confirmed their areas of responsibility are addressed?",
    "Has a post-implementation review or inspection been conducted?",
    "Have any temporary changes been reverted or formally converted to permanent?",
]

SIGNOFF_SLA_DAYS = 14

# Workflow states (the MOC lifecycle / approval state machine)
STATES = [
    "Draft",                       # originator filling it out
    "Submitted for Endorsement",   # impacted endorsers must Approve or Decline
    "Revision Requested",          # an endorser/approver declined -> back to originator
    "Pending Final Approval",      # all endorsers approved -> awaiting VP/CEO
    "Approved",                    # final approval granted -> ready to implement
    "Closed",                      # closure complete
]
