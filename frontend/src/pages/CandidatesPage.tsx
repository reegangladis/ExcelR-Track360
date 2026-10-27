import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { CandidateItem, ImportPreviewResult } from '@/types';
import {
  Users,
  UserPlus,
  UploadCloud,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Edit2,
  RefreshCw,
  Loader2,
  FileSpreadsheet,
} from 'lucide-react';

export const CandidatesPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Search & Filter State
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [statusModalCandidate, setStatusModalCandidate] = useState<CandidateItem | null>(null);
  const [newStatus, setNewStatus] = useState('ACTIVE');
  const [statusReason, setStatusReason] = useState('');

  // Add Candidate Form State
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    academic_qualification: '',
    batch_id: '',
  });
  const [formError, setFormError] = useState<string | null>(null);

  // Bulk Import State
  const [importFile, setImportFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<ImportPreviewResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Fetch Candidates Query
  const { data: candidateData, isLoading, isError, refetch } = useQuery({
    queryKey: ['candidates', searchTerm, statusFilter, page],
    queryFn: () =>
      api.getCandidates({
        search: searchTerm || undefined,
        lifecycle_status: statusFilter || undefined,
        page,
        page_size: pageSize,
      }),
  });

  // Fetch Batches Query
  const { data: batches } = useQuery({
    queryKey: ['batches'],
    queryFn: () => api.getBatches(),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: api.createCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      setIsAddModalOpen(false);
      setFormData({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        academic_qualification: '',
        batch_id: '',
      });
      setFormError(null);
    },
    onError: (err: any) => {
      setFormError(err.message || 'Failed to create candidate.');
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, to_status, reason }: { id: string; to_status: string; reason: string }) =>
      api.transitionCandidateStatus(id, to_status, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      setStatusModalCandidate(null);
      setStatusReason('');
    },
  });

  const previewMutation = useMutation({
    mutationFn: (file: File) => api.previewCandidateImport(file),
    onSuccess: (data) => {
      setPreviewData(data);
      setImportError(null);
    },
    onError: (err: any) => {
      setImportError(err.message || 'Failed to process CSV preview.');
    },
  });

  const commitMutation = useMutation({
    mutationFn: (rows: any[]) => api.commitCandidateImport(rows),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      setIsImportModalOpen(false);
      setImportFile(null);
      setPreviewData(null);
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    createMutation.mutate({
      ...formData,
      batch_id: formData.batch_id || undefined,
    });
  };

  const handleStatusSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!statusModalCandidate || !statusReason) return;
    statusMutation.mutate({
      id: statusModalCandidate.id,
      to_status: newStatus,
      reason: statusReason,
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImportFile(file);
      previewMutation.mutate(file);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      ACTIVE: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      ENROLLED: 'bg-blue-50 text-blue-700 border-blue-200',
      ON_HOLD: 'bg-amber-50 text-amber-700 border-amber-200',
      DROPPED: 'bg-red-50 text-red-700 border-red-200',
      COMPLETED: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      ALUMNI: 'bg-purple-50 text-purple-700 border-purple-200',
    };
    return (
      <span
        className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${
          styles[status] || 'bg-slate-50 text-slate-700 border-slate-200'
        }`}
      >
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Users className="w-7 h-7 text-blue-600" />
            Candidate Lifecycle Management
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative golden record of learners, batch allocations, and academic progression.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsImportModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
          >
            <UploadCloud className="w-4 h-4 text-slate-500" />
            Bulk CSV Import
          </button>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 transition-colors shadow-sm"
          >
            <UserPlus className="w-4 h-4" />
            Add Candidate
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, email, phone, ID..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="text-sm border border-slate-200 rounded-lg py-2 px-3 focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
            >
              <option value="">All Lifecycle Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="ENROLLED">Enrolled</option>
              <option value="ON_HOLD">On Hold</option>
              <option value="DROPPED">Dropped</option>
              <option value="COMPLETED">Completed</option>
              <option value="ALUMNI">Alumni</option>
            </select>
          </div>

          <button
            onClick={() => refetch()}
            title="Refresh"
            className="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Candidates Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600 mb-3" />
            <span className="text-sm text-slate-500 font-medium">Loading candidate records...</span>
          </div>
        ) : isError ? (
          <div className="p-12 text-center text-red-600">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
            <p className="font-semibold">Failed to load candidates.</p>
            <p className="text-xs text-slate-500 mt-1">Check network connectivity or permissions.</p>
          </div>
        ) : candidateData?.items.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3 text-slate-400">
              <Users className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-slate-800">No candidate records found</h3>
            <p className="text-sm text-slate-500 mt-1 mb-4">
              {searchTerm || statusFilter
                ? 'Try adjusting your search criteria or clearing filters.'
                : 'Get started by creating your first student or importing a CSV roster.'}
            </p>
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <UserPlus className="w-3.5 h-3.5" />
              Enroll Candidate
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50 font-semibold text-slate-600">
                <tr>
                  <th className="py-3.5 pl-6 pr-3">Candidate ID</th>
                  <th className="px-3 py-3.5">Name</th>
                  <th className="px-3 py-3.5">Contact Details</th>
                  <th className="px-3 py-3.5">Cohort Batch</th>
                  <th className="px-3 py-3.5">Status</th>
                  <th className="px-3 py-3.5">Projects</th>
                  <th className="py-3.5 pl-3 pr-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {candidateData?.items.map((cand) => (
                  <tr key={cand.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-4 pl-6 pr-3 font-mono font-bold text-xs text-blue-700">
                      {cand.candidate_number}
                    </td>
                    <td className="px-3 py-4 font-medium text-slate-900">
                      {cand.first_name} {cand.last_name}
                    </td>
                    <td className="px-3 py-4 text-xs">
                      <div className="text-slate-800">{cand.email}</div>
                      <div className="text-slate-500 font-mono">{cand.phone}</div>
                    </td>
                    <td className="px-3 py-4 text-xs">
                      {cand.batch_code ? (
                        <span className="font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                          {cand.batch_code}
                        </span>
                      ) : (
                        <span className="text-slate-400 italic">Unassigned</span>
                      )}
                    </td>
                    <td className="px-3 py-4">{getStatusBadge(cand.lifecycle_status)}</td>
                    <td className="px-3 py-4 text-xs font-medium">
                      <span className="text-slate-900 font-bold">{cand.completed_projects_count}</span>
                      <span className="text-slate-500"> / 3</span>
                    </td>
                    <td className="py-4 pl-3 pr-6 text-right">
                      <button
                        onClick={() => {
                          setStatusModalCandidate(cand);
                          setNewStatus(cand.lifecycle_status);
                        }}
                        className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-semibold"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                        Status
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {candidateData && candidateData.total > 0 && (
          <div className="p-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing <span className="font-semibold">{(page - 1) * pageSize + 1}</span> to{' '}
              <span className="font-semibold">
                {Math.min(page * pageSize, candidateData.total)}
              </span>{' '}
              of <span className="font-semibold">{candidateData.total}</span> candidates
            </span>

            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="p-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span>
                Page {page} of {candidateData.total_pages}
              </span>
              <button
                disabled={page >= candidateData.total_pages}
                onClick={() => setPage((p) => p + 1)}
                className="p-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Add Candidate Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-blue-600" />
              Enroll Single Candidate
            </h2>

            {formError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="first_name" className="block font-medium text-slate-700 text-xs mb-1">First Name *</label>
                  <input
                    id="first_name"
                    type="text"
                    required
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="last_name" className="block font-medium text-slate-700 text-xs mb-1">Last Name *</label>
                  <input
                    id="last_name"
                    type="text"
                    required
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="email" className="block font-medium text-slate-700 text-xs mb-1">Email Address *</label>
                <input
                  id="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="student@example.com"
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="phone" className="block font-medium text-slate-700 text-xs mb-1">Phone Number *</label>
                  <input
                    id="phone"
                    type="tel"
                    required
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+919876543210"
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="batch_id" className="block font-medium text-slate-700 text-xs mb-1">Cohort Batch</label>
                  <select
                    id="batch_id"
                    value={formData.batch_id}
                    onChange={(e) => setFormData({ ...formData, batch_id: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                  >
                    <option value="">None (Unassigned)</option>
                    {batches?.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.batch_code} - {b.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 text-xs mb-1">Academic Qualification</label>
                <input
                  type="text"
                  value={formData.academic_qualification}
                  onChange={(e) => setFormData({ ...formData, academic_qualification: e.target.value })}
                  placeholder="B.Tech, B.Sc, MCA..."
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Enrolling...' : 'Enroll Candidate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modify Status Modal */}
      {statusModalCandidate && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-1">Modify Candidate Status</h2>
            <p className="text-xs text-slate-500 mb-4">
              Candidate: <span className="font-semibold text-slate-800">{statusModalCandidate.first_name} {statusModalCandidate.last_name}</span> ({statusModalCandidate.candidate_number})
            </p>

            <form onSubmit={handleStatusSubmit} className="space-y-4 text-sm">
              <div>
                <label className="block font-medium text-slate-700 text-xs mb-1">Target Lifecycle Status</label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="ON_HOLD">ON_HOLD</option>
                  <option value="DROPPED">DROPPED</option>
                  <option value="COMPLETED">COMPLETED</option>
                  <option value="ALUMNI">ALUMNI</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 text-xs mb-1">
                  Mandatory Audit Reason *
                </label>
                <textarea
                  required
                  minLength={5}
                  value={statusReason}
                  onChange={(e) => setStatusReason(e.target.value)}
                  placeholder="State operational reason for this transition..."
                  rows={3}
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setStatusModalCandidate(null)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={statusMutation.isPending || !statusReason}
                  className="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {statusMutation.isPending ? 'Saving...' : 'Confirm Transition'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk CSV Import Modal */}
      {isImportModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-3xl w-full p-6 max-h-[90vh] flex flex-col">
            <h2 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-blue-600" />
              Bulk Candidate Ingestion (Preview & Validate)
            </h2>
            <p className="text-xs text-slate-500 mb-4">
              Upload a CSV file with columns: <span className="font-mono">first_name, last_name, email, phone, batch_code, academic_qualification</span>
            </p>

            {importError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg">
                {importError}
              </div>
            )}

            {/* Upload Area */}
            {!previewData && (
              <div className="space-y-4">
                <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:bg-slate-50 transition-colors">
                  <UploadCloud className="w-10 h-10 text-slate-400 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700">Choose CSV roster to upload</p>
                  <p className="text-xs text-slate-500 mt-1 mb-4">Standard UTF-8 CSV</p>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileUpload}
                    className="text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                  />
                </div>
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => setIsImportModalOpen(false)}
                    className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Validation Preview Results */}
            {previewData && (
              <div className="flex-1 overflow-hidden flex flex-col space-y-4">
                <div className="flex items-center gap-4 text-xs font-semibold">
                  {importFile && (
                    <span className="text-slate-600 font-mono text-xs bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
                      {importFile.name}
                    </span>
                  )}
                  <span className="bg-slate-100 text-slate-700 px-3 py-1 rounded-full">
                    Total: {previewData.total_rows}
                  </span>
                  <span className="bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Valid: {previewData.valid_rows_count}
                  </span>
                  <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full flex items-center gap-1">
                    <XCircle className="w-3.5 h-3.5" /> Invalid: {previewData.error_rows_count}
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto border border-slate-200 rounded-lg">
                  <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                    <thead className="bg-slate-50 font-semibold sticky top-0">
                      <tr>
                        <th className="p-2">Row</th>
                        <th className="p-2">Status</th>
                        <th className="p-2">Name</th>
                        <th className="p-2">Email</th>
                        <th className="p-2">Phone</th>
                        <th className="p-2">Validation Diagnostics</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {previewData.rows.map((r) => (
                        <tr key={r.row_number} className={r.is_valid ? 'bg-white' : 'bg-red-50/50'}>
                          <td className="p-2 font-mono font-bold text-slate-600">{r.row_number}</td>
                          <td className="p-2">
                            {r.is_valid ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            ) : (
                              <XCircle className="w-4 h-4 text-red-600" />
                            )}
                          </td>
                          <td className="p-2 font-medium">
                            {r.first_name} {r.last_name}
                          </td>
                          <td className="p-2 font-mono">{r.email}</td>
                          <td className="p-2 font-mono">{r.phone}</td>
                          <td className="p-2 text-red-600 font-medium">
                            {r.error_message || <span className="text-emerald-700">Ready for ingest</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="pt-4 flex justify-between items-center border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => {
                      setPreviewData(null);
                      setImportFile(null);
                    }}
                    className="text-xs text-slate-600 hover:underline"
                  >
                    Select different file
                  </button>

                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setIsImportModalOpen(false)}
                      className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={previewData.valid_rows_count === 0 || commitMutation.isPending}
                      onClick={() => commitMutation.mutate(previewData.rows)}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 disabled:opacity-50"
                    >
                      {commitMutation.isPending
                        ? 'Committing...'
                        : `Commit ${previewData.valid_rows_count} Valid Candidates`}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
