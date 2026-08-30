import React from 'react';
import { 
  X, 
  User, 
  CreditCard, 
  Sparkles, 
  Clock, 
  CheckCircle2, 
  XCircle
} from 'lucide-react';
import { Transaction, AuditEvent } from '../types';

interface TransactionDetailModalProps {
  transaction: Transaction | null;
  onClose: () => void;
  onAnalyze?: (transactionId: string) => void;
}

export const TransactionDetailModal: React.FC<TransactionDetailModalProps> = ({
  transaction,
  onClose,
  onAnalyze
}) => {
  if (!transaction) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'RECOVERED':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'FAILED':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'APPROVAL_REQUIRED':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'STOPPED':
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
  };

  const getFailureReasonBadge = (reason: string) => {
    switch (reason) {
      case 'UPI_TIMEOUT':
        return 'bg-purple-500/10 text-purple-300 border-purple-500/30';
      case 'BANK_DECLINED':
        return 'bg-rose-500/10 text-rose-300 border-rose-500/30';
      case 'INSUFFICIENT_FUNDS':
        return 'bg-amber-500/10 text-amber-300 border-amber-500/30';
      case 'NETWORK_ERROR':
        return 'bg-sky-500/10 text-sky-300 border-sky-500/30';
      default:
        return 'bg-slate-500/10 text-slate-300 border-slate-500/30';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#0f172a] border border-surface-border rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between bg-surface-card">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
              <CreditCard className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-slate-400">{transaction.id}</span>
                <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full border ${getStatusBadge(transaction.status)}`}>
                  {transaction.status}
                </span>
              </div>
              <h3 className="text-xl font-bold text-white">
                ₹{transaction.amount.toLocaleString('en-IN')}
                <span className="text-xs font-normal text-slate-400 ml-2">({transaction.payment_method})</span>
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Failure Context & Diagnostics */}
          <div className="p-4 rounded-xl bg-surface-base border border-surface-border grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <span className="text-xs text-slate-400 block mb-1">Failure Reason</span>
              <span className={`inline-block text-xs font-mono px-2.5 py-1 rounded-md border font-semibold ${getFailureReasonBadge(transaction.failure_reason)}`}>
                {transaction.failure_reason}
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-1">Error Code</span>
              <span className="text-xs font-mono text-slate-200 font-semibold">
                {transaction.error_code || 'N/A'}
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-1">Retry Attempts</span>
              <span className="text-xs font-mono text-slate-200 font-semibold">
                {transaction.retry_count} / {transaction.max_retries} max allowed
              </span>
            </div>
          </div>

          {/* Customer Profile Card */}
          <div className="p-4 rounded-xl glass-card border border-surface-border">
            <div className="flex items-center gap-2 mb-3">
              <User className="h-4 w-4 text-brand-400" />
              <h4 className="text-sm font-semibold text-white">Customer Historical Context</h4>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <span className="text-xs text-slate-400 block">Name</span>
                <span className="text-sm font-medium text-slate-200">{transaction.customer?.name || transaction.customer_name || 'N/A'}</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block">Email</span>
                <span className="text-xs font-mono text-slate-300 truncate block">{transaction.customer?.email || transaction.customer_email || 'N/A'}</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block">Customer LTV</span>
                <span className="text-sm font-bold text-emerald-400">
                  ₹{(transaction.customer?.lifetime_value || transaction.customer_lifetime_value || 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block">Payment History</span>
                <span className="text-xs font-mono text-slate-300">
                  <span className="text-emerald-400 font-bold">{transaction.previous_successful_payments ?? 0}</span> Success / 
                  <span className="text-red-400 font-bold ml-1">{transaction.previous_failed_payments ?? 0}</span> Fail
                </span>
              </div>
            </div>
          </div>

          {/* AI Reasoning & Policy Engine Section */}
          <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-800/30 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-purple-400" />
                <h4 className="text-sm font-semibold text-purple-200">AI Recovery Assessment</h4>
              </div>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-purple-900/50 text-purple-300 border border-purple-700">
                Pydantic Validated
              </span>
            </div>

            {transaction.status === 'RECOVERED' ? (
              <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-xs text-emerald-300 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>
                  Successfully recovered ₹{transaction.amount.toLocaleString('en-IN')} via safe retry execution.
                </span>
              </div>
            ) : transaction.status === 'STOPPED' ? (
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-300 flex items-center gap-2">
                <XCircle className="h-4 w-4 text-slate-400 shrink-0" />
                <span>
                  Recovery bounded by Policy Engine. Max retries exceeded or persistent risk detected.
                </span>
              </div>
            ) : (
              <div className="p-3 rounded-lg bg-surface-base/80 border border-surface-border text-xs text-slate-300 space-y-2">
                <p className="text-slate-400">
                  Ready for AI Agent diagnosis and policy-gated recovery execution.
                </p>
                {onAnalyze && (
                  <button
                    onClick={() => onAnalyze(transaction.id)}
                    className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>Run AI Diagnosis on this Transaction</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Audit Timeline */}
          {transaction.audit_events && transaction.audit_events.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-mono uppercase text-slate-400 tracking-wider">
                Transaction Audit Trail ({transaction.audit_events.length} Events)
              </h4>
              <div className="space-y-2">
                {transaction.audit_events.map((event: AuditEvent, idx: number) => (
                  <div key={event.id || idx} className="p-3 rounded-lg bg-surface-base border border-surface-border flex items-start justify-between text-xs">
                    <div className="flex items-start gap-2">
                      <Clock className="h-3.5 w-3.5 text-slate-500 mt-0.5" />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{event.event_type}</span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                            {event.actor}
                          </span>
                        </div>
                        {event.decision && (
                          <p className="text-slate-400 text-[11px] mt-0.5">Decision: {event.decision}</p>
                        )}
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500">
                      {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'Just now'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-surface-border bg-surface-card flex items-center justify-between text-xs text-slate-400">
          <span>Razorpay Order ID: <code className="text-slate-300">{transaction.razorpay_order_id || 'N/A'}</code></span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-surface-base border border-surface-border text-slate-300 hover:text-white transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
