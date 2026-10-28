# Release Readiness & Deployment Verification Checklist
## Project: ExcelR Track360 (Student Lifecycle & Operations Management Platform)
**Assessment Date:** October 28, 2026  
**Auditor:** Technical Lead, Software Architect, Security Engineer, QA Engineer  
**Governing Document:** Learner Progress Platform — Business Requirements Document (BRD, dated October 26, 2026)  
**Release Target:** Initial Operational Release & Prototype Evaluation  

---

## 1. Executive Release Gate Decision

| Release Milestone | Readiness Verdict | Detailed Condition & Evidence |
| :--- | :---: | :--- |
| **Stage 1: No-Cost HTML Prototype** | **APPROVED / READY** | Standalone interactive prototype delivered at [`prototype/index.html`](file:///c:/Users/ExcelR/OneDrive/Desktop/ExcelR%20Track360/prototype/index.html). Incurs $0 in cloud/hosting costs. Ready for staff review. |
| **Stage 2: Core Operational Application** | **CODE COMPLETE & VERIFIED / BLOCKED FOR PRODUCTION** | All 72 backend tests pass, all 56 frontend tests pass, TypeScript clean, Vite build successful. **Blocked from live production rollout** pending business resolution of LMS overlap and formal budget/hosting approvals (OBQ-01, OBQ-03). |
| **Stage 3: Deferred Capabilities** | **CONFIRMED DEFERRED** | Placement module, learner self-service file upload portal, and real-time LMS sync remain cleanly decoupled and deferred to Phase 3/4. |

---

## 2. Release Boundary & Phase Traceability

| Functional Domain | BRD Target Phase | Current Status | Release Boundary Policy |
| :--- | :---: | :---: | :--- |
| **No-Cost Interactive Prototype** | Phase 1 | **VERIFIED** | Deployed locally at `prototype/index.html` for stakeholder feedback. |
| **Candidate Golden Master & Batches** | Phase 2 | **VERIFIED** | De-duplication, batch enrollments, lifecycle transitions verified. |
| **Assignment Tracking & Bulk Updates** | Phase 2 | **VERIFIED** | 4 canonical statuses, redo note validation, bulk endpoint verified. |
| **Email Submission Workflow** | Phase 2 | **VERIFIED** | Submissions managed via email; coordinator inputs results in Track360. |
| **15-Business-Day Project Queue** | Phase 2 | **VERIFIED** | SLA weekend-exclusion counter, queue aging, overdue reporting. |
| **Dynamic Project Groups (Tiers 1-3)**| Phase 2 | **VERIFIED** | Dynamic group sizing (`min_size` to `max_size`), milestone reviews. |
| **Dropped Project Handling** | Phase 2 | **VERIFIED** | Mandatory coordinator reason, zero completion credit, audit logging. |
| **Decoupled Internship Accreditation**| Phase 2 | **VERIFIED** | 1 project = 3M, 2 = 6M, 3 = 9M duration multiplier verified. |
| **Two-Stage Certificate Issuance** | Phase 2 | **VERIFIED** | Coordinator review $\to$ Director approval with SoD enforcement. |
| **NASSCOM Clearance Gate** | Phase 2 | **VERIFIED** | Verified NASSCOM score required for DA/BA/DS course certificates. |
| **Tamper-Evident QR Verification** | Phase 2 | **VERIFIED** | Public tokenized verification portal without internal PII disclosure. |
| **Forensic Immutable Audit Trail** | Phase 2 | **VERIFIED** | Full forensic JSON state diffs, CSV exports, tamper prevention. |
| **Student Self-Service Portal** | Phase 3 | *Deferred* | Preserved in codebase but inactive on staff operational dashboard. |
| **In-Platform Direct File Uploads** | Phase 3 | *Deferred* | File upload infrastructure ready; submission workflow remains email. |
| **LMS Automated Sync Integration** | Phase 3/4 | *Deferred* | Explicitly blocked until LMS data ownership matrix is approved. |
| **Placement Tracking Subsystem** | Phase 4 | *Deferred* | Out of initial release scope. |

---

## 3. Technical & Security Verification Checklist

### Security & Privacy (OWASP Alignment)
- [x] **Authentication:** Argon2id password hashing with unique salt; account lockout after 5 failed login attempts.
- [x] **Session Security:** Cryptographically random 256-bit session tokens stored in HttpOnly, SameSite=Lax, Secure cookies.
- [x] **CSRF Protection:** Double-submit cookie + custom header (`x-csrf-token`) verified on all POST/PUT/PATCH/DELETE endpoints.
- [x] **Authorization (RBAC):** Server-side permission dependencies (`require_permission`) on all 40+ API endpoints.
- [x] **Insecure Direct Object References (IDOR):** Verified isolation; candidates cannot view other candidate records.
- [x] **Public Verification Privacy:** Public `/verify/{hash}` endpoint exposes only candidate name, course title, and issue date; zero phone, email, or score leakage.
- [x] **Input Validation:** Pydantic v2 schemas reject malformed payloads, enforce string length constraints, and validate types.

### Code Quality & Build Integrity
- [x] **Backend Test Suite:** `python -m pytest` passes with **72/72 tests** green (100% pass rate).
- [x] **Frontend Unit & Component Tests:** `npm test -- --run` passes with **56/56 tests** green across 12 test files.
- [x] **Static Type Check:** `npm run lint` (`tsc --noEmit`) passes with **0 errors**.
- [x] **Production Bundle Build:** `npm run build` compiles clean production bundle into `dist/` in 13.77s.
- [x] **Database Schema Consistency:** 9 Alembic revisions applied; current head matches code models (`2725b5d30dab`).

### Release Hygiene & Packaging
- [x] **Credential Exclusion:** Active `.env` files excluded from version control and release packages (`.gitignore`).
- [x] **Sample Configuration:** Dedicated `.env.example` provided with placeholder credentials and documentation.
- [x] **Artifact Exclusion:** `node_modules/`, `__pycache__/`, `.pytest_cache/`, `dist/`, and local temporary dumps excluded from source bundle.
- [x] **Git Repository Integrity:** Full commit history preserved; zero destructive rebases or resets performed.

---

## 4. Outstanding Business Blockers (Must Resolve Before Stage 2 Production)

1. **LMS Overlap & Data Authority (OBQ-01 / OBQ-02):** Written resolution from the LMS product owner confirming whether the new LMS portal tracks assignments and projects.
2. **Budget & Hosting Approval (OBQ-03):** Formal executive sign-off for operational cloud hosting, managed PostgreSQL, and email SMTP provider.
3. **Project Grouping Policy (OBQ-04):** Business confirmation whether 40 learners in a capstone constitute one large team or multiple small pods (current system supports configurable dynamic sizing).
4. **Certificate Multiplier Ambiguity (OBQ-05):** Confirmation whether learners receive separate 3-month certificates per project or one cumulative credential (3/6/9 months).
5. **NASSCOM Operating Procedures (OBQ-06):** Confirmation of the designated liaison responsible for uploading official NASSCOM clearance rosters.
