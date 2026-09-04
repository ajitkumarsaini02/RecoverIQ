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
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItemConfig {
  id: NavTab;
  label: string;
  icon: React.ElementType;
  badge?: string;
  badgeColor?: string;
  isPrimary?: boolean;
}

export const Navigation: React.FC<NavigationProps> = ({ 
  activeTab, 
  onSelectTab, 
  pendingApprovalsCount = 0,
  mobileOpen = false,
  onCloseMobile
}) => {
  const recoverySection: NavItemConfig[] = [
    {
      id: 'playground',
      label: 'Autonomous Recovery',
      icon: Play,
      isPrimary: true,
      badge: 'CORE',
      badgeColor: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
    },
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: LayoutDashboard
    },
    {
      id: 'transactions',
      label: 'Transactions',
      icon: Receipt
    },
    {
      id: 'approvals',
      label: 'Approval Queue',
      icon: CheckCircle2,
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount.toString() : undefined,
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse'
    },
  ];

  const insightsSection: NavItemConfig[] = [
    {
      id: 'simulation',
      label: 'Recovery Analytics',
      icon: Sparkles
    },
    {
      id: 'audit',
      label: 'Audit Trail',
      icon: History
    },
  ];

  const systemSection: NavItemConfig[] = [
    {
      id: 'settings',
      label: 'System & Keys',
      icon: Settings
    },
  ];

  const renderNavGroup = (title: string, items: NavItemConfig[]) => (
    <div className="space-y-1 mb-4">
      <div className="px-3 py-1.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-400">
        {title}
      </div>
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onSelectTab(item.id)}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all group cursor-pointer ${
              isActive
                ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-semibold shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent'
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <Icon
                className={`h-4 w-4 transition-colors shrink-0 ${
                  isActive ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-200'
                }`}
              />
              <span className="truncate">{item.label}</span>
            </div>
            {item.badge && (
              <span
                className={`text-[9px] font-mono px-1.5 py-0.5 rounded border font-semibold shrink-0 ${
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
  );

  const navContent = (
    <div className="flex flex-col justify-between h-full">
      <div className="space-y-1">
        {renderNavGroup('RECOVERY', recoverySection)}
        {renderNavGroup('INSIGHTS', insightsSection)}
        {renderNavGroup('SYSTEM', systemSection)}
      </div>

      {/* Enterprise System Info Footer */}
      <div className="p-3 rounded-xl bg-surface-base/90 border border-surface-border text-[11px] font-mono space-y-1 mt-auto">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">GATEWAY:</span>
          <span className="font-semibold text-emerald-400">RAZORPAY TEST</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">ENGINE:</span>
          <span className="text-slate-200 font-semibold">AUTONOMOUS v1.0</span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (hidden on mobile, visible md and up) */}
      <aside className="hidden md:flex w-64 border-r border-surface-border bg-surface-card/60 backdrop-blur-md flex-col justify-between shrink-0 p-3.5 min-h-[calc(100vh-4rem)]">
        {navContent}
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/75 backdrop-blur-sm animate-fadeIn"
            onClick={onCloseMobile}
          />
          {/* Slide-out Drawer */}
          <aside className="relative z-10 w-72 max-w-[80vw] bg-surface-card border-r border-surface-border p-4 flex flex-col justify-between h-full shadow-2xl animate-slideRight overflow-y-auto">
            {navContent}
          </aside>
        </div>
      )}
    </>
  );
};
