import React, { useState, useEffect } from 'react';
import { 
  Search, 
  RefreshCw, 
  ChevronLeft, 
  ChevronRight, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  ShieldAlert, 
  Eye
} from 'lucide-react';
import { Transaction, FailureReason, TransactionStatus } from '../types';
import { fetchTransactions, fetchTransactionById, reseedDatabase } from '../services/api';
import { TransactionDetailModal } from './TransactionDetailModal';

export const Transactions: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [loading, setLoading] = useState<boolean>(true);
  const [, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [failureFilter, setFailureFilter] = useState<string>('ALL');
  const [methodFilter, setMethodFilter] = useState<string>('ALL');

  // Selected Transaction for Modal
  const [selectedTxn, setSelectedTxn] = useState<Transaction | null>(null);
  const [, setLoadingDetail] = useState<boolean>(false);
  const [reseeding, setReseeding] = useState<boolean>(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const offset = (page - 1) * pageSize;
      const res = await fetchTransactions({
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        failure_reason: failureFilter !== 'ALL' ? failureFilter : undefined,
        search: search.trim() || undefined,
        limit: pageSize,
        offset: offset
      });
      setTransactions(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch transactions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, pageSize, statusFilter, failureFilter, methodFilter]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      loadData();
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const handleRowClick = async (id: string) => {
    try {
      setLoadingDetail(true);
      const detail = await fetchTransactionById(id);
      setSelectedTxn(detail);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleReseed = async () => {
    try {
      setReseeding(true);
      await reseedDatabase();
      await loadData();
    } catch (err: any) {
      console.error('Failed to reseed:', err);
    } finally {
      setReseeding(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  const getStatusBadge = (status: TransactionStatus) => {
    switch (status) {
      case 'RECOVERED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3 w-3" /> RECOVERED
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-red-500/10 text-red-400 border border-red-500/30">
            <AlertCircle className="h-3 w-3" /> FAILED
          </span>
        );
      case 'APPROVAL_REQUIRED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <ShieldAlert className="h-3 w-3" /> APPROVAL
          </span>
        );
      case 'STOPPED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-slate-500/10 text-slate-400 border border-slate-500/30">
            <Clock className="h-3 w-3" /> STOPPED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-blue-500/10 text-blue-400 border border-blue-500/30">
            {status}
          </span>
        );
    }
  };

  const getReasonColor = (reason: FailureReason) => {
    switch (reason) {
      case 'UPI_TIMEOUT':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
      case 'BANK_DECLINED':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      case 'INSUFFICIENT_FUNDS':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      case 'NETWORK_ERROR':
        return 'text-sky-400 bg-sky-500/10 border-sky-500/30';
      case 'PAYMENT_METHOD_ERROR':
        return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
      default:
        return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Data Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white">Merchant Transactions</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/30">
              TRANSACTION LEDGER
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Complete merchant transaction ledger with customer history, failure reasons, and LTV context.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleReseed}
            disabled={reseeding || loading}
            className="px-3 py-1.5 rounded-xl bg-surface-card border border-surface-border text-xs font-mono text-slate-300 hover:text-white hover:border-slate-600 transition-colors flex items-center gap-1.5 cursor-pointer"
            title="Reset and regenerate fresh merchant dataset"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${reseeding ? 'animate-spin text-brand-400' : ''}`} />
            <span>{reseeding ? 'Refreshing...' : 'Refresh Dataset'}</span>
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="p-4 rounded-xl glass-card border border-surface-border grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Search Input */}
        <div className="relative">
          <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by ID, name, email..."
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-surface-base border border-surface-border text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Status Filter */}
        <div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="w-full px-3 py-2 rounded-lg bg-surface-base border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-brand-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="FAILED">FAILED (Ready for Recovery)</option>
            <option value="RECOVERED">RECOVERED</option>
            <option value="APPROVAL_REQUIRED">APPROVAL REQUIRED</option>
            <option value="STOPPED">STOPPED</option>
            <option value="RECOVERY_PENDING">RECOVERY PENDING</option>
          </select>
        </div>

        {/* Failure Reason Filter */}
        <div>
          <select
            value={failureFilter}
            onChange={(e) => {
              setFailureFilter(e.target.value);
              setPage(1);
            }}
            className="w-full px-3 py-2 rounded-lg bg-surface-base border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-brand-500"
          >
            <option value="ALL">All Failure Reasons</option>
            <option value="UPI_TIMEOUT">UPI_TIMEOUT</option>
            <option value="BANK_DECLINED">BANK_DECLINED</option>
            <option value="INSUFFICIENT_FUNDS">INSUFFICIENT_FUNDS</option>
            <option value="NETWORK_ERROR">NETWORK_ERROR</option>
            <option value="PAYMENT_METHOD_ERROR">PAYMENT_METHOD_ERROR</option>
            <option value="UNKNOWN">UNKNOWN</option>
          </select>
        </div>

        {/* Payment Method / Page size */}
        <div className="flex items-center justify-between gap-2">
          <select
            value={methodFilter}
            onChange={(e) => {
              setMethodFilter(e.target.value);
              setPage(1);
            }}
            className="w-full px-3 py-2 rounded-lg bg-surface-base border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-brand-500"
          >
            <option value="ALL">All Methods</option>
            <option value="UPI">UPI</option>
            <option value="CARD">Card</option>
            <option value="NETBANKING">Netbanking</option>
            <option value="WALLET">Wallet</option>
          </select>

          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
            className="px-3 py-2 rounded-lg bg-surface-base border border-surface-border text-xs text-slate-200 focus:outline-none focus:border-brand-500"
          >
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
          </select>

          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-lg bg-surface-base border border-surface-border text-slate-300 hover:text-white"
            title="Refresh"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="rounded-xl glass-panel border border-surface-border overflow-hidden">
        <div className="overflow-x-auto w-full">
          <table className="w-full text-left border-collapse min-w-[720px]">
            <thead>
              <tr className="border-b border-surface-border bg-surface-card/90 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                <th className="py-3 px-4">Transaction ID</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Amount (INR)</th>
                <th className="py-3 px-4">Method</th>
                <th className="py-3 px-4">Failure Reason</th>
                <th className="py-3 px-4">Customer LTV</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/60 text-xs">
              {loading ? (
                Array.from({ length: 8 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="py-3 px-4"><div className="h-4 bg-slate-800 rounded w-20" /></td>
                    <td className="py-3 px-4"><div className="h-4 bg-slate-800 rounded w-32" /></td>
                    <td className="py-3 px-4"><div className="h-4 bg-slate-800 rounded w-16" /></td>
                    <td className="py-3 px-4"><div className="h-4 bg-slate-800 rounded w-12" /></td>
                    <td className="py-3 px-4"><div className="h-4 bg-slate-800 rounded w-24" /></td>
                    <td className="py-3 px-4"><div className="h-4 bg-slate-800 rounded w-16" /></td>
                    <td className="py-3 px-4"><div className="h-4 bg-slate-800 rounded w-20" /></td>
                    <td className="py-3 px-4 text-right"><div className="h-4 bg-slate-800 rounded w-12 ml-auto" /></td>
                  </tr>
                ))
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <AlertCircle className="h-8 w-8 mx-auto text-slate-500 mb-2" />
                    <p className="font-medium">No transactions found matching the selected filters.</p>
                    <p className="text-xs text-slate-500 mt-1">Try changing search or resetting filters.</p>
                  </td>
                </tr>
              ) : (
                transactions.map((txn) => (
                  <tr 
                    key={txn.id}
                    onClick={() => handleRowClick(txn.id)}
                    className="hover:bg-surface-highlight/40 transition-colors cursor-pointer group"
                  >
                    <td className="py-3 px-4 font-mono font-medium text-slate-300 group-hover:text-brand-300">
                      {txn.id}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-200">{txn.customer_name || txn.customer?.name || 'Customer'}</div>
                      <div className="text-[11px] font-mono text-slate-400">{txn.customer_email || txn.customer?.email}</div>
                    </td>
                    <td className="py-3 px-4 font-bold text-white">
                      ₹{txn.amount.toLocaleString('en-IN')}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-surface-base border border-surface-border text-slate-300">
                        {txn.payment_method}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-block text-[11px] font-mono px-2 py-0.5 rounded border font-semibold ${getReasonColor(txn.failure_reason)}`}>
                        {txn.failure_reason}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">
                      ₹{(txn.customer_lifetime_value || 0).toLocaleString('en-IN')}
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(txn.status)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRowClick(txn.id);
                        }}
                        className="p-1.5 rounded-lg bg-surface-base border border-surface-border text-slate-400 hover:text-white hover:border-brand-500/50 transition-colors"
                        title="View Context & AI Analysis"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="px-6 py-4 border-t border-surface-border bg-surface-card/60 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
          <div>
            Showing <span className="text-slate-200 font-semibold">{total > 0 ? (page - 1) * pageSize + 1 : 0}</span> to{' '}
            <span className="text-slate-200 font-semibold">{Math.min(page * pageSize, total)}</span> of{' '}
            <span className="text-slate-200 font-semibold">{total.toLocaleString()}</span> synthetic transactions
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="p-1.5 rounded-lg bg-surface-base border border-surface-border text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:text-white hover:border-slate-500"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="font-mono text-xs px-2">
              Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="p-1.5 rounded-lg bg-surface-base border border-surface-border text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:text-white hover:border-slate-500"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Transaction Detail Modal */}
      {selectedTxn && (
        <TransactionDetailModal
          transaction={selectedTxn}
          onClose={() => setSelectedTxn(null)}
        />
      )}
    </div>
  );
};
