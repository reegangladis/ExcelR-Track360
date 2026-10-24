import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-200 bg-white py-6 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-500 gap-4">
        <div>
          <span className="font-semibold text-slate-700">ExcelR Track360</span> — Track Every Student. Every Assignment. Every Milestone.
        </div>
        <div className="flex items-center space-x-6">
          <span>Phase 3: Project Foundation & Environment Setup</span>
          <span>•</span>
          <a
            href="/api/v1/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-600 hover:text-brand-700 hover:underline"
          >
            API Swagger Docs
          </a>
          <span>•</span>
          <span>FastAPI + PostgreSQL + React 18</span>
        </div>
      </div>
    </footer>
  );
};
