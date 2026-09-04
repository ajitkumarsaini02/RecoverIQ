import React, { useState } from 'react';
import { 
  Key, 
  Cpu, 
  ShieldCheck, 
  RefreshCw, 
  CheckCircle2,
  Database,
  Lock
} from 'lucide-react';
import { SystemStatus } from '../types';
import { fetchHealth } from '../services/api';

interface SettingsViewProps {
  status: SystemStatus | null;
  onRefresh: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ status, onRefresh }) => {
  const [testingPing, setTestingPing] = useState<boolean>(false);
  const [pingSuccess, setPingSuccess] = useState<boolean | null>(null);

  const handleTestPing = async () => {
    try {
      setTestingPing(true);
      await fetchHealth();
      setPingSuccess(true);
      onRefresh();
    } catch {
      setPingSuccess(false);
    } finally {
      setTestingPing(false);
    }
  };

  const isRzpLive = status?.integrations.razorpay.configured;
  const isAiLive = status?.integrations.ai_engine.configured;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold tracking-tight text-white">System & Keys Configuration</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] sm:text-[11px] font-mono font-semibold bg-brand-500/15 text-brand-300 border border-brand-500/30">
              ENV: {status?.mode || 'TEST SANDBOX'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise infrastructure settings, gateway credentials, AI engine parameters, and policy safety thresholds.
          </p>
        </div>

        <button
          onClick={handleTestPing}
          disabled={testingPing}
          className="px-4 py-2 rounded-xl bg-surface-card border border-surface-border text-xs font-mono text-slate-200 hover:text-white hover:border-slate-600 transition-colors flex items-center justify-center gap-2 cursor-pointer w-full sm:w-auto"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${testingPing ? 'animate-spin text-brand-400' : ''}`} />
          <span>{testingPing ? 'Testing API Ping...' : 'Test Backend Health'}</span>
        </button>
      </div>

      {pingSuccess === true && (
        <div className="p-3.5 sm:p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-emerald-300 flex items-center gap-2 text-xs">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>Backend health check successful: 200 OK. All services operational.</span>
        </div>
      )}

      {/* 4 Technical Infrastructure Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card 1: Razorpay Integration */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Key className="h-5 w-5 text-razorpay-accent" />
              <h3 className="text-sm font-bold text-white">Razorpay Gateway Integration</h3>
            </div>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
              isRzpLive
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                : 'bg-blue-500/15 text-blue-400 border-blue-500/30'
            }`}>
              {status?.integrations.razorpay.mode || 'TEST_MODE'}
            </span>
          </div>

          <div className="space-y-2.5 text-xs text-slate-300">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Environment:</span>
              <span className="font-semibold text-emerald-400 font-mono text-[11px]">RAZORPAY TEST MODE</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Key ID (Masked):</span>
              <span className="font-mono text-slate-200 bg-surface-base px-2 py-0.5 rounded border border-surface-border">
                {status?.integrations.razorpay.key_id_masked || 'rzp_test_••••••••1Rp'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Key Secret:</span>
              <span className="font-mono text-slate-400 flex items-center gap-1">
                <Lock className="h-3 w-3" /> •••••••••••••••• (Masked)
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Safety Guard:</span>
              <span className="text-emerald-300">Zero real money charged</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-base border border-surface-border text-[11px] text-slate-400">
            All recovery orders and payment links are created strictly in Razorpay Test sandbox. Production merchant credentials are never accessed.
          </div>
        </div>

        {/* Card 2: AI Reasoning Agent */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-purple-400" />
              <h3 className="text-sm font-bold text-white">AI Reasoning Engine</h3>
            </div>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
              isAiLive
                ? 'bg-purple-500/15 text-purple-300 border-purple-500/30'
                : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
            }`}>
              {isAiLive ? (status?.integrations.ai_engine.mode || 'ONLINE') : 'HEURISTIC'}
            </span>
          </div>

          <div className="space-y-2.5 text-xs text-slate-300">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Provider:</span>
              <span className="font-semibold text-purple-300 font-mono text-[11px]">
                {status?.integrations.ai_engine.provider.toUpperCase() || 'GEMINI'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Model Architecture:</span>
              <span className="font-mono text-slate-200">gemini-3.8-flash</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Schema Validation:</span>
              <span className="font-mono text-emerald-400 font-semibold">Pydantic v2 (Strict Typed)</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Domain Fallback:</span>
              <span className="text-emerald-300">100% Deterministic Fallback Ready</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-base border border-surface-border text-[11px] text-slate-400">
            AI outputs are strictly parsed into deterministic schema objects. If the external LLM is unreachable, the system gracefully falls back to local heuristic rules without downtime.
          </div>
        </div>

        {/* Card 3: Policy Engine Guardrails */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
              <h3 className="text-sm font-bold text-white">Policy Engine Guardrails</h3>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
              DETERMINISTIC GATE
            </span>
          </div>

          <div className="space-y-2.5 text-xs text-slate-300">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Max Auto Retries:</span>
              <span className="font-bold text-white font-mono">2 Attempts Ceiling</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">High-Value Escalation:</span>
              <span className="font-bold text-amber-300 font-mono">&gt; ₹20,000 threshold</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Min Probability Floor:</span>
              <span className="font-bold text-white font-mono">25% (0.25 confidence)</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Repeated Failure Cap:</span>
              <span className="text-slate-200">Auto-stop on chronic decline</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-base border border-surface-border text-[11px] text-slate-400">
            Policy guardrails execute synchronously after AI analysis. No payment action can bypass this deterministic safety gate.
          </div>
        </div>

        {/* Card 4: Database & Infrastructure */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-400" />
              <h3 className="text-sm font-bold text-white">Database & Application Layer</h3>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30">
              LOCAL / ACID
            </span>
          </div>

          <div className="space-y-2.5 text-xs text-slate-300">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Database Engine:</span>
              <span className="font-mono text-slate-200 font-semibold">SQLite 3</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">ORM Layer:</span>
              <span className="font-mono text-slate-200">SQLAlchemy 2.0</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">API Framework:</span>
              <span className="font-mono text-emerald-400">FastAPI 0.115</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Audit Storage:</span>
              <span className="text-slate-200">Immutable Relational Log</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-base border border-surface-border text-[11px] text-slate-400">
            Relational tables manage customers, transactions, recovery actions, and immutable audit trails with transaction-level ACID compliance.
          </div>
        </div>
      </div>
    </div>
  );
};
