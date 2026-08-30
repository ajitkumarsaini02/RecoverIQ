import React, { useState } from 'react';
import { 
  Key, 
  Cpu, 
  ShieldCheck, 
  RefreshCw, 
  CheckCircle2
} from 'lucide-react';
import { SystemStatus } from '../types';

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
      const res = await fetch('/api/health');
      setPingSuccess(res.ok);
      onRefresh();
    } catch {
      setPingSuccess(false);
    } finally {
      setTestingPing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white">System & Integration Status</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-brand-500/20 text-brand-300 border border-brand-500/30">
              ENVIRONMENT: {status?.mode || 'TEST MODE / DEMO'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Integration configuration for Razorpay Test Mode, AI Reasoning Layer, and Database.
          </p>
        </div>

        <button
          onClick={handleTestPing}
          disabled={testingPing}
          className="px-4 py-2 rounded-xl bg-surface-card border border-surface-border text-xs font-mono text-slate-200 hover:text-white hover:border-slate-600 transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${testingPing ? 'animate-spin text-brand-400' : ''}`} />
          <span>{testingPing ? 'Testing...' : 'Test Backend Connection'}</span>
        </button>
      </div>

      {pingSuccess === true && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-emerald-300 flex items-center gap-2 text-xs">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>Backend health check successful: 200 OK</span>
        </div>
      )}

      {/* 3 Main Integration Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Razorpay Integration */}
        <div className="p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Key className="h-5 w-5 text-razorpay-accent" />
              <h3 className="text-sm font-bold text-white">Razorpay Test Mode</h3>
            </div>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
              status?.integrations.razorpay.configured
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                : 'bg-blue-500/20 text-blue-400 border-blue-500/30'
            }`}>
              {status?.integrations.razorpay.mode}
            </span>
          </div>

          <div className="space-y-2 text-xs text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-400">Key ID:</span>
              <span className="font-mono text-slate-200">{status?.integrations.razorpay.key_id_masked || 'SIMULATED'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Environment:</span>
              <span className="font-semibold text-emerald-400">TEST MODE ONLY</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Safety Guard:</span>
              <span className="text-slate-300">Never uses real money</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-base border border-surface-border text-[11px] text-slate-400">
            To use official Razorpay Test Mode keys, specify <code>RAZORPAY_KEY_ID</code> and <code>RAZORPAY_KEY_SECRET</code> in <code>backend/.env</code>.
          </div>
        </div>

        {/* AI Agent Engine */}
        <div className="p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-purple-400" />
              <h3 className="text-sm font-bold text-white">AI Reasoning Agent</h3>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
              {status?.integrations.ai_engine.mode || 'ONLINE'}
            </span>
          </div>

          <div className="space-y-2 text-xs text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-400">Engine Type:</span>
              <span className="font-semibold text-purple-300">{status?.integrations.ai_engine.provider.toUpperCase()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Schema Validation:</span>
              <span className="font-mono text-brand-400">Pydantic v2</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Fallback Heuristics:</span>
              <span className="text-emerald-400 font-semibold">100% Uptime Ready</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-base border border-surface-border text-[11px] text-slate-400">
            Deterministic domain fallback guarantees 100% agent reliability even if third-party LLM APIs are offline.
          </div>
        </div>

        {/* Policy Engine & Guardrails */}
        <div className="p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-brand-400" />
              <h3 className="text-sm font-bold text-white">Policy Engine Guardrails</h3>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30">
              ENFORCED
            </span>
          </div>

          <div className="space-y-2 text-xs text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-400">Max Auto Retries:</span>
              <span className="font-bold text-white font-mono">2 Attempts</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">High-Value Gate:</span>
              <span className="font-bold text-amber-300 font-mono">&gt; ₹20,000</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Min Prob Floor:</span>
              <span className="font-bold text-white font-mono">25% (0.25)</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-base border border-surface-border text-[11px] text-slate-400">
            All AI decisions are bounded, explainable, and gated before any payment action executes.
          </div>
        </div>
      </div>
    </div>
  );
};
