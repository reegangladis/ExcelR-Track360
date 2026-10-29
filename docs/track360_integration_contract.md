# ExcelR Track360 — Learnova Integration API Contract
## System Integration & Data Synchronization Contract
**Governing Documents:** Learner Progress Platform BRD (dated October 26, 2026) & Track360 System Architecture  
**Document Reference:** INT-TRK360-V1.0  
**Effective Date:** October 28, 2026  
**Status:** Formally Verified & Ready for Learnova Integration  
**Integration Strategy:** Authenticated REST API with Server-Enforced RBAC (No Direct Database Coupling)  

---

## 1. Architectural Integration Principles

ExcelR Track360 functions as the **authoritative operational system of record** for candidate lifecycle states, assignment evaluation histories, collaborative project progression, and certificate credential verification.

As ExcelR Learnova (derived from Learnova-AI) is developed, the two platforms interface via secure, authenticated HTTP APIs under the following non-negotiable principles:

1. **Zero Record Duplication:** Track360 owns the canonical Golden Candidate profile (`Candidate`) identified by UUID and sequential identifier (`EX-YYYY-XXXX`). Learnova shall reference Track360 candidate identifiers rather than maintaining a disconnected student table.
2. **Deterministic Prerequisite Gating:** Milestone progression (Project eligibility, Internship accredited duration, Certificate eligibility) is calculated authoritatively by Track360.
3. **No Direct Database Sharing:** Learnova communicates with Track360 exclusively through authenticated REST endpoints (`/api/v1/*`), ensuring domain invariants, database transactions, and audit triggers cannot be bypassed.
4. **Authoritative Timestamping:** All submission attempts and review decisions record server-verified UTC timestamps upon arrival.

---

## 2. Supported API Contract Specifications

The following 10 integration operations represent the verified API surface implemented, tested, and active in Track360.

---

### Operation 1: Learner Lookup
* **Purpose:** Allows Learnova to verify learner identity, biographical attributes, and current lifecycle status without duplicating student profiles.
* **HTTP Method & Endpoint:** `GET /api/v1/candidates/{candidate_id}` (or `GET /api/v1/candidates?search={query}`)
* **Mode:** Read-Only
* **Required Permission:** `candidate:profile_view` (Staff) or `candidate:profile_read_own` (Student viewing own profile)
* **Request Schema:**
  - Path parameter: `candidate_id` (`UUID`, e.g. `123e4567-e89b-12d3-a456-426614174000`)
  - Query parameters (for list/search): `search` (string), `lifecycle_status` (string), `batch_id` (UUID), `track_id` (UUID), `page` (int, default 1), `page_size` (int, default 20)
* **Response Schema (`CandidateResponse`):**
  ```json
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "456e7890-e89b-12d3-a456-426614174000",
    "candidate_number": "EX-2026-0042",
    "first_name": "Arjun",
    "last_name": "Sharma",
    "email": "arjun.sharma@example.com",
    "phone": "+919876543210",
    "alternate_phone": null,
    "academic_qualification": "B.Tech Computer Science",
    "lifecycle_status": "ACTIVE",
    "project_eligible": true,
    "completed_projects_count": 1,
    "batch_code": "DATA-2026-01",
    "created_at": "2026-10-26T10:00:00Z",
    "updated_at": "2026-10-28T14:30:00Z"
  }
  ```
* **Error Responses:**
  - `401 Unauthorized`: Session token missing or expired.
  - `403 Forbidden`: User lacks `candidate:profile_view` permission.
  - `404 Not Found`: Candidate ID does not exist.
* **Audit Behavior:** Read operation; monitored via access telemetry.
* **Test Evidence:** [`backend/tests/test_candidates.py::test_candidate_list_search_and_pagination`](file:///backend/tests/test_candidates.py)

---

### Operation 2: Course Enrollment Lookup
* **Purpose:** Retrieves active and historical cohort enrollments associated with a specific candidate.
* **HTTP Method & Endpoint:** `GET /api/v1/candidates/{candidate_id}` (includes batch mapping) and `GET /api/v1/batches`
* **Mode:** Read-Only
* **Required Permission:** `candidate:profile_view`
* **Request Schema:**
  - Path parameter: `candidate_id` (`UUID`)
* **Response Schema (`BatchResponse` via Batches endpoint):**
  ```json
  [
    {
      "id": "789e0123-e89b-12d3-a456-426614174000",
      "track_id": "890e1234-e89b-12d3-a456-426614174000",
      "batch_code": "DATA-2026-01",
      "title": "Data Analytics Oct 2026 Morning Cohort",
      "start_date": "2026-10-01",
      "expected_end_date": "2027-04-01",
      "status": "ACTIVE",
      "coordinator_id": "901e2345-e89b-12d3-a456-426614174000",
      "created_at": "2026-09-15T09:00:00Z"
    }
  ]
  ```
* **Error Responses:** `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.
* **Audit Behavior:** Read-Only.
* **Test Evidence:** [`backend/tests/test_candidates.py::test_candidate_crud_and_duplicate_prevention`](file:///backend/tests/test_candidates.py)

---

### Operation 3: Assignment Status Retrieval
* **Purpose:** Ingests or polls current assignment submission and completion statuses for an individual or cohort.
* **HTTP Method & Endpoint:** `GET /api/v1/assignments/submissions`
* **Mode:** Read-Only
* **Required Permission:** `assignment:submission_view`
* **Request Schema:**
  - Query parameters: `candidate_id` (UUID), `batch_id` (UUID), `status` (string: `NOT_SUBMITTED`, `SUBMITTED`, `CORRECTIONS_REQUESTED`, `APPROVED`), `page` (int, default 1), `page_size` (int, default 50)
* **Response Schema (`AssignmentSubmissionPaginated`):**
  ```json
  {
    "items": [
      {
        "id": "abce1234-e89b-12d3-a456-426614174000",
        "allocation_id": "bcde2345-e89b-12d3-a456-426614174000",
        "candidate_id": "123e4567-e89b-12d3-a456-426614174000",
        "candidate_name": "Arjun Sharma",
        "candidate_number": "EX-2026-0042",
        "assignment_code": "SQL-ADV-01",
        "assignment_title": "Complex Window Functions and CTEs",
        "batch_code": "DATA-2026-01",
        "current_submission_status": "APPROVED",
        "current_completion_status": "PASSED_COMPLETED",
        "total_attempts": 2,
        "latest_score": 88.5,
        "due_date_utc": "2026-10-20T23:59:59Z",
        "latest_submitted_at_utc": "2026-10-19T18:22:10Z",
        "is_late": false
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1
  }
  ```
* **Error Responses:** `401 Unauthorized`, `403 Forbidden`.
* **Audit Behavior:** Read-Only.
* **Test Evidence:** [`backend/tests/test_submissions.py::test_assignment_submission_lifecycle`](file:///backend/tests/test_submissions.py)

---

### Operation 4: Assignment Feedback & Attempt Retrieval
* **Purpose:** Obtains multi-round evaluation history, reviewer feedback notes, and rubric scores for student guidance.
* **HTTP Method & Endpoint:** `GET /api/v1/assignments/submissions/{submission_id}`
* **Mode:** Read-Only
* **Required Permission:** `assignment:submission_view`
* **Request Schema:**
  - Path parameter: `submission_id` (`UUID`)
* **Response Schema (`AssignmentSubmissionDetailResponse`):**
  ```json
  {
    "id": "abce1234-e89b-12d3-a456-426614174000",
    "allocation_id": "bcde2345-e89b-12d3-a456-426614174000",
    "candidate_id": "123e4567-e89b-12d3-a456-426614174000",
    "candidate_name": "Arjun Sharma",
    "candidate_number": "EX-2026-0042",
    "assignment_code": "SQL-ADV-01",
    "assignment_title": "Complex Window Functions and CTEs",
    "current_submission_status": "APPROVED",
    "current_completion_status": "PASSED_COMPLETED",
    "total_attempts": 2,
    "latest_score": 88.5,
    "due_date_utc": "2026-10-20T23:59:59Z",
    "attempts": [
      {
        "id": "cdef3456-e89b-12d3-a456-426614174000",
        "attempt_number": 1,
        "submitted_at_utc": "2026-10-18T14:10:00Z",
        "is_late": false,
        "reviews": [
          {
            "id": "defa4567-e89b-12d3-a456-426614174000",
            "reviewer_name": "Priya Nair (Reviewer)",
            "review_status": "CORRECTIONS_REQUESTED",
            "total_score": 52.0,
            "passing_threshold": 60.0,
            "feedback_notes": "Window partition syntax is invalid in Query 3. Please correct frame specifications and resubmit.",
            "created_at": "2026-10-19T09:00:00Z"
          }
        ]
      },
      {
        "id": "cdef3456-e89b-12d3-a456-426614174001",
        "attempt_number": 2,
        "submitted_at_utc": "2026-10-19T18:22:10Z",
        "is_late": false,
        "reviews": [
          {
            "id": "defa4567-e89b-12d3-a456-426614174001",
            "reviewer_name": "Priya Nair (Reviewer)",
            "review_status": "APPROVED",
            "total_score": 88.5,
            "passing_threshold": 60.0,
            "feedback_notes": "Window specifications corrected. All test cases execute cleanly.",
            "created_at": "2026-10-20T11:00:00Z"
          }
        ]
      }
    ]
  }
  ```
* **Error Responses:** `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.
* **Audit Behavior:** Read-Only.
* **Test Evidence:** [`backend/tests/test_submissions.py::test_resubmission_on_corrections_requested`](file:///backend/tests/test_submissions.py)

---

### Operation 5: Authorized Assignment Updates (Bulk Status API)
* **Purpose:** Enables Learnova to transmit assignment evaluation outcomes and corrections in batch or single-item calls.
* **HTTP Method & Endpoint:** `POST /api/v1/assignments/submissions/bulk-status`
* **Mode:** Modifies Relational Data (Transactional)
* **Required Permission:** `assignment:review`
* **Request Schema (`BulkAssignmentStatusUpdateRequest`):**
  ```json
  {
    "items": [
      {
        "submission_id": "abce1234-e89b-12d3-a456-426614174000",
        "status": "Done",
        "awarded_score": 92.0,
        "evaluator_notes": "All unit tests pass with optimal time complexity."
      },
      {
        "submission_id": "bcde2345-e89b-12d3-a456-426614174001",
        "status": "Redo",
        "correction_note": "Missing error handling block in ETL script. Minimum 5 characters required.",
        "awarded_score": 45.0
      }
    ]
  }
  ```
  *(Note: `status` accepts canonical BRD values: `"Not submitted"`, `"Submitted"`, `"Redo"`, `"Done"` or relational values: `"PENDING"`, `"SUBMITTED"`, `"CORRECTIONS_REQUESTED"`, `"APPROVED"`).*
* **Validation Rules:**
  - When status is `Redo` / `CORRECTIONS_REQUESTED`, `correction_note` is strictly mandatory ($\ge 5$ characters, non-whitespace). Blank values rejected with HTTP 422.
* **Response Schema (`BulkAssignmentStatusUpdateResponse`):**
  ```json
  {
    "total_processed": 2,
    "successful_count": 2,
    "failed_count": 0,
    "results": [
      {
        "submission_id": "abce1234-e89b-12d3-a456-426614174000",
        "success": true,
        "status": "APPROVED",
        "error": null
      },
      {
        "submission_id": "bcde2345-e89b-12d3-a456-426614174001",
        "success": true,
        "status": "CORRECTIONS_REQUESTED",
        "error": null
      }
    ]
  }
  ```
* **Audit Behavior:** Emits immutable `AuditLog` record per modified item capturing `pre_state`, `post_state`, and actor IP. Automatically re-evaluates candidate prerequisite completion and updates `Candidate.project_eligible`.
* **Test Evidence:** [`backend/tests/test_brd_alignment.py::test_bulk_assignment_status_update_endpoint`](file:///backend/tests/test_brd_alignment.py)

---

### Operation 6: Project Eligibility & Allocation Queue
* **Purpose:** Inspects candidates awaiting project group allocation, including SLA aging and overdue indicators.
* **HTTP Method & Endpoint:** `GET /api/v1/projects/queue`
* **Mode:** Read-Only
* **Required Permission:** `project:group_manage`
* **Request Schema:**
  - Query parameters: `track_id` (UUID), `batch_id` (UUID), `only_overdue` (bool, default false), `page` (int, default 1), `page_size` (int, default 20)
* **Response Schema (`ProjectQueuePaginatedResponse`):**
  ```json
  {
    "items": [
      {
        "candidate_id": "123e4567-e89b-12d3-a456-426614174000",
        "candidate_name": "Arjun Sharma",
        "candidate_number": "EX-2026-0042",
        "email": "arjun.sharma@example.com",
        "batch_code": "DATA-2026-01",
        "track_title": "Data Analytics",
        "completed_assignments_count": 8,
        "total_mandatory_assignments": 8,
        "completion_date_utc": "2026-10-05T14:00:00Z",
        "business_days_in_queue": 17,
        "is_overdue_15_days": true
      }
    ],
    "total": 1,
    "overdue_count": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
  ```
* **Error Responses:** `401 Unauthorized`, `403 Forbidden`.
* **Audit Behavior:** Read-Only.
* **Test Evidence:** [`backend/tests/test_brd_alignment.py::test_project_allocation_queue_and_overdue_tracking`](file:///backend/tests/test_brd_alignment.py)

---

### Operation 7: Project Status & Completion History
* **Purpose:** Retrieves collaborative team structure, milestone progression, and handles allocation drops.
* **HTTP Method & Endpoint:**
  - Query group: `GET /api/v1/projects/groups/{group_id}`
  - Drop allocation: `POST /api/v1/projects/groups/{group_id}/allocations/{allocation_id}/drop`
* **Mode:** Read (GET) / Modifies (POST drop)
* **Required Permission:** `candidate:profile_view` (read) / `project:group_manage` (drop)
* **Drop Request Schema (`ProjectDropRequest`):**
  ```json
  {
    "reason": "Learner took medical leave; team reconstituted with remaining 3 members."
  }
  ```
* **Response Schema (`ProjectGroupResponse`):**
  ```json
  {
    "id": "901e2345-e89b-12d3-a456-426614174000",
    "batch_id": "789e0123-e89b-12d3-a456-426614174000",
    "batch_code": "DATA-2026-01",
    "project_id": "a12e3456-e89b-12d3-a456-426614174000",
    "project_code": "DA-CAPSTONE-01",
    "project_title": "Omnichannel Retail Analytics Engine",
    "group_name": "Cohort Alpha Pod 1",
    "group_status": "IN_PROGRESS",
    "readiness_status": "BLOCKED_PENDING_MEMBERS",
    "min_size": 2,
    "target_size": 4,
    "max_size": 5,
    "member_count": 3,
    "members": [
      {
        "id": "b23e4567-e89b-12d3-a456-426614174000",
        "candidate_id": "123e4567-e89b-12d3-a456-426614174000",
        "candidate_name": "Arjun Sharma",
        "candidate_number": "EX-2026-0042",
        "role": "LEADER",
        "status": "ACTIVE",
        "joined_at": "2026-10-10T10:00:00Z"
      }
    ],
    "created_at": "2026-10-10T10:00:00Z"
  }
  ```
* **Audit Behavior:** Drop operation updates allocation to `DROPPED`, records coordinator reason, awards 0 credit, and logs `AuditLog` entry.
* **Test Evidence:** [`backend/tests/test_brd_alignment.py::test_dropped_project_requires_reason_and_preserves_history`](file:///backend/tests/test_brd_alignment.py)

---

### Operation 8: Certificate Eligibility & Credential Status
* **Purpose:** Evaluates whether a candidate satisfies all curricular requirements (100% assignments, projects, NASSCOM clearance) and tracks issuance.
* **HTTP Method & Endpoint:** `GET /api/v1/certificates/eligibility/{candidate_id}`
* **Mode:** Read-Only
* **Required Permission:** `certificate:issue_request`
* **Response Schema (`CertificateEligibilityDiagnostic`):**
  ```json
  {
    "candidate_id": "123e4567-e89b-12d3-a456-426614174000",
    "candidate_name": "Arjun Sharma",
    "track_code": "DA",
    "is_eligible": true,
    "mandatory_assignments_met": true,
    "completed_mandatory_assignments": 8,
    "total_mandatory_assignments": 8,
    "projects_met": true,
    "completed_projects_count": 2,
    "nasscom_clearance_met": true,
    "nasscom_cleared_at": "2026-10-22T00:00:00Z",
    "accredited_internship_months": 6,
    "blocking_reasons": []
  }
  ```
* **Public Verification Endpoint:** `GET /api/v1/certificates/public-verify/{identifier}`
  - Accessible publicly without login. Exposes candidate name, course, and verification status with zero internal contact information or PII.
* **Audit Behavior:** Read-Only.
* **Test Evidence:** [`backend/tests/test_brd_alignment.py::test_nasscom_clearance_gate_for_data_analytics`](file:///backend/tests/test_brd_alignment.py), [`backend/tests/test_certificates.py::test_public_verification_portal`](file:///backend/tests/test_certificates.py)

---

### Operation 9: Authentication & Session Protocol
* **Purpose:** Establishes server-managed session credentials for API access.
* **HTTP Method & Endpoint:** `POST /api/v1/auth/login` (and `POST /api/v1/auth/logout`)
* **Mode:** Session State Initialization
* **Required Permission:** Public (Login) / Active Session (Logout)
* **Request Schema (`LoginRequest`):**
  ```json
  {
    "email": "reviewer@excelr.com",
    "password": "SecurePassword123!"
  }
  ```
* **Response Schema (`LoginResponse`):**
  ```json
  {
    "user": {
      "id": "e4567890-e89b-12d3-a456-426614174000",
      "email": "reviewer@excelr.com",
      "full_name": "Priya Nair",
      "status": "ACTIVE",
      "roles": ["ASSIGNMENT_REVIEWER"],
      "permissions": ["assignment:review", "assignment:submission_view"]
    },
    "csrf_token": "a1b2c3d4e5f67890abcdef1234567890"
  }
  ```
* **Session Cookie Architecture:**
  - `track360_session`: Cryptographic 256-bit token stored in `HttpOnly`, `SameSite=Lax`, `Secure` (production) cookie.
  - `track360_csrf`: JavaScript-accessible CSRF token sent in the `x-csrf-token` header for mutating methods (`POST`, `PUT`, `PATCH`, `DELETE`).
* **Test Evidence:** [`backend/tests/test_auth.py::test_auth_login_success_sets_cookies`](file:///backend/tests/test_auth.py)

---

### Operation 10: Health Checks & Error Specifications
* **Purpose:** System probes and RFC 7807 problem details for monitoring and error handling.
* **Probes:**
  - `GET /api/v1/health`: Liveness probe (`{"status": "healthy", "app_name": "ExcelR Track360", "environment": "development"}`)
  - `GET /api/v1/ready`: Readiness probe verifying PostgreSQL connection (`{"status": "ready", "database": {"connected": true, "latency_ms": 1.45, "error": null}}`)
* **Standard RFC 7807 Error Response Schema:**
  ```json
  {
    "type": "https://track360.excelr.com/errors/validation-error",
    "title": "Unprocessable Entity",
    "status": 422,
    "detail": "Correction note must be at least 5 non-whitespace characters when status is Redo.",
    "instance": "/api/v1/assignments/submissions/bulk-status",
    "code": "REDO_NOTE_MANDATORY"
  }
  ```
* **Status Code Map:**
  - `400 Bad Request`: Malformed payload or header.
  - `401 Unauthorized`: Missing or invalid session cookie.
  - `403 Forbidden`: Authenticated user lacks required permission.
  - `404 Not Found`: Resource does not exist.
  - `409 Conflict`: Uniqueness constraint violation (duplicate email/phone/serial).
  - `422 Unprocessable Entity`: Business rule prerequisite violation.
  - `503 Service Unavailable`: Database connectivity probe failure.
* **Test Evidence:** [`backend/tests/test_health.py`](file:///backend/tests/test_health.py), [`backend/tests/test_ready.py`](file:///backend/tests/test_ready.py), [`backend/tests/test_errors.py`](file:///backend/tests/test_errors.py)

---

## 3. Implementation Checklist for Learnova Engineers

1. **Authentication:** Obtain a dedicated service account credentials or session token with the appropriate role (`ASSIGNMENT_REVIEWER` or `OPS_ADMIN`).
2. **Double-Submit CSRF:** Ensure all POST/PATCH/DELETE requests include both the `track360_session` cookie and the `x-csrf-token` header.
3. **No Duplicate Identity Creation:** Query `GET /api/v1/candidates?search={email}` before enrolling a learner; link existing Track360 `candidate.id`.
4. **Prerequisite Gating Awareness:** Do not mark learners as project-ready in external UIs; query `GET /api/v1/projects/queue` to inspect system-verified eligibility.

