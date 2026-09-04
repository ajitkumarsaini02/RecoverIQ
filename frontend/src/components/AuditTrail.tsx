import React, { useState, useEffect } from 'react';
import { 
  History, 
  Search, 
  RefreshCw, 
  ChevronDown, 
  ChevronRight,
  Code,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Zap,
  ArrowRight
} from 'lucide-react';
import { fetchAuditTrail } from '../services/api';
import { AuditEvent } from '../types';

export const AuditTrail: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actorFilter, setActorFilter] = useState<string>('ALL');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('ALL');
  const [txnSearch, setTxnSearch] = useState<string>('');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAuditTrail({
        transaction_id: txnSearch.trim() || undefined,
        limit: 100
      });
      setEvents(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit trail');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [actorFilter, eventTypeFilter]);

  const filteredEvents = events.filter((e) => {
    if (actorFilter !== 'ALL' && e.actor !== actorFilter) return false;
    if (eventTypeFilter !== 'ALL' && e.event_type !== eventTypeFilter) return false;
    if (txnSearch.trim() && e.transaction_id && !e.transaction_id.toLowerCase().includes(txnSearch.toLowerCase())) {
      return false;
    }
    return true;
  });

  const eventTypeOptions = Array.from(new Set(events.map((e) => e.event_type).filter(Boolean))).sort();

  const getActorBadge = (actor: string) => {
    switch (actor) {
      case 'AI_AGENT':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
      case 'POLICY_ENGINE':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'HUMAN_OPERATOR':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'RAZORPAY_GATEWAY':
        return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getEventIcon = (type: string) => {
    if (type.includes('FAILED') || type.includes('REJECTED')) {
      return <XCircle className="h-4 w-4 text-rose-400 shrink-0" />;
    }
    if (type.includes('RECOVERED') || type.includes('SUCCEEDED') || type.includes('APPROVED')) {
      return <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />;
    }
    if (type.includes('APPROVAL') || type.includes('GATE')) {
      return <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />;
    }
    if (type.includes('POLICY')) {
      return <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />;
    }
    return <Zap className="h-4 w-4 text-purple-400 shrink-0" />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white">Immutable Audit Trail</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] sm:text-[11px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              100% EXPLAINABLE & BOUNDED
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Financial compliance log. Every payment failure, AI diagnosis, policy check, and recovery event is recorded permanently with full metadata.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl bg-surface-card border border-surface-border text-xs font-mono text-slate-300 hover:text-white hover:border-slate-600 transition-colors flex items-center gap-2 cursor-pointer w-full sm:w-auto justify-center"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-brand-400' : ''}`} />
          <span>{loading ? 'Refreshing...' : 'Refresh Logs'}</span>
        </button>
      </div>

      {/* Visual Flow Banner */}
      <div className="p-4 rounded-xl glass-panel border border-surface-border">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-2 font-semibold">
          Financial Recovery Lifecycle Flow
        </span>
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <span className="px-2.5 py-1 rounded-lg bg-rose-950/40 text-rose-300 border border-rose-800/40 font-semibold">
            1. Failure Detected
          </span>
          <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
          <span className="px-2.5 py-1 rounded-lg bg-purple-950/40 text-purple-300 border border-purple-800/40 font-semibold">
            2. AI Analysis
          </span>
          <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
          <span className="px-2.5 py-1 rounded-lg bg-emerald-950/40 text-emerald-300 border border-emerald-800/40 font-semibold">
            3. Policy Evaluation
          </span>
          <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
          <span className="px-2.5 py-1 rounded-lg bg-blue-950/40 text-blue-300 border border-blue-800/40 font-semibold">
            4. Recovery Decision
          </span>
          <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
          <span className="px-2.5 py-1 rounded-lg bg-amber-950/40 text-amber-300 border border-amber-800/40 font-semibold">
            5. Execution / Approval
          </span>
          <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
          <span className="px-2.5 py-1 rounded-lg bg-emerald-950/40 text-emerald-300 border border-emerald-800/40 font-semibold">
            6. Final Result
          </span>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="p-4 rounded-xl glass-card border border-surface-border grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={txnSearch}
            onChange={(e) => setTxnSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadData()}
            placeholder="Search by Transaction ID (e.g. txn_0001)..."
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-surface-base border border-surface-border text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Actor Filter */}
        <div>
          <select
            value={actorFilter}
            onChange={(e) => setActorFilter(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-surface-base border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-brand-500 cursor-pointer"
          >
            <option value="ALL">All Actors</option>
            <option value="AI_AGENT">AI_AGENT (Diagnosis & Reasoning)</option>
            <option value="POLICY_ENGINE">POLICY_ENGINE (Safety Guardrails)</option>
            <option value="HUMAN_OPERATOR">HUMAN_OPERATOR (Manual Sign-Offs)</option>
            <option value="RAZORPAY_GATEWAY">RAZORPAY_GATEWAY (Payment Events)</option>
            <option value="SYSTEM">SYSTEM (Lifecycle & Seeding)</option>
          </select>
        </div>

        {/* Event Type Filter */}
        <div>
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-surface-base border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-brand-500 cursor-pointer"
          >
            <option value="ALL">All Event Types</option>
            {eventTypeOptions.map((et) => (
              <option key={et} value={et}>{et}</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* Timeline Stream List */}
      <div className="space-y-3 relative before:absolute before:inset-0 before:left-6 before:w-0.5 before:bg-surface-border before:hidden sm:before:block">
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="p-4 rounded-xl glass-card border border-surface-border animate-pulse h-20" />
          ))
        ) : filteredEvents.length === 0 ? (
          <div className="p-12 rounded-2xl glass-panel border border-surface-border text-center text-slate-400 space-y-2">
            <History className="h-8 w-8 mx-auto text-slate-500" />
            <p className="font-medium text-slate-300">No audit events found matching filters.</p>
            <p className="text-xs text-slate-500">Try adjusting your search criteria or resetting filters.</p>
          </div>
        ) : (
          filteredEvents.map((ev) => {
            const isExpanded = expandedEventId === ev.id;
            return (
              <div
                key={ev.id}
                className="p-4 rounded-xl glass-panel border border-surface-border space-y-2 transition-all hover:border-slate-600 relative sm:ml-10"
              >
                {/* Node indicator */}
                <div className="hidden sm:flex absolute -left-10 top-4 h-6 w-6 rounded-full bg-surface-card border border-surface-border items-center justify-center -translate-x-1/2">
                  <span className="h-2 w-2 rounded-full bg-brand-400" />
                </div>

                <div 
                  onClick={() => setExpandedEventId(isExpanded ? null : ev.id)}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 cursor-pointer"
                >
                  <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                    <button 
                      type="button"
                      className="text-slate-400 hover:text-white shrink-0"
                      aria-label={isExpanded ? 'Collapse event' : 'Expand event'}
                    >
                      {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </button>

                    {getEventIcon(ev.event_type)}

                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border font-bold ${getActorBadge(ev.actor)}`}>
                      {ev.actor}
                    </span>

                    <span className="font-semibold text-xs text-white">
                      {ev.event_type}
                    </span>

                    {ev.decision && (
                      <span className="text-[10px] sm:text-[11px] font-mono text-brand-300 bg-brand-950/60 px-2 py-0.5 rounded border border-brand-800/40 truncate max-w-[240px]">
                        Decision: {ev.decision}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                    {ev.transaction_id && (
                      <span className="text-slate-300 bg-surface-base px-2 py-0.5 rounded border border-surface-border">
                        {ev.transaction_id}
                      </span>
                    )}
                    <span className="text-[11px] text-slate-400">
                      {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : 'Recent'}
                    </span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-surface-border animate-fadeIn space-y-2">
                    <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                      <Code className="h-3.5 w-3.5" />
                      <span>Event Audit Details (JSON Payload):</span>
                    </div>
                    <pre className="p-3 rounded-lg bg-surface-base border border-surface-border text-[11px] font-mono text-emerald-300 overflow-x-auto max-h-60 leading-relaxed">
                      {JSON.stringify(ev.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
