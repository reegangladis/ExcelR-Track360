import React from 'react';
import { Link } from 'react-router-dom';
import { SystemStatusCard } from '@/components/SystemStatusCard';
import { 
  Users, 
  FileText, 
  FolderGit2, 
  Briefcase, 
  Award, 
  ShieldCheck, 
  ArrowRight,
  Sparkles,
  Terminal
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const modules = [
    {
      title: 'Candidate Lifecycle',
      phase: 'Phase 6',
      icon: Users,
      description: 'Single golden profile, de-duplication, batch CSV ingestion, and lifecycle status tracking.',
      status: 'Architected',
      path: '/candidates',
    },
    {
      title: 'Assignments & Evaluation',
      phase: 'Phases 7–9',
      icon: FileText,
      description: 'Multi-stage submission ingestion, server UTC timestamps, rubric grading, and resubmissions.',
      status: 'Architected',
      path: '/assignments',
    },
    {
      title: 'Projects & Group Readiness',
      phase: 'Phases 10–13',
      icon: FolderGit2,
      description: 'Configurable group builder, deliverable evaluations, group readiness engine, and 3-project cap.',
      status: 'Architected',
      path: '/projects',
    },
    {
      title: 'Internship Milestones',
      phase: 'Phase 14',
      icon: Briefcase,
      description: 'Decoupled calendar date tracking and duration multiplier policy (1=3mo, 2=6mo, 3=9mo).',
      status: 'Architected',
      path: '/internships',
    },
    {
      title: 'Verified Certificates',
      phase: 'Phase 15',
      icon: Award,
      description: 'Two-tier approval gate, unique serials, QR code embedding, and public verification portal.',
      status: 'Architected',
      path: '/certificates',
    },
    {
      title: 'Audit Logs & Governance',
      phase: 'Phase 17',
      icon: ShieldCheck,
      description: 'Immutable append-only audit trail, role-based export controls, and exception tracking.',
      status: 'Architected',
      path: '/audit',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-brand-950 to-slate-900 text-white p-8 sm:p-10 shadow-xl border border-slate-800">
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-semibold bg-brand-500/20 text-brand-300 border border-brand-500/30 backdrop-blur-sm">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Platform Foundation Active — Phase 3</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
            ExcelR <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-blue-200">Track360</span>
          </h1>

          <p className="text-base sm:text-lg text-slate-300 font-normal leading-relaxed">
            <span className="font-semibold text-white">Track Every Student. Every Assignment. Every Milestone.</span><br />
            Enterprise-grade student lifecycle & operations management platform engineered with zero unverified assumptions.
          </p>

          <div className="flex flex-wrap gap-2.5 pt-2 text-xs">
            {['FastAPI 0.141', 'SQLAlchemy 2.0', 'PostgreSQL 16', 'React 18', 'TypeScript', 'Tailwind CSS', 'Docker'].map((tech) => (
              <span key={tech} className="px-2.5 py-1 rounded-md bg-white/10 text-slate-200 font-mono font-medium border border-white/10">
                {tech}
              </span>
            ))}
          </div>
        </div>

        {/* Ambient background glow */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 rounded-full bg-brand-500/10 blur-3xl pointer-events-none"></div>
      </div>

      {/* Live Infrastructure Probes */}
      <section aria-labelledby="system-status-heading">
        <h2 id="system-status-heading" className="sr-only">System Foundation Status</h2>
        <SystemStatusCard />
      </section>

      {/* Domain Modules Roadmap Grid */}
      <section className="space-y-4">
        <div className="flex justify-between items-end">
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Core Domain Modules</h2>
            <p className="text-xs text-slate-500">
              Implementation roadmap following the approved 18-phase architecture specification
            </p>
          </div>
          <span className="text-xs font-medium text-slate-500 hidden sm:block">
            6 Core Domains • 37 Tables Planned
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {modules.map((mod) => {
            const Icon = mod.icon;
            return (
              <div
                key={mod.title}
                className="group bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm hover:shadow-md hover:border-brand-300 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-50 text-slate-700 flex items-center justify-center group-hover:bg-brand-50 group-hover:text-brand-600 transition-colors">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-semibold text-brand-700 bg-brand-50 px-2 py-0.5 rounded-full border border-brand-200/60 font-mono">
                      {mod.phase}
                    </span>
                  </div>

                  <h3 className="text-base font-semibold text-slate-900 group-hover:text-brand-600 transition-colors">
                    {mod.title}
                  </h3>

                  <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                    {mod.description}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-medium">Status: {mod.status}</span>
                  <Link
                    to={mod.path}
                    className="inline-flex items-center space-x-1 text-brand-600 font-semibold group-hover:translate-x-0.5 transition-transform"
                  >
                    <span>View Roadmap</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Developer Quick Reference */}
      <section className="bg-slate-900 rounded-2xl p-6 text-slate-300 text-xs border border-slate-800 space-y-3 font-mono">
        <div className="flex items-center space-x-2 text-white font-semibold">
          <Terminal className="w-4 h-4 text-brand-400" />
          <span>Developer Command Reference</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
          <div className="bg-black/40 p-3 rounded-lg border border-slate-800">
            <span className="text-slate-500 block text-[10px]">BACKEND STARTUP</span>
            <code className="text-brand-300">cd backend && uvicorn app.main:app --reload</code>
          </div>
          <div className="bg-black/40 p-3 rounded-lg border border-slate-800">
            <span className="text-slate-500 block text-[10px]">FRONTEND STARTUP</span>
            <code className="text-emerald-300">cd frontend && npm run dev</code>
          </div>
          <div className="bg-black/40 p-3 rounded-lg border border-slate-800">
            <span className="text-slate-500 block text-[10px]">TEST SUITE</span>
            <code className="text-purple-300">pytest backend/tests & npm test</code>
          </div>
        </div>
      </section>
    </div>
  );
};
