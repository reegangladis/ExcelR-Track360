# ExcelR Track360

> **Track Every Student. Every Assignment. Every Milestone.**

**ExcelR Track360** is an enterprise-grade, internal Student Lifecycle & Operations Management Platform. It replaces fragmented spreadsheets and ad-hoc email communications with a unified, auditable, and role-governed operational system of record.

The platform orchestrates the complete student journey: candidate profiling, cohort onboarding, multi-attempt assignment submissions and rubric reviews, collaborative group project allocations, internship milestone tracking, tamper-evident certificate issuance, and executive operational reporting.

---

## 1. System Purpose & Core Capabilities

- **Single Golden Profile:** Maintains one authoritative record per candidate from initial enrollment through post-completion alumni status, preventing profile duplication across batches.
- **Authoritative Review Cycles:** Decouples assignment submission from approval. Enforces server-authoritative UTC timestamps, file-type validations, multi-round resubmissions, and immutable attempt versioning.
- **Strict Prerequisite Gating:** Enforces that candidates complete 100% of mandatory curriculum assignments before unlocking project allocations.
- **Dynamic Collaborative Projects:** Facilitates configurable group formation (custom team sizes), milestone reviews, group deliverable submissions, and progression tracking capped at a maximum of three (3) sequential projects.
- **Intelligent Group Readiness:** Evaluates whether all required group members have completed deliverables and submitted individual advancement requests, providing clear administrative exception workflows for lagging or inactive candidates.
- **Decoupled Internship Tracking:** Separates real-world corporate calendar internship dates from accredited certificate durations (1 project = 3 months, 2 projects = 6 months, 3 projects = 9 months).
- **Tamper-Evident Credentialing:** Enforces a two-tier approval workflow, cryptographically unique certificate serial IDs, dynamic QR codes, and a public, tokenized verification portal requiring no login.
- **Comprehensive Auditability:** Immutably records every administrative waiver, status transition, score adjustment, and data export operation.

---

## 2. Proposed Architecture & Technology Stack

The platform is designed as a **Modular Monolith** with clean domain boundaries:

```mermaid
graph LR
    subgraph Frontend Tier
        FE[React 18+ / TypeScript / Vite / Tailwind CSS / shadcn/ui]
    end

    subgraph Backend Tier
        BE[FastAPI / Python 3.11+ / SQLAlchemy 2.0 Async / Pydantic v2]
    end

    subgraph Data & Storage Tier
        DB[(PostgreSQL 15+)]
        Storage[(Private Object Storage)]
    end

    FE -->|Server-managed Session Cookies / REST| BE
    BE --> DB
    BE --> Storage
```

### Technology Stack Specifications
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui component primitives, React Router v6, TanStack Query v5, React Hook Form, Zod.
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (Async/Declarative), Alembic migrations, Pydantic v2 schemas.
- **Database:** PostgreSQL 15+.
- **Testing:** Pytest, HTTPX, Vitest, React Testing Library.
- **Infrastructure:** Docker, Docker Compose, Git.
- **Security:** Server-side managed sessions (`HttpOnly`, `SameSite=Lax`, encrypted cookies), server-side RBAC on every API endpoint, private asset storage via temporary streaming tokens.

---

## 3. Documentation Structure

All system design, architectural models, and specifications reside under [`docs/`](file:///c:/Users/ExcelR/OneDrive/Desktop/ExcelR%20Track360/docs/):

```
docs/
├── requirements/
│   ├── BRD.md                          # Business Requirements Document
│   ├── SRS.md                          # Software Requirements Specification
│   ├── USER_ROLES_AND_PERMISSIONS.md   # Role-Permission Matrix across 9 roles
│   ├── BUSINESS_RULES.md               # Explicit logic & exception rules
│   ├── WORKFLOW_SPECIFICATION.md       # Step-by-step lifecycle workflows & states
│   ├── PAGE_INVENTORY.md               # Catalog of 30+ admin & student pages
│   ├── ACCEPTANCE_CRITERIA.md          # Given-When-Then testable specifications
│   └── OPEN_BUSINESS_QUESTIONS.md      # Unresolved decisions & stakeholder options
├── architecture/
│   ├── SYSTEM_ARCHITECTURE.md          # Modular monolith design, boundaries & lifecycle
│   ├── PROJECT_STRUCTURE.md            # Monorepo layout, modules & conventions
│   ├── API_DESIGN.md                   # RESTful standards, envelopes & endpoint inventory
│   ├── SECURITY_DESIGN.md              # Session lifecycle, Argon2id, RBAC, PII & audit
│   ├── TESTING_STRATEGY.md             # Quality gates, Pytest, Vitest & E2E scenarios
│   └── PHASE_2_DECISIONS.md            # ADRs, tradeoffs & schema adaptability
├── database/
│   ├── ERD.md                          # Mermaid entity relationship diagrams & indexes
│   └── DATABASE_SCHEMA.md              # 37-table PostgreSQL DDL schema & constraints
├── workflows/                          # State machines & sequence flows
└── testing/
    ├── README.md                       # Quality assurance & automated test plans
    └── PHASE_3_TEST_REPORT.md          # Phase 3 verification report & test results
```

---

## 4. Planned 18-Phase Development Roadmap

Track360 is built systematically across 18 development phases to guarantee production rigor and zero unverified assumptions:

| Phase | Phase Name | Focus & Primary Deliverables | Status |
| :---: | :--- | :--- | :---: |
| **01** | **Requirements & Business Analysis** | BRD, SRS, Role Matrix, Business Rules, Workflows, Page Inventory, Acceptance Criteria, Open Questions. | **COMPLETE** |
| **02** | **System Architecture & Database Design** | Modular Monolith architecture, monorepo layout, ERD, 37-table DDL schema, API design, security architecture, testing strategy, ADRs. | **COMPLETE** |
| **03** | **Project Foundation & Environment Setup** | Runnable FastAPI backend, React 18 + Vite frontend, PostgreSQL dev config, health & ready probes, automated test suites. | **COMPLETE** |
| **04** | **Database Schema Design & Data Modeling** | Declarative SQLAlchemy 2.0 models (37 tables), UUIDv7 keys, Alembic migrations, database test fixtures. | *Up Next* |
| **05** | **Authentication, Sessions & RBAC Foundation** | Cookie session management, password hashing, role guard middlewares, authentication endpoints. | Planned |
| **06** | **Candidate Management Module** | Authoritative profiles, CSV batch import with dry-run validation, candidate search & filters. | Planned |
| **07** | **Assignment Authoring & Allocation Engine** | Template editor, rubric parameters, batch & individual student allocations, deadline rules. | Planned |
| **08** | **Student Submission & Private Storage** | Student submission dropzone, private file storage streaming, server UTC timestamping, lateness flags. | Planned |
| **09** | **Assignment Review & Resubmission Engine** | Reviewer queues, rubric scoring workspace, correction requests, immutable attempt history. | Planned |
| **10** | **Milestone Progression & Project Eligibility Gate** | 100% assignment passing verification engine, eligibility badges, exception waiver workflows. | Planned |
| **11** | **Project Catalog & Dynamic Group Builder** | Project specs library, drag-and-drop group builder, configurable sizing, duplicate check. | Planned |
| **12** | **Group Deliverable Submission & Evaluation** | Shared group deliverables repository, team evaluation workspace, corrections cycle. | Planned |
| **13** | **Group Readiness & Multi-Project Progression** | Readiness engine, blocked member alerts, inactive member removal, split workflows, max 3 projects cap. | Planned |
| **14** | **Internship Tracking & Duration Policy Mapping** | Calendar date tracking, duration multiplier policy (1=3mo, 2=6mo, 3=9mo), milestone completion. | Planned |
| **15** | **Certificate Approvals & Public Verification** | Two-tier approval gate, unique serial generation, PDF & QR engine, public verification portal. | Planned |
| **16** | **Notifications & Communication Queue** | In-app alerts, background SMTP email dispatch queue, retry with exponential backoff. | Planned |
| **17** | **Operational Reporting & Audit Log Explorer** | Executive cockpits, SLA metrics, immutable audit explorer, role-governed CSV/Excel exports. | Planned |
| **18** | **End-to-End Hardening, QA & Production Readiness** | Integration test suite, security penetration audit, performance load testing, operational runbooks. | Planned |

> **Roadmap Alignment Note:** The original 18-phase roadmap establishes Phase 3 as **Project Foundation & Environment Setup** and Phase 4 as **Database Schema Design & Data Modeling**. The Phase 2 summary table had tentatively referenced database modeling under the Phase 3 label; this discrepancy is formally reconciled by preserving the original 18-phase sequence.

---

## 5. Developer Quickstart Guide

### Prerequisites
- **Python:** 3.11+
- **Node.js:** 20+ (tested on v24.19) and **npm:** 10+
- **PostgreSQL:** 15+ or 16 (local service or Docker)
- **Docker & Docker Compose** (optional for containerized PostgreSQL)

### 1. Environment Setup
```bash
# Backend environment setup
cp backend/.env.example backend/.env

# Frontend environment setup
cp frontend/.env.example frontend/.env.local
```

### 2. Running the Backend
```bash
cd backend
# Run development server
uvicorn app.main:app --reload --port 8000
```
- Swagger Docs: `http://localhost:8000/api/v1/docs`
- Health Probe: `http://localhost:8000/api/v1/health`
- Readiness Probe: `http://localhost:8000/api/v1/ready`

### 3. Running the Frontend
```bash
cd frontend
# Install dependencies
npm install

# Start Vite development server
npm run dev
```
- Frontend UI: `http://localhost:5173`

### 4. Running PostgreSQL with Docker Compose
```bash
docker compose up -d postgres
```

### 5. Automated Testing
```bash
# Run backend tests (8 passing unit & integration tests)
python -m pytest backend/tests

# Run frontend tests (Vitest + React Testing Library)
cd frontend && npm test

# Run frontend TypeScript type-check
cd frontend && npm run lint
```

---

## 6. Current Development Phase

- **Active Phase:** Phase 3 – Project Foundation & Environment Setup
- **Milestone Status:** **100% Complete.** Runnable backend, React frontend, Docker Compose configuration, health and readiness probes, and automated test suites verified.

---

## 7. Instructions for Progressing to Phase 4

To proceed to **Phase 4: Database Schema Design & Data Modeling**:
1. Verify that both backend and frontend test suites are passing.
2. Ensure no uncommitted working files remain in the repository.
3. Instruct the assistant:
   > *"Phase 3 is verified and complete. Proceed to Phase 4: Database Schema Design & Data Modeling."*
