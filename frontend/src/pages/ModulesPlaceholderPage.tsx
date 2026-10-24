import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, Clock, FileCode, CheckCircle } from 'lucide-react';

interface ModuleConfig {
  title: string;
  phase: string;
  phaseNumber: number;
  description: string;
  plannedFeatures: string[];
}

const moduleMap: Record<string, ModuleConfig> = {
  '/candidates': {
    title: 'Candidate Lifecycle Management',
    phase: 'Phase 6: Candidate Management Module',
    phaseNumber: 6,
    description: 'Golden master profiles, batch CSV ingestion engine with dry-run validation, and lifecycle status tracking.',
    plannedFeatures: [
      'Single Authoritative Profile (zero duplication on email/phone)',
      'Batch CSV Ingestion with dry-run error matrix',
      'Advanced search, filtering by cohort, and pagination',
      'Lifecycle state transitions (Enrolled -> Active -> Completed)',
    ],
  },
  '/assignments': {
    title: 'Assignment Management & Review Queue',
    phase: 'Phases 7–9: Assignment Authoring, Submission & Evaluation',
    phaseNumber: 7,
    description: 'Assignment template library, cohort dispatching, server UTC submission timestamping, and rubric reviews.',
    plannedFeatures: [
      'Reusable assignment question library with markdown rubrics',
      'Cohort & individual student allocation models',
      'Private storage upload with file format whitelisting',
      'Iterative review cycles (Submitted -> Corrections Requested -> Approved)',
      'Attempt versioning & complete reviewer history preservation',
    ],
  },
  '/projects': {
    title: 'Collaborative Projects & Group Readiness',
    phase: 'Phases 10–13: Project Engine, Group Builder & Readiness',
    phaseNumber: 10,
    description: '100% assignment prerequisite gating, dynamic group formation, shared deliverables, and readiness tracking.',
    plannedFeatures: [
      'Prerequisite gating (100% mandatory assignments completed)',
      'Dynamic group builder (configurable sizing, never hardcoded to 4)',
      'Shared group deliverable evaluation & scoring',
      'Group readiness calculation engine before next project progression',
      'Sequential project progression capped at standard max 3 projects',
    ],
  },
  '/internships': {
    title: 'Internship Milestones Management',
    phase: 'Phase 14: Internship Milestone Tracking',
    phaseNumber: 14,
    description: 'Formal corporate internship tracking decoupled from accredited certificate duration calculations.',
    plannedFeatures: [
      'Calendar start date and end date logging',
      'Configurable duration mapping (1 proj = 3mo, 2 proj = 6mo, 3 proj = 9mo)',
      'Milestone completion verification',
    ],
  },
  '/certificates': {
    title: 'Certificate Issuance & Public Verification',
    phase: 'Phase 15: Credentialing & Verification Portal',
    phaseNumber: 15,
    description: 'Two-tier verification approval, unique serial generation, high-res PDF rendering, and zero-auth verification.',
    plannedFeatures: [
      'Two-tier approval gate by Certificate Approver role',
      'Cryptographically unique serial generation (EXCELR-[YEAR]-[TRACK]-[HEX8])',
      'Dynamic QR code embedding and PDF generation',
      'Public verification endpoint (/verify/:serial) requiring no login',
      'Duplicate issuance prevention and revocation tracking',
    ],
  },
  '/audit': {
    title: 'Audit Logging & System Governance',
    phase: 'Phase 17: Operational Reporting & Audit Logs',
    phaseNumber: 17,
    description: 'Immutable append-only audit trail capturing every override, waiver, score adjustment, and data export.',
    plannedFeatures: [
      'Immutable database audit logging with actor IP and pre/post states',
      'Mandatory textual justification for administrative waivers',
      'Role-governed data export center with logging',
    ],
  },
};

export const ModulesPlaceholderPage: React.FC = () => {
  const location = useLocation();
  const config = moduleMap[location.pathname] || {
    title: 'Module Under Development',
    phase: 'Scheduled Phase',
    phaseNumber: 0,
    description: 'This operational module is scheduled in the 18-phase implementation roadmap.',
    plannedFeatures: ['Architectural design complete in Phase 2', 'Implementation scheduled in designated phase'],
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <Link
        to="/"
        className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-500 hover:text-brand-600 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to System Dashboard</span>
      </Link>

      <div className="bg-white rounded-3xl border border-slate-200/80 p-8 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-brand-50 text-brand-700 border border-brand-200/60 mb-2 font-mono">
              <Clock className="w-3.5 h-3.5" />
              <span>{config.phase}</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              {config.title}
            </h1>
          </div>

          <span className="self-start sm:self-center px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 font-mono">
            Status: Design Complete
          </span>
        </div>

        <p className="text-sm text-slate-600 leading-relaxed">
          {config.description}
        </p>

        <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/60 space-y-4">
          <div className="flex items-center space-x-2 text-sm font-semibold text-slate-800">
            <FileCode className="w-4 h-4 text-brand-600" />
            <span>Approved Specifications & Scope</span>
          </div>

          <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-600">
            {config.plannedFeatures.map((feat) => (
              <li key={feat} className="flex items-start space-x-2">
                <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                <span>{feat}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="p-4 rounded-xl bg-blue-50/60 border border-blue-100 text-xs text-blue-900">
          <span className="font-semibold block mb-1">Architecture Alignment:</span>
          Full DDL schemas, state machine transition tables, and API contracts for this module are documented in{' '}
          <code className="font-mono bg-blue-100/80 px-1.5 py-0.5 rounded text-blue-950 font-semibold">docs/database/DATABASE_SCHEMA.md</code> and{' '}
          <code className="font-mono bg-blue-100/80 px-1.5 py-0.5 rounded text-blue-950 font-semibold">docs/architecture/API_DESIGN.md</code>.
        </div>
      </div>
    </div>
  );
};
