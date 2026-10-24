import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Database, Server, Clock } from 'lucide-react';

export const SystemStatusCard: React.FC = () => {
  const {
    data: health,
    isLoading: healthLoading,
    isError: healthError,
    error: healthErrorObj,
    refetch: refetchHealth,
    isFetching: healthFetching,
  } = useQuery({
    queryKey: ['system-health'],
    queryFn: api.getHealth,
    refetchInterval: 30000,
    retry: 1,
  });

  const {
    data: readiness,
    isLoading: readinessLoading,
    isError: readinessError,
    error: readinessErrorObj,
    refetch: refetchReadiness,
    isFetching: readinessFetching,
  } = useQuery({
    queryKey: ['system-readiness'],
    queryFn: api.getReadiness,
    refetchInterval: 30000,
    retry: 1,
  });

  const isRefreshing = healthFetching || readinessFetching;

  const handleRefresh = () => {
    refetchHealth();
    refetchReadiness();
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center font-bold text-sm">
            <Server className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900">System Foundation Status</h3>
            <p className="text-xs text-slate-500">Live infrastructure probes & connectivity health</p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors disabled:opacity-50"
          title="Re-probe system endpoints"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        {/* API Backend Health Probe */}
        <div className="p-4 rounded-xl border border-slate-100 bg-slate-50/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">FastAPI Backend</span>
            {healthLoading ? (
              <span className="text-xs font-medium text-slate-400 animate-pulse">Checking...</span>
            ) : health?.status === 'healthy' ? (
              <span className="inline-flex items-center space-x-1 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Healthy</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1 text-xs font-semibold text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded-full border border-rose-200">
                <XCircle className="w-3.5 h-3.5 text-rose-600" />
                <span>Offline</span>
              </span>
            )}
          </div>

          <div className="mt-3 space-y-1.5 text-xs text-slate-600">
            <div className="flex justify-between">
              <span className="text-slate-400">Environment:</span>
              <span className="font-mono font-medium text-slate-700">{health?.environment || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">API Version:</span>
              <span className="font-mono font-medium text-slate-700">{health?.version || '0.1.0'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400 flex items-center space-x-1">
                <Clock className="w-3 h-3 text-slate-400" />
                <span>Uptime:</span>
              </span>
              <span className="font-mono text-slate-700">
                {health?.uptime_seconds !== undefined ? `${health.uptime_seconds}s` : '—'}
              </span>
            </div>
            {healthError && (
              <div className="mt-2 text-rose-600 text-[11px] bg-rose-50 p-2 rounded border border-rose-200">
                Connection failed: {(healthErrorObj as Error)?.message || 'Backend unreachable on /api/v1/health'}
              </div>
            )}
          </div>
        </div>

        {/* PostgreSQL Database Probe */}
        <div className="p-4 rounded-xl border border-slate-100 bg-slate-50/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider flex items-center space-x-1">
              <Database className="w-3.5 h-3.5" />
              <span>PostgreSQL Database</span>
            </span>
            {readinessLoading ? (
              <span className="text-xs font-medium text-slate-400 animate-pulse">Checking...</span>
            ) : readiness?.database?.status === 'connected' ? (
              <span className="inline-flex items-center space-x-1 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Connected</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1 text-xs font-semibold text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                <span>Unavailable</span>
              </span>
            )}
          </div>

          <div className="mt-3 space-y-1.5 text-xs text-slate-600">
            <div className="flex justify-between">
              <span className="text-slate-400">Database Target:</span>
              <span className="font-mono font-medium text-slate-700 truncate max-w-[180px]">
                {readiness?.database?.target || 'localhost:5432/track360_dev'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Roundtrip Latency:</span>
              <span className="font-mono font-medium text-slate-700">
                {readiness?.database?.latency_ms !== undefined ? `${readiness.database.latency_ms} ms` : '—'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Readiness Probe:</span>
              <span className={`font-semibold ${readiness?.status === 'ready' ? 'text-emerald-600' : 'text-amber-600'}`}>
                {readiness?.status === 'ready' ? 'Ready for Traffic' : 'Not Ready (HTTP 503)'}
              </span>
            </div>

            {readiness?.database?.status === 'unavailable' && (
              <div className="mt-2 text-amber-800 text-[11px] bg-amber-50 p-2.5 rounded-lg border border-amber-200">
                <span className="font-semibold block mb-0.5">Database Disconnected:</span>
                <span>{readiness.database.error || 'Connection refused to PostgreSQL.'}</span>
                <span className="block mt-1 text-slate-600">
                  Tip: Start Docker Compose with <code className="bg-amber-100 px-1 py-0.5 rounded font-mono">docker compose up -d</code> or verify local PostgreSQL on port 5432.
                </span>
              </div>
            )}
            {readinessError && !readiness && (
              <div className="mt-2 text-rose-600 text-[11px] bg-rose-50 p-2 rounded border border-rose-200">
                {(readinessErrorObj as Error)?.message || 'Readiness probe unreachable'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
