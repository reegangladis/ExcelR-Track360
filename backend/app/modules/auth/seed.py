"""
ExcelR Track360 - RBAC Seed & Initial Provisioning
Populates core system roles, permissions, role-permission matrix,
and optional developer/administrator bootstrap account.
Strictly adheres to URP-TRK360-V1.0 specifications.
"""
from typing import Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import hash_password, utc_now
from app.modules.auth.models import Role, Permission, RolePermission, User, UserRole

# Standard System Roles (code, name, description)
SYSTEM_ROLES: List[Tuple[str, str, str]] = [
    ("ROLE_SUPER_ADMIN", "Super Administrator", "Global platform administration, user provisioning, role assignments, system-wide config, and unconstrained audit access."),
    ("ROLE_OPS_ADMIN", "Operations Administrator", "Daily operational supervision, batch creation, course setup, reviewer queue balancing, and operational exception handling."),
    ("ROLE_CAN_COORD", "Candidate Coordinator", "Candidate onboarding, profile maintenance, batch CSV bulk ingestion, contact updates, and enrollment verification."),
    ("ROLE_ASG_REVIEWER", "Assignment Reviewer", "Evaluating student assignment submissions, grading against rubrics, authoring feedback, and approving/requesting revisions."),
    ("ROLE_PRJ_COORD", "Project Coordinator", "Managing project repository, forming student groups, monitoring group collaboration, evaluating deliverables, and group progression."),
    ("ROLE_INT_COORD", "Internship Coordinator", "Monitoring candidate progression toward internship criteria, logging start/end dates, and tracking completion."),
    ("ROLE_CERT_APPROVER", "Certificate Approver", "Independent verification of completed prerequisites, formal electronic approval of credentials, and certificate revocation."),
    ("ROLE_READ_ONLY", "Reporting / Read-Only User", "Monitoring dashboards, inspecting SLA compliance, and generating scheduled analytics reports without write/approve capabilities."),
    ("ROLE_STUDENT", "Student / Candidate", "Student portal access, viewing curriculum, submitting individual assignment files, collaborating in assigned project groups, and downloading certificates."),
]

# Standard System Permissions (code, module, description)
SYSTEM_PERMISSIONS: List[Tuple[str, str, str]] = [
    # Candidate Domain
    ("candidate:view_full", "candidate", "View full candidate profile with PII"),
    ("candidate:view_masked", "candidate", "View masked candidate overview (peer safe)"),
    ("candidate:create", "candidate", "Create single candidate profile"),
    ("candidate:import", "candidate", "Batch import candidate roster via CSV"),
    ("candidate:update", "candidate", "Update candidate profile and contact details"),
    ("candidate:status_change", "candidate", "Update lifecycle status (Active, Drop, Archive)"),
    ("candidate:export", "candidate", "Export candidate registry to CSV"),
    
    # Assignment Domain
    ("assignment:template_manage", "assignment", "Create and edit assignment templates and rubrics"),
    ("assignment:allocate", "assignment", "Allocate assignments to cohorts or candidates"),
    ("assignment:submit", "assignment", "Upload and submit assignment solutions"),
    ("assignment:review", "assignment", "Review, score, and provide feedback on submissions"),
    ("assignment:approve", "assignment", "Final passing approval of assignment submission"),
    ("assignment:override", "assignment", "Administrative override of assignment grade or status"),
    ("assignment:view", "assignment", "View submissions and attempt history"),
    
    # Project Domain
    ("project:catalog_manage", "project", "Maintain project catalog, milestones, and deliverables"),
    ("project:group_manage", "project", "Form, resize, and configure project groups"),
    ("project:allocate", "project", "Allocate projects to groups or candidates"),
    ("project:submit", "project", "Upload group project deliverables"),
    ("project:review", "project", "Review and grade group deliverables"),
    ("project:advance", "project", "Advance group to next sequential project"),
    ("project:progression_request", "project", "Candidate request for next project progression"),
    ("project:override", "project", "Administrative group readiness override and member removal"),
    
    # Internship Domain
    ("internship:create", "internship", "Initiate candidate internship record"),
    ("internship:update", "internship", "Update internship calendar dates and supervisor details"),
    ("internship:approve", "internship", "Confirm internship milestone completion"),
    ("internship:override", "internship", "Override internship eligibility rules"),
    ("internship:view", "internship", "View internship records and durations"),
    
    # Certificate Domain
    ("certificate:view", "certificate", "View issued certificates and verification records"),
    ("certificate:request", "certificate", "Submit certificate issuance request"),
    ("certificate:approve", "certificate", "Formally approve certificate issuance request"),
    ("certificate:generate", "certificate", "Generate and sign certificate PDF"),
    ("certificate:revoke", "certificate", "Revoke an issued certificate"),
    
    # System Domain
    ("system:users_manage", "system", "Provision and manage staff users and role assignments"),
    ("system:config_manage", "system", "Modify platform configuration and policy settings"),
    ("system:audit_view", "system", "Inspect complete immutable audit trail"),
    ("system:reports_export", "system", "Generate and export operational reports"),
]

# Role to Permissions Mapping
ROLE_PERMISSION_MAP: Dict[str, List[str]] = {
    "ROLE_SUPER_ADMIN": [p[0] for p in SYSTEM_PERMISSIONS],  # All permissions
    "ROLE_OPS_ADMIN": [
        "candidate:view_full", "candidate:view_masked", "candidate:create", "candidate:import",
        "candidate:update", "candidate:status_change", "candidate:export",
        "assignment:template_manage", "assignment:allocate", "assignment:review", "assignment:approve",
        "assignment:override", "assignment:view",
        "project:catalog_manage", "project:group_manage", "project:allocate", "project:review",
        "project:advance", "project:override",
        "internship:create", "internship:update", "internship:approve", "internship:override", "internship:view",
        "certificate:view", "certificate:request", "certificate:generate",
        "system:audit_view", "system:reports_export",
    ],
    "ROLE_CAN_COORD": [
        "candidate:view_full", "candidate:view_masked", "candidate:create", "candidate:import",
        "candidate:update", "candidate:status_change", "candidate:export",
        "assignment:allocate", "assignment:view",
        "certificate:request", "certificate:view",
        "system:reports_export",
    ],
    "ROLE_ASG_REVIEWER": [
        "candidate:view_masked",
        "assignment:review", "assignment:approve", "assignment:view",
    ],
    "ROLE_PRJ_COORD": [
        "candidate:view_masked",
        "project:catalog_manage", "project:group_manage", "project:allocate",
        "project:review", "project:advance", "project:override",
        "certificate:request", "certificate:view",
        "system:reports_export",
    ],
    "ROLE_INT_COORD": [
        "candidate:view_masked",
        "internship:create", "internship:update", "internship:approve", "internship:view",
        "certificate:request", "certificate:view",
        "system:reports_export",
    ],
    "ROLE_CERT_APPROVER": [
        "candidate:view_masked",
        "certificate:view", "certificate:approve", "certificate:revoke", "certificate:generate",
        "system:reports_export",
    ],
    "ROLE_READ_ONLY": [
        "candidate:view_masked", "candidate:export",
        "assignment:view",
        "internship:view",
        "certificate:view",
        "system:audit_view", "system:reports_export",
    ],
    "ROLE_STUDENT": [
        "candidate:view_masked",
        "assignment:submit", "assignment:view",
        "project:submit", "project:progression_request",
        "internship:view",
        "certificate:view",
    ],
}


async def seed_roles_and_permissions(db: AsyncSession) -> None:
    """Seeds missing roles, permissions, and role-permission junctions idempotently."""
    # 1. Seed Permissions
    existing_perms = await db.execute(select(Permission))
    perm_by_code = {p.code: p for p in existing_perms.scalars().all()}
    
    for code, module, desc in SYSTEM_PERMISSIONS:
        if code not in perm_by_code:
            new_perm = Permission(code=code, module=module, description=desc)
            db.add(new_perm)
            perm_by_code[code] = new_perm
    await db.flush()

    # 2. Seed Roles
    existing_roles = await db.execute(select(Role))
    role_by_code = {r.code: r for r in existing_roles.scalars().all()}

    for code, name, desc in SYSTEM_ROLES:
        if code not in role_by_code:
            new_role = Role(code=code, name=name, description=desc, is_system_role=True)
            db.add(new_role)
            role_by_code[code] = new_role
    await db.flush()

    # 3. Seed Role Permissions
    for role_code, perm_codes in ROLE_PERMISSION_MAP.items():
        role = role_by_code.get(role_code)
        if not role:
            continue
        
        # Query existing permissions assigned to this role
        existing_rp = await db.execute(
            select(RolePermission.permission_id).where(RolePermission.role_id == role.id)
        )
        assigned_perm_ids = set(existing_rp.scalars().all())

        for p_code in perm_codes:
            perm = perm_by_code.get(p_code)
            if perm and perm.id not in assigned_perm_ids:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await db.commit()
    logger.info("Successfully synced roles and permissions in database.")


async def seed_bootstrap_admin(
    db: AsyncSession,
    email: str = "admin@excelr.com",
    password: str = "Admin@Track360_2026!",
    full_name: str = "Master System Administrator",
) -> User:
    """Provisions initial local development administrator if not present."""
    await seed_roles_and_permissions(db)

    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    admin_user = result.scalar_one_or_none()

    if admin_user is None:
        admin_user = User(
            email=email.lower().strip(),
            password_hash=hash_password(password),
            full_name=full_name,
            status="ACTIVE",
            is_verified=True,
        )
        db.add(admin_user)
        await db.flush()

        # Assign ROLE_SUPER_ADMIN
        super_admin_role = (
            await db.execute(select(Role).where(Role.code == "ROLE_SUPER_ADMIN"))
        ).scalar_one()

        db.add(UserRole(user_id=admin_user.id, role_id=super_admin_role.id))
        await db.commit()
        logger.info(f"Created default administrator account: {email}")
    else:
        logger.info(f"Administrator account already exists: {email}")

    return admin_user
