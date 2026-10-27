"""
ExcelR Track360 - Assignment Submission & Review Test Suite
Phase 7 Verification:
1. Deliverable upload & attempt versioning (immutable history)
2. Authoritative server UTC timestamping & lateness delta
3. Rubric evaluation & passing score threshold enforcement
4. Corrections request and Attempt N+1 resubmission
5. Prerequisite gating (100% mandatory assignments -> project_eligible = True)
6. IDOR protection: Student cannot access peer submissions
"""
from datetime import datetime, timedelta, timezone
import io
from typing import Tuple
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.core.security import hash_password
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
from app.modules.auth.models import User, Role, UserRole
from app.modules.auth.seed import seed_bootstrap_admin
from app.modules.candidates.models import Course, CourseTrack, Batch, Candidate, Enrollment
from app.modules.assignments.models import Assignment, AssignmentAllocation, AssignmentSubmission


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Seeds default admin before tests."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed_bootstrap_admin(
            db=session,
            email="admin@excelr.com",
            password="Admin@Track360_2026!",
            full_name="Master Administrator",
        )


async def login_as_admin(async_client: AsyncClient) -> dict:
    """Helper returning auth cookies and headers for Super Admin."""
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


async def provision_student_account(
    async_client: AsyncClient, admin_auth: dict, batch_id: uuid.UUID
) -> Tuple[dict, uuid.UUID, uuid.UUID]:
    """Provisions a student user linked to a candidate enrolled in batch_id."""
    uid = uuid.uuid4().hex[:6]
    email = f"student_{uid}@example.com"
    pwd = "Student@123456_Secure!"

    # 1. Create candidate record
    cand_resp = await async_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Student",
            "last_name": f"User_{uid}",
            "email": email,
            "phone": f"+9198{uuid.uuid4().int % 100000000:08d}",
            "batch_id": str(batch_id),
        },
        **admin_auth,
    )
    assert cand_resp.status_code == 201
    candidate_id = uuid.UUID(cand_resp.json()["id"])

    # 2. Create User account & link candidate.user_id
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(pwd),
            full_name=f"Student User {uid}",
            status="ACTIVE",
            is_verified=True,
        )
        session.add(user)
        await session.flush()

        role_res = await session.execute(select(Role).where(Role.code == "ROLE_STUDENT"))
        role = role_res.scalar_one()
        session.add(UserRole(user_id=user.id, role_id=role.id))

        # Link candidate to user
        cand = (await session.execute(select(Candidate).where(Candidate.id == candidate_id))).scalar_one()
        cand.user_id = user.id
        await session.commit()
        user_id = user.id

    # 3. Login as student
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert login_resp.status_code == 200
    csrf = login_resp.json()["csrf_token"]
    session_token = login_resp.cookies[SESSION_COOKIE_NAME]
    student_auth = {
        "cookies": {SESSION_COOKIE_NAME: session_token, CSRF_COOKIE_NAME: csrf},
        "headers": {"x-csrf-token": csrf},
    }
    return student_auth, candidate_id, user_id


async def provision_assignment_and_cohort(async_client: AsyncClient, admin_auth: dict):
    """Sets up course, track, batch, and assignment template for submissions."""
    uid = uuid.uuid4().hex[:6]
    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": f"CRS_{uid}", "title": "Data Engineering"},
        **admin_auth,
    )
    course_id = c_resp.json()["id"]

    t_resp = await async_client.post(
        "/api/v1/courses/tracks",
        json={"course_id": course_id, "code": f"TRK_{uid}", "title": "Big Data Track"},
        **admin_auth,
    )
    track_id = t_resp.json()["id"]

    b_resp = await async_client.post(
        "/api/v1/batches",
        json={
            "track_id": track_id,
            "batch_code": f"BAT_{uid}",
            "title": f"Cohort {uid}",
            "start_date": "2026-03-01",
        },
        **admin_auth,
    )
    batch_id = uuid.UUID(b_resp.json()["id"])

    # Create assignment with rubric
    asg_resp = await async_client.post(
        "/api/v1/assignments",
        json={
            "track_id": track_id,
            "code": f"ASG_BD_{uid}",
            "title": "Spark ETL Pipeline",
            "instructions_markdown": "# Assignment\nWrite PySpark transformations.",
            "sequence_order": 1,
            "is_mandatory": True,
            "max_score": 100.0,
            "passing_score": 60.0,
            "rubric_template": [
                {"key": "syntax", "title": "PySpark Syntax", "max_points": 40.0},
                {"key": "correctness", "title": "ETL Output Integrity", "max_points": 60.0},
            ],
            "allowed_file_types": ["zip", "ipynb", "pdf"],
            "max_file_size_mb": 15,
        },
        **admin_auth,
    )
    assignment_id = uuid.UUID(asg_resp.json()["id"])
    return track_id, batch_id, assignment_id


@pytest.mark.asyncio
async def test_assignment_submission_lifecycle(async_client: AsyncClient):
    """Verifies deliverable upload, checksum calculation, attempt versioning, and status update."""
    admin_auth = await login_as_admin(async_client)
    track_id, batch_id, assignment_id = await provision_assignment_and_cohort(async_client, admin_auth)
    student_auth, candidate_id, _ = await provision_student_account(async_client, admin_auth, batch_id)

    # 1. Allocate to Cohort Batch (Due date in 7 days)
    now = datetime.now(timezone.utc)
    alloc_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": str(assignment_id),
            "batch_id": str(batch_id),
            "due_date_utc": (now + timedelta(days=7)).isoformat(),
        },
        **admin_auth,
    )
    assert alloc_resp.status_code == 201
    allocation_id = alloc_resp.json()["id"]

    # 2. Student Submits Deliverable (Attempt 1)
    file_bytes = b"def test_solution(): pass\nprint('hello track360')"
    submit_resp = await async_client.post(
        f"/api/v1/assignments/allocations/{allocation_id}/submit",
        files={"file": ("solution.ipynb", io.BytesIO(file_bytes), "application/x-ipynb+json")},
        data={"repository_url": "https://github.com/student/etl-pipeline", "student_notes": "Completed exercises 1 to 5."},
        **student_auth,
    )
    assert submit_resp.status_code == 201
    attempt_data = submit_resp.json()
    assert attempt_data["attempt_number"] == 1
    assert attempt_data["is_late"] is False
    assert attempt_data["lateness_minutes"] == 0
    assert attempt_data["original_filename"] == "solution.ipynb"
    assert attempt_data["repository_url"] == "https://github.com/student/etl-pipeline"

    # 3. Verify Submission Record Created & Queryable
    list_resp = await async_client.get("/api/v1/assignments/submissions", **student_auth)
    assert list_resp.status_code == 200
    subs = list_resp.json()["items"]
    assert len(subs) == 1
    assert subs[0]["current_submission_status"] == "SUBMITTED"
    assert subs[0]["total_attempts"] == 1


@pytest.mark.asyncio
async def test_assignment_lateness_delta_calculation(async_client: AsyncClient):
    """Verifies that past-due submissions are automatically marked is_late=True with lateness minutes."""
    admin_auth = await login_as_admin(async_client)
    track_id, batch_id, assignment_id = await provision_assignment_and_cohort(async_client, admin_auth)
    student_auth, candidate_id, _ = await provision_student_account(async_client, admin_auth, batch_id)

    # 1. Allocate with Due Date 2 hours in the past, Grace Period in 2 days
    now = datetime.now(timezone.utc)
    due_date = now - timedelta(hours=2)
    grace_date = now + timedelta(days=2)

    alloc_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": str(assignment_id),
            "batch_id": str(batch_id),
            "due_date_utc": due_date.isoformat(),
            "grace_period_end_utc": grace_date.isoformat(),
        },
        **admin_auth,
    )
    assert alloc_resp.status_code == 201
    allocation_id = alloc_resp.json()["id"]

    # 2. Student Submits
    submit_resp = await async_client.post(
        f"/api/v1/assignments/allocations/{allocation_id}/submit",
        data={"repository_url": "https://github.com/student/late-repo"},
        **student_auth,
    )
    assert submit_resp.status_code == 201
    attempt = submit_resp.json()
    assert attempt["is_late"] is True
    assert attempt["lateness_minutes"] >= 115  # Approx 120 minutes late

    # 3. Check list status is LATE_SUBMITTED
    list_resp = await async_client.get("/api/v1/assignments/submissions", **student_auth)
    assert list_resp.status_code == 200
    assert list_resp.json()["items"][0]["current_submission_status"] == "LATE_SUBMITTED"


@pytest.mark.asyncio
async def test_assignment_evaluation_and_rubric_scoring(async_client: AsyncClient):
    """Verifies evaluator review, passing score threshold enforcement, and rubric items."""
    admin_auth = await login_as_admin(async_client)
    track_id, batch_id, assignment_id = await provision_assignment_and_cohort(async_client, admin_auth)
    student_auth, candidate_id, _ = await provision_student_account(async_client, admin_auth, batch_id)

    # Allocate & Submit
    alloc_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": str(assignment_id),
            "batch_id": str(batch_id),
            "due_date_utc": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        **admin_auth,
    )
    allocation_id = alloc_resp.json()["id"]

    await async_client.post(
        f"/api/v1/assignments/allocations/{allocation_id}/submit",
        data={"repository_url": "https://github.com/student/test-repo"},
        **student_auth,
    )

    # Get submission ID from list
    list_resp = await async_client.get("/api/v1/assignments/submissions", **admin_auth)
    submission_id = list_resp.json()["items"][0]["id"]

    # 1. Invalid Review: Score below passing threshold (Passing is 60.0, awarding 50.0) -> Rejection with 422
    fail_review_resp = await async_client.post(
        f"/api/v1/assignments/submissions/{submission_id}/review",
        json={
            "review_outcome": "APPROVED",
            "qualitative_feedback": "Decent effort but incomplete.",
            "rubric_scores": [
                {"criterion_key": "syntax", "criterion_title": "PySpark Syntax", "max_points": 40.0, "awarded_points": 25.0},
                {"criterion_key": "correctness", "criterion_title": "ETL Output Integrity", "max_points": 60.0, "awarded_points": 25.0},
            ],
        },
        **admin_auth,
    )
    assert fail_review_resp.status_code == 422
    assert "below the required passing threshold" in fail_review_resp.json()["detail"]

    # 2. Valid Approval: Score 85.0 >= 60.0
    pass_review_resp = await async_client.post(
        f"/api/v1/assignments/submissions/{submission_id}/review",
        json={
            "review_outcome": "APPROVED",
            "qualitative_feedback": "Excellent data pipeline implementation with clean transformations.",
            "rubric_scores": [
                {"criterion_key": "syntax", "criterion_title": "PySpark Syntax", "max_points": 40.0, "awarded_points": 35.0},
                {"criterion_key": "correctness", "criterion_title": "ETL Output Integrity", "max_points": 60.0, "awarded_points": 50.0},
            ],
        },
        **admin_auth,
    )
    assert pass_review_resp.status_code == 201
    rev_data = pass_review_resp.json()
    assert rev_data["review_outcome"] == "APPROVED"
    assert rev_data["total_score"] == 85.0
    assert len(rev_data["rubric_scores"]) == 2

    # 3. Verify submission detail reflects PASSED_COMPLETED
    detail_resp = await async_client.get(f"/api/v1/assignments/submissions/{submission_id}", **student_auth)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["current_submission_status"] == "APPROVED"
    assert detail_resp.json()["current_completion_status"] == "PASSED_COMPLETED"
    assert detail_resp.json()["latest_score"] == 85.0


@pytest.mark.asyncio
async def test_resubmission_on_corrections_requested(async_client: AsyncClient):
    """Verifies that feedback requesting corrections allows attempt N+1 while preserving attempt 1 immutably."""
    admin_auth = await login_as_admin(async_client)
    track_id, batch_id, assignment_id = await provision_assignment_and_cohort(async_client, admin_auth)
    student_auth, candidate_id, _ = await provision_student_account(async_client, admin_auth, batch_id)

    alloc_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": str(assignment_id),
            "batch_id": str(batch_id),
            "due_date_utc": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        **admin_auth,
    )
    allocation_id = alloc_resp.json()["id"]

    # Attempt 1
    await async_client.post(
        f"/api/v1/assignments/allocations/{allocation_id}/submit",
        data={"repository_url": "https://github.com/student/v1"},
        **student_auth,
    )

    list_resp = await async_client.get("/api/v1/assignments/submissions", **admin_auth)
    submission_id = list_resp.json()["items"][0]["id"]

    # Reviewer requests rework
    await async_client.post(
        f"/api/v1/assignments/submissions/{submission_id}/review",
        json={
            "review_outcome": "CORRECTIONS_REQUESTED",
            "qualitative_feedback": "Please fix partition performance.",
            "rubric_scores": [
                {"criterion_key": "syntax", "criterion_title": "PySpark Syntax", "max_points": 40.0, "awarded_points": 20.0},
                {"criterion_key": "correctness", "criterion_title": "ETL Output Integrity", "max_points": 60.0, "awarded_points": 20.0},
            ],
        },
        **admin_auth,
    )

    # Attempt 2 Resubmission
    sub2_resp = await async_client.post(
        f"/api/v1/assignments/allocations/{allocation_id}/submit",
        data={"repository_url": "https://github.com/student/v2_fixed", "student_notes": "Optimized partitions."},
        **student_auth,
    )
    assert sub2_resp.status_code == 201
    assert sub2_resp.json()["attempt_number"] == 2

    # Verify Detail has both Attempt 1 and Attempt 2
    detail_resp = await async_client.get(f"/api/v1/assignments/submissions/{submission_id}", **student_auth)
    assert detail_resp.status_code == 200
    attempts = detail_resp.json()["attempts"]
    assert len(attempts) == 2
    assert attempts[0]["attempt_number"] == 1
    assert attempts[1]["attempt_number"] == 2
    assert attempts[0]["reviews"][0]["review_outcome"] == "CORRECTIONS_REQUESTED"


@pytest.mark.asyncio
async def test_prerequisite_gating_project_eligibility(async_client: AsyncClient):
    """Verifies that 100% mandatory assignment approval automatically sets candidate.project_eligible = True."""
    admin_auth = await login_as_admin(async_client)
    track_id, batch_id, assignment_id = await provision_assignment_and_cohort(async_client, admin_auth)
    student_auth, candidate_id, _ = await provision_student_account(async_client, admin_auth, batch_id)

    # Verify initial candidate status: project_eligible == False
    c_detail = await async_client.get(f"/api/v1/candidates/{candidate_id}", **admin_auth)
    assert c_detail.json()["project_eligible"] is False

    # Allocate & Submit
    alloc_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": str(assignment_id),
            "batch_id": str(batch_id),
            "due_date_utc": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        **admin_auth,
    )
    allocation_id = alloc_resp.json()["id"]

    await async_client.post(
        f"/api/v1/assignments/allocations/{allocation_id}/submit",
        data={"repository_url": "https://github.com/student/mandatory-repo"},
        **student_auth,
    )

    list_resp = await async_client.get("/api/v1/assignments/submissions", **admin_auth)
    submission_id = list_resp.json()["items"][0]["id"]

    # Reviewer approves submission
    await async_client.post(
        f"/api/v1/assignments/submissions/{submission_id}/review",
        json={
            "review_outcome": "APPROVED",
            "qualitative_feedback": "Perfect job, passing grade.",
            "rubric_scores": [
                {"criterion_key": "syntax", "criterion_title": "PySpark Syntax", "max_points": 40.0, "awarded_points": 40.0},
                {"criterion_key": "correctness", "criterion_title": "ETL Output Integrity", "max_points": 60.0, "awarded_points": 60.0},
            ],
        },
        **admin_auth,
    )

    # Candidate should now be project_eligible == True! (BR-PRJ-01 satisfied)
    c_after = await async_client.get(f"/api/v1/candidates/{candidate_id}", **admin_auth)
    assert c_after.json()["project_eligible"] is True


@pytest.mark.asyncio
async def test_submission_idor_protection(async_client: AsyncClient):
    """Verifies that Student A cannot access Student B's submission (HTTP 403 Forbidden)."""
    admin_auth = await login_as_admin(async_client)
    track_id, batch_id, assignment_id = await provision_assignment_and_cohort(async_client, admin_auth)

    student_a_auth, _, _ = await provision_student_account(async_client, admin_auth, batch_id)
    student_b_auth, _, _ = await provision_student_account(async_client, admin_auth, batch_id)

    alloc_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": str(assignment_id),
            "batch_id": str(batch_id),
            "due_date_utc": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        **admin_auth,
    )
    allocation_id = alloc_resp.json()["id"]

    # Student A submits
    await async_client.post(
        f"/api/v1/assignments/allocations/{allocation_id}/submit",
        data={"repository_url": "https://github.com/studentA/repo"},
        **student_a_auth,
    )

    list_resp = await async_client.get("/api/v1/assignments/submissions", **admin_auth)
    sub_a_id = list_resp.json()["items"][0]["id"]

    # Student B attempts to inspect Student A's submission -> 403 Forbidden
    idor_resp = await async_client.get(f"/api/v1/assignments/submissions/{sub_a_id}", **student_b_auth)
    assert idor_resp.status_code == 403
    assert "Forbidden" in idor_resp.json()["detail"]
