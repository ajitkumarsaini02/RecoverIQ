import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  ShieldAlert, 
  RefreshCw
} from 'lucide-react';
import { fetchApprovals, approveRecoveryAction, rejectRecoveryAction } from '../services/api';

export const ApprovalQueue: React.FC = () => {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApprovals();
      setApprovals(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch approval queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApprove = async (actionId: string) => {
    try {
      setActionInProgress(actionId);
      await approveRecoveryAction(actionId);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to approve recovery action');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleReject = async (actionId: string) => {
    try {
      setActionInProgress(actionId);
      await rejectRecoveryAction(actionId, 'Merchant manually rejected recovery');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to reject recovery action');
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white">Merchant Approval Queue</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">
              HUMAN-IN-THE-LOOP GUARDRAILS
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic policy guardrail queue. High-value transactions (&gt; ₹20,000) and high-risk recoveries require explicit merchant authorization.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl bg-surface-card border border-surface-border text-xs font-mono text-slate-300 hover:text-white hover:border-slate-600 transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-brand-400' : ''}`} />
          <span>{loading ? 'Refreshing...' : `Pending Approvals (${approvals.length})`}</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* Approvals List */}
      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="p-6 rounded-2xl glass-card border border-surface-border animate-pulse h-36" />
          ))}
        </div>
      ) : approvals.length === 0 ? (
        <div className="p-12 rounded-2xl glass-panel border border-surface-border text-center space-y-3">
          <CheckCircle2 className="h-10 w-10 text-emerald-400 mx-auto" />
          <h3 className="text-base font-bold text-white">Approval Queue is Clear</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            All current recovery operations are within safe automated bounds. High-value transactions will appear here when triggered.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((item) => {
            const isProcessing = actionInProgress === item.id;
            return (
              <div
                key={item.id}
                className="p-6 rounded-2xl glass-panel border border-amber-500/30 space-y-4 relative overflow-hidden"
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex items-start gap-3.5">
                    <div className="h-10 w-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
                      <ShieldAlert className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-slate-400">{item.transaction_id}</span>
                        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                          HIGH-VALUE GATE
                        </span>
                      </div>
                      <h3 className="text-lg font-bold text-white mt-0.5">
                        ₹{(item.transaction?.amount || 0).toLocaleString('en-IN')}{' '}
                        <span className="text-xs font-normal text-slate-400">
                          ({item.transaction?.customer_name || 'Customer'})
                        </span>
                      </h3>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5 shrink-0">
                    <button
                      onClick={() => handleReject(item.id)}
                      disabled={isProcessing}
                      className="px-4 py-2 rounded-xl bg-surface-base border border-surface-border hover:border-red-500/50 text-red-400 hover:text-red-300 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                    >
                      <XCircle className="h-4 w-4" />
                      <span>Reject & Halt</span>
                    </button>
                    <button
                      onClick={() => handleApprove(item.id)}
                      disabled={isProcessing}
                      className="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-brand-500 hover:from-emerald-500 hover:to-brand-400 text-white text-xs font-bold shadow-lg shadow-brand-500/20 flex items-center gap-1.5 transition-all disabled:opacity-50"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      <span>{isProcessing ? 'Executing...' : 'Approve & Execute Recovery'}</span>
                    </button>
                  </div>
                </div>

                {/* Diagnostic Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 rounded-xl bg-surface-base/80 border border-surface-border text-xs">
                  <div>
                    <span className="text-slate-400 block mb-1">AI Recommendation:</span>
                    <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono font-semibold">
                      {item.action_type}
                    </span>
                    <p className="text-[11px] text-slate-300 mt-1">{item.ai_reasoning}</p>
                  </div>

                  <div>
                    <span className="text-slate-400 block mb-1">Recovery Probability:</span>
                    <span className="font-bold text-emerald-400 font-mono text-sm">
                      {((item.ai_probability || 0) * 100).toFixed(1)}%
                    </span>
                    <p className="text-[11px] text-slate-400 mt-1">Diagnosis: {item.ai_diagnosis}</p>
                  </div>

                  <div>
                    <span className="text-slate-400 block mb-1">Policy Gate Rationale:</span>
                    <p className="text-[11px] text-amber-300 font-medium">
                      {item.policy_reasons?.[0] || 'High-value transaction exceeding ₹20,000 threshold.'}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
