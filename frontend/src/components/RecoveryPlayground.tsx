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
import { runDemoScenario, API_BASE } from '../services/api';
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
    badge: 'UPI LATENCY',
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
    badge: 'ISSUER DECLINE',
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
    badge: 'GATEWAY TIMEOUT',
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
    badge: 'INSUFFICIENT FUNDS',
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
    badge: 'RETRY CEILING',
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
    badge: 'ENTERPRISE ESCALATION',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/40'
  },
];

export const RecoveryPlayground: React.FC = () => {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('temporary_upi_failure');
  const [executionMode, setExecutionMode] = useState<'TEST_MODE' | 'SIMULATION_MODE'>('TEST_MODE');
  const [running, setRunning] = useState<boolean>(false);
  const [result, setResult] = useState<DemoScenarioResult | null>(null);
  const [stepIndex, setStepIndex] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const selectedScenario = PRESET_SCENARIOS.find((s) => s.id === selectedScenarioId) || PRESET_SCENARIOS[0];

  const handleRunScenario = async () => {
    console.log("[RecoverIQ] Run Scenario clicked");
    console.log("[RecoverIQ] Selected scenario:", selectedScenarioId);
    console.log("[RecoverIQ] Execution mode:", executionMode);
    console.log("[RecoverIQ] API URL:", API_BASE);

    try {
      setRunning(true);
      setError(null);
      setResult(null);
      setStepIndex(1); // Step 1: Payment Attempt

      const scenarioToRun = selectedScenarioId || 'temporary_upi_failure';
      const data = await runDemoScenario(scenarioToRun, executionMode);
      console.log("[RecoverIQ] Scenario execution successful:", data);
      
      // Animate through all 7 pipeline steps smoothly for execution visibility
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
      console.error('[RecoverIQ] Scenario execution failed:', err);
      setError(err.message || 'Unable to connect to RecoverIQ backend.');
      setRunning(false);
      setStepIndex(0);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Top Banner */}
      <div className="p-4 sm:p-6 rounded-2xl glass-panel relative overflow-hidden border border-surface-border">
        <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-brand-500/10 to-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-4 sm:gap-6">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2 mb-1.5 sm:mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] sm:text-[11px] font-mono font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/30">
                Autonomous Pipeline
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Autonomous Recovery
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 mt-1">
              Intelligent payment recovery pipeline that analyzes failed transactions, evaluates recovery risk, applies policy guardrails, and executes the safest recovery action.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3 shrink-0">
            {/* Mode Switcher */}
            <div className="flex p-1 rounded-xl bg-surface-base border border-surface-border justify-center">
              <button
                type="button"
                onClick={() => setExecutionMode('TEST_MODE')}
                className={`flex-1 sm:flex-initial px-2.5 sm:px-3 py-1.5 rounded-lg text-[11px] sm:text-xs font-mono font-semibold transition-all cursor-pointer text-center ${
                  executionMode === 'TEST_MODE'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                🟢 Razorpay Test Mode
              </button>
              <button
                type="button"
                onClick={() => setExecutionMode('SIMULATION_MODE')}
                className={`flex-1 sm:flex-initial px-2.5 sm:px-3 py-1.5 rounded-lg text-[11px] sm:text-xs font-mono font-semibold transition-all cursor-pointer text-center ${
                  executionMode === 'SIMULATION_MODE'
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                🟣 Simulation Sandbox
              </button>
            </div>

            <button
              type="button"
              onClick={handleRunScenario}
              disabled={running}
              className="px-5 sm:px-6 py-2.5 sm:py-3 rounded-xl bg-gradient-to-r from-brand-600 to-emerald-500 hover:from-brand-500 hover:to-emerald-400 text-white font-bold text-xs sm:text-sm shadow-xl shadow-brand-500/25 flex items-center justify-center gap-2 transition-all transform active:scale-95 disabled:opacity-50 shrink-0 cursor-pointer w-full sm:w-auto"
            >
              <Play className={`h-4 w-4 fill-white ${running ? 'animate-spin' : ''}`} />
              <span>{running ? 'Executing Recovery Pipeline...' : `Run Scenario: ${selectedScenario.badge}`}</span>
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3.5 sm:p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 flex items-center gap-3 text-xs sm:text-sm">
          <XCircle className="h-5 w-5 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Scenario Selector Grid */}
      <div>
        <div className="flex items-center justify-between mb-2.5 sm:mb-3">
          <h3 className="text-[11px] sm:text-xs font-mono uppercase tracking-wider text-slate-400">
            CHOOSE RECOVERY SCENARIO (CLICK TO SELECT)
          </h3>
          <span className="text-[11px] font-mono text-emerald-400 font-semibold flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Selected: {selectedScenario.badge}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 sm:gap-3">
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
                    ? 'border-brand-400/80 bg-brand-950/40 ring-2 ring-brand-500/50 shadow-lg shadow-brand-500/20'
                    : 'border-surface-border hover:border-slate-600 hover:bg-surface-card'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5">
                    <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full border ${s.badgeColor}`}>
                      {s.badge}
                    </span>
                    {isSelected && (
                      <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                        ✓ SELECTED
                      </span>
                    )}
                  </div>
                  <span className="text-sm font-bold text-white">
                    ₹{s.amount.toLocaleString('en-IN')}
                  </span>
                </div>
                <h4 className={`font-semibold text-sm transition-colors ${isSelected ? 'text-brand-300' : 'text-slate-100'}`}>
                  {s.title}
                </h4>
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

      {/* Currently Selected Scenario Detail Banner */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-brand-950/40 via-surface-card to-blue-950/30 border border-brand-500/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg shadow-brand-500/10">
        <div className="flex items-start sm:items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-brand-400 shrink-0 mt-0.5 sm:mt-0">
            <CheckCircle2 className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                ACTIVE SELECTION:
              </span>
              <span className="text-xs font-mono font-bold text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/30">
                {selectedScenario.badge}
              </span>
              <span className="text-xs font-bold text-white">
                ₹{selectedScenario.amount.toLocaleString('en-IN')} ({selectedScenario.method})
              </span>
              <span className="text-[10px] font-mono text-rose-300 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/30">
                {selectedScenario.reason}
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1">
              <strong className="text-white">{selectedScenario.title}:</strong> {selectedScenario.subtitle}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleRunScenario}
          disabled={running}
          className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-md shadow-brand-500/30 transition-all shrink-0 cursor-pointer w-full sm:w-auto"
        >
          <Play className={`h-3.5 w-3.5 fill-white ${running ? 'animate-spin' : ''}`} />
          <span>{running ? 'Running...' : 'Execute Now'}</span>
        </button>
      </div>

      {/* Live 7-Step Pipeline Stepper */}
      <div className="p-4 sm:p-6 rounded-2xl glass-panel border border-surface-border space-y-4 sm:space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-brand-400" />
            <h3 className="text-sm sm:text-base font-bold text-white">7-Step Visual Recovery Pipeline</h3>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Mode:</span>
            <span className={`px-2 py-0.5 rounded font-semibold border ${
              executionMode === 'TEST_MODE'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : 'bg-purple-500/20 text-purple-300 border-purple-500/40'
            }`}>
              {executionMode === 'TEST_MODE' ? 'Razorpay Test Mode' : 'Simulation Sandbox'}
            </span>
          </div>
        </div>

        {/* 7 Stepper Progress Nodes */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {[
            { step: 1, label: '1. PAYMENT', desc: `₹${selectedScenario.amount.toLocaleString('en-IN')}` },
            { step: 2, label: '2. FAILURE', desc: selectedScenario.reason },
            { step: 3, label: '3. AI ANALYSIS', desc: 'Context & History' },
            { step: 4, label: '4. RECOVERY DECISION', desc: 'Probability Est.' },
            { step: 5, label: '5. POLICY CHECK', desc: 'Safety Guardrails' },
            { step: 6, label: '6. ACTION', desc: executionMode === 'TEST_MODE' ? 'Razorpay API' : 'Simulated Action' },
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
                  <div className="flex flex-wrap items-center gap-2">
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
                      result.mode === 'TEST_MODE'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                    }`}>
                      {result.mode === 'TEST_MODE' ? 'Razorpay Test Mode' : 'SIMULATED RECOVERY'}
                    </span>
                    {result.ai_analysis.model_used && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30">
                        {result.ai_analysis.model_used}
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-slate-200 mt-1.5">
                    {result.recovery_result.message}
                  </p>
                </div>
              </div>

              {result.recovery_result.recovered_amount > 0 && (
                <div className="p-3 rounded-xl bg-surface-base border border-emerald-500/30 text-right shrink-0">
                  <span className="text-[11px] font-mono text-slate-400 uppercase block">
                    {result.mode === 'TEST_MODE' ? 'Revenue Captured' : 'Simulated Revenue'}
                  </span>
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
            <p className="font-medium text-slate-300">Ready to execute autonomous recovery</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Select any recovery scenario above and click <strong className="text-white">"Run Scenario"</strong> to evaluate the live recovery pipeline.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
