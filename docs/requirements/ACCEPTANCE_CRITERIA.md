# Acceptance Criteria Specification
## Project: ExcelR Track360
### Student Lifecycle & Operations Management Platform
**Document Reference:** ACC-TRK360-V1.0  
**Phase:** Phase 1 – Requirements & Business Analysis  
**Status:** Baseline Specification  

---

## 1. Candidate Management (AC-CAN)

### AC-CAN-001: Golden Candidate Profile & Duplicate Prevention
- **Scenario:** Attempting to register a candidate with an existing email or phone.
  - **Given** an existing candidate is registered with email `"student.alpha@example.com"` and phone `"+919876543210"`.
  - **When** a staff user attempts to register a new candidate with email `"Student.Alpha@example.com"` (case variant) OR phone `"+919876543210"`.
  - **Then** the system shall reject the request with HTTP 409 Conflict.
  - **And** the response body shall specify which attribute (`email` or `phone`) violates uniqueness.
  - **And** no duplicate database row shall be created.

### AC-CAN-002: CSV Batch Ingestion Dry-Run Validation
- **Scenario:** Uploading a CSV roster with valid and invalid rows.
  - **Given** a CSV roster containing 50 rows, where Row 12 has an invalid email format and Row 35 contains a phone number already registered.
  - **When** the Candidate Coordinator uploads this CSV to `/api/v1/candidates/import/dry-run`.
  - **Then** the system shall return HTTP 200 with `is_valid: false`.
  - **And** the report shall detail:
    - Row 12: `INVALID_EMAIL_FORMAT`
    - Row 35: `DUPLICATE_PHONE_NUMBER`
    - Valid row count: 48, Errored row count: 2.
  - **And** no candidate records shall be committed to the database until errors are resolved and confirmation is invoked.

### AC-CAN-003: Candidate Profile PII Data Isolation
- **Scenario:** A student attempts to query another candidate's full profile.
  - **Given** Student A (ID `CAND-001`) and Student B (ID `CAND-002`) are authenticated.
  - **When** Student A sends a GET request to `/api/v1/candidates/CAND-002`.
  - **Then** the server shall return HTTP 403 Forbidden.
  - **And** no personal data (phone, email, grades) of Student B shall be returned.

---

## 2. Assignment Management (AC-ASG)

### AC-ASG-001: Server-Authoritative UTC Timestamping & Lateness Flagging
- **Scenario:** Student submits an assignment after the configured due date.
  - **Given** an assignment allocation has a due date of `2026-11-01T18:00:00Z`.
  - **When** the candidate's browser sends a submission payload received by the server at `2026-11-01T18:04:15Z` (UTC).
  - **Then** the system shall record `submitted_at = 2026-11-01T18:04:15Z`.
  - **And** the system shall automatically set `is_late = true` and `lateness_seconds = 255`.
  - **And** client-supplied clock times in headers or payload shall be completely ignored.

### AC-ASG-002: File Upload Restrictions & Security
- **Scenario:** Candidate attempts to submit an unapproved file format or an oversized payload.
  - **Given** an assignment configured to accept `.pdf`, `.zip`, and `.ipynb` up to 25 MB.
  - **When** a candidate uploads a file named `solution.exe` OR an archive of size 35 MB.
  - **Then** the API shall reject the upload with HTTP 422 Unprocessable Entity or HTTP 413 Payload Too Large.
  - **And** the file shall not be written to persistent storage.

### AC-ASG-003: Submissions Do Not Equal Approval
- **Scenario:** Candidate submits an assignment and expects completion.
  - **Given** a candidate submits their deliverable file.
  - **When** the submission is confirmed by the server.
  - **Then** the submission state shall be `SUBMITTED`.
  - **And** the assignment allocation state shall remain `INCOMPLETE`.
  - **And** the candidate's curriculum completion metric shall NOT count the assignment as complete until an authorized reviewer marks it `APPROVED`.

### AC-ASG-004: Iterative Review & Correction History Preservation
- **Scenario:** Reviewer requests corrections, and candidate resubmits.
  - **Given** Submission Attempt 1 has score 45/100 and status `CORRECTIONS_REQUESTED` with comments from Reviewer 1.
  - **When** the candidate submits revised files as Attempt 2.
  - **Then** the system shall create a new `SubmissionAttempt` record with `attempt_number = 2`.
  - **And** Attempt 1 files, comments, and timestamp shall remain immutably accessible in the review history.

---

## 3. Project Management (AC-PRJ)

### AC-PRJ-001: Project 1 Prerequisite Gate Enforcement
- **Scenario:** Project Coordinator attempts to allocate Project 1 to a candidate with pending assignments.
  - **Given** a track curriculum requires 8 mandatory assignments.
  - **And** Candidate X has 7 assignments in `APPROVED` status and 1 assignment in `SUBMITTED` status.
  - **When** the Coordinator attempts to allocate Candidate X to a Project 1 group.
  - **Then** the system shall reject the allocation with HTTP 400 Bad Request.
  - **And** the error message shall state: `"Candidate X is ineligible for Project 1: Mandatory assignment [ASG-008] is not Approved."`

### AC-PRJ-002: Sequential Project Cap (Maximum 3 Projects)
- **Scenario:** Attempting to allocate a 4th project to a candidate who completed Project 3.
  - **Given** Candidate Y has completed Project 1, Project 2, and Project 3.
  - **When** a Project Coordinator attempts to allocate Candidate Y to Project 4.
  - **Then** the system shall block the transaction with HTTP 422 Unprocessable Entity.
  - **And** the system shall indicate: `"Maximum standard project limit (3) reached for Candidate Y."`
  - **Unless** a Super Administrator has explicitly submitted an authorized cap extension override with audit justification.

### AC-PRJ-003: Dynamic Group Sizing
- **Scenario:** Coordinator forms a group of size 3 for a track configured with min=2, target=3, max=5.
  - **Given** a project allocation configured with `min_size = 2` and `max_size = 5`.
  - **When** the Coordinator creates a group with 3 candidates.
  - **Then** the group creation succeeds with status `FORMED`.
  - **When** the Coordinator attempts to create a group with 1 candidate (when solo is disabled).
  - **Then** the system rejects with: `"Group size 1 is below minimum permitted size of 2."`

---

## 4. Collaborative Group Readiness (AC-GRP)

### AC-GRP-001: Group Readiness Evaluation (All Members Ready)
- **Scenario:** All group members submit advancement requests after project approval.
  - **Given** Group 10 contains 4 candidates (C1, C2, C3, C4).
  - **And** the Project 1 deliverable is marked `APPROVED`.
  - **When** C1, C2, C3, and C4 all click "Request Next Project" in their student portals.
  - **Then** Group 10 status shall automatically transition to `READY_FOR_NEXT_PROJECT`.
  - **And** the Project Coordinator receives a notification: `"Group 10 is ready for Project 2 allocation."`

### AC-GRP-002: Blocked Group Progression Due to Inactive Member
- **Scenario:** 3 members have requested progression, but 1 member is lagging.
  - **Given** Group 10 has deliverable status `APPROVED`.
  - **And** C1, C2, and C3 have requested progression, but C4 has not.
  - **When** the system evaluates group readiness.
  - **Then** Group 10 status shall remain `BLOCKED_PENDING_MEMBERS`.
  - **And** the readiness dashboard shall display: `"Blocked: Awaiting request from Candidate C4."`
  - **And** automated reminder notifications shall be queued for C4.

### AC-GRP-003: Inactive Member Removal & Group Reconstitution
- **Scenario:** Project Coordinator removes an inactive member to unblock a group.
  - **Given** Group 10 is in `BLOCKED_PENDING_MEMBERS` due to C4 being unresponsive.
  - **When** the Project Coordinator removes C4 with reason: `"Student inactive > 14 days"`.
  - **Then** C4 is detached from Group 10 with status `UNASSIGNED_FROM_PROJECT`.
  - **And** Group 10 immediately recalculates readiness with remaining members (C1, C2, C3).
  - **And** since all 3 remaining members have requested progression, Group 10 status becomes `READY_FOR_NEXT_PROJECT`.
  - **And** an audit log entry is written recording C4's removal and the coordinator's justification.

---

## 5. Internship Milestone Management (AC-INT)

### AC-INT-001: Decoupling of Calendar Dates from Duration Mapping
- **Scenario:** Calculating accredited duration from completed projects.
  - **Given** Candidate Z completed Project 1 on `2026-03-01` and Project 2 on `2026-06-15`.
  - **And** the candidate's formal corporate internship dates are `2026-02-01` to `2026-08-01` (6 calendar months).
  - **When** the Internship Coordinator views Candidate Z's record.
  - **Then** the accredited certificate duration shall be calculated as `6 Months` (2 completed projects $\times$ 3 months/project).
  - **And** the system shall explicitly display both the calendar dates and the accredited duration as distinct attributes.

---

## 6. Certificate Management (AC-CER)

### AC-CER-001: Verified Eligibility Gate Before Approval
- **Scenario:** Attempting to approve certificate issuance for a candidate with incomplete assignments.
  - **Given** Candidate W has completed Project 1, but has 1 mandatory assignment in `CORRECTIONS_REQUESTED`.
  - **When** a staff user attempts to trigger certificate issuance for Candidate W.
  - **Then** the system shall reject the request with HTTP 400 Bad Request.
  - **And** the response shall list the unfulfilled prerequisites blocking eligibility.

### AC-CER-002: Unique Certificate Identifier & Tamper Resistance
- **Scenario:** System generates an approved certificate.
  - **Given** Certificate Approver approves issuance for Candidate V.
  - **When** the certificate generation task executes.
  - **Then** the system shall generate a unique serial (e.g. `EXCELR-2026-FSD-7D2A1B8C`).
  - **And** the generated PDF shall include:
    - Candidate full name
    - Accredited duration (e.g., "6 Months")
    - Course Track title
    - Issue Date (UTC)
    - Embedded QR code linking directly to `/verify/EXCELR-2026-FSD-7D2A1B8C`.
  - **And** accessing `/api/v1/certificates/verify/EXCELR-2026-FSD-7D2A1B8C` publicly shall return `status: "VALID"`.

### AC-CER-003: Duplicate Certificate Issuance Prevention
- **Scenario:** Attempting to issue a second certificate for the same milestone.
  - **Given** Candidate V already has an active issued certificate for Milestone 2 (`6 Months`).
  - **When** an administrator or coordinator attempts to initiate another certificate for Candidate V for Milestone 2.
  - **Then** the system shall block the transaction with HTTP 409 Conflict: `"An active certificate for Milestone 2 has already been issued to this candidate."`

---

## 7. Security & Non-Functional Controls (AC-SEC)

### AC-SEC-001: Server-Side RBAC Enforcement on Protected API
- **Scenario:** Assignment Reviewer attempts to access the System Policy Configuration endpoint.
  - **Given** an authenticated user with `ROLE_ASG_REVIEWER`.
  - **When** the user sends a PUT request to `/api/v1/settings/policies`.
  - **Then** the server shall return HTTP 403 Forbidden.
  - **And** no configuration values shall be altered.

### AC-SEC-002: Private File Access Control
- **Scenario:** Unauthenticated user attempts to download a student submission file directly.
  - **Given** a student submission file stored at storage key `storage/submissions/2026/sub_9842.pdf`.
  - **When** an unauthenticated web client requests the file URL directly without an active session cookie or signed token.
  - **Then** the server shall return HTTP 401 Unauthorized.
  - **And** the file content shall not be streamed.

### AC-SEC-003: Immutable Audit Logging of Administrative Overrides
- **Scenario:** Operations Admin overrides a group readiness block.
  - **Given** Operations Admin (User ID `USR-004`) overrides the readiness block on Group 15 with reason `"Student on approved medical leave"`.
  - **When** the override transaction completes.
  - **Then** an entry must exist in the `audit_logs` table containing:
    - `actor_id = 'USR-004'`
    - `entity_type = 'PROJECT_GROUP'`
    - `entity_id = 'GRP-015'`
    - `action = 'ADMINISTRATIVE_READINESS_OVERRIDE'`
    - `justification = 'Student on approved medical leave'`
    - `timestamp = Current UTC time`
  - **And** the audit record cannot be modified or deleted via any standard API endpoint.
