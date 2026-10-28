"""
ExcelR Track360 - BRD Requirements Alignment Test Suite
Verifies critical business constraints specified in the October 26, 2026 BRD:
1. Exact Statuses & Mandatory Redo Correction Note Validation (Part 5)
2. Bulk Assignment Status Updates & Atomic Eligibility Progression (Part 6)
3. 15-Business-Day Project Queue & Weekend-Exclusion SLA (Part 7)
4. Dropped Project Workflow with Mandatory Reason (Part 7)
5. NASSCOM Clearance Verification for Data Analytics/Science Course Certificates (Part 8)
"""
from datetime import datetime, timedelta, timezone, date
from typing import Tuple
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.core.security import hash_password, utc_now
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
from app.modules.auth.models import Role, User, UserRole
from app.modules.candidates.models import Batch, Candidate, CandidateNote, Course, CourseTrack, Enrollment
from app.modules.assignments.models import Assignment, AssignmentAllocation, AssignmentSubmission, SubmissionAttempt
from app.modules.projects.models import Project, ProjectGroup, ProjectGroupMember, ProjectAllocation
from app.modules.certificates.service import CertificateService
from app.shared.business_calendar import calculate_business_days, is_allocation_overdue


async def login_as_admin(async_client: AsyncClient) -> dict:
    """Helper returning auth session cookies and CSRF headers."""
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@excelr.com", "password": "Admin@Track360_2026!"},
    )
    assert resp.status_code == 200
    csrf = resp.json()["csrf_token"]
    session_token = resp.cookies[SESSION_COOKIE_NAME]
    return {
        "cookies": {SESSION_COOKIE_NAME: session_token, CSRF_COOKIE_NAME: csrf},
        "headers": {"x-csrf-token": csrf},
    }


def test_business_calendar_weekend_exclusion():
    """Verifies that calculate_business_days excludes Saturdays and Sundays."""
    # A Friday to the following Monday = 1 working day elapsed (Monday)
    # Friday 2026-10-23 to Monday 2026-10-26
    start = date(2026, 10, 23)
    end = date(2026, 10, 26)
    days = calculate_business_days(start, end)
    assert days == 1, f"Expected 1 business day between Fri and Mon, got {days}"

    # A 3-week window (21 calendar days = 15 business days)
    start_3w = date(2026, 10, 5)
    end_3w = date(2026, 10, 26)
    days_3w = calculate_business_days(start_3w, end_3w)
    assert days_3w == 15

    # More than 15 working days elapsed is overdue
    assert is_allocation_overdue(datetime(2026, 10, 5, tzinfo=timezone.utc), sla_business_days=15) is True


@pytest.mark.asyncio
async def test_redo_validation_enforces_meaningful_correction_note(async_client: AsyncClient):
    """
    BRD Part 5: When an evaluator changes an assignment to Redo,
    a meaningful correction note is strictly mandatory (backend rejection of blank/whitespace).
    """
    auth = await login_as_admin(async_client)
    uid = uuid.uuid4().hex[:6]

    session_factory = get_session_factory()
    async with session_factory() as session:
        course = Course(id=uuid.uuid4(), code=f"CRS-REDO-{uid}", title="Course Redo", is_active=True)
        session.add(course)
        await session.flush()

        track = CourseTrack(
            id=uuid.uuid4(), course_id=course.id, code=f"TRK-REDO-{uid}",
            title="Redo Track", total_mandatory_assignments=1, total_required_projects=1, is_active=True
        )
        session.add(track)
        await session.flush()

        batch = Batch(id=uuid.uuid4(), track_id=track.id, batch_code=f"B-REDO-{uid}", title="Batch Redo", start_date=date.today())
        session.add(batch)
        await session.flush()

        cand = Candidate(
            id=uuid.uuid4(), candidate_number=f"EX-REDO-{uid}", first_name="Aman", last_name="Verma",
            email=f"aman.{uid}@example.com", phone=f"+9198765{uid[:5]}", lifecycle_status="ACTIVE", project_eligible=False
        )
        session.add(cand)
        await session.flush()

        asg = Assignment(
            id=uuid.uuid4(), track_id=track.id, code=f"ASG-REDO-{uid}", title="Python Milestone",
            instructions_markdown="Complete python tasks", sequence_order=1, is_mandatory=True,
            max_score=100.0, passing_score=60.0, is_active=True
        )
        session.add(asg)
        await session.flush()

        alloc = AssignmentAllocation(
            id=uuid.uuid4(), assignment_id=asg.id, batch_id=batch.id, candidate_id=cand.id,
            due_date_utc=utc_now() + timedelta(days=7)
        )
        session.add(alloc)
        await session.flush()

        sub = AssignmentSubmission(
            id=uuid.uuid4(), allocation_id=alloc.id, candidate_id=cand.id,
            current_submission_status="SUBMITTED", current_completion_status="INCOMPLETE", total_attempts=1
        )
        session.add(sub)
        await session.flush()

        att = SubmissionAttempt(
            id=uuid.uuid4(), submission_id=sub.id, attempt_number=1,
            submitted_at_utc=utc_now(), is_late=False, lateness_minutes=0
        )
        session.add(att)
        await session.commit()
        sub_id = str(sub.id)

    # 1. Attempt Redo (CORRECTIONS_REQUESTED) with blank feedback -> MUST FAIL with 422
    resp_blank = await async_client.post(
        f"/api/v1/assignments/submissions/{sub_id}/review",
        json={
            "review_outcome": "CORRECTIONS_REQUESTED",
            "qualitative_feedback": "     ",
            "rubric_scores": [],
        },
        **auth,
    )
    assert resp_blank.status_code == 422
    assert "correction note" in resp_blank.text.lower() or "value_error" in resp_blank.text.lower()

    # 2. Attempt Redo with meaningful correction note -> MUST SUCCEED with 201
    resp_valid = await async_client.post(
        f"/api/v1/assignments/submissions/{sub_id}/review",
        json={
            "review_outcome": "CORRECTIONS_REQUESTED",
            "qualitative_feedback": "Please fix unit test assertions and re-submit code.",
            "rubric_scores": [],
        },
        **auth,
    )
    assert resp_valid.status_code == 201
    data = resp_valid.json()
    assert data["review_outcome"] == "CORRECTIONS_REQUESTED"
    assert "fix unit test" in data["qualitative_feedback"]


@pytest.mark.asyncio
async def test_bulk_assignment_status_update_endpoint(async_client: AsyncClient):
    """
    BRD Part 6: Bulk assignment operations grid support.
    Updates multiple learner assignments atomically, validates redo notes, and re-evaluates project eligibility.
    """
    auth = await login_as_admin(async_client)
    uid = uuid.uuid4().hex[:6]

    session_factory = get_session_factory()
    async with session_factory() as session:
        course = Course(id=uuid.uuid4(), code=f"CRS-BLK-{uid}", title="Bulk Course", is_active=True)
        session.add(course)
        await session.flush()

        track = CourseTrack(
            id=uuid.uuid4(), course_id=course.id, code=f"TRK-BLK-{uid}",
            title="Bulk Track", total_mandatory_assignments=1, total_required_projects=1, is_active=True
        )
        session.add(track)
        await session.flush()

        batch = Batch(id=uuid.uuid4(), track_id=track.id, batch_code=f"B-BLK-{uid}", title="Bulk Batch", start_date=date.today())
        session.add(batch)
        await session.flush()

        c1 = Candidate(
            id=uuid.uuid4(), candidate_number=f"EX-B1-{uid}", first_name="Rohan", last_name="Sharma",
            email=f"rohan.{uid}@example.com", phone=f"+9198111{uid[:5]}", lifecycle_status="ACTIVE", project_eligible=False
        )
        c2 = Candidate(
            id=uuid.uuid4(), candidate_number=f"EX-B2-{uid}", first_name="Pooja", last_name="Nair",
            email=f"pooja.{uid}@example.com", phone=f"+9198222{uid[:5]}", lifecycle_status="ACTIVE", project_eligible=False
        )
        session.add_all([c1, c2])
        await session.flush()

        asg = Assignment(
            id=uuid.uuid4(), track_id=track.id, code=f"ASG-BLK-{uid}", title="Milestone 1",
            instructions_markdown="Instructions...", sequence_order=1, is_mandatory=True,
            max_score=100.0, passing_score=60.0, is_active=True
        )
        session.add(asg)
        await session.flush()

        alloc1 = AssignmentAllocation(id=uuid.uuid4(), assignment_id=asg.id, batch_id=batch.id, candidate_id=c1.id, due_date_utc=utc_now() + timedelta(days=7))
        alloc2 = AssignmentAllocation(id=uuid.uuid4(), assignment_id=asg.id, batch_id=batch.id, candidate_id=c2.id, due_date_utc=utc_now() + timedelta(days=7))
        session.add_all([alloc1, alloc2])
        await session.flush()

        sub1 = AssignmentSubmission(id=uuid.uuid4(), allocation_id=alloc1.id, candidate_id=c1.id, current_submission_status="PENDING", current_completion_status="INCOMPLETE")
        sub2 = AssignmentSubmission(id=uuid.uuid4(), allocation_id=alloc2.id, candidate_id=c2.id, current_submission_status="PENDING", current_completion_status="INCOMPLETE")
        session.add_all([sub1, sub2])
        await session.commit()

        sub1_id = str(sub1.id)
        sub2_id = str(sub2.id)
        c1_id = c1.id

    # Execute bulk status update: Mark sub1 as Done and sub2 as Redo (with note)
    bulk_payload = {
        "items": [
            {
                "submission_id": sub1_id,
                "status": "Done",
                "awarded_score": 85.0,
            },
            {
                "submission_id": sub2_id,
                "status": "Redo",
                "correction_note": "Please update exploratory analysis charts.",
            },
        ]
    }
    resp = await async_client.post("/api/v1/assignments/submissions/bulk-status", json=bulk_payload, **auth)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["total_processed"] == 2
    assert res_data["successful_count"] == 2
    assert res_data["failed_count"] == 0

    # Verify c1 became project_eligible because all mandatory assignments are Done
    async with session_factory() as session:
        c1_check = (await session.execute(select(Candidate).where(Candidate.id == c1_id))).scalar_one()
        assert c1_check.project_eligible is True


@pytest.mark.asyncio
async def test_project_allocation_queue_and_overdue_tracking(async_client: AsyncClient):
    """
    BRD Part 7: 15-business-day allocation target tracking.
    Queue must reflect working days in queue (excluding weekends) and overdue flags.
    """
    auth = await login_as_admin(async_client)
    uid = uuid.uuid4().hex[:6]

    session_factory = get_session_factory()
    async with session_factory() as session:
        course = Course(id=uuid.uuid4(), code=f"CRS-Q-{uid}", title="Queue Course", is_active=True)
        session.add(course)
        await session.flush()

        track = CourseTrack(
            id=uuid.uuid4(), course_id=course.id, code=f"TRK-Q-{uid}",
            title="Queue Track", total_mandatory_assignments=1, total_required_projects=1, is_active=True
        )
        session.add(track)
        await session.flush()

        batch = Batch(id=uuid.uuid4(), track_id=track.id, batch_code=f"B-Q-{uid}", title="Queue Batch", start_date=date.today())
        session.add(batch)
        await session.flush()

        # Eligible candidate who completed assignments 25 days ago (overdue > 15 business days)
        old_time = utc_now() - timedelta(days=25)
        c_overdue = Candidate(
            id=uuid.uuid4(), candidate_number=f"EX-Q1-{uid}", first_name="Kavita", last_name="Iyer",
            email=f"kavita.{uid}@example.com", phone=f"+9198333{uid[:5]}", lifecycle_status="ACTIVE",
            project_eligible=True, updated_at=old_time, created_at=old_time
        )
        session.add(c_overdue)
        await session.flush()

        enr = Enrollment(id=uuid.uuid4(), candidate_id=c_overdue.id, batch_id=batch.id, enrollment_status="ACTIVE")
        session.add(enr)
        await session.commit()
        track_id = str(track.id)

    resp = await async_client.get(f"/api/v1/projects/queue?track_id={track_id}", **auth)
    assert resp.status_code == 200
    q_data = resp.json()
    assert q_data["total"] >= 1
    item = next(i for i in q_data["items"] if i["candidate_number"] == f"EX-Q1-{uid}")
    assert item["is_overdue_15_days"] is True
    assert item["business_days_in_queue"] >= 16


@pytest.mark.asyncio
async def test_dropped_project_requires_reason_and_preserves_history(async_client: AsyncClient):
    """
    BRD Part 7: Dropped project workflow must enforce mandatory reason,
    set status to DROPPED, preserve allocation record, and not grant completion credit.
    """
    auth = await login_as_admin(async_client)
    uid = uuid.uuid4().hex[:6]

    session_factory = get_session_factory()
    async with session_factory() as session:
        course = Course(id=uuid.uuid4(), code=f"CRS-DRP-{uid}", title="Drop Course", is_active=True)
        session.add(course)
        await session.flush()

        track = CourseTrack(
            id=uuid.uuid4(), course_id=course.id, code=f"TRK-DRP-{uid}",
            title="Drop Track", total_mandatory_assignments=1, total_required_projects=1, is_active=True
        )
        session.add(track)
        await session.flush()

        batch = Batch(id=uuid.uuid4(), track_id=track.id, batch_code=f"B-DRP-{uid}", title="Drop Batch", start_date=date.today())
        session.add(batch)
        await session.flush()

        cand = Candidate(
            id=uuid.uuid4(), candidate_number=f"EX-DRP-{uid}", first_name="Vikram", last_name="Seth",
            email=f"vikram.{uid}@example.com", phone=f"+9198444{uid[:5]}", lifecycle_status="ACTIVE", project_eligible=True
        )
        session.add(cand)
        await session.flush()

        project = Project(
            id=uuid.uuid4(), track_id=track.id, code=f"PRJ-DRP-{uid}", title="Capstone Spec",
            tier="TIER_1_FOUNDATIONAL", complexity="INTERMEDIATE", passing_score=70.0, is_active=True
        )
        session.add(project)
        await session.flush()

        group = ProjectGroup(
            id=uuid.uuid4(), batch_id=batch.id, project_id=project.id,
            group_name=f"Group-Drop-{uid}", group_status="ACTIVE", readiness_status="NOT_READY",
            min_size=1, target_size=2, max_size=4
        )
        session.add(group)
        await session.flush()

        member = ProjectGroupMember(id=uuid.uuid4(), group_id=group.id, candidate_id=cand.id, role="LEADER", status="ACTIVE")
        session.add(member)
        await session.flush()

        alloc = ProjectAllocation(
            id=uuid.uuid4(), group_id=group.id, project_id=project.id,
            tier="TIER_1_FOUNDATIONAL", status="ALLOCATED", allocated_at=utc_now()
        )
        session.add(alloc)
        await session.commit()
        group_id = str(group.id)
        alloc_id = str(alloc.id)

    # 1. Drop without reason -> MUST FAIL with 422
    resp_empty = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocations/{alloc_id}/drop",
        json={"reason": "   "},
        **auth,
    )
    assert resp_empty.status_code == 422

    # 2. Drop with valid reason -> MUST SUCCEED with 200
    resp_ok = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocations/{alloc_id}/drop",
        json={"reason": "Candidate relocated for family emergency; unable to complete deliverables."},
        **auth,
    )
    assert resp_ok.status_code == 200

    # 3. Verify allocation status is DROPPED and candidate completed_projects_count remains 0
    async with session_factory() as session:
        alloc_check = (await session.execute(select(ProjectAllocation).where(ProjectAllocation.id == uuid.UUID(alloc_id)))).scalar_one()
        assert alloc_check.status == "DROPPED"
        cand_check = (await session.execute(select(Candidate).where(Candidate.id == cand.id))).scalar_one()
        assert cand_check.completed_projects_count == 0


@pytest.mark.asyncio
async def test_nasscom_clearance_gate_for_data_analytics():
    """
    BRD Part 8: NASSCOM clearance cannot be inferred from assignment completion.
    Data Analytics, Business Analytics, and Data Science tracks require verified NASSCOM clearance.
    """
    uid = uuid.uuid4().hex[:6]
    session_factory = get_session_factory()
    async with session_factory() as session:
        admin_user = (await session.execute(select(User).where(User.email == "admin@excelr.com"))).scalar_one()

        course = Course(id=uuid.uuid4(), code=f"CRS-DA-{uid}", title="Data Analytics Masters", is_active=True)
        session.add(course)
        await session.flush()

        track = CourseTrack(
            id=uuid.uuid4(), course_id=course.id, code=f"DA-{uid}",
            title="Data Analytics Professional Track", total_mandatory_assignments=1, total_required_projects=1, is_active=True
        )
        session.add(track)
        await session.flush()

        batch = Batch(id=uuid.uuid4(), track_id=track.id, batch_code=f"B-DA-{uid}", title="DA Batch", start_date=date.today())
        session.add(batch)
        await session.flush()

        # Candidate with completed assignments & project, but NO NASSCOM clearance
        cand = Candidate(
            id=uuid.uuid4(), candidate_number=f"EX-DA-{uid}", first_name="Deepa", last_name="Menon",
            email=f"deepa.{uid}@example.com", phone=f"+9198555{uid[:5]}", lifecycle_status="ACTIVE",
            project_eligible=True, completed_projects_count=1
        )
        session.add(cand)
        await session.flush()

        enr = Enrollment(id=uuid.uuid4(), candidate_id=cand.id, batch_id=batch.id, enrollment_status="ACTIVE")
        session.add(enr)
        await session.commit()
        cand_id = cand.id
        track_id = track.id
        admin_id = admin_user.id

    # Calculate eligibility without NASSCOM clearance
    async with session_factory() as session:
        diag = await CertificateService.calculate_candidate_eligibility(
            db=session, candidate_id=cand_id, track_id=track_id
        )
        assert diag.is_eligible is False
        assert any("NASSCOM" in r for r in diag.ineligibility_reasons)

        # Now record verified NASSCOM clearance in candidate notes
        note = CandidateNote(
            id=uuid.uuid4(), candidate_id=cand_id, author_id=admin_id,
            note_category="ACADEMIC", note_text="NASSCOM assessment CLEARED with score 88% on 2026-10-25"
        )
        session.add(note)
        await session.commit()

        # Re-evaluate eligibility with NASSCOM clearance recorded
        diag_cleared = await CertificateService.calculate_candidate_eligibility(
            db=session, candidate_id=cand_id, track_id=track_id
        )
        # NASSCOM blocker is resolved
        assert not any("NASSCOM" in r for r in diag_cleared.ineligibility_reasons)
