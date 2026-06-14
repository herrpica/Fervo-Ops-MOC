"""Seed the database with the four real Project Red OMOCs (imported from the v1
workbooks). Idempotent: only seeds if the mocs table is empty."""
from . import models
from .reference import (CHECKLIST_QUESTIONS, RISK_QUESTIONS, DEPARTMENTS,
                        CLOSURE_QUESTIONS)

CONTACTS = {
    "Erik Stein": "erik.stein@fervoenergy.com",
    "Jason Bottoms": "jason.bottoms@fervoenergy.com",
    "Joseph Catania": "joseph.catania@fervoenergy.com",
    "Sydni Tomblin": "sydni.tomblin@fervoenergy.com",
    "Camden Lang": "camden.lang@fervoenergy.com",
    "Gerard Ngo": "gerard.ngo@fervoenergy.com",
    "Christian Gradl": "christian.gradl@fervoenergy.com",
    "Quinn Woodard": "quinn.woodard@fervoenergy.com",
    "Gabriel Martin-Hsia": "gabriel.martin-hsia@fervoenergy.com",
    "Caroline Courbois": "caroline.courbois@fervoenergy.com",
    "Robert Perez": "robert.perez@fervoenergy.com",
}
STATUS = {"Complete": "Complete", "Ongoing": "In Progress", "In Progress": "In Progress",
          "Not Started": "Not Started", "": "Not Started"}

# People directory (name, email, department, role). Email is the identity key.
PEOPLE = [
    ("Tim Pica", "tim.pica@fervoenergy.com", "PSM / Safety", "MOC Coordinator"),
    ("Camden Lang", "camden.lang@fervoenergy.com", "Production Engineering", "Senior Production Engineer"),
    ("Gabriel Martin-Hsia", "gabriel.martin-hsia@fervoenergy.com", "Turbomachinery Engineering", "Turbomachinery Lead"),
    ("Caroline Courbois", "caroline.courbois@fervoenergy.com", "Instrumentation and Controls Engineering", "I&C Engineer"),
    ("Erik Stein", "erik.stein@fervoenergy.com", "Instrumentation and Controls Engineering", "I&C Lead"),
    ("Jason Bottoms", "jason.bottoms@fervoenergy.com", "Drafting and Modeling", "CAD Manager"),
    ("Joseph Catania", "joseph.catania@fervoenergy.com", "Operations", "Plant Manager"),
    ("Sydni Tomblin", "sydni.tomblin@fervoenergy.com", "Reservoir Engineering", "Reservoir Engineer"),
    ("Gerard Ngo", "gerard.ngo@fervoenergy.com", "Electrical Engineering", "Electrical Engineering Supervisor"),
    ("Christian Gradl", "christian.gradl@fervoenergy.com", "Operations", "VP Operations"),
    ("Quinn Woodard", "quinn.woodard@fervoenergy.com", "PowerCo", "VP Power Generation & Surface Facilities"),
    ("Robert Perez", "robert.perez@fervoenergy.com", "Cybersecurity", "Manager of Cybersecurity"),
]
# Map the abbreviated assignee names used in the seed action items to a person email.
ALIAS = {
    "J. Catania": "joseph.catania@fervoenergy.com", "E. Stein": "erik.stein@fervoenergy.com",
    "J. Bottoms": "jason.bottoms@fervoenergy.com", "C. Courbois": "caroline.courbois@fervoenergy.com",
    "C. Lang": "camden.lang@fervoenergy.com", "R. Perez (Cybersecurity Manager)": "robert.perez@fervoenergy.com",
}


def _assignee_email(who):
    return ALIAS.get(who) or CONTACTS.get(who, "")


def _email(name):
    return CONTACTS.get(name, "")


def _build(spec):
    m = models.MOC(
        change_number=spec["num"], status="Active",
        workflow_state="Submitted for Endorsement",
        emergency=spec.get("emergency", False), temporary=spec.get("temporary", False),
        operating_unit=spec.get("ou", "Fervo Project Site"), change_name=spec["name"],
        initiator=spec.get("initiator") or spec["init"][0]["name"],
        initiator_email=_email(spec.get("initiator") or spec["init"][0]["name"]),
        date_requested=spec["date"],
        description=spec["desc"], justification=spec["just"], is_seed=True,
    )
    for i, (cat, q) in enumerate(CHECKLIST_QUESTIONS):
        m.checklist.append(models.ChecklistItem(
            idx=i, category=cat, question=q, answer=("Y" if i in spec["checklist"] else "N")))
    for i, (cat, q) in enumerate(RISK_QUESTIONS):
        m.risk_items.append(models.RiskItem(
            idx=i, category=cat, question=q, severity=spec["sev"][i], likelihood=1))
    impacted = {row[0]: row for row in spec.get("stake", [])}
    for i, dept in enumerate(DEPARTMENTS):
        row = impacted.get(i)
        if row:
            m.stakeholders.append(models.Stakeholder(
                idx=i, department=dept, impacted=True, endorser_name=row[1],
                endorser_email=_email(row[1]), notes=(row[2] if len(row) > 2 else "")))
        else:
            m.stakeholders.append(models.Stakeholder(idx=i, department=dept, impacted=False))
    for j, a in enumerate(spec.get("actions", []), start=1):
        m.action_items.append(models.ActionItem(
            seq=j, type=a.get("type", ""), description=a["desc"], assigned_to=a["who"],
            assigned_email=_assignee_email(a["who"]),
            due_date=a.get("due", ""), status=STATUS.get(a.get("status", ""), "Not Started"),
            comments=a.get("comments", "")))
    for j, a in enumerate(spec.get("att", []), start=1):
        m.attachments.append(models.Attachment(seq=j, description=a["desc"], link=a.get("link", "")))
    init = spec["init"]
    m.approvals.append(models.Approval(kind="initiation", role="Initiator",
        name=init[0]["name"], title=init[0].get("title", ""), email=_email(init[0]["name"]),
        initials=init[0].get("initials", ""), date=init[0].get("date", "")))
    m.approvals.append(models.Approval(kind="initiation", role="MOC Coordinator",
        name=init[1]["name"], title=init[1].get("title", ""), email=_email(init[1]["name"]),
        initials=init[1].get("initials", ""), date=init[1].get("date", "")))
    ap = spec["approver"]
    m.approvals.append(models.Approval(kind="final", role="VP Operations",
        name=ap["name"], title=ap.get("title", ""), email=_email(ap["name"]), approved=False))
    for i, q in enumerate(CLOSURE_QUESTIONS):
        m.closure_items.append(models.ClosureItem(idx=i, question=q, complete=False))
    m.audit_events.append(models.AuditEvent(event_type="created", summary="MOC created.", actor=m.initiator))
    m.audit_events.append(models.AuditEvent(event_type="submitted", summary="Submitted for endorsement.", actor=m.initiator))
    return m


INIT_PROD = {"name": "Camden Lang", "title": "Senior Production Engineer"}
COORD_GMH = {"name": "Gabriel Martin-Hsia", "title": "Turbomachinery Lead"}
CC = {"name": "Caroline Courbois", "title": "Instrumentation and Controls Engineer"}
GRADL = {"name": "Christian Gradl", "title": "VP Operations"}

SPECS = [
    {"num": "RED-MOC-04", "name": "Historian — Site Historian & Firewall", "ou": "Red",
     "date": "2025-11-07", "checklist": [9], "sev": [1,1,1,1,1,1,1,1,2,1],
     "desc": "Installing:\n- Canary site historian to store data.\n- Firewall to support secure internet access for remote data visualization.",
     "just": "Fervo currently relies on manual data pulls from Ormat's plant historian. The reasonable path forward is for Fervo to have a remotely-accessible site historian; remote access via a secure connection requires updates to the network architecture.",
     "stake": [[3, "Erik Stein", "Also endorsed by Cybersecurity — Robert Perez (Manager of Cybersecurity)"],
               [8, "Jason Bottoms"], [10, "Sydni Tomblin"], [11, "Camden Lang"]],
     "actions": [
         {"desc": "Install and commission firewall, server, Starlink connection. Move Ubiquiti and workstation ethernet to firewall.", "who": "C. Courbois", "due": "2025-12-31", "status": "Complete"},
         {"desc": "Apply firewall rules to all extraneous network traffic after monitoring traffic for a 1-week period.", "who": "R. Perez (Cybersecurity Manager)", "due": "2025-12-31", "status": "Ongoing", "comments": "Baseline protections in place. Narrowing permitted traffic further."},
         {"desc": "Update network drawing to reflect updated configuration.", "who": "J. Bottoms", "due": "2025-12-31", "status": "Complete"}],
     "att": [{"desc": "Updated OT network diagram", "link": "https://app.box.com/s/u6r1uy7pi9kgkjn7q2at0p2aucjfjib3"}],
     "init": [{"name": CC["name"], "title": CC["title"], "initials": "CC", "date": "2025-12-29"},
              {"name": CC["name"], "title": CC["title"], "initials": "CC", "date": "2025-12-29"}],
     "approver": {"name": "Quinn Woodard", "title": "VP Power Generation & Surface Facilities (PowerCo)"}},

    {"num": "RED-MOC-03", "name": "Red: Temporary Ultrasonic Historization", "ou": "Red",
     "date": "2025-10-07", "temporary": True, "checklist": [], "sev": [1,1,1,1,1,1,3,2,1,1],
     "desc": "Removed logic assigning values to the historized DP output and scaled flow tags. Readings are now fed from the ultrasonic analog input to these historized tags.",
     "just": "There was an urgent need for historized flow data. The orifice plate DP meter is no longer accurate. Until Ormat can historize the ultrasonic tag and the orifice plate is replaced, the ultrasonic flow data will be historized on the existing tag.",
     "stake": [[3, "Erik Stein"], [9, "Joseph Catania"], [10, "Sydni Tomblin"], [11, "Camden Lang"]],
     "actions": [
         {"desc": "Go online with PLC. Make appropriate logic changes.", "who": "C. Courbois", "due": "2025-10-07", "status": "Complete"},
         {"desc": "Ormat: subscribe to the PLC ultrasonic tag on their PI historian.", "who": "Ormat controls", "due": "2026-03-01", "status": "Complete", "comments": "Action de-scoped. Workaround: installed Fervo-owned Historian."},
         {"desc": "Replace damaged orifice plate.", "who": "C. Lang", "due": "2026-03-01", "status": "Not Started"},
         {"desc": "Revert PLC changes after orifice plate is replaced and historian is modified.", "who": "C. Courbois", "due": "2026-03-01", "status": "Not Started"}],
     "init": [{"name": CC["name"], "title": CC["title"], "initials": "CC", "date": "2025-10-21"}, INIT_PROD],
     "approver": GRADL},

    {"num": "RED-MOC-02", "name": "Red: Power to MOVs", "ou": "Red", "date": "2025-10-01",
     "emergency": True, "checklist": [2, 3], "sev": [1,1,1,1,1,1,2,2,1,1],
     "desc": "Wire 120/240V AC power directly to three motor-operated valves (GV-3422 brine return block, GV-3422.1 sump, GV-34A22 production block), bypassing failed field batteries, and install a UPS so the brine return block valve fails to a safe configuration on loss of primary power (preventing ~300F brine reaching the injection pumps).",
     "just": "Achieves the intended design — motor actuation of the three valves under primary AC power — and provides automatic safe configuration on loss of primary power at the well pad.",
     "stake": [[1, "Gerard Ngo"], [8, "Jason Bottoms"], [9, "Joseph Catania"], [11, "Camden Lang"]],
     "actions": [
         {"desc": "Wire 120V AC to brine return and production valves; remove batteries from field junction boxes.", "who": "J. Catania", "due": "2025-10-01", "status": "Complete"},
         {"desc": "Wire 240V AC power directly to the sump valve (GV-3422.1).", "who": "J. Catania", "due": "2025-10-01", "status": "Ongoing", "comments": "Completion contingent on parts availability in Winnemucca."},
         {"desc": "Install 120V UPS at e-house to supply the brine return valve (GV-3422).", "who": "J. Catania", "due": "2025-10-01", "status": "Ongoing", "comments": "Completion contingent on parts availability in Winnemucca."},
         {"desc": "Complete redlines to reflect current configuration.", "who": "J. Bottoms", "due": "2025-10-31", "status": ""}],
     "init": [INIT_PROD, COORD_GMH], "approver": GRADL},

    {"num": "RED-MOC-01", "name": "Red FIT3422 — Redundant Production Flow Meter", "ou": "Red",
     "date": "2025-09-30", "emergency": True, "checklist": [2, 3, 6], "sev": [1,1,1,1,1,1,2,2,1,1],
     "desc": "Install one additional flow meter (Flexim ultrasonic) on the production line. The 4-20 mA signal wires to a spare analog IO terminal; a new control-system tag is created and the HMI updated to display the live reading.",
     "just": "The existing dP orifice flow meter has been producing unreliable data. A redundant flow metering device improves robustness of the Red data acquisition campaign.",
     "stake": [[3, "Erik Stein"], [8, "Jason Bottoms"], [9, "Joseph Catania"], [10, "Sydni Tomblin"], [11, "Camden Lang"]],
     "actions": [
         {"desc": "Install new Flexim ultrasonic meter on production piping.", "who": "J. Catania", "due": "2025-10-01", "status": "Complete"},
         {"desc": "Wire new Flexim ultrasonic signal to spare analog IO terminals.", "who": "J. Catania", "due": "2025-10-01", "status": "Complete"},
         {"desc": "Create a new tag to accommodate the new flow signal - PLC download.", "who": "E. Stein", "due": "2025-10-15", "status": "Complete"},
         {"desc": "Update the HMI to display ultrasonic flow reading.", "who": "E. Stein", "due": "2025-10-15", "status": "Complete"},
         {"desc": "Complete redlines to reflect current configuration.", "who": "J. Bottoms", "due": "2025-10-31", "status": "Complete"}],
     "att": [{"desc": "PLC/HMI update - photos of changes", "link": "Redline 10_2_2025"}],
     "init": [INIT_PROD, COORD_GMH], "approver": GRADL},
]


def seed_people(db):
    if db.query(models.Person).count() > 0:
        return
    for name, email, dept, role in PEOPLE:
        db.add(models.Person(name=name, email=email, department=dept, role=role))
    db.commit()


def seed_if_empty(db):
    seed_people(db)
    if db.query(models.MOC).count() > 0:
        return False
    for spec in SPECS:
        db.add(_build(spec))
    db.commit()
    return True
