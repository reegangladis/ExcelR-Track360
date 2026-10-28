# Database Migration, Backup, and Disaster Recovery Runbook
## Project: ExcelR Track360 (Student Lifecycle & Operations Management Platform)
**Effective Date:** October 28, 2026  
**Database Lead:** Database Administrator & Site Reliability Engineering Team  
**Governing Document:** Learner Progress Platform — Business Requirements Document (BRD, dated October 26, 2026)  
**Database Engine:** PostgreSQL 18 (Dedicated Port: 5433)  

---

## 1. Migration Architecture & Version History

ExcelR Track360 manages all relational schema versions using **Alembic** (the standard database migration tool for SQLAlchemy).

### Migration Chain & Heads

The current migration head is **`2725b5d30dab`**, comprising 9 chronological, linear revisions:

| Revision ID | Down Revision | Description / Scope | Applied Date |
| :--- | :--- | :--- | :--- |
| `001_core_system` | None (Initial) | Core user accounts, roles, permissions, candidate master, course tracks, batches, and enrollments. | Initial Setup |
| `002_assignment_mgmt` | `001_core_system` | Assignment definitions, rubric criteria templates, dual batch/candidate allocations. | Migration Chain |
| `003_submissions_engine`| `002_assignment_mgmt` | Submissions, attempt versioning, file assets, lateness tracking, reviewer feedback. | Migration Chain |
| `004_project_catalog` | `003_submissions_engine`| Project specifications across Tiers 1–3, sequential milestones, rubric weights. | Migration Chain |
| `005_project_groups` | `004_project_catalog` | Dynamic group sizing (`min_size`, `target_size`, `max_size`), group memberships, leaders, mentors. | Migration Chain |
| `006_allocations_flow` | `005_project_groups` | Project allocations, collaborative group readiness state machine, deliverable reviews. | Migration Chain |
| `007_internships` | `006_allocations_flow` | Decoupled calendar dates, accredited duration multipliers, corporate partner records. | Migration Chain |
| `008_certificates` | `007_internships` | Cryptographic SHA-256 hashes, dynamic QR codes, two-stage approval workflow (SoD). | Migration Chain |
| `2725b5d30dab` | `008_certificates` | Notifications center, persistent email dispatch queue, forensic immutable audit logs. | **Head (Current)** |

### Checking Current Migration Status
```powershell
# Navigate to backend directory
cd "c:\Users\ExcelR\OneDrive\Desktop\ExcelR Track360\backend"

# Check active head revision
python -m alembic current

# View complete revision history
python -m alembic history --verbose
```

---

## 2. Database Schema Integrity & Constraints

The Track360 relational model enforces data integrity at the database layer through native constraints:

1. **Unique Constraints:**
   - `uq_candidates_email` / `uq_candidates_phone`: Prevents duplicate candidate registration.
   - `uq_candidates_number`: Enforces unique sequential candidate identifier (`EX-2026-XXXX`).
   - `uq_allocations_candidate_assignment`: Enforces at most one active allocation per candidate per assignment.
   - `uq_certificates_serial_number` / `uq_certificates_verification_hash`: Protects tamper-evident credential verification.
2. **Check Constraints:**
   - `chk_submission_status`: Enforces valid submission states (`PENDING`, `SUBMITTED`, `LATE_SUBMITTED`, `UNDER_REVIEW`, `CORRECTIONS_REQUESTED`, `APPROVED`, `REJECTED`).
   - `chk_completion_status`: Strictly enforces `current_completion_status IN ('INCOMPLETE', 'PASSED_COMPLETED', 'FAILED')`.
   - `chk_allocations_target`: Enforces that an allocation must belong to either a batch or an individual candidate (`batch_id IS NOT NULL OR candidate_id IS NOT NULL`).
   - `chk_group_sizing`: Enforces `min_size <= target_size <= max_size`.
3. **Foreign Key Referential Integrity:**
   - Deletions of parent entities (`Course`, `CourseTrack`, `Candidate`, `Assignment`) are strictly restricted via `ON DELETE RESTRICT` to prevent accidental orphaned operational data.

---

## 3. Routine Backup Procedures (pg_dump)

In accordance with BRD Part 13 operational requirements, database backups must be executed daily and retained for at least 30 days.

### Standard Logical Backup Command
```powershell
# Set environment variables for the dedicated PostgreSQL cluster
$env:PGHOST = "localhost"
$env:PGPORT = "5433"
$env:PGUSER = "track360_user"
$env:PGPASSWORD = "track360_secure_pass"

# Generate timestamped backup file
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "C:\Users\ExcelR\OneDrive\Desktop\ExcelR Track360\backups\track360_backup_$timestamp.dump"

# Ensure backup directory exists
if (-not (Test-Path "C:\Users\ExcelR\OneDrive\Desktop\ExcelR Track360\backups")) {
    New-Item -ItemType Directory -Path "C:\Users\ExcelR\OneDrive\Desktop\ExcelR Track360\backups"
}

# Execute custom-format compressed backup
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" `
    -h $env:PGHOST `
    -p $env:PGPORT `
    -U $env:PGUSER `
    -F c `
    -b `
    -v `
    -f $backupFile `
    track360_dev
```

---

## 4. Disaster Recovery & Restore Procedures

> [!CAUTION]
> Never restore directly into a live production database without first taking a pre-restore safety snapshot. Always perform test restorations into an isolated staging database (`track360_restore_test`).

### Step-by-Step Restoration Protocol

1. **Verify Backup Archive Integrity:**
   ```powershell
   & "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" -l $backupFile | Select-Object -First 20
   ```
2. **Create Fresh Disposable Target Database:**
   ```powershell
   $env:PGPASSWORD = "track360_secure_pass"
   & "C:\Program Files\PostgreSQL\18\bin\dropdb.exe" -h localhost -p 5433 -U track360_user --if-exists track360_restore_test
   & "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -h localhost -p 5433 -U track360_user -O track360_user track360_restore_test
   ```
3. **Execute Parallel Restoration:**
   ```powershell
   & "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" `
       -h localhost `
       -p 5433 `
       -U track360_user `
       -d track360_restore_test `
       -v `
       -j 2 `
       $backupFile
   ```
4. **Post-Restore Schema & Row Reconciliation:**
   ```powershell
   # Run table row count reconciliation
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -p 5433 -U track360_user -d track360_restore_test -c "
   SELECT schemaname, relname, n_live_tup 
   FROM pg_stat_user_tables 
   ORDER BY n_live_tup DESC;
   "
   ```
5. **Alembic Head Verification on Restored Database:**
   ```powershell
   $env:DATABASE_URL = "postgresql+asyncpg://track360_user:track360_secure_pass@localhost:5433/track360_restore_test"
   python -m alembic current
   # Expected Output: 2725b5d30dab (head)
   ```

---

## 5. Recovery Objectives (RPO & RTO)

- **Recovery Point Objective (RPO):** Maximum 24 hours of data loss during disaster scenario via automated nightly backups. With PostgreSQL WAL archiving enabled, RPO $<15$ minutes.
- **Recovery Time Objective (RTO):** Full database restoration and application reconnection within **30 minutes**.
- **Retention Schedule:** Daily backup archives retained locally and on secondary storage for **30 calendar days**.
