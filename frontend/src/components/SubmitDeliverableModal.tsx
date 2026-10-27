import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AllocationItem } from '@/types';
import { X, Upload, GitBranch, FileText, AlertCircle, Loader2 } from 'lucide-react';

interface SubmitDeliverableModalProps {
  isOpen: boolean;
  onClose: () => void;
  allocations: AllocationItem[];
  defaultAllocationId?: string;
}

export const SubmitDeliverableModal: React.FC<SubmitDeliverableModalProps> = ({
  isOpen,
  onClose,
  allocations,
  defaultAllocationId,
}) => {
  const queryClient = useQueryClient();

  const [allocationId, setAllocationId] = useState(defaultAllocationId || '');
  const [submissionType, setSubmissionType] = useState<'url' | 'file'>('url');
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [studentNotes, setStudentNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  const submitMutation = useMutation({
    mutationFn: (formData: FormData) =>
      api.submitAssignmentDeliverable(allocationId, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      queryClient.invalidateQueries({ queryKey: ['allocations'] });
      onClose();
      // Reset form
      setRepositoryUrl('');
      setSelectedFile(null);
      setStudentNotes('');
      setError(null);
    },
    onError: (err: any) => {
      setError(err.message || 'Failed to submit assignment deliverable.');
    },
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!allocationId) {
      setError('Please select an allocated assignment.');
      return;
    }

    if (submissionType === 'url' && !repositoryUrl.trim()) {
      setError('Please provide a repository URL.');
      return;
    }

    if (submissionType === 'file' && !selectedFile) {
      setError('Please select a deliverable file to upload.');
      return;
    }

    const formData = new FormData();
    if (submissionType === 'url') {
      formData.append('repository_url', repositoryUrl.trim());
    } else if (selectedFile) {
      formData.append('file', selectedFile);
    }

    if (studentNotes.trim()) {
      formData.append('student_notes', studentNotes.trim());
    }

    submitMutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-2">
            <Upload className="w-5 h-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900">
              Submit Assignment Deliverable
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          {/* Allocation Selection */}
          <div>
            <label htmlFor="submit_allocation" className="block text-xs font-semibold text-slate-700 mb-1">
              Select Allocated Assignment *
            </label>
            <select
              id="submit_allocation"
              required
              value={allocationId}
              onChange={(e) => setAllocationId(e.target.value)}
              className="w-full border border-slate-300 rounded-lg p-2 text-xs"
            >
              <option value="">Choose assignment allocation...</option>
              {allocations.map((alloc) => (
                <option key={alloc.id} value={alloc.id}>
                  {alloc.assignment_code} - {alloc.assignment_title} ({alloc.batch_code || alloc.candidate_name || 'Individual'})
                </option>
              ))}
            </select>
          </div>

          {/* Deliverable Type Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Deliverable Mode *
            </label>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="sub_type"
                  checked={submissionType === 'url'}
                  onChange={() => setSubmissionType('url')}
                  className="text-indigo-600"
                />
                <GitBranch className="w-3.5 h-3.5 text-slate-500" />
                Git Repository URL
              </label>
              <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="sub_type"
                  checked={submissionType === 'file'}
                  onChange={() => setSubmissionType('file')}
                  className="text-indigo-600"
                />
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                Upload File Asset
              </label>
            </div>
          </div>

          {/* URL Input */}
          {submissionType === 'url' ? (
            <div>
              <label htmlFor="repo_url" className="block text-xs font-medium text-slate-700 mb-1">
                Repository URL *
              </label>
              <input
                id="repo_url"
                type="url"
                required
                placeholder="https://github.com/organization/assignment-repo"
                value={repositoryUrl}
                onChange={(e) => setRepositoryUrl(e.target.value)}
                className="w-full border border-slate-300 rounded-lg p-2 text-xs font-mono"
              />
            </div>
          ) : (
            <div>
              <label htmlFor="deliverable_file" className="block text-xs font-medium text-slate-700 mb-1">
                Deliverable File (.pdf, .zip, .ipynb) *
              </label>
              <input
                id="deliverable_file"
                type="file"
                required
                accept=".pdf,.zip,.ipynb,.tar.gz"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="w-full border border-slate-300 rounded-lg p-1.5 text-xs text-slate-700"
              />
              {selectedFile && (
                <p className="text-[11px] text-slate-500 mt-1">
                  Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>
          )}

          {/* Notes */}
          <div>
            <label htmlFor="student_notes" className="block text-xs font-medium text-slate-700 mb-1">
              Submission Notes / Commit Reference
            </label>
            <textarea
              id="student_notes"
              rows={2}
              placeholder="Add implementation notes, run instructions, or summary of corrections..."
              value={studentNotes}
              onChange={(e) => setStudentNotes(e.target.value)}
              className="w-full border border-slate-300 rounded-lg p-2 text-xs text-slate-700 placeholder:text-slate-400"
            />
          </div>

          <div className="bg-slate-50 p-3 rounded border border-slate-200 text-[11px] text-slate-500 space-y-1">
            <p>• Timestamps are authoritatively recorded in UTC on the server.</p>
            <p>• If submitted past the deadline, lateness minutes will be calculated automatically.</p>
            <p>• New submissions increment the attempt counter while preserving previous attempt records.</p>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitMutation.isPending}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2 shadow-sm"
            >
              {submitMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Submit Attempt
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
