import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  ShieldAlert, 
  RefreshCw,
  AlertTriangle
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
            <span className="px-2.5 py-0.5 rounded-full text-[10px] sm:text-[11px] font-mono font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
              HUMAN-IN-THE-LOOP GUARDRAIL
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic safety gate. High-value transactions (&gt; ₹20,000) and flagged actions require explicit merchant sign-off before execution.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl bg-surface-card border border-surface-border text-xs font-mono text-slate-300 hover:text-white hover:border-slate-600 transition-colors flex items-center gap-2 cursor-pointer w-full sm:w-auto justify-center"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-brand-400' : ''}`} />
          <span>{loading ? 'Refreshing...' : `Pending Approvals (${approvals.length})`}</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 text-xs flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Approvals List */}
      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="p-6 rounded-2xl glass-card border border-surface-border animate-pulse h-40" />
          ))}
        </div>
      ) : approvals.length === 0 ? (
        <div className="p-12 rounded-2xl glass-panel border border-surface-border text-center space-y-3">
          <CheckCircle2 className="h-10 w-10 text-emerald-400 mx-auto" />
          <h3 className="text-base font-bold text-white">Approval Queue is Clear</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            All current recovery operations are within safe automated bounds. High-value transactions exceeding ₹20,000 will be held here for manual authorization.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((item) => {
            const isProcessing = actionInProgress === item.id;
            const amount = item.transaction?.amount || 0;
            const customerName = item.transaction?.customer_name || item.transaction?.customer?.name || 'Customer';
            const riskLevel = item.ai_risk_level || 'LOW';

            return (
              <div
                key={item.id}
                className="p-5 sm:p-6 rounded-2xl glass-panel border border-amber-500/40 space-y-4 relative overflow-hidden shadow-lg"
              >
                {/* Header Row: High-Value Gate Notice + Action Buttons */}
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="h-10 w-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
                      <ShieldAlert className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                          HIGH-VALUE TRANSACTION
                        </span>
                        <span className="text-xs font-mono text-slate-400">{item.transaction_id}</span>
                        <span className="text-[11px] text-slate-400">· Human approval required</span>
                      </div>
                      <h3 className="text-xl sm:text-2xl font-bold text-white font-mono">
                        ₹{amount.toLocaleString('en-IN')}{' '}
                        <span className="text-xs font-normal font-sans text-slate-400">
                          ({customerName})
                        </span>
                      </h3>
                    </div>
                  </div>

                  {/* Approve / Reject Controls */}
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-2.5 shrink-0">
                    <button
                      onClick={() => handleReject(item.id)}
                      disabled={isProcessing}
                      className="px-4 py-2.5 rounded-xl bg-surface-base border border-surface-border hover:border-rose-500/50 text-rose-300 hover:text-rose-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer"
                    >
                      <XCircle className="h-4 w-4" />
                      <span>{isProcessing ? 'Processing...' : 'Reject & Halt'}</span>
                    </button>
                    <button
                      onClick={() => handleApprove(item.id)}
                      disabled={isProcessing}
                      className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-brand-500 hover:from-emerald-500 hover:to-brand-400 text-white text-xs font-bold shadow-md shadow-brand-500/20 flex items-center justify-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      <span>{isProcessing ? 'Executing...' : 'Approve & Execute'}</span>
                    </button>
                  </div>
                </div>

                {/* 4-Item Diagnostic Preview Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 p-4 rounded-xl bg-surface-base border border-surface-border text-xs">
                  {/* Item 1: Recommendation */}
                  <div>
                    <span className="text-slate-400 text-[11px] block mb-1 font-mono">AI Recommendation:</span>
                    <span className="inline-block px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono font-semibold text-xs">
                      {item.action_type}
                    </span>
                    <p className="text-[11px] text-slate-300 mt-1 line-clamp-2">{item.ai_reasoning}</p>
                  </div>

                  {/* Item 2: Risk Assessment */}
                  <div>
                    <span className="text-slate-400 text-[11px] block mb-1 font-mono">Risk Assessment:</span>
                    <span className={`inline-block px-2 py-0.5 rounded font-mono font-semibold text-xs ${
                      riskLevel === 'LOW' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    }`}>
                      {riskLevel} RISK
                    </span>
                    <p className="text-[11px] text-slate-400 mt-1">Diagnosis: {item.ai_diagnosis}</p>
                  </div>

                  {/* Item 3: Recovery Probability */}
                  <div>
                    <span className="text-slate-400 text-[11px] block mb-1 font-mono">Recovery Probability:</span>
                    <span className="font-bold text-emerald-400 font-mono text-sm block">
                      {((item.ai_probability || 0) * 100).toFixed(1)}%
                    </span>
                    <p className="text-[11px] text-slate-400 mt-1">Confidence score</p>
                  </div>

                  {/* Item 4: Policy Gate Reason */}
                  <div>
                    <span className="text-slate-400 text-[11px] block mb-1 font-mono">Policy Reason:</span>
                    <p className="text-[11px] text-amber-300 font-medium leading-relaxed">
                      {item.policy_reasons?.[0] || 'Approval required because amount exceeds ₹20,000 threshold.'}
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
