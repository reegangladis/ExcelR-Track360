import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { CertificatePublicVerifyResponse } from '@/types';
import {
  Award,
  ShieldCheck,
  ShieldAlert,
  Search,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight,
  Copy,
  Check,
  RefreshCw,
} from 'lucide-react';

export const PublicVerifyPage: React.FC = () => {
  const { identifier: urlParam } = useParams<{ identifier?: string }>();
  const [searchInput, setSearchInput] = useState<string>(urlParam || '');
  const [activeIdentifier, setActiveIdentifier] = useState<string>(urlParam || '');
  const [copiedHash, setCopiedHash] = useState(false);

  useEffect(() => {
    if (urlParam) {
      setSearchInput(urlParam);
      setActiveIdentifier(urlParam);
    }
  }, [urlParam]);

  const {
    data: result,
    isLoading,
    isError,
  } = useQuery<CertificatePublicVerifyResponse>({
    queryKey: ['public-verify', activeIdentifier],
    queryFn: () => api.verifyCertificatePublic(activeIdentifier),
    enabled: !!activeIdentifier.trim(),
    retry: false,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setActiveIdentifier(searchInput.trim());
    }
  };

  const handleCopyHash = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      {/* Top Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-amber-500 to-amber-600 rounded-xl text-slate-950 font-bold shadow-lg shadow-amber-500/20">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-extrabold tracking-tight text-white flex items-center gap-2">
              ExcelR Track360
              <span className="text-[10px] uppercase font-bold tracking-widest text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded-full border border-indigo-800/40">
                Registry
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">Official National Credential Verification Engine</p>
          </div>
        </div>

        <Link
          to="/login"
          className="text-xs font-semibold text-slate-400 hover:text-white transition-colors flex items-center gap-1.5"
        >
          Staff & Student Portal
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-12 space-y-8 flex flex-col justify-center">
        {/* Verification Search Box */}
        <div className="space-y-3 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-950/60 border border-indigo-800/40 text-xs font-medium text-indigo-300">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            SEC-CERT-01 Cryptographic Validation Protocol
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
            Verify Credential Authenticity
          </h2>
          <p className="text-sm text-slate-400 max-w-xl mx-auto">
            Instant, independent validation of completed academic tracks, accredited milestone durations, and verified certificate credentials.
          </p>

          <form onSubmit={handleSearch} className="max-w-xl mx-auto mt-6 flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Enter Serial ID (e.g. EXCELR-2026-FSD-...) or Hash"
                className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700/80 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-inner"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !searchInput.trim()}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2"
            >
              {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Verify'}
            </button>
          </form>
        </div>

        {/* Verification Result Display */}
        {isLoading && (
          <div className="p-12 bg-slate-900/60 rounded-2xl border border-slate-800 text-center space-y-3 animate-pulse">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-400 mx-auto" />
            <p className="text-sm font-semibold text-slate-300">
              Querying ExcelR National Cryptographic Registry...
            </p>
          </div>
        )}

        {isError && (
          <div className="p-8 bg-slate-900/80 rounded-2xl border border-rose-900/50 shadow-2xl text-center space-y-3 animate-in fade-in">
            <div className="w-14 h-14 bg-rose-950/80 text-rose-400 rounded-full flex items-center justify-center mx-auto border border-rose-800/60">
              <ShieldAlert className="w-7 h-7" />
            </div>
            <h3 className="text-xl font-bold text-white">Credential Record Not Found</h3>
            <p className="text-xs text-rose-300 max-w-md mx-auto">
              No authentic certificate matches identifier{' '}
              <span className="font-mono text-white font-bold">{activeIdentifier}</span>. Please verify the serial number on your credential.
            </p>
          </div>
        )}

        {result && (
          <div className="animate-in fade-in duration-300">
            {/* Valid & Issued State */}
            {result.is_valid && result.status === 'ISSUED' && (
              <div className="bg-slate-900/90 rounded-2xl border-2 border-emerald-500/40 shadow-2xl overflow-hidden shadow-emerald-500/10">
                {/* Official Stamp Banner */}
                <div className="bg-gradient-to-r from-emerald-950 via-slate-900 to-emerald-950 px-6 py-4 border-b border-emerald-500/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-xl border border-emerald-500/40">
                      <ShieldCheck className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                        Official Academic Record
                      </span>
                      <h4 className="text-base font-bold text-white flex items-center gap-2">
                        Authentic Verified Credential
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      </h4>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-xs font-bold text-emerald-300 bg-emerald-950/60 px-2.5 py-1 rounded-md border border-emerald-800/50">
                      {result.serial_number}
                    </span>
                  </div>
                </div>

                {/* Credential Data Grid */}
                <div className="p-6 md:p-8 space-y-6">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                      Awarded To Candidate
                    </span>
                    <h3 className="text-2xl md:text-3xl font-extrabold text-white">
                      {result.candidate_name}
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-1">
                      <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
                        <Layers className="w-4 h-4 text-indigo-400" />
                        Accredited Specialization Track
                      </span>
                      <p className="text-base font-bold text-slate-100">{result.track_title}</p>
                    </div>

                    <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-1">
                      <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
                        <Clock className="w-4 h-4 text-amber-400" />
                        Accredited Duration Policy
                      </span>
                      <p className="text-base font-bold text-amber-300">
                        {result.accredited_duration_months} Months Accredited Program
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 bg-slate-950/60 rounded-xl border border-slate-800 text-xs">
                    <div>
                      <span className="text-slate-400 block">Date of Official Issuance:</span>
                      <span className="font-semibold text-slate-200">{result.issue_date}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Issuing Authority:</span>
                      <span className="font-semibold text-indigo-300">ExcelR Academic Standards Board</span>
                    </div>
                  </div>

                  {/* Cryptographic Hash Verification Box */}
                  <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        Cryptographic Verification Signature (HMAC-SHA256)
                      </span>
                      <button
                        onClick={() => handleCopyHash(result.verification_hash)}
                        className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                      >
                        {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedHash ? 'Copied' : 'Copy Signature'}
                      </button>
                    </div>
                    <p className="font-mono text-xs text-slate-300 break-all select-all bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                      {result.verification_hash}
                    </p>
                  </div>
                </div>

                {/* Footer Assurance */}
                <div className="px-6 py-3.5 bg-slate-950 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Cryptographically secured & tamper-evident.</span>
                  <span className="text-emerald-400 font-semibold">100% Verified Authentic</span>
                </div>
              </div>
            )}

            {/* Revoked State */}
            {result.status === 'REVOKED' && (
              <div className="bg-slate-900/90 rounded-2xl border-2 border-rose-500/50 shadow-2xl overflow-hidden shadow-rose-500/10">
                <div className="bg-gradient-to-r from-rose-950 via-slate-900 to-rose-950 px-6 py-4 border-b border-rose-500/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-rose-500/20 text-rose-400 rounded-xl border border-rose-500/40">
                      <ShieldAlert className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-rose-400">
                        Registry Alert
                      </span>
                      <h4 className="text-base font-bold text-white flex items-center gap-2">
                        Credential Revoked & Nullified
                      </h4>
                    </div>
                  </div>
                  <span className="font-mono text-xs font-bold text-rose-300 bg-rose-950/60 px-2.5 py-1 rounded-md border border-rose-800/50">
                    {result.serial_number}
                  </span>
                </div>

                <div className="p-6 md:p-8 space-y-4">
                  <div>
                    <span className="text-xs text-slate-400 block mb-1">Formerly Awarded To</span>
                    <h3 className="text-2xl font-bold text-white">{result.candidate_name}</h3>
                  </div>

                  <div className="p-4 bg-rose-950/30 rounded-xl border border-rose-800/50 text-xs text-rose-200 space-y-1">
                    <p className="font-semibold text-rose-300">
                      Revocation Category: {result.revocation_category || 'Administrative Invalidation'}
                    </p>
                    <p>
                      This credential has been formally invalidated by authorized institutional officials and is no longer valid for professional or academic representation.
                    </p>
                    {result.revoked_at && (
                      <p className="text-[11px] text-slate-400 pt-1">
                        Revocation Timestamp: {result.revoked_at}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Tampered State */}
            {result.status === 'TAMPERED' && (
              <div className="bg-slate-900/90 rounded-2xl border-2 border-amber-500/50 shadow-2xl overflow-hidden p-6 text-center space-y-3">
                <div className="w-12 h-12 bg-amber-950/60 text-amber-400 rounded-xl flex items-center justify-center mx-auto border border-amber-800/50">
                  <ShieldAlert className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-white">Cryptographic Tampering Detected</h3>
                <p className="text-xs text-amber-200 max-w-md mx-auto">
                  The cryptographic signature for serial number {result.serial_number} does not match the authoritative registry records.
                </p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-6 text-center text-xs text-slate-500">
        <p>© 2026 ExcelR Solutions. Track360 Academic Registry & Credential Verification Portal.</p>
      </footer>
    </div>
  );
};
