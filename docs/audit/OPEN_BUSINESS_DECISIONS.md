# Open Business Decisions & Organizational Policy Registry
## Project: ExcelR Track360 (Student Lifecycle & Operations Management Platform)
**Document Reference:** OBD-TRK360-V1.0  
**Audit Date:** October 28, 2026  
**Status:** Mandatory Active Decisions Registry  

---

## 1. Governance & Purpose

In adherence to Part 16 of the Master Implementation Directives (*"Do not invent business policy, pretend integration exists, or make unverified assumptions"*), this document records the 12 critical business decisions, operational ambiguities, and architectural dependencies identified during the October 28, 2026 audit.

For each decision, this registry outlines:
1. The exact question.
2. Why it matters to the architecture and operational rollout.
3. The options identified from the business requirements document.
4. The implementation affected in the codebase.
5. The safe temporary/fallback behavior adopted.
6. The required organizational authority for final sign-off.

---

## 2. Master Business Decisions Registry

### OBQ-01: LMS System Ownership & Overlap Boundary
* **Question:** Does the new LMS portal already own learner records, course enrollments, assignment submissions, project allocations, and progress reporting?
* **Why it Matters:** Determines whether Track360 operates as the primary operational system of record or as a complementary administrative tool. Deploying a competing student database risks duplicate student logins, desynchronized records, and operational confusion.
* **Identified Options:**
  - *Option A (Track360 Authoritative Monolith):* Track360 serves as the single operational master for learner progress, assignments, projects, internships, and certificates.
  - *Option B (LMS Master with Track360 Operations Layer):* LMS owns student-facing portal and assignment uploads; Track360 ingests completion events and manages project allocations, coordinator workflows, and certificates.
  - *Option C (Full LMS Migration):* If the LMS natively supports multi-attempt rubrics, group project caps, and two-tier certification, Track360 is retired in favor of LMS configuration.
* **Affected Codebase:** Backend learner models, assignment dropzone, candidate registry, and authentication routes.
* **Safe Temporary Behavior:** Continue safe local development of Track360 as an independent operational modular monolith; do not connect to external production LMS APIs or deploy competing production infrastructure until confirmed.
* **Required Approver:** Head of Technology & Academic Product Owner.
* **Current Status:** **BLOCKED ON BUSINESS CONFIRMATION**

---

### OBQ-02: Authoritative Master for Learner Identity
* **Question:** Which system holds authoritative precedence for learner identity: Track360, the new LMS, or the CRM/ERP enrollment database?
* **Why it Matters:** Governs primary key mapping, duplicate resolution rules, and whether Track360 can update learner biographical details.
* **Identified Options:**
  - *Option A:* Track360 generates and owns the golden student enrollment ID (`EX-YYYY-XXXX`).
  - *Option B:* Track360 consumes external CRM/LMS student UUIDs and maintains them as foreign keys.
* **Affected Codebase:** [`Candidate`](file:///c:/Users/ExcelR/OneDrive/Desktop/ExcelR%20Track360/backend/app/modules/candidates/models.py#L99) schema and CSV import service.
* **Safe Temporary Behavior:** Support deterministic internal `candidate_number` while preserving external enrollment IDs and strict email/phone uniqueness constraints.
* **Required Approver:** Operations Director & Enterprise Architect.
* **Current Status:** **OPEN**

---

### OBQ-03: Operational Application & Hosting Budget Approval
* **Question:** Has the operational application, technology stack, and cloud hosting budget been formally approved beyond the no-cost HTML prototype?
* **Why it Matters:** The BRD specifies that the first deliverable is a no-cost prototype, and paid hosting/tools require formal sign-off before Phase 2.
* **Identified Options:**
  - *Option A:* Approval granted for on-premise / self-hosted PostgreSQL and FastAPI server on existing internal servers.
  - *Option B:* Cloud managed hosting approved (e.g. AWS/Azure RDS and container services).
  - *Option C:* Initial deployment restricted to local intranet and zero-cost prototypes.
* **Affected Codebase:** Docker Compose, production deployment scripts, object storage providers.
* **Safe Temporary Behavior:** Maintain zero-cost local execution (local PostgreSQL, local filesystem file storage); avoid cloud billing or paid third-party SaaS commitments.
* **Required Approver:** Managing Director & Finance Head.
* **Current Status:** **OPEN (Prototype Active)**

---

### OBQ-04: Project Team Sizing Policy (~40 Learners)
* **Question:** The BRD mentions approximately 40 learners per project. Does this mean one large collective cohort project with 40 participants, or 8–10 smaller sub-teams of 4–5 members executing the project in parallel?
* **Why it Matters:** Dictates group formation algorithms, mentor allocations, group readiness calculations, deliverable review workspaces, and peer contribution metrics.
* **Identified Options:**
  - *Option A (Single 40-member Cohort Project):* The entire cohort collaborates on a single shared project repository.
  - *Option B (Sub-team Structure of 3–5 Members):* Approximately 40 learners in a batch are partitioned into 8–10 independent project groups working on the same project specification.
* **Affected Codebase:** [`ProjectGroup`](file:///c:/Users/ExcelR/OneDrive/Desktop/ExcelR%20Track360/backend/app/modules/projects/models.py#L105) capacity constraints (`min_size`, `target_size`, `max_size`).
* **Safe Temporary Behavior:** Maintain dynamic, configurable team sizing (`min_size`, `target_size`, `max_size`) on `ProjectGroup` rather than hardcoding any fixed value.
* **Required Approver:** Head of Training & Project Operations Lead.
* **Current Status:** **OPEN**

---

### OBQ-05: Certificate Issuance Cadence (Per-Project vs Cumulative)
* **Question:** Does each completed project produce a separate, independent 3-month internship certificate, or is a single cumulative 3-, 6-, or 9-month credential issued upon program completion?
* **Why it Matters:** Influences certificate serial numbering, revocation policies, ReportLab PDF templates, and public verification records.
* **Identified Options:**
  - *Option A (Incremental Per-Project):* Candidate receives an individual certificate after each project (Project 1 = 3-month cert, Project 2 = 3-month cert, Project 3 = 3-month cert).
  - *Option B (Cumulative Credential):* Candidate receives one exit credential reflecting total accredited duration (1 project = 3 months, 2 projects = 6 months, 3 projects = 9 months).
* **Affected Codebase:** [`CertificateRecord`](file:///c:/Users/ExcelR/OneDrive/Desktop/ExcelR%20Track360/backend/app/modules/certificates/models.py#L27) and [`CertificateService`](file:///c:/Users/ExcelR/OneDrive/Desktop/ExcelR%20Track360/backend/app/modules/certificates/service.py).
* **Safe Temporary Behavior:** Support `certificate_type` of both `FINAL_COMPREHENSIVE` and `MILESTONE` in data models; default to cumulative credential with configurable duration mapping.
* **Required Approver:** Certification Director & Academic Council.
* **Current Status:** **OPEN**

---

### OBQ-06: NASSCOM Clearance Ownership & Verification
* **Question:** Who owns and enters NASSCOM assessment clearance for Data Analytics, Business Analytics, and Data Science candidates, and how is it verified?
* **Why it Matters:** The BRD specifies that course certificates for DA, BA, and DS tracks cannot be issued without NASSCOM clearance. It must not be inferred from assignment completion.
* **Identified Options:**
  - *Option A:* Operations Administrator manually records NASSCOM clearance date and test score after receiving official NASSCOM roster.
  - *Option B:* Batch CSV import of NASSCOM scorecard results.
* **Affected Codebase:** [`Candidate`](file:///c:/Users/ExcelR/OneDrive/Desktop/ExcelR%20Track360/backend/app/modules/candidates/models.py#L99) model, candidate profile API, and certificate eligibility service.
* **Safe Temporary Behavior:** Implement explicit `nasscom_cleared` field and clearance logging endpoint restricted to `ROLE_OPS_ADMIN` and `ROLE_SUPER_ADMIN`.
* **Required Approver:** Academic Director & Certification Head.
* **Current Status:** **OPEN**

---

### OBQ-07: Initial Production Role Rollout
* **Question:** Which of the 9 user roles must be activated in the initial production release, and which belong to later phases?
* **Why it Matters:** Affects initial user onboarding, staff training, and login portal access. For example, student self-service and placement tracking are designated for later phases.
* **Identified Options:**
  - *Option A (Staff-Only Initial Rollout):* Super Admin, Operations Admin, Candidate Coordinator, Assignment Reviewer, Project Coordinator, Certification Team. Student portal disabled initially while submissions continue via email.
  - *Option B (Full Portal Rollout):* Activate all 9 roles including Student Portal simultaneously.
* **Affected Codebase:** Frontend navigation routes, [`ProtectedRoute`](file:///c:/Users/ExcelR/OneDrive/Desktop/ExcelR%20Track360/frontend/src/components/ProtectedRoute.tsx), and student dropzone views.
* **Safe Temporary Behavior:** Preserve all role definitions in the RBAC matrix; allow configuration flag to restrict portal access to staff during initial deployment.
* **Required Approver:** Operations Director.
* **Current Status:** **OPEN**

---

### OBQ-08: Data Retention & Audit Log Policy
* **Question:** What is the mandatory archival and retention period for learner records, assignment attempts, submitted files, and immutable audit logs?
* **Why it Matters:** Governs disk storage capacity planning, backup retention schedules, and GDPR/DPDP regulatory compliance.
* **Identified Options:**
  - *Option A:* 3-year active retention, followed by cold compressed backup.
  - *Option B:* 7-year statutory educational record retention.
  - *Option C:* Indefinite retention of golden candidate records and issued certificate hashes, with file asset purging after 12 months.
* **Affected Codebase:** Database pruning cron jobs, local file asset management, and backup scripts.
* **Safe Temporary Behavior:** Enforce soft-deletion across all learner entities; do not purge historical submission attempts or audit logs until retention policy is approved.
* **Required Approver:** Legal & Compliance Officer.
* **Current Status:** **OPEN**

---

### OBQ-09: Named Product Owner & System Administrator
* **Question:** Who are the designated, named organizational product owners and system administrators with sign-off authority for Track360?
* **Why it Matters:** Ensures clear accountability for approving business rule changes, security waivers, and production releases.
* **Safe Temporary Behavior:** Use organizational role titles (`Operations Administrator`, `Super Administrator`) rather than inventing individual staff names.
* **Required Approver:** Executive Management.
* **Current Status:** **PENDING APPOINTMENT**

---

### OBQ-10: Bulk Update Performance Target (5 Seconds vs 5 Minutes)
* **Question:** The BRD contains two conflicting performance expectations for bulk updates: one section specifies under 5 seconds, while another states 5 minutes for cohort batches. Which target is authoritative?
* **Why it Matters:** Dictates whether bulk operations are processed synchronously in the HTTP request-response cycle (requiring <5 seconds) or offloaded to an asynchronous background worker queue (e.g. Celery/Redis) with progress polling.
* **Identified Options:**
  - *Option A (Synchronous HTTP):* Bulk update of up to 100 assignment records completed within 2–5 seconds inside a single database transaction.
  - *Option B (Asynchronous Job Queue):* Bulk imports of 1,000+ records processed via background task queue with job ID and progress updates.
* **Affected Codebase:** [`AssignmentService.bulk_status_update`](file:///c:/Users/ExcelR/OneDrive/Desktop/ExcelR%20Track360/backend/app/modules/assignments/service.py) and CSV ingestion services.
* **Safe Temporary Behavior:** Implement high-performance bulk SQL operations (`executemany` within single transaction) that execute under 2 seconds for cohort batches (up to 100 rows), while supporting batched chunking for historical imports.
* **Required Approver:** Lead System Architect & Product Owner.
* **Current Status:** **OPEN**

---

### OBQ-11: Holiday Calendar for 15-Business-Day Allocation Target
* **Question:** Which official organizational or national holiday calendar should be excluded when computing the 15-business-day project allocation window?
* **Why it Matters:** Business-day calculations currently exclude Saturdays and Sundays. National/state public holidays (e.g., Republic Day, Diwali, Independence Day) also impact SLA calculations.
* **Identified Options:**
  - *Option A (Weekends Only):* Saturday and Sunday excluded from business-day counter.
  - *Option B (Weekends + Configurable Holiday Calendar):* Exclude weekends plus a database-configured holiday table.
* **Affected Codebase:** `calculate_business_days` in `app/shared/business_calendar.py`.
* **Safe Temporary Behavior:** Implement weekend exclusion as default, with parameter supporting a list of custom holiday dates.
* **Required Approver:** Human Resources & Operations Lead.
* **Current Status:** **OPEN**

---

### OBQ-12: Ambiguous Duplicate Learner Resolution Protocol
* **Question:** During historical data migration of 69,000 learners, what is the approved workflow when a record matches an existing learner by phone number or name, but has a different email address?
* **Why it Matters:** Automatic merging risks conflating two separate individuals with shared family phone numbers or identical common names, while creating separate records risks duplicate certificate issuance.
* **Identified Options:**
  - *Option A:* Automatic merge if phone number and full name match.
  - *Option B (Strict Separation & Human Review):* Flag record as an ambiguous duplicate exception in the import preview report; require authorized coordinator to inspect and approve merge or separation.
* **Affected Codebase:** Migration script and CSV import service.
* **Safe Temporary Behavior:** Adopt Option B: never auto-merge on phone/name alone; flag conflicting rows in trial import exceptions table for human review.
* **Required Approver:** Data Governance Lead & Candidate Operations Manager.
* **Current Status:** **OPEN**
