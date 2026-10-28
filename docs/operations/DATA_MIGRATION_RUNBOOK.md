# Historical Spreadsheet Migration Runbook & Execution Protocol
## Project: ExcelR Track360 (Student Lifecycle & Operations Management Platform)
**Effective Date:** October 28, 2026  
**Data Lead:** Lead Data Engineer & Business Analyst  
**Governing Document:** Learner Progress Platform — Business Requirements Document (BRD, dated October 26, 2026)  
**Historical Scope:** Approximately 69,000 unique learners across ~285,000 spreadsheet rows in 4 source workbooks.  

---

## 1. Scope, Context & Ingestion Strategy

Historically, ExcelR operational coordinators tracked learner assignment submissions, milestone evaluations, project allocations, and internship accreditations across 4 primary Excel spreadsheets.

### Planning Figures vs Relational Reality
- **Planning Volume:** ~69,000 learners and ~285,000 historical rows across 4 files.
- **Critical Principle:** A spreadsheet row does **NOT** equal a unique learner. Many learners span multiple rows across different batches, milestones, and courses.
- **Authority:** The Track360 relational model enforces a single Golden Candidate profile (`Candidate`) linked to multiple `Enrollment`, `AssignmentSubmission`, and `ProjectAllocation` records.
- **Integrity Rule:** Never overwrite existing verified candidate records during trial imports. All ingestion operations must be strictly idempotent.

---

## 2. Spreadsheet Semantic Mapping Rules

Historical spreadsheets utilized ad-hoc cell fills, free-form text, and blank cells. The ingestion pipeline applies strict deterministic conversion rules:

| Spreadsheet Visual / Cell Value | Target Track360 Status | Conversion Logic & Semantic Rule |
| :--- | :--- | :--- |
| **Green Cell Fill** | `Done` (`APPROVED`) | Converted to `Done` **only** if evaluator name or passing score is present, or cohort policy explicitly confirms green fill denotes 100% completion. |
| **Blank / White Cell** | `Not submitted` (`PENDING`) | Converted to `Not submitted` with zero attempts recorded. |
| **Pending / Review Needed** | `Submitted` (`SUBMITTED`) | Converted to `Submitted` with current timestamp and attempt #1 created. |
| **Correction / Redo Text** | `Redo` (`CORRECTIONS_REQUESTED`) | Converted to `Redo`. The cell's textual notes are captured as the evaluator's mandatory correction note. If empty, flagged for coordinator review. |
| **Score $\ge$ Passing Threshold** | `Done` (`APPROVED`) | Score recorded in `latest_score` and `current_completion_status = 'PASSED_COMPLETED'`. |
| **Score < Passing Threshold** | `Redo` (`CORRECTIONS_REQUESTED`) | Attempt recorded, score preserved, review note required for resubmission. |

---

## 3. The 20-Stage Migration Lifecycle Protocol

In strict alignment with BRD Part 10, the migration proceeds through the following 20 ordered phases:

1. **Source Inventory & Custody:** Identify the 4 source files, worksheets/tabs, columns, and designated department owners (Data Analytics, Full Stack, Cloud, Management).
2. **Field Schema Mapping:** Establish explicit column-to-attribute mappings (`Candidate.first_name`, `Candidate.email`, `Candidate.phone`, `Batch.batch_code`, `Assignment.code`).
3. **Traceability Provenance:** Store source filename, worksheet name, and source row number in `import_row_results.source_metadata` for every imported record.
4. **Data Normalization:** Normalize all names (trim, title-case), emails (lowercase, strip whitespace), phone numbers (E.164 standard formatting), and ISO dates.
5. **Visual State Transformation:** Convert assignment cell colors and free-text statuses into the 4 canonical business states.
6. **Green Cell Audit:** Verify that green cells correspond to approved deliverables before marking `Done`.
7. **Blank Cell Audit:** Verify that empty cells represent unsubmitted work rather than omitted records.
8. **Pending Note Extraction:** Extract historical feedback notes for `Redo` records; generate placeholder notes for records requiring coordinator review.
9. **Project & Credential Reconstruction:** Reconstruct historical project allocations, start dates, completion dates, and issued certificate serial numbers.
10. **Exception Segregation:** Flag duplicate emails, conflicting phone numbers, missing batch codes, and ambiguous names into an exception quarantine table.
11. **Dry-Run Import Report Generation:** Execute `preview_csv_import` generating summary metrics (valid rows, error rows, duplicate candidates).
12. **Pilot Trial Run (Data Analytics):** Execute pilot import on the largest course, **Data Analytics**, into an isolated staging schema.
13. **50-Record Random Sample Verification:** Randomly select 50 candidates from the imported batch and perform side-by-side reconciliation against original spreadsheet cells.
14. **Metric & Count Reconciliation:** Compare total learners, completed assignments, and project counts between spreadsheet pivot tables and database SQL aggregations.
15. **Exception Resolution Hearing:** Present quarantined exceptions to course coordinators for authorized manual resolution.
16. **Formal Steering Committee Sign-off:** Secure written approval from the Operations Director and Lead Business Analyst before initiating full production migration.
17. **Full Production Migration:** Execute automated, chunked batch import (batches of 5,000 rows) with transaction rollbacks on unexpected errors.
18. **Two-Week Parallel Operations:** Run ExcelR Track360 alongside the existing spreadsheets for exactly 14 calendar days. Staff record all submissions in both systems.
19. **Parallel Discrepancy Auditing:** Daily automated delta scripts compare spreadsheet inputs against Track360 audit logs, resolving discrepancies.
20. **Spreadsheet Archival:** Convert historical spreadsheet files to read-only archives (`.xlsx` read-only lock) and store them in secure cold storage after final executive sign-off.

---

## 4. Reconciliation SQL Queries

To verify import fidelity post-migration, execute the following audit scripts:

```sql
-- 1. Total Imported Candidates vs Unique Emails
SELECT 
    COUNT(*) AS total_candidates,
    COUNT(DISTINCT email) AS unique_emails,
    COUNT(DISTINCT phone) AS unique_phones
FROM candidates;

-- 2. Assignment Status Distribution Across Batches
SELECT 
    b.batch_code,
    s.current_submission_status,
    s.current_completion_status,
    COUNT(*) AS total_submissions
FROM assignment_submissions s
JOIN assignment_allocations a ON s.allocation_id = a.id
JOIN batches b ON a.batch_id = b.id
GROUP BY b.batch_code, s.current_submission_status, s.current_completion_status
ORDER BY b.batch_code, total_submissions DESC;

-- 3. Quarantined Import Exceptions Summary
SELECT 
    error_field,
    error_message,
    COUNT(*) AS occurrence_count
FROM import_batch_rows
WHERE is_valid = FALSE
GROUP BY error_field, error_message
ORDER BY occurrence_count DESC;
```
