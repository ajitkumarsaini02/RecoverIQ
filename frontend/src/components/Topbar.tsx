import React, { useState } from 'react';
import { ShieldCheck, Cpu, Zap, RefreshCw, Menu, X, Info } from 'lucide-react';
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
  const isFallback = status?.integrations.ai_engine.mode?.includes('FALLBACK') || !isAiLive;
  const [showGuardrailTooltip, setShowGuardrailTooltip] = useState(false);

  return (
    <header className="h-16 border-b border-surface-border bg-surface-card/95 backdrop-blur-md px-3 sm:px-6 flex items-center justify-between sticky top-0 z-40">
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

        {/* Logo & Brand Title */}
        <button 
          onClick={onLogoClick}
          className="flex items-center gap-2.5 sm:gap-3 text-left group focus:outline-none transition-all active:scale-95 cursor-pointer"
          title="RecoverIQ Home"
        >
          <div className="h-8 w-8 sm:h-9 sm:w-9 rounded-xl bg-gradient-to-tr from-brand-600 to-blue-600 flex items-center justify-center shadow-md shadow-brand-500/20 group-hover:shadow-brand-500/40 transition-shadow shrink-0">
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
              AI Payment Recovery Platform
            </p>
          </div>
        </button>
      </div>

      {/* Integration Badges & Header Controls */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* 1. Razorpay Test Mode Badge (Unmistakable Test Indicator) */}
        <div 
          className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-lg bg-surface-base border border-surface-border text-[11px] font-mono"
          title="Razorpay Test Environment: Simulated transactions only. Real accounts will never be charged."
        >
          <span className={`h-2 w-2 rounded-full shrink-0 ${isRzpLive ? 'bg-emerald-400 animate-pulse' : 'bg-blue-400'}`} />
          <span className="text-slate-400 hidden lg:inline">GATEWAY:</span>
          <span className="font-semibold text-emerald-400">
            RAZORPAY · TEST MODE
          </span>
        </div>

        {/* 2. AI Engine State Badge */}
        <div 
          className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-lg bg-surface-base border border-surface-border text-[11px] font-mono"
          title={isFallback ? 'Running on deterministic heuristic fallback' : 'Connected to live Gemini AI'}
        >
          <Cpu className="h-3.5 w-3.5 text-purple-400 shrink-0" />
          <span className="text-slate-400 hidden xl:inline">AI:</span>
          <span className={`font-semibold ${isFallback ? 'text-amber-300' : 'text-purple-300'}`}>
            {isFallback ? 'FALLBACK · Heuristic' : `LIVE AI · ${(status?.integrations.ai_engine.provider || 'Gemini').toUpperCase()}`}
          </span>
        </div>

        {/* 3. Policy Guardrails Active Popover / Tooltip */}
        <div className="relative hidden sm:block">
          <button
            type="button"
            onClick={() => setShowGuardrailTooltip(!showGuardrailTooltip)}
            onMouseEnter={() => setShowGuardrailTooltip(true)}
            onMouseLeave={() => setShowGuardrailTooltip(false)}
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-lg bg-brand-950/40 border border-brand-800/50 text-[11px] font-mono text-brand-300 hover:border-brand-500/60 transition-all cursor-pointer"
          >
            <ShieldCheck className="h-3.5 w-3.5 text-brand-400" />
            <span className="font-semibold">GUARDRAILS ACTIVE</span>
            <Info className="h-3 w-3 text-brand-400/80" />
          </button>

          {showGuardrailTooltip && (
            <div className="absolute right-0 top-full mt-2 w-72 p-3.5 rounded-xl bg-[#0d1424] border border-brand-500/40 shadow-2xl z-50 text-xs text-slate-200 animate-fadeIn">
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-surface-border">
                <div className="flex items-center gap-1.5 font-bold text-brand-300 font-mono text-[11px]">
                  <ShieldCheck className="h-4 w-4 text-brand-400" />
                  <span>SAFETY GUARDRAILS ACTIVE</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-400 mb-2.5">
                Deterministic policy controls enforced before any external payment action can execute:
              </p>
              <ul className="space-y-1.5 text-[11px] font-mono">
                <li className="flex items-start gap-1.5">
                  <span className="text-brand-400 font-bold">•</span>
                  <span><strong className="text-white">Max Retries:</strong> 2 attempts per payment</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-brand-400 font-bold">•</span>
                  <span><strong className="text-white">High-Value Gate:</strong> Approval for &gt; ₹20,000</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-brand-400 font-bold">•</span>
                  <span><strong className="text-white">Probability Floor:</strong> Min 25% confidence</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-brand-400 font-bold">•</span>
                  <span><strong className="text-white">Repeated Failure Cap:</strong> Auto-stop chronic issues</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-brand-400 font-bold">•</span>
                  <span><strong className="text-white">Audit Logging:</strong> 100% immutable record</span>
                </li>
              </ul>
            </div>
          )}
        </div>

        {/* Refresh Status Button */}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-2 rounded-lg bg-surface-base border border-surface-border text-slate-400 hover:text-white hover:border-slate-600 transition-colors shrink-0 cursor-pointer"
          title="Refresh Integration Health"
          aria-label="Refresh Status"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-brand-400' : ''}`} />
        </button>
      </div>
    </header>
  );
};
