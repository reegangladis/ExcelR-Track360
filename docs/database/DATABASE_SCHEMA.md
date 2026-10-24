# Database Schema Specification
## Project: ExcelR Track360
### Student Lifecycle & Operations Management Platform
**Document Reference:** DBS-TRK360-V1.0  
**Phase:** Phase 2 – System Architecture & Database Design  
**Status:** Approved for Implementation Planning  

---

## 1. Relational Conventions & Standards

1. **Engine:** PostgreSQL 15+.
2. **Identifier Datatype:** Primary keys use `UUID` generated via UUIDv7 algorithms.
3. **Temporal Precision:** All timestamps use `TIMESTAMPTZ` (Timestamp with Time Zone), with storage and calculations executing strictly in **Coordinated Universal Time (UTC)**.
4. **Naming Standard:**
   - Table names: `snake_case` plural (e.g. `candidates`, `assignment_allocations`).
   - Column names: `snake_case` (e.g. `first_name`, `submitted_at_utc`).
   - Foreign key columns: `[singular_parent_table]_id` (e.g. `candidate_id`, `batch_id`).
5. **Referential Action Integrity:**
   - Academic master records (courses, tracks, candidates, certificates): `ON DELETE RESTRICT` to prevent accidental loss of historical records.
   - Transient junction records (user roles, role permissions): `ON DELETE CASCADE`.
6. **Data Immutability Guarantee:**
   - Tables storing academic proof (`submission_attempts`, `submission_reviews`, `project_completions`, `certificates`, `audit_logs`) are strictly append-only. No application API or repository shall issue `DELETE` or `UPDATE` queries against finalized attempts or audit records.

---

## 2. DDL Schema Definitions

### 2.1 Domain 1: Identity, RBAC & Server-Managed Sessions

```sql
-- 1. Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(32) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' 
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'LOCKED', 'DEACTIVATED')),
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ NULL,
    last_login_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX uq_users_email_lower ON users (LOWER(TRIM(email)));

-- 2. Roles Table
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    is_system_role BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Permissions Table
CREATE TABLE permissions (
    id UUID PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    module VARCHAR(64) NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. User Roles Junction Table
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (user_id, role_id)
);

-- 5. Role Permissions Junction Table
CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- 6. User Sessions Table (Server-Managed Sessions)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash VARCHAR(64) NOT NULL UNIQUE,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_user_sessions_user_active ON user_sessions (user_id, expires_at) WHERE is_revoked = FALSE;
```

---

### 2.2 Domain 2: Candidates & Academic Cohorts

```sql
-- 7. Courses Table
CREATE TABLE courses (
    id UUID PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. Course Tracks Table
CREATE TABLE course_tracks (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    code VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    total_mandatory_assignments INT NOT NULL DEFAULT 0,
    total_required_projects INT NOT NULL DEFAULT 3,
    duration_policy_config JSONB NOT NULL DEFAULT '{"1": 3, "2": 6, "3": 9}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. Batches Table
CREATE TABLE batches (
    id UUID PRIMARY KEY,
    track_id UUID NOT NULL REFERENCES course_tracks(id) ON DELETE RESTRICT,
    batch_code VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    start_date DATE NOT NULL,
    expected_end_date DATE NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('UPCOMING', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')),
    coordinator_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. Candidates Table (One Authoritative Golden Record)
CREATE TABLE candidates (
    id UUID PRIMARY KEY,
    user_id UUID NULL UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    candidate_number VARCHAR(64) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    alternate_phone VARCHAR(32) NULL,
    academic_qualification VARCHAR(150) NULL,
    lifecycle_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
        CHECK (lifecycle_status IN ('ENROLLED', 'ACTIVE', 'ON_HOLD', 'DROPPED', 'COMPLETED', 'ALUMNI')),
    project_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    completed_projects_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX uq_candidates_email_lower ON candidates (LOWER(TRIM(email)));
CREATE UNIQUE INDEX uq_candidates_phone ON candidates (phone);
CREATE INDEX ix_candidates_lifecycle_eligible ON candidates (lifecycle_status, project_eligible);

-- 11. Enrollments Table
CREATE TABLE enrollments (
    id UUID PRIMARY KEY,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    batch_id UUID NOT NULL REFERENCES batches(id) ON DELETE RESTRICT,
    enrollment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    enrollment_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
        CHECK (enrollment_status IN ('ACTIVE', 'COMPLETED', 'DROPPED', 'TRANSFERRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (candidate_id, batch_id)
);

-- 12. Candidate Notes Table
CREATE TABLE candidate_notes (
    id UUID PRIMARY KEY,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    note_category VARCHAR(64) NOT NULL DEFAULT 'GENERAL',
    note_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

### 2.3 Domain 3: Assignments, Submissions & Evaluation Cycles

```sql
-- 13. File Assets Table (Private Storage Metadata)
CREATE TABLE file_assets (
    id UUID PRIMARY KEY,
    storage_backend VARCHAR(32) NOT NULL DEFAULT 'local' CHECK (storage_backend IN ('local', 's3')),
    storage_key VARCHAR(500) NOT NULL UNIQUE,
    original_filename VARCHAR(255) NOT NULL,
    file_extension VARCHAR(16) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 14. Assignments Table
CREATE TABLE assignments (
    id UUID PRIMARY KEY,
    track_id UUID NOT NULL REFERENCES course_tracks(id) ON DELETE RESTRICT,
    code VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    instructions_markdown TEXT NOT NULL,
    sequence_order INT NOT NULL DEFAULT 1,
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    max_score DECIMAL(5, 2) NOT NULL DEFAULT 100.00,
    passing_score DECIMAL(5, 2) NOT NULL DEFAULT 60.00,
    rubric_template JSONB NOT NULL DEFAULT '[]',
    allowed_file_types JSONB NOT NULL DEFAULT '["pdf", "zip", "ipynb"]',
    max_file_size_mb INT NOT NULL DEFAULT 25,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 15. Assignment Allocations Table
CREATE TABLE assignment_allocations (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL REFERENCES assignments(id) ON DELETE RESTRICT,
    batch_id UUID NULL REFERENCES batches(id) ON DELETE RESTRICT,
    candidate_id UUID NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    due_date_utc TIMESTAMPTZ NOT NULL,
    grace_period_end_utc TIMESTAMPTZ NULL,
    allocation_status VARCHAR(32) NOT NULL DEFAULT 'PENDING'
        CHECK (allocation_status IN ('PENDING', 'SUBMITTED', 'COMPLETED', 'EXPIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (batch_id IS NOT NULL OR candidate_id IS NOT NULL)
);
CREATE UNIQUE INDEX uq_allocations_candidate_assignment 
    ON assignment_allocations (candidate_id, assignment_id) 
    WHERE candidate_id IS NOT NULL;

-- 16. Assignment Submissions Table (One record per student per allocation)
CREATE TABLE assignment_submissions (
    id UUID PRIMARY KEY,
    allocation_id UUID NOT NULL REFERENCES assignment_allocations(id) ON DELETE RESTRICT,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    current_submission_status VARCHAR(32) NOT NULL DEFAULT 'PENDING'
        CHECK (current_submission_status IN ('PENDING', 'SUBMITTED', 'LATE_SUBMITTED', 'UNDER_REVIEW', 'CORRECTIONS_REQUESTED', 'APPROVED', 'REJECTED')),
    current_completion_status VARCHAR(32) NOT NULL DEFAULT 'INCOMPLETE'
        CHECK (current_completion_status IN ('INCOMPLETE', 'PASSED_COMPLETED', 'FAILED')),
    total_attempts INT NOT NULL DEFAULT 0,
    latest_score DECIMAL(5, 2) NULL,
    first_submitted_at_utc TIMESTAMPTZ NULL,
    latest_submitted_at_utc TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (allocation_id, candidate_id)
);

-- 17. Submission Attempts Table (Immutable Versioned Rounds)
CREATE TABLE submission_attempts (
    id UUID PRIMARY KEY,
    submission_id UUID NOT NULL REFERENCES assignment_submissions(id) ON DELETE RESTRICT,
    attempt_number INT NOT NULL,
    file_asset_id UUID NULL REFERENCES file_assets(id) ON DELETE RESTRICT,
    repository_url VARCHAR(500) NULL,
    student_notes TEXT NULL,
    submitted_at_utc TIMESTAMPTZ NOT NULL,
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    lateness_minutes INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (submission_id, attempt_number)
);

-- 18. Submission Reviews Table (Immutable Review Records)
CREATE TABLE submission_reviews (
    id UUID PRIMARY KEY,
    attempt_id UUID NOT NULL REFERENCES submission_attempts(id) ON DELETE RESTRICT,
    reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    review_outcome VARCHAR(32) NOT NULL 
        CHECK (review_outcome IN ('APPROVED', 'CORRECTIONS_REQUESTED', 'REJECTED')),
    total_score DECIMAL(5, 2) NOT NULL,
    qualitative_feedback TEXT NOT NULL,
    internal_evaluator_notes TEXT NULL,
    review_completed_at_utc TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 19. Review Rubric Scores Table
CREATE TABLE review_rubric_scores (
    id UUID PRIMARY KEY,
    review_id UUID NOT NULL REFERENCES submission_reviews(id) ON DELETE CASCADE,
    criterion_key VARCHAR(64) NOT NULL,
    criterion_title VARCHAR(150) NOT NULL,
    max_points DECIMAL(5, 2) NOT NULL,
    awarded_points DECIMAL(5, 2) NOT NULL,
    criterion_comments TEXT NULL
);
```

---

### 2.4 Domain 4: Projects, Collaborative Groups & Group Readiness

```sql
-- 20. Projects Table
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    track_id UUID NOT NULL REFERENCES course_tracks(id) ON DELETE RESTRICT,
    milestone_tier INT NOT NULL CHECK (milestone_tier IN (1, 2, 3)),
    code VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    brief_markdown TEXT NOT NULL,
    deliverable_schema JSONB NOT NULL DEFAULT '{"required_links": ["repository_url", "deployment_url"], "documentation_pdf": true}',
    evaluation_rubric JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 21. Project Cohorts Table
CREATE TABLE project_cohorts (
    id UUID PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES batches(id) ON DELETE RESTRICT,
    milestone_tier INT NOT NULL CHECK (milestone_tier IN (1, 2, 3)),
    min_group_size INT NOT NULL DEFAULT 2,
    target_group_size INT NOT NULL DEFAULT 4,
    max_group_size INT NOT NULL DEFAULT 5,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('FORMING', 'ACTIVE', 'EVALUATION', 'COMPLETED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 22. Project Groups Table
CREATE TABLE project_groups (
    id UUID PRIMARY KEY,
    cohort_id UUID NOT NULL REFERENCES project_cohorts(id) ON DELETE RESTRICT,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    group_name VARCHAR(100) NOT NULL UNIQUE,
    group_status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS'
        CHECK (group_status IN ('FORMED', 'IN_PROGRESS', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'COMPLETED')),
    readiness_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_DELIVERABLE'
        CHECK (readiness_status IN ('PENDING_DELIVERABLE', 'BLOCKED_PENDING_MEMBERS', 'READY_FOR_NEXT_PROJECT', 'ADVANCED', 'OVERRIDDEN')),
    deliverable_approved_at_utc TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 23. Group Members Table
CREATE TABLE group_members (
    id UUID PRIMARY KEY,
    group_id UUID NOT NULL REFERENCES project_groups(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    member_role VARCHAR(32) NOT NULL DEFAULT 'MEMBER' CHECK (member_role IN ('LEADER', 'MEMBER')),
    participation_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' 
        CHECK (participation_status IN ('ACTIVE', 'WITHDRAWN', 'REMOVED')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    detached_at TIMESTAMPTZ NULL,
    UNIQUE (group_id, candidate_id)
);
CREATE INDEX ix_group_members_candidate_active 
    ON group_members (candidate_id, participation_status) 
    WHERE participation_status = 'ACTIVE';

-- 24. Group Submissions Table
CREATE TABLE group_submissions (
    id UUID PRIMARY KEY,
    group_id UUID NOT NULL REFERENCES project_groups(id) ON DELETE RESTRICT,
    attempt_number INT NOT NULL DEFAULT 1,
    repository_url VARCHAR(500) NOT NULL,
    deployment_url VARCHAR(500) NULL,
    documentation_file_id UUID NULL REFERENCES file_assets(id) ON DELETE RESTRICT,
    submitted_by UUID NOT NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    submitted_at_utc TIMESTAMPTZ NOT NULL,
    evaluation_status VARCHAR(32) NOT NULL DEFAULT 'SUBMITTED'
        CHECK (evaluation_status IN ('SUBMITTED', 'UNDER_REVIEW', 'CORRECTIONS_REQUESTED', 'APPROVED', 'REJECTED')),
    score DECIMAL(5, 2) NULL,
    reviewer_feedback TEXT NULL,
    reviewer_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at_utc TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (group_id, attempt_number)
);

-- 25. Project Progression Requests Table
CREATE TABLE project_progression_requests (
    id UUID PRIMARY KEY,
    group_id UUID NOT NULL REFERENCES project_groups(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    from_milestone_tier INT NOT NULL CHECK (from_milestone_tier IN (1, 2, 3)),
    to_milestone_tier INT NOT NULL CHECK (to_milestone_tier IN (2, 3, 4)),
    requested_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING' 
        CHECK (status IN ('PENDING', 'PROCESSED', 'BYPASSED')),
    UNIQUE (group_id, candidate_id, from_milestone_tier)
);

-- 26. Project Completions Table (Permanent Milestone Record)
CREATE TABLE project_completions (
    id UUID PRIMARY KEY,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    group_id UUID NOT NULL REFERENCES project_groups(id) ON DELETE RESTRICT,
    milestone_tier INT NOT NULL CHECK (milestone_tier IN (1, 2, 3)),
    final_score DECIMAL(5, 2) NOT NULL,
    completed_date DATE NOT NULL,
    verified_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    UNIQUE (candidate_id, milestone_tier)
);
```

---

### 2.5 Domain 5: Internship & Certificate Management

```sql
-- 27. Internship Records Table (Decoupled from Certificate Duration)
CREATE TABLE internship_records (
    id UUID PRIMARY KEY,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    track_id UUID NOT NULL REFERENCES course_tracks(id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    expected_end_date DATE NULL,
    actual_completion_date DATE NULL,
    accredited_duration_months INT NOT NULL DEFAULT 3,
    internship_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
        CHECK (internship_status IN ('ELIGIBLE', 'ACTIVE', 'COMPLETED', 'TERMINATED')),
    coordinator_notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (candidate_id, track_id)
);

-- 28. Certificate Templates Table
CREATE TABLE certificate_templates (
    id UUID PRIMARY KEY,
    template_code VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(150) NOT NULL,
    layout_schema JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 29. Certificates Table
CREATE TABLE certificates (
    id UUID PRIMARY KEY,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    track_id UUID NOT NULL REFERENCES course_tracks(id) ON DELETE RESTRICT,
    template_id UUID NOT NULL REFERENCES certificate_templates(id) ON DELETE RESTRICT,
    serial_number VARCHAR(100) NOT NULL UNIQUE,
    certificate_type VARCHAR(32) NOT NULL DEFAULT 'FINAL_COMPREHENSIVE'
        CHECK (certificate_type IN ('MILESTONE', 'FINAL_COMPREHENSIVE')),
    milestone_level INT NULL CHECK (milestone_level IN (1, 2, 3)),
    accredited_duration_months INT NOT NULL,
    issue_date DATE NOT NULL,
    candidate_display_name VARCHAR(200) NOT NULL,
    course_display_title VARCHAR(250) NOT NULL,
    pdf_file_asset_id UUID NULL REFERENCES file_assets(id) ON DELETE SET NULL,
    verification_qr_url VARCHAR(500) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_APPROVAL'
        CHECK (status IN ('PENDING_APPROVAL', 'ISSUED', 'REVOKED')),
    issued_at_utc TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX uq_active_cert_candidate_milestone 
    ON certificates (candidate_id, certificate_type, milestone_level) 
    WHERE status != 'REVOKED';

-- 30. Certificate Approvals Table (Two-Tier Sign-off)
CREATE TABLE certificate_approvals (
    id UUID PRIMARY KEY,
    certificate_id UUID NOT NULL REFERENCES certificates(id) ON DELETE RESTRICT,
    approver_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    decision VARCHAR(32) NOT NULL CHECK (decision IN ('APPROVED', 'REJECTED')),
    decision_notes TEXT NULL,
    decided_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 31. Certificate Revocations Table
CREATE TABLE certificate_revocations (
    id UUID PRIMARY KEY,
    certificate_id UUID NOT NULL REFERENCES certificates(id) ON DELETE RESTRICT,
    revoked_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    reason_category VARCHAR(64) NOT NULL,
    detailed_reason TEXT NOT NULL,
    revoked_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

### 2.6 Domain 6: Cross-Cutting Operations, Notifications & Audit Logs

```sql
-- 32. System Policies Table (Configurable Dynamic Engine)
CREATE TABLE system_policies (
    id UUID PRIMARY KEY,
    policy_key VARCHAR(100) NOT NULL UNIQUE,
    policy_value JSONB NOT NULL,
    description TEXT NULL,
    last_modified_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 33. Import Jobs Table (CSV Batch Tracking)
CREATE TABLE import_jobs (
    id UUID PRIMARY KEY,
    job_type VARCHAR(64) NOT NULL DEFAULT 'CANDIDATE_ROSTER',
    original_filename VARCHAR(255) NOT NULL,
    total_rows INT NOT NULL DEFAULT 0,
    valid_rows INT NOT NULL DEFAULT 0,
    error_rows INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'DRY_RUN_COMPLETED'
        CHECK (status IN ('PROCESSING', 'DRY_RUN_COMPLETED', 'COMMITTED', 'FAILED')),
    initiated_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 34. Import Row Errors Table
CREATE TABLE import_row_errors (
    id UUID PRIMARY KEY,
    import_job_id UUID NOT NULL REFERENCES import_jobs(id) ON DELETE CASCADE,
    row_number INT NOT NULL,
    error_field VARCHAR(64) NOT NULL,
    error_code VARCHAR(64) NOT NULL,
    error_message TEXT NOT NULL,
    raw_row_data JSONB NOT NULL
);

-- 35. Notification Events Table
CREATE TABLE notification_events (
    id UUID PRIMARY KEY,
    recipient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    action_url VARCHAR(500) NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 36. Email Queue Table
CREATE TABLE email_queue (
    id UUID PRIMARY KEY,
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(250) NOT NULL,
    body_html TEXT NOT NULL,
    delivery_status VARCHAR(32) NOT NULL DEFAULT 'PENDING'
        CHECK (delivery_status IN ('PENDING', 'SENT', 'FAILED', 'RETRYING')),
    attempt_count INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 5,
    last_error_message TEXT NULL,
    next_retry_at_utc TIMESTAMPTZ NULL,
    sent_at_utc TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 37. Immutable Audit Logs Table (Append-Only)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    actor_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    actor_ip_address VARCHAR(45) NULL,
    actor_user_agent TEXT NULL,
    action_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id UUID NOT NULL,
    pre_state JSONB NULL,
    post_state JSONB NULL,
    justification TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_audit_logs_entity ON audit_logs (entity_type, entity_id, created_at DESC);
CREATE INDEX ix_audit_logs_actor ON audit_logs (actor_user_id, created_at DESC);
```

---

## 3. Database Migration Strategy & Zero-Downtime Conventions

1. **Tooling:** All migrations are authored and executed via **Alembic**.
2. **Reversibility Requirement:** Every migration file must implement a symmetrical, fully tested `downgrade()` function matching `upgrade()`.
3. **Safe Column Addition Rules:**
   - When adding new columns that are non-nullable, the migration must either:
     1. Supply a server default (`DEFAULT ...`), or
     2. Add the column as nullable, populate data via batch updates, and alter column to `NOT NULL` in a subsequent step.
4. **Concurrent Index Creation:** Indexes on tables with active production traffic shall be applied with `CREATE INDEX CONCURRENTLY` to avoid write table locks.
