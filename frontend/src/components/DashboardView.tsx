import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert, 
  RefreshCw, 
  ArrowUpRight,
  ShieldCheck,
  XCircle,
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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white">Revenue Recovery Intelligence</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/30">
              LIVE METRICS
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time financial recovery analytics computed dynamically across active transaction records.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl bg-surface-card border border-surface-border text-xs font-mono text-slate-300 hover:text-white hover:border-slate-600 transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-brand-400' : ''}`} />
          <span>{loading ? 'Recalculating...' : 'Refresh Analytics'}</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* 8 Dynamic KPI Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Card 1: Revenue at Risk */}
        <div className="p-5 rounded-2xl glass-card border border-rose-900/40 relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Revenue at Risk</span>
            <AlertTriangle className="h-4 w-4 text-rose-400" />
          </div>
          <div className="text-2xl font-extrabold text-white tracking-tight">
            ₹{(metrics?.revenue_at_risk || 0).toLocaleString('en-IN')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {metrics?.total_failed_count || 0} failed merchant transactions
          </p>
        </div>

        {/* Card 2: Revenue Recovered */}
        <div className="p-5 rounded-2xl glass-card border border-emerald-900/40 relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-emerald-400 uppercase tracking-wider">Revenue Recovered</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-extrabold text-emerald-400 tracking-tight">
            +₹{(metrics?.revenue_recovered || 0).toLocaleString('en-IN')}
          </div>
          <div className="flex items-center gap-1 text-[11px] text-emerald-400/90 mt-1">
            <ArrowUpRight className="h-3.5 w-3.5" />
            <span>{metrics?.successful_recoveries_count || 0} recovered payments</span>
          </div>
        </div>

        {/* Card 3: Recovery Rate */}
        <div className="p-5 rounded-2xl glass-card border border-brand-900/40 relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-brand-300 uppercase tracking-wider">Recovery Rate</span>
            <TrendingUp className="h-4 w-4 text-brand-400" />
          </div>
          <div className="text-2xl font-extrabold text-brand-300 tracking-tight">
            {metrics?.recovery_rate || 0}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Avg: ₹{(metrics?.average_recovery_amount || 0).toLocaleString('en-IN')} / recovery
          </p>
        </div>

        {/* Card 4: Failed Payments */}
        <div className="p-5 rounded-2xl glass-card border border-surface-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Failed Payments</span>
            <XCircle className="h-4 w-4 text-slate-400" />
          </div>
          <div className="text-2xl font-extrabold text-white tracking-tight">
            {metrics?.total_failed_count || 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Total failed transactions
          </p>
        </div>

        {/* Card 5: Recovery Attempts */}
        <div className="p-5 rounded-2xl glass-card border border-surface-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Recovery Attempts</span>
            <Layers className="h-4 w-4 text-blue-400" />
          </div>
          <div className="text-2xl font-extrabold text-white tracking-tight">
            {metrics?.recovery_attempts_count || 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Total recovery executions
          </p>
        </div>

        {/* Card 6: Successful Recoveries */}
        <div className="p-5 rounded-2xl glass-card border border-surface-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Successful Recoveries</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-extrabold text-white tracking-tight">
            {metrics?.successful_recoveries_count || 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Captured & verified
          </p>
        </div>

        {/* Card 7: Pending Approvals */}
        <div className="p-5 rounded-2xl glass-card border border-amber-900/40">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-amber-400 uppercase tracking-wider">Pending Approvals</span>
            <ShieldAlert className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-2xl font-extrabold text-amber-400 tracking-tight">
            {metrics?.pending_approvals_count || 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            High-value gated payments
          </p>
        </div>

        {/* Card 8: Stopped Cases */}
        <div className="p-5 rounded-2xl glass-card border border-surface-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Stopped Cases</span>
            <ShieldCheck className="h-4 w-4 text-slate-400" />
          </div>
          <div className="text-2xl font-extrabold text-slate-300 tracking-tight">
            {metrics?.stopped_cases_count || 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Policy 2-retry limits enforced
          </p>
        </div>
      </div>

      {/* 5 Dynamic Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Revenue at Risk vs Revenue Recovered */}
        <div className="p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">1. Revenue at Risk vs Revenue Recovered (7 Days)</h3>
            <span className="text-[10px] font-mono text-slate-400">₹ AMOUNTS</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics?.recovery_trend || []}>
                <defs>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorRecovered" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
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
        <div className="p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">2. Failure Reasons Breakdown</h3>
            <span className="text-[10px] font-mono text-slate-400">BY OCCURRENCE</span>
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
                    `${val} txns (₹${item.payload.amount.toLocaleString('en-IN')})`,
                    'Failures'
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

        {/* Chart 3: Recovery Actions Distribution */}
        <div className="p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">3. Recovery Actions Recommended & Taken</h3>
            <span className="text-[10px] font-mono text-purple-400">AI AGENT & POLICY</span>
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
                <Bar dataKey="count" name="Actions Executed" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Recovery Outcomes Distribution */}
        <div className="p-6 rounded-2xl glass-panel border border-surface-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">4. Transaction Recovery Status Outcomes</h3>
            <span className="text-[10px] font-mono text-emerald-400">PORTFOLIO HEALTH</span>
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
                <Bar dataKey="count" name="Count" fill="#10b981" radius={[4, 4, 0, 0]}>
                  {metrics?.recovery_outcomes_breakdown?.map((entry, index) => {
                    const color = entry.outcome === 'RECOVERED' ? '#10b981' : entry.outcome === 'FAILED' ? '#ef4444' : entry.outcome === 'STOPPED' ? '#64748b' : '#f59e0b';
                    return <Cell key={`cell-outcome-${index}`} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 5: 7-Day Recovery Rate Trend (%) */}
        <div className="p-6 rounded-2xl glass-panel border border-surface-border space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">5. 7-Day Recovery Rate Trend (%)</h3>
            <span className="text-[10px] font-mono text-brand-300 font-bold">CONVERSION EFFICIENCY</span>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics?.recovery_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} unit="%" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1f293d', borderRadius: '0.75rem', fontSize: '12px' }}
                  formatter={(val: any) => [`${val}%`, 'Recovery Rate']}
                />
                <Area type="monotone" dataKey="recovery_rate" name="Recovery Rate %" stroke="#10b981" fill="#10b981" fillOpacity={0.2} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
