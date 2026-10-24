# Project Structure & Repository Conventions
## Project: ExcelR Track360
### Student Lifecycle & Operations Management Platform
**Document Reference:** STR-TRK360-V1.0  
**Phase:** Phase 2 – System Architecture & Database Design  
**Status:** Approved for Implementation Planning  

---

## 1. Monorepo Directory Organization

ExcelR Track360 is organized as a structured monorepo separating frontend, backend, documentation, database migrations, and deployment infrastructure while maintaining unified version control and shared tooling.

```
excelr-track360/
├── .github/                        # CI/CD Workflows, pull request & issue templates
├── backend/                        # FastAPI Python 3.11+ application
│   ├── alembic/                    # Database migration scripts & environment
│   ├── app/                        # Application source code
│   │   ├── api/                    # API route definitions and controllers
│   │   ├── core/                   # Core infrastructure (config, security, session, DB)
│   │   ├── modules/                # Domain-driven business modules
│   │   ├── shared/                 # Shared models, schemas, and utility functions
│   │   └── main.py                 # FastAPI application entry point
│   ├── tests/                      # Pytest automated test suites
│   ├── .env.example                # Template for backend environment variables
│   ├── Dockerfile                  # Container build recipe for backend
│   ├── pyproject.toml              # Python project metadata, dependencies & tool configs
│   └── alembic.ini                 # Alembic migration configuration
├── frontend/                       # React 18+ TypeScript Vite application
│   ├── public/                     # Static assets (favicons, logos, manifests)
│   ├── src/                        # Frontend source code
│   │   ├── app/                    # Routing, layout wrappers, and global providers
│   │   ├── components/             # Reusable UI components (shadcn/ui & custom)
│   │   ├── features/               # Domain feature modules (UI, hooks, api calls)
│   │   ├── hooks/                  # Global reusable React hooks
│   │   ├── lib/                    # HTTP client, auth provider, utility libraries
│   │   ├── types/                  # Global TypeScript type definitions
│   │   ├── index.css               # Tailwind CSS base styles & design system tokens
│   │   └── main.tsx                # React DOM entry point
│   ├── tests/                      # Vitest & React Testing Library test suites
│   ├── .env.example                # Template for frontend environment variables
│   ├── Dockerfile                  # Container build recipe for frontend
│   ├── package.json                # Node dependencies & npm scripts
│   ├── tsconfig.json               # TypeScript strict compiler configuration
│   ├── tailwind.config.js          # Tailwind design tokens & theme configuration
│   └── vite.config.ts              # Vite bundler configuration & proxy settings
├── infra/                          # Infrastructure & orchestration definitions
│   ├── docker/                     # Environment-specific compose files
│   │   ├── docker-compose.dev.yml  # Local developer container stack
│   │   └── docker-compose.prod.yml # Production deployment compose stack
│   └── nginx/                      # Reverse proxy & security configuration
│       ├── nginx.conf              # Main Nginx server block
│       └── conf.d/security.conf    # TLS & security headers configuration
├── docs/                           # Authoritative platform documentation
│   ├── requirements/               # Phase 1 specifications (BRD, SRS, Rules, etc.)
│   ├── architecture/               # Phase 2 architecture specs (System, API, Security)
│   ├── database/                   # Phase 2 database specs (ERD, DDL Schema)
│   ├── workflows/                  # Operational state machines & BPMN workflows
│   └── testing/                    # QA plans & automated testing guidelines
├── scripts/                        # Maintenance, seed data, and deployment scripts
│   ├── seed_dev_data.py            # Generates synthetic candidate & cohort fixtures
│   ├── wait_for_db.py              # Startup health probe for PostgreSQL readiness
│   └── run_checks.sh               # Local pre-commit linter & test runner
├── .gitignore                      # Git exclusion rules
└── README.md                       # Platform root overview & development guide
```

---

## 2. Backend Modular Structure (`backend/app/`)

The backend codebase is structured into self-contained domain modules under `app/modules/`. This design enforces encapsulation and prevents uncontrolled cross-package coupling.

```
backend/app/
├── core/                           # System-Wide Infrastructure
│   ├── config.py                   # Pydantic BaseSettings environment loader
│   ├── database.py                 # Async SQLAlchemy engine & session factory
│   ├── exceptions.py               # RFC 7807 Exception definitions & handlers
│   ├── logging.py                  # Structured JSON logging configuration
│   ├── middleware.py               # Session extraction, CORS, and request ID middleware
│   ├── security.py                 # Argon2 password hashing & cryptographic helpers
│   └── session.py                  # Server-managed session store (DB/Redis backed)
├── shared/                         # Reusable Foundation Objects
│   ├── base_model.py               # DeclarativeBase, UUIDv7 PK, and TimestampMixin
│   ├── pagination.py               # PageRequest & PaginatedResponse[T] generic schemas
│   ├── permissions.py              # Role Enum, Permission Enum & RBAC dependency guards
│   ├── storage.py                  # Abstract StorageService (Local & S3 implementations)
│   └── schemas.py                  # Standard envelope & error models
├── modules/                        # Domain-Driven Business Modules
│   ├── auth/                       # Module 1: Identity & Sessions
│   │   ├── router.py               # /api/v1/auth endpoints (login, logout, session)
│   │   ├── service.py              # Authentication, password verify, lockout logic
│   │   ├── models.py               # User, Role, Permission, UserSession ORM models
│   │   └── schemas.py              # LoginRequest, UserResponse, SessionState schemas
│   ├── candidates/                 # Module 2: Candidate Lifecycle
│   │   ├── router.py               # /api/v1/candidates, /api/v1/batches endpoints
│   │   ├── service.py              # Candidate creation, dry-run CSV ingestion engine
│   │   ├── models.py               # Candidate, Batch, Course, Enrollment ORM models
│   │   └── schemas.py              # CandidateCreate, CSVImportReport, CandidateFilter
│   ├── assignments/                # Module 3: Assignments & Evaluation
│   │   ├── router.py               # /api/v1/assignments, /api/v1/reviews endpoints
│   │   ├── service.py              # Allocation, submission ingestion, rubric grading
│   │   ├── models.py               # Assignment, Allocation, Submission, Attempt, Review
│   │   └── schemas.py              # SubmissionCreate, ReviewEvaluate, RubricInput
│   ├── projects/                   # Module 4: Projects & Group Readiness
│   │   ├── router.py               # /api/v1/projects, /api/v1/groups endpoints
│   │   ├── service.py              # Group builder, deliverable review, readiness engine
│   │   ├── models.py               # Project, ProjectGroup, GroupMember, ProgressionRequest
│   │   └── schemas.py              # GroupCreate, DeliverableUpload, ReadinessStatus
│   ├── internships/                # Module 5: Internship Tracking
│   │   ├── router.py               # /api/v1/internships endpoints
│   │   ├── service.py              # Duration mapping policy, calendar date tracking
│   │   ├── models.py               # InternshipRecord, InternshipMilestone ORM models
│   │   └── schemas.py              # InternshipCreate, DurationReport, MilestoneUpdate
│   ├── certificates/               # Module 6: Certificates & Public Verification
│   │   ├── router.py               # /api/v1/certificates, /api/v1/verify endpoints
│   │   ├── service.py              # Eligibility check, approval gate, PDF & QR renderer
│   │   ├── models.py               # Certificate, CertificateApproval, Revocation
│   │   └── schemas.py              # CertificateIssueRequest, VerificationResponse
│   ├── notifications/              # Module 7: Notification & Email Queue
│   │   ├── router.py               # /api/v1/notifications endpoints
│   │   ├── service.py              # Notification publisher, SMTP queue worker, retries
│   │   ├── models.py               # NotificationEvent, EmailQueueEntry ORM models
│   │   └── schemas.py              # NotificationItem, EmailStatus
│   └── audit/                      # Module 8: Audit Logging & System Policies
│       ├── router.py               # /api/v1/audit-logs, /api/v1/settings endpoints
│       ├── service.py              # Immutable log writer, policy parameter manager
│       ├── models.py               # AuditLog, SystemPolicy ORM models
│       └── schemas.py              # AuditLogEntry, SystemPolicyUpdate
└── main.py                         # FastAPI App instantiation, router mounts, lifecycle
```

---

## 3. Frontend Modular Structure (`frontend/src/`)

The frontend organizes code into feature domains corresponding directly to backend services:

```
frontend/src/
├── app/                            # Application Framework Core
│   ├── layouts/                    # AdminLayout, StudentLayout, PublicLayout, AuthLayout
│   ├── routes/                     # React Router tree configuration & route guards
│   └── providers/                  # QueryClientProvider, AuthProvider, ThemeProvider
├── components/                     # Shared UI Library
│   ├── ui/                         # shadcn/ui primitives (Button, Dialog, Table, Form, etc.)
│   └── shared/                     # Data table with pagination, file dropzone, stat cards
├── features/                       # Domain Feature Modules
│   ├── auth/                       # Login form, password reset, session timeout dialog
│   │   ├── api/                    # useLoginMutation, useLogoutMutation
│   │   ├── components/             # LoginForm, ResetPasswordCard
│   │   └── schemas/                # authFormValidation.ts (Zod)
│   ├── candidates/                 # Directory, 360 profile view, CSV batch import modal
│   ├── assignments/                # Catalog, template editor, student submission dropzone
│   ├── reviews/                    # Reviewer queue, evaluation workspace, rubric grading
│   ├── projects/                   # Group builder workspace, group deliverable tracker
│   ├── readiness/                  # Group readiness monitor, lagging member alerts
│   ├── internships/                # Internship timeline, calendar milestone tracker
│   ├── certificates/               # Approval workbench, PDF download, public verify page
│   └── audit/                      # Audit trail explorer, system policy configuration
├── hooks/                          # Reusable hooks (useDebounce, useMediaQuery, useStorage)
├── lib/                            # Infrastructure Utilities
│   ├── api.ts                      # Axios/Fetch client with CSRF & session cookie defaults
│   ├── queryClient.ts              # TanStack Query client with standard staleTimes
│   └── utils.ts                    # Class name merging (cn), date formatters (UTC to Local)
├── types/                          # Shared TypeScript interface definitions
├── index.css                       # Design tokens, color system, font family imports
└── main.tsx                        # Application mount point
```

---

## 4. Architectural Naming Conventions

To ensure consistent readability across the full stack, the codebase adheres to the following conventions:

| Artifact | Convention | Examples |
| :--- | :--- | :--- |
| **Python Files & Modules** | `snake_case` | `candidate_service.py`, `group_readiness.py` |
| **Python Classes & ORM Models** | `PascalCase` | `CandidateModel`, `AssignmentSubmission`, `AuditLog` |
| **Python Functions & Methods** | `snake_case` | `evaluate_submission()`, `calculate_readiness()` |
| **Python Constants** | `UPPER_SNAKE_CASE` | `MAX_GROUP_SIZE`, `DEFAULT_PAGE_SIZE` |
| **Pydantic Schemas** | `PascalCase` + Suffix | `CandidateCreateRequest`, `SubmissionDetailResponse` |
| **TypeScript Files** | `camelCase` or `kebab-case` | `useAuth.ts`, `candidate-service.ts` |
| **TypeScript Components** | `PascalCase` | `CandidateDirectoryTable.tsx`, `SubmissionReviewCard.tsx` |
| **TypeScript Types & Interfaces**| `PascalCase` | `CandidateProfile`, `AssignmentAllocation` |
| **Database Tables** | `snake_case` (plural) | `candidates`, `assignment_submissions`, `audit_logs` |
| **Database Columns** | `snake_case` | `candidate_id`, `created_at`, `is_late` |
| **Database Primary Keys** | `id` (UUIDv7) | `id UUID NOT NULL PRIMARY KEY` |
| **Database Foreign Keys** | `[singular_entity]_id` | `candidate_id`, `batch_id`, `project_id` |
| **REST API Routes** | `kebab-case` (plural nouns) | `/api/v1/project-groups`, `/api/v1/assignment-allocations` |

---

## 5. Configuration & Environment Variable Strategy

Application configuration is managed strictly through environment variables validated at startup using Pydantic's `BaseSettings`. No secrets, keys, or environment-specific configurations are hardcoded.

### 5.1 Environment Tiers
1. **Local Development (`.env.development`):** Local PostgreSQL, local filesystem storage, debug logs enabled, fake SMTP sandbox (e.g. Mailhog).
2. **Automated Testing (`.env.test`):** Isolated test database with transaction rollback, memory-based test fixtures.
3. **Staging / Production (`.env.production`):** Managed PostgreSQL (SSL required), private S3/MinIO bucket, TLS cookies, production SMTP gateway, structured JSON logs.

### 5.2 Backend `.env.example` Specification
```bash
# Server Environment
APP_ENV=development
DEBUG=false
APP_NAME="ExcelR Track360"
APP_BASE_URL=http://localhost:3000
API_V1_PREFIX=/api/v1

# Security & Session Management
SECRET_KEY=change-this-to-a-secure-random-256-bit-key-in-production
SESSION_COOKIE_NAME=track360_session
SESSION_EXPIRE_SECONDS=28800           # 8 hours idle timeout
SESSION_COOKIE_SECURE=false             # Set to true in production with HTTPS
SESSION_COOKIE_SAMESITE=lax

# Database Configuration (PostgreSQL)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=track360_user
DATABASE_PASSWORD=track360_secure_pass
DATABASE_NAME=track360_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=false

# Storage Configuration
STORAGE_BACKEND=local                   # Options: local, s3
STORAGE_LOCAL_ROOT=./storage_private
# S3 / MinIO Settings (active if STORAGE_BACKEND=s3)
STORAGE_S3_ENDPOINT=
STORAGE_S3_BUCKET=excelr-track360-assets
STORAGE_S3_ACCESS_KEY=
STORAGE_S3_SECRET_KEY=
STORAGE_S3_REGION=us-east-1

# SMTP & Transactional Email
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=no-reply@track360.excelr.com
SMTP_FROM_NAME="ExcelR Track360"
SMTP_USE_TLS=false

# Operational Policy Defaults
DEFAULT_PASSING_SCORE=60.0
DEFAULT_MAX_PROJECTS=3
DEFAULT_GROUP_MIN_SIZE=2
DEFAULT_GROUP_TARGET_SIZE=4
DEFAULT_GROUP_MAX_SIZE=5
```

### 5.3 Frontend `.env.example` Specification
```bash
# API Base Endpoint (proxied via Vite in development)
VITE_API_BASE_URL=/api/v1
VITE_APP_TITLE="ExcelR Track360"
VITE_PUBLIC_VERIFY_URL=https://track360.excelr.com/verify
```
