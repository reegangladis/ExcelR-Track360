import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  Download,
  RefreshCw,
  Search,
  Filter,
  Eye,
  X,
  Copy,
  Check,
  ShieldCheck,
  AlertCircle,
  FileSpreadsheet,
  ChevronLeft,
  ChevronRight,
  User as UserIcon,
  Globe,
  Database,
  ArrowRight,
} from 'lucide-react';
import { api } from '@/lib/api';
import { AuditLogItem, AuditLogListResponse } from '@/types';

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [entityType, setEntityType] = useState<string>('');
  const [actionType, setActionType] = useState<string>('');
  const [search, setSearch] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');

  // Selected Log for Inspector Modal
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res: AuditLogListResponse = await api.getAuditLogs({
        entity_type: entityType || undefined,
        action_type: actionType || undefined,
        search: search.trim() || undefined,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
        page,
        page_size: pageSize,
      });
      setLogs(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err?.message || 'Failed to load audit records.');
    } finally {
      setIsLoading(false);
    }
  }, [entityType, actionType, search, dateFrom, dateTo, page, pageSize]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleExportCsv = async () => {
    setIsExporting(true);
    setSuccessMessage(null);
    setError(null);
    try {
      const filename = `audit_trail_${new Date().toISOString().slice(0, 10)}.csv`;
      await api.exportAuditLogsCsv(
        {
          entity_type: entityType || undefined,
          action_type: actionType || undefined,
          date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
          date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
        },
        filename
      );
      setSuccessMessage('Audit trail export generated and recorded successfully.');
      // Refresh to reflect the new self-recorded AUDIT_LOG_EXPORTED entry
      setTimeout(() => {
        fetchLogs();
      }, 800);
    } catch (err: any) {
      setError(err?.message || 'Failed to export audit logs.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleResetFilters = () => {
    setEntityType('');
    setActionType('');
    setSearch('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
  };

  const handleCopyJson = (data: any, sectionKey: string) => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopiedSection(sectionKey);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const formatUtcDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    } catch {
      return isoStr;
    }
  };

  const getActionBadgeColor = (action: string) => {
    if (action.includes('ISSUED') || action.includes('APPROVED') || action.includes('COMPLETED')) {
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
    if (action.includes('REVOKED') || action.includes('REJECTED') || action.includes('TERMINATED') || action.includes('FAILED')) {
      return 'bg-rose-50 text-rose-700 border-rose-200';
    }
    if (action.includes('EXPORTED')) {
      return 'bg-purple-50 text-purple-700 border-purple-200';
    }
    if (action.includes('DISPATCH') || action.includes('SUBMITTED') || action.includes('REVIEW')) {
      return 'bg-blue-50 text-blue-700 border-blue-200';
    }
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <div className="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-md">
              <History className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                Audit Trail Explorer
              </h1>
              <p className="text-xs text-slate-500">
                Immutable, append-only security ledger governed by RFC 4180 export standards
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchLogs()}
            disabled={isLoading}
            className="inline-flex items-center space-x-2 px-3 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors disabled:opacity-50"
            title="Refresh logs"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleExportCsv}
            disabled={isExporting || total === 0}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium shadow-sm transition-colors disabled:opacity-50"
          >
            {isExporting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Compliance / Security Guarantee Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900 text-white p-4 rounded-xl flex items-center space-x-3 shadow-sm">
          <ShieldCheck className="w-8 h-8 text-emerald-400 flex-shrink-0" />
          <div>
            <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
              Tamper-Evident Ledger
            </div>
            <div className="text-sm font-medium text-slate-200">
              Append-only database triggers with actor IP & User-Agent capture
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-xl flex items-center space-x-3 shadow-sm">
          <FileSpreadsheet className="w-8 h-8 text-indigo-600 flex-shrink-0" />
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Self-Auditing Exports (FR-REP-003)
            </div>
            <div className="text-sm font-medium text-slate-800">
              Every data extract automatically emits an immutable audit event
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-xl flex items-center space-x-3 shadow-sm">
          <Database className="w-8 h-8 text-blue-600 flex-shrink-0" />
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Total Logged Operations
            </div>
            <div className="text-xl font-bold text-slate-900">{total.toLocaleString()} Records</div>
          </div>
        </div>
      </div>

      {/* Feedback Messages */}
      {successMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-sm flex items-center justify-between">
          <span>{successMessage}</span>
          <button
            onClick={() => setSuccessMessage(null)}
            className="text-emerald-600 hover:text-emerald-900"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-sm flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-600 hover:text-rose-900">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm font-semibold text-slate-700">
            <Filter className="w-4 h-4 text-slate-500" />
            <span>Search & Forensic Filters</span>
          </div>
          {(entityType || actionType || search || dateFrom || dateTo) && (
            <button
              onClick={handleResetFilters}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Reset All Filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Entity Domain Filter */}
          <div>
            <label htmlFor="filter-entity-domain" className="block text-xs font-medium text-slate-600 mb-1">Entity Domain</label>
            <select
              id="filter-entity-domain"
              value={entityType}
              onChange={(e) => {
                setEntityType(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Domains</option>
              <option value="CERTIFICATE">CERTIFICATE</option>
              <option value="ASSIGNMENT">ASSIGNMENT</option>
              <option value="PROJECT">PROJECT</option>
              <option value="INTERNSHIP">INTERNSHIP</option>
              <option value="CANDIDATE">CANDIDATE</option>
              <option value="NOTIFICATIONS">NOTIFICATIONS</option>
              <option value="AUDIT_LOGS">AUDIT_LOGS</option>
              <option value="AUTH">AUTH</option>
              <option value="SYSTEM">SYSTEM</option>
            </select>
          </div>

          {/* Action Type Filter */}
          <div>
            <label htmlFor="filter-action-type" className="block text-xs font-medium text-slate-600 mb-1">Action Type</label>
            <select
              id="filter-action-type"
              value={actionType}
              onChange={(e) => {
                setActionType(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Actions</option>
              <option value="CERTIFICATE_GENERATED">CERTIFICATE_GENERATED</option>
              <option value="CERTIFICATE_STAGE1_APPROVED">CERTIFICATE_STAGE1_APPROVED</option>
              <option value="CERTIFICATE_ISSUED">CERTIFICATE_ISSUED</option>
              <option value="CERTIFICATE_REVOKED">CERTIFICATE_REVOKED</option>
              <option value="BATCH_NOTIFICATION_DISPATCH">BATCH_NOTIFICATION_DISPATCH</option>
              <option value="AUDIT_LOG_EXPORTED">AUDIT_LOG_EXPORTED</option>
              <option value="ASSIGNMENT_SUBMITTED">ASSIGNMENT_SUBMITTED</option>
              <option value="PROJECT_ALLOCATED">PROJECT_ALLOCATED</option>
              <option value="INTERNSHIP_INITIALIZED">INTERNSHIP_INITIALIZED</option>
            </select>
          </div>

          {/* Free Text Search */}
          <div>
            <label htmlFor="search-audit-events" className="block text-xs font-medium text-slate-600 mb-1">Free-Text Query</label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                id="search-audit-events"
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setPage(1);
                    fetchLogs();
                  }
                }}
                placeholder="Search actor, action, justification..."
                className="w-full text-xs rounded-lg border border-slate-300 pl-8 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Date From */}
          <div>
            <label htmlFor="filter-date-from" className="block text-xs font-medium text-slate-600 mb-1">Date From (UTC)</label>
            <input
              id="filter-date-from"
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Date To */}
          <div>
            <label htmlFor="filter-date-to" className="block text-xs font-medium text-slate-600 mb-1">Date To (UTC)</label>
            <input
              id="filter-date-to"
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
              className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      </div>

      {/* Audit Log Events Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Timestamp (UTC)</th>
                <th className="py-3.5 px-4">Action Event</th>
                <th className="py-3.5 px-4">Domain & Entity</th>
                <th className="py-3.5 px-4">Actor</th>
                <th className="py-3.5 px-4">Justification & Details</th>
                <th className="py-3.5 px-4 text-center">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
                    <span>Querying immutable audit logs...</span>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <History className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    <p className="text-sm font-medium text-slate-600">No audit events match your filters</p>
                    <p className="text-xs text-slate-400 mt-1">Try resetting the search terms or date ranges</p>
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-600 whitespace-nowrap">
                      {formatUtcDate(log.created_at)}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`inline-block px-2.5 py-1 rounded-md text-[10px] font-semibold tracking-wide border ${getActionBadgeColor(
                          log.action_type
                        )}`}
                      >
                        {log.action_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-semibold text-slate-800">{log.entity_type}</span>
                        {log.entity_id && (
                          <span
                            className="font-mono text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded cursor-help"
                            title={`Entity UUID: ${log.entity_id}`}
                          >
                            {log.entity_id.slice(0, 8)}...
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-col">
                        <div className="flex items-center space-x-1 text-slate-900 font-medium">
                          <UserIcon className="w-3 h-3 text-slate-400" />
                          <span>{log.actor_name || 'System / Automated'}</span>
                        </div>
                        {log.actor_email && (
                          <span className="text-[10px] text-slate-500 font-mono truncate max-w-[150px]">
                            {log.actor_email}
                          </span>
                        )}
                        {log.actor_ip_address && (
                          <span className="text-[9px] text-slate-400 flex items-center space-x-0.5 mt-0.5">
                            <Globe className="w-2.5 h-2.5 text-slate-400" />
                            <span>{log.actor_ip_address}</span>
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 max-w-xs">
                      <p className="text-slate-700 truncate" title={log.justification || 'No justification provided'}>
                        {log.justification || (
                          <span className="text-slate-400 italic">No justification provided</span>
                        )}
                      </p>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <button
                        onClick={() => setSelectedLog(log)}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 text-[11px] font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-md transition-colors"
                        title="Inspect full audit record"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50 gap-3">
          <div className="text-xs text-slate-500">
            Showing <span className="font-semibold">{logs.length > 0 ? (page - 1) * pageSize + 1 : 0}</span> to{' '}
            <span className="font-semibold">{Math.min(page * pageSize, total)}</span> of{' '}
            <span className="font-semibold">{total}</span> total events
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1">
              <span className="text-xs text-slate-500">Rows:</span>
              <select
                aria-label="Rows per page"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="text-xs rounded border border-slate-300 py-1 px-2 bg-white"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </div>

            <div className="flex items-center space-x-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1 rounded border border-slate-300 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                title="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs text-slate-600 px-2">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1 rounded border border-slate-300 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                title="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Forensic JSON Inspector Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <History className="w-5 h-5 text-indigo-400" />
                <h2 className="text-base font-bold">Audit Record Forensic Inspector</h2>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6">
              {/* Meta Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-400 block uppercase tracking-wider text-[10px]">
                    Event ID
                  </span>
                  <span className="font-mono text-slate-800 break-all">{selectedLog.id}</span>
                </div>
                <div>
                  <span className="text-slate-400 block uppercase tracking-wider text-[10px]">
                    Action Type
                  </span>
                  <span
                    className={`inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-semibold border ${getActionBadgeColor(
                      selectedLog.action_type
                    )}`}
                  >
                    {selectedLog.action_type}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block uppercase tracking-wider text-[10px]">
                    Domain & Target ID
                  </span>
                  <span className="text-slate-800 font-semibold">{selectedLog.entity_type}</span>
                  {selectedLog.entity_id && (
                    <span className="font-mono text-[10px] text-slate-500 block truncate">
                      {selectedLog.entity_id}
                    </span>
                  )}
                </div>
                <div>
                  <span className="text-slate-400 block uppercase tracking-wider text-[10px]">
                    Timestamp (UTC)
                  </span>
                  <span className="font-mono text-slate-700">{formatUtcDate(selectedLog.created_at)}</span>
                </div>
              </div>

              {/* Actor & Security Context */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
                <h3 className="font-semibold text-slate-800 flex items-center space-x-1.5">
                  <UserIcon className="w-3.5 h-3.5 text-slate-500" />
                  <span>Actor & Security Context</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-slate-600">
                  <div>
                    <span className="text-slate-400 block text-[10px]">Actor Name / Email:</span>
                    <span className="font-medium text-slate-800">
                      {selectedLog.actor_name || 'System'} ({selectedLog.actor_email || 'N/A'})
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Client IP Address:</span>
                    <span className="font-mono text-slate-800">
                      {selectedLog.actor_ip_address || '127.0.0.1'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">User-Agent:</span>
                    <span className="font-mono text-[10px] text-slate-600 truncate block">
                      {selectedLog.actor_user_agent || 'Internal API Client'}
                    </span>
                  </div>
                </div>
                {selectedLog.justification && (
                  <div className="pt-2 border-t border-slate-200">
                    <span className="text-slate-400 block text-[10px]">Business Justification:</span>
                    <p className="text-slate-800 italic mt-0.5">{selectedLog.justification}</p>
                  </div>
                )}
              </div>

              {/* State Diffs (Pre-State vs Post-State) */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-800 flex items-center space-x-1.5">
                    <span>State Transition Payloads</span>
                    <ArrowRight className="w-4 h-4 text-slate-400" />
                  </h3>
                  <button
                    onClick={() =>
                      handleCopyJson(
                        {
                          pre_state: selectedLog.pre_state,
                          post_state: selectedLog.post_state,
                        },
                        'all_states'
                      )
                    }
                    className="inline-flex items-center space-x-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                  >
                    {copiedSection === 'all_states' ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-emerald-600">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy Complete Payload</span>
                      </>
                    )}
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Pre-State */}
                  <div className="bg-slate-900 rounded-xl p-4 text-slate-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">
                        Pre-State (Prior)
                      </span>
                      {selectedLog.pre_state && (
                        <button
                          onClick={() => handleCopyJson(selectedLog.pre_state, 'pre')}
                          className="text-[10px] text-slate-400 hover:text-white"
                        >
                          {copiedSection === 'pre' ? 'Copied' : 'Copy'}
                        </button>
                      )}
                    </div>
                    <pre className="text-[11px] font-mono overflow-x-auto max-h-60 p-2 bg-slate-950/60 rounded-lg text-slate-300">
                      {selectedLog.pre_state
                        ? JSON.stringify(selectedLog.pre_state, null, 2)
                        : '// No prior state recorded'}
                    </pre>
                  </div>

                  {/* Post-State */}
                  <div className="bg-slate-900 rounded-xl p-4 text-slate-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                        Post-State (Resulting)
                      </span>
                      {selectedLog.post_state && (
                        <button
                          onClick={() => handleCopyJson(selectedLog.post_state, 'post')}
                          className="text-[10px] text-slate-400 hover:text-white"
                        >
                          {copiedSection === 'post' ? 'Copied' : 'Copy'}
                        </button>
                      )}
                    </div>
                    <pre className="text-[11px] font-mono overflow-x-auto max-h-60 p-2 bg-slate-950/60 rounded-lg text-slate-300">
                      {selectedLog.post_state
                        ? JSON.stringify(selectedLog.post_state, null, 2)
                        : '// No post state recorded'}
                    </pre>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-medium transition-colors"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
