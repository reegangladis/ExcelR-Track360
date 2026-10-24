# Page Inventory & UI Architecture Specification
## Project: ExcelR Track360
### Student Lifecycle & Operations Management Platform
**Document Reference:** PGI-TRK360-V1.0  
**Phase:** Phase 1 – Requirements & Business Analysis  
**Status:** Baseline Specification  

---

## 1. UI Navigation Architecture

The Track360 frontend is architected as two distinct portal experiences powered by a shared design system (Tailwind CSS and shadcn/ui):

1. **Operations & Administrative Portal (`/admin/*`):** High-density, data-intensive workspace for staff, reviewers, coordinators, and leadership.
2. **Student Progress Portal (`/student/*`):** Motivating, clear, task-oriented workspace for candidates to manage their assignments, group projects, and certificates.
3. **Public Gateway (`/verify/*`, `/login`, `/reset-password`):** Zero-friction, responsive public authentication and credential verification endpoints.

---

## 2. Public & Authentication Pages

| Page ID | Route | Page Title | Allowed Roles | Primary Purpose | Primary Actions | Key Data Displayed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PG-AUTH-01** | `/login` | Staff & Student Login | Public (Unauthenticated) | Authenticates users via server-managed session cookies. | - Submit credentials<br>- Remember me checkbox<br>- Navigate to password reset | - Email input<br>- Password input<br>- Error alerts for failed attempts / lockouts |
| **PG-AUTH-02** | `/forgot-password` | Password Recovery Request | Public (Unauthenticated) | Initiates password reset link dispatch via email. | - Enter primary email<br>- Request reset link | - Email input<br>- Rate limit cooldown banner |
| **PG-AUTH-03** | `/reset-password` | Set New Password | Public with valid token | Sets new password via signed, time-limited token. | - Enter new password<br>- Confirm password<br>- Submit reset | - Password strength meter<br>- Token expiration countdown |
| **PG-AUTH-04** | `/session-expired` | Session Timeout Notice | Public / Any Expired Session | Notifies user of session expiration; redirects safely. | - Log in again button | - Session termination reason banner |
| **PG-PUB-01** | `/verify/:serial` | Public Certificate Verification | Public (No login required) | Validates authenticity of issued certificates for employers. | - View credential status<br>- Download verification summary PDF<br>- Copy verification link | - Certificate Serial ID<br>- Candidate Name<br>- Course Track<br>- Accredited Duration<br>- Issue Date<br>- Status (`VALID` / `REVOKED`) |

---

## 3. Operations & Administrative Portal Pages

### 3.1 Overview & Candidate Management

| Page ID | Route | Page Title | Allowed Roles | Primary Purpose | Primary Actions | Key Data Displayed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PG-ADM-DASH** | `/admin/dashboard` | Operations Cockpit | Super Admin, Ops Admin, All Coordinators, Reviewers, Read-Only | Real-time bird's-eye view of operational pipeline, bottlenecks, and SLAs. | - Quick filter by batch<br>- Jump to pending review queues<br>- View system alerts | - Total active candidates<br>- Review queue SLA metrics<br>- Blocked project groups count<br>- Pending certificate approvals<br>- Activity feed |
| **PG-ADM-CAN-01**| `/admin/candidates` | Candidate Directory | Super Admin, Ops Admin, Candidate Coord, Read-Only | Search, filter, and monitor candidate lifecycle records. | - Search by name/email/phone<br>- Filter by status/batch<br>- Bulk status transition<br>- Export CSV<br>- Launch CSV import | - Candidate roster table<br>- Contact details<br>- Batch & Track<br>- Lifecycle Status badge<br>- Assignment progress %<br>- Project eligibility indicator |
| **PG-ADM-CAN-02**| `/admin/candidates/:id` | Candidate 360 Profile | Super Admin, Ops Admin, All Coordinators, Read-Only | Authoritative single-pane view of a candidate's complete history. | - Edit profile details<br>- Change lifecycle state<br>- Grant administrative waiver<br>- View audit timeline | - Biographical & contact info<br>- Academic assignments timeline<br>- Project history & group peers<br>- Internship milestones<br>- Issued certificates<br>- Full audit history |
| **PG-ADM-CAN-03**| `/admin/candidates/import` | Candidate Batch CSV Ingestion | Super Admin, Ops Admin, Candidate Coord | Multi-step dry-run and bulk ingestion of candidate rosters. | - Download CSV template<br>- Upload CSV<br>- Inspect validation matrix<br>- Confirm batch import | - File dropzone<br>- Dry-run preview summary<br>- Errored rows table with line # and error code |
| **PG-ADM-CAN-04**| `/admin/candidates/new` | Create Candidate Profile | Super Admin, Ops Admin, Candidate Coord | Manually registers an individual candidate. | - Input form validation<br>- Save candidate<br>- Cancel | - Identity & contact fields<br>- Batch & Track dropdowns<br>- Initial status selector |

---

### 3.2 Assignment & Review Workspace

| Page ID | Route | Page Title | Allowed Roles | Primary Purpose | Primary Actions | Key Data Displayed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PG-ADM-ASG-01**| `/admin/assignments` | Assignment Catalog | Super Admin, Ops Admin, Reviewer, Read-Only | Manages reusable assignment questions, rubrics, and instructions. | - Create new assignment<br>- Edit template<br>- Archive assignment | - Assignment library grid<br>- Curriculum module<br>- Passing score threshold<br>- Deliverable type |
| **PG-ADM-ASG-02**| `/admin/assignments/new` | Assignment Template Editor | Super Admin, Ops Admin | Authors rich markdown instructions, rubrics, and parameters. | - Markdown editor with preview<br>- Upload reference materials<br>- Configure scoring thresholds | - Assignment title & track<br>- Markdown body<br>- Passing score input<br>- Allowed file types |
| **PG-ADM-ASG-03**| `/admin/assignments/allocations` | Cohort Allocation Matrix | Super Admin, Ops Admin, Candidate Coord | Dispatches assignments to batches or individual candidates. | - Select batch or students<br>- Set due date & grace period<br>- Confirm batch allocation | - Allocation status table<br>- Submission rates per batch<br>- Overdue counts |
| **PG-ADM-REV-01**| `/admin/reviews` | Reviewer Queue | Super Admin, Ops Admin, Assignment Reviewer | Central dispatch queue for pending student submissions. | - Claim submission for evaluation<br>- Filter by track/reviewer/age<br>- Sort by SLA urgency | - Pending submissions list<br>- Student name & batch<br>- Submission UTC timestamp<br>- SLA timer (e.g. 18h remaining)<br>- Attempt # badge |
| **PG-ADM-REV-02**| `/admin/reviews/:subId` | Submission Evaluation Workspace | Super Admin, Ops Admin, Assignment Reviewer | Interactive grading workspace for evaluating student deliverables. | - Stream/view submitted files<br>- Compare prior attempts<br>- Enter rubric scores<br>- Submit `APPROVED`<br>- Submit `CORRECTIONS_REQUESTED` | - Student submission files & links<br>- Attempt version tabs<br>- Interactive rubric input<br>- Markdown feedback editor<br>- Previous reviewer notes |

---

### 3.3 Project & Collaborative Group Management

| Page ID | Route | Page Title | Allowed Roles | Primary Purpose | Primary Actions | Key Data Displayed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PG-ADM-PRJ-01**| `/admin/projects` | Project Catalog | Super Admin, Ops Admin, Project Coord, Read-Only | Manages industry project briefs, tiers (1, 2, 3), and rubrics. | - Create project brief<br>- Edit deliverables list<br>- Configure group size rules | - Project catalog cards<br>- Milestone tier (P1, P2, P3)<br>- Tech stack tags<br>- Active groups count |
| **PG-ADM-PRJ-02**| `/admin/projects/builder` | Project Group Builder | Super Admin, Ops Admin, Project Coord | Drag-and-drop workspace to assemble eligible students into groups. | - Filter eligible candidates<br>- Drag students into groups<br>- Assign project template<br>- Launch group project | - Unallocated eligible candidates pool<br>- Active groups being formed<br>- Group size counter indicator |
| **PG-ADM-PRJ-03**| `/admin/projects/groups` | Active Project Groups Directory | Super Admin, Ops Admin, Project Coord, Read-Only | Monitors ongoing group projects and evaluation stages. | - Search by group ID<br>- Filter by milestone tier<br>- Inspect group details | - Groups table<br>- Group name & project tier<br>- Member list & avatars<br>- Current status badge<br>- Last activity date |
| **PG-ADM-PRJ-04**| `/admin/projects/groups/:id`| Group Evaluation & Workspace | Super Admin, Ops Admin, Project Coord | Evaluates group deliverables and manages team membership. | - Stream deliverables<br>- Grade group work<br>- Request deliverable corrections<br>- Remove inactive member<br>- Split group | - Group deliverable URLs & files<br>- Member participation matrix<br>- Rubric evaluation form<br>- Historical feedback log |
| **PG-ADM-PRJ-05**| `/admin/projects/readiness`| Group Readiness Dashboard | Super Admin, Ops Admin, Project Coord | Identifies blocked groups and orchestrates progression to Next Project. | - Filter blocked groups<br>- Trigger member reminders<br>- Administrative Readiness Override<br>- Advance group to next project | - Ready groups table<br>- Blocked groups table with lagging member names<br>- Days blocked counter<br>- Override action modal |

---

### 3.4 Internship & Certificate Management

| Page ID | Route | Page Title | Allowed Roles | Primary Purpose | Primary Actions | Key Data Displayed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PG-ADM-INT-01**| `/admin/internships` | Internship Directory | Super Admin, Ops Admin, Internship Coord, Read-Only | Tracks candidate internship records, dates, and durations. | - Filter by track/status<br>- Update calendar dates<br>- Confirm completion | - Candidate name & batch<br>- Start & End calendar dates<br>- Accredited duration (3/6/9 mo)<br>- Status (`ACTIVE`, `COMPLETED`) |
| **PG-ADM-CER-01**| `/admin/certificates/queue`| Certificate Approval Queue | Super Admin, Certificate Approver | Dedicated approval gate for verifying milestones and signing credentials. | - Inspect prerequisite audit<br>- Formally Approve Issuance<br>- Reject with reason | - Pending candidate approvals<br>- Prerequisite verification badges (100% ASG, PRJ, INT)<br>- Requested duration<br>- Candidate track |
| **PG-ADM-CER-02**| `/admin/certificates` | Certificate Registry | Super Admin, Ops Admin, Certificate Approver, Read-Only | Complete registry of all issued, pending, and revoked credentials. | - Search by serial ID<br>- Download generated PDF<br>- Open public verification link<br>- Revoke certificate modal | - Unique Serial ID<br>- Candidate Name<br>- Accredited Duration<br>- Issue Date<br>- Status badge (`ISSUED`, `REVOKED`) |

---

### 3.5 Administration, Configuration & Audits

| Page ID | Route | Page Title | Allowed Roles | Primary Purpose | Primary Actions | Key Data Displayed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PG-ADM-SET-01**| `/admin/settings/users` | User & Staff Management | Super Administrator | Provisions administrative accounts and assigns system roles. | - Invite staff user<br>- Update roles<br>- Deactivate user<br>- Reset user 2FA/Password | - Staff user list<br>- Assigned roles<br>- Last login timestamp<br>- Account status |
| **PG-ADM-SET-02**| `/admin/settings/policies`| System Configuration & Policies | Super Administrator | Manages organizational business rules, group sizes, and caps. | - Adjust default group sizes<br>- Adjust project duration multipliers<br>- Update passing score defaults | - Configuration parameters form<br>- Policy change audit history |
| **PG-ADM-SET-03**| `/admin/settings/audits` | Immutable Audit Trail Explorer | Super Admin, Ops Admin, Read-Only Auditor | Inspects complete security log of all overrides and state transitions. | - Filter by actor/entity/action<br>- Search by date range<br>- Export audit log | - Audit records table<br>- Timestamp (UTC)<br>- Actor ID & Role<br>- Entity Type & ID<br>- Before & After State<br>- Justification note |
| **PG-ADM-REP-01**| `/admin/reports` | Operational Analytics & Export Center | Super Admin, Ops Admin, Read-Only | Custom reports and governed data export hub. | - Generate cohort SLA report<br>- Export student registry CSV<br>- Export completion metrics | - Interactive charts<br>- Export download triggers with format options (`CSV`, `XLSX`) |

---

## 4. Student Progress Portal Pages

| Page ID | Route | Page Title | Allowed Roles | Primary Purpose | Primary Actions | Key Data Displayed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PG-STU-DASH** | `/student/dashboard` | My Learning 360 Dashboard | Student / Candidate | Overview of candidate's individual progress, active tasks, and milestones. | - View active alerts<br>- Jump to next pending assignment<br>- Jump to group project | - Overall curriculum completion %<br>- Current lifecycle phase badge<br>- Milestone tracker (Assignments $\rightarrow$ Projects $\rightarrow$ Internship $\rightarrow$ Certificate) |
| **PG-STU-ASG-01**| `/student/assignments` | My Assignments | Student / Candidate | Roster of all assigned coursework with due dates and statuses. | - Filter by pending/completed<br>- Click to submit or view review | - Assignment cards list<br>- Due date & lateness badge<br>- Current status badge<br>- Score & feedback preview |
| **PG-STU-ASG-02**| `/student/assignments/:id`| Assignment Submission & Feedback | Student / Candidate | Details of assignment instructions, submission dropzone, and reviews. | - Upload submission file<br>- Enter repository URL<br>- Submit work<br>- View reviewer feedback & rubric | - Markdown assignment instructions<br>- Upload dropzone<br>- Attempt history tabs<br>- Reviewer qualitative comments<br>- Rubric score breakdown |
| **PG-STU-PRJ-01**| `/student/project` | My Collaborative Project | Student / Candidate | Workspace for active group project, team coordination, and readiness. | - View project brief<br>- Submit group deliverables<br>- Click "Request Next Project"<br>- View team readiness status | - Project title & deliverables checklist<br>- Teammates list with individual readiness indicators<br>- Deliverable submission links<br>- Group status banner |
| **PG-STU-INT-01**| `/student/internship` | My Internship Milestones | Student / Candidate | Displays accredited internship milestones and calendar progression. | - View internship verification status | - Formal start/end dates<br>- Accredited duration (e.g. 3, 6, 9 months)<br>- Verified project links |
| **PG-STU-CER-01**| `/student/certificates` | My Credentials | Student / Candidate | Repository of all verified certificates earned by the candidate. | - Download official PDF<br>- Copy public verification link<br>- Share credential | - Certificate preview card<br>- Unique Serial ID<br>- Verification QR code<br>- Issuance date |
| **PG-STU-ACC-01**| `/student/profile` | My Account & Notifications | Student / Candidate | Manages personal notification preferences and password. | - Update phone / contact details<br>- Change password<br>- Notification preferences | - Contact info<br>- Notification settings |
