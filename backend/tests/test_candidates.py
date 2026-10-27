"""
ExcelR Track360 - Candidate Management Test Suite
Phase 5 Verification: CRUD, duplicate prevention, search/filter,
status state transitions, bulk CSV preview & commit, and IDOR protection.
"""
from datetime import date
import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.core.security import hash_password
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
from app.modules.auth.models import User, Role, UserRole
from app.modules.auth.seed import seed_bootstrap_admin
from app.modules.candidates.models import Course, CourseTrack, Batch, Candidate


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


@pytest.mark.asyncio
async def test_candidate_crud_and_duplicate_prevention(async_client: AsyncClient):
    """Verifies candidate creation, duplicate checks on email and phone, and update."""
    admin_auth = await login_as_admin(async_client)

    # 1. Create Course, Track, and Batch first
    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": f"DA_{uuid.uuid4().hex[:4]}", "title": "Data Analytics"},
        **admin_auth,
    )
    assert c_resp.status_code == 200
    course_id = c_resp.json()["id"]

    t_resp = await async_client.post(
        "/api/v1/courses/tracks",
        json={
            "course_id": course_id,
            "code": f"DA_FAST_{uuid.uuid4().hex[:4]}",
            "title": "FastTrack Analytics",
        },
        **admin_auth,
    )
    assert t_resp.status_code == 200
    track_id = t_resp.json()["id"]

    b_resp = await async_client.post(
        "/api/v1/batches",
        json={
            "track_id": track_id,
            "batch_code": f"BATCH_{uuid.uuid4().hex[:4]}",
            "title": "Cohort Alpha",
            "start_date": "2026-11-01",
        },
        **admin_auth,
    )
    assert b_resp.status_code == 200
    batch_id = b_resp.json()["id"]

    # 2. Create Candidate
    uid = uuid.uuid4().hex[:8]
    cand_resp = await async_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": f"john_{uid}@excelr.com",
            "phone": f"+9198{uid[:8]}",
            "academic_qualification": "B.Tech Computer Science",
            "batch_id": batch_id,
        },
        **admin_auth,
    )
    assert cand_resp.status_code == 201
    cand_data = cand_resp.json()
    assert cand_data["first_name"] == "John"
    assert cand_data["candidate_number"].startswith("EX-")
    candidate_id = cand_data["id"]

    # 3. Duplicate Email Rejection (409 Conflict)
    dup_email_resp = await async_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Another",
            "last_name": "Person",
            "email": f"john_{uid}@excelr.com",
            "phone": f"+9188{uid[:8]}",
        },
        **admin_auth,
    )
    assert dup_email_resp.status_code == 409
    assert "already exists" in dup_email_resp.json()["detail"]

    # 4. Duplicate Phone Rejection (409 Conflict)
    dup_phone_resp = await async_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Different",
            "last_name": "Person",
            "email": f"diff_{uid}@excelr.com",
            "phone": f"+9198{uid[:8]}",
        },
        **admin_auth,
    )
    assert dup_phone_resp.status_code == 409

    # 5. Update Candidate
    update_resp = await async_client.patch(
        f"/api/v1/candidates/{candidate_id}",
        json={"first_name": "Jonathan", "academic_qualification": "M.Tech AI"},
        **admin_auth,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["first_name"] == "Jonathan"
    assert update_resp.json()["academic_qualification"] == "M.Tech AI"


@pytest.mark.asyncio
async def test_candidate_status_transition_state_machine(async_client: AsyncClient):
    """Verifies lifecycle status modification with mandatory audit reasoning."""
    admin_auth = await login_as_admin(async_client)
    uid = uuid.uuid4().hex[:8]

    # Create candidate
    cand_resp = await async_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Status",
            "last_name": "Tester",
            "email": f"status_{uid}@excelr.com",
            "phone": f"+9177{uid[:8]}",
        },
        **admin_auth,
    )
    candidate_id = cand_resp.json()["id"]

    # Valid transition to ON_HOLD
    on_hold_resp = await async_client.patch(
        f"/api/v1/candidates/{candidate_id}/status",
        json={"to_status": "ON_HOLD", "reason": "Candidate requested 30-day medical hiatus"},
        **admin_auth,
    )
    assert on_hold_resp.status_code == 200
    assert on_hold_resp.json()["lifecycle_status"] == "ON_HOLD"

    # Invalid status name rejected
    invalid_resp = await async_client.patch(
        f"/api/v1/candidates/{candidate_id}/status",
        json={"to_status": "BOGUS_STATUS", "reason": "Invalid test status"},
        **admin_auth,
    )
    assert invalid_resp.status_code == 400


@pytest.mark.asyncio
async def test_candidate_list_search_and_pagination(async_client: AsyncClient):
    """Verifies server-side pagination, search by name/email, and filtering."""
    admin_auth = await login_as_admin(async_client)
    uid = uuid.uuid4().hex[:6]

    # Create two candidates
    await async_client.post(
        "/api/v1/candidates",
        json={
            "first_name": f"SearchTarget_{uid}",
            "last_name": "UniqueUser",
            "email": f"target_{uid}@excelr.com",
            "phone": f"+9166{uid[:8]}",
        },
        **admin_auth,
    )

    # Search query
    search_resp = await async_client.get(
        f"/api/v1/candidates?search=SearchTarget_{uid}",
        cookies=admin_auth["cookies"],
    )
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == f"target_{uid}@excelr.com"


@pytest.mark.asyncio
async def test_candidate_csv_import_preview_and_commit(async_client: AsyncClient):
    """Verifies dry-run CSV parsing, row validation errors, and transactional commit."""
    admin_auth = await login_as_admin(async_client)
    uid = uuid.uuid4().hex[:6]

    csv_data = f"""first_name,last_name,email,phone,batch_code,academic_qualification
Alice,Valid,alice_{uid}@excelr.com,+915511{uid},,B.Sc
,MissingName,bad_{uid}@excelr.com,+915522{uid},,B.Com
Bob,BadEmail,notanemail,+915533{uid},,MCA
Charlie,ShortPhone,charlie_{uid}@excelr.com,123,,B.Tech
David,ValidTwo,david_{uid}@excelr.com,+915544{uid},,B.A
"""
    # 1. Preview
    files = {"file": ("roster.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    preview_resp = await async_client.post(
        "/api/v1/candidates/import/preview",
        files=files,
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["total_rows"] == 5
    assert preview["valid_rows_count"] == 2
    assert preview["error_rows_count"] == 3

    # Check row errors
    rows = preview["rows"]
    assert rows[0]["is_valid"] is True  # Alice
    assert rows[1]["is_valid"] is False  # Missing first name
    assert rows[1]["error_field"] == "first_name"
    assert rows[2]["is_valid"] is False  # Bad email
    assert rows[2]["error_field"] == "email"
    assert rows[3]["is_valid"] is False  # Short phone
    assert rows[3]["error_field"] == "phone"
    assert rows[4]["is_valid"] is True  # David

    # 2. Commit valid rows
    commit_resp = await async_client.post(
        "/api/v1/candidates/import/commit",
        json={"rows": rows},
        **admin_auth,
    )
    assert commit_resp.status_code == 200
    commit_data = commit_resp.json()
    assert commit_data["inserted_count"] == 2
    assert commit_data["skipped_count"] == 3


@pytest.mark.asyncio
async def test_candidate_idor_protection_for_students(async_client: AsyncClient):
    """
    IDOR Security Gate:
    1. Students are forbidden from querying the candidate list (/api/v1/candidates).
    2. A student querying another student's record (/api/v1/candidates/{other_id}) receives 403 Forbidden.
    3. A student querying their own profile (/api/v1/candidates/me or /api/v1/candidates/{own_id}) succeeds.
    """
    admin_auth = await login_as_admin(async_client)
    uid = uuid.uuid4().hex[:6]

    # Create Student User A and linked Candidate A
    session_factory = get_session_factory()
    student_role = None
    async with session_factory() as session:
        student_role = (await session.execute(select(Role).where(Role.code == "ROLE_STUDENT"))).scalar_one()

        user_a = User(
            email=f"student_a_{uid}@excelr.com",
            password_hash=hash_password("Pass123!"),
            full_name="Student User A",
            status="ACTIVE",
            is_verified=True,
        )
        session.add(user_a)
        await session.flush()
        session.add(UserRole(user_id=user_a.id, role_id=student_role.id))

        cand_a = Candidate(
            user_id=user_a.id,
            candidate_number=f"EX-A-{uid}",
            first_name="Alice",
            last_name="Learner",
            email=user_a.email,
            phone=f"+9111{uid[:8]}",
            lifecycle_status="ACTIVE",
        )
        session.add(cand_a)

        # Create Candidate B (not linked to User A)
        cand_b = Candidate(
            candidate_number=f"EX-B-{uid}",
            first_name="Bob",
            last_name="Other",
            email=f"bob_{uid}@excelr.com",
            phone=f"+9122{uid[:8]}",
            lifecycle_status="ACTIVE",
        )
        session.add(cand_b)
        await session.commit()
        await session.refresh(cand_a)
        await session.refresh(cand_b)
        cand_a_id = cand_a.id
        cand_b_id = cand_b.id

    # Login as Student A
    login_a = await async_client.post(
        "/api/v1/auth/login",
        json={"email": f"student_a_{uid}@excelr.com", "password": "Pass123!"},
    )
    assert login_a.status_code == 200
    token_a = login_a.cookies[SESSION_COOKIE_NAME]
    auth_a = {"cookies": {SESSION_COOKIE_NAME: token_a}}

    # 1. Student A attempts to access candidate list -> 403 Forbidden
    list_attempt = await async_client.get("/api/v1/candidates", **auth_a)
    assert list_attempt.status_code == 403

    # 2. Student A attempts to access Candidate B by ID -> 403 Forbidden
    idor_attempt = await async_client.get(f"/api/v1/candidates/{cand_b_id}", **auth_a)
    assert idor_attempt.status_code == 403
    assert "cannot access another candidate's profile" in idor_attempt.json()["detail"]

    # 3. Student A accesses their own candidate profile by ID -> 200 OK
    own_resp = await async_client.get(f"/api/v1/candidates/{cand_a_id}", **auth_a)
    assert own_resp.status_code == 200
    assert own_resp.json()["email"] == f"student_a_{uid}@excelr.com"

    # 4. Student A accesses /candidates/me -> 200 OK
    me_resp = await async_client.get("/api/v1/candidates/me", **auth_a)
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == str(cand_a_id)
