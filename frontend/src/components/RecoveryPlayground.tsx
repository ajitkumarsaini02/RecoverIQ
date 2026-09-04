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
  ArrowRight 
} from 'lucide-react';
import { runDemoScenario } from '../services/api';
import { DemoScenarioResult } from '../types';

interface PresetScenarioCard {
  id: string;
  category: string;
  title: string;
  subtitle: string;
  amount: number;
  method: string;
  reason: string;
  previewAction: string;
  previewProbability: number;
  previewRisk: 'LOW' | 'MEDIUM' | 'HIGH';
  previewPolicy: 'APPROVED' | 'BLOCKED' | 'APPROVAL REQUIRED';
  previewApproval: boolean;
  previewRetries: string;
  badgeColor: string;
}

const PRESET_SCENARIOS: PresetScenarioCard[] = [
  {
    id: 'temporary_upi_failure',
    category: 'UPI LATENCY',
    title: 'Temporary UPI Failure',
    subtitle: 'Transient PSP network timeout during checkout payment routing.',
    amount: 4999,
    method: 'UPI',
    reason: 'UPI_TIMEOUT',
    previewAction: 'RETRY_PAYMENT',
    previewProbability: 91,
    previewRisk: 'LOW',
    previewPolicy: 'APPROVED',
    previewApproval: false,
    previewRetries: '0 / 2',
    badgeColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
  },
  {
    id: 'bank_decline',
    category: 'ISSUER DECLINE',
    title: 'Bank Issuer Decline',
    subtitle: 'Issuing bank refused authorization on card charge attempt.',
    amount: 2499,
    method: 'CARD',
    reason: 'BANK_DECLINED',
    previewAction: 'ALTERNATIVE_PAYMENT_METHOD',
    previewProbability: 76,
    previewRisk: 'LOW',
    previewPolicy: 'APPROVED',
    previewApproval: false,
    previewRetries: '0 / 2',
    badgeColor: 'bg-blue-500/10 text-blue-300 border-blue-500/30'
  },
  {
    id: 'network_failure',
    category: 'GATEWAY TIMEOUT',
    title: 'Gateway Network Failure',
    subtitle: 'Transient TCP/SSL handshake interruption during gateway routing.',
    amount: 999,
    method: 'UPI',
    reason: 'NETWORK_ERROR',
    previewAction: 'RETRY_PAYMENT',
    previewProbability: 88,
    previewRisk: 'LOW',
    previewPolicy: 'APPROVED',
    previewApproval: false,
    previewRetries: '0 / 2',
    badgeColor: 'bg-purple-500/10 text-purple-300 border-purple-500/30'
  },
  {
    id: 'insufficient_funds',
    category: 'INSUFFICIENT FUNDS',
    title: 'Insufficient Funds',
    subtitle: 'Customer balance insufficient for order; direct retry is unsafe.',
    amount: 14999,
    method: 'NETBANKING',
    reason: 'INSUFFICIENT_FUNDS',
    previewAction: 'PAYMENT_LINK',
    previewProbability: 68,
    previewRisk: 'MEDIUM',
    previewPolicy: 'APPROVED',
    previewApproval: false,
    previewRetries: '0 / 2',
    badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/30'
  },
  {
    id: 'repeated_failure',
    category: 'RETRY CEILING',
    title: 'Repeated Payment Failure',
    subtitle: 'Customer already failed twice previously; ceiling limit reached.',
    amount: 4999,
    method: 'CARD',
    reason: 'BANK_DECLINED',
    previewAction: 'STOP',
    previewProbability: 12,
    previewRisk: 'HIGH',
    previewPolicy: 'BLOCKED',
    previewApproval: false,
    previewRetries: '2 / 2',
    badgeColor: 'bg-rose-500/10 text-rose-300 border-rose-500/30'
  },
  {
    id: 'high_value_transaction',
    category: 'HIGH-VALUE GATE',
    title: 'High-Value Payment',
    subtitle: 'Large transaction exceeding ₹20,000 safety threshold.',
    amount: 49999,
    method: 'CARD',
    reason: 'BANK_DECLINED',
    previewAction: 'ALTERNATIVE_PAYMENT_METHOD',
    previewProbability: 82,
    previewRisk: 'LOW',
    previewPolicy: 'APPROVAL REQUIRED',
    previewApproval: true,
    previewRetries: '0 / 2',
    badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/30'
  },
];

export const RecoveryPlayground: React.FC = () => {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('temporary_upi_failure');
  const [executionMode, setExecutionMode] = useState<'TEST_MODE' | 'SIMULATION_MODE'>('TEST_MODE');
  const [running, setRunning] = useState<boolean>(false);
  const [loadingStage, setLoadingStage] = useState<string>('');
  const [result, setResult] = useState<DemoScenarioResult | null>(null);
  const [stepIndex, setStepIndex] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const selectedScenario = PRESET_SCENARIOS.find((s) => s.id === selectedScenarioId) || PRESET_SCENARIOS[0];

  const handleRunScenario = async () => {
    try {
      setRunning(true);
      setError(null);
      setResult(null);
      setStepIndex(1);
      setLoadingStage('Analyzing transaction context & history...');

      const stageTimer1 = setTimeout(() => {
        setStepIndex(2);
        setLoadingStage('Assessing recovery probability with AI agent...');
      }, 400);

      const stageTimer2 = setTimeout(() => {
        setStepIndex(3);
        setLoadingStage('Applying policy guardrails & safety rules...');
      }, 900);

      const stageTimer3 = setTimeout(() => {
        setStepIndex(4);
        setLoadingStage('Preparing recovery action & audit logging...');
      }, 1400);

      const scenarioToRun = selectedScenarioId || 'temporary_upi_failure';
      const data = await runDemoScenario(scenarioToRun, executionMode);

      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      clearTimeout(stageTimer3);

      setStepIndex(5);
      setResult(data);
      setRunning(false);
      setLoadingStage('');
    } catch (err: any) {
      console.error('[RecoverIQ] Scenario execution failed:', err);
      setError(err.message || 'Unable to connect to RecoverIQ backend.');
      setRunning(false);
      setStepIndex(0);
      setLoadingStage('');
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Hero Section & Pipeline Visualization */}
      <div className="p-5 sm:p-6 rounded-2xl glass-panel relative overflow-hidden border border-surface-border">
        <div className="relative z-10 space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/30">
                  AUTONOMOUS RECOVERY
                </span>
                <span className="text-xs text-slate-400">Razorpay AI Revenue Engine</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                Recover failed payments with AI-driven decisions, policy guardrails and auditable recovery actions.
              </h2>
            </div>

            {/* Execution Mode Selector */}
            <div className="shrink-0">
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1">
                EXECUTION MODE
              </div>
              <div className="inline-flex p-1 rounded-xl bg-surface-base border border-surface-border">
                <button
                  type="button"
                  onClick={() => setExecutionMode('TEST_MODE')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer ${
                    executionMode === 'TEST_MODE'
                      ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Razorpay Test Mode
                </button>
                <button
                  type="button"
                  onClick={() => setExecutionMode('SIMULATION_MODE')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer ${
                    executionMode === 'SIMULATION_MODE'
                      ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Simulation Sandbox
                </button>
              </div>
            </div>
          </div>

          {/* Compact Enterprise Pipeline Visualization */}
          <div className="pt-3 border-t border-surface-border/70 flex flex-wrap items-center gap-2 sm:gap-3 text-xs font-mono text-slate-300">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
              Pipeline Flow:
            </span>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-base border border-surface-border text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
              <span>Detect</span>
            </div>
            <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-base border border-surface-border text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-purple-400" />
              <span>Analyze</span>
            </div>
            <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-base border border-surface-border text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span>Guardrail</span>
            </div>
            <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-base border border-surface-border text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
              <span>Recover</span>
            </div>
            <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-base border border-surface-border text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              <span>Audit</span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3.5 sm:p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 flex items-center gap-3 text-xs">
          <XCircle className="h-5 w-5 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 2. Scenario Cards Grid (3 × 2) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Select Recovery Scenario (3 × 2 Grid)
          </h3>
          <span className="text-[11px] font-mono text-slate-400">
            Click any card to preview AI & policy decisions
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
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
                className={`p-4 rounded-xl glass-card transition-all cursor-pointer relative ${
                  isSelected
                    ? 'border-emerald-500/70 bg-emerald-950/20 shadow-md shadow-emerald-500/10'
                    : 'border-surface-border hover:border-slate-600 hover:bg-surface-card'
                }`}
              >
                {/* Top Row: Category (Left) + ₹ Amount (Right) */}
                <div className="flex items-center justify-between gap-2 mb-2.5">
                  <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full border ${s.badgeColor}`}>
                    {s.category}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-bold text-white font-mono">
                      ₹{s.amount.toLocaleString('en-IN')}
                    </span>
                    {isSelected && (
                      <span className="h-2 w-2 rounded-full bg-emerald-400" title="Active selection" />
                    )}
                  </div>
                </div>

                {/* Scenario Title */}
                <h4 className={`text-sm font-semibold transition-colors ${isSelected ? 'text-emerald-300' : 'text-slate-100'}`}>
                  {s.title}
                </h4>

                {/* Human-Readable Explanation */}
                <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                  {s.subtitle}
                </p>

                {/* Bottom Row: Method (Left) + Technical Error Code (Right, secondary) */}
                <div className="mt-3 pt-2.5 border-t border-surface-border/60 flex items-center justify-between text-[11px] font-mono">
                  <span className="text-slate-400">Method: <strong className="text-slate-200">{s.method}</strong></span>
                  <span className="text-slate-400 text-[10px]">{s.reason}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. AI Decision Preview & Single Primary Action Panel */}
      <div className="p-5 rounded-2xl glass-panel border border-surface-border shadow-enterprise space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="h-4 w-4 text-purple-400" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
                AI DECISION PREVIEW
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                · {selectedScenario.title} (₹{selectedScenario.amount.toLocaleString('en-IN')})
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Evaluated against real merchant transaction data and deterministic policy guardrails.
            </p>
          </div>

          {/* SINGLE PRIMARY CTA BUTTON */}
          <div className="shrink-0">
            <button
              type="button"
              onClick={handleRunScenario}
              disabled={running}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-brand-500 hover:from-emerald-500 hover:to-brand-400 text-white font-bold text-xs sm:text-sm shadow-md shadow-brand-500/20 flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
            >
              <Play className={`h-4 w-4 fill-white ${running ? 'animate-spin' : ''}`} />
              <span>{running ? 'Evaluating Pipeline...' : 'Run Recovery Analysis'}</span>
            </button>
          </div>
        </div>

        {/* Dynamic Preview Matrix */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-2">
          {/* Item 1: Action */}
          <div className="p-3 rounded-xl bg-surface-base border border-surface-border">
            <span className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
              Action
            </span>
            <span className="text-xs font-mono font-bold text-purple-300 truncate block">
              {result ? result.ai_analysis.recommended_action : selectedScenario.previewAction}
            </span>
          </div>

          {/* Item 2: Probability */}
          <div className="p-3 rounded-xl bg-surface-base border border-surface-border">
            <span className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
              AI Probability
            </span>
            <span className="text-xs font-mono font-bold text-emerald-400 block">
              {result ? `${(result.ai_analysis.recovery_probability * 100).toFixed(0)}%` : `${selectedScenario.previewProbability}%`}
            </span>
          </div>

          {/* Item 3: Risk Level */}
          <div className="p-3 rounded-xl bg-surface-base border border-surface-border">
            <span className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
              Risk Level
            </span>
            {(() => {
              const risk = result ? result.ai_analysis.risk_level : selectedScenario.previewRisk;
              const color = risk === 'LOW' ? 'text-emerald-400' : risk === 'MEDIUM' ? 'text-amber-400' : 'text-rose-400';
              return <span className={`text-xs font-mono font-bold block ${color}`}>{risk} RISK</span>;
            })()}
          </div>

          {/* Item 4: Policy Gate */}
          <div className="p-3 rounded-xl bg-surface-base border border-surface-border">
            <span className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
              Policy Gate
            </span>
            {(() => {
              const allowed = result ? result.policy_decision.allowed : selectedScenario.previewPolicy !== 'BLOCKED';
              const reqApproval = result ? result.policy_decision.requires_human_approval : selectedScenario.previewApproval;
              if (reqApproval) {
                return <span className="text-xs font-mono font-bold text-amber-300 block">GATE REQUIRED</span>;
              }
              return allowed ? (
                <span className="text-xs font-mono font-bold text-emerald-400 block">APPROVED</span>
              ) : (
                <span className="text-xs font-mono font-bold text-rose-400 block">BLOCKED</span>
              );
            })()}
          </div>

          {/* Item 5: Retry Limit */}
          <div className="p-3 rounded-xl bg-surface-base border border-surface-border">
            <span className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
              Retry Count
            </span>
            <span className="text-xs font-mono font-bold text-slate-200 block">
              {result ? `${result.transaction.retry_count} / ${result.transaction.max_retries}` : selectedScenario.previewRetries}
            </span>
          </div>

          {/* Item 6: Human Sign-off */}
          <div className="p-3 rounded-xl bg-surface-base border border-surface-border">
            <span className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
              Human Sign-Off
            </span>
            {(() => {
              const needsSignOff = result ? result.policy_decision.requires_human_approval : selectedScenario.previewApproval;
              return needsSignOff ? (
                <span className="text-xs font-mono font-bold text-amber-300 block">REQUIRED</span>
              ) : (
                <span className="text-xs font-mono font-bold text-slate-400 block">AUTONOMOUS</span>
              );
            })()}
          </div>
        </div>

        {/* Chronological Loading Progress Sequence */}
        {running && (
          <div className="p-4 rounded-xl bg-surface-base border border-emerald-500/30 space-y-2 animate-fadeIn">
            <div className="flex items-center gap-2 text-xs font-mono text-emerald-300">
              <Activity className="h-4 w-4 animate-spin text-emerald-400" />
              <span className="font-semibold">{loadingStage}</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div 
                className="bg-emerald-400 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${(stepIndex / 5) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* 4. Execution Result & Diagnostic Breakdown */}
      {result && (
        <div className="space-y-4 animate-fadeIn">
          {/* Main Execution Result Banner */}
          <div className={`p-5 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
            result.recovery_result.status === 'SUCCESS'
              ? 'bg-emerald-950/30 border-emerald-800/60'
              : result.recovery_result.status === 'PENDING'
              ? 'bg-blue-950/30 border-blue-800/60'
              : result.recovery_result.status === 'PENDING_APPROVAL'
              ? 'bg-amber-950/30 border-amber-800/60'
              : 'bg-slate-900/60 border-slate-700'
          }`}>
            <div className="flex items-start gap-3.5">
              <div className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 ${
                result.recovery_result.status === 'SUCCESS'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : result.recovery_result.status === 'PENDING'
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : result.recovery_result.status === 'PENDING_APPROVAL'
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  : 'bg-slate-800 text-slate-400 border border-slate-700'
              }`}>
                {result.recovery_result.status === 'SUCCESS' ? (
                  <CheckCircle2 className="h-5 w-5" />
                ) : result.recovery_result.status === 'PENDING' ? (
                  <Clock className="h-5 w-5" />
                ) : result.recovery_result.status === 'PENDING_APPROVAL' ? (
                  <UserCheck className="h-5 w-5" />
                ) : (
                  <XCircle className="h-5 w-5" />
                )}
              </div>

              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
                    Execution State:
                  </span>
                  <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded-full border ${
                    result.recovery_result.status === 'SUCCESS'
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      : result.recovery_result.status === 'PENDING'
                      ? 'bg-blue-500/20 text-blue-300 border-blue-500/40'
                      : result.recovery_result.status === 'PENDING_APPROVAL'
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                      : 'bg-slate-800 text-slate-300 border-slate-700'
                  }`}>
                    {result.recovery_result.status}
                  </span>

                  <span className="text-[10px] font-mono px-2 py-0.5 rounded border font-semibold bg-surface-base text-slate-300 border-surface-border">
                    {result.mode === 'TEST_MODE' ? 'RAZORPAY TEST' : 'SIMULATION'}
                  </span>

                  {result.ai_analysis.fallback_used ? (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 font-semibold">
                      HEURISTIC_FALLBACK
                    </span>
                  ) : (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 font-semibold">
                      LIVE_LLM ({result.ai_analysis.model_used || 'gemini-3.8-flash'})
                    </span>
                  )}
                </div>

                <p className="text-xs font-medium text-slate-200 mt-1.5 leading-relaxed">
                  {result.recovery_result.message}
                </p>

                {/* Clear Financial Reality Note: Avoid falsely claiming revenue captured when test order is created */}
                {result.recovery_result.status === 'PENDING' && (
                  <p className="text-[11px] font-mono text-slate-400 mt-1">
                    Razorpay Test Order generated: <code className="text-slate-300">{result.recovery_result.razorpay_order_id || result.transaction.razorpay_order_id}</code>. Awaiting customer retry checkout.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* 3-Column Diagnostic Deep Dive */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Column 1: AI Agent Reasoning */}
            <div className="p-4 rounded-xl glass-card border border-surface-border space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-purple-400" />
                  <h4 className="text-xs font-bold text-purple-200 uppercase tracking-wider font-mono">
                    AI Agent Diagnosis
                  </h4>
                </div>
                <span className="text-[10px] font-mono text-slate-400">Pydantic v2</span>
              </div>

              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-slate-400 text-[11px] block">Diagnosis:</span>
                  <p className="font-semibold text-slate-200 mt-0.5">{result.ai_analysis.diagnosis}</p>
                </div>

                <div className="flex items-center justify-between p-2 rounded-lg bg-surface-base border border-surface-border">
                  <span className="text-slate-400 text-[11px]">Recovery Probability:</span>
                  <span className="font-bold text-emerald-400 font-mono text-xs">
                    {(result.ai_analysis.recovery_probability * 100).toFixed(1)}%
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 text-[11px] block">Recommended Action:</span>
                  <span className="inline-block mt-1 px-2 py-0.5 rounded font-mono text-xs font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30">
                    {result.ai_analysis.recommended_action}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 text-[11px] block">AI Rationale:</span>
                  <p className="text-slate-300 text-[11px] mt-0.5 leading-relaxed">{result.ai_analysis.reason}</p>
                </div>
              </div>
            </div>

            {/* Column 2: Policy Engine Gate */}
            <div className="p-4 rounded-xl glass-card border border-surface-border space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <h4 className="text-xs font-bold text-emerald-300 uppercase tracking-wider font-mono">
                    Policy Engine Gate
                  </h4>
                </div>
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                  result.policy_decision.allowed ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'
                }`}>
                  {result.policy_decision.allowed ? 'POLICY APPROVED' : 'POLICY BLOCKED'}
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-slate-400 text-[11px] block">Authorized Action:</span>
                  <span className="font-mono font-bold text-slate-200 mt-0.5 block">{result.policy_decision.action}</span>
                </div>

                <div className="p-2 rounded-lg bg-surface-base border border-surface-border">
                  <span className="text-slate-400 text-[11px] block mb-1">Safety Rules Evaluated:</span>
                  <ul className="space-y-1">
                    {result.policy_decision.rules_evaluated?.map((r, i) => (
                      <li key={i} className="flex items-center gap-1.5 text-[11px]">
                        {r.passed ? (
                          <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
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
                  <span className="text-slate-400 text-[11px] block">Evaluation Rationale:</span>
                  <p className="text-slate-300 text-[11px] mt-0.5">
                    {result.policy_decision.reasons?.[0] || 'Safety thresholds satisfied.'}
                  </p>
                </div>
              </div>
            </div>

            {/* Column 3: Customer Context */}
            <div className="p-4 rounded-xl glass-card border border-surface-border space-y-3">
              <div className="flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-blue-400" />
                <h4 className="text-xs font-bold text-blue-200 uppercase tracking-wider font-mono">
                  Customer & Payment Data
                </h4>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Customer:</span>
                  <span className="font-medium text-slate-200">{result.transaction.customer_name || 'Merchant Customer'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Customer LTV:</span>
                  <span className="font-bold text-emerald-400 font-mono">
                    ₹{(result.transaction.customer_lifetime_value || 0).toLocaleString('en-IN')}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Past History:</span>
                  <span className="font-mono text-slate-300">
                    <span className="text-emerald-400 font-bold">{result.transaction.previous_successful_payments}</span> Success / 
                    <span className="text-rose-400 font-bold ml-1">{result.transaction.previous_failed_payments}</span> Fail
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
                  <span className="font-mono text-slate-300 truncate max-w-[130px]">
                    {result.transaction.razorpay_order_id || 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Audit Timeline */}
          <div className="p-4 rounded-xl bg-surface-base border border-surface-border space-y-2.5">
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
                    <p className="text-slate-400 text-[10px] truncate">
                      Decision: <span className="text-slate-300">{event.decision}</span>
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
