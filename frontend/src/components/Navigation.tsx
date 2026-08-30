import React from 'react';
import { 
  Play, 
  LayoutDashboard, 
  Receipt, 
  CheckCircle2, 
  History, 
  Sparkles, 
  Settings
} from 'lucide-react';

export type NavTab = 
  | 'playground' 
  | 'dashboard' 
  | 'transactions' 
  | 'approvals' 
  | 'audit' 
  | 'simulation' 
  | 'settings';

interface NavigationProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  pendingApprovalsCount?: number;
}

export const Navigation: React.FC<NavigationProps> = ({ 
  activeTab, 
  onSelectTab, 
  pendingApprovalsCount = 0 
}) => {
  const navItems = [
    {
      id: 'playground' as NavTab,
      label: 'Autonomous Recovery',
      icon: Play,
      description: 'Intelligent payment recovery pipeline'
    },
    {
      id: 'dashboard' as NavTab,
      label: 'Dashboard',
      icon: LayoutDashboard,
      description: 'KPIs & recovery analytics'
    },
    {
      id: 'transactions' as NavTab,
      label: 'Transactions',
      icon: Receipt,
      description: 'Merchant payment ledger'
    },
    {
      id: 'approvals' as NavTab,
      label: 'Approval Queue',
      icon: CheckCircle2,
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount.toString() : undefined,
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse',
      description: 'Human-in-the-loop guardrail queue'
    },
    {
      id: 'simulation' as NavTab,
      label: 'Recovery Analytics',
      icon: Sparkles,
      description: 'Portfolio batch recovery evaluation'
    },
    {
      id: 'audit' as NavTab,
      label: 'Audit Trail',
      icon: History,
      description: 'Immutable decision logs'
    },
    {
      id: 'settings' as NavTab,
      label: 'System & Keys',
      icon: Settings,
      description: 'Gateway & engine configuration'
    },
  ];

  return (
    <aside className="w-64 border-r border-surface-border bg-surface-card/60 backdrop-blur-md flex flex-col justify-between shrink-0 p-4 min-h-[calc(100vh-4rem)]">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
          Core Workflows
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                isActive
                  ? 'bg-gradient-to-r from-brand-600/20 to-blue-600/10 text-white border border-brand-500/30 shadow-sm shadow-brand-500/10'
                  : 'text-slate-300 hover:text-white hover:bg-surface-highlight/50'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon
                  className={`h-4 w-4 transition-colors ${
                    isActive ? 'text-brand-400' : 'text-slate-400 group-hover:text-slate-200'
                  }`}
                />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded-md border font-semibold ${
                    item.badgeColor || 'bg-surface-base text-slate-400 border-surface-border'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer info */}
      <div className="p-3 rounded-xl bg-surface-base/80 border border-surface-border/60 text-xs space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Gateway:</span>
          <span className="font-semibold text-slate-200">Razorpay</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Engine:</span>
          <span className="text-brand-400 font-semibold">Autonomous v1.0</span>
        </div>
      </div>
    </aside>
  );
};
