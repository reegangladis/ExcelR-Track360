"""
ExcelR Track360 - Project Groups & Dynamic Sizing Test Suite
Phase 9 Verification:
1. Dynamic Group Sizing (min 2, target 4, max 5)
2. Capacity guards: Max 5 enforcement (6th addition rejected with 422)
3. Cohort batch isolation: Candidates must belong to the group's cohort batch
4. Single active group membership constraint within a cohort batch
5. Min size removal guard: Removal below 2 members rejected without override
6. Leader assignment & group status progression
7. RBAC permissions (project:group_manage enforcement)
"""
import uuid
from datetime import date
from typing import Tuple, List
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.core.security import hash_password
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
from app.modules.auth.models import Role, User, UserRole
from app.modules.auth.seed import seed_bootstrap_admin
from app.modules.candidates.models import Batch, Candidate, Course, CourseTrack, Enrollment
from app.modules.projects.models import Project


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


async def provision_batch_and_track() -> Tuple[uuid.UUID, uuid.UUID]:
    """Provisions a course, track, and cohort batch."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        uid = uuid.uuid4().hex[:6]
        course = Course(
            id=uuid.uuid4(),
            code=f"CRS_GRP_{uid}",
            title=f"Full Stack Data Engineering {uid}",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        track = CourseTrack(
            id=uuid.uuid4(),
            course_id=course.id,
            code=f"TRK_GRP_{uid}",
            title=f"Engineering Track {uid}",
            total_mandatory_assignments=2,
            total_required_projects=1,
            is_active=True,
        )
        session.add(track)
        await session.flush()

        batch = Batch(
            id=uuid.uuid4(),
            track_id=track.id,
            batch_code=f"BATCH-GRP-{uid}",
            title=f"Cohort Batch {uid}",
            start_date=date(2026, 11, 1),
            status="ACTIVE",
        )
        session.add(batch)
        await session.commit()
        return batch.id, track.id


async def provision_candidates_in_batch(
    async_client: AsyncClient, admin_auth: dict, batch_id: uuid.UUID, count: int = 6
) -> List[uuid.UUID]:
    """Provisions candidates enrolled in the given batch."""
    candidate_ids = []
    for i in range(count):
        uid = uuid.uuid4().hex[:6]
        resp = await async_client.post(
            "/api/v1/candidates",
            json={
                "first_name": f"Cand{i}",
                "last_name": f"User_{uid}",
                "email": f"cand_{i}_{uid}@example.com",
                "phone": f"+9198{uuid.uuid4().int % 100000000:08d}",
                "batch_id": str(batch_id),
            },
            **admin_auth,
        )
        assert resp.status_code == 201, f"Failed to create candidate: {resp.text}"
        candidate_ids.append(uuid.UUID(resp.json()["id"]))
    return candidate_ids


async def provision_student_account(async_client: AsyncClient) -> dict:
    """Provisions a student user."""
    uid = uuid.uuid4().hex[:6]
    email = f"student_grp_{uid}@example.com"
    pwd = "Student@123456_Secure!"

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
        await session.commit()

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert login_resp.status_code == 200
    csrf = login_resp.json()["csrf_token"]
    session_token = login_resp.cookies[SESSION_COOKIE_NAME]
    return {
        "cookies": {SESSION_COOKIE_NAME: session_token, CSRF_COOKIE_NAME: csrf},
        "headers": {"x-csrf-token": csrf},
    }


@pytest.mark.asyncio
async def test_group_formation_and_dynamic_sizing(async_client: AsyncClient):
    """
    Verifies dynamic team sizing constraints:
    - Min 2 members required / Target 4 / Max 5 members
    - Forming a group with 2 candidates
    - Adding 3rd, 4th, 5th candidates
    - Attempting to add a 6th candidate is rejected with 422
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    candidates = await provision_candidates_in_batch(async_client, admin_auth, batch_id, count=6)

    # 1. Form a group with 2 initial members
    create_payload = {
        "batch_id": str(batch_id),
        "group_name": "Alpha Data Ninjas",
        "min_size": 2,
        "target_size": 4,
        "max_size": 5,
        "initial_candidate_ids": [str(candidates[0]), str(candidates[1])],
        "leader_candidate_id": str(candidates[0]),
    }
    resp = await async_client.post("/api/v1/projects/groups", json=create_payload, **admin_auth)
    assert resp.status_code == 201
    group_data = resp.json()
    group_id = group_data["id"]

    assert group_data["group_name"] == "Alpha Data Ninjas"
    assert group_data["group_status"] == "FORMING"
    assert group_data["member_count"] == 2
    assert len(group_data["members"]) == 2

    # Verify leader designation
    leader_mem = next(m for m in group_data["members"] if m["candidate_id"] == str(candidates[0]))
    assert leader_mem["role"] == "LEADER"
    other_mem = next(m for m in group_data["members"] if m["candidate_id"] == str(candidates[1]))
    assert other_mem["role"] == "MEMBER"

    # 2. Add 3rd member
    resp3 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/members",
        json={"candidate_id": str(candidates[2]), "role": "MEMBER"},
        **admin_auth,
    )
    assert resp3.status_code == 201
    assert resp3.json()["member_count"] == 3

    # 3. Add 4th member (Target size)
    resp4 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/members",
        json={"candidate_id": str(candidates[3]), "role": "MEMBER"},
        **admin_auth,
    )
    assert resp4.status_code == 201
    assert resp4.json()["member_count"] == 4

    # 4. Add 5th member (Maximum size capacity)
    resp5 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/members",
        json={"candidate_id": str(candidates[4]), "role": "MEMBER"},
        **admin_auth,
    )
    assert resp5.status_code == 201
    assert resp5.json()["member_count"] == 5

    # 5. Attempt to add 6th member -> MUST fail with 422 Unprocessable Entity
    resp6 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/members",
        json={"candidate_id": str(candidates[5]), "role": "MEMBER"},
        **admin_auth,
    )
    assert resp6.status_code == 422
    assert "maximum capacity" in resp6.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cohort_isolation_guard(async_client: AsyncClient):
    """
    Verifies that candidates cannot be added to a group belonging to a different cohort batch.
    """
    admin_auth = await login_as_admin(async_client)
    batch_a, track_id = await provision_batch_and_track()
    batch_b, _ = await provision_batch_and_track()

    candidates_a = await provision_candidates_in_batch(async_client, admin_auth, batch_a, count=2)
    candidates_b = await provision_candidates_in_batch(async_client, admin_auth, batch_b, count=2)

    # Create group in Batch A
    resp = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_a),
            "group_name": "Batch A Innovators",
            "initial_candidate_ids": [str(candidates_a[0]), str(candidates_a[1])],
        },
        **admin_auth,
    )
    assert resp.status_code == 201
    group_id = resp.json()["id"]

    # Attempt to add candidate from Batch B to Batch A's group -> MUST fail with 422
    cross_resp = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/members",
        json={"candidate_id": str(candidates_b[0]), "role": "MEMBER"},
        **admin_auth,
    )
    assert cross_resp.status_code == 422
    assert "not actively enrolled" in cross_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_duplicate_active_membership_guard(async_client: AsyncClient):
    """
    Verifies that a candidate cannot belong to multiple active groups within the same cohort.
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, _ = await provision_batch_and_track()
    candidates = await provision_candidates_in_batch(async_client, admin_auth, batch_id, count=4)

    # 1. Create Group 1 with candidate 0 and 1
    resp1 = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Team One",
            "initial_candidate_ids": [str(candidates[0]), str(candidates[1])],
        },
        **admin_auth,
    )
    assert resp1.status_code == 201

    # 2. Attempt to create Group 2 with candidate 0 again -> MUST fail with 409 Conflict
    conflict_create = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Team Two",
            "initial_candidate_ids": [str(candidates[0]), str(candidates[2])],
        },
        **admin_auth,
    )
    assert conflict_create.status_code == 409
    assert "already a member" in conflict_create.json()["detail"].lower()

    # 3. Create Group 2 with candidates 2 and 3
    resp2 = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Team Two",
            "initial_candidate_ids": [str(candidates[2]), str(candidates[3])],
        },
        **admin_auth,
    )
    assert resp2.status_code == 201
    group_2_id = resp2.json()["id"]

    # 4. Attempt to add candidate 0 to Group 2 via POST /members -> MUST fail with 409 Conflict
    add_conflict = await async_client.post(
        f"/api/v1/projects/groups/{group_2_id}/members",
        json={"candidate_id": str(candidates[0]), "role": "MEMBER"},
        **admin_auth,
    )
    assert add_conflict.status_code == 409
    assert "already an active member" in add_conflict.json()["detail"].lower()


@pytest.mark.asyncio
async def test_minimum_size_removal_guard_and_override(async_client: AsyncClient):
    """
    Verifies that removing a member from a 2-person group is blocked (422)
    unless administrative override=true is provided.
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, _ = await provision_batch_and_track()
    candidates = await provision_candidates_in_batch(async_client, admin_auth, batch_id, count=3)

    resp = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Duo Dynamic",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(candidates[0]), str(candidates[1])],
        },
        **admin_auth,
    )
    assert resp.status_code == 201
    group_id = resp.json()["id"]

    # 1. Attempt to remove candidate 1 without override -> MUST fail with 422
    del_blocked = await async_client.delete(
        f"/api/v1/projects/groups/{group_id}/members/{candidates[1]}",
        **admin_auth,
    )
    assert del_blocked.status_code == 422
    assert "minimum size constraint" in del_blocked.json()["detail"].lower()

    # 2. Remove candidate 1 WITH override=true -> MUST succeed
    del_override = await async_client.delete(
        f"/api/v1/projects/groups/{group_id}/members/{candidates[1]}?override=true",
        **admin_auth,
    )
    assert del_override.status_code == 200
    assert del_override.json()["member_count"] == 1

    # 3. Attempting to activate group with < min_size members -> MUST fail with 422
    activate_fail = await async_client.patch(
        f"/api/v1/projects/groups/{group_id}",
        json={"group_status": "ACTIVE"},
        **admin_auth,
    )
    assert activate_fail.status_code == 422
    assert "at least 2 active members" in activate_fail.json()["detail"].lower()


@pytest.mark.asyncio
async def test_leader_assignment_and_progression(async_client: AsyncClient):
    """
    Verifies leader reassignment and group status transitions.
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, _ = await provision_batch_and_track()
    candidates = await provision_candidates_in_batch(async_client, admin_auth, batch_id, count=3)

    resp = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Phoenix Squad",
            "initial_candidate_ids": [str(candidates[0]), str(candidates[1]), str(candidates[2])],
            "leader_candidate_id": str(candidates[0]),
        },
        **admin_auth,
    )
    assert resp.status_code == 201
    group_id = resp.json()["id"]

    # 1. Reassign leader to candidate 1
    leader_resp = await async_client.patch(
        f"/api/v1/projects/groups/{group_id}/leader/{candidates[1]}",
        **admin_auth,
    )
    assert leader_resp.status_code == 200
    updated_members = leader_resp.json()["members"]

    m0 = next(m for m in updated_members if m["candidate_id"] == str(candidates[0]))
    assert m0["role"] == "MEMBER"

    m1 = next(m for m in updated_members if m["candidate_id"] == str(candidates[1]))
    assert m1["role"] == "LEADER"

    # 2. Transition group status to ACTIVE
    status_resp = await async_client.patch(
        f"/api/v1/projects/groups/{group_id}",
        json={"group_status": "ACTIVE"},
        **admin_auth,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["group_status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_group_management_rbac_guards(async_client: AsyncClient):
    """
    Verifies RBAC enforcement:
    - Unauthenticated requests are rejected with 401
    - Student users cannot create or mutate project groups (403 Forbidden)
    """
    batch_id, _ = await provision_batch_and_track()
    student_auth = await provision_student_account(async_client)

    # 1. Unauthenticated creation -> 401
    async_client.cookies.clear()
    unauth_resp = await async_client.post(
        "/api/v1/projects/groups",
        json={"batch_id": str(batch_id), "group_name": "Unauthorized Group"},
    )
    assert unauth_resp.status_code == 401

    # 2. Student creation -> 403 Forbidden (missing project:group_manage)
    student_create = await async_client.post(
        "/api/v1/projects/groups",
        json={"batch_id": str(batch_id), "group_name": "Student Created Group"},
        **student_auth,
    )
    assert student_create.status_code == 403
