import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { RubricCriterionItem } from '@/types';
import {
  X,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ExternalLink,
  Download,
  Loader2,
  Clock,
  Award,
} from 'lucide-react';

interface SubmissionReviewModalProps {
  submissionId: string | null;
  onClose: () => void;
}

export const SubmissionReviewModal: React.FC<SubmissionReviewModalProps> = ({
  submissionId,
  onClose,
}) => {
  const queryClient = useQueryClient();

  const { data: detail, isLoading } = useQuery({
    queryKey: ['submissionDetail', submissionId],
    queryFn: () => (submissionId ? api.getSubmissionDetail(submissionId) : null),
    enabled: !!submissionId,
  });

  const [outcome, setOutcome] = useState<'APPROVED' | 'CORRECTIONS_REQUESTED' | 'REJECTED'>('APPROVED');
  const [qualitativeFeedback, setQualitativeFeedback] = useState('');
  const [internalNotes, setInternalNotes] = useState('');
  const [criterionScores, setCriterionScores] = useState<
    Record<string, { awarded_points: number; comments: string }>
  >({});
  const [error, setError] = useState<string | null>(null);

  // Initialize rubric scores when detail loads
  useEffect(() => {
    if (detail?.assignment_rubric) {
      const initial: Record<string, { awarded_points: number; comments: string }> = {};
      detail.assignment_rubric.forEach((c) => {
        initial[c.key] = { awarded_points: c.max_points, comments: '' };
      });
      setCriterionScores(initial);
    }
  }, [detail]);

  const reviewMutation = useMutation({
    mutationFn: (payload: any) => api.reviewSubmission(submissionId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      onClose();
    },
    onError: (err: any) => {
      setError(err.message || 'Failed to submit review.');
    },
  });

  if (!submissionId) return null;

  const totalScore = Object.values(criterionScores).reduce(
    (sum, c) => sum + (Number(c.awarded_points) || 0),
    0
  );
  const passingScore = detail?.passing_score ?? 60;
  const isBelowPassing = totalScore < passingScore;

  const handleScoreChange = (key: string, points: number, max: number) => {
    const val = Math.max(0, Math.min(points, max));
    setCriterionScores((prev) => ({
      ...prev,
      [key]: { ...prev[key], awarded_points: val },
    }));
  };

  const handleCommentsChange = (key: string, comments: string) => {
    setCriterionScores((prev) => ({
      ...prev,
      [key]: { ...prev[key], comments },
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!qualitativeFeedback.trim()) {
      setError('Qualitative feedback is required.');
      return;
    }

    if (outcome === 'APPROVED' && isBelowPassing) {
      setError(
        `Cannot approve submission: Total score (${totalScore.toFixed(
          1
        )}) is below the required passing threshold (${passingScore.toFixed(1)}).`
      );
      return;
    }

    const rubricScores = (detail?.assignment_rubric || []).map((c: RubricCriterionItem) => ({
      criterion_key: c.key,
      criterion_title: c.title,
      max_points: c.max_points,
      awarded_points: Number(criterionScores[c.key]?.awarded_points || 0),
      criterion_comments: criterionScores[c.key]?.comments || undefined,
    }));

    reviewMutation.mutate({
      review_outcome: outcome,
      qualitative_feedback: qualitativeFeedback.trim(),
      internal_evaluator_notes: internalNotes.trim() || undefined,
      rubric_scores: rubricScores,
    });
  };

  const latestAttempt = detail?.attempts?.[detail.attempts.length - 1];

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 bg-slate-50">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Award className="w-5 h-5 text-indigo-600" />
              Rubric Evaluation & Grading
            </h2>
            <p className="text-xs text-slate-500">
              {detail ? `${detail.assignment_code} • ${detail.candidate_name} (${detail.candidate_number})` : 'Loading...'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoading || !detail ? (
          <div className="p-12 flex flex-col items-center justify-center text-slate-500 gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            <span className="text-sm">Fetching authoritative submission history...</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-5 space-y-5">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{error}</span>
              </div>
            )}

            {/* Submission Deliverables & Meta */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">
                  Attempt #{latestAttempt?.attempt_number} of {detail.total_attempts}
                </span>
                <span className="flex items-center gap-1.5 text-slate-500">
                  <Clock className="w-3.5 h-3.5" />
                  Submitted UTC: {latestAttempt?.submitted_at_utc ? new Date(latestAttempt.submitted_at_utc).toUTCString() : 'N/A'}
                </span>
              </div>

              {latestAttempt?.is_late && (
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-50 text-amber-700 border border-amber-200 text-xs font-medium">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Late Submission: {latestAttempt.lateness_minutes} minutes past deadline
                </div>
              )}

              {latestAttempt?.repository_url && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500 font-medium">Git Repository:</span>
                  <a
                    href={latestAttempt.repository_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-600 hover:underline flex items-center gap-1 font-mono"
                  >
                    {latestAttempt.repository_url}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}

              {latestAttempt?.file_asset && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500 font-medium">Deliverable File:</span>
                  <a
                    href={`/api/v1/assignments/submissions/files/${latestAttempt.file_asset.id}`}
                    download
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 font-medium transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    {latestAttempt.file_asset.original_filename} (
                    {(latestAttempt.file_asset.file_size_bytes / 1024).toFixed(1)} KB)
                  </a>
                </div>
              )}

              {latestAttempt?.student_notes && (
                <div className="text-xs text-slate-600 bg-white p-2.5 rounded border border-slate-200">
                  <span className="font-semibold text-slate-700 block mb-1">Student Notes:</span>
                  {latestAttempt.student_notes}
                </div>
              )}
            </div>

            {/* Rubric Criteria Scoring */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                  Rubric Assessment Criteria
                </label>
                <div className="text-xs font-semibold">
                  Total Score:{' '}
                  <span className={isBelowPassing ? 'text-amber-600 font-bold' : 'text-emerald-600 font-bold'}>
                    {totalScore.toFixed(1)}
                  </span>{' '}
                  / {detail.max_score} (Passing: {passingScore})
                </div>
              </div>

              <div className="space-y-3">
                {detail.assignment_rubric?.map((criterion) => {
                  const currentScore = criterionScores[criterion.key]?.awarded_points ?? criterion.max_points;
                  const comments = criterionScores[criterion.key]?.comments ?? '';

                  return (
                    <div
                      key={criterion.key}
                      className="border border-slate-200 rounded-lg p-3 bg-white space-y-2 hover:border-slate-300 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="font-semibold text-xs text-slate-800">{criterion.title}</span>
                          {criterion.description && (
                            <p className="text-xs text-slate-400 mt-0.5">{criterion.description}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <input
                            type="number"
                            min="0"
                            max={criterion.max_points}
                            step="0.5"
                            value={currentScore}
                            onChange={(e) =>
                              handleScoreChange(criterion.key, parseFloat(e.target.value) || 0, criterion.max_points)
                            }
                            className="w-16 border border-slate-300 rounded px-2 py-1 text-xs text-right font-mono"
                          />
                          <span className="text-xs text-slate-400">/ {criterion.max_points}</span>
                        </div>
                      </div>
                      <input
                        type="text"
                        placeholder="Criterion feedback or remarks (optional)..."
                        value={comments}
                        onChange={(e) => handleCommentsChange(criterion.key, e.target.value)}
                        className="w-full border border-slate-200 rounded px-2.5 py-1 text-xs text-slate-600 placeholder:text-slate-400"
                      />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Qualitative Feedback */}
            <div>
              <label htmlFor="qualitative_feedback" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Qualitative Feedback *
              </label>
              <textarea
                id="qualitative_feedback"
                required
                rows={3}
                placeholder="Detailed reviewer evaluation, actionable remarks, and strengths/weaknesses..."
                value={qualitativeFeedback}
                onChange={(e) => setQualitativeFeedback(e.target.value)}
                className="w-full border border-slate-300 rounded-lg p-2.5 text-xs text-slate-700 placeholder:text-slate-400 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {/* Internal Notes */}
            <div>
              <label htmlFor="internal_notes" className="block text-xs font-semibold text-slate-600 mb-1">
                Internal Evaluator Notes (Audit Trail Only)
              </label>
              <input
                id="internal_notes"
                type="text"
                placeholder="Internal notes not visible to student..."
                value={internalNotes}
                onChange={(e) => setInternalNotes(e.target.value)}
                className="w-full border border-slate-300 rounded-lg p-2 text-xs text-slate-700 placeholder:text-slate-400"
              />
            </div>

            {/* Review Outcome Selection */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                Evaluation Decision *
              </label>
              <div className="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setOutcome('APPROVED')}
                  disabled={isBelowPassing}
                  className={`p-3 rounded-lg border text-left flex flex-col gap-1 transition-all ${
                    outcome === 'APPROVED'
                      ? 'border-emerald-600 bg-emerald-50 ring-1 ring-emerald-600'
                      : 'border-slate-200 hover:bg-slate-50'
                  } ${isBelowPassing ? 'opacity-40 cursor-not-allowed' : ''}`}
                >
                  <div className="flex items-center gap-1.5 text-emerald-700 font-bold text-xs">
                    <CheckCircle className="w-4 h-4" />
                    APPROVED
                  </div>
                  <span className="text-[11px] text-slate-500">
                    Passed assignment. Contributes to project prerequisite gating.
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setOutcome('CORRECTIONS_REQUESTED')}
                  className={`p-3 rounded-lg border text-left flex flex-col gap-1 transition-all ${
                    outcome === 'CORRECTIONS_REQUESTED'
                      ? 'border-amber-600 bg-amber-50 ring-1 ring-amber-600'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-amber-700 font-bold text-xs">
                    <AlertTriangle className="w-4 h-4" />
                    REWORK REQUESTED
                  </div>
                  <span className="text-[11px] text-slate-500">
                    Candidate can submit Attempt #{detail.total_attempts + 1} with fixes.
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setOutcome('REJECTED')}
                  className={`p-3 rounded-lg border text-left flex flex-col gap-1 transition-all ${
                    outcome === 'REJECTED'
                      ? 'border-rose-600 bg-rose-50 ring-1 ring-rose-600'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-rose-700 font-bold text-xs">
                    <XCircle className="w-4 h-4" />
                    REJECTED
                  </div>
                  <span className="text-[11px] text-slate-500">
                    Mark as failed with no additional attempt granted.
                  </span>
                </button>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={reviewMutation.isPending}
                className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2 shadow-sm"
              >
                {reviewMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Confirm Evaluation & Save Score
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
