import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  NotificationListResponse,
  EmailQueueListResponse,
  NotificationDispatchCreate,
} from '@/types';
import {
  Bell,
  Check,
  CheckCheck,
  Mail,
  Send,
  AlertTriangle,
  RefreshCw,
  Clock,
  ExternalLink,
  RotateCcw,
  X,
  Plus,
} from 'lucide-react';

export const NotificationsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [activeTab, setActiveTab] = useState<'ALL' | 'UNREAD' | 'EMAIL_QUEUE'>('ALL');
  const [page, setPage] = useState<number>(1);
  const [isBroadcastModalOpen, setIsBroadcastModalOpen] = useState(false);
  const pageSize = 15;

  const isSuperAdminOrOps = user?.roles.some((r) =>
    ['ROLE_SUPER_ADMIN', 'ROLE_OPS_ADMIN'].includes(r)
  );

  // Queries
  const { data: notificationsData, isLoading: isNotifsLoading } = useQuery<NotificationListResponse>({
    queryKey: ['notifications', activeTab, page],
    queryFn: () =>
      api.getNotifications({
        unread_only: activeTab === 'UNREAD',
        page,
        page_size: pageSize,
      }),
    enabled: activeTab !== 'EMAIL_QUEUE',
  });

  const { data: emailQueueData, isLoading: isQueueLoading } = useQuery<EmailQueueListResponse>({
    queryKey: ['email-queue', page],
    queryFn: () => api.getEmailQueue({ page, page_size: pageSize }),
    enabled: activeTab === 'EMAIL_QUEUE' && isSuperAdminOrOps,
  });

  // Fast Unread Count
  const { data: unreadData } = useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => api.getUnreadNotificationCount(),
  });

  // Mutations
  const markReadMutation = useMutation({
    mutationFn: (id: string) => api.markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-recent'] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => api.markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-recent'] });
    },
  });

  const retryEmailsMutation = useMutation({
    mutationFn: () => api.retryFailedEmails(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-queue'] });
    },
  });

  const unreadCount = unreadData?.unread_count || 0;
  const notifications = notificationsData?.items || [];
  const totalNotifications = notificationsData?.total || 0;
  const totalNotifPages = Math.ceil(totalNotifications / pageSize) || 1;

  const emailItems = emailQueueData?.items || [];
  const totalEmails = emailQueueData?.total || 0;
  const totalEmailPages = Math.ceil(totalEmails / pageSize) || 1;

  const formatEventType = (type: string) => {
    switch (type) {
      case 'ASSIGNMENT_ALLOCATED':
        return { label: 'Assignment', color: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300' };
      case 'SUBMISSION_RECEIVED':
        return { label: 'Submission', color: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300' };
      case 'REVIEW_FEEDBACK_PUBLISHED':
        return { label: 'Evaluation', color: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300' };
      case 'GROUP_READINESS_BLOCKED':
        return { label: 'Group Blocked', color: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300' };
      case 'CERTIFICATE_ISSUED':
        return { label: 'Certificate', color: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300' };
      case 'CERTIFICATE_REVOKED':
        return { label: 'Revocation', color: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300' };
      default:
        return { label: type.replace('_', ' '), color: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300' };
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 rounded-2xl text-white shadow-xl border border-indigo-800/30">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-500/20 text-indigo-400 rounded-xl border border-indigo-500/30">
            <Bell className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Notification Center & Communication Hub
            </h1>
            <p className="text-sm text-slate-300 mt-0.5">
              Event-driven in-app alerts, milestone notifications, and transactional email queue dispatcher.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {unreadCount > 0 && activeTab !== 'EMAIL_QUEUE' && (
            <button
              onClick={() => markAllReadMutation.mutate()}
              disabled={markAllReadMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-indigo-400/30 text-indigo-200 hover:bg-indigo-900/50 hover:text-white transition-all text-sm font-semibold"
            >
              {markAllReadMutation.isPending ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCheck className="w-4 h-4 text-emerald-400" />
              )}
              Mark All Read
            </button>
          )}

          {isSuperAdminOrOps && (
            <button
              onClick={() => setIsBroadcastModalOpen(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-semibold rounded-xl shadow-lg shadow-indigo-500/25 transition-all text-sm"
            >
              <Plus className="w-4 h-4" />
              Broadcast Alert
            </button>
          )}
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Unread Alerts
            </p>
            <h3 className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">{unreadCount}</h3>
            <span className="text-xs text-slate-400">Requiring attention</span>
          </div>
          <div className="p-3 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 rounded-xl">
            <Bell className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Total Notifications
            </p>
            <h3 className="text-2xl font-bold text-slate-800 dark:text-slate-200 mt-1">{totalNotifications}</h3>
            <span className="text-xs text-slate-400">Historical alerts</span>
          </div>
          <div className="p-3 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-xl">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        {isSuperAdminOrOps && (
          <>
            <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Email Queue
                </p>
                <h3 className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">{totalEmails}</h3>
                <span className="text-xs text-slate-400">Transactional emails</span>
              </div>
              <div className="p-3 bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 rounded-xl">
                <Mail className="w-6 h-6" />
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Retry Action
                </p>
                <button
                  onClick={() => retryEmailsMutation.mutate()}
                  disabled={retryEmailsMutation.isPending}
                  className="mt-1 inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 font-semibold text-xs rounded-lg border border-amber-200 dark:border-amber-800/40 transition-colors"
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${retryEmailsMutation.isPending ? 'animate-spin' : ''}`} />
                  Retry Failed
                </button>
                <p className="text-[11px] text-slate-400 mt-0.5">Flush retry backoff</p>
              </div>
              <div className="p-3 bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 rounded-xl">
                <RotateCcw className="w-6 h-6" />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        <button
          onClick={() => {
            setActiveTab('ALL');
            setPage(1);
          }}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            activeTab === 'ALL'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <span>All Notifications</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-white/20 text-white">
            {totalNotifications}
          </span>
        </button>

        <button
          onClick={() => {
            setActiveTab('UNREAD');
            setPage(1);
          }}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            activeTab === 'UNREAD'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <span>Unread Only</span>
          {unreadCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500 text-white font-extrabold">
              {unreadCount}
            </span>
          )}
        </button>

        {isSuperAdminOrOps && (
          <button
            onClick={() => {
              setActiveTab('EMAIL_QUEUE');
              setPage(1);
            }}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === 'EMAIL_QUEUE'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            <Mail className="w-3.5 h-3.5" />
            <span>Email Dispatch Queue</span>
          </button>
        )}
      </div>

      {/* Main Content Pane */}
      {activeTab !== 'EMAIL_QUEUE' ? (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
          {isNotifsLoading ? (
            <div className="py-16 flex flex-col items-center justify-center text-slate-400">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-2" />
              <p className="text-sm font-semibold">Retrieving notifications...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <Bell className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-base font-bold text-slate-700 dark:text-slate-300">
                {activeTab === 'UNREAD' ? 'No unread notifications' : 'No notifications found'}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                You will receive alerts here when lifecycle events occur.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {notifications.map((notif) => {
                const badge = formatEventType(notif.event_type);
                return (
                  <div
                    key={notif.id}
                    className={`p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-colors ${
                      notif.is_read
                        ? 'bg-white dark:bg-slate-900 hover:bg-slate-50/50'
                        : 'bg-indigo-50/30 dark:bg-indigo-950/20 hover:bg-indigo-50/50'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div
                        className={`w-2.5 h-2.5 rounded-full mt-2 shrink-0 ${
                          notif.is_read
                            ? 'bg-transparent'
                            : 'bg-indigo-600 ring-4 ring-indigo-100 dark:ring-indigo-950'
                        }`}
                      />
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${badge.color}`}
                          >
                            {badge.label}
                          </span>
                          <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                            {notif.title}
                          </h4>
                        </div>
                        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed max-w-2xl">
                          {notif.body}
                        </p>
                        <p className="text-[11px] text-slate-400 flex items-center gap-1.5 pt-0.5">
                          <Clock className="w-3 h-3" />
                          {new Date(notif.created_at).toLocaleString([], {
                            dateStyle: 'medium',
                            timeStyle: 'short',
                          })}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                      {notif.action_url && (
                        <button
                          onClick={() => navigate(notif.action_url!)}
                          className="inline-flex items-center gap-1 text-xs font-semibold px-3 py-1.5 rounded-lg border border-indigo-200 dark:border-indigo-800/50 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 transition-colors"
                        >
                          View Action
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      )}

                      {!notif.is_read && (
                        <button
                          onClick={() => markReadMutation.mutate(notif.id)}
                          disabled={markReadMutation.isPending}
                          title="Mark as read"
                          className="inline-flex items-center gap-1 text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/40 transition-colors"
                        >
                          <Check className="w-3.5 h-3.5" />
                          Mark Read
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {totalNotifications > 0 && (
            <div className="flex items-center justify-between px-6 py-4 bg-slate-50/75 dark:bg-slate-800/40 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-500">
              <span>
                Showing {notifications.length} of {totalNotifications} notifications
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
                  Page {page} of {totalNotifPages}
                </span>
                <button
                  disabled={page >= totalNotifPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Email Dispatch Queue Pane */
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 bg-slate-50/60 dark:bg-slate-800/30 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Outgoing Transactional Email Queue
              </h3>
              <p className="text-xs text-slate-500">
                Displays asynchronous SMTP queue with exponential backoff retry metadata.
              </p>
            </div>
            <button
              onClick={() => retryEmailsMutation.mutate()}
              disabled={retryEmailsMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${retryEmailsMutation.isPending ? 'animate-spin' : ''}`} />
              Flush / Retry Failed
            </button>
          </div>

          {isQueueLoading ? (
            <div className="py-16 flex flex-col items-center justify-center text-slate-400">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-2" />
              <p className="text-sm font-semibold">Retrieving email queue records...</p>
            </div>
          ) : emailItems.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <Mail className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-base font-bold text-slate-700 dark:text-slate-300">
                Email Queue is Empty
              </p>
              <p className="text-xs text-slate-400 mt-1">
                All transactional emails have been successfully dispatched.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Recipient</th>
                    <th className="py-3 px-4">Subject</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Attempts</th>
                    <th className="py-3 px-4">Enqueued At</th>
                    <th className="py-3 px-4">Error Diagnostics</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {emailItems.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="py-3 px-4 font-medium text-slate-900 dark:text-slate-100">
                        {item.recipient_email}
                      </td>
                      <td className="py-3 px-4 max-w-xs truncate" title={item.subject}>
                        {item.subject}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            item.delivery_status === 'SENT'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : item.delivery_status === 'PENDING'
                              ? 'bg-blue-50 text-blue-700 border border-blue-200'
                              : item.delivery_status === 'RETRYING'
                              ? 'bg-amber-50 text-amber-700 border border-amber-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {item.delivery_status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {item.attempt_count} / {item.max_attempts}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(item.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-4 max-w-xs text-rose-600 truncate" title={item.last_error_message || ''}>
                        {item.last_error_message || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Email Queue Pagination */}
          {totalEmails > 0 && (
            <div className="flex items-center justify-between px-6 py-4 bg-slate-50/75 dark:bg-slate-800/40 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-500">
              <span>
                Showing {emailItems.length} of {totalEmails} queued emails
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
                  Page {page} of {totalEmailPages}
                </span>
                <button
                  disabled={page >= totalEmailPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Broadcast Alert Modal */}
      {isBroadcastModalOpen && (
        <BroadcastAlertModal
          onClose={() => setIsBroadcastModalOpen(false)}
          onSuccess={() => {
            setIsBroadcastModalOpen(false);
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['email-queue'] });
          }}
        />
      )}
    </div>
  );
};

// ============================================================================
// Broadcast Notification Modal Component
// ============================================================================
interface BroadcastModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

const BroadcastAlertModal: React.FC<BroadcastModalProps> = ({ onClose, onSuccess }) => {
  const [eventType, setEventType] = useState('SYSTEM_ALERT');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [actionUrl, setActionUrl] = useState('');
  const [queueEmail, setQueueEmail] = useState(false);
  const [emailSubject, setEmailSubject] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch candidates for selection
  const { data: candidatesData } = useQuery({
    queryKey: ['candidates-for-broadcast'],
    queryFn: () => api.getCandidates({ page: 1, page_size: 50 }),
  });

  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);

  const dispatchMutation = useMutation({
    mutationFn: (data: NotificationDispatchCreate) => api.dispatchNotification(data),
    onSuccess: () => {
      onSuccess();
    },
    onError: (err: any) => {
      setErrorMsg(err.message || 'Failed to dispatch notification broadcast');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedUserIds.length === 0) {
      setErrorMsg('Please select at least one recipient candidate.');
      return;
    }
    if (!title.trim() || !body.trim()) {
      setErrorMsg('Notification Title and Body are mandatory.');
      return;
    }

    dispatchMutation.mutate({
      recipient_user_ids: selectedUserIds,
      event_type: eventType,
      title: title.trim(),
      body: body.trim(),
      action_url: actionUrl.trim() || null,
      queue_email: queueEmail,
      email_subject: emailSubject.trim() || title.trim(),
    });
  };

  const candidates = candidatesData?.items || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-indigo-50/50 dark:bg-indigo-950/20">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 rounded-lg">
              <Send className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Broadcast In-App Alert
              </h3>
              <p className="text-xs text-slate-500">
                Dispatches targeted operational notifications and transactional emails.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto">
          {errorMsg && (
            <div className="p-3 bg-rose-50 text-rose-700 text-xs rounded-xl flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Event Classification *
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="SYSTEM_ALERT">System Alert</option>
              <option value="ASSIGNMENT_ALLOCATED">Assignment Allocation</option>
              <option value="SUBMISSION_RECEIVED">Submission Receipt</option>
              <option value="REVIEW_FEEDBACK_PUBLISHED">Review Feedback Published</option>
              <option value="GROUP_READINESS_BLOCKED">Group Readiness Blocked</option>
              <option value="CERTIFICATE_ISSUED">Certificate Issued</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Select Recipient Candidates *
            </label>
            <div className="max-h-32 overflow-y-auto p-2 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700 space-y-1.5">
              {candidates.map((c) => (
                <label
                  key={c.id}
                  className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50 p-1 rounded"
                >
                  <input
                    type="checkbox"
                    checked={selectedUserIds.includes(c.user_id || c.id)}
                    onChange={(e) => {
                      const uid = c.user_id || c.id;
                      if (e.target.checked) {
                        setSelectedUserIds((prev) => [...prev, uid]);
                      } else {
                        setSelectedUserIds((prev) => prev.filter((id) => id !== uid));
                      }
                    }}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>
                    {c.first_name} {c.last_name} ({c.email})
                  </span>
                </label>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Selected: {selectedUserIds.length} recipient(s)
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Notification Title *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Schedule Update for React Project Group"
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Notification Body *
            </label>
            <textarea
              rows={3}
              required
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="State the notification message clearly..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Action URL (Optional)
            </label>
            <input
              type="text"
              value={actionUrl}
              onChange={(e) => setActionUrl(e.target.value)}
              placeholder="e.g. /projects or /assignments/123"
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-2">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="cb-queue-email"
                checked={queueEmail}
                onChange={(e) => setQueueEmail(e.target.checked)}
                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
              />
              <label htmlFor="cb-queue-email" className="text-xs font-semibold text-slate-700 dark:text-slate-300 select-none">
                Enqueue Transactional Email Dispatch (SMTP)
              </label>
            </div>

            {queueEmail && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Email Subject Line
                </label>
                <input
                  type="text"
                  value={emailSubject}
                  onChange={(e) => setEmailSubject(e.target.value)}
                  placeholder="Defaults to notification title"
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-medium text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            )}
          </div>

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
              disabled={dispatchMutation.isPending}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-md shadow-indigo-600/20"
            >
              {dispatchMutation.isPending && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
              Send Broadcast
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
