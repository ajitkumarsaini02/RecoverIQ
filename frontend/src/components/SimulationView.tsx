import React, { useState } from 'react';
import { 
  Sparkles, 
  CheckCircle2, 
  XCircle, 
  ShieldAlert,
  Info
} from 'lucide-react';
import { runSimulation } from '../services/api';

export const SimulationView: React.FC = () => {
  const [running, setRunning] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunSimulation = async () => {
    try {
      setRunning(true);
      setError(null);
      const data = await runSimulation();
      setSimResult(data);
    } catch (err: any) {
      setError(err.message || 'Failed to run batch recovery simulation');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-surface-border relative overflow-hidden">
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-4 sm:gap-6">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] sm:text-[11px] font-mono font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
                SIMULATION SANDBOX
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] sm:text-[11px] font-mono font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/30">
                PORTFOLIO BATCH EVALUATION
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Recovery Analytics & Portfolio Simulation
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 leading-relaxed">
              Batch-evaluate unrecovered failed transactions across the portfolio using autonomous AI reasoning and deterministic policy guardrails.
            </p>
            <div className="flex items-center gap-1.5 text-[11px] text-amber-300/90 font-mono mt-2">
              <Info className="h-3.5 w-3.5 shrink-0" />
              <span>SIMULATION MODE — No external payment action will be executed.</span>
            </div>
          </div>

          <button
            onClick={handleRunSimulation}
            disabled={running}
            className="px-5 sm:px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-brand-600 hover:from-purple-500 hover:to-brand-500 text-white font-bold text-xs sm:text-sm shadow-md shadow-purple-500/20 flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50 shrink-0 cursor-pointer w-full sm:w-auto"
          >
            <Sparkles className={`h-4 w-4 ${running ? 'animate-spin' : ''}`} />
            <span>{running ? 'Evaluating Batch Recovery...' : 'Run Portfolio Analytics'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* Results Display */}
      {simResult ? (
        <div className="space-y-6 animate-fadeIn">
          {/* Dynamic Summary Card */}
          <div className="p-6 rounded-2xl glass-panel border border-brand-500/40 shadow-enterprise space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Batch Recovery Simulation Completed</h3>
              </div>
              <span className="text-xs font-mono text-slate-400">
                Batch ID: <code className="text-brand-300">{simResult.simulation_id}</code>
              </span>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed">
              {simResult.message}
            </p>

            {/* 6 Key Dynamic Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
              <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Portfolio</span>
                <span className="text-lg font-bold text-white font-mono">{(simResult.total_portfolio_transactions ?? 0).toLocaleString('en-IN')}</span>
                <span className="text-[10px] text-slate-500 block">Total records</span>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Evaluated</span>
                <span className="text-lg font-bold text-purple-300 font-mono">{simResult.transactions_evaluated}</span>
                <span className="text-[10px] text-slate-500 block">Failed txns</span>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-base border border-rose-900/30">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">At Risk</span>
                <span className="text-lg font-bold text-rose-400 font-mono">
                  ₹{(simResult.initial_revenue_at_risk || 0).toLocaleString('en-IN')}
                </span>
                <span className="text-[10px] text-slate-500 block">Failed revenue</span>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-base border border-blue-500/30">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Attempts</span>
                <span className="text-lg font-bold text-blue-400 font-mono">{simResult.recovery_attempts}</span>
                <span className="text-[10px] text-slate-500 block">Actions run</span>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-base border border-emerald-500/40">
                <span className="text-[10px] font-mono text-emerald-400 uppercase block">Simulated Revenue</span>
                <span className="text-lg font-bold text-emerald-400 font-mono">
                  +₹{(simResult.revenue_recovered || 0).toLocaleString('en-IN')}
                </span>
                <span className="text-[10px] text-slate-500 block">Recovered</span>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-base border border-brand-500/40">
                <span className="text-[10px] font-mono text-brand-300 uppercase block">Recovery Rate</span>
                <span className="text-lg font-bold text-brand-300 font-mono">{simResult.recovery_rate}%</span>
                <span className="text-[10px] text-slate-500 block">Conversion</span>
              </div>
            </div>
          </div>

          {/* 3 Outcome Breakdown Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 rounded-2xl glass-card border border-emerald-500/30 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <h4 className="text-sm font-bold text-white">Simulated Recoveries</h4>
              </div>
              <div className="text-2xl font-extrabold text-emerald-400 font-mono">{simResult.successful_recoveries}</div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Eligible for automatic recovery via safe retry or Razorpay payment link.
              </p>
            </div>

            <div className="p-5 rounded-2xl glass-card border border-surface-border space-y-2">
              <div className="flex items-center gap-2">
                <XCircle className="h-4 w-4 text-slate-400" />
                <h4 className="text-sm font-bold text-white">Policy Halted / Stopped</h4>
              </div>
              <div className="text-2xl font-extrabold text-slate-300 font-mono">{simResult.stopped_cases}</div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Bounded by 2-retry safety ceiling or low probability floor (&lt; 25%) to protect customer experience.
              </p>
            </div>

            <div className="p-5 rounded-2xl glass-card border border-amber-500/30 space-y-2">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-amber-400" />
                <h4 className="text-sm font-bold text-white">Gated for Human Approval</h4>
              </div>
              <div className="text-2xl font-extrabold text-amber-400 font-mono">{simResult.pending_approvals_generated}</div>
              <p className="text-xs text-slate-400 leading-relaxed">
                High-value enterprise payments (&gt; ₹20,000) routed to Approval Queue.
              </p>
            </div>
          </div>

          {/* Compliance Ledger Note */}
          <div className="p-3.5 rounded-xl bg-surface-base border border-surface-border text-center text-xs text-slate-400">
            <span className="font-semibold text-slate-300">Auditable Ledger: </span>
            <span>All simulation operations write immutable audit events with actor <code>SYSTEM</code> and event type <code>SIMULATION_BATCH_EXECUTED</code>.</span>
          </div>
        </div>
      ) : (
        <div className="p-12 rounded-2xl glass-panel border border-surface-border text-center space-y-3">
          <Sparkles className="h-10 w-10 text-purple-400 mx-auto" />
          <h3 className="text-base font-bold text-white">Ready for Portfolio Batch Recovery</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            Click <strong className="text-white">"Run Portfolio Analytics"</strong> to evaluate unrecovered payment failures across the merchant portfolio.
          </p>
        </div>
      )}
    </div>
  );
};
