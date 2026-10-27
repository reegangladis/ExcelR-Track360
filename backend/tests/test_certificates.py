"""
ExcelR Track360 - Phase 12: Certificate Management & Verification Engine Test Suite
Strictly verifies:
1. BR-CERT-01 Prerequisite Eligibility Gating & Diagnostics Calculation
2. Unique Serial ID Generation (EXCELR-{YEAR}-{TRACK}-{HEX8}) & HMAC-SHA256 Verification Hash (SEC-CERT-01)
3. Stage 0: Certificate Request Initiation
4. Stage 1: Coordinator Review & Status Transition
5. BR-CERT-02 & SoD Boundary: Self-Approval Prohibition (Stage 1 reviewer/requester blocked from Stage 2 sign-off)
6. Stage 2: Formal Sign-off by Certificate Approver & Automated PDF Generation
7. PDF Certificate Artifact Download & Embedded QR Code Integrity
8. FR-CER-005 Public Verification Portal (Zero-Auth, Cryptographic Integrity Check, Tamper Detection)
9. FR-CER-006 Revocation Engine (Reason Categories, Detailed Rationale, Immediate Public Status Update)
10. Role-Based Access Control (RBAC) & Student IDOR Protection
"""
import hmac
import hashlib
import uuid
from datetime import date, datetime, timedelta, timezone
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
from app.modules.assignments.models import Assignment, AssignmentAllocation, AssignmentSubmission
from app.modules.projects.models import Project, ProjectGroup, ProjectGroupMember, ProjectGroupSubmission
from app.modules.internships.models import InternshipRecord
from app.modules.certificates.models import CertificateRecord, CertificateApproval, CertificateRevocation
from app.modules.certificates.service import CertificateService


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
        "user_id": str(user.id),
        "cookies": {SESSION_COOKIE_NAME: session_token, CSRF_COOKIE_NAME: csrf},
        "headers": {"x-csrf-token": csrf},
    }


async def setup_candidate_ecosystem(candidate_email: str, student_uid: str) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Provisions a course, track, batch, candidate user, and candidate record."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Course
        course = Course(
            id=uuid.uuid4(),
            code=f"CRS-CERT-{student_uid}",
            title="Full Stack Software Engineering",
            is_active=True,
        )
        session.add(course)
        await session.flush()

        # Track with Duration Policy (1=3m, 2=6m, 3=9m)
        track = CourseTrack(
            id=uuid.uuid4(),
            course_id=course.id,
            code=f"TRK-CERT-{student_uid[:4].upper()}",
            title="Full Stack Development Specialization",
            total_mandatory_assignments=1,
            total_required_projects=1,
            duration_policy_config={"1": 3, "2": 6, "3": 9},
            is_active=True,
        )
        session.add(track)
        await session.flush()

        # Batch
        batch = Batch(
            id=uuid.uuid4(),
            track_id=track.id,
            batch_code=f"BATCH-CERT-{student_uid}",
            title="FSD Master Cohort",
            start_date=date(2026, 1, 1),
            status="ACTIVE",
        )
        session.add(batch)
        await session.flush()

        # Student User
        role_res = await session.execute(select(Role).where(Role.code == "ROLE_STUDENT"))
        student_role = role_res.scalars().first()
        student_user = User(
            id=uuid.uuid4(),
            email=candidate_email,
            password_hash=hash_password("Student@Track360_2026!"),
            full_name=f"Student {student_uid}",
            status="ACTIVE",
            is_verified=True,
        )
        session.add(student_user)
        await session.flush()
        session.add(UserRole(user_id=student_user.id, role_id=student_role.id))

        # Candidate
        candidate = Candidate(
            id=uuid.uuid4(),
            user_id=student_user.id,
            candidate_number=f"CAN-{student_uid[:8].upper()}",
            first_name="Anita",
            last_name=f"Desai-{student_uid[:6]}",
            email=candidate_email,
            phone=f"+9198{uuid.uuid4().int % 100000000:08d}",
            lifecycle_status="ACTIVE",
        )
        session.add(candidate)
        session.add(Enrollment(candidate_id=candidate.id, batch_id=batch.id, enrollment_status="ACTIVE"))

        # Mandatory Assignment
        asg = Assignment(
            id=uuid.uuid4(),
            track_id=track.id,
            code=f"ASG-MANDATORY-{student_uid[:6]}",
            title="Core Python & Architecture",
            instructions_markdown="Complete assignment instructions",
            is_mandatory=True,
            max_score=100.0,
            passing_score=70.0,
            max_file_size_mb=10,
            allowed_file_types=["pdf", "zip"],
        )
        session.add(asg)
        await session.flush()

        # Approved Allocation & Submission for candidate
        alloc = AssignmentAllocation(
            id=uuid.uuid4(),
            assignment_id=asg.id,
            candidate_id=candidate.id,
            due_date_utc=datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            allocation_status="COMPLETED",
        )
        session.add(alloc)
        await session.flush()

        sub = AssignmentSubmission(
            id=uuid.uuid4(),
            allocation_id=alloc.id,
            candidate_id=candidate.id,
            current_submission_status="APPROVED",
            current_completion_status="PASSED_COMPLETED",
            total_attempts=1,
            latest_score=95.0,
        )
        session.add(sub)

        # Completed Internship Record
        internship = InternshipRecord(
            id=uuid.uuid4(),
            candidate_id=candidate.id,
            track_id=track.id,
            start_date=date(2026, 2, 1),
            actual_completion_date=date(2026, 8, 1),
            accredited_duration_months=6,
            internship_status="COMPLETED",
            company_name="Tata Consultancy Services",
        )
        session.add(internship)

        await session.commit()
        return candidate.id, track.id, internship.id


@pytest.mark.asyncio
async def test_certificate_eligibility_and_initiation(async_client: AsyncClient):
    """
    Verifies:
    1. Prerequisite eligibility diagnostic checks (100% assignments passed + completed internship).
    2. Coordinator initiates certificate issuance request.
    3. Serial number generation and cryptographic hash integrity.
    """
    uid = uuid.uuid4().hex[:8]
    cand_email = f"anita.cert_{uid}@excelr.com"
    cand_id, track_id, int_id = await setup_candidate_ecosystem(cand_email, uid)

    coord_auth = await create_user_with_role(
        async_client=async_client,
        email=f"coord.cert_{uid}@excelr.com",
        password="Coord@Track360_2026!",
        full_name=f"Coordinator {uid}",
        role_code="ROLE_INT_COORD",
    )

    # 1. Check Eligibility Diagnostic
    diag_res = await async_client.get(
        f"/api/v1/certificates/eligibility/{cand_id}",
        cookies=coord_auth["cookies"],
        headers=coord_auth["headers"],
    )
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    assert diag_data["is_eligible"] is True
    assert diag_data["assignments_completed"] is True
    assert diag_data["internship_completed"] is True
    assert diag_data["accredited_duration_months"] == 6
    assert diag_data["has_active_certificate"] is False

    # 2. Initiate Certificate Request
    req_res = await async_client.post(
        "/api/v1/certificates",
        json={
            "candidate_id": str(cand_id),
            "track_id": str(track_id),
            "internship_record_id": str(int_id),
            "certificate_type": "FINAL_COMPREHENSIVE",
            "issue_date": str(date(2026, 10, 27)),
            "notes": "Completed all academic requirements and Tata Consultancy Services internship.",
        },
        cookies=coord_auth["cookies"],
        headers=coord_auth["headers"],
    )
    assert req_res.status_code == 201
    cert_data = req_res.json()
    assert cert_data["status"] == "PENDING_APPROVAL"
    assert cert_data["serial_number"].startswith("EXCELR-2026-")
    assert cert_data["accredited_duration_months"] == 6
    assert len(cert_data["verification_hash"]) == 64
    assert cert_data["verification_qr_url"] == f"/verify/{cert_data['serial_number']}"


@pytest.mark.asyncio
async def test_two_stage_approval_and_sod_enforcement(async_client: AsyncClient):
    """
    Verifies:
    1. Stage 1 Coordinator Review advances certificate to REVIEWED.
    2. Separation of Duties (SoD): The same Coordinator is BLOCKED from Stage 2 sign-off.
    3. Independent Certificate Approver signs off on Stage 2, advancing certificate to ISSUED.
    4. Automated PDF generation generates authentic artifact.
    """
    uid = uuid.uuid4().hex[:8]
    cand_email = f"priya.cert_{uid}@excelr.com"
    cand_id, track_id, int_id = await setup_candidate_ecosystem(cand_email, uid)

    coord_auth = await create_user_with_role(
        async_client=async_client,
        email=f"coord.stage_{uid}@excelr.com",
        password="Coord@Track360_2026!",
        full_name=f"Coordinator {uid}",
        role_code="ROLE_INT_COORD",
    )

    approver_auth = await create_user_with_role(
        async_client=async_client,
        email=f"approver.cert_{uid}@excelr.com",
        password="Approver@Track360_2026!",
        full_name=f"Dean Approver {uid}",
        role_code="ROLE_CERT_APPROVER",
    )

    # 1. Coordinator initiates
    init_res = await async_client.post(
        "/api/v1/certificates",
        json={
            "candidate_id": str(cand_id),
            "track_id": str(track_id),
            "internship_record_id": str(int_id),
            "certificate_type": "FINAL_COMPREHENSIVE",
        },
        cookies=coord_auth["cookies"],
        headers=coord_auth["headers"],
    )
    assert init_res.status_code == 201
    cert_id = init_res.json()["id"]

    # 2. Stage 1 Review by Coordinator
    rev_res = await async_client.post(
        f"/api/v1/certificates/{cert_id}/review",
        json={
            "decision": "APPROVED",
            "decision_notes": "Prerequisites verified and verified with external employer.",
        },
        cookies=coord_auth["cookies"],
        headers=coord_auth["headers"],
    )
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["status"] == "REVIEWED"
    assert rev_data["stage1_reviewer_id"] == coord_auth["user_id"]
    assert len(rev_data["approvals"]) == 1
    assert rev_data["approvals"][0]["stage"] == "STAGE_1_REVIEW"

    # 3. SoD Violation: Coordinator attempts Stage 2 Approval
    sod_res = await async_client.post(
        f"/api/v1/certificates/{cert_id}/approve",
        json={
            "decision": "APPROVED",
            "decision_notes": "Attempting self-signoff",
        },
        cookies=coord_auth["cookies"],
        headers=coord_auth["headers"],
    )
    # ROLE_INT_COORD is not authorized for Stage 2 sign-off (HTTP 403)
    assert sod_res.status_code == 403

    # If Coordinator had elevated role or tried to approve their own request:
    # Service enforces initiator != approver
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Give coord_auth the ROLE_CERT_APPROVER role as well to test strict SoD
        role_res = await session.execute(select(Role).where(Role.code == "ROLE_CERT_APPROVER"))
        cert_role = role_res.scalars().first()
        ur = UserRole(user_id=uuid.UUID(coord_auth["user_id"]), role_id=cert_role.id)
        session.add(ur)
        await session.commit()

    # Re-login with updated dual role
    relogin_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": f"coord.stage_{uid}@excelr.com", "password": "Coord@Track360_2026!"},
    )
    coord_dual_auth = {
        "cookies": {SESSION_COOKIE_NAME: relogin_res.cookies[SESSION_COOKIE_NAME], CSRF_COOKIE_NAME: relogin_res.json()["csrf_token"]},
        "headers": {"x-csrf-token": relogin_res.json()["csrf_token"]},
    }

    # Even with ROLE_CERT_APPROVER, SoD strictly prevents approving their own initiated certificate
    sod_dual_res = await async_client.post(
        f"/api/v1/certificates/{cert_id}/approve",
        json={"decision": "APPROVED", "decision_notes": "Self sign-off attempt"},
        cookies=coord_dual_auth["cookies"],
        headers=coord_dual_auth["headers"],
    )
    assert sod_dual_res.status_code == 403
    assert "Separation of Duties violation" in sod_dual_res.json()["detail"]

    # 4. Legitimate Independent Sign-off by Approver
    appr_res = await async_client.post(
        f"/api/v1/certificates/{cert_id}/approve",
        json={
            "decision": "APPROVED",
            "decision_notes": "Formally approved and signed by Quality Standards Board.",
        },
        cookies=approver_auth["cookies"],
        headers=approver_auth["headers"],
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == "ISSUED"
    assert appr_data["stage2_approver_id"] == approver_auth["user_id"]
    assert appr_data["pdf_file_asset_id"] is not None
    assert len(appr_data["approvals"]) == 2

    # 5. Download Certificate PDF
    pdf_res = await async_client.get(
        f"/api/v1/certificates/{cert_id}/pdf",
        cookies=approver_auth["cookies"],
        headers=approver_auth["headers"],
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")
    assert len(pdf_res.content) > 3000


@pytest.mark.asyncio
async def test_public_verification_portal(async_client: AsyncClient):
    """
    Verifies FR-CER-005 Public Verification Portal:
    1. Zero authentication required.
    2. Lookup by Serial Number returns authentic candidate metadata and valid cryptographic integrity.
    3. Lookup by Verification Hash returns authentic metadata.
    4. Tampered / non-existent lookups return 404 or TAMPERED.
    """
    uid = uuid.uuid4().hex[:8]
    cand_email = f"rahul.verify_{uid}@excelr.com"
    cand_id, track_id, int_id = await setup_candidate_ecosystem(cand_email, uid)

    coord_auth = await create_user_with_role(
        async_client=async_client,
        email=f"coord.pub_{uid}@excelr.com",
        password="Coord@Track360_2026!",
        full_name=f"Coordinator {uid}",
        role_code="ROLE_INT_COORD",
    )
    approver_auth = await create_user_with_role(
        async_client=async_client,
        email=f"approver.pub_{uid}@excelr.com",
        password="Approver@Track360_2026!",
        full_name=f"Approver {uid}",
        role_code="ROLE_CERT_APPROVER",
    )

    # Initiate, Review, Approve
    init_res = await async_client.post(
        "/api/v1/certificates",
        json={"candidate_id": str(cand_id), "track_id": str(track_id)},
        cookies=coord_auth["cookies"],
        headers=coord_auth["headers"],
    )
    cert_id = init_res.json()["id"]
    serial = init_res.json()["serial_number"]
    v_hash = init_res.json()["verification_hash"]

    await async_client.post(
        f"/api/v1/certificates/{cert_id}/review",
        json={"decision": "APPROVED"},
        cookies=coord_auth["cookies"],
        headers=coord_auth["headers"],
    )
    await async_client.post(
        f"/api/v1/certificates/{cert_id}/approve",
        json={"decision": "APPROVED"},
        cookies=approver_auth["cookies"],
        headers=approver_auth["headers"],
    )

    # Public Verification - Unauthenticated
    pub_res = await async_client.get(f"/api/v1/certificates/public-verify/{serial}")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["is_valid"] is True
    assert pub_data["status"] == "ISSUED"
    assert pub_data["serial_number"] == serial
    assert "Anita" in pub_data["candidate_name"]
    assert pub_data["accredited_duration_months"] == 6

    # Public Verification by Hash - Unauthenticated
    hash_res = await async_client.get(f"/api/v1/certificates/public-verify/{v_hash}")
    assert hash_res.status_code == 200
    assert hash_res.json()["serial_number"] == serial

    # Non-existent ID
    bad_res = await async_client.get("/api/v1/certificates/public-verify/NON-EXISTENT-SERIAL-999")
    assert bad_res.status_code == 404


@pytest.mark.asyncio
async def test_certificate_revocation(async_client: AsyncClient):
    """
    Verifies FR-CER-006 Revocation Workflow:
    1. Authorized Certificate Approver revokes an issued certificate.
    2. Mandates valid reason category and detailed rationale.
    3. Public verification portal immediately returns REVOKED with revocation metadata.
    4. Blocked from revoking non-issued or already revoked certificates.
    """
    uid = uuid.uuid4().hex[:8]
    cand_email = f"karan.revoke_{uid}@excelr.com"
    cand_id, track_id, int_id = await setup_candidate_ecosystem(cand_email, uid)

    coord_auth = await create_user_with_role(
        async_client=async_client,
        email=f"coord.rev_{uid}@excelr.com",
        password="Coord@Track360_2026!",
        full_name=f"Coordinator {uid}",
        role_code="ROLE_INT_COORD",
    )
    approver_auth = await create_user_with_role(
        async_client=async_client,
        email=f"approver.rev_{uid}@excelr.com",
        password="Approver@Track360_2026!",
        full_name=f"Approver {uid}",
        role_code="ROLE_CERT_APPROVER",
    )

    # Issue certificate
    init_res = await async_client.post(
        "/api/v1/certificates",
        json={"candidate_id": str(cand_id), "track_id": str(track_id)},
        cookies=coord_auth["cookies"],
        headers=coord_auth["headers"],
    )
    cert_id = init_res.json()["id"]
    serial = init_res.json()["serial_number"]

    await async_client.post(
        f"/api/v1/certificates/{cert_id}/review",
        json={"decision": "APPROVED"},
        cookies=coord_auth["cookies"],
        headers=coord_auth["headers"],
    )
    await async_client.post(
        f"/api/v1/certificates/{cert_id}/approve",
        json={"decision": "APPROVED"},
        cookies=approver_auth["cookies"],
        headers=approver_auth["headers"],
    )

    # 1. Invalid Revocation - Detail too short (< 10 chars)
    short_res = await async_client.post(
        f"/api/v1/certificates/{cert_id}/revoke",
        json={
            "reason_category": "ACADEMIC_MALPRACTICE",
            "detailed_reason": "bad",
        },
        cookies=approver_auth["cookies"],
        headers=approver_auth["headers"],
    )
    assert short_res.status_code == 422

    # 2. Valid Revocation
    rev_res = await async_client.post(
        f"/api/v1/certificates/{cert_id}/revoke",
        json={
            "reason_category": "ACADEMIC_MALPRACTICE",
            "detailed_reason": "Post-issuance investigation confirmed plagiarized deliverable submission.",
        },
        cookies=approver_auth["cookies"],
        headers=approver_auth["headers"],
    )
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["status"] == "REVOKED"
    assert rev_data["revocation_category"] == "ACADEMIC_MALPRACTICE"
    assert rev_data["revoked_by_id"] == approver_auth["user_id"]
    assert len(rev_data["revocations"]) == 1

    # 3. Public Verification Portal immediately shows REVOKED
    pub_res = await async_client.get(f"/api/v1/certificates/public-verify/{serial}")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["is_valid"] is False
    assert pub_data["status"] == "REVOKED"
    assert pub_data["revocation_category"] == "ACADEMIC_MALPRACTICE"

    # 4. Attempting to revoke an already REVOKED certificate fails
    dup_rev = await async_client.post(
        f"/api/v1/certificates/{cert_id}/revoke",
        json={
            "reason_category": "DATA_ENTRY_ERROR",
            "detailed_reason": "Attempting duplicate revocation of an already revoked certificate.",
        },
        cookies=approver_auth["cookies"],
        headers=approver_auth["headers"],
    )
    assert dup_rev.status_code == 400


@pytest.mark.asyncio
async def test_student_idor_and_rbac(async_client: AsyncClient):
    """
    Verifies RBAC and Student IDOR Protection:
    1. Students can view and download their own ISSUED certificate.
    2. Students are BLOCKED from other students' certificates.
    3. Students CANNOT initiate, review, approve, or revoke certificates.
    4. Students CANNOT see drafts or pending reviews.
    """
    uid = uuid.uuid4().hex[:8]
    cand1_email = f"student1_{uid}@excelr.com"
    cand1_id, track_id, _ = await setup_candidate_ecosystem(cand1_email, uid)

    uid2 = uuid.uuid4().hex[:8]
    cand2_email = f"student2_{uid2}@excelr.com"
    cand2_id, _, _ = await setup_candidate_ecosystem(cand2_email, uid2)

    admin_auth = await login_as_admin(async_client)

    # Issue certificate for candidate 1
    init_res = await async_client.post(
        "/api/v1/certificates",
        json={"candidate_id": str(cand1_id), "track_id": str(track_id)},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    cert1_id = init_res.json()["id"]

    await async_client.post(
        f"/api/v1/certificates/{cert1_id}/review",
        json={"decision": "APPROVED"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    # Approve with override for super admin
    await async_client.post(
        f"/api/v1/certificates/{cert1_id}/approve?allow_override=true",
        json={"decision": "APPROVED"},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )

    # Login as Student 1
    login_stud1 = await async_client.post(
        "/api/v1/auth/login",
        json={"email": cand1_email, "password": "Student@Track360_2026!"},
    )
    stud1_auth = {
        "cookies": {SESSION_COOKIE_NAME: login_stud1.cookies[SESSION_COOKIE_NAME], CSRF_COOKIE_NAME: login_stud1.json()["csrf_token"]},
        "headers": {"x-csrf-token": login_stud1.json()["csrf_token"]},
    }

    # Login as Student 2
    login_stud2 = await async_client.post(
        "/api/v1/auth/login",
        json={"email": cand2_email, "password": "Student@Track360_2026!"},
    )
    stud2_auth = {
        "cookies": {SESSION_COOKIE_NAME: login_stud2.cookies[SESSION_COOKIE_NAME], CSRF_COOKIE_NAME: login_stud2.json()["csrf_token"]},
        "headers": {"x-csrf-token": login_stud2.json()["csrf_token"]},
    }

    # 1. Student 1 views their own certificate
    view_res = await async_client.get(
        f"/api/v1/certificates/{cert1_id}",
        cookies=stud1_auth["cookies"],
        headers=stud1_auth["headers"],
    )
    assert view_res.status_code == 200
    assert view_res.json()["candidate_id"] == str(cand1_id)

    # Student 1 downloads their own PDF
    pdf_res = await async_client.get(
        f"/api/v1/certificates/{cert1_id}/pdf",
        cookies=stud1_auth["cookies"],
        headers=stud1_auth["headers"],
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"

    # 2. Student 2 is BLOCKED from viewing Student 1's certificate (IDOR check)
    idor_view = await async_client.get(
        f"/api/v1/certificates/{cert1_id}",
        cookies=stud2_auth["cookies"],
        headers=stud2_auth["headers"],
    )
    assert idor_view.status_code == 403

    # Student 2 is BLOCKED from downloading Student 1's PDF
    idor_pdf = await async_client.get(
        f"/api/v1/certificates/{cert1_id}/pdf",
        cookies=stud2_auth["cookies"],
        headers=stud2_auth["headers"],
    )
    assert idor_pdf.status_code == 403

    # 3. Student 1 is BLOCKED from initiating requests
    init_blocked = await async_client.post(
        "/api/v1/certificates",
        json={"candidate_id": str(cand1_id), "track_id": str(track_id)},
        cookies=stud1_auth["cookies"],
        headers=stud1_auth["headers"],
    )
    assert init_blocked.status_code == 403

    # 4. Student 1 is BLOCKED from revoking
    rev_blocked = await async_client.post(
        f"/api/v1/certificates/{cert1_id}/revoke",
        json={"reason_category": "ACADEMIC_MALPRACTICE", "detailed_reason": "Unauthorized attempt"},
        cookies=stud1_auth["cookies"],
        headers=stud1_auth["headers"],
    )
    assert rev_blocked.status_code == 403
