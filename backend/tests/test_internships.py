"""
ExcelR Track360 - Phase 11: Internship Lifecycle & Milestone Progression Test Suite
Strictly verifies:
1. BR-INT-01 Decoupling of Internship Lifecycle from Certificate Duration
2. BR-INT-02 Configurable Project-to-Internship Duration Policy (1 PRJ=3m, 2 PRJ=6m, 3 PRJ=9m)
3. FR-INT-001 Internship Eligibility Calculation & Candidate Diagnostic Check
4. FR-INT-002 Internship Record Initialization, Calendar Tracking & Company Mapping
5. Duplicate Active Record Prevention (Unique candidate_id + track_id constraint)
6. Calendar Date Validation (expected_end_date >= start_date)
7. Operational Calendar Updates via PATCH
8. Verified Internship Completion Workflow (Sets actual_completion_date & ACHIEVED status)
9. Termination with Mandatory Explanation Requirement
10. RBAC Boundaries & Student IDOR Protection
"""
import uuid
from datetime import date, timedelta
from typing import Tuple, List
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
from app.modules.auth.models import Role, User, UserRole
from app.modules.auth.seed import seed_bootstrap_admin
from app.modules.candidates.models import Batch, Candidate, Course, CourseTrack
from app.modules.projects.models import Project, ProjectMilestone, ProjectGroup, ProjectGroupMember, ProjectGroupSubmission
from app.modules.internships.models import InternshipRecord, InternshipMilestone


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


async def create_user_with_role(
    async_client: AsyncClient,
    email: str,
    password: str,
    full_name: str,
    role_code: str,
) -> dict:
    """Creates a user with a specific platform role and returns credentials."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        role_res = await session.execute(select(Role).where(Role.code == role_code))
        role = role_res.scalars().first()
        assert role is not None, f"Role {role_code} not found in database"

        from app.core.security import hash_password
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            status="ACTIVE",
            is_verified=True,
        )
        session.add(user)
        await session.flush()

        ur = UserRole(user_id=user.id, role_id=role.id)
        session.add(ur)
        await session.commit()

    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    csrf = resp.json()["csrf_token"]
    session_token = resp.cookies[SESSION_COOKIE_NAME]
    return {
        "user_id": user.id,
        "auth": {
            "cookies": {SESSION_COOKIE_NAME: session_token, CSRF_COOKIE_NAME: csrf},
            "headers": {"x-csrf-token": csrf},
        },
    }


async def provision_batch_and_track() -> Tuple[uuid.UUID, uuid.UUID]:
    """Provisions a course, track, and cohort batch."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        uid = uuid.uuid4().hex[:6]
        course = Course(
            id=uuid.uuid4(),
            code=f"CRS_INT_{uid}",
            title=f"Data Analytics & AI {uid}",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        track = CourseTrack(
            id=uuid.uuid4(),
            course_id=course.id,
            code=f"TRK_INT_{uid}",
            title=f"Applied Data Science Track {uid}",
            total_mandatory_assignments=2,
            total_required_projects=3,
            is_active=True,
        )
        session.add(track)
        await session.flush()

        batch = Batch(
            id=uuid.uuid4(),
            track_id=track.id,
            batch_code=f"BATCH-INT-{uid}",
            title=f"Analytics Cohort {uid}",
            start_date=date(2026, 11, 1),
            status="ACTIVE",
        )
        session.add(batch)
        await session.commit()
        return batch.id, track.id


async def provision_candidate(
    async_client: AsyncClient, admin_auth: dict, batch_id: uuid.UUID, user_id: uuid.UUID = None
) -> uuid.UUID:
    """Provisions a single candidate in the batch."""
    uid = uuid.uuid4().hex[:6]
    cand_payload = {
        "first_name": "Intern",
        "last_name": f"Candidate{uid}",
        "email": f"intern_{uid}@excelr.com",
        "phone": f"+9198{uuid.uuid4().int % 100000000:08d}",
        "batch_id": str(batch_id),
    }
    res = await async_client.post(
        "/api/v1/candidates",
        json=cand_payload,
        **admin_auth,
    )
    assert res.status_code == 201, f"Failed to provision candidate: {res.text}"
    cand_id = uuid.UUID(res.json()["id"])

    if user_id:
        session_factory = get_session_factory()
        async with session_factory() as session:
            cand = await session.get(Candidate, cand_id)
            cand.user_id = user_id
            await session.commit()

    return cand_id


@pytest.mark.asyncio
async def test_internship_initialization_and_calendar_decoupling(async_client: AsyncClient):
    """
    Verifies BR-INT-01: Decoupling of Internship Lifecycle from Certificate Duration.
    Calendar dates (start_date, expected_end_date) are distinct operational entities
    from accredited milestone duration (3 months baseline).
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    candidate_id = await provision_candidate(async_client, admin_auth, batch_id)

    # Initialize formal internship record
    start_d = date(2026, 11, 15)
    exp_end_d = date(2027, 5, 15)
    create_payload = {
        "candidate_id": str(candidate_id),
        "track_id": str(track_id),
        "start_date": str(start_d),
        "expected_end_date": str(exp_end_d),
        "company_name": "Microsoft Cloud Innovation Labs",
        "coordinator_notes": "Enrolled in enterprise analytics internship program.",
        "initial_status": "ACTIVE",
    }

    res = await async_client.post(
        "/api/v1/internships",
        json=create_payload,
        **admin_auth,
    )
    assert res.status_code == 201, f"Failed to initialize internship: {res.text}"
    data = res.json()

    assert data["candidate_id"] == str(candidate_id)
    assert data["track_id"] == str(track_id)
    assert data["start_date"] == "2026-11-15"
    assert data["expected_end_date"] == "2027-05-15"
    assert data["company_name"] == "Microsoft Cloud Innovation Labs"
    assert data["internship_status"] == "ACTIVE"
    # Decoupled duration starts at 3 months per BR-INT-02 baseline
    assert data["accredited_duration_months"] == 3

    # Check 3 sequential milestone tiers created
    milestones = data["milestones"]
    assert len(milestones) == 3
    assert milestones[0]["milestone_tier"] == 1
    assert milestones[0]["accredited_months"] == 3
    assert milestones[1]["milestone_tier"] == 2
    assert milestones[1]["accredited_months"] == 6
    assert milestones[2]["milestone_tier"] == 3
    assert milestones[2]["accredited_months"] == 9


@pytest.mark.asyncio
async def test_internship_duplicate_prevention(async_client: AsyncClient):
    """Verifies candidate cannot have duplicate active records under the same track."""
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    candidate_id = await provision_candidate(async_client, admin_auth, batch_id)

    create_payload = {
        "candidate_id": str(candidate_id),
        "track_id": str(track_id),
        "start_date": "2026-11-01",
    }

    res1 = await async_client.post("/api/v1/internships", json=create_payload, **admin_auth)
    assert res1.status_code == 201

    # Second initialization attempt should return 409 Conflict
    res2 = await async_client.post("/api/v1/internships", json=create_payload, **admin_auth)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_internship_calendar_date_validation(async_client: AsyncClient):
    """Verifies expected_end_date cannot be earlier than start_date."""
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    candidate_id = await provision_candidate(async_client, admin_auth, batch_id)

    invalid_payload = {
        "candidate_id": str(candidate_id),
        "track_id": str(track_id),
        "start_date": "2026-12-01",
        "expected_end_date": "2026-11-01",  # Before start date
    }

    res = await async_client.post("/api/v1/internships", json=invalid_payload, **admin_auth)
    assert res.status_code == 422
    assert "Expected end date cannot be earlier" in res.json()["detail"]


@pytest.mark.asyncio
async def test_internship_calendar_date_and_company_updates(async_client: AsyncClient):
    """Verifies PATCH /internships/{id} modifies operational calendar dates and company mapping."""
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    candidate_id = await provision_candidate(async_client, admin_auth, batch_id)

    create_res = await async_client.post(
        "/api/v1/internships",
        json={
            "candidate_id": str(candidate_id),
            "track_id": str(track_id),
            "start_date": "2026-11-01",
            "company_name": "ExcelR Labs",
        },
        **admin_auth,
    )
    assert create_res.status_code == 201
    record_id = create_res.json()["id"]

    # Update calendar dates and corporate partner
    patch_payload = {
        "start_date": "2026-11-10",
        "expected_end_date": "2027-05-30",
        "company_name": "Amazon Web Services Analytics Lab",
        "coordinator_notes": "Corporate placement finalized.",
    }
    patch_res = await async_client.patch(
        f"/api/v1/internships/{record_id}",
        json=patch_payload,
        **admin_auth,
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["start_date"] == "2026-11-10"
    assert updated["expected_end_date"] == "2027-05-30"
    assert updated["company_name"] == "Amazon Web Services Analytics Lab"
    assert updated["coordinator_notes"] == "Corporate placement finalized."


@pytest.mark.asyncio
async def test_internship_milestone_progression_and_sync(async_client: AsyncClient):
    """
    Verifies BR-INT-02: Configurable Project-to-Internship Duration Policy.
    - 1 Approved Project -> 3 Months
    - 2 Approved Projects -> 6 Months
    - 3 Approved Projects -> 9 Months
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    candidate_id = await provision_candidate(async_client, admin_auth, batch_id)

    # Initialize record
    init_res = await async_client.post(
        "/api/v1/internships",
        json={"candidate_id": str(candidate_id), "track_id": str(track_id), "start_date": "2026-11-01"},
        **admin_auth,
    )
    assert init_res.status_code == 201
    record_id = init_res.json()["id"]
    assert init_res.json()["accredited_duration_months"] == 3

    # Simulate Candidate completing 2 projects in a group
    session_factory = get_session_factory()
    async with session_factory() as session:
        grp = ProjectGroup(
            id=uuid.uuid4(),
            batch_id=batch_id,
            group_name="Analytics Cohort Squad",
            group_status="ACTIVE",
            readiness_status="READY_FOR_NEXT_PROJECT",  # Completed project milestone
            min_size=1,
            target_size=2,
            max_size=4,
        )
        session.add(grp)
        await session.flush()

        mem = ProjectGroupMember(
            id=uuid.uuid4(),
            group_id=grp.id,
            candidate_id=candidate_id,
            role="MEMBER",
            status="ACTIVE",
        )
        session.add(mem)

        # Add 2 distinct approved project submissions
        p1 = Project(id=uuid.uuid4(), track_id=track_id, code=f"PRJ-01-{uuid.uuid4().hex[:4]}", title="Project 1", tier="TIER_1_FOUNDATIONAL")
        p2 = Project(id=uuid.uuid4(), track_id=track_id, code=f"PRJ-02-{uuid.uuid4().hex[:4]}", title="Project 2", tier="TIER_2_INTERMEDIATE")
        session.add_all([p1, p2])
        await session.flush()

        sub1 = ProjectGroupSubmission(
            id=uuid.uuid4(),
            group_id=grp.id,
            project_id=p1.id,
            submitted_by_id=candidate_id,
            attempt_number=1,
            status="APPROVED",
        )
        sub2 = ProjectGroupSubmission(
            id=uuid.uuid4(),
            group_id=grp.id,
            project_id=p2.id,
            submitted_by_id=candidate_id,
            attempt_number=1,
            status="APPROVED",
        )
        session.add_all([sub1, sub2])
        await session.commit()

    # Call /sync-duration
    sync_res = await async_client.post(
        f"/api/v1/internships/{record_id}/sync-duration",
        **admin_auth,
    )
    assert sync_res.status_code == 200
    synced_data = sync_res.json()

    # 2 Approved Projects -> 6 Months Accredited Duration
    assert synced_data["accredited_duration_months"] == 6

    # Tier 1 and Tier 2 milestones must be marked ACHIEVED
    m1 = next(m for m in synced_data["milestones"] if m["milestone_tier"] == 1)
    m2 = next(m for m in synced_data["milestones"] if m["milestone_tier"] == 2)
    m3 = next(m for m in synced_data["milestones"] if m["milestone_tier"] == 3)
    assert m1["status"] == "ACHIEVED"
    assert m2["status"] == "ACHIEVED"
    assert m3["status"] == "PENDING"


@pytest.mark.asyncio
async def test_internship_completion_workflow(async_client: AsyncClient):
    """Verifies confirming completion sets status=COMPLETED and actual_completion_date."""
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    candidate_id = await provision_candidate(async_client, admin_auth, batch_id)

    init_res = await async_client.post(
        "/api/v1/internships",
        json={"candidate_id": str(candidate_id), "track_id": str(track_id), "start_date": "2026-11-01"},
        **admin_auth,
    )
    assert init_res.status_code == 201
    record_id = init_res.json()["id"]

    # Confirm completion
    comp_res = await async_client.post(
        f"/api/v1/internships/{record_id}/complete",
        json={
            "actual_completion_date": "2027-02-01",
            "completion_notes": "Successfully presented final deliverables to review board.",
        },
        **admin_auth,
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["internship_status"] == "COMPLETED"
    assert comp_data["actual_completion_date"] == "2027-02-01"
    assert "Successfully presented" in comp_data["coordinator_notes"]

    # Attempting to complete an already completed record returns 400
    dup_comp = await async_client.post(
        f"/api/v1/internships/{record_id}/complete",
        json={"actual_completion_date": "2027-02-01"},
        **admin_auth,
    )
    assert dup_comp.status_code == 400
    assert "already marked as COMPLETED" in dup_comp.json()["detail"]


@pytest.mark.asyncio
async def test_internship_termination_with_mandatory_reason(async_client: AsyncClient):
    """Verifies terminating an internship requires a mandatory textual reason."""
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    candidate_id = await provision_candidate(async_client, admin_auth, batch_id)

    init_res = await async_client.post(
        "/api/v1/internships",
        json={"candidate_id": str(candidate_id), "track_id": str(track_id), "start_date": "2026-11-01"},
        **admin_auth,
    )
    assert init_res.status_code == 201
    record_id = init_res.json()["id"]

    # Termination with short reason fails validation (< 10 chars)
    short_res = await async_client.post(
        f"/api/v1/internships/{record_id}/terminate",
        json={"reason": "Left"},
        **admin_auth,
    )
    assert short_res.status_code == 422

    # Termination with valid reason succeeds
    term_res = await async_client.post(
        f"/api/v1/internships/{record_id}/terminate",
        json={"reason": "Candidate relocated for university degree program abroad."},
        **admin_auth,
    )
    assert term_res.status_code == 200
    term_data = term_res.json()
    assert term_data["internship_status"] == "TERMINATED"
    assert "relocated for university" in term_data["coordinator_notes"]

    # Completing a terminated internship is blocked
    comp_blocked = await async_client.post(
        f"/api/v1/internships/{record_id}/complete",
        json={"actual_completion_date": "2027-02-01"},
        **admin_auth,
    )
    assert comp_blocked.status_code == 400
    assert "terminated" in comp_blocked.json()["detail"].lower()


@pytest.mark.asyncio
async def test_internship_rbac_and_student_idor_protection(async_client: AsyncClient):
    """
    Verifies:
    1. ROLE_INT_COORD can initialize and manage internships.
    2. Unauthorized roles (e.g. ROLE_ASG_REVIEWER) cannot initialize internships.
    3. ROLE_STUDENT can view their own internship record but is blocked from other students' records.
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()

    uid = uuid.uuid4().hex[:6]
    # Create Internship Coordinator
    int_coord_user = await create_user_with_role(
        async_client,
        email=f"coord.internship_{uid}@excelr.com",
        password="Coord@Track360_2026!",
        full_name="Internship Officer",
        role_code="ROLE_INT_COORD",
    )

    # Create Assignment Reviewer (unauthorized for internship initiation)
    reviewer_user = await create_user_with_role(
        async_client,
        email=f"reviewer.temp_{uid}@excelr.com",
        password="Reviewer@Track360_2026!",
        full_name="Assignment Evaluator",
        role_code="ROLE_ASG_REVIEWER",
    )

    # Create 2 Students
    student1_user = await create_user_with_role(
        async_client,
        email=f"student.one_{uid}@excelr.com",
        password="Student1@Track360_2026!",
        full_name="Student One",
        role_code="ROLE_STUDENT",
    )
    student2_user = await create_user_with_role(
        async_client,
        email=f"student.two_{uid}@excelr.com",
        password="Student2@Track360_2026!",
        full_name="Student Two",
        role_code="ROLE_STUDENT",
    )

    cand1_id = await provision_candidate(async_client, admin_auth, batch_id, user_id=student1_user["user_id"])
    cand2_id = await provision_candidate(async_client, admin_auth, batch_id, user_id=student2_user["user_id"])

    # 1. Assignment Reviewer attempts to initialize internship -> 403 Forbidden
    unauth_init = await async_client.post(
        "/api/v1/internships",
        json={"candidate_id": str(cand1_id), "track_id": str(track_id), "start_date": "2026-11-01"},
        **reviewer_user["auth"],
    )
    assert unauth_init.status_code == 403

    # 2. Internship Coordinator initializes internship for Student 1 -> 201 Created
    coord_init = await async_client.post(
        "/api/v1/internships",
        json={"candidate_id": str(cand1_id), "track_id": str(track_id), "start_date": "2026-11-01"},
        **int_coord_user["auth"],
    )
    assert coord_init.status_code == 201
    cand1_rec_id = coord_init.json()["id"]

    # 3. Student 1 inspects their own record -> 200 OK
    s1_view_own = await async_client.get(
        f"/api/v1/internships/{cand1_rec_id}",
        **student1_user["auth"],
    )
    assert s1_view_own.status_code == 200
    assert s1_view_own.json()["candidate_id"] == str(cand1_id)

    # 4. Student 2 attempts to inspect Student 1's record -> 403 Forbidden (IDOR Guard)
    s2_idor_attempt = await async_client.get(
        f"/api/v1/internships/{cand1_rec_id}",
        **student2_user["auth"],
    )
    assert s2_idor_attempt.status_code == 403
    assert "Students can only view their own" in s2_idor_attempt.json()["detail"]
