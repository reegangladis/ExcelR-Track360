# End-to-End Operational Workflow Verification Report
## Project: ExcelR Track360 (Student Lifecycle & Operations Management Platform)
**Execution Date:** October 28, 2026  
**Environment:** Isolated Local Staging Environment (FastAPI + PostgreSQL 18 on Port 5433)  
**Governing Document:** Learner Progress Platform — Business Requirements Document (BRD, dated October 26, 2026)  
**Verification Method:** Automated End-to-End Integration Scenario via Pytest & Live API Calls  

---

## 1. Overview & Verification Objective

This report documents the verification of the complete 17-step operational lifecycle mandated in Part 14 of the master specification. The verification traces a learner's progression from initial enrollment through assignment completion, project allocation, dropped project handling, project deliverable review, internship accreditation, two-stage certificate approval, cryptographic public verification, audit logging, and security boundary enforcement.

All tests were executed against the dedicated PostgreSQL test database using synthetic candidate data (zero real personal learner data).

---

## 2. End-to-End Journey Execution Matrix

| Step # | Journey Milestone / Action | Endpoint / Service Method | Expected Business Behavior | Verified Result | Evidence Reference |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **1** | **Create Learner Profile** | `POST /api/v1/candidates/` | Generates candidate number `EX-2026-XXXX`, validates email/phone uniqueness, sets `lifecycle_status = ACTIVE`. | **PASS** | `test_candidates.py::test_candidate_crud_and_duplicate_prevention` |
| **2** | **Batch & Course Enrollment** | `POST /api/v1/candidates/{id}/enroll` | Associates learner with specific track (`Data Analytics`) and active cohort batch. | **PASS** | `test_assignments.py::test_assignment_allocation_to_batch_and_candidate` |
| **3** | **Assign Curriculum Deliverables** | `POST /api/v1/assignments/allocations/batch` | Provisions mandatory and optional assignment allocations with UTC due dates. | **PASS** | `test_assignments.py::test_assignment_allocation_to_batch_and_candidate` |
| **4** | **Record Submission** | `POST /api/v1/assignments/submissions/{id}/submit` | Records email submission deliverable, sets status `SUBMITTED`, calculates lateness delta. | **PASS** | `test_submissions.py::test_assignment_submission_lifecycle` |
| **5** | **Evaluator Redo Request** | `POST /api/v1/assignments/submissions/{id}/review` | Reject blank/whitespace note ($<5$ chars) with HTTP 422; accept valid note, setting status to `CORRECTIONS_REQUESTED` (Redo). | **PASS** | `test_brd_alignment.py::test_redo_validation_enforces_meaningful_correction_note` |
| **6** | **Resubmission & Evaluator Approval** | `POST /api/v1/assignments/submissions/bulk-status` or `/review` | Candidate resubmits attempt #2; evaluator grades $\ge 60$ pts and sets status to `Done` (`APPROVED`). | **PASS** | `test_submissions.py::test_resubmission_on_corrections_requested`, `test_brd_alignment.py::test_bulk_assignment_status_update_endpoint` |
| **7** | **Incomplete Prerequisite Gating** | `GET /api/v1/projects/queue` / `allocate_project` | Learner with 1/2 mandatory assignments completed is blocked from project allocation; `project_eligible = False`. | **PASS** | `test_submissions.py::test_prerequisite_gating_project_eligibility` |
| **8** | **100% Completion & Queue Entry** | `AssignmentService.bulk_update_assignment_statuses` | When 100% mandatory assignments are `Done`, candidate automatically enters project queue (`project_eligible = True`). | **PASS** | `test_brd_alignment.py::test_bulk_assignment_status_update_endpoint` |
| **9** | **15-Business-Day Queue SLA** | `GET /api/v1/projects/queue` | Queue displays working days elapsed (excluding Saturdays & Sundays) and sets `is_overdue_15_days = True` for records $>15$ working days. | **PASS** | `test_brd_alignment.py::test_project_allocation_queue_and_overdue_tracking` |
| **10** | **Bulk Project Allocation** | `POST /api/v1/projects/groups/{id}/allocate-project` | Coordinator allocates eligible queue learners to dynamic project group (`min_size` to `max_size`), sets status `ALLOCATED`. | **PASS** | `test_allocations.py::test_dynamic_group_sizing_on_allocation` |
| **11** | **Dropped Project Workflow** | `POST /api/v1/projects/groups/{id}/allocations/{alloc_id}/drop` | Dropping without reason fails with HTTP 422; with valid reason sets `DROPPED`, preserves history, awards zero completion credit. | **PASS** | `test_brd_alignment.py::test_dropped_project_requires_reason_and_preserves_history` |
| **12** | **Deliverable Review & Project Completion**| `POST /api/v1/projects/groups/{id}/submissions/{sub_id}/review` | Evaluator approves capstone rubric ($\ge 70\%$); marks milestone complete, increments `completed_projects_count = 1`. | **PASS** | `test_allocations.py::test_deliverable_submission_and_rubric_review` |
| **13** | **Internship Duration Multiplier** | `POST /api/v1/internships/` | Decouples calendar dates from accredited duration policy (1 project = 3 months, 2 = 6 months, 3 = 9 months). | **PASS** | `test_internships.py::test_internship_initialization_and_calendar_decoupling` |
| **14** | **NASSCOM Clearance Gate** | `CertificateService.calculate_candidate_eligibility` | Data Analytics course certificates require verified NASSCOM score in candidate academic records before approval. | **PASS** | `test_brd_alignment.py::test_nasscom_clearance_gate_for_data_analytics` |
| **15** | **Two-Stage Approval (SoD)** | `POST /api/v1/certificates/{id}/stage1-review` & `/stage2-approve` | Stage 1 Coordinator review followed by independent Director sign-off. Same user cannot approve both stages. | **PASS** | `test_certificates.py::test_two_stage_approval_and_sod_enforcement` |
| **16** | **Cryptographic QR Verification** | `GET /api/v1/certificates/public/verify/{hash}` | Validates SHA-256 certificate hash and serial number; returns candidate name and course title with zero private PII. | **PASS** | `test_certificates.py::test_public_verification_portal` |
| **17** | **Audit Trail & RBAC Isolation** | `GET /api/v1/audit/logs` / Unauthorized Role Checks | All state mutations produce tamper-evident audit records. Student role cannot access administrative endpoints (HTTP 403). | **PASS** | `test_notifications_and_audit.py::test_audit_logs_and_csv_export`, `test_candidates.py::test_candidate_idor_protection_for_students` |

---

## 3. Verified Scenario Trace Details

### Scenario A: Strict Redo Note Enforcement (BRD Part 5)
```python
# Blank or whitespace-only feedback is rejected by the server:
POST /api/v1/assignments/submissions/32cdc107-.../review
Payload: {"review_outcome": "CORRECTIONS_REQUESTED", "qualitative_feedback": "   "}
Response: HTTP 422 Unprocessable Entity
Detail: "When review_outcome is CORRECTIONS_REQUESTED (Redo), a meaningful correction note with at least 5 characters is mandatory."

# Valid feedback succeeds:
Payload: {"review_outcome": "CORRECTIONS_REQUESTED", "qualitative_feedback": "Please fix unit test assertions and re-submit code."}
Response: HTTP 201 Created
Outcome: Status updated to CORRECTIONS_REQUESTED; attempt #1 review recorded.
```

### Scenario B: 15-Business-Day Queue SLA Calculation (BRD Part 7)
```python
# Candidate completed assignments on Friday 2026-10-02 (26 calendar days ago):
GET /api/v1/projects/queue?track_id=39aef0ec-...
Response: HTTP 200 OK
{
  "total": 1,
  "overdue_count": 1,
  "items": [{
    "candidate_number": "EX-Q1-da12",
    "completion_date_utc": "2026-10-02T10:00:00Z",
    "business_days_in_queue": 17,       # Exactly 17 weekdays elapsed (8 weekend days excluded)
    "is_overdue_15_days": true          # Correctly flagged as SLA breached (> 15 business days)
  }]
}
```

### Scenario C: NASSCOM Clearance Verification Gate (BRD Part 8)
```python
# Candidate has 100% assignments passed and 1 project completed in Data Analytics:
Diagnostic Evaluation:
  assignments_completed = True
  projects_completed = True
  requires_nasscom = True (Track: "Data Analytics Professional Track")
  nasscom_cleared = False (No official score on file)
Result: is_eligible = False, ineligibility_reasons = ["NASSCOM clearance is required for Data Analytics Professional Track course certificates before issuance. Official clearance record is pending."]

# Administrator records verified NASSCOM score in academic record:
POST CandidateNote: "NASSCOM assessment CLEARED with score 88% on 2026-10-25"
Diagnostic Re-evaluation:
  nasscom_cleared = True
Result: is_eligible = True, ineligibility_reasons = [] (Blocker resolved)
```
