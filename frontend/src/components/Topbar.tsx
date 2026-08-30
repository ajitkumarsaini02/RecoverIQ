import React from 'react';
import { ShieldCheck, Cpu, Database, Zap, RefreshCw, Menu, X } from 'lucide-react';
import { SystemStatus } from '../types';

interface TopbarProps {
  status: SystemStatus | null;
  loading: boolean;
  onRefresh: () => void;
  onLogoClick?: () => void;
  mobileMenuOpen?: boolean;
  onToggleMobileMenu?: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ 
  status, 
  loading, 
  onRefresh, 
  onLogoClick,
  mobileMenuOpen,
  onToggleMobileMenu
}) => {
  const isRzpLive = status?.integrations.razorpay.configured;
  const isAiLive = status?.integrations.ai_engine.configured;

  return (
    <header className="h-16 border-b border-surface-border bg-surface-card/90 backdrop-blur-md px-3 sm:px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Mobile Hamburger Toggle Button */}
        <button
          type="button"
          onClick={onToggleMobileMenu}
          className="md:hidden p-2 rounded-lg bg-surface-base border border-surface-border text-slate-300 hover:text-white transition-colors cursor-pointer"
          title="Toggle Navigation Menu"
          aria-label="Toggle Navigation Menu"
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>

        {/* Logo & Title */}
        <button 
          onClick={onLogoClick}
          className="flex items-center gap-2.5 sm:gap-3 text-left group focus:outline-none transition-all active:scale-95 cursor-pointer"
          title="Go to Home / Playground"
        >
          <div className="h-8 w-8 sm:h-9 sm:w-9 rounded-xl bg-gradient-to-tr from-brand-600 to-blue-600 flex items-center justify-center shadow-lg shadow-brand-500/20 group-hover:shadow-brand-500/40 transition-shadow shrink-0">
            <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 sm:gap-2">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-white flex items-center gap-1 group-hover:text-brand-300 transition-colors">
                Recover<span className="text-brand-400">IQ</span>
              </h1>
              <span className="text-[9px] sm:text-[10px] uppercase font-mono px-1.5 sm:px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-300 border border-brand-500/30 font-semibold tracking-wider">
                ENTERPRISE
              </span>
            </div>
            <p className="text-[10px] sm:text-xs text-slate-400 group-hover:text-slate-300 transition-colors hidden xs:block">
              Razorpay AI Recovery Engine
            </p>
          </div>
        </button>
      </div>

      {/* Integration Badges */}
      <div className="flex items-center gap-1.5 sm:gap-3">
        {/* Razorpay Badge */}
        <div className="flex items-center gap-1.5 px-2 sm:px-3 py-1 rounded-lg bg-surface-base border border-surface-border text-[10px] sm:text-xs font-mono">
          <span className={`h-2 w-2 rounded-full shrink-0 ${isRzpLive ? 'bg-emerald-400 animate-pulse' : 'bg-blue-400'}`} />
          <span className="text-slate-400 hidden sm:inline">Razorpay:</span>
          <span className={isRzpLive ? 'text-emerald-400 font-semibold' : 'text-blue-400 font-semibold'}>
            {status?.integrations.razorpay.mode === 'TEST_MODE' ? 'TEST' : 'SIM'}
          </span>
        </div>

        {/* AI Agent Badge */}
        <div className="flex items-center gap-1.5 px-2 sm:px-3 py-1 rounded-lg bg-surface-base border border-surface-border text-[10px] sm:text-xs font-mono">
          <Cpu className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-purple-400 shrink-0" />
          <span className="text-slate-400 hidden sm:inline">AI:</span>
          <span className={isAiLive ? 'text-purple-300 font-semibold' : 'text-emerald-400 font-semibold'}>
            {isAiLive ? (status?.integrations.ai_engine.provider || 'GEMINI').toUpperCase() : 'HEURISTIC'}
          </span>
        </div>

        {/* DB Badge (Desktop only) */}
        <div className="items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-base border border-surface-border text-xs font-mono hidden xl:flex">
          <Database className="h-3.5 w-3.5 text-slate-400" />
          <span className="text-slate-400">DB:</span>
          <span className="text-emerald-400 font-semibold">SQLITE</span>
        </div>

        {/* Policy Guardrails Active Indicator (Desktop only) */}
        <div className="items-center gap-1.5 px-3 py-1 rounded-lg bg-brand-950/40 border border-brand-800/40 text-xs font-mono text-brand-400 hidden lg:flex">
          <ShieldCheck className="h-3.5 w-3.5 text-brand-400" />
          <span>GUARDRAILS</span>
        </div>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-1.5 sm:p-2 rounded-lg bg-surface-base border border-surface-border text-slate-400 hover:text-white hover:border-slate-600 transition-colors shrink-0 cursor-pointer"
          title="Refresh Status"
        >
          <RefreshCw className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${loading ? 'animate-spin text-brand-400' : ''}`} />
        </button>
      </div>
    </header>
  );
};
