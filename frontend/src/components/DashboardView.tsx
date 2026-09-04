import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert, 
  RefreshCw, 
  ArrowUpRight,
  ShieldCheck,
  Clock,
  Layers
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  Cell, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend 
} from 'recharts';
import { fetchDashboardMetrics } from '../services/api';
import { DashboardMetrics } from '../types';

export const DashboardView: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchDashboardMetrics();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#64748b'];

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold tracking-tight text-white">
              Revenue Recovery Executive Dashboard
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] sm:text-[11px] font-mono font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/30">
              REAL-TIME LEDGER
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Financial recovery analytics computed continuously across active transaction records.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl bg-surface-card border border-surface-border text-xs font-mono text-slate-300 hover:text-white hover:border-slate-600 transition-colors flex items-center justify-center gap-2 cursor-pointer w-full sm:w-auto"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-brand-400' : ''}`} />
          <span>{loading ? 'Recalculating...' : 'Refresh Analytics'}</span>
        </button>
      </div>

      {error && (
        <div className="p-3.5 sm:p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* Prioritized Executive KPI Cards (Grid) */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* KPI 1: Total Failed Revenue (At Risk) */}
        <div className="p-4 sm:p-5 rounded-2xl glass-card border border-rose-900/30">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Failed Revenue</span>
            <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-white tracking-tight font-mono">
            ₹{(metrics?.revenue_at_risk || 0).toLocaleString('en-IN')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {metrics?.total_failed_count || 0} failed payments
          </p>
        </div>

        {/* KPI 2: Recovered Revenue */}
        <div className="p-4 sm:p-5 rounded-2xl glass-card border border-emerald-900/40">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono text-emerald-400 uppercase tracking-wider">Recovered Revenue</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-emerald-400 tracking-tight font-mono">
            +₹{(metrics?.revenue_recovered || 0).toLocaleString('en-IN')}
          </div>
          <div className="flex items-center gap-1 text-[11px] text-emerald-400/90 mt-1">
            <ArrowUpRight className="h-3 w-3 shrink-0" />
            <span>{metrics?.successful_recoveries_count || 0} successfully captured</span>
          </div>
        </div>

        {/* KPI 3: Recovery Rate */}
        <div className="p-4 sm:p-5 rounded-2xl glass-card border border-brand-900/40">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono text-brand-300 uppercase tracking-wider">Recovery Rate</span>
            <TrendingUp className="h-4 w-4 text-brand-400 shrink-0" />
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-brand-300 tracking-tight font-mono">
            {metrics?.recovery_rate || 0}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Avg Ticket: ₹{(metrics?.average_recovery_amount || 0).toLocaleString('en-IN')}
          </p>
        </div>

        {/* KPI 4: Recovery Attempts */}
        <div className="p-4 sm:p-5 rounded-2xl glass-card border border-surface-border">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Attempts Executed</span>
            <Layers className="h-4 w-4 text-blue-400 shrink-0" />
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-white tracking-tight font-mono">
            {metrics?.recovery_attempts_count || 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Automated recovery runs
          </p>
        </div>

        {/* KPI 5: Pending Recovery */}
        <div className="p-4 sm:p-5 rounded-2xl glass-card border border-surface-border">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Pending Recovery</span>
            <Clock className="h-4 w-4 text-amber-400 shrink-0" />
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-amber-300 tracking-tight font-mono">
            {Math.max(0, (metrics?.total_failed_count || 0) - (metrics?.successful_recoveries_count || 0) - (metrics?.stopped_cases_count || 0))}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Awaiting customer retry / link
          </p>
        </div>

        {/* KPI 6: Approval Required */}
        <div className="p-4 sm:p-5 rounded-2xl glass-card border border-amber-900/30">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono text-amber-400 uppercase tracking-wider">Approval Required</span>
            <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0" />
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-amber-400 tracking-tight font-mono">
            {metrics?.pending_approvals_count || 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            High-value gated payments
          </p>
        </div>

        {/* KPI 7: Stopped Transactions */}
        <div className="p-4 sm:p-5 rounded-2xl glass-card border border-surface-border">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Stopped Halts</span>
            <ShieldCheck className="h-4 w-4 text-slate-400 shrink-0" />
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-slate-300 tracking-tight font-mono">
            {metrics?.stopped_cases_count || 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Max retry policy halts
          </p>
        </div>

        {/* KPI 8: Total Transactions */}
        <div className="p-4 sm:p-5 rounded-2xl glass-card border border-surface-border">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Portfolio Total</span>
            <span className="text-xs font-mono text-slate-400">LEDGER</span>
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-slate-200 tracking-tight font-mono">
            {(metrics?.total_transactions_count || 0).toLocaleString('en-IN')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Active merchant txns
          </p>
        </div>
      </div>

      {/* Meaningful Visual Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Revenue at Risk vs Revenue Recovered */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Revenue at Risk vs Recovered (Trend)</h3>
            <span className="text-[10px] font-mono text-slate-400">₹ INR</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics?.recovery_trend || []}>
                <defs>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorRecovered" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1f293d', borderRadius: '0.75rem', fontSize: '12px' }}
                  formatter={(val: any) => [`₹${Number(val).toLocaleString('en-IN')}`, '']}
                />
                <Legend />
                <Area type="monotone" dataKey="at_risk" name="Revenue at Risk" stroke="#f43f5e" fillOpacity={1} fill="url(#colorRisk)" />
                <Area type="monotone" dataKey="recovered" name="Revenue Recovered" stroke="#10b981" fillOpacity={1} fill="url(#colorRecovered)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Failure Reasons Breakdown */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Failure Reasons Breakdown</h3>
            <span className="text-[10px] font-mono text-slate-400">BY COUNT</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics?.failure_reasons_breakdown || []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" stroke="#64748b" fontSize={11} />
                <YAxis dataKey="reason" type="category" stroke="#64748b" fontSize={10} width={110} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1f293d', borderRadius: '0.75rem', fontSize: '12px' }}
                  formatter={(val: any, _name: any, item: any) => [
                    `${val} transactions (₹${item.payload.amount.toLocaleString('en-IN')})`,
                    'Volume'
                  ]}
                />
                <Bar dataKey="count" name="Failed Count" fill="#3b82f6" radius={[0, 4, 4, 0]}>
                  {metrics?.failure_reasons_breakdown?.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: AI Recovery Actions Distribution */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">AI Recovery Action Distribution</h3>
            <span className="text-[10px] font-mono text-purple-400">AUTONOMOUS DECISIONS</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics?.recovery_actions_breakdown || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="action" stroke="#64748b" fontSize={10} interval={0} angle={-15} textAnchor="end" height={45} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1f293d', borderRadius: '0.75rem', fontSize: '12px' }}
                />
                <Bar dataKey="count" name="Actions Taken" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Portfolio Outcome Statuses */}
        <div className="p-5 sm:p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Transaction Status Outcomes</h3>
            <span className="text-[10px] font-mono text-emerald-400">PORTFOLIO STATUS</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics?.recovery_outcomes_breakdown || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="outcome" stroke="#64748b" fontSize={10} interval={0} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1f293d', borderRadius: '0.75rem', fontSize: '12px' }}
                />
                <Bar dataKey="count" name="Transactions" fill="#10b981" radius={[4, 4, 0, 0]}>
                  {metrics?.recovery_outcomes_breakdown?.map((entry, index) => {
                    const color = entry.outcome === 'RECOVERED' ? '#10b981' : entry.outcome === 'FAILED' ? '#ef4444' : entry.outcome === 'STOPPED' ? '#64748b' : '#f59e0b';
                    return <Cell key={`cell-outcome-${index}`} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
