# API Architecture & Endpoint Specification
## Project: ExcelR Track360
### Student Lifecycle & Operations Management Platform
**Document Reference:** API-TRK360-V1.0  
**Phase:** Phase 2 – System Architecture & Database Design  
**Status:** Approved for Implementation Planning  

---

## 1. RESTful Principles & Design Standards

ExcelR Track360 exposes a RESTful HTTP API governed by the following architectural standards:

1. **Protocol & Base URL:** HTTPS only. Base URL prefix: `/api/v1`.
2. **Resource Naming:** Clear plural nouns (e.g., `/candidates`, `/assignments`, `/project-groups`). Query parameters are formatted in `snake_case`.
3. **HTTP Verbs:**
   - `GET`: Idempotent resource retrieval. Zero side effects.
   - `POST`: Resource creation, state transition triggers, and batch operations.
   - `PUT` / `PATCH`: Idempotent complete replacement or partial updates.
   - `DELETE`: Soft deletion or revocation operations.
4. **Content Negotiation:** All request and response bodies use `application/json`, except binary file upload and streaming endpoints which use `multipart/form-data` and `application/octet-stream`.

---

## 2. Request & Response Envelopes

### 2.1 Standard Paginated List Envelope
```json
{
  "data": [
    { "id": "0192a83f-42e1-7000-8000-000000000001", "first_name": "Rohan", "last_name": "Sharma", "email": "rohan.s@example.com" }
  ],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total_items": 1420,
    "total_pages": 57,
    "has_next": true,
    "has_prev": false
  }
}
```

### 2.2 Standard Single Resource Envelope
```json
{
  "data": {
    "id": "0192a83f-42e1-7000-8000-000000000001",
    "candidate_number": "CAN-2026-00042",
    "lifecycle_status": "ACTIVE",
    "created_at": "2026-10-24T12:00:00Z"
  }
}
```

### 2.3 Standard RFC 7807 Error Envelope
```json
{
  "type": "https://errors.track360.excelr.com/DUPLICATE_CANDIDATE",
  "title": "Conflict Detected",
  "status": 409,
  "detail": "A candidate with email 'rohan.s@example.com' is already registered.",
  "instance": "/api/v1/candidates",
  "code": "ERR_DUPLICATE_RESOURCE",
  "timestamp": "2026-10-24T12:35:00Z",
  "invalid_params": [
    { "name": "email", "reason": "Already exists in candidate registry" }
  ]
}
```

---

## 3. Query Parameters: Filtering, Sorting & Pagination

All list endpoints support standard query parameters:
- `page`: 1-based page number (default: `1`).
- `page_size`: Number of records per page (default: `25`, max: `100`).
- `sort_by`: Column to sort on (e.g. `created_at`, `due_date`, `score`).
- `sort_order`: Direction (`asc` or `desc`, default: `desc`).
- `search`: Case-insensitive text search matching names, emails, or codes.

---

## 4. Comprehensive Endpoint Inventory

### 4.1 Module 1: Authentication & Session Management (`/api/v1/auth`)

| Method | Endpoint | Allowed Roles | Description | Request Body | Response Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Public (Unauth) | Authenticates credentials, issues HttpOnly session cookie. | `LoginRequest` | 200 OK |
| `POST` | `/api/v1/auth/logout` | Authenticated | Revokes current session and clears cookie. | Empty | 200 OK |
| `GET` | `/api/v1/auth/me` | Authenticated | Returns current authenticated user profile & permissions. | Empty | 200 OK |
| `POST` | `/api/v1/auth/forgot-password`| Public (Unauth) | Queues password recovery email with signed token. | `ForgotPasswordRequest` | 200 OK |
| `POST` | `/api/v1/auth/reset-password` | Public (Unauth) | Resets password using token verification. | `ResetPasswordRequest` | 200 OK |

---

### 4.2 Module 2: Candidate & Cohort Management (`/api/v1/candidates`, `/api/v1/batches`)

| Method | Endpoint | Allowed Roles | Description | Request Body | Response Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/candidates` | Staff, Reviewers | Lists candidates with filtering, search, and pagination. | Query Params | 200 OK |
| `POST` | `/api/v1/candidates` | Super Admin, Ops Admin, Candidate Coord | Manually registers a single candidate profile. | `CandidateCreateRequest` | 201 Created |
| `GET` | `/api/v1/candidates/{id}` | Staff, Reviewers, Student (Own) | Retrieves 360-degree candidate profile and milestones. | Empty | 200 OK |
| `PATCH`| `/api/v1/candidates/{id}` | Super Admin, Ops Admin, Candidate Coord | Updates candidate contact or academic details. | `CandidateUpdateRequest` | 200 OK |
| `POST` | `/api/v1/candidates/{id}/status`| Super Admin, Ops Admin | Transitions lifecycle status (e.g., to ON_HOLD or DROPPED). | `StatusTransitionRequest` | 200 OK |
| `POST` | `/api/v1/candidates/import/dry-run`| Candidate Coord, Ops Admin | Uploads CSV roster for dry-run validation without DB insert. | `multipart/form-data` | 200 OK |
| `POST` | `/api/v1/candidates/import/commit` | Candidate Coord, Ops Admin | Commits a validated CSV batch import job. | `{"job_id": "UUID"}` | 200 OK |
| `GET` | `/api/v1/batches` | Staff, Reviewers | Lists academic cohorts and assigned tracks. | Query Params | 200 OK |
| `POST` | `/api/v1/batches` | Ops Admin, Super Admin | Creates a new cohort batch. | `BatchCreateRequest` | 201 Created |

---

### 4.3 Module 3: Assignments, Allocations & Reviews (`/api/v1/assignments`, `/api/v1/reviews`)

| Method | Endpoint | Allowed Roles | Description | Request Body | Response Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/assignments` | Staff, Reviewers | Lists assignment templates in catalog. | Query Params | 200 OK |
| `POST` | `/api/v1/assignments` | Ops Admin, Super Admin | Creates assignment template with rubrics and rules. | `AssignmentCreateRequest`| 201 Created |
| `POST` | `/api/v1/assignments/allocations` | Ops Admin, Candidate Coord | Allocates assignments to a batch or individual student. | `AllocationCreateRequest`| 201 Created |
| `GET` | `/api/v1/student/allocations` | Student (Own only) | Lists student's personal assignment allocations and statuses. | Query Params | 200 OK |
| `POST` | `/api/v1/allocations/{id}/submit` | Student (Own only) | Submits assignment file or repository URL (records server UTC). | `multipart/form-data` | 201 Created |
| `GET` | `/api/v1/reviews/queue` | Reviewers, Ops Admin | Returns pending submission evaluation queue with SLA timer. | Query Params | 200 OK |
| `GET` | `/api/v1/reviews/submissions/{id}` | Reviewers, Staff, Student (Own) | Retrieves complete submission attempt history and rubrics. | Empty | 200 OK |
| `POST` | `/api/v1/reviews/submissions/{id}/evaluate` | Reviewers, Ops Admin | Submits official evaluation (`APPROVED`, `CORRECTIONS`, `REJECTED`). | `ReviewEvaluationRequest`| 200 OK |

---

### 4.4 Module 4: Projects, Groups & Group Readiness (`/api/v1/projects`, `/api/v1/groups`)

| Method | Endpoint | Allowed Roles | Description | Request Body | Response Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/projects` | Staff, Reviewers | Lists project catalog briefs and tiers (1, 2, 3). | Query Params | 200 OK |
| `POST` | `/api/v1/projects` | Project Coord, Ops Admin | Creates project brief with deliverable schemas. | `ProjectCreateRequest` | 201 Created |
| `GET` | `/api/v1/projects/eligible-candidates`| Project Coord, Ops Admin | Queries candidates with 100% assignments passed. | Query Params | 200 OK |
| `POST` | `/api/v1/project-groups` | Project Coord, Ops Admin | Forms a collaborative group and allocates project. | `GroupCreateRequest` | 201 Created |
| `GET` | `/api/v1/project-groups/{id}` | Staff, Group Members | Retrieves group workspace, deliverables, and readiness status. | Empty | 200 OK |
| `POST` | `/api/v1/project-groups/{id}/submit` | Group Members | Uploads shared project deliverables (URL + PDF). | `DeliverableUploadRequest`| 201 Created |
| `POST` | `/api/v1/project-groups/{id}/evaluate` | Project Coord, Ops Admin | Grades group deliverable against rubric. | `GroupEvaluationRequest` | 200 OK |
| `POST` | `/api/v1/project-groups/{id}/request-progression`| Student (Member) | Candidate submits individual request to advance to next project. | Empty | 200 OK |
| `GET` | `/api/v1/project-groups/{id}/readiness`| Staff, Group Members | Returns detailed group readiness checklist and blockers. | Empty | 200 OK |
| `POST` | `/api/v1/project-groups/{id}/override` | Project Coord, Ops Admin | Administratively advances ready candidates with audit note. | `OverrideRequest` | 200 OK |
| `POST` | `/api/v1/project-groups/{id}/remove-member`| Project Coord | Detaches inactive member and triggers readiness recalculation. | `RemoveMemberRequest` | 200 OK |

---

### 4.5 Module 5: Internship Management (`/api/v1/internships`)

| Method | Endpoint | Allowed Roles | Description | Request Body | Response Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/internships` | Internship Coord, Staff | Lists internship records with calendar dates and durations. | Query Params | 200 OK |
| `POST` | `/api/v1/internships` | Internship Coord, Ops Admin | Initializes formal candidate internship record. | `InternshipCreateRequest`| 201 Created |
| `PATCH`| `/api/v1/internships/{id}` | Internship Coord | Updates formal start/end calendar dates or notes. | `InternshipUpdateRequest`| 200 OK |
| `POST` | `/api/v1/internships/{id}/complete`| Internship Coord | Confirms verified completion of internship milestone. | `InternshipCompleteRequest`| 200 OK |

---

### 4.6 Module 6: Certificates & Public Verification (`/api/v1/certificates`, `/api/v1/verify`)

| Method | Endpoint | Allowed Roles | Description | Request Body | Response Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/certificates/queue` | Certificate Approver, Super Admin | Returns pending certificate requests awaiting sign-off. | Query Params | 200 OK |
| `POST` | `/api/v1/certificates/request` | Coordinators, Ops Admin | Initiates certificate issuance request for eligible candidate. | `CertIssueRequest` | 201 Created |
| `POST` | `/api/v1/certificates/{id}/approve` | Certificate Approver, Super Admin | Formally signs off; triggers PDF & unique serial generation. | `CertApprovalRequest` | 200 OK |
| `GET` | `/api/v1/certificates/{id}/download` | Certificate Approver, Staff, Student (Own)| Streams authentic, high-resolution certificate PDF. | Empty | 200 OK (PDF) |
| `POST` | `/api/v1/certificates/{id}/revoke` | Certificate Approver, Super Admin | Revokes issued certificate with mandatory reason category. | `CertRevokeRequest` | 200 OK |
| `GET` | `/api/v1/verify/{serial_number}` | Public (No Auth Required) | Public verification endpoint returning real-time validity status.| Empty | 200 OK |

---

### 4.7 Module 7: Files, Notifications & Auditing (`/api/v1/files`, `/api/v1/audit-logs`)

| Method | Endpoint | Allowed Roles | Description | Request Body | Response Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/files/{id}/stream` | Authenticated (Authorized roles)| Authenticated, tokenized streaming of private asset. | Empty | 200 OK (Stream) |
| `GET` | `/api/v1/notifications` | Authenticated (Own notifications)| Lists in-app notifications for the logged-in user. | Query Params | 200 OK |
| `PATCH`| `/api/v1/notifications/{id}/read` | Authenticated (Own notifications)| Marks in-app notification as read. | Empty | 200 OK |
| `GET` | `/api/v1/audit-logs` | Super Admin, Ops Admin, Auditor | Queries immutable security audit trail. | Query Params | 200 OK |
| `GET` | `/api/v1/settings/policies` | Super Admin | Reads global configurable policies (group size, pass marks). | Empty | 200 OK |
| `PUT` | `/api/v1/settings/policies/{key}` | Super Admin | Updates configurable system policy parameter with audit log. | `PolicyUpdateRequest` | 200 OK |
