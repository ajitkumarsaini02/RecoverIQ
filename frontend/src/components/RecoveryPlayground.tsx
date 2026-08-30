import React, { useState } from 'react';
import { 
  Play, 
  Sparkles, 
  ShieldCheck, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  UserCheck, 
  CreditCard, 
  History,
  Activity,
  Zap
} from 'lucide-react';
import { runDemoScenario } from '../services/api';
import { DemoScenarioResult } from '../types';

interface PresetScenarioCard {
  id: string;
  title: string;
  subtitle: string;
  amount: number;
  method: string;
  reason: string;
  expectedOutcome: string;
  badge: string;
  badgeColor: string;
}

const PRESET_SCENARIOS: PresetScenarioCard[] = [
  {
    id: 'temporary_upi_failure',
    title: 'Scenario 1: Temporary UPI Timeout',
    subtitle: 'High LTV customer experiencing transient PSP network timeout',
    amount: 4999,
    method: 'UPI',
    reason: 'UPI_TIMEOUT',
    expectedOutcome: 'AI: 91% Prob -> Auto-Retry -> ₹4,999 Recovered',
    badge: 'FLAGSHIP DEMO',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
  },
  {
    id: 'bank_decline',
    title: 'Scenario 2: Bank Issuer Decline',
    subtitle: 'Card issuer decline on subscription transaction',
    amount: 2499,
    method: 'CARD',
    reason: 'BANK_DECLINED',
    expectedOutcome: 'AI: Alternate Method -> Smart Link Dispatched',
    badge: 'PAYMENT METHOD',
    badgeColor: 'bg-blue-500/20 text-blue-300 border-blue-500/40'
  },
  {
    id: 'network_failure',
    title: 'Scenario 3: Gateway Network Drop',
    subtitle: 'SSL / gateway handshake interruption during checkout',
    amount: 999,
    method: 'UPI',
    reason: 'NETWORK_ERROR',
    expectedOutcome: 'AI: 88% Prob -> Immediate Safe Retry -> Recovered',
    badge: 'NETWORK',
    badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/40'
  },
  {
    id: 'insufficient_funds',
    title: 'Scenario 4: Insufficient Account Balance',
    subtitle: 'Netbanking decline due to daily account limit',
    amount: 14999,
    method: 'NETBANKING',
    reason: 'INSUFFICIENT_FUNDS',
    expectedOutcome: 'AI: Payment Link Recovery -> Scheduled Link Sent',
    badge: 'PAYMENT LINK',
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40'
  },
  {
    id: 'repeated_failure',
    title: 'Scenario 5: Repeated Failure Cap',
    subtitle: 'Customer already failed twice previously',
    amount: 4999,
    method: 'CARD',
    reason: 'BANK_DECLINED',
    expectedOutcome: 'Policy Engine: 2-Retry Ceiling Reached -> STOP',
    badge: 'GUARDRAIL STOP',
    badgeColor: 'bg-slate-500/20 text-slate-300 border-slate-500/40'
  },
  {
    id: 'high_value_transaction',
    title: 'Scenario 6: High-Value Enterprise Payment',
    subtitle: 'Large B2B transaction exceeding ₹20,000 threshold',
    amount: 49999,
    method: 'CARD',
    reason: 'BANK_DECLINED',
    expectedOutcome: 'Policy Engine: Gated -> Approval Queue Triggered',
    badge: 'HUMAN APPROVAL',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/40'
  },
];

export const RecoveryPlayground: React.FC = () => {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('temporary_upi_failure');
  const [running, setRunning] = useState<boolean>(false);
  const [result, setResult] = useState<DemoScenarioResult | null>(null);
  const [stepIndex, setStepIndex] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const selectedScenario = PRESET_SCENARIOS.find((s) => s.id === selectedScenarioId) || PRESET_SCENARIOS[0];

  const handleRunScenario = async () => {
    try {
      setRunning(true);
      setError(null);
      setResult(null);
      setStepIndex(1); // Step 1: Payment Attempt

      const data = await runDemoScenario(selectedScenarioId);
      
      // Animate through all 7 pipeline steps smoothly for hackathon judges
      setTimeout(() => setStepIndex(2), 250); // Step 2: Gateway Failure
      setTimeout(() => setStepIndex(3), 600); // Step 3: AI Analysis
      setTimeout(() => setStepIndex(4), 950); // Step 4: Recovery Decision
      setTimeout(() => setStepIndex(5), 1300); // Step 5: Policy Check
      setTimeout(() => setStepIndex(6), 1650); // Step 6: Safe Action
      setTimeout(() => {
        setStepIndex(7); // Step 7: Revenue Result
        setResult(data);
        setRunning(false);
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to execute demo scenario');
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl glass-panel relative overflow-hidden border border-surface-border">
        <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-brand-500/10 to-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-brand-500/20 text-brand-300 border border-brand-500/40">
                Flagship Hackathon Demo
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                TEST MODE / SIMULATION
              </span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white">
              Autonomous Recovery Playground
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              Experience the end-to-end intelligent recovery pipeline: Customer payment fails on Razorpay Gateway $\rightarrow$ AI agent analyzes history $\rightarrow$ Policy engine checks safety guardrails $\rightarrow$ Safe recovery executed.
            </p>
          </div>

          <button
            onClick={handleRunScenario}
            disabled={running}
            className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-brand-600 to-emerald-500 hover:from-brand-500 hover:to-emerald-400 text-white font-bold text-sm shadow-xl shadow-brand-500/25 flex items-center justify-center gap-2.5 transition-all transform active:scale-95 disabled:opacity-50 shrink-0"
          >
            <Play className={`h-4 w-4 fill-white ${running ? 'animate-spin' : ''}`} />
            <span>{running ? 'Executing Recovery Pipeline...' : 'Run Scenario'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 flex items-center gap-3 text-sm">
          <XCircle className="h-5 w-5 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Scenario Selector Grid */}
      <div>
        <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-3">
          Select Merchant Payment Scenario (6 Presets)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {PRESET_SCENARIOS.map((s) => {
            const isSelected = selectedScenarioId === s.id;
            return (
              <div
                key={s.id}
                onClick={() => {
                  setSelectedScenarioId(s.id);
                  setResult(null);
                  setStepIndex(0);
                }}
                className={`p-4 rounded-xl glass-card border transition-all cursor-pointer relative overflow-hidden ${
                  isSelected
                    ? 'border-brand-500/60 bg-surface-highlight/70 shadow-lg shadow-brand-500/10'
                    : 'border-surface-border hover:border-slate-600 hover:bg-surface-card'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full border ${s.badgeColor}`}>
                    {s.badge}
                  </span>
                  <span className="text-sm font-bold text-white">
                    ₹{s.amount.toLocaleString('en-IN')}
                  </span>
                </div>
                <h4 className="font-semibold text-sm text-slate-100">{s.title}</h4>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">{s.subtitle}</p>
                <div className="mt-3 pt-3 border-t border-surface-border/50 flex items-center justify-between text-[11px] font-mono text-slate-300">
                  <span>Method: {s.method}</span>
                  <span className="text-brand-300 font-semibold">{s.reason}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live 7-Step Pipeline Stepper */}
      <div className="p-6 rounded-2xl glass-panel border border-surface-border space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-brand-400" />
            <h3 className="text-base font-bold text-white">7-Step Visual Recovery Pipeline</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">
            Selected: <strong className="text-white">{selectedScenario.title}</strong>
          </span>
        </div>

        {/* 7 Stepper Progress Nodes */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {[
            { step: 1, label: '1. PAYMENT', desc: `₹${selectedScenario.amount.toLocaleString('en-IN')}` },
            { step: 2, label: '2. FAILURE', desc: selectedScenario.reason },
            { step: 3, label: '3. AI ANALYSIS', desc: 'Context & History' },
            { step: 4, label: '4. RECOVERY DECISION', desc: 'Probability Est.' },
            { step: 5, label: '5. POLICY CHECK', desc: 'Safety Guardrails' },
            { step: 6, label: '6. ACTION', desc: 'Razorpay Execution' },
            { step: 7, label: '7. RESULT', desc: 'Revenue Outcome' },
          ].map((st) => {
            const isCompleted = stepIndex >= st.step;
            const isCurrent = stepIndex === st.step;
            return (
              <div
                key={st.step}
                className={`p-3 rounded-xl border text-left transition-all ${
                  isCurrent
                    ? 'bg-brand-500/20 border-brand-400 text-white shadow-md shadow-brand-500/20'
                    : isCompleted
                    ? 'bg-surface-base border-brand-500/30 text-slate-200'
                    : 'bg-surface-base/40 border-surface-border text-slate-500'
                }`}
              >
                <div className="flex items-center gap-1.5 mb-1">
                  {isCompleted ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-brand-400" />
                  ) : (
                    <Clock className="h-3.5 w-3.5 text-slate-500" />
                  )}
                  <span className="text-[11px] font-bold font-mono truncate">{st.label}</span>
                </div>
                <p className="text-[10px] truncate text-slate-400">{st.desc}</p>
              </div>
            );
          })}
        </div>

        {/* Execution Output Cards */}
        {result ? (
          <div className="space-y-4 animate-fadeIn">
            {/* Main Result Banner */}
            <div className={`p-5 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
              result.recovery_result.status === 'SUCCESS'
                ? 'bg-emerald-950/30 border-emerald-800/60'
                : result.recovery_result.status === 'PENDING_APPROVAL'
                ? 'bg-amber-950/30 border-amber-800/60'
                : 'bg-slate-900/60 border-slate-700'
            }`}>
              <div className="flex items-start gap-3.5">
                <div className={`h-11 w-11 rounded-xl flex items-center justify-center shrink-0 ${
                  result.recovery_result.status === 'SUCCESS'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : result.recovery_result.status === 'PENDING_APPROVAL'
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  {result.recovery_result.status === 'SUCCESS' ? (
                    <CheckCircle2 className="h-6 w-6" />
                  ) : result.recovery_result.status === 'PENDING_APPROVAL' ? (
                    <UserCheck className="h-6 w-6" />
                  ) : (
                    <XCircle className="h-6 w-6" />
                  )}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                      Execution Outcome:
                    </span>
                    <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded-full border ${
                      result.recovery_result.status === 'SUCCESS'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : result.recovery_result.status === 'PENDING_APPROVAL'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : 'bg-slate-800 text-slate-300 border-slate-700'
                    }`}>
                      {result.recovery_result.status}
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${
                      result.mode.includes('REAL TEST MODE')
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : 'bg-blue-500/20 text-blue-300 border-blue-500/40'
                    }`}>
                      Razorpay: {result.mode}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-slate-200 mt-1">
                    {result.recovery_result.message}
                  </p>
                </div>
              </div>

              {result.recovery_result.recovered_amount > 0 && (
                <div className="p-3 rounded-xl bg-surface-base border border-emerald-500/30 text-right shrink-0">
                  <span className="text-[11px] font-mono text-slate-400 uppercase block">Revenue Recovered</span>
                  <span className="text-2xl font-extrabold text-emerald-400">
                    +₹{result.recovery_result.recovered_amount.toLocaleString('en-IN')}
                  </span>
                </div>
              )}
            </div>

            {/* 3-Column Diagnostic Deep-Dive */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Column 1: AI Agent Reasoning */}
              <div className="p-4 rounded-xl glass-card border border-purple-800/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-purple-400" />
                    <h4 className="text-sm font-bold text-purple-200">AI Agent Diagnosis</h4>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-900/50 text-purple-300">
                    Pydantic v2
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-slate-400 block">Diagnosis:</span>
                    <p className="font-semibold text-slate-200">{result.ai_analysis.diagnosis}</p>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-surface-base border border-surface-border">
                    <span className="text-slate-400">Recovery Probability:</span>
                    <span className="font-bold text-emerald-400 font-mono text-sm">
                      {(result.ai_analysis.recovery_probability * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400 block">Recommended Action:</span>
                    <span className="inline-block mt-0.5 px-2 py-0.5 rounded font-mono text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      {result.ai_analysis.recommended_action}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400 block">AI Reasoning Grounding:</span>
                    <p className="text-slate-300 text-[11px] mt-0.5 leading-relaxed">{result.ai_analysis.reason}</p>
                  </div>
                </div>
              </div>

              {/* Column 2: Policy Engine Guardrails */}
              <div className="p-4 rounded-xl glass-card border border-brand-800/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-brand-400" />
                    <h4 className="text-sm font-bold text-brand-200">Policy Engine Gate</h4>
                  </div>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                    result.policy_decision.allowed ? 'bg-brand-900/50 text-brand-300' : 'bg-red-900/50 text-red-300'
                  }`}>
                    {result.policy_decision.allowed ? 'POLICY APPROVED' : 'POLICY BLOCKED'}
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-slate-400 block">Authorized Action:</span>
                    <span className="font-mono font-bold text-slate-200">{result.policy_decision.action}</span>
                  </div>

                  <div className="p-2 rounded-lg bg-surface-base border border-surface-border">
                    <span className="text-slate-400 block mb-1">Safety Rules Evaluated:</span>
                    <ul className="space-y-1">
                      {result.policy_decision.rules_evaluated?.map((r, i) => (
                        <li key={i} className="flex items-center gap-1.5 text-[11px]">
                          {r.passed ? (
                            <CheckCircle2 className="h-3 w-3 text-brand-400 shrink-0" />
                          ) : (
                            <XCircle className="h-3 w-3 text-amber-400 shrink-0" />
                          )}
                          <span className={r.passed ? 'text-slate-300' : 'text-amber-300 font-medium'}>
                            {r.description}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <span className="text-slate-400 block">Evaluation Rationale:</span>
                    <p className="text-slate-300 text-[11px] mt-0.5">
                      {result.policy_decision.reasons?.[0] || 'Safety thresholds satisfied.'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Column 3: Customer Context Snapshot */}
              <div className="p-4 rounded-xl glass-card border border-surface-border space-y-3">
                <div className="flex items-center gap-2">
                  <CreditCard className="h-4 w-4 text-blue-400" />
                  <h4 className="text-sm font-bold text-blue-200">Customer & Payment Data</h4>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Customer:</span>
                    <span className="font-medium text-slate-200">{result.transaction.customer_name || 'Merchant Customer'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Customer LTV:</span>
                    <span className="font-bold text-emerald-400">
                      ₹{(result.transaction.customer_lifetime_value || 0).toLocaleString('en-IN')}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Past History:</span>
                    <span className="font-mono text-slate-300">
                      <span className="text-emerald-400 font-bold">{result.transaction.previous_successful_payments}</span> Success / 
                      <span className="text-red-400 font-bold ml-1">{result.transaction.previous_failed_payments}</span> Fail
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Retries Attempted:</span>
                    <span className="font-mono text-slate-200">
                      {result.transaction.retry_count} / {result.transaction.max_retries}
                    </span>
                  </div>
                  <div className="pt-2 border-t border-surface-border flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Razorpay Order:</span>
                    <span className="font-mono text-slate-300 truncate max-w-[120px]">{result.transaction.razorpay_order_id || 'N/A'}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Audit Timeline */}
            <div className="p-4 rounded-xl bg-surface-base border border-surface-border space-y-2">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-slate-400" />
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300">
                  Pipeline Audit Trail ({result.audit_timeline.length} Events Logged)
                </h4>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
                {result.audit_timeline.map((event, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-surface-card border border-surface-border text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-brand-300 font-bold">
                        {event.actor}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'Just now'}
                      </span>
                    </div>
                    <p className="font-semibold text-slate-200 text-[11px] truncate">{event.event_type}</p>
                    {event.decision && (
                      <p className="text-slate-400 text-[10px]">Decision: <span className="text-slate-300">{event.decision}</span></p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="py-12 text-center text-slate-400 space-y-2">
            <Zap className="h-8 w-8 mx-auto text-brand-400/60 animate-pulse" />
            <p className="font-medium text-slate-300">Ready to simulate payment recovery</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Select any scenario above and click <strong className="text-white">"Run Scenario"</strong> to experience the live 7-step pipeline.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
