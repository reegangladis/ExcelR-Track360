"""
ExcelR Track360 - Projects & Milestones Catalog Test Suite
Phase 8 Verification:
1. Project template CRUD across Tier 1, Tier 2, and Tier 3 Capstones
2. Milestone weight percentage validation (must sum exactly to 100.0%)
3. Search and tier/track filtering
4. Milestone stage addition and update lifecycle
5. RBAC permission guards (project:catalog_manage enforcement)
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.core.security import hash_password
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
from app.modules.auth.models import Role, User, UserRole
from app.modules.auth.seed import seed_bootstrap_admin
from app.modules.candidates.models import Course, CourseTrack


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


async def provision_track() -> uuid.UUID:
    """Provisions a course and course track for project testing."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        uid = uuid.uuid4().hex[:6]
        course = Course(
            id=uuid.uuid4(),
            code=f"CRS_{uid}",
            title=f"Data Analytics Masterclass {uid}",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        track = CourseTrack(
            id=uuid.uuid4(),
            course_id=course.id,
            code=f"TRK_{uid}",
            title=f"Analytics Track {uid}",
            total_mandatory_assignments=3,
            total_required_projects=3,
            is_active=True,
        )
        session.add(track)
        await session.commit()
        return track.id


@pytest.mark.asyncio
async def test_project_crud_and_tier_classification(async_client: AsyncClient):
    """Verifies creating, reading, and updating Project specifications across Tiers."""
    admin_auth = await login_as_admin(async_client)
    track_id = await provision_track()
    uid = uuid.uuid4().hex[:6]

    # 1. Create a Tier 1 Foundational Project with 3 milestones summing to 100%
    create_resp = await async_client.post(
        "/api/v1/projects",
        json={
            "track_id": str(track_id),
            "code": f"PRJ_T1_{uid}",
            "title": "Retail Analytics & Operational Insights",
            "description": "Foundational SQL and BI dashboarding capstone.",
            "tier": "TIER_1_FOUNDATIONAL",
            "complexity": "LOW",
            "min_team_size": 2,
            "max_team_size": 4,
            "passing_score": 65.0,
            "deliverable_specs": [
                {"key": "repo", "title": "GitHub Repo", "deliverable_type": "GIT_REPO", "is_required": True},
                {"key": "dash", "title": "Tableau / PowerBI Dashboard", "deliverable_type": "FILE_UPLOAD", "is_required": True},
            ],
            "rubric_template": [
                {"key": "etl_quality", "title": "ETL Integrity & Schema", "max_points": 50.0},
                {"key": "viz_quality", "title": "Visual Dashboard Storytelling", "max_points": 50.0},
            ],
            "milestones": [
                {
                    "sequence_order": 1,
                    "title": "Milestone 1: Database Schema & ETL Setup",
                    "description": "Star schema modeling and initial data load.",
                    "weight_percentage": 30.0,
                    "max_score": 100.0,
                    "is_mandatory": True,
                },
                {
                    "sequence_order": 2,
                    "title": "Milestone 2: Metric Calculations & Stored Procedures",
                    "description": "Core metric logic and validation.",
                    "weight_percentage": 40.0,
                    "max_score": 100.0,
                    "is_mandatory": True,
                },
                {
                    "sequence_order": 3,
                    "title": "Milestone 3: Interactive Visual Dashboards",
                    "description": "Final user dashboard presentation.",
                    "weight_percentage": 30.0,
                    "max_score": 100.0,
                    "is_mandatory": True,
                },
            ],
        },
        **admin_auth,
    )
    assert create_resp.status_code == 201, create_resp.text
    project_data = create_resp.json()
    project_id = project_data["id"]

    assert project_data["code"] == f"PRJ_T1_{uid}".upper()
    assert project_data["tier"] == "TIER_1_FOUNDATIONAL"
    assert len(project_data["milestones"]) == 3
    assert project_data["milestones"][0]["weight_percentage"] == 30.0
    assert project_data["milestones"][1]["weight_percentage"] == 40.0

    # 2. Get project detail
    get_resp = await async_client.get(f"/api/v1/projects/{project_id}", **admin_auth)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == project_id

    # 3. Update project details
    patch_resp = await async_client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "title": "Retail Analytics & Real-Time Operational Insights (Updated)",
            "complexity": "MEDIUM",
            "passing_score": 70.0,
        },
        **admin_auth,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Retail Analytics & Real-Time Operational Insights (Updated)"
    assert patch_resp.json()["passing_score"] == 70.0


@pytest.mark.asyncio
async def test_milestone_weight_validation(async_client: AsyncClient):
    """Verifies that milestone weights not summing to 100% are rejected with HTTP 422."""
    admin_auth = await login_as_admin(async_client)
    track_id = await provision_track()
    uid = uuid.uuid4().hex[:6]

    # Milestones sum to 80% (invalid)
    resp = await async_client.post(
        "/api/v1/projects",
        json={
            "track_id": str(track_id),
            "code": f"PRJ_INV_{uid}",
            "title": "Invalid Weight Project",
            "tier": "TIER_2_INTERMEDIATE",
            "milestones": [
                {"sequence_order": 1, "title": "Milestone 1", "weight_percentage": 50.0},
                {"sequence_order": 2, "title": "Milestone 2", "weight_percentage": 30.0},
            ],
        },
        **admin_auth,
    )
    assert resp.status_code == 422
    assert "Milestone weight percentages must sum exactly to 100.0%" in resp.text


@pytest.mark.asyncio
async def test_project_search_and_filtering(async_client: AsyncClient):
    """Verifies filtering project catalog by tier, complexity, and search query."""
    admin_auth = await login_as_admin(async_client)
    track_id = await provision_track()
    uid = uuid.uuid4().hex[:6]

    # Create Tier 3 Capstone
    await async_client.post(
        "/api/v1/projects",
        json={
            "track_id": str(track_id),
            "code": f"PRJ_CAP_{uid}",
            "title": f"Enterprise Data Lakehouse & MLOps Pipeline {uid}",
            "tier": "TIER_3_CAPSTONE",
            "complexity": "CRITICAL",
            "milestones": [
                {"sequence_order": 1, "title": "Architecture", "weight_percentage": 50.0},
                {"sequence_order": 2, "title": "Deployment", "weight_percentage": 50.0},
            ],
        },
        **admin_auth,
    )

    # Filter by TIER_3_CAPSTONE
    list_resp = await async_client.get(
        "/api/v1/projects",
        params={"tier": "TIER_3_CAPSTONE", "search": uid},
        **admin_auth,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["tier"] == "TIER_3_CAPSTONE"
    assert items[0]["complexity"] == "CRITICAL"


@pytest.mark.asyncio
async def test_project_rbac_and_permission_isolation(async_client: AsyncClient):
    """Verifies that non-admin/student accounts cannot modify project catalog without permission."""
    admin_auth = await login_as_admin(async_client)
    track_id = await provision_track()

    # Create an unprivileged user
    uid = uuid.uuid4().hex[:6]
    email = f"student_prj_{uid}@example.com"
    pwd = "Student@123456_Secure!"

    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(pwd),
            full_name="Student Reviewer",
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
    stud_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert stud_resp.status_code == 200
    csrf = stud_resp.json()["csrf_token"]
    student_auth = {
        "cookies": {
            SESSION_COOKIE_NAME: stud_resp.cookies[SESSION_COOKIE_NAME],
            CSRF_COOKIE_NAME: csrf,
        },
        "headers": {"x-csrf-token": csrf},
    }

    # Student cannot create project (requires project:catalog_manage) -> 403 Forbidden
    create_resp = await async_client.post(
        "/api/v1/projects",
        json={
            "track_id": str(track_id),
            "code": "PRJ_UNAUTH_01",
            "title": "Unauthorized Project",
            "tier": "TIER_1_FOUNDATIONAL",
        },
        **student_auth,
    )
    assert create_resp.status_code == 403
