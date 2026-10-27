"""
ExcelR Track360 - Phase 10: Project Allocation & Completion Test Suite
Strictly verifies:
1. Mentor Assignment & Staff Evaluator Mapping
2. BR-PRJ-01 Prerequisite Assignment Completion Gating & Waiver Validation
3. AC-PRJ-003 Dynamic Group Sizing on Project Allocation (min_size <= len <= max_size)
4. BR-PRJ-04 Single Active Project Constraint (Concurrent Active Project Prevention)
5. WF-05 Deliverable Submissions, Multi-Attempt Revisions & Review Rubric Evaluation
6. BR-GRP-01 & AC-GRP-001 / AC-GRP-002 Collaborative Group Readiness State Machine
7. AC-GRP-003 Inactive Member Removal & Immediate Group Readiness Recalculation
8. WF-06 Multi-Project Tier Advancement (Tier 1 -> Tier 2 -> Tier 3 Capstone -> Completed)
9. BR-PRJ-02 & AC-PRJ-002 Maximum 3 Projects Cap Enforcement (4th Allocation Blocked with HTTP 422)
"""
import uuid
from datetime import date
from typing import Tuple, List
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
from app.modules.auth.models import Role, User, UserRole
from app.modules.auth.seed import seed_bootstrap_admin
from app.modules.candidates.models import Batch, Candidate, Course, CourseTrack, Enrollment
from app.modules.projects.models import Project, ProjectMilestone, ProjectGroup, ProjectGroupMember


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
            code=f"CRS_ALC_{uid}",
            title=f"Full Stack Cloud Engineering {uid}",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        track = CourseTrack(
            id=uuid.uuid4(),
            course_id=course.id,
            code=f"TRK_ALC_{uid}",
            title=f"Engineering Track {uid}",
            total_mandatory_assignments=2,
            total_required_projects=3,
            is_active=True,
        )
        session.add(track)
        await session.flush()

        batch = Batch(
            id=uuid.uuid4(),
            track_id=track.id,
            batch_code=f"BATCH-ALC-{uid}",
            title=f"Cohort Batch {uid}",
            start_date=date(2026, 11, 1),
            status="ACTIVE",
        )
        session.add(batch)
        await session.commit()
        return batch.id, track.id


async def provision_candidates(
    async_client: AsyncClient, admin_auth: dict, batch_id: uuid.UUID, count: int = 4
) -> List[uuid.UUID]:
    """Provisions candidates enrolled in the given batch."""
    candidate_ids = []
    for i in range(count):
        uid = uuid.uuid4().hex[:6]
        cand_payload = {
            "first_name": f"Student{i}",
            "last_name": f"Candidate{uid}",
            "email": f"cand_{uid}_{i}@excelr.com",
            "phone": f"+9198{uuid.uuid4().int % 100000000:08d}",
            "batch_id": str(batch_id),
        }
        res = await async_client.post(
            "/api/v1/candidates",
            json=cand_payload,
            **admin_auth,
        )
        assert res.status_code == 201, f"Failed to provision candidate: {res.text}"
        candidate_ids.append(uuid.UUID(res.json()["id"]))
    return candidate_ids


async def provision_project_spec(
    async_client: AsyncClient, admin_auth: dict, track_id: uuid.UUID, tier: str = "TIER_1_FOUNDATIONAL"
) -> uuid.UUID:
    """Provisions a project specification for testing."""
    uid = uuid.uuid4().hex[:5]
    prj_payload = {
        "track_id": str(track_id),
        "code": f"PRJ-{tier[:4]}-{uid}",
        "title": f"Enterprise System {tier} {uid}",
        "tier": tier,
        "complexity": "MEDIUM",
        "min_team_size": 2,
        "max_team_size": 5,
        "passing_score": 60.0,
        "milestones": [
            {
                "sequence_order": 1,
                "title": "Architecture & Schema",
                "weight_percentage": 50.0,
                "max_score": 100.0,
                "is_mandatory": True,
            },
            {
                "sequence_order": 2,
                "title": "Final Implementation & Deployment",
                "weight_percentage": 50.0,
                "max_score": 100.0,
                "is_mandatory": True,
            },
        ],
    }
    res = await async_client.post(
        "/api/v1/projects",
        json=prj_payload,
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert res.status_code == 201, f"Failed to provision project: {res.text}"
    return uuid.UUID(res.json()["id"])


# ==============================================================
# Phase 10 Tests
# ==============================================================

@pytest.mark.asyncio
async def test_mentor_assignment(async_client: AsyncClient):
    """Verifies assigning an authoritative staff mentor to a project group."""
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    cand_ids = await provision_candidates(async_client, admin_auth, batch_id, count=3)

    # 1. Create group
    grp_res = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Alpha Squad",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(c) for c in cand_ids],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert grp_res.status_code == 201
    group_id = grp_res.json()["id"]

    # 2. Assign admin as mentor
    session_factory = get_session_factory()
    async with session_factory() as session:
        admin_user = (await session.execute(select(User).where(User.email == "admin@excelr.com"))).scalar_one()
        admin_user_id = admin_user.id

    mentor_res = await async_client.put(
        f"/api/v1/projects/groups/{group_id}/mentor",
        json={"mentor_id": str(admin_user_id)},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert mentor_res.status_code == 200
    assert mentor_res.json()["mentor_id"] == str(admin_user_id)
    assert mentor_res.json()["mentor_name"] == admin_user.full_name

    # 3. Invalid mentor id -> 404
    fake_mentor_res = await async_client.put(
        f"/api/v1/projects/groups/{group_id}/mentor",
        json={"mentor_id": str(uuid.uuid4())},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert fake_mentor_res.status_code == 404


@pytest.mark.asyncio
async def test_project_allocation_prerequisite_gating_and_waiver(async_client: AsyncClient):
    """
    Verifies BR-PRJ-01:
    - Candidate without completed mandatory assignments is blocked from Project 1.
    - Prerequisite waiver requires explicit justification.
    - Prerequisite waiver with justification successfully allocates the project.
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    cand_ids = await provision_candidates(async_client, admin_auth, batch_id, count=3)
    project_id = await provision_project_spec(async_client, admin_auth, track_id, tier="TIER_1_FOUNDATIONAL")

    # Create group
    grp_res = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Beta Squad",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(c) for c in cand_ids],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert grp_res.status_code == 201
    group_id = grp_res.json()["id"]

    # 1. Attempt allocation without waiver -> Rejected (BR-PRJ-01)
    alloc_fail = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocate-project",
        json={"project_id": str(project_id), "waive_prerequisites": False},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert alloc_fail.status_code == 422
    assert "prerequisite mandatory assignments" in alloc_fail.json()["detail"]

    # 2. Attempt waiver without justification -> 400
    waiver_no_just = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocate-project",
        json={"project_id": str(project_id), "waive_prerequisites": True, "waiver_justification": ""},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert waiver_no_just.status_code == 400
    assert "Waiver justification is mandatory" in waiver_no_just.json()["detail"]

    # 3. Waiver with academic justification -> Allocation succeeds
    alloc_success = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocate-project",
        json={
            "project_id": str(project_id),
            "waive_prerequisites": True,
            "waiver_justification": "Approved via academic committee waiver ref #AC-2026-089",
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert alloc_success.status_code == 200
    data = alloc_success.json()
    assert data["project_id"] == str(project_id)
    assert data["group_status"] == "ACTIVE"
    assert data["readiness_status"] == "AWAITING_SUBMISSION"
    assert data["current_milestone_title"] == "Architecture & Schema"


@pytest.mark.asyncio
async def test_dynamic_group_sizing_on_allocation(async_client: AsyncClient):
    """Verifies AC-PRJ-003: Allocation blocked if group size is below min_size."""
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    cand_ids = await provision_candidates(async_client, admin_auth, batch_id, count=1)
    project_id = await provision_project_spec(async_client, admin_auth, track_id)

    # Form a 1-candidate group
    grp_res = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Solo Squad",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(cand_ids[0])],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert grp_res.status_code == 201
    group_id = grp_res.json()["id"]

    # Allocation should fail with 422: Group size 1 is below minimum permitted size of 2
    alloc_res = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocate-project",
        json={"project_id": str(project_id), "waive_prerequisites": True, "waiver_justification": "Waiver"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert alloc_res.status_code == 422
    assert "Group size 1 is below minimum permitted size of 2" in alloc_res.json()["detail"]


@pytest.mark.asyncio
async def test_single_active_project_constraint(async_client: AsyncClient):
    """Verifies BR-PRJ-04: Candidate cannot be in multiple active project groups concurrently."""
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    cand_ids = await provision_candidates(async_client, admin_auth, batch_id, count=4)
    project_id = await provision_project_spec(async_client, admin_auth, track_id)

    # Group 1 (cand_0, cand_1)
    g1 = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Group 1",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(cand_ids[0]), str(cand_ids[1])],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert g1.status_code == 201
    g1_id = g1.json()["id"]

    # Allocate project to Group 1
    a1 = await async_client.post(
        f"/api/v1/projects/groups/{g1_id}/allocate-project",
        json={"project_id": str(project_id), "waive_prerequisites": True, "waiver_justification": "Waiver G1"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert a1.status_code == 200

    # Group 2 (cand_2, cand_3)
    g2 = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Group 2",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(cand_ids[2]), str(cand_ids[3])],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert g2.status_code == 201
    g2_id = g2.json()["id"]

    # Now manually associate cand_0 into Group 2 via DB to simulate illegal concurrent assignment
    session_factory = get_session_factory()
    async with session_factory() as session:
        session.add(
            ProjectGroupMember(
                id=uuid.uuid4(),
                group_id=uuid.UUID(g2_id),
                candidate_id=cand_ids[0],
                role="MEMBER",
                status="ACTIVE",
            )
        )
        await session.commit()

    # Attempting to allocate project to Group 2 must raise HTTP 409 (BR-PRJ-04)
    a2 = await async_client.post(
        f"/api/v1/projects/groups/{g2_id}/allocate-project",
        json={"project_id": str(project_id), "waive_prerequisites": True, "waiver_justification": "Waiver G2"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert a2.status_code == 409
    assert "already assigned to another active project group" in a2.json()["detail"]


@pytest.mark.asyncio
async def test_deliverable_submission_and_rubric_review(async_client: AsyncClient):
    """
    Verifies WF-05:
    - Group deliverable submission with repo URL, deployment link, notes.
    - Review with CORRECTIONS_REQUESTED sets readiness to CORRECTIONS_REQUESTED.
    - Subsequent submission increments attempt number.
    - Final approval clears progression gates and sets readiness to BLOCKED_PENDING_MEMBERS.
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    cand_ids = await provision_candidates(async_client, admin_auth, batch_id, count=2)
    project_id = await provision_project_spec(async_client, admin_auth, track_id)

    # 1. Create and allocate
    grp_res = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Delivery Squad",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(c) for c in cand_ids],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    group_id = grp_res.json()["id"]

    await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocate-project",
        json={"project_id": str(project_id), "waive_prerequisites": True, "waiver_justification": "Waiver"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )

    # 2. Member 0 submits deliverable (Attempt #1)
    sub1_res = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/submissions",
        json={
            "submitted_by_candidate_id": str(cand_ids[0]),
            "repo_url": "https://github.com/excelr-student/enterprise-cloud",
            "live_demo_url": "https://enterprise-cloud.vercel.app",
            "notes": "Initial milestone submission for evaluation",
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert sub1_res.status_code == 201
    sub1 = sub1_res.json()
    assert sub1["attempt_number"] == 1
    assert sub1["status"] == "SUBMITTED"

    # Verify group readiness is SUBMITTED
    grp_check = await async_client.get(
        f"/api/v1/projects/groups/{group_id}",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert grp_check.json()["readiness_status"] == "SUBMITTED"

    # 3. Reviewer evaluates Attempt #1 with CORRECTIONS_REQUESTED
    rev1_res = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/submissions/{sub1['id']}/review",
        json={
            "status": "CORRECTIONS_REQUESTED",
            "score": 45.0,
            "feedback": "Database indexes missing and ER diagram is incomplete.",
            "rubric_scores": [{"criterion": "Schema", "score": 20.0, "max": 50.0}],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert rev1_res.status_code == 200
    assert rev1_res.json()["status"] == "CORRECTIONS_REQUESTED"

    # Group readiness should be CORRECTIONS_REQUESTED
    grp_check2 = await async_client.get(
        f"/api/v1/projects/groups/{group_id}",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert grp_check2.json()["readiness_status"] == "CORRECTIONS_REQUESTED"

    # 4. Member 1 submits revised deliverable (Attempt #2)
    sub2_res = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/submissions",
        json={
            "submitted_by_candidate_id": str(cand_ids[1]),
            "repo_url": "https://github.com/excelr-student/enterprise-cloud",
            "live_demo_url": "https://enterprise-cloud.vercel.app",
            "notes": "Revised schema with PostgreSQL B-Tree indexes attached.",
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert sub2_res.status_code == 201
    assert sub2_res.json()["attempt_number"] == 2

    # 5. Reviewer approves Attempt #2
    rev2_res = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/submissions/{sub2_res.json()['id']}/review",
        json={
            "status": "APPROVED",
            "score": 92.5,
            "feedback": "Outstanding architectural revision.",
            "rubric_scores": [{"criterion": "Schema", "score": 50.0, "max": 50.0}],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert rev2_res.status_code == 200
    assert rev2_res.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_collaborative_group_readiness_state_machine(async_client: AsyncClient):
    """
    Verifies BR-GRP-01, AC-GRP-001, AC-GRP-002:
    - Group of 3 members with APPROVED deliverable.
    - C1 signs off -> group status remains BLOCKED_PENDING_MEMBERS.
    - C2 signs off -> group status remains BLOCKED_PENDING_MEMBERS.
    - C3 signs off -> group automatically transitions to READY_FOR_NEXT_PROJECT.
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    cand_ids = await provision_candidates(async_client, admin_auth, batch_id, count=3)
    project_id = await provision_project_spec(async_client, admin_auth, track_id)

    # 1. Create and allocate
    grp_res = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Collaborative Team 10",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(c) for c in cand_ids],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    group_id = grp_res.json()["id"]

    await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocate-project",
        json={"project_id": str(project_id), "waive_prerequisites": True, "waiver_justification": "Waiver"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )

    # 2. Submit & approve deliverable
    sub_res = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/submissions",
        json={"submitted_by_candidate_id": str(cand_ids[0]), "repo_url": "https://github.com/team10/app"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    sub_id = sub_res.json()["id"]

    await async_client.post(
        f"/api/v1/projects/groups/{group_id}/submissions/{sub_id}/review",
        json={"status": "APPROVED", "score": 88.0, "feedback": "Approved!"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )

    # 3. Check readiness before any candidate requests
    readiness0 = await async_client.get(
        f"/api/v1/projects/groups/{group_id}/readiness",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    r0 = readiness0.json()
    assert r0["deliverable_approved"] is True
    assert r0["can_advance"] is False
    assert len(r0["pending_candidate_ids"]) == 3
    assert len(r0["ready_candidate_ids"]) == 0

    # 4. Candidate 0 requests progression
    r_c0 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/progression-request",
        json={"candidate_id": str(cand_ids[0]), "notes": "Candidate 0 finished milestone."},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert r_c0.status_code == 200
    assert r_c0.json()["readiness_status"] == "BLOCKED_PENDING_MEMBERS"
    assert r_c0.json()["can_advance"] is False
    assert len(r_c0.json()["pending_candidate_ids"]) == 2

    # 5. Candidate 1 requests progression
    r_c1 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/progression-request",
        json={"candidate_id": str(cand_ids[1]), "notes": "Candidate 1 finished milestone."},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert r_c1.status_code == 200
    assert r_c1.json()["readiness_status"] == "BLOCKED_PENDING_MEMBERS"
    assert len(r_c1.json()["pending_candidate_ids"]) == 1
    assert r_c1.json()["pending_candidate_ids"][0] == str(cand_ids[2])

    # 6. Candidate 2 requests progression -> ALL MEMBERS READY!
    r_c2 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/progression-request",
        json={"candidate_id": str(cand_ids[2]), "notes": "Candidate 2 finished milestone."},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert r_c2.status_code == 200
    assert r_c2.json()["readiness_status"] == "READY_FOR_NEXT_PROJECT"
    assert r_c2.json()["can_advance"] is True
    assert len(r_c2.json()["pending_candidate_ids"]) == 0
    assert len(r_c2.json()["ready_candidate_ids"]) == 3


@pytest.mark.asyncio
async def test_inactive_member_removal_recalculates_readiness(async_client: AsyncClient):
    """
    Verifies AC-GRP-003:
    - Group of 3 members (C0, C1, C2).
    - C0 and C1 submit progression requests, C2 is inactive.
    - Group is in BLOCKED_PENDING_MEMBERS.
    - Coordinator removes C2 with reason 'Student inactive > 14 days'.
    - Group immediately recalculates readiness with remaining members (C0, C1)
      and transitions to READY_FOR_NEXT_PROJECT.
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    cand_ids = await provision_candidates(async_client, admin_auth, batch_id, count=3)
    project_id = await provision_project_spec(async_client, admin_auth, track_id)

    # 1. Setup group and approve deliverable
    grp_res = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Reconstitution Squad",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(c) for c in cand_ids],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    group_id = grp_res.json()["id"]

    await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocate-project",
        json={"project_id": str(project_id), "waive_prerequisites": True, "waiver_justification": "Waiver"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )

    sub_res = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/submissions",
        json={"submitted_by_candidate_id": str(cand_ids[0]), "repo_url": "https://github.com/reconstitute/app"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    sub_id = sub_res.json()["id"]

    await async_client.post(
        f"/api/v1/projects/groups/{group_id}/submissions/{sub_id}/review",
        json={"status": "APPROVED", "score": 90.0, "feedback": "Approved!"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )

    # 2. C0 and C1 request progression
    await async_client.post(
        f"/api/v1/projects/groups/{group_id}/progression-request",
        json={"candidate_id": str(cand_ids[0])},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    await async_client.post(
        f"/api/v1/projects/groups/{group_id}/progression-request",
        json={"candidate_id": str(cand_ids[1])},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )

    # Verify group is currently blocked awaiting C2
    readiness_before = await async_client.get(
        f"/api/v1/projects/groups/{group_id}/readiness",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert readiness_before.json()["readiness_status"] == "BLOCKED_PENDING_MEMBERS"
    assert readiness_before.json()["can_advance"] is False
    assert readiness_before.json()["pending_candidate_ids"] == [str(cand_ids[2])]

    # 3. Coordinator removes inactive C2 with documented reason
    remove_res = await async_client.delete(
        f"/api/v1/projects/groups/{group_id}/members/{cand_ids[2]}?reason=Student%20inactive%20%3E%2014%20days",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert remove_res.status_code == 200

    # 4. Group readiness must immediately recalculate to READY_FOR_NEXT_PROJECT!
    readiness_after = await async_client.get(
        f"/api/v1/projects/groups/{group_id}/readiness",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert readiness_after.json()["readiness_status"] == "READY_FOR_NEXT_PROJECT"
    assert readiness_after.json()["can_advance"] is True
    assert len(readiness_after.json()["pending_candidate_ids"]) == 0
    assert len(readiness_after.json()["ready_candidate_ids"]) == 2


@pytest.mark.asyncio
async def test_multi_project_advancement_and_max_cap(async_client: AsyncClient):
    """
    Verifies:
    1. Tier 1 advancement to Tier 2.
    2. Tier 2 advancement to Tier 3 (Capstone).
    3. Tier 3 advancement completes the project track (group completed, readiness completed).
    4. BR-PRJ-02 & AC-PRJ-002: Attempting to allocate a 4th project to candidate is blocked with HTTP 422.
    """
    admin_auth = await login_as_admin(async_client)
    batch_id, track_id = await provision_batch_and_track()
    cand_ids = await provision_candidates(async_client, admin_auth, batch_id, count=2)

    # Provision Tier 1, Tier 2, and Tier 3 specifications
    p1_id = await provision_project_spec(async_client, admin_auth, track_id, tier="TIER_1_FOUNDATIONAL")
    p2_id = await provision_project_spec(async_client, admin_auth, track_id, tier="TIER_2_INTERMEDIATE")
    p3_id = await provision_project_spec(async_client, admin_auth, track_id, tier="TIER_3_CAPSTONE")

    # 1. Allocate Project 1
    grp_res = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Capstone Highflyers",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(c) for c in cand_ids],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    group_id = grp_res.json()["id"]

    await async_client.post(
        f"/api/v1/projects/groups/{group_id}/allocate-project",
        json={"project_id": str(p1_id), "waive_prerequisites": True, "waiver_justification": "P1 Waiver"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )

    # Helper function to submit, approve, and sign off
    async def complete_current_project(p_id: uuid.UUID):
        sub = await async_client.post(
            f"/api/v1/projects/groups/{group_id}/submissions",
            json={"submitted_by_candidate_id": str(cand_ids[0]), "repo_url": "https://github.com/flyers/repo"},
            cookies=admin_auth["cookies"],
            headers=admin_auth["headers"],
        )
        await async_client.post(
            f"/api/v1/projects/groups/{group_id}/submissions/{sub.json()['id']}/review",
            json={"status": "APPROVED", "score": 95.0, "feedback": "Approved"},
            cookies=admin_auth["cookies"],
            headers=admin_auth["headers"],
        )
        for cid in cand_ids:
            await async_client.post(
                f"/api/v1/projects/groups/{group_id}/progression-request",
                json={"candidate_id": str(cid)},
                cookies=admin_auth["cookies"],
                headers=admin_auth["headers"],
            )

    # Complete Project 1
    await complete_current_project(p1_id)

    # 2. Advance to Project 2 (Tier 2)
    adv1 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/advance",
        json={"next_project_id": str(p2_id)},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert adv1.status_code == 200
    assert adv1.json()["project_id"] == str(p2_id)
    assert adv1.json()["group_status"] == "ACTIVE"

    # Complete Project 2
    await complete_current_project(p2_id)

    # 3. Advance to Project 3 (Tier 3 Capstone)
    adv2 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/advance",
        json={"next_project_id": str(p3_id)},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert adv2.status_code == 200
    assert adv2.json()["project_id"] == str(p3_id)

    # Complete Project 3 (Capstone)
    await complete_current_project(p3_id)

    # 4. Advance from Capstone -> Group reaches COMPLETED!
    adv3 = await async_client.post(
        f"/api/v1/projects/groups/{group_id}/advance",
        json={},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert adv3.status_code == 200
    assert adv3.json()["group_status"] == "COMPLETED"
    assert adv3.json()["readiness_status"] == "COMPLETED"

    # 5. BR-PRJ-02 & AC-PRJ-002: Attempting to allocate a 4th project to cand_0
    # Create new group for cand_0 and another candidate
    extra_cand = await provision_candidates(async_client, admin_auth, batch_id, count=1)
    g_extra = await async_client.post(
        "/api/v1/projects/groups",
        json={
            "batch_id": str(batch_id),
            "group_name": "Post-Capstone Group",
            "min_size": 2,
            "max_size": 5,
            "initial_candidate_ids": [str(cand_ids[0]), str(extra_cand[0])],
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    g_extra_id = g_extra.json()["id"]

    # Provision a 4th project specification
    p4_id = await provision_project_spec(async_client, admin_auth, track_id, tier="TIER_3_CAPSTONE")

    # Allocation of 4th project must be blocked with HTTP 422!
    p4_res = await async_client.post(
        f"/api/v1/projects/groups/{g_extra_id}/allocate-project",
        json={"project_id": str(p4_id), "waive_prerequisites": True, "waiver_justification": "Attempt 4"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert p4_res.status_code == 422
    assert "Maximum standard project limit (3) reached for Candidate" in p4_res.json()["detail"]
