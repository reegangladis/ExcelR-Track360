"""
ExcelR Track360 - Assignment Management Test Suite
Phase 6 Verification:
1. Assignment template CRUD & rubric scoring definitions
2. Validation rules (passing_score <= max_score, unique code)
3. Allocation to batch and candidate targets
4. Duplicate allocation rejection & date bounds checking
5. RBAC permission guards (assignment:template_manage, assignment:allocate)
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
from app.modules.auth.models import User, Role, UserRole
from app.modules.auth.seed import seed_bootstrap_admin
from app.modules.candidates.models import Course, CourseTrack, Batch, Candidate
from app.modules.assignments.models import Assignment, AssignmentAllocation


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


async def create_course_track_and_batch(async_client: AsyncClient, admin_auth: dict):
    """Helper to provision course track and batch for allocation tests."""
    uid = uuid.uuid4().hex[:6]
    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": f"CRS_{uid}", "title": "Data Science"},
        **admin_auth,
    )
    assert c_resp.status_code == 200
    course_id = c_resp.json()["id"]

    t_resp = await async_client.post(
        "/api/v1/courses/tracks",
        json={"course_id": course_id, "code": f"TRK_{uid}", "title": "Core Track"},
        **admin_auth,
    )
    assert t_resp.status_code == 200
    track_id = t_resp.json()["id"]

    b_resp = await async_client.post(
        "/api/v1/batches",
        json={
            "track_id": track_id,
            "batch_code": f"BAT_{uid}",
            "title": f"Cohort {uid}",
            "start_date": "2026-02-01",
        },
        **admin_auth,
    )
    assert b_resp.status_code == 200
    batch_id = b_resp.json()["id"]

    return track_id, batch_id


@pytest.mark.asyncio
async def test_assignment_template_crud_and_validation(async_client: AsyncClient):
    """Verifies creation, rubric JSON structure, score bounds validation, and update."""
    admin_auth = await login_as_admin(async_client)
    track_id, _ = await create_course_track_and_batch(async_client, admin_auth)

    uid = uuid.uuid4().hex[:6]
    code = f"ASG_PY_{uid}"

    # 1. Validation failure: passing_score > max_score
    invalid_resp = await async_client.post(
        "/api/v1/assignments",
        json={
            "track_id": track_id,
            "code": code,
            "title": "Python Basics Assignment",
            "instructions_markdown": "Complete all exercises in the notebook.",
            "max_score": 50.0,
            "passing_score": 60.0,
        },
        **admin_auth,
    )
    assert invalid_resp.status_code == 422

    # 2. Valid Assignment Creation with Rubric Template
    rubric = [
        {"key": "code_quality", "title": "Code Structure & PEP8", "max_points": 30.0},
        {"key": "correctness", "title": "Test Case Pass Rate", "max_points": 50.0},
        {"key": "docs", "title": "Markdown Documentation", "max_points": 20.0},
    ]
    create_resp = await async_client.post(
        "/api/v1/assignments",
        json={
            "track_id": track_id,
            "code": code,
            "title": "Python Basics Assignment",
            "instructions_markdown": "# Assignment 1\nComplete the exercises and submit a zip/ipynb file.",
            "sequence_order": 1,
            "is_mandatory": True,
            "max_score": 100.0,
            "passing_score": 60.0,
            "rubric_template": rubric,
            "allowed_file_types": ["ipynb", "zip", "pdf"],
            "max_file_size_mb": 20,
        },
        **admin_auth,
    )
    assert create_resp.status_code == 201
    asg_data = create_resp.json()
    assignment_id = asg_data["id"]
    assert asg_data["code"] == code.upper()
    assert len(asg_data["rubric_template"]) == 3
    assert asg_data["is_mandatory"] is True

    # 3. Duplicate code rejection (409 Conflict)
    dup_resp = await async_client.post(
        "/api/v1/assignments",
        json={
            "track_id": track_id,
            "code": code,
            "title": "Another Assignment",
            "instructions_markdown": "Some instructions.",
        },
        **admin_auth,
    )
    assert dup_resp.status_code == 409
    assert "already exists" in dup_resp.json()["detail"]

    # 4. Get Assignment by ID
    get_resp = await async_client.get(f"/api/v1/assignments/{assignment_id}", **admin_auth)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == assignment_id

    # 5. Update Assignment (Patch title & max_score)
    patch_resp = await async_client.patch(
        f"/api/v1/assignments/{assignment_id}",
        json={"title": "Updated Python Foundations", "max_score": 90.0, "passing_score": 55.0},
        **admin_auth,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated Python Foundations"
    assert patch_resp.json()["max_score"] == 90.0


@pytest.mark.asyncio
async def test_assignment_list_and_search(async_client: AsyncClient):
    """Verifies assignment list querying, search filter, and pagination."""
    admin_auth = await login_as_admin(async_client)
    track_id, _ = await create_course_track_and_batch(async_client, admin_auth)

    uid = uuid.uuid4().hex[:6]
    for i in range(3):
        await async_client.post(
            "/api/v1/assignments",
            json={
                "track_id": track_id,
                "code": f"SEARCH_{uid}_{i}",
                "title": f"Searchable Assignment Module {i}",
                "instructions_markdown": "Instructions here...",
                "sequence_order": i + 1,
            },
            **admin_auth,
        )

    # Search by code prefix
    list_resp = await async_client.get(
        f"/api/v1/assignments?search=SEARCH_{uid}",
        **admin_auth,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 3

    # Filter by track
    track_filter_resp = await async_client.get(
        f"/api/v1/assignments?track_id={track_id}",
        **admin_auth,
    )
    assert track_filter_resp.status_code == 200
    assert len(track_filter_resp.json()["items"]) >= 3


@pytest.mark.asyncio
async def test_assignment_allocation_to_batch_and_candidate(async_client: AsyncClient):
    """Verifies allocation to batch and candidate, duplicate guards, and date validation."""
    admin_auth = await login_as_admin(async_client)
    track_id, batch_id = await create_course_track_and_batch(async_client, admin_auth)

    uid = uuid.uuid4().hex[:6]
    # Create Assignment
    asg_resp = await async_client.post(
        "/api/v1/assignments",
        json={
            "track_id": track_id,
            "code": f"ALLOC_{uid}",
            "title": f"Allocation Test Assignment {uid}",
            "instructions_markdown": "Solve problems and submit.",
        },
        **admin_auth,
    )
    assert asg_resp.status_code == 201
    assignment_id = asg_resp.json()["id"]

    now = datetime.now(timezone.utc)
    due_date = now + timedelta(days=7)
    grace_date = due_date + timedelta(days=2)

    # 1. Date Validation: Grace period preceding due date rejected
    bad_dates_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": assignment_id,
            "batch_id": batch_id,
            "due_date_utc": due_date.isoformat(),
            "grace_period_end_utc": (due_date - timedelta(days=1)).isoformat(),
        },
        **admin_auth,
    )
    assert bad_dates_resp.status_code == 422

    # 2. Allocate to Batch
    alloc_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": assignment_id,
            "batch_id": batch_id,
            "due_date_utc": due_date.isoformat(),
            "grace_period_end_utc": grace_date.isoformat(),
        },
        **admin_auth,
    )
    assert alloc_resp.status_code == 201
    alloc_data = alloc_resp.json()
    assert alloc_data["assignment_id"] == assignment_id
    assert alloc_data["batch_id"] == batch_id
    assert alloc_data["allocation_status"] == "PENDING"

    # 3. Duplicate allocation to same batch blocked (409 Conflict)
    dup_alloc_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": assignment_id,
            "batch_id": batch_id,
            "due_date_utc": due_date.isoformat(),
        },
        **admin_auth,
    )
    assert dup_alloc_resp.status_code == 409
    assert "already allocated" in dup_alloc_resp.json()["detail"]

    # 4. Create Candidate & Allocate to Candidate Directly
    cand_resp = await async_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Alice",
            "last_name": "Test",
            "email": f"alice_{uid}@example.com",
            "phone": f"+9198{uuid.uuid4().int % 100000000:08d}",
            "batch_id": batch_id,
        },
        **admin_auth,
    )
    assert cand_resp.status_code == 201
    candidate_id = cand_resp.json()["id"]

    cand_alloc_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": assignment_id,
            "candidate_id": candidate_id,
            "due_date_utc": due_date.isoformat(),
        },
        **admin_auth,
    )
    assert cand_alloc_resp.status_code == 201
    assert cand_alloc_resp.json()["candidate_id"] == candidate_id

    # 5. Duplicate candidate allocation blocked (409 Conflict)
    dup_cand_resp = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": assignment_id,
            "candidate_id": candidate_id,
            "due_date_utc": due_date.isoformat(),
        },
        **admin_auth,
    )
    assert dup_cand_resp.status_code == 409


@pytest.mark.asyncio
async def test_assignment_rbac_and_permission_isolation(async_client: AsyncClient):
    """Verifies that users without assignment:template_manage or assignment:allocate are blocked with 403."""
    admin_auth = await login_as_admin(async_client)
    track_id, batch_id = await create_course_track_and_batch(async_client, admin_auth)

    # 1. Register a student user without staff permissions
    student_email = f"student_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "Student@123456_Track!"

    # Create candidate and user
    c_resp = await async_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Bob",
            "last_name": "Learner",
            "email": student_email,
            "phone": f"+9197{uuid.uuid4().int % 100000000:08d}",
            "batch_id": batch_id,
        },
        **admin_auth,
    )
    assert c_resp.status_code == 201

    session_factory = get_session_factory()
    from app.core.security import hash_password

    async with session_factory() as session:
        # Create student user
        user = User(
            id=uuid.uuid4(),
            email=student_email,
            password_hash=hash_password(pwd),
            full_name="Bob Learner",
            status="ACTIVE",
            is_verified=True,
        )
        session.add(user)
        await session.flush()

        role_res = await session.execute(select(Role).where(Role.code == "ROLE_STUDENT"))
        role = role_res.scalar_one()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()

    # Login as student
    stud_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": student_email, "password": pwd},
    )
    assert stud_login.status_code == 200
    stud_csrf = stud_login.json()["csrf_token"]
    stud_session = stud_login.cookies[SESSION_COOKIE_NAME]
    stud_auth = {
        "cookies": {SESSION_COOKIE_NAME: stud_session, CSRF_COOKIE_NAME: stud_csrf},
        "headers": {"x-csrf-token": stud_csrf},
    }

    # Student cannot create an assignment template (403 Forbidden)
    stud_create = await async_client.post(
        "/api/v1/assignments",
        json={
            "track_id": track_id,
            "code": f"STUD_ASG_{uuid.uuid4().hex[:4]}",
            "title": "Hacked Assignment",
            "instructions_markdown": "Should be rejected.",
        },
        **stud_auth,
    )
    assert stud_create.status_code == 403

    # Student cannot allocate an assignment (403 Forbidden)
    stud_alloc = await async_client.post(
        "/api/v1/assignments/allocations",
        json={
            "assignment_id": str(uuid.uuid4()),
            "batch_id": batch_id,
            "due_date_utc": datetime.now(timezone.utc).isoformat(),
        },
        **stud_auth,
    )
    assert stud_alloc.status_code == 403
