# Entity Relationship Diagram (ERD)
## Project: ExcelR Track360
### Student Lifecycle & Operations Management Platform
**Document Reference:** ERD-TRK360-V1.0  
**Phase:** Phase 2 – System Architecture & Database Design  
**Status:** Approved for Implementation Planning  

---

## 1. Domain Entities & Relationship Overview

The ExcelR Track360 data model is structured across seven core relational domains:

```mermaid
erDiagram
    %% ==========================================
    %% 1. IDENTITY & SESSIONS
    %% ==========================================
    USERS ||--o{ USER_ROLES : has
    ROLES ||--o{ USER_ROLES : assigned_to
    ROLES ||--o{ ROLE_PERMISSIONS : contains
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : granted_by
    USERS ||--o{ USER_SESSIONS : owns
    USERS ||--o{ CANDIDATES : linked_student_user

    %% ==========================================
    %% 2. CANDIDATES & ACADEMIC COHORTS
    %% ==========================================
    COURSES ||--o{ COURSE_TRACKS : offers
    COURSE_TRACKS ||--o{ BATCHES : runs
    BATCHES ||--o{ ENROLLMENTS : contains
    CANDIDATES ||--o{ ENROLLMENTS : enrolled_in
    CANDIDATES ||--o{ CANDIDATE_NOTES : has

    %% ==========================================
    %% 3. ASSIGNMENTS & EVALUATIONS
    %% ==========================================
    COURSE_TRACKS ||--o{ ASSIGNMENTS : defines
    ASSIGNMENTS ||--o{ ASSIGNMENT_ALLOCATIONS : allocated_via
    BATCHES ||--o{ ASSIGNMENT_ALLOCATIONS : targeted_batch
    CANDIDATES ||--o{ ASSIGNMENT_ALLOCATIONS : targeted_candidate
    ASSIGNMENT_ALLOCATIONS ||--o{ ASSIGNMENT_SUBMISSIONS : receives
    ASSIGNMENT_SUBMISSIONS ||--o{ SUBMISSION_ATTEMPTS : versions
    SUBMISSION_ATTEMPTS ||--o{ SUBMISSION_REVIEWS : evaluated_by
    USERS ||--o{ SUBMISSION_REVIEWS : reviewer
    SUBMISSION_REVIEWS ||--o{ REVIEW_RUBRIC_SCORES : scores

    %% ==========================================
    %% 4. PROJECTS & COLLABORATIVE GROUPS
    %% ==========================================
    COURSE_TRACKS ||--o{ PROJECTS : includes
    BATCHES ||--o{ PROJECT_COHORTS : initiates
    PROJECT_COHORTS ||--o{ PROJECT_GROUPS : organizes
    PROJECTS ||--o{ PROJECT_GROUPS : assigned_project
    PROJECT_GROUPS ||--o{ GROUP_MEMBERS : includes
    CANDIDATES ||--o{ GROUP_MEMBERS : participates_in
    PROJECT_GROUPS ||--o{ GROUP_SUBMISSIONS : submits
    GROUP_SUBMISSIONS ||--o{ GROUP_REVIEWS : reviewed_as
    PROJECT_GROUPS ||--o{ PROJECT_PROGRESSION_REQUESTS : requests
    CANDIDATES ||--o{ PROJECT_PROGRESSION_REQUESTS : requested_by
    CANDIDATES ||--o{ PROJECT_COMPLETIONS : earns
    PROJECTS ||--o{ PROJECT_COMPLETIONS : completed_for

    %% ==========================================
    %% 5. INTERNSHIP MILESTONES
    %% ==========================================
    CANDIDATES ||--o{ INTERNSHIP_RECORDS : undertakes
    COURSE_TRACKS ||--o{ INTERNSHIP_RECORDS : under_track
    INTERNSHIP_RECORDS ||--o{ INTERNSHIP_MILESTONES : tracks

    %% ==========================================
    %% 6. CERTIFICATES & CREDENTIALS
    %% ==========================================
    CANDIDATES ||--o{ CERTIFICATES : awarded_to
    COURSE_TRACKS ||--o{ CERTIFICATES : certified_in
    CERTIFICATES ||--o{ CERTIFICATE_APPROVALS : approved_by
    USERS ||--o{ CERTIFICATE_APPROVALS : approver_user
    CERTIFICATES ||--o{ CERTIFICATE_REVOCATIONS : revoked_by
    USERS ||--o{ CERTIFICATE_REVOCATIONS : revoking_user

    %% ==========================================
    %% 7. CROSS-CUTTING AUDIT & FILES
    %% ==========================================
    USERS ||--o{ AUDIT_LOGS : triggered_by
    USERS ||--o{ FILE_ASSETS : uploaded_by
```

---

## 2. Detailed Entity Attributes & Cardinality

### 2.1 Identity, RBAC & Session Domain

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email UK
        string password_hash
        string full_name
        string phone
        string status
        boolean is_verified
        int failed_login_attempts
        timestamp locked_until
        timestamp last_login_at
        timestamp created_at
        timestamp updated_at
    }

    ROLES {
        uuid id PK
        string code UK
        string name
        string description
        boolean is_system_role
    }

    PERMISSIONS {
        uuid id PK
        string code UK
        string module
        string description
    }

    USER_ROLES {
        uuid user_id PK,FK
        uuid role_id PK,FK
        timestamp assigned_at
        uuid assigned_by FK
    }

    ROLE_PERMISSIONS {
        uuid role_id PK,FK
        uuid permission_id PK,FK
    }

    USER_SESSIONS {
        uuid id PK
        uuid user_id FK
        string session_token_hash UK
        string ip_address
        string user_agent
        timestamp expires_at
        timestamp last_activity_at
        boolean is_revoked
        timestamp created_at
    }

    USERS ||--o{ USER_ROLES : has
    ROLES ||--o{ USER_ROLES : maps
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : maps
    USERS ||--o{ USER_SESSIONS : establishes
```

### 2.2 Candidates & Academic Curriculum Domain

```mermaid
erDiagram
    COURSES {
        uuid id PK
        string code UK
        string title
        text description
        boolean is_active
        timestamp created_at
    }

    COURSE_TRACKS {
        uuid id PK
        uuid course_id FK
        string code UK
        string title
        int total_mandatory_assignments
        int total_required_projects
        jsonb duration_policy_config
        boolean is_active
        timestamp created_at
    }

    BATCHES {
        uuid id PK
        uuid track_id FK
        string batch_code UK
        string title
        date start_date
        date expected_end_date
        string status
        uuid coordinator_id FK
        timestamp created_at
    }

    CANDIDATES {
        uuid id PK
        uuid user_id FK,UK "Nullable if not yet registered in auth"
        string candidate_number UK
        string first_name
        string last_name
        string email UK
        string phone UK
        string alternate_phone
        string lifecycle_status
        boolean project_eligible
        int completed_projects_count
        timestamp created_at
        timestamp updated_at
    }

    ENROLLMENTS {
        uuid id PK
        uuid candidate_id FK
        uuid batch_id FK
        date enrollment_date
        string enrollment_status
        timestamp created_at
    }

    COURSES ||--o{ COURSE_TRACKS : includes
    COURSE_TRACKS ||--o{ BATCHES : structures
    BATCHES ||--o{ ENROLLMENTS : receives
    CANDIDATES ||--o{ ENROLLMENTS : undergoes
```

### 2.3 Assignments, Allocations & Iterative Reviews

```mermaid
erDiagram
    ASSIGNMENTS {
        uuid id PK
        uuid track_id FK
        string code UK
        string title
        text instructions_markdown
        int sequence_order
        boolean is_mandatory
        decimal max_score
        decimal passing_score
        jsonb rubric_template
        jsonb allowed_file_types
        int max_file_size_mb
        timestamp created_at
    }

    ASSIGNMENT_ALLOCATIONS {
        uuid id PK
        uuid assignment_id FK
        uuid batch_id FK "Nullable if individual allocation"
        uuid candidate_id FK "Nullable if batch allocation"
        timestamp due_date_utc
        timestamp grace_period_end_utc
        string allocation_status
        timestamp created_at
    }

    ASSIGNMENT_SUBMISSIONS {
        uuid id PK
        uuid allocation_id FK
        uuid candidate_id FK
        string current_submission_status
        string current_completion_status
        int total_attempts
        decimal latest_score
        timestamp first_submitted_at_utc
        timestamp latest_submitted_at_utc
    }

    SUBMISSION_ATTEMPTS {
        uuid id PK
        uuid submission_id FK
        int attempt_number
        uuid file_asset_id FK "Nullable if repository URL only"
        string repository_url
        text student_notes
        timestamp submitted_at_utc
        boolean is_late
        int lateness_minutes
    }

    SUBMISSION_REVIEWS {
        uuid id PK
        uuid attempt_id FK
        uuid reviewer_id FK
        string review_outcome
        decimal total_score
        text qualitative_feedback
        text internal_evaluator_notes
        timestamp review_completed_at_utc
    }

    REVIEW_RUBRIC_SCORES {
        uuid id PK
        uuid review_id FK
        string criterion_key
        string criterion_title
        decimal max_points
        decimal awarded_points
        text criterion_comments
    }

    ASSIGNMENTS ||--o{ ASSIGNMENT_ALLOCATIONS : instantiates
    ASSIGNMENT_ALLOCATIONS ||--o{ ASSIGNMENT_SUBMISSIONS : targets
    ASSIGNMENT_SUBMISSIONS ||--o{ SUBMISSION_ATTEMPTS : contains
    SUBMISSION_ATTEMPTS ||--o{ SUBMISSION_REVIEWS : undergoes
    SUBMISSION_REVIEWS ||--o{ REVIEW_RUBRIC_SCORES : breaks_down
```

### 2.4 Projects, Groups & Group Readiness

```mermaid
erDiagram
    PROJECTS {
        uuid id PK
        uuid track_id FK
        int milestone_tier "1, 2, or 3"
        string code UK
        string title
        text brief_markdown
        jsonb deliverable_schema
        jsonb evaluation_rubric
        timestamp created_at
    }

    PROJECT_COHORTS {
        uuid id PK
        uuid batch_id FK
        int milestone_tier
        int min_group_size
        int target_group_size
        int max_group_size
        string status
        timestamp created_at
    }

    PROJECT_GROUPS {
        uuid id PK
        uuid cohort_id FK
        uuid project_id FK
        string group_name UK
        string group_status
        string readiness_status
        timestamp deliverable_approved_at_utc
        timestamp created_at
    }

    GROUP_MEMBERS {
        uuid id PK
        uuid group_id FK
        uuid candidate_id FK
        string member_role "LEADER, MEMBER"
        string participation_status "ACTIVE, WITHDRAWN, REMOVED"
        timestamp joined_at
        timestamp detached_at
    }

    GROUP_SUBMISSIONS {
        uuid id PK
        uuid group_id FK
        int attempt_number
        string repository_url
        string deployment_url
        uuid documentation_file_id FK
        timestamp submitted_at_utc
        string evaluation_status
        decimal score
        text reviewer_feedback
        uuid reviewer_id FK
        timestamp reviewed_at_utc
    }

    PROJECT_PROGRESSION_REQUESTS {
        uuid id PK
        uuid group_id FK
        uuid candidate_id FK
        int from_milestone_tier
        int to_milestone_tier
        timestamp requested_at_utc
        string status "PENDING, PROCESSED, BYPASSED"
    }

    PROJECT_COMPLETIONS {
        uuid id PK
        uuid candidate_id FK
        uuid project_id FK
        uuid group_id FK
        int milestone_tier
        decimal final_score
        date completed_date
        timestamp verified_at_utc
    }

    PROJECTS ||--o{ PROJECT_GROUPS : assigned
    PROJECT_COHORTS ||--o{ PROJECT_GROUPS : manages
    PROJECT_GROUPS ||--o{ GROUP_MEMBERS : contains
    PROJECT_GROUPS ||--o{ GROUP_SUBMISSIONS : uploads
    PROJECT_GROUPS ||--o{ PROJECT_PROGRESSION_REQUESTS : collects
    CANDIDATES ||--o{ PROJECT_COMPLETIONS : records
```

### 2.5 Internship & Certificate Domain

```mermaid
erDiagram
    INTERNSHIP_RECORDS {
        uuid id PK
        uuid candidate_id FK
        uuid track_id FK
        date start_date
        date expected_end_date
        date actual_completion_date
        int accredited_duration_months
        string internship_status
        text coordinator_notes
        timestamp created_at
        timestamp updated_at
    }

    CERTIFICATES {
        uuid id PK
        uuid candidate_id FK
        uuid track_id FK
        string serial_number UK
        string certificate_type "MILESTONE, FINAL_COMPREHENSIVE"
        int milestone_level "1, 2, 3 or null"
        int accredited_duration_months
        date issue_date
        string candidate_display_name
        string course_display_title
        uuid pdf_file_asset_id FK
        string verification_qr_url
        string status "PENDING_APPROVAL, ISSUED, REVOKED"
        timestamp issued_at_utc
        timestamp created_at
    }

    CERTIFICATE_APPROVALS {
        uuid id PK
        uuid certificate_id FK
        uuid approver_id FK
        string decision "APPROVED, REJECTED"
        text decision_notes
        timestamp decided_at_utc
    }

    CERTIFICATE_REVOCATIONS {
        uuid id PK
        uuid certificate_id FK
        uuid revoked_by FK
        string reason_category
        text detailed_reason
        timestamp revoked_at_utc
    }

    INTERNSHIP_RECORDS ||--o{ CERTIFICATES : qualifies
    CERTIFICATES ||--o{ CERTIFICATE_APPROVALS : gates
    CERTIFICATES ||--o{ CERTIFICATE_REVOCATIONS : invalidates
```

---

## 3. Primary Key & Identifier Strategy

1. **UUIDv7 for Domain Entities:**
   - All operational tables use **UUIDv7** (RFC 9562) as their primary key.
   - *Rationale:* Unlike random UUIDv4, UUIDv7 embeds a millisecond-precision UTC timestamp in the leading 48 bits. This preserves natural chronological B-Tree index locality, eliminating index fragmentation during high-throughput inserts while preventing sequential ID guessing attacks.
2. **Human-Readable Business Codes:**
   - Candidates: `candidate_number` (e.g., `CAN-2026-00042`).
   - Batches: `batch_code` (e.g., `FSD-2026-B12`).
   - Assignments: `code` (e.g., `ASG-PY-001`).
   - Certificates: `serial_number` (e.g., `EXCELR-2026-FSD-7D2A1B8C`).

---

## 4. Key Performance Indexes

| Table | Index Columns | Index Type | Purpose |
| :--- | :--- | :--- | :--- |
| `candidates` | `LOWER(TRIM(email))` | B-Tree Unique | Case-insensitive email de-duplication |
| `candidates` | `phone` | B-Tree Unique | Mobile phone de-duplication |
| `candidates` | `(lifecycle_status, project_eligible)` | B-Tree Partial | High-speed filtering of project-ready candidates |
| `assignment_allocations` | `(candidate_id, assignment_id)` | B-Tree Unique | Prevents duplicate allocation of same assignment |
| `submission_attempts` | `(submission_id, attempt_number)` | B-Tree Unique | Enforces sequential attempt versioning |
| `group_members` | `(group_id, candidate_id)` | B-Tree Unique | Prevents duplicate candidate membership in group |
| `project_groups` | `(cohort_id, readiness_status)` | B-Tree | High-speed lookup for blocked/ready groups |
| `certificates` | `serial_number` | B-Tree Unique | Constant-time ($O(1)$) public certificate verification |
| `certificates` | `(candidate_id, certificate_type, milestone_level)` | Partial Unique (`status != 'REVOKED'`) | Blocks duplicate active certificate issuance |
| `audit_logs` | `(entity_type, entity_id, created_at)` | B-Tree | Fast retrieval of entity audit history |
