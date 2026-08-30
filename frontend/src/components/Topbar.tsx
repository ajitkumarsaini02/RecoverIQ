import React from 'react';
import { ShieldCheck, Cpu, Database, Zap, RefreshCw } from 'lucide-react';
import { SystemStatus } from '../types';

interface TopbarProps {
  status: SystemStatus | null;
  loading: boolean;
  onRefresh: () => void;
  onLogoClick?: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ status, loading, onRefresh, onLogoClick }) => {
  const isRzpLive = status?.integrations.razorpay.configured;
  const isAiLive = status?.integrations.ai_engine.configured;

  return (
    <header className="h-16 border-b border-surface-border bg-surface-card/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      <button 
        onClick={onLogoClick}
        className="flex items-center gap-3 text-left group focus:outline-none transition-all active:scale-95 cursor-pointer"
        title="Go to Home / Playground"
      >
        <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-brand-600 to-blue-600 flex items-center justify-center shadow-lg shadow-brand-500/20 group-hover:shadow-brand-500/40 transition-shadow">
          <Zap className="h-5 w-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5 group-hover:text-brand-300 transition-colors">
              Recover<span className="text-brand-400">IQ</span>
            </h1>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-300 border border-brand-500/30 font-semibold tracking-wider">
              ENTERPRISE
            </span>
          </div>
          <p className="text-xs text-slate-400 group-hover:text-slate-300 transition-colors">Razorpay AI Revenue Recovery Engine</p>
        </div>
      </button>

      {/* Integration Badges */}
      <div className="flex items-center gap-3">
        {/* Razorpay Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-base border border-surface-border text-xs font-mono">
          <span className={`h-2 w-2 rounded-full ${isRzpLive ? 'bg-emerald-400 animate-pulse' : 'bg-blue-400'}`} />
          <span className="text-slate-400">Razorpay:</span>
          <span className={isRzpLive ? 'text-emerald-400 font-semibold' : 'text-blue-400 font-semibold'}>
            {status?.integrations.razorpay.mode === 'TEST_MODE' ? 'TEST MODE' : 'SIMULATION MODE'}
          </span>
        </div>

        {/* AI Agent Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-base border border-surface-border text-xs font-mono">
          <Cpu className="h-3.5 w-3.5 text-purple-400" />
          <span className="text-slate-400">AI:</span>
          <span className={isAiLive ? 'text-purple-300 font-semibold' : 'text-emerald-400 font-semibold'}>
            {isAiLive ? status?.integrations.ai_engine.provider.toUpperCase() : 'RULE ENGINE (ONLINE)'}
          </span>
        </div>

        {/* DB Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-base border border-surface-border text-xs font-mono hidden md:flex">
          <Database className="h-3.5 w-3.5 text-slate-400" />
          <span className="text-slate-400">DB:</span>
          <span className="text-emerald-400 font-semibold">SQLITE</span>
        </div>

        {/* Policy Guardrails Active Indicator */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-brand-950/40 border border-brand-800/40 text-xs font-mono text-brand-400 hidden lg:flex">
          <ShieldCheck className="h-3.5 w-3.5 text-brand-400" />
          <span>GUARDRAILS: ACTIVE</span>
        </div>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-2 rounded-lg bg-surface-base border border-surface-border text-slate-400 hover:text-white hover:border-slate-600 transition-colors"
          title="Refresh Status"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-brand-400' : ''}`} />
        </button>
      </div>
    </header>
  );
};
