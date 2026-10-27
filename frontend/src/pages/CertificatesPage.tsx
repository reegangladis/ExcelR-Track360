import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  CertificateItem,
  TrackItem,
  CertificateIssueRequest,
  CertificateReviewRequest,
  CertificateApprovalRequest,
  CertificateRevokeRequest,
  CertificateEligibilityDiagnostic,
} from '@/types';
import {
  Award,
  Plus,
  Search,
  Filter,
  Layers,
  CheckCircle2,
  Clock,
  AlertTriangle,
  X,
  RefreshCw,
  Download,
  FileCheck,
  ShieldCheck,
  ShieldAlert,
  ExternalLink,
  Copy,
  Check,
  UserCheck,
  FileText,
} from 'lucide-react';

export const CertificatesPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Filters State
  const [selectedTrack, setSelectedTrack] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 15;

  // Modals & Drawer State
  const [isInitModalOpen, setIsInitModalOpen] = useState(false);
  const [selectedDetailId, setSelectedDetailId] = useState<string | null>(null);
  const [reviewingCert, setReviewingCert] = useState<CertificateItem | null>(null);
  const [approvingCert, setApprovingCert] = useState<CertificateItem | null>(null);
  const [revokingCert, setRevokingCert] = useState<CertificateItem | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Queries
  const { data: tracks } = useQuery<TrackItem[]>({
    queryKey: ['tracks'],
    queryFn: () => api.getTracks(),
  });

  const { data: candidatesData } = useQuery({
    queryKey: ['candidates-for-certs'],
    queryFn: () => api.getCandidates({ page: 1, page_size: 100 }),
  });

  const { data: certificatesData, isLoading } = useQuery({
    queryKey: ['certificates', selectedTrack, selectedStatus, searchTerm, page],
    queryFn: () =>
      api.getCertificates({
        track_id: selectedTrack || undefined,
        status: selectedStatus || undefined,
        search: searchTerm || undefined,
        page,
        page_size: pageSize,
      }),
  });

  const certificates = certificatesData?.items || [];
  const total = certificatesData?.total || 0;
  const totalPages = Math.ceil(total / pageSize) || 1;

  // Metrics
  const issuedCount = certificates.filter((c) => c.status === 'ISSUED').length;
  const pendingReviewCount = certificates.filter((c) => c.status === 'PENDING_APPROVAL').length;
  const pendingApproveCount = certificates.filter((c) => c.status === 'REVIEWED').length;
  const revokedCount = certificates.filter((c) => c.status === 'REVOKED').length;

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2500);
  };

  const handleDownloadPdf = async (cert: CertificateItem) => {
    try {
      await api.downloadCertificatePdf(cert.id, `${cert.serial_number}.pdf`);
    } catch (err: any) {
      alert(`Download failed: ${err.message || 'Unknown error'}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 rounded-2xl text-white shadow-xl border border-indigo-800/30">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-500/20 text-amber-400 rounded-xl border border-amber-500/30">
              <Award className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">Certificate Management & Verification Engine</h1>
              <p className="text-sm text-slate-300 mt-0.5">
                Two-tier academic approval gate, cryptographic HMAC-SHA256 signatures, dynamic QR codes, and tamper-evident PDF credentialing.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="/verify"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-indigo-400/30 text-indigo-200 hover:bg-indigo-900/50 hover:text-white transition-all text-sm font-semibold"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Public Verification Portal
            <ExternalLink className="w-3.5 h-3.5 opacity-70" />
          </a>
          <button
            onClick={() => setIsInitModalOpen(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-semibold rounded-xl shadow-lg shadow-indigo-500/25 transition-all text-sm"
          >
            <Plus className="w-4 h-4" />
            Request Certificate
          </button>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Total Issued</p>
            <h3 className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{issuedCount}</h3>
            <span className="text-xs text-slate-400">Authentic credentials</span>
          </div>
          <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 rounded-xl">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Stage 1 Review</p>
            <h3 className="text-2xl font-bold text-amber-500 mt-1">{pendingReviewCount}</h3>
            <span className="text-xs text-slate-400">Coordinator queue</span>
          </div>
          <div className="p-3 bg-amber-50 dark:bg-amber-950/40 text-amber-500 rounded-xl">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Stage 2 Sign-off</p>
            <h3 className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">{pendingApproveCount}</h3>
            <span className="text-xs text-slate-400">Director approval</span>
          </div>
          <div className="p-3 bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 rounded-xl">
            <UserCheck className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Revoked</p>
            <h3 className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">{revokedCount}</h3>
            <span className="text-xs text-slate-400">Invalidated credentials</span>
          </div>
          <div className="p-3 bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 rounded-xl">
            <ShieldAlert className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search candidate, serial, track..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 placeholder-slate-400"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
            {[
              { label: 'All', value: '' },
              { label: 'Pending Review', value: 'PENDING_APPROVAL' },
              { label: 'Pending Sign-off', value: 'REVIEWED' },
              { label: 'Issued', value: 'ISSUED' },
              { label: 'Revoked', value: 'REVOKED' },
            ].map((tab) => (
              <button
                key={tab.value}
                onClick={() => {
                  setSelectedStatus(tab.value);
                  setPage(1);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  selectedStatus === tab.value
                    ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Track Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={selectedTrack}
              onChange={(e) => {
                setSelectedTrack(e.target.value);
                setPage(1);
              }}
              className="py-2 pl-3 pr-8 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 rounded-xl text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Specializations</option>
              {tracks?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Certificates Table */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 flex flex-col items-center justify-center text-slate-500">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
            <p className="text-sm font-medium">Loading certificate credentials...</p>
          </div>
        ) : certificates.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Award className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto mb-3" />
            <h4 className="text-base font-semibold text-slate-800 dark:text-slate-200">No Certificates Found</h4>
            <p className="text-sm text-slate-400 mt-1">
              No certificate issuance records match your current filter criteria.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/75 dark:bg-slate-800/40 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  <th className="py-3.5 px-4">Serial Number</th>
                  <th className="py-3.5 px-4">Candidate</th>
                  <th className="py-3.5 px-4">Specialization Track</th>
                  <th className="py-3.5 px-4">Accredited Duration</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Issue Date</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-medium">
                {certificates.map((cert) => (
                  <tr
                    key={cert.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    {/* Serial ID */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/40 px-2 py-1 rounded-md border border-indigo-200/50 dark:border-indigo-800/40">
                          {cert.serial_number}
                        </span>
                        <button
                          onClick={() => handleCopy(cert.serial_number, cert.id)}
                          title="Copy serial number"
                          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                        >
                          {copiedHash === cert.id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </td>

                    {/* Candidate */}
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        {cert.candidate_display_name}
                      </div>
                    </td>

                    {/* Track */}
                    <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                      <div className="flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="truncate max-w-xs">{cert.course_display_title}</span>
                      </div>
                    </td>

                    {/* Duration */}
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-full border border-slate-200/60 dark:border-slate-700/60">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {cert.accredited_duration_months} Months
                      </span>
                    </td>

                    {/* Status Badge */}
                    <td className="py-3.5 px-4">
                      {cert.status === 'PENDING_APPROVAL' && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800/40">
                          <Clock className="w-3 h-3" />
                          Pending Review
                        </span>
                      )}
                      {cert.status === 'REVIEWED' && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-800/40">
                          <UserCheck className="w-3 h-3" />
                          Pending Sign-off
                        </span>
                      )}
                      {cert.status === 'ISSUED' && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800/40">
                          <ShieldCheck className="w-3 h-3" />
                          Issued & Valid
                        </span>
                      )}
                      {cert.status === 'REJECTED' && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800/40">
                          <AlertTriangle className="w-3 h-3" />
                          Rejected
                        </span>
                      )}
                      {cert.status === 'REVOKED' && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-800/40">
                          <ShieldAlert className="w-3 h-3" />
                          Revoked
                        </span>
                      )}
                    </td>

                    {/* Issue Date */}
                    <td className="py-3.5 px-4 text-slate-500 text-xs">
                      {cert.issue_date}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {cert.status === 'PENDING_APPROVAL' && (
                          <button
                            onClick={() => setReviewingCert(cert)}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-amber-600 hover:text-amber-700 dark:text-amber-400 bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 px-2.5 py-1.5 rounded-lg border border-amber-200 dark:border-amber-800/50 transition-colors"
                          >
                            Stage 1 Review
                          </button>
                        )}

                        {cert.status === 'REVIEWED' && (
                          <button
                            onClick={() => setApprovingCert(cert)}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400 bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/40 px-2.5 py-1.5 rounded-lg border border-blue-200 dark:border-blue-800/50 transition-colors"
                          >
                            Stage 2 Sign-off
                          </button>
                        )}

                        {cert.status === 'ISSUED' && (
                          <>
                            <button
                              onClick={() => handleDownloadPdf(cert)}
                              title="Download PDF"
                              className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 px-2.5 py-1.5 rounded-lg border border-emerald-200 dark:border-emerald-800/50 transition-colors"
                            >
                              <Download className="w-3.5 h-3.5" />
                              PDF
                            </button>
                            <button
                              onClick={() => setRevokingCert(cert)}
                              title="Revoke Certificate"
                              className="inline-flex items-center gap-1 text-xs font-semibold text-rose-600 hover:text-rose-700 dark:text-rose-400 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 px-2.5 py-1.5 rounded-lg border border-rose-200 dark:border-rose-800/50 transition-colors"
                            >
                              Revoke
                            </button>
                          </>
                        )}

                        <button
                          onClick={() => setSelectedDetailId(cert.id)}
                          title="Inspect Details & Audit Trail"
                          className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        >
                          <FileText className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {total > 0 && (
          <div className="flex items-center justify-between px-4 py-3 bg-slate-50/75 dark:bg-slate-800/40 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-500">
            <span>
              Showing {certificates.length} of {total} certificate credentials
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold"
              >
                Previous
              </button>
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modals & Drawers */}
      {isInitModalOpen && (
        <InitiateCertificateModal
          candidates={candidatesData?.items || []}
          tracks={tracks || []}
          onClose={() => setIsInitModalOpen(false)}
          onSuccess={() => {
            setIsInitModalOpen(false);
            queryClient.invalidateQueries({ queryKey: ['certificates'] });
          }}
        />
      )}

      {reviewingCert && (
        <Stage1ReviewModal
          cert={reviewingCert}
          onClose={() => setReviewingCert(null)}
          onSuccess={() => {
            setReviewingCert(null);
            queryClient.invalidateQueries({ queryKey: ['certificates'] });
          }}
        />
      )}

      {approvingCert && (
        <Stage2ApproveModal
          cert={approvingCert}
          onClose={() => setApprovingCert(null)}
          onSuccess={() => {
            setApprovingCert(null);
            queryClient.invalidateQueries({ queryKey: ['certificates'] });
          }}
        />
      )}

      {revokingCert && (
        <RevokeCertificateModal
          cert={revokingCert}
          onClose={() => setRevokingCert(null)}
          onSuccess={() => {
            setRevokingCert(null);
            queryClient.invalidateQueries({ queryKey: ['certificates'] });
          }}
        />
      )}

      {selectedDetailId && (
        <CertificateDetailDrawer
          certificateId={selectedDetailId}
          onClose={() => setSelectedDetailId(null)}
          onDownloadPdf={handleDownloadPdf}
        />
      )}
    </div>
  );
};

// ============================================================================
// 1. INITIATE CERTIFICATE REQUEST MODAL (With Diagnostic Pre-check)
// ============================================================================
interface InitiateModalProps {
  candidates: any[];
  tracks: TrackItem[];
  onClose: () => void;
  onSuccess: () => void;
}

const InitiateCertificateModal: React.FC<InitiateModalProps> = ({
  candidates,
  tracks,
  onClose,
  onSuccess,
}) => {
  const [candidateId, setCandidateId] = useState('');
  const [trackId, setTrackId] = useState('');
  const [issueDate, setIssueDate] = useState(new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Diagnostic Query
  const { data: diag, isLoading: isDiagLoading } = useQuery<CertificateEligibilityDiagnostic>({
    queryKey: ['certificate-diag', candidateId, trackId],
    queryFn: () => api.getCertificateEligibility(candidateId, trackId || undefined),
    enabled: !!candidateId,
  });

  const mutation = useMutation({
    mutationFn: (data: CertificateIssueRequest) => api.initiateCertificate(data),
    onSuccess: () => {
      onSuccess();
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Failed to submit certificate request');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    if (!candidateId || !trackId) {
      setErrorMsg('Please select both a candidate and an academic course track.');
      return;
    }
    mutation.mutate({
      candidate_id: candidateId,
      track_id: trackId,
      issue_date: issueDate,
      notes,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-xl w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 rounded-lg border border-indigo-100 dark:border-indigo-900/50">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Request Certificate Issuance
              </h3>
              <p className="text-xs text-slate-500">
                Initiates Stage 0 draft with prerequisite diagnostic gating.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto">
          {errorMsg && (
            <div className="p-3.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/50 rounded-xl text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Candidate Selection */}
          <div>
            <label htmlFor="select-cert-candidate" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Select Candidate *
            </label>
            <select
              id="select-cert-candidate"
              value={candidateId}
              onChange={(e) => setCandidateId(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">-- Choose Candidate --</option>
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.first_name} {c.last_name} ({c.email})
                </option>
              ))}
            </select>
          </div>

          {/* Track Selection */}
          <div>
            <label htmlFor="select-cert-track" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Specialization Course Track *
            </label>
            <select
              id="select-cert-track"
              value={trackId}
              onChange={(e) => setTrackId(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">-- Choose Specialization Track --</option>
              {tracks.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title} ({t.code})
                </option>
              ))}
            </select>
          </div>

          {/* Real-time Diagnostic Preview */}
          {candidateId && (
            <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200/80 dark:border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-indigo-500" />
                  Prerequisite Diagnostic Evaluation
                </span>
                {isDiagLoading ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-slate-400" />
                ) : diag?.is_eligible ? (
                  <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-full border border-emerald-200">
                    Eligible for Credential
                  </span>
                ) : (
                  <span className="text-[11px] font-semibold text-rose-600 bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded-full border border-rose-200">
                    Prerequisites Incomplete
                  </span>
                )}
              </div>

              {diag && (
                <div className="text-xs text-slate-600 dark:text-slate-400 space-y-1.5 pt-1">
                  <div className="flex items-center justify-between">
                    <span>Mandatory Assignments Passed:</span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {diag.passed_mandatory_assignments} / {diag.total_mandatory_assignments}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Accredited Program Duration:</span>
                    <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                      {diag.accredited_duration_months} Months
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Internship Record Status:</span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {diag.internship_status || 'No Formal Record'}
                    </span>
                  </div>

                  {!diag.is_eligible && diag.ineligibility_reasons.length > 0 && (
                    <div className="p-2.5 bg-rose-50/60 dark:bg-rose-950/30 rounded-lg border border-rose-200/60 text-[11px] text-rose-700 dark:text-rose-300 space-y-1 mt-2">
                      <p className="font-semibold">Ineligibility Diagnostic Reasons:</p>
                      <ul className="list-disc pl-4 space-y-0.5">
                        {diag.ineligibility_reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Issue Date */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Date of Issuance
            </label>
            <input
              type="date"
              value={issueDate}
              onChange={(e) => setIssueDate(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Coordinator Request Notes
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Completed all coursework, deliverables, and enterprise internship."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Footer Submit */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 dark:text-slate-400"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending || (diag && !diag.is_eligible)}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-600/20 transition-all flex items-center gap-2"
            >
              {mutation.isPending && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
              Submit Request
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ============================================================================
// 2. STAGE 1 REVIEW MODAL (Coordinator)
// ============================================================================
interface Stage1ModalProps {
  cert: CertificateItem;
  onClose: () => void;
  onSuccess: () => void;
}

const Stage1ReviewModal: React.FC<Stage1ModalProps> = ({ cert, onClose, onSuccess }) => {
  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [decisionNotes, setDecisionNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: CertificateReviewRequest) =>
      api.reviewCertificateStage1(cert.id, data),
    onSuccess: () => {
      onSuccess();
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Stage 1 Review failed');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      decision,
      decision_notes: decisionNotes,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-amber-50/50 dark:bg-amber-950/20">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 rounded-lg">
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Stage 1: Coordinator Credential Review
              </h3>
              <p className="text-xs text-slate-500">
                Validate academic milestones before advancing to Stage 2 sign-off.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 bg-rose-50 text-rose-700 text-xs rounded-xl flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
            <p><strong>Candidate:</strong> {cert.candidate_display_name}</p>
            <p><strong>Track:</strong> {cert.course_display_title}</p>
            <p><strong>Serial:</strong> <span className="font-mono text-indigo-600">{cert.serial_number}</span></p>
            <p><strong>Accredited Duration:</strong> {cert.accredited_duration_months} Months</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Review Decision *
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setDecision('APPROVED')}
                className={`py-2 px-3 rounded-xl border text-xs font-bold transition-all ${
                  decision === 'APPROVED'
                    ? 'bg-emerald-50 border-emerald-500 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                    : 'border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-slate-50'
                }`}
              >
                Pass to Stage 2 Sign-off
              </button>
              <button
                type="button"
                onClick={() => setDecision('REJECTED')}
                className={`py-2 px-3 rounded-xl border text-xs font-bold transition-all ${
                  decision === 'REJECTED'
                    ? 'bg-rose-50 border-rose-500 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300'
                    : 'border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-slate-50'
                }`}
              >
                Reject Request
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Review Notes
            </label>
            <textarea
              rows={3}
              value={decisionNotes}
              onChange={(e) => setDecisionNotes(e.target.value)}
              placeholder="Document prerequisite verification details..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
            <button type="button" onClick={onClose} className="px-4 py-2 text-xs font-semibold text-slate-600">
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-md shadow-amber-600/20"
            >
              {mutation.isPending && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
              Submit Stage 1 Decision
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ============================================================================
// 3. STAGE 2 APPROVE MODAL (Director / SoD Enforcement)
// ============================================================================
interface Stage2ModalProps {
  cert: CertificateItem;
  onClose: () => void;
  onSuccess: () => void;
}

const Stage2ApproveModal: React.FC<Stage2ModalProps> = ({ cert, onClose, onSuccess }) => {
  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [decisionNotes, setDecisionNotes] = useState('');
  const [allowOverride, setAllowOverride] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: CertificateApprovalRequest) =>
      api.approveCertificateStage2(cert.id, data, allowOverride),
    onSuccess: () => {
      onSuccess();
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Stage 2 Approval failed');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      decision,
      decision_notes: decisionNotes,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-blue-50/50 dark:bg-blue-950/20">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded-lg">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Stage 2: Director Sign-off & Generation
              </h3>
              <p className="text-xs text-slate-500">
                Electronic sign-off triggers automated PDF & dynamic QR generation.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 bg-rose-50 text-rose-700 text-xs rounded-xl flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* SoD Protection Notice */}
          <div className="p-3 bg-blue-50/70 dark:bg-blue-950/30 rounded-xl border border-blue-200/60 dark:border-blue-900/40 text-xs text-blue-900 dark:text-blue-200 space-y-1">
            <p className="font-bold flex items-center gap-1.5">
              <UserCheck className="w-4 h-4 text-blue-600" />
              Separation of Duties (SoD) Protocol:
            </p>
            <p className="text-[11px] text-blue-800/80 dark:text-blue-300">
              Per BR-CERT-02, the Stage 1 Coordinator who requested this certificate cannot sign off as Stage 2 Approver.
            </p>
          </div>

          <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl space-y-1 text-xs text-slate-600 dark:text-slate-400">
            <p><strong>Candidate:</strong> {cert.candidate_display_name}</p>
            <p><strong>Track:</strong> {cert.course_display_title}</p>
            <p><strong>Serial:</strong> <span className="font-mono text-indigo-600">{cert.serial_number}</span></p>
            <p><strong>Accredited Duration:</strong> {cert.accredited_duration_months} Months</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Final Approval Decision *
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setDecision('APPROVED')}
                className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all ${
                  decision === 'APPROVED'
                    ? 'bg-emerald-50 border-emerald-500 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 shadow-sm'
                    : 'border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-slate-50'
                }`}
              >
                Formally Sign & Issue
              </button>
              <button
                type="button"
                onClick={() => setDecision('REJECTED')}
                className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all ${
                  decision === 'REJECTED'
                    ? 'bg-rose-50 border-rose-500 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 shadow-sm'
                    : 'border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-slate-50'
                }`}
              >
                Reject Issuance
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Sign-off Endorsement Notes
            </label>
            <textarea
              rows={2}
              value={decisionNotes}
              onChange={(e) => setDecisionNotes(e.target.value)}
              placeholder="Sign-off justification notes for the academic register..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="cb-sod-override"
              checked={allowOverride}
              onChange={(e) => setAllowOverride(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
            />
            <label htmlFor="cb-sod-override" className="text-xs text-slate-600 dark:text-slate-400 select-none">
              Super Administrator SoD Override (Audit Recorded)
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
            <button type="button" onClick={onClose} className="px-4 py-2 text-xs font-semibold text-slate-600">
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-md shadow-blue-600/20"
            >
              {mutation.isPending && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
              Execute Stage 2 Sign-off
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ============================================================================
// 4. REVOCATION MODAL
// ============================================================================
interface RevokeModalProps {
  cert: CertificateItem;
  onClose: () => void;
  onSuccess: () => void;
}

const RevokeCertificateModal: React.FC<RevokeModalProps> = ({ cert, onClose, onSuccess }) => {
  const [reasonCategory, setReasonCategory] = useState<
    'ACADEMIC_MALPRACTICE' | 'DATA_ENTRY_ERROR' | 'DISCIPLINARY_ACTION' | 'ADMINISTRATIVE_OVERRIDE'
  >('ACADEMIC_MALPRACTICE');
  const [detailedReason, setDetailedReason] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: CertificateRevokeRequest) =>
      api.revokeCertificate(cert.id, data),
    onSuccess: () => {
      onSuccess();
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Revocation failed');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (detailedReason.trim().length < 10) {
      setErrorMsg('Detailed explanation must be at least 10 characters long.');
      return;
    }
    mutation.mutate({
      reason_category: reasonCategory,
      detailed_reason: detailedReason,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-rose-50/50 dark:bg-rose-950/20">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-rose-100 dark:bg-rose-900/40 text-rose-600 dark:text-rose-400 rounded-lg">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Revoke Certificate Credential
              </h3>
              <p className="text-xs text-slate-500">
                Immediately updates public verification registry status to REVOKED.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 bg-rose-50 text-rose-700 text-xs rounded-xl flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="p-3.5 bg-rose-50/50 dark:bg-rose-950/30 rounded-xl border border-rose-200/50 text-xs text-rose-900 dark:text-rose-200">
            <strong>Warning:</strong> You are about to invalidate certificate{' '}
            <span className="font-mono font-bold text-rose-700 dark:text-rose-300">{cert.serial_number}</span>{' '}
            for <strong>{cert.candidate_display_name}</strong>. This action is permanently logged to the immutable audit trail.
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Revocation Category *
            </label>
            <select
              value={reasonCategory}
              onChange={(e) => setReasonCategory(e.target.value as any)}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-rose-500"
            >
              <option value="ACADEMIC_MALPRACTICE">Academic Malpractice / Plagiarism</option>
              <option value="DATA_ENTRY_ERROR">Data Entry / Administrative Error</option>
              <option value="DISCIPLINARY_ACTION">Disciplinary Action</option>
              <option value="ADMINISTRATIVE_OVERRIDE">Administrative Board Override</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Detailed Revocation Rationale (Minimum 10 chars) *
            </label>
            <textarea
              rows={3}
              required
              value={detailedReason}
              onChange={(e) => setDetailedReason(e.target.value)}
              placeholder="State comprehensive justification for credential revocation..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-rose-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
            <button type="button" onClick={onClose} className="px-4 py-2 text-xs font-semibold text-slate-600">
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-md shadow-rose-600/20"
            >
              {mutation.isPending && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
              Confirm Revocation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ============================================================================
// 5. CERTIFICATE DETAIL & AUDIT DRAWER
// ============================================================================
interface DrawerProps {
  certificateId: string;
  onClose: () => void;
  onDownloadPdf: (cert: CertificateItem) => void;
}

const CertificateDetailDrawer: React.FC<DrawerProps> = ({
  certificateId,
  onClose,
  onDownloadPdf,
}) => {
  const { data: cert, isLoading } = useQuery<CertificateItem>({
    queryKey: ['certificate-detail', certificateId],
    queryFn: () => api.getCertificate(certificateId),
  });

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/60 backdrop-blur-sm flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-xl bg-white dark:bg-slate-900 h-full shadow-2xl border-l border-slate-200 dark:border-slate-800 flex flex-col">
        {/* Drawer Header */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/30">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-500/20 text-amber-500 rounded-xl border border-amber-500/30">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Certificate Credential Detail
              </h3>
              <p className="text-xs text-slate-500">
                Cryptographic signatures, two-stage approval logs, and verification QR.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Body */}
        {isLoading || !cert ? (
          <div className="p-12 flex flex-col items-center justify-center text-slate-500">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
            <p className="text-sm">Loading credential audit record...</p>
          </div>
        ) : (
          <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
            {/* Credential Snapshot Card */}
            <div className="p-5 bg-gradient-to-br from-slate-900 to-indigo-950 text-white rounded-2xl border border-indigo-500/30 shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-amber-400 tracking-wider">
                  {cert.serial_number}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-white/10 text-white border border-white/20">
                  {cert.status}
                </span>
              </div>
              <div>
                <p className="text-xs text-indigo-200">Awarded to</p>
                <h4 className="text-xl font-bold text-white">{cert.candidate_display_name}</h4>
              </div>
              <div>
                <p className="text-xs text-indigo-200">Specialization</p>
                <p className="text-sm font-semibold text-slate-100">{cert.course_display_title}</p>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-white/10 text-xs text-indigo-200">
                <span>Accredited Duration: {cert.accredited_duration_months} Months</span>
                <span>Issue Date: {cert.issue_date}</span>
              </div>
            </div>

            {/* Cryptographic Signature & Public Verification */}
            <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-800 space-y-3">
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-500" />
                Cryptographic Integrity Verification
              </h5>
              <div>
                <span className="text-xs text-slate-500 block mb-1">HMAC-SHA256 Verification Signature:</span>
                <div className="font-mono text-[11px] p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 break-all select-all">
                  {cert.verification_hash}
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-slate-500">Public Verification URL:</span>
                <a
                  href={`/verify/${cert.serial_number}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
                >
                  /verify/{cert.serial_number}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>

            {/* Two-Stage Approval Trail */}
            <div className="space-y-3">
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Two-Stage Approval Timeline
              </h5>
              <div className="space-y-3">
                {/* Stage 0 */}
                <div className="p-3 bg-slate-50 dark:bg-slate-800/30 rounded-xl border border-slate-200/60 dark:border-slate-800 text-xs space-y-1">
                  <div className="flex items-center justify-between font-semibold text-slate-800 dark:text-slate-200">
                    <span>Stage 0: Initiated</span>
                    <span className="text-[11px] text-slate-400">{cert.requested_at}</span>
                  </div>
                  <p className="text-slate-500">Request submitted into approval queue.</p>
                </div>

                {/* Stage 1 */}
                <div className="p-3 bg-amber-50/50 dark:bg-amber-950/20 rounded-xl border border-amber-200/50 text-xs space-y-1">
                  <div className="flex items-center justify-between font-semibold text-amber-900 dark:text-amber-200">
                    <span>Stage 1: Coordinator Review</span>
                    <span className="text-[11px] text-amber-700 dark:text-amber-400">
                      {cert.stage1_reviewed_at || 'Pending'}
                    </span>
                  </div>
                  {cert.stage1_notes && (
                    <p className="text-amber-800 dark:text-amber-300">
                      <strong>Notes:</strong> {cert.stage1_notes}
                    </p>
                  )}
                </div>

                {/* Stage 2 */}
                <div className="p-3 bg-blue-50/50 dark:bg-blue-950/20 rounded-xl border border-blue-200/50 text-xs space-y-1">
                  <div className="flex items-center justify-between font-semibold text-blue-900 dark:text-blue-200">
                    <span>Stage 2: Director / Approver Sign-off</span>
                    <span className="text-[11px] text-blue-700 dark:text-blue-400">
                      {cert.stage2_approved_at || 'Pending'}
                    </span>
                  </div>
                  {cert.stage2_notes && (
                    <p className="text-blue-800 dark:text-blue-300">
                      <strong>Notes:</strong> {cert.stage2_notes}
                    </p>
                  )}
                </div>

                {/* Revocation (if revoked) */}
                {cert.status === 'REVOKED' && (
                  <div className="p-3 bg-rose-50/50 dark:bg-rose-950/20 rounded-xl border border-rose-200/50 text-xs space-y-1">
                    <div className="flex items-center justify-between font-semibold text-rose-900 dark:text-rose-200">
                      <span>Credential Revoked</span>
                      <span className="text-[11px] text-rose-700 dark:text-rose-400">{cert.revoked_at}</span>
                    </div>
                    <p className="text-rose-800 dark:text-rose-300">
                      <strong>Category:</strong> {cert.revocation_category}
                    </p>
                    <p className="text-rose-800 dark:text-rose-300">
                      <strong>Rationale:</strong> {cert.revocation_reason}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center gap-3">
              {cert.status === 'ISSUED' && (
                <button
                  onClick={() => onDownloadPdf(cert)}
                  className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 shadow-md shadow-emerald-600/20 transition-all"
                >
                  <Download className="w-4 h-4" />
                  Download Official PDF
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
