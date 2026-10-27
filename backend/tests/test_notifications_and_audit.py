"""
ExcelR Track360 - Phase 13: In-App Notifications & Audit Trail Explorer Test Suite
Strictly verifies:
1. FR-NOT-001: Event-Driven In-App Notifications (Creation, Unread Counting, Mark Read, Mark All Read)
2. FR-NOT-002: Email Notification Queue & Retry Logging
3. Notification Ownership & Tenant Privacy (Users cannot read/mutate other users' notifications)
4. FR-REP-002: Comprehensive Audit Trail Querying & Filtering
5. FR-REP-003: Governed CSV Data Export & Self-Recording Audit Event
6. RBAC Enforcement on Operational Audit Logs and Email Queue
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.core.security import hash_password
from app.modules.audit.service import write_audit_log
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
from app.modules.auth.models import Role, User, UserRole
from app.modules.auth.seed import seed_bootstrap_admin
from app.modules.notifications.models import EmailQueueItem, NotificationEvent


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
    data = resp.json()
    csrf = data["csrf_token"]
    user_id = data["user"]["id"]
    session_token = resp.cookies[SESSION_COOKIE_NAME]
    return {
        "user_id": user_id,
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


@pytest.mark.asyncio
async def test_notification_event_creation_and_lifecycle(async_client: AsyncClient):
    """Verifies in-app notification dispatch, unread counting, and individual read acknowledgement."""
    admin_auth = await login_as_admin(async_client)
    student_auth = await create_user_with_role(
        async_client,
        email=f"notif_student1_{uuid.uuid4().hex[:6]}@example.com",
        password="StudentPass@123",
        full_name="Aarav Sharma",
        role_code="ROLE_STUDENT",
    )
    student_uid = student_auth["user_id"]

    # 1. Admin dispatches notification to student with email enqueued
    dispatch_resp = await async_client.post(
        "/api/v1/notifications/dispatch",
        json={
            "recipient_user_ids": [student_uid],
            "event_type": "ASSIGNMENT_ALLOCATED",
            "title": "New Assignment Allocation: React Deep Dive",
            "body": "Your instructor has allocated the React Deep Dive assignment to your batch.",
            "action_url": "/assignments/asgn-123",
            "queue_email": True,
            "email_subject": "ExcelR Track360 - Assignment Allocated",
            "email_html": "<h2>New Assignment</h2><p>Please check your student portal.</p>",
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert dispatch_resp.status_code == 201
    created_events = dispatch_resp.json()
    assert len(created_events) == 1
    notif_id = created_events[0]["id"]
    assert created_events[0]["is_read"] is False

    # 2. Student checks unread badge count
    count_resp = await async_client.get(
        "/api/v1/notifications/unread-count",
        cookies=student_auth["cookies"],
        headers=student_auth["headers"],
    )
    assert count_resp.status_code == 200
    assert count_resp.json()["unread_count"] == 1

    # 3. Student lists notifications
    list_resp = await async_client.get(
        "/api/v1/notifications",
        cookies=student_auth["cookies"],
        headers=student_auth["headers"],
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 1
    assert data["unread_count"] == 1
    assert data["items"][0]["id"] == notif_id

    # 4. Student marks notification as read
    mark_resp = await async_client.patch(
        f"/api/v1/notifications/{notif_id}/read",
        cookies=student_auth["cookies"],
        headers=student_auth["headers"],
    )
    assert mark_resp.status_code == 200
    assert mark_resp.json()["is_read"] is True

    # 5. Unread count drops to 0
    count_resp2 = await async_client.get(
        "/api/v1/notifications/unread-count",
        cookies=student_auth["cookies"],
        headers=student_auth["headers"],
    )
    assert count_resp2.status_code == 200
    assert count_resp2.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_all_notifications_read(async_client: AsyncClient):
    """Verifies bulk read acknowledgement across multiple unread notification alerts."""
    admin_auth = await login_as_admin(async_client)
    student_auth = await create_user_with_role(
        async_client,
        email=f"notif_student2_{uuid.uuid4().hex[:6]}@example.com",
        password="StudentPass@123",
        full_name="Bhavna Patel",
        role_code="ROLE_STUDENT",
    )
    student_uid = student_auth["user_id"]

    # Dispatch 3 notifications
    for i in range(3):
        await async_client.post(
            "/api/v1/notifications/dispatch",
            json={
                "recipient_user_ids": [student_uid],
                "event_type": "SYSTEM_ALERT",
                "title": f"System Alert #{i+1}",
                "body": f"Operational notification body {i+1}",
                "queue_email": False,
            },
            cookies=admin_auth["cookies"],
            headers=admin_auth["headers"],
        )

    # Check unread count is 3
    count_resp = await async_client.get(
        "/api/v1/notifications/unread-count",
        cookies=student_auth["cookies"],
        headers=student_auth["headers"],
    )
    assert count_resp.json()["unread_count"] == 3

    # Mark all as read
    mark_all_resp = await async_client.post(
        "/api/v1/notifications/mark-all-read",
        cookies=student_auth["cookies"],
        headers=student_auth["headers"],
    )
    assert mark_all_resp.status_code == 200
    assert mark_all_resp.json()["updated_count"] == 3

    # Unread count is now 0
    count_resp_after = await async_client.get(
        "/api/v1/notifications/unread-count",
        cookies=student_auth["cookies"],
        headers=student_auth["headers"],
    )
    assert count_resp_after.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_notification_ownership_security(async_client: AsyncClient):
    """Ensures unauthorized users cannot mutate another user's notification records."""
    admin_auth = await login_as_admin(async_client)
    student1_auth = await create_user_with_role(
        async_client,
        email=f"owner_{uuid.uuid4().hex[:6]}@example.com",
        password="StudentPass@123",
        full_name="User One",
        role_code="ROLE_STUDENT",
    )
    student2_auth = await create_user_with_role(
        async_client,
        email=f"intruder_{uuid.uuid4().hex[:6]}@example.com",
        password="StudentPass@123",
        full_name="User Two",
        role_code="ROLE_STUDENT",
    )

    # Dispatch to Student 1
    dispatch_resp = await async_client.post(
        "/api/v1/notifications/dispatch",
        json={
            "recipient_user_ids": [student1_auth["user_id"]],
            "event_type": "PRIVATE_ALERT",
            "title": "Private Alert",
            "body": "Confidential academic standing.",
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    notif_id = dispatch_resp.json()[0]["id"]

    # Student 2 tries to mark Student 1's notification as read -> 403 Forbidden
    hack_resp = await async_client.patch(
        f"/api/v1/notifications/{notif_id}/read",
        cookies=student2_auth["cookies"],
        headers=student2_auth["headers"],
    )
    assert hack_resp.status_code == 403
    assert "Access denied" in hack_resp.json()["detail"]


@pytest.mark.asyncio
async def test_email_queue_management_and_retry(async_client: AsyncClient):
    """Verifies transactional email queue inspection, RBAC restriction, and retry scheduling."""
    admin_auth = await login_as_admin(async_client)
    student_email = f"email_queue_{uuid.uuid4().hex[:6]}@example.com"
    student_auth = await create_user_with_role(
        async_client,
        email=student_email,
        password="StudentPass@123",
        full_name="Email Recipient",
        role_code="ROLE_STUDENT",
    )

    # Dispatch notification with email queueing
    await async_client.post(
        "/api/v1/notifications/dispatch",
        json={
            "recipient_user_ids": [student_auth["user_id"]],
            "event_type": "SUBMISSION_RECEIVED",
            "title": "Submission Received",
            "body": "Your project submission has been received by the evaluation queue.",
            "queue_email": True,
            "email_subject": "Track360: Deliverable Received",
        },
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )

    # 1. Student attempts to access email queue -> 403 Forbidden
    student_queue_resp = await async_client.get(
        "/api/v1/notifications/email-queue",
        cookies=student_auth["cookies"],
        headers=student_auth["headers"],
    )
    assert student_queue_resp.status_code == 403

    # 2. Admin inspects email queue
    admin_queue_resp = await async_client.get(
        "/api/v1/notifications/email-queue",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert admin_queue_resp.status_code == 200
    queue_data = admin_queue_resp.json()
    assert queue_data["total"] >= 1
    pending_items = [i for i in queue_data["items"] if i["recipient_email"] == student_email]
    assert len(pending_items) == 1
    queue_item_id = pending_items[0]["id"]
    assert pending_items[0]["delivery_status"] == "PENDING"

    # 3. Simulate failure in database
    session_factory = get_session_factory()
    async with session_factory() as session:
        item = await session.get(EmailQueueItem, uuid.UUID(queue_item_id))
        item.delivery_status = "FAILED"
        item.attempt_count = 5
        item.last_error_message = "SMTP Connection Timeout (504 Gateway Timeout)"
        await session.commit()

    # 4. Admin triggers retry
    retry_resp = await async_client.post(
        "/api/v1/notifications/email-queue/retry-failed",
        json={"queue_ids": [queue_item_id]},
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert retry_resp.status_code == 200
    assert retry_resp.json()["retried_count"] >= 1

    # Verify status changed to RETRYING
    async with session_factory() as session:
        rechecked_item = await session.get(EmailQueueItem, uuid.UUID(queue_item_id))
        assert rechecked_item.delivery_status == "RETRYING"
        assert rechecked_item.next_retry_at_utc is not None


@pytest.mark.asyncio
async def test_audit_logs_and_csv_export(async_client: AsyncClient):
    """Verifies audit trail querying, filtering, RBAC protection, and self-recorded CSV exports."""
    admin_auth = await login_as_admin(async_client)
    student_auth = await create_user_with_role(
        async_client,
        email=f"audit_student_{uuid.uuid4().hex[:6]}@example.com",
        password="StudentPass@123",
        full_name="Chirag Gupta",
        role_code="ROLE_STUDENT",
    )

    action_token = f"WAIVER_{uuid.uuid4().hex[:6].upper()}"

    # 1. Append a custom audit log to the database
    session_factory = get_session_factory()
    async with session_factory() as session:
        await write_audit_log(
            db=session,
            action=action_token,
            actor_id=uuid.UUID(admin_auth["user_id"]),
            resource_type="CANDIDATE_PROFILE",
            resource_id=student_auth["user_id"],
            pre_state={"is_eligible": False},
            details={"is_eligible": True, "waived_assignments": ["ASGN-101"]},
            justification="Academic Director authorized prerequisite waiver for lateral entrant.",
            request_ip="192.168.1.100",
            user_agent="Mozilla/5.0 Test Suite",
        )
        await session.commit()

    # 2. Student attempts to read audit logs -> 403 Forbidden
    student_audit_resp = await async_client.get(
        "/api/v1/audit/logs",
        cookies=student_auth["cookies"],
        headers=student_auth["headers"],
    )
    assert student_audit_resp.status_code == 403

    # 3. Admin queries audit logs filtered by action
    admin_audit_resp = await async_client.get(
        f"/api/v1/audit/logs?action_type={action_token}",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert admin_audit_resp.status_code == 200
    logs_data = admin_audit_resp.json()
    assert logs_data["total"] >= 1
    found_log = logs_data["items"][0]
    assert found_log["action_type"] == action_token
    assert found_log["entity_type"] == "CANDIDATE_PROFILE"
    assert found_log["pre_state"] == {"is_eligible": False}
    assert found_log["post_state"]["is_eligible"] is True
    assert "Academic Director authorized" in found_log["justification"]

    # 4. Admin exports audit logs to CSV
    export_resp = await async_client.get(
        f"/api/v1/audit/logs/export?action_type={action_token}",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers["content-type"]
    assert 'filename="audit_trail_export.csv"' in export_resp.headers["content-disposition"]
    csv_text = export_resp.text
    assert "Audit ID,Timestamp (UTC),Action Type,Entity Type" in csv_text
    assert action_token in csv_text
    assert "CANDIDATE_PROFILE" in csv_text

    # 5. Verify FR-REP-003: Self-recording audit log exists for AUDIT_LOG_EXPORTED
    admin_audit_recheck = await async_client.get(
        "/api/v1/audit/logs?action_type=AUDIT_LOG_EXPORTED",
        cookies=admin_auth["cookies"],
        headers=admin_auth["headers"],
    )
    assert admin_audit_recheck.status_code == 200
    assert admin_audit_recheck.json()["total"] >= 1
    export_log = admin_audit_recheck.json()["items"][0]
    assert export_log["action_type"] == "AUDIT_LOG_EXPORTED"
    assert export_log["entity_type"] == "AUDIT_LOGS"
